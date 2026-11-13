"""Exceptions, circuit breakers and immediate notifications (SSOI §14, §16B).

* Exceptions are deduplicated: the same problem raises one open exception, not a stream of alerts.
* IMMEDIATE exceptions notify the owner right away (in-app banner + Windows toast where available);
  WEEKLY exceptions wait for the weekly report.
* A circuit breaker suspends one automated GCI workflow. Tripping a breaker never creates, edits or
  cancels a brokerage order or instruction; when the owner must act at the broker (for example, pausing
  Autoinvest), GCI raises an exception that says exactly what to do and by when.
"""
import subprocess
import sys
import uuid

from .db import Store, now_iso

WORKFLOWS = {
    "research_spend": "Discretionary research spending",
    "contribution_proposals": "ByrdWay → brokerage contribution proposals",
    "recurring_monitor": "Autoinvest standing-instruction monitoring",
    "gain_certification": "Realized-gain certification",
    "market_data": "Market-data refresh",
    "live_activation": "Activation of standing instructions (leaving shadow mode)",
}

TRIGGERS = {
    "stale_data": ["market_data", "contribution_proposals"],
    "reconciliation_failed": ["gain_certification", "research_spend", "contribution_proposals", "live_activation"],
    "credentials_compromised": ["live_activation", "contribution_proposals"],
    "limit_exceeded": ["contribution_proposals", "recurring_monitor", "live_activation"],
    "duplicate_transaction": ["contribution_proposals", "gain_certification"],
    "missing_risk_inputs": ["contribution_proposals"],
    "integration_unexpected": ["market_data", "recurring_monitor"],
    "budget_exhausted": ["research_spend"],
}
IMMEDIATE_CATEGORIES = {"unauthorized_activity", "credentials_compromised", "reconciliation_failed",
                        "duplicate_transaction", "security_incident", "limit_exceeded", "owner_action_deadline"}


class Control:
    def __init__(self, store: Store, notifier=None):
        self.s = store
        self.notify = notifier or default_notifier

    # ---- exceptions ---------------------------------------------------------
    def raise_exception(self, category: str, message: str, dedupe_key: str = None, severity: str = None) -> dict:
        severity = severity or ("IMMEDIATE" if category in IMMEDIATE_CATEGORIES else "WEEKLY")
        key = dedupe_key or f"{category}:{message}"
        row = self.s.conn.execute("SELECT * FROM exceptions WHERE dedupe_key=?", (key,)).fetchone()
        if row and row["status"] == "OPEN":
            return {"id": row["id"], "duplicate": True}
        eid = "EXC-" + uuid.uuid4().hex[:8].upper()
        with self.s.tx() as c:
            if row:  # previously resolved; reopen under a fresh key so history is kept
                c.execute("UPDATE exceptions SET dedupe_key=? WHERE id=?", (f"{key}#closed-{row['id']}", row["id"]))
            c.execute("INSERT INTO exceptions (id, ts, severity, category, message, dedupe_key, status) VALUES (?,?,?,?,?,?,?)",
                      (eid, now_iso(), severity, category, message, key, "OPEN"))
            self.s.log("system", "EXCEPTION_RAISED", {"id": eid, "severity": severity, "category": category, "message": message})
        if severity == "IMMEDIATE":
            delivered = self.notify("Genesis Capital Intelligence", f"{category}: {message}")
            with self.s.tx() as c:
                c.execute("UPDATE exceptions SET notified=? WHERE id=?", (1 if delivered else 0, eid))
        return {"id": eid, "duplicate": False, "severity": severity}

    def resolve(self, exc_id: str, resolution: str, owner="owner"):
        with self.s.tx() as c:
            c.execute("UPDATE exceptions SET status='RESOLVED', resolved_ts=?, resolution=? WHERE id=? AND status='OPEN'",
                      (now_iso(), resolution, exc_id))
            self.s.log(owner, "EXCEPTION_RESOLVED", {"id": exc_id, "resolution": resolution})

    def open_exceptions(self, severity=None):
        q = "SELECT * FROM exceptions WHERE status='OPEN'" + (" AND severity=?" if severity else "") + " ORDER BY ts"
        return [dict(r) for r in self.s.conn.execute(q, (severity,) if severity else ())]

    def exceptions_between(self, start, end):
        return [dict(r) for r in self.s.conn.execute("SELECT * FROM exceptions WHERE ts>=? AND ts<? ORDER BY ts", (start, end))]

    # ---- breakers -----------------------------------------------------------
    def trip(self, trigger: str, detail: str) -> list:
        if trigger not in TRIGGERS:
            raise ValueError(f"unknown trigger {trigger}")
        tripped = []
        with self.s.tx() as c:
            for wf in TRIGGERS[trigger]:
                c.execute("INSERT INTO breakers VALUES (?,?,?,?) ON CONFLICT(workflow) DO UPDATE SET state='OPEN', "
                          "reason=excluded.reason, ts=excluded.ts", (wf, "OPEN", f"{trigger}: {detail}", now_iso()))
                tripped.append(wf)
            self.s.log("system", "BREAKER_TRIPPED", {"trigger": trigger, "detail": detail, "workflows": tripped,
                                                     "brokerage_orders_created": 0})
        cat = trigger if trigger in IMMEDIATE_CATEGORIES else "circuit_breaker"
        self.raise_exception(cat, f"{detail} → suspended: {', '.join(tripped)}", dedupe_key=f"breaker:{trigger}:{detail}",
                             severity="IMMEDIATE" if trigger in IMMEDIATE_CATEGORIES else "WEEKLY")
        return tripped

    def reset(self, workflow: str, owner="owner", note=""):
        if owner != "owner":
            raise PermissionError("Only the owner resets a circuit breaker.")
        with self.s.tx() as c:
            c.execute("UPDATE breakers SET state='CLOSED', reason=?, ts=? WHERE workflow=?", (f"reset: {note}", now_iso(), workflow))
            self.s.log(owner, "BREAKER_RESET", {"workflow": workflow, "note": note})

    def is_open(self, workflow: str):
        r = self.s.conn.execute("SELECT * FROM breakers WHERE workflow=? AND state='OPEN'", (workflow,)).fetchone()
        return dict(r) if r else None

    def guard(self, workflow: str):
        b = self.is_open(workflow)
        if b:
            raise BreakerOpen(f"{WORKFLOWS.get(workflow, workflow)} is suspended: {b['reason']}")

    def breakers(self):
        states = {r["workflow"]: dict(r) for r in self.s.conn.execute("SELECT * FROM breakers")}
        return [{"workflow": w, "label": l, **states.get(w, {"state": "CLOSED", "reason": None, "ts": None})}
                for w, l in WORKFLOWS.items()]


class BreakerOpen(Exception):
    pass


def default_notifier(title: str, body: str) -> bool:
    """Windows toast via PowerShell (no third-party packages). Returns False where unavailable;
    the exception still appears as an in-app banner and in the weekly report."""
    if sys.platform != "win32":
        return False
    script = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null;"
              "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
              "$x=$t.GetElementsByTagName('text');$x.Item(0).AppendChild($t.CreateTextNode($env:GCI_T))>$null;"
              "$x.Item(1).AppendChild($t.CreateTextNode($env:GCI_B))>$null;"
              "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Genesis Capital Intelligence').Show("
              "[Windows.UI.Notifications.ToastNotification]::new($t))")
    try:
        import os
        env = {**os.environ, "GCI_T": title[:60], "GCI_B": body[:200]}
        r = subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False
