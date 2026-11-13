"""ByrdWay Concept Tiles in the OWNER-APPROVED design (measured from the approved Geometry + Honors product).

Every geometry, colour and type size below was measured from the approved PDF's drawing instructions:
landscape letter 792 x 612 pt, cream page, sticky-note cards with a 10 % shadow offset (+2, +3), Kalam (OFL)
handwriting type, navy ink #16324a, running header "BYRDWAY MATHEMATICS AND SCIENCE / SEE IT. UNDERSTAND IT.
EXPLAIN IT.", footer course name + page number.

Unit structure (approved format): chapter map (19 tiles) -> one lesson page per approved tile (6 cards:
1 Meaning and why it works, 2 Picture the reasoning, 3 Worked examples | explain each move, 4 Practice and check,
5 Misconception / teach back, 6 Honors: complete reasoning) -> Independent practice Problems 1-6 and 7-12 ->
My 19-Tile Teach-It-Back Poster Board -> Answer key and short solution verifications.

conformance() re-measures a built PDF and compares it with this specification (independent design QA).
"""
import html as H
import re
import sys
from pathlib import Path

import imageread

E = H.escape
W, HT = 792, 612
CREAM = (0.984, 0.969, 0.929)
INK = (0x16 / 255, 0x32 / 255, 0x4a / 255)
YEL, BLU, PNK, GRN, ORG, PUR = ((1.0, 0.961, 0.541), (0.686, 0.878, 0.937), (0.957, 0.729, 0.855),
                                (0.804, 0.941, 0.639), (1.0, 0.831, 0.624), (0.851, 0.773, 0.933))
CYCLE = [YEL, BLU, PNK, GRN, ORG, PUR]
HEADER_L, HEADER_R = 'BYRDWAY MATHEMATICS AND SCIENCE', 'SEE IT. UNDERSTAND IT. EXPLAIN IT.'

# measured card rectangles (x0, y0, x1, y1) and colours per page type
LAYOUT = {
    'title': [((28, 35, 764, 73), YEL)],
    'lesson': [((28, 88, 388, 233), YEL), ((404, 88, 764, 233), BLU), ((28, 244, 764, 369), PNK),
               ((28, 380, 388, 470), GRN), ((404, 380, 764, 470), ORG), ((28, 480, 764, 575), PUR)],
    'map_top': [((28, 88, 266, 162), PNK), ((278, 88, 764, 162), GRN)],
    'practice1': [((28, 117, 388, 563), YEL), ((404, 117, 764, 563), BLU)],
    'practice2': [((28, 117, 388, 563), PNK), ((404, 117, 764, 563), GRN)],
    'key': [((28, 90, 388, 315), YEL), ((404, 90, 764, 315), BLU), ((28, 329, 388, 554), PNK), ((404, 329, 764, 554), GRN)],
    'contents_l': [((28, 90 + 70 * i, 389, 148 + 70 * i), CYCLE[i % 6]) for i in range(6)],
    'contents_r': [((403, 90 + 70 * i, 764, 148 + 70 * i), CYCLE[i % 6]) for i in range(6)],
}
MAP_GRID = [((28 + 149 * c, 176 + 97 * r, 168 + 149 * c, 264 + 97 * r)) for r in range(3) for c in range(5)] + \
           [((28 + 187 * c, 467, 203 + 187 * c, 555)) for c in range(4)]
BOARD_LABELS = ['1. Meaning in my words', '2. Draw the main model', '3. Explain why it works', '4. Define symbols / units',
                '5. State the conditions', '6. Worked example 1', '7. Justify each move', '8. Worked example 2',
                '9. Draw a second model', '10. Connect two forms', '11. Context and units', '12. My practice problem',
                '13. Check the original', '14. Find and repair an error', '15. Honors proof / cases', '16. Common mistake',
                '17. Quick reference', '18. Chapter connections', '19. Teach it back aloud']


def font_dir():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / 'fonts'


CSS = """
@font-face {font-family: kalam; src: url(Kalam-Regular.ttf);}
@font-face {font-family: kalam; font-weight: bold; src: url(Kalam-Bold.ttf);}
* {font-family: kalam; color: #16324a;}
p {margin: 0 0 3px 0;} h3 {font-weight: bold; font-size: 12.2px; margin: 0 0 4px 0;}
.b {font-weight: bold;}
"""


