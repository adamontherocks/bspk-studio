# Fit rings of dots as true arcs and straight lines (generic; numpy, scipy, shapely: system python). VISION.md §7, R7: the solid
# modeller crawls through walls made of thousands of tiny segments; the same walls as a few hundred arcs and lines build in seconds.
#
# Every dot stays within TOL of the fitted curve, and every piece starts and ends on one of the ring's own dots (an arc passes
# through three of them), so pieces meet exactly. Several rings that share a stretch of wall (the floor bands of one plate: one
# wall across heights) get the identical curve there: each ring is cut at ANCHORS, the dots where the rings part ways, and each
# stretch between two anchors is fitted once, by its dots alone, and reused wherever it appears. Slabs fitted this way still
# meet exactly at their shared walls.
#   fit_faces(faces) -> fitted faces, each ring {'start': [x, y], 'segs': [['L', [x, y]] | ['A', [mid x, mid y], [x, y]], ...]}
#   (unify(rings) first, for rings that share walls)
import math
import numpy as np

TOL = 0.002              # mm: every dot within 2 µm of the fitted curve (the model's grid is 0.1 µm; the machine holds ~10 µm)
MAX_SWEEP = math.pi / 2  # an arc turns at most 90° (a full circle is four or more arcs; keeps every arc well conditioned)
SAG = 0.005              # mm: between two neighbouring dots an arc may stand off their straight segment at most 5 µm. Dots alone don't
                         # pin an arc down: any three lie on some circle, and three dots across a 43 mm straight side once made an arc
                         # bowing 0.2 mm (D29, 2026-11-22). The sim's own circles sag at most 3.3 µm between dots.

def _circle(a, b, c):
    """centre and radius of the circle through three dots, or None if they are (nearly) in line"""
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12: return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)

CLEAR = 3                # where the wall comes back near itself (a spike, a hook: the resolver leaves a few, µm wide), each dot's
                         # tolerance is at most a third of that gap, or the pieces on its two sides cross (D19, D26, D31: 2026-11-22)

def _clearance(P, reach):
    """for each dot, how near the chain comes to it elsewhere (not along its own stretch: the arc length between is over CLEAR times
    the gap), and for each segment, how near it passes to a dot elsewhere; inf where nothing comes within reach"""
    from scipy.spatial import cKDTree
    n = len(P); seg = np.diff(P, axis=0); L = np.hypot(*seg.T); s = np.concatenate([[0.0], np.cumsum(L)]); tot = s[-1]
    closed = n > 3 and bool(np.all(P[0] == P[-1]))
    m = np.maximum(1, np.ceil(L / reach)).astype(int); rep = np.repeat(np.arange(n - 1), m)
    f0 = np.concatenate([np.arange(k) / k for k in m]); f1 = np.concatenate([np.arange(1, k + 1) / k for k in m])
    A = P[rep] + seg[rep] * f0[:, None]; B = P[rep] + seg[rep] * f1[:, None]; sA = s[rep] + L[rep] * f0
    kk = min(24, len(A)); r = float((L[rep] * (f1 - f0)).max()) / 2 + reach
    _, idx = cKDTree((A + B) / 2).query(P, kk, distance_upper_bound=r); idx = idx.reshape(n, kk)
    ok = idx < len(A); idx = np.where(ok, idx, 0)
    a, b = A[idx], B[idx]; v = b - a; l2 = (v * v).sum(2); l2[l2 == 0] = 1e-18
    t = np.clip(((P[:, None, :] - a) * v).sum(2) / l2, 0, 1); q = a + t[..., None] * v
    d = np.hypot(q[..., 0] - P[:, None, 0], q[..., 1] - P[:, None, 1])
    g = np.abs(sA[idx] + t * np.sqrt(l2) - s[:, None])
    if closed: g = np.minimum(g, tot - g)
    far = ok & (g > CLEAR * d + 1e-9) & (d <= reach)
    dd = np.where(far, d, np.inf); j = dd.argmin(1); clr = dd[np.arange(n), j]
    sclr = np.full(n - 1, np.inf); hit = np.isfinite(clr)                      # a segment that passes near a dot elsewhere is tight too
    np.minimum.at(sclr, rep[idx[np.arange(n), j]][hit], clr[hit])
    return clr, sclr

