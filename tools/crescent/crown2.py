# Crown 2 (2026-11-19, Adam's notes P58, P60): a real worm, a tilted stem and a crown you can grip, at today's spot (~1:30).
#
#   - the worm gets its real thread (a helical sweep of its cross-section, sim d.twist): one start, RIGHT-hand, module 1, Ø6 pitch
#   - the stem is tilted up toward the crown by the worm's lead angle (atan 1/6 = 9.46 deg, sim d.place), so the thread at the mesh
#     lies along the centre wheel's straight teeth (a right-hand worm needs its outer end raised for that). The same tilt lifts the
#     crown to mid-stack.
#   - the worm meshes the centre wheel 6 deg round from its 3 o'clock point (2 mm from before): tilted at 0 deg, its lower end
#     would clip the third wheel's recess by 1 mm
#   - the stem rides on a wedge strip in a 2.1 mm groove milled from the main plate's top (the strip's top follows the slope),
#     and a second strip above it holds it down, flush with the plate's top, clamped by the motion-works plate; the strips are cut
#     on edge from 2 mm acrylic sheet (each milled from one face, like every other part)
#   - the worm sits in a pocket with stepped floors (its tilted underside), under a flush cap; the pocket's end walls take its thrust
#   - the crown: Ø21 x 11, 24 flutes, 1 mm off a flat milled into the case edge square to the stem (one flat in the main plate,
#     one in the motion-works plate, each set so the crown clears it by 1 mm at its nearest)
#   apply(J, log)      python3 crown2.py IN.json OUT.json
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, union, circle, opening, close
import pyclipper as pc
import plate_clean as PC

A, ZW, PHI = 26.7, 5.6, math.radians(6.0)
LAM = math.atan(1 / 6)
M_W, R_TIP, R_ROOT, RP, L_W = 1.0, 4.0, 1.75, 3.0, 8.0
R_STEM, GROOVE_W, STRIP_T, WIDE_W, STRIP_HI_T, N_STEP = 1.0, 2.1, 2.0, 3.3, 3.0, 4
R_CR, L_CR, N_FL, GAP_CR = 10.5, 11.0, 24, 1.0
T1, TOP3 = 12.7, 22.225
OLD_D1 = ('Groove for the crown stem', 'Pocket for the worm', 'Groove opened onto the centre wheel recess', 'Knife edge where the stem groove',
          'Seat for the worm cap', 'Seat for the stem cap')

def worm_section(cx, cz, n=240):
    p = math.pi * M_W; ta = math.tan(math.radians(20)); out = []
    for i in range(n):
        psi = 2 * math.pi * i / n; z = (p * psi / (2 * math.pi)) % p; z = z - p if z > p / 2 else z
        r = max(R_ROOT, min(R_TIP, RP + (p / 4 - abs(z)) / ta)); out.append((cx + r * math.cos(psi), cz + r * math.sin(psi)))
    return out
def fluted(cx, cz, n=480):
    return [(cx + (R_CR - 0.35 * (1 - math.cos(N_FL * 2 * math.pi * i / n))) * math.cos(2 * math.pi * i / n),
             cz + (R_CR - 0.35 * (1 - math.cos(N_FL * 2 * math.pi * i / n))) * math.sin(2 * math.pi * i / n)) for i in range(n)]
def rounded(pts, r):
    """a polygon with its outside corners rounded r (an opening), as points"""
    while True:                                                           # a corner radius can't exceed half the narrower side
        o = [q for q in opening([P(pts)], r) if pc.Orientation(q)]
        if o: return [tuple(q) for q in F(max(o, key=lambda q: abs(pc.Area(q))))]
        r -= 0.02
def dots(pts): return [{'u': round(float(u), 4), 'v': round(float(v), 4), 'smooth': False} for u, v in pts]
def axis_angle(R):
    ang = math.acos(max(-1, min(1, (np.trace(R) - 1) / 2)))
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]); return (ax / np.linalg.norm(ax)).tolist(), math.degrees(ang)

