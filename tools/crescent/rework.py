# Crescent rework, 2026-11-17: Adam's hand edits engineered in place.
#   - the raised barrel bridge, right bridge and right rim plate become one motion-works plate (3/8", top at the rim plates'),
#     milled from the top: every part it holds bores its own seat from its swept shape (0.75 mm round, 0.5 mm under), and the
#     wheels under it are bored down to a 2.8 mm floor (the old bridges' layer) that will carry their bearings
#   - the hand cock and the crescent become one top bridge (milled from the top)
#   - the balance side window 3x wider, a new one as wide at the barrel; the main plate's edge back to a full circle
#   - accidents put back: two stray dots on the hour star, the crescent rim plate's shape (front and back)
# No new through holes: bearings, screws and the windows in the floor come in a later step.
#
#   python3 rework.py ADAM.json REF_1831.json ELEMENTS.json OUT.json
import json, math, sys, os
import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MP
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import refit as RF

SRC, REF, ELEM, OUT = sys.argv[1:5]
J = json.load(open(SRC)); R = json.load(open(REF)); ELS = json.load(open(ELEM))
st = J['state']; pr = J['project']; mech = pr['mechanisms']
SK = {k['id']: k for k in st['sketches']}
DR = {d['id']: d for d in st['drawn']}
RSK = {k['id']: k for k in R['state']['sketches']}; RDR = {d['id']: d for d in R['state']['drawn']}
def byname(prefix): return next(d for d in st['drawn'] if d['name'].startswith(prefix))

Z_PLATE_TOP = 12.7; T_MW = 9.525; Z_MW_TOP = Z_PLATE_TOP + T_MW      # 22.225: the rim plates' top, under the crescent
FLOOR_TOP = Z_PLATE_TOP + 2.8                                      # 15.5: the bores over the wheels stop here (the old bridges' layer)
CLEAR, UNDER = 0.75, 0.5                                           # seats: 0.75 mm round each part's sweep, 0.5 mm under it
H = 0.05
xs = np.arange(-70.0, 70.0 + H / 2, H); GX, GY = np.meshgrid(xs, xs)
def ij(x, y): return int(round((y + 70) / H)), int(round((x + 70) / H))

# ---------- geometry helpers (rasters at 0.05 mm) ----------
def poly_of(dots, N=32):
    return RF.spline([(q['u'], q['v'], bool(q.get('smooth'))) for q in dots], N=N)
def raster(poly):
    poly = np.asarray(poly); a, b = poly.min(0), poly.max(0)
    i0, j0 = max(0, int((a[1] + 70) / H) - 2), max(0, int((a[0] + 70) / H) - 2)
    i1, j1 = min(len(xs), int((b[1] + 70) / H) + 3), min(len(xs), int((b[0] + 70) / H) + 3)
    m = np.zeros(GX.shape, bool)
    if i1 > i0 and j1 > j0:
        m[i0:i1, j0:j1] = MP(poly).contains_points(np.c_[GX[i0:i1, j0:j1].ravel(), GY[i0:i1, j0:j1].ravel()]).reshape(i1 - i0, j1 - j0)
    return m
def disc(c, r): return np.hypot(GX - c[0], GY - c[1]) <= r
def dilate(m, r): return ndimage.distance_transform_edt(~m) * H <= r
def erode(m, r): return ndimage.distance_transform_edt(m) * H > r
def close(m, r): return erode(dilate(m, r), r)
def opening(m, r): return dilate(erode(m, r), r)
def loops(m, min_area=0.3, sigma=3.0):   # the mask's edge as smooth loops (contoured on a smoothed distance field, not the pixel steps)
    sdf = (ndimage.distance_transform_edt(~m) - ndimage.distance_transform_edt(m)) * H
    sdf = ndimage.gaussian_filter(sdf, sigma)
    cs = plt.contour(GX, GY, sdf, levels=[0.0]); segs = cs.allsegs[0]; plt.close('all'); out = []
    for sg in segs:
        sg = np.asarray(sg)
        if len(sg) < 6: continue
        ar = 0.5 * (np.dot(sg[:, 0], np.roll(sg[:, 1], 1)) - np.dot(sg[:, 1], np.roll(sg[:, 0], 1)))
        if abs(ar) >= min_area: out.append((sg, abs(ar)))
    return out
