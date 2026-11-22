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
  // Colour-blind safe: your lines are yellow, cut parts white (solid edge), hand sweeps pale grey (dashed edge), the plate dark grey,
  // axis centres blue. Red is kept for clashes only.
  const COL = { sketch: 0xffd23f, sketchDim: 0xb39a3a, part: 0xe3e8ec, sweep: 0xb4c0cb, shaft: 0x86bddb, plate: 0x7d8da0, plane: 0x86bddb, rubber: 0xffe9a0 };
  const SNAPS = [0, 0.05, 0.1, 0.5, 1];
  const HINT = 'click the plane to add a dot · drag a dot to move it · double-click a dot: sharp ↔ smooth · click a line to insert a dot · drag a line to move the whole drawing · click the first dot (or Enter) to close · Delete removes the selected dot · drag empty space to orbit · Esc to stop';

  const st = { axis: 'z', offset: 4.2, current: null, sel: null, xray: 0.22, cut: false, snap: 0.1, drag: null, down: null, cursor: null, savedExplode: 0,
               face: 'front' };   // which outline of a selected drawn part its dots edit: 'front' (its sketch) or 'back'

  // ---------- coordinates: (u, v) on the plane <-> model mm ----------
  const toModel = (axis, c, u, v) => (axis === 'z' ? [u, v, c] : axis === 'y' ? [u, c, v] : [c, u, v]);
  const toUV = (axis, p) => (axis === 'z' ? [p[0], p[1]] : axis === 'y' ? [p[0], p[2]] : [p[1], p[2]]);
  const sketching = () => tool === 'sketch';
  // A selected drawn part (in the normal select tool) shows its outline dots, and they edit like a sketch's.
  const editPart = () => (!sketching() && tool === 'select' && selectedId && parts[selectedId] && parts[selectedId].kind === 'drawn' && parts[selectedId].visible
    ? S.drawn.find(d => d.id === selectedId) || null : null);
  const active = () => sketching() || !!editPart();
  const curId = () => { const d = editPart(); return d ? d.sketch : st.current; };
  const cur = () => S.sketches.find(k => k.id === curId()) || null;
  const ownerOf = k => (k ? S.drawn.find(d => d.sketch === k.id) || null : null);
  // What the dots edit right now: the current sketch (sketch tool), or the selected part's front or back outline.
  // pts is the dot list to change; plane is where those dots sit.
  function target() {
    const d = editPart();
    if (!d) { const k = cur(); return k ? { k, d: ownerOf(k), face: 'front', pts: k.points, plane: k.plane, editing: false } : null; }
    const k = sketchOf(d);
    if (!k) return null;
    const [f0, f1] = faceOffsets(d, k), back = st.face === 'back';
    if (st.face === 'edge') {   // a joining edge: its own dots, which move freely in 3D
      const i = Math.min(st.edge || 0, k.points.length - 1);
      return { k, d, face: 'edge', edge: i, pts: edgeDotsOf(d, i), plane: { axis: k.plane.axis, offset: f0 }, editing: true, sg: depthSign(d) };
    }
    return { k, d, face: st.face, pts: back ? backOf(d, k) : k.points, plane: { axis: k.plane.axis, offset: back ? f1 : f0 }, editing: true, sg: depthSign(d) };
  }
  // The live joining edge's dot list, created on first use (so it's part of the scene and saves).
  function ownEdge(tg) {
    if (tg.face !== 'edge') return tg;
    const d = tg.d, n = tg.k.points.length;
    if (!d.edges || d.edges.length !== n) d.edges = Array.from({ length: n }, (_, i) => (d.edges && d.edges[i]) || []);
    if (!d.edges[tg.edge]) d.edges[tg.edge] = [];
    tg.pts = d.edges[tg.edge];
    return tg;
  }
  // A dot on a joining edge is placed relative to the straight line between its ends; store a new position that way.
  // Its stored depth t is kept as its real depth along the edge (between its neighbours'), and d as the rest of the offset.
  function setEdgeDot(tg, q, P) {
    const fd = faceDots(tg.d, tg.k), F = fd.F[tg.edge], B = fd.B[tg.edge], FB = sub3(B, F), L2 = dot3(FB, FB);
    const list = tg.pts, i = list.indexOf(q), lo = i > 0 ? list[i - 1].t + 1e-4 : 0.001, hi = i >= 0 && i < list.length - 1 ? list[i + 1].t - 1e-4 : 0.999;
    if (L2 > 1e-12) q.t = +Math.min(Math.max(dot3(sub3(P, F), FB) / L2, lo, 0.001), hi, 0.999).toFixed(5);
    const base = lerp3(F, B, q.t);
    q.d = [+(P[0] - base[0]).toFixed(4), +(P[1] - base[1]).toFixed(4), +(P[2] - base[2]).toFixed(4)];
  }
  // Where a dot really is: on its face, plus its own depth (a part's dots only; sketch dots are flat).
  const depthOf = (tg, q) => (tg.editing ? tg.sg * (q.w || 0) : 0);
  const dotPos = (tg, q) => {
    if (tg.face === 'edge') { const fd = faceDots(tg.d, tg.k); return edgeDotPos(fd.F[tg.edge], fd.B[tg.edge], q); }
    return toModel(tg.plane.axis, tg.plane.offset + depthOf(tg, q), q.u, q.v);
  };
  // Keep a dot's depth from carrying it through to the other face. (While the back still copies the front, they move together.)
  function clampDepth(tg, i, w) {
    if (!tg.editing || !tg.d.back) return w;
    const t = tg.d.thickness, F = tg.k.points, B = tg.d.back;
    return tg.face === 'back' ? Math.max(w, ((F[i] && F[i].w) || 0) - t + MIN_WALL) : Math.min(w, t + ((B[i] && B[i].w) || 0) - MIN_WALL);
  }
  // Until the back outline is changed it is the front's dots; the first change gives it its own copy.
  function ownBack(tg) {
    if (tg.face !== 'back' || !tg.editing) return tg;
    if (!tg.d.back || tg.d.back.length !== tg.k.points.length) tg.d.back = tg.k.points.map(q => ({ ...q }));
    tg.pts = tg.d.back;
    return tg;
  }
  const plane = () => { const t = target(); return t ? t.plane : { axis: st.axis, offset: st.offset }; };
  const snapV = v => (st.snap ? Math.round(v / st.snap) * st.snap : v);

  // ---------- scene objects ----------
  const group = new THREE.Group();
  group.renderOrder = 10;
  world.add(group);
  const planeGroup = new THREE.Group(), cutGroup = new THREE.Group(), lineGroup = new THREE.Group(), ballGroup = new THREE.Group(), snapGroup = new THREE.Group();
  group.add(planeGroup, cutGroup, lineGroup, ballGroup, snapGroup);
  renderer.localClippingEnabled = true;
  const clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

  function dotTexture(hollow, selected) {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d');
    if (selected) { g.beginPath(); g.arc(32, 32, 30, 0, Math.PI * 2); g.fillStyle = '#ffffff'; g.fill(); }
    g.beginPath(); g.arc(32, 32, selected ? 24 : 26, 0, Math.PI * 2); g.fillStyle = '#0d1319'; g.fill();
    g.beginPath(); g.arc(32, 32, selected ? 19 : 21, 0, Math.PI * 2); g.fillStyle = '#ffd23f'; g.fill();
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
    // Axis centres: a cross on any top-down plane, to snap to. An axis isn't a part, so it has no keep-out area.
    if (axis === 'z') for (const a of ARBOR_DEFS) out.push({ kind: 'cross', u: D.pos[a.id][0], v: D.pos[a.id][1], style: 'shaft', name: `${a.name} axis` });
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
      if (s.kind === 'cross') { pts.push(P(s.u - 0.5, s.v), P(s.u + 0.5, s.v), P(s.u, s.v - 0.5), P(s.u, s.v + 0.5)); continue; }
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

  const sample = k => outlinePoints(k);   // the polyspline (main script), shared with drawn parts
  let lineKey = '';
  const balls = [];
  function addBall(pos, smooth, i, big = false) {
    const sp = new THREE.Sprite(dotMat[`${!!smooth}|${i === st.sel}`]);
    sp.position.set(...pos);
    sp.scale.set(big ? 0.03 : 0.024, big ? 0.03 : 0.024, 1);
    sp.renderOrder = 15;
    sp.userData.idx = i;
    ballGroup.add(sp);
    balls.push(sp);
  }
  // A selected drawn part: both outlines and the edges joining their dots. The live outline is bright and carries the dots.
  function drawCage(tg) {
    const { k, d } = tg, ax = k.plane.axis, [f0, f1] = faceOffsets(d, k), front = k.points, back = backOf(d, k), sg = tg.sg;
    const outline = (pts, c, live) => {
      const P = sample({ points: pts, closed: k.closed }).map(p => toModel(ax, c + sg * wAt(pts, p[2], p[3]), p[0], p[1])), segs = [];
      for (let i = 0; i < P.length - 1; i++) segs.push(P[i], P[i + 1]);
      fat(lineGroup, segs, live ? COL.sketch : COL.sketchDim, live ? 3 : 2, live ? 1 : 0.85, false, 12);
    };
    outline(front, f0, tg.face === 'front');
    outline(back, f1, tg.face === 'back');
    const fd = faceDots(d, k), faint = [], live = [];
    for (let i = 0; i < front.length; i++) {
      const C = chainSamples(edgeChain(d, k, i, fd)), on = tg.face === 'edge' && tg.edge === i;
      for (let j = 0; j < C.length - 1; j++) (on ? live : faint).push(C[j].slice(0, 3), C[j + 1].slice(0, 3));
    }
    fat(lineGroup, faint, COL.sketchDim, 1.5, 0.6, false, 12);
    fat(lineGroup, live, COL.sketch, 3, 1, false, 12);
    tg.pts.forEach((q, i) => addBall(dotPos(tg, q), q.smooth, i));
  }
  function buildLines() {
    const tgE = editPart() ? target() : null;
    const key = JSON.stringify([S.sketches, S.drawn, curId(), st.sel, st.face, st.edge, sketching(), !!editPart(), st.cursor && st.drag == null ? st.cursor : null,
      (st.snapUsed || []).map(c => [c.kind, c.a, c.id, c.e, c.e2, c.at, c.th])]);
    if (key === lineKey) return;
    lineKey = key;
    clear(lineGroup);
    clear(ballGroup);
    balls.length = 0;
    for (const k of S.sketches) {
      if (tgE && tgE.k.id === k.id) { drawCage(tgE); continue; }
      if ((ownerOf(k) || cutUser(k)) && !sketching()) continue;   // a part's outline (or a pocket's) shows only while you edit it
      const mine = sketching() && k.id === curId();
      const pts = sample(k);
      if (pts.length > 1) {
        const segs = [];
        for (let i = 0; i < pts.length - 1; i++) segs.push(toModel(k.plane.axis, k.plane.offset, pts[i][0], pts[i][1]), toModel(k.plane.axis, k.plane.offset, pts[i + 1][0], pts[i + 1][1]));
        fat(lineGroup, segs, mine ? COL.sketch : COL.sketchDim, mine ? 3 : 2, mine ? 1 : 0.8, false, 12);
      }
      if (!mine) continue;
      k.points.forEach((q, i) => addBall(toModel(k.plane.axis, k.plane.offset, q.u, q.v), q.smooth, i, i === 0 && !k.closed && k.points.length >= 3));
      // Rubber band from the last dot to the cursor while you're still drawing.
      if (!k.closed && k.points.length && st.cursor && !st.drag) {
        const last = k.points[k.points.length - 1];
        fat(lineGroup, [toModel(k.plane.axis, k.plane.offset, last.u, last.v), toModel(k.plane.axis, k.plane.offset, st.cursor[0], st.cursor[1])], COL.rubber, 1.5, 0.75, true, 12);
      }
    }
    drawSnaps();
  }

  // ---------- picking ----------
  const ray = new THREE.Raycaster(), ndc2 = new THREE.Vector2();
  function aim(cx, cy) {
    const r = canvas.getBoundingClientRect();
    ndc2.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc2, camera);
  }
  function planeUV(cx, cy, off = null) {
    const p = plane(), c = off == null ? p.offset : off;
    aim(cx, cy);
    const n = new THREE.Vector3(p.axis === 'x' ? 1 : 0, p.axis === 'y' ? 1 : 0, p.axis === 'z' ? 1 : 0);
    const hit = ray.ray.intersectPlane(new THREE.Plane(n, -c * scale), new THREE.Vector3());
    if (!hit) return null;
    const m = world.worldToLocal(hit);
    return toUV(p.axis, [m.x, m.y, m.z]);
  }
  // Where a drag puts a dot. Seen face-on (or at a fair angle) the dot follows the cursor on its own face.
  // Seen nearly edge-on, the cursor's line of sight runs almost along the face and a pixel would become metres,
  // so the dot moves in a plane facing you instead and is dropped onto its face: it can only slide along what you see.
  function dragUV(cx, cy, d) {
    if (d.faceOK) return planeUV(cx, cy, d.planeOff);
    const p = plane();
    aim(cx, cy);
    const anchorW = world.localToWorld(new THREE.Vector3(...d.anchor));
    const facing = new THREE.Plane().setFromNormalAndCoplanarPoint(camera.getWorldDirection(new THREE.Vector3()), anchorW);
    const hit = ray.ray.intersectPlane(facing, new THREE.Vector3());
    if (!hit) return null;
    const m = world.worldToLocal(hit);
    return toUV(p.axis, [m.x, m.y, m.z]);
  }
  function facesYou() {
    const p = plane(), n = new THREE.Vector3(p.axis === 'x' ? 1 : 0, p.axis === 'y' ? 1 : 0, p.axis === 'z' ? 1 : 0);
    return Math.abs(camera.getWorldDirection(new THREE.Vector3()).dot(n)) >= 0.3;   // within ~72° of face-on
  }
  // The dot under the cursor: a hit on its drawn disc, or failing that the nearest dot within a small reach,
  // so a click that lands just beside a dot (a corner, say) takes that dot instead of adding a new one on the line.
  const NEAR_DOT_PX = 14;
  const toScreen = (p, r = canvas.getBoundingClientRect()) => { const v = world.localToWorld(new THREE.Vector3(...p)).project(camera); return v.z > 1 ? null : [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; };
  function ballAt(cx, cy) {
    if (!balls.length) return null;
    // Dots rebuilt since the last frame have no screen position yet; without this they all "cover" the screen.
    group.updateMatrixWorld(true);
    aim(cx, cy);
    const h = ray.intersectObjects(balls, false)[0];
    if (h) return h.object.userData.idx;
    const r = canvas.getBoundingClientRect(), w = new THREE.Vector3();
    let best = null;
    for (const b of balls) {
      const s2 = toScreen(world.worldToLocal(b.getWorldPosition(w)).toArray(), r);
      const dpx = s2 ? Math.hypot(s2[0] - cx, s2[1] - cy) : Infinity;
      if (dpx <= NEAR_DOT_PX && (!best || dpx < best.d)) best = { d: dpx, idx: b.userData.idx };
    }
    return best ? best.idx : null;
  }
  // Clicking a line never adds a dot right beside an existing one: not beside any dot of that outline, and on a joining edge
  // not beside its end dots either (they're the corners). Returns where the click landed instead, so it can be selected.
  function dotBeside(tg, cx, cy) {
    const r = canvas.getBoundingClientRect(), near = (p, what) => { const s2 = toScreen(p, r); return s2 && Math.hypot(s2[0] - cx, s2[1] - cy) <= NEAR_DOT_PX ? what : null; };
    if (tg.face === 'edge') {
      const C = edgeChain(tg.d, tg.k, tg.edge);
      for (let j = 0; j < C.length; j++) { const hit = near(C[j].p, j === 0 ? { face: 'front', idx: tg.edge } : j === C.length - 1 ? { face: 'back', idx: tg.edge } : { idx: j - 1 }); if (hit) return hit; }
      return null;
    }
    for (let i = 0; i < tg.pts.length; i++) { const hit = near(dotPos(tg, tg.pts[i]), { idx: i }); if (hit) return hit; }
    return null;
  }
  // Nearest point on an outline, in screen pixels: which segment, and how far along it (0 to 1).
  function lineNear(pts, closed, pl, cx, cy, sg = 0) {
    if (pts.length < 2) return null;
    const r = canvas.getBoundingClientRect(), v = new THREE.Vector3();
    const scr = sample({ points: pts, closed }).map(q => { v.set(...toModel(pl.axis, pl.offset + sg * wAt(pts, q[2], q[3]), q[0], q[1])); world.localToWorld(v); v.project(camera); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height, q[2], q[3]]; });
    let best = null;
    for (let i = 0; i < scr.length - 1; i++) {
      const [x1, y1] = scr[i], [x2, y2] = scr[i + 1], dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, ((cx - x1) * dx + (cy - y1) * dy) / L2)) : 0;
      const d = Math.hypot(cx - (x1 + t * dx), cy - (y1 + t * dy));
      const seg = scr[i + 1][2], fa = scr[i][2] === seg ? scr[i][3] : 0;
      if (!best || d < best.d) best = { d, seg, frac: fa + (scr[i + 1][3] - fa) * t };
    }
    return best && best.d < 8 ? best : null;
  }
  // Nearest point on a sampled 3D line ([x, y, z, link, fraction] samples), in screen pixels.
  function samplesNear(sm, cx, cy) {
    const r = canvas.getBoundingClientRect(), v = new THREE.Vector3();
    const scr = sm.map(q => { world.localToWorld(v.set(q[0], q[1], q[2])); v.project(camera); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height, q[3], q[4]]; });
    let best = null;
    for (let i = 0; i < scr.length - 1; i++) {
      const [x1, y1] = scr[i], [x2, y2] = scr[i + 1], dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, ((cx - x1) * dx + (cy - y1) * dy) / L2)) : 0;
      const d = Math.hypot(cx - (x1 + t * dx), cy - (y1 + t * dy));
      const seg = scr[i + 1][2], fa = scr[i][2] === seg ? scr[i][3] : 0;
      if (!best || d < best.d) best = { d, seg, frac: fa + (scr[i + 1][3] - fa) * t };
    }
    return best && best.d < 8 ? best : null;
  }
  const edgeSamplesOf = (tg, i) => chainSamples(edgeChain(tg.d, tg.k, i));
  const lineAt = (cx, cy) => {
    const tg = target();
    if (!tg) return null;
    if (tg.face === 'edge') return samplesNear(edgeSamplesOf(tg, tg.edge), cx, cy);
    return lineNear(tg.pts, tg.k.closed, tg.plane, cx, cy, tg.editing ? tg.sg : 0);
  };
  // Another outline or joining edge of the selected part (a faint one): clicking it makes it the live one.
  function otherLineAt(cx, cy) {
    const tg = target();
    if (!tg || !tg.editing) return null;
    const [f0, f1] = faceOffsets(tg.d, tg.k), ax = tg.k.plane.axis, hits = [];
    if (tg.face !== 'front') { const h = lineNear(tg.k.points, tg.k.closed, { axis: ax, offset: f0 }, cx, cy, tg.sg); if (h) hits.push({ ...h, face: 'front' }); }
    if (tg.face !== 'back') { const h = lineNear(backOf(tg.d, tg.k), tg.k.closed, { axis: ax, offset: f1 }, cx, cy, tg.sg); if (h) hits.push({ ...h, face: 'back' }); }
    for (let i = 0; i < tg.k.points.length; i++) {
      if (tg.face === 'edge' && tg.edge === i) continue;
      const h = samplesNear(edgeSamplesOf(tg, i), cx, cy);
      if (h) hits.push({ ...h, face: 'edge', edge: i });
    }
    return hits.sort((a, b) => a.d - b.d)[0] || null;
  }
  // A point on a plane facing you, through a given point: how a joining-edge dot follows the cursor (it has no face to slide on).
  function facingPoint(cx, cy, anchor) {
    aim(cx, cy);
    const facing = new THREE.Plane().setFromNormalAndCoplanarPoint(camera.getWorldDirection(new THREE.Vector3()), world.localToWorld(new THREE.Vector3(...anchor)));
    const hit = ray.ray.intersectPlane(facing, new THREE.Vector3());
    return hit ? world.worldToLocal(hit).toArray() : null;
  }
  // The wall a joining-edge dot slides along: of the two walls meeting at its edge, the one turned most toward you.
  // A wall's direction at the edge: along the edge (front dot to back dot) and across to the neighbouring front dot.
  // Seen nearly edge-on (both walls), there's no good wall to slide on, and it falls back to a plane facing you.
  function edgeWall(tg) {
    const fd = faceDots(tg.d, tg.k), n = tg.k.points.length, i = tg.edge, F = fd.F[i];
    const along = new THREE.Vector3(...sub3(fd.B[i], F)).normalize(), view = camera.getWorldDirection(new THREE.Vector3());
    let best = null;
    for (const j of [(i - 1 + n) % n, (i + 1) % n]) {
      const across = new THREE.Vector3(...sub3(fd.F[j], F)), nv = along.clone().cross(across);
      if (nv.lengthSq() < 1e-12) continue;
      nv.normalize();
      const facing = Math.abs(nv.dot(view));
      if (!best || facing > best.facing) best = { facing, n: nv.toArray(), basis: [along.toArray(), nv.clone().cross(along).normalize().toArray()] };
    }
    return best && best.facing >= 0.3 ? best : null;
  }
  function wallPoint(cx, cy, anchor, nrm) {   // where the cursor meets the wall's plane through the dot
    aim(cx, cy);
    const pl = new THREE.Plane().setFromNormalAndCoplanarPoint(new THREE.Vector3(...nrm), world.localToWorld(new THREE.Vector3(...anchor)));
    const hit = ray.ray.intersectPlane(pl, new THREE.Vector3());
    return hit ? world.worldToLocal(hit).toArray() : null;
  }
  function facingBasis() {
    const m = camera.matrixWorld.elements;
    return [[m[0], m[1], m[2]], [m[4], m[5], m[6]]];   // the camera's right and up directions
  }
  // Snap to the grid, and onto an axis centre when close to one (top plane only).
  function snapUV(uv) {
    let [u, v] = [snapV(uv[0]), snapV(uv[1])];
    if (plane().axis === 'z') for (const s of cutsNow) if (s.style === 'shaft' && Math.hypot(uv[0] - s.u, uv[1] - s.v) < 0.35) { u = s.u; v = s.v; }
    return [+u.toFixed(4), +v.toFixed(4)];
  }

  // ---------- a part's two outlines keep the same dots, one for one ----------
  // Adding a dot to one adds the matching dot to the other, at the same fraction along the same segment.
  function insertDot(tg, seg, frac, uv) {
    const other = tg.d && tg.d.back ? (tg.pts === tg.d.back ? tg.k.points : tg.d.back) : null;
    const withW = (q, w) => (Math.abs(w) > 1e-9 ? { ...q, w: +w.toFixed(4) } : q);
    if (other) {
      const n = other.length, [u, v] = outlinePointAt(other, true, seg, frac), wo = wAt(other, seg, frac);
      other.splice(seg + 1, 0, withW({ u: +u.toFixed(4), v: +v.toFixed(4), smooth: !!(other[seg].smooth && other[(seg + 1) % n].smooth) }, wo));
    }
    const w = tg.editing ? wAt(tg.pts, seg, frac) : 0;
    tg.pts.splice(seg + 1, 0, withW({ u: uv[0], v: uv[1], smooth: false }, w));
    if (tg.d && tg.d.edges) tg.d.edges.splice(seg + 1, 0, []);   // the new dot's joining edge starts straight
  }
  function removeDotAt(tg, i) {
    tg.k.points.splice(i, 1);
    if (tg.d && tg.d.back) tg.d.back.splice(i, 1);
    if (tg.d && tg.d.edges) tg.d.edges.splice(i, 1);
  }
  // A dot on a joining edge, added where you clicked: between the chain points either side of the click.
  function insertEdgeDot(tg, seg, frac) {
    ownEdge(tg);
    const C = edgeChain(tg.d, tg.k, tg.edge), P = chainPointAt(C, seg, frac);
    // Its place along the edge: how far the point is along the straight line from front dot to back dot (so a dot added to a
    // straight edge has no offset at all), kept between its neighbours on the edge.
    const F = C[0].p, B = C[C.length - 1].p, FB = [B[0] - F[0], B[1] - F[1], B[2] - F[2]], L2 = FB[0] ** 2 + FB[1] ** 2 + FB[2] ** 2;
    const along = L2 > 1e-12 ? ((P[0] - F[0]) * FB[0] + (P[1] - F[1]) * FB[1] + (P[2] - F[2]) * FB[2]) / L2 : 0.5;
    const lo = C[seg].t + 1e-4, hi = C[seg + 1].t - 1e-4;
    const q = { t: +Math.min(Math.max(along, lo, 0.001), hi, 0.999).toFixed(5), d: [0, 0, 0], smooth: false };
    tg.pts.splice(seg, 0, q);   // in place first, so its depth is kept between its neighbours'
    setEdgeDot(tg, q, P);
    return seg;
  }

  // ---------- edits: each one is recorded, so it autosaves and undoes ----------
  // Quick edits to one outline merge into one log line and one undo step; the line lists every action in it.
  let burst = { key: '', actions: [] };
  function save(x, what) {
    const tg = x.pts ? x : { k: x, d: ownerOf(x), face: 'front', pts: x.points, editing: false };
    const back = tg.face === 'back' && tg.editing, edge = tg.face === 'edge' && tg.editing;
    const key = edge ? `ek:${tg.d.id}:${tg.edge}` : back ? `bk:${tg.d.id}` : `sk:${tg.k.id}`, last = history[hIndex];
    const merging = hIndex > 0 && hIndex === history.length - 1 && last.key === key && performance.now() - last.time < MERGE_MS && burst.key === key;
    burst = merging ? { key, actions: [...burst.actions, what] } : { key, actions: [what] };
    const acts = burst.actions.slice(), k = tg.k;
    const label = tg.d ? `${nameOf(tg.d.id)} ${edge ? `joining edge ${tg.edge + 1}` : back ? 'back outline' : 'outline'}` : k.name;
    const count = edge ? `${tg.pts.length} dot${tg.pts.length === 1 ? '' : 's'} on it` : `${k.points.length} dot${k.points.length === 1 ? '' : 's'}${k.closed ? ', closed' : ''}`;
    commit({ key, from: 0, to: 0, adapt: false, make: () => `${label}: ${acts.join(', ')} (${count})` });
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
  // A drawn part's panel shows the selected dot's numbers, so it redraws when the selected dot changes.
  function selChanged() { if (editPart()) renderSelected(); }
  function updatePartDotFields() {
    const tg = target(), q = tg && st.sel != null ? tg.pts[st.sel] : null;
    if (!q) return;
    const P3 = tg.face === 'edge' ? modelToPlane(tg.plane.axis, dotPos(tg, q)) : null;
    const vals = P3 ? { u: P3[0], v: P3[1], n: P3[2] } : { u: q.u, v: q.v, n: tg.plane.offset + depthOf(tg, q) };
    document.querySelectorAll('#selected [data-dotf]').forEach(el => { if (document.activeElement !== el) el.value = +(vals[el.dataset.dotf] * scale).toFixed(3); });
  }
  function setFace(face, edge = null) {
    if (face === st.face && (face !== 'edge' || edge === st.edge)) return;
    st.face = face;
    if (face === 'edge') st.edge = edge;
    st.sel = null;
    buildLines();
    renderSelected();
  }

  canvas.addEventListener('pointerdown', e => {
    if (!active() || e.button !== 0) return;
    // A press on a dot drags the dot (it slides along its face). Only a press on the arrows away from the dot belongs to them;
    // their small plane square sits right on the dot and would otherwise take it in and out of its face.
    const bi = ballAt(e.clientX, e.clientY);
    if (bi == null && dotGizmo.object) {
      const r = canvas.getBoundingClientRect();
      dotGizmo.pointerHover({ x: (e.clientX - r.left) / r.width * 2 - 1, y: -((e.clientY - r.top) / r.height) * 2 + 1, button: -1 });
      dotGizmo.updateMatrixWorld(true);
      if (dotGizmo.axis) return;
    }
    const tg = target();
    const li = bi == null ? lineAt(e.clientX, e.clientY) : null;
    if (tg && bi == null && li != null && tg.editing) {
      // On a part the outline isn't a handle: a click on it adds a dot there, a drag from it orbits the view as usual.
      st.lineTap = { seg: li.seg, frac: li.frac, x: e.clientX, y: e.clientY };
      keepSelection = true;
      return;
    }
    if (tg && bi != null && tg.face === 'edge') {   // a joining-edge dot: it slides along the wall you're looking at
      e.stopImmediatePropagation();
      controls.enabled = false;
      st.drag = { kind: 'dot', edge: true, idx: bi, x: e.clientX, y: e.clientY, moved: false, anchor: dotPos(tg, tg.pts[bi]), wall: edgeWall(tg) };
      if (st.sel !== bi) { st.sel = bi; selChanged(); }
      buildLines();
      return;
    }
    if (tg && (bi != null || li != null)) {
      e.stopImmediatePropagation();
      controls.enabled = false;
      const ax = tg.plane.axis;
      const at = bi != null ? [tg.pts[bi].u, tg.pts[bi].v] : outlinePointAt(tg.pts, tg.k.closed, li.seg, li.frac);
      const off = tg.plane.offset + (bi != null ? depthOf(tg, tg.pts[bi]) : 0);
      st.drag = { kind: bi != null ? 'dot' : 'line', idx: bi, seg: li && li.seg, frac: li && li.frac, x: e.clientX, y: e.clientY, moved: false,
                  faceOK: facesYou(), anchor: toModel(ax, off, at[0], at[1]), planeOff: off, orig: null };
      st.drag.start = dragUV(e.clientX, e.clientY, st.drag);
      if (bi != null && st.sel !== bi) { st.sel = bi; selChanged(); }
      buildLines();
      renderPanel();
      return;
    }
    if (tg && tg.editing) {
      const other = otherLineAt(e.clientX, e.clientY);
      if (other) { e.stopImmediatePropagation(); setFace(other.face, other.edge); return; }
      if (st.sel != null) { st.sel = null; buildLines(); selChanged(); }   // a click on the part away from its dots lets go of the dot
      return;   // editing a part: a click off its outlines selects as usual
    }
    if (sketching()) st.down = { x: e.clientX, y: e.clientY };
  }, { capture: true });

  canvas.addEventListener('pointermove', e => {
    if (!active()) return;
    const d = st.drag;
    if (!sketching() && !d) return;
    if (d && d.edge) {
      if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 3) return;
      const tg = ownEdge(target()), q = tg && tg.pts[d.idx];
      const raw = d.wall ? wallPoint(e.clientX, e.clientY, d.anchor, d.wall.n) : facingPoint(e.clientX, e.clientY, d.anchor);
      if (!q || !raw) return;
      d.moved = true;
      const sn = snapDot(tg, d.idx, raw, d.wall ? d.wall.basis : facingBasis(), e.altKey);
      st.snapUsed = sn ? sn.used : null;
      setEdgeDot(tg, q, sn ? sn.P : raw);
      updatePartDotFields();
      requestSolve();
      buildLines();
      return;
    }
    const uv = d ? dragUV(e.clientX, e.clientY, d) : planeUV(e.clientX, e.clientY);
    st.cursor = uv && sketching() ? snapUV(uv) : null;
    showReadout();
    if (d && uv) {
      if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 3) return;
      const tg = ownBack(target());
      if (!d.moved) d.orig = tg.pts.map(q => ({ ...q }));
      d.moved = true;
      if (d.kind === 'dot') {
        const ax = tg.plane.axis, raw = toModel(ax, d.planeOff, uv[0], uv[1]);   // the dot slides along its face, at its own depth
        const sn = snapDot(tg, d.idx, raw, [toModel(ax, 0, 1, 0), toModel(ax, 0, 0, 1)], e.altKey);
        st.snapUsed = sn ? sn.used : null;
        if (sn) { const [u, v] = modelToPlane(ax, sn.P); tg.pts[d.idx].u = +u.toFixed(4); tg.pts[d.idx].v = +v.toFixed(4); }
        else { const [u, v] = snapUV(uv); tg.pts[d.idx].u = u; tg.pts[d.idx].v = v; }
      } else if (d.start) {
        const du = snapV(uv[0] - d.start[0]), dv = snapV(uv[1] - d.start[1]);
        tg.pts.forEach((q, i) => { q.u = +(d.orig[i].u + du).toFixed(4); q.v = +(d.orig[i].v + dv).toFixed(4); });
      }
      updateDotFields();
      updatePartDotFields();
      if (tg.d) requestSolve();   // its solid rebuilds as you drag
    }
    buildLines();
  });

  window.addEventListener('pointerup', e => {
    if (!active()) return;
    if (st.lineTap) {
      const lt = st.lineTap;
      st.lineTap = null;
      if (Math.hypot(e.clientX - lt.x, e.clientY - lt.y) >= 4) return;   // it was an orbit
      const tg = ownBack(target());
      if (!tg) return;
      const beside = dotBeside(tg, e.clientX, e.clientY);
      if (beside) {   // right next to a dot: select it, don't add one on top of it
        if (beside.face) { setFace(beside.face); st.sel = beside.idx; buildLines(); selChanged(); }
        else if (st.sel !== beside.idx) { st.sel = beside.idx; buildLines(); selChanged(); }
        return;
      }
      if (tg.face === 'edge') {
        st.sel = insertEdgeDot(tg, lt.seg, lt.frac);
        save(tg, `added dot ${st.sel + 1}`);
        buildLines();
        selChanged();
        return;
      }
      const [u, v] = outlinePointAt(tg.pts, tg.k.closed, lt.seg, lt.frac);   // right on the outline where you clicked
      insertDot(tg, lt.seg, lt.frac, [+u.toFixed(4), +v.toFixed(4)]);
      st.sel = lt.seg + 1;
      save(tg, `inserted dot ${lt.seg + 2}`);
      buildLines();
      selChanged();
      return;
    }
    const d = st.drag;
    if (d) {
      st.drag = null;
      st.snapUsed = null;
      controls.enabled = true;
      const tg = target(), k = tg.k;
      if (d.moved) save(tg, d.kind === 'dot' ? `moved dot ${d.idx + 1}` : tg.editing ? 'moved the whole outline' : 'moved the whole drawing');
      else if (d.edge) { /* a click on a joining-edge dot just selects it */ }
      else if (d.kind === 'dot' && d.idx === 0 && !k.closed && k.points.length >= 3) {
        // Wait a moment: if this turns out to be a double-click (sharp/smooth), don't close.
        clearTimeout(st.closeTimer);
        st.closeTimer = setTimeout(() => { const kk = cur(); if (kk && kk.id === k.id && !kk.closed && kk.points.length >= 3) { kk.closed = true; save(kk, 'closed the shape'); renderPanel(); } }, 280);
      }
      else if (d.kind === 'line' && dotBeside(tg, e.clientX, e.clientY)) { /* beside a dot: no new dot on top of it */ }
      else if (d.kind === 'line') {
        ownBack(tg);
        const [u, v] = outlinePointAt(tg.pts, k.closed, d.seg, d.frac);   // right on the outline where you clicked
        insertDot(tg, d.seg, d.frac, [+u.toFixed(4), +v.toFixed(4)]);
        st.sel = d.seg + 1;
        save(tg, `inserted dot ${d.seg + 2}`);
        selChanged();
      }
      buildLines();
      renderPanel();
      return;
    }
    if (!sketching()) return;
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
    const ow = ownerOf(k2);
    if (ow && ow.back) ow.back.push({ u, v, smooth: false });
    st.sel = k2.points.length - 1;
    save(k2, k2.points.length === 1 ? 'started' : `added dot ${k2.points.length}`);
    renderPanel();
  });

  canvas.addEventListener('dblclick', e => {
    if (!active()) return;
    const bi = ballAt(e.clientX, e.clientY), tg = target();
    if (bi == null || !tg) return;
    e.stopImmediatePropagation();   // not the view's double-click zoom
    clearTimeout(st.closeTimer);
    ownBack(tg);
    ownEdge(tg);
    tg.pts[bi].smooth = !tg.pts[bi].smooth;
    st.sel = bi;
    save(tg, `made dot ${bi + 1} ${tg.pts[bi].smooth ? 'smooth' : 'sharp'}`);
    renderPanel();
    selChanged();
  }, { capture: true });

  window.addEventListener('keydown', e => {
    if (!active()) return;
    const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName);
    if (typing) return;
    const k = cur();
    if ((e.key === 'Delete' || e.key === 'Backspace') && k && st.sel != null) { e.preventDefault(); deleteDot(); }
    if (e.key === 'Enter' && sketching() && k && !k.closed && k.points.length >= 3) { k.closed = true; save(k, 'closed the shape'); renderPanel(); }
  });

  function deleteDot() {
    const tg = target();
    if (!tg || st.sel == null || !tg.pts[st.sel]) return;
    if (tg.face === 'edge') {   // a joining edge can lose all its dots (it goes back to straight)
      const n = st.sel + 1;
      ownEdge(tg).pts.splice(st.sel, 1);
      st.sel = tg.pts.length ? Math.min(st.sel, tg.pts.length - 1) : null;
      save(tg, `deleted dot ${n}`);
      selChanged();
      return;
    }
    if (tg.d && tg.k.points.length <= 3) { flash('A part’s outline needs at least 3 dots.'); return; }
    const n = st.sel + 1, k = tg.k;
    removeDotAt(tg, st.sel);
    if (k.points.length < 3) k.closed = false;
    st.sel = k.points.length ? Math.min(st.sel, k.points.length - 1) : null;
    save(tg, `deleted dot ${n}`);
    renderPanel();
    selChanged();
  }

  // ---------- snapping, measured in true 3D (never on screen, so it holds from any viewing angle) ----------
  // The cage is what you're shaping: its dots (front and back on a part) and the edges between them.
  // Snaps: a corner at 90° or 45° (at the dot, or at a neighbour it pulls on), an edge along X, Y or Z,
  // an edge the length of another edge, and the dot at the same X, Y or Z as another dot.
  const SNAP_DEG = 2.5, SNAP_PX = 8;
  let altHeld = false;
  window.addEventListener('keydown', e => { if (e.key === 'Alt') altHeld = true; });
  window.addEventListener('keyup', e => { if (e.key === 'Alt') altHeld = false; });
  window.addEventListener('blur', () => { altHeld = false; });
  const AX = ['X', 'Y', 'Z'];
  const sub3 = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const len3 = a => Math.hypot(a[0], a[1], a[2]);
  const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  function cage(tg) {
    const nodes = new Map(), edges = [], k = tg.k, ax = k.plane.axis, n = k.points.length;
    const ring = (pfx, m) => { for (let i = 0; i < (k.closed ? m : m - 1); i++) edges.push([pfx + i, pfx + ((i + 1) % m)]); };
    if (tg.editing) {
      const d = tg.d, [f0, f1] = faceOffsets(d, k), sg = tg.sg;
      k.points.forEach((q, i) => nodes.set('F' + i, { p: toModel(ax, f0 + sg * (q.w || 0), q.u, q.v), name: `dot ${i + 1}` }));
      ring('F', n);
      // While the back copies the front it moves with any front dot you drag, so it can't be a reference then
      // (unless you're dragging a joining-edge dot, which moves alone).
      if (d.back || tg.face === 'edge') {
        backOf(d, k).forEach((q, i) => nodes.set('B' + i, { p: toModel(ax, f1 + sg * (q.w || 0), q.u, q.v), name: `back dot ${i + 1}` }));
        ring('B', n);
        const fd = faceDots(d, k);
        for (let i = 0; i < n; i++) {   // joining edge i: front dot, its own dots, back dot
          const chain = ['F' + i];
          edgeDotsOf(d, i).forEach((q, j) => { const id = `E${i}_${j}`; nodes.set(id, { p: edgeDotPos(fd.F[i], fd.B[i], q), name: `dot ${j + 1} on joining edge ${i + 1}`, edge: i }); chain.push(id); });
          chain.push('B' + i);
          for (let j = 0; j < chain.length - 1; j++) edges.push([chain[j], chain[j + 1]]);
        }
      }
    } else {
      k.points.forEach((q, i) => nodes.set('F' + i, { p: toModel(ax, k.plane.offset, q.u, q.v), name: `dot ${i + 1}` }));
      ring('F', n);
    }
    return { nodes, edges, me: tg.editing && tg.face === 'edge' ? `E${tg.edge}_${st.sel}` : (tg.editing && tg.face === 'back' ? 'B' : 'F') + st.sel };
  }
  const edgeKey = e => [...e].sort().join('|');
  function mmPerPx(P) {
    const w = world.localToWorld(new THREE.Vector3(...P));
    return 2 * camera.position.distanceTo(w) * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, canvas.clientHeight) / scale;
  }
  // Move P0 within the directions you're allowed to move it (basis) until every constraint holds. null if it can't.
  function solveOn(P0, basis, cons) {
    const m = cons.length, n = basis.length;
    if (m > n) return null;
    let s = basis.map(() => 0);
    const at = sv => { const p = P0.slice(); basis.forEach((b, j) => { for (let c = 0; c < 3; c++) p[c] += b[c] * sv[j]; }); return p; };
    for (let it = 0; it < 16; it++) {
      const P = at(s), r = cons.map(c => c.res(P));
      if (r.every(x => Math.abs(x) < 1e-7)) return P;
      const h = 1e-5, J = cons.map(() => new Array(n).fill(0));
      for (let j = 0; j < n; j++) { const s2 = s.slice(); s2[j] += h; const P2 = at(s2); cons.forEach((c, i) => { J[i][j] = (c.res(P2) - r[i]) / h; }); }
      // smallest step that zeroes the residuals: ds = -Jᵀ (J Jᵀ)⁻¹ r
      const JJ = J.map(a => J.map(b => a.reduce((t, x, k2) => t + x * b[k2], 0)));
      let y;
      if (m === 1) { if (Math.abs(JJ[0][0]) < 1e-14) return null; y = [r[0] / JJ[0][0]]; }
      else { const det = JJ[0][0] * JJ[1][1] - JJ[0][1] * JJ[1][0]; if (Math.abs(det) < 1e-14) return null; y = [(JJ[1][1] * r[0] - JJ[0][1] * r[1]) / det, (-JJ[1][0] * r[0] + JJ[0][0] * r[1]) / det]; }
      s = s.map((sj, j) => sj - J.reduce((t, row, i) => t + row[j] * y[i], 0));
    }
    const P = at(s);
    return cons.every(c => Math.abs(c.res(P)) < 1e-5) ? P : null;
  }
  function snapDot(tg, idx, P0, basis, off) {
    if (off) return null;
    const cg = cage(tg), me = cg.me;
    if (!cg.nodes.has(me)) return null;
    const pos = (id, P) => (id === me ? P : cg.nodes.get(id).p);
    const tol = Math.max(0.1 / scale, SNAP_PX * mmPerPx(P0));   // real 0.1 mm, or 8 px at this zoom if that's bigger
    // Dots on the joining edge of a front or back dot you drag ride along with it, so they're no reference for it.
    const linked = new Set(/^[FB]\d+$/.test(me) ? [...cg.nodes.keys()].filter(id => id.startsWith(`E${me.slice(1)}_`)) : []);
    const usable = e => !e.some(id => linked.has(id));
    const mine = cg.edges.filter(e => e.includes(me) && usable(e));
    const cands = [];
    // Same X, Y or Z as another dot: only along a direction you can actually move in.
    for (const [id, nd] of cg.nodes) {
      if (id === me || linked.has(id)) continue;
      for (let a = 0; a < 3; a++) {
        if (basis.every(b => Math.abs(b[a]) < 1e-9)) continue;
        cands.push({ kind: 'align', a, id, res: P => P[a] - nd.p[a], near: Math.abs(P0[a] - nd.p[a]) <= tol });
      }
    }
    // An edge the length of another edge (on either face, or through the part).
    const L = (e, P) => len3(sub3(pos(e[0], P), pos(e[1], P)));
    for (const e of mine) for (const e2 of cg.edges) {
      if (edgeKey(e) === edgeKey(e2) || !usable(e2)) continue;
      cands.push({ kind: 'len', e, e2, res: P => L(e, P) - L(e2, P), near: Math.abs(L(e, P0) - L(e2, P0)) <= tol });
    }
    // Corners: at this dot between any two of its edges, and at a neighbour between the edge to this dot and its other edges.
    const cosAt = (v, a, b, P) => { const A = sub3(pos(a, P), pos(v, P)), B = sub3(pos(b, P), pos(v, P)), la = len3(A), lb = len3(B); return la < 1e-6 || lb < 1e-6 ? null : dot3(A, B) / (la * lb); };
    const corner = (v, a, b) => {
      const c0 = cosAt(v, a, b, P0);
      if (c0 == null) return;
      const deg = Math.acos(Math.max(-1, Math.min(1, c0))) * 180 / Math.PI;
      for (const th of [90, 45, 135]) {
        if (Math.abs(deg - th) > SNAP_DEG) continue;
        const ct = Math.cos(th * Math.PI / 180), arm = Math.min(len3(sub3(pos(a, P0), pos(v, P0))), len3(sub3(pos(b, P0), pos(v, P0))));
        cands.push({ kind: 'angle', at: v, a, b, th, arm, res: P => { const c = cosAt(v, a, b, P); return c == null ? 1 : (c - ct) * arm; }, near: true });
      }
    };
    const others = id => mine.map(e => (e[0] === id ? e[1] : e[0]));
    const nbrs = others(me);
    for (let i = 0; i < nbrs.length; i++) for (let j = i + 1; j < nbrs.length; j++) corner(me, nbrs[i], nbrs[j]);
    for (const q of nbrs) for (const e of cg.edges) {
      if (!e.includes(q) || e.includes(me) || !usable(e)) continue;
      corner(q, me, e[0] === q ? e[1] : e[0]);
    }
    // A flat wall: its four corners in one plane (only walls whose two joining edges are straight).
    if (tg.editing && cg.nodes.has('B0')) {
      const n = tg.k.points.length;
      for (let s2 = 0; s2 < n; s2++) {
        const s3 = (s2 + 1) % n, ids = ['F' + s2, 'F' + s3, 'B' + s3, 'B' + s2];
        if (!ids.includes(me) || edgeDotsOf(tg.d, s2).length || edgeDotsOf(tg.d, s3).length) continue;
        const others = ids.filter(x => x !== me);
        const res = P => {
          const [a, b, c] = others.map(id => pos(id, P)), nv = [(b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]), (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]), (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])];
          const L0 = len3(nv);
          return L0 < 1e-9 ? 0 : dot3(sub3(P, a), nv) / L0;
        };
        const r0 = res(P0);
        if (Math.abs(r0) > 1e-7) cands.push({ kind: 'flat', wall: ids, res, near: Math.abs(r0) <= tol });
      }
    }
    // Solve each nearby candidate on its own, then try the best one together with a second.
    const cap = c => (c.kind === 'angle' ? Math.max(tol, c.arm * Math.tan(3 * Math.PI / 180)) : tol * 1.5);
    const dist = P => len3(sub3(P, P0));
    const singles = [];
    for (const c of cands) {
      if (!c.near) continue;
      const P = solveOn(P0, basis, [c]);
      if (P && dist(P) <= cap(c)) singles.push({ c, P, d: dist(P) });
    }
    if (!singles.length) return null;
    singles.sort((x, y) => x.d - y.d);
    let best = { P: singles[0].P, used: [singles[0].c], d: singles[0].d };
    if (basis.length > 1) {
      for (const o of singles.slice(1, 14)) {
        const P = solveOn(P0, basis, [singles[0].c, o.c]);
        if (P && dist(P) <= Math.max(cap(singles[0].c), cap(o.c)) && (best.used.length < 2 || dist(P) < best.d)) best = { P, used: [singles[0].c, o.c], d: dist(P) };
      }
    }
    return best;
  }

  // What the selected dot measures, and what it snapped to: white edges, dashed guides, and tags.
  const tagLayer = document.createElement('div');
  tagLayer.className = 'snap-tags';
  stage.appendChild(tagLayer);
  let tags = [];
  function addTag(text, p, hit, lift = 0) {   // lift: pixels above the point (corner angles sit just above their dot)
    const el = document.createElement('div');
    el.className = 'snap-tag' + (hit ? ' hit' : '');
    el.textContent = text;
    tagLayer.appendChild(el);
    tags.push({ el, p, lift });
  }
  function placeTags() {
    if (!tags.length) return;
    const w = stage.clientWidth, h = stage.clientHeight, v = new THREE.Vector3();
    for (const t of tags) {
      world.localToWorld(v.set(...t.p)).project(camera);
      if (v.z > 1) { t.el.hidden = true; continue; }
      t.el.hidden = false;
      t.el.style.transform = `translate(${((v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - v.y) / 2 * h - t.lift).toFixed(1)}px) translate(-50%, -50%)`;
    }
  }
  function drawSnaps() {
    clear(snapGroup);
    tagLayer.textContent = '';
    tags = [];
    const tg = active() ? target() : null;
    if (!tg || st.sel == null || !tg.pts[st.sel]) return;
    const cg = cage(tg), me = cg.me;
    if (!cg.nodes.has(me)) return;
    const pos = id => cg.nodes.get(id).p, mid = (a, b) => a.map((x, i) => (x + b[i]) / 2);
    const lenOf = e => len3(sub3(pos(e[0]), pos(e[1])));
    const used = st.snapUsed || [], hot = new Map();   // edge key -> tag text when it snapped
    const guides = [], cornerTags = [];
    // Two alignments with the same neighbour make that edge run along the third axis.
    const aligned = new Map();
    for (const c of used) if (c.kind === 'align') aligned.set(c.id, [...(aligned.get(c.id) || []), c.a]);
    for (const c of used) {
      if (c.kind === 'align') {
        const along = cg.edges.find(e => e.includes(me) && e.includes(c.id));
        if (along) {   // lined up with a neighbour: if the edge now runs exactly along one axis, say that on the edge
          const v = sub3(pos(c.id), pos(me)), off = [0, 1, 2].filter(a => Math.abs(v[a]) > 1e-6);
          if (off.length === 1) { hot.set(edgeKey(along), `∥ ${AX[off[0]]}`); continue; }
        }
        guides.push([pos(me), pos(c.id), `same ${AX[c.a]} as ${cg.nodes.get(c.id).name}`]);
      } else if (c.kind === 'len') {
        const t = `= ${f2(lenOf(c.e) * scale)} mm`;
        hot.set(edgeKey(c.e), t);
        hot.set(edgeKey(c.e2), t);
      } else if (c.kind === 'flat') {
        const w = c.wall;
        for (let j = 0; j < 4; j++) hot.set(edgeKey([w[j], w[(j + 1) % 4]]), hot.get(edgeKey([w[j], w[(j + 1) % 4]])) || '');
        cornerTags.push([w.map(pos).reduce((a2, p) => a2.map((x, k2) => x + p[k2] / 4), [0, 0, 0]), 'flat wall']);
      } else if (c.kind === 'angle') {
        hot.set(edgeKey([c.at, c.a]), hot.get(edgeKey([c.at, c.a])) || '');
        hot.set(edgeKey([c.at, c.b]), hot.get(edgeKey([c.at, c.b])) || '');
        cornerTags.push([pos(c.at), `${c.th}°`]);
      }
    }
    // Snapped edges in solid white (the matched edge too), guides dashed.
    const segs = [];
    for (const e of cg.edges) if (hot.has(edgeKey(e))) segs.push(pos(e[0]), pos(e[1]));
    fat(snapGroup, segs, 0xf4f7fa, 3.5, 1, false, 14);
    const dash = [];
    for (const [a, b] of guides) dash.push(a, b);
    fat(snapGroup, dash, 0xf4f7fa, 1.5, 0.9, true, 14);
    // Tags: each edge at the dot shows its true length; snapped ones say why.
    for (const e of cg.edges) {
      const key = edgeKey(e), atMe = e.includes(me);
      if (!atMe && !hot.has(key)) continue;
      const t = hot.get(key);
      addTag(t ? (t.startsWith('=') ? t : `${t ? t + ' · ' : ''}${f2(lenOf(e) * scale)} mm`) : `${f2(lenOf(e) * scale)} mm`, mid(pos(e[0]), pos(e[1])), hot.has(key));
    }
    for (const [a, b, t] of guides) addTag(t, mid(a, b), true);
    for (const [p, t] of cornerTags) addTag(t, p, true, 20);
    // The corner angle at the dot, between its two outline edges, when nothing snapped there.
    if (!cornerTags.length && me[0] === 'E') {   // a joining-edge dot: the bend at it, between its neighbours along the edge
      const nb = cg.edges.filter(e => e.includes(me)).map(e => (e[0] === me ? e[1] : e[0]));
      if (nb.length === 2) {
        const A = sub3(pos(nb[0]), pos(me)), B = sub3(pos(nb[1]), pos(me)), la = len3(A), lb = len3(B);
        if (la > 1e-6 && lb > 1e-6) addTag(`${(Math.acos(Math.max(-1, Math.min(1, dot3(A, B) / (la * lb)))) * 180 / Math.PI).toFixed(1)}°`, pos(me), false, 20);
      }
    } else if (!cornerTags.length) {
      const pfx = me[0], i = +me.slice(1), n = tg.k.points.length;
      const a = pfx + ((i - 1 + n) % n), b = pfx + ((i + 1) % n);
      if (tg.k.closed || (i > 0 && i < n - 1)) {
        const A = sub3(pos(a), pos(me)), B = sub3(pos(b), pos(me)), la = len3(A), lb = len3(B);
        if (la > 1e-6 && lb > 1e-6 && n >= 3) addTag(`${(Math.acos(Math.max(-1, Math.min(1, dot3(A, B) / (la * lb)))) * 180 / Math.PI).toFixed(1)}°`, pos(me), false, 20);
      }
    }
    placeTags();
  }

  // ---------- the selected dot's own arrows: move it along one axis only ----------
  // An outline dot stays on its face, so only the two directions along the face are offered.
  const dotGizmo = new THREE.TransformControls(camera, canvas);
  dotGizmo.setSpace('world');
  dotGizmo.setSize(0.7);
  scene.add(dotGizmo);
  styleArrows(dotGizmo);
  const dotProxy = new THREE.Object3D();
  world.add(dotProxy);
  let dg = null;
  dotGizmo.addEventListener('dragging-changed', e => {
    controls.enabled = !e.value;
    if (e.value) {
      const tg = target();
      if (!tg || st.sel == null || !tg.pts[st.sel]) return;
      ownBack(tg);
      ownEdge(tg);
      const q0 = tg.pts[st.sel], P0 = dotPos(tg, q0);
      dg = { start: dotProxy.position.clone(), orig: { ...q0 }, idx: st.sel, moved: false, startP: P0, startN: modelToPlane(tg.plane.axis, P0)[2] };
      return;
    }
    if (!dg) return;
    const g = dg;
    dg = null;
    st.snapUsed = null;
    const tg = target();
    if (g.moved && tg) save(tg, `moved dot ${g.idx + 1}`);
    buildLines();
  });
  dotGizmo.addEventListener('objectChange', () => {
    if (!dg) return;
    // A click on an arrow isn't a move: hold still until the pointer has travelled 4 px.
    if (!dg.moved && pressAt && Math.hypot(lastPointer[0] - pressAt[0], lastPointer[1] - pressAt[1]) < 4) { dotProxy.position.copy(dg.start); return; }
    let tg = ownBack(target()), q = tg && tg.pts[dg.idx];
    if (!q) return;
    const dv = dotProxy.position.clone().sub(dg.start), ax = tg.plane.axis;
    let P = [dg.startP[0] + dv.x, dg.startP[1] + dv.y, dg.startP[2] + dv.z];
    const basis = [...(dotGizmo.axis || '')].filter(ch => 'XYZ'.includes(ch)).map(ch => [ch === 'X' ? 1 : 0, ch === 'Y' ? 1 : 0, ch === 'Z' ? 1 : 0]);
    const sn = basis.length ? snapDot(tg, dg.idx, P, basis, altHeld) : null;
    st.snapUsed = sn ? sn.used : null;
    if (sn) P = sn.P;
    if (tg.face === 'edge') {
      setEdgeDot(ownEdge(tg), q, P);
      dg.moved = true;
      requestSolve();
      updatePartDotFields();
      buildLines();
      return;
    }
    const [u, v, nrm] = modelToPlane(ax, P);
    q.u = +u.toFixed(4);
    q.v = +v.toFixed(4);
    if (tg.editing && Math.abs(nrm - dg.startN) > 1e-9) {
      // Moving a front dot in or out moves only that dot: a back that still copies the front gets its own dots first.
      if (tg.face === 'front' && !tg.d.back) { tg.d.back = tg.k.points.map(p => ({ ...p })); tg.d.back[dg.idx] = { ...dg.orig }; }
      const w = clampDepth(tg, dg.idx, (nrm - tg.plane.offset) / tg.sg);
      if (Math.abs(w) > 1e-9) q.w = +w.toFixed(4); else delete q.w;
    } else if (tg.editing) {
      if (dg.orig.w) q.w = dg.orig.w; else delete q.w;
    }
    dg.moved = true;
    if (tg.d) requestSolve();
    updateDotFields();
    updatePartDotFields();
    buildLines();
  });
  function placeDotGizmo() {
    const tg = active() ? target() : null, q = tg && st.sel != null ? tg.pts[st.sel] : null;
    if (!q || st.drag) { if (dotGizmo.object && !dg) dotGizmo.detach(); return; }
    if (!dotGizmo.object) dotGizmo.attach(dotProxy);
    const ax = tg.plane.axis, flat = !tg.editing;   // a sketch stays flat; a part's dot can also go in and out of its face
    dotGizmo.showX = !flat || ax !== 'x'; dotGizmo.showY = !flat || ax !== 'y'; dotGizmo.showZ = !flat || ax !== 'z';
    if (!dg) dotProxy.position.set(...dotPos(tg, q));
  }
  const busy = () => !!st.drag || !!dg;   // a dot is being dragged (by hand or by its arrows)
  const dotSelected = () => { const tg = active() ? target() : null; return !!(tg && st.sel != null && tg.pts[st.sel]); };

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
      S.sketches.map(x => [x.id, x.name, x.closed, x.points.length, x.plane.axis]), S.drawn.map(d => [d.id, d.sketch, nameOf(d.id)]),
      k && st.sel != null && k.points[st.sel] ? k.points[st.sel].smooth : null]);
    showReadout();
    if (!force && key === panelKey) { updateDotFields(); return; }
    panelKey = key;
    section.innerHTML = '';
    const head = document.createElement('div');
    head.innerHTML = window.Fold ? Fold.head('sketches', 'Sketch · 2D', S.sketches.length ? `· ${S.sketches.length}` : '') : `<div class="eyebrow">Sketch · 2D</div>`;
    section.appendChild(head);
    const btn = document.createElement('div');
    btn.className = 'row';
    btn.innerHTML = `<button class="tool${sketching() ? ' on' : ''}" data-a="tool">${sketching() ? 'Stop sketching' : 'Start sketching'}</button>`;
    section.appendChild(btn);
    if (!sketching()) {
      section.appendChild(para('note', S.sketches.length
        ? `${S.sketches.length} sketch${S.sketches.length > 1 ? 'es' : ''} in this scene, drawn in yellow. Start sketching to edit them.`
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
    row3.innerHTML = `<button data-a="new">New sketch</button>${k && !k.closed && k.points.length >= 3 ? '<button data-a="close">Close shape</button>' : ''}${k && k.closed ? '<button data-a="open">Open shape</button>' : ''}` +
      (k && k.closed && k.points.length >= 3 && !ownerOf(k) && !cutUser(k) ? '<button class="primary" data-a="mkpart">Make it a part</button>' : '');
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
    ul.dataset.foldList = 'sketches';
    if (window.Fold && Fold.is('sketches')) ul.classList.add('folded');
    ul.innerHTML = S.sketches.map(x => `<li data-k="${x.id}" class="${x.id === st.current && sketching() ? 'on' : ''}">
      <div class="pin-top"><b style="color:var(--sketch)">${x.id}</b><span class="where">${esc(x.name)} · ${AXES[x.plane.axis].label} at ${AXES[x.plane.axis].n} ${f2(x.plane.offset * scale)} · ${x.points.length} dots${x.closed ? ', closed' : ''}</span>
      ${ownerOf(x) ? `<span class="where">→ ${esc(nameOf(ownerOf(x).id))}</span>` : cutUser(x) ? `<span class="where">→ pocket in ${esc(nameOf(cutUser(x).id))}</span>` : x.closed && x.points.length >= 3 ? '<button class="mini" data-a="mkpart">Make part</button>' : ''}
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
    else if (a === 'mkpart') makeDrawnFrom(li ? li.dataset.k : k && k.id);
    else if (a === 'smooth' && k && st.sel != null) { k.points[st.sel].smooth = !k.points[st.sel].smooth; save(k, `made dot ${st.sel + 1} ${k.points[st.sel].smooth ? 'smooth' : 'sharp'}`); renderPanel(); }
    else if (a === 'del') deleteDot();
    else if (a === 'edit' && li) { st.current = li.dataset.k; st.sel = null; const kk = cur(); st.axis = kk.plane.axis; st.offset = kk.plane.offset; refresh(); renderPanel(); }
    else if (a === 'delk' && li) {
      const kk = S.sketches.find(x => x.id === li.dataset.k), owner = ownerOf(kk), ownerName = owner ? nameOf(owner.id) : '';
      S.sketches = S.sketches.filter(x => x.id !== li.dataset.k);
      if (owner) {   // the part is made from this outline, so it goes too (undo brings both back)
        S.drawn = S.drawn.filter(d => d.id !== owner.id);
        S.pins = S.pins.filter(q => q.part !== owner.id);
        delete S.info[owner.id];
      }
      if (st.current === li.dataset.k) { st.current = null; st.sel = null; }
      commit({ text: `Removed ${kk ? kk.name : 'a sketch'}${owner ? ` and ${ownerName}, the part made from it` : ''}`, adapt: false });
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
    if (st.current && !S.sketches.some(k => k.id === st.current)) { st.current = null; st.sel = null; }
    // Selecting a different drawn part (or none) clears the selected dot. The sketch tool keeps its own.
    const ed = editPart() ? curId() : null;
    if (ed !== st.editLive) { st.editLive = ed; st.sel = null; st.face = 'front'; }
    const k = cur();
    if (k && st.sel != null && st.sel >= k.points.length) st.sel = k.points.length ? k.points.length - 1 : null;
    buildPlane();
    buildCuts();
    buildLines();
    renderPanel();
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
    placeDotGizmo();
    placeTags();
    syncResolution();
    updateClip();
    if (performance.now() < flashUntil + 50) showReadout();
  }

  window.Sketcher = { enter, exit, refresh, tick, renderPanel: () => renderPanel(true), hint: HINT,
    // for scripts and tests
    state: () => ({ ...st, drag: !!st.drag }), sample: id => { const k = S.sketches.find(x => x.id === id); return k ? sample(k) : []; },
    cuts: () => cutsNow.map(s => ({ ...s })), setAxis, lookStraight,
    face: () => st.face, setFace, dotSelected, busy,
    // the selected dot of a drawn part, for its panel: index, count, face, u, v, smooth, plane axis
    dot: () => { const tg = editPart() ? target() : null, q = tg && st.sel != null ? tg.pts[st.sel] : null;
      if (!q) return null;
      if (tg.face === 'edge') { const [u, v, n] = modelToPlane(tg.plane.axis, dotPos(tg, q)); return { i: st.sel, count: tg.pts.length, face: 'edge', edge: tg.edge, u, v, n, smooth: !!q.smooth, axis: tg.plane.axis }; }
      return { i: st.sel, count: tg.pts.length, face: tg.face, u: q.u, v: q.v, n: tg.plane.offset + depthOf(tg, q), smooth: !!q.smooth, axis: tg.plane.axis }; },
    edge: () => (st.face === 'edge' ? st.edge : null),
    setDot: (f, val) => {
      const tg = ownEdge(ownBack(target()));
      if (!tg || st.sel == null || !tg.pts[st.sel]) return;
      const q = tg.pts[st.sel];
      if (tg.face === 'edge') {   // a joining-edge dot: set that coordinate of its real position
        const P3 = modelToPlane(tg.plane.axis, dotPos(tg, q));
        P3[{ u: 0, v: 1, n: 2 }[f]] = val;
        setEdgeDot(tg, q, toModel(tg.plane.axis, P3[2], P3[0], P3[1]));
      } else if (f === 'n') {   // the third number is where the dot sits along the face's normal; it becomes the dot's depth
        if (tg.face === 'front' && !tg.d.back) tg.d.back = tg.k.points.map(p => ({ ...p }));   // only this dot moves
        const w = clampDepth(tg, st.sel, (val - tg.plane.offset) / tg.sg);
        if (Math.abs(w) > 1e-9) q.w = +w.toFixed(4); else delete q.w;
      } else q[f] = +val.toFixed(4);
      save(tg, `typed dot ${st.sel + 1}`);
    },
    toggleSmooth: () => { const tg = ownEdge(ownBack(target())); if (!tg || st.sel == null || !tg.pts[st.sel]) return; const q = tg.pts[st.sel]; q.smooth = !q.smooth; save(tg, `made dot ${st.sel + 1} ${q.smooth ? 'smooth' : 'sharp'}`); },
    deleteDot };
  renderPanel(true);
  refresh();
})();
