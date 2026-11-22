# Crescent tidy pass, 2026-11-17 (night): Adam's latest plates, cleaned and lined up (exact geometry, pyclipper).
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
#   python3 tidy.py ADAM.json OUT.json
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

main, rimL, mw, top = byname('Main plate'), byname('Crescent rim plate'), byname('Motion-works plate'), byname('Crescent and hand bridge')
sec = next(d for d in st['drawn'] if d['id'] not in (main['id'], rimL['id'], mw['id'], top['id']) and not d.get('cuts') and zband(d)[0] > 20 and d['id'] not in mech['mounts'])
POS = st['pos']; Fo = np.array(POS['fourth'], float); Bc = np.array(POS['balance'], float); B = np.array(POS['barrel'], float)

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

# ---------- 3. the top bridge: edge to r 64, corners rounded ----------
tp = clean(snap_rim(outline(top), R_TOP))
n, err, scraps, holes = set_outline(top, tp)
top_paths = outline(top)
log.append(f'crescent and hand bridge: edge to r {R_TOP}, corners rounded; {n} dots (within {err[0]:.3f} mm)')

# ---------- 4. the seconds bridge ----------
sp = outline(sec); spF = F(sp[0])
far = max(((i, j) for i in range(0, len(spF), 4) for j in range(i + 1, len(spF), 4)), key=lambda ij: np.hypot(*(spF[ij[0]] - spF[ij[1]])))
ends = [spF[far[0]], spF[far[1]]]; screws = []
add = [circle(Fo, 3.6)]
for e in ends:
    v = e - Fo; r = float(np.hypot(*v)); u = v / r
    s = Fo + u * max(r, 18.7 + 0.75 + 3.0)                               # on solid plate: 3 mm clear of the window's edge
    screws.append(s)
    o = pc.PyclipperOffset(); o.ArcTolerance = ARC; o.AddPath(P([Fo + u * (r - 3.0), s]), pc.JT_ROUND, pc.ET_OPENROUND); add += o.Execute(2.6 * S)
    add.append(circle(s, 3.0))
secp = clean(union(sp, *[[a] for a in add]), 1.0, 0.8)
secp = diff(secp, offset(top_paths, GAP))
n, err, scraps, holes = set_outline(sec, secp)
SK[sec['sketch']]['plane'] = {'axis': 'z', 'offset': ZT}; sec['thickness'] = 2.8; sec['mill'] = 'front'
sec['name'] = 'Seconds bridge (two screws; the seconds wheel\'s upper bearing)'
cut(sec, 'bearing', 'Bearing · seconds (upper, 1×3×1)', 3.0, Fo, 1.0, 'front', axis='fourth')
for i, s in enumerate(screws):
    cut(sec, 'screw', f'Screw · seconds bridge {i + 1} (M2 countersunk)', 2.2, s, None, 'back', {'d': 4.2})
    cut(mw, 'pilot', f'Screw pilot · seconds bridge {i + 1} (M2)', 1.6, s, 4.0, 'back')
in_seat = [i + 1 for i, s in enumerate(screws) if any(pc.PointInPolygon(P([s])[0], p) for l in LEDGES for p in regions[l]) or pc.PointInPolygon(P([s])[0], SEC_WIN[0])]
log.append(f'seconds bridge: on the plate at z {ZT:.3f}, 2.8 thick, {n} dots; screw bosses at {[tuple(np.round(s, 1)) for s in screws]}' + (f' (screw {in_seat} lands in a seat: check)' if in_seat else ', both on solid plate'))

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
pr['decor']['colors'][sec['id']] = '#d9dcdf'
J['savedAt'] = '2026-11-18T05:00:00.000Z'
json.dump(J, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('\n'.join(log)); print('written', OUT, '|', len(st['drawn']), 'parts,', len(st['sketches']), 'sketches')
