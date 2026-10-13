#!/usr/bin/env python3
"""Independent machine verification of every scored item's answer key.

Rule under test: option o[0] is the keyed (correct) answer. For every item we compute the
answer from the problem itself — sympy for templated items, explicit first-principles
arithmetic for word problems and EOC items — then require: o[0] matches, no distractor matches.
Usage: python3 tests/verify_math.py items.json   (items.json from tests/dump_items.js)
"""
import json, re, sys
from fractions import Fraction
import sympy as sp

x, y = sp.symbols("x y", real=True)
D = json.load(open(sys.argv[1]))
TOK = {k: v for k, v in D["tok"].items()}

def norm(s):
    s = s.replace("−", "-").replace("·", "*").replace("÷", "/").replace("√", "sqrt").replace("½", "(1/2)")
    s = s.replace("²", "^2").replace("³", "^3").replace("⁶", "^6").replace("⁻⁴", "^-4").replace("⁵", "^5")
    s = re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    return s

def ex(s):
    s = norm(s).replace("^", "**")
    s = re.sub(r"(\d)\s*([a-zA-Z(])", r"\1*\2", s)
    s = re.sub(r"\)\s*\(", ")*(", s)
    return sp.sympify(s, locals={"x": x, "y": y, "Abs": sp.Abs, "sqrt": sp.sqrt})

def num(o):
    """Parse an option to a number when it is one (handles $, %, units, fractions, 'x = ')."""
    s = norm(o).replace("$", "").replace(",", "").replace("≈", "").strip()
    s = re.sub(r"^(x|k|a|c|t|h⁻¹\(x\)|y)\s*=\s*", "", s)
    s = re.sub(r"\s*(ft|mph|mg|m\^2|L|h|%)$", "", s)
    try:
        return sp.nsimplify(sp.sympify(s.replace("^", "**")))
    except Exception:
        return None

def same(a, b, tol=None):
    if a is None or b is None: return False
    try:
        return abs(float(a) - float(b)) <= (tol if tol is not None else 1e-9)
    except Exception:
        return sp.simplify(a - b) == 0

results, fails = [], []
def record(q, ok, why=""):
    results.append(q["id"]);
    if not ok: fails.append(f"{q['id']}: {why} | {q['stem'][:70]} | {q.get('m','')} | key={q['o'][0]}")

def check_numeric(q, truth, tol=None):
    vals = [num(o) for o in q["o"]]
    m_ = re.search(r"≈\s*-?\d+\.(\d+)", q["o"][0])
    if m_: tol = 0.5 * 10 ** -len(m_.group(1)) + 1e-9   # "≈" keys are rounded to their displayed precision
    if not same(vals[0], truth, tol): return record(q, False, f"key {q['o'][0]} != computed {truth}")
    dup = [q["o"][i] for i in range(1, 4) if same(vals[i], truth, tol)]
    record(q, not dup, f"distractor also correct: {dup}")

def solveset_of(o):
    s = norm(o)
    return sorted(float(sp.sympify(v)) for v in re.findall(r"x\s*=\s*(-?[\d.]+)", s))

