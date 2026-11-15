# Claude's pass on Adam's 2026-11-13 plate mods: his scene + the seven approved fixes + the engineering of his new parts.
import json, math, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import outline as spline
import outline as CO     # true case geometry
adam = json.load(open(sys.argv[1])); fixed = json.load(open(sys.argv[2])); OUT = sys.argv[3]
A, F = adam['state'], fixed['state']
pos = copy.deepcopy(A['pos']); pos['sl_barrel'] = fixed['project']['defaults']['pos']['sl_barrel']
M, C, H = pos['mwheel'], pos['center'], pos['hour']
Z5, T5 = 26.05, 3.3                  # the motion layer (P5's plane and thickness): all three pieces sit in it
RS = 24.7 + 0.75                     # minute wheel space: tips + 0.75
GAP = 0.3                            # between separate plates in one layer: ±0.15 machining each side, so they never bind
STEP = 3.5                           # dot spacing on curves (the sim's spline then follows within a few hundredths)
# ---------- case outline as a dense loop with arc length ----------
def case_loop(n=8000):
    pts, _ = CO.outline(400)                     # 1600 evenly spaced points on the true shape
    return [(p['u'], p['v']) for p in pts]
LOOP = case_loop(); NL = len(LOOP)
CUM = [0.0]
for i in range(1, NL + 1): CUM.append(CUM[-1] + math.dist(LOOP[i - 1], LOOP[i % NL]))
PER = CUM[-1]
def case_s(p):            # arc length of the nearest point on the case
    best = None
    for i in range(NL):
        a, b = LOOP[i], LOOP[(i + 1) % NL]; ax, ay = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
        q = (a[0] + ax * t, a[1] + ay * t); d = math.dist(p, q)
        if best is None or d < best[0]: best = (d, CUM[i] + t * math.dist(a, b))
    return best[1]
def case_at(s):
    s %= PER
    lo, hi = 0, NL
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if CUM[mid] <= s: lo = mid
        else: hi = mid
    a, b = LOOP[lo], LOOP[(lo + 1) % NL]; t = (s - CUM[lo]) / max(1e-12, CUM[lo + 1] - CUM[lo])
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def case_run(p0, p1):     # counter-clockwise along the case from p0 to p1, evenly spaced
    s0, s1 = case_s(p0), case_s(p1)
    if s1 < s0: s1 += PER
    n = max(1, math.ceil((s1 - s0) / STEP))
    return [case_at(s0 + (s1 - s0) * k / n) for k in range(n + 1)]
