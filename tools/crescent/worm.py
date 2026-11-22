# Crown worm (2026-11-18, Adam's notes P42, P43): the crown stem drives the centre wheel itself from the side through a worm, inside the
# main plate. The keyless works under the plate go: setting wheel, pin wheel and its pins, keyless pinion, setting and keyless plates.
#
# Layout. The worm meshes the centre wheel (48, module 1, shift -0.3, z 4.6-6.6) at the wheel's own 3 o'clock point, so the stem runs
# straight along +y (the sim draws side parts only along x or y) to the rim at about half past one. In the wheel's mid-plane the worm's
# thread is a module-1 rack; its pitch line sits at r 23.7 from the centre arbor (24 - 0.3), the same rack the wheel's teeth are drawn
# from, so worm axis = centre + 26.7 in x (Ø6 pitch worm). Tip clearance: worm tip r 4 reaches r 22.7 (wheel root 22.45); wheel tip
# 24.7, worm root r 1.75 at 24.95: 0.25 mm both ways.
# One start: one crown turn = one tooth = 1.25 min of the hour = about 112 beats; 48 turns an hour. Left-hand thread, so running the
# train forward presses the worm down (onto the stem's groove floor) instead of lifting it; the crown turns counterclockwise end-on.
# The crown is the only drive (nothing winds the mainspring), so the worm stays in mesh: no pull-out position.
# Made: the main plate gets a groove for the stem (milled from the top, the stem rests on its floor), a pocket for the worm (its end
# walls take the worm's thrust) and two seats; a worm cap and a stem cap sit flush in the seats and the motion-works plate clamps them.
#
#   apply(J, log)   (refine.py can call it; idempotent)   ·   python3 worm.py IN.json OUT.json
import json, math, os, sys, copy
import numpy as np
import pyclipper as pc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pk2 import P, F, inter, diff, opening, circle

C = (21.1396, 17.4537)          # centre arbor
A = 26.7                        # worm axis from the centre arbor (wheel pitch r 24 - 0.3 shift + worm pitch r 3)
XW, ZW = C[0] + A, 5.6          # worm and stem axis (along y): x, z (the centre wheel's mid-plane)
R_TIP, R_ROOT, R_STEM = 4.0, 1.75, 1.0
W0, W1 = 13.95, 21.95           # worm ends (y): clear of the third wheel's footprint at the inner end (that wheel is 0.2 above the worm)
YS0 = W0 - 3.0                  # stem's inner end
R_CROWN, T_CROWN = 4.5, 5.0
R_RIM = 66.0
Y_CROWN = math.sqrt(R_RIM ** 2 - (XW - R_CROWN) ** 2) + 0.5   # the crown's inner face clears the rim on its near side
Z_GROOVE = ZW - R_STEM - 0.05   # groove floor: the stem rests on it
Z_WORM_FLOOR = ZW - R_TIP - 0.3
Z_CAP = ZW + R_TIP + 0.3        # worm cap's underside: 0.3 over the worm
Z_TOP = 12.7                    # main plate's top face
GAP = 0.05                      # seat around each cap
R_CORNER = 1.7                  # inside corners a 1/8" bit (r 1.59) reaches

def pt(u, v, smooth=False): return {'u': round(float(u), 4), 'v': round(float(v), 4), 'smooth': smooth}
def ccw(pts):
    a = sum(pts[i]['u'] * pts[(i + 1) % len(pts)]['v'] - pts[(i + 1) % len(pts)]['u'] * pts[i]['v'] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]
