# Stack alignment (2026-11-21, Adam: "these should all be smooth continuous surfaces x y and z"; notes P67, P77-P85).
# Two walls that should be one surface were running 0.1-1.3 mm apart, leaving thin strips of floor between them that read as
# bumps, overlaps and uneven walls. Two rules, both only ever removing material (so no clearance can shrink):
#   - in a plate: a strip of floor narrower than STRIP (1.0 mm) between a deeper level and a higher wall drops to the deeper level,
#     so the wall runs straight down (seat ledges that hold a part, like the worm cap's 1.25 mm, are wider and stay)
#   - between the main plate and the motion-works plate on it: where the motion-works plate's edge and the main plate's edge below
#     run within STACK (1.5 mm) of each other, the thin strip goes: a strip of the main plate's top face showing beside the
#     motion-works plate's wall is cut down to the recess beside it; a thin overhang of the motion-works plate over a recess is cut
#     away through. The two walls then meet as one.
#   strips(A2s, w)            used by plate_clean.apply/rebuild on their level regions
#   align(J, log)             adds 'Align:' cuts to the main plate and the motion-works plate (plate_clean then folds them in)
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, opening, spline_poly, simplify, dots_sharp

STRIP, STACK = 1.0, 1.5

def strips(A2s, w=STRIP):
    """level regions (air at or below each level, ascending, nested): thin floor bands drop to the level below; returns how many"""
    n = 0
    for i in range(len(A2s) - 1, 0, -1):
        band = diff(A2s[i], A2s[i - 1])
        # only a strip that runs along the deeper level (a step in a wall) merges; a narrow floor between two higher walls
        # (a groove, a slot) is a real feature and stays
        thin = inter(diff(band, opening(band, w / 2)), offset(A2s[i - 1], 0.05))
        thin = [q for q in thin if pc.Orientation(q) and abs(pc.Area(q)) / S / S > 0.01]
        if thin:
            A2s[i - 1] = union(A2s[i - 1], offset(thin, 0.02)) if False else union(A2s[i - 1], thin); n += len(thin)
    return n

from plate_clean import ring_sim   # the sim's own circle
def cut_regions(d, SK, T):
    """(paths, floor) of every from-the-top cut, as the sim draws it (drilled holes left out)"""
    out = []
    for c in d.get('cuts') or []:
        if c.get('from') != 'back': continue
        D = T if c.get('depth') is None else min(T, max(0.0, c['depth']))
        if c['kind'] == 'pocket':
            k = SK.get(c['sketch'])
            if k and len(k['points']) >= 3: out.append((union([P(spline_poly(k['points']))]), round(T - D, 4)))
        elif c.get('d') and c.get('at') and not (c['kind'] in ('hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel') and c['d'] <= 3.2):
            out.append(([P(ring_sim(c['at'], c['d'] / 2))], round(T - D, 4)))
    return out

def align(J, log, lower='D1', upper='D3'):
    import plate_clean as PC
    st = J['state']; SK = {k['id']: k for k in st['sketches']}
    d1 = next(x for x in st['drawn'] if x['id'] == lower); d3 = next(x for x in st['drawn'] if x['id'] == upper)
    k1, k3 = SK[d1['sketch']], SK[d3['sketch']]; T1, T3 = d1['thickness'], d3['thickness']; z1, z3 = k1['plane']['offset'], k3['plane']['offset']
    out1 = union([P(spline_poly(k1['points']))]); out3 = union([P(spline_poly(k3['points']))])
    c1 = cut_regions(d1, SK, T1); c3 = cut_regions(d3, SK, T3)
    W1 = inter(union(*[p for p, f in c1]), out1)                                   # where the main plate's top face is cut away
    solid3 = diff(out3, union(*[p for p, f in c3 if f <= 1e-6]))                   # the motion-works plate at its bottom face
    open3 = diff(out1, solid3)                                                     # over the main plate, where nothing of it sits
    levels1 = sorted({f for p, f in c1 if f < T1 - 1e-6})
    air1 = {L: union(*[p for p, f in c1 if f <= L + 1e-6]) for L in levels1}
    ids = PC.next_cut_id(J); n_a = n_b = 0
    def add(d, k, name, poly, depth):
        sid = f'KA{d["id"]}_{len(st["sketches"])}'
        pts = simplify(np.vstack([F(poly), F(poly)[:1]]), 0.002)[:-1]
        st['sketches'].append({'id': sid, 'name': name[:40], 'plane': {'axis': 'z', 'offset': k['plane']['offset']}, 'closed': True, 'points': dots_sharp(pts)})
        d['cuts'].append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(depth, 4), 'name': name})
    # a strip of the main plate's top showing beside the motion-works plate's wall: down to the recess beside it
    Sa = diff(open3, W1)
    for q in diff(Sa, opening(Sa, STACK / 2)):
        if not pc.Orientation(q) or abs(pc.Area(q)) / S / S < 0.01: continue
        near = offset([q], 0.15)
        touch = [L for L in levels1 if inter(near, air1[L])]
        if not touch: continue
        L = max(touch)
        for r in inter(offset([q], 0.1), union([q], W1, open3)):
            if pc.Orientation(r): add(d1, k1, f'Align: a strip of the main plate beside the motion-works plate\'s wall, down to {z1 + L:.2f}', r, T1 - L); n_a += 1
    # a thin overhang of the motion-works plate over a recess: cut away through
    Sb = inter(diff(W1, open3), solid3)
    for q in diff(Sb, opening(Sb, STACK / 2)):
        if not pc.Orientation(q) or abs(pc.Area(q)) / S / S < 0.01: continue
        for r in inter(offset([q], 0.1), union([q], W1)):
            if pc.Orientation(r): add(d3, k3, 'Align: a thin overhang over the main plate\'s recess, cut away through', r, T3); n_b += 1
    log.append(f'stack {lower}/{upper}: {n_a} strips of the main plate\'s top cut down beside the motion-works plate\'s walls, {n_b} thin overhangs cut away (under {STACK:g} mm)')
    return n_a + n_b
