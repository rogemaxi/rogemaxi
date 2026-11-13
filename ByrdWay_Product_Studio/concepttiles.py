"""Concept Tiles Builder + independent construction QA (Engineering Division, construction side).

Input  : the owner-APPROVED table of contents (units -> tiles, Honors flags) and the tile content
         (one record per tile, in the owner's Concept Tile section structure).
Output : one PDF per unit with a real text layer (every page stays editable/re-verifiable), one tile per page,
         Lil Dr. Byrd on every tile (approved image only), plus a QA report.

Loop per unit:  BUILD -> VERIFY (independent) -> failures listed -> content fixed -> BUILD again ... until every
mandatory check passes. The next unit is built only after the current one passes.

Independent verification (never the builder judging itself):
  1. structure  : tiles exactly match the approved TOC (count, order, titles, Honors flags) - nothing
                  substituted, shortened or added
  2. complete   : every required section present; Honors tiles carry the Honors section; every worked
                  example and practice item has an answer AND a machine-checkable spec
  3. academic   : every answer re-computed by the Academic Verifier (units + dimensional analysis for physics)
  4. lessons    : the rendered PDF is re-read by the SAME Reader/Verifier the Inspection Division uses on
                  existing products (worked steps, arithmetic, spelling) - the builders are held to what the
                  repairers learned
  5. visual     : one tile per page with no overflow, title on its page, the mascot image on every page
"""
import html as H
import json
import re
from pathlib import Path

import academic
import imageread

SECTIONS = ('meaning', 'picture', 'examples', 'practice', 'misconception', 'teach_back')
E = H.escape


# ------------------------------------------------------------------ table of contents
def toc_from_blueprint_md(text):
    """Parse the approved TOC table: '| 1 Unit Title | tile · tile · (H) tile |'."""
    units = []
    for line in text.splitlines():
        m = re.match(r'^\|\s*(\d+)\s+([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$', line)
        if not m:
            continue
        tiles = []
        for t in [x.strip() for x in m.group(3).split('·')]:
            honors = t.startswith('(H)')
            tiles.append({'title': t[3:].strip() if honors else t, 'honors': honors})
        units.append({'unit': int(m.group(1)), 'title': m.group(2).strip(), 'tiles': tiles})
    return units


def check_structure(toc_unit, tiles):
    out = []
    want = [(t['title'], t['honors']) for t in toc_unit['tiles']]
    got = [(t.get('title'), bool(t.get('honors'))) for t in tiles]
    out.append(('structure.tile_count', len(got) == len(want), f'{len(got)} built, {len(want)} approved'))
    for i, (w, g) in enumerate(zip(want, got), 1):
        out.append((f'structure.tile{i}.title', _same_title(w[0], g[0]), f'approved "{w[0]}" / built "{g[0]}"'))
        out.append((f'structure.tile{i}.honors', w[1] == g[1], f'approved honors={w[1]} / built honors={g[1]}'))
    return out


def _same_title(a, b):
    n = lambda s: re.sub(r'[^a-z0-9²₀=+/]', '', str(s).lower().replace('&', 'and'))
    return n(a) == n(b)


# ------------------------------------------------------------------ verification of content
def _verify(question, answer, spec):
    return academic.verify_item({'question': question, 'answer': answer, 'verify': spec})


