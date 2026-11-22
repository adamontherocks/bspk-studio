# Crescent engineering pass (exact geometry, pyclipper): Adam's latest plates cleaned, lined up and made into parts.
# Grown from tidy.py (2026-11-17). Also, when the scene asks for it:
#   - the crescent and hand bridge is split: the crescent keeps its band outside the minute track's circle (and its track),
#     the hand cock keeps the part inside it from the right-side anchor to the minute hand arbor; no bridge spans the movement
#   - Adam's balance bridge (a new part over the balance well) gets a boss and bearing over the balance staff, two screws
#   - the seconds bridge becomes a clean pill, sunk into the plate onto its 15.5 floor (screws into the floor and the main plate)
#   - perimeters stepped like a real movement: main plate r 66, the second level (crescent rim plate, motion-works plate)
#     r 65, the top level (crescent and hand bridge) r 64; wherever a part comes within 3 mm of its circle, its edge runs
#     out to it, so the steps line up all the way round
#   - parts that meet at the same level get one even 0.5 mm joint (the crescent rim plate keeps its edge, the plate beside
#     it follows it); every outline gets rounded inside corners (r 1.6, a 1/8" end mill) and outside corners (r 1)
#   - the motion-works plate's edge runs out to the rim again over the barrel window, so the window is a clean opening
#     under a straight wall; both side windows get rounded inside corners
#   - the plate's seats settle on three ledges (15.5, 17.1, 19.1): each part sits on the ledge at or under its base
#   - Adam's seconds bridge: on the plate (z 22.225, 2.8 sheet), two screw bosses on solid plate, a bearing boss over the
#     seconds arbor; a window through the plate down to the seconds wheel; no seconds hand
#
#   python3 engineer.py ADAM.json OUT.json
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import *
import pyclipper as pc

SRC, OUT = sys.argv[1:3]
J = json.load(open(SRC)); st = J['state']; pr = J['project']; mech = pr['mechanisms']
SK = {k['id']: k for k in st['sketches']}
def DR(): return {d['id']: d for d in st['drawn']}
def byname(prefix): return next(d for d in st['drawn'] if d['name'].startswith(prefix))
def zband(d): z = SK[d['sketch']]['plane']['offset']; return (z, z + d['thickness'])
def outline(d): return [P(ccw(spline_poly(SK[d['sketch']]['points'])))]      # either way round in the file; anticlockwise here
def add_sketch(name, dots):
    n = 1
    while f'K{n}' in SK: n += 1
    k = {'id': f'K{n}', 'name': name, 'plane': {'axis': 'z', 'offset': 0.0}, 'closed': True, 'points': dots}; st['sketches'].append(k); SK[k['id']] = k; return k['id']
def next_cut(d):
    n = 1; used = {c['id'] for c in d.get('cuts', [])}
    while f'h{n}' in used: n += 1
    return f'h{n}'
def pocket(d, name, path, depth):
    kid = add_sketch(f'{name} (pocket outline)', dots_sharp(simplify(F(path), 0.005)))
    d.setdefault('cuts', []).append({'id': next_cut(d), 'kind': 'pocket', 'name': name, 'from': 'back', 'depth': None if depth is None else round(depth, 3), 'sketch': kid, 'seat': None, 'csk': None})
def cut(d, kind, name, dia, at, depth=None, frm='back', csk=None, axis=None):
    c = {'id': next_cut(d), 'kind': kind, 'name': name, 'from': frm, 'depth': depth, 'seat': None, 'csk': csk, 'at': [round(float(at[0]), 4), round(float(at[1]), 4)], 'd': dia}
    if axis: c['axis'] = axis
    d.setdefault('cuts', []).append(c)
def set_outline(d, paths, tol=0.1):
    big, holes, scraps = outer_and_holes(paths)
    pts, err, L = fit_smooth(big, tol); SK[d['sketch']]['points'] = pts; d['back'] = None; d['edges'] = None
    return len(pts), err, [abs(pc.Area(s)) / (S * S) for s in scraps], [abs(pc.Area(h)) / (S * S) for h in holes]
