# Plate resolver (generic; any project, any 2.5D part milled from one face). VISION.md §7, the resolver path, R2.
#
# Input: one drawn part as the designer drew it (its outline and its cuts: the INTENT, never edited here) and the shop rules.
# Output: the part as the machine will cut it (the RESOLVED plate): an outline plus one region per floor ("tier"), stored on the
# part as d['resolved'] beside the intent. Same intent and rules in, same plate out: it always starts from scratch, so dragging a
# polyspline and resolving again never piles a fix on a fix.
#
# Per floor, deepest first (a floor is the height left under a cut, measured from the far face):
#   1. the air: everything cut at least that deep (the outside, the pockets and the larger bores; small drilled holes stay their
#      own true circles and are not part of the tiers);
#   2. hairlines and thin walls: plate narrower than 2 × max(SPECK, minWall/2) comes down, and with a minWall, islands of plate
#      smaller than TOWER_A too. The real cuts stay exact: the rounding only adds air away from them. Each corner is rounded once,
#      at the floor where it first appears (a thin re-rounding against a rounding below is dropped; a thin piece that cuts a
#      hairline of plate away stays);
#   3. the cutter: air the smallest cutter cannot reach (inside corners tighter than its radius) goes back to plate, so what is
#      stored is what the machine will leave;
#   4. one wall across heights: the floors' walls welded where they nearly coincide and ledge starts faired (onewall);
#   5. the tiers: the outline from the through floor, each floor's air as rings (outer anticlockwise, holes clockwise).
#
#   python3 resolve.py IN.json PID[,PID...] [OUT.json]       (writes d['resolved'] for each part; the sim stamps its key on load)
#   serve.py runs it for the sim's Resolve button (resolve_scene below).
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import pyclipper as pc
from geo import (P, F, S, union, diff, inter, offset, close, opening, simplify, area, pieces, spline_poly, ring_sim, ar, pos, BOX,
                 clean_level)
import onewall as OW

DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}
DRILL_MAX = 3.2       # a drilled kind this size or smaller is a drilled hole (its own true circle); larger is milled with the tiers
SHOP = {'cutter': 1.0, 'minWall': 0.0}     # defaults: smallest end mill Ø (mm); thin-wall takedown (0: hairlines only)
SPECK = 0.1           # plate narrower than 2 × SPECK is a hairline: it always comes down
TOWER_A = 40.0        # with a minWall: islands of plate smaller than this (mm²) standing above a floor come down
NEEDS = 0.15          # a piece the rounding adds must be this wide somewhere to count ...
BRIDGE = 0.75         # ... unless air runs along this much of its edge (both sides): then it cuts a hairline of plate and stays
TIER_TOL = 1e-4       # tier rings kept to 0.1 µm of the model (the sim's grid), so a wall shared by two tiers stays one edge
TIER_REACH = 0.3      # each tier's region reaches this far past the plate's edge, so no tier edge lies exactly on the outline

def is_drilled(c): return c['kind'] in DRILLED and c.get('d') and c['d'] <= DRILL_MAX
def resolvable(d, k):
    """a 2.5D part: drawn on a z plane, straight walls (no back outline, twist or slant)"""
    return k is not None and k['plane']['axis'] == 'z' and k.get('closed', True) and not d.get('back') and not d.get('twist') and not d.get('place')
def face_of(d):
    """the face the part is milled from (the sim's 'mill'; else the face its blind cuts come from; else the back)"""
    if d.get('mill') in ('back', 'front'): return d['mill']
    blind = [c for c in d.get('cuts') or [] if c.get('depth') is not None and c['depth'] < d['thickness'] - 1e-6]
    return (blind[0].get('from') or 'front') if blind else 'back'
def shop_of(J, d):
    s = dict(SHOP); s.update({k: v for k, v in (J.get('project', {}).get('shop') or {}).items() if k in SHOP})
    if d.get('minWall') is not None: s['minWall'] = float(d['minWall'])
    if d.get('cutter'): s['cutter'] = float(d['cutter'])                         # a part can name a smaller (or larger) end mill
    return s

