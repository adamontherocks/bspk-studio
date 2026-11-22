# One wall, one surface (2026-11-22, Adam: "walls and surfaces should have continuous smooth surfaces... the vertical wall has
# additional non-congruent ledges"). A plate milled from one sheet is described as pockets grouped by floor depth, so a wall that
# rises past several floors is the edge of different pockets at different heights. Wherever those edges miss each other by more
# than 0.003 mm the sim draws a line across the wall (index.html buildPlate, EPS); past about 0.05 mm it shows as a ledge. Passes
# that edit each depth on its own (ledge redraw, smoothing, restore) leave the copies a few to a few tens of µm apart.
# Rule: weld. Every point of a level's wall that lies within WELD of the wall below it is moved exactly onto that wall (levels
# done from the bottom up, so a weld carries on up through every floor the wall passes). The moves are at most WELD and always
# toward the wall below. A real ledge (wider than WELD) is left as it is.
#   weld(J, log, pid)        redraws the plate's pockets (fair.write_back) and returns the level regions
#   python3 onewall.py IN.json OUT.json [D3]
import json, sys, os
import numpy as np
import pyclipper as pc
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, offset
import fair as FA, smooth as SM

WELD = 0.06
SUB = 0.2                   # lower walls are indexed in pieces this long

def seg_index(paths):
    """the walls of a level as segments, cut into short pieces for a nearest-segment lookup"""
    A, B = [], []
    for q in paths:
        Q = F(q); R = np.roll(Q, -1, 0)
        for a, b in zip(Q, R):
            L = float(np.hypot(*(b - a))); n = max(1, int(np.ceil(L / SUB)))
            t = np.linspace(0, 1, n + 1)
            pts = a + (b - a) * t[:, None]
            A.append(pts[:-1]); B.append(pts[1:])
    if not A: return None
    A = np.vstack(A); B = np.vstack(B)
    return A, B, cKDTree((A + B) / 2)

def project(X, idx, k=6, seg=False):
    """nearest point on the indexed walls for each point of X, and its distance (seg: also the unit direction of that wall)"""
    A, B, T = idx
    _, j = T.query(X, k=k)
    a = A[j]; b = B[j]; ab = b - a; L2 = (ab ** 2).sum(-1)
    t = np.clip((((X[:, None, :] - a) * ab).sum(-1)) / np.maximum(L2, 1e-18), 0, 1)
    p = a + ab * t[..., None]; d = np.hypot(*(p - X[:, None, :]).transpose(2, 0, 1))
    m = d.argmin(1); r = np.arange(len(X))
    if not seg: return p[r, m], d[r, m]
    u = ab[r, m]; u = u / np.maximum(np.hypot(u[:, 0], u[:, 1]), 1e-18)[:, None]
    return p[r, m], d[r, m], u

GRADE = (0.006, 0.02)       # regrade(): a point within 6 µm of the wall below goes onto it, one 20 µm or more away stays, and in
                            # between it moves part way (smoothstep), so a wall leaves the one below in a curve, not a step
                            # (2026-11-22, Adam: "a new weird radius appearing at a handful of the ledges, where a plate has two depths";
                            # a fade along the wall over 0.35 mm was tried first and dropped: it pulled walls into new thin spots)

def densify(Q, step=0.05):
    """the loop with points added so no segment is longer than step (its own corners kept)"""
    R = np.roll(Q, -1, 0); out = []
    for a, b in zip(Q, R):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
        out.append(a + (b - a) * (np.arange(n) / n)[:, None])
    return np.vstack(out)

def weld_level(upper, lower, forbid=None, full=WELD, zero=None):
    """upper walls onto the lower walls: points within full of them moved exactly onto them; with zero, points between full
    and zero moved part way (and the loop densified first, so the change runs smoothly along the wall)"""
    import shapely
    idx = seg_index(lower)
    if idx is None: return upper, 0
    out = []; n = 0
    for q in upper:
        Q = F(q)
        if np.abs(Q).max() > 150: out.append(q); continue          # the far box round the plate
        if zero: Q = densify(Q)
        p, d = project(Q, idx)
        if zero: f = np.where(d <= full, 1.0, SM.smoothstep(np.clip((zero - d) / (zero - full), 0, 1)))
        else: f = (d < full).astype(float)
        f[d < 1e-6] = 0
        if not f.any(): out.append(q); continue
        Qn = Q + (p - Q) * f[:, None]
        if forbid is not None and not forbid.is_empty:              # a pull never takes a wall into a part's clearance
            bad = shapely.contains_xy(forbid, Qn[:, 0], Qn[:, 1]) & ~shapely.contains_xy(forbid, Q[:, 0], Q[:, 1])
            Qn[bad] = Q[bad]
        n += int((f > 0).sum()); out.append(P(Qn))
    return union(out), n