log = []
R_MAIN, R_L2, R_TOP, SNAP, GAP = 66.0, 65.0, 64.0, 3.0, 0.5
Z0, T_MW = 12.7, 9.525; ZT = Z0 + T_MW
LEDGES = [15.5, 17.1, 19.1]

def snap_rim(paths, R):
    """run the edge out to the circle R wherever the part comes within SNAP of it, then trim to R"""
    near = inter(paths, diff([circle((0, 0), R + 20)], [circle((0, 0), R - SNAP)]))
    fills = []
    for piece in near:
        if not pc.Orientation(piece): continue
        a = np.degrees(np.arctan2(F(piece)[:, 1], F(piece)[:, 0])) % 360; a.sort()
        gaps = np.diff(np.r_[a, a[0] + 360]); k = int(np.argmax(gaps))     # the widest gap between its points is where it isn't
        a0, a1 = (a[0], a[-1]) if k == len(a) - 1 else (a[k + 1], a[k] + 360)
        fills.append(sector(R - SNAP - 0.6, R, a0, a1))
    return inter(union(paths, fills), [circle((0, 0), R)])
def clean(paths, ri=1.6, ro=1.0): return opening(close(paths, ri), ro)

main, rimL, mw = byname('Main plate'), byname('Crescent rim plate'), byname('Motion-works plate')
top = next(d for d in st['drawn'] if d['name'].startswith('Crescent') and not d['name'].startswith('Crescent rim'))
POS = st['pos']; Fo = np.array(POS['fourth'], float); Bc = np.array(POS['balance'], float); B = np.array(POS['barrel'], float)
Qh = np.array(POS['retro'], float); Hs = np.array(POS['hourstar'], float)
RI = json.load(open(os.path.join(HERE, 'crescent_geo.json')))['RI']        # the minute track's circle about the hand arbor
sec = next((d for d in st['drawn'] if d['name'].startswith('Seconds bridge')), None)
hand = next((d for d in st['drawn'] if d['name'].startswith('Hand cock')), None)
fixed_ids = {d['id'] for d in st['drawn'] if d['id'] in mech['mounts']}
known = {main['id'], rimL['id'], mw['id'], top['id']} | ({sec['id']} if sec else set()) | ({hand['id']} if hand else set())
new_top = [d for d in st['drawn'] if d['id'] not in known and d['id'] not in fixed_ids and SK[d['sketch']]['plane']['axis'] == 'z' and zband(d)[0] > 20]
bal = next((d for d in st['drawn'] if d['name'].startswith('Balance bridge')), None) or next((d for d in new_top if inter(offset(outline(d), 6.0), [circle(Bc, 1.0)])), None)
for d in st['drawn']:
    if d['id'] in (mw['id'],): d['back'] = None

# ---------- 1. crescent rim plate: its old straddle pockets go (no bridge feet under it now), edges cleaned, r 65 ----------
rimL['cuts'] = [c for c in rimL.get('cuts', []) if not c['name'].startswith('Clears the')]
rim_paths = clean(snap_rim(outline(rimL), R_L2))
n, err, scraps, holes = set_outline(rimL, rim_paths)
rim_paths = outline(rimL)
log.append(f'crescent rim plate: edge to r {R_L2}, corners rounded; {n} dots (within {err[0]:.3f} mm); its old straddle pockets removed')

# ---------- 2. motion-works plate ----------
TABLE = {l['arbor']: (min(l['values']) - 1.0, max(l['values']) + 1.0) for l in mech.get('links', []) if l.get('kind') == 'table'}
RANGES = {'lever': (-1.5, 42.7), 'jumper': (0.0, 4.5), 'click': (2.0, 14.0)}
def centre_of(did):
    mt = mech['mounts'][did]; return np.array(mt['pivot'] if 'pivot' in mt else POS[mt['axis']], float)
