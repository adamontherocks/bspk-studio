# Hairline check (2026-11-21, Adam's notes P70-P72 "fragment"): rebuilds each plate the way the sim does (index.html cutLayers /
# buildPlate: holes as 72-sided rings, pockets on the polyspline, one section per slab between cut depths) and flags any sliver of
# material thinner than 0.2 mm in any slab. The raster checks (0.05 mm pixels) can't see these; the sim draws them as fragments.
#
#   python3 hairline_check.py SCENE.json [D1,D3,...]
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, opening, spline_poly

def ring(c, r):                 # the sim's own circle (plate_clean.ring_sim)
    from plate_clean import ring_sim
    return ring_sim(c, r)
def layers(d, SK):
    T = d['thickness']; out = []
    for c in d.get('cuts') or []:
        D = T if c.get('depth') is None else min(T, max(0, c['depth']))
        iv = (T - min(T, D), T) if c.get('from') == 'back' else (0, min(T, D))
        if c['kind'] == 'pocket':
            k = SK.get(c['sketch'])
            if k and len(k['points']) >= 3: out.append((iv, [P(spline_poly(k['points']))]))
            continue
        if not c.get('d') or not c.get('at'): continue
        out.append((iv, [P(ring(c['at'], c['d'] / 2))]))
        if c.get('seat') and c['seat'].get('d', 0) > c['d']:
            sd = min(D, c['seat']['depth']); siv = (T - sd, T) if c.get('from') == 'back' else (0, sd)
            out.append((siv, [P(ring(c['at'], c['seat']['d'] / 2))]))
    return out
def check(J, pid, thin=0.1):
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; d = next(x for x in st['drawn'] if x['id'] == pid)
    k = SK[d['sketch']]; z0 = k['plane']['offset']; T = d['thickness']
    outline = union([P(spline_poly(k['points']))]); L = layers(d, SK)
    cuts_at = sorted({0.0, T} | {min(T, max(0.0, v)) for iv, _ in L for v in iv})
    found = []
    for a, b in zip(cuts_at[:-1], cuts_at[1:]):
        if b - a < 1e-6: continue
        mid = (a + b) / 2
        act = [p for iv, ps in L if iv[0] <= mid <= iv[1] for p in ps]
        # the sim turns every cut the same way round before combining them (sameWay), then subtracts
        act = [p if pc.Orientation(p) else p[::-1] for p in act]
        mat = diff(outline, union(act)) if act else outline
        sl = diff(mat, opening(mat, thin))
        for q in sl:
            if not pc.Orientation(q): continue
            ar = abs(pc.Area(q)) / S / S
            if ar < 1e-4: continue
            Pq = F(q); per = float(np.hypot(*(np.roll(Pq, -1, 0) - Pq).T).sum()); th = 2 * ar / max(per, 1e-9)
            if th < 0.002: continue                                     # zero-width overlaps of coincident edges (numerical ghosts the sim can't draw)
            c = Pq.mean(0)
            found.append(dict(z=round(z0 + mid, 3), at=[round(float(c[0]), 2), round(float(c[1]), 2)], area=round(ar, 4), thick=round(th, 4), slab=(a, b), poly=q))
    return found

def sweep(J, pid, log, rounds=6):
    """cut every sliver down to the bottom of the slab it stands in (from the top), and check again, until none are left"""
    from pk2 import offset, union as _u
    import plate_clean as PC
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid); k = next(s_ for s_ in st['sketches'] if s_['id'] == d['sketch'])
    z0, T = k['plane']['offset'], d['thickness']; ids = PC.next_cut_id(J); n = 0
    for _ in range(rounds):
        f = check(J, pid)
        if not f: break
        for x in f:
            a = x['slab'][0]
            for q in offset([x['poly']], 0.25 if x['area'] < 0.02 else 0.15):   # a compact speck gets a round cover
                if not pc.Orientation(q): continue
                sid = f'KH{pid}_{len(st["sketches"])}'
                st['sketches'].append({'id': sid, 'name': f'Hairline {pid}', 'plane': {'axis': 'z', 'offset': z0}, 'closed': True,
                                       'points': [{'u': round(float(u), 4), 'v': round(float(v), 4), 'smooth': False} for u, v in F(q)]})
                d['cuts'].append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(T - a, 4),
                                  'name': f'Clean: hairline sliver taken down to {z0 + a:.2f}'})
                n += 1
    left = len(check(J, pid))
    log.append(f'hairlines {pid}: {n} slivers under 0.2 mm cut down to the floor beside them; {left} left')
    return left

if __name__ == '__main__':
    J = json.load(open(sys.argv[1]))
    ids = sys.argv[2].split(',') if len(sys.argv) > 2 else [d['id'] for d in J['state']['drawn'] if d.get('mill') and d.get('cuts')]
    tot = 0
    for pid in ids:
        f = check(J, pid); tot += len(f)
        locs = sorted({tuple(x['at']) for x in f})
        print(pid, f'{len(f)} slivers in slabs, {len(locs)} spots', locs[:30])
    print('TOTAL', tot)

def steps(J, pid, w=1.0):
    """stacked walls: in consecutive slabs, a ledge thinner than w (the top of one slab showing beside the wall of the next) is
    a wall that steps by less than w instead of running straight; returns [(z, at, area)]"""
    from pk2 import offset
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; d = next(x for x in st['drawn'] if x['id'] == pid)
    k = SK[d['sketch']]; z0 = k['plane']['offset']; T = d['thickness']
    outline = union([P(spline_poly(k['points']))]); L = layers(d, SK)
    cuts_at = sorted({0.0, T} | {min(T, max(0.0, v)) for iv, _ in L for v in iv})
    mats = []
    for a, b in zip(cuts_at[:-1], cuts_at[1:]):
        if b - a < 1e-6: continue
        mid = (a + b) / 2; act = [p if pc.Orientation(p) else p[::-1] for iv, ps in L if iv[0] <= mid <= iv[1] for p in ps]
        mats.append((b, diff(outline, union(act)) if act else outline))
    out = []
    for (zb, m0), (_, m1) in zip(mats[:-1], mats[1:]):
        ledge = diff(m0, m1)                                    # floor at the top of this slab
        thin = inter(diff(ledge, opening(ledge, w / 2)), offset(m1, 0.05))
        for q in thin:
            if pc.Orientation(q) and abs(pc.Area(q)) / S / S > 0.02:
                c = F(q).mean(0); out.append((round(z0 + zb, 2), (round(float(c[0]), 1), round(float(c[1]), 1)), round(abs(pc.Area(q)) / S / S, 3)))
    return out
