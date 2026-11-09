"""Blueprint-driven builders (Agents 4 and 5, milestone F).

Power Tool Builder  : blueprint -> one self-contained interactive HTML module at a time.
Lil Dr. Byrd Builder: chapter blueprint -> print-ready HTML + PDF, one chapter at a time.

Guarantees:
  * content comes ONLY from the owner blueprint; every item carries provenance
    ('owner_blueprint' by default, or e.g. 'ai_draft:<model>' which forces review);
  * module/chapter N+1 cannot be built until N is OWNER_APPROVED;
  * every answer is checked by the independent verifier; an INCORRECT answer
    blocks the module; UNSUPPORTED answers require owner attestation;
  * the approved layout template and Lil Dr. Byrd mascot come only from the
    approved-asset registry. If missing, the artwork task is BLOCKED (never
    substituted) while the rest of the build continues;
  * the built-in layout is labelled PROVISIONAL and Release QA blocks it until
    the owner supplies/approves the real ByrdWay template.
"""
import html, json, re, shutil, uuid
from pathlib import Path
from engine import workspace, write_json, read_json, sha256, utcnow, atomic_write_text
from academic import verify_item, CORRECT, INCORRECT
from assets import get_asset, LIL_DR_BYRD_ID

E = html.escape
APPROVAL_READY = 'BUILT_VERIFIED_AWAITING_APPROVAL'


# ------------------------------------------------------------ validation
def validate_power_tool_blueprint(bp):
    errs = []
    for k in ('product_title', 'subject', 'modules'):
        if not bp.get(k):
            errs.append(f'missing {k}')
    ids = set()
    for i, m in enumerate(bp.get('modules') or []):
        if not m.get('id') or not re.fullmatch(r'[a-z0-9_\-]{1,40}', str(m.get('id'))):
            errs.append(f'module {i}: id must be lowercase slug')
        if m.get('id') in ids:
            errs.append(f'duplicate module id {m.get("id")}')
        ids.add(m.get('id'))
        if not m.get('title'):
            errs.append(f'module {m.get("id")}: missing title')
        if not any(m.get(k) for k in ('concepts', 'worked_examples', 'practice', 'flashcards', 'cheat_sheet')):
            errs.append(f'module {m.get("id")}: no content sections (blueprint incomplete)')
        for j, q in enumerate(m.get('practice') or []):
            if not q.get('question') or (q.get('answer') in (None, '') and q.get('correct') is None):
                errs.append(f'module {m.get("id")} practice {j}: question and answer required')
    return errs


def validate_chapter_blueprint(bp):
    errs = []
    for k in ('series', 'subject', 'chapters'):
        if not bp.get(k):
            errs.append(f'missing {k}')
    for i, c in enumerate(bp.get('chapters') or []):
        if not c.get('title') or not c.get('sections'):
            errs.append(f'chapter {i + 1}: title and sections required')
    return errs


# ------------------------------------------------------------ build state
class Build:
    def __init__(self, root, build_id):
        self.root = workspace(root)
        self.id = build_id
        self.dir = self.root / 'builds' / build_id
        self.state_path = self.dir / 'state.json'

    @classmethod
    def create(cls, root, blueprint, kind):
        if kind == 'power_tool':
            errs, units = validate_power_tool_blueprint(blueprint), [m['id'] for m in blueprint.get('modules', [])]
        elif kind == 'lil_dr_byrd':
            errs = validate_chapter_blueprint(blueprint)
            units = [f'ch{i + 1:02d}' for i in range(len(blueprint.get('chapters', [])))]
        else:
            raise ValueError('kind must be power_tool or lil_dr_byrd')
        if errs:
            raise ValueError('Blueprint incomplete: ' + '; '.join(errs))
        b = cls(root, uuid.uuid4().hex[:10])
        b.dir.mkdir(parents=True)
        write_json(b.dir / 'blueprint.json', blueprint)
        write_json(b.state_path, {'id': b.id, 'kind': kind, 'created_at': utcnow(),
                                  'blueprint_sha256': sha256(b.dir / 'blueprint.json'),
                                  'order': units, 'units': {u: {'status': 'NOT_BUILT'} for u in units}})
        return b

    @property
    def state(self):
        return read_json(self.state_path)

    def save(self, s):
        write_json(self.state_path, s)

    @property
    def blueprint(self):
        if sha256(self.dir / 'blueprint.json') != self.state['blueprint_sha256']:
            raise ValueError('Blueprint changed after build creation; create a new build')
        return read_json(self.dir / 'blueprint.json')

    def _require_previous_approved(self, unit):
        s = self.state
        order = s['order']
        if unit not in order:
            raise ValueError(f'Unknown module/chapter {unit}')
        for prev in order[:order.index(unit)]:
            if s['units'][prev]['status'] != 'OWNER_APPROVED':
                raise PermissionError(f'{prev} must be OWNER_APPROVED before building {unit}')

    def approve(self, unit, owner_confirmed=False, attest_unsupported=False, note=''):
        if owner_confirmed is not True:
            raise PermissionError('Explicit owner approval required')
        s = self.state
        u = s['units'][unit]
        if u['status'] not in (APPROVAL_READY, 'NEEDS_OWNER_REVIEW'):
            raise PermissionError(f'{unit} is {u["status"]}; cannot approve')
        if u['status'] == 'NEEDS_OWNER_REVIEW' and not attest_unsupported:
            raise PermissionError('Unverified or AI-drafted items present: owner must attest they reviewed them')
        if sha256(u['output']) != u['output_sha256']:
            raise ValueError('Built output modified after verification')
        u.update(status='OWNER_APPROVED', approved_at=utcnow(), approval_note=note,
                 owner_attested_unverified=bool(attest_unsupported))
        self.save(s)
        return u

    def reject(self, unit, reason):
        s = self.state
        s['units'][unit].update(status='OWNER_REJECTED', rejected_at=utcnow(), reject_reason=reason)
        self.save(s)