def check_tile(tile, idx):
    out = []
    for s in SECTIONS:
        v = tile.get(s)
        out.append((f'complete.tile{idx}.{s}', bool(v), 'present' if v else f'section "{s}" missing'))
    out.append((f'complete.tile{idx}.diagram', bool(tile.get('diagram')), 'diagram spec present' if tile.get('diagram')
                else '"Picture the reasoning" needs a real diagram'))
    n_ex = len(tile.get('examples') or [])
    out.append((f'complete.tile{idx}.two_worked_examples', n_ex >= 2, f'{n_ex} worked example(s); 2 required'))
    out.append((f'complete.tile{idx}.lil_dr_byrd_tip', bool(tile.get('byrd_says')),
                'Lil Dr. Byrd tip present' if tile.get('byrd_says') else 'Lil Dr. Byrd needs a guiding tip'))
    if tile.get('honors'):
        out.append((f'complete.tile{idx}.honors_section', bool(tile.get('honors_reasoning')),
                    'Honors full reasoning present' if tile.get('honors_reasoning') else 'Honors section missing'))
    items = [('example', e) for e in tile.get('examples') or []] + [('practice', p) for p in [tile.get('practice')] if p]
    for k, (kind, it) in enumerate(items, 1):
        q, spec = it.get('question') or it.get('problem'), it.get('verify')
        a = it.get('verify_answer', it.get('answer'))         # same value as printed, in checkable form
        if not (q and a and spec):
            out.append((f'academic.tile{idx}.{kind}{k}.checkable', False,
                        'question, answer and a machine-checkable spec are all required'))
            continue
        r = _verify(q, a, spec)
        out.append((f'academic.tile{idx}.{kind}{k}', r['status'] == academic.CORRECT,
                    f'{r["status"]}: {str(r.get("evidence"))[:160]}'))
    return out