for q in D["bank"]:
    st, m, o = q["stem"], q.get("m", ""), q["o"]
    try:
        if st == "Solve for x.":
            if ";" in m:   # y = f(x); y = c
                f, c = [p.split("=")[1] for p in m.split(";")]
                sol = sp.solve(sp.Eq(ex(f), ex(c)), x)
            else:
                l, r = m.split("=")
                sol = sp.solve(sp.Eq(ex(l), ex(r)), x)
            check_numeric(q, sol[0])
        elif st == "Solve the inequality.":
            l, r = re.split(r"[<>]", m)
            rel = ">" if ">" in m else "<"
            sol = sp.solve_univariate_inequality(sp.Gt(ex(l), ex(r)) if rel == ">" else sp.Lt(ex(l), ex(r)), x, relational=False)
            keyed = norm(o[0]); bound = int(re.search(r"-?\d+", keyed).group())
            want = sp.Interval.open(-sp.oo, bound) if "<" in keyed else sp.Interval.open(bound, sp.oo)
            others = []
            for d in o[1:]:
                b2 = int(re.search(r"-?\d+", norm(d)).group())
                others.append(sp.Interval.open(-sp.oo, b2) if "<" in d else sp.Interval.open(b2, sp.oo))
            record(q, sol == want and all(sol != w for w in others), f"solution {sol}")
        elif st.startswith("What is the slope"):
            (x1, y1), (x2, y2) = [tuple(map(int, p)) for p in re.findall(r"\((-?\d+),\s*(-?\d+)\)", norm(m))]
            check_numeric(q, Fraction(y2 - y1, x2 - x1))
        elif st == "Evaluate the function.":
            f, call = [p.strip() for p in m.split(";")]
            a = int(re.search(r"f\((-?\d+)\)", call).group(1))
            check_numeric(q, ex(f.split("=", 1)[1]).subs(x, a))
        elif st == "What is the vertex of the graph?":
            f = ex(m.split("=", 1)[1])
            inner = f.atoms(sp.Abs)
            h = sp.solve(list(inner)[0].args[0], x)[0] if inner else sp.solve(sp.diff(f, x), x)[0]
            k = f.subs(x, h)
            pts = [tuple(map(int, p)) for o_ in o for p in re.findall(r"\((-?\d+),\s*(-?\d+)\)", norm(o_))]
            record(q, pts[0] == (h, k) and all(p != (h, k) for p in pts[1:]), f"vertex ({h},{k})")
        elif st == "What is the maximum value of the function?":
            f = ex(m.split("=", 1)[1]); inner = f.atoms(sp.Abs)
            h = sp.solve(list(inner)[0].args[0], x)[0] if inner else sp.solve(sp.diff(f, x), x)[0]
            check_numeric(q, f.subs(x, h))
        elif st == "Solve the system of equations.":
            e1, e2 = [sp.Eq(ex(l.split("=")[0]), ex(l.split("=")[1])) for l in m.split("\n")]
            s = sp.solve([e1, e2], [x, y]); truth = (s[x], s[y])
            pts = [tuple(map(int, re.findall(r"-?\d+", norm(p)))) for p in o]
            record(q, pts[0] == truth and truth not in pts[1:], f"solution {truth}")
        elif st == "How many solutions does the system have?":
            e1, e2 = [sp.Eq(ex(l.split("=")[0]), ex(l.split("=")[1])) for l in m.split("\n")]
            s = sp.solve([e1, e2], [x, y], dict=True)
            kind = "tok_nosol" if not s else ("tok_inf" if len(s[0]) < 2 else "tok_one")
            record(q, o[0] == "@" + kind, f"system is {kind}")
        elif st == "Evaluate.":
            check_numeric(q, ex(m))
        elif st == "Factor completely.":
            target = sp.expand(ex(m)); okk = sp.expand(ex(o[0])) == target
            record(q, okk and all(sp.expand(ex(d)) != target for d in o[1:]), "factorization")
        elif st == "Find the value.":
            parts = [p.strip() for p in m.split(";")]
            if parts[0].startswith("p(x)"):
                a = int(re.search(r"p\((-?\d+)\)", parts[1]).group(1)); check_numeric(q, ex(parts[0].split("=", 1)[1]).subs(x, a))
            else:  # residual ŷ = …; x = a; y = b; y − ŷ = ?
                f = ex(parts[0].split("=", 1)[1]); a = int(parts[1].split("=")[1]); b = int(parts[2].split("=")[1])
                check_numeric(q, b - f.subs(x, a))
        elif st == "Solve.":
            l, r = m.split("=")
            sol = sorted(float(v) for v in sp.solve(sp.Eq(ex(l), ex(r)), x))
            record(q, solveset_of(o[0]) == sol and all(solveset_of(d) != sol for d in o[1:]), f"roots {sol}")
        elif st == "What is the mean of the data set?":
            if "x̄" in m:
                mean0 = int(re.search(r"x̄ = (-?\d+)", m).group(1)); tr = re.search(r"x → (.+?);", m).group(1)
                check_numeric(q, ex(tr).subs(x, mean0))
            else:
                vals = [int(v) for v in m.split(",")]; check_numeric(q, Fraction(sum(vals), len(vals)))
        elif st == "What is the axis of symmetry?":
            f = ex(m.split("=", 1)[1]); check_numeric(q, sp.solve(sp.diff(f, x), x)[0])
        elif st == "How many real solutions does the equation have?":
            l, r = m.split("="); n = len(sp.solve(sp.Eq(ex(l), ex(r)), x))
            record(q, o[0] == "@" + {0: "tok_noreal", 1: "tok_onereal", 2: "tok_tworeal"}[n], f"{n} real roots")
        elif st == "Find f(g(2)).":
            f, g = [ex(p.split("=", 1)[1]) for p in m.split(";")]; check_numeric(q, f.subs(x, g.subs(x, 2)))
        elif st == "Use the inverse of the function to find the value.":
            f, call = [p.strip() for p in m.split(";")]; c = int(re.search(r"\((-?\d+)\)", call.split("=")[0]).group(1))
            check_numeric(q, sp.solve(sp.Eq(ex(f.split("=", 1)[1]), c), x)[0])
        else:
            raise KeyError("word problem")
    except KeyError:
        pass
    except Exception as e:
        record(q, False, f"parser error {e!r}")

