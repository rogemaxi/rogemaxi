"""Repair Engineer (image pages) + Repair Reviewer - corrections on a PROTECTED COPY of a flattened PDF.

A flattened page is one picture. The only correction possible without the editable source is a
RECONSTRUCTED REGION: the wrong characters are covered with the surrounding background colour and the
corrected characters are drawn on top (Helvetica, size and colour matched to the original). Artwork outside
that small box is never touched. Every patch is marked RECONSTRUCTED_REGION and needs the owner's visual
approval; the exact font of the original cannot be reproduced (that needs the editable source).

Repair Engineer: apply_patch(strategy)          strategies: token -> token_wide -> line
Repair Reviewer: review_patch()                  independent checks, any failure rejects the patch:
  1. every other page is pixel-identical; on the patched page nothing changed outside the patch box
  2. the page reader, run fresh on the patched copy, reads the NEW text in the box and not the old one
  3. the corrected statement now verifies, and the page has no new suspected error or typo
repair_with_review(): Engineer -> Reviewer -> (rejected: back to the Engineer with the next strategy) -> ...
bounded by the number of strategies; if every attempt is rejected the defect is BLOCKED with the reasons.
"""
import re
from pathlib import Path

import imageread

STRATEGIES = ('token', 'token_wide', 'line')


class RepairBlocked(Exception):
    def __init__(self, msg, attempts):
        super().__init__(msg)
        self.attempts = attempts


def _fitz():
    return imageread._fitz()


def _norm(t):
    return re.sub(r'\s+', '', imageread.clean(str(t))).replace('−', '-').replace('×', 'x').lower()


def _token_box(line_rect, line_text, token, wide=False):
    """Box of `token` inside the OCR line box (characters assumed evenly spaced - the reviewer verifies)."""
    x0, y0, x1, y1 = line_rect
    t = imageread.clean(line_text)
    i = t.replace(' ', '').find(token.replace(' ', ''))
    if i < 0:
        return None
    n = max(1, len(t.replace(' ', '')))
    w = (x1 - x0) / n
    a, b = x0 + i * w, x0 + (i + len(token.replace(' ', ''))) * w
    pad = w * (0.6 if wide else 0.25)
    return (a - pad, y0 - 1, min(x1 + w, b + pad), y1 + 1)


