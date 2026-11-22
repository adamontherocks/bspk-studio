# Wall flow (2026-11-21, Adam, notes P87-P90: "top down changes in radius... bumps, or uneven continuity or flow to the vertical
# wall following a horizontal path"). A standing step of the round trip: Adam sketches, Claude makes it correct, and correct
# includes walls whose radius changes gradually as you follow them around from above. Three kinds of break:
#   facet   a curve built from short flats and tight corners all turning the same way (it should be one steady arc)
#   wiggle  the wall turns one way, then the other, within a short run (an S-bend, a bump or a dent)
#   jump    in the middle of a turn the radius suddenly changes by a lot (a steady arc that abruptly tightens or opens)
# A lone corner between two straight runs is a normal milled corner and is not flagged.
#
#   flow_loop(Q)   flags on one wall loop (Nx2, mm)
#   scan(J)        flags on every plate's walls, one per spot: [dict(pid, z, kind, at, r, detail)]
#   python3 flow.py SCENE.json [--notes]      counts (and, with --notes, which wall notes each flag sits on)
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import F, S
import walls as W

STEP, SIGMA = 0.05, 0.15     # resample spacing and curvature smoothing (mm)
K0 = 1 / 10.0                # a turn: radius under 10 mm
FACET_GAP = 1.6              # same-way turns closer than this are one curve broken into pieces
FACET_TURN = 8.0             # degrees each piece must turn to count
WIGGLE_GAP = 2.5             # opposite turns closer than this are an S or a bump
WIGGLE_TURN = 6.0
WIGGLE_R = 8.0               # ...when one of them is tighter than this, and either both are modest (a bump or an S: under
WIGGLE_MAX = 75.0            #   WIGGLE_MAX degrees each) or the reverse one is a tight notch (under NOTCH_R); a lobe round a boss
NOTCH_R = 2.0                #   rejoining a wall with a gentle fillet is a shape, not a bump
DIP = 0.45                   # inside one turn, the radius opening to more than 1/DIP of the tighter peaks between them: a flat spot
JUMP = 3.0                   # inside one turn, the radius changing by this factor (to under JUMP_R)...
JUMP_R = 3.0
JUMP_LEN, JUMP_RUN = 0.4, 0.5  # ...within this length, with this much steady arc on each side

def _turns(kap, h):
    """runs where the radius is under 1/K0, in order around the loop: dict(j0, j1 (unwrapped indices), sign, turn, rmin)"""
    n = len(kap); on = np.abs(kap) > K0
    if not on.any(): return [], 0
    if on.all(): return [dict(j0=0, j1=n - 1, sign=int(np.sign(kap.sum())), turn=float(np.degrees(kap.sum() * h)), rmin=float(1 / np.abs(kap).max()), idx=list(range(n)))], 0
    start = int(np.argmax(~on)); sg = np.sign(kap) * on; out = []; j = 0
    while j < n:
        a = (start + j) % n
        if sg[a] == 0: j += 1; continue
        s0 = sg[a]; j0 = j
        while j < n and sg[(start + j) % n] == s0: j += 1
        idx = [(start + m) % n for m in range(j0, j)]
        out.append(dict(j0=j0, j1=j - 1, sign=int(s0), turn=float(np.degrees(kap[idx].sum() * h)), rmin=float(1 / np.abs(kap[idx]).max()), idx=idx))
    return out, start

