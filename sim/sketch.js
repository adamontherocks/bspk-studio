// 2D sketcher: a see-through drawing plane you place anywhere in the live mechanism.
// Parts go x-ray, and every part the plane passes through is outlined on it, so you can trace the empty space.
// Click to add dots. A filled dot is a sharp corner; double-click it hollow and the line curves smoothly through it.
// Sketches live in the scene (S.sketches), so they save, autosave, undo and go in the report like everything else.
// Loaded after the main script and uses its globals (S, D, scene, world, camera, controls, commit, ...).
(function () {
  'use strict';

  const AXES = {
    z: { label: 'Top · XY', uv: ['X', 'Y'], n: 'Z' },
    y: { label: 'Front · XZ', uv: ['X', 'Z'], n: 'Y' },
    x: { label: 'Side · YZ', uv: ['Y', 'Z'], n: 'X' },
  };
  const COL = { sketch: 0xff7ad9, sketchDim: 0xb7609e, part: 0xff6b5b, sweep: 0xf0b44c, shaft: 0x86bddb, plate: 0x7d8da0, plane: 0x86bddb, rubber: 0xffb3ec };
  const SNAPS = [0, 0.05, 0.1, 0.5, 1];
  const HINT = 'click the plane to add a dot · drag a dot to move it · double-click a dot: sharp ↔ smooth · click a line to insert a dot · drag a line to move the whole drawing · click the first dot (or Enter) to close · Delete removes the selected dot · drag empty space to orbit · Esc to stop';

  const st = { axis: 'z', offset: 4.2, current: null, sel: null, xray: 0.22, cut: false, snap: 0.1, drag: null, down: null, cursor: null, savedExplode: 0 };

  // ---------- coordinates: (u, v) on the plane <-> model mm ----------
  const toModel = (axis, c, u, v) => (axis === 'z' ? [u, v, c] : axis === 'y' ? [u, c, v] : [c, u, v]);
  const toUV = (axis, p) => (axis === 'z' ? [p[0], p[1]] : axis === 'y' ? [p[0], p[2]] : [p[1], p[2]]);
  const cur = () => S.sketches.find(k => k.id === st.current) || null;
  const plane = () => { const k = cur(); return k ? k.plane : { axis: st.axis, offset: st.offset }; };
  const sketching = () => tool === 'sketch';
  const snapV = v => (st.snap ? Math.round(v / st.snap) * st.snap : v);

  // ---------- scene objects ----------
  const group = new THREE.Group();
  group.renderOrder = 10;
  world.add(group);
  const planeGroup = new THREE.Group(), cutGroup = new THREE.Group(), lineGroup = new THREE.Group(), ballGroup = new THREE.Group();
  group.add(planeGroup, cutGroup, lineGroup, ballGroup);
  renderer.localClippingEnabled = true;
  const clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

  function dotTexture(hollow, selected) {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d');
    if (selected) { g.beginPath(); g.arc(32, 32, 30, 0, Math.PI * 2); g.fillStyle = '#ffffff'; g.fill(); }
    g.beginPath(); g.arc(32, 32, selected ? 24 : 26, 0, Math.PI * 2); g.fillStyle = '#0d1319'; g.fill();
    g.beginPath(); g.arc(32, 32, selected ? 19 : 21, 0, Math.PI * 2); g.fillStyle = '#ff7ad9'; g.fill();
    if (hollow) { g.beginPath(); g.arc(32, 32, 11, 0, Math.PI * 2); g.fillStyle = '#0d1319'; g.fill(); }
    return new THREE.CanvasTexture(c);
  }
  const dotMat = {};
  for (const h of [false, true]) for (const s of [false, true]) {
    dotMat[`${h}|${s}`] = new THREE.SpriteMaterial({ map: dotTexture(h, s), depthTest: false, depthWrite: false, sizeAttenuation: false });
  }
  const lineMat = (color, opacity = 1, dashed = false) => (dashed
    ? new THREE.LineDashedMaterial({ color, transparent: true, opacity, depthTest: false, depthWrite: false, dashSize: 0.6, gapSize: 0.4 })
    : new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthTest: false, depthWrite: false }));

  function clear(g) {
    for (const o of [...g.children]) {
      g.remove(o);
      if (o.geometry) o.geometry.dispose();
      if (o.material && !Object.values(dotMat).includes(o.material)) { fatMats.delete(o.material); o.material.dispose(); }
    }
  }
  // Plain WebGL lines are one device pixel wide (half a pixel on a retina screen), too faint to work with.
  // These are real-width lines, in screen pixels.
  const fatMats = new Set();
  function fat(g, pts, color, width, opacity = 1, dashed = false, order = 12) {
    if (pts.length < 2) return;
    const geo = new THREE.LineSegmentsGeometry();
    geo.setPositions(pts.flat());
    const mat = new THREE.LineMaterial({ color, linewidth: width, transparent: true, opacity, depthTest: false, depthWrite: false, dashed, dashSize: 0.5, gapSize: 0.35 });
    mat.resolution.set(canvas.clientWidth, canvas.clientHeight);
    fatMats.add(mat);
    const line = new THREE.LineSegments2(geo, mat);
    if (dashed) line.computeLineDistances();
    line.renderOrder = order;
    g.add(line);
  }
  // A see-through fill: a fan for circles, two triangles for boxes.
  function fill(g, tris, color, opacity, order = 10) {
    if (!tris.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(tris.flat(), 3));
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide, depthTest: false, depthWrite: false }));
    mesh.renderOrder = order;
    g.add(mesh);
  }
  let resW = 0, resH = 0;
  function syncResolution() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (w === resW && h === resH) return;
    resW = w; resH = h;
    for (const m of fatMats) m.resolution.set(w, h);
  }
  function segments(g, pts, mat, order = 11) {
    if (!pts.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts.flat(), 3));
    const ls = new THREE.LineSegments(geo, mat);
    if (mat.isLineDashedMaterial) ls.computeLineDistances();
    ls.renderOrder = order;
    g.add(ls);
  }

  // ---------- the drawing plane: a faint screen with a 1 mm grid ----------
  function extent(axis) {
    const R = S.movementD / 2 * 1.25;
    if (axis === 'z') return [-R, R, -R, R];
    const top = Math.max(...Object.values(D.tops)) + 3;
    return [-R, R, -2, top];
  }
  let planeKey = '';
  function buildPlane() {
    const p = plane(), [u0, u1, v0, v1] = extent(p.axis);
    const key = JSON.stringify([p, u0, u1, v0, v1, sketching()]);
    if (key === planeKey) return;
    planeKey = key;
    clear(planeGroup);
    if (!sketching()) return;
    const P = (u, v) => toModel(p.axis, p.offset, u, v);
    const geo = new THREE.BufferGeometry();
    const a = P(u0, v0), b = P(u1, v0), c = P(u1, v1), d = P(u0, v1);
    geo.setAttribute('position', new THREE.Float32BufferAttribute([...a, ...b, ...c, ...a, ...c, ...d], 3));
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: COL.plane, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthTest: false, depthWrite: false }));
    mesh.renderOrder = 9;
    planeGroup.add(mesh);
    const minor = [], major = [];
    for (let u = Math.ceil(u0); u <= u1; u++) (u % 5 === 0 ? major : minor).push(P(u, v0), P(u, v1));
    for (let v = Math.ceil(v0); v <= v1; v++) (v % 5 === 0 ? major : minor).push(P(u0, v), P(u1, v));
    segments(planeGroup, minor, lineMat(COL.plane, 0.16), 9);
    segments(planeGroup, major, lineMat(COL.plane, 0.4), 9);
    fat(planeGroup, [a, b, b, c, c, d, d, a], COL.plane, 1.5, 0.6, false, 9);
  }

  // ---------- x-ray cuts: every part the plane passes through, outlined on the plane ----------
  function cutShapes(axis, c) {
    const out = [];
    for (const e of elements(S, D)) {
      const style = e.hand ? 'sweep' : (e.gear || e.drum) ? 'part' : 'shaft';
      if (axis === 'z') {
        if (c >= e.z0 - 1e-9 && c <= e.z1 + 1e-9) out.push({ kind: 'circle', u: e.x, v: e.y, r: e.r, style, name: e.name });
      } else {
        const d = (axis === 'x' ? e.x : e.y) - c;
        if (Math.abs(d) < e.r) {
          const w = Math.sqrt(e.r * e.r - d * d), uc = axis === 'x' ? e.y : e.x;
          out.push({ kind: 'rect', u0: uc - w, u1: uc + w, v0: e.z0, v1: e.z1, style, name: e.name });
        }
      }
    }
    const R = S.movementD / 2;
    if (axis === 'z') out.push({ kind: 'circle', u: 0, v: 0, r: R, style: 'plate', name: 'Movement edge' });
    else if (Math.abs(c) < R) { const w = Math.sqrt(R * R - c * c); out.push({ kind: 'rect', u0: -w, u1: w, v0: -1, v1: 0, style: 'plate', name: 'Mainplate' }); }
    return out;
  }
  let cutKey = '', cutsNow = [];
  function buildCuts() {
    const p = plane();
    const key = JSON.stringify([p, sketching(), S.stages, S.solo, S.pos, S.thick, S.hands, S.movementD]);
    if (key === cutKey) return;
    cutKey = key;
    clear(cutGroup);
    cutsNow = sketching() ? cutShapes(p.axis, p.offset) : [];
    const by = { part: [], sweep: [], shaft: [], plate: [] }, area = { part: [], sweep: [], shaft: [], plate: [] };
    const P = (u, v) => toModel(p.axis, p.offset, u, v);
    for (const s of cutsNow) {
      const pts = by[s.style], tri = area[s.style];
      if (s.kind === 'circle') {
        const N = s.r > 2 ? 72 : 20;
        for (let i = 0; i < N; i++) {
          const a0 = i / N * Math.PI * 2, a1 = (i + 1) / N * Math.PI * 2;
          const q0 = P(s.u + s.r * Math.cos(a0), s.v + s.r * Math.sin(a0)), q1 = P(s.u + s.r * Math.cos(a1), s.v + s.r * Math.sin(a1));
          pts.push(q0, q1);
          if (s.style !== 'plate') tri.push(P(s.u, s.v), q0, q1);
        }
        if (s.style === 'shaft') pts.push(P(s.u - 0.4, s.v), P(s.u + 0.4, s.v), P(s.u, s.v - 0.4), P(s.u, s.v + 0.4));
      } else {
        const a = P(s.u0, s.v0), b = P(s.u1, s.v0), c2 = P(s.u1, s.v1), d = P(s.u0, s.v1);
        pts.push(a, b, b, c2, c2, d, d, a);
        tri.push(a, b, c2, a, c2, d);
      }
    }
    // Shaded keep-out areas show what the plane passes through; outlines make the edges crisp.
    fill(cutGroup, area.plate, COL.plate, 0.18, 10);
    fill(cutGroup, area.sweep, COL.sweep, 0.1, 10);
    fill(cutGroup, area.part, COL.part, 0.2, 10);
    fill(cutGroup, area.shaft, COL.shaft, 0.35, 10);
    fat(cutGroup, by.plate, COL.plate, 1.5, 0.8, true, 11);
    fat(cutGroup, by.sweep, COL.sweep, 1.5, 0.9, true, 11);
    fat(cutGroup, by.part, COL.part, 2, 0.95, false, 11);
    fat(cutGroup, by.shaft, COL.shaft, 2, 1, false, 11);
  }

  // ---------- the polyspline: straight between sharp dots, smooth (Catmull-Rom) through hollow ones ----------
  function sample(k) {
    const P = k.points, n = P.length, out = [];
    if (n < 2) return n ? [[P[0].u, P[0].v, 0]] : [];
    const at = i => P[((i % n) + n) % n];
    const tan = i => {
      const p = P[i];
      if (!p.smooth) return [0, 0];
      const prev = k.closed ? at(i - 1) : P[Math.max(0, i - 1)], next = k.closed ? at(i + 1) : P[Math.min(n - 1, i + 1)];
      return [(next.u - prev.u) / 6, (next.v - prev.v) / 6];
    };
    const segs = k.closed ? n : n - 1;
    for (let s = 0; s < segs; s++) {
      const a = P[s], b = at(s + 1), ta = tan(s), tb = tan((s + 1) % n);
      const N = !a.smooth && !b.smooth ? 1 : 24;
      const c1 = [a.u + ta[0], a.v + ta[1]], c2 = [b.u - tb[0], b.v - tb[1]];
      for (let j = s === 0 ? 0 : 1; j <= N; j++) {
        const t = j / N, m = 1 - t;
        out.push([m * m * m * a.u + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t * t * t * b.u,
                  m * m * m * a.v + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t * t * t * b.v, s]);
      }
    }
    return out;
  }
  let lineKey = '';
  const balls = [];
  function buildLines() {
    const key = JSON.stringify([S.sketches, st.current, st.sel, sketching(), st.cursor && st.drag == null ? st.cursor : null]);
    if (key === lineKey) return;
    lineKey = key;
    clear(lineGroup);
    clear(ballGroup);
    balls.length = 0;
    for (const k of S.sketches) {
      const pts = sample(k), mine = k.id === st.current && sketching();
      if (pts.length > 1) {
        const segs = [];
        for (let i = 0; i < pts.length - 1; i++) segs.push(toModel(k.plane.axis, k.plane.offset, pts[i][0], pts[i][1]), toModel(k.plane.axis, k.plane.offset, pts[i + 1][0], pts[i + 1][1]));
        fat(lineGroup, segs, mine ? COL.sketch : COL.sketchDim, mine ? 3 : 2, mine ? 1 : 0.8, false, 12);
      }
      if (!mine) continue;
      k.points.forEach((q, i) => {
        const sp = new THREE.Sprite(dotMat[`${!!q.smooth}|${i === st.sel}`]);
        sp.position.set(...toModel(k.plane.axis, k.plane.offset, q.u, q.v));
        const big = i === 0 && !k.closed && k.points.length >= 3;
        sp.scale.set(big ? 0.03 : 0.024, big ? 0.03 : 0.024, 1);
        sp.renderOrder = 15;
        sp.userData.idx = i;
        ballGroup.add(sp);
        balls.push(sp);
      });
      // Rubber band from the last dot to the cursor while you're still drawing.
      if (!k.closed && k.points.length && st.cursor && !st.drag) {
        const last = k.points[k.points.length - 1];
        fat(lineGroup, [toModel(k.plane.axis, k.plane.offset, last.u, last.v), toModel(k.plane.axis, k.plane.offset, st.cursor[0], st.cursor[1])], COL.rubber, 1.5, 0.75, true, 12);
      }
    }
  }

  // ---------- picking ----------
  const ray = new THREE.Raycaster(), ndc2 = new THREE.Vector2();
  function aim(cx, cy) {
    const r = canvas.getBoundingClientRect();
    ndc2.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc2, camera);
  }
  function planeUV(cx, cy) {
    const p = plane();
    aim(cx, cy);
    const n = new THREE.Vector3(p.axis === 'x' ? 1 : 0, p.axis === 'y' ? 1 : 0, p.axis === 'z' ? 1 : 0);
    const hit = ray.ray.intersectPlane(new THREE.Plane(n, -p.offset * scale), new THREE.Vector3());
    if (!hit) return null;
    const m = world.worldToLocal(hit);
    return toUV(p.axis, [m.x, m.y, m.z]);
  }
  function ballAt(cx, cy) {
    if (!balls.length) return null;
    // Dots rebuilt since the last frame have no screen position yet; without this they all "cover" the screen.
    group.updateMatrixWorld(true);
    aim(cx, cy);
    const h = ray.intersectObjects(balls, false)[0];
    return h ? h.object.userData.idx : null;
  }
  // Nearest line of the current sketch, in screen pixels.
  function lineAt(cx, cy) {
    const k = cur();
    if (!k || k.points.length < 2) return null;
    const r = canvas.getBoundingClientRect(), pts = sample(k), v = new THREE.Vector3();
    const scr = pts.map(q => { v.set(...toModel(k.plane.axis, k.plane.offset, q[0], q[1])); world.localToWorld(v); v.project(camera); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height, q[2]]; });
    let best = null;
    for (let i = 0; i < scr.length - 1; i++) {
      const [x1, y1] = scr[i], [x2, y2] = scr[i + 1], dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, ((cx - x1) * dx + (cy - y1) * dy) / L2)) : 0;
      const d = Math.hypot(cx - (x1 + t * dx), cy - (y1 + t * dy));
      if (!best || d < best.d) best = { d, seg: scr[i + 1][2] };
    }
    return best && best.d < 8 ? best.seg : null;
  }
  // Snap to the grid, and onto a shaft centre when close to one (top plane only).
  function snapUV(uv) {
    let [u, v] = [snapV(uv[0]), snapV(uv[1])];
    if (plane().axis === 'z') for (const s of cutsNow) if (s.style === 'shaft' && Math.hypot(uv[0] - s.u, uv[1] - s.v) < 0.35) { u = s.u; v = s.v; }
    return [+u.toFixed(4), +v.toFixed(4)];
  }

  // ---------- edits: each one is recorded, so it autosaves and undoes ----------
  // Quick edits to one sketch merge into one log line and one undo step; the line lists every action in it.
  let burst = { key: '', actions: [] };
  function save(k, what) {
    const key = `sk:${k.id}`, last = history[hIndex];
    const merging = hIndex > 0 && hIndex === history.length - 1 && last.key === key && performance.now() - last.time < MERGE_MS && burst.key === key;
    burst = merging ? { key, actions: [...burst.actions, what] } : { key, actions: [what] };
    const acts = burst.actions.slice();
    commit({ key, from: 0, to: 0, adapt: false,
      make: () => `${k.name}: ${acts.join(', ')} (${k.points.length} dot${k.points.length === 1 ? '' : 's'}${k.closed ? ', closed' : ''})` });
    showReadout();
  }
  function newSketch() {
    const n = S.sketches.reduce((mx, k) => Math.max(mx, +String(k.id).slice(1) || 0), 0) + 1;
    const k = { id: `K${n}`, name: `Sketch ${n}`, plane: { axis: st.axis, offset: +st.offset.toFixed(4) }, closed: false, points: [] };
    S.sketches.push(k);
    st.current = k.id;
    st.sel = null;
    return k;
  }

  canvas.addEventListener('pointerdown', e => {
    if (!sketching() || e.button !== 0) return;
    const bi = ballAt(e.clientX, e.clientY);
    const li = bi == null ? lineAt(e.clientX, e.clientY) : null;
    if (bi != null || li != null) {
      e.stopImmediatePropagation();
      controls.enabled = false;
      const k = cur();
      st.drag = { kind: bi != null ? 'dot' : 'line', idx: bi, seg: li, x: e.clientX, y: e.clientY, moved: false,
                  start: planeUV(e.clientX, e.clientY), orig: k.points.map(q => ({ ...q })) };
      if (bi != null) st.sel = bi;
      buildLines();
      renderPanel();
      return;
    }
    st.down = { x: e.clientX, y: e.clientY };
  }, { capture: true });

  canvas.addEventListener('pointermove', e => {
    if (!sketching()) return;
    const uv = planeUV(e.clientX, e.clientY);
    st.cursor = uv ? snapUV(uv) : null;
    showReadout();
    const d = st.drag;
    if (d && uv) {
      if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 3) return;
      d.moved = true;
      const k = cur();
      if (d.kind === 'dot') {
        const [u, v] = snapUV(uv);
        k.points[d.idx].u = u; k.points[d.idx].v = v;
      } else if (d.start) {
        const du = snapV(uv[0] - d.start[0]), dv = snapV(uv[1] - d.start[1]);
        k.points.forEach((q, i) => { q.u = +(d.orig[i].u + du).toFixed(4); q.v = +(d.orig[i].v + dv).toFixed(4); });
      }
      updateDotFields();
    }
    buildLines();
  });

  window.addEventListener('pointerup', e => {
    if (!sketching()) return;
    const d = st.drag, k = cur();
    if (d) {
      st.drag = null;
      controls.enabled = true;
      if (d.moved) save(k, d.kind === 'dot' ? `moved dot ${d.idx + 1}` : 'moved the whole drawing');
      else if (d.kind === 'dot' && d.idx === 0 && !k.closed && k.points.length >= 3) {
        // Wait a moment: if this turns out to be a double-click (sharp/smooth), don't close.
        clearTimeout(st.closeTimer);
        st.closeTimer = setTimeout(() => { const kk = cur(); if (kk && kk.id === k.id && !kk.closed && kk.points.length >= 3) { kk.closed = true; save(kk, 'closed the shape'); renderPanel(); } }, 280);
      }
      else if (d.kind === 'line' && planeUV(e.clientX, e.clientY)) {
        const [u, v] = snapUV(planeUV(e.clientX, e.clientY));
        k.points.splice(d.seg + 1, 0, { u, v, smooth: false });
        st.sel = d.seg + 1;
        save(k, `inserted dot ${d.seg + 2}`);
      }
      buildLines();
      renderPanel();
      return;
    }
    const down = st.down;
    st.down = null;
    if (!down || e.target !== canvas || e.button !== 0 || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return;
    const uv = planeUV(e.clientX, e.clientY);
    if (!uv) return;
    let k2 = cur();
    if (k2 && k2.closed) { flash('This shape is closed. Click a line to add a dot, or New sketch to start another.'); return; }
    if (!k2) k2 = newSketch();
    const [u, v] = snapUV(uv);
    k2.points.push({ u, v, smooth: false });
    st.sel = k2.points.length - 1;
    save(k2, k2.points.length === 1 ? 'started' : `added dot ${k2.points.length}`);
    renderPanel();
  });

  canvas.addEventListener('dblclick', e => {
    if (!sketching()) return;
    const bi = ballAt(e.clientX, e.clientY), k = cur();
    if (bi == null || !k) return;
    clearTimeout(st.closeTimer);
    k.points[bi].smooth = !k.points[bi].smooth;
    st.sel = bi;
    save(k, `made dot ${bi + 1} ${k.points[bi].smooth ? 'smooth' : 'sharp'}`);
    renderPanel();
  });

  window.addEventListener('keydown', e => {
    if (!sketching()) return;
    const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName);
    if (typing) return;
    const k = cur();
    if ((e.key === 'Delete' || e.key === 'Backspace') && k && st.sel != null) { e.preventDefault(); deleteDot(); }
    if (e.key === 'Enter' && k && !k.closed && k.points.length >= 3) { k.closed = true; save(k, 'closed the shape'); renderPanel(); }
  });

  function deleteDot() {
    const k = cur();
    if (!k || st.sel == null || !k.points[st.sel]) return;
    const n = st.sel + 1;
    k.points.splice(st.sel, 1);
    if (k.points.length < 3) k.closed = false;
    st.sel = k.points.length ? Math.min(st.sel, k.points.length - 1) : null;
    save(k, `deleted dot ${n}`);
    renderPanel();
  }

  // ---------- view helpers ----------
  function lookStraight() {
    const p = plane(), dist = camera.position.distanceTo(controls.target);
    const t = controls.target.clone();
    if (p.axis === 'z') t.z = p.offset * scale; else if (p.axis === 'y') t.y = p.offset * scale; else t.x = p.offset * scale;
    const side = Math.sign((p.axis === 'z' ? camera.position.z - t.z : p.axis === 'y' ? camera.position.y - t.y : camera.position.x - t.x)) || 1;
    const dir = new THREE.Vector3(p.axis === 'x' ? side : 0, p.axis === 'y' ? side : 0, p.axis === 'z' ? side : 0.0001);
    if (p.axis !== 'z') dir.z += 0.0001;
    controls.target.copy(t);
    camera.position.copy(t).addScaledVector(dir.normalize(), dist);
    controls.update();
  }
  function axisFromView() {
    const d = camera.position.clone().sub(controls.target);
    const a = [Math.abs(d.x), Math.abs(d.y), Math.abs(d.z)];
    return a[2] >= a[0] && a[2] >= a[1] ? 'z' : a[1] >= a[0] ? 'y' : 'x';
  }
  function setAxis(axis) {
    const k = cur();
    if (k && k.points.length) { st.current = null; st.sel = null; }   // keep that drawing on its own plane; the next click starts a new one
    st.axis = axis;
    const t = controls.target;
    st.offset = +((axis === 'z' ? t.z : axis === 'y' ? t.y : t.x) / scale).toFixed(2);
    if (axis === 'z' && Math.abs(st.offset) < 1e-6) st.offset = 4.2;
    const k2 = cur();
    if (k2) k2.plane = { axis, offset: st.offset };
    refresh();
    renderPanel();
  }

  // ---------- cut-away: hide parts on your side of the plane so you can look into the gap ----------
  function applyClip() {
    const on = sketching() && st.cut;
    for (const id of partOrder) {
      const p = parts[id];
      for (const m of [...p.mats, p.edgeMat]) {
        const want = on ? [clip] : null;
        if ((m.clippingPlanes && m.clippingPlanes.length) !== (want && want.length)) { m.clippingPlanes = want; m.needsUpdate = true; }
      }
    }
  }
  function updateClip() {
    if (!(sketching() && st.cut)) return;
    const p = plane(), c = p.offset * scale;
    const n = new THREE.Vector3(p.axis === 'x' ? 1 : 0, p.axis === 'y' ? 1 : 0, p.axis === 'z' ? 1 : 0);
    const camSide = Math.sign(camera.position.dot(n) - c) || 1;
    clip.normal.copy(n).multiplyScalar(-camSide);   // keep what's behind the plane, cut what's between it and you
    clip.constant = camSide * c;
  }

  // ---------- readout over the view ----------
  const readout = document.createElement('div');
  readout.className = 'overlay';
  readout.style.top = '42px';
  readout.hidden = true;
  stage.appendChild(readout);
  let flashUntil = 0, flashText = '';
  function flash(text) { flashText = text; flashUntil = performance.now() + 2600; showReadout(); }
  function showReadout() {
    if (!sketching()) { readout.hidden = true; return; }
    const p = plane(), ax = AXES[p.axis], k = cur();
    const where = `${ax.label} plane at ${ax.n} = ${f2(p.offset * scale)} mm`;
    const at = st.cursor ? ` · cursor ${ax.uv[0]} ${f2(st.cursor[0] * scale)}, ${ax.uv[1]} ${f2(st.cursor[1] * scale)}` : '';
    const what = k ? ` · ${k.name}: ${k.points.length} dots${k.closed ? ', closed' : ''}` : ' · click to start a sketch';
    readout.innerHTML = esc(where + at + what) + (performance.now() < flashUntil ? `<br><span style="color:var(--warn)">${esc(flashText)}</span>` : '');
    readout.hidden = false;
  }

  // ---------- panel ----------
  const section = document.getElementById('sketchSection');
  let panelKey = '';
  function renderPanel(force) {
    const k = cur(), p = plane();
    const key = JSON.stringify([sketching(), st.current, st.sel, st.axis, p.axis, st.cut, st.snap, Math.round(st.xray * 100),
      S.sketches.map(x => [x.id, x.name, x.closed, x.points.length, x.plane.axis]), k && st.sel != null && k.points[st.sel] ? k.points[st.sel].smooth : null]);
    showReadout();
    if (!force && key === panelKey) { updateDotFields(); return; }
    panelKey = key;
    section.innerHTML = '';
    const head = document.createElement('div');
    head.innerHTML = `<div class="eyebrow">Sketch · 2D</div>`;
    section.appendChild(head);
    const btn = document.createElement('div');
    btn.className = 'row';
    btn.innerHTML = `<button class="tool${sketching() ? ' on' : ''}" data-a="tool">${sketching() ? 'Stop sketching' : 'Start sketching'}</button>`;
    section.appendChild(btn);
    if (!sketching()) {
      section.appendChild(para('note', S.sketches.length
        ? `${S.sketches.length} sketch${S.sketches.length > 1 ? 'es' : ''} in this scene, drawn in pink. Start sketching to edit them.`
        : 'Draw on a see-through plane anywhere in the mechanism. Parts go x-ray and the ones the plane cuts are outlined on it, so you can trace the empty space between them.'));
      listSketches();
      return;
    }
    section.appendChild(subHead('Drawing plane'));
    const seg = document.createElement('div');
    seg.className = 'seg';
    seg.innerHTML = Object.entries(AXES).map(([a, d]) => `<button data-axis="${a}" class="${p.axis === a ? 'on' : ''}">${d.label}</button>`).join('') +
      '<button data-a="face">Match my view</button>';
    section.appendChild(seg);
    const R = S.movementD / 2 * 1.2, top = Math.max(...Object.values(D.tops)) + 2;
    const [mn, mx] = p.axis === 'z' ? [-1, top] : [-R, R];
    section.appendChild(control({ label: `Plane position · ${AXES[p.axis].n}`, unit: 'mm', min: mn * scale, max: mx * scale, step: 0.05, value: p.offset * scale,
      onInput: v => { const kk = cur(); if (kk) kk.plane.offset = v / scale; else st.offset = v / scale; refresh(); showReadout(); },
      onCommit: (a, b) => { const kk = cur(); if (kk) save(kk, `moved its plane to ${AXES[p.axis].n} = ${f2(b)} mm`); } }));
    const row2 = document.createElement('div');
    row2.className = 'row';
    row2.innerHTML = '<button data-a="look">Look straight at the plane</button>';
    section.appendChild(row2);
    section.appendChild(control({ label: 'X-ray · how solid the parts look', unit: '%', min: 3, max: 100, step: 1, value: Math.round(st.xray * 100),
      onInput: v => { st.xray = v / 100; xrayOpacity = st.xray; refreshLook(); }, onCommit: () => {} }));
    const opts = document.createElement('div');
    opts.className = 'field-l';
    opts.innerHTML = `<label class="toggle"><input type="checkbox" data-a="cut" ${st.cut ? 'checked' : ''}> Cut away the parts between you and the plane</label>
      <label class="toggle">Snap dots to <select data-a="snap">${SNAPS.map(s => `<option value="${s}" ${s === st.snap ? 'selected' : ''}>${s ? `${s} mm grid` : 'nothing'}</option>`).join('')}</select></label>`;
    section.appendChild(opts);

    section.appendChild(subHead('Sketches'));
    listSketches();
    const row3 = document.createElement('div');
    row3.className = 'row';
    row3.innerHTML = `<button data-a="new">New sketch</button>${k && !k.closed && k.points.length >= 3 ? '<button data-a="close">Close shape</button>' : ''}${k && k.closed ? '<button data-a="open">Open shape</button>' : ''}`;
    section.appendChild(row3);
    if (k && st.sel != null && k.points[st.sel]) {
      const q = k.points[st.sel], ax = AXES[k.plane.axis];
      section.appendChild(subHead(`Dot ${st.sel + 1} of ${k.points.length} · ${q.smooth ? 'smooth' : 'sharp'}`));
      const box = document.createElement('div');
      box.className = 'field-l';
      box.innerHTML = `<div class="row"><label class="field-l" style="flex:1">${ax.uv[0]} mm<input class="txt" type="number" step="0.01" data-f="u"></label><label class="field-l" style="flex:1">${ax.uv[1]} mm<input class="txt" type="number" step="0.01" data-f="v"></label></div>
        <div class="row"><button class="mini" data-a="smooth">${q.smooth ? 'Make it sharp' : 'Make it smooth'}</button><button class="mini" data-a="del">Delete dot</button></div>`;
      section.appendChild(box);
      updateDotFields(true);
    }
    section.appendChild(para('note', 'Click the plane to add dots. Filled dots are sharp corners; double-click one to make it hollow and the line curves through it. Click a line to insert a dot, drag a line to move the whole drawing.'));
  }
  function listSketches() {
    if (!S.sketches.length) return;
    const ul = document.createElement('ul');
    ul.className = 'pins';
    ul.innerHTML = S.sketches.map(x => `<li data-k="${x.id}" class="${x.id === st.current && sketching() ? 'on' : ''}">
      <div class="pin-top"><b style="color:var(--sketch)">${x.id}</b><span class="where">${esc(x.name)} · ${AXES[x.plane.axis].label} at ${AXES[x.plane.axis].n} ${f2(x.plane.offset * scale)} · ${x.points.length} dots${x.closed ? ', closed' : ''}</span>
      ${sketching() ? '<button class="mini" data-a="edit">Edit</button>' : ''}<button class="mini" data-a="delk">Remove</button></div></li>`).join('');
    section.appendChild(ul);
  }
  function updateDotFields(force) {
    const k = cur();
    if (!k || st.sel == null || !k.points[st.sel]) return;
    for (const f of ['u', 'v']) {
      const el = section.querySelector(`[data-f="${f}"]`);
      if (el && (force || document.activeElement !== el)) el.value = +(k.points[st.sel][f] * scale).toFixed(3);
    }
  }
  section.addEventListener('click', e => {
    const a = e.target.dataset.a, axis = e.target.dataset.axis, li = e.target.closest('[data-k]');
    const k = cur();
    if (a === 'tool') setTool(sketching() ? 'select' : 'sketch');
    else if (axis) setAxis(axis);
    else if (a === 'face') setAxis(axisFromView());
    else if (a === 'look') lookStraight();
    else if (a === 'new') { st.current = null; st.sel = null; flash('Click the plane to start the new sketch.'); refresh(); renderPanel(); }
    else if (a === 'close' && k) { k.closed = true; save(k, 'closed the shape'); renderPanel(); }
    else if (a === 'open' && k) { k.closed = false; save(k, 'opened the shape'); renderPanel(); }
    else if (a === 'smooth' && k && st.sel != null) { k.points[st.sel].smooth = !k.points[st.sel].smooth; save(k, `made dot ${st.sel + 1} ${k.points[st.sel].smooth ? 'smooth' : 'sharp'}`); renderPanel(); }
    else if (a === 'del') deleteDot();
    else if (a === 'edit' && li) { st.current = li.dataset.k; st.sel = null; const kk = cur(); st.axis = kk.plane.axis; st.offset = kk.plane.offset; refresh(); renderPanel(); }
    else if (a === 'delk' && li) {
      const kk = S.sketches.find(x => x.id === li.dataset.k);
      S.sketches = S.sketches.filter(x => x.id !== li.dataset.k);
      if (st.current === li.dataset.k) { st.current = null; st.sel = null; }
      commit({ text: `Removed ${kk ? kk.name : 'a sketch'}`, adapt: false });
      renderPanel(true);
    }
  });
  section.addEventListener('change', e => {
    const a = e.target.dataset.a, f = e.target.dataset.f, k = cur();
    if (a === 'cut') { st.cut = e.target.checked; applyClip(); updateClip(); }
    else if (a === 'snap') st.snap = +e.target.value;
    else if (f && k && st.sel != null && e.target.value !== '' && isFinite(+e.target.value)) {
      k.points[st.sel][f] = +(+e.target.value / scale).toFixed(4);
      save(k, `typed dot ${st.sel + 1}`);
    }
  });

  // ---------- hooks the main script calls ----------
  function refresh() {
    if (st.current && !cur()) { st.current = null; st.sel = null; }
    const k = cur();
    if (k && st.sel != null && st.sel >= k.points.length) st.sel = k.points.length ? k.points.length - 1 : null;
    buildPlane();
    buildCuts();
    buildLines();
    if (sketching()) renderPanel();
  }
  function enter() {
    st.savedExplode = explode;
    if (explode > 0) setExplode(0);
    if (!cur() && S.sketches.length) {
      const last = S.sketches[S.sketches.length - 1];
      st.current = last.id; st.axis = last.plane.axis; st.offset = last.plane.offset;
    }
    if (!cur()) { st.axis = axisFromView(); const t = controls.target; st.offset = +((st.axis === 'z' ? t.z : st.axis === 'y' ? t.y : t.x) / scale).toFixed(2); if (st.axis === 'z' && Math.abs(st.offset) < 1e-6) st.offset = 4.2; }
    xrayOpacity = st.xray;
    refreshLook();
    applyClip();
    planeKey = cutKey = lineKey = '';
    refresh();
    showReadout();
  }
  function exit() {
    st.drag = null; st.down = null; st.cursor = null;
    controls.enabled = true;
    xrayOpacity = null;
    refreshLook();
    applyClip();
    planeKey = cutKey = lineKey = '';
    refresh();
    showReadout();
    if (st.savedExplode > 0) setExplode(st.savedExplode);
  }
  function tick() {
    syncResolution();
    updateClip();
    if (performance.now() < flashUntil + 50) showReadout();
  }

  window.Sketcher = { enter, exit, refresh, tick, renderPanel: () => renderPanel(true), hint: HINT,
    // for scripts and tests
    state: () => ({ ...st, drag: !!st.drag }), sample: id => { const k = S.sketches.find(x => x.id === id); return k ? sample(k) : []; },
    cuts: () => cutsNow.map(s => ({ ...s })), setAxis, lookStraight };
  renderPanel(true);
  refresh();
})();