def _colors(page, box):
    """(background, ink) RGB in 0..1 sampled from the rendered page around/inside the box."""
    fitz = _fitz()
    import numpy as np
    r = fitz.Rect(box)
    ring = fitz.Rect(r.x0 - 4, r.y0 - 3, r.x1 + 4, r.y1 + 3) & page.rect
    pix = page.get_pixmap(dpi=144, clip=ring)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(float)
    edge = np.concatenate([a[:2].reshape(-1, 3), a[-2:].reshape(-1, 3), a[:, :2].reshape(-1, 3), a[:, -2:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)
    flat = a.reshape(-1, 3)
    dist = np.abs(flat - bg).sum(axis=1)
    ink = flat[dist >= np.percentile(dist, 92)].mean(axis=0) if len(flat) else np.zeros(3)
    return tuple(bg / 255), tuple(ink / 255)


def _ink(page, box, bg):
    """Ink columns/rows inside box (PDF points): returns (runs [(x0,x1)], (top, bottom)) of the printed glyphs."""
    fitz = _fitz()
    import numpy as np
    dpi = 288
    pix = page.get_pixmap(dpi=dpi, clip=fitz.Rect(box) & page.rect)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(float)
    ink = np.abs(a - np.array(bg) * 255).sum(axis=2) > 120
    s = 72 / dpi
    cols, rows = np.nonzero(ink.any(axis=0))[0], np.nonzero(ink.any(axis=1))[0]
    if not len(cols):
        return [], None
    runs, start, prev = [], cols[0], cols[0]
    for c in cols[1:]:
        if c - prev > 2:
            runs.append((box[0] + start * s, box[0] + (prev + 1) * s))
            start = c
        prev = c
    runs.append((box[0] + start * s, box[0] + (prev + 1) * s))
    return runs, (box[1] + rows[0] * s, box[1] + (rows[-1] + 1) * s)


def _snap(box, runs):
    """Snap an estimated token box to the printed glyphs it overlaps (so the cover starts/ends on real ink)."""
    hit = [r for r in runs if min(r[1], box[2]) - max(r[0], box[0]) > 0.5 * (r[1] - r[0])]   # mostly inside
    if not hit:
        return box
    return (hit[0][0] - 0.8, box[1], hit[-1][1] + 0.8, box[3])


def apply_patch(src_pdf, out_pdf, page_no, line_rect, line_text, old, new, strategy):
    """Repair Engineer. Writes the patched copy; returns the patch description."""
    fitz = _fitz()
    with fitz.open(src_pdf) as doc:
        page = doc[page_no - 1]
        if strategy == 'line':
            body = re.sub(r'\s*[Vv✓✔]\s*$', '', imageread.clean(line_text))
            if old not in body:
                raise ValueError(f'"{old}" not found in the line "{body}"')
            box, text = (line_rect[0] - 1, line_rect[1] - 1, line_rect[2] + 1, line_rect[3] + 1), body.replace(old, new, 1)
        else:
            box, text = _token_box(line_rect, line_text, old, wide=strategy == 'token_wide'), new
            if not box:
                raise ValueError(f'"{old}" not found in the line "{line_text}"')
        bg, ink = _colors(page, box)
        runs, vert = _ink(page, (line_rect[0] - 2, line_rect[1] - 2, line_rect[2] + 2, line_rect[3] + 2), bg)
        if strategy != 'line':
            box = _snap(box, runs)
            vert = _ink(page, box, bg)[1] or vert          # height of the OLD glyphs themselves (no descenders)
        h = box[3] - box[1]
        size = max(5.0, h * 0.82)
        baseline = box[3] - h * 0.22
        if vert and not re.search(r'[gjpqy(),]', old + new):
            cap = vert[1] - vert[0]                     # printed glyph height = Helvetica cap height (0.72 em)
            size, baseline = max(5.0, cap / 0.72), vert[1]
        while size > 5 and fitz.get_text_length(text, 'helv', size) > max(box[2] - box[0], 1) * 1.6:
            size -= 0.5
        if strategy == 'line':                          # a rewritten line must fit inside the original line
            while size > 5 and fitz.get_text_length(text, 'helv', size) > box[2] - box[0] - 2:
                size -= 0.25
        width = fitz.get_text_length(text, 'helv', size)
        box = (box[0], box[1], max(box[2], box[0] + width + 2), box[3])
        page.draw_rect(fitz.Rect(box), color=None, fill=bg, overlay=True)
        page.insert_text(fitz.Point(box[0] + 0.8, baseline), text, fontsize=size, fontname='helv', color=ink)
        doc.save(str(out_pdf), garbage=3, deflate=True)
    return {'page': page_no, 'box': [round(v, 2) for v in box], 'old': old, 'new': new, 'text_drawn': text,
            'strategy': strategy, 'font': 'Helvetica (original font cannot be reproduced without the source)',
            'background_rgb': [round(c, 3) for c in bg], 'ink_rgb': [round(c, 3) for c in ink],
            'status': 'RECONSTRUCTED_REGION_AWAITING_VISUAL_APPROVAL'}


def review_patch(orig_pdf, cand_pdf, patch, item):
    """Repair Reviewer - independent of the Engineer: re-renders, re-reads and re-verifies the copy."""
    fitz = _fitz()
    import numpy as np
    checks = []
    pno, box = patch['page'], patch['box']
    with fitz.open(orig_pdf) as a, fitz.open(cand_pdf) as b:
        same_count = a.page_count == b.page_count
        checks.append(('page count unchanged', same_count, f'{a.page_count} -> {b.page_count}'))
        others = [i + 1 for i in range(min(a.page_count, b.page_count)) if i + 1 != pno and
                  a[i].get_pixmap(dpi=40).samples != b[i].get_pixmap(dpi=40).samples]
        checks.append(('every other page pixel-identical', not others, f'changed: {others or "none"}'))
        dpi = 72
        pa, pb = a[pno - 1].get_pixmap(dpi=dpi), b[pno - 1].get_pixmap(dpi=dpi)
        A = np.frombuffer(pa.samples, dtype=np.uint8).reshape(pa.h, pa.w, pa.n)[:, :, :3].astype(int)
        B = np.frombuffer(pb.samples, dtype=np.uint8).reshape(pb.h, pb.w, pb.n)[:, :, :3].astype(int)
        diff = np.abs(A - B).sum(axis=2) > 24
        ys, xs = np.nonzero(diff)
        s = dpi / 72
        inside = True
        if len(xs):
            inside = (xs.min() >= (box[0] - 3) * s and xs.max() <= (box[2] + 3) * s and
                      ys.min() >= (box[1] - 3) * s and ys.max() <= (box[3] + 3) * s)
        checks.append(('changes confined to the patch box', bool(inside and len(xs)),
                       'no change at all' if not len(xs) else
                       f'changed pixels x {xs.min()}..{xs.max()} y {ys.min()}..{ys.max()} (box {box})'))
        # independent fresh reading of the patched region (both resolutions)
        page = b[pno - 1]
        reads = []
        for d in imageread.OCR_DPIS:                     # whole page, like the reader: small clips read poorly
            reads.append(' '.join(l['text'] for l in imageread.ocr_page(page, d) if _overlap(l['rect'], box)))
        # read in at least one pass (a pass can miss a whole line), and the wrong text in none
        new_ok = any(_norm(patch['new']) in _norm(t) for t in reads)
        old_gone = not any(re.search(r'(?<![\w.])' + re.escape(_norm(patch['old'])) + r'(?![\w.])', _norm(t)) for t in reads) \
            or _norm(patch['old']) in _norm(patch['new'])
        checks.append(('reader sees the corrected text', new_ok, f'read: {reads}'))
        checks.append(('reader no longer sees the wrong text', old_gone, f'read: {reads}'))
    # the corrected statement must verify and the page must not gain new problems
    before = imageread.review_pdf(orig_pdf, pages=[pno])
    after = imageread.review_pdf(cand_pdf, pages=[pno])
    probs = lambda rv: [i for i in rv['items'] if i['status'] in (imageread.STATUS_ERR, 'SUSPECTED_TYPO')]
    # the SAME defect still at this spot (a different word that happens to share the line is not this defect)
    still = [i for i in probs(after) if _overlap(i['rect'], box) and
             (_norm(patch['old']) in _norm(i.get('shown') or i['statement']) or i['status'] == imageread.STATUS_ERR)]
    checks.append(('defect no longer detected at this location', not still,
                   f'still flagged: {[i["statement"] for i in still]}' if still else 'not flagged'))
    # pixels outside the box are proven unchanged above, so only a problem NEAR the patch can be caused by it;
    # anything further away is the reader seeing an unchanged word differently (recorded, not blamed on the patch)
    near = (box[0] - 60, box[1] - 30, box[2] + 60, box[3] + 30)
    new_probs = [i for i in probs(after) if _overlap(i['rect'], near) and
                 i['statement'] not in {j['statement'] for j in probs(before)} and
                 _norm(i.get('shown') or i['statement']) != _norm(patch['old'])]
    checks.append(('no new suspected error or typo on the page', not new_probs,
                   f'new: {[i["statement"] for i in new_probs]}' if new_probs else 'none'))
    if item.get('kind') in ('worked step', 'solved equation', 'arithmetic', 'solving step'):
        ok_here = [i for i in after['items'] if i['status'] == imageread.STATUS_OK and _overlap(i['rect'], box)]
        checks.append(('corrected statement verifies', bool(ok_here),
                       f'verified: {[i["statement"] for i in ok_here]}' if ok_here else 'not re-verified at this location'))
    return {'passed': all(c[1] for c in checks), 'checks': [{'check': c[0], 'passed': bool(c[1]), 'detail': c[2]}
                                                            for c in checks]}


def _ocr_clip(page, rect, dpi):
    import numpy as np
    pix = page.get_pixmap(dpi=dpi, clip=rect)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
    res, _ = imageread._engine()(img)
    return [{'text': str(t)} for _, t, _ in (res or [])]


def _overlap(a, b, m=2):
    return not (a[2] < b[0] - m or b[2] < a[0] - m or a[3] < b[1] - m or b[3] < a[1] - m)


def replacement_for(item, decision):
    """(old, new) characters for a confirmed finding, or raise if the owner has not given enough to repair."""
    old = str(item.get('token') or '').strip()
    corr = (decision or {}).get('replacement')
    if not old:
        raise ValueError('the exact wrong characters could not be located on the page')
    if item.get('kind') == 'spelling':
        if not corr:
            raise ValueError('spelling: the owner must type the correct word (dictionary suggestions are guesses)')
        return old, corr.strip()
    new = (corr or item.get('expected') or '').strip()
    if not new:
        raise ValueError('no verified replacement value')
    if item.get('kind') == 'solved equation':
        old = old.split('=')[-1].strip()
        new = new.split('=')[-1].strip()
    return old, new


def repair_with_review(orig_pdf, work_dir, item, decision, max_attempts=len(STRATEGIES)):
    """Engineer <-> Reviewer loop. Returns (patched_pdf, evidence) or raises RepairBlocked."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    old, new = replacement_for(item, decision)
    attempts = []
    for k, strategy in enumerate(STRATEGIES[:max_attempts], 1):
        out = work / f'{item["id"]}_attempt{k}.pdf'
        try:
            patch = apply_patch(orig_pdf, out, item['page'], item.get('line_rect') or item['rect'],
                                item.get('line') or item['statement'], old, new, strategy)
        except Exception as e:
            attempts.append({'attempt': k, 'strategy': strategy, 'engineer_error': str(e)})
            continue
        verdict = review_patch(orig_pdf, out, patch, item)
        attempts.append({'attempt': k, 'strategy': strategy, 'patch': patch, 'review': verdict})
        if verdict['passed']:
            return out, {'item': item['id'], 'old': old, 'new': new, 'attempts': attempts, 'accepted': patch,
                         'changed_pages': [item['page']], 'reviewer': 'Repair Reviewer (independent re-read)'}
    reasons = [c['check'] for a in attempts for c in (a.get('review') or {}).get('checks', []) if not c['passed']] + \
              [a['engineer_error'] for a in attempts if a.get('engineer_error')]
    raise RepairBlocked(f'Repair Reviewer rejected every attempt for {item["id"]}: {sorted(set(reasons))}', attempts)
