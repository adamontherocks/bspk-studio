# Wall smoothing (2026-11-21): the correcting half of flow.py, a standing step of the round trip (Adam sketches, Claude makes it
# correct; correct includes walls whose radius changes gradually as you follow them around from above).
# Every wall of a plate's levels is filtered along its own length, so a curve broken into flats and corners, an S-bend or a bump
# becomes one steady curve. The filter passes shapes longer than a few mm untouched (straight walls stay straight, true arcs
# keep their radius) and removes the short ones (bumps, facets, wiggles shorter than about 2*SIG).
# Limits, so the design stays Adam's and nothing gets worse:
#   - no point of a wall moves more than DMAX
#   - a wall never comes closer than CLEAR to what a part needs (the keep-out, which already holds the sim's 0.5 mm gap), never
#     into the boss round a hole, never into the gap round a neighbouring plate; where it already was closer, it stays put
#   - the plate's rim, edges lined up on the plate below and the edge of a neighbouring plate's gap stay where they are
#   - where two levels share a wall (one wall running straight down past a floor), both move together, so it stays one wall
#   smooth_plate(J, log, pid)       redraws the plate's pockets (fair.write_back)
#   python3 smooth.py IN.json OUT.json [D3]
import json, math, sys, os
import numpy as np
import pyclipper as pc
from scipy import ndimage
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, spline_poly
import fair as FA, keepout as K, walls as W

SIG, DMAX, CLEAR, RAMP, H = 1.0, 0.5, 0.55, 1.0, 0.05
SPECK = 0.1                       # material narrower than 2*SPECK (the sliver check's rule) goes
SHARE, PIN = 0.04, 0.02          # a point this close to a lower level's wall shares it; this close to a fixed edge stays put

def region(paths):
    """clipper paths (properly nested rings, as union() returns them) -> a shapely region (even-odd)"""
    g = None
    for q in paths:
        Q = F(q)
        if len(Q) < 3: continue
        p = Polygon(Q).buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    g = g if g is not None else Polygon()
    shapely.prepare(g)                                   # point tests run many times per wall
    return g

def clean_level(paths, min_area=0.01):
    """a level's air without specks: loops under min_area (air specks in plate, or plate specks in air) are dropped"""
    return union([q for q in paths if abs(pc.Area(q)) / S / S >= min_area])

def samples(paths, step=0.02):
    pts = [W.resample(F(q), step)[0] for q in paths if len(q) >= 3]
    return np.vstack(pts) if pts else np.zeros((0, 2))

def lowpass(R, h, sig=SIG):
    """the wall's shape with everything shorter than about 2*sig removed; arcs keep their radius (1-(1-g)^2 transfer)"""
    n = len(R); w = 2 * np.pi * np.fft.fftfreq(n, d=h); g = np.exp(-0.5 * (sig * w) ** 2); T = 1 - (1 - g) ** 2
    return np.c_[np.real(np.fft.ifft(np.fft.fft(R[:, 0]) * T)), np.real(np.fft.ifft(np.fft.fft(R[:, 1]) * T))]

def ring_dist(mask, h):
    """distance along a closed ring to the nearest True, and the index of that point"""
    n = len(mask)
    if not mask.any(): return np.full(n, 1e9), np.zeros(n, int)
    m3 = np.r_[mask, mask, mask]
    d, ind = ndimage.distance_transform_edt(~m3, return_indices=True)
    return d[n:2 * n] * h, ind[0][n:2 * n] % n

def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

ALPHA, NIT = 0.95, 60             # the smoother: each pass X = limits(ALPHA*lowpass(X) + (1-ALPHA)*original); shapes shorter than
SIG_P = 0.5                       #   about 4 mm are taken out, longer ones (straight runs, true arcs) kept

