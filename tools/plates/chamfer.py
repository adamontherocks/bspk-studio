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
