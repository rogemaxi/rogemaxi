# Animation Test Results

## Test 1 — Lumi wing-motion test v1
- File: `lumi/renders/lumi_wing_test_v1.mp4` (1,503,152 bytes, SHA-256 `ab4ed63bad377d61e50c8c91ef0d65668517875a80a9ff534a79f5aaff668c78`)
- Source: Lumi front view from 02-lumi-sheet.webp (provisional). Built by `rig/build_layers.py` + `rig/render_wing_test.py` (Python 3.13, numpy 2.5, Pillow 12.3, ffmpeg 6.1.1).
- Method: 2D cut-out rig. 5 layers. Wings: inverse-mapped non-rigid warp about shoulder pivots — foreshortening (to 50% width) + lift (−4°→+16°), skewed stroke (quick downstroke), tips lag root ~1 frame for follow-through. Body: hover lift on each downstroke + 4 s drift + ±1.6° tilt. Antennae: secondary sway. 1.5 Hz wingbeat, 12 beats, loops.

### Measured (ffprobe / full decode / pixel analysis)
| Check | Target | Result | Status |
|---|---|---|---|
| Frames | 192 | nb_read_frames=192 | PASS |
| Resolution | 1280x720 | 1280x720 | PASS |
| Frame rate | 24 | 24/1 (r & avg) | PASS |
| Duration | 8 s | 8.000000 s | PASS |
| Codec / pix_fmt | MP4 | h264 / yuv420p, faststart | PASS |
| Audio | none | 0 audio streams | PASS |
| Full decode | no errors | 0 ffmpeg errors | PASS |
| Blank frames | 0 | 0 | PASS |
| Fixed camera | no pan/zoom | background corner mean frame-diff = 0.00 | PASS |
| Genuine wing articulation | visible | left-wing silhouette coverage 0.83→0.42→0.78 each beat; wing-region diff 11.7–12.0 vs face 6.8 | PASS |
| Identity / face / eyes | stable | eyes, face, palette unchanged (layers are original pixels) — visual QA contact sheet | PASS (engineer QA) |
| Clipping / tearing | none critical | none seen at full res on f0, f9, contact sheet | PASS (engineer QA) |

### Known limitations (honest)
1. Source panel is only 370x285 px; upscaled ~2x → slightly soft vs. a native render.
2. Faint pale halo on some edges (paper glow baked into the art).
3. Wings deform as flat cards (2.5D); no true 3D wing bend. Forewing/hindwing move as one piece per side.
4. A few tiny static glow sparkles from the source remain beside the right wing and tail.
5. No blink/facial animation (would need new artwork — not authorized).
6. Owner (Gate F) has not judged it. Engineer PASS ≠ approval.