def _sup(t):
    t = E(str(t))
    t = re.sub(r'\^\((-?\d+)\)', r'<sup>\1</sup>', t)
    return re.sub(r'\^(-?\d+)', r'<sup>\1</sup>', t)


class Book:
    def __init__(self, course):
        self.fitz = imageread._fitz()
        self.doc = self.fitz.open()
        self.course = course
        self.arch = self.fitz.Archive(str(font_dir()))
        self.overflow = []

    # -------------------------------------------------- primitives
    def page(self, white=False):
        p = self.doc.new_page(width=W, height=HT)
        p.draw_rect(p.rect, color=None, fill=(1, 1, 1) if white else CREAM)
        self.text(p, (28, 9, 300, 24), f'<p class="b" style="font-size:8.5px">{HEADER_L}</p>')
        self.text(p, (493, 9, 764, 24), f'<p style="font-size:8.5px">{HEADER_R}</p>')
        self.text(p, (28, 589, 300, 603), f'<p style="font-size:8px">{E(self.course)}</p>')
        self.text(p, (700, 589, 764, 603), f'<p style="font-size:8px;text-align:right">{self.doc.page_count}</p>')
        return p

    def card(self, p, r, col, shadow=True):
        R = self.fitz.Rect(*r)
        if shadow:
            p.draw_rect(R + (2, 3, 2, 3), color=None, fill=(0, 0, 0), fill_opacity=0.1)
        p.draw_rect(R, color=None, fill=col)
        # folded corner (bottom right), as on the approved notes
        p.draw_polyline([(R.x1 - 7, R.y1), (R.x1, R.y1 - 7), (R.x1 - 7, R.y1 - 7), (R.x1 - 7, R.y1)],
                        color=None, fill=tuple(min(1, c * 0.88) for c in col))
        return R

    def text(self, p, r, html, label=''):
        """Place text; if it does not fit, step the body size down (max 2 steps, never below 8.6 px) like a designer
        would. Still not fitting = recorded overflow (a QA failure), never silently cut."""
        for k in range(3):
            h = html if k == 0 else re.sub(r'font-size:(\d+(?:\.\d+)?)px',
                                           lambda m: f'font-size:{max(8.6, float(m.group(1)) - 0.6 * k):.1f}px', html)
            spare, scale = p.insert_htmlbox(self.fitz.Rect(*r), h, css=CSS, archive=self.arch, scale_low=1)
            if spare >= 0:
                return spare
        self.overflow.append(f'page {self.doc.page_count} {label}'.strip())
        return spare

    def title(self, p, t):
        self.card(p, LAYOUT['title'][0][0], YEL)
        self.text(p, (40, 40, 760, 70), f'<p class="b" style="font-size:17px">{E(t)}</p>', 'title')

    # -------------------------------------------------- page types
    def cover(self, title, tagline, author, mascot=None):
        p = self.page()
        for (r, col), rot in zip([((48, 42, 618, 140), YEL), ((58, 158, 604, 262), BLU), ((48, 288, 398, 392), PNK),
                                   ((420, 292, 606, 386), GRN)], (-0.6, 0.5, 0.4, -0.5)):
            R = self.fitz.Rect(*r)
            q = R.quad.morph(R.tl + (R.br - R.tl) * 0.5, self.fitz.Matrix(rot))
            p.draw_quad(q.transform(self.fitz.Matrix(1, 1).pretranslate(3, 4)), color=None, fill=(0, 0, 0), fill_opacity=0.1)
            p.draw_quad(q, color=None, fill=col)
        self.text(p, (68, 62, 600, 92), '<p class="b" style="font-size:20px">BYRDWAY MATHEMATICS AND SCIENCE</p>')
        self.text(p, (68, 92, 600, 140), f'<p class="b" style="font-size:34px">{E(title.upper())}</p>')
        self.text(p, (78, 222, 600, 258), f'<p style="font-size:21px">{E(tagline)}</p>')
        self.text(p, (66, 300, 392, 388), '<p style="font-size:17px">Inspired by the Richard Feynman Approach to Learning</p>'
                                          '<p class="b" style="font-size:16px">See It. Understand It. Explain It.</p>')
        self.text(p, (432, 306, 600, 380), f'<p class="b" style="font-size:19px">{E(author)}</p>')
        if mascot:
            p.insert_image(self.fitz.Rect(640, 300, 760, 460), filename=str(mascot), keep_proportion=True)

    def contents(self, units, starts):
        p = self.page()
        self.title(p, 'Table of Contents | one complete packet')
        for i, u in enumerate(units):
            side = 'contents_l' if i < 5 else 'contents_r'
            r, col = LAYOUT[side][i % 5]
            R = self.card(p, r, col)
            self.text(p, (R.x0 + 10, R.y0 + 5, R.x1 - 50, R.y1 - 4),
                      f'<p class="b" style="font-size:12.3px">{u["unit"]:02d}. {E(u["title"])}</p>'
                      f'<p style="font-size:9.5px">{len(u["tiles"])} tiles · practice · 19-tile board · answer key</p>')
            self.text(p, (R.x1 - 46, R.y0 + 16, R.x1 - 6, R.y1 - 4), f'<p class="b" style="font-size:13px;text-align:right">{starts[u["unit"]]}</p>')
        self.text(p, (30, 527, 764, 548), '<p style="font-size:10.5px">Each unit: map · one lesson per tile · Problems 1-12 · '
                                          '19-tile board · answer key. Lil Dr. Byrd guides every tile.</p>')

    def unit_map(self, u, tiles, extra):
        p = self.page()
        self.title(p, f'UNIT {u["unit"]:02d} | {u["title"]}')
        (r1, c1), (r2, c2) = LAYOUT['map_top']
        R = self.card(p, r1, c1)
        self.text(p, (R.x0 + 10, R.y0 + 4, R.x1 - 8, R.y1 - 4), '<h3>See it. Understand it. Explain it.</h3>'
                  '<p style="font-size:10.7px">Explain in plain words. Draw the model. Work the mathematics. Check it. Teach it back.</p>')
        R = self.card(p, r2, c2)
        big = extra.get('big_idea') or tiles[0]['meaning'].split('.')[0] + '.'
        self.text(p, (R.x0 + 10, R.y0 + 4, R.x1 - 8, R.y1 - 4), f'<h3>The big idea</h3><p style="font-size:11.5px">{_sup(big)}</p>')
        hon = [t for t in tiles if t.get('honors')]
        T = lambda i: tiles[min(i, len(tiles) - 1)]
        cells = [(f'{i + 1}. {t["title"]}', t.get('key', '')) for i, t in enumerate(tiles)]
        cells += [('11. Work an example', tiles[0]['examples'][0]['problem']),
                  ('12. Try another', T(1)['practice']['question']),
                  ('13. Check the mathematics', 'Substitute each answer back in and check its units.'),
                  ('14. Honors connection', hon[0]['title'] if hon else 'Every formula comes from a definition you can explain.'),
                  ('15. Avoid the trap', T(2)['misconception']['correct']),
                  ('16. Common mistake', T(3)['misconception']['incorrect']),
                  ('17. Quick reference', ' · '.join(t['title'] for t in tiles[4:7])),
                  ('18. Roadmap', f'Unit {u["unit"]:02d}: {u["title"]}. Practice and key follow the lessons.'),
                  ('19. Teach it back', tiles[-1]['teach_back'])]
        for k, (r, (head, body)) in enumerate(zip(MAP_GRID, cells)):
            R = self.card(p, r, CYCLE[k % 6])
            self.text(p, (R.x0 + 7, R.y0 + 3, R.x1 - 5, R.y1 - 3),
                      f'<p class="b" style="font-size:9.6px">{E(head)}</p><p style="font-size:7.6px">{_sup(body)}</p>', f'map tile {k + 1}')

    def lesson(self, u, n, t, diagram_png, mascot, key_page):
        p = self.page()
        self.title(p, f'UNIT {u["unit"]:02d} | TILE {n} | {t["title"]}' + ('  (Honors)' if t.get('honors') else ''))
        c = [self.card(p, r, col) for r, col in LAYOUT['lesson']]
        pad = lambda R, r=0: (R.x0 + 10, R.y0 + 4, R.x1 - 8 - r, R.y1 - 4)
        self.text(p, pad(c[0]), f'<h3>1. Meaning and why it works</h3><p style="font-size:10px">{_sup(t["meaning"])}</p>'
                                f'<p style="font-size:10px"><span class="b">Key relationship:</span> {_sup(t.get("key", ""))}</p>', 'card 1')
        self.text(p, (c[1].x0 + 10, c[1].y0 + 4, c[1].x1 - 8, c[1].y0 + 64),
                  f'<h3>2. Picture the reasoning</h3><p style="font-size:9.6px">{_sup(t["picture"])}</p>', 'card 2')
        if diagram_png:
            p.insert_image(self.fitz.Rect(c[1].x0 + 60, c[1].y0 + 64, c[1].x1 - 60, c[1].y1 - 6), filename=str(diagram_png),
                           keep_proportion=True)
        self.text(p, (c[2].x0 + 10, c[2].y0 + 4, c[2].x1 - 8, c[2].y0 + 24), '<h3>3. Worked examples | explain each move</h3>')
        for k, ex in enumerate(t['examples'][:2]):
            x0 = c[2].x0 + 10 + k * 368
            body = f'<p style="font-size:10.2px"><span class="b">Example {k + 1}.</span> {_sup(ex["problem"])}</p>' + \
                   ''.join(f'<p style="font-size:10.2px">{_sup(s)}</p>' for s in ex.get('steps', [])) + \
                   f'<p class="b" style="font-size:10.2px">Answer: {_sup(ex["answer"])}</p>'
            self.text(p, (x0, c[2].y0 + 26, x0 + 352, c[2].y1 - 4), body, f'card 3 example {k + 1}')
        self.text(p, pad(c[3]), f'<h3>4. Practice and check</h3><p style="font-size:10.2px">{_sup(t["practice"]["question"])}</p>'
                                f'<p style="font-size:10.2px">Solve it independently, then check the answer key on page {key_page}.</p>', 'card 4')
        m = t['misconception']
        self.text(p, pad(c[4]), f'<h3>5. Misconception / teach back</h3><p style="font-size:10px">Not this: {_sup(m["incorrect"])} '
                                f'Instead: {_sup(m["correct"])}</p><p style="font-size:10px">{_sup(t["teach_back"])}</p>', 'card 5')
        if t.get('honors'):
            body = f'<h3>6. Honors: complete reasoning</h3><p style="font-size:10px">{_sup(t["honors_reasoning"])}</p>'
        else:
            body = (f'<h3>6. Lil Dr. Byrd: the key idea</h3><p style="font-size:10.5px">{_sup(t.get("byrd_says", ""))}</p>'
                    f'<p style="font-size:10.5px"><span class="b">Remember:</span> {_sup(t.get("key", ""))}</p>')
        self.text(p, pad(c[5], 70), body, 'card 6')
        if mascot:
            p.insert_image(self.fitz.Rect(c[5].x1 - 72, c[5].y0 + 6, c[5].x1 - 10, c[5].y1 - 6), filename=str(mascot),
                           keep_proportion=True)

    def practice(self, u, problems, first, key_page):
        for half, lay in ((0, 'practice1'), (1, 'practice2')):
            p = self.page()
            a = first + 6 * half
            self.title(p, f'UNIT {u["unit"]:02d} | Independent practice | Problems {a}-{a + 5}')
            self.text(p, (30, 80, 764, 100), f'<p style="font-size:10.5px">Use justified steps. Include units in every answer. '
                                             f'Round only when the problem asks. Key: page {key_page}.</p>')
            for side, (r, col) in enumerate(LAYOUT[lay]):
                R = self.card(p, r, col)
                s = a + 3 * side
                items = ''.join(f'<p style="font-size:10.8px;margin-bottom:14px">{s + i}. {_sup(q["question"])}</p>'
                                for i, q in enumerate(problems[s - 1:s + 2]))
                self.text(p, (R.x0 + 12, R.y0 + 6, R.x1 - 10, R.y1 - 6),
                          f'<p class="b" style="font-size:14px;margin-bottom:10px">Problems {s}-{s + 2}</p>{items}', f'practice {s}')

    def board(self, u, signature, sig_png):
        p = self.page(white=True)
        self.title(p, f'UNIT {u["unit"]:02d} | My 19-Tile Teach-It-Back Poster Board')
        if sig_png:
            p.insert_image(self.fitz.Rect(120, 80, 330, 200), filename=str(sig_png), keep_proportion=True)
        self.text(p, (408, 84, 764, 200), f'<p class="b" style="font-size:12px">Signature idea: {E(signature)}</p>'
                                          '<p style="font-size:10.8px">Close the book. Explain, draw, calculate, and justify. Use tile 15 '
                                          'to reconstruct the reasoning. Compare afterward; repair gaps in another color.</p>')
        x, y = [28 + 147.2 * i for i in range(6)], [205, 286, 367, 448, 529]
        for r in range(4):
            cols = 5 if r < 3 else 4
            xs = x if r < 3 else [28 + 184 * i for i in range(5)]
            for cidx in range(cols):
                k = r * 5 + cidx
                p.draw_rect(self.fitz.Rect(xs[cidx], y[r], xs[cidx + 1], y[r + 1]), color=(0, 0, 0), width=1.2)
                self.text(p, (xs[cidx] + 6, y[r] + 4, xs[cidx + 1] - 4, y[r] + 30),
                          f'<p class="b" style="font-size:9.6px">{E(BOARD_LABELS[k])}</p>')
        self.text(p, (30, 545, 764, 566), f'<p style="font-size:10px">Name: ____________________ Date: __________ '
                                          f'Revision: ______ | {E(u["title"])}</p>')

    def answer_key(self, u, problems, first):
        p = self.page()
        self.title(p, f'UNIT {u["unit"]:02d} | Answer key and short solution verifications')
        for q, (r, col) in enumerate(LAYOUT['key']):
            R = self.card(p, r, col)
            s = first + 3 * q
            rows = ''.join(f'<p style="font-size:10.4px;margin-bottom:9px">{s + i}. {_sup(pr["answer"])}. {_sup(check_line(pr))}</p>'
                           for i, pr in enumerate(problems[s - 1:s + 2]))
            self.text(p, (R.x0 + 10, R.y0 + 5, R.x1 - 8, R.y1 - 5), f'<p class="b" style="font-size:12.5px">Problems {s}-{s + 2}</p>{rows}', f'key {s}')

    def save(self, out):
        self.doc.set_metadata({'title': self.course, 'author': 'ByrdWay Mathematics & Science'})
        self.doc.subset_fonts()
        self.doc.save(str(out), garbage=3, deflate=True)


