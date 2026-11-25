# Chamfers for the exporters (2026-11-25): the sim's 45° rim chamfers, cut as the sim draws them (sim/index.html, chamferLoop and
# chamferFeats). A chamfer sits on a cut's rim (cut['chamfer'], its width = its depth) or on a part's outline (d['chamfer'] =
# {face, size}): the opening grows by the chamfer at the top and the wall slopes in to the drawn outline that far down, starting where
# the cut meets material (the face, or the floor of a cut it sits in). Corners are mitred (sharp), as V-carving leaves them.
# Solids: a ruled loft between the outline and its mitred offset, vertex for vertex, so every face is a flat trapezoid (a drafted
# extrude of a many-sided outline meshed with cracks, 2026-11-25). It starts a little lower and inside, on the same 45°, so its foot
# crosses the wall below instead of lying on it.
import math

def area(p): return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2

def _x(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1]); s = (d[0] - c[0], d[1] - c[1]); den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12: return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    return (a[0] + t * r[0], a[1] + t * r[1])

def _offset(p, dist):
    n = len(p); N = []
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        N.append(((b[1] - a[1]) / L, -(b[0] - a[0]) / L))          # right-hand normals: toward the material
    out = []
    for i, v in enumerate(p):
        n1, n2 = N[i - 1], N[i]; k = max(0.05, 1 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((v[0] + dist * (n1[0] + n2[0]) / k, v[1] + dist * (n1[1] + n2[1]) / k))
    return out

def loop(path, c, removed_inside=True, min_edge=0.1, inner=0.0):
    """the outline turned so the removed side is on its left, short edges and straight-through points dropped, edges that would turn
    round folded away; returns (p, offsets) with offsets[d] for each distance d in (-inner, c) (the same vertices)"""
    p = []
    for q in path:
        q = (float(q[0]), float(q[1]))
        if not p or math.dist(q, p[-1]) > min_edge: p.append(q)
    while len(p) > 2 and math.dist(p[0], p[-1]) <= min_edge: p.pop()
    if len(p) < 3: return None
    if (area(p) > 0) != removed_inside: p.reverse()
    for _ in range(400):
        n = len(p)
        if n < 3: return None
        st = next((i for i in range(n) if abs((p[i][0] - p[i - 1][0]) * (p[(i + 1) % n][1] - p[i][1]) - (p[i][1] - p[i - 1][1]) * (p[(i + 1) % n][0] - p[i][0])) < 1e-9
                   and (p[i][0] - p[i - 1][0]) * (p[(i + 1) % n][0] - p[i][0]) + (p[i][1] - p[i - 1][1]) * (p[(i + 1) % n][1] - p[i][1]) > 0), None)
        if st is not None: p.pop(st); continue
        bad = None
        for dist in (c, -inner):
            if not dist: continue
            o = _offset(p, dist)
            for i in range(n):
                j = (i + 1) % n
                if (p[j][0] - p[i][0]) * (o[j][0] - o[i][0]) + (p[j][1] - p[i][1]) * (o[j][1] - o[i][1]) <= 0: bad = i; break
            if bad is not None: break
        if bad is None: return p, {c: _offset(p, c), -inner: _offset(p, -inner) if inner else p}
        i, j = bad, (bad + 1) % n
        X = _x(p[i - 1], p[i], p[j], p[(j + 1) % n]) or ((p[i][0] + p[j][0]) / 2, (p[i][1] + p[j][1]) / 2)
        p = [X if m == i else v for m, v in enumerate(p) if m != j]
    return None

def bevel(path, c, z_face, into, z0=0.0, removed_inside=True, under=0.05, E=0.01):
    """the solid a chamfer takes out, as a loft op {'kind': 'loft', 'w0', 'w1'}: z_face is the face's z, into (+1/-1) the way into
    the part, z0 how far below the face it starts. From the outline `under` inside at depth z0 + c + under up to the outline grown
    by c + E at depth z0 - E: 45° all the way."""
    r = loop(path, c + E, removed_inside, inner=under)
    if not r: return None
    p, o = r
    zA = z_face + into * (z0 + c + under); zB = z_face + into * (z0 - E)
    return {'kind': 'loft', 'w0': [[x, y, zA] for x, y in o[-under]], 'w1': [[x, y, zB] for x, y in o[c + E]]}

def width_of(ch):
    """a part's edge chamfer's width for an edge facing `deg` degrees (as the sim's chamferWidthOf): ch['widths'] = [[deg, w], ...]
    round the compass, read between; else ch['size']"""
    t = sorted([((float(a) % 360 + 360) % 360, max(0.0, float(w))) for a, w in (ch.get('widths') or [])])
    if not t: return lambda deg: float(ch.get('size') or 0)
    def f(deg):
        a = (deg % 360 + 360) % 360
        for (d0, w0), (d1, w1) in zip(t, t[1:] + [(t[0][0] + 360, t[0][1])]):
            aa = a + 360 if a < d0 and d0 == t[0][0] else a
            if d0 - 1e-9 <= aa <= d1 + 1e-9: return w0 if d1 - d0 < 1e-9 else w0 + (w1 - w0) * (aa - d0) / (d1 - d0)
        return t[0][1]
    return f

def edge_wedges(outline, ch, z_face, into, E=0.01):
    """a part's edge chamfer (any angle, widths by side) as one wedge per edge, each the half-space above that face's chamfer plane,
    run on past the edge's ends: cut together they leave the faces meeting in true ridges. Ops {'kind': 'pprism', 'pts', 'vec'}."""
    tan = math.tan(math.radians(ch.get('angle') or 45.0)); wof = width_of(ch)
    p = [(float(x), float(y)) for x, y in outline]
    if len(p) > 48:                     # a curved outline: its arcs as chords within 5 µm, so it isn't hundreds of wedges (each its own face)
        from shapely.geometry import Polygon as _P
        p = [tuple(q) for q in _P(p).buffer(0).simplify(0.005).exterior.coords[:-1]]
    if area(p) < 0: p.reverse()                                  # anticlockwise: outward normals on the right
    ops = []; wmax = max([wof(a) for a in range(0, 360, 5)] + [0.0]); span = 2 * wmax + 1.0   # (run on past each end far enough to meet its neighbours, no further)
    for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1e-9: continue
        tx, ty = (x1 - x0) / L, (y1 - y0) / L; nx, ny = ty, -tx       # outward
        w = wof(math.degrees(math.atan2(ny, nx)))
        if w <= 1e-6: continue
        X = 2.0 + w; up = 1.0
        # the section across the edge (s: out from the deck line, h: up from the face, signed into the part): along the chamfer plane
        # from just inside the deck line out past the outline, then up and back
        sec = [(-0.02, 0.02 * tan), (w + X, -(w + X) * tan), (w + X, up), (-0.02, up)]
        bx, by = x0 - nx * w - tx * span, y0 - ny * w - ty * span        # the deck line, run back past the edge's start
        pts = [[bx + nx * s_, by + ny * s_, z_face - into * h] for s_, h in sec]
        ops.append({'kind': 'pprism', 'pts': pts, 'vec': [tx * 2 * span + tx * L, ty * 2 * span + ty * L, 0.0]})
    return ops
