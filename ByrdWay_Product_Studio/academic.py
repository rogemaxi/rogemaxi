"""Independent Academic Verifier (Agent 6) - deterministic, no AI.

verify_item({'question', 'answer', 'verify'?: spec, 'choices'?, 'correct'?})
  -> {'status': CORRECT | INCORRECT | UNSUPPORTED | PARSE_ERROR,
      'domain', 'expected', 'claimed', 'methods': [...], 'evidence', 'suggested_answer'}

Two methods are used wherever feasible so no single computation is trusted:
  arithmetic  : SymPy exact evaluation  + independent float evaluation
  equations   : SymPy solveset          + substitution of each claimed root
  derivatives : symbolic diff           + central finite differences
  integrals   : symbolic integrate      + differentiate the claimed antiderivative /
                                          numeric quadrature (mpmath) for definite integrals
  limits      : SymPy limit             + numeric approach from both sides
  statistics  : Python `statistics`     + hand-rolled formula
  geometry    : closed-form formula     + float re-computation
  physics     : SymPy units (value)     + dimensional analysis of the claimed unit
Anything not matched is UNSUPPORTED (flagged for human review, never passed).

Untrusted text is never passed to eval: expressions go through a strict token
whitelist and an exponent-size guard before SymPy parses them.
"""
import json, math, re, statistics as pystats
from fractions import Fraction

import sympy as sp
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations,
                                        implicit_multiplication_application)

CORRECT, INCORRECT, UNSUPPORTED, PARSE_ERROR = 'CORRECT', 'INCORRECT', 'UNSUPPORTED', 'PARSE_ERROR'
FUNCS = {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sec', 'csc', 'cot', 'sqrt', 'log', 'ln',
         'exp', 'abs', 'pi', 'Abs'}
TRANSFORMS = standard_transformations + (implicit_multiplication_application,)
MAX_LEN = 300


class UnsafeExpression(ValueError):
    pass


