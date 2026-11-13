"""Command line: python -m gci <command>

  serve   [--db PATH] [--dataset REAL|SYNTHETIC] [--port N] [--no-browser]
  demo    [--amount 40] [--out DIR]          Phase 19 acceptance demo (synthetic DB)
  verify  [--db PATH] [--dataset ...]        Audit-chain + ledger integrity check
  backup  --db PATH --to FILE
"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import VERSION


def default_db():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "GenesisCapitalIntelligence"
    return base / "gci_real.db"


def main(argv=None):
    p = argparse.ArgumentParser(prog="gci", description=f"Genesis Capital Intelligence {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--db", default=str(default_db()))
    s.add_argument("--dataset", default="REAL", choices=["REAL", "SYNTHETIC"])
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-browser", action="store_true")
    d = sub.add_parser("demo")
    d.add_argument("--amount", default="40")
    d.add_argument("--out", default="demo_output")
    v = sub.add_parser("verify")
    v.add_argument("--db", default=str(default_db()))
    v.add_argument("--dataset", default="REAL", choices=["REAL", "SYNTHETIC"])
    b = sub.add_parser("backup")
    b.add_argument("--db", default=str(default_db()))
    b.add_argument("--to", required=True)
    a = p.parse_args(argv)

    if a.cmd == "serve":
        from .server import serve
        serve(a.db, a.dataset, a.port, not a.no_browser)
    elif a.cmd == "demo":
        from .demo import run
        out = Path(a.out) / f"scenario_{a.amount}"
        r = run(out / "gci_demo.db", a.amount, out)
        for st in r["steps"]:
            print(f"{st['step']:>2} {'PASS' if st['pass'] else 'FAIL'}  {st['title']}")
        print(f"{r['passed']}/{r['total']} passed. Report: {r['report']}")
        sys.exit(0 if r["passed"] == r["total"] else 1)
    elif a.cmd == "verify":
        from .db import Store
        from .ledgers import Ledgers
        st = Store.open(a.db, a.dataset)
        print(json.dumps({"chain": st.verify_chain(), "ledgers": Ledgers(st).reconcile_internal()}, indent=2))
    elif a.cmd == "backup":
        from .db import Store
        from .security import backup
        st = Store.open(a.db, "REAL")
        print(backup(st, a.to))


if __name__ == "__main__":
    main()
