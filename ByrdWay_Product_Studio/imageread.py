"""Read and mathematically verify IMAGE-ONLY (flattened) PDF pages - free, local, no AI.

Pipeline per page:
  1. render at two resolutions and OCR each (RapidOCR, ONNX, runs offline);
  2. extract mathematical statements from the text lines
     - arithmetic equalities  "6 × 9 = 54"
     - solved equations        "3x + 5 = 20" followed below by "x = 5"
  3. verify with the deterministic Academic Verifier;
  4. a statement that FAILS is retried under known OCR confusions (÷→+, ×→x/+, lost superscripts,
     ✓→V ...). If any plausible reading verifies, it is reported as LIKELY_OCR_MISREAD, never as an
     error. Only statements failing under every reading become SUSPECTED_ERROR;
  5. unknown words read identically in both passes, with high confidence, are SUSPECTED_TYPO.
Every finding carries the page number, its rectangle on the page (PDF points) and a cropped picture.
Nothing here edits the PDF: findings need the owner's confirmation (see release.decide_image_finding).
"""
import hashlib, json, re
from pathlib import Path

import academic

OCR_DPIS = (144, 216)
MIN_CONF = 0.50
_ENGINE = None

STATUS_OK, STATUS_ERR, STATUS_MISREAD, STATUS_UNREADABLE = ('VERIFIED_CORRECT', 'SUSPECTED_ERROR',
                                                            'LIKELY_OCR_MISREAD', 'NOT_CHECKABLE')


def available():
    try:
        import rapidocr_onnxruntime  # noqa
        return True
    except Exception:
        return False


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz


def ocr_page(page, dpi):
    """Return [{'text','conf','rect':(x0,y0,x1,y1) in PDF points}] for one page."""
    import numpy as np
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
    res, _ = _engine()(img)
    s = 72.0 / dpi
    out = []
    for box, text, conf in res or []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        out.append({'text': str(text).strip(), 'conf': float(conf),
                    'rect': (min(xs) * s, min(ys) * s, max(xs) * s, max(ys) * s)})
    return out


# ------------------------------------------------------------------ normalising OCR text
def clean(text):
    t = text.replace('−', '-').replace('–', '-').replace('—', '-').replace('·', '×')
    t = re.sub(r'(?<=\d)\s*[Vv✓✔]\s*$', '', t)                     # trailing check mark read as V
    t = re.sub(r'^(?:example|check|solution|answer|ans|result)s?\s*:\s*', '', t, flags=re.I)
    return t.strip()


def _alternatives(expr):
    """Plausible readings of an OCR'd arithmetic left-hand side (bounded)."""
    alts = {expr}
    swaps = [('+', '÷'), ('+', '×'), ('x', '×'), ('X', '×'), ('-', '÷'), ('-', '='), ('4', '÷')]
    for a, b in swaps:
        idx = [i for i, ch in enumerate(expr) if ch == a]
        for i in idx[:4]:
            alts.add(expr[:i] + b + expr[i + 1:])
    # lost superscript: ")2" -> ")^2", "x2" -> "x^2", digit run after ")"
    alts |= {re.sub(r'\)\s*([23])(?!\d)', r')^\1', e) for e in list(alts)}
    alts |= {re.sub(r'(?<=\d)([23])(?=\s*[-+×÷*/=]|$)', r'^\1', e) for e in list(alts)}
    return list(alts)[:40]


def _equation_readings(eq):
    """Ordered readings of an OCR'd equation: the literal text first, then known OCR confusions
    (':' for ÷/−, lost signs, lost superscripts: x2 -> x^2, 32x-1=33 -> 3^(2x-1)=3^3)."""
    lhs, rhs = eq.split('=', 1)
    outs = []

    def add(l, r):
        if (l, r) not in outs and ':' not in l:
            outs.append((l, r))
    if ':' in lhs:
        for op in ('-', '÷', '+'):
            add(lhs.replace(':', op), rhs)
    add(lhs, rhs)
    base = list(outs)
    for l, r in base:
        for op in ('-', '+'):                                         # sign lost: "2x1=3" -> "2x-1=3"
            add(re.sub(r'([a-z])(\d)', r'\1' + op + r'\2', l, flags=re.I), r)
    sup = lambda e: re.sub(r'([a-z])([23])(?![0-9])', r'\1^\2', e, flags=re.I)
    for l, r in base:
        add(sup(l), sup(r))
    for l, r in base:
        m = re.match(r'^\s*(\d)(\d?\s*[a-z][^=]*)$', l, re.I)          # base digit + exponent expression
        if m:
            b = m.group(1)
            add(f'{b}^({m.group(2).strip()})', re.sub(r'^\s*' + b + r'(\d+)\s*$', b + r'^(\1)', r))
    return [l + '=' + r for l, r in outs]