def smooth_ring(R, h, pinned, share, d_share, forbid):
    """displacement for one resampled ring: a constrained smoother. Each pass low-passes the wall and pulls it back toward where
    it was, then applies the limits: pinned points stay, shared points move as the level below moved them, nothing moves more
    than DMAX, a point that would cut into a limit is pushed back to it (so the wall wraps an obstacle in one smooth curve,
    like an elastic band round a peg), and a point already inside a limit never moves further in."""
    fixed = pinned                                             # (a pin wins over a shared wall: both levels carry the same pin)
    # forbid: one limit for the whole ring, or [(mask, limit), ...] (different points answer to different limits)
    groups = [] if forbid is None else ([(np.ones(len(R), bool), forbid)] if isinstance(forbid, tuple) else list(forbid))
    G = []
    for m, fb in groups:
        if fb is None or fb[0].is_empty or not m.any(): continue
        fg, fT, fpts = fb
        was = np.zeros(len(R), bool); was[m] = shapely.contains_xy(fg, R[m, 0], R[m, 1])
        vout = None
        if was.any():
            _, j = fT.query(R[was]); vout = fpts[j] - R[was]; vout /= np.maximum(np.hypot(*vout.T), 1e-9)[:, None]
        G.append((m, fg, fT, fpts, was, vout))
    was_any = np.zeros(len(R), bool)
    for g in G: was_any |= g[4]
    X = R.copy()
    def limits(X, final=False):
        d = X - R
        d[share] = d_share[share]; d[fixed] = 0
        d *= np.minimum(1, DMAX / np.maximum(np.hypot(*d.T), 1e-12))[:, None]
        for m, fg, fT, fpts, was, vout in G:
            if was.any():
                dn = (d[was] * vout).sum(1); d[was] -= np.minimum(dn, 0)[:, None] * vout
            free = m & ~(fixed | share | was_any)
            Y = R + d; bad = free.copy(); bad[free] = shapely.contains_xy(fg, Y[free, 0], Y[free, 1])
            if bad.any():
                _, j = fT.query(Y[bad]); v = fpts[j] - Y[bad]; nv = np.hypot(*v.T)[:, None]
                d[bad] += v + v / np.maximum(nv, 1e-9) * 0.004
                if final:
                    Y = R + d; still = bad.copy(); still[bad] = shapely.contains_xy(fg, Y[bad, 0], Y[bad, 1])
                    d[still] = 0
        return R + d
    for _ in range(NIT):
        X = limits(ALPHA * lowpass(X, h, SIG_P) + (1 - ALPHA) * R)
    X = limits(X, final=True)
    return X - R

def setup(J, pid, pl):
    """per level: KO (what parts need), MM (bosses round holes, the floor under a part sitting on the plate), NB (a neighbour's gap)"""
    st = J['state']; nL = len(pl.L); KO, MM = [], []
    ring = pl.holes_ring(1.0)
    NEIGH = {'D3': ['D6'], 'D6': ['D3']}.get(pid, [])
    NB = offset(union(*[m for n in NEIGH for _, _, m in W.slabs(J, n)]), K.EL['minGap']) if NEIGH else []
    for i in range(nL):
        za, zb = pl.band(i); ko = K.keepout(J, za, zb)
        KO.append(clean_level(inter(ko, pl.A[i])))
        mm = inter(ring, diff(FA.BOX, pl.A[i]))
        if i == 0:
            for d in st['drawn']:
                k = next((x for x in st['sketches'] if x['id'] == d['sketch']), None)
                if not k or d['id'] in K.PLATE_IDS or k['plane']['axis'] != 'z': continue
                if abs(k['plane']['offset'] - (pl.z0 + pl.L[1] if nL > 1 else -1)) < 0.01 or d['id'] == 'D29':
                    mm = union(mm, inter(union([P(spline_poly(k['points']))]), diff(FA.BOX, pl.A[0])))
        MM.append(mm)
    return KO, MM, NB

ON_TOP = {'D1': ('D3', 'D6')}        # plates whose bottom edge sits on this plate's walls: those walls stay put (at every level)

