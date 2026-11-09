# ByrdWay Product Engineering Studio v0.1

**Status:** working local prototype, NOT production-ready autonomous repair/build system. Original source remains unchanged. Seven roles are specified, but only local audit, manual proposal and optional read-only OpenAI specialist review are implemented. No automated 99.9 quality certification.

## Windows 11 installation
1. Install Python 3.11+ from python.org (select Add Python to PATH).
2. Extract this ZIP to a folder on your desktop.
3. Double-click `START_WINDOWS.bat` or run `python app.py` from the extracted folder.
4. Import an existing HTML, ZIP or PDF. Originals are copied to `Documents\\ByrdWay_Product_Studio\\originals` with SHA-256 integrity records.
5. Run **Local Audit**. The report is saved in `Documents\\ByrdWay_Product_Studio\\reports`.
6. To enable AI read-only review, run `pip install openai pymupdf` and set `OPENAI_API_KEY` in your Windows user environment. Do not put your key into any product or share it. The app requests confirmation before each API review. API usage incurs charges.
7. For editable HTML/JS/CSS/TXT/MD/JSON, use **Create Text Repair Proposal**. Proposed copies go into `proposals` and are NOT automatically released. ZIP/PDF repairs require a future source-aware editor.

## Design and security
- Seven roles: Orchestrator, Power Tool Repair, Explainer Repair, Power Tool Builder, Lil Dr. Byrd Builder, Academic Verifier, Release QA.
- No external code execution, browser execution, publication, product listing edits or autonomous payment.
- Read-only AI requests send a maximum of 12,000 characters of product text per review; do not use on confidential source without accepting this transfer.
- Never run an unlimited repair loop. Future automated passes will use explicit iteration and cost limits, independent checks and a stop condition.
- `approve_proposal` exists as a tested engine function but no UI release button is exposed because full regression QA is not yet implemented.
- ZIP imports reject path traversal, symbolic links, excessive file counts and large uncompressed archives.
- AI output is advice, not verified academic truth. No 99.9 score is claimed without a defined test suite and actual pass evidence.
- PDF text extraction requires optional PyMuPDF. Image-only PDFs need approved source/OCR and visual review.

## Next milestones
1. Test against one original ByrdWay Power Tool ZIP/HTML and its known defects.
2. Add source-aware ZIP repair proposals and headless browser interaction/regression tests.
3. Add PDF page comparison and editable source workflows for Anime, Concept Tiles and Lil Dr. Byrd Explainers.
4. Implement independent academic checks and evidence-based 99.9 acceptance scoring.
5. Add blueprint-driven builders for new Power Tools and Lil Dr. Byrd Explainers, with chapter approval.
6. Package signed Windows executable only after Windows testing.

## Run tests
`python -m unittest discover -s tests -v`