FAIR = (0.15, 0.1, 0.25)    # fair_departures(): (sigma, near, far) in mm. Where a wall leaves the wall below, its standoff from that wall
                            # (0 along the shared stretch) is smoothed along the wall with a gaussian of sigma; the change is used in full
                            # within near of the wall below and fades out by far. A shared stretch stays exactly shared; the ledge comes
                            # off in a tangent curve instead of a tight S (2026-11-22: the hard weld left r 0.2 mm S-bends at ledge starts,
                            # and the smoother, which holds shared walls, put new kinks where the held part met the free part)

def ring_gauss(s, v, sig, L, h=0.005):
    """v sampled at arc lengths s round a closed loop of length L, smoothed by a gaussian of sig (mm), back at s"""
    n = max(8, int(np.ceil(L / h))); g = np.arange(n) * (L / n)
    vg = np.interp(g, s, v, period=L)
    f = np.fft.rfftfreq(n, d=L / n)
    return np.interp(s, g, np.fft.irfft(np.fft.rfft(vg) * np.exp(-2 * (np.pi * f * sig) ** 2), n), period=L)

def fair_level(upper, lower, forbid=None):
    """fair every place a wall of this level leaves the wall below (FAIR); returns the level, the deepest cut and deepest fill (mm)"""
    import shapely
    idx = seg_index(lower)
    if idx is None: return upper, 0.0, 0.0
    low = SM.region(lower); sig, near, far = FAIR
    out = []; cut = fill = 0.0
    for q in upper:
        Q = F(q)
        if np.abs(Q).max() > 150: out.append(q); continue
        Qd = densify(Q, 0.01)
        p, d, u = project(Qd, idx, seg=True)
        if not ((d > 0.003) & (d < far)).any(): out.append(q); continue
        perp = np.c_[-u[:, 1], u[:, 0]]                              # away from the wall below (toward the material)
        probe = p + perp * 0.002
        perp[shapely.contains_xy(low, probe[:, 0], probe[:, 1])] *= -1
        nrm = np.where((d > 1e-4)[:, None], (Qd - p) / np.maximum(d, 1e-12)[:, None], perp)
        seg = np.hypot(*(np.roll(Qd, -1, 0) - Qd).T); s = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
        ds = ring_gauss(s, np.minimum(d, far), sig, seg.sum())
        w = SM.smoothstep(np.clip((far - d) / (far - near), 0, 1))
        mv = w * (np.maximum(ds, 0) - d); mv[np.abs(mv) < 0.0005] = 0
        if not mv.any(): out.append(q); continue
        Qn = Qd + nrm * mv[:, None]
        if forbid is not None and not forbid.is_empty:              # never into a part's clearance
            bad = shapely.contains_xy(forbid, Qn[:, 0], Qn[:, 1]) & ~shapely.contains_xy(forbid, Qd[:, 0], Qd[:, 1])
            Qn[bad] = Qd[bad]; mv[bad] = 0
        cut = max(cut, float(mv.max())); fill = max(fill, float(-mv.min()))
        out.append(P(Qn))
    return union(out), cut, fill

def regrade_levels(A, KO):
    """the graded weld (GRADE) on level regions A (deepest air first), bottom-up; KO: per level, what parts need"""
    A = list(A); moved = 0
    for i in range(1, len(A)):
        fb = SM.region(offset(KO[i], 0.05)) if KO[i] else None
        A[i], n = weld_level(A[i], A[i - 1], fb, *GRADE); moved += n
        A[i] = SM.clean_level(union(A[i], A[i - 1]))
    return A, moved

