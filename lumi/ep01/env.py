"""Procedural PLACEHOLDER environment art for Episode 01 v0 (pending approved art).

World space is 1920x1080 units; the garden bed top is at GROUND_Y.
Everything is drawn at supersampled resolution and cached in work/env/.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "work/env"
WORLD_W, WORLD_H = 1920, 1080
GROUND_Y = 790  # back edge of the bed top plane
BED_FRONT_Y = 905  # front lip of the bed
POT_BASE_Y = 852  # pots and props stand here
BG_SCALE = 2  # background painted at 2x world resolution
POT_W, POT_H = 124, 104  # world units


def _noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // cell + 2), max(2, w // cell + 2))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255


def _glow(canvas, x, y, r, color, strength):
    """Additive soft radial glow into a float RGB canvas."""
    h, w, _ = canvas.shape
    x0, x1 = max(0, int(x - 3 * r)), min(w, int(x + 3 * r))
    y0, y1 = max(0, int(y - 3 * r)), min(h, int(y + 3 * r))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = ((xx - x) ** 2 + (yy - y) ** 2) / (r * r)
    g = np.exp(-d2)[..., None] * strength
    canvas[y0:y1, x0:x1] += g * np.array(color, np.float32)


def paint_background():
    """Night garden: sky, moon, distant treehouse ridge, foliage, glowing bells, garden bed."""
    W, H = WORLD_W * BG_SCALE, WORLD_H * BG_SCALE
    S = BG_SCALE
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = yy / H
    top, mid, hor = np.array([0.07, 0.08, 0.22]), np.array([0.17, 0.16, 0.38]), np.array([0.40, 0.34, 0.55])
    sky = np.where((t < 0.45)[..., None], top + (mid - top) * (t / 0.45)[..., None],
                   mid + (hor - mid) * np.clip((t - 0.45) / 0.3, 0, 1)[..., None])
    sky = sky + (_noise(W, H, 90, 1)[..., None] - 0.5) * 0.03
    rng = np.random.default_rng(7)
    for _ in range(260):  # static stars, upper sky
        sx, sy = rng.random() * W, rng.random() * H * 0.5
        _glow(sky, sx, sy, rng.uniform(1.2, 2.6) * S, (0.9, 0.9, 1.0), rng.uniform(0.15, 0.6))
    mx, my = 1500 * S, 210 * S  # moon
    _glow(sky, mx, my, 260 * S, (0.55, 0.52, 0.65), 0.35)
    d = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
    moon = np.clip((88 * S - d) / (2 * S), 0, 1)[..., None]
    crater = 0.93 + 0.07 * _noise(W, H, 40, 3)[..., None]
    sky = sky * (1 - moon) + np.array([0.97, 0.95, 0.86]) * crater * moon

    def ridge(base, amp, freq, seed, color, blur_r, lights=0):
        nonlocal sky
        r = np.random.default_rng(seed)
        ph = r.random(4) * 6.28
        x = np.arange(W) / S
        yline = base + amp * (0.5 * np.sin(x * freq + ph[0]) + 0.3 * np.sin(x * freq * 2.3 + ph[1])
                              + 0.2 * np.sin(x * freq * 5.1 + ph[2]))
        mask = (yy / S > yline[None, :]).astype(np.float32)
        m = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(blur_r * S))).astype(np.float32)[..., None] / 255
        sky = sky * (1 - m) + np.array(color) * m
        for _ in range(lights):  # treehouse windows
            lx = r.uniform(80, WORLD_W - 80)
            ly = float(np.interp(lx, x, yline)) + r.uniform(12, 60)
            _glow(sky, lx * S, ly * S, 6 * S, (1.0, 0.72, 0.38), 0.9)
            _glow(sky, lx * S, ly * S, 22 * S, (1.0, 0.6, 0.3), 0.18)

    ridge(560, 70, 0.006, 11, (0.16, 0.15, 0.33), 3, lights=14)
    ridge(650, 55, 0.009, 12, (0.11, 0.13, 0.26), 2, lights=8)
    ridge(735, 30, 0.013, 13, (0.08, 0.12, 0.20), 1.5)

    # side foliage masses framing the bed
    fol = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry in [(80, 520, 260, 420), (260, 760, 220, 160), (1850, 560, 260, 440),
                           (1680, 770, 230, 150), (-40, 200, 220, 360), (1960, 230, 220, 330)]:
        fol = np.maximum(fol, (((xx / S - cx) / rx) ** 2 + ((yy / S - cy) / ry) ** 2 < 1).astype(np.float32))
    fol = np.asarray(Image.fromarray((fol * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(10 * S))).astype(np.float32)[..., None] / 255
    folcol = np.array([0.07, 0.17, 0.19]) * (0.8 + 0.4 * _noise(W, H, 60, 21)[..., None])
    sky = sky * (1 - fol) + folcol * fol

    # garden bed: mossy top plane (pots stand here) + darker front face
    Y = yy / S
    bed = np.clip((Y - GROUND_Y + 4) / 8, 0, 1)[..., None]
    top_plane = np.clip((BED_FRONT_Y - Y) / 6, 0, 1)[..., None]
    moss = np.array([0.12, 0.20, 0.17]) * (0.8 + 0.35 * _noise(W, H, 50, 31)[..., None])
    moss = moss * (0.85 + 0.25 * ((Y - GROUND_Y) / (BED_FRONT_Y - GROUND_Y)).clip(0, 1)[..., None])
    face = np.array([0.15, 0.11, 0.13]) * (0.8 + 0.3 * _noise(W, H, 70, 33)[..., None])
    face = face * (1 - 0.5 * np.clip((Y - BED_FRONT_Y) / 200, 0, 1))[..., None]
    lip = np.exp(-((Y - BED_FRONT_Y) / 5) ** 2)[..., None] * 0.6
    soil = moss * top_plane + face * (1 - top_plane)
    soil = soil * (1 - lip) + np.array([0.26, 0.36, 0.25]) * lip
    sky = sky * (1 - bed) + soil * bed

    # hanging glowing bell flowers (left & right vines)
    vine = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vine)
    bells = []
    for vx, n in [(150, 5), (300, 3), (1630, 4), (1790, 5)]:
        dv.line([(vx * S, 0), ((vx + 15) * S, n * 70 * S)], fill=200, width=3 * S)
        for j in range(n):
            bells.append((vx + 6 + j * 3, 60 + j * 68))
    vm = np.asarray(vine.filter(ImageFilter.GaussianBlur(1.5 * S))).astype(np.float32)[..., None] / 255
    sky = sky * (1 - vm) + np.array([0.10, 0.22, 0.16]) * vm
    for bx, by in bells:
        _glow(sky, bx * S, by * S, 9 * S, (1.0, 0.86, 0.6), 0.85)
        _glow(sky, bx * S, by * S, 34 * S, (0.95, 0.7, 0.5), 0.16)

    # soft blurred foreground blossoms in the bottom corners
    for fx, fy, col in [(120, 1040, (0.75, 0.55, 0.85)), (260, 1065, (0.95, 0.7, 0.85)),
                        (1800, 1045, (0.65, 0.55, 0.9)), (1650, 1070, (0.95, 0.75, 0.85))]:
        _glow(sky, fx * S, fy * S, 55 * S, col, 0.55)

    img = Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8))
    return img


def paint_pot(seed=0):
    """Terracotta pot sprite, RGBA, drawn at 4x world size."""
    k = 4
    w, h = POT_W * k, POT_H * k
    im = Image.new("RGBA", (w, h + 8 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rim_h = 22 * k
    body = [(10 * k, rim_h), (w - 10 * k, rim_h), (w - 20 * k, h), (20 * k, h)]
    d.polygon(body, fill=(168, 92, 66, 255))
    d.rounded_rectangle((0, 2 * k, w - 1, rim_h + 2 * k), radius=6 * k, fill=(190, 110, 78, 255))
    d.ellipse((6 * k, 0, w - 6 * k, 14 * k), fill=(70, 45, 40, 255))  # soil
    a = np.asarray(im).astype(np.float32) / 255
    hh, ww = a.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    shade = 0.62 + 0.55 * (1 - xx / ww) ** 0.8  # moonlight from the upper right reads as cool rim
    rim = np.clip((xx / ww - 0.80) / 0.2, 0, 1) * 0.35
    tex = 0.92 + 0.16 * _noise(ww, hh, 10 * k // 2, 40 + seed)
    rgb = a[..., :3] * shade[..., None] * tex[..., None]
    rgb = rgb + rim[..., None] * np.array([0.35, 0.40, 0.65])
    rgb = rgb * 0.62  # night exposure
    out = np.dstack([np.clip(rgb, 0, 1), a[..., 3]])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.8))


def paint_leaf():
    """Large fallen leaf sprite, RGBA, 4x world size (300x150 world). Anchor = centre."""
    k = 4
    w, h = 300 * k, 150 * k
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(0, 181):
        th = math.radians(i)
        x = (w / 2) - (w / 2 - 6 * k) * math.cos(th)
        y = (h / 2) - (h / 2 - 8 * k) * math.sin(th) ** 0.85 * (1 - 0.12 * math.cos(th))
        pts.append((x, y))
    for i in range(180, -1, -1):
        th = math.radians(i)
        x = (w / 2) - (w / 2 - 6 * k) * math.cos(th)
        y = (h / 2) + (h / 2 - 8 * k) * math.sin(th) ** 0.85 * (1 + 0.08 * math.cos(th))
        pts.append((x, y))
    d.polygon(pts, fill=(255, 255, 255, 255))
    a = np.asarray(im).astype(np.float32)[..., 3] / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / w
    base = np.array([0.55, 0.62, 0.25]) * (1 - u[..., None]) + np.array([0.80, 0.62, 0.22]) * u[..., None]
    shade = 0.85 + 0.25 * (1 - yy / h)[..., None]
    tex = 0.9 + 0.2 * _noise(w, h, 24, 50)[..., None]
    rgb = base * shade * tex
    vein = Image.new("L", (w, h), 0)
    dv = ImageDraw.Draw(vein)
    dv.line([(4 * k, h / 2), (w - 4 * k, h / 2)], fill=255, width=3 * k)
    for i in range(1, 8):
        x0 = w * i / 8.5
        dv.line([(x0, h / 2), (x0 + 34 * k, h / 2 - 48 * k)], fill=170, width=2 * k)
        dv.line([(x0, h / 2), (x0 + 34 * k, h / 2 + 48 * k)], fill=170, width=2 * k)
    vm = np.asarray(vein.filter(ImageFilter.GaussianBlur(1.2 * k))).astype(np.float32)[..., None] / 255
    rgb = rgb * (1 - vm * 0.45) + np.array([0.9, 0.85, 0.5]) * vm * 0.2
    rgb = rgb * 0.70
    out = np.dstack([np.clip(rgb, 0, 1), a])
    im = Image.fromarray((out * 255).astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(1.0))
    # short stem on the left end
    d = ImageDraw.Draw(im)
    d.line([(0, h / 2 + 2 * k), (14 * k, h / 2)], fill=(110, 95, 45, 255), width=4 * k)
    return im


def build_cache():
    CACHE.mkdir(parents=True, exist_ok=True)
    paint_background().save(CACHE / "bg_world.png")
    for i in range(3):
        paint_pot(i).save(CACHE / f"pot_{i}.png")
    paint_leaf().save(CACHE / "leaf.png")
    print("env cache built")


if __name__ == "__main__":
    build_cache()
