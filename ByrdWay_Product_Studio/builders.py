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


def _verify_items(items, where, sample=False):
    results, n_bad, n_unsup, prov_review = [], 0, 0, 0
    for i, it in enumerate(items):
        src = 'sample_not_approved' if sample else it.get('source', 'owner_blueprint')
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
nav{display:flex;flex-wrap:wrap;gap:4px 12px}nav a{margin-right:0}button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--accent);background:#fff;color:var(--accent);cursor:pointer;min-height:44px}
button:focus-visible,input:focus-visible{outline:3px solid #ffb000;outline-offset:2px}
.flash{display:inline-block;width:min(100%,260px);min-height:110px;margin:6px;vertical-align:top}
.feedback.ok{color:var(--ok)}.feedback.bad{color:var(--bad)}input[type=text]{font:inherit;padding:8px;min-width:12ch;max-width:100%}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #d0d7de;padding:6px;text-align:left}
.bw-session li{margin:2px 0}.bw-mascot{width:72px;height:auto;float:right}progress{width:100%;height:14px}
input[type=range]{width:min(100%,320px)}
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
 // ---------------- ByrdWay Mastery Experience layer (placement, gate, hints, faded, generators, review, report)
 var M=data.mastery||null; if(!M){return;}
 var KEY='byrdway:'+M.product, st={};
 try{st=JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){st={};}
 var me=st[M.module]=st[M.module]||{attempts:0,correct:0,streak:0,best_streak:0,mastered:false,placement:null,generated:0,started:Date.now()};
 function save(){try{localStorage.setItem(KEY,JSON.stringify(st));}catch(e){}}
 function txt(id,t){var el=document.getElementById(id); if(el) el.textContent=t; return el;}
 function pct(){var n=data.practice.length,c=0;for(var k in correct){if(correct[k])c++;}return n?c/n:0;}
 function refresh(){
   txt('bw-streak','Streak: '+me.streak+' (best '+me.best_streak+')');
   var done=0,keys=Object.keys(answered).length; var pr=document.getElementById('bw-progress');
   if(pr){pr.max=data.practice.length||1; pr.value=keys;}
   var p=pct(), gate=document.getElementById('bw-gate'), nxt=document.getElementById('bw-next');
   if(p>=M.threshold && keys===data.practice.length){me.mastered=true;
     if(gate){gate.textContent='Mastered ('+Math.round(p*100)+'%). Next skill unlocked!';gate.className='feedback ok';}
     if(nxt){nxt.hidden=false;}}
   else{ if(gate){gate.textContent='Locked: score at least '+Math.round(M.threshold*100)+'% on every Practice question to unlock the next skill (now '+Math.round(p*100)+'%).';gate.className='feedback bad';}
     if(nxt){nxt.hidden=true;}}
   save();
 }
 var baseCheck=window.bwCheck;
 window.bwCheck=function(i){
   baseCheck(i); var q=data.practice[i], ok=correct[i]; me.attempts++;
   if(ok){me.correct++;me.streak++;me.best_streak=Math.max(me.best_streak,me.streak);}
   else{me.streak=0; var fb=document.getElementById('f'+i); if(fb&&q.hint&&fb.textContent.indexOf('Enter')!==0){fb.textContent='Not yet. Hint: '+q.hint;}}
   refresh();
 };
 window.bwPlacement=function(){
   var miss={},out=document.getElementById('bw-placement-path');
   M.placement.forEach(function(q,i){var v=(document.getElementById('p'+i)||{}).value||''; if(!matches(v,q)) miss[q.skill||'core']=true;});
   var ks=Object.keys(miss); me.placement=ks; save();
   out.textContent = ks.length ? 'Your personal path: start with '+ks.join(', ')+', then continue in order.' : 'Placement: you are ready - go straight to the Practice and the Mastery check.';
 };
 window.bwFaded=function(i){
   var f=M.faded[i], v=document.getElementById('fd'+i).value, ok=matches(v,f);
   var fb=document.getElementById('ff'+i); fb.className='feedback '+(ok?'ok':'bad');
   fb.textContent= ok ? 'Correct! Now try the independent Practice.' : 'Not yet. Look back at the worked example step by step.';
 };
 function ev(expr,vals){ if(!/^[\sA-Za-z0-9_+\-*\/().]*$/.test(expr)) throw new Error('bad expr');
   var names=Object.keys(vals); return Function.apply(null,names.concat(['return ('+expr+');'])).apply(null,names.map(function(k){return vals[k];})); }
 function fill(t,v){return t.replace(/\{(\w+)\}/g,function(_,k){return v[k];});}
 var gen=null;
 window.bwGenerate=function(g){
   var G=M.generators[g], v={}; for(var k in G.params){var r=G.params[k];
     do{v[k]=r[0]+Math.floor(Math.random()*(r[1]-r[0]+1));}while((G.nonzero||[]).indexOf(k)>=0&&v[k]===0);}
   for(var c in (G.compute||{})){v[c]=ev(G.compute[c],v);}
   gen={g:g,answer:String(fill(G.answer,v))}; txt('gq'+g,fill(G.template,v)); txt('gf'+g,''); var a=document.getElementById('ga'+g); if(a){a.value='';}
   me.generated++; save();
 };
 window.bwGenCheck=function(g){
   if(!gen||gen.g!==g){bwGenerate(g);return;}
   var v=document.getElementById('ga'+g).value, ok=matches(v,{answer:gen.answer,accept:[]});
   var fb=txt('gf'+g, ok?'Correct! Press New problem for another.':'Not yet. '+(M.generators[g].hint||'Check each step.')); fb.className='feedback '+(ok?'ok':'bad');
   if(ok){me.streak++;me.best_streak=Math.max(me.best_streak,me.streak);}else{me.streak=0;} refresh();
 };
 window.bwReview=function(i){
   var q=M.review[i], v=document.getElementById('rv'+i).value, ok=matches(v,q), fb=txt('rf'+i, ok?'Correct - still mastered.':'Not yet - revisit that earlier skill. '+(q.hint||''));
   fb.className='feedback '+(ok?'ok':'bad');
 };
 window.bwSim=function(){
   var S=M.simulation, v={}; S.inputs.forEach(function(inp){v[inp.name]=Number(document.getElementById('sim-'+inp.name).value); txt('simv-'+inp.name, v[inp.name]+' '+(inp.unit||''));});
   var out=[]; S.outputs.forEach(function(o){var r=ev(o.expr,v); out.push(o.label+' = '+(Math.round(r*1000)/1000)+' '+(o.unit||''));});
   txt('sim-out',out.join('   |   '));
 };
 window.bwReport=function(){
   var rows=[]; for(var mid in st){var r=st[mid]; rows.push(mid+': '+(r.mastered?'MASTERED':'in progress')+', '+r.correct+'/'+r.attempts+' correct, best streak '+r.best_streak+', generated problems '+r.generated);}
   var el=document.getElementById('bw-report-out'); el.textContent=''; var h=document.createElement('p');
   h.textContent='ByrdWay progress report - '+M.product+' - '+new Date().toLocaleDateString(); el.appendChild(h);
   var ul=document.createElement('ul'); rows.forEach(function(t){var li=document.createElement('li'); li.textContent=t; ul.appendChild(li);}); el.appendChild(ul);
 };
 if(M.simulation){bwSim();}
 refresh();
})();
"""


def _module_html(bp, m, honors_ok, mastery=None):
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
    # elements the module script references always exist (hidden when the feature is unused)
    if not practice:
        parts.append('<p id="bw-score" hidden></p>')
    if not (practice and m.get('pathway')):
        parts.append('<div id="bw-pathway" hidden></div>')
    if m.get('honors'):
        if honors_ok:
            body = ''.join(f'<div class="card"><h3>{E(h["title"])}</h3><p>{E(h["explanation"])}</p></div>' for h in m['honors'])
            parts.append(sec('honors', 'Honors Extension', body)); nav.append(('honors', 'Honors'))
    mastery = mastery or {}
    if mastery:
        mp, mdata = _mastery_parts(bp, m, mastery)
        parts = mp['top'] + parts[:] + mp['bottom']
        if mp.get('faded'):
            ix = next((i for i, p in enumerate(parts) if p.startswith('<section id="practice"')), len(parts))
            parts.insert(ix, mp['faded'])
        nav += mp['nav']
    data = {'practice': [{'question': q['question'], 'answer': str(q.get('answer', '')),
                          **({'verify': q['verify']} if q.get('verify') else {}), 'accept': [str(a) for a in q.get('accept', [])],
                          'choices': q.get('choices'), 'correct_index': _choice_index(q),
                          'explanation': q.get('explanation', ''), 'skill': q.get('skill'),
                          'hint': q.get('hint', '')} for q in practice],
            'pathway': m.get('pathway') or {}}
    if mastery:
        data['mastery'] = mdata
    data_json = json.dumps(data).replace('</', '<\\/')
    navhtml = '<nav aria-label="Sections">' + ''.join(f'<a href="#{a}">{E(t)}</a>' for a, t in nav) + '</nav>'
    content = f'<header><h1>{E(bp["product_title"])}: {E(m["title"])}</h1>{navhtml}</header><main>{"".join(parts)}</main>'
    return content, data_json


# ------------------------------------------------------- ByrdWay Mastery Experience (owner standard 2026-11-11)
MASTERY_THRESHOLD = 0.9
SIM_SUBJECTS = ('physics', 'statistic', 'function', 'graph', 'motion', 'calculus')
DEFAULT_BLOCKS = [('Placement check', 10), ('Learn: concepts and worked examples', 25), ('Faded example', 10),
                  ('Independent practice + mastery check', 35), ('Unlimited generated practice', 25),
                  ('Spaced review of earlier skills', 10), ('Progress report', 5)]
BUILTIN_SIMS = {
    'motion': {'title': 'Motion simulator: x = v0 t + (1/2) a t^2',
               'inputs': [{'name': 'v0', 'label': 'Initial velocity v0', 'min': -10, 'max': 10, 'step': 1, 'value': 2, 'unit': 'm/s'},
                          {'name': 'a', 'label': 'Acceleration a', 'min': -5, 'max': 5, 'step': 0.5, 'value': 1, 'unit': 'm/s^2'},
                          {'name': 't', 'label': 'Time t', 'min': 0, 'max': 10, 'step': 0.5, 'value': 3, 'unit': 's'}],
               'outputs': [{'label': 'x', 'expr': 'v0*t + 0.5*a*t*t', 'unit': 'm'},
                           {'label': 'v', 'expr': 'v0 + a*t', 'unit': 'm/s'}]},
    'linear': {'title': 'Line explorer: y = m x + b',
               'inputs': [{'name': 'm', 'label': 'Slope m', 'min': -5, 'max': 5, 'step': 0.5, 'value': 2},
                          {'name': 'b', 'label': 'Intercept b', 'min': -10, 'max': 10, 'step': 1, 'value': 1},
                          {'name': 'x', 'label': 'x', 'min': -10, 'max': 10, 'step': 1, 'value': 3}],
               'outputs': [{'label': 'y', 'expr': 'm*x + b'}]},
}


def needs_simulation(bp, m):
    t = f'{bp.get("subject", "")} {m.get("title", "")}'.lower()
    return bool(m.get('simulation')) or any(k in t for k in SIM_SUBJECTS)


def mastery_data(bp, m, review=(), mascot_uri=None):
    """Everything the Mastery Experience needs, derived ONLY from the owner blueprint (no invented content):
    placement = first practice item of each skill; faded example = the worked example with its last step hidden;
    review = practice items of earlier modules (spaced review); generators/simulation/hints come from the blueprint."""
    practice = list(m.get('practice') or [])
    seen, placement = set(), []
    for q in practice:
        sk = q.get('skill') or 'core'
        if sk not in seen and not q.get('choices'):
            seen.add(sk)
            placement.append({'question': q['question'], 'answer': str(q.get('answer', '')),
                              'accept': [str(a) for a in q.get('accept', [])], 'skill': sk})
    faded = []
    for w in m.get('worked_examples') or []:
        steps = list(w.get('steps') or [])
        if len(steps) >= 2:
            faded.append({'question': w['question'], 'shown': steps[:-1], 'answer': str(w['answer']),
                          'accept': [str(a) for a in w.get('accept', [])]})
    sim = m.get('simulation')
    if isinstance(sim, str):
        sim = BUILTIN_SIMS.get(sim)
    if sim is None and needs_simulation(bp, m):
        sim = BUILTIN_SIMS['motion' if 'physic' in str(bp.get('subject', '')).lower() else 'linear']
    return {'product': bp.get('product_title', ''), 'module': m['id'], 'threshold': MASTERY_THRESHOLD,
            'placement': placement, 'faded': faded, 'generators': list(m.get('generators') or []),
            'review': [{'question': q['question'], 'answer': str(q.get('answer', '')), 'hint': q.get('hint', ''),
                        'accept': [str(a) for a in q.get('accept', [])]} for q in review if not q.get('choices')][:4],
            'simulation': sim, 'blocks': [list(b) for b in (m.get('session_blocks') or DEFAULT_BLOCKS)],
            'mascot': mascot_uri, 'next_module': m.get('_next_title')}


def _mastery_parts(bp, m, M):
    sec = lambda sid, title, body: f'<section id="{E(sid)}" aria-labelledby="{E(sid)}-h"><h2 id="{E(sid)}-h">{E(title)}</h2>{body}</section>'
    mascot = (f'<img class="bw-mascot" src="{M["mascot"]}" alt="Lil Dr. Byrd">' if M.get('mascot') else '')
    total = sum(b[1] for b in M['blocks'])
    top = [sec('session', f'Your {total}-minute session',
               '<ol class="bw-session">' + ''.join(f'<li>{E(b[0])} - {b[1]} min</li>' for b in M['blocks']) + '</ol>'
               '<label for="bw-progress">Progress</label> <progress id="bw-progress" value="0" max="1"></progress>'
               '<p id="bw-streak" aria-live="polite">Streak: 0</p>')]
    if M['placement']:
        items = ''.join(f'<div class="card"><p>{E(q["question"])}</p><label for="p{i}">Your answer:</label> '
                        f'<input type="text" id="p{i}" autocomplete="off"></div>' for i, q in enumerate(M['placement']))
        top.append(sec('placement', 'Placement check (start here)', items +
                       '<button type="button" onclick="bwPlacement()">Get my personal path</button>'
                       '<p id="bw-placement-path" class="feedback" aria-live="polite"></p>'))
    faded = ''
    if M['faded']:
        body = ''
        for i, f in enumerate(M['faded']):
            body += (f'<div class="card">{mascot if i == 0 else ""}<p><strong>Your turn (faded example):</strong> {E(f["question"])}</p><ol>'
                     + ''.join(f'<li>{E(x)}</li>' for x in f['shown']) +
                     f'<li><label for="fd{i}">Complete the last step - answer:</label> <input type="text" id="fd{i}" autocomplete="off"> '
                     f'<button type="button" onclick="bwFaded({i})">Check</button><span class="feedback" id="ff{i}" aria-live="polite"></span></li></ol>'
                     + (f'<p><em>Lil Dr. Byrd: this last step is the hard one - do the same operation to both sides.</em></p>' if i == 0 else '')
                     + '</div>')
        faded = sec('faded', 'Faded example', body)
    bottom = [sec('mastery-gate', 'Mastery check', '<p id="bw-gate" class="feedback bad" aria-live="polite"></p>'
                  f'<p id="bw-next" hidden><strong>Next skill unlocked{": " + E(M["next_module"]) if M.get("next_module") else ""}</strong></p>')]
    if M['generators']:
        body = ''
        for g, G in enumerate(M['generators']):
            body += (f'<div class="card"><p><strong>{E(G.get("skill", "Practice"))}</strong> - unlimited problems, every answer verified.</p>'
                     f'<p id="gq{g}" aria-live="polite">Press New problem.</p><label for="ga{g}">Your answer:</label> '
                     f'<input type="text" id="ga{g}" autocomplete="off"> <button type="button" onclick="bwGenCheck({g})">Check</button> '
                     f'<button type="button" onclick="bwGenerate({g})">New problem</button><p class="feedback" id="gf{g}" aria-live="polite"></p></div>')
        bottom.append(sec('generated', 'Unlimited practice', body))
    if M['review']:
        body = ''.join(f'<div class="card"><p>{E(q["question"])}</p><label for="rv{i}">Your answer:</label> '
                       f'<input type="text" id="rv{i}" autocomplete="off"> <button type="button" onclick="bwReview({i})">Check</button>'
                       f'<p class="feedback" id="rf{i}" aria-live="polite"></p></div>' for i, q in enumerate(M['review']))
        bottom.append(sec('review', 'Spaced review of earlier skills', body))
    if M.get('simulation'):
        S = M['simulation']
        body = f'<p>{E(S.get("title", "Simulation"))}</p>' + ''.join(
            f'<p><label for="sim-{E(i["name"])}">{E(i["label"])}</label> <input type="range" id="sim-{E(i["name"])}" '
            f'min="{i["min"]}" max="{i["max"]}" step="{i["step"]}" value="{i["value"]}" oninput="bwSim()"> '
            f'<span id="simv-{E(i["name"])}"></span></p>' for i in S['inputs']) + '<p id="sim-out" aria-live="polite"></p>'
        bottom.append(sec('simulation', 'Interactive simulation', body))
    bottom.append(sec('report', 'Progress report', '<p>Stored only on this device. No account needed.</p>'
                      '<button type="button" onclick="bwReport()">Show my progress report</button><div id="bw-report-out"></div>'))
    nav = [('placement', 'Placement')] if M['placement'] else []
    nav += [(x, t) for x, t, ok in (('faded', 'Faded', M['faded']), ('mastery-gate', 'Mastery', True),
                                    ('generated', 'Unlimited', M['generators']), ('review', 'Review', M['review']),
                                    ('simulation', 'Simulation', M.get('simulation')), ('report', 'Report', True)) if ok]
    return {'top': top, 'bottom': bottom, 'faded': faded, 'nav': nav}, M


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


DEFAULT_TEMPLATE_ID = 'byrdway_template'


def is_sample(bp):
    return bool(bp.get('_sample')) or str(bp.get('product_title') or bp.get('series') or '').upper().startswith('SAMPLE') \
        or 'SAMPLE' in str(bp.get('_notice', '')).upper()


def _apply_template(root, bp, title, content, data_json):
    tid = bp.get('template_asset_id') or (DEFAULT_TEMPLATE_ID if get_asset(root, DEFAULT_TEMPLATE_ID) else None)
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
    results, n_bad, n_unsup, prov = _verify_items(items, f'{module_id}', is_sample(bp))
    idx = [x['id'] for x in bp['modules']].index(module_id)
    review = [q for x in bp['modules'][:idx] for q in (x.get('practice') or [])]
    m = dict(m, _next_title=bp['modules'][idx + 1]['title'] if idx + 1 < len(bp['modules']) else None)
    mascot = get_asset(root, bp.get('mascot_asset_id', LIL_DR_BYRD_ID))
    mascot_uri = None
    if mascot:
        import base64, mimetypes
        mt = mimetypes.guess_type(mascot['file'])[0] or 'image/png'
        mascot_uri = f'data:{mt};base64,' + base64.b64encode(Path(mascot['file']).read_bytes()).decode()
    M = mastery_data(bp, m, review, mascot_uri)
    content, data_json = _module_html(bp, m, honors_ok, M)
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
    results, n_bad, n_unsup, prov = _verify_items(items, unit, is_sample(bp))
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
                                                        'sample_content': is_sample(bp),
                                                        'blueprint_sha256': s['blueprint_sha256'],
                                                        'units': {u: {k: v for k, v in s['units'][u].items() if k != 'verification'}
                                                                  for u in s['order']}}, indent=2))
    s['assembled'] = {'path': str(out), 'sha256': sha256(out), 'at': utcnow()}
    b.save(s)
    return out


# ---------------------------------------------------------------- form editor support
# Plain-text line formats used by the in-app blueprint form (no JSON for the owner).
SEP = '::'
FORM_HELP = {
    'concepts': 'One per line:  Title :: explanation',
    'worked_examples': 'One per line:  Problem :: step 1; step 2; step 3 :: answer',
    'practice': ('One per line:  Question :: answer\n'
                 'Multiple choice:  Question :: choice A | choice B | choice C :: correct choice\n'
                 'Physics with units (optional 3rd part):  Question :: 49 N :: F = m*a ; m = 5 kg, a = 9.8 m/s^2 ; F'),
    'flashcards': 'One per line:  Front :: Back',
    'cheat_sheet': 'One per line:  Term :: meaning',
    'sections': ('## Heading starts a section (## Honors: Heading = honors section)\n'
                 'KEY: key idea   |   EXAMPLE: problem :: step 1; step 2 :: answer\n'
                 'Any other line = a paragraph'),
}


class FormError(ValueError):
    pass


def _split(line, n_min, n_max, where):
    parts = [p.strip() for p in line.split(SEP)]
    if not n_min <= len(parts) <= n_max or not all(parts[:n_min]):
        raise FormError(f'{where}: expected {n_min}-{n_max} parts separated by "{SEP}", got: {line!r}')
    return parts


def _lines(text):
    return [(i + 1, l.strip()) for i, l in enumerate((text or '').splitlines()) if l.strip()]


def _physics_spec(part):
    """'F = m*a ; m = 5 kg, a = 9.8 m/s^2 ; F' -> verify spec."""
    bits = [b.strip() for b in part.split(';')]
    if len(bits) != 3 or '=' not in bits[0]:
        raise FormError(f'Physics check must be "formula ; givens ; find", got {part!r}')
    given = {}
    for g in bits[1].split(','):
        if '=' not in g:
            raise FormError(f'Given value must look like "m = 5 kg", got {g!r}')
        k, v = g.split('=', 1)
        given[k.strip()] = v.strip()
    return {'type': 'physics', 'formula': bits[0], 'given': given, 'find': bits[2]}


def _practice(text, where):
    out = []
    for n, l in _lines(text):
        p = _split(l, 2, 3, f'{where} practice line {n}')
        if len(p) == 3 and '|' in p[1]:
            choices = [c.strip() for c in p[1].split('|') if c.strip()]
            if p[2] not in choices:
                raise FormError(f'{where} practice line {n}: correct choice {p[2]!r} is not one of {choices}')
            out.append({'question': p[0], 'choices': choices, 'answer': p[2]})
        elif len(p) == 3:
            out.append({'question': p[0], 'answer': p[1], 'verify': _physics_spec(p[2])})
        else:
            out.append({'question': p[0], 'answer': p[1]})
    return out


def _slug(t, used):
    base = re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:30] or 'module'
    s, i = base, 2
    while s in used:
        s, i = f'{base}-{i}', i + 1
    used.add(s)
    return s


def power_tool_blueprint_from_form(form):
    """form: {product_title, subject, grade, honors_approved, modules:[{title, concepts, worked_examples,
    practice, flashcards, cheat_sheet}]} with plain-text line fields. Raises FormError with line numbers."""
    used, mods = set(), []
    for i, m in enumerate(form.get('modules') or [], 1):
        w = f'Module {i} ({m.get("title") or "untitled"})'
        if not (m.get('title') or '').strip():
            raise FormError(f'Module {i}: title is required')
        mod = {'id': _slug(m['title'], used), 'title': m['title'].strip()}
        mod['concepts'] = [{'title': p[0], 'explanation': p[1]} for n, l in _lines(m.get('concepts'))
                           for p in [_split(l, 2, 2, f'{w} concepts line {n}')]]
        mod['worked_examples'] = [{'question': p[0], 'steps': [s.strip() for s in p[1].split(';') if s.strip()],
                                   'answer': p[2]} for n, l in _lines(m.get('worked_examples'))
                                  for p in [_split(l, 3, 3, f'{w} worked examples line {n}')]]
        mod['practice'] = _practice(m.get('practice'), w)
        mod['flashcards'] = [{'front': p[0], 'back': p[1]} for n, l in _lines(m.get('flashcards'))
                             for p in [_split(l, 2, 2, f'{w} flashcards line {n}')]]
        mod['cheat_sheet'] = [[p[0], p[1]] for n, l in _lines(m.get('cheat_sheet'))
                              for p in [_split(l, 2, 2, f'{w} cheat sheet line {n}')]]
        mods.append({k: v for k, v in mod.items() if v != []})
    bp = {'product_title': (form.get('product_title') or '').strip(), 'subject': (form.get('subject') or '').strip(),
          'grade': (form.get('grade') or '').strip(), 'honors_approved': bool(form.get('honors_approved')),
          'modules': mods, '_created_with': 'ByrdWay Studio blueprint form'}
    if form.get('_sample'):
        bp['_sample'] = True
    errs = validate_power_tool_blueprint(bp)
    if errs:
        raise FormError('; '.join(errs))
    return bp


def form_from_power_tool_blueprint(bp):
    def j(rows):
        return '\n'.join(f' {SEP} '.join(r) for r in rows)
    mods = []
    for m in bp.get('modules', []):
        pr = []
        for q in m.get('practice', []):
            if q.get('choices'):
                ans = q.get('answer') if q.get('answer') not in (None, '') else q['choices'][_choice_index(q)]
                pr.append([q['question'], ' | '.join(map(str, q['choices'])), str(ans)])
            elif q.get('verify', {}).get('type') == 'physics':
                v = q['verify']
                pr.append([q['question'], str(q['answer']), f'{v["formula"]} ; ' +
                           ', '.join(f'{k} = {x}' for k, x in v['given'].items()) + f' ; {v["find"]}'])
            else:
                pr.append([q['question'], str(q['answer'])])
        mods.append({'title': m['title'],
                     'concepts': j([[c['title'], c['explanation'] if isinstance(c['explanation'], str)
                                     else ' '.join(c['explanation'])] for c in m.get('concepts', [])]),
                     'worked_examples': j([[w['question'], '; '.join(w.get('steps', [])), str(w['answer'])]
                                           for w in m.get('worked_examples', [])]),
                     'practice': j(pr), 'flashcards': j([[f['front'], f['back']] for f in m.get('flashcards', [])]),
                     'cheat_sheet': j([[str(r[0]), str(r[1])] for r in m.get('cheat_sheet', []) if isinstance(r, (list, tuple))])})
    return {'product_title': bp.get('product_title', ''), 'subject': bp.get('subject', ''),
            'grade': bp.get('grade', ''), 'honors_approved': bool(bp.get('honors_approved')),
            'modules': mods, '_sample': is_sample(bp)}


def chapter_blueprint_from_form(form):
    """form: {subject, honors, honors_approved, chapters:[{title, sections, practice}]}"""
    chs = []
    for i, c in enumerate(form.get('chapters') or [], 1):
        w = f'Chapter {i} ({c.get("title") or "untitled"})'
        if not (c.get('title') or '').strip():
            raise FormError(f'Chapter {i}: title is required')
        sections, cur = [], None
        for n, l in _lines(c.get('sections')):
            if l.startswith('##'):
                head = l.lstrip('#').strip()
                honors = head.lower().startswith('honors:')
                cur = {'heading': head.split(':', 1)[1].strip() if honors else head, 'paragraphs': []}
                if honors:
                    cur['honors'] = True
                sections.append(cur)
                continue
            if cur is None:
                raise FormError(f'{w} sections line {n}: start with a "## Heading" line')
            if l.upper().startswith('KEY:'):
                cur['key_idea'] = l[4:].strip()
            elif l.upper().startswith('EXAMPLE:'):
                p = _split(l[8:], 3, 4, f'{w} sections line {n}')
                ex = {'question': p[0], 'steps': [s.strip() for s in p[1].split(';') if s.strip()], 'answer': p[2]}
                if len(p) == 4:
                    ex['verify'] = _physics_spec(p[3])
                cur.setdefault('worked_examples', []).append(ex)
            else:
                cur['paragraphs'].append(l)
        if not sections:
            raise FormError(f'{w}: at least one "## Heading" section is required')
        chs.append({'title': c['title'].strip(), 'sections': sections, 'practice': _practice(c.get('practice'), w)})
    bp = {'series': 'Lil Dr. Byrd Explainer', 'subject': (form.get('subject') or '').strip(),
          'honors': bool(form.get('honors')), 'honors_approved': bool(form.get('honors_approved')),
          'mascot_asset_id': LIL_DR_BYRD_ID, 'answers_location': 'end_of_chapter', 'chapters': chs,
          '_created_with': 'ByrdWay Studio blueprint form'}
    if form.get('_sample'):
        bp['_sample'] = True
    errs = validate_chapter_blueprint(bp)
    if errs:
        raise FormError('; '.join(errs))
    return bp


def form_from_chapter_blueprint(bp):
    chs = []
    for c in bp.get('chapters', []):
        lines = []
        for s in c['sections']:
            lines.append(('## Honors: ' if s.get('honors') else '## ') + s['heading'])
            lines += s.get('paragraphs', [])
            if s.get('key_idea'):
                lines.append('KEY: ' + s['key_idea'])
            for w in s.get('worked_examples', []):
                parts = [w['question'], '; '.join(w.get('steps', [])), str(w['answer'])]
                if w.get('verify', {}).get('type') == 'physics':
                    v = w['verify']
                    parts.append(f'{v["formula"]} ; ' + ', '.join(f'{k} = {x}' for k, x in v['given'].items()) + f' ; {v["find"]}')
                lines.append('EXAMPLE: ' + f' {SEP} '.join(parts))
        pr = []
        for q in c.get('practice', []):
            if q.get('verify', {}).get('type') == 'physics':
                v = q['verify']
                pr.append(f' {SEP} '.join([q['question'], str(q['answer']), f'{v["formula"]} ; ' +
                                           ', '.join(f'{k} = {x}' for k, x in v['given'].items()) + f' ; {v["find"]}']))
            else:
                pr.append(f'{q["question"]} {SEP} {q["answer"]}')
        chs.append({'title': c['title'], 'sections': '\n'.join(lines), 'practice': '\n'.join(pr)})
    return {'subject': bp.get('subject', ''), 'honors': bool(bp.get('honors')),
            'honors_approved': bool(bp.get('honors_approved')), 'chapters': chs, '_sample': is_sample(bp)}


def save_blueprint(root, bp, kind, name=None):
    """Save to <workspace>/blueprints/<kind>_<name>.json (drafts are kept; nothing is overwritten silently)."""
    d = workspace(root) / 'blueprints'
    d.mkdir(exist_ok=True)
    title = name or bp.get('product_title') or bp.get('chapters', [{}])[0].get('title') or 'blueprint'
    base = f'{kind}_{re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")[:40]}'
    p, i = d / f'{base}.json', 2
    while p.exists():
        p, i = d / f'{base}_{i}.json', i + 1
    write_json(p, bp)
    return p


def prerequisites(root, kind, bp=None):
    """Checklist shown BEFORE building: [(label, ok, explanation)]."""
    from browsertest import playwright_available
    out = []
    if bp is not None:
        errs = validate_power_tool_blueprint(bp) if kind == 'power_tool' else validate_chapter_blueprint(bp)
        out.append(('Blueprint is complete', not errs, '; '.join(errs) or 'OK'))
        out.append(('Content is owner material (not the sample)', not is_sample(bp),
                    'SAMPLE content can be built for practice but Release QA will block it.' if is_sample(bp) else 'OK'))
    if kind == 'power_tool':
        t = get_asset(root, (bp or {}).get('template_asset_id') or DEFAULT_TEMPLATE_ID)
        out.append(('Approved ByrdWay page template registered', bool(t),
                    'OK' if t else 'Not registered: modules use a PROVISIONAL layout and release will be BLOCKED. '
                                   'Use "Register approved template…".'))
        ok = playwright_available()
        out.append(('Browser engine for interaction tests', ok, 'OK' if ok else 'Use Help → Install browser engine (one-time download).'))
    else:
        m = get_asset(root, (bp or {}).get('mascot_asset_id') or LIL_DR_BYRD_ID)
        out.append(('Approved Lil Dr. Byrd image registered', bool(m),
                    'OK' if m else 'Not registered: chapters are built WITHOUT the mascot and release is BLOCKED. '
                                   'Use "Register Lil Dr. Byrd image…". The Studio never draws a substitute.'))
    return out
