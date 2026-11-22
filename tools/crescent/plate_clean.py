# Plate clean (2026-11-19, Adam's notes P44-P60): the main plate's levels rebuilt from the cuts that do a job, instead of
# patches on patches.
#
# Every earlier tidy pass added its own small pockets ("tower cut down", "island removed", "point rounded", "cusp rounded")
# on top of the wheel recesses. Their edges nearly coincided with the recesses' edges, so each one left a new hairline
# sliver or a lower tower beside it, and some had spurs of their own. This pass throws all of those away and works out the
# plate again from what must be cut (the wheel recesses, the windows, the stem and worm pockets):
#   for every floor level, deepest first, the air at or below that level (with everything outside the plate) is closed
#   by a round tool of radius R: any wall or point of plate under 2R wide comes down to that level and every outside
#   corner is rounded r R; any island of plate standing above that level, smaller than TOWER_A, comes down too.
# What that adds beyond the real cuts becomes one clean pocket per piece, reaching 0.3 mm into air that is already cut
# (so no hairline is left where its edge meets a recess). Only plate is removed, never added, so every clearance holds.
# Drilled holes, bearings and screws are left as they are. Re-running replaces the previous "Clean:" pockets.
#
#   apply(J, log, part_id='D1')      python3 plate_clean.py IN.json OUT.json [D1]
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, close, opening, circle, spline_poly, simplify, dots_sharp

R, TOWER_A, OVERLAP = 1.2, 40.0, 0.3
SIMPLIFY = 0.003     # pocket dots: points within this of the line through their neighbours dropped
PATCH = ('Tidy:', 'Tower removed', 'Island removed', 'Cusp rounded', 'Clean:')
DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}

def next_cut_id(J):
    """the sim keeps only cuts with an id h<n> (index.html's loader drops the rest), unique across the scene"""
    n = max([int(c['id'][1:]) for d in J['state']['drawn'] for c in (d.get('cuts') or []) if str(c.get('id', '')).startswith('h') and str(c['id'])[1:].isdigit()] + [0])
    while True:
        n += 1; yield f'h{n}'
def swept_discs(J, zlo, zhi, gap=0.6):
    """the circle each turning or swinging drawn part sweeps (about its arbor or pivot), for parts within zlo..zhi"""
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; mounts = J['project'].get('mechanisms', {}).get('mounts', {}) or {}
    out = []
    for d in st['drawn']:
        m = mounts.get(d['id']); k = SK.get(d['sketch'])
        if not m or not k or k['plane']['axis'] != 'z': continue
        c = st['pos'].get(m['axis']) if m.get('axis') else m.get('pivot')
        if not c: continue
        a, b = k['plane']['offset'], k['plane']['offset'] + d['thickness']
        if min(a, b) >= zhi or max(a, b) <= zlo: continue
        r = max(np.hypot(*(np.asarray(spline_poly(k['points'])) - c).T))
        out.append(circle(c, r + gap))
    return union(out) if out else []
def is_patch(c): return any((c.get('name') or '').startswith(p) for p in PATCH)
def ring_sim(c, r):
    """the sim's circle (index.html cutLayers ring()): 72 sides"""
    n = 72   # (finer circles for r > 3.4 written and tested 2026-11-22, held back until the main plate's rebuild is verified: n = max(72, 4 * ceil(pi * r / 0.6)))
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
def is_drilled(c): return c['kind'] in DRILLED and c.get('d') and c['d'] <= 3.2
def cut_paths(c, SK):
    if c['kind'] == 'pocket':
        k = SK.get(c['sketch'])
        return union([P(spline_poly(k['points']))]) if k else []
    return [P(ring_sim(c['at'], c['d'] / 2))] if c.get('d') else []      # the sim's own circle, so no hairline is left against it
def pieces(a):
    """split a region into simple outlines: each outer loop with no holes, cutting through holes with straight lines"""
    out = []
    stack = [a]
    while stack:
        reg = stack.pop()
        outs = [p for p in reg if pc.Orientation(p)]
        for o in outs:
            holes = [h for h in reg if not pc.Orientation(h) and pc.PointInPolygon(h[0], o) != 0]
            if not holes: out.append(o); continue
            hp = F(holes[0]); hx = np.mean(hp[:, 0]); bb = F(o); y0, y1 = bb[:, 1].min() - 1, bb[:, 1].max() + 1; x0, x1 = bb[:, 0].min() - 1, bb[:, 0].max() + 1
            ov = min(0.05, 0.2 * (hp[:, 0].max() - hp[:, 0].min()))   # overlapping halves, so no seam can open between them (less than the island is wide)
            sub = [o] + holes
            for half in ([[x0, y0], [hx + ov, y0], [hx + ov, y1], [x0, y1]], [[hx - ov, y0], [x1, y0], [x1, y1], [hx - ov, y1]]):
                h = inter(sub, [P(half)])
                if h: stack.append(h)
    return out