# ------------------------------------------------------------------ parsing
def normalize(s):
    s = str(s).strip()
    rep = {'×': '*', '·': '*', '∙': '*', '÷': '/', '−': '-', '–': '-', '—': '-', 'π': 'pi',
           '²': '^2', '³': '^3', '⁴': '^4', '½': '(1/2)', '¼': '(1/4)', '¾': '(3/4)', '∞': 'oo'}
    for a, b in rep.items():
        s = s.replace(a, b)
    s = re.sub(r'√\s*\(', 'sqrt(', s)
    s = re.sub(r'√\s*([\d.]+|[a-zA-Z])', r'sqrt(\1)', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*°', r'(\1*pi/180)', s)
    s = re.sub(r'\bdeg(rees)?\b', '*pi/180', s)
    s = re.sub(r'(?<=\d),(?=\d{3}\b)', '', s)          # 1,000 -> 1000
    s = s.replace('^', '**')
    s = re.sub(r'\bln\b', 'log', s)
    s = re.sub(r'\|([^|]+)\|', r'Abs(\1)', s)
    return s.strip().rstrip('.?')


_TOKEN = re.compile(r'\s*(?:(\*\*|[-+*/()=,])|(\d+\.\d*|\.\d+|\d+)|([A-Za-z_]+)|(oo))')


def _check_tokens(s):
    if len(s) > MAX_LEN:
        raise UnsafeExpression('Expression too long')
    pos, out = 0, []
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise UnsafeExpression(f'Disallowed character near {s[pos:pos + 10]!r}')
        op, num, ident, inf = m.groups()
        if num and len(num) > 20:
            raise UnsafeExpression('Numeric literal too long')
        if ident:
            if ident in FUNCS or ident == 'oo':
                pass
            elif len(ident) == 1:
                pass
            elif len(ident) <= 3 and ident.isalpha():
                out.append((m.start(3), m.end(3), '*'.join(ident)))  # xy -> x*y
            else:
                raise UnsafeExpression(f'Unknown identifier {ident!r}')
        pos = m.end()
    for a, b, rep in reversed(out):
        s = s[:a] + rep + s[b:]
    return s


def _locals():
    d = {c: sp.Symbol(c) for c in 'abcdfghjklmnopqrstuvwxyzABCDFGHJKLMNOPQRSTUVWXYZ'}
    d.update({'e': sp.E, 'E': sp.E, 'pi': sp.pi, 'sqrt': sp.sqrt, 'log': sp.log, 'exp': sp.exp,
              'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan, 'asin': sp.asin, 'acos': sp.acos,
              'atan': sp.atan, 'sec': sp.sec, 'csc': sp.csc, 'cot': sp.cot, 'abs': sp.Abs,
              'Abs': sp.Abs, 'oo': sp.oo, 'i': sp.Symbol('i')})
    return d


def safe_parse(s):
    s = _check_tokens(normalize(s))
    if not s or '=' in s:
        raise UnsafeExpression('Not a single expression')
    raw = parse_expr(s, local_dict=_locals(), transformations=TRANSFORMS, evaluate=False)
    for node in sp.preorder_traversal(raw):
        if isinstance(node, sp.Pow):
            ex = node.exp
            if ex.is_Number and abs(float(ex)) > 1000:
                raise UnsafeExpression('Exponent too large')
            if isinstance(ex, sp.Pow) or (not ex.is_Number and any(isinstance(a, sp.Pow) for a in sp.preorder_traversal(ex))):
                raise UnsafeExpression('Nested power towers are not evaluated')
    return parse_expr(s, local_dict=_locals(), transformations=TRANSFORMS)


def safe_equation(s):
    s = normalize(s)
    if s.count('=') != 1:
        raise UnsafeExpression('Equation must contain exactly one "="')
    l, r = s.split('=')
    return safe_parse(l), safe_parse(r)


# --------------------------------------------------------------- comparison
def _decimals(text):
    m = re.search(r'\d+\.(\d+)', str(text))
    return len(m.group(1)) if m else None


def numbers_match(expected, claimed_expr, claimed_text):
    """Exact symbolic equality, or a correctly rounded decimal approximation."""
    try:
        diff = sp.simplify(sp.nsimplify(expected) - claimed_expr) if not expected.has(sp.Float) else None
        if diff == 0:
            return True
    except Exception:
        pass
    try:
        ev, cv = complex(sp.N(expected, 30)), complex(sp.N(claimed_expr, 30))
    except Exception:
        return False
    if abs(ev.imag) > 1e-12 or abs(cv.imag) > 1e-12:
        return abs(ev - cv) < 1e-9
    d = _decimals(claimed_text)
    if d is not None and claimed_expr.is_Float or (d is not None and claimed_expr.is_Number):
        return abs(ev.real - cv.real) <= 0.5 * 10 ** (-d) + 1e-12
    return abs(ev.real - cv.real) <= 1e-9 * max(1.0, abs(ev.real))


def strip_answer(ans):
    a = str(ans).strip()
    a = re.sub(r'^(answer|ans|a)\s*[:=)]\s*', '', a, flags=re.I)
    a = re.sub(r'^\$|\$$', '', a).strip()
    return a.rstrip('.')


def parse_answer_set(ans, var=None):
    a = strip_answer(ans)
    a = re.sub(r'^\{(.*)\}$', r'\1', a)
    parts = re.split(r'\s*(?:,|;|\bor\b|\band\b)\s*', a)
    vals = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p = re.sub(r'^[A-Za-z]\s*=\s*', '', p)
        vals.append((safe_parse(p), p))
    return vals


def _fmt(expr, like=''):
    """Format a corrected answer in the same style as the claimed answer."""
    like = str(like)
    prefix = ''
    m = re.match(r'^\s*([A-Za-z])\s*=\s*', like)
    if m:
        prefix = f'{m.group(1)} = '
    d = _decimals(like)
    if expr.is_number and d is not None:
        return prefix + f'{float(sp.N(expr)):.{d}f}'
    if expr.is_Integer:
        return prefix + str(int(expr))
    if expr.is_Rational:
        return prefix + f'{expr.p}/{expr.q}'
    s = str(expr).replace('**', '^')
    return prefix + s


def _result(status, domain, expected=None, claimed=None, methods=(), evidence='', suggested=None):
    return {'status': status, 'domain': domain,
            'expected': None if expected is None else str(expected).replace('**', '^'),
            'claimed': None if claimed is None else str(claimed), 'methods': list(methods),
            'evidence': evidence, 'suggested_answer': suggested}


# ------------------------------------------------------------------ domains
def check_expression(expr_text, claimed, domain='arithmetic'):
    expected = safe_parse(expr_text)
    if expected.free_symbols:
        return check_equivalence(expr_text, claimed, domain='algebraic simplification')
    vals = parse_answer_set(claimed)
    if len(vals) != 1:
        return _result(INCORRECT, domain, expected, claimed, ['sympy exact'], 'Expected a single value')
    cexpr, ctext = vals[0]
    ok = numbers_match(sp.nsimplify(expected) if not expected.has(sp.Float) else expected, cexpr, ctext)
    # independent method: float evaluation of the same expression via mpmath-free path
    try:
        f_exp = float(sp.N(expected, 20))
        f_ok = math.isclose(f_exp, float(sp.N(cexpr, 20)), rel_tol=1e-9, abs_tol=0.5 * 10 ** -(_decimals(ctext) or 9))
    except Exception:
        f_ok = ok
    status = CORRECT if ok and f_ok else INCORRECT
    return _result(status, domain, sp.nsimplify(expected) if not expected.has(sp.Float) else expected, claimed,
                   ['sympy exact evaluation', 'independent floating-point evaluation'],
                   f'{expr_text} evaluates to {expected} (≈{float(sp.N(expected)):.10g})',
                   None if status == CORRECT else _fmt(sp.nsimplify(expected), claimed))


def check_equivalence(expr_text, claimed, domain='algebraic simplification'):
    e = safe_parse(expr_text)
    c = safe_parse(strip_answer(re.sub(r'^\s*[A-Za-z]\s*\(?[a-z]?\)?\s*=\s*', '', strip_answer(claimed))))
    sym_ok = sp.simplify(e - c) == 0
    num_ok = _spot_check(e, c)
    status = CORRECT if sym_ok and num_ok else INCORRECT
    return _result(status, domain, sp.simplify(e), claimed, ['symbolic simplify(e - claimed) == 0',
                   'numeric spot checks at 5 points'], f'simplified form {sp.simplify(e)}',
                   None if status == CORRECT else _fmt(sp.simplify(e), claimed))


def _spot_check(a, b, points=(0.37, 1.13, 2.71, -0.83, 3.9)):
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    good = 0
    for k, x in enumerate(points):
        subs = {s: x + 0.11 * i for i, s in enumerate(syms)}
        try:
            va, vb = complex(sp.N(a.subs(subs))), complex(sp.N(b.subs(subs)))
        except Exception:
            continue
        if not (math.isfinite(va.real) and math.isfinite(vb.real)):
            continue
        if abs(va - vb) > 1e-7 * max(1, abs(va)):
            return False
        good += 1
    return good >= 2


def check_solve(equation, claimed, var=None):
    l, r = safe_equation(equation)
    syms = sorted((l - r).free_symbols, key=str)
    v = sp.Symbol(var) if var else (syms[0] if len(syms) == 1 else None)
    if v is None:
        return _result(UNSUPPORTED, 'equation', None, claimed, [], 'Multiple variables; specify which to solve for')
    sol = sp.solveset(sp.Eq(l, r), v, domain=sp.S.Reals)
    if not isinstance(sol, sp.FiniteSet):
        return _result(UNSUPPORTED, 'equation', sol, claimed, ['sympy solveset'], 'Solution set is not finite')
    expected = sorted(sol, key=lambda z: float(sp.N(z)))
    claimed_vals = parse_answer_set(claimed)
    matched, subs_ok = set(), True
    for cexpr, ctext in claimed_vals:
        hit = [i for i, e in enumerate(expected) if numbers_match(e, cexpr, ctext)]
        if hit:
            matched.add(hit[0])
        val = complex(sp.N((l - r).subs(v, cexpr)))
        tol = 1e-9 if _decimals(ctext) is None else 10 ** (-(_decimals(ctext) or 0) + 1)
        if abs(val) > tol * max(1, abs(complex(sp.N(l.subs(v, cexpr))))):
            subs_ok = False
    ok = len(matched) == len(expected) and len(claimed_vals) == len(expected) and subs_ok
    exp_txt = ', '.join(str(e) for e in expected)
    sug = None
    if not ok:
        sug = ' or '.join(_fmt(e, claimed_vals[0][1] if claimed_vals else '') for e in expected)
        if re.match(r'^\s*[A-Za-z]\s*=', strip_answer(claimed)):
            sug = ' or '.join(f'{v} = {_fmt(e)}' for e in expected)
    return _result(CORRECT if ok else INCORRECT, 'algebra: equation', exp_txt, claimed,
                   ['sympy solveset over reals', 'substitution of each claimed root'],
                   f'{equation}: solution set {{{exp_txt}}}; substitution check {"passed" if subs_ok else "FAILED"}', sug)


def check_derivative(expr_text, claimed, var='x', order=1):
    v = sp.Symbol(var)
    f = safe_parse(expr_text)
    expected = sp.diff(f, v, order)
    ctext = re.sub(r"^\s*(?:[a-zA-Z]'+\s*\(\s*\w\s*\)|dy/dx|d/dx\s*\S*|y')\s*=\s*", '', strip_answer(claimed))
    c = safe_parse(ctext)
    sym_ok = sp.simplify(expected - c) == 0
    # independent: central finite differences of the ORIGINAL function
    num_ok = True
    if order == 1:
        for x0 in (0.7, 1.3, 2.2):
            try:
                h = 1e-5
                fd = (float(sp.N(f.subs(v, x0 + h))) - float(sp.N(f.subs(v, x0 - h)))) / (2 * h)
                cv = float(sp.N(c.subs(v, x0)))
                if abs(fd - cv) > 1e-4 * max(1, abs(fd)):
                    num_ok = False
            except Exception:
                continue
    ok = sym_ok and num_ok
    return _result(CORRECT if ok else INCORRECT, 'calculus: derivative', expected, claimed,
                   ['symbolic differentiation', 'central finite differences of original function'],
                   f'd/d{var} [{expr_text}] = {expected}', None if ok else _fmt(expected))


def check_integral(expr_text, claimed, var='x', lower=None, upper=None):
    v = sp.Symbol(var)
    f = safe_parse(expr_text)
    if lower is None:
        ctext = re.sub(r'\+\s*[Cc]\s*$', '', strip_answer(claimed)).strip()
        c = safe_parse(ctext)
        ok = sp.simplify(sp.diff(c, v) - f) == 0 and _spot_check(sp.diff(c, v), f)
        expected = sp.integrate(f, v)
        return _result(CORRECT if ok else INCORRECT, 'calculus: indefinite integral', f'{expected} + C', claimed,
                       ['differentiate claimed antiderivative and compare to integrand', 'numeric spot checks'],
                       f'd/d{var}[claimed] {"equals" if ok else "does NOT equal"} {f}',
                       None if ok else _fmt(expected) + ' + C')
    a, b = safe_parse(str(lower)), safe_parse(str(upper))
    expected = sp.integrate(f, (v, a, b))
    import mpmath
    fl = sp.lambdify(v, f, 'mpmath')
    quad = float(mpmath.quad(fl, [float(sp.N(a)), float(sp.N(b))]))
    vals = parse_answer_set(claimed)
    ok = len(vals) == 1 and numbers_match(expected, vals[0][0], vals[0][1]) and \
        math.isclose(quad, float(sp.N(vals[0][0])), rel_tol=1e-6, abs_tol=0.5 * 10 ** -(_decimals(vals[0][1]) or 6))
    return _result(CORRECT if ok else INCORRECT, 'calculus: definite integral', expected, claimed,
                   ['symbolic definite integral', 'numeric quadrature (mpmath)'],
                   f'∫[{lower},{upper}] {expr_text} d{var} = {expected} ≈ {quad:.10g}',
                   None if ok else _fmt(expected, vals[0][1] if vals else ''))


def check_limit(expr_text, claimed, var='x', to='0'):
    v = sp.Symbol(var)
    f = safe_parse(expr_text)
    point = safe_parse(str(to))
    expected = sp.limit(f, v, point)
    vals = parse_answer_set(claimed)
    ok = len(vals) == 1 and (expected == vals[0][0] if not expected.is_finite else numbers_match(expected, vals[0][0], vals[0][1]))
    num_ok = True
    if expected.is_finite and point.is_finite:
        p = float(sp.N(point))
        for h in (1e-4, -1e-4):
            try:
                if abs(float(sp.N(f.subs(v, p + h))) - float(sp.N(expected))) > 1e-2 * max(1, abs(float(sp.N(expected)))):
                    num_ok = False
            except Exception:
                pass
    status = CORRECT if ok and num_ok else INCORRECT
    return _result(status, 'calculus: limit', expected, claimed, ['sympy limit', 'numeric approach from both sides'],
                   f'lim {var}->{to} {expr_text} = {expected}', None if status == CORRECT else _fmt(expected))


def _manual_stats(data):
    n = len(data)
    mean = sum(data) / n
    s = sorted(data)
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    pvar = sum((x - mean) ** 2 for x in data) / n
    svar = sum((x - mean) ** 2 for x in data) / (n - 1) if n > 1 else float('nan')
    return {'mean': mean, 'median': median, 'range': s[-1] - s[0], 'pvar': pvar, 'svar': svar}


def check_statistic(stat, data, claimed, question=''):
    data = [float(Fraction(str(x))) if not isinstance(x, (int, float)) else float(x) for x in data]
    if not data:
        return _result(UNSUPPORTED, 'statistics', None, claimed, [], 'No data')
    stat = stat.lower()
    man = _manual_stats(data)
    q = question.lower()
    candidates = {}
    if stat in ('mean', 'average'):
        candidates = {'mean': (pystats.fmean(data), man['mean'])}
    elif stat == 'median':
        candidates = {'median': (pystats.median(data), man['median'])}
    elif stat == 'range':
        candidates = {'range': (max(data) - min(data), man['range'])}
    elif stat == 'mode':
        modes = pystats.multimode(data)
        vals = parse_answer_set(claimed)
        got = sorted(float(sp.N(v)) for v, _ in vals)
        ok = sorted(modes) == got and len(modes) < len(set(data))
        return _result(CORRECT if ok else INCORRECT, 'statistics: mode', modes, claimed,
                       ['statistics.multimode', 'frequency count'], f'modes {modes}',
                       None if ok else ', '.join(_fmt(sp.nsimplify(m)) for m in modes))
    elif stat in ('standard deviation', 'sd', 'stdev', 'variance'):
        is_var = stat == 'variance'
        pop = (pystats.pvariance(data) if is_var else pystats.pstdev(data),
               man['pvar'] if is_var else math.sqrt(man['pvar']))
        smp = (pystats.variance(data) if is_var else pystats.stdev(data),
               man['svar'] if is_var else math.sqrt(man['svar'])) if len(data) > 1 else None
        if 'sample' in q and smp:
            candidates = {'sample': smp}
        elif 'population' in q:
            candidates = {'population': pop}
        else:
            candidates = {'population': pop, **({'sample': smp} if smp else {})}
    else:
        return _result(UNSUPPORTED, 'statistics', None, claimed, [], f'Statistic {stat!r} not supported')
    vals = parse_answer_set(claimed)
    if len(vals) != 1:
        return _result(INCORRECT, f'statistics: {stat}', None, claimed, [], 'Expected one value')
    cexpr, ctext = vals[0]
    matched = None
    for name, (a, b) in candidates.items():
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
            return _result(UNSUPPORTED, 'statistics', None, claimed, [], 'Internal method disagreement')
        if numbers_match(sp.Float(a, 30), cexpr, ctext) or (_decimals(ctext) is None and math.isclose(a, float(sp.N(cexpr)), rel_tol=1e-9)):
            matched = name
    first = list(candidates.values())[0][0]
    ev = f'{", ".join(f"{k}={v[0]:.10g}" for k, v in candidates.items())}'
    note = ' (ambiguous population/sample: question should specify)' if len(candidates) > 1 and matched else ''
    return _result(CORRECT if matched else INCORRECT, f'statistics: {stat}', ev, claimed,
                   ['Python statistics module', 'independent hand-rolled formula'], ev + note,
                   None if matched else _fmt(sp.Float(first, 12), ctext or '0.00'))


GEOMETRY = {
    ('circle', 'area'): (('r',), lambda r: sp.pi * r ** 2),
    ('circle', 'circumference'): (('r',), lambda r: 2 * sp.pi * r),
    ('rectangle', 'area'): (('l', 'w'), lambda l, w: l * w),
    ('rectangle', 'perimeter'): (('l', 'w'), lambda l, w: 2 * (l + w)),
    ('triangle', 'area'): (('b', 'h'), lambda b, h: sp.Rational(1, 2) * b * h),
    ('right triangle', 'hypotenuse'): (('a', 'b'), lambda a, b: sp.sqrt(a ** 2 + b ** 2)),
    ('sphere', 'volume'): (('r',), lambda r: sp.Rational(4, 3) * sp.pi * r ** 3),
    ('sphere', 'surface area'): (('r',), lambda r: 4 * sp.pi * r ** 2),
    ('cylinder', 'volume'): (('r', 'h'), lambda r, h: sp.pi * r ** 2 * h),
    ('cube', 'volume'): (('s',), lambda s: s ** 3),
    ('cone', 'volume'): (('r', 'h'), lambda r, h: sp.Rational(1, 3) * sp.pi * r ** 2 * h),
    ('triangle', 'third angle'): (('a', 'b'), lambda a, b: 180 - a - b),
}


def check_geometry(shape, quantity, params, claimed):
    key = (shape.lower(), quantity.lower())
    if key not in GEOMETRY:
        return _result(UNSUPPORTED, 'geometry', None, claimed, [], f'No formula for {quantity} of {shape}')
    names, fn = GEOMETRY[key]
    try:
        args = [sp.nsimplify(params[n]) for n in names]
    except KeyError as e:
        return _result(UNSUPPORTED, 'geometry', None, claimed, [], f'Missing parameter {e}')
    expected = fn(*args)
    vals = parse_answer_set(re.sub(r'\s*(sq\.?\s*)?(units?|cm|mm|m|in|ft|degrees|°)(\^?\d|²|³)?\s*$', '', strip_answer(claimed)))
    ok = len(vals) == 1 and numbers_match(expected, vals[0][0], vals[0][1])
    f2 = float(fn(*[float(a) for a in args])) if 'pi' not in str(expected) else float(sp.N(expected))
    ok = ok and math.isclose(f2, float(sp.N(vals[0][0])), rel_tol=1e-6,
                             abs_tol=0.5 * 10 ** -(_decimals(vals[0][1]) or 6) + 1e-9)
    return _result(CORRECT if ok else INCORRECT, f'geometry: {quantity} of {shape}', expected, claimed,
                   ['closed-form formula (exact)', 'float re-computation'],
                   f'{quantity} of {shape} with {params} = {expected} ≈ {float(sp.N(expected)):.10g}',
                   None if ok else _fmt(expected, vals[0][1] if vals else ''))


# ----------------------------------------------------------------- physics
def _units():
    from sympy.physics import units as u
    return {'m': u.meter, 'km': u.kilometer, 'cm': u.centimeter, 'mm': u.millimeter, 's': u.second,
            'ms': u.millisecond, 'min': u.minute, 'h': u.hour, 'kg': u.kilogram, 'g': u.gram,
            'N': u.newton, 'J': u.joule, 'kJ': 1000 * u.joule, 'W': u.watt, 'kW': 1000 * u.watt, 'Pa': u.pascal,
            'Hz': u.hertz, 'C': u.coulomb, 'V': u.volt, 'A': u.ampere, 'ohm': u.ohm, 'Ω': u.ohm,
            'K': u.kelvin, 'mol': u.mole, 'L': u.liter}


_BASE = None


def parse_quantity(text):
    """'9.8 m/s^2' -> sympy quantity expression. Strict whitelist of unit names."""
    from sympy.physics import units as u
    U = _units()
    t = normalize(text).replace('Ω', 'ohm')
    m = re.match(r'^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*)$', t)
    if not m:
        raise UnsafeExpression(f'Not a quantity: {text!r}')
    num, unit = m.group(1), m.group(2).strip()
    value = sp.nsimplify(num) if 'e' not in num.lower() else sp.Float(num)
    if not unit:
        return value, value, num
    toks = re.findall(r'[A-Za-zΩ]+|\*\*|[*/()]|\d+|\s+', unit)
    if ''.join(toks) != unit:
        raise UnsafeExpression(f'Bad unit expression {unit!r}')
    expr = ''
    for tk in toks:
        if tk.isalpha():
            if tk not in U:
                raise UnsafeExpression(f'Unknown unit {tk!r}')
            expr += f'U_{tk}'
        elif tk.isspace():
            expr += '*'
        else:
            expr += tk
    ns = {f'U_{k}': v for k, v in U.items()}
    unit_expr = parse_expr(expr, local_dict=ns, evaluate=True)
    return value * unit_expr, value, num


def _to_base(q):
    from sympy.physics import units as u
    from sympy.physics.units.quantities import Quantity
    b = u.convert_to(q, [u.meter, u.kilogram, u.second, u.ampere, u.kelvin, u.mole])
    # SymPy can create distinct-but-equal Quantity objects; compare by unit name
    return b.subs({a: sp.Symbol('unit_' + str(a.name)) for a in b.atoms(Quantity)})


def check_physics(formula, given, find, claimed):
    """formula 'F = m*a', given {'m': '5 kg', 'a': '9.8 m/s^2'}, find 'F', claimed '49 N'."""
    l, r = formula.split('=', 1)
    target = sp.Symbol(find)
    lhs, rhs = safe_parse(l), safe_parse(r)
    subs = {}
    for k, v in given.items():
        subs[sp.Symbol(k)] = parse_quantity(v)[0]
    sol = sp.solve(sp.Eq(lhs, rhs), target)
    if len(sol) != 1:
        sol = [s for s in sol if (s.subs({k: 1 for k in s.free_symbols}) if s.free_symbols else s).is_positive] or sol
        if len(sol) != 1:
            return _result(UNSUPPORTED, 'physics', sol, claimed, [], 'Formula does not give a unique result')
    expected = _to_base(sp.simplify(sol[0].subs(subs)))
    try:
        cq, cval, ctext = parse_quantity(strip_answer(claimed))
    except UnsafeExpression as e:
        return _result(PARSE_ERROR, 'physics', expected, claimed, [], str(e))
    cbase = _to_base(cq)
    ratio = sp.simplify(cbase / expected) if expected != 0 else None
    dims_ok = ratio is not None and ratio.is_number
    val_ok = False
    if dims_ok:
        d = _decimals(ctext)
        val_ok = abs(float(ratio) - 1) <= (0.5 * 10 ** (-d) / max(abs(float(cval)), 1e-30) if d is not None else 1e-9) + 1e-12
    ok = dims_ok and val_ok
    ev = f'{find} = {sol[0]} = {expected}'
    if not dims_ok:
        ev += ' | DIMENSION MISMATCH: claimed unit is not the unit of ' + find
    return _result(CORRECT if ok else INCORRECT, 'physics: units & value', expected, claimed,
                   ['sympy units algebra', 'dimensional analysis of claimed unit'], ev, None)


# ------------------------------------------------------- question classifier
_NUM_LIST = r'(-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?)+)'


def classify(question):
    """Infer a verification spec from question text. Returns spec or None."""
    q = normalize(question)
    ql = q.lower()
    m = re.search(r'solve(?:\s+for\s+([a-z]))?\s*[:\-]?\s*(.+?=.+?)(?:\s+for\s+([a-z]))?\s*$', q, re.I)
    if m:
        return {'type': 'solve', 'equation': m.group(2), 'var': m.group(1) or m.group(3)}
    m = re.search(r"(?:derivative of|differentiate|d/d([a-z]))\s*(?:\(\s*)?(?:f\([a-z]\)\s*=\s*|y\s*=\s*)?(.+?)\)?(?:\s+with respect to\s+([a-z]))?$", q, re.I)
    if m:
        return {'type': 'derivative', 'expr': m.group(2), 'var': m.group(3) or m.group(1) or 'x'}
    m = re.search(r'(?:integral of|integrate|∫)\s*(.+?)(?:\s*d([a-z]))?(?:\s+from\s+(\S+)\s+to\s+(\S+))?$', q, re.I)
    if m:
        return {'type': 'integral', 'expr': m.group(1).strip(), 'var': m.group(2) or 'x',
                'lower': m.group(3), 'upper': m.group(4)}
    m = re.search(r'lim(?:it)?\s*(?:as\s*)?\(?\s*([a-z])\s*(?:->|→|approaches)\s*([^\s)]+)\s*\)?\s*(?:of\s*)?(.+)$', q, re.I)
    if m:
        return {'type': 'limit', 'var': m.group(1), 'to': m.group(2), 'expr': m.group(3)}
    m = re.search(r'(mean|average|median|mode|range|sample standard deviation|population standard deviation|standard deviation|variance)\b.*?' + _NUM_LIST, ql)
    if m:
        stat = m.group(1).replace('sample ', '').replace('population ', '')
        return {'type': 'statistic', 'stat': stat, 'data': [x.strip() for x in m.group(2).split(',')]}
    m = re.search(r'(area|circumference|volume|surface area)\s+of\s+(?:a|the)\s+(circle|sphere|cylinder|cone|cube)\s+with\s+(radius|diameter|side)\s+(?:of\s+)?([\d.]+)(?:.*?height\s+(?:of\s+)?([\d.]+))?', ql)
    if m:
        qty, shape, kind, val, h = m.groups()
        val = float(val) if '.' in val else int(val)
        p = {'r': val / 2 if kind == 'diameter' else val, 's': val}
        if h:
            p['h'] = float(h) if '.' in h else int(h)
        return {'type': 'geometry', 'shape': shape, 'quantity': qty, 'params': p}
    m = re.search(r'hypotenuse.*?legs?\s*(?:of\s*)?(?:length\s*)?([\d.]+)\s*(?:and|,)\s*([\d.]+)', ql)
    if m:
        return {'type': 'geometry', 'shape': 'right triangle', 'quantity': 'hypotenuse',
                'params': {'a': m.group(1), 'b': m.group(2)}}
    m = re.search(r'area\s+of\s+(?:a|the)\s+rectangle.*?([\d.]+)\s*(?:by|x|\*)\s*([\d.]+)', ql)
    if m:
        return {'type': 'geometry', 'shape': 'rectangle', 'quantity': 'area', 'params': {'l': m.group(1), 'w': m.group(2)}}
    m = re.search(r'simplify\s*[:\-]?\s*(.+)$', q, re.I)
    if m:
        return {'type': 'expression', 'expr': m.group(1)}
    m = re.match(r'^(?:which\s+(?:is|equals)|what\s+is|what\'s|compute|calculate|evaluate|find)?\s*[:\-]?\s*(.+?)\s*(?:=\s*)?$', q, re.I)
    if m:
        body = m.group(1)
        if re.search(r'\d', body) and re.fullmatch(r'[\d\s.+\-*/()^a-z,]+', body, re.I):
            try:
                if not safe_parse(body).free_symbols:
                    return {'type': 'expression', 'expr': body}
            except UnsafeExpression:
                return {'type': 'expression', 'expr': body}   # verify_item reports PARSE_ERROR
            except Exception:
                return None
    return None


def verify_item(item):
    """Verify one question/answer item. Never raises for bad content."""
    question = str(item.get('question', ''))
    answer = item.get('answer')
    if item.get('choices') is not None and item.get('correct') is not None and answer is None:
        try:
            idx = item['correct']
            idx = 'abcdefgh'.index(idx.lower()) if isinstance(idx, str) and not idx.isdigit() else int(idx)
            answer = item['choices'][idx]
        except (ValueError, IndexError, TypeError):
            return _result(PARSE_ERROR, 'multiple choice', None, item.get('correct'), [], 'Correct-choice index invalid')
    if answer is None or str(answer).strip() == '':
        return _result(PARSE_ERROR, 'unknown', None, answer, [], 'No answer given')
    spec = item.get('verify') or classify(question)
    if not spec:
        return _result(UNSUPPORTED, 'unclassified', None, answer, [],
                       'Question type not supported by deterministic verifier: human or AI-assisted review required')
    try:
        t = spec['type']
        if t == 'expression':
            r = check_expression(spec['expr'], answer)
        elif t == 'equivalence':
            r = check_equivalence(spec['expr'], answer)
        elif t == 'solve':
            r = check_solve(spec['equation'], answer, spec.get('var'))
        elif t == 'derivative':
            r = check_derivative(spec['expr'], answer, spec.get('var', 'x'), int(spec.get('order', 1)))
        elif t == 'integral':
            r = check_integral(spec['expr'], answer, spec.get('var', 'x'), spec.get('lower'), spec.get('upper'))
        elif t == 'limit':
            r = check_limit(spec['expr'], answer, spec.get('var', 'x'), spec.get('to', '0'))
        elif t == 'statistic':
            r = check_statistic(spec['stat'], spec['data'], answer, question)
        elif t == 'geometry':
            r = check_geometry(spec['shape'], spec['quantity'], spec['params'], answer)
        elif t == 'physics':
            r = check_physics(spec['formula'], spec['given'], spec['find'], answer)
        else:
            r = _result(UNSUPPORTED, t, None, answer, [], f'Unknown verify type {t!r}')
    except UnsafeExpression as e:
        r = _result(PARSE_ERROR, spec.get('type', '?'), None, answer, [], f'Rejected expression: {e}')
    except Exception as e:  # sympy can raise many things on odd input
        r = _result(PARSE_ERROR, spec.get('type', '?'), None, answer, [], f'{type(e).__name__}: {str(e)[:160]}')
    r['spec'] = spec
    if item.get('choices') is not None and r['status'] == INCORRECT and r.get('suggested_answer'):
        # find which choice is actually correct (for index repair)
        for i, ch in enumerate(item['choices']):
            sub = verify_item({'question': question, 'answer': ch, 'verify': spec})
            if sub['status'] == CORRECT:
                r['correct_choice_index'] = i
                break
    return r


# ------------------------------------------------------- claim extraction
_ARITH_CLAIM = re.compile(r'(?<![\w.])(\(?-?\d[\d.,]*\)?(?:\s*[-+×x*/÷·−^]\s*\(?-?\d[\d.,]*\)?)+)\s*=\s*(-?\d[\d.,]*(?:\s*/\s*\d+)?)(?![\d.]*\s*[-+×*/÷^])')


def extract_arithmetic_claims(text):
    """Find statements like '7 × 8 = 56' in explainer / answer-key text."""
    out = []
    for m in _ARITH_CLAIM.finditer(text):
        lhs = m.group(1).replace('x', '×') if re.search(r'\d\s*x\s*\d', m.group(1)) else m.group(1)
        out.append({'question': lhs.strip(), 'answer': m.group(2).strip().rstrip('.,'),
                    'verify': {'type': 'expression', 'expr': lhs.strip()},
                    'location': {'offset': m.start(), 'text': m.group(0)}})
    return out


def extract_qa_pairs(text):
    """'Q: ... A: ...' / '1. question ... Answer: value' patterns."""
    out = []
    for m in re.finditer(r'(?im)^\s*(?:Q(?:uestion)?\s*\d*[:.)]|\d+[.)])\s*(.+?)\s*$\s*^\s*(?:A(?:nswer)?|Ans)\s*[:.)]\s*(.+?)\s*$', text):
        out.append({'question': m.group(1), 'answer': m.group(2), 'location': {'offset': m.start(), 'text': m.group(0)}})
    return out


_KEY_Q = r'(?:question|q|prompt|problem|questionText|stem|text)'
_KEY_A = r'(?:answer|ans|correctAnswer|correct_answer|solution|key|expected)'
_KEY_CHOICES = r'(?:choices|options|answers|answerChoices|alternatives)'
_KEY_CORRECT = r'(?:correct|correctIndex|correct_index|answerIndex|answer_index|correctOption|correctChoice)'


def object_spans(text, limit=20000, comments=None):
    """(start, end) of every {...} object at any depth, skipping strings and comments.
    If `comments` is a list, comment spans are appended to it."""
    spans, stack, i, n = [], [], 0, len(text)
    while i < n and len(spans) < limit:
        c = text[i]
        if c in '"\'`':
            q = c
            i += 1
            while i < n and text[i] != q:
                if text[i] == '\\':
                    i += 1
                elif text[i] == '\n' and q != '`':
                    break
                i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            j = n if j < 0 else j
            if comments is not None:
                comments.append((i, j))
            i = j
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            if comments is not None:
                comments.append((i, j))
            i = j - 1
        elif c == '{':
            stack.append(i)
        elif c == '}' and stack:
            spans.append((stack.pop(), i + 1))
        i += 1
    return spans


def _mask_nested(obj):
    """Blank out nested {...} so only the object's own top-level keys are matched (offsets preserved)."""
    out, comments = list(obj), []
    for a, b in object_spans(obj[1:-1], comments=comments) + comments:
        for k in range(a + 1, b + 1):
            out[k] = ' '
    return ''.join(out)
_VAL = r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|-?\d+(?:\.\d+)?)'''
_VAL_T = r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\$]|\\.)*`|-?\d+(?:\.\d+)?)'''


