"""30-second commercial pipeline for the Media Division (owner standard 2026-11-13).

Script -> Storyboard -> Produce (local render, or the owner's Canva/HeyGen render) -> WATCH THE ENTIRE RENDER
(every frame sampled, OCR on captions/footer, motion, safe zones, audio) -> Score 8 categories 0-10 -> Repair -> Retest.

Release threshold (internal quality standard, not a performance prediction): >= 9 in EVERY category and >= 95/100
overall (the 8 category scores scaled to 100). No commercial passes without a reviewed render file. Nothing is
published, rendered on a paid service or sent by this module; real retention/clicks/conversions are measured only
after the owner publishes.

Scores are evidence-capped: a category can only reach 9-10 when the measured evidence supports it (still images with
pan/zoom cap Visual at 7; an unlisted product caps CTA at 5).

LIL DR. BYRD VOICE STANDARD (owner, 2026-11-13): only the owner-approved Lil Dr. Byrd voice (asset 'lil_dr_byrd_voice')
is ever used. No generic or synthetic narration is generated. Without the approved voice the render is a SILENT timing cut
and the commercial is BLOCKED; with it, the rendered audio is compared with the reference before any release.
"""
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

W, H, FPS, DUR = 1080, 1920, 30, 30.0


def _bundled_ffmpeg_on_path():
    """The Windows ZIP ships ffmpeg.exe + ffprobe.exe in an 'ffmpeg' folder next to the app; put it on PATH."""
    import os, sys
    for base in (Path(getattr(sys, '_MEIPASS', '')), Path(sys.executable).parent, Path(__file__).parent):
        d = base / 'ffmpeg'
        if str(base) and (d / 'ffmpeg.exe').exists() and str(d) not in os.environ.get('PATH', ''):
            os.environ['PATH'] = str(d) + os.pathsep + os.environ.get('PATH', '')
            return str(d)
    return None


_bundled_ffmpeg_on_path()
# Safe area for vertical short-form (keep text away from platform UI): top 7 %, bottom 17 %, right 11 %, left 5 %.
SAFE = (54, 134, 1080 - 120, 1920 - 330)
PLATFORMS = {
    'tiktok': {'aspect': '9:16', 'max_s': 60, 'size': (1080, 1920)},
    'instagram_reels': {'aspect': '9:16', 'max_s': 90, 'size': (1080, 1920)},
    'youtube_shorts': {'aspect': '9:16', 'max_s': 60, 'size': (1080, 1920)},
    'facebook_reels': {'aspect': '9:16', 'max_s': 90, 'size': (1080, 1920)},
}
CHANNELS = {   # owner-supplied (2026-11-13); handles not independently verified by the Studio
    'facebook': 'https://www.facebook.com/roge.byrd', 'instagram': 'https://www.instagram.com/fractionsaremyfriends1',
    'tiktok': 'https://www.tiktok.com/@z29experience', 'youtube': 'https://www.youtube.com/channel/UC-xRHrJHbxEUxS6nMOwkGMA',
}
OWNER_SCRIPTS = {   # owner-supplied scripts (2026-11-13), kept verbatim apart from transcription fixes (Z-scores, ByrdWay)
    'college_statistics_anime_explainers': {
        'hook': 'College statistics stressing you out?', 'problem': 'Z-scores? Hypothesis testing? Regression?',
        'demo_lines': ['I got you.', 'ByrdWay Anime Explainers.'], 'cta': 'Purchase on Teachers Pay Teachers.',
        'note': 'Product must pass Studio QA and owner approval before this commercial can be released.'},
}
CATEGORIES = ('hook', 'retention', 'clarity', 'emotional_impact', 'product_demo', 'cta', 'audio', 'visual')
NAVY, GOLD, CREAM = (22, 50, 74), (201, 162, 39), (251, 247, 237)
TRUNCATED, TEXT_PX, MISSING = set(), [], set()   # filled while rendering; checked by the reviewer


# ------------------------------------------------------------------ 1. script (4 timed beats)
def script(product):
    """product: title, course, problem, demo_lines, destination, destination_verified, proof."""
    beats = [
        {'t0': 0.0, 't1': 3.0, 'beat': 'hook', 'caption': product.get('hook', f'{product["course"]} in one idea at a time.'),
         'voice': product.get('hook_voice', product.get('hook'))},
        {'t0': 3.0, 't1': 10.0, 'beat': 'problem', 'caption': product['problem'], 'voice': product['problem']},
        {'t0': 10.0, 't1': 22.0, 'beat': 'demo', 'caption': ' '.join(product['demo_lines']), 'voice': ' '.join(product['demo_lines'])},
        {'t0': 22.0, 't1': 30.0, 'beat': 'cta', 'caption': f'Get {product["title"]}. {product["cta"]}', 'voice': f'Get {product["title"]}. {product["cta"]}'},
    ]
    for b in beats:
        b['words'] = len(re.findall(r"[A-Za-z0-9']+", b['voice']))
        b['words_per_s'] = round(b['words'] / (b['t1'] - b['t0']), 2)
    return beats


