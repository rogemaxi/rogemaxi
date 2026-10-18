"""Render Episode 01 v0 frames from timeline states and stream them to ffmpeg.

Usage: python render.py                 -> full 240 s picture (renders/ep01_v0_picture.mp4)
       python render.py --stills 5 71   -> preview PNGs at those seconds (work/stills/)
"""
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "rig"))
import timeline as TL  # noqa: E402
from env import BG_SCALE, POT_H, POT_W  # noqa: E402
from render_wing_test import stroke  # noqa: E402

W, H, SS = 1280, 720, 2  # output size, supersampling for props
BANK = ROOT / "work/bank"
ENV = ROOT / "work/env"
OUT = ROOT / "renders/ep01_v0_picture.mp4"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

A = {}  # per-worker assets


def init_assets():
    A["bg"] = Image.open(ENV / "bg_world.png").convert("RGB")
    A["pots"] = [Image.open(ENV / f"pot_{i}.png").convert("RGBA") for i in range(3)]
    A["leaf"] = Image.open(ENV / "leaf.png").convert("RGBA")
    A["flap"] = [Image.open(BANK / f"flap_{k:02d}.png").convert("RGBA") for k in range(32)]
    A["glow"] = [Image.open(BANK / f"glow_{k:02d}.png").convert("RGBA") for k in range(32)]
    A["expr"] = {n: Image.open(BANK / f"expr_{n}.png").convert("RGB") for n in ("joy", "concern", "sleepy")}
    A["blur_bg"] = A["bg"].resize((W // 2, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize(
        (W, H), Image.BICUBIC)
    # radial glow sprite
    yy, xx = np.mgrid[-64:64, -64:64].astype(np.float32)
    g = np.exp(-(xx * xx + yy * yy) / (2 * 22.0 ** 2))
    A["dot"] = g
    # soft contact shadow
    sh = np.exp(-((xx / 60) ** 2 + (yy / 18) ** 2) * 3)
    A["shadow"] = Image.fromarray(np.dstack([np.zeros_like(sh)] * 3 + [sh * 150]).astype(np.uint8), "RGBA")
    A["font_b"] = ImageFont.truetype(FONT_B, 44 * SS)
    A["font_i"] = ImageFont.truetype(FONT_I, 34 * SS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / 262.0) ** 2 + ((yy - H / 2 - 12) / 318.0) ** 2)
    A["oval"] = np.clip((1.0 - d) / 0.2, 0, 1)[..., None]


class Cam:
    def __init__(self, cx, cy, z):
        self.cx, self.cy = cx, cy
        self.s = z * W / 1920.0  # output px per world unit

    def to(self, x, y, ss=SS):
        return ((x - self.cx) * self.s + W / 2) * ss, ((y - self.cy) * self.s + H / 2) * ss


def paste(canvas, sprite, x, y):
    x, y = int(round(x)), int(round(y))
    cw, ch = canvas.size
    w, h = sprite.size
    x0, y0, x1, y1 = max(0, x), max(0, y), min(cw, x + w), min(ch, y + h)
    if x0 < x1 and y0 < y1:
        canvas.alpha_composite(sprite.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def place(canvas, sprite, cx, cy, scale, rot=0.0, sy=1.0):
    """Scale (and optionally y-squash / rotate clockwise by rot deg) a sprite, centre it at (cx, cy)."""
    w, h = max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale * sy))
    im = sprite.resize((w, h), Image.LANCZOS)
    if abs(rot) > 0.01:
        im = im.rotate(-rot, resample=Image.BICUBIC, expand=True)
    paste(canvas, im, cx - im.width / 2, cy - im.height / 2)


def glow_dots(canvas_arr, pts):
    """Additive glow dots: pts = [(x, y, radius_px, (r,g,b), strength)] in canvas px."""
    h, w, _ = canvas_arr.shape
    for x, y, r, col, st in pts:
        k = r / 22.0
        size = int(128 * k)
        if size < 4:
            continue
        g = np.asarray(Image.fromarray((A["dot"] * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                       np.float32) / 255
        x0, y0 = int(x - size / 2), int(y - size / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + size), min(h, y0 + size)
        if xa >= xb or ya >= yb:
            continue
        canvas_arr[ya:yb, xa:xb] += g[ya - y0:yb - y0, xa - x0:xb - x0, None] * np.array(col, np.float32) * st


def bezier(p0, p1, p2, n=18):
    out = []
    for i in range(n + 1):
        u = i / n
        out.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
                    (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]))
    return out


