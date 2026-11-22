# Involute spur gear outline, the same construction as sim/involute.js (keep the two in step), plus a mesh checker.
import math
import numpy as np
from matplotlib.path import Path as MP
N_FLANK, N_TIP, N_VALLEY = 10, 3, 4
PA = math.radians(20)

def compute(m, z, x=0.0, pa=PA):
    rp = m * z / 2; rb = rp * math.cos(pa); ra = rp + m * (1 + x); rf = rp - m * (1.25 - x)
    half = math.pi / (2 * z) + 2 * x * math.tan(pa) / z + (math.tan(pa) - pa)
    t0 = math.sqrt((rf / rb) ** 2 - 1) if rf > rb else 0.0
    t1 = math.sqrt((ra / rb) ** 2 - 1)
    flank = [(rb * math.sqrt(1 + t * t), -half + t - math.atan(t)) for t in (t0 + (t1 - t0) * i / N_FLANK for i in range(N_FLANK + 1))]
    tip_half = -flank[-1][1]; root_half = half if rf < rb else -flank[0][1]
    return dict(m=m, z=z, x=x, rp=rp, rb=rb, ra=ra, rf=rf, half=half, flank=flank, tip_half=tip_half, root_half=root_half, step=2 * math.pi / z)

def tooth(g, i):
    """one tooth and the valley after it, as points (local, gear centre at 0, tooth i centred at angle i*step)"""
    P = lambda r, a: (r * math.cos(a), r * math.sin(a))
    a = i * g['step']; pts = []
    if g['rf'] < g['rb']: pts.append(P(g['rf'], a - g['half']))
    for r, ang in g['flank']: pts.append(P(r, a + ang))
    for j in range(1, N_TIP): pts.append(P(g['ra'], a - g['tip_half'] + 2 * g['tip_half'] * j / N_TIP))
    for r, ang in reversed(g['flank']): pts.append(P(r, a - ang))
    if g['rf'] < g['rb']: pts.append(P(g['rf'], a + g['half']))
    v0, v1 = a + g['root_half'], a + g['step'] - g['root_half']
    for j in range(1, N_VALLEY): pts.append(P(g['rf'], v0 + (v1 - v0) * j / N_VALLEY))
    return pts

def outline(g): return [p for i in range(g['z']) for p in tooth(g, i)]

def place(pts, c, ang):
    ca, sa = math.cos(ang), math.sin(ang); p = np.asarray(pts, float)
    return np.c_[c[0] + p[:, 0] * ca - p[:, 1] * sa, c[1] + p[:, 0] * sa + p[:, 1] * ca]

def densify(pts, step=0.03):
    p = np.asarray(pts, float); out = []
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]; n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * k / n for k in range(n)]
    return np.array(out)

def overlaps(A, B):
    """do two closed outlines overlap? (dense boundary points of each tested inside the other)"""
    return MP(A).contains_points(densify(B)).any() or MP(B).contains_points(densify(A)).any()
