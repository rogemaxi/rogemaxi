// ByrdWay Physics I + Honors Power Tool — application entry: shell, routing, settings application.
import * as store from './app/store.js';
import { setLang, t, LANGS } from './app/i18n.js';
import { esc, tt } from './app/ui.js';
import { wireNarration } from './app/narration.js';
import { register3D } from './lab/harness.js';
import * as R3D from './lab/render3d.js';
import * as V from './app/views/index.js';

register3D(R3D);
store.load();
let current = null; // {destroy()} of the active view (labs own animation loops and WebGL contexts)

function applySettings() {
  const s = store.get().settings;
  setLang(s.lang);
  const root = document.documentElement;
  const reduced = s.reducedMotion ?? matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.toggle('reduced-motion', reduced);
  root.classList.toggle('hc', s.contrast === 'high');
  root.style.setProperty('--fs', s.fontScale || 1);
}

function shell(route) {
  const s = store.get().settings;
  const nav = [['home', 'nav.home'], ['units', 'nav.units'], ['labs', 'nav.labs'], ['engines', 'nav.engines'], ['assess', 'nav.assess'], ['videos', 'nav.videos'], ['reference', 'nav.reference'], ['settings', 'nav.settings']];
  return `<a class="skip" href="#main">${tt('nav.skip')}</a>
  <header class="topnav">
    <a class="brand" href="#/home"><span class="logo" aria-hidden="true">◆</span> ${tt('brand')} <span>${tt('product')}</span></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="navlinks">☰ ${tt('nav.menu')}</button>
    <nav class="navlinks" id="navlinks" aria-label="Main">${nav.map(([r, k]) => `<a href="#/${r}" ${route === r ? 'aria-current="page" class="active"' : ''}>${tt(k)}</a>`).join('')}</nav>
    <label class="langsel"><span class="sr-only">${tt('lang.label')}</span>🌐 <select id="langsel" aria-label="${tt('lang.label')}">${LANGS.map(l => `<option value="${l.code}" ${l.code === s.lang ? 'selected' : ''}>${esc(l.native)}</option>`).join('')}</select></label>
  </header>
  ${store.storageOK ? '' : `<div class="banner warn" role="alert">${tt('dash.notsaved')}</div>`}
  <main id="main" tabindex="-1"></main>
  <footer class="foot">${tt('footer')}</footer>`;
}

let routed = false;
function route() {
  current?.destroy?.(); current = null;
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  applySettings();
  const hash = location.hash.replace(/^#\/?/, '') || 'cover';
  const [name, ...rest] = hash.split('/').map(decodeURIComponent);
  const app = document.getElementById('app');
  if (name === 'cover') { app.innerHTML = V.cover(); return; }
  app.innerHTML = shell(name);
  const main = document.getElementById('main');
  wireShell(app);
  try {
    current = V.dispatch(name, rest, main) || null;
  } catch (e) {
    console.error(e);
    main.innerHTML = `<div class="page"><h1>⚠️</h1><p>${esc(e.message)}</p><p><a href="#/home">${tt('gohome')}</a></p></div>`;
  }
  wireNarration(main);
  window.scrollTo(0, 0);
  // On in-app navigation move focus to the new page (screen readers announce it); on first load leave focus at the
  // top so the first Tab reaches the skip link and the navigation.
  if (routed && !history.state?.noFocus) main.focus({ preventScroll: true });
  routed = true;
  document.title = `${t('brand')} ${t('product')}`;
}

function wireShell(app) {
  // The skip link must not change location.hash (that is the router); it only moves focus to the main region.
  app.querySelector('.skip').onclick = e => { e.preventDefault(); app.querySelector('#main').focus(); };
  app.querySelector('#langsel').onchange = e => { store.update(s => { s.settings.lang = e.target.value; }); route(); };
  const mb = app.querySelector('.menu-btn');
  mb.onclick = () => { const nl = app.querySelector('.navlinks'); const open = nl.classList.toggle('open'); mb.setAttribute('aria-expanded', open); };
}

window.addEventListener('hashchange', route);
window.__byrdway = { store, route }; // test hook
route();
