"""Validation engine (SSOI Phase 6): rolling windows, walk-forward, out-of-sample,
cost sensitivity, drawdowns, inflation adjustment, benchmark comparison.

Look-ahead prevention: a strategy only ever receives `history[:t]` as an
immutable tuple, so it is impossible for it to read prices at or after t.
Results are always labelled BACKTEST - never actual profits.
"""
import math

LABEL = "BACKTEST (hypothetical; not actual results)"


class LookAheadError(Exception):
    pass


def returns(prices):
    return [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]


def max_drawdown(values):
    peak, mdd = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd


def simulate(prices: dict, strategy, start: int, end: int, cost_bps=0.0, spread_bps=0.0, expense_ratio=None,
             periods_per_year=12, rebalance_every=1):
    """prices: {symbol: [p0, p1, ...]} aligned. strategy(history) -> {symbol: weight}, sum<=1, rest cash (0%)."""
    syms = sorted(prices)
    n = len(prices[syms[0]])
    if any(len(prices[s]) != n for s in syms):
        raise ValueError("price series must be aligned")
    value, weights, curve, turnover_cost = 1.0, {s: 0.0 for s in syms}, [1.0], 0.0
    er = expense_ratio or {}
    for t in range(start, end):
        if (t - start) % rebalance_every == 0:
            history = {s: tuple(prices[s][:t + 1]) for s in syms}  # information available at close of t
            target = strategy(history)
            if sum(target.values()) > 1.0000001 or any(w < 0 for w in target.values()):
                raise ValueError("weights must be non-negative and sum to <= 1 (no leverage or shorting)")
            trade = sum(abs(target.get(s, 0.0) - weights[s]) for s in syms)
            c = trade * (cost_bps + spread_bps / 2) / 10000
            value *= (1 - c)
            turnover_cost += c
            weights = {s: target.get(s, 0.0) for s in syms}
        growth = sum(weights[s] * (prices[s][t + 1] / prices[s][t] - er.get(s, 0.0) / periods_per_year) for s in syms)
        growth += 1 - sum(weights.values())
        new_value = value * growth
        # drift weights
        if new_value > 0:
            weights = {s: weights[s] * value * (prices[s][t + 1] / prices[s][t]) / new_value for s in syms}
        value = new_value
        curve.append(value)
    yrs = (end - start) / periods_per_year
    cagr = value ** (1 / yrs) - 1 if yrs > 0 and value > 0 else None
    rets = returns(curve)
    vol = (math.sqrt(sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / max(len(rets) - 1, 1)) * math.sqrt(periods_per_year)
           if rets else None)
    return {"label": LABEL, "final_value": value, "cagr": cagr, "volatility": vol, "max_drawdown": max_drawdown(curve),
            "cost_drag": turnover_cost, "start": start, "end": end, "curve": curve}


def rolling_windows(n_points: int, window: int, step: int):
    return [(s, s + window) for s in range(0, n_points - window, step)]


def walk_forward(prices, make_strategy, train: int, test: int, **kw):
    """Fit on [s, s+train), evaluate out-of-sample on [s+train, s+train+test). Never overlaps."""
    syms = sorted(prices)
    n = len(prices[syms[0]])
    results, s = [], 0
    while s + train + test < n:
        train_slice = {k: tuple(v[s:s + train]) for k, v in prices.items()}
        strat = make_strategy(train_slice)
        oos = simulate(prices, strat, s + train, s + train + test, **kw)
        results.append({"train": (s, s + train), "test": (s + train, s + train + test), **{k: oos[k] for k in
                        ("final_value", "cagr", "max_drawdown", "cost_drag")}})
        s += test
    return {"label": LABEL, "folds": results, "n_folds": len(results)}


def cost_sensitivity(prices, strategy, start, end, cost_grid=(0, 5, 10, 25, 50), **kw):
    return [{"cost_bps": c, **{k: simulate(prices, strategy, start, end, cost_bps=c, **kw)[k]
                               for k in ("final_value", "cagr", "cost_drag")}} for c in cost_grid]


def real_return(nominal_total, inflation_total):
    return (1 + nominal_total) / (1 + inflation_total) - 1


def compare_to_benchmark(prices, strategy, benchmark_strategy, windows, **kw):
    rows = []
    for (a, b) in windows:
        s = simulate(prices, strategy, a, b, **kw)
        bm = simulate(prices, benchmark_strategy, a, b, **kw)
        rows.append({"window": (a, b), "strategy": s["final_value"], "benchmark": bm["final_value"],
                     "excess": s["final_value"] - bm["final_value"]})
    wins = sum(1 for r in rows if r["excess"] > 0)
    return {"label": LABEL, "windows": rows, "strategy_won": wins, "n": len(rows),
            "note": "Fewer than 3 windows is insufficient." if len(rows) < 3 else None}


def survivorship_check(universe_as_of: dict, symbols_used: list, as_of_index: int):
    """universe_as_of: {symbol: (listed_index, delisted_index_or_None)}. Using a symbol before it existed = look-ahead."""
    bad = [s for s in symbols_used if s not in universe_as_of or universe_as_of[s][0] > as_of_index]
    if bad:
        raise LookAheadError(f"Symbols not investable at t={as_of_index}: {bad}")
    delisted = [s for s, (_, d) in universe_as_of.items() if d is not None and d >= as_of_index]
    return {"ok": True, "delisted_in_universe": delisted}