def _verify_items(items, where):
    results, n_bad, n_unsup, prov_review = [], 0, 0, 0
    for i, it in enumerate(items):
        src = it.get('source', 'owner_blueprint')
        if not str(src).startswith('owner'):
            prov_review += 1
        if it.get('answer') in (None, '') and it.get('correct') is None:
            continue
        r = verify_item(it)
        r['where'] = f'{where}[{i}]'
        r['question'] = it.get('question')
        r['provenance'] = src
        results.append(r)
        if r['status'] == INCORRECT:
            n_bad += 1
        elif r['status'] != CORRECT:
            n_unsup += 1
    return results, n_bad, n_unsup, prov_review


def _status(n_bad, n_unsup, prov_review, blocked_assets):
    if n_bad:
        return 'BLOCKED_ACADEMIC_DEFECT'
    if n_unsup or prov_review or blocked_assets:
        return 'NEEDS_OWNER_REVIEW' if not blocked_assets else 'BLOCKED_MISSING_APPROVED_ASSET'
    return APPROVAL_READY


# ------------------------------------------------------- Power Tool module
PROVISIONAL_CSS = """
:root{--ink:#14213d;--accent:#1f6feb;--ok:#1a7f37;--bad:#cf222e;--bg:#fbfcfe;--card:#fff}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.5}
header,main{max-width:900px;margin:auto;padding:16px}h1{font-size:1.6rem}h2{border-bottom:2px solid var(--accent);padding-bottom:4px}
.card{background:var(--card);border:1px solid #d0d7de;border-radius:10px;padding:14px;margin:12px 0}
nav a{margin-right:12px}button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--accent);background:#fff;color:var(--accent);cursor:pointer;min-height:44px}
button:focus-visible,input:focus-visible{outline:3px solid #ffb000;outline-offset:2px}
.flash{display:inline-block;width:min(100%,260px);min-height:110px;margin:6px;vertical-align:top}
.feedback.ok{color:var(--ok)}.feedback.bad{color:var(--bad)}input[type=text]{font:inherit;padding:8px;min-width:12ch;max-width:100%}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #d0d7de;padding:6px;text-align:left}
@media print{button{display:none}}
"""

