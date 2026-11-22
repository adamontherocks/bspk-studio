// Contact-driven motion for BSPK Studio (added 2026-11-15 for the Crescent movement).
// A project's `mechanisms` block makes drawn parts move: some turn with an arbor, some swing on a pivot by an angle the
// engine solves from the drawn shapes themselves (a lever's nose resting on a cam, a pawl kicking a ratchet, a jumper
// seating a star). Links drive arbors from those angles (a rack turning a hand pinion, a faux balance swinging).
// Kinematics only: shapes, contact, timing and ranges are checked; forces, masses and spring rates are not.
// The engine also sweeps a full 12 hours and clash-checks drawn parts (fixed and moving) against each other and the gears.
(function () {
  'use strict';
  const DEG = Math.PI / 180;
  const Mech = { checksDrawn: false, sweep: null, staticClashes: [] };
  window.Mech = Mech;
  const def = () => (typeof PROJECT !== 'undefined' && PROJECT.mechanisms) || null;

  // ---------- geometry ----------
  const rot = (p, c, a) => { const x = p[0] - c[0], y = p[1] - c[1], ca = Math.cos(a), sa = Math.sin(a); return [c[0] + x * ca - y * sa, c[1] + x * sa + y * ca]; };
  function inside(p, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const a = poly[i], b = poly[j];
      if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < a[0] + (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1])) c = !c;
    }
    return c;
  }
  function distToPoly(p, poly) {   // shortest distance from a point to a closed outline
    let best = Infinity;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const a = poly[j], b = poly[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1e-12;
      const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)), x = a[0] + t * dx - p[0], y = a[1] + t * dy - p[1];
      best = Math.min(best, x * x + y * y);
    }
    return Math.sqrt(best);
  }
  // a round pin (radius r) touching an outline: inside it, or closer than its radius to the edge
  const touches = (p, poly, r) => inside(p, poly) || (r > 0 && distToPoly(p, poly) < r);
  const polys = {};
  function poly(did) {   // the drawn part's outline, world coordinates, as drawn (its pose)
    const d = S.drawn.find(x => x.id === did), k = sketchOf(d);
    if (!k) return null;
    const key = JSON.stringify([k.points, k.plane]);
    if (!polys[did] || polys[did].key !== key) polys[did] = { key, pts: outlinePoints(k).slice(0, -1).map(p => [p[0], p[1]]) };
    return polys[did].pts;
  }
  // where a drawn part turns, and by how much, at a moment
  function mountOf(did) { const m = def(); return m && m.mounts && m.mounts[did]; }
  function centreOf(did) {
    const mt = mountOf(did);
    if (!mt) return null;
    if (mt.axis) return S.pos[mt.axis];
    return mt.pivot;
  }

  // ---------- one moment: solve every angle (deg), starting from the previous state ----------
  function fresh() { return { a: {}, sig: 0, k: 0, pushed: false, flex: 0, pushPeak: 0, events: [] }; }
  let live = null, liveT = null;
  function axisAngle(axis, te, s) {   // an arbor's angle: from a link if one drives it, else its rate
    const m = def(), l = m && (m.links || []).find(x => x.arbor === axis);
    if (l) {
      if (l.kind === 'oscillate' || l.kind === 'table') return linkAngle(l, te, s);
      if (s) return l.ratio * (s.a[l.from] || 0) + (l.offset || 0);
    }
    return (D.omega[axis] || 0) * te / DEG;
  }
  // a link's angle: a ratio from a solved angle, a sine of another arbor (a stand-in), or a table played back against another
  // arbor's angle (an escapement solved offline from the drawn shapes: it repeats every tooth, so one tooth's worth is stored)
  function linkAngle(l, te, s) {
    if (l.kind === 'oscillate') return l.amp * Math.sin((l.cycles || 1) * axisAngle(l.from, te) * DEG + (l.phase || 0) * DEG);
    if (l.kind === 'table') {
      const P = l.period, N = l.values.length, w = axisAngle(l.from, te), x = (((w % P) + P) % P) / P * N, i = Math.floor(x), f = x - i;
      return l.values[i % N] * (1 - f) + l.values[(i + 1) % N] * f + (l.offset || 0);
    }
    return l.ratio * (s ? (s.a[l.from] || 0) : 0) + (l.offset || 0);
  }
  function camState(s, f, te) {
    const cm = mountOf(f.cam);
    if (f.camAngle) return { c: cm ? centreOf(f.cam) : f.pivot, ang: s.a[f.camAngle] || 0 };
    if (cm && cm.axis) return { c: S.pos[cm.axis], ang: axisAngle(cm.axis, te) };
    if (cm && cm.angle) return { c: cm.pivot, ang: s.a[cm.angle] || 0 };
    return { c: [0, 0], ang: 0 };
  }
  function springDir(f, cs) {   // the side a spring pushes a follower: toward the cam's centre
    if (f._dir) return f._dir;
    const n0 = f.nose, dp = Math.hypot(...[0, 1].map(i => rot(n0, f.pivot, DEG)[i] - cs.c[i])), dm = Math.hypot(...[0, 1].map(i => rot(n0, f.pivot, -DEG)[i] - cs.c[i]));
    f._dir = dp < dm ? 1 : -1;
    return f._dir;
  }
  function solveFollower(s, f, te) {
    const cam = poly(f.cam);
    if (!cam) return;
    const cs = camState(s, f, te), dir = springDir(f, cs), lo = f.min, hi = f.max;
    const inCam = a => touches(rot(rot(f.nose, f.pivot, a * DEG), cs.c, -cs.ang * DEG), cam, f.noseR || 0);   // the nose may be a round pin
    const step = 0.05;
    let a = s.a[f.id] != null ? s.a[f.id] : 0;
    const bis = (x, y) => { for (let i = 0; i < 28; i++) { const m = (x + y) / 2; if (inCam(m)) x = m; else y = m; } return y; };
    if (inCam(a)) {          // the cam pushed the nose: move against the spring until it's clear
      let b = a, n = 0;
      while (inCam(b) && n++ < 4000) b -= dir * step;
      a = bis(b + dir * step, b);
    } else {                 // the spring carries it toward the cam until it touches, or to its stop
      let b = a, n = 0;
      while (n++ < 4000) {
        const nb = b + dir * step;
        if ((dir > 0 && nb > hi) || (dir < 0 && nb < lo)) { b = dir > 0 ? hi : lo; break; }
        if (inCam(nb)) { b = bis(nb, b); break; }
        b = nb;
      }
      a = b;
    }
    s.a[f.id] = Math.max(lo, Math.min(hi, a));
  }
  function solveRatchet(s, r, aPrev) {
    const wheel = poly(r.wheel);
    if (!wheel) return;
    const f = def().solve.find(x => x.id === r.pawl.follow), aNow = s.a[r.pawl.follow] || 0;
    const pushDir = f && f._dir ? f._dir : -1;           // the pawl kicks while its lever moves the way its spring drives it
    const tipAt = a => rot(r.pawl.tip, r.pawl.pivot, a * DEG);
    const inWheel = (p, sig) => touches(rot(p, r.pivot, -sig * DEG), wheel, r.pawl.tipR || 0);   // the pawl's tip may be a round pin
    const seat = () => s.k * r.pitch * r.advance;
    const moving = Math.sign(aNow - aPrev);
    let pushing = false;
    if (moving === pushDir && Math.abs(aNow - aPrev) > 1e-9) {
      const n = Math.max(1, Math.ceil(Math.abs(aNow - aPrev) / 0.1)), before = s.sig;
      for (let i = 1; i <= n; i++) {
        const p = tipAt(aPrev + (aNow - aPrev) * i / n);
        let g = 0;
        while (inWheel(p, s.sig) && g++ < 3000) s.sig += 0.05 * r.advance;
      }
      pushing = s.sig !== before;
      if (pushing) { s.pushPeak = Math.max(s.pushPeak, (s.sig - seat()) * r.advance); s.pushed = true; }
    }
    if (!pushing) {
      // the pawl rides back over the teeth: its flexure gives; record how far it has to lift
      const p = tipAt(aNow);
      if (moving !== pushDir && inWheel(p, s.sig)) {
        const c = r.pivot, v = [p[0] - c[0], p[1] - c[1]], L0 = Math.hypot(...v) || 1;
        let d = 0;
        while (d < 6 && inWheel([c[0] + v[0] / L0 * (L0 + d), c[1] + v[1] / L0 * (L0 + d)], s.sig)) d += 0.02;
        s.flex = Math.max(s.flex, d);
      }
      if (s.pushed) {        // the push has ended: the jumper decides where the star rests
        const off = (s.sig - seat()) * r.advance;
        if (off > r.apex) { s.k += 1; s.events.push({ kind: 'jump', push: s.pushPeak }); }
        else if (off > 0.01) s.events.push({ kind: 'fail', push: s.pushPeak });
        s.sig = seat(); s.pushed = false; s.pushPeak = 0;
      }
    }
    s.a[r.id] = s.sig;
  }
  function step(s, te) {
    const m = def();
    const prev = Object.assign({}, s.a);
    for (const so of m.solve) {
      if (so.kind === 'follower') solveFollower(s, so, te);
      else if (so.kind === 'ratchet') solveRatchet(s, so, prev[so.pawl.follow] != null ? prev[so.pawl.follow] : 0);
    }
  }

  // ---------- the 12-hour sweep: the check, and the table that lets the view jump to any time ----------
  function runSweep() {
    const m = def(), s = fresh(), DT = 5, HOURS = 12, T_END = HOURS * 3600 + 120;
    const lever = m.solve.find(x => x.kind === 'follower'), rat = m.solve.find(x => x.kind === 'ratchet');
    const table = [], flybacks = [], ranges = {};
    let prevLever = 0, onStop = 0, samples = 0;
    for (const so of m.solve) delete so._dir;
    for (let te = 0; te <= T_END; te += DT) {
      step(s, te);
      for (const so of m.solve) { const v = s.a[so.id] || 0; const r = ranges[so.id] || (ranges[so.id] = [Infinity, -Infinity]); if (so.kind === 'follower') { r[0] = Math.min(r[0], v); r[1] = Math.max(r[1], v); } }
      if (lever) {
        const v = s.a[lever.id] || 0;
        if (v < prevLever - 5) flybacks.push(te);
        if (Math.abs(v - lever.min) < 1e-6 || Math.abs(v - lever.max) < 1e-6) onStop++;
        prevLever = v; samples++;
      }
      table.push({ te, a: Object.assign({}, s.a), sig: s.sig, k: s.k });
    }
    const jumps = s.events.filter(e => e.kind === 'jump'), fails = s.events.filter(e => e.kind === 'fail');
    // the hand's sweep through its link, measured over the second hour (after the first fly-back)
    const link = (m.links || []).find(l => lever && l.from === lever.id);
    const span = flybacks.length > 1 ? table.filter(r => r.te > flybacks[0] + DT && r.te < flybacks[1] - DT).map(r => r.a[lever.id]) : [];
    const handSweep = link && span.length ? Math.abs(link.ratio) * (Math.max(...span) - Math.min(...span)) : null;
    Mech.sweep = { flybacks, jumps, fails, flex: s.flex, ranges, onStop, samples, handSweep, table, DT, hours: HOURS, rat, clashes: [], reading: null };
    return Mech.sweep;
  }
  // does the movement tell the right time? Read every hand the way a person would, every sample, against the clock
  function readsTime(table, DT) {
    const m = def(), rd = m.read;
    if (!rd) return null;
    const out = {}, settle = rd.settle || 2 * DT, wrap = (d, p) => ((d % p) + p + p / 2) % p - p / 2;
    if (rd.minute) {   // a hand on a link from a solved angle, read on a uniform track from 'zero' (0 min) to 'full' (60 min)
      const l = (m.links || []).find(x => x.arbor === rd.minute.arbor), span = ((rd.minute.zero - rd.minute.full) % 360 + 360) % 360;
      // before each fly-back a round feeler rolls over the snail's edge and the hand eases back a little: find that stretch
      // (the lever turning against its hour-long direction) and report it apart, rather than hide it or call it an error
      const lever = (r) => r.a[l.from] || 0;
      let rollS = 0, rollDeg = 0;
      for (let i = 1; i < table.length; i++) {
        if (table[i].te % 3600 !== 0 || table[i].te === 0) continue;
        let j = i - 1, peak = j;
        while (j > 0 && lever(table[j - 1]) > lever(table[j]) + 1e-6 && table[i].te - table[j - 1].te < 600) j--;   // walk back while the lever was falling
        for (let q = j; q < i; q++) if (lever(table[q]) > lever(table[peak])) peak = q;
        rollS = Math.max(rollS, table[i].te - table[j].te);
        rollDeg = Math.max(rollDeg, Math.abs(l.ratio) * (lever(table[j]) - lever(table[i - 1])));
      }
      const rollOff = rollS > 0 ? rollS + DT : 0;
      let worst = 0, at = 0, n = 0;
      for (const r of table) {
        const into = r.te % 3600;
        if (into < settle || into > 3600 - rollOff) continue;   // the fly-back itself, and the roll-off before it
        const world = l.ratio * (r.a[l.from] || 0) + (l.offset || 0) + 90;   // hands point to 12 o'clock at no turn
        const reading = (((rd.minute.zero - world) % 360 + 360) % 360) / span * 60, err = reading - into / 60;
        n++; if (Math.abs(err) > Math.abs(worst)) { worst = err; at = r.te; }
      }
      out.minute = { worst, at, n, rollS: rollOff, rollDeg };
    }
    if (rd.hour) {   // a star stepped by a solved angle: which numeral is under the index
      const st = rd.hour.step || 30;
      let wrong = 0, firstWrong = null, seat = 0, n = 0;
      for (const r of table) {
        const into = r.te % 3600;
        if (into < settle) continue;
        const a = (r.a[rd.hour.solve] || 0) * (rd.hour.sign || 1), k = Math.round(a / st);
        const shows = ((k % 12) + 12) % 12 || 12, should = Math.floor(r.te / 3600) % 12 || 12;
        seat = Math.max(seat, Math.abs(a - k * st)); n++;
        if (shows !== should) { wrong++; if (firstWrong == null) firstWrong = { te: r.te, shows, should }; }
      }
      out.hour = { wrong, firstWrong, seat, n };
    }
    if (rd.seconds) {   // a hand on an arbor turning at its rate
      let worst = 0;
      for (const r of table) {
        const world = (D.omega[rd.seconds.arbor] || 0) * r.te / DEG + 90;
        const reading = (((90 - world) % 360 + 360) % 360) / 6;
        worst = Math.max(worst, Math.abs(wrap(reading - r.te % 60, 60)));
      }
      out.seconds = { worst };
    }
    return out;
  }

  // ---------- clash checks for drawn parts: fixed ones against gears, moving ones against everything ----------
  function zBand(d) { const k = sketchOf(d), [f0, f1] = faceOffsets(d, k); return [Math.min(f0, f1), Math.max(f0, f1)]; }
  let CACHE = { mat: new Map(), placed: new Map() };   // emptied whenever the shapes may have changed: within one run of the checks nothing moves
  function material(d, k, zLocal) {   // the part's material at a depth: outline minus the cuts active there (Clipper paths)
    const ck = d.id + '|' + zLocal.toFixed(4), hit = CACHE.mat.get(ck);
    if (hit) return hit;
    const res = materialRaw(d, k, zLocal); CACHE.mat.set(ck, res); return res;
  }
  function materialRaw(d, k, zLocal) {
    const C = ClipperLib, outline = outlinePoints(k).slice(0, -1).map(p => [p[0], p[1]]);
    const layers = isFlat(d, k) ? (d.cuts || []).flatMap(c => cutLayers(c, k, d.thickness)) : [];
    const cl = new C.Clipper(), out = new C.Paths();
    cl.AddPath(toClip(outline), C.PolyType.ptSubject, true);
    const act = layers.filter(l => l.iv[0] <= zLocal && l.iv[1] >= zLocal).map(l => sameWay(toClip(l.path)));   // all one way round (see sameWay)
    if (act.length) cl.AddPaths(act, C.PolyType.ptClip, true);
    cl.Execute(C.ClipType.ctDifference, out, C.PolyFillType.pftNonZero, C.PolyFillType.pftNonZero);
    return out;
  }
  function areaOf(a, b) {
    const C = ClipperLib, cl = new C.Clipper(), out = new C.Paths();
    cl.AddPaths(a, C.PolyType.ptSubject, true); cl.AddPaths(b, C.PolyType.ptClip, true);
    cl.Execute(C.ClipType.ctIntersection, out, C.PolyFillType.pftNonZero, C.PolyFillType.pftNonZero);
    return out.reduce((t, p) => t + Math.abs(C.Clipper.Area(p)), 0) / (CLIP * CLIP);
  }
  const circlePath = (x, y, r) => [toClip(Array.from({ length: 64 }, (_, j) => [x + r * Math.cos(j * Math.PI / 32), y + r * Math.sin(j * Math.PI / 32)]))];
  function staticClashes() {
    if (!window.ClipperLib) return [];
    const els = elements(S, D), out = [], m = def() || {};
    const moving = new Set(Object.keys(m.mounts || {}));
    for (const d of S.drawn) {
      if (moving.has(d.id) || d.place) continue;
      const k = sketchOf(d);
      if (!k || !k.closed || k.plane.axis !== 'z') continue;
      const [z0, z1] = zBand(d);
      for (const e of els) {
        const lo = Math.max(z0, e.z0), hi = Math.min(z1, e.z1);
        if (hi - lo <= 1e-6) continue;
        const zMid = (lo + hi) / 2 - z0, mat = material(d, k, d.grow === 'minus' ? z1 - (lo + hi) / 2 : zMid);
        const a = areaOf(mat, circlePath(e.x, e.y, e.r + S.minGap));
        if (a > 0.02) out.push(`${nameOf(d.id)} × ${e.name}: ${a.toFixed(2)} mm² inside its space (with the ${S.minGap} mm gap)`);
      }
    }
    return out;
  }
  function placed(did, ang) {   // a moving drawn part at an angle, as Clipper paths: its outline minus its through holes and slots
    const c = centreOf(did), d = S.drawn.find(x => x.id === did), k = sketchOf(d);   // (a pin in a closed slot is not a clash)
    const thru = (d.cuts || []).filter(x => x.depth == null);
    if (!thru.length || !window.ClipperLib) return [toClip(poly(did).map(p => rot(p, c, ang * DEG)))];
    let paths = CACHE.placed.get(did);
    if (!paths) { paths = material(d, k, d.thickness / 2).map(path => path.map(q => [q.X / CLIP, q.Y / CLIP])); CACHE.placed.set(did, paths); }
    return paths.map(path => toClip(path.map(p => rot(p, c, ang * DEG))));
  }
  function movingClashes(table) {
    if (!window.ClipperLib) return [];
    const m = def(), mounts = m.mounts || {}, out = new Map();
    const fixed = S.drawn.filter(d => !mounts[d.id] && sketchOf(d) && sketchOf(d).plane.axis === 'z');
    const movers = S.drawn.filter(d => mounts[d.id] && !mounts[d.id].axisX && !mounts[d.id].axisY && !d.place);   // side and slanted parts are checked side-on
    // pairs that are meant to touch (a follower and its cam, a pawl and its wheel): only a small disc round the touching point is let off,
    // so the rest of the follower (its arm, its body) is still checked against the cam
    const contacts = new Map(), NOSE_R = 1.2;
    for (const so of m.solve) {
      if (so.kind === 'follower') contacts.set([so.part, so.cam].sort().join('|'), row => rot(so.nose, so.pivot, (row.a[so.id] || 0) * DEG));
      if (so.kind === 'ratchet') { const f = m.solve.find(x => x.id === so.pawl.follow), pp = so.pawl.part || (f && f.part); if (pp) contacts.set([pp, so.wheel].sort().join('|'), row => rot(so.pawl.tip, so.pawl.pivot, (row.a[so.pawl.follow] || 0) * DEG)); }
    }
    const areaOutside = (a, b, c) => {   // area of a ∩ b outside the disc at c
      const C = ClipperLib, cl = new C.Clipper(), ab = new C.Paths();
      cl.AddPaths(a, C.PolyType.ptSubject, true); cl.AddPaths(b, C.PolyType.ptClip, true);
      cl.Execute(C.ClipType.ctIntersection, ab, C.PolyFillType.pftNonZero, C.PolyFillType.pftNonZero);
      if (!ab.length) return 0;
      const whole = ab.reduce((t, p) => t + Math.abs(C.Clipper.Area(p)), 0) / (CLIP * CLIP);
      return Math.max(0, whole - areaOf(ab, circlePath(c[0], c[1], NOSE_R)));
    };
    const angleOf = (did, row) => { const mt = mounts[did]; return mt.axis ? axisAngle(mt.axis, row.te, { a: row.a }) : (row.a[mt.angle] || 0); };
    const rows = table.filter((r, i) => i % 12 === 0 || (i > 0 && Math.abs((r.a.lever || 0) - (table[i - 1].a.lever || 0)) > 1));
    const els = elements(S, D);
    // each part's box (Clipper units): pairs whose boxes don't meet can't overlap, so they skip the polygon work
    const boxOf = paths => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; for (const p of paths) for (const q of p) { if (q.X < x0) x0 = q.X; if (q.X > x1) x1 = q.X; if (q.Y < y0) y0 = q.Y; if (q.Y > y1) y1 = q.Y; } return [x0, y0, x1, y1]; };
    const meet = (A, B) => A[0] <= B[2] && B[0] <= A[2] && A[1] <= B[3] && B[1] <= A[3];
    const fixedMat = new Map();
    const fixedAt = (fx, zl) => { const k = fx.id + '|' + zl.toFixed(4); let v = fixedMat.get(k); if (!v) { const mat = material(fx, sketchOf(fx), zl); v = { mat, box: boxOf(mat) }; fixedMat.set(k, v); } return v; };
    const zb = new Map(movers.map(d => [d.id, zBand(d)]));
    for (const row of rows) {
      const P = new Map(movers.map(mv => { const pm = placed(mv.id, angleOf(mv.id, row)); return [mv.id, { pm, box: boxOf(pm) }]; }));   // each mover placed once per moment
      for (const mv of movers) {
        const [a0, a1] = zb.get(mv.id), { pm, box } = P.get(mv.id);
        for (const fx of fixed) {
          const [b0, b1] = zBand(fx), lo = Math.max(a0, b0), hi = Math.min(a1, b1);
          if (hi - lo <= 1e-6) continue;
          const F = fixedAt(fx, (lo + hi) / 2 - b0);
          if (!meet(box, F.box)) continue;
          const a = areaOf(pm, F.mat);
          if (a > 0.05) out.set(`${nameOf(mv.id)} × ${nameOf(fx.id)}`, Math.max(a, out.get(`${nameOf(mv.id)} × ${nameOf(fx.id)}`) || 0));
        }
        for (const mv2 of movers) {
          if (mv2.id <= mv.id) continue;
          const [b0, b1] = zb.get(mv2.id);
          if (Math.min(a1, b1) - Math.max(a0, b0) <= 1e-6) continue;
          if (mounts[mv.id].pivot && mounts[mv2.id].pivot && JSON.stringify(mounts[mv.id].pivot) === JSON.stringify(mounts[mv2.id].pivot) && mounts[mv.id].angle === mounts[mv2.id].angle) continue;
          const Q = P.get(mv2.id);
          if (!meet(box, Q.box)) continue;
          const touch = contacts.get([mv.id, mv2.id].sort().join('|'));
          const a = touch ? areaOutside(pm, Q.pm, touch(row)) : areaOf(pm, Q.pm);
          if (a > 0.05) out.set(`${nameOf(mv.id)} × ${nameOf(mv2.id)}`, Math.max(a, out.get(`${nameOf(mv.id)} × ${nameOf(mv2.id)}`) || 0));
        }
        for (const e of els) {
          if (Math.min(a1, e.z1) - Math.max(a0, e.z0) <= 1e-6) continue;
          if ((m.meshes || []).some(x => x.part === mv.id && x.gear === e.gear)) continue;   // a drawn rack meshes this gear (its mesh is proven offline)
          const mt = mounts[mv.id];
          if (mt.axis && mt.axis === e.arbor) continue;
          const R = (e.r + 0.2) * CLIP;
          if (!meet(box, [e.x * CLIP - R, e.y * CLIP - R, e.x * CLIP + R, e.y * CLIP + R])) continue;
          const a = areaOf(pm, circlePath(e.x, e.y, e.r + 0.2));
          if (a > 0.05) out.set(`${nameOf(mv.id)} × ${e.name}`, Math.max(a, out.get(`${nameOf(mv.id)} × ${e.name}`) || 0));
        }
      }
    }
    return [...out.entries()].map(([k, v]) => `${k}: up to ${v.toFixed(2)} mm²`);
  }

  // ---------- an escapement played from a table: check it over one tooth in fine steps (the 5 s sweep only sees a few phases) ----------
  function escapementCheck() {
    const m = def(), mounts = m.mounts || {}, out = { pairs: new Map(), steps: 0, worst: 0, links: [] };
    for (const l of (m.links || []).filter(x => x.kind === 'table')) {
      if (out.links.some(x => x.from === l.from)) continue;
      const group = new Set([l.from, ...(m.links || []).filter(x => x.kind === 'table' && x.from === l.from).map(x => x.arbor)]);
      out.links.push({ from: l.from, arbors: [...group] });
      const movers = S.drawn.filter(d => mounts[d.id] && mounts[d.id].axis && group.has(mounts[d.id].axis));
      const w = D.omega[l.from] || 0;
      if (!w) continue;
      const tooth = l.period * DEG / Math.abs(w), N = 240;
      for (let i = 0; i < N; i++) {
        const te = 7200 + tooth * i / N; out.steps++;
        const placedAt = movers.map(d => ({ d, p: placed(d.id, axisAngle(mounts[d.id].axis, te)), z: zBand(d) }));
        for (let a = 0; a < placedAt.length; a++) for (let b = a + 1; b < placedAt.length; b++) {
          const A = placedAt[a], B = placedAt[b];
          if (mounts[A.d.id].axis === mounts[B.d.id].axis) continue;
          if (Math.min(A.z[1], B.z[1]) - Math.max(A.z[0], B.z[0]) <= 1e-6) continue;
          const ar = areaOf(A.p, B.p), key = `${nameOf(A.d.id)} × ${nameOf(B.d.id)}`;
          out.worst = Math.max(out.worst, ar);
          if (ar > 0.02) out.pairs.set(key, Math.max(out.pairs.get(key) || 0, ar));
        }
      }
    }
    return out;
  }

  // ---------- made from one face: every machined cut that stops part-way into a part comes from the face it is milled from ----------
  // Through cuts can be milled from either face. Countersinks are drilled by hand, so they don't count.
  function millFaces() {
    const out = { two: [], wrong: [], tops: 0, bottoms: 0, either: 0 };
    for (const d of zParts()) {
      const blind = (d.cuts || []).filter(c => c.depth != null && c.depth < d.thickness - 1e-6);
      const faces = new Set(blind.map(c => (c.from === 'back') !== (d.grow === 'minus') ? 'top' : 'bottom'));
      for (const c of d.cuts || []) if (c.seat && c.depth == null) faces.add((c.from === 'back') !== (d.grow === 'minus') ? 'top' : 'bottom');   // a bearing seat over a through bore
      const want = d.mill === 'back' ? 'top' : d.mill === 'front' ? 'bottom' : null;
      if (faces.size > 1) out.two.push(`${nameOf(d.id)}: cuts from the top and the bottom`);
      else if (want && faces.size === 1 && !faces.has(want)) out.wrong.push(`${nameOf(d.id)}: milled from the ${want}, but its cuts come from the ${[...faces][0]}`);
      else if (faces.has('top') || want === 'top') out.tops++;
      else if (faces.has('bottom') || want === 'bottom') out.bottoms++;
      else out.either++;
    }
    return out;
  }

  // ---------- more interference checks: part against part, rods through material, side-on parts ----------
  function zParts() { return S.drawn.filter(d => { const k = sketchOf(d); return k && k.closed && k.plane.axis === 'z' && !d.place; }); }   // a slanted part is checked side-on
  function fixedVsFixed() {
    const m = def() || {}, mounts = m.mounts || {}, list = zParts().filter(d => !mounts[d.id]), out = [];
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
      const a = list[i], b = list[j], [a0, a1] = zBand(a), [b0, b1] = zBand(b), lo = Math.max(a0, b0), hi = Math.min(a1, b1);
      if (hi - lo <= 1e-6) continue;
      const zm = (lo + hi) / 2, A = material(a, sketchOf(a), zm - a0), B = material(b, sketchOf(b), zm - b0), ar = areaOf(A, B);
      if (ar > 0.05) out.push(`${nameOf(a.id)} × ${nameOf(b.id)}: ${ar.toFixed(2)} mm² overlap (z ${lo.toFixed(1)}–${hi.toFixed(1)})`);
    }
    return out;
  }
  // a rod runs from the bottom of its lowest bearing to the top of whatever it carries; every part it crosses needs a hole there
  function cutBand(d, c) {
    const [z0, z1] = zBand(d), T = z1 - z0, D = c.depth == null ? T : Math.min(T, c.depth);
    const fromTop = (c.from === 'back') !== (d.grow === 'minus');
    return fromTop ? [z1 - D, z1] : [z0, z0 + D];
  }
  function rodChecks() {
    const m = def() || {}, mounts = m.mounts || {}, out = [], RODS = (m.rods || {});
    for (const a of ARBOR_DEFS) {
      const p = S.pos[a.id];
      if (!p) continue;
      const r = (RODS[a.id] != null ? RODS[a.id] : 1.0) / 2;
      let lo = Infinity, hi = -Infinity;
      for (const d of zParts()) for (const c of d.cuts || []) if (c.axis === a.id && c.kind === 'bearing') { const [b0, b1] = cutBand(d, c); lo = Math.min(lo, b0); hi = Math.max(hi, b1); }
      for (const g of a.gears) { const G = D.gears[g.id]; lo = Math.min(lo, G.z0); hi = Math.max(hi, G.z1); }
      for (const h of HAND_DEFS) if (h.arbor === a.id) hi = Math.max(hi, S.hands[h.id].z + S.hands[h.id].t);
      for (const [did, mt] of Object.entries(mounts)) {
        const c = centreOf(did), d = S.drawn.find(x => x.id === did);
        if (d && c && Math.hypot(c[0] - p[0], c[1] - p[1]) < 1e-3 && poly(did) && inside(p, poly(did))) { const [z0, z1] = zBand(d); hi = Math.max(hi, z1); }   // only parts the rod goes through (not a pin set off the axis)
      }
      if (!isFinite(lo)) continue;
      for (const d of zParts()) {
        const [z0, z1] = zBand(d), a0 = Math.max(lo, z0) + 0.05, a1 = Math.min(hi, z1) - 0.05;
        if (a1 <= a0) continue;
        const mt = mounts[d.id], c = centreOf(d.id);
        if (mt && c && Math.hypot(c[0] - p[0], c[1] - p[1]) < 1e-3) continue;   // a part turning on this very axis is carried by the rod
        let worst = 0, at = null;
        for (let z = a0; z <= a1 + 1e-9; z += Math.max(0.25, (a1 - a0) / 12)) {
          const ar = areaOf(material(d, sketchOf(d), z - z0), circlePath(p[0], p[1], r));
          if (ar > worst) { worst = ar; at = z; }
        }
        if (worst > 0.01) out.push(`${esc(a.name)} rod (Ø${(2 * r).toFixed(1)}) passes through solid ${nameOf(d.id)} at z ${at.toFixed(1)}: it needs a hole there`);
      }
    }
    return out;
  }
  // parts drawn on a side plane (stem, crown, winding pinion): slice them into z-layers of rectangles and test those
  // A slanted (d.place) or twisted (d.twist) part is sliced from its real 3D shape: its mesh, as placed and turned right now,
  // cut by level planes every 0.3 mm; each cut's segments are joined into loops (even-odd, so holes stay holes).
  function meshSlices(d) {
    const p = (typeof parts !== 'undefined' ? parts : {})[d.id];
    if (!p || !window.ClipperLib) return [];
    (p.place || p.root).updateWorldMatrix(true, true);
    const T = [], v = new THREE.Vector3();
    p.statics.traverse(o => {
      if (!o.isMesh) return;
      const pos = o.geometry.attributes.position, idx = o.geometry.index, n = idx ? idx.count : pos.count, M = o.matrixWorld;
      const get = i => v.fromBufferAttribute(pos, idx ? idx.getX(i) : i).applyMatrix4(M).toArray();
      for (let i = 0; i + 2 < n; i += 3) T.push([get(i), get(i + 1), get(i + 2)]);
    });
    if (!T.length) return [];
    let z0 = Infinity, z1 = -Infinity;
    for (const t of T) for (const q of t) { z0 = Math.min(z0, q[2]); z1 = Math.max(z1, q[2]); }
    const key = q => `${Math.round(q[0] * 1e4)},${Math.round(q[1] * 1e4)}`;
    const cut = (A, B, z) => { const [a, b] = (A[0] < B[0] || (A[0] === B[0] && A[1] <= B[1])) ? [A, B] : [B, A]; const t = (z - a[2]) / (b[2] - a[2]); return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; };
    const slices = [], C = ClipperLib;
    for (let z = z0 + 0.1 + 1e-5; z < z1; z += 0.3) {
      const segs = [];
      for (const t of T) {
        const pts = [];
        for (let e = 0; e < 3; e++) { const A = t[e], B = t[(e + 1) % 3]; if ((A[2] > z) !== (B[2] > z)) pts.push(cut(A, B, z)); }
        if (pts.length === 2) segs.push(pts);
      }
      if (!segs.length) continue;
      const adj = new Map();
      segs.forEach((sg, i) => { for (const q of sg) { const kq = key(q); if (!adj.has(kq)) adj.set(kq, []); adj.get(kq).push(i); } });
      const used = new Set(), loops = [];
      for (let i = 0; i < segs.length; i++) {
        if (used.has(i)) continue;
        used.add(i); const loop = [segs[i][0], segs[i][1]]; let end = segs[i][1];
        for (let g = 0; g < segs.length; g++) {
          const nx = (adj.get(key(end)) || []).find(j => !used.has(j));
          if (nx == null) break;
          used.add(nx); const sg = segs[nx]; end = key(sg[0]) === key(end) ? sg[1] : sg[0]; loop.push(end);
        }
        if (loop.length >= 4) loops.push(loop);
      }
      const cl = new C.Clipper(), out = new C.Paths();
      cl.AddPaths(loops.map(toClip), C.PolyType.ptSubject, true);
      cl.Execute(C.ClipType.ctUnion, out, C.PolyFillType.pftEvenOdd, C.PolyFillType.pftEvenOdd);
      if (out.length) slices.push({ z, path: out });
    }
    return slices;
  }
  function sideSlices(d) {
    const k = sketchOf(d);
    if (d.place || d.twist) return meshSlices(d);
    if (!k || !k.closed || k.plane.axis === 'z') return [];
    const ax = k.plane.axis, [f0, f1] = faceOffsets(d, k), n0 = Math.min(f0, f1), n1 = Math.max(f0, f1);
    const poly = outlinePoints(k).slice(0, -1).map(q => [q[0], q[1]]), vs = poly.map(q => q[1]);
    const slices = [];
    for (let v = Math.min(...vs) + 0.1; v < Math.max(...vs); v += 0.3) {
      const xs = [];
      for (let i = 0; i < poly.length; i++) { const A = poly[i], B = poly[(i + 1) % poly.length]; if ((A[1] > v) !== (B[1] > v)) xs.push(A[0] + (B[0] - A[0]) * (v - A[1]) / (B[1] - A[1])); }
      xs.sort((x, y) => x - y);
      for (let i = 0; i + 1 < xs.length; i += 2) {
        const [u0, u1] = [xs[i], xs[i + 1]];   // the plane's u runs along model y (x-plane) or model x (y-plane); v is model z
        const rect = ax === 'x' ? [[n0, u0], [n1, u0], [n1, u1], [n0, u1]] : [[u0, n0], [u1, n0], [u1, n1], [u0, n1]];
        slices.push({ z: v, path: [toClip(rect)] });
      }
    }
    return slices;
  }
  function sideChecks() {
    const out = new Map(), els = elements(S, D), m = def() || {}, mounts = m.mounts || {};
    const side = S.drawn.filter(d => { const k = sketchOf(d); return k && k.closed && (k.plane.axis !== 'z' || d.place); });
    for (const sd of side) {
      for (const sl of sideSlices(sd)) {
        for (const d of zParts()) {
          if (mounts[d.id]) continue;
          const [z0, z1] = zBand(d);
          if (sl.z <= z0 || sl.z >= z1) continue;
          const ar = areaOf(sl.path, material(d, sketchOf(d), sl.z - z0));
          if (ar > 0.02) { const key = `${nameOf(sd.id)} × ${nameOf(d.id)}`; out.set(key, Math.max(out.get(key) || 0, ar)); }
        }
        for (const e of els) {
          if (sl.z <= e.z0 || sl.z >= e.z1) continue;
          if ((m.meshes || []).some(x => x.part === sd.id && x.gear === e.gear)) continue;   // a drawn worm meshes this gear (its mesh is proven offline)
          const ar = areaOf(sl.path, circlePath(e.x, e.y, e.r));
          if (ar > 0.02) { const key = `${nameOf(sd.id)} × ${e.name}`; out.set(key, Math.max(out.get(key) || 0, ar)); }
        }
      }
    }
    return [...out.entries()].map(([k, v]) => `${k}: up to ${v.toFixed(2)} mm² in one 0.3 mm slice`);
  }

  // ---------- engraving: ticks, numbers and text printed on a drawn part's top face ----------
  function engrave(part, d, items) {
    const k = sketchOf(d);
    if (!k || !items || !items.length) return;
    const top = Math.max(...faceOffsets(d, k));
    const pts = outlinePoints(k);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of pts) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    const W = x1 - x0, Hh = y1 - y0, px = Math.min(28, 2048 / Math.max(W, Hh));
    const cv = document.createElement('canvas'); cv.width = Math.ceil(W * px); cv.height = Math.ceil(Hh * px);
    const g = cv.getContext('2d');
    const P = (x, y) => [(x - x0) * px, (y1 - y) * px];
    g.strokeStyle = g.fillStyle = '#20262d'; g.lineCap = 'round'; g.textAlign = 'center'; g.textBaseline = 'middle';
    for (const it of items) {
      if (it.kind === 'arc') {
        const n = it.n, [l0, l1] = it.len || [1.5, 3];
        for (let i = 0; i <= n; i++) {
          const a = (it.a0 + (it.a1 - it.a0) * i / n) * DEG, maj = i % it.major === 0, L1 = maj ? l1 : l0;
          const [ax, ay] = P(it.c[0] + it.r * Math.cos(a), it.c[1] + it.r * Math.sin(a)), [bx, by] = P(it.c[0] + (it.r + L1) * Math.cos(a), it.c[1] + (it.r + L1) * Math.sin(a));
          g.lineWidth = (maj ? 0.32 : 0.18) * px; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
        }
        if (it.labels) for (const [i, txt] of Object.entries(it.labels)) {
          const a = (it.a0 + (it.a1 - it.a0) * (+i) / n) * DEG, [x, y] = P(it.c[0] + it.rl * Math.cos(a), it.c[1] + it.rl * Math.sin(a));
          g.save(); g.translate(x, y); g.rotate(-(a - Math.PI / 2)); g.font = `600 ${it.size * px}px Georgia, serif`; g.fillText(txt, 0, 0); g.restore();
        }
      } else if (it.kind === 'text') {
        const [x, y] = P(it.at[0], it.at[1]);
        g.save(); g.translate(x, y); g.rotate(-(it.angle || 0) * DEG); g.font = `${it.weight || 600} ${it.size * px}px Georgia, serif`; g.fillText(it.text, 0, 0); g.restore();
      } else if (it.kind === 'ring') {
        for (let i = 0; i < it.n; i++) {
          const a = (90 - 360 * i / it.n) * DEG, maj = i % it.major === 0, L1 = maj ? it.len[1] : it.len[0];
          const [ax, ay] = P(it.c[0] + it.r * Math.cos(a), it.c[1] + it.r * Math.sin(a)), [bx, by] = P(it.c[0] + (it.r - L1) * Math.cos(a), it.c[1] + (it.r - L1) * Math.sin(a));
          g.lineWidth = (maj ? 0.28 : 0.15) * px; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
        }
      }
    }
    const tex = new THREE.CanvasTexture(cv); tex.anisotropy = 4;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(W, Hh), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
    mesh.position.set((x0 + x1) / 2, (y0 + y1) / 2, top + 0.03);
    mesh.userData.part = part.id;
    mesh.raycast = () => {};   // the printing's transparent sheet covers the part's whole bounding box: clicks go through it to the real surface
    part.statics.add(mesh);
  }

  // ---------- keeping the scene in step: mounts, engravings, springs ----------
  const done = {};
  Mech.sync = function () {
    const m = def();
    if (!m) { Mech.checksDrawn = false; return; }
    const eng = (PROJECT.decor && PROJECT.decor.engrave) || {};
    for (const d of S.drawn) {
      const p = parts[d.id];
      if (!p) continue;
      if (done[d.id] === p.key) continue;
      done[d.id] = p.key;
      const c = centreOf(d.id);
      if (c) {
        p.root.position.set(c[0], c[1], 0);
        p.statics.position.set(-c[0], -c[1], 0);
        p.anchorLocal.x -= c[0]; p.anchorLocal.y -= c[1];
      }
      const mx = mountOf(d.id);
      if (mx && mx.axisX) {   // a side part turning about a line along model x (a stem, its pinion, the crown) through [y, z]
        p.root.position.set(0, mx.axisX[0], mx.axisX[1]);
        p.statics.position.set(0, -mx.axisX[0], -mx.axisX[1]);
        p.anchorLocal.y -= mx.axisX[0]; p.anchorLocal.z -= mx.axisX[1];
      }
      if (mx && mx.axisY) {   // the same along model y, through [x, z] (a stem lying along y, its worm, the crown)
        p.root.position.set(mx.axisY[0], 0, mx.axisY[1]);
        p.statics.position.set(-mx.axisY[0], 0, -mx.axisY[1]);
        p.anchorLocal.x -= mx.axisY[0]; p.anchorLocal.z -= mx.axisY[1];
      }
      if (eng[d.id]) engrave(p, d, eng[d.id]);
    }
    // the project's own colours (materials, not states): applied once to each part's base material
    const cols = (PROJECT.decor && PROJECT.decor.colors) || {};
    for (const id of partOrder) {
      const p = parts[id], c = cols[id] != null ? cols[id] : cols['group:' + p.group];
      if (c == null || p._mechColor === c) continue;
      const hex = typeof c === 'string' ? parseInt(c.replace('#', ''), 16) : c;
      p.mat.color.setHex(hex); p.mat.userData.baseColor = hex; p.color = hex; p._mechColor = c;
    }
    // Checks never run on an edit: the designer edits freely, and the checks (all the clash tests and the 12-hour sweep, several
    // seconds) run only when asked (Run checks in the Checks panel). The motion itself is swept once when the project opens.
    if (!Mech.sweep) { for (const so of m.solve) delete so._dir; runSweep(); live = null; }
    const sig = shapeSig();
    if (sig !== Mech._sig) { Mech._sig = sig; if (Mech.checksDrawn) { Mech.checksDrawn = false; Mech.stale = true; } }
  };
  function shapeSig() {   // changes whenever a drawn part is rebuilt or a wheel moves (cheap: the parts' own rebuild keys)
    return S.drawn.map(d => (parts[d.id] && parts[d.id].key) || '').join('|') + JSON.stringify([S.pos, S.stages, S.solo, S.hands]);
  }
  Mech.runChecks = function () {   // every check, on the shapes as they are now
    const m = def();
    if (!m) return;
    const t0 = performance.now();
    CACHE = { mat: new Map(), placed: new Map() };
    for (const so of m.solve) delete so._dir;
    runSweep();
    Mech.staticClashes = staticClashes();
    Mech.partClashes = fixedVsFixed();
    Mech.millFaces = millFaces();
    Mech.rodClashes = rodChecks();
    Mech.sideClashes = sideChecks();
    Mech.escapement = escapementCheck();
    Mech.sweep.clashes = movingClashes(Mech.sweep.table);
    Mech.sweep.reading = readsTime(Mech.sweep.table, Mech.sweep.DT);
    Mech.checksDrawn = true; Mech.stale = false; Mech._sig = shapeSig();
    Mech.lastRun = { at: new Date(), ms: Math.round(performance.now() - t0) };
    live = null;
  };
  const wires = {};
  function drawSprings(s) {
    const m = def();
    for (const sp of m.springs || []) {
      const mt = mountOf(sp.to.part), ang = mt && mt.angle ? (s.a[mt.angle] || 0) : 0, c = centreOf(sp.to.part) || [0, 0];
      const end = rot(sp.to.at, c, ang * DEG), st0 = sp.from;
      const key = end.map(v => v.toFixed(3)).join();
      let w = wires[sp.id];
      if (w && w.key === key) continue;
      if (w) { world.remove(w.mesh); w.mesh.geometry.dispose(); }
      const mid = [(st0[0] + end[0]) / 2, (st0[1] + end[1]) / 2], dx = end[0] - st0[0], dy = end[1] - st0[1], L0 = Math.hypot(dx, dy) || 1;
      const bow = [mid[0] - dy / L0 * L0 * 0.12, mid[1] + dx / L0 * L0 * 0.12];
      const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(st0[0], st0[1], sp.z), new THREE.Vector3(bow[0], bow[1], sp.z), new THREE.Vector3(end[0], end[1], sp.z));
      const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, sp.r || 0.25, 8, false), new THREE.MeshStandardMaterial({ color: 0xd9dee4, metalness: 0.7, roughness: 0.3 }));
      world.add(mesh);
      wires[sp.id] = { mesh, key };
    }
  }
  // each frame: solve from the last moment, or jump in from the sweep table if time moved far
  Mech.frame = function (te) {
    const m = def();
    if (!m || !Mech.sweep) return;
    const sw = Mech.sweep, period = 12 * 3600;
    const tm = ((te % period) + period) % period;
    if (!live || liveT == null || tm < liveT || tm - liveT > 120) {
      const row = sw.table[Math.max(0, Math.min(sw.table.length - 1, Math.floor(tm / sw.DT)))];
      live = fresh(); live.a = Object.assign({}, row.a); live.sig = row.sig; live.k = row.k; liveT = row.te;
    }
    if (tm > liveT) { step(live, tm); liveT = tm; }
    for (const [did, mt] of Object.entries(m.mounts || {})) {
      const p = parts[did];
      if (!p) continue;
      if (mt.axisX) { p.root.rotation.x = (mt.ratio || 1) * axisAngle(mt.from, te, live) * DEG + (mt.phase || 0) * DEG; continue; }
      if (mt.axisY) { p.root.rotation.y = (mt.ratio || 1) * axisAngle(mt.from, te, live) * DEG + (mt.phase || 0) * DEG; continue; }
      p.root.rotation.z = (mt.axis ? axisAngle(mt.axis, te, live) : (live.a[mt.angle] || 0)) * DEG;
    }
    for (const l of m.links || []) {
      const ang = linkAngle(l, te, live);
      if (parts[l.arbor]) parts[l.arbor].spin.rotation.z = ang * DEG;
      for (const h of HAND_DEFS) if (h.arbor === l.arbor) parts[h.id].spin.rotation.z = ang * DEG;
    }
    drawSprings(live);
  };

  // ---------- what the Checks panel says ----------
  const clock = te => { const h = Math.floor(te / 3600), mm = Math.floor((te % 3600) / 60), ss = Math.round(te % 60); return `${h}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`; };
  Mech.report = function () {
    const m = def(), sw = Mech.sweep, items = [];
    if (!m || !sw) return items;
    const ex = m.expect || {};
    const lever = m.solve.find(x => x.kind === 'follower');
    const gaps = sw.flybacks.slice(1).map((t, i) => t - sw.flybacks[i]);
    const regular = gaps.length && gaps.every(g => Math.abs(g - (ex.flyback_every || 3600)) <= sw.DT * 2);
    items.push([sw.flybacks.length >= sw.hours && regular ? 'ok' : 'err', `<b>Retrograde minute</b> (12-hour sweep, every ${sw.DT} s): the lever rides the snail and flies back ${sw.flybacks.length} times, ${regular ? `once every hour (first at ${clock(sw.flybacks[0])})` : 'not evenly'}` +
      (sw.handSweep != null ? `; the hand sweeps ${sw.handSweep.toFixed(1)}° (track ${(ex.hand_sweep || 0).toFixed(1)}°)` : '') + (lever ? `; lever range ${sw.ranges[lever.id][0].toFixed(1)}° to ${sw.ranges[lever.id][1].toFixed(1)}°` : '')]);
    if (sw.rat) {
      const pushes = sw.jumps.map(j => j.push);
      const ok = sw.jumps.length === (ex.hour_steps || 12) && !sw.fails.length;
      items.push([ok ? 'ok' : 'err', `<b>Jumping hour</b>: the pawl kicked the star ${sw.jumps.length} times in 12 hours${sw.fails.length ? `, ${sw.fails.length} kicks too short to pass the jumper` : ''}` +
        (pushes.length ? `; each push ${Math.min(...pushes).toFixed(1)}°–${Math.max(...pushes).toFixed(1)}° (the jumper's peak is at ${sw.rat.apex}°, the next seat at ${sw.rat.pitch}°, so the jumper snaps it home)` : '')]);
      items.push([sw.flex <= (ex.pawl_flex_max || 3) ? 'ok' : 'warn', `<b>Pawl</b>: rides back over one ratchet tooth each hour, lifting ${sw.flex.toFixed(2)} mm on its flexure (allowed ${ex.pawl_flex_max || 3} mm)`]);
    }
    const others = m.solve.filter(x => x.kind === 'follower' && x !== lever);
    if (others.length) items.push(['info', `<b>Springs on their cams</b><div class="mono">${others.map(f => `${esc(f.label || f.id)}: swings ${(sw.ranges[f.id][1] - sw.ranges[f.id][0]).toFixed(1)}° (${sw.ranges[f.id][0].toFixed(1)}° to ${sw.ranges[f.id][1].toFixed(1)}°)`).join('<br>')}</div>`]);
    items.push([Mech.staticClashes.length ? 'err' : 'ok', Mech.staticClashes.length
      ? `<b>Drawn parts clash with wheels</b><div class="mono">${Mech.staticClashes.map(esc).join('<br>')}</div>`
      : `<b>Drawn parts</b>: none of the ${S.drawn.length} plates, bridges and mechanism parts cuts into a wheel's space (with the ${S.minGap} mm gap)`]);
    const pc = Mech.partClashes || [], rc = Mech.rodClashes || [], sc = Mech.sideClashes || [];
    items.push([pc.length ? 'err' : 'ok', pc.length ? `<b>Parts overlap each other</b><div class="mono">${pc.map(esc).join('<br>')}</div>` : `<b>Parts against parts</b>: no two plates, bridges or cocks overlap`]);
    items.push([rc.length ? 'err' : 'ok', rc.length ? `<b>Rods through solid material</b><div class="mono">${rc.join('<br>')}</div>` : `<b>Rods</b>: every arbor's rod, from its lowest bearing to the top of what it carries, passes through a hole in every part it crosses`]);
    items.push([sc.length ? 'err' : 'ok', sc.length ? `<b>Side-on parts clash</b> (stem, crown, winding pinion)<div class="mono">${sc.map(esc).join('<br>')}</div>` : `<b>Side-on parts</b>: the stem, crown and winding pinion clear the plates, wheels and rods`]);
    const mf = Mech.millFaces;
    if (mf) { const bad = [...mf.two, ...mf.wrong]; items.push([bad.length ? 'err' : 'ok', bad.length ? `<b>Parts that need milling from both faces</b><div class="mono">${bad.map(esc).join('<br>')}</div>`
      : `<b>One face each</b>: every flat part is milled from one face on a 3-axis machine (${mf.tops} from the top, ${mf.bottoms} from the bottom, ${mf.either} cut right through); countersinks on the other face are drilled by hand`]); }
    items.push([sw.clashes.length ? 'err' : 'ok', sw.clashes.length
      ? `<b>Moving parts clash</b> somewhere in the 12 hours<div class="mono">${sw.clashes.map(esc).join('<br>')}</div>`
      : `<b>Moving parts</b>: the snail, lever, ratchet, star, jumper, click, fork and roller stay clear of every other part through the 12 hours (where a nose, pawl or click is meant to touch, only 1.2 mm round the touching point is let off; a pin in a closed slot or hole counts as clear)`]);
    for (const pr of m.proofs || []) items.push([pr.ok ? 'ok' : 'err', `<b>${esc(pr.label)}</b> <small>(proven in ${esc(pr.by)})</small>: ${esc(pr.text)}`]);
    const ec = Mech.escapement;
    if (ec && ec.links.length) {
      const pairs = [...ec.pairs.entries()];
      items.push([pairs.length ? 'err' : 'ok', pairs.length
        ? `<b>Escapement parts cut into each other</b> (one tooth in ${ec.steps} steps)<div class="mono">${pairs.map(([k, v]) => `${esc(k)}: up to ${v.toFixed(3)} mm²`).join('<br>')}</div>`
        : `<b>Escapement</b>: over one tooth of the escape wheel in ${ec.steps} steps, the fork rides the teeth without cutting into them, its ring clears the balance staff and the impulse pin stays inside the roller's slot (largest overlap ${ec.worst.toFixed(3)} mm², touching counts as 0)`]);
    }
    const rt = sw.reading;
    if (rt) {
      const mOk = !rt.minute || (Math.abs(rt.minute.worst) <= 0.25 && rt.minute.rollS <= 60 && rt.minute.rollDeg <= 3), hOk = !rt.hour || rt.hour.wrong === 0, sOk = !rt.seconds || rt.seconds.worst < 0.05;
      const bits = [];
      if (rt.minute) bits.push(`minute hand within ${(Math.abs(rt.minute.worst) * 60).toFixed(1)} s of the true time on the crescent's evenly divided track (worst at ${clock(rt.minute.at)}, ${rt.minute.worst >= 0 ? 'ahead' : 'behind'})` +
        (rt.minute.rollS ? `, except the last ${rt.minute.rollS} s before each hour, where the feeler rolls over the snail's edge and the hand eases back ${rt.minute.rollDeg.toFixed(1)}° before it flies back` : ''));
      if (rt.hour) bits.push(rt.hour.wrong ? `the hour star shows the wrong hour ${rt.hour.wrong} times (first at ${clock(rt.hour.firstWrong.te)}: ${rt.hour.firstWrong.shows} instead of ${rt.hour.firstWrong.should})` : `the hour star shows the right hour under the index all 12 hours (seated within ${rt.hour.seat.toFixed(1)}°)`);
      if (rt.seconds) bits.push(sOk ? 'the seconds hand reads exactly' : `the seconds hand is off by up to ${rt.seconds.worst.toFixed(2)} s`);
      items.push([mOk && hOk && sOk ? 'ok' : 'err', `<b>Reads the time</b> (12 hours, every ${sw.DT} s, read the way a person would): ${bits.join('; ')}`]);
    }
    items.push(['info', 'Kinematics only: shapes, contact, timing and ranges are checked. Forces, spring stiffness and wear are not.']);
    return items;
  };
})();
// The page's first solve ran before this file loaded: ask for another so the mounts, engravings and checks appear.
if (typeof requestSolve === 'function') requestSolve();