def seg_hits_case(a, b):  # first crossing of segment a→b with the case loop
    best = None
    for i in range(NL):
        p, q = LOOP[i], LOOP[(i + 1) % NL]
        d = (b[0] - a[0]) * (q[1] - p[1]) - (b[1] - a[1]) * (q[0] - p[0])
        if abs(d) < 1e-12: continue
        t = ((p[0] - a[0]) * (q[1] - p[1]) - (p[1] - a[1]) * (q[0] - p[0])) / d
        u = ((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) / d
        if 0 <= t <= 1 and 0 <= u <= 1 and (best is None or t < best[0]): best = (t, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return best
def seg_hits_circle(a, b, c=M, r=RS):
    dx, dy = b[0] - a[0], b[1] - a[1]; fx, fy = a[0] - c[0], a[1] - c[1]
    qa, qb, qc = dx * dx + dy * dy, 2 * (fx * dx + fy * dy), fx * fx + fy * fy - r * r
    disc = qb * qb - 4 * qa * qc
    if disc < 0: return None
    ts = sorted([(-qb - math.sqrt(disc)) / (2 * qa), (-qb + math.sqrt(disc)) / (2 * qa)])
    for t in ts:
        if 0 <= t <= 1: return (t, (a[0] + dx * t, a[1] + dy * t))
    return None
ang = lambda p, c=M: math.degrees(math.atan2(p[1] - c[1], p[0] - c[0])) % 360
def arc_run(p0, p1, cw):  # along the space circle from p0 to p1, clockwise or not
    a0, a1 = ang(p0), ang(p1)
    if cw:
        if a1 > a0: a1 -= 360
    else:
        if a1 < a0: a1 += 360
    L = abs(a1 - a0) * math.pi / 180 * RS; n = max(1, math.ceil(L / STEP))
    return [(M[0] + RS * math.cos(math.radians(a0 + (a1 - a0) * k / n)), M[1] + RS * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
def tangent_from(P, side):    # tangent point on the space circle from an outside point; side 'left'/'right' = smaller/larger x
    d = math.dist(P, M); al = math.degrees(math.acos(RS / d)); t0 = ang(P)
    pts = [(M[0] + RS * math.cos(math.radians(t0 + s * al)), M[1] + RS * math.sin(math.radians(t0 + s * al))) for s in (1, -1)]
    return min(pts, key=lambda q: q[0]) if side == 'left' else max(pts, key=lambda q: q[0])
def offset(poly, dist):   # offset a polyline sideways (left of travel = +)
    out = []
    for i, p in enumerate(poly):
        a = poly[max(0, i - 1)]; b = poly[min(len(poly) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        out.append((p[0] - dy / L * dist, p[1] + dx / L * dist))
    return out
def resample(poly, step=STEP):
    cum = [0.0]
    for i in range(1, len(poly)): cum.append(cum[-1] + math.dist(poly[i - 1], poly[i]))
    n = max(1, math.ceil(cum[-1] / step)); out = []
    for k in range(n + 1):
        s = cum[-1] * k / n; j = max(0, min(len(poly) - 2, next((i for i in range(len(cum) - 1) if cum[i + 1] >= s), len(poly) - 2)))
        t = (s - cum[j]) / max(1e-12, cum[j + 1] - cum[j]); out.append((poly[j][0] + (poly[j + 1][0] - poly[j][0]) * t, poly[j][1] + (poly[j + 1][1] - poly[j][1]) * t))
    return out
def clip_ends(poly):      # trim a split curve (top → bottom) at the case (top) and the space circle (bottom)
    out = list(poly)
    for i in range(len(out) - 1):          # top: last crossing of the case walking from the top end inward
        h = seg_hits_case(out[i + 1], out[i])
        if h: top = (i, h[1])
    i0, ptop = top
    for j in range(len(out) - 1):
        h = seg_hits_circle(out[j], out[j + 1])
        if h: bot = (j, h[1]); break
    j0, pbot = bot
    return [ptop] + out[i0 + 1:j0 + 1] + [pbot]
# ---------- Adam's split lines, made clean ----------
KA = {k['id']: k for k in A['sketches']}
def sampled(k):           # his outline as drawn, with the segment index of every sample
    P = k['points']; n = len(P); out = []
    for s in range(n):
        a, b = P[s], P[(s + 1) % n]; N = 1 if not a.get('smooth') and not b.get('smooth') else 24
        from geo import pt_at
        for j in range(0 if s == 0 else 1, N + 1): out.append((pt_at(P, True, s, j / N), s))
    return out
_sc = sampled(KA['K8']); cres = [(KA['K8']['points'][8]['u'], KA['K8']['points'][8]['v'])] + [p for seg in (8, 9, 10, 11, 12, 0, 1) for p, s in _sc if s == seg]   # dots 9 → 10 → … → 13 → 1 → 2 → 3: its right edge
p7 = [p for p, s in sampled(KA['K10']) if s in (3, 4, 5, 6, 7)]                    # dots 4 → 5 → 6 → 7 → 8 → 9: Part 7's inner edge
cres = cres[::-1]                                                                   # top → bottom
mid = []
for p in cres:
    q = min(p7, key=lambda q: math.dist(p, q)); mid.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
mid = resample(mid, 1.0)
for _ in range(60): mid = [mid[0]] + [((mid[i - 1][0] + 2 * mid[i][0] + mid[i + 1][0]) / 4, (mid[i - 1][1] + 2 * mid[i][1] + mid[i + 1][1]) / 4) for i in range(1, len(mid) - 1)] + [mid[-1]]
mid = resample(mid, 1.0)
def extend(poly, L=20):
    a, b = poly[0], poly[1]; u = ((a[0] - b[0]) / math.dist(a, b), (a[1] - b[1]) / math.dist(a, b)); head = (a[0] + u[0] * L, a[1] + u[1] * L)
    a, b = poly[-1], poly[-2]; u = ((a[0] - b[0]) / math.dist(a, b), (a[1] - b[1]) / math.dist(a, b)); tail = (a[0] + u[0] * L, a[1] + u[1] * L)
    return [head] + poly + [tail]
mid = extend(mid)
# Square the ends: the last few mm of the split turn to meet the case edge and the wheel's space at right angles,
# so neither piece ends in a thin tip (a shallow crossing left the crescent a 1.27 mm² sliver).
def square_ends(poly, Lb=14.0, Lt=14.0):
    core = clip_ends(poly)            # top end on the case, bottom end on the wheel's space, where the curve naturally lands
    def blend(P0, d0, P1, d1, n=20):   # cubic from P0 leaving along d0 to P1 arriving along d1
        L = math.dist(P0, P1) * 0.4
        c1 = (P0[0] + d0[0] * L, P0[1] + d0[1] * L); c2 = (P1[0] - d1[0] * L, P1[1] - d1[1] * L)
        return [((1-t)**3*P0[0] + 3*(1-t)**2*t*c1[0] + 3*(1-t)*t*t*c2[0] + t**3*P1[0], (1-t)**3*P0[1] + 3*(1-t)**2*t*c1[1] + 3*(1-t)*t*t*c2[1] + t**3*P1[1]) for t in (k / n for k in range(n + 1))]
    cum = [0.0]
    for i in range(1, len(core)): cum.append(cum[-1] + math.dist(core[i - 1], core[i]))
    it = next(i for i in range(len(cum)) if cum[i] >= Lt); ib = next(i for i in range(len(cum) - 1, -1, -1) if cum[-1] - cum[i] >= Lb)
    unit = lambda a, b: ((b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b))
    Pb = core[-1]; r = unit(M, Pb); Pb = (M[0] + RS * r[0], M[1] + RS * r[1])
    bottom = blend(core[ib], unit(core[ib - 1], core[ib + 1]), Pb, (-r[0], -r[1]))
    Pt = core[0]; s = case_s(Pt); a, b = case_at(s - 0.5), case_at(s + 0.5); tx, ty = unit(a, b); out_n = (ty, -tx)
    top = blend(core[it], unit(core[it + 1], core[it - 1]), case_at(s), out_n)[::-1]
    return top + core[it + 1:ib] + bottom
# travelling top → bottom, the crescent (toward C) is on the right, Part 7 on the left
side_c = -1 if math.dist(offset(mid, -1)[len(mid) // 2], C) < math.dist(offset(mid, 1)[len(mid) // 2], C) else 1
mid_sq = extend(resample(square_ends(mid), 1.0), 6)
split_c = resample(clip_ends(offset(mid_sq, side_c * GAP / 2)))
split_7 = resample(clip_ends(offset(mid_sq, -side_c * GAP / 2)))
def cross_angle(curve, which):
    a, b = (curve[0], curve[1]) if which == 'top' else (curve[-1], curve[-2])
    if which == 'top':
        s = case_s(a); p, q = case_at(s - 0.5), case_at(s + 0.5); ref = (q[0] - p[0], q[1] - p[1])
    else: ref = (-(a[1] - M[1]), a[0] - M[0])
    d = (b[0] - a[0], b[1] - a[1]); c = abs(d[0] * ref[0] + d[1] * ref[1]) / math.hypot(*d) / math.hypot(*ref)
    return round(math.degrees(math.acos(min(1, c))), 1)
print('split meets the case at', cross_angle(split_c, 'top'), '° and the wheel space at', cross_angle(split_c, 'bottom'), '° (90 = square)')
# bottom split between Part 8 and Part 7: the midline of his two edges, straight
bt, bb = (-5.79, -14.49), (-7.43, -38.92)
u = ((bb[0] - bt[0]) / math.dist(bt, bb), (bb[1] - bt[1]) / math.dist(bt, bb))
line = [(bt[0] - u[0] * 10, bt[1] - u[1] * 10), (bb[0] + u[0] * 10, bb[1] + u[1] * 10)]      # top → bottom; Part 8 on the right of travel (west)
def straight_split(dist):
    l = offset(line, dist); top = seg_hits_circle(l[1], l[0]); bot = seg_hits_case(l[0], l[1])
    # walking up from the bottom, the first circle hit is the lower one
    return [top[1], bot[1]]
b8 = straight_split(-GAP / 2); b7 = straight_split(GAP / 2)
if b8[1][0] > b7[1][0]: b8, b7 = b7, b8
# window at the top edge: where Adam's pieces reach the case, tangent down to the wheel's space
case_top = lambda x: (x, CO.BY + math.sqrt(CO.R ** 2 - x ** 2))
W8, W5 = case_top(-16.8037), case_top(11.3700)
TG8, TG5 = tangent_from(W8, 'left'), tangent_from(W5, 'right')
def join(*runs):
    pts = []
    for r in runs:
        for i, p in enumerate(r):
            if pts and i == 0 and math.dist(pts[-1][0], p) < 1e-6: pts[-1] = (pts[-1][0], False); continue
            pts.append((p, i not in (0, len(r) - 1)))
    if math.dist(pts[0][0], pts[-1][0]) < 1e-6: pts.pop()
    return [{'u': round(p[0], 4), 'v': round(p[1], 4), 'smooth': bool(s)} for p, s in pts]
line_run = lambda a, b: [a, b]
# Part 8 (left bridge): case from the window corner round the left side to the bottom split, up it, round the space, out along the window edge
part8 = join(case_run(W8, b8[1]), [b8[1], b8[0]], arc_run(b8[0], TG8, cw=True), line_run(TG8, W8))
# crescent: window edge down, round the space to the split, up the split to the case, back along the top edge
cres_pts = join(line_run(W5, TG5), arc_run(TG5, split_c[-1], cw=True), split_c[::-1], case_run(split_c[0], W5))
# Part 7 (right top plate): down its side of the split, round the space bottom, down the bottom split, round the case
part7 = join(split_7, arc_run(split_7[-1], b7[0], cw=True), [b7[0], b7[1]], case_run(b7[1], split_7[0]))
# ---------- checks on the outlines ----------
def poly_of(points): return spline({'points': points, 'closed': True})
def min_gap(P, Q):
    best = 1e9
    for p in P[::2]:
        for i in range(len(Q) - 1):
            a, b = Q[i], Q[i + 1]; ax, ay = b[0] - a[0], b[1] - a[1]; L2 = ax * ax + ay * ay or 1e-12
            t = max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2)); best = min(best, math.dist(p, (a[0] + ax * t, a[1] + ay * t)))
    return best
def inside(p, Q):
    c = False
    for i in range(len(Q)):
        a, b = Q[i], Q[(i + 1) % len(Q)]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < a[0] + (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]): c = not c
    return c
O8, OC, O7 = poly_of(part8), poly_of(cres_pts), poly_of(part7)
for na, Pa, nb, Pb in (('Part 8', O8, 'Part 7', O7), ('crescent', OC, 'Part 7', O7), ('crescent', OC, 'Part 8', O8)):
    over = sum(inside(p, Pb) for p in Pa[::3])
    print(f'{na} ↔ {nb}: closest {min_gap(Pa, Pb):.3f} mm, samples inside the other {over}')
for nm, O in (('Part 8', O8), ('crescent', OC), ('Part 7', O7)):
    print(f'{nm}: closest to the minute wheel axis {min(math.dist(p, M) for p in O):.3f} (space r {RS})')
print('dots', len(part8), len(cres_pts), len(part7), '| window', [round(v, 2) for v in W8], [round(v, 2) for v in W5], 'tangents', [round(v, 2) for v in TG8], [round(v, 2) for v in TG5])
# ---------- the scene ----------
S = copy.deepcopy(A)
fixed_sk = {k['id']: k for k in F['sketches']}
sk = []
for k in A['sketches']:
    if k['id'] in ('K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7', 'K9'): sk.append(copy.deepcopy(fixed_sk[k['id']]))
    elif k['id'] == 'K8': sk.append({**k, 'name': 'P5 crescent outline', 'plane': {'axis': 'z', 'offset': Z5}, 'points': cres_pts})
    elif k['id'] == 'K10': sk.append({**k, 'name': 'Right top plate outline', 'plane': {'axis': 'z', 'offset': Z5}, 'points': part7})
    elif k['id'] == 'K11': sk.append({**k, 'name': 'Left bridge outline', 'plane': {'axis': 'z', 'offset': Z5}, 'points': part8})
# hour rod slot in the left bridge (the rod passes 2.55 mm from the minute wheel's space: no room for a wall, so the hole opens into it)
ux, uy = M[0] - H[0], M[1] - H[1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L; nx, ny = -uy, ux
sk.append({'id': 'K12', 'name': 'Left bridge: hour rod slot (opens into the minute wheel space)', 'plane': {'axis': 'z', 'offset': Z5}, 'closed': True,
           'points': [{'u': round(H[0] + a * ux + b * nx, 4), 'v': round(H[1] + a * uy + b * ny, 4), 'smooth': False} for a, b in ((0, -1.99), (4.0, -1.99), (4.0, 1.99), (0, 1.99))]})
S['sketches'] = sk
FD = {d['id']: d for d in F['drawn']}
def cut(kind, name, d=None, at=None, axis=None, depth=None, frm='front', seat=None, csk=None, sketch=None):
    c = {'kind': kind, 'name': name, 'from': frm, 'depth': depth, 'seat': seat, 'csk': csk}
    if sketch: c['sketch'] = sketch; return c
    if axis: c['axis'] = axis; at = pos[axis]
    c['at'] = [round(at[0], 4), round(at[1], 4)]; c['d'] = d
    return c
BEARING = dict(seat={'d': 7.2, 'depth': 0.6}, depth=2.5)
SC = {'C1': (-55.5, 29), 'C2': (-55.5, -29), 'C3': (-20, -34), 'C4': (20, -34), 'C5': (55.5, 29), 'C6': (55.5, -29), 'C7': (23, 34)}
PIN5 = (34, -12)
def plain(c): return {k: v for k, v in c.items() if k != 'id'}
def number(cuts): return [{'id': f'h{i + 1}', **c} for i, c in enumerate(cuts)]
def named(did, *names):
    return [plain(c) for c in FD[did]['cuts'] if c['name'] in names]
def all_but(did, *names): return [plain(c) for c in FD[did]['cuts'] if c['name'] not in names]
drawn = []
for d in A['drawn']:
    did = d['id']
    if did in ('D1',): nd = copy.deepcopy(FD[did])
    elif did == 'D2':
        nd = copy.deepcopy(FD[did]); nd['cuts'] = number([plain(c) for c in FD[did]['cuts']] + [cut('bearing', 'Bearing · hour rod (lowest; the hour disc unit drops in from the top)', 6.0, axis='hour', frm='back', **BEARING)])
    elif did == 'D3':
        nd = copy.deepcopy(FD[did]); nd['cuts'] = number([plain(c) for c in FD[did]['cuts']] + [cut('clear', 'Hour rod clearance', 3.5, axis='hour'), cut('pilot', 'Screw C7 · pilot (holds the crescent)', 2.5, SC['C7'], depth=6.5, frm='back')])
    elif did == 'D4':
        nd = copy.deepcopy(FD[did]); nd['cuts'] = number([plain(c) for c in FD[did]['cuts']] + [cut('clear', 'Hour rod clearance (the rod runs on down to P2)', 3.5, axis='hour'), cut('hole', 'Screw C7 · clearance', 3.4, SC['C7']), cut('dowel', 'Steady pin for the crescent (3 mm rod, 5 long, pressed in)', 3.0, PIN5, depth=2.0, frm='back')])
    elif did == 'D5':
        nd = {**copy.deepcopy(d), 'name': 'P5 crescent', 'thickness': T5, 'grow': 'plus', 'back': None, 'edges': None}
        nd['cuts'] = number([cut('hole', 'Transfer pinion opening (12 teeth, tips + 0.75): the minute disc unit drops through', 16.1, axis='center'),
                             cut('hole', 'Screw C7 · clearance', 3.4, SC['C7']), cut('dowel', 'Steady pin hole (slides over the pin in P4)', 3.05, PIN5)])
    elif did == 'D6':
        nd = copy.deepcopy(FD[did])
        keep = [plain(c) for c in FD[did]['cuts'] if c['name'].startswith('Screw') or c['name'].startswith('Dowel')]
        nd['cuts'] = number([cut('hole', 'Hour wheel opening (42 teeth, tips + 0.75): the hour disc unit drops in here', 44.9, axis='hour'),
                             cut('hole', 'Hour disc recess (Ø47.5 + 0.7 all round, 0.5 under the disc)', 48.9, axis='hour', depth=3.2, frm='back'),
                             cut('hole', 'Transfer pinion opening (tips + 0.75)', 16.1, axis='center'),
                             cut('hole', 'Minute disc recess (Ø47.5 + 0.7 all round, 0.5 under the disc)', 48.9, axis='center', depth=3.2, frm='back'),
                             cut('hole', 'Minute pinion pocket (14 leaves, tips + 0.75, 0.5 over it)', 18.1, axis='mwheel', depth=3.65, frm='front'),
                             cut('hole', 'Minute wheel arbor bushing (plain hole: no room for a bearing between the disc recesses)', 3.05, axis='mwheel')]
                            + keep + [cut('screw', 'Screw C7 · M3 countersunk (holds the crescent)', 3.4, SC['C7'], frm='back', csk={'d': 6.3})])
    elif did == 'D7':
        nd = {**copy.deepcopy(d), 'name': 'Right top plate', 'thickness': T5, 'grow': 'plus', 'back': None, 'edges': None}
        nd['cuts'] = number([cut('hole', f'Screw {s} · clearance', 3.4, SC[s]) for s in ('C4', 'C5', 'C6')] + [cut('dowel', 'Dowel 2', 3.0, (48, -28))])
    elif did == 'D8':
        nd = {**copy.deepcopy(d), 'name': 'Left bridge', 'thickness': T5, 'grow': 'plus', 'back': None, 'edges': None}
        nd['cuts'] = number([cut('hole', f'Screw {s} · clearance', 3.4, SC[s]) for s in ('C1', 'C2', 'C3')] + [cut('dowel', 'Dowel 1', 3.0, (-46, 22)),
                             cut('clear', 'Hour rod clearance', 4.0, axis='hour'), cut('pocket', 'Hour rod slot into the minute wheel space (no sliver)', sketch='K12')])
    drawn.append(nd)
S['drawn'] = drawn
S['pos'] = pos
S['stages'] = copy.deepcopy(A['stages']); S['stages']['s_barrel']['m'] = 0.33
S['stages']['s_minute']['z'] = 26.3      # minute wheel centred in the 3.3 layer: 0.25 above P4, 0.25 under P6
S['stages']['s_hour']['z'] = 29.7        # hour wheel and minute pinion 29.7–32.5: 0.5 under the discs (the disc bonds to the wheel through a 0.5 hub); 0.35 over the left bridge
S['thick'] = {**A.get('thick', {}), 'cannon_pinion': 2.8, 'minute_pinion': 2.8}   # the sim centres a gear taller than its stage, so the pinion-to-disc hub is a note, not a taller gear
S['hands'] = {'minute_disc': {'length': 23.75, 'z': 33.0, 't': 5.1}, 'hour_disc': {'length': 23.75, 'z': 33.0, 't': 5.1}}
info = {k: v for k, v in A.get('info', {}).items() if k != 'plate'}
adam_note = A.get('info', {}).get('plate', {}).get('note', '')
info.update({
  'D7': {'name': 'Right top plate (one piece with P6)', 'note': f'Adam: “{adam_note}” (typed 2026-11-13; it landed on the Work surface, moved here). Claude: cut it flat from 1/4" faced to 3.3 and solvent-weld it under P6 (dowels line the two up), so both stay one-sided cuts on the Z1; in the sim it stays its own drawn part. Screws C4–C6 pass through it.'},
  'D5': {'name': 'P5 crescent', 'note': 'Claude: a bridge between the minute wheel and the right top plate, around the transfer pinion. A steady pin in P4 locates it, so it sits still while the top plate goes on; screw C7 (from P6’s top, through it and P4 into P3) then clamps it. 0.3 mm gap to the right top plate. Needs Adam: what it should carry, if anything.'},
  'D8': {'name': 'Left bridge', 'note': 'Claude: fills the left of the motion layer around the minute wheel (tips + 0.75). The hour rod passes through a slot at its edge: the minute wheel is too close for a bearing here, so the hour rod runs in bearings in P2 and P4 instead. Clamped by screws C1–C3, located by dowel 1. 0.3 mm gap to the right top plate.'},
  'D6': {'name': 'P6 top plate', 'note': 'Claude: recessed for both discs (0.5 under each, 0.7 round the rim) with openings the disc units drop through. The minute wheel arbor’s top pivot is a plain 3.05 hole between the recesses (no room for a bearing; it turns once in 4 hours).'},
  'hour': {'note': 'Hour wheel and hour disc are one piece, bonded through a Ø30 × 0.5 hub so the disc clears the minute pinion by 0.5: the unit drops in from the top and presses onto the hour rod like a hand. The rod runs in bearings in P2 and P4 (12.5 mm apart), with a collar above P4’s bearing for end shake.'},
  'center': {'note': 'Transfer pinion (12 teeth, 2.8 thick, meshing with the minute wheel) and the minute disc are one piece, joined by a hub up through P6 (29.1–33.0, under Ø14.6 so it passes the opening; the sim has no hub part, so it shows a gap): it drops in from the top, through P6 and the crescent, onto the transfer tube that grips the Slava center arbor. Turning the disc sets the time.'},
})
S['info'] = info
scene = {'format': 'bspk-studio-scene', 'version': 3, 'savedAt': '2026-11-13T18:00:00.000Z', 'state': S, 'project': copy.deepcopy(fixed['project'])}
json.dump(scene, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('written', OUT, {d['id']: len(d['cuts']) for d in drawn})
