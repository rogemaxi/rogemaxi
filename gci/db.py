"""SQLite storage with a versioned schema and an append-only, hash-chained event log.

Each database file belongs to exactly one dataset: REAL or SYNTHETIC. Synthetic
(test/demo) records can never be written into a REAL database and vice versa.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import SCHEMA_VERSION, VERSION

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, actor TEXT NOT NULL, kind TEXT NOT NULL,
  payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
  BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
  BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;

CREATE TABLE IF NOT EXISTS authorizations (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, owner TEXT NOT NULL, action TEXT NOT NULL,
  amount TEXT, details TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('APPROVED','CONSUMED','REVOKED')),
  consumed_ts TEXT);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ledger TEXT NOT NULL CHECK (ledger IN ('A','B','C')),
  ts TEXT NOT NULL, kind TEXT NOT NULL, amount TEXT NOT NULL,
  memo TEXT NOT NULL DEFAULT '', authorization_id TEXT REFERENCES authorizations(id),
  transfer_id TEXT, external_id TEXT UNIQUE, ref TEXT);
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger_entries
  BEGIN SELECT RAISE(ABORT, 'ledger entries are immutable; post a correcting entry'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger_entries
  BEGIN SELECT RAISE(ABORT, 'ledger entries are immutable; post a correcting entry'); END;

CREATE TABLE IF NOT EXISTS lots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, acquired_ts TEXT NOT NULL,
  qty TEXT NOT NULL, remaining_qty TEXT NOT NULL, cost_total TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
  ref TEXT);
CREATE TABLE IF NOT EXISTS realized (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, symbol TEXT NOT NULL, qty TEXT NOT NULL,
  proceeds TEXT NOT NULL, cost_basis TEXT NOT NULL, fees TEXT NOT NULL, gain TEXT NOT NULL, lot_id INTEGER, ref TEXT);
CREATE TABLE IF NOT EXISTS prices (
  symbol TEXT NOT NULL, as_of TEXT NOT NULL, price TEXT NOT NULL, currency TEXT NOT NULL,
  source TEXT NOT NULL, retrieved_at TEXT NOT NULL, PRIMARY KEY (symbol, as_of, source));

CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY, created_ts TEXT NOT NULL, record TEXT NOT NULL, review_date TEXT NOT NULL,
  status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decision_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT NOT NULL REFERENCES decisions(id),
  ts TEXT NOT NULL, observed TEXT NOT NULL, triggered TEXT NOT NULL, outcome TEXT, lessons TEXT);

CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, decision_id TEXT, created_ts TEXT NOT NULL, card TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED','DEFERRED')),
  decided_ts TEXT, decided_by TEXT, note TEXT);

CREATE TABLE IF NOT EXISTS research_jobs (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, task_type TEXT NOT NULL, agents TEXT NOT NULL,
  status TEXT NOT NULL, cost TEXT NOT NULL, duration_ms INTEGER NOT NULL, tokens INTEGER NOT NULL DEFAULT 0,
  decision_id TEXT, output TEXT);

CREATE TABLE IF NOT EXISTS gain_certifications (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  record TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('CERTIFIED','REJECTED','ALLOCATED')));

CREATE TABLE IF NOT EXISTS contribution_proposals (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, record TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PROPOSED','CONFIRMED','DECLINED')));

CREATE TABLE IF NOT EXISTS imports (
  row_hash TEXT PRIMARY KEY, ts TEXT NOT NULL, source TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ips_versions (
  version INTEGER PRIMARY KEY, created_ts TEXT NOT NULL, policy TEXT NOT NULL, policy_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('DRAFT','SIGNED','SUPERSEDED')), signed_ts TEXT, signed_by TEXT);

CREATE TABLE IF NOT EXISTS bridge_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL, amount TEXT NOT NULL,
  source TEXT NOT NULL, external_id TEXT UNIQUE, effective_date TEXT, memo TEXT NOT NULL DEFAULT '', record TEXT);
CREATE TRIGGER IF NOT EXISTS bridge_no_update BEFORE UPDATE ON bridge_entries
  BEGIN SELECT RAISE(ABORT, 'bridge entries are immutable'); END;
CREATE TABLE IF NOT EXISTS bridge_proposals (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, record TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PROPOSED','AUTHORIZED','DEPOSIT_CONFIRMED','DECLINED','EXPIRED')),
  authorization_id TEXT, deposit_ref TEXT UNIQUE);

CREATE TABLE IF NOT EXISTS job_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT NOT NULL, period_key TEXT NOT NULL, started_ts TEXT NOT NULL,
  heartbeat_ts TEXT NOT NULL, finished_ts TEXT, status TEXT NOT NULL CHECK (status IN ('RUNNING','DONE','FAILED','INTERRUPTED','SKIPPED')),
  result TEXT, attempt INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX IF NOT EXISTS job_runs_done ON job_runs(job, period_key) WHERE status='DONE';

CREATE TABLE IF NOT EXISTS exceptions (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, severity TEXT NOT NULL CHECK (severity IN ('IMMEDIATE','WEEKLY')),
  category TEXT NOT NULL, message TEXT NOT NULL, dedupe_key TEXT UNIQUE, status TEXT NOT NULL CHECK (status IN ('OPEN','RESOLVED')),
  resolved_ts TEXT, resolution TEXT, notified INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS breakers (
  workflow TEXT PRIMARY KEY, state TEXT NOT NULL CHECK (state IN ('CLOSED','OPEN')), reason TEXT, ts TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS valuation_snapshots (
  as_of TEXT PRIMARY KEY, record TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS weekly_reports (
  week_start TEXT PRIMARY KEY, created_ts TEXT NOT NULL, record TEXT NOT NULL, markdown TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS security_incidents (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, provider TEXT NOT NULL, location TEXT NOT NULL, finding TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('OPEN','ROTATED_CONFIRMED','FALSE_POSITIVE')), resolved_ts TEXT, note TEXT);

CREATE TABLE IF NOT EXISTS shadow_checks (
  item TEXT PRIMARY KEY, status TEXT NOT NULL CHECK (status IN ('PENDING','PASSED','FAILED')), ts TEXT, evidence TEXT);
"""

