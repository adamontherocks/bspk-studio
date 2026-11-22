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
#   2026-11-18 (Adam's markup notes): every perimeter flush at r 66; the balance and escapement opening is the main plate's
#   recess walls united (balance well, fork sweep, escape wheel) plus the side window's slot; straight support arms with round
#   bosses and upper bearings to the escape and fork arbors; the outcrop over the intermediate wheel an arc about it; the
#   motion-works plate screwed down to the main plate (orphan pilots removed); no thin strips taken down along parts' edges
#
#   python3 refine.py ADAM.json OUT.json [NOTES_FROM.json]   (the markup notes are carried over from the third file)
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import *
import pyclipper as pc

SRC, OUT = sys.argv[1:3]; NOTES_FROM = sys.argv[3] if len(sys.argv) > 3 else None
J = json.load(open(SRC)); st = J['state']; pr = J['project']; mech = pr['mechanisms']
import esc2_apply
_esc_log = []
if os.path.exists(os.path.join(HERE, 'escapement2_geo.json')): esc2_apply.apply(J, _esc_log)
import retro2
retro2.apply(J, _esc_log, LF=float(os.environ.get('RETRO_LF', 17.0)))                                                  # feeler pin Ø1.5 closer to the pivot, snail re-cut (P26, P27)
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
log = list(_esc_log)

# ---------- the family of sizes ----------
R_MAIN, R_L2, R_TOP, SNAP, GAP = 66.0, 66.0, 66.0, 3.0, 0.5       # every perimeter flush (Adam: the steps read as misalignment)
R_ANCHOR, R_HUB, R_IN, R_OUT = 3.2, 5.0, 2.0, 1.0
R_RING = R_TOP - R_ANCHOR                                                 # 62.8: the centre line of the rim bands; every rim screw
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

MP_HOLES = []                                                              # everything cut into the main plate's top
for c in main['cuts']:
    if c.get('at') and c.get('d') and c['kind'] in ('hole', 'bearing', 'clear', 'pilot'): MP_HOLES.append(circle(c['at'], c['d'] / 2))
    elif c['kind'] == 'pocket' and c.get('sketch') in SK: MP_HOLES.append(P(ccw(np.array([(q['u'], q['v']) for q in SK[c['sketch']]['points']]))))
MP_HOLES = union(MP_HOLES)
MP_SHOWN = union([circle(c['at'], c['d'] / 2) for c in main['cuts'] if c['kind'] == 'hole' and c.get('at') and c.get('d') and c['name'].startswith('Recess')],
                 [p for name, p in UNDER for p in p])                     # the recesses, trims and side windows: the edges you see
# (P29) a cusp of full-height main plate between two recesses gets a round nose (r 1), not a round notch cut into it
RECESS_D = union([circle(c['at'], c['d'] / 2) for c in main['cuts'] if c['kind'] == 'hole' and c['name'].startswith('Recess')])
n_trim = 0
for c in list(main['cuts']):
    if c['kind'] != 'hole' or not c['name'].startswith('Cusp trimmed'): continue
    zone = [circle(c['at'], c['d'] / 2 + 3.0)]
    mat = inter(zone, diff(BIG, RECESS_D))
    nose = diff(mat, offset(offset(mat, -1.0), 1.0))                       # the sliver a 1 mm round nose takes off the cusp's tip
    nose = [q for q in nose if pc.Orientation(q) and abs(pc.Area(q)) / (S * S) > 0.02 and not inter([q], offset(diff(BIG, zone), 0.05))]
    main['cuts'].remove(c)
    for q in nose:
        kid = add_sketch(c['name'].replace('Cusp trimmed', 'Cusp rounded') + ' (pocket outline)', [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in F(q)])
        main['cuts'].append({'id': next_cut(main), 'kind': 'pocket', 'name': c['name'].replace('Cusp trimmed', 'Cusp rounded (r 1 nose)'), 'from': 'back', 'depth': c['depth'], 'sketch': kid, 'seat': None, 'csk': None})
    n_trim += 1
