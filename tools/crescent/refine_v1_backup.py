# Crescent refinement pass (exact geometry, pyclipper), 2026-11-18. Adam sketches with crude splines "because they look good
# this way"; this pass redraws them so they are functional, machinable, anchored and geometrically aligned, keeping his intent:
#   - one family of sizes everywhere: screw anchors and bars r 3.2 (6.4 wide, the seconds pill's size), bearing hubs r 5,
#     inside corners r 2, outside corners r 1; perimeters main plate r 66, second level r 65, top level r 64
#   - the crescent and the balance bridge are one part: the band is a true lune (r 64 about the centre, the minute track's
#     circle less 0.6 about the hand arbor) cut square at both ends, symmetric about the middle of its minute track; the balance
#     sits in a round hub with two straight bars, symmetric about the line from the movement's centre through the balance
#   - the hand cock is a band concentric with the rim (6.4 wide, round screw ends centred on their screws), symmetric about the
#     line through the movement's centre and the hand arbor, with a straight bar through the hour star to the hub on the hand
#     arbor; screws at both ends and where the bar lands
#   - every rim screw on the top level sits on one circle (r 60.8, the bands' centre line); the crescent's four symmetric
#   - the crescent rim plate under the band: its inner edge 3 mm under the band (the joint hides), its lower end flush under
#     the crescent's end
#   - plates follow what sits on them and what lies under them: an edge of the motion-works plate (outline, and its full-height
#     top) that runs within 2 mm of an edge of a part above it, or of a recess or window in the main plate below it, is moved
#     onto that edge, so walls run straight down through the stack ("no radius under, straight edge above")
#   - back faces match front faces everywhere
#
#   python3 refine.py ADAM.json OUT.json
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import *
import pyclipper as pc

SRC, OUT = sys.argv[1:3]
J = json.load(open(SRC)); st = J['state']; pr = J['project']; mech = pr['mechanisms']
SK = {k['id']: k for k in st['sketches']}
def DR(): return {d['id']: d for d in st['drawn']}
def byname(prefix, required=True):
    d = next((d for d in st['drawn'] if d['name'].startswith(prefix)), None)
    if d is None and required: raise SystemExit(f'no part named {prefix}...')
    return d
def zband(d): z = SK[d['sketch']]['plane']['offset']; return (z, z + d['thickness'])
def outline(d): return [P(ccw(spline_poly(SK[d['sketch']]['points'])))]
def add_sketch(name, dots):
    n = 1
    while f'K{n}' in SK: n += 1
    k = {'id': f'K{n}', 'name': name, 'plane': {'axis': 'z', 'offset': 0.0}, 'closed': True, 'points': dots}; st['sketches'].append(k); SK[k['id']] = k; return k['id']
def next_cut(d):
    n = 1; used = {c['id'] for c in d.get('cuts', [])}
    while f'h{n}' in used: n += 1
    return f'h{n}'
def rdp_loop(Pn, eps):
    """Douglas-Peucker on a closed loop: the fewest corners within eps of the exact edge"""
    Pn = np.asarray(Pn, float); Q = np.vstack([Pn, Pn[:1]])
    def rec(a, b):
        if b <= a + 1: return [a]
        seg = Q[b] - Q[a]; L = np.hypot(*seg) or 1e-12
        dd = np.abs(seg[0] * (Q[a + 1:b, 1] - Q[a, 1]) - seg[1] * (Q[a + 1:b, 0] - Q[a, 0])) / L
        k = int(np.argmax(dd))
        return rec(a, a + 1 + k) + rec(a + 1 + k, b) if dd[k] > eps else [a]
    far = int(np.argmax(np.hypot(*(Pn - Pn[0]).T)))
    return Pn[sorted(set(rec(0, far) + rec(far, len(Q) - 1)))]
def pocket(d, name, path, depth):
    kid = add_sketch(f'{name} (pocket outline)', dots_sharp(rdp_loop(F(path), 0.025)))
    d.setdefault('cuts', []).append({'id': next_cut(d), 'kind': 'pocket', 'name': name, 'from': 'back', 'depth': None if depth is None else round(depth, 3), 'sketch': kid, 'seat': None, 'csk': None})
def cut(d, kind, name, dia, at, depth=None, frm='back', csk=None, axis=None):
    c = {'id': next_cut(d), 'kind': kind, 'name': name, 'from': frm, 'depth': depth, 'seat': None, 'csk': csk, 'at': [round(float(at[0]), 4), round(float(at[1]), 4)], 'd': dia}
    if axis: c['axis'] = axis
    d.setdefault('cuts', []).append(c)
