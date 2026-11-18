"""Verified revenue intake from the owner's platforms into the Capital Authorization Bridge.

Only money actually PAID to the business counts. Estimates, pending payouts and unit-sales x price never count.

* ByrdWay Product Studio (TpT products): Bridge.import_studio_ledger (read-only, daily).
* Amazon KDP books + Audible audiobooks: the KDP *Payment Report* download (kdp.amazon.com/help/topic/G201436840).
  Columns used: Payment Number, Marketplace, Payment Status ("Paid"/"Failed"), Payment Date, Payout Amount
  ("Pending" until the bank confirms), Sales Period, Source (eBook, KENP, "Audiobook - ..."). Rows count only when
  Payment Status is Paid AND Payout Amount is a number.
* Stripe (apps/direct sales): payouts with status=paid, i.e. money that reached the bank, net of Stripe fees and
  refunds. Requires a RESTRICTED read-only key (rk_...). Full secret keys (sk_...) are refused: GCI never holds a key
  that can move money.
"""
import csv
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .bridge import Bridge, BridgeError
from .money import D, ZERO

KDP_REQUIRED = ["Payment Number", "Marketplace", "Payment Status", "Payment Date", "Payout Amount"]


def _num(v):
    s = re.sub(r"[^0-9.\-]", "", str(v or ""))
    if s in ("", "-", "."):
        raise ValueError("not a number")
    return D(s)


def import_kdp_payments(store, csv_text: str, source_file: str) -> dict:
    """KDP Payment Report (save the downloaded report as CSV). Books and Audible audiobook royalties."""
    b = Bridge(store)
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("﻿")))
    hdr = {h.strip().lower(): h for h in (reader.fieldnames or [])}
    missing = [c for c in KDP_REQUIRED if c.lower() not in hdr]
    if missing:
        raise BridgeError(f"Not a KDP Payment Report; missing columns {missing}. Download Reports → Payments, save as CSV.")
    g = lambda row, name: (row.get(hdr.get(name.lower(), ""), "") or "").strip()
    added = pending = failed = dup = 0
    errors, by_source = [], {}
    for i, row in enumerate(reader, start=2):
        status = g(row, "Payment Status").lower()
        if status == "failed":
            failed += 1
            continue
        if status != "paid":
            pending += 1
            continue
        try:
            amt = _num(g(row, "Payout Amount"))
        except ValueError:
            pending += 1  # "Pending": the bank has not confirmed receipt yet
            continue
        src = g(row, "Source") or "KDP"
        ext = "KDP-" + "|".join([g(row, "Payment Number"), g(row, "Marketplace"), src, g(row, "Sales Period")])
        if store.conn.execute("SELECT 1 FROM bridge_entries WHERE external_id=?", (ext,)).fetchone():
            dup += 1
            continue
        if amt <= ZERO:
            continue
        try:
            b._post("SELLER_PROCEEDS", amt, f"KDP {src} ({g(row, 'Marketplace')}) paid {g(row, 'Payment Date')}", ext,
                    _iso(g(row, "Payment Date")), {"platform": "Audible" if "audio" in src.lower() else "KDP", "row": row})
            added += 1
            k = "Audiobooks" if "audio" in src.lower() else "Books"
            by_source[k] = str(D(by_source.get(k, "0")) + amt)
        except BridgeError as exc:
            errors.append({"line": i, "error": str(exc)})
    store.log("owner", "KDP_PAYMENTS_IMPORT", {"file": source_file, "added": added, "pending_skipped": pending,
                                                "failed_skipped": failed, "duplicates": dup})
    return {"added": added, "pending_skipped": pending, "failed_skipped": failed, "duplicates": dup, "by_source": by_source,
            "errors": errors}


def _iso(s):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return s or None


# ------------------------------------------------------------------ Stripe
STRIPE_API = "https://api.stripe.com/v1/payouts"
CRED_NAME = "stripe_restricted_read_key"


def check_stripe_key(key: str):
    if not key or not key.startswith(("rk_live_", "rk_test_")):
        raise PermissionError("Use a Stripe RESTRICTED key (starts with rk_) with only 'Payouts: Read' permission. "
                              "GCI refuses full secret keys (sk_) because they can move money.")


def sync_stripe_payouts(store, key: str, opener=urllib.request.urlopen, max_pages=20) -> dict:
    check_stripe_key(key)
    b = Bridge(store)
    added = dup = 0
    after = None
    for _ in range(max_pages):
        q = {"status": "paid", "limit": "100"}
        if after:
            q["starting_after"] = after
        req = urllib.request.Request(STRIPE_API + "?" + urllib.parse.urlencode(q), headers={"Authorization": f"Bearer {key}"})
        with opener(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        for p in data.get("data", []):
            if p.get("status") != "paid" or p.get("currency", "usd").lower() != "usd":
                continue
            ext = f"STRIPE-{p['id']}"
            if store.conn.execute("SELECT 1 FROM bridge_entries WHERE external_id=?", (ext,)).fetchone():
                dup += 1
                continue
            amt = D(p["amount"]) / 100
            d = datetime.fromtimestamp(p.get("arrival_date", 0), tz=timezone.utc).date().isoformat()
            if amt > ZERO:
                b._post("SELLER_PROCEEDS", amt, f"Stripe payout {p['id']} arrived {d}", ext, d, {"platform": "Stripe"})
                added += 1
        if not data.get("has_more") or not data.get("data"):
            break
        after = data["data"][-1]["id"]
    store.log("system", "STRIPE_PAYOUT_SYNC", {"added": added, "already_imported": dup})
    return {"added": added, "already_imported": dup}


def job_stripe_sync(store, now=None):
    """Daily job. Uses the DPAPI-encrypted key if the owner saved one; otherwise reports NOT_CONFIGURED."""
    from pathlib import Path
    from .security import CredentialStore, CredentialStoreUnavailable
    if store.path == ":memory:":
        return {"status": "NOT_CONFIGURED"}
    try:
        key = CredentialStore(Path(store.path).parent / "credentials.json").get(CRED_NAME)
    except CredentialStoreUnavailable:
        return {"status": "NOT_CONFIGURED", "reason": "encrypted credential store needs Windows"}
    if not key:
        return {"status": "NOT_CONFIGURED"}
    return {"status": "OK", **sync_stripe_payouts(store, key)}
