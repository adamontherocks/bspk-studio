# Main plate resolver (2026-11-22; the resolver path, VISION.md §7 R2; intent in intent/main-plate.md).
# Builds the main plate from scratch, every time, from what it is for:
#   - the outline: the true r 66 rim (mainplate.true_rim) and the worm and stem cap as one part (mainplate.merge_caps);
#   - the real cuts: wheel recesses, the bigger bearings and the windows, stem, worm and crown cuts (drilled holes keep their own cuts);
#   - rule R4 per floor, deepest first: plate under 2.4 mm comes down (a closing of the air by r 1.2), islands under 40 mm² come down,
#     micro spikes and notches under 0.2 mm go. The real cuts stay exact: the rounding only adds air away from them and overlaps into
#     them, because re-drawing a circle or the rim through a closing left a 2 µm zigzag along every round wall;
#   - the floors made one wall where they nearly coincide (onewall: graded weld, ledge starts faired);
#   - written as one region per tier (fair.write_tiers), the tiers carrying every non-drilled cut, so nothing is drawn twice.
# Then the plates standing on it get their rims onto r 66 too (mainplate.snap_rims). Each corner is rounded once, at the floor where it
# first appears (a thin re-rounding against a rounding below is dropped; a thin piece cutting a hairline of plate away stays).
# Status (Adam's scene of 2026-11-22): no slivers, no walls drawn twice, 1 notch of 1 µm or more on the main plate, Z1 clean, no clashes
# in the sim. Costs: Run checks about 25 s (tiers carry about 52,000 dots); a recess no longer follows its arbor until this reruns (R6).
#   python3 resolve_main.py IN.json OUT.json
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pyclipper as pc
from pk2 import P, F, S, union, diff, inter, offset, close, opening, spline_poly
import numpy as np
import mainplate as MP, plate_clean as PC, fair as FA, smooth as SM, onewall as OW

NEEDS = 0.15                # a piece the rounding adds must be this wide somewhere to count (narrower everywhere: a corner rounded again)
FORK_SWING = 3.2            # the pallet fork's swing either way, degrees (the largest recorded, escapement2)
BRIDGE = 0.75               # ... unless air runs along this much of its edge (both sides): then it cuts a hairline of plate and stays

def levels(J, d, k):
    st = J['state']; SK = {s['id']: s for s in st['sketches']}; T = d['thickness']
    keep = [c for c in d['cuts'] if not PC.is_patch(c)]
    outline = union([P(spline_poly(k['points']))])
    outside = diff([P([[-200, -200], [200, -200], [200, 200], [-200, 200]])], outline)
    func = [(PC.cut_paths(c, SK), round(T - (T if c.get('depth') is None else min(T, max(0, c['depth']))), 4))
            for c in keep if not PC.is_drilled(c) and c.get('from') == 'back']
    Ls = sorted({f for _, f in func if f < T - 1e-6}); prev, A2s, reals, towers = [], [], [], 0
    rounded = []                                                           # air the rounding has added on the floors below
    for L in Ls:
        cuts_here = union(outside, *[p for p, f in func if f <= L + 1e-6])
        real = union(cuts_here, prev)
        C = close(real, PC.R)
        big = [p for p in C if pc.Orientation(p) or abs(pc.Area(p)) / S / S >= PC.TOWER_A]; towers += len(C) - len(big)
        C = union(big, real)
        C = union(opening(close(C, 0.1), 0.1), real)
        # one rounding per corner: a corner is rounded at the floor where it first appears, and that rounding carries up. What the
        # rounding adds here is kept as whole pieces, tips and all, unless the piece is thin everywhere (under NEEDS) and lies against a
        # rounding a floor below already made: that is the same corner rounded again a hair differently, so the one below stands.
        # A thin piece with air along both sides cuts a hairline of plate away, and stays.
        raw = diff(C, real)
        def needed(q):
            if opening([q], NEEDS / 2): return True                      # somewhere wide enough: a real takedown
            if not rounded or not inter(offset([q], 0.01), rounded): return True   # a corner's first rounding
            Q = F(q); per = float(np.hypot(*(np.roll(Q, -1, 0) - Q).T).sum())
            near = inter(offset([q], 0.004), inter(real, offset([q], 0.01)))   # the air within 4 µm of its edge
            adj = sum(abs(pc.Area(p)) for p in near) / S / S / 0.004       # ~ the length of its edge that has air beside it
            return adj > BRIDGE * per
        outers = [q for q in raw if pc.Orientation(q) and needed(q)]
        add = inter(raw, outers) if outers else []
        A2 = union(real, inter(offset(add, 0.01), C)) if add else real
        rounded = diff(A2, cuts_here)
        A2s.append(A2); reals.append(real); prev = A2
    return keep, Ls, A2s, reals, towers

