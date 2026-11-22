# The main plate's rebuild (2026-11-22, Adam's notes P91, P97-P100; approved "yes" to the rebuild, "Start it").
#   merge_caps(J, log)   P91: the worm cap (D30) and the stem cap (D31) as one part, cut from the 5.05 mm stock, the worm end milled
#                        2.25 mm thinner from underneath so it sits on the worm cap's seat as before; r 0.5 inside corners where the
#                        bar meets the square (the 1 mm cutter's radius), the main plate's seat opened to match
#   true_rim(J, log)     P97-P100: the main plate's rim a true r 66 circle (its 13 smooth dots sagged up to 83 µm between them) and
#                        every plate edge that runs along the rim snapped onto it (dents of 0.15-0.24 mm in the rim plate and the
#                        crescent bridge); only edge points running along the rim move, so a plate's corner at the rim and the gap
#                        to its neighbour stay as they are
#   rebuild(J, log)      the main plate's pockets through the level model with its round cuts (recesses, bearing seats, pilots)
#                        held as fixed walls: graded weld, ledge starts faired (onewall), pockets written back around those cuts
#   python3 mainplate.py IN.json OUT.json
import json, sys, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, union, diff, inter, offset, simplify, dots_sharp, spline_poly
import fair as FA, smooth as SM, onewall as OW, plate_clean as PC

R_RIM = 66.0
SNAP = (0.30, 0.60)         # an edge point within 0.30 mm of the rim goes onto it, one 0.60 mm off stays, between it moves part way
ALONG = (10.0, 25.0)        # ... and only where the edge runs along the rim: within 10 deg of it in full, fading out by 25 deg
RIM_SNAP = (0.10, 0.15)     # rebuild(): a pocket wall within 0.10 mm of the rim goes onto it (part way to 0.15)
CIRCLE_SNAP = (0.03, 0.045) # ... and within 30 µm of a round cut onto that cut (part way to 45 µm)

def _sketch(J, pid):
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid)
    return d, next(k for k in st['sketches'] if k['id'] == d['sketch'])

def _poly(k):
    pts = [(p['u'], p['v']) for p in k['points']]
    return np.asarray(spline_poly(k['points']), float) if any(p.get('smooth') for p in k['points']) else np.array(pts, float)