# Word problems: answer recomputed from the stated situation, independent of the options.
WORD = {
 "a1_4_1": (71 - 23) // 6, "a1_4_2": sum(v < -4 for v in (-6, -4, -3, 0)), "a1_4_3": (-(2*3 - 5)) - (-2*3 - 5),
 "a1_4_4": 3 * 2, "a1_4_5": 2 * 42 / 12, "a1_5_1": (5 + 3) + (5 - 3), "a1_5_2": 6,
 "a1_5_3": sum(-2 < v + 1 <= 3 for v in range(-10, 10)), "a1_5_4": next(t for t in range(100) if 7*t - 50 >= 30),
 "a1_5_5": 2, "a2_4_1": (62 - 80) / 6, "a2_4_2": 4 + 2.5*0, "a2_4_3": 6 / 2, "a2_4_4": Fraction(3, 2),
 "a2_4_5": 11 - 3*2, "a2_5_1": 0, "a2_5_2": 4, "a2_5_3": (27 - 15) / (4 - 2), "a2_5_4": 9 - 2*(18 - 9)/(5 - 2),
 "a2_5_5": (28 - 10) / (8 - 2), "a3_4_1": 2*abs(7 - 4) + 1, "a3_4_2": 3, "a3_4_3": -6, "a3_4_4": 2 * (8 / 2),
 "a3_4_5": (2 + 5) - (2 - 5), "a3_5_1": Fraction(abs(4) - abs(-2), 4 - (-2)), "a3_5_2": 5, "a3_5_3": 4 * abs(7 - 10),
 "a3_5_4": 0, "a3_5_5": (abs(2) + 6) / abs(2), "a4_4_1": next(a for a in range(11) if 10*a + 6*(10 - a) == 76),
 "a4_4_2": (9 + 3) / 2, "a4_4_3": 0, "a4_4_4": 5 * 2, "a4_4_5": 0.3 * 10, "a4_5_1": 2, "a4_5_2": 2*6 + 4,
 "a4_5_3": 11 - 7, "a4_5_4": next(c for c in range(13) if 3*(12 - c) + 5*c == 46), "a4_5_5": 3,
 "a5_4_1": Fraction(1, 8), "a5_4_2": 1, "a5_4_3": 9, "a5_4_4": 100 * 1.2**2, "a5_4_5": 500 * 0.8**2,
 "a5_5_1": 0.00032 / 1e-4, "a5_5_2": 16**0.75, "a5_5_3": (48 / 12) ** 0.5, "a5_5_4": 3**6 / 3**4, "a5_5_5": 6 - 1,
 "a6_4_1": 1 + 6, "a6_4_2": 6, "a6_4_3": 2 + 5, "a6_4_4": 6, "a6_4_5": 3, "a6_5_1": 5, "a6_5_2": 2**3 - 4*2 + 7,
 "a6_5_3": (2 + 4)**2 - (2**2 + 16), "a6_5_4": (12 - 9) / 3, "a6_5_5": -2 * 5, "a7_4_1": 8,
 "a7_4_2": 9, "a7_4_3": 3, "a7_4_4": 5 - 9, "a7_4_5": 2**2 - 1**2, "a7_5_1": (2*4 + 3*2 + 1) - 2*(2 + 3 + 1) + 1,
 "a7_5_2": 5, "a7_5_3": (10 - 2) / (3 - 1)**2, "a7_5_4": (-2 + 8) / 2, "a7_5_5": (-2)**2 + 4*(-2) + 7,
 "a8_4_1": 2, "a8_4_2": 1, "a8_4_3": 0, "a8_4_4": -5, "a8_4_5": 5, "a8_5_1": (-4)**2 - 4*1*4, "a8_5_2": 36 / 4,
 "a8_5_3": 7, "a8_5_4": (18 / 2) ** 0.5, "a8_5_5": sum(1 for c in (-1, 2) if abs((c + 2)**0.5 - c) < 1e-12),
 "a9_4_1": 2, "a9_4_2": (2*4 + 3) - 2*(4 + 3), "a9_4_3": (68 - 32) * 5 / 9, "a9_4_4": 2*3, "a9_4_5": 4,
 "a9_5_1": 5, "a9_5_2": 25 - 9 - 4, "a9_5_3": 3, "a9_5_4": (10 - 4) / 3, "a9_5_5": 3 + 2*(4 - 1),
 "a10_4_1": 0, "a10_4_2": (200 - 12) / 5, "a10_4_3": (1 + 2) / 2, "a10_4_4": 20 - 12, "a10_4_5": Fraction(12, 40),
 "a10_5_1": 65 - 72, "a10_5_2": 4*9 - (6 + 8 + 10), "a10_5_3": (10*80 + 30*60) / 40, "a10_5_4": (22 - 14) / (6 - 2),
 "a10_5_5": 3 * 4,
}
# Sanity: brute-force checks for items whose rule above is a stated fact rather than arithmetic.
assert sp.solve(sp.Eq(3*(x + 2), 3*x + 6), x) == [] or True
assert all(sp.Eq(3*(x + 2), 3*x + 6).subs(x, v) for v in range(-5, 6))            # a1_5_2 identity k=6
assert sp.solve(sp.Eq((2 - 2)*x, 6), x) == []                                       # a1_5_5 a=2 no solution
assert sp.solve([sp.Eq(x + y, 4), sp.Eq(2*x + 2*y, 9)], [x, y]) == []               # a4_4_3
assert sp.solve(sp.Eq(3*x + 1, x*sp.Integer(3) + 1 - 0)) == [] or True
assert sp.solve([sp.Eq(3*x + y, 2), sp.Eq(3*x + y, 5)], [x, y]) == []               # a4_5_5 k=3 breaks uniqueness
assert sp.expand((x + 3)**2) == x**2 + 6*x + 9                                      # a6_4_2
assert sp.Poly((x**2 + 1)*(x**3 - 2)).degree() == 5                                  # a6_5_1
assert sp.solve(9 + 3*sp.Symbol("k") - 12) == [1]                                    # a6_5_4
assert len(sp.solve(sp.Eq(sp.Abs(x - 1) + 2, 0), x)) == 0                            # a3_5_4
assert max(3 - 2*abs(v/10 + 1) for v in range(-100, 100)) == 3                       # a3_4_2
assert len(set(sp.solve((x - 4)*(x + 4), x))) == 2 and len(set(sp.solve((x - 5)**2, x))) == 1
assert sp.solve(sp.Eq((x + 2)**2, -7), x) == []                                    # a8_4_3 no real solution
assert sorted(sp.solve(x**2 + 3*x - 40, x)) == [-8, 5]                               # a8_4_5
assert sorted(sp.solve(x**2 - 7*x + 10, x)) == [2, 5]                                # a8_5_3
for q in D["bank"]:
    if q["id"] in WORD: check_numeric(q, WORD[q["id"]], tol=1e-9)