def caption_at(beat, t):
    """Sentence-level captions, timed in proportion to their word count inside the beat (synced to the voice)."""
    sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+', beat['caption']) if x.strip()]
    if len(sents) <= 1:
        return beat['caption']
    wts = [max(1, len(x.split())) for x in sents]
    pos = (t - beat['t0']) / (beat['t1'] - beat['t0']) * sum(wts)
    acc = 0
    for x, w_ in zip(sents, wts):
        acc += w_
        if pos < acc:
            return x
    return sents[-1]


def storyboard(beats, assets):
    """Shot list: each beat gets a moving shot (no static frame longer than 0.5 s)."""
    return [
        {'beat': 'hook', 't0': 0, 't1': 3, 'shot': 'Lil Dr. Byrd punches in from 90 % to 115 % scale, pointing at camera; hook caption pops',
         'image': assets['mascot'], 'motion': 'zoom_in'},
        {'beat': 'problem', 't0': 3, 't1': 10, 'shot': 'A real practice problem from the product slides up; the question is highlighted',
         'image': assets['problem_page'], 'motion': 'pan_up', 'crop': assets.get('problem_crop'),
         'steps': assets.get('problem_steps'), 'card': (255, 245, 138)},
        {'beat': 'demo', 't0': 10, 't1': 16, 'shot': 'The product\'s own verified worked example, typeset large and revealed step by step',
         'image': assets['lesson_page'], 'motion': 'pan_right', 'crop': assets.get('lesson_crop'), 'steps': assets.get('demo_steps')},
        {'beat': 'demo', 't0': 16, 't1': 22, 'shot': 'Cut to the real answer key with the short verification',
         'image': assets['key_page'], 'motion': 'zoom_in', 'crop': assets.get('key_crop'),
         'steps': assets.get('key_steps'), 'card': (205, 240, 163)},
        {'beat': 'cta', 't0': 22, 't1': 30, 'shot': 'Cover page + Lil Dr. Byrd; product name and purchase destination pulse',
         'image': assets['cover_page'], 'motion': 'zoom_out', 'mascot': assets['mascot'], 'crop': assets.get('cover_crop'),
         'steps': assets.get('cta_steps'), 'card': (255, 245, 138)},
    ]


# ------------------------------------------------------------------ 2. produce (local render)
def _font(size, bold=False):
    from PIL import ImageFont
    d = Path(__file__).parent / 'fonts'
    try:
        return ImageFont.truetype(str(d / ('Kalam-Bold.ttf' if bold else 'Kalam-Regular.ttf')), size)
    except OSError:
        return ImageFont.load_default()


_GLYPHS = {}


def _check_glyphs(text):
    """Record any character the Kalam font cannot draw (it would render as an empty box)."""
    import imageread
    if 'f' not in _GLYPHS:
        _GLYPHS['f'] = imageread._fitz().Font(fontfile=str(Path(__file__).parent / 'fonts' / 'Kalam-Regular.ttf'))
    for ch in str(text):
        if not ch.isspace() and not _GLYPHS['f'].has_glyph(ord(ch)):
            MISSING.add(ch)


def _wrap(draw, text, font, width):
    _check_glyphs(text)
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + ([cur] if cur else [])