def _pretty(f):
    f = re.sub(r'\*\*\(1/2\)\*\*', '^', str(f))
    f = re.sub(r'\*\*(\d)', lambda m: '⁰¹²³⁴⁵⁶⁷⁸⁹'[int(m.group(1))], f)
    f = f.replace('sqrt', '√').replace('pi', 'π').replace('*', '·')
    return re.sub(r'\^(\d)', lambda m: '⁰¹²³⁴⁵⁶⁷⁸⁹'[int(m.group(1))], f)


def check_line(item):
    v = item.get('verify') or {}
    if v.get('type') == 'physics':
        g = ', '.join(f'{k} = {_pretty(x)}' for k, x in v['given'].items())
        return f'Check: {_pretty(v["formula"])} with {g}'
    if v.get('type') == 'expression':
        return f'Check: {_pretty(v["expr"])}'
    return 'Check the units.'


# -------------------------------------------------- independent design-conformance QA
def conformance(pdf, plan):
    """Re-measure the built PDF and compare with the approved specification. plan: list of (page_no, kind)."""
    fitz = imageread._fitz()
    out = []
    want = {'lesson': LAYOUT['lesson'], 'practice1': LAYOUT['practice1'], 'practice2': LAYOUT['practice2'],
            'key': LAYOUT['key'], 'map': LAYOUT['map_top']}
    with fitz.open(pdf) as d:
        for pno, kind in plan:
            pg = d[pno - 1]
            ok_size = abs(pg.rect.width - W) < 0.5 and abs(pg.rect.height - HT) < 0.5
            out.append((f'design.p{pno}.landscape_letter', ok_size, f'{pg.rect.width} x {pg.rect.height}'))
            fills = [(tuple(round(c, 3) for c in dr['fill']), tuple(round(v) for v in dr['rect']))
                     for dr in pg.get_drawings() if dr.get('fill') and dr['rect'].width > 60 and (dr.get('fill_opacity') or 1) > 0.5]
            bg = (1.0, 1.0, 1.0) if kind == 'board' else tuple(round(c, 3) for c in CREAM)
            out.append((f'design.p{pno}.page_colour', any(f[0] == bg and f[1] == (0, 0, W, HT) for f in fills), f'background {bg}'))
            if kind in want:
                miss = [r for r, col in want[kind] if (tuple(round(c, 3) for c in col), r) not in fills]
                out.append((f'design.p{pno}.{kind}_cards_match_reference', not miss,
                            f'{len(want[kind]) - len(miss)}/{len(want[kind])} cards at the approved position and colour'
                            + (f'; missing {miss}' if miss else '')))
            fonts = {f[3].split('+')[-1] for f in pg.get_fonts()}
            body = [s for b in pg.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]
            kal = sum(len(s['text']) for s in body if 'Kalam' in s['font'])
            tot = sum(len(s['text']) for s in body) or 1
            out.append((f'design.p{pno}.handwritten_type', kal / tot >= 0.97,
                        f'{kal / tot * 100:.1f} % of characters in Kalam; fonts {sorted(fonts)}'))
            txt = pg.get_text()
            out.append((f'design.p{pno}.header_footer', HEADER_L in txt and HEADER_R in txt and str(pno) in txt.split('\n'),
                        'running header, course footer and page number'))
            ink = [s for s in body if 'Kalam' in s['font']]
            out.append((f'design.p{pno}.ink_colour', all(s['color'] == 0x16324a for s in ink) or kind == 'board',
                        'navy ink #16324a'))
    return out


