// Three.js renderer for lab scenes. It only DRAWS the state that the physics model computes; it never
// changes the physics. Turning effects off, lowering graphics, or using the 2D fallback leaves the model identical.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch { return false; }
}

const col = c => new THREE.Color(c || '#7dd3fc');

export class Renderer3D {
  constructor(host, lab, { quality = 'high', reducedMotion = false } = {}) {
    this.host = host; this.lab = lab; this.quality = quality; this.reducedMotion = reducedMotion;
    this.scale = lab.scale || 1;           // metres per scene unit
    const renderer = new THREE.WebGLRenderer({ antialias: quality === 'high', powerPreference: 'high-performance', preserveDrawingBuffer: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality === 'high' ? 2 : 1));
    renderer.shadowMap.enabled = quality === 'high';
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer = renderer;
    host.append(renderer.domElement);
    renderer.domElement.setAttribute('aria-hidden', 'true');

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(lab.space ? '#02040b' : '#0b1220');
    scene.fog = lab.space ? null : new THREE.Fog('#0b1220', 80, 320);
    this.scene = scene;
    const cam = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);
    this.camera = cam;
    const controls = new OrbitControls(cam, renderer.domElement);
    controls.enableDamping = !reducedMotion; controls.dampingFactor = 0.08;
    this.controls = controls;