def apply(J, log, part_id='D1'):
    st = J['state']; SK = {k['id']: k for k in st['sketches']}
    d = next(x for x in st['drawn'] if x['id'] == part_id)
    k = SK[d['sketch']]; z0, T = k['plane']['offset'], d['thickness']
    cuts = d.get('cuts', []) or []
    patches = [c for c in cuts if is_patch(c)]
    keep = [c for c in cuts if not is_patch(c)]
    for c in patches:                                             # their sketches go with them
        if c['kind'] == 'pocket': st['sketches'] = [s for s in st['sketches'] if s['id'] != c['sketch']]
    SK = {s['id']: s for s in st['sketches']}
    outline = union([P(spline_poly(k['points']))])
    box = [P([[-200, -200], [200, -200], [200, 200], [-200, 200]])]
    outside = diff(box, outline)
    func = []                                                     # (paths, floor) of the cuts that do a job, from the top
    for c in keep:
        if is_drilled(c) or c.get('from') != 'back': continue
        D = T if c.get('depth') is None else min(T, max(0.0, c['depth']))
        func.append((cut_paths(c, SK), round(T - D, 4)))
    levels = sorted({f for _, f in func if f < T - 1e-6})
    prev, new, towers, n_pts = [], [], 0, 0
    ids = next_cut_id(J)
    A2s, reals = [], []
    for L in levels:
        real = union(outside, *[p for p, f in func if f <= L + 1e-6])
        A2 = close(real, R)                                       # the real cuts only, closed once (re-closing the level below drifted at the rim)
        big = [p for p in A2 if pc.Orientation(p) or abs(pc.Area(p)) / S / S >= TOWER_A]
        towers += len(A2) - len(big)
        A2 = union(big, prev)
        A2 = union(opening(close(A2, 0.1), 0.1), real, prev)       # micro spikes and notches (under 0.2 mm) off: the sim draws them as slivers
        A2s.append(A2); reals.append(real); prev = A2
    import stack_align as SA
    # floor strips under 1 mm drop to the level below (walls run straight down), but never through the plate
    iv = [i for i, L in enumerate(levels) if L > 1e-6]; _L = [A2s[i] for i in iv]; n_strip = SA.strips(_L)
    for i, a in zip(iv, _L): A2s[i] = union(close(a, R), reals[i])       # strip ends blended (r R), the real cuts kept
    for i in range(1, len(A2s)): A2s[i] = union(A2s[i], A2s[i - 1])
    prev = []
    for L, A2, real in zip(levels, A2s, reals):
        A = union(real, prev)
        extra = opening(diff(A2, A), 0.003)                      # only numerical slivers (under 6 µm) are dropped: real specks get cut too
        extra = [p for p in extra if abs(pc.Area(p)) / S / S >= 0.0001 or not pc.Orientation(p)]
        if not extra: prev = A2; continue
        reg = inter(offset(extra, OVERLAP), A2)
        reg = inter(reg, offset(outline, 0.5))
        for p in pieces(reg):
            a = abs(pc.Area(p)) / S / S
            if a < 0.0001: continue
            pts = F(p); pts = simplify(np.vstack([pts, pts[:1]]), SIMPLIFY)[:-1]
            if len(pts) < 3: continue
            sid = f'KC{len(new) + 1}_{part_id}'
            while sid in SK: sid += 'x'
            st['sketches'].append({'id': sid, 'name': f'Clean {part_id} {L + z0:.2f}', 'plane': {'axis': 'z', 'offset': z0}, 'closed': True, 'points': dots_sharp(pts)})
            new.append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(T - L, 4),
                        'name': f'Clean: plate under 2 mm, points and towers taken down to {L + z0:.2f} ({a:.2f} mm2)'})
            n_pts += len(pts)
        prev = A2
    d['cuts'] = keep + new
    log.append(f'plate clean {part_id}: {len(patches)} old patch cuts removed; {len(new)} clean pockets over {len(levels)} levels '
               f'(walls and points under {2 * R:g} mm, {towers} towers under {TOWER_A:g} mm2, {n_strip} floor strips under 1 mm dropped), {n_pts} dots')
    return new

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    for pid in (sys.argv[3].split(',') if len(sys.argv) > 3 else ['D1']): apply(J, log, pid)
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))