def _verify_arith(lhs, rhs):
    r = academic.verify_item({'question': lhs, 'answer': rhs, 'verify': {'type': 'expression', 'expr': lhs}})
    return r


_COLON = re.compile(r'(?<=[\d)a-zA-Z])\s+:\s+(?=[(\d\-a-zA-Z])')


def check_line(line):
    """Arithmetic claims in one OCR line. OCR often reads ÷ and − as ':'; every plausible reading is tried."""
    t = clean(line['text'])
    if not _COLON.search(t):
        return _check_text(t)
    variants = [_check_text(_COLON.sub(f' {op} ', t)) for op in ('÷', '-', '+')]
    variants.sort(key=lambda res: -sum(1 for r in res if r[0] == STATUS_OK))
    return variants[0]


def _check_text(t):
    out = []
    for c in academic.extract_arithmetic_claims(t):
        lhs, rhs = c['question'], c['answer']
        if re.search(r'\d\s*[xX]\s*\d', c['location']['text']):
            continue                     # OCR 'x' between digits: times sign or a variable? ambiguous
        start = c['location']['offset']
        before = t[:start].rstrip()
        # OCR: a claim glued to a variable or operator ("x2-4x-5=0" -> "4x-5=0") is part of an equation
        if re.search(r'[A-Za-z]', lhs.replace('×', '')) or (before and before[-1] in '+-×÷*/^=(' + 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            continue
        r = _verify_arith(lhs, rhs)
        if r['status'] == academic.CORRECT:
            out.append((STATUS_OK, lhs, rhs, r, None))
            continue
        if r['status'] != academic.INCORRECT:
            out.append((STATUS_UNREADABLE, lhs, rhs, r, None))
            continue
        alt_ok = None
        for alt in _alternatives(lhs):
            if alt == lhs:
                continue
            ra = _verify_arith(alt, rhs)
            if ra['status'] == academic.CORRECT:
                alt_ok = alt
                break
        if alt_ok:
            out.append((STATUS_MISREAD, lhs, rhs, r, alt_ok))
        else:
            out.append((STATUS_ERR, lhs, rhs, r, None))
    return out


_EQ = re.compile(r'([0-9a-z()\s+\-×÷*/^.:]*[a-z][0-9a-z()\s+\-×÷*/^.:]*=[0-9a-z()\s+\-×÷*/^.]+)$', re.I)
_SOL = re.compile(r'^\s*([a-z])\s*=\s*(-?\d+(?:\.\d+)?(?:/\d+)?)\s*$', re.I)


def check_solved_equations(lines):
    """'3x + 5 = 20' followed (just below, same column) by 'x = 5'."""
    out = []
    for i, ln in enumerate(lines):
        t = clean(ln['text'])
        t = re.sub(r'^.*?(?:solve(?:\s+for\s+[a-z])?\s*:?)\s*', '', t, flags=re.I)
        m = _EQ.search(t)
        if not m or _SOL.match(t) or t.count('=') != 1:
            continue
        eq = m.group(1).strip()
        vars_ = set(re.findall(r'(?<![a-z])([a-z])(?![a-z])', eq, re.I))
        if len(vars_) != 1:
            continue
        v = vars_.pop()
        x0, y0, x1, y1 = ln['rect']
        h = max(4.0, y1 - y0)
        best, best_all = None, []
        for other in lines[i + 1:]:
            ox0, oy0, ox1, oy1 = other['rect']
            if oy0 < y0 or oy0 > y1 + 8 * h or ox1 < x0 - 3 * h or ox0 > x1 + 3 * h:
                continue
            sm = _SOL.match(clean(other['text']))
            if sm and sm.group(1).lower() == v.lower():
                if best_all and abs(other['rect'][1] - best_all[0][0]['rect'][1]) > 1.5 * h:
                    break                            # the FIRST isolated answer closes this worked example
                best = (other, sm.group(2))
                best_all.append(best)
        if not best:
            continue
        shown = [x[1] for x in best_all]
        status, r, used = STATUS_UNREADABLE, None, eq
        for reading in _equation_readings(eq):
            ok, any_parsed = True, False
            for val in shown:
                try:
                    l_, r_ = academic.safe_equation(reading)
                    sym = academic.sp.Symbol(v)
                    diff = complex(academic.sp.N((l_ - r_).subs(sym, academic.safe_parse(val))))
                    any_parsed = True
                    ok = ok and abs(diff) < 1e-6
                except Exception:
                    ok = False
            if any_parsed and ok:
                status, used = STATUS_OK, reading
                break
            if any_parsed:
                status = STATUS_ERR
        if status == STATUS_ERR:
            for reading in _equation_readings(eq):
                r = academic.verify_item({'question': f'Solve {reading}', 'answer': ' or '.join(f'{v} = {x}' for x in shown),
                                          'verify': {'type': 'solve', 'equation': reading, 'var': v}})
                if r['status'] == academic.INCORRECT:
                    break
        r = r or {'expected': None, 'methods': ['substitution of each shown solution'], 'evidence': f'{used}: shown solutions satisfy it'}
        rect = (min(x0, best[0]['rect'][0]), y0, max(x1, best[0]['rect'][2]), best[0]['rect'][3])
        out.append({'status': status, 'kind': 'solved equation', 'statement': f'{eq}  →  ' + ' or '.join(f'{v} = {x}' for x in shown),
                    'shown': ' or '.join(f'{v} = {x}' for x in shown), 'expected': r.get('expected'), 'rect': rect,
                    'conf': min(ln['conf'], best[0]['conf']), 'methods': r['methods'], 'evidence': r['evidence']})
    return out


# ------------------------------------------------------------------ worked steps (v0.6.0)
# A worked example on a page is a CHAIN of equal expressions:
#     f(4) = 2(4) + 3          Simplify: (3x2)3          7,500,000 = 7.5 × 106
#          = 8 + 3                     = 33(x2)3
#          = 11                        = 27x6
# Each "= ..." line below an expression continues it. Every step must equal the step before it.
_ARROW = re.compile(r'\s*(?:-?→|->|⇒|=>)\s*')
_LABEL = re.compile(r'^(?:[A-Za-z][A-Za-z\'’]+[\s,]*)+:\s*|^(?:so|then|thus|check|hence|now)\b[\s,]*', re.I)
_FDEF = re.compile(r'(?<![A-Za-z])([A-Za-z])\(\s*([a-z])\s*\)\s*=\s*([^=,;:]+?)\s*(?:[,;:].*)?$')
_FCALL = re.compile(r'(?<![A-Za-z])([A-Za-z])\(\s*(-?\d+(?:\.\d+)?)\s*\)')
_BAD = re.compile(r'[?？@#$%&_\[\]{}<>≤≥≠~"“”|]|[^\x00-\x7F×÷·−–—√π²³]')


def _norm_term(t):
    t = t.replace('−', '-').replace('–', '-').replace('—', '-').replace('·', '×').strip()
    return t.strip(' .,;')


def _term_readings(t, funcs):
    """Plausible readings of one OCR'd step (literal first). Known OCR losses: superscripts
    (x2 -> x^2, )3 -> )^3, 33(x2) -> 3^3(x^2), ×106 -> ×10^6), thousands separators (7.500,000)."""
    t = _norm_term(t)
    if not t or _BAD.search(t) or len(t) > 80:
        return []
    t = re.sub(r'(?<=[\d)])\s*[xX]\s*(?=10\s*-?\d)', '×', t)
    t = re.sub(r'(?<=\d)\s*[Vv✓✔]\s*$', '', t)            # 7.5x106 -> 7.5×106
    for name, (var, body) in funcs.items():                              # f(4) -> (2(4)+3)
        t = re.sub(rf'(?<![A-Za-z]){name}\(\s*(-?\d+(?:\.\d+)?)\s*\)',
                   lambda m: '(' + re.sub(rf'(?<![A-Za-z]){var}(?![A-Za-z])', f'({m.group(1)})', body) + ')', t)
    if _FCALL.search(t) or re.search(r'[A-Za-z]{2,}', t.replace('sqrt', '')):
        return []                                                        # unknown function / prose
    rules = [
        lambda s: re.sub(r'(?<=\d)[.,](?=\d{3}(?:[.,]\d{3})*(?!\d))', '', s),          # 7.500,000 -> 7500000
        lambda s: re.sub(r'(×\s*10)\s*(-?\d{1,2})(?![\d.])', r'\1^(\2)', s),           # ×106 -> ×10^(6)
        lambda s: re.sub(r'([a-zA-Z])([2-9])(?![\d.])', r'\1^\2', s),                   # x2 -> x^2
        lambda s: re.sub(r'\)\s*([2-9])(?![\d.])', r')^\1', s),                          # )3 -> )^3
        lambda s: re.sub(r'(?<![\d.^])(\d)([2-9])(?=\()', r'\1^\2', s),                 # 33(x) -> 3^3(x)
        lambda s: s.replace('X', 'x'),
        lambda s: re.sub(r'(?<![A-Za-z])V(?=\s*\d)', '√', s),                          # V36 -> √36
        lambda s: re.sub(r'(?<![\d.^])([2-9])([2-9])(?![\d.(])', r'\1^\2', s),           # 52 -> 5^2, 24 -> 2^4
        lambda s: re.sub(r'(?<=\d)\.(?=\d(?!\d))', '×', s),                             # 6·3 read as 6.3
    ]
    outs = []
    for mask in range(1 << len(rules)):
        s = t
        for i, rule in enumerate(rules):
            if mask >> i & 1:
                s = rule(s)
        if s not in outs:
            outs.append(s)
    parsed = []
    import warnings
    for s in outs[:96]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                e = academic.safe_parse(s)
        except Exception:
            continue
        if isinstance(e, academic.sp.Expr):
            parsed.append((s, e))
    return parsed


def _fingerprint(e):
    syms = sorted(e.free_symbols, key=str)
    vals = []
    for k, x in enumerate((0.37, 1.13, -0.83)):
        try:
            v = complex(academic.sp.N(e.subs({s: x + 0.11 * i for i, s in enumerate(syms)})))
        except Exception:
            return None
        vals.append(v)
    return vals


def _same(a, b):
    fa, fb = _fingerprint(a), _fingerprint(b)
    if fa is None or fb is None:
        return False
    if any(abs(x - y) > 1e-7 * max(1, abs(x)) for x, y in zip(fa, fb)):
        return False
    try:
        return academic.sp.simplify(a - b) == 0
    except Exception:
        return False


def _split_steps(text):
    """'Simplify: (3x2)3 = 33(x2)3 = 27x6' -> ['(3x2)3', '33(x2)3', '27x6']; leading '=' kept as a marker."""
    t = clean(text)
    cont = t.lstrip().startswith('=')
    t = _LABEL.sub('', t.lstrip(' =')) if not cont else t.lstrip(' =')
    parts = [p for p in re.split(r'\s*=\s*', t)]
    return cont, [p for p in parts if p.strip()]


def _function_defs(lines):
    """[(line, name, var, body)] for every 'f(x) = ...' definition on the page."""
    defs = []
    for ln in lines:
        m = _FDEF.search(clean(ln['text']))
        if m and m.group(1) != m.group(2):
            body = _norm_term(m.group(3))
            try:
                academic.safe_parse(re.sub(r'([a-zA-Z])([2-9])(?!\d)', r'\1^\2', body))
            except Exception:
                continue
            defs.append((ln, m.group(1), m.group(2), re.sub(r'([a-zA-Z])([2-9])(?!\d)', r'\1^\2', body)))
    return defs


def _funcs_for(defs, ln):
    """The definition in force for a line: the nearest one above it (same column preferred)."""
    out = {}
    x0, y0 = ln['rect'][0], ln['rect'][1]
    for d, name, var, body in sorted(defs, key=lambda t: (t[0]['rect'][1])):
        if d['rect'][1] <= y0 + 1:
            col = abs(d['rect'][0] - x0) < 250
            if name not in out or col or not out[name][2]:
                out[name] = (var, body, col)
    return {k: (v[0], v[1]) for k, v in out.items()}


def check_worked_steps(lines, other_pass=()):
    """Verify every step of worked examples (chains of '=' within a line and '= ...' lines below it).
    Returns items with status VERIFIED_CORRECT, SUSPECTED_ERROR or NOT_CHECKABLE (+ reason).
    A step is only called an error when it was read clearly (confidence >= 0.85, same text in both
    OCR passes), fails under EVERY plausible reading, and does not match any other expression on the
    page (which would mean the two lines belong to different examples)."""
    chains = []                                   # [{'lines': [...], 'terms': [(text, line)], 'cont': bool}]
    defs = _function_defs(lines)
    for ln in lines:
        t = clean(ln['text'])
        if _ARROW.search(t):
            continue
        if '=' not in t:
            # a bare expression ("Simplify: (3x2)3", "3x(x2-4x+5)") can start a chain continued below
            body = _LABEL.sub('', t)
            if re.search(r'[\d)]', body) and _term_readings(body, _funcs_for(defs, ln)):
                chains.append({'lines': [ln], 'terms': [(body, ln, False)]})
            continue
        if _ARROW.search(t):
            continue                              # equation steps with arrows: handled by solved-equation check
        cont, parts = _split_steps(t)
        if not parts:
            continue
        if cont:
            x0, y0, x1, y1 = ln['rect']
            h = max(4.0, y1 - y0)
            best = None
            for ch in chains:
                last = ch['lines'][-1]['rect']
                first = ch['lines'][0]['rect']
                gap = y0 - last[3]
                if -0.5 * h <= gap <= 2.2 * h and first[0] - 2.5 * h <= x0 <= first[2] + h:
                    d = abs(x0 - first[0]) + gap
                    if best is None or d < best[0]:
                        best = (d, ch)
            if best:
                best[1]['lines'].append(ln)
                best[1]['terms'] += [(p, ln, True) for p in parts]
            continue
        raw = clean(ln['text'])
        first_is_label = bool(re.match(r'^\s*(?:[A-Za-z]{2,}\s*)+=', raw))      # "Area = (x+5)(x-2)"
        defn = _FDEF.search(raw)
        terms = [(p, ln, False) for p in parts]
        if first_is_label or (defn and parts and re.fullmatch(r'\s*[A-Za-z]\(\s*[a-z]\s*\)\s*', parts[0])):
            terms = terms[1:]                                                       # a name or definition, not a step
        if parts and re.fullmatch(r'\s*[a-zA-Z]\s*', parts[0]):
            terms = terms[1:]                                                       # "y = 2x + 1" defines y
        chains.append({'lines': [ln], 'terms': terms})
    page_exprs = []
    for ch in chains:
        for p, ln, _ in ch['terms']:
            r = _term_readings(p, _funcs_for(defs, ln))
            if r:
                page_exprs.append((p, r))
    other_texts = [re.sub(r'\s+', '', clean(o['text'])) for o in other_pass]
    out = []
    for ch in chains:
        terms = [(p, ln, c, _term_readings(p, _funcs_for(defs, ln))) for p, ln, c in ch['terms']]
        skip = set()
        for k, ((pa, la, ca, ra), (pb, lb, cb, rb)) in enumerate(zip(terms, terms[1:])):
            if k in skip:
                continue
            if k + 2 < len(terms) and terms[k + 2][1] is lb and ra and rb:
                # OCR reads '-' as '=' ("= 3x3 + 4x = 14" for "= 3x3 + 4x - 14"): try the joined reading
                pc = terms[k + 2][0]
                for op in ('-', '+'):
                    rj = _term_readings(f'{pb} {op} {pc}', _funcs_for(defs, lb))
                    if rj and any(_same(ea, ej) for _, ea in ra[:8] for _, ej in rj[:8]):
                        out.append(_step_item(STATUS_OK, pa, f'{pb} {op} {pc}', la, lb, ra[0][1],
                                              f'equal to the previous step when "=" is read as "{op}"'))
                        skip |= {k + 1}
                        break
                if k + 1 in skip:
                    continue
            if not ra or not rb:
                continue                               # prose, an unknown function or an unreadable step
            if re.sub(r'[\s()]', '', pa) == re.sub(r'[\s()]', '', pb):
                continue                               # "(x) = x": nothing to check
            has_var = any(e.free_symbols for _, e in ra + rb)
            if has_var and la is lb and not cb:
                # an '=' inside one line between expressions with variables may be an EQUATION to solve,
                # not a simplification step: verify if it is an identity, never accuse.
                if any(_same(ea, eb) for _, ea in ra[:6] for _, eb in rb[:6]):
                    out.append(_step_item(STATUS_OK, pa, pb, la, lb, ra[0][1], 'identity holds'))
                continue
            match = next(((sa, sb) for sa, ea in ra for sb, eb in rb if _same(ea, eb)), None)
            if match:
                out.append(_step_item(STATUS_OK, pa, pb, la, lb, ra[0][1],
                                      f'step equal to the previous step (read as {match[0]} = {match[1]})'))
                continue
            # clear = read the same way in BOTH passes (independent resolutions) with reasonable confidence
            clear = (min(la['conf'], lb['conf']) >= 0.6 and
                     all(any(re.sub(r'\s+', '', _norm_term(x)) in o for o in other_texts) for x in (pa, pb)))
            elsewhere = any(q not in (pa, pb) and any(_same(eb, eq) for _, eb in rb[:4] for _, eq in rq[:4])
                            for q, rq in page_exprs)
            if clear and not elsewhere:
                out.append(_step_item(STATUS_ERR, pa, pb, la, lb, ra[0][1],
                                      'this step does not equal the step before it under any plausible reading'))
            else:
                why = ('read with low confidence or differently in the second pass' if not clear else
                       'matches another expression on the page - the lines may belong to different examples')
                out.append(_step_item(STATUS_UNREADABLE, pa, pb, la, lb, ra[0][1], why))
    return out


def _step_item(status, pa, pb, la, lb, prev, why):
    rect = (min(la['rect'][0], lb['rect'][0]), min(la['rect'][1], lb['rect'][1]),
            max(la['rect'][2], lb['rect'][2]), max(la['rect'][3], lb['rect'][3]))
    try:
        exp = str(academic.sp.expand(prev)) if prev.free_symbols else str(academic.sp.nsimplify(prev))
    except Exception:
        exp = str(prev)
    exp = re.sub(r'(?<=[\d)])\*(?=[A-Za-z(])', '', exp).replace('*', '×')
    return {'status': status, 'kind': 'worked step', 'statement': f'{_norm_term(pa)} = {_norm_term(pb)}',
            'shown': _norm_term(pb), 'expected': exp.replace('**', '^') if status == STATUS_ERR else None,
            'rect': rect, 'conf': min(la['conf'], lb['conf']), 'methods': ['symbolic simplify(previous - step) == 0',
            'numeric spot checks at 3 points', 'OCR re-readings (lost superscripts, separators)'],
            'evidence': why, 'reason': why if status == STATUS_UNREADABLE else None, 'line': lb['text']}


# ------------------------------------------------------------------ typos
_MATH_WORDS = set('''pemdas gcf lcm lcd sqrt abs coeff vertex axis parabola quadratic polynomial binomial trinomial
monomial integers integer rational irrational reciprocal exponent exponents radicand radical asymptote
inequalities inequality distributive associative commutative byrdway anime honors subtopics subtopic
precalculus algebra geometry intercept intercepts slope midpoint discriminant factoring factor'''.split())


def _spell():
    from spellchecker import SpellChecker
    sp = SpellChecker()
    sp.word_frequency.load_words(_MATH_WORDS)
    return sp


_SHORT = set('''a an of to is in at by or as if on it be we do no up so b c x y and add the for are its not can one two use all any has how may new per set sum way who why yes now has its out off'''.split())
_PREFIXES = ('multi', 'non', 'semi', 'pre', 'sub', 'anti', 'inter', 'self', 'co')


def _segmentable(w, sp, memo=None):
    """True if w is several known words run together (OCR dropped the spaces)."""
    memo = {} if memo is None else memo
    if w in memo:
        return memo[w]
    if not w:
        return True
    ok = False
    for i in range(1, len(w) + 1):
        head = w[:i]
        if (len(head) >= 4 and _known(head, sp)) or head in _SHORT or head in _MATH_WORDS:
            if _segmentable(w[i:], sp, memo):
                ok = True
                break
    memo[w] = ok
    return ok


def _known(wl, sp):
    if sp.known([wl]) or wl in _PREFIXES:
        return True
    for suf in ('es', 's', 'ed', 'ing'):
        if wl.endswith(suf) and sp.known([wl[:-len(suf)]]):
            return True
    return False


def typo_candidates(pass_a, pass_b):
    """Words unknown to the dictionary, read identically in both passes with confidence >= 0.8."""
    sp = _spell()
    words_b = {}
    for ln in pass_b:
        for w in re.findall(r'[A-Za-z]{5,}', ln['text']):
            words_b.setdefault(w.lower(), ln)
    seen, out = set(), []
    for ln in pass_a:
        if ln['conf'] < 0.8:
            continue
        for w in re.findall(r'[A-Za-z]{5,}', ln['text']):
            wl = w.lower()
            if wl in seen or wl not in words_b or words_b[wl]['conf'] < 0.8:
                continue
            seen.add(wl)
            if w.isupper() or _known(wl, sp):
                continue                                  # ALL-CAPS = logo / title art
            if _segmentable(wl, sp):
                continue                                  # merged words = OCR spacing, not a typo
            sugg = sp.correction(wl)
            out.append({'status': 'SUSPECTED_TYPO', 'kind': 'spelling', 'statement': w,
                        'shown': w, 'expected': sugg if sugg and sugg != wl else None,
                        'rect': ln['rect'], 'conf': ln['conf'], 'line': ln['text']})
    return out


# ------------------------------------------------------------------ page + document
READER_VERSION = 1          # OCR cache format (the reading itself); checks run fresh every time


def proposal(f):
    """Plain-language correction proposed to the owner (applied in the editable source, never to the art)."""
    if f['status'] == STATUS_ERR and f['kind'] == 'arithmetic' and f.get('expected'):
        lhs = f['statement'].rsplit('=', 1)[0].strip()
        return f'Change "{f["statement"]}" to "{lhs} = {f["expected"]}".'
    if f['status'] == STATUS_ERR and f['kind'] == 'solved equation':
        v = f['shown'].split('=')[0].strip()
        exp = f.get('expected')
        target = f'{v} = {exp}' if exp else 'the correct solution'
        return (f'Change "{f["shown"]}" to "{target}", then re-check every later step and the final '
                f'solution that use this value.')
    if f['status'] == STATUS_ERR and f['kind'] == 'worked step':
        prev = f['statement'].rsplit(' = ', 1)[0]
        return (f'The step "{f["shown"]}" does not equal the step before it ("{prev}"); the previous step '
                f'simplifies to "{f.get("expected")}". Correct this step and every later step that uses it.')
    if f['status'] == 'SUSPECTED_TYPO':
        hint = f' (dictionary suggestion: "{f["expected"]}" - confirm against the context)' if f.get('expected') else ''
        return f'Correct the spelling of "{f["shown"]}"{hint}.'
    return None


def _stable_id(pno, f):
    key = f'{pno}|{f["kind"]}|{f["statement"]}|{round(f["rect"][0])}|{round(f["rect"][1])}'
    return f'p{pno}-' + hashlib.sha256(key.encode()).hexdigest()[:6]


def _cached_passes(pdf_path, page, pno, cache_dir):
    if not cache_dir:
        return [ocr_page(page, dpi) for dpi in OCR_DPIS]
    h = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()[:20]
    p = Path(cache_dir) / f'{h}_p{pno}_v{READER_VERSION}.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            pass
    passes = [ocr_page(page, dpi) for dpi in OCR_DPIS]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(passes), encoding='utf-8')
    return passes