def sweep(did):
    d = DR()[did]; poly = simplify(spline_poly(SK[d['sketch']]['points'], 8), 0.01); mt = mech['mounts'][did]; c = centre_of(did)
    if ('axis' in mt and mt['axis'] not in TABLE) or mt.get('angle') == 'hour':
        return [circle(c, float(np.hypot(*(poly - c).T).max()))]
    a0, a1 = TABLE[mt['axis']] if 'axis' in mt else RANGES[mt['angle']]
    return union([P(rot(poly, c, a)) for a in np.arange(a0, a1 + 1e-9, 0.5)])
mwp = outline(mw)
# over the barrel window the edge runs out to the rim again (Adam pulled it in only to ask for the window)
ab = math.degrees(math.atan2(B[1], B[0])); half = math.degrees(13.5 / 63.0)
mwp = union(mwp, [sector(50.0, R_L2, ab - 18.0, ab + 26.0)])           # the whole dip (about 66-110 deg); the joint to the rim plate is cut below
mwp = snap_rim(mwp, R_L2)
mwp = diff(mwp, offset(rim_paths, GAP))                                  # one even 0.5 mm joint along the crescent rim plate
for did, mt in mech['mounts'].items():                                    # parts reaching below the plate: its edge steps round them
    if 'axisX' in mt: continue
    z0, z1 = zband(DR()[did])
    if z1 > Z0 and z0 - 0.5 < Z0 + 0.01 and inter(mwp, sweep(did)):
        mwp = diff(mwp, offset(sweep(did), 1.25)); log.append(f'plate edge steps round the {DR()[did]["name"].split(" (")[0].lower()}')
mwp = clean(mwp)
old_sk = {c['sketch'] for c in mw.get('cuts', []) if c.get('kind') == 'pocket'}
n, err, scraps, holes = set_outline(mw, mwp)
foot = outline(mw)
mw['cuts'] = []; mw['thickness'] = T_MW; SK[mw['sketch']]['plane'] = {'axis': 'z', 'offset': Z0}
log.append(f'motion-works plate: edge to r {R_L2} (and out to the rim over the barrel window), 0.5 mm joint to the crescent rim plate, corners rounded; {n} dots (within {err[0]:.3f} mm)' +
           (f'; scraps dropped {[round(s, 1) for s in scraps]} mm²' if scraps else ''))

# seats on three ledges
seat_by_ledge = {l: [] for l in LEDGES}; names_by_ledge = {l: [] for l in LEDGES}
def ledge_for(bottom): return max(l for l in LEDGES if l <= bottom + 1e-6)
for did, mt in mech['mounts'].items():
    if 'axisX' in mt: continue
    d = DR()[did]; z0, z1 = zband(d)
    if z1 <= Z0 or z0 >= ZT or z0 - 0.5 < Z0 + 0.01: continue
    sw = sweep(did)
    if not inter(sw, foot): continue
    if 'Pawl pin' in d['name']: sw = offset(sw, 2.0)
    l = ledge_for(z0 - 0.5); seat_by_ledge[l] += offset(sw, 0.75); names_by_ledge[l].append(d['name'].split(' (')[0])
spr = mech['springs'][0]; Lc = centre_of(spr['to']['part']); wires = []
for a in np.arange(RANGES['lever'][0], RANGES['lever'][1] + 1e-9, 2.0):
    lug = rot([spr['to']['at']], Lc, a)[0]; a_, b_ = np.array(spr['from'], float), lug
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC; o.AddPath(P([a_, b_]), pc.JT_ROUND, pc.ET_OPENROUND); wires += o.Execute((spr['r'] + 0.75) * S)
if inter(union(wires), foot): l = ledge_for(spr['z'] - spr['r'] - 0.5); seat_by_ledge[l] += wires; names_by_ledge[l].append('Return spring')
for e in json.load(open(os.path.join(HERE, 'elements_crescent.json'))):
    if 'sweep' in e['name'] or e['z1'] <= Z0 or e['z0'] >= ZT: continue
    c = [circle((e['x'], e['y']), e['r'] + 0.75)]
    if not inter(c, foot): continue
    l = ledge_for(e['z0'] - 0.5); seat_by_ledge[l] += c; names_by_ledge[l].append(e['name'].split(' (')[0])
