"""Render the 8-second Lumi wing-motion test: 1280x720, 24 fps, 192 frames, no audio.

Genuine per-layer character animation (not a pan/zoom of a still):
  * wings: non-rigid warp about shoulder pivots -- foreshortening (rotation toward
    camera) + lift, with tip lag so the wing bends through each stroke
  * body: hover bob driven by the wingbeat (rises on the downstroke) + slow drift/tilt
  * antennae: secondary sway about their bases, lagging the body
Camera is fixed. Layers come from rig/build_layers.py; originals are never touched.
"""
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "rig/layers"
FRAMES = ROOT / "work/frames"
OUT = ROOT / "renders/lumi_wing_test_v1.mp4"

W, H, FPS, N = 1280, 720, 24, 192
BEAT = 16  # frames per wingbeat -> 1.5 Hz, exactly 12 beats in 192 frames (loops cleanly)

PIVOT_L = np.array([300.0, 300.0])  # shoulder pivots in layer space (x, y)
PIVOT_R = np.array([474.0, 300.0])
ANT_BASE_L = (366, 168)
ANT_BASE_R = (408, 168)


def load(name):
    return np.asarray(Image.open(LAYERS / f"{name}.png")).astype(np.float32) / 255


def bilinear(img, x, y):
    h, w, _ = img.shape
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    valid = (x0 >= 0) & (y0 >= 0) & (x0 < w - 1) & (y0 < h - 1)
    x0 = np.clip(x0, 0, w - 2)
    y0 = np.clip(y0, 0, h - 2)
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    out = a * (1 - fy) + b * fy
    out[~valid] = 0
    return out


def stroke(phase):
    """0 = wings fully open/down, 1 = fully raised & foreshortened.
    Skewed so the downstroke (power stroke) is quicker than the recovery."""
    p = np.mod(phase, 1.0)
    up = 0.58  # fraction of the cycle spent on the upstroke
    rise = 0.5 - 0.5 * np.cos(np.pi * p / up)
    fall = 0.5 + 0.5 * np.cos(np.pi * (p - up) / (1 - up))
    return np.where(p < up, rise, fall)


def warp_wing(img, pivot, side, phase):
    """Inverse-map a wing layer. side=-1 for left wing, +1 for right wing."""
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx - pivot[0]) * side  # outward distance from pivot
    v = yy - pivot[1]
    r = np.sqrt(u * u + v * v)
    lag = np.clip(r / 360.0, 0, 1) * 0.07  # tips trail the root by up to ~1.1 frames
    s = stroke(phase - lag)
    # foreshortening: wing swings toward the camera -> horizontal compression
    c = 1.0 - 0.50 * s
    # lift: tip rises on the upstroke, dips slightly below rest at the bottom
    A = np.radians(-4.0 + 20.0 * s) * np.clip(r / 200.0, 0.35, 1.0)
    ca, sa = np.cos(A), np.sin(A)
    us = u * ca - v * sa
    vs = u * sa + v * ca
    us = us / c
    sx = pivot[0] + us * side
    sy = pivot[1] + vs
    out = bilinear(img, sx, sy)
    out[..., 3] *= np.clip((u + 30.0) / 30.0, 0, 1)  # soft stop before the body centreline
    # light catches the wing as it turns toward camera
    out[..., :3] *= (1.0 + 0.07 * s)[..., None]
    return out, s


def over(dst, src):
    a = src[..., 3:4]
    dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    dst[..., 3:4] = a + dst[..., 3:4] * (1 - a)
    return dst


def rotate_layer(arr, deg, center):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGBA")
    im = im.rotate(deg, resample=Image.BICUBIC, center=center)
    return np.asarray(im).astype(np.float32) / 255


def background():
    """Soft paper-to-lavender field from the sheet's own palette; non-distracting."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top = np.array([0.86, 0.84, 0.91])
    bot = np.array([0.92, 0.89, 0.90])  # sheet paper tone
    t = (yy / H)[..., None]
    bg = top * (1 - t) + bot * t
    d = np.sqrt(((xx - W / 2) / 420) ** 2 + ((yy - H / 2 + 10) / 300) ** 2)
    glow = np.exp(-d * d)[..., None]
    bg = bg * (1 - 0.35 * glow) + np.array([0.93, 0.97, 0.94]) * 0.35 * glow
    return bg


def main():
    wl, wr = load("wing_l"), load("wing_r")
    body = load("body")
    al, ar = load("antenna_l"), load("antenna_r")
    lh, lw, _ = body.shape
    bg = background()

    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    only = [int(a) for a in sys.argv[1:]]
    for f in (only or range(N)):
        t = f / FPS
        phase = f / BEAT
        ch = np.zeros((lh, lw, 4), np.float32)
        lw_img, s_l = warp_wing(wl, PIVOT_L, -1, phase)
        rw_img, _ = warp_wing(wr, PIVOT_R, +1, phase)
        ch = over(ch, lw_img)
        ch = over(ch, rw_img)

        s_root = float(stroke(phase))
        sway = 3.0 * math.sin(2 * math.pi * t / 2.0 - 0.6) + 1.5 * s_root
        ch = over(ch, rotate_layer(al, sway, ANT_BASE_L))
        ch = over(ch, rotate_layer(ar, -sway + 0.8 * math.sin(2 * math.pi * t / 2.0 - 1.1), ANT_BASE_R))
        ch = over(ch, body)

        # hover: body lifted by each downstroke + slow 4 s drift, slight tilt
        lift = -6.0 * float(stroke(phase - 0.62))
        drift_y = 8.0 * math.sin(2 * math.pi * t / 4.0)
        drift_x = 6.0 * math.sin(2 * math.pi * t / 8.0)
        tilt = 1.6 * math.sin(2 * math.pi * t / 4.0 + 0.8)
        im = Image.fromarray((np.clip(ch, 0, 1) * 255).astype(np.uint8), "RGBA")
        im = im.rotate(tilt, resample=Image.BICUBIC, center=(lw / 2, lh / 2), expand=False)
        frame = Image.fromarray((bg * 255).astype(np.uint8)).convert("RGBA")
        ox = int(round((W - lw) / 2 + drift_x))
        oy = int(round((H - lh) / 2 + drift_y + lift + 20))
        frame.alpha_composite(im, (ox, oy))
        frame.convert("RGB").save(FRAMES / f"f{f:04d}.png")
        if f % 48 == 0:
            print(f"frame {f}/{N}", flush=True)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", str(FRAMES / "f%04d.png"), "-frames:v", str(N),
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-movflags", "+faststart", "-an", str(OUT),
    ]
    if not only: subprocess.run(cmd, check=True)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
