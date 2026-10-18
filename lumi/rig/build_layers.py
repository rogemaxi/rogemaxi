"""Build reversible rig layers for Lumi from the provisional front-view reference.

Reads the ORIGINAL sheet read-only and writes derivative PNG layers to lumi/rig/layers/.
Pipeline: crop front view -> 2x Lanczos upscale -> background matte -> split into
body / left wing / right wing / left antenna / right antenna -> inpaint wing roots
hidden behind the body so wing motion never reveals holes.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets/originals/02-lumi-sheet.webp"
OUT = ROOT / "rig/layers"
CROP = (15, 630, 385, 905)  # front-view turnaround panel, excludes "FRONT" label
UP = 2  # working scale


def ellipse(h, w, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:h, 0:w]
    return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0


def _box(a, r, axis):
    r = max(int(r), 1)
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
    hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(a, r):
    """Approximate Gaussian blur (3 box passes) on float arrays."""
    a = np.asarray(a, np.float32)
    if r < 1:
        k = np.array([r / 2, 1 - r, r / 2], np.float32)
        for ax in (0, 1):
            a = sum(w * np.roll(a, s, axis=ax) for w, s in zip(k, (-1, 0, 1)))
        return a
    br = max(1, int(round(r * 0.8)))
    for _ in range(3):
        a = _box(_box(a, br, 0), br, 1)
    return a


def inpaint(rgb, known, iters=60):
    """Fill unknown pixels by repeated normalized blur (push-pull diffusion)."""
    rgb = rgb * known[..., None]
    w = known.astype(np.float32)
    out = rgb.copy()
    for i in range(iters):
        r = 2 + i // 10
        num = np.stack([blur(out[..., c] * w, r) for c in range(3)], -1)
        den = blur(w, r)[..., None]
        fill = num / np.maximum(den, 1e-4)
        out = np.where(known[..., None], rgb, fill)
        w = np.maximum(known.astype(np.float32), np.clip(den[..., 0] * 4, 0, 1))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGB").crop(CROP)
    src = src.resize((src.width * UP, src.height * UP), Image.LANCZOS)
    rgb = np.asarray(src).astype(np.float32) / 255
    h, w, _ = rgb.shape

    # --- background matte: fit a linear-gradient paper colour from border pixels
    border = np.zeros((h, w), bool)
    border[:12, :] = border[:, :12] = True
    border[:, -60:] = False  # right edge holds a neighbouring tail; skip
    ys, xs = np.nonzero(border)
    A = np.stack([xs, ys, np.ones_like(xs)], 1).astype(np.float32)
    bg = np.zeros_like(rgb)
    yy, xx = np.mgrid[0:h, 0:w]
    G = np.stack([xx, yy, np.ones_like(xx)], -1).astype(np.float32)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, rgb[ys, xs, c], rcond=None)
        bg[..., c] = G @ coef
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    alpha = np.clip((dist - 0.035) / 0.10, 0, 1)

    # remove stray content: neighbouring turnaround tail on the right edge
    alpha[390:, 650:] = 0

    # cream fur/face sits close to the paper colour, so the colour matte leaves
    # holes: everything not connected to the border background is solid character
    bgmask = Image.fromarray(((alpha < 0.35) * 255).astype(np.uint8)).copy()  # copy: writable
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, h - 1)):
        if bgmask.getpixel(seed) == 255:
            ImageDraw.floodfill(bgmask, seed, 128)
    solid = np.asarray(bgmask) != 128
    solid_core = blur(solid.astype(np.float32), 2) > 0.98  # erode ~2px, keep matte edge
    alpha = np.maximum(alpha, blur(solid_core.astype(np.float32), 1.5))
    alpha = blur(alpha, 0.6)

    # keep only the main silhouette (drops isolated matte speckles)
    comp = Image.fromarray(((alpha > 0.12) * 255).astype(np.uint8)).copy()
    ImageDraw.floodfill(comp, (386, 380), 128)  # seed inside the torso
    main_part = blur((np.asarray(comp) == 128).astype(np.float32), 3) > 0.02
    alpha = alpha * main_part
    alpha = np.clip(alpha, 0, 1) ** 1.25  # tighten the soft paper-glow edge

    # keep original edge colours: un-premultiplying low-alpha pixels turns them grey,
    # and the render background is the same paper/lavender family as the sheet
    fg = rgb

    # --- region masks (working-scale coordinates, hand-placed from inspection)
    head = ellipse(h, w, 388, 258, 122, 102)
    torso = ellipse(h, w, 386, 400, 92, 108)
    arms = ellipse(h, w, 292, 395, 42, 70) | ellipse(h, w, 448, 392, 38, 66)
    legs = (xx > 330) & (xx < 450) & (yy > 440) & (yy < 510)
    tail = (yy > 432) & (xx < 330)
    body = head | torso | arms | legs | tail
    ant = (yy < 175) & (xx > 245) & (xx < 520) & ~head
    ant_l = ant & (xx < 386)
    ant_r = ant & (xx >= 386)
    wing_l = (xx < 386) & ~body & ~ant
    wing_r = (xx >= 386) & ~body & ~ant

    def soft(m, r=1.2):
        return blur(m.astype(np.float32), r)

    layers = {
        "body": soft(body) * alpha,
        "antenna_l": soft(ant_l) * alpha,
        "antenna_r": soft(ant_r) * alpha,
    }
    for name, m in (("wing_l", wing_l), ("wing_r", wing_r)):
        # wing extends under the body: inpaint colour and alpha into the hidden root
        side = (xx < 386) if name == "wing_l" else (xx >= 386)
        root = side & (head | torso | arms) & (yy > 150) & (yy < 470)
        known = m & (alpha > 0.5)
        filled = inpaint(fg, known)
        a = soft(m) * alpha
        near = blur(known.astype(np.float32), 10) * 2.0
        a_fill = np.where(root, np.clip(near, 0, 1), 0)
        a = np.maximum(a, a_fill)
        layers[name] = (filled, a)

    def save(name, col, a):
        rgba = np.dstack([col, a])
        Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")

    for name, v in layers.items():
        if isinstance(v, tuple):
            save(name, *v)
        else:
            save(name, fg, v)
    save("full_matte", fg, alpha)
    Image.fromarray((bg * 255).astype(np.uint8)).save(OUT / "paper_bg.png")
    print("layers written:", sorted(p.name for p in OUT.glob("*.png")), "size", (w, h))


if __name__ == "__main__":
    main()
