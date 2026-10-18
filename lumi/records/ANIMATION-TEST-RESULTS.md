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

## Test 2 — Episode 01 v0, full 240 s ("A Little Space to Grow")
Owner instruction 2026-10-18: "this must be 240s video" (overrides the SSOI gate that held full-episode work until the contact test; contact animation is included as Shot 07).
- File: `lumi/renders/ep01_v0_a_little_space_to_grow.mp4` (24,436,748 bytes, SHA-256 `5ab277fd7e0c27de8252ee93f989da10d15b1ac2ba286dca7b4bbd4e40c3c2fe`)
- Built by: `rig/lumi_bank.py` → `ep01/env.py` → `ep01/render.py` (timeline `ep01/timeline.py`) + `ep01/audio.py`, muxed with ffmpeg loudnorm. Render time ≈ 46 min on 4 CPU cores.

| Check | Target | Result | Status |
|---|---|---|---|
| Duration | 240 s | 240.000000 s (video, audio, container) | PASS |
| Frames | 5,760 | nb_read_frames=5760 | PASS |
| Resolution / fps | 1280x720 / 24 | 1280x720 / 24/1 | PASS |
| Shots | 15 | 15 (contact sheet renders/qa/ep01_v0_shot_contact_sheet.png) | PASS |
| Full decode | 0 errors | 0 | PASS |
| Black frames | only the planned end fade | black 238.83–239.96 s only | PASS |
| Frozen stretches ≥2 s | none | none (freezedetect n=0.0005) | PASS |
| Audio | stereo, original | AAC 48 kHz stereo; −17.7 LUFS integrated; peak −1.2 dBFS | PASS (peak 0.8 dB over the −2 dB target; not clipping) |
| Problem visible frame 0 | yes | crowded seedlings under leaf at t=0 | PASS |
| Shot 07 contact: approach, grasp, lift, carry, place, release, stays | all | renders/qa/ep01_v0_shot07_contact_sequence.png | PASS (engineer QA) |
| Continuity (pots, leaf, Lumi) | no jumps | max per-frame move 10.1 world units within shots | PASS |
| Flashing | none | fireflies pulse with a 7 s period; no strobing | PASS |

### Known limitations (v0)
1. Built from SSOI §VII summary, NOT the approved screenplay (unavailable) — see EP01-V0-SHOT-LIST.md.
2. Environment, pots, seedlings and leaf are procedural placeholder art, simpler than the character art.
3. Lumi exists only in the front view: she can't turn or show profile. Close-ups are the three sheet expressions (static art, gentle bob).
4. No narration/voice (no voice talent or TTS available). Story is visual + music/SFX.
5. Contact is 2D layering (paws over the leaf/pot edge); no true grip deformation.
6. Owner has not reviewed. Engineer PASS ≠ approval.
