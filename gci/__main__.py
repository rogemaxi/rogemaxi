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
    ac = sub.add_parser("acceptance", help="Run all SSOI acceptance demos on synthetic databases")
    ac.add_argument("--out", default="acceptance_output")
    j = sub.add_parser("run-jobs", help="Run due daily/weekly jobs once (for Windows Task Scheduler)")
    j.add_argument("--db", default=str(default_db()))
    j.add_argument("--dataset", default="REAL", choices=["REAL", "SYNTHETIC"])
    i = sub.add_parser("install-schedule", help="Register a daily Windows scheduled task that runs run-jobs")
    i.add_argument("--db", default=str(default_db()))
    i.add_argument("--time", default="06:40")
    i.add_argument("--remove", action="store_true")
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
    elif a.cmd == "acceptance":
        from .acceptance import run_all
        import shutil
        if Path(a.out).exists():
            shutil.rmtree(a.out)
        r = run_all(a.out)
        for k in ("investment_40", "investment_10000", "operations"):
            print(f"{k}: {r[k]['passed']}/{r[k]['total']}")
            for st in r[k]["steps"]:
                if not st["pass"]:
                    print(f"   FAIL {st['step']} {st['title']}: {str(st['evidence'])[:300]}")
        print("ALL PASSED" if r["all_passed"] else "SOME FAILED")
        sys.exit(0 if r["all_passed"] else 1)
    elif a.cmd == "run-jobs":
        from .db import Store
        from .ops import Scheduler
        st = Store.open(a.db, a.dataset)
        for r in Scheduler(st, Path(a.db).parent / "reports").run_due():
            print(f"{r['job']:<22} {r['period']:<12} {r['status']}")
    elif a.cmd == "install-schedule":
        import subprocess
        name = "GenesisCapitalIntelligence-DailyJobs"
        if sys.platform != "win32":
            print("Windows only. On this OS use cron to run: python -m gci run-jobs"); sys.exit(2)
        if a.remove:
            sys.exit(subprocess.run(["schtasks", "/Delete", "/TN", name, "/F"]).returncode)
        here = str(Path(__file__).resolve().parent.parent)
        cmd = f'cmd /c cd /d "{here}" && "{sys.executable}" -m gci run-jobs --db "{a.db}"'
        r = subprocess.run(["schtasks", "/Create", "/SC", "DAILY", "/TN", name, "/TR", cmd, "/ST", a.time, "/F"])
        print("Registered." if r.returncode == 0 else "schtasks failed."); sys.exit(r.returncode)
    elif a.cmd == "backup":
        from .db import Store
        from .security import backup
        st = Store.open(a.db, "REAL")
        print(backup(st, a.to))


if __name__ == "__main__":
    main()