def flow_loop(Q, small_hole=1.65):
    Q = np.asarray(Q, float)
    R, h = W.resample(Q, STEP); n = len(R)
    rr = np.hypot(*(R - R.mean(0)).T)
    if rr.std() < 0.03: return []                                     # a round hole or boss: a circle flows by definition
    kap = W.curvature(R, h, SIGMA); T, start = _turns(kap, h); fl = []
    at = lambda j: R[(start + int(j)) % n]
    m = len(T)
    for i in range(m):
        a = T[i]
        # inside one turn: two tight peaks with a flat spot between (facet), or an abrupt change of radius (jump)
        k = np.abs(kap[a['idx']])
        if len(k) > 6:
            pk = [j for j in range(1, len(k) - 1) if k[j] >= k[j - 1] and k[j] > k[j + 1] and k[j] > 1 / 4.0]
            for p1, p2 in zip(pk[:-1], pk[1:]):
                lo = k[p1:p2 + 1].min()
                if lo < DIP * min(k[p1], k[p2]) and (p2 - p1) * h < FACET_GAP:
                    fl.append(dict(kind='facet', at=at(a['j0'] + (p1 + p2) // 2), r=1 / max(k[p1], k[p2]),
                                   detail=f'flat spot of r{1 / lo:.1f} between r{1 / k[p1]:.1f} and r{1 / k[p2]:.1f}, {(p2 - p1) * h:.1f} mm apart'))
            w = max(1, int(JUMP_RUN / h)); g = max(1, int(JUMP_LEN / h))
            for j in range(w, len(k) - w - g, max(1, w // 2)):
                k1 = np.median(k[j - w:j]); k2 = np.median(k[j + g:j + g + w])
                if max(k1, k2) > 1 / JUMP_R and max(k1, k2) / max(min(k1, k2), 1e-9) > JUMP:
                    fl.append(dict(kind='jump', at=at(a['j0'] + j + g // 2), r=1 / max(k1, k2), detail=f'r{1 / k1:.1f} to r{1 / k2:.1f} within {JUMP_LEN} mm'))
        if m > 1:
            b = T[(i + 1) % m]
            gap = ((b['j0'] - a['j1']) if i + 1 < m else (b['j0'] + n - a['j1'])) * h
            mid = a['j1'] + gap / h / 2
            if b['sign'] == a['sign'] and gap < FACET_GAP and min(abs(a['turn']), abs(b['turn'])) >= FACET_TURN:
                fl.append(dict(kind='facet', at=at(mid), r=min(a['rmin'], b['rmin']),
                               detail=f'turns of {abs(a["turn"]):.0f} and {abs(b["turn"]):.0f} deg (r{a["rmin"]:.1f}, r{b["rmin"]:.1f}) with a {gap:.1f} mm flat between'))
            elif b['sign'] != a['sign'] and gap < WIGGLE_GAP and min(abs(a['turn']), abs(b['turn'])) >= WIGGLE_TURN and min(a['rmin'], b['rmin']) < WIGGLE_R \
                    and (max(abs(a['turn']), abs(b['turn'])) <= WIGGLE_MAX or (a if abs(a['turn']) < abs(b['turn']) else b)['rmin'] < NOTCH_R):
                fl.append(dict(kind='wiggle', at=at(mid), r=min(a['rmin'], b['rmin']),
                               detail=f'{a["turn"]:+.0f} deg (r{a["rmin"]:.1f}) then {b["turn"]:+.0f} deg (r{b["rmin"]:.1f}), {gap:.1f} mm apart'))
    return fl

def scan(J, pids=W.PLATES, near=0.6):
    flags = []
    for pid in pids:
        for za, zb, m in W.slabs(J, pid):
            for q in m:
                if abs(pc.Area(q)) / S / S < 0.01: continue
                for f in flow_loop(F(q)): flags.append(dict(pid=pid, z=round(zb, 3), **f))
    out = []                                    # one flag per spot: the same wall seen in several slabs
    for f in sorted(flags, key=lambda f: (-f['z'], f['r'])):
        if any(np.hypot(*(np.asarray(g['at']) - f['at'])) < near for g in out if g['pid'] == f['pid']): continue
        out.append(f)
    return out

def wall_notes(J):
    """Adam's notes that sit on a plate (the ones about walls), as (id, x, y, radius)"""
    plates = set(W.PLATES)
    return [(p['id'], p['w'][0], p['w'][1], p.get('r') or 0.0, p['part'], p.get('note', '')) for p in J['state'].get('pins', []) if p['part'] in plates]

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); fl = scan(J)
    from collections import Counter
    print('flags', len(fl), dict(Counter(f['kind'] for f in fl)), dict(Counter(f['pid'] for f in fl)))
    if '--notes' in sys.argv:
        hit = 0; ns = wall_notes(J)
        for nid, x, y, r, part, note in ns:
            near = [f for f in fl if np.hypot(f['at'][0] - x, f['at'][1] - y) < r + 2.5]
            hit += bool(near)
            print(f'{nid:4s} {part:4s} r{r:.1f} {note[:28]:28s} ' + ('; '.join(f'{f["kind"]} {f["pid"]} z{f["z"]} {f["detail"]}' for f in near[:3]) or '-- none'))
        print(f'notes with a flag: {hit}/{len(ns)}')