# ------------------------------------------------------------------ diagrams (drawn from data, never decorative guesses)
def draw_diagram(spec, out_png, scale=3, font_path=None, bg='white'):
    """Render a teaching diagram from a small data spec. Types:
      graph  : {'x_label','y_label','points':[[x,y],...],'shade':bool,'labels':[[x,y,'text'],...]}
      arrows : {'arrows':[[x0,y0,x1,y1,'label'],...]}            (head-to-tail vectors, paths, components)
      boxes  : {'boxes':['km','m','cm'],'links':['x1000','x100']} (conversion ladders, step chains)"""
    from PIL import Image, ImageDraw, ImageFont
    W, Hh = 420 * scale, 190 * scale
    im = Image.new('RGB', (W, Hh), bg)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(str(font_path) if font_path else 'DejaVuSans.ttf', 13 * scale)
    except OSError:
        try:
            font = ImageFont.load_default(size=13 * scale)       # Pillow >= 10.1: scalable built-in font (Windows)
        except TypeError:
            font = ImageFont.load_default()
    ink, gold, blue = (20, 33, 61), (201, 162, 39), (29, 58, 138)
    t = spec.get('type')
    collisions = []
    if t == 'graph':
        pts = spec['points']
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1 = min(0, min(xs)), max(xs) or 1
        y0, y1 = min(0, min(ys)), max(ys) or 1
        L, R, T, B = 50 * scale, W - 20 * scale, 15 * scale, Hh - 35 * scale
        X = lambda v: L + (v - x0) / (x1 - x0) * (R - L)
        Y = lambda v: B - (v - y0) / (y1 - y0) * (B - T)
        if spec.get('shade'):
            d.polygon([(X(xs[0]), Y(0))] + [(X(a), Y(b)) for a, b in pts] + [(X(xs[-1]), Y(0))], fill=(255, 236, 170))
        d.line([(L, B), (R, B)], fill=ink, width=2 * scale)
        d.line([(L, B), (L, T)], fill=ink, width=2 * scale)
        d.line([(X(a), Y(b)) for a, b in pts], fill=blue, width=3 * scale)
        for a, b in pts:
            d.ellipse([X(a) - 4 * scale, Y(b) - 4 * scale, X(a) + 4 * scale, Y(b) + 4 * scale], fill=blue)
        d.text((R - 120 * scale, B + 8 * scale), spec.get('x_label', ''), fill=ink, font=font)
        d.text((4 * scale, T), spec.get('y_label', ''), fill=ink, font=font)
        for a, b, txt in spec.get('labels', []):
            d.text((X(a) + 6 * scale, Y(b) - 18 * scale), txt, fill=ink, font=font)
    elif t == 'arrows':
        arr = spec['arrows']
        allx = [v for a in arr for v in (a[0], a[2])]
        ally = [v for a in arr for v in (a[1], a[3])]
        x0, x1, y0, y1 = min(allx), max(allx), min(ally), max(ally)
        span = max(x1 - x0, y1 - y0, 1)
        k = min((W - 120 * scale) / max(x1 - x0, 1e-9) if x1 > x0 else 1e9,
                (Hh - 50 * scale) / max(y1 - y0, 1e-9) if y1 > y0 else 1e9, (W - 120 * scale) / span)
        ox, oy = 60 * scale - x0 * k, Hh - 25 * scale + y0 * k
        P = lambda x, y: (ox + x * k, oy - y * k)
        import math
        placed, segs = [], [(P(a[0], a[1]), P(a[2], a[3])) for a in arr]
        for i, (ax, ay, bx, by, lab) in enumerate(arr):
            col = [blue, (180, 30, 30), (10, 110, 50), gold][i % 4]
            a_, b_ = P(ax, ay), P(bx, by)
            d.line([a_, b_], fill=col, width=4 * scale)
            ang = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
            for s_ in (2.6, -2.6):
                d.line([b_, (b_[0] - 14 * scale * math.cos(ang + s_ / 6), b_[1] - 14 * scale * math.sin(ang + s_ / 6))],
                       fill=col, width=4 * scale)
            mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            nx, ny = -math.sin(ang), math.cos(ang)               # unit normal to the arrow
            tw, th = d.textbbox((0, 0), lab, font=font)[2:]
            best = None
            for side in (1, -1):
                for off in (14, 26, 40):
                    cx, cy = mx + side * nx * off * scale, my + side * ny * off * scale
                    box = (cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)
                    hit = any(_hits(box, q) for q in placed) or any(_seg_hits(box, s_) for s_ in segs)
                    if not hit and 0 <= box[0] and box[2] <= W and 0 <= box[1] and box[3] <= Hh:
                        best = box
                        break
                if best:
                    break
            if best is None:
                collisions.append(lab)
                best = (mx + 6 * scale, my - 20 * scale, mx + 6 * scale + tw, my - 20 * scale + th)
            placed.append(best)
            d.text((best[0], best[1]), lab, fill=col, font=font)
    elif t == 'boxes':
        n = len(spec['boxes'])
        bw, gap = (W - 40 * scale) / (n * 1.6), (W - 40 * scale) / (n * 1.6) * 0.6
        for i, lab in enumerate(spec['boxes']):
            x = 20 * scale + i * (bw + gap)
            d.rounded_rectangle([x, 60 * scale, x + bw, 130 * scale], radius=12 * scale, outline=blue, width=3 * scale,
                                fill=(238, 243, 255))
            d.text((x + 12 * scale, 82 * scale), lab, fill=ink, font=font)
            if i < n - 1:
                ax = x + bw
                d.line([(ax + 4 * scale, 95 * scale), (ax + gap - 4 * scale, 95 * scale)], fill=gold, width=4 * scale)
                d.text((ax + 2 * scale, 40 * scale), spec.get('links', [''] * n)[i], fill=(122, 92, 0), font=font)
    else:
        raise ValueError(f'unknown diagram type {t!r}')
    im.save(out_png)
    return {'png': out_png, 'label_collisions': collisions}


