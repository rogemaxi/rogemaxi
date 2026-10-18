"""Original synthesized soundtrack for Episode 01 v0 (no samples, no third-party audio).

Music: soft pad (C-Am-F-G) + music-box "Lumi motif" (original) placed on story beats.
SFX: tink-tink (clay pot taps), leaf flop/rustle, pot slides, bloom sparkles, wing flutter
driven by Lumi's actual wingbeat. Closing hum: voice-like hum of the motif.
Output: renders/ep01_v0_audio.wav (48 kHz, 16-bit stereo).
"""
import math
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "rig"))
import timeline as TL  # noqa: E402
from render_wing_test import stroke  # noqa: E402

SR = 48000
DUR = TL.DURATION
N = SR * DUR
rng = np.random.default_rng(2026)


def hz(note):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    return 440.0 * 2 ** ((names[note[0]] + 12 * (int(note[-1]) - 4)) / 12)


def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    e = np.full(n, s, np.float32)
    e[:a] = np.linspace(0, 1, a, endpoint=False) if a else e[:a]
    e[a:a + d] = np.linspace(1, s, min(d, max(0, n - a)), endpoint=False)[: max(0, min(d, n - a))]
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def band_noise(n, lo, hi, seed=None):
    r = np.random.default_rng(seed) if seed is not None else rng
    x = r.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= ((f >= lo) & (f <= hi)) * 1.0
    y = np.fft.irfft(X, n).astype(np.float32)
    return y / (np.abs(y).max() + 1e-9)


def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l * 1.414
    buf[i:i + len(sig), 1] += sig * gain * r * 1.414


def musicbox(freq, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t * 6)
           + 0.12 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t * 9))
    return (sig * np.exp(-t * 2.6) * env_adsr(n, 0.004, 0, 1, 0.05)).astype(np.float32)


def tink():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f0 = 1760.0
    sig = sum(a * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * dcy)
              for a, m, dcy in ((1.0, 1.0, 14), (0.5, 2.71, 22), (0.25, 5.13, 30)))
    click = band_noise(n, 2500, 7000, seed=5) * np.exp(-t * 400) * 0.3
    return ((sig + click) * env_adsr(n, 0.001, 0, 1, 0.02)).astype(np.float32)


def thump(dur=0.35, f=90):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t * (1 - 0.3 * t)) * np.exp(-t * 14)).astype(np.float32)


def whoosh(dur, lo=300, hi=2500, seed=1):
    n = int(dur * SR)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return (band_noise(n, lo, hi, seed) * e).astype(np.float32)


def sparkle(dur=1.6, seed=3):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    notes = [hz(x) * 2 for x in ("C5", "D5", "E5", "G5", "A5")]
    for k in range(9):
        t0 = k * dur / 11 + r.uniform(0, 0.05)
        s = musicbox(r.choice(notes), 0.7) * r.uniform(0.25, 0.5)
        i = int(t0 * SR)
        out[i:i + len(s)] += s[: n - i]
    return out