log.append(f'main plate: {n_trim} cusp trims (round notches) replaced by r 1 noses on the cusps')
def recess(name):
    c = next(c for c in main['cuts'] if c['kind'] == 'hole' and c['name'] == f'Recess · {name}'); return np.array(c['at'], float), c['d'] / 2
SIDE_BAL = next(p for name, p in UNDER if name.startswith('side window') and 'balance' in name)
Y_WIN = float(F(SIDE_BAL[0])[:, 1].min())                                  # the balance side window's lower edge (-6)

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
mwp = outline(mw); mw_raw = mwp
ab = math.degrees(math.atan2(B[1], B[0]))
mwp = union(mwp, [sector(50.0, R_L2, ab - 18.0, ab + 26.0)])           # the barrel window: the edge runs to the rim over it
mwp = union(mwp, diff(rim0, offset(rim_p, GAP)))                         # where the rim plate got shorter, this plate fills in (P9)
mwp = snap_rim(mwp, R_L2)
hand_p0 = hand_shape(61.0)
mwp = snap_inside(mwp, MP_SHOWN, 2.0)                                     # walls straight down onto the main plate's visible edges
for ref in (cres_p, hand_p0): mwp = snap_inside(mwp, ref, 2.0)              # and straight up into the parts above
pre = mwp
# the seconds pill (placed now: the opening keeps clear of its screw ends)
sp = F(outline(sec)[0])
far = max(((i, j) for i in range(0, len(sp), 2) for j in range(i + 1, len(sp), 2)), key=lambda ij: np.hypot(*(sp[ij[0]] - sp[ij[1]])))
u = sp[far[1]] - sp[far[0]]; u = u / np.hypot(*u)
L_now = np.hypot(*(sp[far[1]] - sp[far[0]])) / 2 - R_ANCHOR               # already a pill (the last pass made it): keep its length
for L2 in ([round(L_now, 2)] if abs(np.dot(sp - Fo, [-u[1], u[0]])).max() < R_ANCHOR + 0.1 else []) + list(np.arange(18.7 + 0.75 + 3.0, 34.0, 0.25)):
    e0, e1 = Fo - u * L2, Fo + u * L2
    if L2 == round(L_now, 2) or all(any(pc.PointInPolygon(P([q])[0], f) == 1 for f in offset(mw_raw, -(R_ANCHOR + 0.3 + 0.8)) if pc.Orientation(f)) for q in (e0, e1)): break
else: raise SystemExit('no room for the seconds pill')
pill = capsule(e0, e1, R_ANCHOR)
KEEP_PILL = offset(pill, 0.3)                                               # the pill's seat: the window's bite follows it exactly (P20)
# the balance and escapement opening: the main plate's recess walls under it, united with Adam's opening and the side window's slot
BW, RB = recess('balance well'); FK, RF = recess('pallet fork sweep'); ES, RE = recess('escape wheel')
def part_with(paths, q):
    return [p for p in outers(paths) if pc.PointInPolygon(P([q])[0], p)]
adam_open = part_with(diff([circle(O, R_L2 - 0.5)], union(mwp, offset(rim_p, GAP + 0.3))), Bc)
DISCS = union([circle(BW, RB)], [circle(FK, RF)], [circle(ES, RE)], SIDE_BAL)
adam_open = snap_to(adam_open, DISCS, 2.5)                                 # his edges that ran 1-2 mm off the walls go onto them (P18)
OPEN = diff(union(adam_open, DISCS), KEEP_PILL)
CW, RCW = recess('centre wheel')
dd = np.hypot(*(CW - ES)); aa = (RE ** 2 - RCW ** 2 + dd ** 2) / (2 * dd); hh = math.sqrt(RE ** 2 - aa ** 2)
uu = (CW - ES) / dd; pp = np.array([-uu[1], uu[0]]); cusps = [ES + aa * uu + s_ * hh * pp for s_ in (1, -1)]
CUSP_EC = min(cusps, key=lambda q: q[1])                                    # the escape window meets the centre wheel's wall here (P21)

