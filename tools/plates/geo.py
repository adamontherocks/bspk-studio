# Plate geometry kernel (generic; any project). Exact polygons with pyclipper, the same Clipper engine the sim runs in the browser,
# at the sim's grid (0.1 µm). Gathered 2026-11-22 from the tools proven on Crescent (refit.spline, pk2, plate_clean.pieces,
# smooth.region/clean_level) so the resolver carries nothing project-specific.
import math
import numpy as np
import pyclipper as pc
import shapely
from shapely.geometry import Polygon

def spline(P, closed=True, N=24):
    """the sim's outline through dots P = [(u, v, smooth)], sampled N per segment (closed)"""
    n = len(P); out = []
    def tan(i):
        u, v, sm = P[i % n]
        if not sm: return (0.0, 0.0)
        a = P[(i - 1) % n]; b = P[(i + 1) % n]
        return ((b[0] - a[0]) / 6, (b[1] - a[1]) / 6)
    for s in range(n):
        a = P[s]; b = P[(s + 1) % n]; ta = tan(s); tb = tan(s + 1)
        c1 = (a[0] + ta[0], a[1] + ta[1]); c2 = (b[0] - tb[0], b[1] - tb[1])
        nn = N if (a[2] or b[2]) else 1
        for j in range(nn):
            t = j / nn; m = 1 - t
            out.append((m ** 3 * a[0] + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * b[0],
                        m ** 3 * a[1] + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * b[1]))
    return np.array(out)

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

def pieces(a):
    """split a region into simple outlines: each outer loop with no holes, cutting through holes with straight lines"""
    out = []
    stack = [a]
    while stack:
        reg = stack.pop()
        outs = [p for p in reg if pc.Orientation(p)]
        for o in outs:
            holes = [h for h in reg if not pc.Orientation(h) and pc.PointInPolygon(h[0], o) != 0]
            if not holes: out.append(o); continue
            hp = F(holes[0]); hx = np.mean(hp[:, 0]); bb = F(o); y0, y1 = bb[:, 1].min() - 1, bb[:, 1].max() + 1; x0, x1 = bb[:, 0].min() - 1, bb[:, 0].max() + 1
            ov = min(0.05, 0.2 * (hp[:, 0].max() - hp[:, 0].min()))   # overlapping halves, so no seam can open between them (less than the island is wide)
            sub = [o] + holes
            for half in ([[x0, y0], [hx + ov, y0], [hx + ov, y1], [x0, y1]], [[hx - ov, y0], [x1, y0], [x1, y1], [hx - ov, y1]]):
                h = inter(sub, [P(half)])
                if h: stack.append(h)
    return out

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

def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def spline_poly(dots, N=24):
    """the sim's own curve through a sketch's dots (index.html outlinePoints)"""
    return spline([(q['u'], q['v'], bool(q.get('smooth'))) for q in dots], N=N)

def ring_sim(c, r):
    """the sim's circle for a round cut (index.html cutLayers ring())"""
    n = max(72, 4 * math.ceil(math.pi * r / 0.6))
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def ar(q): return abs(pc.Area(q)) / S / S
def pos(a): return [q for q in a if pc.Orientation(q)]
BOX = [P([[-500, -500], [500, -500], [500, 500], [-500, 500]])]
