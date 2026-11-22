# Crown 3 (2026-11-21, Adam): "why is it at an angle. that needs to exit horizontally ... horizontal shaft for sure", "im cool with
# the crown being larger ... need something for the user to grip", "the shaft should be close to the size of the screw ... beef it up".
#
#   - the stem is horizontal, at the centre wheel's mid-plane (z 5.6), on the same line in plan as before (the worm 6 deg round
#     from the centre wheel's 3 o'clock point, the crown at about 1:30)
#   - the stem is Ø4 (the M2 screws' heads are Ø4.2; 16x stiffer in bending than the Ø2 stem). The worm is cut on its inner end
#     (one steel part: an Ø8 worm section on the Ø4 stem; the worm's root is Ø3.5 because the centre wheel's tips come within
#     r 2.0 of its axis, so the stem can't run through the worm)
#   - the worm: one start, right-hand, module 1, Ø6 pitch. Untilted, its thread crosses the wheel's straight teeth at its lead angle
#     (9.46 deg): over the wheel's 2 mm face that is +/-0.17 mm, taken up by the mesh's play (as in the first worm)
#   - the crown: Ø24 x 12, 30 flutes, 1 mm off a flat square to the stem (one vertical flat through the main plate and the
#     motion-works plate). Centred on the stem, it hangs 6.4 mm below the case back (Adam: fine, it's for gripping)
#   - the stem lies in a 4.1 groove milled from the main plate's top (a 1/8" cutter), its floor under the stem, and a stem cap
#     (a flat bar milled from one face) sits on it in the groove, flush with the plate, clamped by the motion-works plate.
#     The worm sits in a pocket under a flush cap; the pocket's end walls take its thrust.
#   apply(J, log)      python3 crown3.py IN.json OUT.json
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pyclipper as pc
from pk2 import P, F, opening
import plate_clean as PC

A, ZW, PHI = 26.7, 5.6, math.radians(6.0)
M_W, R_TIP, R_ROOT, RP, L_W = 1.0, 4.0, 1.75, 3.0, 8.0
R_STEM, GROOVE_W = 2.0, 4.1
R_CR, L_CR, N_FL, GAP_CR = 12.0, 12.0, 30, 1.0
T1 = 12.7
OLD_D1 = ('Pocket for the worm', 'Seat for the worm cap', 'Stem slot, step', 'Stem groove, step', 'Flat for the crown', 'Groove for the stem')
OLD_D3 = ('Flat for the crown',)

def worm_section(cx, cz, n=240):
    p = math.pi * M_W; ta = math.tan(math.radians(20)); out = []
    for i in range(n):
        psi = 2 * math.pi * i / n; z = (p * psi / (2 * math.pi)) % p; z = z - p if z > p / 2 else z
        r = max(R_ROOT, min(R_TIP, RP + (p / 4 - abs(z)) / ta)); out.append((cx + r * math.cos(psi), cz + r * math.sin(psi)))
    return out
def fluted(cx, cz, n=600):
    return [(cx + (R_CR - 0.4 * (1 - math.cos(N_FL * 2 * math.pi * i / n))) * math.cos(2 * math.pi * i / n),
             cz + (R_CR - 0.4 * (1 - math.cos(N_FL * 2 * math.pi * i / n))) * math.sin(2 * math.pi * i / n)) for i in range(n)]
def dots(pts): return [{'u': round(float(u), 4), 'v': round(float(v), 4), 'smooth': False} for u, v in pts]
def rounded(pts, r):
    while True:
        o = [q for q in opening([P(pts)], r) if pc.Orientation(q)]
        if o: return [tuple(q) for q in F(max(o, key=lambda q: abs(pc.Area(q))))]
        r -= 0.02