def draw_seedling(draw, glows, base, unit, p, t, i):
    d, lean, hl, grow = p["droop"], p["lean"], p["health"], p["grow"]
    Hs = 118 * grow * unit * (1 - 0.35 * d)
    sway = math.radians(2.5 * hl * math.sin(t * 0.9 + i * 1.7))
    th = math.radians(lean * (6 + 62 * d)) + sway
    tip = (base[0] + Hs * math.sin(th), base[1] - Hs * math.cos(th))
    ctrl = (base[0] + Hs * 0.08 * math.sin(th) - lean * d * 6 * unit, base[1] - Hs * 0.62)
    pts = bezier(base, ctrl, tip)
    stem_col = tuple(int(a + (b - a) * hl) for a, b in zip((70, 92, 58), (96, 170, 84)))
    leaf_col = tuple(int(a + (b - a) * hl) for a, b in zip((86, 110, 66), (128, 214, 112)))
    vein_col = tuple(int(c * 0.75) for c in leaf_col)
    for j in range(len(pts) - 1):
        wdt = (7.5 - 3.5 * j / len(pts)) * unit
        draw.line([pts[j], pts[j + 1]], fill=stem_col + (255,), width=max(1, int(wdt)))
    phi = math.atan2(tip[1] - pts[-3][1], tip[0] - pts[-3][0])  # stem direction at tip
    openness = hl * (1 - 0.7 * d)
    spread = math.radians(18 + 62 * openness)
    L, Wd = 54 * grow * unit, 25 * grow * unit
    for sgn in (-1, 1):
        a = phi + sgn * spread
        ca, sa = math.cos(a), math.sin(a)
        poly = []
        for k in range(24):
            u = k / 23 * math.pi
            lx, ly = L * (0.5 - 0.5 * math.cos(u)), sgn * Wd * 0.5 * math.sin(u) * (1.0 if k < 12 else 0.85)
            poly.append((tip[0] + lx * ca - ly * sa, tip[1] + lx * sa + ly * ca))
        for k in range(23, -1, -1):
            u = k / 23 * math.pi
            lx, ly = L * (0.5 - 0.5 * math.cos(u)), -sgn * Wd * 0.25 * math.sin(u)
            poly.append((tip[0] + lx * ca - ly * sa, tip[1] + lx * sa + ly * ca))
        draw.polygon(poly, fill=leaf_col + (255,))
        draw.line([tip, (tip[0] + L * 0.9 * ca, tip[1] + L * 0.9 * sa)], fill=vein_col + (255,),
                  width=max(1, int(1.6 * unit)))
    if hl > 0.45:
        glows.append((tip[0], tip[1], 40 * unit * grow, (0.55, 1.0, 0.75), 0.30 * (hl - 0.45) / 0.55))


