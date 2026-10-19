// Lab harness: builds the full investigation UI around a lab definition and runs its physics model with a
// fixed time step. The model (pure physics, unit-tested) is the single source of truth for every number shown.
import { t, localize } from '../app/i18n.js';
import { esc, L, P as plain, tt, fmt, parseNumber, gradeNumber, download, extLink } from '../app/ui.js';
import * as store from '../app/store.js';
import { Graph, seriesColor } from './graph.js';
import { Renderer2D } from './render2d.js';
import { RESOURCES } from '../data/curriculum/index.js';

let R3D = null; // lazily resolved 3D module (always bundled; kept separate so a WebGL failure never breaks the page)
export function register3D(mod) { R3D = mod; }

export function labComplete(num) {
  const s = store.get().labs[num];
  return !!(s && s.predicted != null && s.runs > 0 && Object.keys(s.challenge || {}).length > 0 && s.evaluated);
}

export function mountLab(root, lab, opts = {}) {
  const settings = store.get().settings;
  const reduced = settings.reducedMotion ?? matchMedia('(prefers-reduced-motion: reduce)').matches;
  const { value: T } = localize('lab.' + lab.num, lab.text);
  const prog = store.lab(lab.num);
  store.update(() => { prog.opened = true; });
  const params = Object.fromEntries(lab.params.map(p => [p.id, p.value]));
  const res = RESOURCES.labs.find(l => l.num === lab.num);

  root.innerHTML = `
  <section class="lab" aria-labelledby="labttl">
    <header class="lab-head">
      <div class="eyebrow">${tt('engine.labs')} · ${lab.num}</div>
      <h1 id="labttl">${L(T.title)}</h1>
      <p class="lab-q"><strong>${tt('lab.question')}:</strong> ${L(T.question)}</p>
      ${lab.advanced ? `<p class="pw-note">${tt('path.advanced.note')}</p>` : ''}
    </header>
    <div class="lab-predict card" id="lp">
      <h2>${tt('lab.predict')}</h2>
      <p>${L(T.predict.prompt)}</p>
      <div class="choices" role="radiogroup">${T.predict.choices.map((c, i) => `<label class="choice"><input type="radio" name="lpred" value="${i}" ${prog.predicted === i ? 'checked' : ''}> <span>${L(c)}</span></label>`).join('')}</div>
      <button class="btn gold" id="lplock">${tt('lab.predict.lock')}</button>
      <div class="fb" id="lpfb" aria-live="polite"></div>
    </div>
    <div class="lab-main">
      <div class="lab-stage-wrap">
        <div class="lab-stage" id="stage" role="img" aria-label="${esc(plain(T.title))}">
          <div class="hud"><span id="hudt"></span><span class="fxbadge" id="fxbadge" hidden>✦ ${tt('lab.effects.note')}</span></div>
        </div>
        <p class="hint" id="stagehint">${tt('lab.camera.hint')}</p>
        <div class="lab-controls" role="toolbar" aria-label="Simulation controls">
          <button class="btn gold" id="run">▶ ${tt('lab.run')}</button>
          <button class="btn" id="reset">↺ ${tt('lab.reset')}</button>
          <button class="btn" id="replay">⟲ ${tt('lab.replay')}</button>
          <label class="sel">${tt('lab.slow')} <select id="speed"><option value="1">1×</option><option value="0.5">½×</option><option value="0.25">¼×</option><option value="0.1">⅒×</option></select></label>
          <label class="sel">${tt('lab.camera')} <select id="cam"><option value="free">${tt('lab.camera.free')}</option><option value="side">${tt('lab.camera.side')}</option><option value="top">${tt('lab.camera.top')}</option>${lab.camera?.followId ? `<option value="follow">${tt('lab.camera.follow')}</option>` : ''}</select></label>
          <label class="sel">${tt('lab.view')} <select id="view"><option value="quant">${tt('lab.view.quant')}</option><option value="concept">${tt('lab.view.concept')}</option></select></label>
        </div>
        <div class="lab-toggles">
          <label><input type="checkbox" id="tv" checked> ${tt('lab.vectors')}</label>
          <label><input type="checkbox" id="tt" checked> ${tt('lab.trails')}</label>
          <label><input type="checkbox" id="te" checked> ${tt('lab.energy')}</label>
          <label><input type="checkbox" id="tfx" ${reduced ? '' : 'checked'}> ${tt('lab.effects')}</label>
        </div>
      </div>
      <aside class="lab-side">
        <div class="card"><h2>${tt('lab.params')}</h2><div id="params"></div></div>
        <div class="card"><h2>${tt('lab.measure')}</h2><dl class="measures" id="measures" aria-live="off"></dl><div id="ebars"></div></div>
        <div class="card" id="eqcard"><h2>${tt('lab.equations')}</h2><div id="eqs" class="eqs"></div></div>
      </aside>
    </div>
    <div class="lab-data">
      <div class="card"><h2>${tt('lab.graph')}</h2>
        ${lab.graph.choices ? `<label class="sel">y: <select id="gsel">${lab.graph.choices.map((c, i) => `<option value="${i}">${esc(c.label)}</option>`).join('')}</select></label>` : ''}
        <canvas id="graph" class="graph" role="img" aria-label="${tt('lab.graph')}"></canvas></div>
      <div class="card"><h2>${tt('lab.data')}</h2>
        <div class="row"><button class="btn" id="rec">● ${tt('lab.record')}</button><button class="btn ghost" id="clr">${tt('lab.clear')}</button><button class="btn ghost" id="csv">${tt('lab.export')}</button></div>
        <div class="tablewrap"><table class="data" id="runs"></table></div></div>
    </div>
    <div class="lab-tasks">
      <div class="card"><h2>${tt('lab.guided')}</h2><ol class="guided">${T.guided.map(g => `<li>${L(g)}</li>`).join('')}</ol></div>
      <div class="card"><h2>${tt('lab.challenge')}</h2><ol class="challenges">${T.challenges.map((c, i) => `<li><p>${L(c)}</p><button class="btn" data-ch="${i}">${tt('lab.challenge.check')}</button> <span class="fb" id="chfb${i}" aria-live="polite">${prog.challenge?.[i] ? '✓ ' + tt('lab.challenge.met') : ''}</span></li>`).join('')}</ol></div>
      <div class="card"><h2>${tt('lab.evaluate')}</h2><p id="evq"></p>
        <div class="qrow"><input class="qin" id="evin" inputmode="decimal" aria-label="${tt('q.answer')}"><span class="unit" id="evunit"></span><button class="btn gold" id="evbtn">${tt('q.check')}</button></div>
        <div class="fb" id="evfb" aria-live="polite"></div></div>
      <details class="card"><summary><h2>${tt('lab.honors')}</h2></summary><p>${L(T.honors.prompt)}</p><details><summary>${tt('q.solution')}</summary><p>${L(T.honors.solution)}</p></details></details>
      <details class="card" open><summary><h2>${tt('lab.assumptions')}</h2></summary><ul>${T.assumptions.map(a => `<li>${L(a)}</li>`).join('')}</ul></details>
      ${res ? `<div class="card"><h2>${tt('lab.videos')}</h2><p class="hint">${tt('videos.note')}</p><div class="vlinks">${extLink(res.links.khan, tt('videos.khan'), 'vbtn khan')}${extLink(res.links.oct, tt('videos.oct'), 'vbtn oct')}${extLink(res.links.yt, tt('videos.yt'), 'vbtn yt')}</div></div>` : ''}
      <p class="lab-prog" id="lprog"></p>
    </div>
  </section>`;

  const $ = s => root.querySelector(s);
  const stage = $('#stage');

  // ---------- renderer ----------
  const use3D = settings.graphics !== 'low' && R3D && R3D.webglAvailable() && !opts.force2D;
  let rend;
  try { rend = use3D ? new R3D.Renderer3D(stage, lab, { quality: settings.graphics, reducedMotion: reduced }) : new Renderer2D(stage, lab); }
  catch (e) { rend = new Renderer2D(stage, lab); }
  if (rend instanceof Renderer2D) {
    $('#stagehint').textContent = settings.graphics === 'low' ? t('lab.lowgfx') : t('lab.nowebgl');
    $('#cam').disabled = true;
  }
  root.dataset.renderer = rend instanceof Renderer2D ? '2d' : '3d';
  rend.effectsOn = !reduced;

  // ---------- parameters ----------
  const pbox = $('#params');
  pbox.innerHTML = lab.params.map(p => {
    const lbl = L(T.params[p.id] ?? p.id);
    if (p.options) return `<label class="param"><span>${lbl}</span><select data-p="${p.id}">${p.options.map(o => `<option value="${o.value}" ${o.value === p.value ? 'selected' : ''}>${esc(T.options?.[o.value] ? plain(T.options[o.value]) : o.label)}</option>`).join('')}</select></label>`;
    return `<label class="param"><span>${lbl} <output data-o="${p.id}">${fmt(p.value, 4)}</output> ${esc(p.unit || '')}</span>
      <input type="range" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}" data-p="${p.id}" aria-valuetext="${p.value} ${esc(p.unit || '')}"></label>`;
  }).join('');
  pbox.addEventListener('input', e => {
    const id = e.target.dataset.p; if (!id) return;
    const def = lab.params.find(p => p.id === id);
    params[id] = def.options ? (isNaN(+e.target.value) ? e.target.value : +e.target.value) : +e.target.value;
    const o = pbox.querySelector(`[data-o="${id}"]`); if (o) o.textContent = fmt(params[id], 4);
    e.target.setAttribute?.('aria-valuetext', `${params[id]} ${def.unit || ''}`);
    reset();
  });

  // ---------- model & loop ----------
  let model, running = false, speed = 1, simAcc = 0, last = 0, series = [], sampleT = 0, raf = 0, idleFrames = 0;
  const dt = lab.dt || 1 / 240, sampleEvery = lab.sampleEvery || 1 / 30;
  const graph = new Graph($('#graph'), {});
  const runs = [];
  let gsel = 0;

  function reset() {
    running = false; $('#run').innerHTML = `▶ ${esc(t('lab.run'))}`;
    model = lab.create({ ...params });
    rend.resetDynamic(); rend.buildDecor(lab.decor ? lab.decor(params) : []);
    series = []; sampleT = 0; sample(true); draw(0, true); refreshEq(); drawGraph();
    evalQ();
  }
  function sample(force) {
    if (!force && model.t < sampleT - 1e-9) return;
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    series.push({ t: model.t, ...m }); sampleT = model.t + sampleEvery;
  }
  function stepSim(simDt) {
    let n = Math.ceil(simDt / dt - 1e-9), events = [];
    n = Math.min(n, 4000);
    for (let i = 0; i < n && !model.done; i++) { model.step(dt); if (model.events?.length) { events.push(...model.events); model.events.length = 0; } sample(); }
    return events;
  }
  function frame(ts) {
    raf = requestAnimationFrame(frame);
    const now = ts / 1000, real = Math.min(0.05, last ? now - last : 0); last = now;
    let events = [];
    if (running) {
      simAcc += real * speed;
      if (simAcc >= dt) { const chunk = Math.floor(simAcc / dt) * dt; simAcc -= chunk; events = stepSim(chunk); }
      if (model.done) { running = false; finishRun(); $('#run').innerHTML = `▶ ${esc(t('lab.run'))}`; }
      idleFrames = 0;
    } else if (++idleFrames % 2) return; // idle: render at ~30 fps for camera movement
    draw(now, false, events);
  }
  function draw(now, force, events = []) {
    const desc = model.scene({ concept: viewMode === 'concept', energy: $('#te').checked });
    if (events.length) desc.events = events;
    rend.update(desc, now || performance.now() / 1000);
    $('#fxbadge').hidden = !rend.effectVisible;
    $('#hudt').textContent = `${t('lab.time')}: ${model.t.toFixed(2)} s · ${speed}×`;
    if (force || !(idleFrames % 6)) renderMeasures();
  }
  let viewMode = 'quant';
  function renderMeasures() {
    const ms = model.measures();
    $('#measures').innerHTML = ms.filter(m => !m.hidden).map(m => {
      const lbl = T.measures?.[m.id] ? plain(T.measures[m.id]) : m.label;
      return `<div><dt>${esc(lbl)}</dt><dd>${viewMode === 'concept' && m.unit ? conceptBar(m) : `${fmt(m.value, 4)} <span class="u">${esc(m.unit || '')}</span>`}</dd></div>`;
    }).join('');
    const en = model.energy?.();
    $('#ebars').innerHTML = en && $('#te').checked ? energyBars(en) : '';
    if (viewMode === 'quant') refreshEq();
  }
  function conceptBar(m) {
    const ref = Math.abs(m.ref || m.value || 1); const k = Math.min(1, Math.abs(m.value) / ref);
    return `<span class="cbar ${m.value < 0 ? 'neg' : ''}"><span style="width:${Math.round(k * 100)}%"></span></span>`;
  }
  function energyBars(en) {
    const max = Math.max(1e-9, ...en.map(e => Math.abs(e.value)));
    return `<div class="ebars">${en.map(e => `<div class="ebar"><span class="eb-l">${esc(e.label)}</span><span class="eb-t"><span style="width:${Math.round(Math.abs(e.value) / max * 100)}%;background:${e.color}"></span></span><span class="eb-v">${viewMode === 'quant' ? fmt(e.value, 3) + ' J' : ''}</span></div>`).join('')}</div>`;
  }
  function refreshEq() { $('#eqs').innerHTML = lab.equations(params, model, viewMode).map(e => `<div class="eq">${esc(e)}</div>`).join(''); }
  function drawGraph() {
    const G = lab.graph.choices ? lab.graph.choices[gsel] : lab.graph;
    const xk = G.x || 't';
    const cur = (G.y).map((k, i) => ({ label: G.labels?.[i] ?? k, color: seriesColor(i), pts: series.map(s => [s[xk], s[k]]) }));
    const old = runs.flatMap((r, ri) => G.y.map((k, i) => ({ label: `${t('lab.run.n', { n: ri + 1 })}${G.y.length > 1 ? ' ' + (G.labels?.[i] ?? k) : ''}`, color: seriesColor(ri + G.y.length + i), dashed: true, pts: r.series.map(s => [s[xk], s[k]]) })));
    graph.set([...cur, ...old], { xLabel: G.xLabel || 't (s)', yLabel: G.yLabel || '' });
  }
  let gTimer = 0;
  const gLoop = setInterval(() => { if (running && ++gTimer) drawGraph(); }, 250);

  function finishRun() {
    store.update(() => { prog.runs = (prog.runs || 0) + 1; });
    drawGraph(); renderMeasures(); renderRuns(true); progress();
  }
  function renderRuns(autoRecord) {
    if (autoRecord && lab.autoRecord !== false) record(true);
    const keys = lab.recordKeys || model.measures().filter(m => !m.hidden).map(m => m.id);
    const ms = model.measures();
    const lbl = k => { const m = ms.find(x => x.id === k); return (T.measures?.[k] ? plain(T.measures[k]) : m?.label || k) + (m?.unit ? ` (${m.unit})` : ''); };
    $('#runs').innerHTML = runs.length ? `<thead><tr><th>#</th>${lab.params.map(p => `<th>${esc(plain(T.params[p.id] ?? p.id))}${p.unit ? ` (${esc(p.unit)})` : ''}</th>`).join('')}${keys.map(k => `<th>${esc(lbl(k))}</th>`).join('')}</tr></thead><tbody>${runs.map((r, i) => `<tr><td>${i + 1}</td>${lab.params.map(p => `<td>${esc(typeof r.params[p.id] === 'number' ? fmt(r.params[p.id], 4) : r.params[p.id])}</td>`).join('')}${keys.map(k => `<td>${fmt(r.final[k], 4)}</td>`).join('')}</tr>`).join('')}</tbody>` : '';
  }
  function record(auto) {
    const final = Object.fromEntries(model.measures().map(m => [m.id, m.value]));
    const sig = JSON.stringify(params) + model.t.toFixed(4);
    if (runs.length && runs.at(-1).sig === sig) return;
    runs.push({ params: { ...params }, final, series: series.slice(), sig, t: model.t });
    if (runs.length > 8) runs.shift();
    if (!auto) renderRuns(false);
    drawGraph();
  }

  // ---------- controls ----------
  $('#run').onclick = () => {
    if (store.get().labs[lab.num]?.predicted == null) { $('#lpfb').innerHTML = `<span class="warn">${tt('sec.predict.prompt')}</span>`; $('#lp').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' }); return; }
    if (model.done) reset();
    running = !running; last = 0;
    $('#run').innerHTML = running ? `⏸ ${esc(t('lab.pause'))}` : `▶ ${esc(t('lab.run'))}`;
  };
  $('#reset').onclick = reset;
  $('#replay').onclick = () => { if (store.get().labs[lab.num]?.predicted == null) return $('#run').click(); reset(); running = true; $('#run').innerHTML = `⏸ ${esc(t('lab.pause'))}`; };
  $('#speed').onchange = e => { speed = +e.target.value; };
  $('#cam').onchange = e => rend.setCamera(e.target.value, model);
  $('#view').onchange = e => { viewMode = e.target.value; $('#eqcard').hidden = viewMode === 'concept'; renderMeasures(); };
  $('#tv').onchange = e => { rend.showVectors = e.target.checked; if (!e.target.checked) rend.hideVectorLabels?.(); };
  $('#tt').onchange = e => { rend.showTrails = e.target.checked; };
  $('#te').onchange = () => renderMeasures();
  $('#tfx').onchange = e => { rend.effectsOn = e.target.checked; if (!e.target.checked) rend.clearEffects(); };
  $('#rec').onclick = () => record(false);
  $('#clr').onclick = () => { runs.length = 0; renderRuns(false); drawGraph(); };
  $('#csv').onclick = () => {
    const keys = Object.keys(series[0] || { t: 0 });
    const rows = [keys.join(','), ...series.map(s => keys.map(k => s[k]).join(','))];
    download(`byrdway-lab${lab.num}-data.csv`, rows.join('\n'), 'text/csv');
  };
  $('#gsel')?.addEventListener('change', e => { gsel = +e.target.value; drawGraph(); });

  $('#lplock').onclick = () => {
    const sel = root.querySelector('input[name=lpred]:checked');
    if (!sel) { $('#lpfb').innerHTML = `<span class="warn">${tt('q.choose')}</span>`; return; }
    store.update(() => { prog.predicted = +sel.value; });
    $('#lpfb').innerHTML = `✓ ${tt('sec.predict.yours')}: ${L(T.predict.choices[+sel.value])}`;
    progress();
  };
  if (prog.predicted != null) $('#lpfb').innerHTML = `✓ ${tt('sec.predict.yours')}: ${L(T.predict.choices[prog.predicted])}`;

  root.querySelectorAll('[data-ch]').forEach(btn => btn.onclick = () => {
    const i = +btn.dataset.ch, ok = lab.challenges[i]({ params, model, runs });
    $('#chfb' + i).innerHTML = ok ? `<span class="good">✓ ${tt('lab.challenge.met')}</span>` : `<span class="bad">${tt('lab.challenge.notmet')}</span>`;
    if (ok) store.update(() => { (prog.challenge ||= {})[i] = true; });
    progress();
  });

  let evCur = null;
  function evalQ() {
    evCur = lab.evaluate(params);
    const fill = s => String(s).replace(/\{(\w+)\}/g, (_, k) => fmt(evCur.vars?.[k], 4));
    const q = T.evaluate;
    $('#evq').innerHTML = L(q && typeof q === 'object' ? { __untr: fill(q.__untr) } : fill(q));
    $('#evunit').textContent = evCur.unit || '';
    $('#evfb').textContent = '';
  }
  $('#evbtn').onclick = () => {
    const v = parseNumber($('#evin').value);
    if (!$('#evin').value.trim()) return ($('#evfb').textContent = t('q.empty'));
    const g = gradeNumber(v, evCur.answer, evCur.tol ?? 0.03);
    if (g === 'nan') return ($('#evfb').textContent = t('q.nan'));
    $('#evfb').innerHTML = g === 'ok' ? `<span class="good">✓ ${tt('q.correct')} (${fmt(evCur.answer, 4)} ${esc(evCur.unit || '')})</span>` : g === 'close' ? `<span class="warn">${tt('q.close')}</span>` : `<span class="bad">${tt('q.wrong')}</span>`;
    if (g === 'ok') store.update(() => { prog.evaluated = true; });
    progress();
  };

  function progress() {
    const s = store.get().labs[lab.num] || {};
    const yes = b => (b ? '✓' : '—');
    $('#lprog').innerHTML = (labComplete(lab.num) ? `<strong class="good">✓ ${tt('lab.complete')}</strong> · ` : '') +
      esc(t('lab.progress', { p: yes(s.predicted != null), r: s.runs || 0, c: Object.keys(s.challenge || {}).length + '/' + lab.challenges.length, e: yes(s.evaluated) }));
  }

  const onVis = () => { if (document.hidden && running) $('#run').click(); };
  document.addEventListener('visibilitychange', onVis);
  reset(); progress();
  raf = requestAnimationFrame(frame);

  return {
    destroy() { cancelAnimationFrame(raf); clearInterval(gLoop); graph.destroy(); rend.dispose(); document.removeEventListener('visibilitychange', onVis); },
    get model() { return model; }, params, runs, rendererKind: root.dataset.renderer,
  };
}