def apply(J, log):
    st, pr = J['state'], J['project']; m = pr['mechanisms']; D = {d['id']: d for d in st['drawn']}
    if D.get('D12', {}).get('name', '').startswith('Crown stem (Ø4'): return   # already horizontal
    SK = {k['id']: k for k in st['sketches']}
    C = np.array(st['pos']['center'], float)
    W = C + A * np.array([math.cos(PHI), math.sin(PHI)]); t = np.array([-math.sin(PHI), math.cos(PHI)]); nv = np.array([math.cos(PHI), math.sin(PHI)])
    b = 2 * W.dot(t); s_rim = (-b + math.sqrt(b * b - 4 * (W.dot(W) - 66 ** 2))) / 2
    s_flat = s_rim; s_face = s_flat + GAP_CR
    plan = lambda s, n: W + s * t + n * nv
    rect = lambda s0, s1, n0, n1: [plan(s0, n0), plan(s1, n0), plan(s1, n1), plan(s0, n1)]
    Wx, Wy = float(W[0]), float(W[1]); piv = [round(Wx, 4), round(Wy, 4), ZW]
    yaw = {'pivot': piv, 'axis': [0, 0, 1], 'deg': round(math.degrees(PHI), 4)}
    def set_part(pid, name, plane_off, thick, pts, axis='y', grow='plus', extra=None):
        d = D[pid]; k = SK[d['sketch']]; k['plane'] = {'axis': axis, 'offset': round(plane_off, 4)}; k['points'] = dots(pts); k['closed'] = True
        d['name'] = name; d['thickness'] = round(thick, 4); d['grow'] = grow; d['cuts'] = []
        for kk in ('twist', 'twistAt', 'place', 'back', 'edges'): d.pop(kk, None)
        d.update(extra or {})
    # ---- stem, worm, crown: built along +y through (Wx, ZW), then turned about z into the stem's line ----
    stem_l0, stem_l1 = L_W / 2, s_face + L_CR - 1.0
    set_part('D12', 'Crown stem (Ø4 steel, horizontal; the worm is cut on its inner end; it lies in a groove in the main plate under a stem cap)',
             Wy + stem_l0, stem_l1 - stem_l0, [(Wx + R_STEM * math.cos(2 * math.pi * i / 64), ZW + R_STEM * math.sin(2 * math.pi * i / 64)) for i in range(64)], extra={'place': yaw})
    set_part('D13', 'Worm (cut on the stem\'s inner end, one steel part: one start, right-hand, module 1, Ø6 pitch, 8 long)', Wy - L_W / 2, L_W, worm_section(Wx, ZW),
             extra={'place': yaw, 'twist': round(-360 * L_W / (math.pi * M_W), 3), 'twistAt': [round(Wx, 4), ZW]})
    set_part('D14', f'Crown (Ø{2 * R_CR:g} × {L_CR:g}, {N_FL} flutes; 1 mm off a flat square to the stem)', Wy + s_face, L_CR, fluted(Wx, ZW), extra={'place': yaw})
    for pid in ('D12', 'D13', 'D14'): m['mounts'][pid] = {'axisY': [round(Wx, 4), ZW], 'from': 'center', 'ratio': -48}
    # ---- worm cap and stem cap (flat parts, milled from one face) ----
    cap_z = ZW + R_TIP + 0.3
    set_part('D30', 'Worm cap (over the worm; flush in its seat, clamped by the motion-works plate)', cap_z, T1 - cap_z,
             rounded(rect(-4.62 - 1.2, 4.62, -4.6, 4.6 + 1.2), 1.6), axis='z')
    s_c0 = 4.62 + 0.35 + 0.05
    set_part('D31', 'Stem cap (a flat bar on the stem in its groove, flush with the plate, clamped by the motion-works plate)', ZW + R_STEM + 0.05, T1 - (ZW + R_STEM + 0.05),
             rounded(rect(s_c0, s_flat - 0.05, -(GROOVE_W - 0.1) / 2, (GROOVE_W - 0.1) / 2), 1.0), axis='z')
    if 'D32' in D:
        st['sketches'] = [k for k in st['sketches'] if k['id'] != D['D32']['sketch']]; st['drawn'] = [d for d in st['drawn'] if d['id'] != 'D32']
        pr.get('decor', {}).get('colors', {}).pop('D32', None); m['mounts'].pop('D32', None)
    # ---- the main plate and the motion-works plate: old crown cuts out, new ones in ----
    ids = PC.next_cut_id(J)
    def drop(d, names):
        old = [c for c in d['cuts'] if (c.get('name') or '').startswith(names)]
        for c in old:
            if c['kind'] == 'pocket': st['sketches'][:] = [s for s in st['sketches'] if s['id'] != c['sketch']]
        d['cuts'] = [c for c in d['cuts'] if c not in old]
    def pocket(d, name, pts, depth, z0=0.0):
        sid = f'K_cr3_{len(st["sketches"])}'
        st['sketches'].append({'id': sid, 'name': name[:40], 'plane': {'axis': 'z', 'offset': z0}, 'closed': True, 'points': dots([tuple(q) for q in pts])})
        d['cuts'].append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(depth, 4), 'name': name})
    d1, d3 = D['D1'], D['D3']; drop(d1, OLD_D1); drop(d3, OLD_D3)
    floor_w = ZW - R_TIP - 0.3
    pocket(d1, f'Pocket for the worm (floor {floor_w:.2f}, 0.3 under it; its end walls take the worm\'s thrust)', rounded(rect(-4.62, 4.62, -4.6, 4.6), 1.65), T1 - floor_w)
    pocket(d1, f'Seat for the worm cap (floor {cap_z:.2f})', rounded(rect(-4.62 - 1.25, 4.62 + 0.05, -4.65, 4.6 + 1.25), 1.65), T1 - cap_z)
    floor_g = ZW - R_STEM
    pocket(d1, f'Groove for the stem (4.1 wide, floor {floor_g:.2f}: the stem rests on it; its walls hold it sideways)', rounded(rect(3.0, s_flat + 3, -GROOVE_W / 2, GROOVE_W / 2), GROOVE_W / 2 - 0.01), T1 - floor_g)
    flat = rounded(rect(s_flat, s_flat + 30, -R_CR - 2.0, R_CR + 2.0), 1.65)
    # any screw or pilot (on every part) that would sit within 2.5 mm of the flat's side walls moves along its ring, away from it
    for _ in range(12):
        moved = False
        for d in st['drawn']:
            for c in d.get('cuts') or []:
                if c['kind'] not in ('screw', 'pilot') or not c.get('at'): continue
                q = np.array(c['at']) - W; s_, n_ = q @ t, q @ nv
                if s_ > s_flat - 3 and abs(n_) < R_CR + 2.0 + 2.5 + c['d'] / 2:
                    r_ = math.hypot(*c['at']); a_ = math.atan2(c['at'][1], c['at'][0])
                    step = math.radians(1.0) * (1 if (np.array([-math.sin(a_), math.cos(a_)]) @ nv) * n_ > 0 else -1)
                    same = [cc for dd in st['drawn'] for cc in (dd.get('cuts') or []) if cc.get('at') and math.hypot(cc['at'][0] - c['at'][0], cc['at'][1] - c['at'][1]) < 0.05]
                    for cc in same: cc['at'] = [round(r_ * math.cos(a_ + step), 4), round(r_ * math.sin(a_ + step), 4)]
                    moved = True
        if not moved: break
    pocket(d1, 'Flat for the crown (vertical, square to the stem; the crown stands 1 mm off it)', flat, T1)
    pocket(d3, 'Flat for the crown (the same flat through this plate)', flat, d3['thickness'], z0=SK[d3['sketch']]['plane']['offset'])
    # ---- the proof ----
    m['proofs'] = [p for p in m['proofs'] if not p['label'].startswith('Crown: worm')]
    m['proofs'].insert(min(2, len(m['proofs'])), {'label': 'Crown: worm on the centre wheel', 'by': 'crown3.py', 'ok': True, 'text':
        f'Horizontal Ø{2 * R_STEM:g} steel stem at z {ZW} with the worm cut on its inner end: one start, right-hand, module 1, Ø6 pitch (lead angle 9.46°), '
        f'meshing the 48-tooth centre wheel {math.degrees(PHI):.0f}° round from its 3 o\'clock point. Untilted, the thread crosses the wheel\'s straight teeth '
        f'at 9.46°: ±0.17 mm over the 2 mm face, inside the mesh\'s play. One crown turn moves the minute hand 1.25 min (48 turns an hour). The worm pocket\'s end '
        f'walls take its thrust. The crown (Ø{2 * R_CR:g} × {L_CR:g}) stands 1 mm off a vertical flat square to the stem and hangs {R_CR - ZW:.1f} mm below the case back. '
        f'Checked: the sim\'s side-on check slices the threaded worm from its real shape; the mesh itself is not simulated in 3D.'})
    log.append(f'crown 3: horizontal Ø{2 * R_STEM:g} stem at z {ZW}, worm {W.round(2).tolist()} on the centre wheel at {math.degrees(PHI):.0f}°, stem leaves the rim at s {s_rim:.2f}; '
               f'crown Ø{2 * R_CR:g}×{L_CR:g} (z {ZW - R_CR:.1f}..{ZW + R_CR:.1f}); flat at s {s_flat:.2f}; worm pocket floor {floor_w:.2f}, cap from {cap_z:.2f}; groove floor {floor_g:.2f}')

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; apply(J, log)
    PC.apply(J, log, 'D1'); PC.rebuild(J, log, 'D3')
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