def set_outline(d, paths, tol=0.05):
    big, holes, scraps = outer_and_holes(paths)
    pts, err, L = fit_smooth(big, tol); SK[d['sketch']]['points'] = pts; d['back'] = None; d['edges'] = None
    d['_holes'] = [h for h in holes if abs(pc.Area(h)) / (S * S) > 1.0]                # enclosed windows: through pockets, added with the cuts
    return len(pts), err, [abs(pc.Area(s)) / (S * S) for s in scraps]
def add_windows(d, label):
    for i, h in enumerate(d.pop('_holes', [])): pocket(d, f'Window {i + 1} ({label}, through)', h[::-1] if not pc.Orientation(h) else h, None)
def deg(v): return math.degrees(math.atan2(v[1], v[0]))
def polar(c, r, a): return np.array([c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))])
def capsule(a, b, r):
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC; o.AddPath(P([a, b]), pc.JT_ROUND, pc.ET_OPENROUND); return o.Execute(r * S)
def fan(c, a0, a1, L=250.0):
    """the wedge about c between angles a0 < a1 (degrees)"""
    n = max(8, int((a1 - a0) / 2)); return [P([c] + [polar(c, L, a0 + (a1 - a0) * k / n) for k in range(n + 1)])]
BIG = [P([(-300, -300), (300, -300), (300, 300), (-300, 300)])]
def outers(paths): return [p for p in paths if pc.Orientation(p)]
log = []

# ---------- the family of sizes ----------
R_MAIN, R_L2, R_TOP, SNAP, GAP = 66.0, 65.0, 64.0, 3.0, 0.5
R_ANCHOR, R_HUB, R_IN, R_OUT = 3.2, 5.0, 2.0, 1.0
R_RING = R_TOP - R_ANCHOR                                                 # 60.8: the centre line of the rim bands; every top-level rim screw
Z0, T_MW = 12.7, 9.525; ZT = Z0 + T_MW; T_TOP = 2.8
LEDGES = [15.5, 17.1, 19.1]
CSK = {'d': 4.2}
def clean(paths, ri=R_IN, ro=R_OUT): return opening(close(paths, ri), ro)
def snap_rim(paths, R):
    """run the edge out to the circle R wherever the part comes within SNAP of it, then trim to R"""
    near = inter(paths, diff([circle((0, 0), R + 20)], [circle((0, 0), R - SNAP)]))
    fills = []
    for piece in near:
        if not pc.Orientation(piece): continue
        a = np.degrees(np.arctan2(F(piece)[:, 1], F(piece)[:, 0])) % 360; a.sort()
        gaps = np.diff(np.r_[a, a[0] + 360]); k = int(np.argmax(gaps))
        a0, a1 = (a[0], a[-1]) if k == len(a) - 1 else (a[k + 1], a[k] + 360)
        fills.append(sector(R - SNAP - 0.6, R, a0, a1))
    return inter(union(paths, fills), [circle((0, 0), R)])
def snap_to(Pp, R, s, min_len=3.0):
    """edges of Pp that run within s of R's edge are moved onto it, from either side: thin gaps between them are filled,
    thin slivers past R's edge are trimmed (only where Pp's body is on the far side); where Pp crosses R's edge it stays"""
    if not Pp or not R: return Pp
    h = s / 2; near = diff(offset(R, s), offset(R, -s)); notR = diff(BIG, R)
    PinR, PoutR = inter(Pp, R), diff(Pp, R)
    bodyIn, bodyOut = opening(PinR, h), opening(PoutR, h)
    touches = lambda piece, other: bool(other) and area(inter(offset([piece], 0.05), other)) > 1e-4
    def real(pieces):                                                       # slivers that run along R for 3 mm or more (not hairlines, not crossing blends)
        out = []
        for p in pieces:
            q = F(p); per = float(np.hypot(*(np.roll(q, -1, 0) - q).T).sum())
            if per / 2 >= min_len and offset(offset([p], -0.03), 0.03): out.append(p)
        return out
    add = [p for p in real(outers(inter(diff(close(union(Pp, R), h), union(Pp, R)), near))) if touches(p, bodyOut)]
    add += [p for p in real(outers(inter(diff(close(union(Pp, notR), h), union(Pp, notR)), near))) if touches(p, bodyIn)]
    rem = [p for p in real(outers(inter(diff(PinR, bodyIn), near))) if touches(p, bodyOut)]
    rem += [p for p in real(outers(inter(diff(PoutR, bodyOut), near))) if touches(p, bodyIn)]
    if not (add or rem): return Pp
    out = diff(union(Pp, offset(add, 0.01)), offset(rem, 0.01))
    return [p for p in out if abs(pc.Area(p)) / (S * S) > 0.05]