def circ(cu, cv, r, n=48): return [pt(cu + r * math.cos(2 * math.pi * k / n), cv + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
def rrect(x0, x1, y0, y1, r, n=6):
    out = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for j in range(n + 1):
            a = math.radians(a0 + 90 * j / n); out.append(pt(cx + r * math.cos(a), cy + r * math.sin(a)))
    return ccw(out)
def groove(x, y0, half, y1, n=12):
    out = [pt(x - half, y1), pt(x - half, y0)]
    out += [pt(x + half * math.cos(math.radians(180 + 180 * j / n)), y0 + half * math.sin(math.radians(180 + 180 * j / n))) for j in range(1, n)]
    out += [pt(x + half, y0), pt(x + half, y1)]
    return ccw(out)
def fluted(cu, cv, r, flutes=18, depth=0.35, n=108):
    return [pt(cu + (r - depth / 2 + depth / 2 * math.cos(flutes * 2 * math.pi * k / n)) * math.cos(2 * math.pi * k / n),
               cv + (r - depth / 2 + depth / 2 * math.cos(flutes * 2 * math.pi * k / n)) * math.sin(2 * math.pi * k / n)) for k in range(n)]

def apply(J, log):
    st, pr = J['state'], J['project']; m = pr['mechanisms']
    D = {d['id']: d for d in st['drawn']}
    if 'keyless' not in st['pos'] and D.get('D13', {}).get('name', '').startswith('Worm'): return     # already done
    SK = {k['id']: k for k in st['sketches']}
    nk = [max(int(k['id'][1:]) for k in st['sketches'])]
    def new_sketch(name, plane, pts):
        nk[0] += 1; k = {'id': f'K{nk[0]}', 'name': name, 'plane': plane, 'closed': True, 'points': pts}; st['sketches'].append(k); return k['id']

    # ---- 1. the keyless works under the plate go ----
    gone = ['D9', 'D10', 'D11']
    drop_sk = set()
    for i in gone + ['D12', 'D13', 'D14']:
        d = D[i]; drop_sk.add(d['sketch']); drop_sk |= {c['sketch'] for c in d.get('cuts', []) if c.get('sketch')}
    st['drawn'] = [d for d in st['drawn'] if d['id'] not in gone]
    mp = D['D1']; n0 = len(mp['cuts'])
    mp['cuts'] = [c for c in mp['cuts'] if not (c.get('axis') == 'keyless' or 'keyless' in c.get('name', '') or c.get('name', '').startswith('Centre arbor through to the setting wheel'))]
    cut_gone = n0 - len(mp['cuts'])
    for k in ('s_set',): st['stages'].pop(k, None); pr['stages'].pop(k, None); pr['defaults'].get('stages', {}).pop(k, None)
    for g in ('setting_wheel', 'keyless_pinion', 'pin_wheel'):
        st['thick'].pop(g, None); st['locks'].pop(g, None); pr['defaults'].get('locks', {}).pop(g, None)
    st['pos'].pop('keyless', None); pr['defaults'].get('pos', {}).pop('keyless', None)
    pr['arbors'] = [a for a in pr['arbors'] if a['id'] != 'keyless']
    cen = next(a for a in pr['arbors'] if a['id'] == 'center')
    cen['gears'] = [g for g in cen['gears'] if g['id'] != 'setting_wheel']
    cen['role'] = ('Turns once an hour. Its pinion is driven by the barrel; its wheel drives the third and takes the crown: the worm on the crown stem '
                   'turns it from the side, one tooth per crown turn; the snail on top drives the retrograde minute.')
    m['mounts'].pop('D11', None); m['rods'].pop('keyless', None); pr['groups'].pop('keyless', None)
    cols = pr.get('decor', {}).get('colors', {})
    for k in ('D9', 'D10', 'D11', 'group:keyless'): cols.pop(k, None)
    for f in pr.get('focus', []): f['parts'] = [p for p in f.get('parts', []) if p != 'keyless']
    pr['plate']['role'] = 'Just the ground under the movement; the movement\'s own main plate is the drawn part "Main plate".'
    pr['blurb'] = pr['blurb'].replace('keyless works in two plates under the main plate',
                                      'a worm on the crown stem turns the centre wheel from the side, inside the main plate')
    esc = next(a for a in pr['arbors'] if a['id'] == 'escape')
    esc['role'] = esc['role'].replace('(one crown turn is 450 beats)', '(one crown turn is about 112 beats)')

    # ---- 2. stem, worm, crown: side parts on y-planes, turning about the stem's line ----
    D12, D13, D14 = D['D12'], D['D13'], D['D14']
    y_stem1 = Y_CROWN + T_CROWN * 0.6
    D12.update(name='Crown stem (Ø2 steel; rests in a groove in the main plate and carries the worm)', thickness=round(y_stem1 - YS0, 4),
               grow='plus', back=None, edges=None, sketch=new_sketch('Crown stem outline', {'axis': 'y', 'offset': round(YS0, 4)}, circ(XW, ZW, R_STEM, 32)))
    D12.pop('cuts', None)
    D13.update(name='Worm (steel, one start, left-hand, module 1, Ø6 pitch, 8 long; pressed and pinned on the stem; its thread is not drawn)',
               thickness=round(W1 - W0, 4), grow='plus', back=None, edges=None, cuts=[],
               sketch=new_sketch('Worm outline (its tip diameter)', {'axis': 'y', 'offset': W0}, circ(XW, ZW, R_TIP, 48)))
    D14.update(name='Crown (Ø9, 18 flutes)', thickness=T_CROWN, grow='plus', back=None, edges=None,
               sketch=new_sketch('Crown outline', {'axis': 'y', 'offset': round(Y_CROWN, 4)}, fluted(XW, ZW, R_CROWN)))
    D14.pop('cuts', None)
    for i in ('D12', 'D13', 'D14'): m['mounts'][i] = {'axisY': [round(XW, 4), ZW], 'from': 'center', 'ratio': 48}
    m['meshes'] = [x for x in m.get('meshes', []) if x.get('part') != 'D13'] + [{'part': 'D13', 'gear': 'center_wheel'}]

    # ---- 3. the main plate: groove, worm pocket, two seats; the two caps ----
    zp = {'axis': 'z', 'offset': 0}
    hn = [max(int(c['id'][1:]) for d in st['drawn'] for c in d.get('cuts', []) if c.get('id', 'x')[1:].isdigit())]
    def cut(name, sid, z_floor):
        hn[0] += 1; mp['cuts'].append({'id': f'h{hn[0]}', 'kind': 'pocket', 'name': name, 'sketch': sid, 'from': 'back', 'depth': round(Z_TOP - z_floor, 4), 'seat': None, 'csk': None})
    # the stem's groove in two steps: 3.4 wide down to the stem's top (a 1/8" bit), then 2.1 wide to the floor it rests on (a 2 mm bit, 2.2 of flute)
    cut('Groove for the crown stem, upper (3.4 wide, down to the stem\'s top)', new_sketch('Groove for the crown stem, upper (pocket outline)', zp, groove(XW, YS0, 1.7, 72.0)), ZW + R_STEM + 0.1)
    cut('Groove for the crown stem (2.1 wide; the stem rests on its floor and its walls set the worm\'s centre distance)', new_sketch('Groove for the crown stem (pocket outline)', zp, groove(XW, YS0, R_STEM + 0.05, 72.0)), Z_GROOVE)
    cut('Pocket for the worm (0.3 under it; its inner end wall takes the worm\'s thrust when the crown drives)', new_sketch('Pocket for the worm (pocket outline)', zp, rrect(XW - R_TIP - 1.3, XW + R_TIP + 1.3, W0 - 0.15, W1 + 0.15, R_CORNER)), Z_WORM_FLOOR)
    # beside the worm the groove's wheel-side wall would be under 1 mm (the stem sits 26.7 from the centre arbor, the recess wall is at 25.45):
    # it comes down to the groove floor, and the stem bears on the outer wall, which is where the mesh pushes it
    cut('Groove opened onto the centre wheel recess beside the worm (that wall would be under 1 mm; the mesh pushes the stem onto the outer wall)',
        new_sketch('Groove opened onto the centre wheel recess (pocket outline)', zp, rrect(XW - 5.84, XW + R_STEM + 0.05, YS0 - 2.95, 25.5, R_CORNER)), Z_GROOVE)
    # where the groove leaves the rim at 46 deg, the plate between its outer wall and the rim ends in a knife edge: rounded off r 1
    for wall, z_floor, lvl in ((XW + 1.7, ZW + R_STEM + 0.1, 'upper'), (XW + R_STEM + 0.05, Z_GROOVE, 'lower')):
        box = [P(np.array([(wall, 30.0), (62.0, 30.0), (62.0, 70.0), (wall, 70.0)]))]
        M = inter([circle((0, 0), R_RIM)], box)
        tip = inter(diff(M, opening(M, 1.0)), [P(np.array([(wall - 1, 40.0), (62.0, 40.0), (62.0, 70.0), (wall - 1, 70.0)]))])
        for j, path in enumerate(p_ for p_ in tip if pc.Orientation(p_) and abs(pc.Area(p_)) > 1e-4 * 1e8):
            q = F(path); pts = ccw([pt(x, y) for x, y in q[::max(1, len(q) // 60)]])
            cut(f'Knife edge where the stem groove ({lvl}) leaves the rim, rounded off r 1', new_sketch(f'Groove mouth, {lvl} (pocket outline)', zp, pts), z_floor)
    cap1 = (XW - 5.6, XW + 7.0, 14.6, 27.0); cap2 = (XW - 3.5, XW + 3.5, 30.0, 36.0)
    cut('Seat for the worm cap', new_sketch('Seat for the worm cap (pocket outline)', zp, rrect(cap1[0] - GAP, cap1[1] + GAP, cap1[2] - GAP, cap1[3] + GAP, R_CORNER)), Z_CAP)
    cut('Seat for the stem cap', new_sketch('Seat for the stem cap (pocket outline)', zp, rrect(cap2[0] - GAP, cap2[1] + GAP, cap2[2] - GAP, cap2[3] + GAP, R_CORNER)), ZW + R_STEM + 0.1)
    nd = max(int(d['id'][1:]) for d in st['drawn'])
    caps = [(f'D{nd + 1}', 'Worm cap (over the worm and the stem; sits flush in its seat, clamped by the motion-works plate)', cap1, Z_CAP),
            (f'D{nd + 2}', 'Stem cap (holds the stem down in its groove near the rim; flush in its seat, clamped by the motion-works plate)', cap2, ZW + R_STEM + 0.1)]
    for did, name, (x0, x1, y0, y1), z0 in caps:
        st['drawn'].append({'id': did, 'name': name, 'sketch': new_sketch(name.split(' (')[0] + ' outline', {'axis': 'z', 'offset': round(z0, 4)}, rrect(x0, x1, y0, y1, R_CORNER - GAP)),
                            'thickness': round(Z_TOP - z0, 4), 'grow': 'plus', 'back': None, 'edges': None, 'cuts': []})
        if 'D29' in cols: cols[did] = cols['D29']
    # orphaned sketches of the removed parts
    used = {d['sketch'] for d in st['drawn']} | {c['sketch'] for d in st['drawn'] for c in d.get('cuts', []) if c.get('sketch')}
    st['sketches'] = [k for k in st['sketches'] if k['id'] not in drop_sk or k['id'] in used]

    # ---- 4. the proof that replaces the keyless one ----
    lead = math.pi; lam = math.degrees(math.atan(lead / (math.pi * 6.0))); skew = 1.0 * math.tan(math.radians(lam))
    proof = {'label': 'Crown: worm on the centre wheel', 'by': 'worm.py', 'ok': True, 'text':
             (f'a one-start left-hand worm (module 1, Ø6 pitch, 8 long) on the stem meshes the centre wheel 48 at its 3 o\'clock point. In the wheel\'s '
              f'mid-plane the thread is a module-1 rack with its pitch line at r 23.7 from the centre arbor, the rack the wheel\'s -0.3 shifted teeth are drawn '
              f'from, so it rolls on them like a rack; tip clearance 0.25 mm both ways. The thread slants {lam:.1f}° to the straight teeth: over the 2 mm wheel '
              f'that is ±{skew:.2f} mm, inside the 0.4 mm of axial play a thinner thread (1.17 mm at the pitch line) leaves, so it touches at a point, '
              f'fine for hand cranking. One crown turn = one tooth = 1.25 min = about 112 beats; 48 turns an hour. Turned backwards it meets the barrel click. '
              f'Worked out from the tooth geometry, not run in a 3D mesh simulation')}
    m['proofs'] = [p for p in m['proofs'] if not p['label'].startswith('Keyless')]
    m['proofs'].insert(min(2, len(m['proofs'])), proof)
    log.append(f'crown worm: keyless works removed (setting plate, keyless plate, pin wheel and pins, keyless pinion, setting wheel; {cut_gone} main plate cuts); '
               f'worm Ø6 pitch on the stem at x {XW:.2f} z {ZW}, y {W0}-{W1}; stem y {YS0:.2f}-{y_stem1:.2f}; crown at y {Y_CROWN:.2f} '
               f'(about {90 - math.degrees(math.atan2(Y_CROWN, XW)) + 0:.0f}° from 12 toward 3); groove floor z {Z_GROOVE:.2f}, worm pocket floor z {Z_WORM_FLOOR:.2f}; caps {caps[0][0]}, {caps[1][0]}')

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    apply(J, log); print('\n'.join(log))
    json.dump(J, open(sys.argv[2], 'w'), ensure_ascii=False)