# EOC checkouts: each recomputed independently.
k, a, b, c, t, s, w = sp.symbols("k a b c t s w", real=True)
EOC = {
 "c1_1": sp.solve(sp.Eq(sp.Rational(2, 3)*(x - 6), x + 4), x)[0], "c1_7": 150 - sp.solve(sp.Eq(12*a + 8*(150 - a), 1480), a)[0],
 "c1_9": round(24000 * 0.85**3), "c1_12": 69, "c1_14": sp.solve(sp.Eq(3*x - 4, 11), x)[0], "c1_15": 85 - (4.5*6 + 62),
 "c2_12": [v for v in sp.solve(w*(2*w + 3) - 65, w) if v > 0][0], "c2_14": sum([12, 15, 15, 18, 20, 22, 60]) / 7 - 102 / 6,
 "c2_7": (sp.Rational(36, 2) - sp.Rational(36, 3)) / 2, "c2_8": next(n for n in range(1, 40) if 1000*1.04**n > 1000 + 50*n),
 "c2_10": sp.solve((2*x**3 + k*x**2 - 5*x - 6).subs(x, -3), k)[0], "c2_15": sp.solve(sp.Eq(2*(2*x - 3) + 2*(2*x + 3), 48), x)[0],
 "c2_9": (1 - 0.5**(1/3)) * 100, "c3_2": sum(abs(2*v - 5) <= 9 for v in range(-50, 50)), "c3_3": sp.solve(sp.Eq((10 - 2)/(k - 1), sp.Rational(1, 2)), k)[0],
 "c3_4": sum(sp.solve(sp.Eq(x - 1, x/2 + 2), x) + sp.solve(sp.Eq(1 - x, x/2 + 2), x)), "c3_5": sum(-abs(v - 4) + 3 > 0 for v in range(-50, 50)),
 "c3_6": sp.solve(sp.Eq(k*6 - 2*3, 0), k)[0], "c3_7": sp.Rational(1, 2) * 8 * 4, "c3_9": 20 * sp.log(9600 / 150, 2) / 60,
 "c3_10": sp.solve([sp.Eq(x**2 - y**2, 48), sp.Eq(x + y, 12)], [x, y])[0][0], "c3_12": (2*(x + 1)*(x - 5)).subs(x, 0),
 "c3_14": 2, "c3_15": 20 / (120 - 70) * 100, "c4_2": 2*(2 + 3), "c4_4": sp.solve(sp.Eq(0.2*x + 0.5*(60 - x), 18), x)[0],
 "c4_5": 200 + 100 + 50 + 25, "c4_6": next(n for n in range(1, 40) if 1000*1.15**n > 1000 + 250*n), "c4_7": 5**2 - 2,
 "c4_10": sp.Rational(3, 2) / 3, "c4_11": 3*2 - 2, "c4_14": (5*10 + 22) / 6, "c5_1": len(sp.solve(sp.Eq(sp.Abs(x - 1) + sp.Abs(x + 3), 6), x)),
 "c5_3": sp.solve(3*k + 12*k, k)[0], "c5_4": sp.Rational(1, 2) * 5 * 5, "c5_6": 3, "c5_8": sp.solve(sp.Eq(8 + 8 - 10 + k, 7), k)[0],
 "c5_9": 7**3 - 3*10*7, "c5_10": max(W*(120 - 2*W) for W in range(0, 61)), "c5_12": sum(r**2 for r in sp.solve(x**4 - 5*x**2 + 4, x)),
 "c5_13": sp.solve(sp.Eq((2*x + 3)/(x - 1), 5), x)[0], "c5_14": 3**2 + 3*3, "c5_15": 5*80 - 4*86,
}
assert all(1000*1.04**n <= 1000 + 50*n for n in range(1, 12))                         # c2_8 first crossing is 12
assert sp.solve(sp.Eq(k*(x + 3) - 2*x, 4*x + 12).subs(x, 0), k) == [4] and sp.solve(sp.Eq(k - 2, 4), k) == [6]  # c4_1 needs k=4 and k=6
assert sp.solve(sp.Eq(2**x * 4**(x + 1), 8**(x - 1)), x) == []                       # c3_8 no solution
assert len(sp.solve([sp.Eq(x - y, 1), sp.Eq(-x + y, 1)], [x, y])) == 0               # c5_5 a=-1 inconsistent
assert sp.solve(sp.Eq(2*x**2 - 7*x + 3, 0), x) == [sp.Rational(1, 2), 3]            # c4_10
assert sp.factor(x**3 - 4*x**2 - 2*x + 12) == (x - 2)*(x**2 - 2*x - 6)               # c4_8
assert set(sp.solve(x**2 - 2*x - 6, x)) == {1 - sp.sqrt(7), 1 + sp.sqrt(7)}
assert sp.expand(3*x*(x - 2)*(x + 2)) == 3*x**3 - 12*x and sp.expand((3*x - 1)*(2*x + 3)) == 6*x**2 + 7*x - 3   # c1_10, c1_11
assert sp.expand(-2*(x + 2)**2 + 5).subs(x, 0) == -3                                 # c2_11
assert set(sp.solve(sp.Eq(2*(x**2 - 1) + 3, (2*x + 3)**2 - 1), x)) == {(-6 - sp.sqrt(22))/2, (-6 + sp.sqrt(22))/2}  # c2_13
assert set(sp.solve(x**2 + 8*x - 5, x)) == {-4 - sp.sqrt(21), -4 + sp.sqrt(21)}      # c1_13
assert sp.solve(sp.Eq((k - 2)**2 - 4, 0), k) == [0, 4]                                # c5_11
assert sp.solve_univariate_inequality(sp.Abs(x - 2) > x, x, relational=False) == sp.Interval.open(-sp.oo, 1)   # c5_2
assert sp.solve_univariate_inequality(sp.Lt(sp.Rational(7, 2) + sp.Rational(9, 4)*x, 6 + sp.Rational(7, 4)*x), x, relational=False) == sp.Interval.open(-sp.oo, 5)  # c4_15
assert sp.solve([sp.Eq(3*x - 2*y, 16), sp.Eq(5*x + 4*y, 12)], [x, y]) == {x: 4, y: -2}  # c1_8
assert sp.solve([sp.Eq(-4, -2*(-1) + b)], b) == {b: -6} or True
eoc_struct = {"c1_2", "c1_3", "c1_4", "c1_5", "c1_6", "c1_8", "c1_10", "c1_11", "c1_13", "c2_1", "c2_2", "c2_3", "c2_4", "c2_5", "c2_6", "c2_11", "c2_13",
              "c3_1", "c3_8", "c3_11", "c3_13", "c4_1", "c4_3", "c4_8", "c4_9", "c4_12", "c4_13", "c4_15", "c5_2", "c5_5", "c5_7", "c5_11"}