MODULE_JS = r"""
(function(){
 var data = JSON.parse(document.getElementById('bw-data').textContent);
 function norm(s){return String(s).toLowerCase().replace(/\s+/g,'').replace(/^[a-z]=/,'').replace(/×/g,'*').replace(/−/g,'-');}
 function num(s){var t=norm(s); if(/^-?\d+\/\d+$/.test(t)){var p=t.split('/');return Number(p[0])/Number(p[1]);} return /^-?\d*\.?\d+$/.test(t)?Number(t):NaN;}
 function matches(given, q){
   var accepted=[q.answer].concat(q.accept||[]);
   for(var i=0;i<accepted.length;i++){
     if(norm(given)===norm(accepted[i])) return true;
     var a=num(given), b=num(accepted[i]);
     if(!isNaN(a)&&!isNaN(b)&&Math.abs(a-b)<=1e-9*Math.max(1,Math.abs(b))) return true;
   }
   return false;
 }
 var answered={}, correct={};
 function updateScore(){
   var n=data.practice.length, c=0; for(var k in correct){if(correct[k])c++;}
   var el=document.getElementById('bw-score'); if(el) el.textContent='Score: '+c+' / '+n;
 }
 window.bwCheck=function(i){
   var q=data.practice[i], given;
   if(q.choices){var sel=document.querySelector('input[name="q'+i+'"]:checked'); given=sel?q.choices[Number(sel.value)]:'';}
   else {given=document.getElementById('a'+i).value;}
   var ok = given!=='' && (q.choices ? (Number(document.querySelector('input[name="q'+i+'"]:checked').value)===q.correct_index) : matches(given,q));
   answered[i]=true; correct[i]=ok;
   var fb=document.getElementById('f'+i);
   fb.className='feedback '+(ok?'ok':'bad');
   fb.textContent = given==='' ? 'Enter an answer first.' : (ok ? 'Correct! ' : 'Not yet. ') + (q.explanation||'');
   updateScore();
 };
 window.bwFlip=function(btn){
   var showing=btn.getAttribute('aria-pressed')==='true';
   btn.setAttribute('aria-pressed', showing?'false':'true');
   btn.textContent = showing ? btn.dataset.front : btn.dataset.back;
 };
 window.bwPathway=function(){
   var out=document.getElementById('bw-pathway'); if(!out) return;
   var missed={};
   data.practice.forEach(function(q,i){ if(q.skill && !correct[i]) missed[q.skill]=true; });
   var keys=Object.keys(missed);
   if(!keys.length){out.textContent='Great work - no gaps detected. Continue to the next module.';return;}
   out.innerHTML='';
   var p=document.createElement('p'); p.textContent='Recommended review:'; out.appendChild(p);
   var ul=document.createElement('ul');
   keys.forEach(function(k){var li=document.createElement('li'); var a=document.createElement('a');
     a.href='#'+(data.pathway[k]||'concepts'); a.textContent=k; li.appendChild(a); ul.appendChild(li);});
   out.appendChild(ul);
 };
 updateScore();
})();
"""


def _module_html(bp, m, honors_ok):
    parts = []
    sec = lambda sid, title, body: f'<section id="{E(sid)}" aria-labelledby="{E(sid)}-h"><h2 id="{E(sid)}-h">{E(title)}</h2>{body}</section>'
    nav = []
    if m.get('concepts'):
        body = ''.join(f'<div class="card" id="{E(c.get("id") or "concept-%d" % i)}"><h3>{E(c["title"])}</h3>'
                       + ''.join(f'<p>{E(p)}</p>' for p in ([c['explanation']] if isinstance(c.get('explanation'), str) else c.get('explanation', [])))
                       + '</div>' for i, c in enumerate(m['concepts']))
        parts.append(sec('concepts', 'Concepts', body)); nav.append(('concepts', 'Concepts'))
    if m.get('worked_examples'):
        body = ''.join(f'<div class="card"><h3>Example {i + 1}</h3><p><strong>Problem:</strong> {E(w["question"])}</p>'
                       f'<ol>{"".join(f"<li>{E(s)}</li>" for s in w.get("steps", []))}</ol>'
                       f'<p><strong>Answer:</strong> {E(str(w["answer"]))}</p></div>' for i, w in enumerate(m['worked_examples']))
        parts.append(sec('examples', 'Worked Examples', body)); nav.append(('examples', 'Examples'))
    if m.get('cheat_sheet'):
        rows = ''.join(f'<tr><th scope="row">{E(r[0])}</th><td>{E(r[1])}</td></tr>' if isinstance(r, (list, tuple))
                       else f'<tr><td colspan="2">{E(str(r))}</td></tr>' for r in m['cheat_sheet'])
        parts.append(sec('cheat-sheet', 'Cheat Sheet', f'<table>{rows}</table>')); nav.append(('cheat-sheet', 'Cheat Sheet'))
    if m.get('flashcards'):
        body = ''.join(f'<button class="flash card" aria-pressed="false" data-front="{E(f["front"])}" '
                       f'data-back="{E(f["back"])}" onclick="bwFlip(this)">{E(f["front"])}</button>' for f in m['flashcards'])
        parts.append(sec('flashcards', 'Flashcards', '<p>Select a card to flip it.</p>' + body)); nav.append(('flashcards', 'Flashcards'))
    practice = list(m.get('practice') or [])
    if practice:
        qs = []
        for i, q in enumerate(practice):
            if q.get('choices'):
                inp = ''.join(f'<label><input type="radio" name="q{i}" value="{j}"> {E(str(c))}</label><br>' for j, c in enumerate(q['choices']))
            else:
                inp = f'<label for="a{i}">Your answer:</label> <input type="text" id="a{i}" autocomplete="off">'
            qs.append(f'<div class="card"><p><strong>{i + 1}.</strong> {E(q["question"])}</p>{inp} '
                      f'<button type="button" onclick="bwCheck({i})">Check</button>'
                      f'<p class="feedback" id="f{i}" aria-live="polite"></p></div>')
        body = '<p id="bw-score" aria-live="polite"></p>' + ''.join(qs)
        if m.get('pathway'):
            body += '<button type="button" onclick="bwPathway()">Finish &amp; get my study path</button><div id="bw-pathway" aria-live="polite"></div>'
        parts.append(sec('practice', 'Practice', body)); nav.append(('practice', 'Practice'))
    if m.get('honors'):
        if honors_ok:
            body = ''.join(f'<div class="card"><h3>{E(h["title"])}</h3><p>{E(h["explanation"])}</p></div>' for h in m['honors'])
            parts.append(sec('honors', 'Honors Extension', body)); nav.append(('honors', 'Honors'))
    data = {'practice': [{'answer': str(q.get('answer', '')), 'accept': [str(a) for a in q.get('accept', [])],
                          'choices': q.get('choices'), 'correct_index': _choice_index(q),
                          'explanation': q.get('explanation', ''), 'skill': q.get('skill')} for q in practice],
            'pathway': m.get('pathway') or {}}
    data_json = json.dumps(data).replace('</', '<\\/')
    navhtml = '<nav aria-label="Sections">' + ''.join(f'<a href="#{a}">{E(t)}</a>' for a, t in nav) + '</nav>'
    content = f'<header><h1>{E(bp["product_title"])}: {E(m["title"])}</h1>{navhtml}</header><main>{"".join(parts)}</main>'
    return content, data_json