def _hits(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _seg_hits(box, seg, n=24):
    (x0, y0), (x1, y1) = seg
    return any(box[0] <= x0 + (x1 - x0) * k / n <= box[2] and box[1] <= y0 + (y1 - y0) * k / n <= box[3]
               for k in range(n + 1))


# ------------------------------------------------------------------ rendering (text layer kept)
CSS = """
body{font-family:sans-serif;font-size:9.4pt;color:#14213d;line-height:1.18}
h1{font-size:15pt;color:#1d3a8a;margin:0} .unit{font-size:8pt;color:#7a5c00;font-weight:bold;margin:0}
.honors{color:#8a1c7c;font-weight:bold} h2{font-size:10pt;color:#1d3a8a;margin:5px 0 1px 0;border-bottom:1px solid #c9a227}
p{margin:1px 0 2px 0} .key{font-size:11pt;font-weight:bold;color:#14213d;background-color:#fff4cc;padding:3px}
.step{margin-left:12px} .ans{font-weight:bold;color:#0a5c2a} .bad{color:#a11}
.foot{font-size:7pt;color:#666}
"""


def _math(t):
    t = re.sub(r'\^\((-?\d+)\)', r'<sup>\1</sup>', E(str(t)))      # x^(-4) -> x<sup>-4</sup>
    return re.sub(r'\^(-?\d+)', r'<sup>\1</sup>', t)                # x^2    -> x<sup>2</sup>


def _tile_html(unit, n, tile, mascot_name):
    hon = ' <span class="honors">HONORS</span>' if tile.get('honors') else ''
    b = [f'<p class="unit">BYRDWAY PHYSICS + HONORS · UNIT {unit["unit"]}: {E(unit["title"]).upper()} · TILE {n}</p>',
         f'<table><tr><td width="80%"><h1>{E(tile["title"])}{hon}</h1>'
         f'<p class="key">{_math(tile.get("key", ""))}</p></td>'
         f'<td width="20%"><img src="{E(mascot_name)}" width="78"/></td></tr></table>',
         f'<h2>1. Meaning &amp; reasoning</h2><p>{E(tile["meaning"])}</p>',
         f'<p><i>Lil Dr. Byrd says:</i> <b>{E(tile.get("byrd_says", ""))}</b></p>',
         f'<h2>2. Picture the reasoning</h2><p>{E(tile["picture"])}</p>'
         + (f'<p><img src="diagram_u{unit["unit"]:02d}_t{n:02d}.png" width="250"/></p>' if tile.get('diagram') else ''),
         '<h2>3. Worked examples (Lil Dr. Byrd)</h2>']
    for k, ex in enumerate(tile['examples'], 1):
        b.append(f'<p><b>Example {k}.</b> {_math(ex["problem"])}</p>')
        b += [f'<p class="step">{_math(s)}</p>' for s in ex.get('steps', [])]
        b.append(f'<p class="ans">Answer: {_math(ex["answer"])}</p>')
    p = tile['practice']
    b.append(f'<h2>4. Practice &amp; check</h2><p>{_math(p["question"])}</p>')
    b.append(f'<h2>5. Misconceptions &amp; teach it back</h2><p><span class="bad">Incorrect:</span> '
             f'{_math(tile["misconception"]["incorrect"])}<br/><span class="ans">Correct:</span> '
             f'{_math(tile["misconception"]["correct"])}</p><p><b>Teach it back:</b> {E(tile["teach_back"])}</p>')
    if tile.get('honors'):
        b.append(f'<h2>6. Honors: full reasoning</h2><p>{E(tile["honors_reasoning"])}</p>')
    b.append('<p class="foot">ByrdWay Mathematics &amp; Science · answers to Practice &amp; check are in the answer key.</p>')
    return ''.join(b)


def _key_html(unit, tiles):
    rows = ''.join(f'<tr><td>{n}</td><td>{E(t["title"])}</td><td>{_math(t["practice"]["answer"])}</td></tr>'
                   for n, t in enumerate(tiles, 1))
    return (f'<h1>Unit {unit["unit"]} answer key</h1><table border="1" cellpadding="3"><tr><th>Tile</th>'
            f'<th>Title</th><th>Practice answer</th></tr>{rows}</table>')


def render_unit(unit, tiles, mascot_path, out_pdf):
    """One page per tile + an answer-key page. Returns {'overflow': [tile numbers that did not fit one page]}."""
    fitz = imageread._fitz()
    base = Path(mascot_path).parent
    writer = fitz.DocumentWriter(str(out_pdf))
    page = fitz.paper_rect('letter')
    where = page + (34, 30, -34, -30)
    overflow, diagram_problems = [], {}
    for n, t in enumerate(tiles, 1):
        if t.get('diagram'):
            dg = draw_diagram(t['diagram'], base / f'diagram_u{unit["unit"]:02d}_t{n:02d}.png')
            diagram_problems[n] = dg['label_collisions']
        story = fitz.Story(html=f'<body>{_tile_html(unit, n, t, Path(mascot_path).name)}</body>', user_css=CSS,
                           archive=fitz.Archive(str(base)))
        dev = writer.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
        if more:
            overflow.append(n)
    story = fitz.Story(html=f'<body>{_key_html(unit, tiles)}</body>', user_css=CSS)
    more = True
    while more:
        dev = writer.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return {'overflow': overflow, 'diagram_problems': diagram_problems}


# ------------------------------------------------------------------ independent QA of the built PDF
def qa_pdf(pdf, unit, tiles):
    fitz = imageread._fitz()
    out = []
    with fitz.open(pdf) as doc:
        out.append(('visual.page_count', doc.page_count >= len(tiles) + 1,
                    f'{doc.page_count} pages for {len(tiles)} tiles + answer key'))
        for n, t in enumerate(tiles, 1):
            if n > doc.page_count:
                break
            pg = doc[n - 1]
            txt = pg.get_text('text', flags=0)                  # flags=0: expand ligatures (ﬁ -> fi)
            out.append((f'visual.tile{n}.text_layer', len(txt.strip()) > 200, f'{len(txt)} characters of real text'))
            out.append((f'visual.tile{n}.title_on_page', _same_title(t['title'], t['title']) and
                        re.sub(r'\s+', '', t['title'][:20]) in re.sub(r'\s+', '', txt), 'title found on its page'))
            out.append((f'visual.tile{n}.mascot', bool(pg.get_images()), 'Lil Dr. Byrd image on the page'))
            if t.get('diagram'):
                out.append((f'visual.tile{n}.diagram_on_page', len(pg.get_images()) >= 2,
                            f'{len(pg.get_images())} images on the page (mascot + diagram)'))
            # lessons: the Inspection Division's own Reader/Verifier on the built page
            lines = [{'text': ' '.join(s['text'] for s in l['spans']).strip(), 'conf': 1.0, 'rect': tuple(l['bbox'])}
                     for b in pg.get_text('dict', flags=0)['blocks'] for l in b.get('lines', [])]
            lines = [l for l in lines if l['text']]
            errs = [f for f in imageread.check_worked_steps(lines, lines) if f['status'] == imageread.STATUS_ERR]
            errs += [f'{l} = {r}' for ln in lines for st, l, r, _, _ in imageread.check_line(ln) if st == imageread.STATUS_ERR]
            out.append((f'lessons.tile{n}.worked_steps_and_arithmetic', not errs,
                        f'errors: {[e["statement"] if isinstance(e, dict) else e for e in errs]}' if errs else
                        'every step and arithmetic statement on the page verifies'))
            blocks = [' '.join(' '.join(s['text'] for s in l['spans']) for l in b.get('lines', []))
                      for b in pg.get_text('dict', flags=0)['blocks']]      # a paragraph may wrap inside brackets
            unbalanced = [t for t in blocks if t.count('(') != t.count(')')]
            out.append((f'lessons.tile{n}.brackets_balanced', not unbalanced,
                        f'unbalanced brackets: {unbalanced}' if unbalanced else 'every bracket is closed'))
            typos = imageread.typo_candidates(lines, lines) if lines else []
            typos = [x for x in typos if x['shown'].lower() not in _TECH_WORDS]
            out.append((f'lessons.tile{n}.spelling', not typos,
                        f'possible misspellings: {[x["shown"] for x in typos]}' if typos else 'no misspellings'))
    return out


_TECH_WORDS = set('''kinematics newtons joules pascals coulombs kilograms nanometers micrometers millimeters
centimeters kilometers vectors scalars displacement equilibrium honors byrdway lil centi milli kilo micro'''.split())


# ------------------------------------------------------------------ one unit through the loop
def build_unit(toc_unit, tiles, mascot_path, out_dir, lessons=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = check_structure(toc_unit, tiles)
    for n, t in enumerate(tiles, 1):
        checks += check_tile(t, n)
    pdf = out_dir / f'Physics_Honors_Concept_Tiles_Unit_{toc_unit["unit"]:02d}.pdf'
    if all(c[1] for c in checks if c[0].startswith(('structure', 'complete'))):
        r = render_unit(toc_unit, tiles, mascot_path, pdf)
        bad = {k: v for k, v in r['diagram_problems'].items() if v}
        checks.append(('visual.diagram_labels_clear', not bad,
                       f'labels that could not be placed clear of other labels and lines: {bad}' if bad else
                       'every diagram label is clear of other labels and lines'))
        checks.append(('visual.one_tile_per_page', not r['overflow'],
                       f'tiles that overflow one page: {r["overflow"]}' if r['overflow'] else 'every tile fits one page'))
        checks += qa_pdf(pdf, toc_unit, tiles)
    failed = [c for c in checks if not c[1]]
    rep = {'unit': toc_unit['unit'], 'title': toc_unit['title'], 'pdf': str(pdf) if pdf.exists() else None,
           'checks': [{'check': c[0], 'passed': bool(c[1]), 'detail': c[2]} for c in checks],
           'mandatory_checks': len(checks), 'failed': len(failed),
           'decision': 'PASS' if not failed else 'FAIL - back to the builder',
           'lessons_held_to': lessons or [],
           'failures': [{'check': c[0], 'detail': c[2]} for c in failed]}
    (out_dir / f'unit_{toc_unit["unit"]:02d}_qa.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')
    return rep


# ------------------------------------------------------------------ Assembler (agent 10) + whole-product QA
def assemble_product(toc, unit_reports, mascot_path, out_pdf, title='ByrdWay Physics + Honors Concept Tiles'):
    """Join every PASSED unit into one product: cover, table of contents, all tiles, all answer keys, bookmarks.
    Refuses if any unit is missing, not PASS, or changed since its QA (the file's SHA-256 is re-checked)."""
    import hashlib
    fitz = imageread._fitz()
    by_unit = {r['unit']: r for r in unit_reports}
    problems = []
    for u in toc:
        r = by_unit.get(u['unit'])
        if not r or r.get('decision') != 'PASS' or not r.get('pdf'):
            problems.append(f'unit {u["unit"]} has not passed Build QA')
        elif r.get('pdf_sha256') and hashlib.sha256(Path(r['pdf']).read_bytes()).hexdigest() != r['pdf_sha256']:
            problems.append(f'unit {u["unit"]} PDF changed after QA')
    if problems:
        raise PermissionError('Assembly refused: ' + '; '.join(problems))
    out = fitz.open()
    base = Path(mascot_path).parent
    n_tiles = sum(len(u['tiles']) for u in toc)
    n_hon = sum(t['honors'] for u in toc for t in u['tiles'])
    cover = (f'<body><p class="unit">BYRDWAY MATHEMATICS &amp; SCIENCE</p><h1>{E(title)}</h1>'
             f'<p><img src="{E(Path(mascot_path).name)}" width="160"/></p>'
             f'<p class="key">{len(toc)} units · {n_tiles} Concept Tiles · {n_hon} Honors tiles · answer key for every unit</p>'
             f'<p>One idea per tile: Meaning &amp; reasoning · Picture the reasoning · Worked examples · Practice &amp; check · '
             f'Misconceptions &amp; teach it back · Honors: full reasoning. Lil Dr. Byrd guides every tile.</p></body>')
    tmp = Path(out_pdf).with_suffix('.front.pdf')
    w = fitz.DocumentWriter(str(tmp))
    page = fitz.paper_rect('letter')
    where = page + (54, 54, -54, -54)
    starts, p = {}, 0
    front = 2                                                  # cover + contents (contents fits one page: checked below)
    p = front
    for u in toc:
        starts[u['unit']] = p + 1
        with fitz.open(by_unit[u['unit']]['pdf']) as d:
            p += d.page_count
    rows = ''.join(f'<tr><td>Unit {u["unit"]}</td><td>{E(u["title"])}</td><td>{len(u["tiles"])} tiles</td>'
                   f'<td>page {starts[u["unit"]]}</td></tr>' for u in toc)
    contents = f'<body><h1>Contents</h1><table border="1" cellpadding="3">{rows}</table></body>'
    contents_pages = 0
    for html in (cover, contents):
        st = fitz.Story(html=html, user_css=CSS, archive=fitz.Archive(str(base)))
        more = True
        while more:
            dev = w.begin_page(page)
            more, _ = st.place(where)
            st.draw(dev)
            w.end_page()
            contents_pages += 1
    w.close()
    if contents_pages != front:
        raise ValueError('front matter does not fit two pages')
    with fitz.open(tmp) as f:
        out.insert_pdf(f)
    tmp.unlink()
    outline = [[1, 'Cover', 1], [1, 'Contents', 2]]
    for u in toc:
        with fitz.open(by_unit[u['unit']]['pdf']) as d:
            s = out.page_count + 1
            out.insert_pdf(d)
        outline.append([1, f'Unit {u["unit"]}: {u["title"]}', s])
        for i, t in enumerate(u['tiles']):
            outline.append([2, f'{i + 1}. {t["title"]}{" (Honors)" if t["honors"] else ""}', s + i])
        outline.append([2, f'Unit {u["unit"]} answer key', s + len(u['tiles'])])
    out.set_toc(outline)
    out.set_metadata({'title': title, 'author': 'ByrdWay Mathematics & Science', 'subject': 'Physics + Honors'})
    out.save(str(out_pdf), garbage=3, deflate=True)
    out.close()
    return {'pdf': str(out_pdf), 'starts': starts, 'pages': p}


def qa_product(toc, assembled, unit_reports):
    """Independent whole-product QA: every approved tile present, in order, on its own page with its title;
    bookmarks complete; page count adds up; every unit's QA evidence attached."""
    fitz = imageread._fitz()
    checks = []
    with fitz.open(assembled['pdf']) as doc:
        bm = doc.get_toc()
        n_tiles = sum(len(u['tiles']) for u in toc)
        checks.append(('product.page_count', doc.page_count == assembled['pages'],
                       f'{doc.page_count} pages (expected {assembled["pages"]})'))
        checks.append(('product.bookmarks', len(bm) == 2 + len(toc) * 2 + n_tiles,
                       f'{len(bm)} bookmarks for {len(toc)} units and {n_tiles} tiles'))
        for u in toc:
            s = assembled['starts'][u['unit']]
            for i, t in enumerate(u['tiles']):
                raw = doc[s - 1 + i].get_text('text', flags=0)
                norm = lambda x: re.sub(r'[^a-z0-9²₀=+/]', '', x.lower().replace('&', 'and'))
                ok = norm(t['title'])[:18] in norm(raw) and f'UNIT {u["unit"]}:' in raw
                checks.append((f'product.unit{u["unit"]}.tile{i + 1}.in_place', ok, f'"{t["title"]}" on page {s + i}'))
                checks.append((f'product.unit{u["unit"]}.tile{i + 1}.mascot', bool(doc[s - 1 + i].get_images()),
                               'Lil Dr. Byrd on the page'))
            key = doc[s - 1 + len(u['tiles'])].get_text('text', flags=0)
            checks.append((f'product.unit{u["unit"]}.answer_key', f'Unit {u["unit"]} answer key' in key,
                           f'answer key on page {s + len(u["tiles"])}'))
    for r in unit_reports:
        checks.append((f'product.unit{r["unit"]}.build_qa', r['decision'] == 'PASS' and r['failed'] == 0,
                       f'{r["mandatory_checks"] - r["failed"]}/{r["mandatory_checks"]} unit checks passed'))
    return checks