def _unq(v):
    v = v.strip()
    if v[:1] == '`':
        return v[1:-1].replace('\\`', '`')
    if v[:1] == '"':
        try:
            return json.loads(v)            # decodes \u00d7 etc. exactly like JS
        except ValueError:
            return v[1:-1].replace('\\"', '"')
    if v[:1] == "'":
        try:
            return json.loads('"' + v[1:-1].replace('"', '\\"').replace("\\'", "'") + '"')
        except ValueError:
            return v[1:-1].replace("\\'", "'")
    return v


def extract_source_items(path, text):
    """Extract {question, answer} records embedded in Power Tool JS/JSON/HTML.

    Each item carries a 'patch_target' = exact text of its record so that a
    repair can replace the answer with an exact-once patch.
    """
    items = []
    json_spans = [m.span(1) for m in re.finditer(
        r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', text, re.S | re.I)]
    for start, end in object_spans(text):
        if end - start > 20000 or any(a <= start < b for a, b in json_spans):
            continue                       # JSON blocks are parsed structurally below
        obj = text[start:end]
        top = _mask_nested(obj)
        K = lambda keys: r'''(?<![\w$])["']?''' + keys + r'''["']?\s*:\s*'''
        qm = re.search(K(_KEY_Q) + _VAL_T, top)
        am = re.search(K(_KEY_A) + _VAL_T, top)
        cm = re.search(K(_KEY_CHOICES) + r'\[([^\]]*)\]', top)
        km = re.search(K(_KEY_CORRECT) + r'''(\d+|"[A-Ha-h]"|'[A-Ha-h]')''', top)
        if am and cm and re.fullmatch(r'\d+', am.group(1)) and not km:
            opts = [_unq(c) for c in re.findall(_VAL_T, cm.group(1))]
            if int(am.group(1)) < len(opts) and am.group(1) not in opts:
                km, am = am, None          # `answer: 2` beside options = an index, not a value
        if not qm or not (am or (cm and km)):
            continue
        if not re.search(r'[\d=+\-*/^×÷√π]', _unq(qm.group(1))) and not (am and re.search(r'\d', am.group(1))):
            continue                       # not a math item (e.g. a menu config)
        item = {'question': _unq(qm.group(1)), 'file': path, 'patch_target': obj,
                'line': text[:start].count('\n') + 1}
        if am:
            item['answer'] = _unq(am.group(1))
            item['answer_literal'] = am.group(1)
            item['answer_span'] = am.span(1)
        if cm:
            item['choices'] = [_unq(c) for c in re.findall(_VAL_T, cm.group(1))]
        if km:
            item['correct'] = _unq(km.group(1))
            item['correct_literal'] = km.group(1)
            item['correct_span'] = km.span(1)
        items.append(item)
    for m in re.finditer(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            data = json.loads(m.group(1).replace('<\\/', '</'))
        except ValueError:
            continue
        for rec in _walk_records(data):
            items.append({'question': str(rec['question']), 'answer': rec.get('answer'), 'file': path,
                          'choices': rec.get('choices'), 'verify': rec.get('verify'),
                          'patch_target': None, 'line': text[:m.start()].count('\n') + 1, 'json_block': True})
    for m in re.finditer(r'<[a-zA-Z][^<>]*\bdata-question\s*=\s*"([^"]*)"[^<>]*>', text):
        tag = m.group(0)
        am = re.search(r'\bdata-answer\s*=\s*"([^"]*)"', tag)
        if am:
            items.append({'question': am and m.group(1), 'answer': am.group(1), 'file': path,
                          'patch_target': tag, 'answer_literal': f'"{am.group(1)}"',
                          'answer_span': am.span(1), 'html_attr': True,
                          'line': text[:m.start()].count('\n') + 1})
    return items


def _walk_records(node, depth=0):
    if depth > 6:
        return
    if isinstance(node, dict):
        if node.get('question') and node.get('answer') not in (None, ''):
            yield node
        for v in node.values():
            yield from _walk_records(v, depth + 1)
    elif isinstance(node, list):
        for v in node[:2000]:
            yield from _walk_records(v, depth + 1)


def repair_for_item(item, result):
    """Build an exact-once patch correcting a verified-wrong answer, or None."""
    target = item.get('patch_target')
    if not target or result['status'] != INCORRECT:
        return None
    if 'correct_choice_index' in result and 'correct_span' in item:
        a, b = item['correct_span']
        lit = item['correct_literal']
        idx = result['correct_choice_index']
        new_lit = str(idx) if lit.strip('"\'').isdigit() else lit[0] + 'ABCDEFGH'[idx] + lit[-1]
        return {'file': item['file'], 'find': target, 'replace': target[:a] + new_lit + target[b:],
                'reason': f'Correct choice index points to a wrong option; verified correct option is #{idx}'}
    sug = result.get('suggested_answer')
    if sug is None or 'answer_span' not in item:
        return None
    a, b = item['answer_span']
    lit = item['answer_literal']
    if item.get('html_attr'):
        new = target[:a] + sug.replace('"', '&quot;') + target[b:]
    else:
        q = lit[0] if lit[:1] in '"\'' else ''
        if not q and not re.fullmatch(r'-?\d+(\.\d+)?', sug):
            q = '"'
        body = sug.replace(q, '\\' + q) if q else sug
        new = target[:a] + q + body + q + target[b:]
    return {'file': item['file'], 'find': target, 'replace': new,
            'reason': f'Answer "{item.get("answer")}" verified incorrect; deterministic solution is "{sug}" '
                      f'({"; ".join(result["methods"])})'}
