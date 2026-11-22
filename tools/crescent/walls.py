# Walls (2026-11-21, Adam: "radii should be smooth and consistent. if there is a sudden unusual radius change, that should be
# a flag"): every plate rebuilt slab by slab the way the sim draws it (hairline_check.layers), and the walls you see from above
# listed as loops: the boundary of each slab's material, in movement coordinates.
#   slabs(J, pid)  -> [(z_bottom, z_top, material paths)]
#   wall_loops(J, pids) -> [dict(pid, z, loop Nx2, hole)]  one per distinct wall edge (a wall running through several slabs counted once, at its top)
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, opening, offset, spline_poly
from hairline_check import layers

PLATES = ('D1', 'D3', 'D5', 'D6', 'D2', 'D29')

def slabs(J, pid):
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; d = next(x for x in st['drawn'] if x['id'] == pid)
    k = SK[d['sketch']]; z0 = k['plane']['offset']; T = d['thickness']
    src = d['back'] if d.get('back') else k['points']
    outline = union([P(spline_poly(k['points']))]); L = layers(d, SK)
    cuts_at = sorted({0.0, T} | {min(T, max(0.0, v)) for iv, _ in L for v in iv})
    out = []
    for a, b in zip(cuts_at[:-1], cuts_at[1:]):
        if b - a < 1e-6: continue
        mid = (a + b) / 2
        act = [p if pc.Orientation(p) else p[::-1] for iv, ps in L if iv[0] <= mid <= iv[1] for p in ps]
        out.append((z0 + a, z0 + b, diff(outline, union(act)) if act else outline))
    return out

def wall_loops(J, pids=PLATES):
    out = []
    for pid in pids:
        sl = slabs(J, pid)
        for i, (za, zb, m) in enumerate(sl):
            above = sl[i + 1][2] if i + 1 < len(sl) else None
            for q in m:
                if abs(pc.Area(q)) / S / S < 0.01: continue
                Q = F(q)
                if above is not None:
                    # the part of this edge that the slab above repeats exactly is the same wall: keep only edges seen at this slab's top
                    pass
                out.append(dict(pid=pid, z=round(zb, 3), loop=Q, hole=not pc.Orientation(q)))
    return out

