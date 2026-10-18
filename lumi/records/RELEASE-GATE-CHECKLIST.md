# Release Gate Checklist — scope: Lumi wing-motion test v1 (internal)
| Gate | Item | Status |
|---|---|---|
| A | Correct character reference | PASS (02-lumi-sheet front view) |
| A | Original artwork unchanged | PASS (SHA-256 recorded; copies only read) |
| A | No unauthorized redesign | PASS |
| A | Approved story concepts preserved | NOT TESTED (no story content in test) |
| B | Genuine movement / frames / res / runtime | PASS (see ANIMATION-TEST-RESULTS.md) |
| B | Stable identity, no critical artifacts | PASS (engineer QA); minor halo noted |
| C | Audio (all) | NOT TESTED (silent by spec) |
| D | Story (all) | NOT TESTED |
| E | Render, ffprobe, full decode, dims, fps, no blanks | PASS |
| F | Visual design approval | BLOCKED — owner |
| F | Animation approval | BLOCKED — owner review of v1 |
| F | Script / final master / publication | BLOCKED — owner |
Release gate: CLOSED. Nothing published.

# Release Gate Checklist — scope: Episode 01 v0 (240 s)
| Gate | Item | Status |
|---|---|---|
| A | Correct character reference / originals unchanged | PASS |
| A | Approved story concepts preserved | PASS vs SSOI §VII summary; NOT TESTED vs real screenplay (blocked) |
| A | No unauthorized redesign of characters | PASS (Lumi pixels from sheet; env is labelled placeholder) |
| B | Runtime / frames / resolution / identity / no critical artifacts | PASS |
| C | Rights-cleared original music + SFX + closing hum | PASS (synthesized in ep01/audio.py, no samples) |
| C | Narration / consistent voice identity | NOT TESTED (no narration in v0) |
| C | Gentle transitions / appropriate volume / no sleep claims | PASS (−17.7 LUFS, no claims in video) |
| D | First-second problem, cause→effect, earned resolution, peaceful close | PASS (engineer judgment) |
| E | Render, ffprobe, full decode, dims, fps, no blanks/freezes, no missing assets | PASS |
| F | Visual design / script / animation / final master / publication | BLOCKED — owner |
Release gate: CLOSED. Nothing published.
