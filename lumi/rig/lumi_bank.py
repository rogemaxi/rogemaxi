"""Pre-render Lumi sprite bank for episode rendering (reversible derivatives).

* flap_XX.png  -- 32 wing-phase poses of the full front-view rig (same warp as the
  verified wing test), edges colour-decontaminated so Lumi sits on a night scene
* glow_XX.png  -- matching soft mint glow (Lumi is luminous per the locked concept)
* expr_<name>.png -- expression panels cropped unchanged from the sheet
Run after rig/build_layers.py. Output: work/bank/ (regenerable, not committed).
"""
from pathlib import Path

import numpy as np
from PIL import Image

from build_layers import blur
from render_wing_test import (ANT_BASE_L, ANT_BASE_R, PIVOT_L, PIVOT_R, load,
                              over, rotate_layer, stroke, warp_wing)

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "work/bank"
PHASES = 32
HAND = (388, 428)  # forelimb contact point in rig space (between the paws)
EXPR = {  # sheet-space boxes of the expression panels (no labels)
    "joy": (22, 975, 252, 1232),
    "concern": (262, 975, 500, 1232),
    "sleepy": (492, 975, 712, 1232),
}


def decontaminate(rgba):
    """Replace paper-tinted edge colour with nearby interior colour."""
    a = rgba[..., 3]
    known = (a > 0.9).astype(np.float32)
    num = np.stack([blur(rgba[..., c] * known, 4) for c in range(3)], -1)
    den = blur(known, 4)[..., None]
    fill = num / np.maximum(den, 1e-4)
    edge = (a < 0.9) & (den[..., 0] > 0.02)
    out = rgba.copy()
    out[edge, :3] = fill[edge]
    return out


def main():
    BANK.mkdir(parents=True, exist_ok=True)
    wl, wr = load("wing_l"), load("wing_r")
    body, al, ar = load("body"), load("antenna_l"), load("antenna_r")
    h, w, _ = body.shape
    for k in range(PHASES):
        phase = k / PHASES
        ch = np.zeros((h, w, 4), np.float32)
        ch = over(ch, warp_wing(wl, PIVOT_L, -1, phase)[0])
        ch = over(ch, warp_wing(wr, PIVOT_R, +1, phase)[0])
        sway = 1.5 * float(stroke(phase))
        ch = over(ch, rotate_layer(al, sway, ANT_BASE_L))
        ch = over(ch, rotate_layer(ar, -sway, ANT_BASE_R))
        ch = over(ch, body)
        ch = decontaminate(ch)
        Image.fromarray((np.clip(ch, 0, 1) * 255).astype(np.uint8), "RGBA").save(BANK / f"flap_{k:02d}.png")
        g = np.clip(blur(ch[..., 3], 14) * 0.55, 0, 1)
        glow = np.dstack([np.full_like(g, 0.62), np.full_like(g, 0.95), np.full_like(g, 0.85), g])
        Image.fromarray((glow * 255).astype(np.uint8), "RGBA").save(BANK / f"glow_{k:02d}.png")
    sheet = Image.open(ROOT / "assets/originals/02-lumi-sheet.webp").convert("RGB")
    for name, box in EXPR.items():
        sheet.crop(box).save(BANK / f"expr_{name}.png")
    print("bank written:", len(list(BANK.glob("*.png"))), "files")


if __name__ == "__main__":
    main()