def rdp(P, eps):                       # Douglas-Peucker on a closed loop (for pocket outlines: sharp dots, exact to eps)
    P = np.asarray(P)
    def rec(a, b):
        if b <= a + 1: return [a]
        seg = P[b] - P[a]; L = np.hypot(*seg) or 1e-12
        d = np.abs(np.cross(seg, P[a + 1:b] - P[a])) / L
        k = int(np.argmax(d))
        if d[k] > eps: return rec(a, a + 1 + k) + rec(a + 1 + k, b)
        return [a]
    n = len(P); far = int(np.argmax(np.hypot(*(P - P[0]).T)))
    idx = rec(0, far) + rec(far, n - 1) + [n - 1]
    return P[sorted(set(idx))]
def ccw(P):
    P = np.asarray(P, float); a = 0.5 * (np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
    return P if a >= 0 else P[::-1]
def dots_sharp(P): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in ccw(P)]   # every pocket outline anticlockwise
def dots_smooth(P): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': True} for x, y in P]
def rot(P, c, a_deg):
    a = math.radians(a_deg); ca, sa = math.cos(a), math.sin(a); P = np.asarray(P) - c
    return np.c_[P[:, 0] * ca - P[:, 1] * sa, P[:, 0] * sa + P[:, 1] * ca] + c
def zband(d):
    k = SK[d['sketch']]; z = k['plane']['offset']; return (z, z + d['thickness'])
def new_sketch_id():
    n = 1
    while f'K{n}' in SK: n += 1
    return f'K{n}'
def add_sketch(name, dots, z=0.0):
    kid = new_sketch_id(); k = {'id': kid, 'name': name, 'plane': {'axis': 'z', 'offset': z}, 'closed': True, 'points': dots}
    st['sketches'].append(k); SK[kid] = k; return kid
def next_cut_id(d):
    n = 1; used = {c['id'] for c in d.get('cuts', [])}
    while f'h{n}' in used: n += 1
    return f'h{n}'
def pocket_cut(d, name, poly, depth, frm='back'):
    kid = add_sketch(f'{name} (pocket outline)', dots_sharp(rdp(np.vstack([poly, poly[:1]]), 0.03)[:-1]))
    d.setdefault('cuts', []).append({'id': next_cut_id(d), 'kind': 'pocket', 'name': name, 'from': frm, 'depth': round(depth, 3), 'sketch': kid, 'seat': None, 'csk': None})

log = []
# ---------- 1. accidents back the way they were ----------
star = byname('Hour star'); sk = SK[star['sketch']]
ref_star = {(round(p['u'], 3), round(p['v'], 3)) for p in RSK[RDR[star['id']]['sketch']]['points']}
before = len(sk['points']); sk['points'] = [p for p in sk['points'] if (round(p['u'], 3), round(p['v'], 3)) in ref_star]
log.append(f'hour star: {before} dots -> {len(sk["points"])} (the two stray ones removed)')
rimL = byname('Crescent rim plate'); SK[rimL['sketch']]['points'] = RSK[RDR[rimL['id']]['sketch']]['points']; rimL['back'] = None; rimL['edges'] = None
log.append('crescent rim plate: shape back to 18:31, back face matching the front')
main = byname('Main plate'); SK[main['sketch']]['points'] = RSK[RDR[main['id']]['sketch']]['points']
log.append('main plate: edge back to a full circle (the barrel window is cut instead)')

# ---------- 2. the motion-works plate: the three outlines as one, clean edges ----------
barrel, right, rimR = byname('Barrel bridge'), byname('Right bridge'), byname('Right rim plate')
u = raster(poly_of(SK[barrel['sketch']]['points'])) | raster(poly_of(SK[right['sketch']]['points'])) | raster(poly_of(SK[rimR['sketch']]['points']))
u &= disc((0, 0), 66.0)                                                 # never past the main plate's edge
for other in (rimL, byname('Bottom bridge')):                            # clear of the plates beside it at its level (1.2: the dot fit may move an edge 0.35 at a tip)
    u &= ~dilate(raster(poly_of(SK[other['sketch']]['points'])), 1.2)