INNER = [circle((0, 0), R_TOP - 1.5)]
def snap_inside(Pp, R, s):
    """snap_to, but the perimeter steps (r 64 / 65 / 66) are left alone"""
    out = snap_to(Pp, R, s); return union(inter(out, INNER), diff(Pp, INNER))

# ---------- the parts ----------
main, rimL, mw = byname('Main plate'), byname('Crescent rim plate'), byname('Motion-works plate')
cres = next(d for d in st['drawn'] if d['name'].startswith('Crescent') and not d['name'].startswith('Crescent rim'))
hand, sec = byname('Hand cock'), byname('Seconds bridge')
bal = byname('Balance bridge', required=False)
POS = st['pos']; Fo = np.array(POS['fourth'], float); Bc = np.array(POS['balance'], float); B = np.array(POS['barrel'], float)
Qh = np.array(POS['retro'], float); Hs = np.array(POS['hourstar'], float); O = np.zeros(2)
RI = json.load(open(os.path.join(HERE, 'crescent_geo.json')))['RI']; RIN = RI - 0.6
trk = next(e for e in pr['decor']['engrave'][cres['id']] if e['kind'] == 'arc')
TRK_MID, TRK_HALF = (trk['a0'] + trk['a1']) / 2, abs(trk['a0'] - trk['a1']) / 2       # 148.04, 61.96 about the hand arbor
PHI = TRK_HALF + 3.0                                                       # the band runs 3 deg past the end ticks
AXIS_HC = deg(Qh)                                                          # -30: the movement's centre through the hand arbor
for d in st['drawn']:
    if d['id'] not in mech['mounts']: d['back'] = None                     # back faces match front faces

# ---------- 1. what the plates must make room for (independent of the plates' outlines) ----------
TABLE = {l['arbor']: (min(l['values']) - 1.0, max(l['values']) + 1.0) for l in mech.get('links', []) if l.get('kind') == 'table'}
RANGES = {'lever': (-1.5, 42.7), 'jumper': (0.0, 4.5), 'click': (2.0, 14.0)}
def centre_of(did):
    mt = mech['mounts'][did]; return np.array(mt['pivot'] if 'pivot' in mt else POS[mt['axis']], float)
_sw = {}
def sweep(did):
    if did in _sw: return _sw[did]
    d = DR()[did]; poly = simplify(spline_poly(SK[d['sketch']]['points'], 8), 0.01); mt = mech['mounts'][did]; c = centre_of(did)
    if ('axis' in mt and mt['axis'] not in TABLE) or mt.get('angle') == 'hour':
        r = [circle(c, float(np.hypot(*(poly - c).T).max()))]
    else:
        a0, a1 = TABLE[mt['axis']] if 'axis' in mt else RANGES[mt['angle']]
        r = union([P(rot(poly, c, a)) for a in np.arange(a0, a1 + 1e-9, 0.5)])
    _sw[did] = r; return r
MOVER_CUT, seat_by_ledge, names_by_ledge = [], {l: [] for l in LEDGES}, {l: [] for l in LEDGES}
def ledge_for(bottom): return max(l for l in LEDGES if l <= bottom + 1e-6)
for did, mt in mech['mounts'].items():
    if 'axisX' in mt: continue
    z0, z1 = zband(DR()[did])
    if z1 > Z0 and z0 - 0.5 < Z0 + 0.01: MOVER_CUT += close(offset(sweep(did), 1.25), 2.5)   # reaches below the plate: its edge steps round it, smoothly
    elif not (z1 <= Z0 or z0 >= ZT):
        sw = sweep(did)
        if 'Pawl pin' in DR()[did]['name']: sw = offset(sw, 2.0)
        l = ledge_for(z0 - 0.5); seat_by_ledge[l] += offset(sw, 0.75); names_by_ledge[l].append(DR()[did]['name'].split(' (')[0])
MOVER_CUT = union(MOVER_CUT)
spr = mech['springs'][0]; Lc = centre_of(spr['to']['part']); wires = []
for a in np.arange(RANGES['lever'][0], RANGES['lever'][1] + 1e-9, 2.0):
    lug = rot([spr['to']['at']], Lc, a)[0]; wires += capsule(np.array(spr['from'], float), lug, spr['r'] + 0.75)