def smooth_plate(J, log, pid='D3', lower={'D3': 'D1'}, only=None):
    """only: [(x, y, r)] to redraw just the walls within r of those points (everything else stays exactly as it is)"""
    pl = FA.Plate(J, pid); nL = len(pl.L)
    if not nL: log.append(f'smooth {pid}: no levels'); return None
    KO, MM, NB = setup(J, pid, pl)
    st = J['state']; d1 = next(x for x in st['drawn'] if x['id'] == 'D1'); k1 = next(x for x in st['sketches'] if x['id'] == d1['sketch'])
    fixed = [union([P(spline_poly(k1['points']))])]                       # the movement's rim (the main plate's outline)
    if NB: fixed.append(NB)
    for up in ON_TOP.get(pid, ()): fixed.append(W.slabs(J, up)[0][2])
    fx = samples([q for g in fixed for q in g]); fxT = cKDTree(fx) if len(fx) else None
    lo = lower.get(pid)                                                   # edges lined up on the plate below (the bottom level only:
    lw = samples(W.slabs(J, lo)[-1][2]) if lo else np.zeros((0, 2))        #  higher walls sit over it, not on it)
    lwT = cKDTree(lw) if len(lw) else None
    F_ = []; prev = None; moved = []
    for i in range(nL):
        A = pl.A[i]
        # every wall keeps clear of the parts in its own band; a wall that runs on up past the next floor (it is also the next
        # level's wall) keeps clear of the parts in the bands above as well
        def lim(kos, extra=()):
            fpaths = union(offset(kos, CLEAR) if kos else [], MM[i], NB, *extra); fpts = samples(fpaths, 0.01)
            return (region(fpaths), cKDTree(fpts), fpts) if len(fpts) else None
        lim_own = lim(KO[i]); lim_up = lim(union(*[KO[j] for j in range(i, nL) if KO[j]])) if i + 1 < nL else lim_own
        upT = cKDTree(samples(pl.A[i + 1])) if i + 1 < nL else None
        rings, out = [], []
        cur_pts, cur_d = [], []
        for q in A:
            Q = F(q)
            per = float(np.hypot(*np.diff(np.vstack([Q, Q[:1]]), axis=0).T).sum())
            if per < 3.0 or np.abs(Q).max() > 150:                        # specks, and the far box round the plate
                out.append(q); continue
            R, h = W.resample(Q, H)
            pinned = (fxT.query(R)[0] < PIN) if fxT is not None else np.zeros(len(R), bool)
            if i == 0 and lwT is not None: pinned |= lwT.query(R)[0] < PIN
            if only:
                inside = np.zeros(len(R), bool)
                for x0, y0, r0 in only: inside |= np.hypot(R[:, 0] - x0, R[:, 1] - y0) < r0
                pinned |= ~inside
            if prev is not None:
                dd, ii = prev[0].query(R); share = dd < SHARE; d_share = prev[1][ii]
            else:
                share = np.zeros(len(R), bool); d_share = np.zeros_like(R)
            up = (upT.query(R)[0] < SHARE) if upT is not None else np.zeros(len(R), bool)
            d = smooth_ring(R, h, pinned, share, d_share, [(~up, lim_own), (up, lim_up)])
            Rn = R + d; cur_pts.append(R); cur_d.append(d); moved.append(np.hypot(*d.T).max())
            out.append(P(Rn))
        Fi = [q for q in union(out) if abs(pc.Area(q)) / S / S >= 0.01]      # (no specks: a loop a wall made crossing itself)
        if F_: Fi = union(Fi, F_[-1])                                     # deeper air stays inside shallower air
        Fi = diff(union(Fi, KO[i]) if KO[i] else Fi, MM[i]) if MM[i] else (union(Fi, KO[i]) if KO[i] else Fi)
        if NB: Fi = union(Fi, NB)
        F_.append(clean_level(Fi))
        allR = np.vstack(cur_pts) if cur_pts else np.zeros((0, 2)); allD = np.vstack(cur_d) if cur_d else np.zeros((0, 2))
        prev = (cKDTree(allR), allD) if len(allR) else None
    # slivers: material narrower than 0.2 mm left where a moved wall nearly meets another (the sim draws them as fragments)
    for i in range(nL):
        M = diff(FA.INNER, F_[i]); Mo = offset(offset(M, -SPECK), SPECK)
        F_[i] = diff(FA.BOX, Mo)                          # (rebuilt from the cleaned plate: adding thousands of wedges back can break the union)
        if i: F_[i] = union(F_[i], F_[i - 1])
        F_[i] = clean_level(F_[i])
    FA.write_back(J, pl, F_)
    # a sliver against a drilled hole (holes aren't in the levels): folded into the pocket beside it, at its level and above
    import hairline_check as HC
    L0 = list(pl.L); left = []
    for _ in range(3):
        sl = HC.check(J, pid); left = [x for x in sl if not any(L0[j] <= x['slab'][0] + 1e-6 for j in range(nL))]
        sl = [x for x in sl if x not in left]
        if not sl: break
        for x in sl:
            i = max(j for j in range(nL) if L0[j] <= x['slab'][0] + 1e-6)
            for j in range(i, nL): F_[j] = union(F_[j], offset([x['poly']], 0.01))
        pl = FA.Plate(J, pid); FA.write_back(J, pl, F_)
    if left: log.append(f'smooth {pid}: {len(left)} slivers below every pocket floor (between drilled holes), left for the sliver sweep')
    log.append(f'smooth {pid}: {nL} levels, walls low-passed at {SIG:g} mm (most a point moved: {max(moved) if moved else 0:.2f} mm, limit {DMAX:g}); '
               f'rim, edges on {lo or "-"}, shared walls and {CLEAR:g} mm off every keep-out held')
    return F_

