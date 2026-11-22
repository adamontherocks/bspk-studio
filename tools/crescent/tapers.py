# Tapers vs copies (2026-11-22, Adam: "taper to nothing is intentional.... thats two walls merging to a seamless transition").
# The sim draws a line wherever a slab's outline misses the next slab's by more than 3 µm, and its Walls check called every such
# stretch within 0.3 mm a "split wall". That lumps two different things together:
#   taper   two walls merging: the gap grows steadily from where they meet (under 6 µm) until it leaves the 0.3 mm band (a shelf
#           growing out of the wall), or grows and comes back to zero (a shoulder that swells and fades). Intended.
#   copy    one wall drawn twice: the gap stays small along the stretch without opening out (parting and rejoining under 0.1 mm
#           counts: that is the drift per-depth edits leave), or the stretch ends abruptly in a jump. A defect.
#   cross   two walls crossing each other at a shallow angle (the gap closes inside the run and opens again). A defect.
#   dip     a wall that comes within 0.3 mm of the other and leaves again without meeting it (a near miss): reported, not judged.
# Each run of drawn split segments (chained along its loop) is classified by its gap, sampled every 0.05 mm along it.
#   runs(J, pid)                 [{'kind', 'len', 'height', 'gap_min', 'gap_max', 'ends', 'at'}]
#   python3 tapers.py SCENE.json [D3 D1 ...]
import json, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import walls as W
import shapely
from shapely.geometry import MultiLineString

EPS, SPLIT = 0.003, 0.3      # the sim's own: a segment is shared within EPS (3 points on it), a split within SPLIT
MEET, OPEN = 0.006, 0.25     # a run's end "meets" the other wall under MEET, "opens out" over OPEN
STEADY = 0.85                # a taper's gap rises (or falls) along at least this share of its steps
SWELL = 0.1                  # walls that part and rejoin are a shoulder only if they open to this; under it, one wall drifting in two copies

def _segs(m):
    out = []
    for q in m:
        Q = W.F(q); out.append(np.c_[Q, np.roll(Q, -1, 0)])
    return np.vstack(out) if out else np.zeros((0, 4))

def _drawn(sa, sb):
    """segments of slab a the sim draws against slab b within SPLIT (a split line), with each segment's gap at its middle"""
    A = _segs(sa)
    if not len(A): return A, np.zeros(0)
    g = MultiLineString([W.F(q).tolist() + [W.F(q)[0].tolist()] for q in sb]); shapely.prepare(g)
    p1, p2 = A[:, :2], A[:, 2:]
    d = [shapely.distance(g, shapely.points(p1 + (p2 - p1) * t)) for t in (0.25, 0.5, 0.75)]
    shared = (d[0] < EPS) & (d[1] < EPS) & (d[2] < EPS)
    sel = (~shared) & (d[1] < SPLIT)
    return A[sel], d[1][sel], g, A

def _chain(A):
    """segments joined end to start (they come from closed loops, so consecutive ones share exact points)"""
    if not len(A): return []
    start = {(round(a[0], 6), round(a[1], 6)): i for i, a in enumerate(A)}
    end = {(round(a[2], 6), round(a[3], 6)): i for i, a in enumerate(A)}
    used = np.zeros(len(A), bool); out = []
    for i in range(len(A)):
        if used[i]: continue
        j = i
        while True:                                         # walk back to the run's first segment
            k = end.get((round(A[j][0], 6), round(A[j][1], 6)))
            if k is None or used[k] or k == i: break
            j = k
        run = []
        while j is not None and not used[j]:
            used[j] = True; run.append(j)
            j = start.get((round(A[j][2], 6), round(A[j][3], 6)))
        out.append(run)
    return out

def classify(gaps):
    """gaps: the gap sampled every 0.05 mm along the run, end to end"""
    g0, g1 = gaps[0], gaps[-1]
    ends = tuple('meets' if g < MEET else 'opens' if g > OPEN else 'stops' for g in (g0, g1))
    d = np.diff(gaps)
    up = (d >= -2e-5).mean() if len(d) else 1.0; down = (d <= 2e-5).mean() if len(d) else 1.0
    inner = gaps[1:-1].min() if len(gaps) > 2 else min(g0, g1)
    if ends == ('meets', 'opens') and up >= STEADY: kind = 'taper'
    elif ends == ('opens', 'meets') and down >= STEADY: kind = 'taper'
    elif ends == ('meets', 'meets') and gaps.max() >= SWELL: kind = 'shoulder'
    elif ends == ('opens', 'opens') and inner > MEET: kind = 'dip'     # comes within 0.3 mm of the other wall and leaves again
    elif inner < MEET and min(g0, g1) > MEET: kind = 'cross'          # the two walls cross at a shallow angle
    else: kind = 'copy'                                                 # runs alongside, or ends in a jump
    return kind, ends

def runs(J, pid='D3'):
    sl = W.slabs(J, pid); out = []
    for (za, zb, m0), (_, _, m1) in zip(sl[:-1], sl[1:]):
        for sa, sb in ((m0, m1), (m1, m0)):
            r = _drawn(sa, sb)
            if len(r) < 4: continue
            A, gap, g, Aall = r
            st_all = {(round(a[0], 6), round(a[1], 6)): i for i, a in enumerate(Aall)}
            en_all = {(round(a[2], 6), round(a[3], 6)): i for i, a in enumerate(Aall)}
            for run in _chain(A):
                seg = A[run]; L = float(np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1]).sum())
                # one segment past each end of the run too, so a run that ends because its next segment leaves fast (the sim judges a
                # segment by its middle) is seen to open out, and one whose next segment is shared is seen to meet
                prv = en_all.get((round(seg[0][0], 6), round(seg[0][1], 6))); nxt = st_all.get((round(seg[-1][2], 6), round(seg[-1][3], 6)))
                ext = ([Aall[prv]] if prv is not None else []) + list(seg) + ([Aall[nxt]] if nxt is not None else [])
                pts = []
                for x1, y1, x2, y2 in ext:
                    n = max(1, int(np.ceil(np.hypot(x2 - x1, y2 - y1) / 0.05)))
                    t = np.arange(n) / n; pts.append(np.c_[x1 + (x2 - x1) * t, y1 + (y2 - y1) * t])
                pts.append(np.array(ext[-1:])[:, 2:]); pts = np.vstack(pts)
                gp = np.asarray(shapely.distance(g, shapely.points(pts)))
                kind, ends = classify(gp)
                mid = pts[len(pts) // 2]
                out.append({'kind': kind, 'len': L, 'height': round(zb, 3), 'gap_min': float(gp.min()), 'gap_max': float(gp.max()),
                            'ends': ends, 'at': (round(float(mid[0]), 2), round(float(mid[1]), 2))})
    return out

def summary(J, pid):
    R = runs(J, pid); tot = {}
    for r in R: tot[r['kind']] = tot.get(r['kind'], 0) + r['len']
    return R, {k: round(v / 2, 1) for k, v in tot.items()}         # each split is drawn from both slabs' sides (as the sim halves it)

if __name__ == '__main__':
    J = json.load(open(sys.argv[1]))
    for pid in (sys.argv[2:] or ['D3']):
        R, tot = summary(J, pid)
        print(pid, 'mm by kind (as the sim counts):', tot)
        for r in sorted(R, key=lambda r: -r['len'])[:14]:
            print('   %-8s %5.2f mm  at %s  height %.2f  gap %.4f-%.4f  ends %s' % (r['kind'], r['len'], r['at'], r['height'], r['gap_min'], r['gap_max'], r['ends']))
