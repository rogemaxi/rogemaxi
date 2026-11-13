# Owner Quick Start — ByrdWay Product Engineering Studio v0.5.0

## Install once (about 10 minutes, no Python needed)
1. GitHub → **rogemaxi/rogemaxi → Releases → ByrdWay Product Engineering Studio v0.5.0** (a *draft* only you can
   see) → download **ByrdWayStudio_v0.5.0_Windows_exe.zip** and **VERIFICATION_MANIFEST.txt**.
2. Optional integrity check: PowerShell `Get-FileHash .\ByrdWayStudio_v0.5.0_Windows_exe.zip` must equal the line in
   VERIFICATION_MANIFEST.txt.
3. Right-click the ZIP → **Properties** → tick **Unblock** → OK → right-click → **Extract All** → `C:\ByrdWay`.
4. Open `C:\ByrdWay\ByrdWayStudio\ByrdWayStudio.exe` (first time: *More info → Run anyway*; the program is unsigned).
5. **Help → Install browser engine** (one-time ~150 MB download; needed to test Power Tools).
6. **Help → Run self-test** → must say **PASSED**. **Help → About** shows **v0.5.0**.

(Source alternative: extract `ByrdWay_Product_Studio_v0.5.0_source.zip`, install Python 3.12, run
`install_windows.bat`, then `START_WINDOWS.bat`.)

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
   - *Flattened PDF (Anime Explainer)*: **Review Image Findings…** → confirm or dismiss each finding (a picture of
     each is shown) → **Export Correction Sheet…** → fix in your Canva/PPTX source → import the new PDF.

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

## New in the Byrd Powerhouse build (2026-11-13)
- **Tab 3 → Build next unit with QA loop**: Builder → independent Build QA (answers, Reader checks, code, browser and
  the 9-point Mastery Experience standard) → automatic repair of wrong answers → rebuild → Chief Judge. A unit passes
  only at 100 % of mandatory checks and still waits for your **Approve unit…**.
- **Tab 3 → Build Concept Tiles (approved ByrdWay format)…**: choose the approved table of contents (.md), the tile
  content (.json), the course name and your approved Lil Dr. Byrd image. The PDF is built in the measured ByrdWay
  layout (landscape, sticky-note cards, Kalam handwriting) and checked page by page against that design, the table of
  contents, the answer keys and every answer. The result and QA report are saved in your workspace (`concept_tiles\`).
- **Tab 7 Byrd Powerhouse**: all 12 engineering agents and 10 Revenue & Media roles with honest status.
- **Tab 8 Revenue & Media**: **Run today's sales workflow** (drafts only + your scaling-roadmap stage, the one
  bottleneck and today's 10 prioritized actions), **Import TpT sales report (CSV)…**, **Set Week 1 start date…**,
  **Load product catalog (JSON)…**, **Revenue dashboard**, **Strategy library** (every method with its source).
  Nothing is sent, published, priced or paid by the app.

## Lil Dr. Byrd commercials: video platform + Blotato publishing (tab 8)
The Studio does not make the video itself. It writes the brief, sends it to a video platform, reviews the result and
publishes through Blotato after you approve.
1. **Video platform & Blotato setup…**: register the approved Lil Dr. Byrd image and voice once, paste your Blotato API key
   (Blotato > Settings > API; stored in Windows Credential Manager) and see which of Facebook / Instagram / TikTok /
   YouTube are connected in Blotato (connect missing ones at my.blotato.com/accounts).
2. **Lil Dr. Byrd commercial brief…**: choose a spec JSON (`product`, `lines` with hook / problem / demo / cta, `duration`
   30-45) and a platform: `blotato` (automatic), `google_flow` or `adobe_firefly` (the Studio writes SHOT_LIST.txt you paste
   into Flow / Firefly with the Lil Dr. Byrd image).
3. **Generate on Blotato…** (asks before spending Blotato credits) or render in Flow / Firefly yourself.
4. **Review platform video…**: the Commercial Reviewer watches the whole MP4, scores 8 categories and checks the voice. Choose
   your Lil Dr. Byrd recording to replace any AI voice.
5. **Publish via Blotato…**: only after Reviewer PASS (or, for a first post, everything passing except the audience-data
   categories) and your typed approval. Each platform is reported separately with its live link.
The Windows ZIP includes ffmpeg (folder `ffmpeg`, GPL license file inside) for the Reviewer.