mwp = diff(mwp, OPEN)
# the fork's support: a straight arm from the plate's left body to a round boss on the fork arbor; its top edge carries on the
# side window's lower edge (y -6), so that line runs unbroken from the rim plate to the fork (P2, P3, P14)
yc = Y_WIN - R_ANCHOR
x_joint = Qh[0] - math.sqrt((RIN + 3.0 + GAP) ** 2 - (yc - Qh[1]) ** 2); x_bal = BW[0] - math.sqrt(RB ** 2 - (yc - BW[1]) ** 2)
ROOT_F = np.array([(x_joint + x_bal) / 2, yc])
FORK_ARM = capsule(ROOT_F, FK, R_ANCHOR)
# the escape's support: a straight arm from the plate on Adam's side (his peninsula) to a round boss on the escape arbor (P1, P8)
ring_ = inter(diff([circle(ES, RE + 5.0)], [circle(ES, RE)]), pre)
adam_dir = deg(np.mean(np.vstack([F(p) for p in outers(ring_)]), 0) - ES) if ring_ else 40.0
SEATS_ALL = union(*SEATS.values())
def esc_arm(a):
    # it may cross a seat (there it is the seat's floor, as Adam's peninsula was); never the pill's ends or a moving part's room
    end = polar(ES, RE + 4.5, a); arm = capsule(ES, end, R_ANCHOR)
    bad = area(inter(arm, union(KEEP_PILL, MOVER_CUT))) + max(0.0, area(diff([circle(end, R_ANCHOR)], mwp)) - 3.0)   # its root mostly on plate
    return bad, arm