    scene.add(new THREE.HemisphereLight('#cfe8ff', '#1e293b', 0.9));
    const sun = new THREE.DirectionalLight('#ffffff', 1.6);
    sun.position.set(8, 14, 10); sun.castShadow = quality === 'high';
    sun.shadow.mapSize.set(1024, 1024);
    Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 20, bottom: -20 });
    scene.add(sun);
    this.sun = sun;

    this.dynamic = new THREE.Group(); scene.add(this.dynamic);
    this.decorGroup = new THREE.Group(); scene.add(this.decorGroup);
    this.fx = new THREE.Group(); scene.add(this.fx);
    this.meshes = new Map(); this.arrows = new Map(); this.lines = new Map(); this.trails = new Map();
    this.particles = [];
    this.labelLayer = document.createElement('div'); this.labelLayer.className = 'lab-labels'; host.append(this.labelLayer);
    this.labelEls = new Map();
    this.effectsOn = true; this.showVectors = true; this.showTrails = true;
    this.fxActiveUntil = 0;
    this.resize();
    this.ro = new ResizeObserver(() => this.resize()); this.ro.observe(host);
    this.setCamera('free');
  }

  v3(p) { return new THREE.Vector3((p[0] || 0) / this.scale, (p[1] || 0) / this.scale, (p[2] || 0) / this.scale); }

  resize() {
    const w = this.host.clientWidth || 600, h = this.host.clientHeight || 360;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = '100%'; this.renderer.domElement.style.height = '100%';
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  setCamera(mode, model) {
    const c = this.lab.camera || {};
    const target = this.v3(c.target || [0, 0, 0]);
    const d = (c.dist || 12) / 1;
    const preset = {
      free: c.free || [0.55, 0.45, 1],
      side: [0, 0.02, 1],
      top: [0, 1, 0.001],
      follow: c.free || [0.55, 0.45, 1],
    }[mode] || [0.55, 0.45, 1];
    const dir = new THREE.Vector3(...preset).normalize().multiplyScalar(d);
    this.camera.position.copy(target).add(dir);
    this.controls.target.copy(target);
    this.followId = mode === 'follow' ? (c.followId || null) : null;
    this.controls.update();
  }

  buildDecor(items = []) {
    this.decorGroup.clear();
    for (const it of items) {
      const obj = this.decorObject(it);
      if (obj) this.decorGroup.add(obj);
    }
  }

  decorObject(it) {
    const S = this.scale;
    const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: col(c), roughness: 0.75, metalness: 0.1, ...o });
    switch (it.shape) {
      case 'ground': {
        const g = new THREE.Mesh(new THREE.PlaneGeometry((it.size || 200) / S, (it.size || 200) / S), mat(it.color || '#16213a'));
        g.rotation.x = -Math.PI / 2; g.position.y = (it.y || 0) / S; g.receiveShadow = true;
        const grid = new THREE.GridHelper((it.size || 200) / S, it.divisions || 40, '#334155', '#1e293b');
        grid.position.y = (it.y || 0) / S + 0.001;
        const grp = new THREE.Group(); grp.add(g, grid); return grp;
      }
      case 'stars': {
        const n = this.quality === 'high' ? 4000 : 1500, pos = new Float32Array(n * 3);
        let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
        for (let i = 0; i < n; i++) {
          const u = rnd() * 2 - 1, th = rnd() * Math.PI * 2, r = 800 + rnd() * 600, s = Math.sqrt(1 - u * u);
          pos.set([r * s * Math.cos(th), r * u, r * s * Math.sin(th)], i * 3);
        }
        const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        return new THREE.Points(geo, new THREE.PointsMaterial({ color: '#cbd5e1', size: 1.6, sizeAttenuation: false }));
      }
      case 'box': case 'sphere': case 'cylinder': case 'cone': case 'torus': case 'plane': {
        const m = this.mesh(it); m.castShadow = m.receiveShadow = this.quality === 'high'; return m;
      }
      case 'ramp': {
        // Right-triangle wedge: base along +x from x0, angle θ, length L (hypotenuse), depth D.
        const L = it.length / S, th = it.angle * Math.PI / 180, D = (it.depth || 1.2) / S;
        const shape = new THREE.Shape(); shape.moveTo(0, 0); shape.lineTo(L * Math.cos(th), 0); shape.lineTo(0, L * Math.sin(th)); shape.lineTo(0, 0);
        const geo = new THREE.ExtrudeGeometry(shape, { depth: D, bevelEnabled: false });
        const m = new THREE.Mesh(geo, mat(it.color || '#475569'));
        m.position.set((it.x || 0) / S, (it.y || 0) / S, -D / 2); m.castShadow = m.receiveShadow = this.quality === 'high';
        return m;
      }
      case 'line': {
        const geo = new THREE.BufferGeometry().setFromPoints(it.pts.map(p => this.v3(p)));
        return new THREE.Line(geo, new THREE.LineBasicMaterial({ color: col(it.color || '#64748b'), transparent: true, opacity: it.opacity ?? 1 }));
      }
      case 'label': { this.staticLabel(it); return null; }
      default: return null;
    }
  }

  mesh(b) {
    const S = this.scale;
    let geo;
    const sz = b.size || [1, 1, 1];
    switch (b.shape) {
      case 'sphere': geo = new THREE.SphereGeometry((b.r || sz[0] / 2) / S, 32, 20); break;
      case 'cylinder': geo = new THREE.CylinderGeometry((b.r || sz[0] / 2) / S, (b.r2 ?? b.r ?? sz[0] / 2) / S, (b.h || sz[1]) / S, 32); break;
      case 'cone': geo = new THREE.ConeGeometry((b.r || 0.5) / S, (b.h || 1) / S, 24); break;
      case 'torus': geo = new THREE.TorusGeometry((b.r || 1) / S, (b.tube || 0.05) / S, 12, 64); break;
      case 'plane': geo = new THREE.PlaneGeometry(sz[0] / S, sz[1] / S); break;
      default: geo = new THREE.BoxGeometry(sz[0] / S, sz[1] / S, (sz[2] ?? sz[0]) / S);
    }
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: col(b.color), roughness: b.rough ?? 0.45, metalness: b.metal ?? 0.15,
      emissive: col(b.emissive || '#000000'), emissiveIntensity: b.emissive ? (b.glow ?? 1) : 0,
      transparent: b.opacity != null, opacity: b.opacity ?? 1, side: b.shape === 'plane' ? THREE.DoubleSide : THREE.FrontSide,
    }));
    if (b.pos) m.position.copy(this.v3(b.pos));
    if (b.rot) m.rotation.set(...b.rot);
    m.castShadow = this.quality === 'high';
    return m;
  }

  // Sync dynamic objects with the model's current scene description.
  update(sceneDesc, now) {
    const seen = new Set();
    for (const b of sceneDesc.bodies || []) {
      const key = b.id + ':' + b.shape + ':' + JSON.stringify(b.size || b.r || '') + (b.h || '');
      let m = this.meshes.get(b.id);
      if (!m || m.userData.key !== key) {
        if (m) this.dynamic.remove(m);
        m = this.mesh(b); m.userData.key = key; this.meshes.set(b.id, m); this.dynamic.add(m);
      }
      m.position.copy(this.v3(b.pos));
      if (b.rot) m.rotation.set(...b.rot);
      if (b.color) m.material.color.set(b.color);
      if (b.emissive) { m.material.emissive.set(b.emissive); m.material.emissiveIntensity = b.glow ?? 1; }
      if (b.opacity != null) m.material.opacity = b.opacity;
      if (b.scale) m.scale.set(...b.scale);
      m.visible = b.visible !== false;
      seen.add('b' + b.id);
      if (b.label) this.label('b' + b.id, b.label, b.pos, b.labelOffset);
      if (b.trail && this.showTrails) this.pushTrail(b.id, b.pos, b.trailColor || b.color);
    }
    for (const [id, m] of this.meshes) if (!seen.has('b' + id)) { this.dynamic.remove(m); this.meshes.delete(id); }

    const seenA = new Set();
    if (this.showVectors) for (const v of sceneDesc.vectors || []) {
      const dir = this.v3(v.vec), len = dir.length();
      let a = this.arrows.get(v.id);
      if (!a) { a = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 1, col(v.color)); this.arrows.set(v.id, a); this.dynamic.add(a); }
      a.visible = len > 1e-6;
      if (len > 1e-6) {
        a.position.copy(this.v3(v.from)); a.setDirection(dir.clone().normalize());
        const head = Math.min(len * 0.3, 0.5 * (v.head || 1));
        a.setLength(len, head, head * 0.6); a.setColor(col(v.color));
        if (v.label) {
          const tip = [v.from[0] + v.vec[0], v.from[1] + v.vec[1], (v.from[2] || 0) + (v.vec[2] || 0)];
          this.label('v' + v.id, v.label, tip, [0, 0.3 * this.scale, 0], v.color);
        }
      }
      seenA.add(v.id);
    }
    for (const [id, a] of this.arrows) if (!seenA.has(id)) { a.visible = false; }

    const seenL = new Set();
    for (const ln of sceneDesc.lines || []) {
      let l = this.lines.get(ln.id);
      const pts = ln.pts.map(p => this.v3(p));
      if (!l || l.userData.n !== pts.length) {
        if (l) this.dynamic.remove(l);
        const geo = new THREE.BufferGeometry().setFromPoints(pts);
        l = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: col(ln.color), transparent: true, opacity: ln.opacity ?? 1 }));
        l.userData.n = pts.length; this.lines.set(ln.id, l); this.dynamic.add(l);
      } else {
        const attr = l.geometry.attributes.position;
        pts.forEach((p, i) => attr.setXYZ(i, p.x, p.y, p.z)); attr.needsUpdate = true; l.geometry.computeBoundingSphere();
        l.material.color.set(ln.color || '#7dd3fc'); l.material.opacity = ln.opacity ?? 1;
      }
      seenL.add(ln.id);
    }
    for (const [id, l] of this.lines) if (!seenL.has(id)) { this.dynamic.remove(l); this.lines.delete(id); }

    for (const [, tr] of this.trails) tr.line.visible = this.showTrails;
    for (const ev of sceneDesc.events || []) this.effect(ev, now);
    this.stepEffects(now);

    for (const [k, el] of this.labelEls) if (!el.dataset.static && !seen.has(k) && !k.startsWith('v')) el.style.display = 'none';
    if (this.followId) {
      const m = this.meshes.get(this.followId);
      if (m) { const d = m.position.clone().sub(this.controls.target); this.controls.target.add(d); this.camera.position.add(d); }
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.placeLabels();
  }

  pushTrail(id, pos, color) {
    let tr = this.trails.get(id);
    if (!tr) {
      const max = 4000, geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(max * 3), 3)); geo.setDrawRange(0, 0);
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: col(color), transparent: true, opacity: 0.85 }));
      tr = { line, n: 0, max }; this.trails.set(id, tr); this.dynamic.add(line);
    }
    const p = this.v3(pos), attr = tr.line.geometry.attributes.position;
    if (tr.n > 0) { const lx = attr.getX(tr.n - 1), ly = attr.getY(tr.n - 1), lz = attr.getZ(tr.n - 1); if (Math.hypot(p.x - lx, p.y - ly, p.z - lz) < 0.02) return; }
    if (tr.n >= tr.max) return;
    attr.setXYZ(tr.n++, p.x, p.y, p.z); attr.needsUpdate = true; tr.line.geometry.setDrawRange(0, tr.n);
  }
  clearTrails() { for (const [, tr] of this.trails) this.dynamic.remove(tr.line); this.trails.clear(); }

  // ---- Cinematic effects (visual only) ----
  effect(ev, now) {
    if (!this.effectsOn || this.reducedMotion || this.quality === 'low') return;
    this.fxActiveUntil = now + 1.2;
    const p = this.v3(ev.pos || [0, 0, 0]), s = ev.strength ?? 1;
    if (ev.type === 'impact' || ev.type === 'burst' || ev.type === 'spark') {
      const n = Math.round((this.quality === 'high' ? 220 : 90) * Math.min(2, s));
      const pos = new Float32Array(n * 3), vel = [];
      for (let i = 0; i < n; i++) {
        pos.set([p.x, p.y, p.z], i * 3);
        const u = Math.random() * 2 - 1, th = Math.random() * 6.283, r = Math.sqrt(1 - u * u), sp = (0.8 + Math.random() * 2.5) * (ev.speed || 1);
        vel.push([r * Math.cos(th) * sp, Math.abs(u) * sp * (ev.type === 'spark' ? 1.5 : 1), r * Math.sin(th) * sp]);
      }
      const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      const mat = new THREE.PointsMaterial({ color: col(ev.color || (ev.type === 'spark' ? '#fde68a' : '#fbbf24')), size: ev.type === 'burst' ? 0.12 : 0.07, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false });
      const pts = new THREE.Points(geo, mat); this.fx.add(pts);
      this.particles.push({ obj: pts, vel, born: now, life: ev.life || 1.1, gravity: ev.type === 'spark' ? 3 : 0.4 });
    }
    if (ev.type === 'impact' || ev.type === 'shock') {
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 64), new THREE.MeshBasicMaterial({ color: col(ev.color || '#7dd3fc'), transparent: true, opacity: 0.8, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
      ring.position.copy(p); if (ev.normal === 'x') ring.rotation.y = Math.PI / 2; else ring.rotation.x = -Math.PI / 2 * (ev.normal === 'y' ? 1 : 0);
      ring.scale.setScalar(0.05); this.fx.add(ring);
      this.particles.push({ obj: ring, ring: true, born: now, life: 0.7, max: 1.5 * s });
    }
    if (ev.type === 'arc') {
      const pts = [], a = this.v3(ev.from), b = this.v3(ev.to);
      for (let i = 0; i <= 14; i++) { const q = a.clone().lerp(b, i / 14); if (i % 14) q.add(new THREE.Vector3((Math.random() - 0.5) * 0.25, (Math.random() - 0.5) * 0.25, (Math.random() - 0.5) * 0.25)); pts.push(q); }
      const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: '#c4b5fd', transparent: true, opacity: 1, blending: THREE.AdditiveBlending }));
      this.fx.add(l); this.particles.push({ obj: l, born: now, life: 0.18 });
    }
  }
  stepEffects(now) {
    const dt = 1 / 60;
    this.particles = this.particles.filter(pt => {
      const age = now - pt.born, k = age / pt.life;
      if (k >= 1 || age < 0) { this.fx.remove(pt.obj); pt.obj.geometry.dispose(); pt.obj.material.dispose(); return false; }
      if (pt.ring) { pt.obj.scale.setScalar(0.05 + k * pt.max); pt.obj.material.opacity = 0.8 * (1 - k); }
      else if (pt.vel) {
        const a = pt.obj.geometry.attributes.position;
        for (let i = 0; i < pt.vel.length; i++) { pt.vel[i][1] -= pt.gravity * dt; a.setXYZ(i, a.getX(i) + pt.vel[i][0] * dt, a.getY(i) + pt.vel[i][1] * dt, a.getZ(i) + pt.vel[i][2] * dt); }
        a.needsUpdate = true; pt.obj.material.opacity = 1 - k;
      } else pt.obj.material.opacity = 1 - k;
      return true;
    });
  }
  get effectVisible() { return this.particles.length > 0; }
  clearEffects() { for (const p of this.particles) this.fx.remove(p.obj); this.particles = []; }

  // ---- HTML labels projected from 3D ----
  label(key, text, pos, offset = [0, 0, 0], color) {
    let el = this.labelEls.get(key);
    if (!el) { el = document.createElement('div'); el.className = 'lab-label'; this.labelLayer.append(el); this.labelEls.set(key, el); }
    if (el.textContent !== text) el.textContent = text;
    if (color) el.style.borderColor = color;
    el.style.display = '';
    el._pos = [pos[0] + (offset[0] || 0), pos[1] + (offset[1] || 0), (pos[2] || 0) + (offset[2] || 0)];
  }
  staticLabel(it) { this.label('s' + it.text, it.text, it.pos, [0, 0, 0], it.color); this.labelEls.get('s' + it.text).dataset.static = '1'; }
  placeLabels() {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    for (const [k, el] of this.labelEls) {
      if (!el._pos || el.style.display === 'none') continue;
      if (k.startsWith('v') && !this.showVectors) { el.style.visibility = 'hidden'; continue; }
      const v = this.v3(el._pos).project(this.camera);
      const behind = v.z > 1;
      el.style.visibility = behind ? 'hidden' : 'visible';
      el.style.transform = `translate(${(v.x * 0.5 + 0.5) * w}px, ${(-v.y * 0.5 + 0.5) * h}px) translate(-50%, -120%)`;
    }
  }
  hideVectorLabels() { for (const [k, el] of this.labelEls) if (k.startsWith('v')) el.style.visibility = 'hidden'; }

  resetDynamic() {
    this.clearTrails(); this.clearEffects();
    for (const [, m] of this.meshes) this.dynamic.remove(m); this.meshes.clear();
    for (const [, a] of this.arrows) this.dynamic.remove(a); this.arrows.clear();
    for (const [, l] of this.lines) this.dynamic.remove(l); this.lines.clear();
    for (const [, el] of this.labelEls) el.remove(); this.labelEls.clear();
  }
  dispose() {
    this.ro.disconnect(); this.controls.dispose(); this.renderer.dispose();
    this.renderer.domElement.remove(); this.labelLayer.remove();
  }
}
