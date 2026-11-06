// Involute spur gear outline shared by the sim pages.
// gear.html's CadQuery export template repeats this construction in Python; keep the two in step.
(function (root) {
  'use strict';
  const N_FLANK = 10, N_TIP = 3, N_VALLEY = 4;

  function computeGear(s) {
    const m = s.module, z = Math.round(s.teeth), pa = s.pressure_angle * Math.PI / 180;
    const rp = m * z / 2, rb = rp * Math.cos(pa), ra = rp + m, rf = rp - 1.25 * m;
    const half = Math.PI / (2 * z) + (Math.tan(pa) - pa);
    const t0 = rf > rb ? Math.sqrt((rf / rb) ** 2 - 1) : 0;
    const t1 = Math.sqrt((ra / rb) ** 2 - 1);
    const flank = [];
    for (let i = 0; i <= N_FLANK; i++) {
      const t = t0 + (t1 - t0) * i / N_FLANK;
      flank.push([rb * Math.sqrt(1 + t * t), -half + t - Math.atan(t)]);
    }
    const tipHalf = -flank[N_FLANK][1];
    const rootHalf = rf < rb ? half : -flank[0][1];
    const step = 2 * Math.PI / z;
    return { m, z, pa, rp, rb, ra, rf, half, flank, tipHalf, rootHalf, step,
             pointed: tipHalf <= 0, crowded: step - 2 * rootHalf <= 0 };
  }

  function outline(g) {
    const P = (r, a) => [r * Math.cos(a), r * Math.sin(a)];
    const pts = [];
    for (let i = 0; i < g.z; i++) {
      const a = i * g.step;
      if (g.rf < g.rb) pts.push(P(g.rf, a - g.half));
      for (const [r, ang] of g.flank) pts.push(P(r, a + ang));
      for (let j = 1; j < N_TIP; j++) pts.push(P(g.ra, a - g.tipHalf + 2 * g.tipHalf * j / N_TIP));
      for (let k = g.flank.length - 1; k >= 0; k--) pts.push(P(g.flank[k][0], a - g.flank[k][1]));
      if (g.rf < g.rb) pts.push(P(g.rf, a + g.half));
      const v0 = a + g.rootHalf, v1 = a + g.step - g.rootHalf;
      for (let j = 1; j < N_VALLEY; j++) pts.push(P(g.rf, v0 + (v1 - v0) * j / N_VALLEY));
    }
    return pts;
  }

  function polygonArea(pts) {
    let s = 0;
    for (let i = 0; i < pts.length; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
      s += x0 * y1 - x1 * y0;
    }
    return Math.abs(s) / 2;
  }

  root.Involute = { N_FLANK, N_TIP, N_VALLEY, computeGear, outline, polygonArea };
})(window);