l = ledge_for(spr['z'] - spr['r'] - 0.5); seat_by_ledge[l] += union(wires); names_by_ledge[l].append('Return spring')
ELS = json.load(open(os.path.join(HERE, 'elements_crescent.json')))
for e in ELS:
    if 'sweep' in e['name'] or e['z1'] <= Z0 or e['z0'] >= ZT: continue
    l = ledge_for(e['z0'] - 0.5); seat_by_ledge[l] += [circle((e['x'], e['y']), e['r'] + 0.75)]; names_by_ledge[l].append(e['name'].split(' (')[0])
SEATS = {l: union(seat_by_ledge[l]) for l in LEDGES}
SEC_WIN = [circle(Fo, 18.7 + 0.75)]                                       # through the plate, down to the seconds wheel (flush with its recess)
# what the main plate shows under the motion-works plate: its recesses and side windows (walls to line up with)
UNDER = []
for c in main['cuts']:
    if c['kind'] == 'hole' and c['name'].startswith('Recess') and c.get('at'): UNDER.append(('recess ' + c['name'].split('· ')[-1], [circle(c['at'], c['d'] / 2)]))
    if c['kind'] == 'pocket' and c['name'].startswith('Side window'):
        UNDER.append((c['name'].split(' (')[0].lower(), [P(ccw(np.array([(q['u'], q['v']) for q in SK[c['sketch']]['points']])))]))

# ---------- 2. the top level, drawn from circles and straight bars ----------
# the crescent: a true lune, cut square 3 deg past the minute track's end ticks, symmetric about the track's middle
lune = inter(diff([circle(O, R_TOP)], [circle(Qh, RIN)]), fan(Qh, TRK_MID - PHI, TRK_MID + PHI))
def edge_hit(c, a, R, cc):
    """distance from c along angle a to the circle (cc, R), from inside"""
    v = polar((0, 0), 1, a); w = np.asarray(c, float) - cc; b = float(np.dot(v, w)); return -b + math.sqrt(b * b - (np.dot(w, w) - R * R))
