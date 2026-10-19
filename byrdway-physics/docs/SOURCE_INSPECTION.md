# Phase 1 — Source Inspection

Inspected 19 October 2026.

## A. ByrdWay Algebra 2 + Honors Power Tool v2 (reference architecture)

- **File:** `Byrdway_Algebra_2_Plus_Honors_v2.html`, 478 KB, single file, about 5,900 lines. The owner uploaded it to this session; it is not committed to this repository and was **never modified**.
- **Structure:** one `AREAS` data array (10 learning areas), followed by rendering, SVG diagram, answer-checking (`TEST_KEYS`, 106 keys) and generator code.
- **Patterns preserved in Physics:**
  - Cheat Sheet, Blueprint (decision engine), Flashcards, Test Me (tiered), Honors Layer, Interactive (Khan links and tutor prompt), Quick Bridges and pain points.
  - Answer checking, a scoreboard, progress saved in localStorage, and a back-matter formula finder.
- **Brand tokens reused:** `#0f172a` / `#0b1220` midnight, `#fbbf24` gold, `#7dd3fc` blue, `#4ade80` green, `#f87171` red; Segoe UI typography; pill buttons; card layout.
- **Health check:** all 60 area tabs rendered in headless Chromium with 0 JavaScript errors. There were 106/106 answer keys.
- **Gaps observed:**
  - Standards alignment is present in only 1 of 10 areas.
  - The Honors tier is thin (2 items per area).
  - Content and code share one file.

  The Physics architecture addresses all three: a standards crosswalk, a separate Honors pathway, and modular sources.

## B. Physics Master Table of Contents — Blueprint v1.0

- The owner's Google Drive has **no separate "Blueprint v1.0" document** (searched by title and full text).
- The section list comes from the **Master Table** sheet of `ByrdWay_Physics_Video_Link_Library.xlsx`. That workbook is labeled "Companion to: Master Table of Contents | Power Tool Blueprint v1.0".
- It contains:
  - all 20 units and 170 sections, with pathway tags (Core 141, Honors 19, Advanced 10);
  - the 20 signature labs;
  - 12 orientation items, 10 learning engines, 17 assessment layers, and 13 reference resources.
- **Owner action (non-blocking):** if Blueprint v1.0 contains material beyond the section list, such as per-section objectives, please supply it so it can be reconciled.

## C. Video Link Companion

- Two versions were found in Drive. The newest is `ByrdWay_Physics_Video_Link_Companion.docx`, 73 KB, 19 Oct 2026 17:17. The structured `.xlsx` library carries the same rows plus search keywords.
- The import counts are asserted by `tools/import_library.py`: **20 units, 170 sections, 242 rows, 726 topic-scoped search links**, plus 7 course-anchor links.
- Every link is a search-results URL, and the app says so wherever links appear.
- The originals are kept in `sources/` so the build is reproducible.

## D. Directive requirements → see `docs/TRACEABILITY.md`