# ---------- P91: one cap ----------
def merge_caps(J, log, worm='D30', stem='D31'):
    from shapely.geometry import Polygon
    from shapely import affinity
    st = J['state']
    dw, kw = _sketch(J, worm); ds, ks = _sketch(J, stem)
    W_ = Polygon(_poly(kw)).buffer(0); S_ = Polygon(_poly(ks)).buffer(0)
    # the bar's axis: the long side of its minimum rotated rectangle, pointing from its far end toward the worm cap
    rr = np.array(S_.minimum_rotated_rectangle.exterior.coords[:4])
    e = [rr[1] - rr[0], rr[2] - rr[1]]; ax = max(e, key=lambda v: np.hypot(*v)); ax = ax / np.hypot(*ax)
    if np.dot(np.array(W_.centroid.coords[0]) - np.array(S_.centroid.coords[0]), ax) < 0: ax = -ax
    gap = W_.distance(S_)
    bar = S_.union(affinity.translate(S_, *(ax * (gap + 1.0))))          # the bar carried on straight into the square
    merged = W_.union(bar).buffer(0.5, quad_segs=64).buffer(-0.5, quad_segs=64)   # r 0.5 inside corners where they meet
    full = bar.difference(W_)                                            # the bar part, full thickness
    thin = merged.difference(full)                                       # the worm end (and the two corner fillets)
    thin = max(getattr(thin, 'geoms', [thin]), key=lambda g: g.area)     # (specks where the two outlines touch dropped)
    if merged.geom_type != 'Polygon': merged = max(merged.geoms, key=lambda g: g.area)
    fillets = thin.difference(W_)
    # the merged part keeps the stem cap's id, plane and stock
    ks['points'] = dots_sharp(simplify(np.vstack([np.array(merged.exterior.coords[:-1]), np.array(merged.exterior.coords[:1])]), 0.0002)[:-1])
    ds['name'] = ('Worm and stem cap (one part: a flat bar on the stem in its groove and a square over the worm, flush with the plate, '
                  'clamped by the motion-works plate; the worm end milled 2.25 mm thinner from underneath to sit on the worm seat)')
    pocket = offset([P(np.array(thin.exterior.coords[:-1]))], 0.5)
    pocket = diff(pocket, [P(np.array(g.exterior.coords[:-1])) for g in getattr(full, 'geoms', [full])])
    pk = max(pocket, key=lambda q: abs(__import__('pyclipper').Area(q)))
    sid = 'K' + str(max(int(k['id'][1:]) for k in st['sketches'] if k['id'][1:].isdigit()) + 1)
    st['sketches'].append({'id': sid, 'name': 'Worm end, from underneath', 'plane': dict(ks['plane']), 'closed': True,
                           'points': dots_sharp(F(pk))})
    cid = next(PC.next_cut_id(J))
    ds['cuts'] = (ds.get('cuts') or []) + [{'id': cid, 'kind': 'pocket', 'sketch': sid, 'from': 'front', 'depth': round(9.9 - ks['plane']['offset'], 4),
                                            'name': 'Worm end, 2.25 thinner from underneath (sits on the worm seat at 9.90)'}]
    # the worm cap goes; its pins, colour and project entry move or go with it
    st['drawn'] = [x for x in st['drawn'] if x['id'] != worm]
    st['sketches'] = [k for k in st['sketches'] if k['id'] != kw['id']]
    for p in st['pins']:
        if p.get('part') == worm: p['part'] = stem
    cols = J.get('project', {}).get('decor', {}).get('colors', {})
    cols.pop(worm, None)
    if isinstance(J.get('parts'), list): J['parts'] = [x for x in J['parts'] if x.get('id') != worm]
    # the main plate's worm seat (floor 9.90) takes the two corner fillets
    d1 = next(x for x in st['drawn'] if x['id'] == 'D1'); SK = {k['id']: k for k in st['sketches']}
    seat = next(c for c in d1['cuts'] if c.get('kind') == 'pocket' and abs(c.get('depth', 0) - 2.8) < 1e-6 and 'worm cap' in (c.get('name') or ''))
    kk = SK[seat['sketch']]
    reg = union([P(_poly(kk))], [P(np.array(g.exterior.coords[:-1])) for g in getattr(fillets, 'geoms', [fillets]) if g.area > 1e-6])
    reg = offset(offset(reg, 0.002), -0.002)
    kk['points'] = dots_sharp(F(max(reg, key=lambda q: abs(__import__('pyclipper').Area(q)))))
    seat['name'] = 'Seat for the worm end of the worm and stem cap (floor 9.90)'
    log.append(f'caps: {worm} folded into {stem} ({merged.area:.2f} mm², gap of {gap:.2f} mm bridged inside the stem groove; '
               f'worm end 2.25 mm thinner from underneath; corner fillets {fillets.area:.3f} mm² added to the worm seat)')

# ---------- P97-P100: the rim ----------
def snap_rim(Q):
    """an outline's points that run along the rim, onto r 66 (graded, so an edge leaves the rim in a curve)"""
    Qd = OW.densify(Q, 0.3); r = np.hypot(Qd[:, 0], Qd[:, 1]); d = R_RIM - r
    t = np.roll(Qd, -1, 0) - np.roll(Qd, 1, 0); t = t / np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-12)[:, None]
    ang = np.degrees(np.arcsin(np.clip(np.abs((t * Qd).sum(1) / np.maximum(r, 1e-9)), 0, 1)))
    f = SM.smoothstep(np.clip((SNAP[1] - np.abs(d)) / (SNAP[1] - SNAP[0]), 0, 1))
    g = SM.smoothstep(np.clip((ALONG[1] - ang) / (ALONG[1] - ALONG[0]), 0, 1))
    w = f * g
    if not (w > 0).any(): return Q, 0.0
    Qn = Qd * ((r + w * d) / r)[:, None]
    return Qn, float(np.abs(w * d).max())