GENESIS_HASH = "0" * 64


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DatasetMismatch(Exception):
    pass


class Store:
    """One open database. Use `Store.open(path, dataset)`."""

    def __init__(self, conn: sqlite3.Connection, path: str):
        self.conn = conn
        self.path = path

    @classmethod
    def open(cls, path, dataset: str = "REAL") -> "Store":
        if dataset not in ("REAL", "SYNTHETIC"):
            raise ValueError("dataset must be REAL or SYNTHETIC")
        path = str(path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")  # UI and background jobs use separate connections
        conn.execute("PRAGMA journal_mode=WAL" if path != ":memory:" else "PRAGMA journal_mode=MEMORY")
        conn.executescript(SCHEMA)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ledger_entries)")]
        if "effective_date" not in cols:  # schema v2: transaction date separate from posting time
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN effective_date TEXT")
        store = cls(conn, path)
        existing = store.meta("dataset")
        if existing is None:
            with store.tx():
                conn.execute("INSERT INTO meta VALUES ('dataset', ?)", (dataset,))
                conn.execute("INSERT INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
                conn.execute("INSERT INTO meta VALUES ('created_by_version', ?)", (VERSION,))
            store.log("system", "DB_CREATED", {"dataset": dataset, "schema_version": SCHEMA_VERSION})
        elif existing == dataset and int(store.meta("schema_version") or 1) < SCHEMA_VERSION:
            old = store.meta("schema_version")
            with store.tx():
                conn.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(SCHEMA_VERSION),))
            store.log("system", "SCHEMA_MIGRATED", {"from": old, "to": SCHEMA_VERSION})
        if existing is not None and existing != dataset:
            conn.close()
            raise DatasetMismatch(f"{path} holds {existing} records; refusing to open it as {dataset}")
        return store

    @property
    def dataset(self) -> str:
        return self.meta("dataset")

    def meta(self, key):
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_setting(self, key, value, actor="owner"):
        with self.tx():
            self.conn.execute("INSERT INTO settings VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                              (key, json.dumps(value)))
            self.log(actor, "SETTING_CHANGED", {"key": key, "value": value})

    class _Tx:
        def __init__(self, conn):
            self.conn = conn
            self.outer = False

        def __enter__(self):
            self.outer = not self.conn.in_transaction
            if self.outer:
                self.conn.execute("BEGIN IMMEDIATE")
            return self.conn

        def __exit__(self, exc_type, exc, tb):
            if self.outer:
                self.conn.execute("ROLLBACK" if exc_type else "COMMIT")
            return False

    def tx(self):
        return Store._Tx(self.conn)

    def log(self, actor: str, kind: str, payload: dict) -> str:
        with self.tx():
            row = self.conn.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            prev = row["hash"] if row else GENESIS_HASH
            ts = now_iso()
            body = json.dumps(payload, sort_keys=True, default=str)
            digest = hashlib.sha256(f"{prev}|{ts}|{actor}|{kind}|{body}".encode()).hexdigest()
            self.conn.execute("INSERT INTO events (ts, actor, kind, payload, prev_hash, hash) VALUES (?,?,?,?,?,?)",
                              (ts, actor, kind, body, prev, digest))
            return digest

    def verify_chain(self) -> dict:
        prev = GENESIS_HASH
        count = 0
        for r in self.conn.execute("SELECT * FROM events ORDER BY seq"):
            expect = hashlib.sha256(f"{prev}|{r['ts']}|{r['actor']}|{r['kind']}|{r['payload']}".encode()).hexdigest()
            if r["prev_hash"] != prev or r["hash"] != expect:
                return {"ok": False, "broken_at_seq": r["seq"], "events_checked": count}
            prev = r["hash"]
            count += 1
        return {"ok": True, "events_checked": count, "head": prev}

    def events(self, limit=200, kind=None):
        q = "SELECT * FROM events" + (" WHERE kind=?" if kind else "") + " ORDER BY seq DESC LIMIT ?"
        args = (kind, limit) if kind else (limit,)
        return [dict(r) | {"payload": json.loads(r["payload"])} for r in self.conn.execute(q, args)]

    def close(self):
        self.conn.close()