SEC_WIN = [circle(Fo, 18.7 + 0.75)]                                       # through the plate, down to the seconds wheel
regions = {}
lim = offset(foot, 1.5)
for l in LEDGES:
    r = inter(clean(union(seat_by_ledge[l]), 1.0, 0.6), lim) if seat_by_ledge[l] else []
    regions[l] = [p for p in r if pc.Orientation(p)]                      # a full-height island inside a seat comes down with it
# towers: plate left standing between seats on its own (not reaching the plate's edge), under 60 mm², comes down to the highest ledge beside it
top_left = diff(foot, union(*regions.values(), SEC_WIN))
edge_band = diff(foot, offset(foot, -1.5)); n_t = 0
for piece in top_left:
    if not pc.Orientation(piece): continue
    ar = abs(pc.Area(piece)) / (S * S)
    if ar >= 60 or inter([piece], edge_band) and ar >= 20: continue
    touch = [l for l in LEDGES if inter(offset([piece], 0.4), regions[l])]
    if not touch: continue
    l = max(touch); regions[l] = [p for p in union(regions[l], offset([piece], 0.3)) if pc.Orientation(p)]; n_t += 1
for l in sorted(LEDGES, reverse=True):
    for p in regions[l]: pocket(mw, f'Ledge at {l} mm (seats: {", ".join(sorted(set(names_by_ledge[l])))})', p, ZT - l)
pocket(mw, 'Window down to the seconds wheel (through)', SEC_WIN[0], None)
log.append('ledges: ' + '; '.join(f'{l}: {", ".join(sorted(set(names_by_ledge[l])))}' for l in LEDGES) + f'; {n_t} towers cut down; a window through the plate over the seconds wheel')

# ---------- 3. the top level: the crescent, the hand cock, the balance bridge ----------
def add_part(name, paths, z, t, mill):
    n = 1
    while f'D{n}' in DR(): n += 1
    kid = add_sketch(f'{name} outline', [])
    d = {'id': f'D{n}', 'name': name, 'sketch': kid, 'thickness': t, 'grow': 'plus', 'back': None, 'edges': None, 'cuts': [], 'mill': mill}
    SK[kid]['plane'] = {'axis': 'z', 'offset': z}; SK[kid]['name'] = f'{name} outline'
    st['drawn'].append(d); set_outline(d, paths); return d
whole = outline(top)
cuts_all = list(top.get('cuts', []))
if hand is None:                                                          # split the one piece in two along the minute track's circle
    track = [circle(Qh, RI - 0.6)]
    crescent_p = diff(whole, track)
    keep_side = [P([(Qh[0] - 3.5, -70), (70, -70), (70, 70), (Qh[0] - 3.5, 70)])]
    hand_p = union(inter(inter(whole, track), keep_side), [circle(Qh, 3.4)], [circle(Hs, 3.6)])
    big, holes, scraps = outer_and_holes(clean(hand_p))
    hand = add_part('Hand cock (from the right-side anchor to the minute hand arbor)', [big], ZT, 2.8, 'front')
    log.append('the crescent and hand bridge split along the minute track: no bridge spans the movement now')
else:
    crescent_p = whole
