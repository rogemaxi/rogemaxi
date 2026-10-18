"""Episode 01 "A Little Space to Grow" -- v0 shot timeline (240 s, 15 shots).

Built from the SSOI section VII locked baseline; the real screenplay was not
available. Every frame's state is computed here; render.py only draws it.
"""
import math

FPS = 24
DURATION = 240
N_FRAMES = FPS * DURATION

LUMI_W = 250.0  # world width of Lumi's rig
RIG_W, RIG_CX, RIG_CY = 740.0, 370.0, 275.0
K = LUMI_W / RIG_W
HAND = ((388 - RIG_CX) * K, (428 - RIG_CY) * K)  # forelimb contact offset from Lumi centre
FEET = (428 + 62 - RIG_CY) * K  # paws/feet below centre

POT_BASE_Y = 852
POT_H = 104
RIM_Y = POT_BASE_Y - POT_H + 6
POT_A, POT_B0, POT_C0 = 845.0, 960.0, 1075.0
POT_C1 = 1270.0  # action 2
POT_B1 = 1058.0  # action 3: straight horizontal slide (Pot B correction kept upright)
LEAF_REST0 = (960.0, 652.0, -4.0)  # lying on the seedling tips
LEAF_REST0_SQ = 0.62  # seen from the front, a leaf lying on top reads flattened
LEAF_HALF_H = 75.0
LEAF_GRIP = LEAF_HALF_H - 4  # leaf centre sits this far below the paws
LEAF_GROUND_SQ = 0.55
LEAF_REST1 = (1470.0, POT_BASE_Y + 10 - LEAF_HALF_H * LEAF_GROUND_SQ, 0.0)

# (start, end, id, title) -- shot 07 is the leaf contact sequence per SSOI section X
SHOTS = [
    (0, 10, "01", "Crowded seedlings under a fallen leaf (problem at frame 0)"),
    (10, 28, "02", "Lumi arrives; tink, tink on Pot A"),
    (28, 40, "03", "Close-up: concern"),
    (40, 62, "04", "Failed attempt 1: push all three pots at once"),
    (62, 86, "05", "Failed attempt 2: leaf and pot at once; leaf flops over Lumi"),
    (86, 102, "06", "Pause and observe -> idea"),
    (102, 128, "07", "Action 1: approach, grasp, lift, carry, place, release the leaf"),
    (128, 140, "08", "Moonlight reaches the seedlings; still crowded"),
    (140, 160, "09", "Action 2: Pot C slides right"),
    (160, 172, "10", "Seedling C straightens"),
    (172, 192, "11", "Action 3: Pot B slides right, upright"),
    (192, 208, "12", "Before -> after payoff"),
    (208, 218, "13", "Close-up: gentle joy"),
    (218, 232, "14", "Tink, tink on Pot B; Lumi rests on the leaf; closing hum"),
    (232, 240, "15", "Peaceful wide; gentle fade"),
]