def cut_rings(c, SK, pos_):
    """a milled cut's outlines with the depth each goes to: [(paths, depth)] (a bore's seat is its own, shallower ring)"""
    T = None
    if c['kind'] == 'pocket':
        k = SK.get(c.get('sketch'))
        if not k or not k.get('closed', True) or len(k['points']) < 3: return []
        return [(union([P(spline_poly(k['points']))]), c.get('depth'))]
    at = pos_.get(c['axis']) if c.get('axis') and pos_.get(c['axis']) else c.get('at')
    if not at or not c.get('d'): return []
    out = [([P(ring_sim(at, c['d'] / 2))], c.get('depth'))]
    st = c.get('seat')
    if st and st.get('d', 0) > c['d'] and st.get('depth', 0) > 0: out.append(([P(ring_sim(at, st['d'] / 2))], st['depth']))
    return out

def floors(J, d, k, shop):
    """the air per floor (deepest first) as the cutter will leave it, before the walls are made one. Returns (Ls, A, notes)."""
    st = J['state']; SK = {s['id']: s for s in st['sketches']}; T = d['thickness']; face = face_of(d)
    outline = union([P(spline_poly(k['points']))])
    func = []
    for c in d.get('cuts') or []:
        if is_drilled(c) or (c.get('from') or 'front') != face: continue     # (the sim's loader reads a missing face as the front)
        for paths, depth in cut_rings(c, SK, st['pos']):
            D = T if depth is None else min(T, max(0.0, depth))
            if D > 1e-6: func.append((paths, round(T - D, 4)))
    return floors_from(outline, func, T, shop)

def floors_from(outline, func, T, shop, speck=SPECK):
    """the floors loop for any part: its outline (clipper paths), its cuts as [(paths, floor height from the far face)], its thickness.
    speck: plate narrower than twice this comes down, and outside corners are rounded to it once (a gear passes a few µm: its tooth
    tips are cut as drawn, since an end mill leaves an outside corner sharp)"""
    outside = diff(BOX, outline); near_part = offset(outline, 2.0)
    Ls = sorted({0.0} | {f for _, f in func if f < T - 1e-6})
    R = max(speck, shop['minWall'] / 2); r_cut = shop['cutter'] / 2
    prev, A, rounded, notes = [], [], [], {'towers': 0, 'thin_added': 0.0, 'cutter_filled': 0.0}
    for L in Ls:
        cuts_here = union(outside, *[p for p, f in func if f <= L + 1e-6])
        real = union(cuts_here, prev)
        C = close(real, R)
        if shop['minWall'] > 0:
            big = [p for p in C if pc.Orientation(p) or abs(pc.Area(p)) / S / S >= TOWER_A]; notes['towers'] += len(C) - len(big)
            C = union(big, real)
        C = union(opening(close(C, speck), speck), real)
        raw = diff(C, real)
        def needed(q):
            if opening([q], NEEDS / 2): return True                                    # wide enough somewhere: a real takedown
            if not rounded or not inter(offset([q], 0.01), rounded): return True       # a corner's first rounding
            Q = F(q); per = float(np.hypot(*(np.roll(Q, -1, 0) - Q).T).sum())
            near = inter(offset([q], 0.004), inter(real, offset([q], 0.01)))           # the air within 4 µm of its edge
            adj = sum(abs(pc.Area(p)) for p in near) / S / S / 0.004                   # ~ the length of its edge with air beside it
            return adj > BRIDGE * per
        outers = [q for q in raw if pc.Orientation(q) and needed(q)]
        add = inter(raw, outers) if outers else []
        A2 = union(real, inter(offset(add, 0.01), C)) if add else real
        notes['thin_added'] += sum(ar(q) for q in pos(add)) if add else 0.0
        # the cutter: inside corners tighter than its radius stay plate. Only the real misses go back (the residue's µm tails along
        # every round wall, from re-drawing arcs, are left alone, so walls stay exact)
        miss = inter(diff(A2, opening(A2, r_cut)), near_part)       # (not the far box's own corners)
        miss = opening(miss, 0.003) if miss else []
        if miss:
            notes['cutter_filled'] += sum(ar(q) for q in pos(miss))
            A2 = union(diff(A2, offset(miss, 0.001)), prev)     # (1 µm into the wall it fills against, so it can't come away from it)
        rounded = diff(A2, cuts_here)
        A.append(clean_level(A2)); prev = A2
    return Ls, A, notes, near_part