def fold_slivers(J, pid, A, rounds=3):
    """after a write-back: any sliver the sim-exact check still finds (thinner than 0.2 mm, often against a drilled hole) is folded
    into the pocket beside it, at its level and above; returns how many are left (below every floor: between drilled holes)"""
    import hairline_check as HC
    pl = FA.Plate(J, pid); L0 = list(pl.L); nL = len(L0); left = []
    for r in range(rounds):
        sl = HC.check(J, pid); left = [x for x in sl if not any(L0[j] <= x['slab'][0] + 1e-6 for j in range(nL))]
        sl = [x for x in sl if x not in left]
        if not sl: break
        for x in sl:
            i = max(j for j in range(nL) if L0[j] <= x['slab'][0] + 1e-6)
            for j in range(i, nL): A[j] = union(A[j], offset([x['poly']], 0.01))
        pl = FA.Plate(J, pid); FA.write_back(J, pl, A)
    # one standing through every slab against the outline (the outline is rewritten each time and brings it back): trimmed off the
    # outline itself, written as it is (not simplified again)
    from pk2 import dots_sharp, P as _P
    sl = [x for x in HC.check(J, pid) if x['slab'][0] <= 1e-6]
    if sl:
        d = next(x for x in J['state']['drawn'] if x['id'] == pid); k = next(x for x in J['state']['sketches'] if x['id'] == d['sketch'])
        o = diff(union([_P(spline_poly(k['points']))]), offset([x['poly'] for x in sl], 0.005))
        big = max([q for q in o if pc.Orientation(q)], key=lambda q: abs(pc.Area(q)))
        k['points'] = dots_sharp(F(big))
    return len(left) + len(HC.check(J, pid))

