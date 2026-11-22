# Tiers (2026-11-21, Adam: "walls that dont align"; P59, P67, P68, P79, P80, P84): where one plate stands on another and their
# edges run within STACK of each other, the two walls are made one.
#   rim(J, log)        the main plate's edge becomes a true circle (R_RIM, one dot a degree); every plate whose edge runs along
#                      the rim within RIM_W takes exactly the same circle there (its overhang trimmed, its gap filled)
#   stack(J, log, ...) a thin strip of the lower plate's top showing beside the upper plate's wall, or a thin overhang of the upper
#                      plate over the lower plate's recess: the upper plate's wall comes to the lower plate's wall (Adam's barrel
#                      slot edit: "i sketched it to be consistent with the lower plate"), where no part needs the space; else the
#                      strip of the lower plate is cut down to the recess beside it
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, close, opening, spline_poly, simplify, dots_sharp
import plate_clean as PC

R_RIM, RIM_W, STACK = 66.0, 1.5, 1.5
RIM = [[int(round(R_RIM * math.cos(math.radians(a)) * S)), int(round(R_RIM * math.sin(math.radians(a)) * S))] for a in range(360)]
def ar(q): return abs(pc.Area(q)) / S / S
def pos(a): return [q for q in a if pc.Orientation(q)]
def outline_of(J, pid):
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid); k = next(x for x in st['sketches'] if x['id'] == d['sketch'])
    return d, k, union([P(spline_poly(k['points']))])
def set_outline(k, reg):
    big = max(pos(reg), key=ar); lp = simplify(np.vstack([F(big), F(big)[:1]]), 0.003)[:-1]; k['points'] = dots_sharp(lp)