def review_pdf(pdf_path, pages=None, crop_dir=None, progress=None, cache_dir=None):
    """Review image-only pages. Returns {'pages': {...}, 'items': [...], 'stats': {...}}."""
    fitz = _fitz()
    items, page_stats = [], {}
    with fitz.open(pdf_path) as doc:
        for pno in pages or range(1, doc.page_count + 1):
            page = doc[pno - 1]
            progress and progress(f'Reading page {pno} of {doc.page_count} (OCR, two passes)...')
            passes = _cached_passes(pdf_path, page, pno, cache_dir)
            lines = [l for l in passes[1] if l['conf'] >= MIN_CONF]
            lines.sort(key=lambda l: (round(l['rect'][1] / 6), l['rect'][0]))
            found = []
            for ln in lines:
                for status, lhs, rhs, r, alt in check_line(ln):
                    # consistency: the same claim must be visible in the other pass to be an error
                    if status == STATUS_ERR and not any(rhs in clean(o['text']) and
                                                        _overlap(o['rect'], ln['rect']) for o in passes[0]):
                        status = STATUS_UNREADABLE
                    found.append({'status': status, 'kind': 'arithmetic', 'statement': f'{lhs} = {rhs}',
                                  'shown': rhs, 'expected': r.get('expected'), 'rect': ln['rect'],
                                  'conf': ln['conf'], 'methods': r['methods'], 'evidence': r['evidence'],
                                  'alternative_reading': alt, 'line': ln['text']})
            for f in check_solved_equations(lines):
                if f['status'] == STATUS_ERR:
                    val = f['shown'].split('=')[-1].strip()
                    if not any(_SOL.match(clean(o['text'])) and val in clean(o['text']) and _overlap(o['rect'], f['rect'])
                               for o in passes[0]):
                        f['status'] = STATUS_UNREADABLE
                found.append(f)
            seen = {re.sub(r'\s+', '', f['statement']) for f in found}
            for f in check_worked_steps(lines, passes[0]):
                if re.sub(r'\s+', '', f['statement']) not in seen:
                    found.append(f)
            found += typo_candidates(passes[0], passes[1])
            for f in found:
                f['page'] = pno
                f['id'] = _stable_id(pno, f)
                f['proposal'] = proposal(f)
                if crop_dir and f['status'] in (STATUS_ERR, 'SUSPECTED_TYPO', STATUS_MISREAD):
                    f['crop'] = _crop(page, f['rect'], Path(crop_dir) / f'{f["id"]}.png')
            math_lines = [l for l in lines if re.search(r'\d', l['text']) and re.search(r'[=+×÷*/^]|\d\s*[a-zA-Z]', l['text'])]
            page_stats[pno] = {'lines_read': len(lines), 'math_lines': len(math_lines),
                               'statements': sum(1 for f in found if f['kind'] != 'spelling'),
                               'verified': sum(1 for f in found if f['status'] == STATUS_OK),
                               'errors': sum(1 for f in found if f['status'] == STATUS_ERR),
                               'not_checkable': sum(1 for f in found if f['status'] == STATUS_UNREADABLE),
                               'typos': sum(1 for f in found if f['status'] == 'SUSPECTED_TYPO'),
                               'transcript': [l['text'] for l in lines]}
            items += found
    stats = {s: sum(1 for i in items if i['status'] == s)
             for s in (STATUS_OK, STATUS_ERR, STATUS_MISREAD, STATUS_UNREADABLE, 'SUSPECTED_TYPO')}
    return {'pages': page_stats, 'items': items, 'stats': stats, 'engine': 'RapidOCR (local, offline)',
            'dpis': list(OCR_DPIS)}


