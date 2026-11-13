"""Additional deterministic Algebra 1 checks for the Academic Verifier (exact SymPy, no AI).

Recognised question forms (anything else stays UNSUPPORTED -> human review):
  inequalities (linear, compound, absolute value) - factoring (incl. 'prime over the integers') - FOIL products -
  2x2 linear systems - slope through two points - line through a point with a slope / parallel to a line -
  function evaluation - average rate of change - vertex / axis of symmetry - scientific notation -
  simplify with positive exponents - mean / median / mode / range of a number list.
Every check compares the CLAIMED answer with an independently computed result; partial or ambiguous answers
are reported as UNSUPPORTED, never guessed.
"""
import re

import sympy as sp

X, Y = sp.symbols('x y', real=True)


def _n(s):
    s = str(s)
    for a, b in (('−', '-'), ('–', '-'), ('·', '*'), ('×', '*'), ('÷', '/'), ('²', '^2'), ('³', '^3'), ('≤', '<='),
                 ('≥', '>='), ('√', 'sqrt'), ('∞', 'oo')):
        s = s.replace(a, b)
    return s.strip().rstrip('.').strip()


def _expr(s):
    import academic
    s = _n(s)
    s = re.sub(r'(\d)\s*\(', r'\1*(', s)
    return academic.safe_parse(s).subs({sp.Symbol('x'): X, sp.Symbol('y'): Y})


def _num(s):
    return sp.nsimplify(_expr(s))


# ------------------------------------------------------------------ classification
PATTERNS = [
    ('inequality', r'solve the (?:compound |absolute value )?inequality\s*:\s*(.+)$'),
    ('prime_or_factor', r'factor completely over the integers, or state that it is prime\s*:\s*(.+)$'),
    ('factor', r'^factor(?: completely| by grouping| out the gcf)?\s*:\s*(.+)$'),
    ('foil', r'^multiply(?: using foil)?\s*:\s*(.+)$'),
    ('system', r'^solve (?:the system )?(?:by|using)[^:]*:\s*(.+?)\s+and\s+(.+)$'),
    ('slope2', r'slope of the line through \(([^)]+)\) and \(([^)]+)\)'),
    ('line_point_slope', r'line through \(([^)]+)\) with slope ([-−\d/.]+)'),
    ('line_parallel', r'line parallel to (y\s*=\s*[^ ]+(?:\s*[+-]\s*[^ ]+)?) that passes through \(([^)]+)\)'),
    ('evaluate', r'^evaluate f\(x\)\s*=\s*(.+?) at x\s*=\s*([-−\d./]+)$'),
    ('evaluate', r'^if f\(x\)\s*=\s*(.+?),\s*find f\(([-−\d./]+)\)$'),
    ('avg_rate', r'average rate of change of f\(x\)\s*=\s*(.+?) from x\s*=\s*([-−\d./]+) to x\s*=\s*([-−\d./]+)$'),
    ('vertex', r'(?:find|identify) the vertex of (?:f\(x\)|y)\s*=\s*(.+?)(?:\s+using\b.*)?$'),
    ('axis', r'axis of symmetry for y\s*=\s*(.+)$'),
    ('sci', r'^write ([\d.,]+) in scientific notation$'),
    ('simplify_pos', r'^simplify[^:]*positive exponents\s*:\s*(.+)$'),
]


def classify(question):
    q = _n(question)
    for kind, pat in PATTERNS:
        m = re.search(pat, q, re.I)
        if m:
            return {'type': 'algebra1', 'form': kind, 'parts': [g.strip() for g in m.groups()]}
    m = re.search(r'((?:-?\d+(?:\.\d+)?\s*,\s*){2,}-?\d+(?:\.\d+)?)', q)
    stats = re.findall(r'\b(mean|median|mode|range)\b', q.lower())
    if m and stats and not re.search(r'interquartile|iqr|quartile|deviation|interpret', q.lower()):
        return {'type': 'algebra1', 'form': 'stats', 'parts': [m.group(1)] + stats}
    return None


# ------------------------------------------------------------------ checkers
def _rel_set(text):
    """'x ≥ −5' / '−2 < x ≤ 5' / 'x > 5 or x < −1' -> SymPy set over the reals."""
    t = _n(text).replace('x', 'X')
    parts = re.split(r'\s+or\s+', t)
    out = sp.EmptySet
    for p in parts:
        p = p.strip()
        m = re.fullmatch(r'(.+?)\s*(<=|<)\s*X\s*(<=|<)\s*(.+)', p)
        if m:
            a, op1, op2, b = m.groups()
            out = out | sp.Interval(_num(a), _num(b), left_open=op1 == '<', right_open=op2 == '<')
            continue
        m = re.fullmatch(r'X\s*(<=|>=|<|>)\s*(.+)', p)
        if not m:
            raise ValueError(f'unreadable inequality answer {p!r}')
        op, v = m.groups()
        v = _num(v)
        out = out | {'<': sp.Interval.open(-sp.oo, v), '<=': sp.Interval(-sp.oo, v), '>': sp.Interval.open(v, sp.oo),
                     '>=': sp.Interval(v, sp.oo)}[op]
    return out