def hum_line(notes, beat):
    """Voice-like closed-mouth hum: rich harmonics, steep roll-off, vibrato, legato glides."""
    total = sum(b for _, b in notes) * beat + 0.6
    n = int(total * SR)
    f = np.zeros(n, np.float32)
    i = 0
    for note, b in notes:
        k = int(b * beat * SR)
        f[i:i + k] = hz(note)
        i += k
    f[i:] = hz(notes[-1][0])
    g = int(0.08 * SR)  # glide smoothing
    f = np.convolve(f, np.ones(g) / g, mode="same")
    f[:g] = f[g]
    f[-g:] = f[-g - 1]
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip(t / 0.6, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    sig = sum(np.sin(ph * m) / m ** 1.6 for m in range(1, 9))
    sig *= 1 + 0.25 * np.sin(ph * 1.0)  # nasal warmth
    return (sig * env_adsr(n, 0.25, 0, 1, 0.8) * 0.5).astype(np.float32)


MOTIF = [("E5", 1), ("G5", 1), ("A5", 2), ("G5", 1), ("E5", 1), ("D5", 2),
         ("C5", 1), ("D5", 1), ("E5", 1), ("G5", 1), ("E5", 4)]
BEAT = 60 / 72


def motif(buf, t0, gain=0.22, oct_shift=1.0, notes=MOTIF):
    t = t0
    for note, b in notes:
        add(buf, musicbox(hz(note) * oct_shift, 1.8), t, gain, pan=0.15)
        t += b * BEAT


def main():
    buf = np.zeros((N, 2), np.float32)
    # ---- pad: C - Am - F - G, two bars each, slow swells
    chords = [("C3", "G3", "E4"), ("A2", "E3", "C4"), ("F2", "C3", "A3"), ("G2", "D3", "B3")]
    bar = 4 * BEAT
    seg = 2 * bar
    t = 0.0
    k = 0
    tt = np.arange(int(seg * SR) + int(SR * 1.5)) / SR
    while t < DUR:
        ch = chords[k % 4]
        sig = np.zeros(len(tt), np.float32)
        for nn in ch:
            fq = hz(nn)
            sig += (np.sin(2 * np.pi * fq * tt) + 0.3 * np.sin(2 * np.pi * fq * 2.003 * tt)).astype(np.float32)
        sig *= env_adsr(len(tt), 1.2, 0, 1, 1.5)
        add(buf, sig * 0.5, t, 0.05, pan=-0.2)
        add(buf, sig * 0.5, t + 0.013, 0.05, pan=0.2)
        t += seg
        k += 1
    # ---- melody statements on story beats
    for t0, g in ((0.5, 0.18), (17.5, 0.2), (97.0, 0.16), (129.5, 0.15), (162.0, 0.17), (198.0, 0.22),
                  (209.0, 0.18)):
        motif(buf, t0, g)
    # playful plucks under the failed attempts (gentle humour)
    for i, t0 in enumerate(np.arange(40.0, 86.0, BEAT)):
        add(buf, musicbox(hz("C3" if i % 2 == 0 else "G3") * 2, 0.5), t0, 0.09, pan=-0.3)
    # ---- SFX
    cues = TL.CUES
    for t0 in cues["tink"]:
        add(buf, tink(), t0, 0.32, pan=-0.1)
    add(buf, whoosh(1.2, 200, 900, 11) * np.linspace(0.3, 1, int(1.2 * SR)), cues["strain"][0], 0.05)
    for j in range(16):  # pots rattle while wobbling
        add(buf, thump(0.12, 220 + 30 * (j % 3)), cues["wobble"][0] + j / 3.0, 0.06, pan=0.1 * (j % 3 - 1))
    add(buf, whoosh(0.6, 150, 1200, 12), cues["flop"][0] - 0.3, 0.16)
    add(buf, thump(0.4, 70), cues["flop"][0] + 0.3, 0.22)
    for t0 in cues["rustle"]:
        r = whoosh(1.4, 1500, 6000, int(t0)) * (0.5 + 0.5 * np.sin(np.linspace(0, 40, int(1.4 * SR))) ** 2)
        add(buf, r, t0, 0.07)
    n = int(0.25 * SR)
    tp = np.arange(n) / SR
    pop = np.sin(2 * np.pi * np.cumsum(np.linspace(300, 900, n)) / SR) * np.exp(-tp * 14)
    add(buf, pop.astype(np.float32), cues["pop"][0], 0.14)
    for j, note in enumerate(("C6", "E6", "G6")):
        add(buf, musicbox(hz(note), 1.2), cues["idea"][0] + j * 0.14, 0.12, pan=0.2)
    add(buf, whoosh(0.9, 250, 1800, 21), cues["lift"][0], 0.06)
    add(buf, thump(0.35, 110), cues["set_down"][0], 0.12)
    add(buf, whoosh(0.5, 2000, 6000, 22), cues["set_down"][0], 0.03)
    for t0 in cues["slide"]:
        d = 6.0
        sc = band_noise(int(d * SR), 400, 1600, int(t0)) * env_adsr(int(d * SR), 0.6, 0, 1, 0.8)
        sc *= 0.7 + 0.3 * np.sin(np.linspace(0, 2 * np.pi * 9, int(d * SR)))
        add(buf, sc, t0, 0.035)
    for t0 in cues["bloom"]:
        add(buf, sparkle(seed=int(t0)), t0, 0.5, pan=0.25)
    # ---- closing hum: the motif, hummed twice (second time slower & softer)
    h0 = cues["hum_start"][0]
    hum = hum_line(MOTIF, BEAT * 1.05)
    add(buf, hum, h0, 0.20)
    add(buf, musicbox(hz("C5"), 3.0), h0, 0.06)
    # ---- wing flutter, driven by the rendered wingbeat (very quiet)
    states = TL.all_states()
    flut_env = np.zeros(N, np.float32)
    spf = SR // TL.FPS
    for s in states:
        L = s["lumi"]
        if L is None or s["closeup"] or not L.get("flying", True):
            continue
        ph = L["phase"]
        rate = L.get("rate", 1.5)
        e = abs(float(stroke(ph + 0.02)) - float(stroke(ph - 0.02))) * 12 * min(rate / 1.5, 2.0)
        i = s["f"] * spf
        flut_env[i:i + spf] = min(e, 1.0)
    kernel = np.ones(int(0.02 * SR)) / int(0.02 * SR)
    flut_env = np.convolve(flut_env, kernel, mode="same")
    flutter = band_noise(N, 120, 900, 99) * flut_env
    buf[:, 0] += flutter * 0.035
    buf[:, 1] += flutter * 0.035
    # ---- master: gentle fade-in on the very first ms (no click) and fade-out with the picture
    t = np.arange(N) / SR
    fade = np.clip((DUR - 0.4 - t) / 4.6, 0, 1) ** 1.5
    fade[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    buf *= fade[:, None]
    peak = np.abs(buf).max()
    buf *= 0.70 / peak  # peak at about -3 dBFS
    out = ROOT / "renders/ep01_v0_audio.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())
    rms = 20 * math.log10(float(np.sqrt((buf ** 2).mean())) + 1e-9)
    print(f"wrote {out}  peak {20 * math.log10(0.70):.1f} dBFS  rms {rms:.1f} dBFS  pre-norm peak {peak:.2f}")


if __name__ == "__main__":
    main()