def apply(J, log):
    st, pr = J['state'], J['project']; m = pr['mechanisms']; D = {d['id']: d for d in st['drawn']}
    if D.get('D13', {}).get('twist'): return                                  # already done
    SK = {k['id']: k for k in st['sketches']}
    C = np.array(st['pos']['center'], float)
    W = C + A * np.array([math.cos(PHI), math.sin(PHI)]); t = np.array([-math.sin(PHI), math.cos(PHI)]); nv = np.array([math.cos(PHI), math.sin(PHI)])
    tl, sl, cl = math.tan(LAM), math.sin(LAM), math.cos(LAM)
    zax = lambda s: ZW + s * tl                                               # the stem's axis height at horizontal distance s from the worm
    b = 2 * W.dot(t); s_rim = (-b + math.sqrt(b * b - 4 * (W.dot(W) - 66 ** 2))) / 2
    s_face = lambda z, lc: (lc - (z - ZW) * sl) / cl                          # horizontal s of the crown's inner face at height z
    s_w1 = s_rim                                                              # the main plate's flat passes where the stem leaves the rim
    l_c = (s_w1 + GAP_CR) * cl + (T1 - ZW) * sl                               # along-stem distance to the crown's inner face
    s_w3 = s_face(TOP3, l_c) - GAP_CR
    l_cc = l_c + L_CR / 2; z_cc = ZW + l_cc * sl
    top_cr = z_cc + R_CR * cl + (L_CR / 2) * sl; bot_cr = z_cc - R_CR * cl - (L_CR / 2) * sl
    plan = lambda s, n: W + s * t + n * nv
    rect = lambda s0, s1, n0, n1: [plan(s0, n0), plan(s1, n0), plan(s1, n1), plan(s0, n1)]
    # ---- the worm, its stepped pocket and its cap (sampling the tilted worm's surface) ----
    ell = np.linspace(-L_W / 2, L_W / 2, 81); psi = np.linspace(0, 2 * math.pi, 145)
    LL, PP = np.meshgrid(ell, psi)
    s_pts = LL * cl - R_TIP * np.sin(PP) * sl; z_pts = ZW + LL * sl + R_TIP * np.sin(PP) * cl
    bands = [(-4.92, -1.64), (-1.64, 1.64), (1.64, 4.92)]
    floors = []
    for s0, s1 in bands:
        sel = (s_pts >= s0 - 0.3) & (s_pts <= s1 + 0.3); floors.append(math.floor((z_pts[sel].min() - 0.25) * 20) / 20)
    floors[0] = max(floors[0], 0.6)
    cap_z = math.ceil((z_pts.max() + 0.3) * 20) / 20
    # ---- parts: stem, worm, crown (built along +y through (Wx, ZW), then turned into place) ----
    R = np.array([[math.cos(PHI), -math.sin(PHI), 0], [math.sin(PHI), math.cos(PHI), 0], [0, 0, 1]]) @ np.array([[1, 0, 0], [0, cl, -sl], [0, sl, cl]])
    ax, deg = axis_angle(R); piv = [round(float(W[0]), 4), round(float(W[1]), 4), ZW]
    place = {'pivot': piv, 'axis': [round(a, 6) for a in ax], 'deg': round(deg, 4)}
    yaw = {'pivot': piv, 'axis': [0, 0, 1], 'deg': round(math.degrees(PHI), 4)}
    def set_part(pid, name, plane_off, thick, pts, axis='y', grow='plus', extra=None):
        d = D[pid]; k = SK[d['sketch']]; k['plane'] = {'axis': axis, 'offset': round(plane_off, 4)}; k['points'] = dots(pts); k['closed'] = True
        d['name'] = name; d['thickness'] = round(thick, 4); d['grow'] = grow; d.pop('back', None); d.pop('edges', None); d['cuts'] = []
        for kk in ('twist', 'twistAt', 'place'): d.pop(kk, None)
        d.update(extra or {})
    Wy = float(W[1]); Wx = float(W[0])
    stem_l0, stem_l1 = -L_W / 2, l_c + L_CR - 1.0                      # flush with the worm's back face (a bore in the pocket's wall can't be milled from the top)
    set_part('D12', 'Crown stem (Ø2 steel, tilted 9.5° up to the crown; rides on a wedge strip in a groove in the main plate)',
             Wy + stem_l0, stem_l1 - stem_l0, [(Wx + R_STEM * math.cos(2 * math.pi * i / 48), ZW + R_STEM * math.sin(2 * math.pi * i / 48)) for i in range(48)],
             extra={'place': place})
    set_part('D13', 'Worm (steel, one start, right-hand, module 1, Ø6 pitch, 8 long; pinned on the stem; tilted by its lead angle so its thread lies along the centre wheel\'s straight teeth)',
             Wy - L_W / 2, L_W, worm_section(Wx, ZW), extra={'place': place, 'twist': round(-360 * L_W / (math.pi * M_W), 3), 'twistAt': [round(Wx, 4), ZW]})
    set_part('D14', f'Crown (Ø{2 * R_CR:g} × {L_CR:g}, {N_FL} flutes; 1 mm off a flat square to the stem)', Wy + l_c, L_CR, fluted(Wx, ZW), extra={'place': place})
    for pid in ('D12', 'D13', 'D14'): m['mounts'][pid] = {'axisY': [round(Wx, 4), ZW], 'from': 'center', 'ratio': -48}
    # ---- wedge strips (cut on edge from 2 mm sheet), in the vertical plane through the stem: u = y (along the stem before the yaw), v = z ----
    s_a, s_b = 4.92 + 0.3, s_w1
    # the groove in steps (so no small cutter has to go deep): a 3.3 wide upper groove (a 1/8" cutter) whose floor, step by step, is the
    # stem's centre at the step's far end, and under it the 2.1 slot the stem and the lower strip sit in, whose floor is 2 mm under the
    # stem at the step's near end: the slot's walls reach above the stem's centre everywhere (they hold it sideways) and are ~4 mm deep
    edges = np.linspace(s_a, s_b, N_STEP + 1)
    steps = []
    for a_, b_ in zip(edges[:-1], edges[1:]):
        steps.append((a_, b_, math.floor((zax(a_) - R_STEM / cl - 2.0) * 20) / 20, math.floor(zax(b_) * 20) / 20))
    z_f = steps[0][2]
    lo = [(Wy + s_a, steps[0][2])]
    for a_, b_, zf, zw in steps: lo += [(Wy + a_, zf), (Wy + b_, zf)]
    lo += [(Wy + s_b, zax(s_b) - R_STEM / cl - 0.02), (Wy + s_a, zax(s_a) - R_STEM / cl - 0.02)]
    lo = [lo[0]] + [q for i, q in enumerate(lo[1:], 1) if q != lo[i - 1]]
    s_h = min(s_b, (T1 - 0.02 - 2.0 - R_STEM / cl - 0.02 - ZW) / tl)          # the upper strip stops where it would thin under 2 mm
    hi = [(Wy + s_a, zax(s_a) + R_STEM / cl + 0.02), (Wy + s_h, zax(s_h) + R_STEM / cl + 0.02), (Wy + s_h, T1 - 0.02), (Wy + s_a, T1 - 0.02)]
    lo, hi = rounded(lo, 1.0), rounded(hi, 1.0)
    lo = [tuple(q) for q in F(max([q for q in close([P(lo)], 1.0) if pc.Orientation(q)], key=lambda q: abs(pc.Area(q))))]   # the steps' inside corners r 1 (the slot's step edges are rounded r 1.2)
    set_part('D31', 'Lower stem strip (acrylic, cut on edge from 2 mm sheet; its top follows the stem\'s 9.5° slope, its bottom the slot\'s steps)', Wx, STRIP_T, lo, axis='x', grow='both', extra={'place': yaw})
    if 'D32' not in D:
        sid = 'K_strip_hi'; st['sketches'].append({'id': sid, 'name': 'Upper stem strip', 'plane': {'axis': 'x', 'offset': Wx}, 'closed': True, 'points': []}); SK[sid] = st['sketches'][-1]
        st['drawn'].append({'id': 'D32', 'name': '', 'sketch': sid, 'thickness': STRIP_HI_T, 'grow': 'both'}); D['D32'] = st['drawn'][-1]
    set_part('D32', 'Upper stem strip (acrylic, cut on edge from 3 mm sheet; holds the stem down, flush with the plate, clamped by the motion-works plate)', Wx, STRIP_HI_T, hi, axis='x', grow='both', extra={'place': yaw})
    cols = pr.setdefault('decor', {}).setdefault('colors', {}); cols['D32'] = cols.get('D31', '#d9dcdf')
    # ---- the worm cap (flat, flush with the main plate's top) ----
    cap = rounded(rect(-4.92 - 1.2, 4.92 + 0.3, -4.3, 4.3 + 1.2), 1.6)
    set_part('D30', 'Worm cap (over the worm; flush in its seat, clamped by the motion-works plate)', cap_z, T1 - cap_z, [tuple(q) for q in cap], axis='z')
    # ---- the main plate: old stem cuts out, new ones in ----
    d1 = D['D1']; old = [c for c in d1['cuts'] if (c.get('name') or '').startswith(OLD_D1)]
    for c in old:
        if c['kind'] == 'pocket': st['sketches'] = [s for s in st['sketches'] if s['id'] != c['sketch']]
    d1['cuts'] = [c for c in d1['cuts'] if c not in old]
    ids = PC.next_cut_id(J)
    def pocket(d, name, pts, depth, z0=0.0):
        sid = f'K_cr{len(st["sketches"])}'
        st['sketches'].append({'id': sid, 'name': name[:40], 'plane': {'axis': 'z', 'offset': z0}, 'closed': True, 'points': dots([tuple(q) for q in pts])})
        d['cuts'].append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(depth, 4), 'name': name})
    for (s0, s1), f in zip(bands, floors):                                 # nested from the back wall, so each step is one rounded region
        pocket(d1, f'Pocket for the worm, floor {f:.2f} (stepped under its tilted underside; 0.25 under it)', rounded(rect(bands[0][0], s1, -4.3, 4.3), 1.65), T1 - f)
    pocket(d1, f'Seat for the worm cap (floor {cap_z:.2f})', rounded(rect(-4.92 - 1.25, 4.92 + 0.35, -4.35, 4.3 + 1.25), 1.65), T1 - cap_z)
    for i, (a_, b_, zf, zw) in enumerate(steps):
        last = i == len(steps) - 1; a0 = 2.0 if i == 0 else a_ - 0.3
        b0 = (s_w1 + 3) if last else b_ + 1.2; bw = (s_w1 + 3) if last else b_ + 2.0     # each step's round end runs into the next step, clear of the stem and strips
        pocket(d1, f'Stem slot, step {i + 1} (2.1 wide, floor {zf:.2f}: the lower strip and the stem sit in it)', rounded(rect(a0, b0, -GROOVE_W / 2, GROOVE_W / 2), GROOVE_W / 2 - 0.01), T1 - zf)
        pocket(d1, f'Stem groove, step {i + 1} (3.3 wide, floor {zw:.2f}, the stem\'s centre: the upper strip sits in it)', rounded(rect(a0 if i else 4.0, bw, -WIDE_W / 2, WIDE_W / 2), WIDE_W / 2 - 0.01), T1 - zw)
    pocket(d1, 'Flat for the crown (square to the stem across the case edge; the crown stands 1 mm off it)', rounded(rect(s_w1, s_w1 + 25, -R_CR - 2.0, R_CR + 2.0), 1.65), T1)
    d3 = D['D3']; k3 = SK[d3['sketch']]
    pocket(d3, 'Flat for the crown (as in the main plate, set back for the stem\'s tilt)', rounded(rect(s_w3, s_w3 + 25, -R_CR - 2.0, R_CR + 2.0), 1.65), d3['thickness'], z0=k3['plane']['offset'])
    # ---- the proof ----
    m['proofs'] = [p for p in m['proofs'] if not p['label'].startswith('Crown: worm')]
    m['proofs'].insert(min(2, len(m['proofs'])), {'label': 'Crown: worm on the centre wheel', 'by': 'crown2.py', 'ok': True, 'text':
        f'One-start right-hand worm, module 1, Ø6 pitch (lead angle 9.46°), drawn with its real thread, meshing the 48-tooth centre wheel at '
        f'{math.degrees(PHI):.0f}° round from its 3 o\'clock point. The stem is tilted up 9.46° toward the crown, so at the mesh the thread lies along the '
        f'wheel\'s straight teeth (line contact, not the 0.17 mm skew an untilted worm has). One crown turn moves the minute hand 1.25 min '
        f'(48 turns an hour). The worm pocket\'s end walls take its thrust both ways. The crown (Ø{2 * R_CR:g} × {L_CR:g}) is centred at z {z_cc:.1f} '
        f'(spans {bot_cr:.1f}–{top_cr:.1f}) and stands 1 mm off flats milled square to the stem. Checked: the sim\'s side-on check slices the tilted, '
        f'threaded parts from their real shape; the mesh itself is not simulated in 3D.'})
    log.append(f'crown 2: worm at {math.degrees(PHI):.0f}° on the centre wheel {W.round(2).tolist()}, stem tilted {math.degrees(LAM):.2f}°, right-hand thread; '
               f'stem leaves the rim at s {s_rim:.1f}; crown Ø{2 * R_CR:g}×{L_CR:g} centred z {z_cc:.2f} (spans {bot_cr:.2f}–{top_cr:.2f}); flats at s {s_w1:.2f} (main) '
               f'and {s_w3:.2f} (motion-works); worm pocket floors {floors}, cap from z {cap_z}; stem steps {[(round(a,1), zf, zw) for a, b, zf, zw in steps]}; place {place}')
    return dict(W=W, t=t, n=nv, s_rim=s_rim, s_w1=s_w1, s_w3=s_w3, l_c=l_c, z_cc=z_cc, top=top_cr, bot=bot_cr)

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; r = apply(J, log)
    PC.apply(J, log, 'D1'); PC.rebuild(J, log, 'D3')
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