# audio cues (seconds) consumed by audio.py
CUES = {
    "tink": [22.0, 22.6, 221.0, 221.6],
    "strain": [46.0],
    "wobble": [47.0],
    "flop": [73.4],
    "rustle": [75.5, 77.5],
    "pop": [80.6],
    "idea": [95.6],
    "lift": [108.2],
    "set_down": [120.6],
    "slide": [147.0, 178.0],
    "bloom": [130.0, 161.0, 186.0, 199.0],
    "hum_start": [224.0],
}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def kf(t, keys):
    """Piecewise smoothstep interpolation of floats or tuples."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def seeds_crowded():
    return [dict(droop=0.6, lean=1.0, health=0.25, grow=1.0),
            dict(droop=0.8, lean=-0.25, health=0.25, grow=1.0),
            dict(droop=0.6, lean=-1.0, health=0.25, grow=1.0)]


def seeds_mix(a, b, u):
    return [{k: x[k] + (y[k] - x[k]) * u for k in x} for x, y in zip(a, b)]


def seeds_after_leaf():
    return [dict(droop=0.5, lean=1.0, health=0.5, grow=1.0),
            dict(droop=0.68, lean=-0.25, health=0.5, grow=1.0),
            dict(droop=0.5, lean=-1.0, health=0.5, grow=1.0)]


def seeds_after_c():
    s = seeds_after_leaf()
    s[2] = dict(droop=0.03, lean=-1.0, health=1.0, grow=1.04)
    return s


def seeds_final(grow=1.06):
    return [dict(droop=0.03, lean=1.0, health=1.0, grow=grow),
            dict(droop=0.03, lean=-0.25, health=1.0, grow=grow),
            dict(droop=0.03, lean=-1.0, health=1.0, grow=grow)]


def base_state():
    return dict(
        cam=(960.0, 540.0, 1.0),
        closeup=None,
        lumi=None,  # dict(x, y, tilt, rate) or dict(..., hold=phase)
        lumi_front_of_leaf=True,
        pots=[dict(x=POT_A, rot=0.0), dict(x=POT_B0, rot=0.0), dict(x=POT_C0, rot=0.0)],
        seeds=seeds_crowded(),
        leaf=dict(x=LEAF_REST0[0], y=LEAF_REST0[1], rot=LEAF_REST0[2], sq=LEAF_REST0_SQ),
        title=0.0,
        fade=1.0,
        before=None,  # (state, weight) for the before/after dissolve
    )


def lumi_at_hand(hx, hy):
    return hx - HAND[0], hy - HAND[1]


def _lift_pose(t):
    """Shot 05: Lumi lifts the leaf's right end (pivoting on its left end) while reaching for Pot B."""
    lx, ly, lr = LEAF_REST0
    lift = kf(t, [(66, 0.0), (69, 1.0), (70, 1.0), (72.5, 0.6)])
    rot = lr - 16 * lift
    ang, a0 = math.radians(rot), math.radians(lr)
    px, py = lx - 150 * math.cos(a0), ly - 150 * math.sin(a0)  # leaf's left end stays put
    leaf = (px + 150 * math.cos(ang), py + 150 * math.sin(ang), rot)
    ex, ey = px + 285 * math.cos(ang), py + 285 * math.sin(ang) + 6
    reach = kf(t, [(69.5, 0.0), (72.5, 1.0)])
    hx, hy = lumi_at_hand(ex, ey)
    return leaf, (hx - 25 * reach, hy + 30 * reach)