u = close(u, 1.6)                                                       # inside corners rounded for a 1/8" end mill, seams filled
u = opening(u, 1.0)                                                     # slivers under 2 mm wide trimmed off
lab, n = ndimage.label(u); sizes = ndimage.sum(u, lab, range(1, n + 1)) * H * H
keep = int(np.argmax(sizes)) + 1
if n > 1: log.append(f'motion-works plate: {n - 1} separate scrap(s) dropped ({", ".join(f"{s:.1f}" for i, s in enumerate(sizes) if i + 1 != keep)} mm²)')
u = lab == keep
holes = ndimage.binary_fill_holes(u) & ~u
u = ndimage.binary_fill_holes(u)
if holes.any(): log.append(f'motion-works plate: {holes.sum() * H * H:.1f} mm² of enclosed gaps filled (no through openings yet)')
MW_MASK = u
outer = max(loops(u), key=lambda t: t[1])[0]
np.save(os.path.join(os.path.dirname(OUT), 'mw_outer.npy'), outer)
mw_pts, err, L = RF.fit(dots_smooth(outer[::4]), 0.1)
mw = right                                                              # the right bridge's id carries on as the plate
SK[mw['sketch']]['points'] = mw_pts; SK[mw['sketch']]['plane'] = {'axis': 'z', 'offset': Z_PLATE_TOP}
mw.update({'name': 'Motion-works plate (3/8"; the barrel bridge, right bridge and right rim plate as one)', 'thickness': T_MW, 'grow': 'plus', 'back': None, 'edges': None, 'mill': 'back', 'cuts': []})
log.append(f'motion-works plate: {len(mw_pts)} dots (edge holds to {err[0]:.3f} mm of the cleaned outline), z {Z_PLATE_TOP}-{Z_MW_TOP}')

# ---------- 3. seats: every part inside the plate bores its space from the top ----------
mounts = mech['mounts']; POS = st['pos']
RANGES = {'lever': (-1.5, 42.7), 'jumper': (0.0, 4.5), 'click': (2.0, 14.0)}    # the sim's 12-hour sweep: 0-41.2, 1.7-2.6, 3.8-12.0
def centre_of(did):
    mt = mounts[did]; return np.array(mt['pivot'] if 'pivot' in mt else POS[mt['axis']], float)
TABLE = {l['arbor']: (min(l['values']) - 1.0, max(l['values']) + 1.0) for l in mech.get('links', []) if l.get('kind') == 'table'}   # the fork and the balance only swing
def sweep(did):
    d = DR[did]; P = poly_of(SK[d['sketch']]['points'], N=8); mt = mounts[did]; c = centre_of(did)
    if ('axis' in mt and mt['axis'] not in TABLE) or mt.get('angle') == 'hour':   # turns all the way round
        return disc(c, float(np.hypot(*(P - c).T).max()))
    a0, a1 = TABLE[mt['axis']] if 'axis' in mt else RANGES[mt['angle']]; m = np.zeros(GX.shape, bool)
    for a in np.arange(a0, a1 + 1e-9, 0.5): m |= raster(rot(P, c, a))
    return m
seats = []      # (name, mask, bottom z)
foot = MW_MASK
for did, mt in mounts.items():
    if 'axisX' in mt: continue
    d = DR[did]; z0, z1 = zband(d)
    if z1 <= Z_PLATE_TOP or z0 >= Z_MW_TOP: continue
    m = sweep(did)
    if not (m & foot).any(): continue
    bottom = max(FLOOR_TOP, z0 - UNDER)
    if 'Pawl pin' in d['name']: m = dilate(m, 2.0)                       # the pawl blade flexes ~1.8 mm riding back over a tooth
    seats.append((d['name'].split(' (')[0], m, bottom))
# the return spring: a wire from its stud to the lever's lug, over the lever's swing
spr = mech['springs'][0]; L_ = centre_of(spr['to']['part']); m = np.zeros(GX.shape, bool)
for a in np.arange(RANGES['lever'][0], RANGES['lever'][1] + 1e-9, 1.0):
    lug = rot([spr['to']['at']], L_, a)[0]; a_, b_ = np.array(spr['from']), lug
    for t in np.linspace(0, 1, 60): m |= disc(a_ + (b_ - a_) * t, spr['r'])
if (m & foot).any(): seats.append(('Return spring', m, max(FLOOR_TOP, spr['z'] - spr['r'] - UNDER)))
# wheels, pinions and hubs: in the plate's levels at their own depth; under the plate, bored down to the floor
for e in ELS:
    if 'sweep' in e['name']: continue
    m = disc((e['x'], e['y']), e['r'])
    if not (m & foot).any(): continue
    bottom = FLOOR_TOP if e['z1'] <= Z_PLATE_TOP else max(FLOOR_TOP, e['z0'] - UNDER)
    seats.append((e['name'].split(' (')[0], m, bottom))