def render_scene(s):
    t = s["t"]
    cam = Cam(*s["cam"])
    # background crop
    vw, vh = W / cam.s, H / cam.s
    x0, y0 = (cam.cx - vw / 2) * BG_SCALE, (cam.cy - vh / 2) * BG_SCALE
    bg = A["bg"].transform((W, H), Image.EXTENT, (x0, y0, x0 + vw * BG_SCALE, y0 + vh * BG_SCALE),
                           Image.BICUBIC)
    props = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    unit = cam.s * SS
    glows = []
    # contact shadows
    for p in s["pots"]:
        bx, by = cam.to(p["x"], TL.POT_BASE_Y - 2)
        place(props, A["shadow"], bx, by, unit * 1.15)
    lf = s["leaf"]
    if lf["sq"] < 0.95:
        bx, by = cam.to(lf["x"], TL.POT_BASE_Y + 8)
        place(props, A["shadow"], bx, by, unit * 2.4, sy=0.7)
    L = s["lumi"]
    if L is not None and L.get("flying", True):
        ground_d = max(0.0, TL.POT_BASE_Y - (L["y"] + TL.FEET))
        a = max(0.0, 1 - ground_d / 300)
        if a > 0:
            sh = A["shadow"].copy()
            sh.putalpha(sh.getchannel("A").point(lambda v: int(v * a * 0.8)))
            bx, by = cam.to(L["x"], TL.POT_BASE_Y + 4)
            place(props, sh, bx, by, unit * 1.6)
    # pots + seedlings
    draw = ImageDraw.Draw(props)
    for i, (p, sd) in enumerate(zip(s["pots"], s["seeds"])):
        bx, by = cam.to(p["x"], TL.POT_BASE_Y)
        pot = A["pots"][i]
        sc = unit / 4
        w, h = int(pot.width * sc), int(pot.height * sc)
        im = pot.resize((w, h), Image.LANCZOS)
        if abs(p["rot"]) > 0.01:  # rotate about the base centre
            big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
            big.paste(im, (w // 2, 0))
            im = big.rotate(-p["rot"], resample=Image.BICUBIC, center=(w, h - 8 * sc))
            paste(props, im, bx - w, by - h + 8 * sc)
        else:
            paste(props, im, bx - w / 2, by - h + 8 * sc)
        top = (bx + math.sin(math.radians(p["rot"])) * POT_H * unit, by - (POT_H - 8) * unit)
        draw_seedling(draw, glows, top, unit, sd, t, i)

    def draw_leaf():
        lx, ly = cam.to(lf["x"], lf["y"])
        place(props, A["leaf"], lx, ly, unit / 4, rot=lf["rot"], sy=lf["sq"])

    def draw_lumi():
        idx = int(round((L["phase"] % 1.0) * 32)) % 32
        lift = -5.0 * float(stroke(L["phase"] - 0.62)) if L.get("flying", True) else 0.0
        cx, cy = cam.to(L["x"], L["y"] + lift)
        sc = TL.K * unit
        place(props, A["glow"][idx], cx, cy, sc, rot=L["tilt"])
        place(props, A["flap"][idx], cx, cy, sc, rot=L["tilt"])

    if L is None:
        draw_leaf()
    elif s["lumi_front_of_leaf"]:
        draw_leaf()
        draw_lumi()
    else:
        draw_lumi()
        draw_leaf()

    # fireflies: slow drift, slow gentle pulse (no flashing)
    for k in range(16):
        r = np.random.default_rng(100 + k)
        fx0, fy0, a1, a2, a3 = r.uniform(300, 1650), r.uniform(380, 780), *r.uniform(0, 6.28, 3)
        fx = fx0 + 60 * math.sin(0.11 * t + a1)
        fy = fy0 + 30 * math.sin(0.15 * t + a2)
        br = 0.55 + 0.45 * math.sin(2 * math.pi * t / 7.0 + a3)
        px, py = cam.to(fx, fy)
        glows.append((px, py, 7 * unit, (1.0, 0.85, 0.5), 0.9 * br))

    small = props.resize((W, H), Image.LANCZOS)
    frame = bg.convert("RGBA")
    frame.alpha_composite(small)
    arr = np.asarray(frame.convert("RGB")).astype(np.float32) / 255
    glows_small = [(x / SS, y / SS, r / SS, c, st) for x, y, r, c, st in glows]
    glow_dots(arr, glows_small)
    return arr


def render_closeup(s):
    c = s["closeup"]
    t = s["t"] - c["t0"]
    bg = np.asarray(A["blur_bg"]).astype(np.float32) / 255 * 0.85

    def expr_img(name):
        im = A["expr"][name]
        scale = 650 / im.height * (1 + 0.012 * math.sin(2 * math.pi * t / 3.5))
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), (235, 228, 230))
        bob = 6 * math.sin(2 * math.pi * t / 3.5)
        canvas.paste(im, (int(W / 2 - im.width / 2), int(H / 2 - im.height / 2 + 12 + bob)))
        return np.asarray(canvas).astype(np.float32) / 255

    img = expr_img(c["a"])
    if c["b"] and c["w"] > 0:
        img = img * (1 - c["w"]) + expr_img(c["b"]) * c["w"]
    m = A["oval"]
    arr = bg * (1 - m) + img * m
    glow_dots(arr, [(W / 2, H / 2, 260, (0.35, 0.55, 0.5), 0.10)])
    return arr


def render_frame(s):
    if s["closeup"]:
        arr = render_closeup(s)
    else:
        arr = render_scene(s)
        if s["before"] is not None:
            b, w = s["before"]
            b = dict(b, t=s["t"], lumi=None)
            arr = arr * (1 - w) + render_scene(b) * w
    if s["title"] > 0:
        arr = draw_title(arr, s["title"])
    arr = arr * s["fade"]
    return (np.clip(arr, 0, 1) * 255).astype(np.uint8)


def draw_title(arr, a):
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for text, font, y in (("Lumi & the Night Gardeners", A["font_b"], 120), ("A Little Space to Grow", A["font_i"], 185)):
        tw = d.textlength(text, font=font)
        x = 540 * SS - tw / 2  # keep clear of the moon
        d.text((x + 3 * SS, (y + 3) * SS), text, font=font, fill=(20, 20, 50, int(160 * a)))
        d.text((x, y * SS), text, font=font, fill=(240, 236, 220, int(255 * a)))
    im = im.resize((W, H), Image.LANCZOS)
    base = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    base.alpha_composite(im)
    return np.asarray(base.convert("RGB")).astype(np.float32) / 255


def _work(s):
    return render_frame(s).tobytes()


def main():
    states = TL.all_states()
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        init_assets()
        out = ROOT / "work/stills"
        out.mkdir(parents=True, exist_ok=True)
        for sec in sys.argv[2:]:
            f = min(int(float(sec) * TL.FPS), TL.N_FRAMES - 1)
            Image.fromarray(render_frame(states[f])).save(out / f"t{float(sec):06.2f}.png")
        print("stills written to", out)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(TL.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE)
    with Pool(4, initializer=init_assets) as pool:
        for i, buf in enumerate(pool.imap(_work, states, chunksize=6)):
            ff.stdin.write(buf)
            if i % 480 == 0:
                print(f"frame {i}/{TL.N_FRAMES} (t={i / TL.FPS:.0f}s)", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT, "exit", ff.returncode)


if __name__ == "__main__":
    main()