# the balance: a round hub on the staff, two straight bars symmetric about the line from the movement's centre through it.
# Adam's bars meet the band at about (-28.7, 32) and (-43.5, -23); keep their spread, centred on that line.
adam_ends = [np.array([-28.7, 32.0]), np.array([-43.5, -23.0])]
if bal is not None:
    bp = F(outline(bal)[0]); a_ = np.array([deg(p - Bc) for p in bp]); r_ = np.hypot(*(bp - Bc).T)
    ends = []
    for half in (a_ > 0, a_ <= 0):                                          # his two bar ends: the far points either side of the hub
        if half.sum() < 4: break
        idx = np.where(half)[0]; idx = idx[np.argsort(-r_[idx])][:max(3, len(idx) // 8)]; ends.append(bp[idx].mean(0))
    if len(ends) == 2: adam_ends = ends
a_up, a_dn = deg(adam_ends[0] - Bc), deg(adam_ends[1] - Bc) % 360
BAL_AXIS = deg(Bc - O); spread = (a_dn - a_up) / 2
BAL_ARMS = [BAL_AXIS - spread, BAL_AXIS + spread]
bars = []
for a in BAL_ARMS:
    t = edge_hit(Bc, a, RIN, Qh); bars += capsule(Bc, polar(Bc, t + 2.5, a), R_ANCHOR)
cres_p = inter(clean(union(lune, [circle(Bc, R_HUB)], bars)), [circle(O, R_TOP)])
log.append(f'crescent and balance bridge: one part; the lune symmetric about the minute track\'s middle ({TRK_MID:.2f} deg about the hand arbor), '
           f'square ends {PHI:.1f} deg either side; balance hub r {R_HUB}, bars 6.4 wide at {BAL_ARMS[0]:.1f} and {BAL_ARMS[1]:.1f} deg '
           f'(symmetric about {BAL_AXIS:.1f}, the line from the centre through the balance)')
# the hand cock: a band concentric with the rim, symmetric about the centre-hand arbor line, bar through the hour star to a hub
u_qh = (Hs - Qh) / np.hypot(*(Hs - Qh))
def ring_hit(c, u, R):
    w = np.asarray(c, float); b = float(np.dot(u, w)); return -b + math.sqrt(b * b - (np.dot(w, w) - R * R))
LAND = Qh + u_qh * ring_hit(Qh, u_qh, R_RING); A_LAND = deg(LAND)       # where the bar meets the band's centre line
def hand_shape(h):
    a0, a1 = AXIS_HC - h, AXIS_HC + h
    band = union([sector(R_TOP - 2 * R_ANCHOR, R_TOP, a0, a1)], [circle(polar(O, R_RING, a0), R_ANCHOR)], [circle(polar(O, R_RING, a1), R_ANCHOR)])
    return inter(clean(union(band, capsule(Qh, LAND, R_ANCHOR), [circle(Qh, R_HUB)])), [circle(O, R_TOP)])

# ---------- 3. the crescent rim plate: inner edge 3 mm under the band, ends square (its lower end flush under the crescent's) ----------
rim0 = outline(rimL); ang0 = np.degrees(np.arctan2(F(rim0[0])[:, 1], F(rim0[0])[:, 0])) % 360
TOP_END = float(np.min(ang0[(ang0 > 60) & (ang0 < 180)]))                  # Adam's top end (a radial line, hidden under the band)
rim_p = inter(inter(diff([circle(O, R_L2)], [circle(Qh, RIN + 3.0)]), fan(Qh, TRK_MID - PHI, TRK_MID + PHI)), fan(O, TOP_END, TOP_END + 180))
rim_p = clean(rim_p)
n, err, scraps = set_outline(rimL, rim_p); rim_paths = outline(rimL)
log.append(f'crescent rim plate: r {R_L2} outside, its inner edge 3 mm in under the band (the joint is hidden), top end radial at {TOP_END:.1f} deg, '
           f'lower end flush under the crescent\'s; {n} dots')

# ---------- 4. the motion-works plate: Adam's outline lined up with the parts above and the main plate below ----------
mwp = outline(mw)
ab = math.degrees(math.atan2(B[1], B[0]))
mwp = union(mwp, [sector(50.0, R_L2, ab - 18.0, ab + 26.0)])           # the barrel window: the edge runs to the rim over it
mwp = snap_rim(mwp, R_L2)
hand_p0 = hand_shape(61.0)
for name, ref in UNDER: mwp = snap_to(mwp, ref, 2.0)                    # walls straight down into the main plate's recesses
for ref in (cres_p, hand_p0): mwp = snap_inside(mwp, ref, 2.0)              # and straight up into the parts above
def hard(p): return diff(inter(p, [circle(O, R_L2)]), union(offset(rim_paths, GAP), MOVER_CUT))
mwp = hard(clean(hard(mwp)))
mwp = hard(close(mwp, 1.6))
big, holes, scraps = outer_and_holes(mwp); mwp = [big]
n, err, scraps_ = set_outline(mw, mwp, 0.08); foot = outline(mw)
mw['cuts'] = []; mw['thickness'] = T_MW; SK[mw['sketch']]['plane'] = {'axis': 'z', 'offset': Z0}
log.append(f'motion-works plate: edges snapped onto the main plate\'s recesses and windows below and the parts above (within 2 mm), '
           f'r {R_L2}, 0.5 mm joint, corners r {R_IN}/{R_OUT}; {n} dots' + (f'; scraps dropped {[round(abs(pc.Area(s)) / S / S, 1) for s in scraps]} mm²' if scraps else ''))

# seats on three ledges, towers down
lim = offset(foot, 1.5); regions = {}
for l in LEDGES:
    r = inter(clean(SEATS[l], 1.0, 0.6), lim) if SEATS[l] else []
    regions[l] = outers(r)
top_left = diff(foot, union(*regions.values(), SEC_WIN)); edge_band = diff(foot, offset(foot, -1.5)); n_t = 0
for piece in outers(top_left):
    ar = abs(pc.Area(piece)) / (S * S)
    if ar >= 60 or inter([piece], edge_band) and ar >= 20: continue
    touch = [l for l in LEDGES if inter(offset([piece], 0.4), regions[l])]
    if not touch: continue
    l = max(touch); regions[l] = outers(union(regions[l], offset([piece], 0.3))); n_t += 1

# ---------- 5. screws: on full-height plate, anchors round about them ----------
def solid_at(q, margin):
    """the second-level part with full-height plate under a boss of radius margin at q (the motion-works plate or the rim plate), or None"""
    disc_ = [circle(q, margin)]
    if area(diff(disc_, rim_paths)) < 1e-3: return rimL
    if area(diff(disc_, foot)) < 1e-3 and area(inter(disc_, union(*regions.values(), SEC_WIN))) < 1e-3: return mw
    return None
# the hand cock: the widest symmetric span (near Adam's 61 deg either side) whose end screws and landing screw sit on full plate
h_ok = None
for h in sorted(np.arange(50.0, 66.01, 0.5), key=lambda h: abs(h - 61.0)):
    if all(solid_at(polar(O, R_RING, AXIS_HC + s * h), R_ANCHOR) is mw for s in (-1, 1)): h_ok = h; break
if h_ok is None: raise SystemExit('no full plate under the hand cock\'s end screws')
hand_p = hand_shape(h_ok)
land = next((polar(O, R_RING, A_LAND + da) for da in sorted(np.arange(-14.0, 14.01, 0.5), key=abs) if solid_at(polar(O, R_RING, A_LAND + da), R_ANCHOR) is mw), None)
HAND_SCREWS = [polar(O, R_RING, AXIS_HC - h_ok)] + ([land] if land is not None else []) + [polar(O, R_RING, AXIS_HC + h_ok)]
if land is None: log.append('hand cock: no full plate near the bar\'s landing; two screws')
else: log.append(f'hand cock: the middle screw at {deg(land):.1f} deg (the bar lands at {A_LAND:.1f}; nearest full plate)')
log.append(f'hand cock: band r {R_TOP - 2 * R_ANCHOR:.1f}-{R_TOP} from {AXIS_HC - h_ok:.1f} to {AXIS_HC + h_ok:.1f} deg (symmetric about {AXIS_HC:.1f}), '
           f'round ends on screws, bar 6.4 wide through the hour star to a hub r {R_HUB} on the hand arbor; {len(HAND_SCREWS)} screws on r {R_RING}')
# the crescent: four screws on r 60.8, in symmetric pairs about the track's middle, clear of the track's numbers and the lettering
lab_ang = [trk['a0'] + (trk['a1'] - trk['a0']) * int(k) / trk['n'] for k in trk.get('labels', {})]
texts = [e for e in pr['decor']['engrave'][cres['id']] if e['kind'] == 'text']
def screw_ok(q):
    if area(diff([circle(q, R_ANCHOR)], cres_p)) > 1e-3: return False
    qa = deg(q - Qh); qd = math.dist(q, Qh)
    if qd < trk['r'] + max(trk['len']) + 0.6 + 2.1: return False                           # clear of the ticks
    if any(abs((qa - a + 180) % 360 - 180) * math.pi / 180 * trk['rl'] < 2.1 + 1.5 + trk['size'] and abs(qd - trk['rl']) < 2.1 + trk['size'] for a in lab_ang): return False
    if any(math.dist(q, t['at']) < 2.1 + 0.6 * len(t['text']) * t['size'] / 2 for t in texts): return False
    if any(math.dist(q, b) < R_HUB + R_ANCHOR + 2 for b in (Bc,)): return False
    if any(math.dist(q, c['at']) < 6.0 for c in rimL.get('cuts', []) if c['kind'] == 'screw'): return False      # the rim plate's own screws
    return solid_at(q, R_ANCHOR) is not None
def on_ring(qa):
    """the point on r 60.8 (about the centre) seen at angle qa from the hand arbor"""
    u = polar((0, 0), 1, qa); return Qh + u * ring_hit(Qh, u, R_RING)
best = None
for a1 in np.arange(6.0, 40.0, 0.5):
    if not all(screw_ok(on_ring(TRK_MID + s * a1)) for s in (-1, 1)): continue
    for a2 in np.arange(a1 + 14.0, PHI - 4.0, 0.5):
        if not all(screw_ok(on_ring(TRK_MID + s * a2)) for s in (-1, 1)): continue
        score = (a2, -abs(a2 - 3 * a1))
        if best is None or score > best[0]: best = (score, a1, a2)
if best is None: raise SystemExit('no symmetric place for the crescent\'s screws')
_, a1, a2 = best
CRES_SCREWS = [on_ring(TRK_MID + s) for s in (-a2, -a1, a1, a2)]
log.append(f'crescent: four screws on r {R_RING} at {a1:.1f} and {a2:.1f} deg either side of the track\'s middle')

# ---------- 6. the top parts' outlines and cuts ----------
n, err, _ = set_outline(cres, cres_p, 0.03); cres['name'] = 'Crescent and balance bridge (the minute track; the balance\'s upper bearing)'
cres['mill'] = 'front'; SK[cres['sketch']]['plane'] = {'axis': 'z', 'offset': ZT}; cres['thickness'] = T_TOP
cres['cuts'] = [c for c in cres.get('cuts', []) if c.get('at') is None]
cut(cres, 'bearing', 'Bearing · balance (upper) (1×3×1)', 3.0, Bc, 1, 'front', axis='balance')
add_windows(cres, 'between the balance bars and the band')
for i, q in enumerate(CRES_SCREWS):
    under = solid_at(q, R_ANCHOR)
    cut(cres, 'screw', f'Screw · crescent {i + 1}, into the {"rim plate" if under is rimL else "motion-works plate"} (M2 countersunk)', 2.2, q, None, 'back', CSK)
log.append(f'crescent: {n} dots (within {err[0]:.3f} mm)')
n, err, _ = set_outline(hand, hand_p, 0.03); hand['mill'] = 'front'
hand['name'] = 'Hand cock (a rim band on three screws; the hand arbor\'s and hour star\'s upper bearings)'
keep = [c for c in hand.get('cuts', []) if c['kind'] in ('bearing', 'clear')]
hand['cuts'] = []
for c in keep: c = dict(c); c['id'] = next_cut(hand); hand['cuts'].append(c)
add_windows(hand, 'hand cock')
for i, q in enumerate(HAND_SCREWS): cut(hand, 'screw', f'Screw · hand cock {i + 1}, into the motion-works plate (M2 countersunk)', 2.2, q, None, 'back', CSK)
log.append(f'hand cock: {n} dots (within {err[0]:.3f} mm)')
# the balance bridge is now part of the crescent
if bal is not None:
    st['drawn'] = [d for d in st['drawn'] if d['id'] != bal['id']]
    pr['decor']['colors'].pop(bal['id'], None)
    for k in ('locks',):
        pr['defaults'].get(k, {}).pop(bal['id'], None)
    log.append('balance bridge merged into the crescent (its part removed)')

# the rim plate: its own screws to the main plate stay where they are if still well inside it and clear of the crescent's
rimL['cuts'] = [c for c in rimL.get('cuts', []) if c['kind'] != 'pilot' or 'crescent' not in c['name']]
for c in [c for c in rimL['cuts'] if c['kind'] == 'screw']:
    q = c['at']
    if area(diff([circle(q, R_ANCHOR + 0.5)], rim_paths)) > 1e-3 or any(math.dist(q, s) < 6.0 for s in CRES_SCREWS):
        log.append(f'rim plate screw at {q} no longer fits: CHECK');
for i, q in enumerate(CRES_SCREWS):
    under = solid_at(q, R_ANCHOR)
    cut(under, 'pilot', f'Screw pilot · crescent {i + 1} (M2' + (', drilled through)' if under is rimL else ')'), 1.6, q, None if under is rimL else 4.0, 'back')
for i, q in enumerate(HAND_SCREWS): cut(mw, 'pilot', f'Screw pilot · hand cock {i + 1} (M2)', 1.6, q, 4.0, 'back')

# ---------- 7. the motion-works plate's full-height top lines up with the parts sitting on it ----------
M = diff(foot, union(*regions.values(), SEC_WIN))
M2 = M
for ref in (cres_p, hand_p): M2 = snap_inside(M2, ref, 2.0)
needed = union(*[SEATS[l] for l in LEDGES], SEC_WIN)
M2 = inter(diff(M2, needed), foot)
grown, shrunk = diff(M2, M), diff(M, M2)
for l in LEDGES: regions[l] = outers(diff(regions[l], M2))
for piece in outers(shrunk):                                              # plate taken down to the ledge beside it
    touch = [l for l in LEDGES if inter(offset([piece], 0.3), regions[l])] or [LEDGES[-1]]
    l = max(touch); regions[l] = outers(union(regions[l], offset([piece], 0.05)))
log.append(f'full-height top: {area(grown):.1f} mm² filled and {area(shrunk):.1f} mm² taken down so its edges sit flush under the parts above')
for l in sorted(LEDGES, reverse=True):
    for p in regions[l]:
        if abs(pc.Area(p)) / (S * S) > 0.3: pocket(mw, f'Ledge at {l} mm (seats: {", ".join(sorted(set(names_by_ledge[l])))})', p, ZT - l)
pocket(mw, 'Window down to the seconds wheel (through, flush with its recess)', SEC_WIN[0], None)
# the barrel and centre arbors' upper bearings, in the plate under their seats: a 3x6x2.5 bearing in a bore from the top that
# stops 2.5 below the seat's floor (a lip holds it), the arbor through the lip
for ax_, label in (('barrel', 'barrel'), ('center', 'centre')):
    q = np.array(POS[ax_], float); pt = P([q])[0]
    if not pc.PointInPolygon(pt, foot[0]): continue
    floor_ = max([l for l in LEDGES if any(pc.PointInPolygon(pt, r) for r in regions[l])] or [ZT])
    lip = floor_ - 2.5 - Z0
    if lip >= 1.0:
        cut(mw, 'bearing', f'Bearing · {label} (upper, 3×6×2.5, under its seat)', 6.0, q, round(ZT - floor_ + 2.5, 3), 'back', axis=ax_)
        cut(mw, 'clear', f'{label.capitalize()} arbor through the plate', 3.2, q, None, 'back')
        log.append(f'{label} arbor: upper bearing in the plate, its bore from the {floor_} floor, a {lip:.1f} mm lip under it')
    else:                                                                   # too little floor for a lip: a press fit in a bore right through
        cut(mw, 'bearing', f'Bearing · {label} (upper, 3×6×2.5, pressed into a bore through the floor)', 6.0, q, None, 'back', axis=ax_)
        log.append(f'{label} arbor: upper bearing pressed into a bore through the plate\'s {floor_ - Z0:.1f} mm floor (no room for a lip)')
log.append('ledges: ' + '; '.join(f'{l}: {", ".join(sorted(set(names_by_ledge[l])))}' for l in LEDGES) + f'; {n_t} towers cut down')

# ---------- 8. the seconds bridge: the pill (r 3.2 ends, like every anchor), sunk onto the 15.5 floor ----------
sp = F(outline(sec)[0])
far = max(((i, j) for i in range(0, len(sp), 2) for j in range(i + 1, len(sp), 2)), key=lambda ij: np.hypot(*(sp[ij[0]] - sp[ij[1]])))
u = sp[far[1]] - sp[far[0]]; u = u / np.hypot(*u)
for L2 in np.arange(18.7 + 0.75 + 3.0, 34.0, 0.25):
    e0, e1 = Fo - u * L2, Fo + u * L2
    if all(any(pc.PointInPolygon(P([q])[0], f) == 1 for f in offset(foot, -(R_ANCHOR + 0.3 + 0.8)) if pc.Orientation(f)) for q in (e0, e1)): break
else: raise SystemExit('no room for the seconds pill')
pill = capsule(e0, e1, R_ANCHOR)
set_outline(sec, pill, 0.03); Z_SEC = LEDGES[0]
SK[sec['sketch']]['plane'] = {'axis': 'z', 'offset': Z_SEC}; sec['thickness'] = T_TOP; sec['mill'] = 'front'; sec['cuts'] = []
cut(sec, 'bearing', 'Bearing · seconds (upper, 1×3×1)', 3.0, Fo, 1.0, 'front', axis='fourth')
seat = offset(pill, 0.3); near_out = diff(offset(seat, 1.6), foot)
if near_out: seat = [max(close(union(seat, near_out), 0.8), key=lambda p_: abs(pc.Area(p_)))]
pocket(mw, 'Seat for the seconds bridge (sunk onto the 15.5 floor)', seat[0], ZT - Z_SEC)
main['cuts'] = [c for c in main['cuts'] if 'seconds bridge' not in c['name']]
for i, q in enumerate((e0, e1)):
    cut(sec, 'screw', f'Screw · seconds bridge {i + 1} (M2 countersunk)', 2.2, q, None, 'back', CSK)
    cut(mw, 'pilot', f'Screw pilot · seconds bridge {i + 1} (M2, through the floor)', 1.6, q, None, 'back')
    if all(math.dist(q, (e['x'], e['y'])) > e['r'] + 0.75 + 0.8 + 1.5 for e in ELS if e['z0'] < Z0):
        cut(main, 'pilot', f'Screw pilot · seconds bridge {i + 1} (M2)', 1.6, q, 4.0, 'back')
log.append(f'seconds bridge: pill {2 * L2 + 2 * R_ANCHOR:.1f} x {2 * R_ANCHOR:.1f}, sunk {ZT - Z_SEC:.2f}')

# ---------- 9. tidy ----------
for d in st['drawn']:
    hs_ = d.pop('_holes', None)
    if hs_: log.append(f'NOTE {d["name"][:30]}: {len(hs_)} enclosed holes in its outline were not cut')
pr['hands'] = [h for h in pr['hands'] if h['id'] != 'seconds_hand']
used = {d['sketch'] for d in st['drawn']} | {c['sketch'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
before = len(st['sketches']); st['sketches'] = [k for k in st['sketches'] if k['id'] in used]
log.append(f'{before - len(st["sketches"])} unused outlines removed')
for d in (sec, hand, cres): pr['decor']['colors'][d['id']] = '#d9dcdf'
J['savedAt'] = '2026-11-18T15:00:00.000Z'
json.dump(J, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('\n'.join(log)); print('written', OUT, '|', len(st['drawn']), 'parts,', len(st['sketches']), 'sketches')