def _line_ok(P, i, j, lim):
    a, b = P[i], P[j]; v = b - a; L = float(np.hypot(*v))
    if L < 1e-9: return False
    Q = P[i + 1:j] - a
    if not len(Q): return True
    t = (Q @ v) / (L * L)
    if (t < -1e-9).any() or (t > 1 + 1e-9).any(): return False                  # dots must run along the line, not double back
    return bool((np.abs(Q[:, 0] * v[1] - Q[:, 1] * v[0]) / L <= lim[i + 1:j]).all())

def _arc(P, i, j, lim, slim):
    """the arc through P[i], a middle dot and P[j] if every dot between lies on it (in order, each within its limit), else None"""
    if j - i < 2: return None
    m = (i + j) // 2
    c = _circle(P[i], P[m], P[j])
    if c is None: return None
    (ux, uy), R = c
    if R > 1e4: return None                                                     # nearly straight: a line will do
    Q = P[i:j + 1]
    if (np.abs(np.hypot(Q[:, 0] - ux, Q[:, 1] - uy) - R) > lim[i:j + 1]).any(): return None
    ccw = (P[m][0] - P[i][0]) * (P[j][1] - P[i][1]) - (P[m][1] - P[i][1]) * (P[j][0] - P[i][0]) > 0
    th = np.arctan2(Q[:, 1] - uy, Q[:, 0] - ux); th = (th - th[0]) if ccw else (th[0] - th)
    th = np.mod(th, 2 * math.pi); th[0] = 0.0
    if th[-1] > MAX_SWEEP or (np.diff(th) < -1e-9).any(): return None             # in order along the arc, and not too far round
    c = np.hypot(*np.diff(Q, axis=0).T)
    if (c * c / (8 * R) > slim[i:j]).any(): return None                          # the arc keeps to the dots' own segments
    return m

def fit_chain(P, tol=TOL, raw=False):
    """one open run of dots (first and last kept exactly) -> pieces, greedily as long as each can be. raw: every segment as it is"""
    P = np.asarray(P, float); n = len(P); out = []; i = 0
    if raw or n < 3: return [['L', [float(x), float(y)]] for x, y in P[1:]]
    clr, sclr = _clearance(P, CLEAR * max(tol, SAG))
    near = np.minimum(clr, np.minimum(np.concatenate([[np.inf], sclr]), np.concatenate([sclr, [np.inf]])))   # a dot and its two segments
    lim = np.minimum(tol, near / CLEAR); slim = np.minimum(SAG, np.minimum(np.minimum(near[:-1], near[1:]), sclr) / CLEAR)
    while i < n - 1:
        best = (i + 1, None)                                                    # one segment always fits as a line
        for kind in ('L', 'A'):
            ok = (lambda j: _line_ok(P, i, j, lim)) if kind == 'L' else (lambda j: _arc(P, i, j, lim, slim) is not None)
            lo, step = i + 1, 2
            hi = None
            while True:                                                         # gallop out, then bisect back
                j = min(n - 1, i + step)
                if ok(j):
                    lo = j
                    if j == n - 1: break
                    step *= 2
                else: hi = j; break
            if hi is not None:
                while hi - lo > 1:
                    mid = (lo + hi) // 2
                    if ok(mid): lo = mid
                    else: hi = mid
            if lo > best[0]: best = (lo, kind)                                  # a tie stays a line
        j, kind = best
        if kind == 'A':
            m = _arc(P, i, j, lim, slim); out.append(['A', [float(P[m][0]), float(P[m][1])], [float(P[j][0]), float(P[j][1])]])
        else:
            out.append(['L', [float(P[j][0]), float(P[j][1])]])
        i = j
    return out

EPS = 0.001    # mm: dots of different rings closer than 1 µm are the same wall. Measured 2026-11-22 on two plates: 99% of the dots on
               # a shared wall sit within 0.2 µm of the other ring's wall and nearly all the rest within 1 µm; past that only a thin
               # spread out to 12 µm, where walls really converge (tapers), which stay as drawn.

SNAP = 0.006   # mm: a dot within 6 µm of an earlier ring's wall goes onto it (the resolver's own rule, onewall.GRADE). Between 1 and
               # 12 µm the walls of two floors run side by side for a short way where a taper ends; left apart, the floor between them
               # is a µm sliver whose edges cross once the solid is read back at the usual tolerance (D3's floor at 17.1, 2026-11-22).