cp = clean(snap_rim(crescent_p, R_TOP))
n, err, scraps, holes = set_outline(top, cp); top['name'] = 'Crescent (the minute track)'; top['mill'] = 'back'
crescent_paths = outline(top)
log.append(f'crescent: band outside the minute track only, edge to r {R_TOP}, corners rounded; {n} dots')
hp = clean(snap_rim(diff(outline(hand), offset(crescent_paths, GAP)), R_TOP))
n, err, scraps, holes = set_outline(hand, hp)
hand_paths = outline(hand)
log.append(f'hand cock: right-side anchor to the minute hand arbor, edge to r {R_TOP}; {n} dots')
# the balance bridge: on the plate, a boss over the balance staff joined to Adam's bar, clear of the crescent
if bal is not None:
    bp = outline(bal)
    bF = F(bp[0]); near = bF[int(np.argmin(np.hypot(*(bF - Bc).T)))]
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC; o.AddPath(P([near, Bc]), pc.JT_ROUND, pc.ET_OPENROUND); arm = o.Execute(3.0 * S)
    bp = clean(union(bp, arm, [circle(Bc, 4.2)]), 1.6, 1.0)
    bp = diff(bp, offset(union(crescent_paths, hand_paths), GAP))
    n, err, scraps, holes = set_outline(bal, bp)
    SK[bal['sketch']]['plane'] = {'axis': 'z', 'offset': ZT}; bal['thickness'] = 2.8; bal['mill'] = 'front'
    bal['name'] = 'Balance bridge (across the balance well; the balance\'s upper bearing)'
    log.append(f'balance bridge: on the plate at z {ZT:.3f}, 2.8 thick, a boss over the balance staff; {n} dots')
# the cuts go to whichever part they sit in now
for c in cuts_all:
    at = c.get('at')
    if at is None: continue
    pt = P([at])[0]
    if bal is not None and math.dist(at, Bc) < 1e-3: owner = bal; c = dict(c, **{'from': 'front'}) if c['kind'] == 'bearing' else c
    elif pc.PointInPolygon(pt, hand_paths[0]): owner = hand
    elif pc.PointInPolygon(pt, crescent_paths[0]): owner = top
    else: log.append(f'cut dropped (lands on no part now): {c["name"]}'); continue
    if owner is not top:
        c = dict(c); c['id'] = next_cut(owner)
        if owner is hand and c['kind'] == 'bearing': c['from'] = 'front'          # milled from below like the old hand cock
        if c['kind'] == 'clear' and owner is bal: continue                         # nothing goes above the balance staff now
        owner.setdefault('cuts', []).append(c)
top['cuts'] = [c for c in cuts_all if c.get('at') is None or (pc.PointInPolygon(P([c['at']])[0], crescent_paths[0]) and math.dist(c['at'], Bc) > 1e-3)]
top['mill'] = 'back'; hand['mill'] = 'front'
def solid(q, margin=0.0):
    """full-height motion-works plate under q (not a seat, not the seconds window), margin mm in from its edge"""
    pt = P([q])[0]
    inside = foot if margin <= 0 else offset(foot, -margin)
    return (any(pc.PointInPolygon(pt, f) == 1 for f in inside if pc.Orientation(f))
            and not any(pc.PointInPolygon(pt, r) for r in offset(union(*regions.values()), margin))
            and math.dist(q, Fo) > 19.45 + margin)