def recesses_from_parts(J, log):
    """the recesses for drawn moving parts, from those parts as they are today (rule R1, the inventory's decision 2): the escape
    wheel's tips + 0.75; the pallet fork's swept outline (its arbor, swinging ±3.2°) + 0.75, leaving out what lies over the
    balance well (the well's own recess covers that)"""
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; dr = {x['id']: x for x in st['drawn']}; pos = st['pos']
    d1 = dr['D1']; out = []
    def poly(pid): return np.asarray(spline_poly(SK[dr[pid]['sketch']]['points']))
    def rot(Q, c, deg):
        a = np.radians(deg); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]); return (Q - c) @ R.T + c
    esc = np.array(pos['escape']); fork = np.array(pos['fork']); bal = np.array(pos['balance'])
    well = next(c for c in d1['cuts'] if (c.get('name') or '').startswith('Recess · balance well'))
    r_esc = np.hypot(*(poly('D25') - esc).T).max()
    F_ = np.vstack([rot(poly('D26'), fork, a) for a in np.linspace(-FORK_SWING, FORK_SWING, 9)])
    keep_ = np.hypot(*(F_ - bal).T) > well['d'] / 2 - 0.75
    r_fork = np.hypot(*(F_[keep_] - fork).T).max()
    for name, r in (('Recess · escape wheel', r_esc), ('Recess · pallet fork sweep', r_fork)):
        c = next(x for x in d1['cuts'] if (x.get('name') or '').startswith(name))
        new = round(2 * (r + 0.75), 3); out.append(f"{name.split('· ')[1]} Ø{c['d']} -> Ø{new}"); c['d'] = new
    log.append('recesses from the parts: ' + ', '.join(out))

def resolve(J, log):
    MP.merge_caps(J, log); MP.true_rim(J, log, pids=()); recesses_from_parts(J, log)
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == 'D1'); k = next(s for s in st['sketches'] if s['id'] == d['sketch'])
    keep, Ls, A2s, reals, towers = levels(J, d, k)
    for c in d['cuts']:                                                    # the old clean pockets and the cuts the tiers now carry go
        if c.get('kind') == 'pocket' and (PC.is_patch(c) or not (PC.is_drilled(c) or c.get('from') != 'back')):
            st['sketches'] = [s for s in st['sketches'] if s['id'] != c['sketch']]
    d['cuts'] = [c for c in keep if PC.is_drilled(c) or c.get('from') != 'back']
    pl = FA.Plate(J, 'D1'); pl.pockets = []; pl.rest = d['cuts']; pl.L = Ls; pl.by = {}; pl.A = A2s
    KO, MM, NB = SM.setup(J, 'D1', pl)
    A2s, moved = OW.regrade_levels(A2s, KO); A2s, cut, fill = OW.fair_levels(A2s, KO)
    new = FA.write_tiers(J, pl, A2s)
    MP.snap_rims(J, log=log)                                               # the plates standing on it: their rims onto r 66 too
    log.append(f'resolve main plate: {len(Ls)} floors, {towers} towers taken down, weld {moved} points, fairing cut {cut * 1000:.0f} µm '
               f'fill {fill * 1000:.0f} µm, {len(new)} tier pockets')

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    resolve(J, log); print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