cands = [a for a in np.arange(-180.0, 180.0, 2.0) if esc_arm(a)[0] < 0.05]
cands.sort(key=lambda a: (area(inter(esc_arm(a)[1], SEATS_ALL)) // 5, abs((a - adam_dir + 180) % 360 - 180)))
A_ESC = 16.0 if 16.0 in cands else (cands[0] if cands else None)
if A_ESC is None: raise SystemExit('no clear line for the escape support arm')
ESC_ARM = esc_arm(A_ESC)[1]
mwp = union(mwp, FORK_ARM, ESC_ARM)
d_ = (FK - ROOT_F) / np.hypot(*(FK - ROOT_F)); n_ = np.array([d_[1], -d_[0]])          # the arm's line, and its lower side
below = [P([ROOT_F - 100 * d_, FK + 100 * d_, FK + 100 * d_ + 100 * n_, ROOT_F - 100 * d_ + 100 * n_])]
box_l = [P([(ROOT_F[0] - 12, -80), (FK[0], -80), (FK[0], 80), (ROOT_F[0] - 12, 80)])]
FILL_F = diff(inter(below, box_l), [circle(Fo, 18.7 + 0.75)])
mwp = union(mwp, FILL_F)                                                   # (P17, P19) the arm's underside is the seconds window's arc
Y_TOP_WIN = float(F(SIDE_BAL[0])[:, 1].max())                              # the side window's top edge (18)
CORNER = np.array([BW[0] - math.sqrt(RB ** 2 - (Y_TOP_WIN - BW[1]) ** 2), Y_TOP_WIN])
FILL18 = inter(diff([P([CORNER + (-8, 0), CORNER + (8, 0), CORNER + (8, 8), CORNER + (-8, 8)])], [circle(BW, RB)]), [circle(CORNER, 7.0)])
mwp = union(mwp, FILL18)                                                   # (P18) the corner is exactly the window line meeting the balance arc
log.append(f'balance and escapement opening: the main plate\'s balance well (r {RB}), fork sweep (r {RF}) and escape wheel (r {RE}) walls '
           f'and the side window\'s slot, united; fork arm from ({ROOT_F[0]:.1f}, {ROOT_F[1]:.1f}), its top edge on the window line y {Y_WIN:.1f}; '
           f'escape arm at {A_ESC:.0f} deg (Adam\'s peninsula pointed {adam_dir:.0f}); both end in r {R_ANCHOR} bosses on their arbors')
# the outcrop over the intermediate wheel: its edge an arc about the wheel, just inside the tooth roots (P4)
IW = np.array(POS['inter'], float); R_IW_EDGE = 21.0; R_IW_WALL = recess('intermediate wheel')[1]   # just inside the tooth roots (22.45); the recess wall (25.45)
probe = IW + polar((0, 0), 23.5, -75.0)
notch = part_with(diff([circle(O, R_L2 - 0.5)], union(mwp, offset(rim_p, GAP + 0.3))), probe)
NOTCH_WIN = []
if notch:
    qn = np.vstack([F(p) for p in notch]); rn = np.hypot(*(qn - IW).T); an = np.degrees(np.arctan2(*(qn - IW).T[::-1]))
    sel = (rn > R_IW_EDGE + 1.0) & (rn < 40.0); a_lo, a_hi = float(an[sel].min()), float(an[sel].max())
    mid, half = (a_lo + a_hi) / 2, (a_hi - a_lo) / 2
    notch_new = diff(inter(fan(IW, mid - half, mid + half), [circle(IW, R_IW_WALL)]), [circle(IW, R_IW_EDGE)])   # an even crescent, concentric with the wheel
    mwp = snap_rim(union(mwp, offset(notch, 0.05)), R_L2)                  # the plate whole here, out to the rim; the window is cut as a through pocket
    NOTCH_WIN = [max(outers(opening(notch_new, R_IN)), key=lambda p_: abs(pc.Area(p_)))]
    log.append(f'window over the intermediate wheel (a through pocket): both ends radial about the wheel at {mid - half:.1f} and {mid + half:.1f} deg (symmetric about {mid:.1f}), '
               f'r {R_IW_EDGE}-{R_IW_WALL} about the wheel (inner edge just inside the tooth roots, outer edge on the main plate\'s recess wall)')
    log.append(f'outcrop over the intermediate wheel: its edge an arc r {R_IW_EDGE} about the wheel (tooth tips r 24.7, recess wall r 25.45)')
# (P23, P24) an edge of the plate that hangs over a gear runs concentric with that gear, at its own mean radius
def concentric(mwp, c, probes, half=7.0):
    c = np.asarray(c, float); probes = [np.asarray(q, float) for q in probes]; probe = probes[0]
    bd = np.vstack([F(p) for p in mwp]); near = bd[np.min([np.hypot(*(bd - q).T) for q in probes], 0) < half]
    if len(near) < 5: return mwp, None
    r_ = np.hypot(*(near - c).T); r_p = [float(np.hypot(*(bd[np.argmin(np.hypot(*(bd - q).T))] - c))) for q in probes]
    r0 = float(np.mean(r_p)); keep = near[np.abs(r_ - r0) < 3.0]
    ang = np.degrees(np.arctan2(keep[:, 1] - c[1], keep[:, 0] - c[0])); a_ref = math.degrees(math.atan2(probe[1] - c[1], probe[0] - c[0]))
    ang = (ang - a_ref + 180) % 360 - 180 + a_ref; a_lo, a_hi = float(ang.min()), float(ang.max())
    band = inter(diff([circle(c, r0 + 3.5)], [circle(c, r0 - 3.5)]), fan(c, a_lo, a_hi))
    inside = any(pc.PointInPolygon(P([c + (r0 - 1.5) * (probe - c) / np.hypot(*(probe - c))])[0], q) == 1 for q in mwp if pc.Orientation(q))
    side = [circle(c, r0)] if inside else diff([circle(c, r0 + 3.6)], [circle(c, r0)])
    return union(diff(mwp, band), inter(band, side)), (r0, a_lo, a_hi)
for wheel, probe, note in (('center', [(8.54, 11.03), (6.15, 17.30)], 'P23, P35'), ('barrel', [(-6.57, 26.79), (-2.12, 23.64)], 'P24, P36')):
    mwp, res = concentric(mwp, POS[wheel], probe)
    if res: log.append(f'{note}: the edge over the {wheel} wheel is now an arc r {res[0]:.2f} about it ({res[1]:.0f} to {res[2]:.0f} deg)')
# (P41) the end of the notch over the barrel: one even radius (the open slot's end rounded to half its width)
def even_end(mwp, probe, zr=8.0):
    zone = [circle(probe, zr)]; open_ = diff(zone, mwp); r_ = 0.5
    while r_ < 6 and any(pc.Orientation(q) for q in offset(open_, -(r_ + 0.25))): r_ += 0.25
    return union(diff(mwp, zone), diff(zone, opening(open_, r_))), r_
mwp, r_end = even_end(mwp, np.array([-15.96, 37.53]))
log.append(f'P41: the notch\'s top end is one even radius (r {r_end:.2f}, half its width)')
def hard(p): return diff(inter(p, [circle(O, R_L2)]), union(offset(rim_paths, GAP), MOVER_CUT))
mwp = hard(clean(hard(mwp)))
# (P21) where the escape arm's top edge, the escape window and the centre wheel's wall meet, one smooth blend (r 3) instead of wiggles
zone = [circle(CUSP_EC, 5.5)]
mwp = hard(union(diff(mwp, zone), inter(close(opening(mwp, 3.0), 3.0), zone)))
mwp = hard(close(mwp, 1.6))
big, holes, scraps = outer_and_holes(mwp); mwp = [big]
n, err, scraps_ = set_outline(mw, mwp, 0.08); foot = outline(mw)
mw['cuts'] = []; mw['thickness'] = T_MW; SK[mw['sketch']]['plane'] = {'axis': 'z', 'offset': Z0}
log.append(f'motion-works plate: r {R_L2} flush, edges on the main plate\'s visible edges below and the parts above (within 2 mm), '
           f'0.5 mm joint, corners r {R_IN}/{R_OUT}; {n} dots' + (f'; scraps dropped {[round(abs(pc.Area(s)) / S / S, 1) for s in scraps]} mm²' if scraps else ''))

# seats on three ledges, towers down
lim = offset(foot, 1.5); regions = {}
for l in LEDGES:
    r = inter(clean(SEATS[l], 1.0, 1.0), lim) if SEATS[l] else []
    regions[l] = outers(r)
top_left = diff(foot, union(*regions.values(), SEC_WIN, NOTCH_WIN)); edge_band = diff(foot, offset(foot, -1.5)); n_t = 0
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
    if area(diff(disc_, foot)) < 1e-3 and area(inter(disc_, union(*regions.values(), SEC_WIN, NOTCH_WIN))) < 1e-3: return mw
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

# (P34, P37, P38) no shelf or wall thinner than 2 mm at any level: it drops to the next level down beside it
THRU = union(SEC_WIN, NOTCH_WIN)
def level_region(h):
    if h == ZT: return diff(foot, union(*regions.values(), THRU))
    lower = [l for l in LEDGES if l < h]
    return diff(inter(union(regions[h]), foot), union(*[regions[l] for l in lower], THRU)) if regions[h] else []
n_thin = 0
for h in [ZT] + sorted(LEDGES, reverse=True)[:-1]:
    R = level_region(h)
    if not R: continue
    thin = [q for q in outers(diff(R, opening(R, 1.0))) if abs(pc.Area(q)) / (S * S) > 0.05]
    for q in thin:
        near = [l for l in LEDGES if l < h and inter(offset([q], 0.3), regions[l])]
        if not near: continue
        l = max(near); regions[l] = outers(union(regions[l], offset([q], 0.05))); n_thin += 1
log.append(f'{n_thin} slivers of plate thinner than 2 mm taken down to the level beside them')

# ---------- 7. the plate's pockets (no thin strips taken down along parts' edges: Adam's P12, P13) ----------
for l in sorted(LEDGES, reverse=True):
    for p in regions[l]:
        if abs(pc.Area(p)) / (S * S) > 0.3: pocket(mw, f'Ledge at {l} mm (seats: {", ".join(sorted(set(names_by_ledge[l])))})', p, ZT - l)
pocket(mw, 'Window down to the seconds wheel (through, flush with its recess)', SEC_WIN[0], None)
if NOTCH_WIN: pocket(mw, 'Window over the intermediate wheel (through; its inner edge an arc about the wheel, its ends radial)', NOTCH_WIN[0], None)
cut(mw, 'bearing', 'Bearing · escape (upper, 1×3×1, pressed into the support arm\'s boss)', 3.0, ES, None, 'back', axis='escape')
cut(mw, 'bearing', 'Bearing · pallet fork (upper, 1×3×1, pressed into the support arm\'s boss)', 3.0, FK, None, 'back', axis='fork')
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

# ---------- 8b. the main plate where it shows through the openings: no towers, no points (P31-P33, P39, P40) ----------
mw_mat = diff(foot, THRU)
VISIBLE = diff(diff([circle(O, R_MAIN)], union(mw_mat, rim_paths)), [])
keep_out = union([circle(c['at'], c['d'] / 2 + 2.0) for c in main['cuts'] if c.get('at') and c.get('d') and c['kind'] in ('bearing', 'clear', 'pilot')])
mp_levels = {}
for c in main['cuts']:
    if c.get('from', 'back') != 'back' or c['kind'] not in ('hole', 'pocket'): continue
    poly = [circle(c['at'], c['d'] / 2)] if c.get('at') and c.get('d') else ([P(ccw(np.array([(q['u'], q['v']) for q in SK[c['sketch']]['points']])))] if c.get('sketch') in SK else [])
    if not poly: continue
    z = round(12.7 - (main['thickness'] if c.get('depth') is None else c['depth']), 2)
    mp_levels.setdefault(z, []).extend(poly)
zs = sorted(mp_levels)                                                    # floors, deepest first
covered = {z: union(*[mp_levels[z2] for z2 in zs if z2 <= z]) for z in zs}  # where the plate is at z or deeper
def mp_region(h):                                                         # the main plate's surface at height h
    deeper = [z for z in zs if z < h]
    at = union(mp_levels[h]) if h in mp_levels else diff([circle(O, R_MAIN)], covered[zs[-1]])
    return diff(at, covered[max(deeper)]) if deeper else at
n_tw = n_pt = 0
for h in sorted(set(zs + [12.7]), reverse=True):
    if h == min(zs): continue
    R = inter(mp_region(h), VISIBLE)
    if not R: continue
    gone = []
    for q in outers(R):                                                   # towers: small islands standing above everything round them
        if abs(pc.Area(q)) / (S * S) < 20.0 and not inter(offset([q], 0.3), diff(mp_region(h), [q])): gone.append(q); n_tw += 1
    pts_ = [q for q in outers(diff(R, opening(R, R_IN))) if abs(pc.Area(q)) / (S * S) > 0.05]
    n_pt += len(pts_)
    for q in gone + pts_:
        q2 = diff(inter([q], VISIBLE), keep_out)
        if not q2: continue
        lower = [z for z in zs if z < h and inter(offset(q2, 0.3), mp_region(z))]
        if not lower: continue
        z_to = max(lower)
        for piece in outers(q2):
            if abs(pc.Area(piece)) / (S * S) < 0.05: continue
            kid = add_sketch('Main plate tidy (pocket outline)', [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in F(piece)])
            main['cuts'].append({'id': next_cut(main), 'kind': 'pocket', 'name': f'Tidy: {"tower cut down" if q in gone else "point rounded r 2"} to {z_to}', 'from': 'back',
                                 'depth': round(12.7 - z_to, 3), 'sketch': kid, 'seat': None, 'csk': None})
log.append(f'main plate where it shows: {n_tw} towers cut down, {n_pt} pointed corners rounded r {R_IN}')

# ---------- 9. the motion-works plate screwed down to the main plate (P9) ----------
taken = [c['at'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('at') and c['kind'] in ('screw', 'bearing', 'clear', 'pilot') and d is not main]
def mp_ok(q): return not inter([circle(q, 2.0)], MP_HOLES)
cand = [polar(O, R_RING, a) for a in np.arange(0.0, 360.0, 1.0)]
cand = [q for q in cand if solid_at(q, R_ANCHOR) is mw and mp_ok(q) and all(math.dist(q, t) >= 7.0 for t in taken)]
MW_SCREWS = []
for _ in range(6):
    if not cand: break
    q = max(cand, key=lambda q: min([abs((deg(q) - deg(m) + 180) % 360 - 180) for m in MW_SCREWS] or [999]) + (0.001 * deg(q) if not MW_SCREWS else 0))
    MW_SCREWS.append(q); cand = [c for c in cand if math.dist(c, q) >= 20.0]
for i, q in enumerate(MW_SCREWS):
    cut(mw, 'screw', f'Screw · motion-works plate {i + 1}, into the main plate (M2 countersunk)', 2.2, q, None, 'back', CSK)
    cut(main, 'pilot', f'Screw pilot · motion-works plate {i + 1} (M2)', 1.6, q, 4.0, 'back')
screws_all = [c['at'] for d in st['drawn'] for c in d.get('cuts', []) if c['kind'] == 'screw' and c.get('at')]
orph = [c for c in main['cuts'] if c['kind'] == 'pilot' and not any(math.dist(c['at'], q) < 0.2 for q in screws_all)]
main['cuts'] = [c for c in main['cuts'] if c not in orph]
log.append(f'motion-works plate: {len(MW_SCREWS)} screws into the main plate on r {R_RING} at {[round(deg(q)) for q in MW_SCREWS]} deg; '
           f'{len(orph)} orphan pilots removed from the main plate ({", ".join(c["name"].split("· ")[-1].split(" (")[0] for c in orph)})')
# the crescent's numerals must sit on the band (P11)
off_band = []
for k, txt in trk.get('labels', {}).items():
    a = trk['a0'] + (trk['a1'] - trk['a0']) * int(k) / trk['n']; q = polar(Qh, trk['rl'], a)
    rad, tan = polar((0, 0), 1, a), polar((0, 0), 1, a + 90)                # the numeral's box: its height across the band, width along it
    hh, hw = trk['size'] / 2 + 0.6, 0.3 * trk['size'] * len(txt) + 0.6
    box = [P([q + rad * i * hh + tan * j * hw for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))])]
    if area(diff(box, cres_p)) > 1e-3: off_band.append((txt, a, q))
rl0 = trk['rl']
while off_band and trk['rl'] > trk['r'] + max(trk['len']) + trk['size'] / 2 + 0.5:   # bring the numerals in, never onto the ticks
    trk['rl'] = round(trk['rl'] - 0.1, 3); off_band = []
    for k, txt in trk.get('labels', {}).items():
        a = trk['a0'] + (trk['a1'] - trk['a0']) * int(k) / trk['n']; q = polar(Qh, trk['rl'], a)
        rad, tan = polar((0, 0), 1, a), polar((0, 0), 1, a + 90); hh, hw = trk['size'] / 2 + 0.6, 0.3 * trk['size'] * len(txt) + 0.6
        if area(diff([P([q + rad * i * hh + tan * j * hw for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))])], cres_p)) > 1e-3: off_band.append(txt)