def fair_levels(A, KO):
    """fair_level on every level from the bottom up, then the graded weld; returns A, deepest cut, deepest fill"""
    A = list(A); cut = fill = 0.0
    for i in range(1, len(A)):
        fb = SM.region(offset(KO[i], 0.05)) if KO[i] else None
        A[i], c, f = fair_level(A[i], A[i - 1], fb); cut = max(cut, c); fill = max(fill, f)
        A[i] = SM.clean_level(union(A[i], A[i - 1]))
        for j in range(i + 1, len(A)): A[j] = union(A[j], A[i])
    A, _ = regrade_levels(A, KO)
    return A, cut, fill

def fair_departures(J, log, pid='D3'):
    """fair_levels on a plate's pockets, then the pockets written back"""
    pl = FA.Plate(J, pid)
    KO, MM, NB = SM.setup(J, pid, pl)
    A, cut, fill = fair_levels(pl.A, KO)
    FA.write_back(J, pl, A)
    SM.fold_slivers(J, pid, A)
    log.append(f'fair departures {pid}: where a wall leaves the wall below, its standoff smoothed along the wall (sigma {FAIR[0]:g} mm); deepest cut {cut * 1000:.0f} µm, deepest fill {fill * 1000:.0f} µm')
    return A

LEDGE_MIN = 0.5             # a ledge never wider than this anywhere is not a feature: its walls are made one

def weld(J, log, pid='D3'):
    from pk2 import offset, inter
    pl = FA.Plate(J, pid); nL = len(pl.L); A = list(pl.A); moved = 0
    KO, MM, NB = SM.setup(J, pid, pl)
    # the weld first (it scored better than ledges-first: 16.5 mm of split wall against 25): walls within WELD of the wall below
    # go onto it
    for i in range(1, nL):
        fb = SM.region(offset(KO[i], 0.05)) if KO[i] else None
        A[i], n = weld_level(A[i], A[i - 1], fb); moved += n
        A[i] = SM.clean_level(union(A[i], A[i - 1]))                 # deeper air stays inside shallower air
    # ledges too narrow to be features (a floor that is never LEDGE_MIN wide): cut down to the floor below, so the wall runs
    # straight past; a floor that must stay (a boss round a hole, the floor a part sits on) keeps its ledge
    gone = 0
    for i in range(nL - 2, -1, -1):
        band = diff(A[i + 1], A[i]); thin = []
        for q in band:
            if not pc.Orientation(q): continue
            if offset([q], -LEDGE_MIN / 2): continue                 # somewhere at least LEDGE_MIN wide: a real ledge
            if MM[i] and inter([q], MM[i]): continue
            thin.append(q)
        if not thin: continue
        if i == 0 and pl.L[0] <= 1e-6:
            # above a through cut: cutting the strip through would leave a slot only a small cutter reaches through the whole
            # sheet; the ledge's wall comes back onto the through wall instead (more plate), where no part needs the room
            need = union(*[offset(KO[j], SM.CLEAR) for j in range(1, nL) if KO[j]])
            back = diff(thin, need) if need else thin
            if back:
                for j in range(1, nL): A[j] = union(A[j - 1], diff(A[j], offset(back, 0.001)))
                gone += len(back)
            continue
        A[i] = union(A[i], offset(thin, 0.001)); gone += len(thin)
        for j in range(i + 1, nL): A[j] = union(A[j], A[j - 1])
    for j in range(nL): A[j] = SM.clean_level(A[j])
    FA.write_back(J, pl, A)
    left = SM.fold_slivers(J, pid, A)
    log.append(f'one wall {pid}: {moved} wall points welded onto the wall below (within {WELD * 1000:.0f} µm); {gone} ledges never {LEDGE_MIN:g} mm wide made part of the wall')
    return A

def regrade(J, log, pid='D3'):
    """the graded weld (GRADE) alone on a plate whose walls are already welded: takes out µm steps between heights without a new
    kink where they end"""
    pl = FA.Plate(J, pid)
    KO, MM, NB = SM.setup(J, pid, pl)
    A, moved = regrade_levels(pl.A, KO)
    FA.write_back(J, pl, A)
    SM.fold_slivers(J, pid, A)
    log.append(f'regrade {pid}: {moved} wall points moved onto or toward the wall below (all within {GRADE[0] * 1000:.0f} µm, part way to {GRADE[1] * 1000:.0f} µm)')
    return A

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    weld(J, log, sys.argv[3] if len(sys.argv) > 3 else 'D3')
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
