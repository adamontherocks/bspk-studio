# Crescent, 2026-11-17 (late): the motion-works plate becomes one big secondary plate with staircase seats (Adam's idea).
#   - the bottom bridge is folded in: the plate covers its area and will carry its bearings
#   - every part in the plate's levels sits in a seat milled to its outline over its whole motion (+0.75 mm), floored at
#     that part's own base (0.5 mm under it), so the plate steps down part by part and each part has plate up to its base;
#     the wheels under the plate stay covered (the cams, ratchets and star are the show)
#   - the seconds hand gets a big window down to it
#   - the plate's back face matches its front again (an accidental drag)
# No through holes: bearings, screws and any windows through the plate come in a later step.
#
#   python3 staircase.py ADAM.json OUT.json
import json, math, sys, os
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from platekit import *

SRC, OUT = sys.argv[1:3]
J = json.load(open(SRC)); sc = Scene(J); st = sc.st; mech = sc.mech
Z0, T = 12.7, 9.525; ZT = Z0 + T                 # on the main plate, its top level with the rim plates', under the top bridge
FLOOR = Z0 + 2.8                                 # the bottom layer (12.7-15.5) runs under everything and holds the train's bearings
CLEAR, UNDER = 0.75, 0.5
log = []
mw, bot, rimL = sc.byname('Motion-works plate'), sc.byname('Bottom bridge'), sc.byname('Crescent rim plate')
if mw.get('back'): log.append('motion-works plate: its back face had moved off the front (up to %.1f mm); it matches the front again' %
                              max(math.dist((p['u'], p['v']), (q['u'], q['v'])) for p, q in zip(sc.SK[mw['sketch']]['points'], mw['back'])))
mw['back'] = None; mw['edges'] = None

# ---------- the outline: Adam's plate and the bottom bridge's area as one ----------
mounts = mech['mounts']; POS = st['pos']
RANGES = {'lever': (-1.5, 42.7), 'jumper': (0.0, 4.5), 'click': (2.0, 14.0)}    # the sim's 12-hour sweep: 0-41.2, 1.7-2.6, 3.8-12.0
TABLE = {l['arbor']: (min(l['values']) - 1.0, max(l['values']) + 1.0) for l in mech.get('links', []) if l.get('kind') == 'table'}
def centre_of(did):
    mt = mounts[did]; return np.array(mt['pivot'] if 'pivot' in mt else POS[mt['axis']], float)
def sweep(did):
    d = sc.DR[did]; P = sc.outline(d, N=8); mt = mounts[did]; c = centre_of(did)
    if ('axis' in mt and mt['axis'] not in TABLE) or mt.get('angle') == 'hour':
        return disc(c, float(np.hypot(*(P - c).T).max()))
    a0, a1 = TABLE[mt['axis']] if 'axis' in mt else RANGES[mt['angle']]; m = np.zeros(GX.shape, bool)
    for a in np.arange(a0, a1 + 1e-9, 0.5): m |= raster(rot(P, c, a))
    return m
u = raster(sc.outline(mw)) | raster(sc.outline(bot))
u &= disc((0, 0), 66.0)
u &= ~dilate(raster(sc.outline(rimL)), 1.2)
# a moving part that reaches below the plate's bottom face can't have a seat (it would go through): the plate's edge goes round it
for did, mt in mounts.items():
    if 'axisX' in mt: continue
    z0, z1 = sc.zband(sc.DR[did])
    if z1 > Z0 and z0 - UNDER < Z0 + 0.01:
        m = sweep(did)
        if (m & u).any():
            u &= ~dilate(m, CLEAR + 0.5); log.append(f'plate edge steps round the {sc.DR[did]["name"].split(" (")[0].lower()} (it reaches below the plate)')
u = opening(close(u, 1.6), 1.0)
lab, n = ndimage.label(u); sizes = ndimage.sum(u, lab, range(1, n + 1)) * H * H; keep = int(np.argmax(sizes)) + 1
if n > 1: log.append(f'{n - 1} separate scrap(s) dropped ({", ".join(f"{s:.1f}" for i, s in enumerate(sizes) if i + 1 != keep)} mm²)')
u = ndimage.binary_fill_holes(lab == keep)
foot = u
outer = max(loops(u), key=lambda t: t[1])[0]
pts, err, L = RF.fit(dots_smooth(outer[::4]), 0.1)
OLD_SK = {c['sketch'] for c in mw.get('cuts', []) if c.get('kind') == 'pocket'}   # the cuts being replaced: their outlines go too
sc.SK[mw['sketch']]['points'] = pts; sc.SK[mw['sketch']]['plane'] = {'axis': 'z', 'offset': Z0}
mw.update({'name': 'Motion-works plate (3/8"; one secondary plate: the old barrel, right and bottom bridges and the right rim plate)',
           'thickness': T, 'grow': 'plus', 'mill': 'back', 'cuts': []})