# ---------- outlines of plates that are one level (the rim plate, the crescent bridge, the hand cock) ----------
WINDOW, RAMP_W = 4.0, 2.0           # outlines: redrawn within WINDOW mm of a flagged spot, faded back to as-is over RAMP_W
OUTLINE = {                       # pid: (plates it sits on, plates beside it at the same height)
    'D6': (('D1',), ('D3',)),
    'D5': (('D3', 'D6'), ('D2',)),
    'D2': (('D3', 'D6'), ('D5',)),
}
def smooth_outline(J, log, pid):
    from pk2 import simplify, dots_sharp
    import plate_clean as PC
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid); k = next(x for x in st['sketches'] if x['id'] == d['sketch'])
    z0, T = k['plane']['offset'], d['thickness']; below, beside = OUTLINE[pid]
    d1 = next(x for x in st['drawn'] if x['id'] == 'D1'); k1 = next(x for x in st['sketches'] if x['id'] == d1['sketch'])
    fixed = [union([P(spline_poly(k1['points']))])]                                   # the movement's rim
    lowers = []
    for b in below:                                                                  # walls of the plates it sits on
        sl = W.slabs(J, b); lowers.append(sl[-1][2])
    gap = offset(union(*[m for b in beside for _, _, m in W.slabs(J, b)]), K.EL['minGap']) if beside else []
    if gap: fixed.append(gap)
    fx = samples([q for g in fixed for q in g]); fxT = cKDTree(fx)
    # limits: material never reaches into what a part needs (keep-out + CLEAR) or the neighbour's gap; the bosses round its
    # screws and bearings stay inside it
    ko = K.keepout(J, z0, z0 + T)
    holes = union(*[[P(PC.ring_sim(c['at'], c['d'] / 2 + 1.0))] for c in d.get('cuts') or [] if c.get('at') and c.get('d')])
    out_lim = union(offset(ko, CLEAR) if ko else [], gap)
    outline = union([P(spline_poly(k['points']))])
    big = max([q for q in outline if pc.Orientation(q)], key=lambda q: abs(pc.Area(q)))
    R, h = W.resample(F(big), H)
    pinned = fxT.query(R)[0] < PIN
    # held on the walls below as well, except round Adam's notes: there an edge that was snapped partway onto a lower wall and
    # leaves it in a kink is let go, so it can run as one smooth curve (2026-11-22, P104-P106: "this should be a smooth consistent
    # radius")
    lw = samples([q for g in lowers for q in g]); onlow = cKDTree(lw).query(R)[0] < PIN if len(lw) else np.zeros(len(R), bool)
    near_note = np.zeros(len(R), bool)
    for p_ in st.get('pins', []):
        if p_.get('part') == pid: near_note |= np.hypot(R[:, 0] - p_['w'][0], R[:, 1] - p_['w'][1]) < WINDOW
    pinned |= onlow & ~near_note
    # an outline is one long edge mostly lying on the walls below: only the stretches round a flagged break or one of Adam's
    # wall notes are redrawn (everything else stays exactly as it is, so no new joins are made where nothing was wrong)
    import flow as FL
    spots = [np.asarray(f['at']) for f in FL.flow_loop(F(big))]
    spots += [np.asarray(p['w'][:2]) for p in st.get('pins', []) if p.get('part') == pid]
    win = np.zeros(len(R), bool)
    for c in spots:
        dd0 = np.hypot(*(R - c).T)
        if dd0.min() < 3.0: win |= dd0 < WINDOW
    if not win.any():
        log.append(f'smooth {pid} outline: nothing flagged, left as it is'); return
    dw, _ = ring_dist(win, h)
    pinned |= dw > RAMP_W                                   # outside the windows (and their ramps) nothing moves
    # the outline moving out must stay out of out_lim; moving in must stay out of the holes' bosses: one region, both sides
    fpaths = union(out_lim, holes)
    fpts = samples(fpaths, 0.01)
    forbid = (region(fpaths), cKDTree(fpts), fpts) if len(fpts) else None
    dd = smooth_ring(R, h, pinned, np.zeros(len(R), bool), np.zeros_like(R), forbid)
    ramp = smoothstep(1 - dw / RAMP_W)[:, None]; dd *= ramp     # fade the change out over the ramp
    Rn = R + dd
    lp = simplify(np.vstack([Rn, Rn[:1]]), 0.0002)[:-1]   # (0.2 µm: on a big radius 1 µm left 2.4 mm chords)
    k['points'] = dots_sharp(lp)
    # a speck of plate left between the new edge and a hole or pocket: trimmed off the outline
    import hairline_check as HC
    for _ in range(3):
        sl = HC.check(J, pid)
        if not sl: break
        o = union([P(spline_poly(k['points']))])
        o = diff(o, offset(union(*[[x['poly']] for x in sl]), 0.01))
        big = max([q for q in o if pc.Orientation(q)], key=lambda q: abs(pc.Area(q)))
        k['points'] = dots_sharp(simplify(np.vstack([F(big), F(big)[:1]]), 0.001)[:-1])
    log.append(f'smooth {pid} outline: low-passed (most a point moved: {np.hypot(*dd.T).max():.2f} mm); rim, walls below and the gap to {",".join(beside) or "-"} held')


if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    for pid in (sys.argv[3].split(',') if len(sys.argv) > 3 else ['D3']):
        if pid in OUTLINE: smooth_outline(J, log, pid)
        if pid not in OUTLINE or pid == 'D5': smooth_plate(J, log, pid)      # (the crescent bridge also has a pocket)
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