def _choice_index(q):
    if not q.get('choices'):
        return None
    if q.get('correct') is not None:
        c = q['correct']
        return 'abcdefgh'.index(c.lower()) if isinstance(c, str) and not c.isdigit() else int(c)
    try:
        return [str(c) for c in q['choices']].index(str(q.get('answer')))
    except ValueError:
        return None


def _apply_template(root, bp, title, content, data_json):
    tid = bp.get('template_asset_id')
    rec = get_asset(root, tid) if tid else None
    script = f'<script type="application/json" id="bw-data">{data_json}</script><script>{MODULE_JS}</script>'
    if rec:
        tpl = Path(rec['file']).read_text(encoding='utf-8')
        if '{{CONTENT}}' not in tpl:
            raise ValueError('Approved template lacks {{CONTENT}} placeholder')
        out = tpl.replace('{{TITLE}}', E(title)).replace('{{CONTENT}}', content).replace('{{SCRIPT}}', script)
        if '{{SCRIPT}}' not in tpl:
            out = out.replace('</body>', script + '</body>')
        return out, {'template': tid, 'template_sha256': rec['sha256'], 'template_status': 'OWNER_APPROVED_ASSET'}
    page = (f'<!DOCTYPE html>\n<!-- BYRDWAY PROVISIONAL LAYOUT: not the approved ByrdWay design. Release QA blocks '
            f'export until an approved template asset is supplied. -->\n<html lang="en" data-bw-template="provisional">'
            f'<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{E(title)}</title><style>{PROVISIONAL_CSS}</style></head><body>{content}{script}</body></html>')
    return page, {'template': None, 'template_status': 'PROVISIONAL_UNAPPROVED'}