log.append('crescent numerals: ' + (f'STILL OFF THE BAND: {off_band}' if off_band else
           f'all on the band with 0.6 mm to spare' + (f' (brought in from r {rl0} to r {trk["rl"]} about the hand arbor)' if trk['rl'] != rl0 else '')))
if NOTES_FROM:
    st['pins'] = json.load(open(NOTES_FROM))['state'].get('pins', [])
    known = {d['id'] for d in st['drawn']} | set(st.get('info', {}))
    log.append(f'{len(st["pins"])} markup notes carried over')

# ---------- 9b. crown worm (P42, P43): the keyless works under the plate go; a worm on the crown stem turns the centre wheel ----------
import worm
worm.apply(J, log)

# ---------- 9b2. crown 2 (P58, P60): the worm's real thread, the stem tilted by its lead angle on two strips, a Ø21 crown off a flat ----------
import crown2
crown2.apply(J, log)

# ---------- 9b3. crown 3 (2026-11-21): the stem horizontal and Ø4, the worm cut on it, a Ø24 crown off a vertical flat ----------
import crown3
crown3.apply(J, log)

# ---------- 9c. clean plates (P44-P60): the main plate's levels rebuilt from its real cuts, the motion-works plate's edge faired and its levels rebuilt ----------
import notes44_60
notes44_60.apply(J, log)

# ---------- 9d. notes P61-P76 (2026-11-21): the other plates' outlines exact, the fork hub disc hidden in the fork ----------
import fixes1121
fixes1121.apply(J, log)

# ---------- 10. tidy ----------
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