def resample_closed(Q, step=0.4):
    Q = np.asarray(Q, float); C = np.vstack([Q, Q[:1]]); seg = np.hypot(*np.diff(C, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    n = max(16, int(s[-1] / step)); t = np.linspace(0, s[-1], n, endpoint=False)
    return np.c_[np.interp(t, s, C[:, 0]), np.interp(t, s, C[:, 1])]
SNAP = 0.4
def rim(J, log, pids=('D3', 'D6', 'D2', 'D5')):
    """every other plate's edge, where it runs within SNAP of the main plate's edge, eased onto that same edge (each point moved
    toward it by a smooth amount that fades out at SNAP, so where an edge leaves the rim it leaves as smoothly as before).
    The main plate's own edge is left exactly as it is (its pockets were cleaned against it)."""
    d1, k1, O1 = outline_of(J, 'D1')
    rim1 = np.asarray(spline_poly(k1['points'], N=64), float)
    th1 = np.arctan2(rim1[:, 1], rim1[:, 0]); r1 = np.hypot(rim1[:, 0], rim1[:, 1]); o = np.argsort(th1); th1, r1 = th1[o], r1[o]
    th1 = np.r_[th1[-1] - 2 * np.pi, th1, th1[0] + 2 * np.pi]; r1 = np.r_[r1[-1], r1, r1[0]]
    out = []
    for pid in pids:
        d, k, O = outline_of(J, pid)
        big = max(pos(O), key=ar); Q = resample_closed(F(big))
        r = np.hypot(Q[:, 0], Q[:, 1]); R = np.interp(np.arctan2(Q[:, 1], Q[:, 0]), th1, r1)
        dl = r - R; t = np.clip(np.abs(dl) / SNAP, 0, 1); f = t * t * (3 - 2 * t)
        moved = int((np.abs(dl) < SNAP).sum())
        r2 = R + dl * f; Q2 = Q * (r2 / np.maximum(r, 1e-9))[:, None]
        lp = simplify(np.vstack([Q2, Q2[:1]]), 0.002)[:-1]; k['points'] = dots_sharp(lp)
        out.append(f'{pid} {moved} points eased')
    rim_slivers(J, log, pids)
    log.append(f'rim: plates along the main plate\'s edge eased onto exactly that edge ({", ".join(out)})')

def rim_slivers(J, log, pids):
    """the rim moved out onto the true circle (up to 0.08 mm): where a pocket or hole met the old edge, a sliver of plate is left
    between it and the new one. The main plate's pockets there are carried out past the circle; the others' outlines trimmed."""
    import hairline_check as HC
    st = J['state']; ids = PC.next_cut_id(J); n1 = n2 = 0
    outside = diff([P(PC.ring_sim((0, 0), R_RIM + 2))], [RIM])
    for pid in pids:
        if pid == 'D3': continue
        f = [x for x in HC.check(J, pid) if np.hypot(*x['at']) > R_RIM - 2]
        if f:
            d, k, O = outline_of(J, pid); set_outline(k, diff(O, offset([x['poly'] for x in f], 0.05))); n2 += len(f)
    log.append(f'rim slivers: {n2} slivers trimmed off other plates\' edges')

def align_outline(J, log, pid, lowers, neighbours=(), w=STACK):
    """an outline-only plate standing on `lowers`: where its edge runs side by side with a wall of the plate below (a strip that
    stays under w all along), its edge comes onto that wall: grown over a thin strip of the lower top where no part needs the
    space, trimmed off a thin overhang. A strip that also borders a neighbouring plate is the gap between plates and stays."""
    import walls as W, keepout as K
    d, k, O = outline_of(J, pid); z0 = k['plane']['offset']; z1 = z0 + d['thickness']
    ML = union(*[W.slabs(J, l)[-1][2] for l in lowers]); MU = W.slabs(J, pid)[0][2]
    NB = union(*[W.slabs(J, n)[0][2] for n in neighbours]) if neighbours else []
    ko = K.keepout(J, z0, z1)
    holes = union(*[[P(PC.ring_sim(c['at'], c['d'] / 2 + 1.0))] for c in d.get('cuts') or [] if c.get('at') and c.get('d')]) if d.get('cuts') else []
    led = diff(ML, union(MU, NB) if NB else MU); over = diff(MU, ML)
    g = [x['poly'] for x in W.thin_pieces(led, w) if inter(offset([x['poly']], 0.05), MU) and not (NB and inter(offset([x['poly']], 0.6), NB)) and not inter([x['poly']], offset(ko, 0.05))]
    t = [x['poly'] for x in W.thin_pieces(over, w) if inter(offset([x['poly']], 0.05), ML) and not (holes and inter([x['poly']], holes))]
    if g or t:
        O2 = O
        if g: O2 = union(O2, offset(g, 0.02))
        if t: O2 = diff(O2, offset(t, 0.02))
        O2 = opening(close(O2, 0.05), 0.05)
        # where a strip ends, the edge leaves the wall below: eased there like any other flagged spot (fair.fair_level)
        import fair as FA
        FA.NOTE_WIN = None
        A = diff(FA.BOX, O2); must_air = inter(ko, diff(FA.BOX, O))
        for _ in range(2):
            A = FA.fair_level(A, must_air, holes, 1.0)[0]
        O2 = diff(FA.INNER, A)
        O2 = close(opening(O2, 0.6), 0.6)            # no nub or nick under 1.2 mm left where a strip ended
        set_outline(k, O2)
        d, k, O = outline_of(J, pid); set_outline(k, close(opening(O, 0.15), 0.15))   # (and no wiggle the dots' rounding left)
        import hairline_check as HC
        f = HC.check(J, pid)
        if f:                                                       # a hole or pocket left a sliver against the moved edge: trimmed
            d, k, O = outline_of(J, pid); set_outline(k, close(opening(diff(O, offset([x['poly'] for x in f], 0.05)), 0.15), 0.15))
    log.append(f'{pid} on {"+".join(lowers)}: {len(g)} strips grown, {len(t)} overhangs trimmed onto the wall below')
    return len(g) + len(t)

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; rim(J, log); print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