def snap(rings, eps=SNAP, piece=0.2, k=16):
    """each ring's dots within eps of an earlier ring's wall are moved onto that wall (to the nearest point on it). Walls only move
    onto other walls, never zigzag: a taper now ends where its gap reaches eps, with a kink no bigger than eps. (The earlier walls are
    searched in pieces no longer than `piece`, the k nearest for each dot.)"""
    from scipy.spatial import cKDTree
    R = [np.asarray(r, float).copy() for r in rings]
    for i in range(1, len(R)):
        A0 = np.vstack(R[:i]); B0 = np.vstack([np.roll(r, -1, 0) for r in R[:i]])
        n = np.maximum(1, np.ceil(np.hypot(*(B0 - A0).T) / piece)).astype(int)
        f0 = np.concatenate([np.arange(m) / m for m in n]); f1 = np.concatenate([np.arange(1, m + 1) / m for m in n])
        rep = np.repeat(np.arange(len(A0)), n); a0, b0 = A0[rep], B0[rep]
        A = a0 + (b0 - a0) * f0[:, None]; B = a0 + (b0 - a0) * f1[:, None]
        P = R[i]; kk = min(k, len(A))
        _, idx = cKDTree((A + B) / 2).query(P, kk)
        idx = idx.reshape(len(P), kk)
        a, b = A[idx], B[idx]; v = b - a; l2 = (v * v).sum(2); l2[l2 == 0] = 1e-18
        t = np.clip(((P[:, None, :] - a) * v).sum(2) / l2, 0, 1); q = a + t[..., None] * v
        dd = np.hypot(q[..., 0] - P[:, None, 0], q[..., 1] - P[:, None, 1]); j = dd.argmin(1)
        near = dd[np.arange(len(P)), j] <= eps
        P = P.copy(); P[near] = q[np.arange(len(P)), j][near]
        P = np.round(P, 4); keep = np.any(P != np.roll(P, 1, 0), axis=1); R[i] = P[keep]
    return [r.tolist() for r in R]

def unify(rings, eps=EPS, passes=3):
    """snap, then unify_once until nothing changes (a dot put into one ring can bring a third ring's wall within reach)"""
    rings = snap(rings)
    for _ in range(passes):
        new = unify_once(rings, eps)
        if new == rings: break
        rings = new
    return rings

def unify_once(rings, eps=EPS):
    """rings that share a wall to within eps get the same dots along it: a dot near another ring's dot takes that dot's place, and
    a dot near another ring's segment is put into it. Shared walls are then dot for dot the same, so fit_rings fits them alike.
    (Each ring was thinned to 0.1 µm on its own, keeping different dots along the same wall.)"""
    from scipy.spatial import cKDTree
    R = [np.asarray(r, float) for r in rings]
    if not R: return []
    D = np.vstack(R); owner = np.concatenate([np.full(len(r), i) for i, r in enumerate(R)])
    tree = cKDTree(D)
    rep = np.arange(len(D))                                                     # each dot's stand-in: the first dot near it
    for a, b in sorted(tree.query_pairs(eps)):
        ra, rb = rep[a], rep[b]
        while rep[ra] != ra: ra = rep[ra]
        while rep[rb] != rb: rb = rep[rb]
        if ra != rb: rep[max(ra, rb)] = min(ra, rb)
    for i in range(len(rep)):
        r = i
        while rep[r] != r: r = rep[r]
        rep[i] = r
    D = D[rep]
    out, base = [], 0
    for i, r in enumerate(R):
        n = len(r); P = D[base:base + n]; base += n
        ring = []
        for k in range(n):
            p, q = P[k], P[(k + 1) % n]; ring.append(p)
            v = q - p; L = float(np.hypot(*v))
            if L < 1e-9: continue
            near = tree.query_ball_point((p + q) / 2, L / 2 + eps)
            ins = []
            for j in near:
                if owner[j] == i: continue
                w = D[j] - p; t = float(w @ v) / (L * L)
                if t <= 1e-6 or t >= 1 - 1e-6: continue
                if abs(w[0] * v[1] - w[1] * v[0]) / L <= eps: ins.append((t, j))
            seen = set()
            for t, j in sorted(ins):
                key = (round(D[j][0], 4), round(D[j][1], 4))
                if key not in seen: seen.add(key); ring.append(D[j])
        ring = np.round(np.array(ring), 4)
        keep = np.any(ring != np.roll(ring, 1, 0), axis=1)                      # no dot twice in a row
        out.append(ring[keep].tolist())
    return out

