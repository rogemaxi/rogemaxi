# Lumi & the Night Gardeners — production workspace

- `assets/originals/` — owner reference art (read-only; checksums in `records/MASTER-ASSET-INVENTORY.md`)
- `rig/build_layers.py` — builds reversible rig layers from the Lumi front view
- `rig/render_wing_test.py` — renders the 8 s wing-motion test (1280x720, 24 fps, 192 frames)
- `renders/` — MP4 outputs + QA evidence
- `records/` — the eight SSOI production records

Reproduce (needs Python 3 with numpy + Pillow, and ffmpeg on PATH; works on Windows):

    python lumi/rig/build_layers.py
    python lumi/rig/render_wing_test.py