def _solve_ineq(text):
    t = _n(text)
    m = re.fullmatch(r'(.+?)\s*(<=|<)\s*(.+?)\s*(<=|<)\s*(.+)', t)
    if m:
        a, o1, mid, o2, b = m.groups()
        e = _expr(mid)
        r1 = sp.solveset((_num(a) < e) if o1 == '<' else (_num(a) <= e), X, sp.S.Reals)
        r2 = sp.solveset((e < _num(b)) if o2 == '<' else (e <= _num(b)), X, sp.S.Reals)
        return r1 & r2
    m = re.fullmatch(r'(.+?)\s*(<=|>=|<|>)\s*(.+)', t)
    lhs, op, rhs = m.groups()
    lhs = _expr(lhs.replace('|', 'Abs(', 1).replace('|', ')', 1)) if '|' in lhs else _expr(lhs)
    rel = {'<': sp.Lt, '<=': sp.Le, '>': sp.Gt, '>=': sp.Ge}[op](lhs, _expr(rhs))
    return sp.solveset(rel, X, sp.S.Reals)


def _pair(s):
    m = re.search(r'\(\s*([^,()]+)\s*,\s*([^,()]+)\s*\)', _n(s))
    return (_num(m.group(1)), _num(m.group(2))) if m else None


def _line(s):
    """'y = 4x - 3' / 'y = (1/2)x - 3' -> (m, b)."""
    m = re.search(r'y\s*=\s*(.+)$', _n(s))
    e = sp.expand(_expr(m.group(1)))
    return sp.Poly(e, X).coeff_monomial(X), e.subs(X, 0)


def _num_answer(ans):
    m = re.findall(r'=\s*([-\d./]+)\s*$', _n(ans)) or re.findall(r'^\s*([-\d./]+)\s*$', _n(ans))
    return _num(m[-1]) if m else None