top = np.where(foot, Z_MW_TOP, np.nan)
for name, m, bottom in seats:
    r = close(dilate(m, CLEAR), 1.0) & dilate(foot, 1.5)                 # 0.75 mm round it; inside corners at least r 1 (a 2 mm end mill)
    top = np.where(r & foot, np.minimum(top, bottom), top)
    for poly, ar in loops(r, 1.0):
        pocket_cut(mw, f'Seat · {name}', poly, Z_MW_TOP - bottom)
log.append(f'motion-works plate: {len(seats)} seats bored from the top: ' + ', '.join(sorted({s[0] for s in seats})))

# ---------- 4. towers: plate left standing between seats (on its own under 150 mm², or a stub on the edge under 60 mm²) comes down ----------
edge_band = foot & ~erode(foot, 1.5)
n_t = 0
for lev in sorted(set(np.round(top[foot], 3)), reverse=True)[:-1]:
    mask = (top >= lev - 1e-6) & foot
    lab, n = ndimage.label(mask)
    if not n: continue
    sizes_ = ndimage.sum(mask, lab, range(1, n + 1)) * H * H
    ok = np.zeros(n + 1, bool); ok[np.unique(lab[edge_band & mask])] = True; ok[0] = True   # joined to the plate's edge: a wall, it stays...
    ok[1:] &= sizes_ >= 60.0                                              # ...unless it is only a stub (a real wall runs long)
    ok[1:] |= sizes_ > 150.0                                              # a big standalone block is structure, not a tower
    for j in range(1, n + 1):
        if ok[j]: continue
        sel = lab == j
        ring = dilate(sel, 0.6) & ~sel & foot & (top < lev - 1e-6)
        f = float(np.nanmax(top[ring])) if ring.any() else FLOOR_TOP
        top[sel] = f; n_t += 1
        for poly, ar in loops(dilate(sel, 0.3), 0.3):
            pocket_cut(mw, 'Tower removed (plate standing alone between seats)', poly, Z_MW_TOP - f)
log.append(f'motion-works plate: {n_t} towers cut down')

# ---------- 5. the top bridge: the crescent and the hand cock as one ----------
cres, hc = byname('Crescent'), byname('Hand cock')
u = raster(poly_of(SK[cres['sketch']]['points'])) | raster(poly_of(SK[hc['sketch']]['points']))
u = opening(close(u, 1.6), 1.0)
lab, n = ndimage.label(u); sizes = ndimage.sum(u, lab, range(1, n + 1)); u = lab == (int(np.argmax(sizes)) + 1); u = ndimage.binary_fill_holes(u)
outer = max(loops(u), key=lambda t: t[1])[0]
np.save(os.path.join(os.path.dirname(OUT), 'tb_outer.npy'), outer)
tb_pts, err, L = RF.fit(dots_smooth(outer[::4]), 0.1)
SK[cres['sketch']]['points'] = tb_pts
hc_cuts = []
for c in hc.get('cuts', []):
    c = dict(c)
    if c['kind'] == 'bearing': c['from'] = 'back'                         # milled from the top like the crescent: bearings from the top
    c['id'] = None; hc_cuts.append(c)
