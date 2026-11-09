# Owner Quick Start — ByrdWay Product Engineering Studio v0.4.1

## Install once (about 10 minutes)
**Option A — ready-made program (no Python):**
1. On GitHub: **rogemaxi/rogemaxi → Releases → ByrdWay Product Engineering Studio v0.4.1** →
   download **ByrdWayStudio_v0.4.1_Windows_exe.zip**. (It is a *draft* release until you click Publish; only you can see it.)
2. Right-click the ZIP → **Properties** → tick **Unblock** → OK → right-click → **Extract All** → `C:\ByrdWay`.
3. Download **ByrdWay_Product_Studio_v0.4.1_source.zip** too, extract it, and double-click
   `install_windows.bat` once — it installs the Chromium browser engine used for testing (answer **Y**).
4. Open `C:\ByrdWay\ByrdWayStudio\ByrdWayStudio.exe`. First time only: *More info → Run anyway* (unsigned program).

**Option B — from source:** extract the source ZIP, install Python 3.12 (tick *Add to PATH*), run
`install_windows.bat`, then `START_WINDOWS.bat`.

Check: **Help → About** shows **v0.4.1**. **Help → Run self-test** should say **PASSED**.

## Repair an existing product (tab 1 → tab 2)
1. **① Import Product…** — pick a Power Tool ZIP/HTML or an Explainer/Concept Tiles PDF. A locked copy is made;
   your file is never changed.
2. **② Diagnose (no changes)** — a report opens in your browser: what is wrong, and the exact correction proposed.
3. **③ Repair a Copy & Verify** — the corrections are applied to a copy and independently re-tested. The repair
   report opens: each defect shows **VERIFIED**, **NOT AUTO-FIXABLE**, etc., with before/after pictures.
4. Tab 2 shows a coloured **NEXT STEP** line. If it says QA PASSED: **APPROVE for release…** (type your name),
   then **Export Approved…**. Nothing is ever uploaded — you publish to TpT yourself.
   - *Some questions cannot be checked automatically*: check them yourself, then **Attest Unverifiable Item…** → `ALL`.
   - *BLOCKED*: the report lists what needs a person. The release gate cannot be overridden.

## Build a new product (tab 3)
1. **Step 1** — choose *Power Tool* or *Lil Dr. Byrd Explainer*.
2. **Step 3 first** — **Register approved page template…** (Power Tools) or **Register Lil Dr. Byrd image…**
   (Explainers). The checklist shows ✖ until they are registered. The Studio never draws a substitute mascot.
3. **Step 2** — **Create new blueprint (form)…**: type your approved content, one item per line, using `::` between
   parts (examples are shown above each box). **Check for errors**, then **Save & create build**.
   *Save draft* lets you finish later (**Open saved blueprint / draft…**). The *sample* is only a format example and
   is always blocked at release.
4. **Step 4** — **Build next unit** → **Open unit to review** → **Approve unit…** (or **Reject unit…** and
   **Edit blueprint (new version)…**). Repeat for each module/chapter.
5. **Assemble, verify & send to Jobs** → finish in tab 2 exactly like a repair.

## Money (tab 4)
AI is **DISABLED** until you store an OpenAI key *and* set funding above the reserve. Even then every paid call asks
first and shows its maximum cost. Everything else works offline for free.

## Safety net (tab 5) and problems (tab 6)
**Create verified backup now** before big work. Every error is also written to tab 6. If something fails, send
tab 6's latest lines and `reports\selftest_report.json`.