def check(spec, question, answer):
    """Return (status, expected, evidence). status in CORRECT / INCORRECT / UNSUPPORTED."""
    f, P = spec['form'], spec['parts']
    a = _n(answer)
    if f not in ('prime_or_factor',) and not re.search(r'\d|[a-z]\s*[\^(]', a):
        raise ValueError('answer has no mathematics to check')        # unreadable -> human review, never an accusation
    if f == 'inequality':
        want, got = _solve_ineq(P[0]), _rel_set(a)
        return (('CORRECT' if want == got else 'INCORRECT'), str(want), f'solution set of {P[0]} over the reals = {want}')
    if f in ('factor', 'prime_or_factor'):
        e = sp.expand(_expr(P[0]))
        if f == 'prime_or_factor' and re.search(r'prime', a, re.I):
            fl = sp.factor_list(e)
            prime = len(fl[1]) == 1 and fl[1][0][1] == 1 and sp.degree(fl[1][0][0], X) > 1
            return ('CORRECT' if prime else 'INCORRECT', str(sp.factor(e)), 'irreducible over the integers' if prime else f'factors as {sp.factor(e)}')
        g = _expr(a)
        same = sp.expand(g) == e
        def irreducible(fac):
            base = fac.base if isinstance(fac, sp.Pow) and fac.exp.is_Integer else fac
            if not base.has(X):
                return True
            fl = sp.factor_list(sp.expand(base))
            return len(fl[1]) == 1 and fl[1][0][1] == 1
        complete = all(irreducible(fc) for fc in sp.Mul.make_args(g))
        written_as_product = isinstance(g, (sp.Mul, sp.Pow))
        ok = same and written_as_product and (complete or 'completely' not in question.lower())
        return ('CORRECT' if ok else 'INCORRECT', str(sp.factor(e)),
                f'expands back to {e}: {same}; fully factored: {complete}; written as a product: {written_as_product}')
    if f == 'foil':
        e = sp.expand(_expr(P[0]))
        g = _expr(a)
        ok = sp.expand(g) == e and not re.search(r'\(', a)
        return ('CORRECT' if ok else 'INCORRECT', str(e), f'product expands to {e}')
    if f == 'system':
        eqs = [sp.Eq(_expr(s.split('=')[0]), _expr(s.split('=')[1])) for s in P]
        sol = sp.solve(eqs, [X, Y], dict=True)
        if len(sol) != 1:
            return ('UNSUPPORTED', str(sol), 'system does not have a unique solution')
        want = (sol[0][X], sol[0][Y])
        got = _pair(a)
        return ('CORRECT' if got == want else 'INCORRECT', f'({want[0]}, {want[1]})', f'unique solution {want}')
    if f == 'slope2':
        (x1, y1), (x2, y2) = [_pair(f'({p})') for p in P]
        want = (y2 - y1) / (x2 - x1)
        got = _num_answer(a)
        if got is None:
            raise ValueError('slope not found in the answer')
        return ('CORRECT' if got == want else 'INCORRECT', str(want), f'm = ({y2} - {y1})/({x2} - {x1}) = {want}')
    if f in ('line_point_slope', 'line_parallel'):
        if f == 'line_point_slope':
            (px, py), m_ = _pair(f'({P[0]})'), _num(P[1])
        else:
            m_, _ = _line(P[0])
            px, py = _pair(f'({P[1]})')
        gm, gb = _line(a)
        want_b = py - m_ * px
        ok = gm == m_ and gb == want_b
        return ('CORRECT' if ok else 'INCORRECT', f'y = {m_}x + {want_b}', f'slope {m_} through ({px}, {py}) gives intercept {want_b}')
    if f == 'evaluate':
        want = _expr(P[0]).subs(X, _num(P[1]))
        got = _num_answer(a)
        return ('CORRECT' if got == want else 'INCORRECT', str(want), f'f({P[1]}) = {want}')
    if f == 'avg_rate':
        e = _expr(P[0])
        p, q = _num(P[1]), _num(P[2])
        want = (e.subs(X, q) - e.subs(X, p)) / (q - p)
        got = _num_answer(a)
        return ('CORRECT' if got == want else 'INCORRECT', str(want), f'[f({q}) - f({p})]/({q} - {p}) = {want}')
    if f in ('vertex', 'axis'):
        src = _n(P[0])
        if '|' in src:
            e = _expr(src.replace('|', 'Abs(', 1).replace('|', ')', 1))
            inner = list(e.atoms(sp.Abs))[0].args[0]
            h = sp.solve(inner, X)[0]
        else:
            e = _expr(src)
            if sp.degree(sp.expand(e), X) != 2:
                return ('UNSUPPORTED', None, 'not a quadratic')
            h = sp.solve(sp.diff(e, X), X)[0]
        k = sp.simplify(e.subs(X, h))
        if f == 'axis':
            got = _num_answer(a)
            return ('CORRECT' if got == h else 'INCORRECT', f'x = {h}', f'axis x = {h}')
        got = _pair(a)
        return ('CORRECT' if got == (h, k) else 'INCORRECT', f'({h}, {k})', f'vertex ({h}, {k})')
    if f == 'sci':
        v = sp.nsimplify(P[0].replace(',', ''))
        m = re.fullmatch(r'([-\d.]+)\s*\*\s*10\s*\^\s*\(?([-\d]+)\)?', a.replace(' ', '').replace('*', '*'))
        if not m:
            return ('INCORRECT', None, 'answer is not written as a × 10^n')
        mant, ex = sp.nsimplify(m.group(1)), int(m.group(2))
        ok = mant * sp.Integer(10) ** ex == v and 1 <= abs(mant) < 10
        return ('CORRECT' if ok else 'INCORRECT', None, f'{mant} × 10^{ex} = {mant * sp.Integer(10) ** ex}; 1 ≤ |a| < 10')
    if f == 'simplify_pos':
        e, g = _expr(P[0]), _expr(a)
        ok = sp.simplify(e - g) == 0 and not re.search(r'\^\s*\(?-', a)
        return ('CORRECT' if ok else 'INCORRECT', str(sp.simplify(e)), f'equivalent: {sp.simplify(e - g) == 0}; only positive exponents: {not re.search(chr(94) + "-", a)}')
    if f == 'stats':
        data = [sp.nsimplify(v) for v in P[0].split(',')]
        wanted = {}
        for s in P[1:]:
            if s == 'mean':
                wanted['mean'] = sum(data) / len(data)
            elif s == 'median':
                d = sorted(data)
                n = len(d)
                wanted['median'] = d[n // 2] if n % 2 else (d[n // 2 - 1] + d[n // 2]) / 2
            elif s == 'mode':
                c = {v: data.count(v) for v in data}
                top = max(c.values())
                modes = [v for v in c if c[v] == top]
                if len(modes) != 1:
                    return ('UNSUPPORTED', None, 'multiple modes')
                wanted['mode'] = modes[0]
            elif s == 'range':
                wanted['range'] = max(data) - min(data)
        pairs = dict((k.lower(), _num(v)) for k, v in re.findall(r'(mean|median|mode|range)\s*=\s*([-\d./]+)', a, re.I))
        if not pairs and len(wanted) == 1 and _num_answer(a) is not None:
            pairs = {list(wanted)[0]: _num_answer(a)}
        if set(pairs) != set(wanted):
            return ('UNSUPPORTED', str(wanted), 'answer does not state every requested statistic')
        ok = all(pairs[k] == wanted[k] for k in wanted)
        return ('CORRECT' if ok else 'INCORRECT', str(wanted), f'computed {wanted}')
    return ('UNSUPPORTED', None, f'form {f} not checked')