# -------------------------------------------------- whole product: build + independent QA (used by the app)
def build_product(toc, units_content, out_pdf, course, mascot=None, title=None, author='By Dr. Rogé J. Byrd, Ed.D.',
                  tagline='Small Concepts. Powerful Understanding.'):
    """toc: approved TOC (concepttiles.toc_from_blueprint_md). units_content: {unit_no: {'tiles': [...], 'extra': [...]}}
    ('extra' = problems 11-12). Returns the QA report; the PDF is written only to out_pdf (originals untouched)."""
    import hashlib
    import academic
    import concepttiles as ct
    import construction
    out_pdf = Path(out_pdf)
    dg = out_pdf.parent / 'diagrams'
    dg.mkdir(parents=True, exist_ok=True)
    font = font_dir() / 'Kalam-Regular.ttf'
    per = lambda u: len(u['tiles']) + 5
    starts, s = {}, 3
    for u in toc:
        starts[u['unit']] = s
        s += per(u)
    B = Book(course)
    B.cover(title or course, tagline, author, mascot)
    B.contents(toc, starts)
    plan, checks, ud = [], [], {}
    for u in toc:
        n = u['unit']
        uc = units_content.get(n) or units_content.get(str(n)) or {}
        tiles = [dict(t, title=tt['title'], honors=tt['honors']) for t, tt in zip(uc.get('tiles', []), u['tiles'])]
        checks += [(f'u{n}.{c[0]}', c[1], c[2]) for c in ct.check_structure(u, tiles)]
        if len(tiles) != len(u['tiles']):
            continue
        for i, t in enumerate(tiles, 1):
            checks += [(f'u{n}.{c[0]}', c[1], c[2]) for c in ct.check_tile(t, i)]
        problems = [dict(t['practice']) for t in tiles] + list(uc.get('extra', []))
        checks.append((f'u{n}.practice.twelve_problems', len(problems) >= 12, f'{len(problems)} problems (format needs 12)'))
        for k, p in enumerate(problems[len(tiles):], len(tiles) + 1):
            r = academic.verify_item({'question': p['question'], 'answer': p.get('verify_answer', p['answer']), 'verify': p.get('verify')})
            checks.append((f'u{n}.academic.problem{k}', r['status'] == academic.CORRECT, r['status']))
        problems = (problems + [{'question': '(missing)', 'answer': '(missing)'}] * 12)[:12]
        s, nt = starts[n], len(tiles)
        key_page = s + nt + 4
        B.unit_map(u, tiles, uc)
        plan.append((s, 'map'))
        for i, t in enumerate(tiles, 1):
            png = None
            if t.get('diagram'):
                png = dg / f'u{n:02d}_t{i:02d}.png'
                r = ct.draw_diagram(t['diagram'], png, font_path=font, bg=tuple(int(c * 255) for c in BLU))
                checks.append((f'u{n}.visual.tile{i}.diagram_labels_clear', not r['label_collisions'], str(r['label_collisions'])))
            B.lesson(u, i, t, png, mascot, key_page)
            plan.append((s + i, 'lesson'))
        B.practice(u, problems, 1, key_page)
        plan += [(s + nt + 1, 'practice1'), (s + nt + 2, 'practice2')]
        sig = next((t for t in tiles if t.get('honors')), tiles[0])
        si = tiles.index(sig) + 1
        B.board(u, sig['title'], dg / f'u{n:02d}_t{si:02d}.png' if sig.get('diagram') else None)
        plan.append((s + nt + 3, 'board'))
        B.answer_key(u, problems, 1)
        plan.append((key_page, 'key'))
        ud[n] = {'tiles': tiles, 'start': s, 'key': key_page}
    B.save(out_pdf)
    checks.append(('layout.no_text_overflow', not B.overflow, B.overflow[:10] or 'every text block fits its card'))
    checks += conformance(out_pdf, plan)
    fitz = imageread._fitz()
    norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower().replace('&', 'and'))
    with fitz.open(out_pdf) as d:
        checks.append(('structure.page_count', d.page_count == 2 + sum(per(u) for u in toc), f'{d.page_count} pages'))
        for n, v in ud.items():
            s, nt = v['start'], len(v['tiles'])
            for i, t in enumerate(v['tiles'], 1):
                txt = d[s + i - 1].get_text('text', flags=0)
                checks.append((f'toc.u{n}.tile{i}.on_its_page', norm(t['title'])[:16] in norm(txt) and f'TILE {i} |' in txt,
                               f'"{t["title"]}" on page {s + i}'))
                checks.append((f'continuity.u{n}.tile{i}.key_link', f'answer key on page {v["key"]}' in re.sub(r'\s+', ' ', txt),
                               f'points to page {v["key"]}'))
                checks += [(f'lessons.u{n}.p{s + i}.{c["check"].split(".")[-1]}', c['passed'], c['detail'])
                           for c in construction.reader_checks(txt, f'u{n}t{i}')]
            prac = ' '.join(d[s + nt + k - 1].get_text('text', flags=0) for k in (1, 2))
            key = re.sub(r'\s+', ' ', d[v['key'] - 1].get_text('text', flags=0))
            checks.append((f'continuity.u{n}.problems_1_12', all(f'{k}. ' in prac for k in range(1, 13)), 'problems 1-12 on the practice pages'))
            checks.append((f'continuity.u{n}.answers_1_12', all(f'{k}. ' in key for k in range(1, 13)) and 'Answer key' in key, 'answers 1-12 in the key'))
            checks.append((f'continuity.u{n}.board', '19. Teach it back aloud' in d[s + nt + 2].get_text('text', flags=0), '19-tile board'))
    failed = [c for c in checks if not c[1]]
    return {'pdf': str(out_pdf), 'sha256': hashlib.sha256(out_pdf.read_bytes()).hexdigest(), 'pages': 2 + sum(per(u) for u in toc),
            'mandatory_checks': len(checks), 'failed': len(failed),
            'decision': 'PASS - awaiting owner approval' if not failed else 'FAIL - back to the builder',
            'failures': [list(c) for c in failed], 'design_reference': 'owner-approved ByrdWay Concept Tiles (measured layout)'}