def build_power_tool_module(root, build_id, module_id):
    b = Build(root, build_id)
    if b.state['kind'] != 'power_tool':
        raise ValueError('Not a Power Tool build')
    b._require_previous_approved(module_id)
    bp = b.blueprint
    m = next(x for x in bp['modules'] if x['id'] == module_id)
    honors_ok = bool(bp.get('honors_approved'))
    items = [dict(q) for q in m.get('practice', [])] + [dict(w) for w in m.get('worked_examples', [])]
    results, n_bad, n_unsup, prov = _verify_items(items, f'{module_id}')
    content, data_json = _module_html(bp, m, honors_ok)
    page, tinfo = _apply_template(root, bp, f'{bp["product_title"]} - {m["title"]}', content, data_json)
    out_dir = b.dir / 'modules' / module_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / 'index.html'
    atomic_write_text(out, page)
    status = _status(n_bad, n_unsup, prov, [])
    s = b.state
    s['units'][module_id] = {'status': status, 'output': str(out), 'output_sha256': sha256(out), 'built_at': utcnow(),
                             'verification': results, 'incorrect': n_bad, 'unverified': n_unsup,
                             'non_owner_provenance': prov, 'template': tinfo,
                             'honors': 'included' if (m.get('honors') and honors_ok) else
                                       ('omitted: honors not approved in blueprint' if m.get('honors') else 'none')}
    b.save(s)
    write_json(out_dir / 'provenance.json', {'module': module_id, 'blueprint_sha256': s['blueprint_sha256'],
                                             'items': [{'where': r['where'], 'provenance': r['provenance'],
                                                        'verification': r['status'], 'methods': r['methods']} for r in results],
                                             'template': tinfo, 'generator': 'ByrdWay Studio builders.py (deterministic, no AI)'})
    return s['units'][module_id]


# ------------------------------------------------------ Lil Dr. Byrd chapter
CHAPTER_CSS = """
body{font-family:serif;font-size:11pt;color:#111;line-height:1.45}
h1{font-size:20pt;color:#0b3d91;margin-bottom:4pt}h2{font-size:14pt;color:#0b3d91;border-bottom:1pt solid #0b3d91}
.series{font-size:9pt;letter-spacing:1pt;color:#555}.key{border:1pt solid #0b3d91;padding:6pt;background:#eef3fb}
.example{border-left:3pt solid #e0a800;padding-left:6pt;margin:6pt 0}.answers{font-size:10pt}
img.mascot{width:90pt}img.diagram{width:300pt}
"""


def build_lil_dr_byrd_chapter(root, build_id, unit):
    b = Build(root, build_id)
    if b.state['kind'] != 'lil_dr_byrd':
        raise ValueError('Not a Lil Dr. Byrd build')
    b._require_previous_approved(unit)
    bp = b.blueprint
    idx = int(unit[2:]) - 1
    ch = bp['chapters'][idx]
    blocked = []
    mascot_id = bp.get('mascot_asset_id', LIL_DR_BYRD_ID)
    mascot = get_asset(root, mascot_id)
    out_dir = b.dir / 'chapters' / unit
    out_dir.mkdir(parents=True, exist_ok=True)
    images = {}
    if mascot:
        shutil.copyfile(mascot['file'], out_dir / mascot['name'])
        images['mascot'] = mascot['name']
    else:
        blocked.append({'asset': mascot_id, 'task': 'mascot artwork',
                        'action': 'Owner must register the approved Lil Dr. Byrd image (assets.register_asset kind=mascot). '
                                  'No substitute will be generated.'})
    items, body = [], []
    honors_ok = bool(bp.get('honors_approved'))
    body.append(f'<p class="series">{E(bp["series"])} | {E(bp["subject"])}{" | Honors" if bp.get("honors") else ""}</p>')
    if images.get('mascot'):
        body.append(f'<img class="mascot" src="{E(images["mascot"])}" alt="Lil Dr. Byrd">')
    body.append(f'<h1>Chapter {idx + 1}: {E(ch["title"])}</h1>')
    for s in ch['sections']:
        if s.get('honors') and not honors_ok:
            continue
        body.append(f'<h2>{E(s["heading"])}{" (Honors)" if s.get("honors") else ""}</h2>')
        body += [f'<p>{E(p)}</p>' for p in s.get('paragraphs', [])]
        if s.get('key_idea'):
            body.append(f'<div class="key"><b>Key idea:</b> {E(s["key_idea"])}</div>')
        if s.get('diagram_asset_id'):
            d = get_asset(root, s['diagram_asset_id'])
            if d:
                shutil.copyfile(d['file'], out_dir / d['name'])
                body.append(f'<img class="diagram" src="{E(d["name"])}" alt="{E(s.get("diagram_alt", s["heading"]))}">')
            else:
                blocked.append({'asset': s['diagram_asset_id'], 'task': f'diagram for "{s["heading"]}"',
                                'action': 'Register the approved diagram asset'})
        for w in s.get('worked_examples', []):
            items.append(dict(w))
            body.append(f'<div class="example"><b>Worked example.</b> {E(w["question"])}<ol>'
                        + ''.join(f'<li>{E(x)}</li>' for x in w.get('steps', [])) + f'</ol><b>Result:</b> {E(str(w["answer"]))}</div>')
    practice = ch.get('practice', [])
    if practice:
        body.append('<h2>Practice</h2><ol>' + ''.join(f'<li>{E(q["question"])}</li>' for q in practice) + '</ol>')
        body.append('<h2>Answers &amp; Solutions</h2><ol class="answers">'
                    + ''.join(f'<li>{E(str(q["answer"]))}{(" - " + E(q["explanation"])) if q.get("explanation") else ""}</li>' for q in practice) + '</ol>')
        items += [dict(q) for q in practice]
    results, n_bad, n_unsup, prov = _verify_items(items, unit)
    html_doc = f'<html><head><meta charset="utf-8"><title>{E(ch["title"])}</title><style>{CHAPTER_CSS}</style></head><body>{"".join(body)}</body></html>'
    html_path = out_dir / 'chapter.html'
    atomic_write_text(html_path, html_doc)
    pdf_path = out_dir / f'{unit}.pdf'
    _html_to_pdf(''.join(body), CHAPTER_CSS, out_dir, pdf_path)
    status = _status(n_bad, n_unsup, prov, blocked)
    s = b.state
    s['units'][unit] = {'status': status, 'output': str(pdf_path), 'output_sha256': sha256(pdf_path), 'html': str(html_path),
                        'built_at': utcnow(), 'verification': results, 'incorrect': n_bad, 'unverified': n_unsup,
                        'non_owner_provenance': prov, 'blocked_assets': blocked,
                        'mascot': {'asset_id': mascot_id, 'sha256': mascot['sha256']} if mascot else None}
    b.save(s)
    write_json(out_dir / 'provenance.json', {'chapter': unit, 'blueprint_sha256': s['blueprint_sha256'],
                                             'mascot': s['units'][unit]['mascot'], 'blocked_assets': blocked,
                                             'items': [{'where': r['where'], 'provenance': r['provenance'],
                                                        'verification': r['status']} for r in results]})
    return s['units'][unit]