log.append(f'motion-works plate: the bottom bridge folded in; {len(pts)} dots (edge within {err[0]:.3f} mm of the cleaned outline), z {Z0}-{ZT:.3f}')

# ---------- staircase seats: each part's outline over its motion, floored at its own base ----------
seats = []
for did, mt in mounts.items():
    if 'axisX' in mt: continue
    d = sc.DR[did]; z0, z1 = sc.zband(d)
    if z1 <= Z0 or z0 >= ZT or z0 - UNDER < Z0 + 0.01: continue
    m = sweep(did)
    if not (m & foot).any(): continue
    if 'Pawl pin' in d['name']: m = dilate(m, 2.0)                       # the pawl blade flexes ~1.8 mm riding back over a tooth
    seats.append((d['name'].split(' (')[0], m, max(FLOOR, z0 - UNDER), CLEAR))
spr = mech['springs'][0]; Lc = centre_of(spr['to']['part']); m = np.zeros(GX.shape, bool)
for a in np.arange(RANGES['lever'][0], RANGES['lever'][1] + 1e-9, 1.0):
    lug = rot([spr['to']['at']], Lc, a)[0]; a_, b_ = np.array(spr['from'], float), lug
    for t in np.linspace(0, 1, 60): m |= disc(a_ + (b_ - a_) * t, spr['r'])
if (m & foot).any(): seats.append(('Return spring', m, max(FLOOR, spr['z'] - spr['r'] - UNDER), CLEAR))
ELS = json.load(open(os.path.join(HERE, 'elements_crescent.json')))
for e in ELS:
    if e['z1'] <= Z0 or e['z0'] >= ZT: continue                          # wheels under the plate stay covered
    m = disc((e['x'], e['y']), e['r'])
    if not (m & foot).any(): continue
    if 'Seconds hand' in e['name']: seats.append(('Window down to the seconds hand', m, FLOOR, 2.0)); continue   # a big opening, 2 mm round its sweep
    seats.append((e['name'].split(' (')[0], m, max(FLOOR, e['z0'] - UNDER), CLEAR))
top = np.where(foot, ZT, np.nan)
levels = {}
for name, m, bottom, clr in seats:
    r = close(dilate(m, clr), 1.0) & dilate(foot, 1.5)                   # round it by the clearance; inside corners at least r 1 (a 2 mm end mill)
    top = np.where(r & foot, np.minimum(top, bottom), top)
    levels.setdefault(round(bottom, 2), []).append(name)
    for poly, ar in loops(r, 1.0):
        sc.pocket_cut(mw, f'Seat · {name}' if not name.startswith('Window') else name, poly, ZT - bottom)
log.append('staircase: ' + '; '.join(f'floor {z:.2f}: {", ".join(sorted(set(v)))}' for z, v in sorted(levels.items())))

# ---------- towers: plate left standing between seats on its own (or a stub on the edge) comes down ----------
edge_band = foot & ~erode(foot, 1.5); n_t = 0
for lev in sorted(set(np.round(top[foot], 3)), reverse=True)[:-1]:
    mask = (top >= lev - 1e-6) & foot
    lab, n = ndimage.label(mask)
    if not n: continue
    sizes_ = ndimage.sum(mask, lab, range(1, n + 1)) * H * H
    ok = np.zeros(n + 1, bool); ok[np.unique(lab[edge_band & mask])] = True; ok[0] = True
    ok[1:] &= sizes_ >= 60.0; ok[1:] |= sizes_ > 150.0
    for j in range(1, n + 1):
        if ok[j]: continue
        sel = lab == j
        ring = dilate(sel, 0.6) & ~sel & foot & (top < lev - 1e-6)
        f = float(np.nanmax(top[ring])) if ring.any() else FLOOR
        top[sel] = f; n_t += 1
        for poly, ar in loops(dilate(sel, 0.3), 0.3):
            sc.pocket_cut(mw, 'Tower removed (plate standing alone between seats)', poly, ZT - f)
log.append(f'{n_t} towers cut down')

sc.remove_parts({bot['id']})
used = {d['sketch'] for d in st['drawn']} | {c['sketch'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
gone = [k for k in st['sketches'] if k['id'] in OLD_SK and k['id'] not in used]
st['sketches'] = [k for k in st['sketches'] if k not in gone]; sc.SK = {k['id']: k for k in st['sketches']}
loose = [k['name'] for k in st['sketches'] if k['id'] not in used]
log.append(f'{len(gone)} outlines of the replaced cuts removed; loose sketches left: {len(loose)}')
sc.pr['decor']['colors'][mw['id']] = '#6e6a64'
J['savedAt'] = '2026-11-18T03:00:00.000Z'
json.dump(J, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('\n'.join(log)); print('written', OUT, '|', len(st['drawn']), 'parts,', len(st['sketches']), 'sketches')