def fit_rings(rings, tol=TOL, raw=frozenset()):
    """closed rings of dots (each [[x, y], ...], not repeating the first dot) -> (fitted rings, stats, each ring's stretches); shared
    stretches fitted alike. Stretches in `raw` stay as their exact segments."""
    rings = [[(round(float(x), 4), round(float(y), 4)) for x, y in r] for r in rings]
    seen = {}
    for r in rings:
        n = len(r)
        for k, p in enumerate(r): seen.setdefault(p, set()).add((r[k - 1], r[(k + 1) % n]))
    anchor = {p for p, s in seen.items() if len(s) > 1}
    cache, out, chains, stats = {}, [], [], {'dots': 0, 'pieces': 0, 'arcs': 0}
    for r in rings:
        n = len(r); stats['dots'] += n
        idx = [k for k, p in enumerate(r) if p in anchor]
        if not idx: idx = [min(range(n), key=lambda k: r[k])]                    # a ring of its own: start at its lowest dot
        segs, mine = [], []
        for a, b in zip(idx, idx[1:] + [idx[0] + n]):
            chain = tuple(r[k % n] for k in range(a, b + 1)); mine.append(chain)
            if chain not in cache: cache[chain] = fit_chain(chain, tol, chain in raw)
            segs += cache[chain]
        out.append({'start': list(r[idx[0]]), 'segs': segs}); chains.append(mine)
        stats['pieces'] += len(segs); stats['arcs'] += sum(1 for s in segs if s[0] == 'A')
    return out, stats, chains

def sample(fr, step=0.005):
    """a fitted ring as dense dots (arcs every `step` mm), to check it"""
    p = fr['start']; out = [p]
    for sg in fr['segs']:
        q = sg[-1]
        if sg[0] == 'A':
            (ux, uy), R = _circle(p, sg[1], q)
            t0, t1 = math.atan2(p[1] - uy, p[0] - ux), math.atan2(q[1] - uy, q[0] - ux)
            ccw = (sg[1][0] - p[0]) * (q[1] - p[1]) - (sg[1][1] - p[1]) * (q[0] - p[0]) > 0
            sw = (t1 - t0) % (2 * math.pi) if ccw else -((t0 - t1) % (2 * math.pi))
            k = max(2, int(abs(sw) * R / step))
            out += [[ux + R * math.cos(t0 + sw * i / k), uy + R * math.sin(t0 + sw * i / k)] for i in range(1, k)]
        out.append(q); p = q
    return out

def fit_faces(faces, tol=TOL):
    """faces [{'outer': ring, 'holes': [ring, ...]}] -> ([{'outer': fitted, 'holes': [fitted, ...]}], stats). Each fitted face is
    checked (shapely): one whose walls cross has its stretches put back as their exact segments, in every face that shares them."""
    from shapely.geometry import Polygon
    rings = [r for f in faces for r in [f['outer']] + f['holes']]
    raw = set(); stats = {}; repaired = set()
    for attempt in range(4):
        fitted, stats, chains = fit_rings(rings, tol, frozenset(raw))
        out, bad, k = [], [], 0
        for fi, f in enumerate(faces):
            n = 1 + len(f['holes']); fr = fitted[k:k + n]
            g = Polygon(sample(fr[0])[:-1], [sample(h)[:-1] for h in fr[1:]])
            if not g.is_valid: bad.append(range(k, k + n)); repaired.add(fi)
            out.append({'outer': fr[0], 'holes': fr[1:]}); k += n
        if not bad: break
        for rg in bad:
            for i in rg: raw.update(chains[i])
    # still crossing as its own exact dots: the resolved wall itself crosses, by less than the model's grid (D20: 0.006 µm, where a
    # 1.2 µm notch meets the long edge beside it). shapely resolves the crossing; the main shape is kept, the sub-µm lobe dropped.
    from shapely.geometry.polygon import orient
    k = 0; mended = 0
    for fi, f in enumerate(faces):
        n = 1 + len(f['holes']); fr = out[fi]
        g = Polygon(sample(fr['outer'])[:-1], [sample(h)[:-1] for h in fr['holes']])
        if not g.is_valid:
            g = g.buffer(0)
            if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda q: q.area)
            g = orient(g, 1.0)
            ring = lambda c: {'start': [round(c[0][0], 6), round(c[0][1], 6)], 'segs': [['L', [round(x, 6), round(y, 6)]] for x, y in c[1:]]}
            out[fi] = {'outer': ring(list(g.exterior.coords)), 'holes': [ring(list(h.coords)) for h in g.interiors]}; mended += 1
        k += n
    stats['exact_faces'] = len(repaired); stats['mended'] = mended
    return out, stats