def two_screws(d, paths, label, RB=3.2, across=None):
    """a screw at each end (either side of `across` along the part's length), each in a round boss (r RB) over full-height
    plate; a boss may stand up to 2 mm past the part's edge (it is joined on). Pilots go in the motion-works plate."""
    keep_off = offset(union(crescent_paths, hand_paths), RB + GAP)
    fo_ = [o for o in offset(foot, -RB) if pc.Orientation(o)]; ro_ = offset(union(*regions.values()), RB)
    def ok(q):
        pt = P([q])[0]
        return (any(pc.PointInPolygon(pt, o) == 1 for o in fo_) and not any(pc.PointInPolygon(pt, r) for r in ro_)
                and math.dist(q, Fo) > 19.45 + RB and not any(pc.PointInPolygon(pt, k) for k in keep_off))
    cand = []
    for p_ in offset(paths, -1.0) + offset(paths, 2.0):
        if not pc.Orientation(p_): continue
        Q_ = F(p_); cum = np.r_[0, np.cumsum(np.hypot(*np.diff(Q_, axis=0).T))]; Q_ = Q_[np.r_[True, np.diff(cum // 0.5) > 0]]
        cand += [q for q in Q_ if ok(q)]
    Pn = F(paths[0]); c0 = Pn.mean(0); w, v = np.linalg.eigh(np.cov((Pn - c0).T)); ax_ = v[:, -1]
    mid = float(np.dot((across if across is not None else c0) - c0, ax_))
    lo = [q for q in cand if np.dot(q - c0, ax_) < mid - 5]; hi = [q for q in cand if np.dot(q - c0, ax_) > mid + 5]
    if not lo or not hi: return []
    qa = min(lo, key=lambda q: np.dot(q - c0, ax_)); qb = max(hi, key=lambda q: np.dot(q - c0, ax_))
    np_ = clean(union(paths, [circle(qa, RB)], [circle(qb, RB)]), 1.6, 1.0)
    set_outline(d, diff(np_, offset(union(crescent_paths, hand_paths), GAP)))
    for i, q in enumerate((qa, qb)):
        cut(d, 'screw', f'Screw · {label} {i + 1} (M2 countersunk)', 2.2, q, None, 'back', {'d': 4.2})
        cut(mw, 'pilot', f'Screw pilot · {label} {i + 1} (M2)', 1.6, q, 4.0, 'back')
    return [qa, qb]
if bal is not None and not any(c['kind'] == 'screw' for c in bal.get('cuts', [])):
    sc_ = two_screws(bal, outline(bal), 'balance bridge', across=Bc); log.append(f'balance bridge screws at {[tuple(np.round(q, 1)) for q in sc_]}')
hs = [c['at'] for c in hand.get('cuts', []) if c['kind'] == 'screw']
if len(hs) == 1:
    inner = offset(hand_paths, -2.8); cand = [q for p_ in inner if pc.Orientation(p_) for q in F(p_)[::4]]
    cand = [q for q in cand if solid(q, 2.2) and math.dist(q, Qh) > 5 and math.dist(q, Hs) > 5]
    if cand:
        q = max(cand, key=lambda q: math.dist(q, hs[0]))
        cut(hand, 'screw', 'Screw · hand cock 2, into the motion-works plate (M2 countersunk)', 2.2, q, None, 'back', {'d': 4.2})
        log.append(f'hand cock: a second screw at {tuple(np.round(q, 1))} (one screw alone lets it swing)'); hs.append(list(q))
    else: log.append('hand cock: NO solid plate found for a second screw')
if not any(c['kind'] == 'pilot' and 'hand cock' in c['name'] for c in mw['cuts']):
    for i, q in enumerate(hs): cut(mw, 'pilot', f'Screw pilot · hand cock {i + 1} (M2)', 1.6, q, 4.0, 'back')

# ---------- 4. the seconds bridge: a clean pill, sunk into the plate onto its 15.5 floor ----------
if sec is not None:
    sp = F(outline(sec)[0])
    far = max(((i, j) for i in range(len(sp)) for j in range(i + 1, len(sp))), key=lambda ij: np.hypot(*(sp[ij[0]] - sp[ij[1]])))
    u = sp[far[1]] - sp[far[0]]; u = u / np.hypot(*u)
    RP = 3.2                                                               # the pill: centred on the seconds arbor, 6.4 wide
    for L2 in np.arange(18.7 + 0.75 + 3.0, 34.0, 0.25):                   # each screw at least 3 mm clear of the seconds window's edge, on plate floor
        e0, e1 = Fo - u * L2, Fo + u * L2
        if all(any(pc.PointInPolygon(P([q])[0], f) == 1 for f in offset(foot, -(RP + 0.3 + 0.8)) if pc.Orientation(f)) for q in (e0, e1)): break
    else: raise SystemExit('no room for the seconds pill')
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC; o.AddPath(P([e0, e1]), pc.JT_ROUND, pc.ET_OPENROUND); pill = o.Execute(RP * S)
    set_outline(sec, pill, 0.05)
    Z_SEC = LEDGES[0]                                                      # on the plate's bottom layer (15.5): screws bite the 2.8 floor and the main plate
    SK[sec['sketch']]['plane'] = {'axis': 'z', 'offset': Z_SEC}; sec['thickness'] = 2.8; sec['mill'] = 'front'
    sec['cuts'] = []
    cut(sec, 'bearing', 'Bearing · seconds (upper, 1×3×1)', 3.0, Fo, 1.0, 'front', axis='fourth')
    seat = offset(pill, 0.3)
    near_out = diff(offset(seat, 1.6), foot)                               # where the seat comes within 1.6 of the plate's edge, no sliver wall:
    if near_out: seat = [max(close(union(seat, near_out), 0.8), key=lambda p_: abs(pc.Area(p_)))]   # the seat opens out to the edge
    pocket(mw, 'Seat for the seconds bridge (sunk onto the 15.5 floor)', seat[0], ZT - Z_SEC)
    mw['cuts'] = [c for c in mw['cuts'] if 'seconds bridge' not in c['name'] or c['kind'] != 'pilot']
    main['cuts'] = [c for c in main['cuts'] if 'seconds bridge' not in c['name']]
    for i, q in enumerate((e0, e1)):
        cut(sec, 'screw', f'Screw · seconds bridge {i + 1} (M2 countersunk)', 2.2, q, None, 'back', {'d': 4.2})
        cut(mw, 'pilot', f'Screw pilot · seconds bridge {i + 1} (M2, through the floor)', 1.6, q, None, 'back')
        solid_main = all(math.dist(q, (e['x'], e['y'])) > e['r'] + 0.75 + 0.8 + 1.5 for e in json.load(open(os.path.join(HERE, 'elements_crescent.json'))) if e['z0'] < Z0)
        if solid_main: cut(main, 'pilot', f'Screw pilot · seconds bridge {i + 1} (M2)', 1.6, q, 4.0, 'back')
    log.append(f'seconds bridge: a pill {2 * L2 + 2 * RP:.1f} x {2 * RP:.1f} centred on the seconds arbor, sunk {ZT - Z_SEC:.2f} into the plate (bottom at {Z_SEC}, '
               f'{(ZT - Z_SEC) / (ZT - 6.6) * 100:.0f} % of the way down to the wheel); screws into the floor' + (' and the main plate' if solid_main else ''))

# ---------- 5. no seconds hand ----------
pr['hands'] = [h for h in pr['hands'] if h['id'] != 'seconds_hand']
st.get('hands', {}).pop('seconds_hand', None); pr['defaults'].get('hands', {}).pop('seconds_hand', None)
pr['defaults'].get('locks', {}).pop('seconds_hand', None)
log.append('seconds hand removed (the wheel whirs in its window)')

# ---------- 6. side windows with rounded inside corners ----------
def rounded_rect(pts, r=2.0):
    return offset(offset([P(pts)], -r), r)[0]
for c in main['cuts']:
    if c['kind'] == 'pocket' and c['name'].startswith('Side window'):
        k = SK[c['sketch']]; pts = [(q['u'], q['v']) for q in k['points']]
        k['points'] = dots_sharp(simplify(F(rounded_rect(pts)), 0.005))
log.append('side windows: inside corners rounded r 2')

# ---------- 7. tidy sketches ----------
used = {d['sketch'] for d in st['drawn']} | {c['sketch'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
before = len(st['sketches']); st['sketches'] = [k for k in st['sketches'] if k['id'] in used]
log.append(f'{before - len(st["sketches"])} unused outlines removed; loose sketches left: 0')
for d in (sec, hand, bal):
    if d is not None: pr['decor']['colors'][d['id']] = '#d9dcdf'
J['savedAt'] = '2026-11-18T05:00:00.000Z'
json.dump(J, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('\n'.join(log)); print('written', OUT, '|', len(st['drawn']), 'parts,', len(st['sketches']), 'sketches')
