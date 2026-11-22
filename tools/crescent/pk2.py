# Exact plate geometry with pyclipper (the same Clipper engine the sim uses in the browser): unions, differences,
# round offsets, opening and closing, all on polygons in mm. Replaces the 0.05 mm pixel rasters of platekit.py.
import math, os, sys
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import refit as RF

S = 1e4                                   # Clipper works in integers: 0.1 µm, like the sim
ARC = 0.002 * S                           # round offsets follow the true arc to 2 µm
def P(poly): return [[int(round(x * S)), int(round(y * S))] for x, y in poly]
def F(path): return np.array(path, float) / S
def paths_of(polys): return [P(p) for p in polys]
def _exec(a, b, op):
    c = pc.Pyclipper()
    if a: c.AddPaths(a, pc.PT_SUBJECT, True)
    if b: c.AddPaths(b, pc.PT_CLIP, True)
    return c.Execute(op, pc.PFT_NONZERO, pc.PFT_NONZERO) if a else []
def union(*sets):
    allp = [p for s in sets for p in s]
    return _exec(allp, [], pc.CT_UNION) if allp else []
def diff(a, b): return _exec(a, b, pc.CT_DIFFERENCE) if b else union(a)
def inter(a, b): return _exec(a, b, pc.CT_INTERSECTION) if (a and b) else []
def offset(a, d):
    if not a: return []
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC
    o.AddPaths(a, pc.JT_ROUND, pc.ET_CLOSEDPOLYGON)
    return o.Execute(d * S)
def close(a, r): return offset(offset(a, r), -r)          # inside corners rounded to r, gaps under 2r filled
def opening(a, r): return offset(offset(a, -r), r)        # outside corners rounded to r, necks under 2r removed
def area(a): return sum(pc.Area(p) for p in a) / (S * S)  # holes count negative
def circle(c, r, n=None):
    n = n or max(48, int(2 * math.pi * r / 0.05))
    return [[int(round((c[0] + r * math.cos(2 * math.pi * k / n)) * S)), int(round((c[1] + r * math.sin(2 * math.pi * k / n)) * S))] for k in range(n)]
def sector(r0, r1, a0, a1, n=None):        # an annular sector, angles in degrees (a0 < a1)
    n = n or max(12, int(abs(a1 - a0) * r1 * math.pi / 180 / 0.05))
    out = [(r1 * math.cos(math.radians(a0 + (a1 - a0) * k / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    out += [(r0 * math.cos(math.radians(a1 - (a1 - a0) * k / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * k / n))) for k in range(n + 1)]
    return P(out)
def spline_poly(dots, N=24): return RF.spline([(q['u'], q['v'], bool(q.get('smooth'))) for q in dots], N=N)
def outer_and_holes(a):
    """the biggest outer loop, the holes inside it, and anything else (scraps)"""
    outs = [p for p in a if pc.Orientation(p)]; holes = [p for p in a if not pc.Orientation(p)]
    if not outs: return None, [], []
    big = max(outs, key=lambda p: abs(pc.Area(p)))
    inside = [h for h in holes if pc.PointInPolygon(h[0], big) != 0]
    return big, inside, [p for p in outs if p is not big]
def rot(poly, c, a_deg):
    a = math.radians(a_deg); ca, sa = math.cos(a), math.sin(a); Pn = np.asarray(poly, float) - c
    return np.c_[Pn[:, 0] * ca - Pn[:, 1] * sa, Pn[:, 0] * sa + Pn[:, 1] * ca] + c
def simplify(poly, eps=0.01):
    """Douglas-Peucker: drop points so that every dropped point lies within eps of the chord that replaces it. (Until 2026-11-22
    this checked each dropped point only against the line to its next neighbour, so on a gently curved wall the error added up:
    chords of 0.6-2.4 mm sat 3-6 µm off the wall, and two heights' copies of one wall stepped apart.)"""
    Pn = np.asarray(poly, float); n = len(Pn)
    if n < 3: return Pn
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True; stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2: continue
        A = Pn[a]; ab = Pn[b] - A; L = math.hypot(*ab); seg = Pn[a + 1:b]
        d = np.hypot(*(seg - A).T) if L < 1e-12 else np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps: m = a + 1 + k; keep[m] = True; stack += [(a, m), (m, b)]
    return Pn[keep]
def ccw(Pn):
    Pn = np.asarray(Pn, float); a = 0.5 * (np.dot(Pn[:, 0], np.roll(Pn[:, 1], -1)) - np.dot(Pn[:, 1], np.roll(Pn[:, 0], -1)))
    return Pn if a >= 0 else Pn[::-1]
def dots_sharp(Pn): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in ccw(Pn)]
def dots_smooth(Pn): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': True} for x, y in ccw(Pn)]
def fit_smooth(path, tol=0.1):
    """an exact outline back as the fewest smooth dots on the sim's curve (refit.py), from points every ~0.25 mm"""
    Pn = F(path); L = np.hypot(*(np.roll(Pn, -1, 0) - Pn).T).sum()
    t = np.linspace(0, 1, max(60, int(L / 0.25)), endpoint=False)
    seg = np.hypot(*(np.roll(Pn, -1, 0) - Pn).T); s = np.r_[0, np.cumsum(seg)]; Q = np.vstack([Pn, Pn[:1]])
    x = np.interp(t * s[-1], s, Q[:, 0]); y = np.interp(t * s[-1], s, Q[:, 1])
    return RF.fit(dots_smooth(np.c_[x, y]), tol)
