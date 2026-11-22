# Creases (2026-11-22): what Adam sees on a wall. python3 creases.py SCENE.json [...]
# what Adam sees on a wall: the sim shades a wall smooth across a vertex only if it turns under 35 deg (wallNormals); a sharper turn
# with a segment under 50 um beside it is a notch or a jog (no designed corner is that small), seen as a thin line down the wall.
# Also: kinks where a wall leaves the wall below (within 0.3 mm of the next slab's wall): a turn over 12 deg within 0.1 mm.
import json, sys, numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walls as W
from scipy.spatial import cKDTree
def turns(Q):
    a = np.roll(Q, 1, 0); c = np.roll(Q, -1, 0)
    t = np.degrees(np.arctan2((c-Q)[:,1], (c-Q)[:,0]) - np.arctan2((Q-a)[:,1], (Q-a)[:,0])); t = (t + 180) % 360 - 180
    return t, np.hypot(*(Q-a).T), np.hypot(*(c-Q).T)
def scan(J, pid='D3'):
    sl = W.slabs(J, pid); notch = {}; kink = {}
    for i, s in enumerate(sl):
        loops = [W.F(q) for q in s[2] if np.abs(W.F(q)).max() < 150]
        nb = []
        for j in (i - 1, i + 1):
            if 0 <= j < len(sl):
                for q in sl[j][2]:
                    Q = W.F(q)
                    if np.abs(Q).max() < 150: nb.append(W.resample(Q, 0.01)[0])
        T = cKDTree(np.vstack(nb)) if nb else None
        for Q in loops:
            t, la, lc = turns(Q)
            m = (np.abs(t) > 35) & (np.minimum(la, lc) < 0.05)
            for k in np.where(m)[0]: notch.setdefault((round(Q[k,0], 1), round(Q[k,1], 1)), set()).add(round(s[0], 2))
            if T is None: continue
            d, _ = T.query(Q)
            # a kink at a departure: the wall is near the neighbour's wall (3 um - 0.3 mm) and bends over 12 deg in under 0.1 mm
            m2 = (d > 0.003) & (d < 0.3) & (np.abs(t) > 12) & (np.minimum(la, lc) < 0.1) & ~m
            for k in np.where(m2)[0]: kink.setdefault((round(Q[k,0], 1), round(Q[k,1], 1)), set()).add(round(s[0], 2))
    return notch, kink
if __name__ == '__main__':
    for f in sys.argv[1:]:
        n, k = scan(json.load(open(f)))
        print(f, 'notches', len(n), 'departure kinks', len(k))
        if '-v' in sys.argv[0:1] or len(sys.argv) == 2:
            print('  notches', sorted(n)[:60]); print('  kinks', sorted(k)[:80])

def detail(J, pid='D3'):
    """each notch with its step size (µm) and each kink with its sharpest turn, plus the turns either side"""
    sl = W.slabs(J, pid); n, k = scan(J, pid); rows = []
    for kind, D in (('notch', n), ('kink', k)):
        for c in sorted(D):
            best = None
            for s in sl:
                for q in s[2]:
                    Q = W.F(q)
                    if np.abs(Q).max() > 150: continue
                    t, la, lc = turns(Q); d = np.hypot(*(Q - np.array(c)).T)
                    for j in np.where((d < 0.1) & (np.abs(t) > (35 if kind == 'notch' else 12)))[0]:
                        v = (round(min(la[j], lc[j]) * 1000, 2), int(round(t[j])), s[0])
                        if best is None or (kind == 'notch' and v[0] > best[0]) or (kind == 'kink' and abs(v[1]) > abs(best[1])): best = v
            rows.append((kind, (float(c[0]), float(c[1])), best, sorted(D[c])))
    return rows
