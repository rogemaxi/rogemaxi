# Owner Acceptance Checklist (do this on your Windows PC)

GCI is **not** declared release-ready until you complete steps 1–6 on a clean Windows machine.

1. Install Python 3.11+ from python.org and tick **"Add python.exe to PATH"** (the `py` launcher is included).
2. Extract the ZIP. Check the hash in PowerShell: `Get-FileHash .\GenesisCapitalIntelligence-*.zip -Algorithm SHA256`. It must match the `.sha256` file.
3. Double-click **`Run Acceptance Demo.bat`**. Expect `ALL PASSED` (investment $40 and $10,000, plus operations) and `OK` for the tests.
4. Double-click **`Launch GCI.bat`**. The browser opens at `http://127.0.0.1:8765/`. The header must show **Data: REAL**, **Brokerage: NOT CONNECTED**, and **Orders: disabled by design**.
5. Go to Settings and click **"Test: attempt to place an order"**. It must be refused.
6. Go to Global Markets and click **"Try live Treasury refresh"**. Note whether it returns a live rate or an honest failure.
7. Go to Settings and set your horizon, emergency-fund status, and tax rate. Decide whether to approve the 30% research share.
8. Export your J.P. Morgan activity CSV and import it (Brokerage Integration), then reconcile it against the positions CSV.
9. Security & Audit: rotate the 4 exposed credentials at Stripe, Printful, Printify and Google Cloud, then confirm each one.
10. Approvals & Policies: edit the Investment Policy (account owner, ceiling, legs, max loss, emergency fund confirmed), save the draft, then sign it once.
11. Brokerage Integration: follow the generated Autoinvest steps in the Chase app.
12. Install daily background jobs: `py -3 -m gci install-schedule`. Leave GCI in shadow mode for 7 days, then use Settings → Leave shadow mode.

**Rollback:** GCI never edits your previous install. Delete the extracted folder and re-extract the previous ZIP. Your data lives in `%LOCALAPPDATA%\GenesisCapitalIntelligence\gci_real.db`. To restore from a backup: `py -3 -m gci verify --db <backup file>`, then copy the backup into place.
