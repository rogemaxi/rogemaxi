// Reproducible build: bundles src/ (including Three.js) with esbuild and inlines JS + CSS into ONE standalone
// HTML file that runs offline from disk (file://). No CDN or network request is needed at runtime.
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';

const root = new URL('..', import.meta.url).pathname;
const t0 = Date.now();
const res = await build({
  entryPoints: [root + 'src/main.js'],
  bundle: true, format: 'iife', minify: process.argv.includes('--dev') ? false : true,
  target: ['es2020', 'chrome90', 'firefox88', 'safari14', 'edge90'],
  write: false, legalComments: 'eof', charset: 'utf8',
  loader: { '.json': 'json' },
  logLevel: 'warning',
});
const js = res.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const css = readFileSync(root + 'src/styles.css', 'utf8');
let html = readFileSync(root + 'src/index.html', 'utf8');
html = html.replace('/*__CSS__*/', () => css).replace('/*__JS__*/', () => js);
mkdirSync(root + 'dist', { recursive: true });
const out = root + 'dist/ByrdWay_Physics_I_Honors.html';
writeFileSync(out, html);
const size = statSync(out).size;
const sha = createHash('sha256').update(html).digest('hex').slice(0, 16);
console.log(`built ${out} — ${(size / 1024).toFixed(0)} KB, sha256 ${sha}, ${Date.now() - t0} ms`);