for c in hc_cuts: c['id'] = next_cut_id(cres); cres.setdefault('cuts', []).append(c)
cres['name'] = 'Crescent and hand bridge (one piece across the movement)'; cres['mill'] = 'back'
st['drawn'] = [d for d in st['drawn'] if d['id'] not in (barrel['id'], rimR['id'], hc['id'])]
dead_sketches = {barrel['sketch'], rimR['sketch'], hc['sketch']} | {c['sketch'] for d in (barrel, rimR, hc) for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
log.append(f'top bridge: crescent and hand cock as one ({len(tb_pts)} dots, edge within {err[0]:.3f} mm of the cleaned union); the hand cock\'s bearings now from the top')

# ---------- 6. side windows ----------
Bc = np.array(POS['balance']); B = np.array(POS['barrel'])
for c in main['cuts']:
    if c['kind'] == 'pocket' and c['name'].startswith('Side window onto the balance'):
        k = SK[c['sketch']]; W = 12.0
        k['points'] = dots_sharp([(-67.0, Bc[1] - W), (Bc[0] - 12.0, Bc[1] - W), (Bc[0] - 12.0, Bc[1] + W), (-67.0, Bc[1] + W)])
        c['name'] = 'Side window onto the balance (24 wide; closed above by the crescent rim plate)'
        bal_win = np.array([(-67.0, Bc[1] - W), (Bc[0] - 12.0, Bc[1] + W)])
a = math.atan2(B[1], B[0]); u_ = np.array([math.cos(a), math.sin(a)]); v_ = np.array([-u_[1], u_[0]])
r0, r1, W = math.hypot(*B) + 14.0, 67.5, 12.0
win = [tuple(u_ * r0 + v_ * W), tuple(u_ * r1 + v_ * W), tuple(u_ * r1 - v_ * W), tuple(u_ * r0 - v_ * W)]
barrel_floor = 7.2 - UNDER
kid = add_sketch('Side window onto the barrel (pocket outline)', dots_sharp(win))
main['cuts'].append({'id': next_cut_id(main), 'kind': 'pocket', 'name': 'Side window onto the barrel (24 wide; closed above by the motion-works plate)', 'from': 'back',
                     'depth': round(Z_PLATE_TOP - barrel_floor, 3), 'sketch': kid, 'seat': None, 'csk': None})
log.append(f'side windows: balance 8 -> 24 mm wide; barrel 24 mm wide, down to the barrel recess floor (z {barrel_floor})')
# a crescent rim plate screw that now falls in the wider balance window moves along the rim
def in_win(p, m=2.6): return bal_win[0][0] - m <= p[0] <= bal_win[1][0] + m and bal_win[0][1] - m <= p[1] <= bal_win[1][1] + m
for c in main['cuts']:
    if c['kind'] == 'pilot' and 'crescent rim plate' in c['name'] and in_win(c['at']):
        old = tuple(c['at']); taken = [tuple(x['at']) for d in (main, rimL) for x in d.get('cuts', []) if x['kind'] in ('pilot', 'screw') and x.get('at') and tuple(x['at']) != old]
        rim_m = raster(poly_of(SK[rimL['sketch']]['points'])); cres_m = raster(poly_of(SK[cres['sketch']]['points']))
        rim_in = ndimage.distance_transform_edt(rim_m) * H; cres_in = ndimage.distance_transform_edt(cres_m) * H
        recess = [(np.array([e['x'], e['y']]), e['r'] + 2.5) for e in ELS if e['z0'] < Z_PLATE_TOP and 'sweep' not in e['name']]
        best = None
        for ang in np.arange(150, 235, 0.5):
            for rr in np.arange(48, 63, 0.25):
                p = (rr * math.cos(math.radians(ang)), rr * math.sin(math.radians(ang))); i, j = ij(*p)
                if in_win(p) or rim_in[i, j] < 2.6 or cres_in[i, j] < 2.6: continue
                if any(math.dist(p, q) < 6.0 for q in taken): continue
                if any(math.dist(p, cc) < rad + 2.6 for cc, rad in recess): continue
                sc = abs(math.atan2(p[1], p[0]) - math.atan2(old[1], old[0]))
                if best is None or sc < best[0]: best = (sc, p)
        if best is None: log.append(f'crescent rim plate screw at {old} sits in the wider window and found no new spot: removed'); main['cuts'].remove(c)
        else:
            c['at'] = [round(best[1][0], 4), round(best[1][1], 4)]
            for x in rimL['cuts']:
                if x['kind'] == 'screw' and tuple(x['at']) == old: x['at'] = list(c['at'])
            log.append(f'crescent rim plate screw moved out of the wider window: {old} -> {tuple(c["at"])}')
        break

# ---------- 7. tidy: drop the sketches of the parts that merged away ----------
used = {d['sketch'] for d in st['drawn']} | {c['sketch'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
st['sketches'] = [k for k in st['sketches'] if k['id'] in used or k['id'] not in dead_sketches]
pr['decor']['colors'][mw['id']] = '#6e6a64'                              # a plate, coloured like the main and rim plates
J['savedAt'] = '2026-11-18T00:00:00.000Z'
json.dump(J, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('\n'.join(log)); print('written', OUT, '|', len(st['drawn']), 'parts,', len(st['sketches']), 'sketches')