def true_rim(J, log, pids=('D6', 'D5', 'D2', 'D3')):
    d1, k1 = _sketch(J, 'D1')
    n = 4 * math.ceil(math.pi * R_RIM / 0.6)
    k1['points'] = dots_sharp(np.array([[R_RIM * math.cos(2 * math.pi * i / n), R_RIM * math.sin(2 * math.pi * i / n)] for i in range(n)]))
    # the main plate's pockets that ran out past the old rim (its sag left them ending 0-83 µm inside r 66): carried out past the true
    # rim, so no sliver of plate is left between a pocket and the rim
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; carried = 0
    for c in d1.get('cuts') or []:
        if c.get('kind') != 'pocket' or c.get('sketch') not in SK: continue
        kk = SK[c['sketch']]; Q = _poly(kk); r = np.hypot(Q[:, 0], Q[:, 1])
        m = r > R_RIM - 0.15
        if not m.any() or kk.get('smooth'): continue
        Q = Q.copy(); Q[m] *= ((np.maximum(r[m], R_RIM) + 0.25) / r[m])[:, None]
        kk['points'] = dots_sharp(Q); carried += 1
    out = []
    for pid in pids:
        d, k = _sketch(J, pid)
        Q = _poly(k); Qn, mv = snap_rim(Q)
        if mv <= 0: continue
        k['points'] = dots_sharp(simplify(np.vstack([Qn, Qn[:1]]), 0.0002)[:-1])
        out.append(f'{pid} {mv * 1000:.0f} µm')
    log.append(f'rim: main plate a true r {R_RIM:g} circle ({n} sides of 0.3 mm), {carried} of its pockets carried out past it; rims snapped onto it, largest move: ' + ', '.join(out))

# ---------- the main plate's pockets round its fixed cuts ----------
def rest_layers(pl):
    """the plate's other cuts (recesses, bearing seats with their seats, pilots, countersinks) as (floor level, region), as the sim draws them"""
    out = []
    for c in pl.rest:
        at = c.get('at')
        if not at or not c.get('d'): continue
        D = pl.T if c.get('depth') is None else min(pl.T, max(0.0, c['depth']))
        out.append((round(pl.T - D, 4), [P(PC.ring_sim(at, c['d'] / 2))]))
        if c.get('seat') and c['seat'].get('d', 0) > c['d'] and c['seat'].get('depth', 0) > 0:
            out.append((round(pl.T - min(D, c['seat']['depth']), 4), [P(PC.ring_sim(at, c['seat']['d'] / 2))]))
    return out

def rebuild(J, log, pid='D1'):
    pl = FA.Plate(J, pid)
    rl = rest_layers(pl)
    Ls = sorted(set(pl.L) | {L for L, _ in rl})
    A, fixed, prev = [], [], pl.outside
    for L in Ls:
        here = [q for L2, g in rl if L2 <= L + 1e-9 for q in g]
        prev = union(prev, *[p for p, _ in pl.by.get(L, [])], here); A.append(prev)
        fixed.append(union(here) if here else [])
    pl.L, pl.A = Ls, A
    KO, MM, NB = SM.setup(J, pid, pl)
    # pockets drawn to the old outlines: onto the true rim (they followed its 83 µm sag) and onto the round cuts as the sim now draws
    # them (they followed 72-sided circles, up to 24 µm inside the true ones between corners); then the graded weld for what is left
    rim = [P(np.array(PC.ring_sim((0.0, 0.0), R_RIM)))]
    circ = union(*[g for _, g in rl]) if rl else []
    snapped = 0
    for i in range(len(A)):
        fb = SM.region(offset(KO[i], 0.05)) if KO[i] else None
        A[i], n1 = OW.weld_level(A[i], rim, fb, *RIM_SNAP)
        if circ: A[i], n2 = OW.weld_level(A[i], circ, fb, *CIRCLE_SNAP)
        else: n2 = 0
        A[i] = SM.clean_level(union(A[i], A[i - 1]) if i else A[i]); snapped += n1 + n2
    A, moved = OW.regrade_levels(A, KO)
    A, cut, fill = OW.fair_levels(A, KO)
    FA.write_back(J, pl, A, fixed=fixed)
    SM.fold_slivers(J, pid, A)
    log.append(f'rebuild {pid}: {len(pl.by)} pocket depths and {len(Ls) - len(pl.by)} more from its round cuts; {snapped} wall points onto the rim or a round cut; graded weld ({moved} points), '
               f'ledge starts faired (deepest cut {cut * 1000:.0f} µm, fill {fill * 1000:.0f} µm), pockets written back round the round cuts')
    return A

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    merge_caps(J, log); true_rim(J, log); rebuild(J, log)
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