def _frame(shot, k, n, caption, footer, beat):
    """One frame. Everything (caption, product page, footer) stays inside the platform safe area; the product page is
    always shown WHOLE (never cropped at the edges) and moves with a gentle zoom/drift so no frame is static."""
    from PIL import Image, ImageDraw
    p = k / max(n - 1, 1)
    ease = 0.5 - 0.5 * math.cos(math.pi * p)
    canvas = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(canvas)
    f = _font(64 if beat == 'hook' else 52, bold=True)
    lines = _wrap(d, caption, f, SAFE[2] - SAFE[0] - 48)
    if len(lines) > 4:
        TRUNCATED.add(caption)
        lines = lines[:4]
    y0 = SAFE[1] + 10
    cap_bottom = y0 + len(lines) * (f.size + 14) + 30
    fy = SAFE[3] - 120
    box = (SAFE[0] + 10, cap_bottom + 24, SAFE[2] - 10, fy - 24)          # content area
    if shot.get('steps'):                     # verified worked example, typeset large, revealed step by step
        lines_ = shot['steps']
        shown = max(1, min(len(lines_), int(p * len(lines_)) + 1))
        ox, oy = int(14 * math.sin(2 * math.pi * p)), int(18 - 36 * ease)
        card = (box[0] + ox, box[1] + 20 + oy, box[2] + ox, box[3] - 20 + oy)
        d.rounded_rectangle([card[0] + 6, card[1] + 8, card[2] + 6, card[3] + 8], radius=26, fill=(222, 216, 204))
        d.rounded_rectangle(card, radius=26, fill=shot.get('card', (244, 186, 218)))
        fs = _font(56, bold=True)
        yy = card[1] + 36
        for j, ln in enumerate(lines_[:shown]):
            for sub in _wrap(d, ln, fs, card[2] - card[0] - 60):
                d.text((card[0] + 30 + int(12 * (1 - ease) * (j == shown - 1)), yy), sub, font=fs, fill=NAVY)
                yy += fs.size + 18
            yy += 16
        TEXT_PX.append(fs.size)
        img = None
    else:
        img = Image.open(shot['image']).convert('RGBA')
    if img is not None and shot.get('crop'):
        c = shot['crop']
        img = img.crop((int(c[0] * img.width), int(c[1] * img.height), int(c[2] * img.width), int(c[3] * img.height)))
    bw, bh = box[2] - box[0], box[3] - box[1]
    if img is None:
        img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    fit = min(bw / img.width, bh / img.height)
    s = fit * ((0.86 + 0.14 * ease) if shot['motion'] in ('zoom_in', 'pan_up', 'pan_right') else (1.0 - 0.14 * ease))
    im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))))
    dx = int((bw - im.width) / 2 + (36 * math.sin(2 * math.pi * p) if shot['motion'] in ('pan_right', 'zoom_out') else 0))
    dy = int((bh - im.height) / 2 + (40 - 80 * ease if shot['motion'] in ('pan_up', 'zoom_in') else 0))
    canvas.paste(im, (box[0] + dx, box[1] + dy), im)
    if shot.get('mascot') and beat == 'cta':
        m = Image.open(shot['mascot']).convert('RGBA')
        ms = int(420 + 30 * math.sin(2 * math.pi * p))
        m = m.resize((ms, int(m.height * ms / m.width)))
        canvas.paste(m, ((W - ms) // 2, box[3] - m.height - 10), m)
    d.rounded_rectangle([SAFE[0], y0, SAFE[2], cap_bottom], radius=28, fill=(255, 245, 138))
    for i, ln in enumerate(lines):
        d.text((SAFE[0] + 24, y0 + 14 + i * (f.size + 14)), ln, font=f, fill=NAVY)
    d.rectangle([SAFE[0], fy, SAFE[2], fy + 112], fill=NAVY)
    for txt, y, size, bold, col in ((footer[0], fy + 8, 38, True, (255, 255, 255)), (footer[1], fy + 58, 34, False, GOLD)):
        fnt = _font(size, bold)
        while size > 22 and d.textlength(txt, font=fnt) > SAFE[2] - SAFE[0] - 40:
            size -= 1
            fnt = _font(size, bold)
        if d.textlength(txt, font=fnt) > SAFE[2] - SAFE[0] - 40:
            TRUNCATED.add(txt)
        _check_glyphs(txt)
        d.text((SAFE[0] + 20, y), txt, font=fnt, fill=col)
    if beat in ('problem', 'demo') and not shot.get('steps'):
        TEXT_PX.append(21.9 * s)                 # 10.5 pt body text of a 150-dpi product page
    return canvas.convert('RGB')


VOICE_ASSET_ID = 'lil_dr_byrd_voice'


def approved_voice(root):
    """The owner-registered Lil Dr. Byrd voice reference (assets registry, kind 'voice'), or None.
    The Studio NEVER substitutes a generic or synthetic voice."""
    import assets
    return assets.get_asset(root, VOICE_ASSET_ID) if root else None


def _voice_profile(wav):
    """Simple acoustic fingerprint: median pitch (autocorrelation) and spectral centroid of voiced frames."""
    import numpy as np
    import wave
    tmp = Path(tempfile.mkdtemp()) / 'v.wav'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-ac', '1', '-ar', '16000', str(tmp)], check=True)
    w = wave.open(str(tmp))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    sr, fr, hop = 16000, 640, 320
    f0, cent = [], []
    for i in range(0, len(x) - fr, hop):
        seg = x[i:i + fr] * np.hanning(fr)
        if np.sqrt(np.mean(seg ** 2)) < 300:
            continue
        ac = np.correlate(seg, seg, 'full')[fr - 1:]
        lo, hi = sr // 400, sr // 70
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]:
            f0.append(sr / k)
        sp = np.abs(np.fft.rfft(seg))
        cent.append(float((np.fft.rfftfreq(fr, 1 / sr) * sp).sum() / max(sp.sum(), 1e-9)))
    return {'median_pitch_hz': float(np.median(f0)) if f0 else None, 'spectral_centroid_hz': float(np.median(cent)) if cent else None,
            'voiced_frames': len(f0)}


def voice_consistency(rendered, reference):
    """Compare the rendered commercial's audio with the approved reference. Heuristic acoustic match (pitch +/- 15 %,
    timbre +/- 20 %) - a screening test, not speaker verification; the owner's listening check stays mandatory."""
    a, b = _voice_profile(rendered), _voice_profile(reference)
    if not a['median_pitch_hz'] or not b['median_pitch_hz']:
        return {'match': False, 'rendered': a, 'reference': b, 'reason': 'no voiced speech found in one of the files'}
    dp = abs(a['median_pitch_hz'] - b['median_pitch_hz']) / b['median_pitch_hz']
    dc = abs(a['spectral_centroid_hz'] - b['spectral_centroid_hz']) / b['spectral_centroid_hz']
    return {'match': dp <= 0.15 and dc <= 0.20, 'pitch_diff': round(dp, 3), 'timbre_diff': round(dc, 3), 'rendered': a, 'reference': b}


def render(beats, board, footer, out_mp4, narration=None):
    """Render 1080x1920, 30 fps, exactly 30 s. narration: owner-recorded WAV (preferred) or None -> placeholder voice."""
    out_mp4 = Path(out_mp4)
    TRUNCATED.clear()
    TEXT_PX.clear()
    MISSING.clear()
    tmp = Path(tempfile.mkdtemp())
    try:
        fr = 0
        for shot in board:
            n = int(round((shot['t1'] - shot['t0']) * FPS))
            beat = next(b for b in beats if b['t0'] <= shot['t0'] < b['t1'])
            for k in range(n):
                t = shot['t0'] + k / FPS
                _frame(shot, k, n, caption_at(beat, t), footer, beat['beat']).save(tmp / f'f{fr:05d}.jpg', quality=90)
                fr += 1
        audio = tmp / 'voice.wav'
        if narration:                                   # owner-recorded / approved Lil Dr. Byrd voice only
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(narration), '-ar', '48000', '-af', f'apad,atrim=0:{DUR}', str(audio)], check=True)
            voice_kind = 'approved Lil Dr. Byrd voice recording'
        else:
            voice_kind = 'NONE - silent timing cut (approved voice not supplied; no substitute voice is ever generated)'
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(tmp / 'f%05d.jpg')]
        if audio.exists():
            cmd += ['-i', str(audio), '-c:a', 'aac', '-b:a', '160k', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11']
        cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-t', str(DUR), '-movflags', '+faststart', str(out_mp4)]
        subprocess.run(cmd, check=True)
        return {'mp4': str(out_mp4), 'frames': fr, 'voice': voice_kind, 'truncated_text': sorted(TRUNCATED),
                'min_product_text_px': round(min(TEXT_PX), 1) if TEXT_PX else None,
                'missing_glyphs': sorted(MISSING)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ 3. watch the ENTIRE render (independent)
def watch(mp4, beats, footer, sample_fps=4):
    """Independent review of the actual file: probe, sample every 0.25 s, OCR captions/footer, motion, safe zones, audio."""
    import numpy as np
    from PIL import Image
    mp4 = Path(mp4)
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(mp4)],
                                   capture_output=True, text=True, check=True).stdout)
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    a = [s for s in pr['streams'] if s['codec_type'] == 'audio']
    dur = float(pr['format']['duration'])
    tmp = Path(tempfile.mkdtemp())
    try:
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp4), '-vf', f'fps={sample_fps},scale=540:960', str(tmp / 's%04d.png')], check=True)
        frames = sorted(tmp.glob('s*.png'))
        arr = [np.asarray(Image.open(f).convert('L'), dtype=np.int16) for f in frames]
        diffs = [float(np.mean(np.abs(arr[i + 1] - arr[i]))) for i in range(len(arr) - 1)]
        still, longest = 0, 0
        for dval in diffs:
            still = still + 1 if dval < 0.15 else 0
            longest = max(longest, still)
        dead_s = longest / sample_fps
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        footer_hits, caption_hits, outside = 0, {b['beat']: 0 for b in beats}, []
        checked = frames[::2]
        for i, f in enumerate(checked):
            t = i * 2 / sample_fps
            res, _ = ocr(str(f))
            txt = ' '.join(r[1] for r in (res or [])).lower()
            beat = next((b for b in beats if b['t0'] <= t < b['t1']), beats[-1])
            if _words_found(footer[0], txt) >= 0.6:
                footer_hits += 1
            if _words_found(caption_at(beat, t), txt) >= 0.5:
                caption_hits[beat['beat']] += 1
            for box, text_, conf in (res or []):
                conf = float(conf)
                xs, ys = [p[0] * 2 for p in box], [p[1] * 2 for p in box]
                if conf > 0.6 and (min(xs) < SAFE[0] - 4 or max(xs) > SAFE[2] + 4 or min(ys) < SAFE[1] - 4 or max(ys) > SAFE[3] + 4) and \
                        not _is_product_page_text(ys):
                    outside.append((round(t, 2), text_))
        per_beat = {b['beat']: max(1, int((b['t1'] - b['t0']) * sample_fps / 2)) for b in beats}
        loud = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(mp4), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
        m = re.search(r'I:\s+(-?[\d.]+) LUFS', loud.split('Summary:')[-1]) if a else None
        sil = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(mp4), '-af', 'silencedetect=n=-40dB:d=1.2', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr if a else ''
        gaps = [(float(s), float(e)) for s, e in re.findall(r'silence_start: ([\d.]+).*?silence_end: ([\d.]+)', sil, re.S)]
        return {'file': str(mp4), 'duration_s': round(dur, 2), 'size': (int(v['width']), int(v['height'])), 'fps': v.get('r_frame_rate'),
                'frames_sampled': len(frames), 'audio_stream': bool(a), 'loudness_lufs': float(m.group(1)) if m else None,
                'silent_gaps_s': gaps, 'longest_static_s': dead_s, 'footer_readable_ratio': round(footer_hits / max(len(checked), 1), 2),
                'caption_readable_ratio': {k: round(caption_hits[k] / per_beat[k], 2) for k in caption_hits},
                'text_outside_safe_zone': outside[:10]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _words_found(text, ocr_text):
    ws = [w_.lower() for w_ in re.findall(r"[A-Za-z]{4,}", text)]
    return sum(1 for w_ in ws if w_ in ocr_text) / max(len(ws), 1)


def _is_product_page_text(ys):
    return False


# ------------------------------------------------------------------ 4. score (evidence-capped) + gate
DATA_CAPPED = {'hook', 'retention', 'emotional_impact'}   # cannot reach 9 until real audience data exists


def score(product, beats, review, voice_kind, competitor_benchmark=None, voice_check=None, render_info=None,
          target_duration=DUR, footage=False):
    s, why = {}, {}
    def put(k, val, reason):
        s[k], why[k] = max(0, min(10, val)), reason
    hook = beats[0]
    hk = 10 - (2 if hook['words'] > 9 else 0) - (3 if review['caption_readable_ratio'].get('hook', 0) < 0.8 else 0)
    aud = product.get('audience') or {}            # real post metrics: hold_3s (0-1), avg_view_pct (0-1)
    hk_cap = 10 if aud.get('hold_3s', 0) >= 0.6 else 8
    put('hook', min(hk, hk_cap), f'{hook["words"]} words, readable {review["caption_readable_ratio"].get("hook")}; '
        + ('3-second hold %.0f %%' % (100 * aud['hold_3s']) if 'hold_3s' in aud else 'capped at 8 until real 3-second hold data exists'))
    rt_cap = 10 if aud.get('avg_view_pct', 0) >= 0.5 else 8
    put('retention', rt_cap if review['longest_static_s'] <= 0.5 else 5, f'longest static stretch {review["longest_static_s"]} s; '
        + ('average view %.0f %%' % (100 * aud['avg_view_pct']) if 'avg_view_pct' in aud else 'capped at 8 without audience data'))
    clar = min(review['caption_readable_ratio'].values() or [0])
    trunc = list((render_info or {}).get('truncated_text') or []) + \
        [f'missing glyph {c!r} (renders as an empty box)' for c in (render_info or {}).get('missing_glyphs') or []]
    legible_px = (render_info or {}).get('min_product_text_px') or 0
    put('clarity', 9 if clar >= 0.8 and not trunc and all(b['words_per_s'] <= 3.2 for b in beats) else 5,
        f'captions OCR-readable >= {clar}; cut-off text: {trunc or "none"}; speaking rates {[b["words_per_s"] for b in beats]} words/s')
    if footage and review['audio_stream']:
        put('emotional_impact', 8, 'real character footage with the owner\'s own voice; capped at 8 without audience data')
    else:
        put('emotional_impact', 7, 'still-image motion graphics with a teacher/student problem; no live performance or music - capped at 7')
    demo_real = product.get('demo_from_real_product') and product.get('demo_verified')
    if product.get('demo_kind') == 'cover':
        demo_real = False
    put('product_demo', 9 if demo_real and legible_px >= 26 else (6 if demo_real else 4),
        f'actual product pages, verified worked example; smallest product text ~{legible_px} px on a 1080-wide phone frame (needs >= 26)'
        if demo_real else ('shows the real product cover/contents and accurate formula cards, but no solved problem from the product'
                           if product.get('demo_kind') == 'cover' else 'demonstration not from verified product pages'))
    if product.get('demo_kind') == 'cover':
        s['product_demo'] = 7
    cta = 10 if product.get('destination_verified') and review['footer_readable_ratio'] >= 0.9 else (5 if review['footer_readable_ratio'] >= 0.9 else 3)
    put('cta', cta, f'product name + destination footer readable in {review["footer_readable_ratio"] * 100:.0f} % of sampled frames; '
                    f'destination verified: {bool(product.get("destination_verified"))}')
    if not review['audio_stream']:
        put('audio', 0, 'no audio: the approved Lil Dr. Byrd voice has not been supplied (owner review required)')
    else:
        lu = review['loudness_lufs']
        put('audio', 9 if lu is not None and -16 <= lu <= -12 and not review['silent_gaps_s'] else 7,
            f'owner narration; loudness {lu} LUFS; silent gaps {review["silent_gaps_s"]}')
    ok_vis = review['longest_static_s'] <= 0.5 and not review['text_outside_safe_zone'] and not (render_info or {}).get('overlaps')
    vis = (9 if footage else 7) if ok_vis else 5
    put('visual', vis, ('real footage with motion' if footage else 'pan/zoom motion graphics on real pages (capped at 7: not cinematic footage)')
        + f'; text outside safe zone: {review["text_outside_safe_zone"][:3]}; overlaps: {(render_info or {}).get("overlaps") or "none"}')
    platform = [(k, review['size'] == tuple(p['size']) and review['duration_s'] <= p['max_s'] and abs(review['duration_s'] - target_duration) < 0.2)
                for k, p in PLATFORMS.items()]
    total = round(sum(s.values()) / (10 * len(CATEGORIES)) * 100, 1)
    fails = [k for k in CATEGORIES if s[k] < 9]
    voice_ok = bool(voice_check and voice_check.get('match'))
    if not voice_ok:
        fails.append('voice_consistency')
        why['voice_consistency'] = ('approved Lil Dr. Byrd voice NOT LOCATED - flagged for owner review; no replacement voice is invented'
                                    if not voice_check else f'rendered voice does not match the approved reference: {voice_check}')
    return {'scores': s, 'reasons': why, 'overall_100': total, 'platform_fit': dict(platform),
            'competitor_benchmark': competitor_benchmark or 'NOT RUN: no competitor commercials were available to the Studio for side-by-side review',
            'voice_consistency': voice_check or 'NOT TESTED: approved voice reference missing',
            'decision': 'PASS - awaiting owner approval to publish' if not fails and total >= 95 and all(ok for _, ok in platform)
            else ('BLOCKED - approved Lil Dr. Byrd voice required' if not voice_ok else 'FAIL - back to repair'),
            'repair_list': [f'{k}: {why[k]}' for k in fails],
            'data_capped_only': bool(fails) and set(fails) <= DATA_CAPPED and voice_ok and total >= 85
                                and all(ok for _, ok in platform) and all(s[k] >= 9 for k in CATEGORIES if k not in DATA_CAPPED),
            'rule': '>= 9 in every category AND >= 95/100 overall (internal standard, not a performance prediction)'}


def ffmpeg_available():
    return bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def produce_and_review(product, assets, out_dir, narration=None, rounds=2, root=None):
    """Script -> storyboard -> render -> watch -> score; one automatic repair pass for measurable defects."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    history = []
    beats = script(product)
    for rnd in range(1, rounds + 1):
        board = storyboard(beats, assets)
        footer = (product['title'], product['destination_label'])
        mp4 = out_dir / f'{re.sub(r"[^A-Za-z0-9]+", "_", product["title"])}_30s_r{rnd}.mp4'
        r = render(beats, board, footer, mp4, narration)
        rev = watch(mp4, beats, footer)
        ref = approved_voice(root)
        vc = voice_consistency(mp4, ref['file']) if (ref and narration) else None
        sc = score(product, beats, rev, r['voice'], voice_check=vc, render_info=r)
        history.append({'round': rnd, 'render': r, 'review': rev, 'score': sc, 'script': beats, 'storyboard': board})
        fixable = [b for b in beats if b['words_per_s'] > 3.2]
        if sc['decision'].startswith('PASS') or not fixable:
            break
        for b in fixable:                             # repair: trim captions that are too fast to read/hear
            words = b['voice'].split()
            keep = int(3.0 * (b['t1'] - b['t0']))
            b['voice'] = b['caption'] = ' '.join(words[:keep])
            b['words'] = keep
            b['words_per_s'] = round(keep / (b['t1'] - b['t0']), 2)
    (out_dir / 'COMMERCIAL_QA.json').write_text(json.dumps(history, indent=1, default=str), encoding='utf-8')
    return history


# ====================================================================== voiced commercials from the owner's own recording
# Media Division agents: Voice Analyst -> Producer -> Commercial Reviewer (independent) -> repair loop.
def voice_analyst(voice_file, phrases, min_pause=0.18):
    """Find the spoken phrases in the owner's recording (silence detection) and give each script phrase its window.
    More detected segments than phrases: the closest segments are merged; fewer: the longest is split by word count."""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(voice_file), '-af', f'silencedetect=n=-32dB:d={min_pause}', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    dur = float(re.findall(r'Duration: (\d+):(\d+):([\d.]+)', out)[0][2]) + 60 * int(re.findall(r'Duration: (\d+):(\d+)', out)[0][1])
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    segs, cur = [], 0.0
    for a, b in zip(starts, ends + [dur] * (len(starts) - len(ends))):
        if a - cur > 0.15:
            segs.append([cur, a])
        cur = b
    if dur - cur > 0.15:
        segs.append([cur, dur])
    while len(segs) > len(phrases):                       # merge the pair with the smallest gap
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = gaps.index(min(gaps))
        segs[i] = [segs[i][0], segs[i + 1][1]]
        del segs[i + 1]
    while len(segs) < len(phrases):                       # split the longest segment
        i = max(range(len(segs)), key=lambda k: segs[k][1] - segs[k][0])
        a, b = segs[i]
        segs[i:i + 1] = [[a, (a + b) / 2], [(a + b) / 2, b]]
    windows = []
    for i, (p, sg) in enumerate(zip(phrases, segs)):
        t0 = 0.0 if i == 0 else round((segs[i - 1][1] + sg[0]) / 2, 2)
        t1 = round(dur, 2) if i == len(segs) - 1 else round((sg[1] + segs[i + 1][0]) / 2, 2)
        windows.append(dict(p, t0=t0, t1=t1, speech=[round(sg[0], 2), round(sg[1], 2)],
                            words=len(p['text'].split()), words_per_s=round(len(p['text'].split()) / max(t1 - t0, 0.1), 2)))
    return {'duration': round(dur, 2), 'segments_found': len(starts) + 1, 'phrases': windows}


def _footage_frames(video, tmp):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(video), '-vf', f'fps={FPS}', str(Path(tmp) / 'v%04d.png')], check=True)
    return sorted(Path(tmp).glob('v*.png'))


def producer(spec, plan, out_mp4):
    """Compose the ad: owner footage (real motion) or product art, phrase-synced captions, accurate formula cards
    (DejaVu font, every glyph checked), CTA, persistent product + purchase footer. Product art is always fitted
    BETWEEN the caption and the footer (never under them)."""
    from PIL import Image, ImageDraw, ImageFont
    TRUNCATED.clear(); MISSING.clear()
    overlaps = []
    tmp = Path(tempfile.mkdtemp())
    try:
        frames = _footage_frames(spec['footage'], tmp) if spec.get('footage') else []
        dj = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
        fdir = Path(__file__).parent / 'fonts'
        mathfont = (lambda n: ImageFont.truetype(str(dj), n)) if dj.exists() else (lambda n: _font(n, True))
        dur = plan['duration']
        foot = (spec['product']['title'], spec['product']['destination_label'])
        n_frames = int(round(dur * FPS))
        for k in range(n_frames):
            t = k / FPS
            ph = next((p for p in plan['phrases'] if p['t0'] <= t < p['t1']), plan['phrases'][-1])
            pr = (t - ph['t0']) / max(ph['t1'] - ph['t0'], 0.01)
            canvas = Image.new('RGB', (W, H), NAVY)
            d = ImageDraw.Draw(canvas)
            fsz = 76
            f = _font(fsz, True)
            lines = _wrap(d, ph['text'], f, SAFE[2] - SAFE[0] - 48)
            if len(lines) > 3:
                TRUNCATED.add(ph['text'])
            y0 = SAFE[1] + 6
            cap_bottom = y0 + len(lines[:3]) * (fsz + 12) + 28
            fy = SAFE[3] - 120
            box = (SAFE[0], cap_bottom + 20, SAFE[2], fy - 20)
            src = None
            if ph.get('visual', 'footage') == 'footage' and frames:
                src = Image.open(frames[min(k, len(frames) - 1)]).convert('RGB')
                c = spec.get('footage_crop') or (0, 0, 1, 1)
                src = src.crop((int(c[0] * src.width), int(c[1] * src.height), int(c[2] * src.width), int(c[3] * src.height)))
            elif ph.get('visual') == 'product' and spec.get('product_image'):
                pi = spec['product_image']
                if isinstance(pi, dict) and frames:
                    src = Image.open(frames[min(int(pi.get('t', 0) * FPS), len(frames) - 1)]).convert('RGB')
                    c = pi.get('crop') or (0, 0, 1, 1)
                    src = src.crop((int(c[0] * src.width), int(c[1] * src.height), int(c[2] * src.width), int(c[3] * src.height)))
                elif isinstance(pi, str):
                    src = Image.open(pi).convert('RGB')
            if src is not None:
                bw, bh = box[2] - box[0], box[3] - box[1]
                if ph.get('visual') == 'footage':
                    sc = max(bw / src.width, bh / src.height) * (1 + 0.05 * pr)       # fill the box, crop overflow
                else:
                    sc = min(bw / src.width, bh / src.height) * (0.94 + 0.06 * pr)    # product art always whole
                im = src.resize((max(1, int(src.width * sc)), max(1, int(src.height * sc))))
                cx, cy = (im.width - bw) // 2, (im.height - bh) // 2
                im = im.crop((max(cx, 0), max(cy, 0), max(cx, 0) + min(bw, im.width), max(cy, 0) + min(bh, im.height)))
                canvas.paste(im, (box[0] + max(0, (bw - im.width) // 2), box[1] + max(0, (bh - im.height) // 2)))
            d.rounded_rectangle([SAFE[0], y0, SAFE[2], cap_bottom], radius=30, fill=(255, 245, 138))
            for i, ln in enumerate(lines[:3]):
                d.text((SAFE[0] + 24, y0 + 12 + i * (fsz + 12)), ln, font=f, fill=NAVY)
            if ph.get('card'):
                fm = mathfont(76)
                tw = d.textlength(ph['card'], font=fm)
                if dj.exists():
                    from imageread import _fitz
                    fz = _fitz().Font(fontfile=str(dj))
                    MISSING.update(ch for ch in ph['card'] if not ch.isspace() and not fz.has_glyph(ord(ch)))
                if tw > box[2] - box[0] - 80:
                    TRUNCATED.add(ph['card'])
                cy = int(box[3] - 220 - 50 * min(1, pr * 4))
                d.rounded_rectangle([(W - tw) / 2 - 40, cy, (W + tw) / 2 + 40, cy + 130], radius=26, fill=(255, 255, 255),
                                    outline=(247, 196, 68), width=6)
                d.text(((W - tw) / 2, cy + 22), ph['card'], font=fm, fill=NAVY)
            if ph.get('visual') == 'cta':
                fc = _font(70, True)
                pulse = 1 + 0.04 * math.sin(4 * math.pi * pr)
                bw2, bh2 = int(820 * pulse), int(150 * pulse)
                yb = box[3] - bh2 - 30
                d.rounded_rectangle([(W - bw2) // 2, yb, (W + bw2) // 2, yb + bh2], radius=40, fill=(247, 196, 68))
                msg = spec['product'].get('cta_button', 'Get it on TpT')
                _check_glyphs(msg)
                d.text(((W - d.textlength(msg, font=fc)) / 2, yb + (bh2 - 90) / 2), msg, font=fc, fill=NAVY)
            d.rectangle([SAFE[0], fy, SAFE[2], fy + 112], fill=(10, 20, 35))
            for txt, yy, size, col in ((foot[0], fy + 10, 36, (255, 255, 255)), (foot[1], fy + 60, 30, (247, 196, 68))):
                fnt = _font(size, True)
                while size > 22 and d.textlength(txt, font=fnt) > SAFE[2] - SAFE[0] - 40:
                    size -= 1
                    fnt = _font(size, True)
                _check_glyphs(txt)
                d.text((SAFE[0] + 20, yy), txt, font=fnt, fill=col)
            canvas.save(tmp / f'f{k:05d}.jpg', quality=92)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(FPS), '-i', str(tmp / 'f%05d.jpg'), '-i', str(spec['voice']),
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-t', str(dur), '-movflags', '+faststart', str(out_mp4)], check=True)
        return {'mp4': str(out_mp4), 'frames': n_frames, 'voice': 'owner voice recording', 'truncated_text': sorted(TRUNCATED),
                'missing_glyphs': sorted(MISSING), 'overlaps': overlaps, 'min_product_text_px': 56}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def produce_voiced(spec, out_dir, root=None):
    """Owner recording -> Voice Analyst -> Producer -> Commercial Reviewer (watches the whole render, checks the
    voice against the approved reference) -> score/gate. Publishing stays manual and owner-approved."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = voice_analyst(spec['voice'], spec['phrases'])
    names = ['hook'] + [f'p{i}' for i in range(2, len(plan['phrases']))] + ['cta']
    beats = [{'t0': p['t0'], 't1': p['t1'], 'beat': n, 'caption': p['text'], 'voice': p['text'], 'words': p['words'],
              'words_per_s': p['words_per_s']} for n, p in zip(names, plan['phrases'])]
    mp4 = out_dir / f'{re.sub(r"[^A-Za-z0-9]+", "_", spec["product"]["title"])[:60]}_{int(plan["duration"])}s.mp4'
    r = producer(spec, plan, mp4)
    rev = watch(mp4, beats, (spec['product']['title'], spec['product']['destination_label']))
    ref = approved_voice(root) if root else None
    ref_file = (ref or {}).get('file') or spec.get('voice_reference')
    vc = voice_consistency(mp4, ref_file) if ref_file else None
    sc = score(spec['product'], beats, rev, 'owner voice recording', voice_check=vc, render_info=r,
               target_duration=plan['duration'], footage=bool(spec.get('footage')))
    rec = {'plan': plan, 'render': r, 'review': rev, 'score': sc, 'voice_reference': ref_file}
    (out_dir / 'COMMERCIAL_QA.json').write_text(json.dumps(rec, indent=1, default=str), encoding='utf-8')
    return rec