def tiers(d, Ls, A, near_part):
    """the outline (the through floor's plate) and each floor's air as rings, depth measured from the milled face"""
    T = d['thickness']
    M0 = [q for q in pos(inter(near_part, diff(BOX, A[0]))) if ar(q) >= 0.01]
    if not M0: return None, [], 0
    big = max(M0, key=ar)
    ring = lambda p: [[round(float(x), 4), round(float(y), 4)] for x, y in simplify(np.vstack([F(p), F(p)[:1]]), TIER_TOL)[:-1]]
    reach = offset([big], TIER_REACH)
    out = []
    for i, (L, A2) in enumerate(zip(Ls, A)):
        R = inter(A2, [big]) if i == 0 else inter(A2, reach)       # the through floor: the holes in the plate; above: all its air
        rings = [ring(p) for p in R if ar(p) >= 1e-4]
        if rings: out.append({'depth': round(T - L, 4), 'paths': rings})
    return ring(big), out, len(M0) - 1

def resolve_part(J, pid, log=None):
    t0 = time.time(); st = J['state']
    d = next(x for x in st['drawn'] if x['id'] == pid); k = next((s for s in st['sketches'] if s['id'] == d['sketch']), None)
    if not resolvable(d, k): raise ValueError(f'{pid} is not a flat part milled from one face (drawn on a z plane, straight walls)')
    shop = shop_of(J, d)
    Ls, A, notes, near_part = floors(J, d, k, shop)
    KO = [None] * len(A)
    A, moved = OW.regrade_levels(A, KO)
    A, cut, fill = OW.fair_levels(A, KO)
    outline, tl, extra = tiers(d, Ls, A, near_part)
    if outline is None: raise ValueError(f'{pid}: nothing is left of the part')
    msg = (f"{len(Ls)} floor{'s' if len(Ls) != 1 else ''}; cutter Ø{shop['cutter']:g}: {notes['cutter_filled']:.3f} mm² of corners it can't reach left as plate; "
           + (f"walls under {shop['minWall']:g} mm taken down ({notes['thin_added']:.2f} mm²), {notes['towers']} islands; " if shop['minWall'] > 0 else f"hairlines under {2 * SPECK:g} mm taken down ({notes['thin_added']:.3f} mm²); ")
           + f"walls made one: {moved} points welded, ledge starts faired (≤{max(cut, fill) * 1000:.0f} µm)"
           + (f"; {extra} separate piece{'s' if extra > 1 else ''} dropped (the part is its largest piece)" if extra else '')
           + f"; {time.time() - t0:.1f} s")
    d['resolved'] = {'outline': outline, 'tiers': tl, 'face': face_of(d), 'shop': shop, 'log': msg,
                     'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'key': None}
    if log is not None: log.append(f'{pid}: {msg}')
    return d['resolved']

def resolve_scene(J, pids):
    """for serve.py: resolve the named parts in a scene, return {pid: resolved or {'error': text}}"""
    out = {}
    gp = [pid for pid in pids if pid.startswith('G:')]
    if gp:
        import gears
        out.update(gears.resolve_scene(J, gp))
    for pid in pids:
        if pid in out: continue
        try: out[pid] = resolve_part(J, pid)
        except Exception as e: out[pid] = {'error': f'{type(e).__name__}: {e}'}
    return out

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    for pid in sys.argv[2].split(','): resolve_part(J, pid, log)
    print('\n'.join(log))
    if len(sys.argv) > 3: json.dump(J, open(sys.argv[3], 'w'))