# ---------- the outline itself (the motion-works plate's edge: P47-P49, P53-P55) ----------
def fair(loop, sigma=0.6, step=0.1):
    """resample a closed loop every `step` mm and smooth it with a Gaussian of `sigma` mm (wobbles shorter than ~4 sigma go)"""
    Pn = np.asarray(loop, float); Q = np.vstack([Pn, Pn[:1]]); seg = np.hypot(*np.diff(Q, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    n = max(16, int(s[-1] / step)); t = np.linspace(0, s[-1], n, endpoint=False)
    x = np.interp(t, s, Q[:, 0]); y = np.interp(t, s, Q[:, 1])
    k = int(3 * sigma / step); w = np.exp(-0.5 * (np.arange(-k, k + 1) * step / sigma) ** 2); w /= w.sum()
    sm = lambda a: np.convolve(np.r_[a[-k:], a, a[:k]], w, mode='valid')
    return np.c_[sm(x), sm(y)]
def clean_outline(J, log, part_id, r=1.2, sigma=0.6, tol=0.02):
    import refit as RF
    st = J['state']; SK = {k['id']: k for k in st['sketches']}
    d = next(x for x in st['drawn'] if x['id'] == part_id); k = SK[d['sketch']]
    if len(k['points']) > 100 and not any(q.get('smooth') for q in k['points']):
        return                                                    # already exact (cleaned once): fairing again would shave it each time
    M0 = union([P(spline_poly(k['points']))])
    M1 = close(opening(M0, r), r)                                 # points and necks under 2r off, notches under 2r filled
    outs = [p for p in M1 if pc.Orientation(p)]; big = max(outs, key=lambda p: abs(pc.Area(p)))
    loop = fair(F(big), sigma)
    # fairing and filling may add plate only where nothing turns: never inside a moving part's swept circle
    Mf = inter([P(loop)], M1); Mf = diff(Mf, diff(swept_discs(J, z0 := k['plane']['offset'], z0 + d['thickness']), M0))
    big = max([p for p in Mf if pc.Orientation(p)], key=lambda p: abs(pc.Area(p))); loop = F(big)
    Pn = loop; keep = [Pn[0]]
    for q in Pn[1:]:
        if np.hypot(*(q - keep[-1])) >= 0.1: keep.append(q)
    loop = np.array(keep)
    lp = simplify(np.vstack([loop, loop[:1]]), 0.003)[:-1]          # exact: sharp dots, close on curves, sparse on straights
    fitted = [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in lp]   # (a fitted spline overshot into hooks: P67-P69)
    old = len(k['points']); k['points'] = fitted
    log.append(f'outline {part_id}: points and necks under {2 * r:g} mm rounded off, notches filled, wobbles faired (sigma {sigma:g} mm); '
               f'{old} -> {len(fitted)} dots (fit within {tol:g} mm)')

# ---------- a full rebuild of a plate's pockets (the motion-works plate: its ledges came from pixel rasters) ----------
def rebuild(J, log, part_id, R_in=1.2, R_out=1.0):
    """every from-top pocket of the part is replaced by one clean region per floor level: closed by R_in (plate under 2 R_in
    and points come down, the raster steps on the old ledges' edges with them). Only plate is removed, so every clearance holds.
    (Filling inside corners as well made stepped wedges where a ledge meets a window at a sharp angle, so it is not done.)"""
    st = J['state']; SK = {k['id']: k for k in st['sketches']}
    d = next(x for x in st['drawn'] if x['id'] == part_id); k = SK[d['sketch']]; z0, T = k['plane']['offset'], d['thickness']
    cuts = d.get('cuts', []) or []
    pockets = [c for c in cuts if c['kind'] == 'pocket' and c.get('from') == 'back']
    rest = [c for c in cuts if c not in pockets]
    outline = union([P(spline_poly(k['points']))])
    outside = diff([P([[-200, -200], [200, -200], [200, 200], [-200, 200]])], outline)
    by = {}
    for c in pockets:
        D = T if c.get('depth') is None else min(T, max(0.0, c['depth'])); L = round(T - D, 4)
        by.setdefault(L, {'paths': [], 'names': [], 'each': []}); cp = cut_paths(c, SK)
        by[L]['paths'] += cp; by[L]['names'].append(c.get('name') or 'pocket'); by[L]['each'].append((cp, c.get('name') or 'pocket'))
        st['sketches'] = [s for s in st['sketches'] if s['id'] != c['sketch']]
    SK = {s['id']: s for s in st['sketches']}
    prev, new, towers, n_pts = outside, [], 0, 0
    ids = next_cut_id(J)
    Ls, A2s = sorted(by), []
    for L in Ls:
        A = union(prev, by[L]['paths'])
        A2 = close(A, R_in)                                       # monotone, so the levels stay nested by themselves
        sharp = [q for q in diff(A2, opening(A2, 1.5)) if pc.Orientation(q) and abs(pc.Area(q)) / S / S < 4.0]   # (r 1.5: a filled neck becomes a solid bridge)
        if sharp: A2 = union(diff(A2, sharp), prev)               # small sharp inside corners, notches and necks filled up to the ledge beside them
                                                                  # (P63-P66, P74, P75; the sim's sweep check confirms no moving part needed them)
        big = [p for p in A2 if pc.Orientation(p) or abs(pc.Area(p)) / S / S >= TOWER_A]; towers += len(A2) - len(big)
        A2 = union(big, prev)
        # cutter reach (Z1, common bits): through the plate, inside corners r 1.6 (a 1/8" cutter, 1/2" flute); on the ledges, small
        # inside corners filled to r 1.06 and slots narrower than 2.1 widened to 2.1 (a 2 mm cutter, 8 mm flute)
        if L <= 1e-6:
            A2 = union(opening(A2, 1.6), outside)
        else:
            thin = [q for q in diff(A2, opening(A2, 1.06)) if pc.Orientation(q)]
            small = [q for q in thin if abs(pc.Area(q)) / S / S < 0.6]; wide = [q for q in thin if abs(pc.Area(q)) / S / S >= 0.6]
            if small: A2 = union(diff(A2, small), prev)
            if wide: A2 = close(union(A2, offset(wide, 0.15)), R_in)
        A2 = union(opening(close(A2, 0.1), 0.1), prev)             # micro spikes and notches (under 0.2 mm) off: the sim draws them as slivers
        A2s.append(A2); prev = A2
    import stack_align as SA
    # floor strips under 1 mm drop to the level below (walls run straight down), but never through the plate
    iv = list(range(len(Ls))); _L = [A2s[i] for i in iv]; n_strip = SA.strips(_L)   # (a strip merges only into the level it runs along)
    for i, a in zip(iv, _L):                                      # strip ends blended, small sharp corners filled again
        a = close(a, R_in); sh = [q for q in diff(a, opening(a, 1.06)) if pc.Orientation(q) and abs(pc.Area(q)) / S / S < 0.6]
        A2s[i] = diff(a, sh) if sh else a
    A2s = [union(a, outside) for a in A2s]
    for i in range(1, len(A2s)): A2s[i] = union(A2s[i], A2s[i - 1])
    prev = outside
    for L, A2 in zip(Ls, A2s):
        extra = opening(diff(A2, prev), 0.003)                    # only what is new at this level (numerical slivers under 6 µm dropped),
        reg = inter(offset(extra, OVERLAP), A2)                   # reaching 0.3 mm into what is already cut (and past the plate's edge)
        used = {}
        for p in pieces(reg):
            a = abs(pc.Area(p)) / S / S
            if a < 0.0001: continue
            pts = F(p); pts = simplify(np.vstack([pts, pts[:1]]), 0.003)[:-1]
            ov = [(abs(sum(pc.Area(q) for q in inter([p], cp))), nm) for cp, nm in by[L]['each']]
            nm = max(ov)[1] if ov and max(ov)[0] > 0 else f'Ledge at {L + z0:.2f} mm (rounding)'
            used[nm] = used.get(nm, 0) + 1; i = used[nm] - 1
            sid = f'KR{len(new) + 1}_{part_id}'
            while sid in SK: sid += 'x'
            st['sketches'].append({'id': sid, 'name': f'{part_id} level {L + z0:.2f}', 'plane': {'axis': 'z', 'offset': z0}, 'closed': True, 'points': dots_sharp(pts)})
            new.append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(T - L, 4), 'name': nm if i == 0 else f'{nm} ({i + 1})'})
            n_pts += len(pts)
        prev = A2
    d['cuts'] = rest + new
    log.append(f'rebuilt {part_id}: {len(pockets)} pockets -> {len(new)} over {len(by)} levels (plate under {2 * R_in:g} mm and points off, '
               f'{towers} towers, {n_strip} floor strips under 1 mm dropped), {n_pts} dots')