def shot_state(t):
    s = base_state()
    # ---- 01: problem visible from the first frame
    if t < 10:
        s["cam"] = kf(t, [(0, (960.0, 720.0, 1.6)), (10, (960.0, 715.0, 1.72))])
        return s
    # ---- 02: arrival + tink tink
    if t < 28:
        s["cam"] = (960.0, 540.0, 1.0)
        hx, hy = POT_A - 50, RIM_Y
        tap_y = lambda tt: 9 * (math.exp(-((tt - 22.0) / 0.12) ** 2) + math.exp(-((tt - 22.6) / 0.12) ** 2))
        x, y = kf(t, [(10, (-220.0, 260.0)), (14, (420.0, 360.0)), (18, (680.0, 560.0)),
                      (20.5, lumi_at_hand(hx, hy - 14)), (23.2, lumi_at_hand(hx, hy - 14)),
                      (25.5, (660.0, 560.0)), (28, (640.0, 548.0))])
        if 20.5 <= t <= 23.2:
            y += tap_y(t) + 0.0
        tilt = kf(t, [(10, 10.0), (16, 4.0), (19, -2.0), (24, 0.0), (26.5, 3.0), (28, 2.0)])
        s["lumi"] = dict(x=x, y=y, tilt=tilt, rate=kf(t, [(10, 2.0), (18, 1.5)]))
        s["title"] = kf(t, [(11.5, 0.0), (12.5, 1.0), (16.5, 1.0), (17.5, 0.0)])
        return s
    # ---- 03: concern close-up
    if t < 40:
        s["closeup"] = dict(a="concern", b=None, w=0.0, t0=28)
        return s
    # ---- 04: failed attempt 1
    if t < 62:
        s["cam"] = (930.0, 690.0, 1.35)
        hx, hy = POT_A - 66, 800.0
        px, py = lumi_at_hand(hx, hy)
        x, y = kf(t, [(40, (640.0, 560.0)), (44, (px - 20, py)), (46, (px, py)), (54, (px, py)),
                      (55.5, (px - 70, py - 40)), (62, (px - 60, py - 70))])
        jitter = 2.0 * math.sin(t * 40) if 46 <= t <= 54 else 0.0
        s["lumi"] = dict(x=x + jitter, y=y, tilt=kf(t, [(44, 0.0), (46, 9.0), (54, 9.0), (55.5, -7.0),
                                                       (57, 0.0), (59, -4.0), (62, -3.0)]),
                         rate=kf(t, [(44, 1.6), (46, 3.2), (54, 3.2), (55.5, 1.5)]))
        if 46.5 <= t <= 54:
            a = kf(t, [(46.5, 0.0), (47.5, 1.0), (53, 1.0), (54, 0.0)])
            for i, p in enumerate(s["pots"]):
                p["rot"] = 2.6 * a * math.sin(2 * math.pi * 3.0 * t + i * 0.9)
        return s
    # ---- 05: failed attempt 2 with the falling-leaf gag
    if t < 86:
        s["cam"] = (980.0, 660.0, 1.45)
        lx, ly, lr = LEAF_REST0
        edge = (lx + 135, ly + 6)
        g = lumi_at_hand(*edge)
        if t < 66:
            x, y = kf(t, [(62, (900.0, 500.0)), (66, (g[0], g[1] - 10))])
            s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(62, -3.0), (66, 0.0)]), rate=1.5)
        elif t < 73:
            leaf_pose, lumi_pose = _lift_pose(t)
            s["leaf"].update(x=leaf_pose[0], y=leaf_pose[1], rot=leaf_pose[2])
            s["lumi"] = dict(x=lumi_pose[0], y=lumi_pose[1], tilt=kf(t, [(66, 0.0), (69, -6.0), (72.5, 12.0)]),
                             rate=kf(t, [(66, 1.6), (68, 2.8)]))
        elif t < 80.5:
            # leaf slips and flops over Lumi; she wriggles underneath
            (l0x, l0y, l0r), (m0x, m0y) = _lift_pose(73.0)
            cx, cy = kf(t, [(73, (l0x, l0y)), (74.2, (lx + 60, ly - 10))])
            wig = smooth((t - 75) / 0.5)
            s["leaf"].update(x=cx + wig * 4 * math.sin(t * 9), y=cy + wig * 3 * math.sin(t * 7),
                             rot=kf(t, [(73, l0r), (74.2, 14.0)]) + wig * 5 * math.sin(t * 6),
                             sq=kf(t, [(73, LEAF_REST0_SQ), (74.2, 0.9)]))
            mx, my = kf(t, [(73, (m0x, m0y)), (74.0, (lx + 60, ly - 4))])
            s["lumi"] = dict(x=mx, y=my, tilt=kf(t, [(73, 12.0), (74, 0.0)]) + 8 * math.sin(t * 5) * wig,
                             rate=kf(t, [(73, 2.5), (75, 1.2)]))
            s["lumi_front_of_leaf"] = t < 73.3
        else:
            # pops out the top; the leaf settles back over the seedlings
            x, y = kf(t, [(80.5, (lx + 60, ly - 4)), (81.6, (lx + 70, ly - 150)), (86, (lx + 120, ly - 170))])
            s["leaf"].update(**dict(zip(("x", "y", "rot", "sq"), kf(t, [(80.5, (lx + 60, ly - 10, 14.0, 0.9)),
                                                                          (82.5, (lx, ly, lr, LEAF_REST0_SQ))]))))
            shake = 7 * math.sin((t - 82) * 14) * math.exp(-max(t - 82, 0) * 1.4) if t > 82 else 0.0
            s["lumi"] = dict(x=x, y=y, tilt=shake, rate=kf(t, [(80.5, 2.6), (82, 1.5)]))
            s["lumi_front_of_leaf"] = t > 81.0
        return s
    # ---- 06: pause (eyes closed) -> idea
    if t < 102:
        s["closeup"] = dict(a="sleepy", b="joy", w=kf(t, [(95, 0.0), (97, 1.0)]), t0=86)
        return s
    # ---- 07: leaf contact: approach, grasp, lift, carry, place, release
    if t < 128:
        s["cam"] = (1150.0, 660.0, 1.25)
        lx, ly, lr = LEAF_REST0
        rx, ry, _ = LEAF_REST1
        grip0 = (lx, ly - LEAF_GRIP * LEAF_REST0_SQ)
        if t < 108:
            hx, hy = kf(t, [(102, (980.0, 420.0)), (105.5, (grip0[0], grip0[1] - 26)), (107, grip0), (108, grip0)])
            x, y = lumi_at_hand(hx, hy)
            s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(102, -2.0), (106, 0.0)]), rate=1.5)
            return s
        # leaf is attached to the paws from 108 until release at 121
        if t < 121:
            hx, hy = kf(t, [(108, grip0), (110.5, (lx + 10, grip0[1] - 90)), (113.5, (1250.0, 520.0)),
                            (116.5, (rx, 530.0)), (120.5, (rx, ry - LEAF_GRIP * LEAF_GROUND_SQ)),
                            (121, (rx, ry - LEAF_GRIP * LEAF_GROUND_SQ))])
            sq = kf(t, [(108, LEAF_REST0_SQ), (110.5, 1.0), (117.5, 1.0), (120.5, LEAF_GROUND_SQ)])
            vx = (kf(t + 0.25, [(110.5, lx + 10), (113.5, 1250.0), (116.5, rx)]) -
                  kf(t - 0.25, [(110.5, lx + 10), (113.5, 1250.0), (116.5, rx)])) / 0.5
            swing = -0.035 * vx + 1.5 * math.sin(t * 2.2) * (1 if 109 < t < 118 else 0)
            rot = kf(t, [(108, lr), (110.5, 0.0)]) + swing * (1 - smooth((t - 118) / 2.5))
            s["leaf"].update(x=hx, y=hy + LEAF_GRIP * sq, rot=rot, sq=sq)
            x, y = lumi_at_hand(hx, hy)
            s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(108, 0.0), (110, -3.0), (113, 5.0), (117, 0.0)]),
                             rate=kf(t, [(108, 1.5), (109, 2.5), (119, 2.5), (121, 1.6)]), carrying=True)
            s["seeds"] = seeds_mix(seeds_crowded(), seeds_after_leaf(), smooth((t - 112) / 8))
            return s
        # release: leaf stays put, Lumi lifts away
        s["leaf"].update(x=rx, y=ry, rot=0.0, sq=LEAF_GROUND_SQ)
        hx, hy = kf(t, [(121, (rx, ry - LEAF_GRIP * LEAF_GROUND_SQ)), (123, (rx - 10, ry - 120)),
                        (128, (1180.0, 520.0))])
        x, y = lumi_at_hand(hx, hy)
        s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(121, 0.0), (124, -3.0), (128, 2.0)]), rate=1.5)
        s["seeds"] = seeds_after_leaf()
        return s
    # from here the leaf rests at LEAF_REST1
    s["leaf"].update(x=LEAF_REST1[0], y=LEAF_REST1[1], rot=0.0, sq=LEAF_GROUND_SQ)
    # ---- 08: moonlight reaches the seedlings
    if t < 140:
        s["cam"] = kf(t, [(128, (960.0, 740.0, 1.9)), (140, (960.0, 735.0, 2.0))])
        s["seeds"] = seeds_mix(seeds_after_leaf(), seeds_after_leaf(), 0)
        s["seeds"] = [dict(d, health=d["health"] + 0.1 * smooth((t - 129) / 6)) for d in s["seeds"]]
        return s
    s["seeds"] = seeds_after_leaf()
    # ---- 09: action 2, Pot C slides right
    if t < 160:
        s["cam"] = (1110.0, 690.0, 1.3)
        grip = lambda px: (px + 60, RIM_Y + 8)
        cx = kf(t, [(147, POT_C0), (153, POT_C1)])
        s["pots"][2]["x"] = cx
        s["pots"][2]["rot"] = 1.2 * math.sin((t - 147) * 5) if 147 < t < 153 else 0.0
        if t < 146:
            hx, hy = kf(t, [(140, (1180.0, 520.0)), (144.5, (grip(POT_C0)[0] + 20, grip(POT_C0)[1] - 30)),
                            (146, grip(POT_C0))])
        elif t < 154:
            hx, hy = grip(cx)
        else:
            hx, hy = kf(t, [(154, grip(POT_C1)), (156, (grip(POT_C1)[0] + 10, RIM_Y - 120)), (160, (1240.0, 560.0))])
        x, y = lumi_at_hand(hx, hy)
        s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(146, 0.0), (147.5, -7.0), (153, -7.0), (154.5, 0.0)]),
                         rate=kf(t, [(146, 1.5), (147, 2.4), (153, 2.4), (154.5, 1.5)]))
        lag = s["seeds"][2]
        if 147 < t < 156:
            lag["lean"] = -1.0 - 0.6 * math.sin(min(t - 147, 6) / 6 * math.pi)
        return s
    s["pots"][2]["x"] = POT_C1
    # ---- 10: seedling C straightens
    if t < 172:
        s["cam"] = (POT_C1 - 40, 740.0, 2.0)
        s["seeds"] = seeds_mix(seeds_after_leaf(), seeds_after_c(), smooth((t - 161) / 7))
        return s
    s["seeds"] = seeds_after_c()
    # ---- 11: action 3, Pot B slides right (kept upright)
    if t < 192:
        s["cam"] = (1060.0, 690.0, 1.3)
        grip = lambda px: (px + 60, RIM_Y + 8)
        bx = kf(t, [(178, POT_B0), (184, POT_B1)])
        s["pots"][1]["x"] = bx
        if t < 177:
            hx, hy = kf(t, [(172, (1150.0, 560.0)), (175.5, (grip(POT_B0)[0] + 20, grip(POT_B0)[1] - 30)),
                            (177, grip(POT_B0))])
        elif t < 185:
            hx, hy = grip(bx)
        else:
            hx, hy = kf(t, [(185, grip(POT_B1)), (187, (grip(POT_B1)[0] + 10, RIM_Y - 130)), (192, (1180.0, 520.0))])
        x, y = lumi_at_hand(hx, hy)
        s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(177, 0.0), (178.5, -6.0), (184, -6.0), (185.5, 0.0)]),
                         rate=kf(t, [(177, 1.5), (178, 2.2), (184, 2.2), (185.5, 1.5)]))
        s["seeds"] = seeds_mix(seeds_after_c(), seeds_final(1.04), smooth((t - 185) / 6))
        return s
    s["pots"][1]["x"] = POT_B1
    s["pots"][2]["x"] = POT_C1
    # ---- 12: before -> after payoff
    if t < 208:
        s["cam"] = kf(t, [(192, (1060.0, 650.0, 1.2)), (208, (1060.0, 645.0, 1.26))])
        s["seeds"] = seeds_final(kf(t, [(197, 1.04), (206, 1.08)]))
        s["lumi"] = dict(x=kf(t, [(192, 1180.0), (208, 1160.0)]), y=kf(t, [(192, 460.0), (208, 450.0)]), tilt=2.0,
                         rate=1.3)
        w = kf(t, [(192, 1.0), (195.5, 1.0), (199, 0.0)])
        if w > 0:
            b = base_state()
            b["cam"] = s["cam"]
            s["before"] = (b, w)
        return s
    # ---- 13: gentle joy close-up
    if t < 218:
        s["closeup"] = dict(a="joy", b=None, w=0.0, t0=208)
        return s
    s["seeds"] = seeds_final(1.08)
    perch = (LEAF_REST1[0] + 20, LEAF_REST1[1] - LEAF_HALF_H * LEAF_GROUND_SQ * 0.4 - FEET)
    # ---- 14: tink tink on Pot B, rest on the leaf, closing hum
    if t < 232:
        s["cam"] = kf(t, [(218, (1180.0, 690.0, 1.3)), (232, (1240.0, 700.0, 1.36))])
        hx, hy = POT_B1 + 50, RIM_Y
        tap = 9 * (math.exp(-((t - 221.0) / 0.12) ** 2) + math.exp(-((t - 221.6) / 0.12) ** 2))
        x, y = kf(t, [(218, (1180.0, 520.0)), (220, lumi_at_hand(hx, hy - 14)), (222.2, lumi_at_hand(hx, hy - 14)),
                      (225, (1380.0, 560.0)), (227.5, (perch[0], perch[1] - 25)), (229, perch)])
        if 219.5 < t < 222.5:
            y += tap
        if t < 229:
            s["lumi"] = dict(x=x, y=y, tilt=kf(t, [(222, 0.0), (224, 4.0), (227, 0.0)]),
                             rate=kf(t, [(218, 1.5), (226, 1.2), (229, 0.8)]))
        else:
            s["lumi"] = dict(x=perch[0], y=perch[1], tilt=0.0, hold=True)
        return s
    # ---- 15: peaceful wide, gentle fade
    s["cam"] = kf(t, [(232, (1060.0, 600.0, 1.12)), (240, (1060.0, 590.0, 1.08))])
    s["lumi"] = dict(x=perch[0], y=perch[1], tilt=0.0, hold=True)
    s["fade"] = kf(t, [(235, 1.0), (239.6, 0.0)])
    return s


def all_states():
    """Sequential pass so the wingbeat phase is continuous across frames."""
    states, phase = [], 0.0
    for f in range(N_FRAMES):
        t = f / FPS
        s = shot_state(t)
        s["t"] = t
        s["f"] = f
        L = s["lumi"]
        if L is not None:
            if L.get("hold"):
                # resting: wings slowly open and close (breathing), no flapping
                L["phase"] = 0.40 + 0.12 * math.sin(2 * math.pi * t / 4.0)
                L["flying"] = False
            else:
                phase += L["rate"] / FPS
                L["phase"] = phase
                L["flying"] = True
        states.append(s)
    return states


def shot_at(t):
    for a, b, sid, title in SHOTS:
        if a <= t < b:
            return sid
    return SHOTS[-1][2]