def _html_to_pdf(body_html, css, base_dir, out_pdf):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    story = fitz.Story(html=f'<body>{body_html}</body>', user_css=css, archive=fitz.Archive(str(base_dir)))
    writer = fitz.DocumentWriter(str(out_pdf))
    mediabox = fitz.paper_rect('letter')
    where = mediabox + (54, 54, -54, -54)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()


# ------------------------------------------------------------ assembly
def assemble(root, build_id, owner_confirmed=False):
    """Package all OWNER_APPROVED units into a single candidate ZIP."""
    import zipfile
    if owner_confirmed is not True:
        raise PermissionError('Explicit owner approval required to assemble')
    b = Build(root, build_id)
    s = b.state
    pending = [u for u in s['order'] if s['units'][u]['status'] != 'OWNER_APPROVED']
    if pending:
        raise PermissionError(f'Units not yet approved: {pending}')
    for u in s['order']:
        if sha256(s['units'][u]['output']) != s['units'][u]['output_sha256']:
            raise ValueError(f'{u} output changed after approval')
    bp = b.blueprint
    out = b.dir / f'{re.sub(r"[^A-Za-z0-9]+", "_", bp.get("product_title") or bp.get("series"))}_{build_id}.zip'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        if s['kind'] == 'power_tool':
            links = ''.join(f'<li><a href="{E(u)}/index.html">{E(next(m["title"] for m in bp["modules"] if m["id"] == u))}</a></li>' for u in s['order'])
            z.writestr('index.html', f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                                     f'content="width=device-width, initial-scale=1"><title>{E(bp["product_title"])}</title></head>'
                                     f'<body><h1>{E(bp["product_title"])}</h1><ul>{links}</ul></body></html>')
            for u in s['order']:
                z.write(s['units'][u]['output'], f'{u}/index.html')
        else:
            for u in s['order']:
                z.write(s['units'][u]['output'], f'{u}.pdf')
        z.writestr('BUILD_PROVENANCE.json', json.dumps({'build': build_id, 'kind': s['kind'],
                                                        'blueprint_sha256': s['blueprint_sha256'],
                                                        'units': {u: {k: v for k, v in s['units'][u].items() if k != 'verification'}
                                                                  for u in s['order']}}, indent=2))
    s['assembled'] = {'path': str(out), 'sha256': sha256(out), 'at': utcnow()}
    b.save(s)
    return out