def _overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _crop(page, rect, out, pad=14):
    fitz = _fitz()
    r = fitz.Rect(rect[0] - pad * 4, rect[1] - pad, rect[2] + pad * 4, rect[3] + pad) & page.rect
    out.parent.mkdir(parents=True, exist_ok=True)
    page.get_pixmap(dpi=200, clip=r).save(str(out))
    return str(out)


def annotated_review_copy(src_pdf, out_pdf, approved):
    """Copy of the PDF with REVIEW ANNOTATIONS only (rectangles + notes on a separate layer).
    The page pictures are not modified; returns True if pixels without annotations are identical."""
    fitz = _fitz()
    with fitz.open(src_pdf) as doc:
        for f in approved:
            page = doc[f['page'] - 1]
            r = fitz.Rect(f['rect'])
            a = page.add_rect_annot(r + (-3, -3, 3, 3))
            a.set_colors(stroke=(0.85, 0.1, 0.1))
            a.set_border(width=2)
            a.set_info(title='ByrdWay Studio', content=f'{f["id"]}: {f.get("correction") or f["statement"]}')
            a.update()
        doc.save(str(out_pdf))
    with fitz.open(src_pdf) as a, fitz.open(out_pdf) as b:
        return all(a[i].get_pixmap(dpi=50, annots=False).samples == b[i].get_pixmap(dpi=50, annots=False).samples
                   for i in range(a.page_count))