# ---------- the scan ----------
STEP = 0.05
JOG_R = 4.0
def resample(Q, step=STEP):
    Q = np.asarray(Q, float); C = np.vstack([Q, Q[:1]]); seg = np.hypot(*np.diff(C, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    n = max(32, int(s[-1] / step)); t = np.linspace(0, s[-1], n, endpoint=False)
    return np.c_[np.interp(t, s, C[:, 0]), np.interp(t, s, C[:, 1])], s[-1] / n

def curvature(R, h, sigma=0.2):
    """signed curvature along a closed loop (material on the left: + is an outside corner of plate, - an inside corner)"""
    d = np.roll(R, -1, 0) - np.roll(R, 1, 0); th = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    n = len(R); turn = np.diff(np.r_[th, th[0] + (th[-1] - th[0]) + (th[1] - th[0])])[:n]
    turn = (turn + np.pi) % (2 * np.pi) - np.pi
    k = int(3 * sigma / h)
    if k >= 1:
        w = np.exp(-0.5 * (np.arange(-k, k + 1) * h / sigma) ** 2); w /= w.sum()
        turn = np.convolve(np.r_[turn[-k:], turn, turn[:k]], w, mode='valid')
    return turn / h

def bends(kap, h, k0=1 / 8.0):
    """runs where the radius is under 1/k0: [dict(i0, i1, sign, turn_deg, rmin, len)] around the loop"""
    n = len(kap); on = np.abs(kap) > k0; sg = np.sign(kap) * on
    if on.all() or not on.any():
        return [] if not on.any() else [dict(i0=0, i1=n - 1, sign=int(np.sign(kap.sum())), turn=float(np.degrees(kap.sum() * h)), rmin=float(1 / np.abs(kap).max()), len=n * h)]
    start = int(np.argmax(~on)); out = []; i = 0
    idx = [(start + j) % n for j in range(n)]
    j = 0
    while j < n:
        a = idx[j]
        if sg[a] == 0: j += 1; continue
        s0 = sg[a]; j0 = j
        while j < n and sg[idx[j]] == s0: j += 1
        seg = [idx[m] for m in range(j0, j)]
        out.append(dict(i0=seg[0], i1=seg[-1], j0=j0, j1=j - 1, sign=int(s0), turn=float(np.degrees(kap[seg].sum() * h)),
                        rmin=float(1 / np.abs(kap[seg]).max()), len=len(seg) * h))
    return out

def scan_loop(Q, small_hole=1.65):
    """flags on one wall loop: jogs (opposite bends close together), hooks (U-turns on a tight radius), tight radii"""
    R, h = resample(Q); n = len(R)
    if not pc.Orientation(P(Q)): pass
    rr = np.hypot(*(R - R.mean(0)).T)
    if rr.max() < small_hole + 0.05 and rr.std() < 0.05: return []          # a drilled hole: a circle, not a wall
    kap = curvature(R, h); B = bends(kap, h); fl = []
    m = len(B)
    for i in range(m):
        b = B[i]; c = R[(b['i0'] + ((b['i1'] - b['i0']) % n) // 2) % n]
        if abs(b['turn']) >= 150 and b['rmin'] < 1.5:
            fl.append(dict(kind='hook', at=c, r=b['rmin'], turn=b['turn']))
        elif b['rmin'] < 0.9 and abs(b['turn']) > 15:
            fl.append(dict(kind='tight', at=c, r=b['rmin'], turn=b['turn']))
        if m > 1:
            b2 = B[(i + 1) % m]
            gap = ((b2['j0'] - b['j1']) % n) * h
            if b2['sign'] != b['sign'] and gap < 2.0 and min(abs(b['turn']), abs(b2['turn'])) >= 12 and min(b['rmin'], b2['rmin']) < JOG_R:
                c2 = R[b['i1']] * 0.5 + R[b2['i0']] * 0.5
                fl.append(dict(kind='jog', at=c2, r=min(b['rmin'], b2['rmin']), turn=(b['turn'], b2['turn']), gap=gap))
    return fl

def thin_pieces(X, w):
    out = []
    for q in diff(X, opening(X, w / 2)):
        if not pc.Orientation(q): continue
        ar = abs(pc.Area(q)) / S / S
        if ar < 0.03: continue
        Pq = F(q); per = float(np.hypot(*(np.roll(Pq, -1, 0) - Pq).T).sum()); L = per / 2; th = ar / max(L, 1e-9)
        # a double wall is a strip that stays thin all along (two edges running side by side); the wedge where two edges cross at
        # an angle widens to the full w and is not one
        if L >= 1.2 and th >= 0.02 and not offset([q], -0.6): out.append(dict(at=Pq.mean(0), len=L, thick=th, poly=q))
    return out

def tiers(J, w=1.5):
    """double walls: a ledge or overhang thinner than w between stacked slabs (in a plate, and plate on plate)"""
    sl = {pid: slabs(J, pid) for pid in PLATES}
    pairs = []
    for pid, S_ in sl.items():
        for (za, zb, m0), (_, _, m1) in zip(S_[:-1], S_[1:]): pairs.append((f'{pid} step', zb, m0, m1))
    def top(pid): return sl[pid][-1][2]
    def bot(pid): return sl[pid][0][2]
    # plates resting on plates: the lower plate's top slab against everything whose bottom sits on it
    on = {'D1': ['D3', 'D6'], 'D3': ['D5', 'D2'], 'D6': ['D5', 'D2']}
    for lo, ups in on.items():
        zt = sl[lo][-1][1]
        ub = union(*[bot(u) for u in ups if abs(sl[u][0][0] - zt) < 0.01])
        pairs.append((f'{lo} top / {"+".join(ups)}', zt, top(lo), ub))
    # screw and bearing holes: a hole in one plate over a smaller one in the next is a counterbore, not a double wall
    holes = []
    for pid in PLATES:
        d = next(x for x in J['state']['drawn'] if x['id'] == pid)
        holes += [(c['at'], c['d'] / 2) for c in d.get('cuts') or [] if c.get('at') and c.get('d') and c['kind'] != 'pocket' and c['d'] <= 6.5]
    def at_hole(p): return any(np.hypot(p[0] - h[0][0], p[1] - h[0][1]) < h[1] + 1.8 for h in holes)
    out = []
    for tag, z, m0, m1 in pairs:
        ledge = diff(m0, m1); over = diff(m1, m0)
        for x in thin_pieces(ledge, w):
            if inter(offset([x['poly']], 0.05), m1) and not at_hole(x['at']): out.append(dict(kind='ledge', tag=tag, z=z, **x))
        for x in thin_pieces(over, w):
            if inter(offset([x['poly']], 0.05), m0) and not at_hole(x['at']): out.append(dict(kind='overhang', tag=tag, z=z, **x))
    return out

def scan(J, pids=PLATES):
    flags = []
    for pid in pids:
        for za, zb, m in slabs(J, pid):
            for q in m:
                if abs(pc.Area(q)) / S / S < 0.01: continue
                for f in scan_loop(F(q)): flags.append(dict(pid=pid, z=round(zb, 3), **f))
    for t in tiers(J): flags.append(dict(pid=t['tag'], z=round(t['z'], 3), kind='tier-' + t['kind'], at=t['at'], r=t['thick'], len=t['len']))
    # one flag per spot: the same wall seen in several slabs
    out = []
    for f in sorted(flags, key=lambda f: -f['z']):
        if any(g['kind'] == f['kind'] and np.hypot(*(np.asarray(g['at']) - f['at'])) < 0.6 for g in out): continue
        out.append(f)
    return out

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); fl = scan(J)
    from collections import Counter
    print(Counter(f['kind'] for f in fl)); print(Counter(f['pid'] for f in fl))
