"""Market-data adapters with provenance and staleness labelling (SSOI Phase 17).

Adapters:
  * EvidenceSnapshot - dated, sourced research snapshot files in data/evidence/
  * TreasuryBillRates - U.S. Treasury official daily bill rates CSV (no key needed)
Free sources are NOT exchange-licensed real-time feeds; every value carries its
source URL, as-of date and retrieval time, and is flagged stale past max_age.
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "evidence"
TREASURY_BILLS_CSV = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
                      "all/{ym}?type=daily_treasury_bill_rates&field_tdr_date_value_month={ym}&page&_format=csv")


class DataUnavailable(Exception):
    pass


def age_days(as_of: str, today: date = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    return (today - date.fromisoformat(as_of[:10])).days


def freshness(as_of: str, max_age_days: int, today: date = None) -> dict:
    a = age_days(as_of, today)
    return {"as_of": as_of, "age_days": a, "max_age_days": max_age_days, "stale": a > max_age_days}


def load_snapshot(path=None, today: date = None) -> dict:
    files = sorted(EVIDENCE_DIR.glob("*.json")) if path is None else [Path(path)]
    if not files:
        raise DataUnavailable("No evidence snapshot available.")
    snap = json.loads(files[-1].read_text(encoding="utf-8"))
    snap["freshness"] = {k: freshness(v["as_of"], v["max_age_days"], today) for k, v in snap.get("freshness_inputs", {}).items()}
    snap["file"] = files[-1].name
    return snap


def fetch_treasury_bills(ym: str = None, timeout=20, opener=urllib.request.urlopen) -> dict:
    """Live fetch from Treasury. Raises DataUnavailable on any failure (network policy, outage, format change)."""
    ym = ym or datetime.now(timezone.utc).strftime("%Y%m")
    url = TREASURY_BILLS_CSV.format(ym=ym)
    try:
        with opener(url, timeout=timeout) as r:
            text = r.read().decode("utf-8")
    except Exception as exc:
        raise DataUnavailable(f"Treasury fetch failed: {exc}") from exc
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "Date" not in rows[0]:
        raise DataUnavailable("Treasury CSV format not recognised.")
    latest = rows[0]
    key = next((k for k in latest if "13 WEEKS COUPON EQUIVALENT" in k.upper()), None)
    if key is None:
        raise DataUnavailable("13-week coupon-equivalent column missing.")
    m, d, y = latest["Date"].split("/")
    return {"as_of": f"{y}-{m}-{d}", "tbill_13w_coupon_equiv_pct": float(latest[key]), "source": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