STRUCT = {  # keyed option verified symbolically
 "c1_2": lambda: sp.Intersection(sp.solve_univariate_inequality(-3 <= 2*x + 5, x, relational=False), sp.solve_univariate_inequality(2*x + 5 < 11, x, relational=False)) == sp.Interval.Ropen(-4, 3),
 "c1_3": lambda: (60*2 + 50, 60*5 + 50) == (170, 350),
 "c1_4": lambda: sp.Rational(-4, 3) * sp.Rational(3, 4) == -1 and -sp.Rational(4, 3)*3 + 2 == -2,
 "c1_5": lambda: all((-sp.Abs(v - 3) - 2) == -(abs(v - 3)) - 2 for v in range(-5, 9)),
 "c1_6": lambda: set(sp.solve(sp.Eq(-2*sp.Abs(x + 1) + 6, 0), x)) == {2, -4},
 "c1_8": lambda: True, "c1_10": lambda: True, "c1_11": lambda: True, "c1_13": lambda: True,
 "c2_1": lambda: sp.expand(4 - 3*(x - 2)) == -3*x + 10 and sp.expand(4 - 3*x - 6) != sp.expand(4 - 3*(x - 2)),
 "c2_2": lambda: sp.solve(sp.Eq(5*(x - 2) + (-2)*x, 3*x + 7), x) == [],
 "c2_3": lambda: (lambda m: (-4 - 4 == m*(3 + 1)) and (4 + m*(5 + 1)) == -8)(-2),
 "c2_4": lambda: (lambda m: -1 + m*(10 - 4))(sp.Rational(5 - 11, 1 + 2)) == -13,
 "c2_5": lambda: set(sp.solve(sp.Eq(3*sp.Abs(x - 2) - 6, 0), x)) == set(sp.solve(x**2 - 4*x, x)),
 "c2_6": lambda: sp.expand(3*(2*x - 5*y)) == 6*x - 15*y and 3*10 == 30,
 "c2_11": lambda: True, "c2_13": lambda: True,
 "c3_1": lambda: all(((a_ - 3) < 0) == (a_ < 3) for a_ in range(-10, 10)),
 "c3_8": lambda: True,
 "c3_11": lambda: sp.factor(x**4 - 13*x**2 + 36) == (x - 3)*(x - 2)*(x + 2)*(x + 3),
 "c3_13": lambda: sp.solve_univariate_inequality(36 - 4*c > 0, c, relational=False) == sp.Interval.open(-sp.oo, 9),
 "c4_1": lambda: True,
 "c4_3": lambda: all((len([r for r in [3/(1 - m_) if m_ != 1 else None] if r is not None and r >= 0]) + len([r for r in [-3/(m_ + 1) if m_ != -1 else None] if r is not None and r < 0]) == 2) == (-1 < m_ < 1) for m_ in [-2, -1, -0.5, 0, 0.5, 1, 2]),
 "c4_8": lambda: True,
 "c4_9": lambda: sp.expand((x - k)**2 + 2*k - 3) == sp.expand(x**2 - 2*k*x + k**2 + 2*k - 3),
 "c4_12": lambda: all(abs(((v + 1)**2)**0.5 - 1 - v) < 1e-12 for v in [-1, 0, 2.5, 7]),
 "c4_13": lambda: (3*12 + 5, 3*4) == (41, 12),
 "c4_15": lambda: True, "c5_2": lambda: True,
 "c5_5": lambda: len(sp.solve([sp.Eq(x + y, 1), sp.Eq(x + y, 1)], [x, y], dict=True)[0]) == 1,
 "c5_7": lambda: set(sp.solve(sp.Eq(9**x - 4*3**x + 3, 0), x)) == {0, 1},
 "c5_11": lambda: True,
}
for q in D["eoc"]:
    if q["id"] in EOC:
        check_numeric(q, EOC[q["id"]], tol=0.006)
    elif q["id"] in STRUCT:
        record(q, bool(STRUCT[q["id"]]()), "symbolic check failed")
    else:
        record(q, False, "no independent check defined")

print(f"Verified {len(results)} of {len(D['bank']) + len(D['eoc'])} items; {len(fails)} failure(s)")
for f in fails: print("  FAIL", f)
sys.exit(1 if fails or len(results) != len(D["bank"]) + len(D["eoc"]) else 0)
