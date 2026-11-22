# Crescent: Claude's movement for BSPK Studio. Generates sim/projects/crescent.json.
# Module 1 involute teeth, Ø128 movement, retrograde minute (snail + rack lever), lever kick on a jumping hour star, small seconds.
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import design as DS
from kit import X, Y, circle, curve, bez, U, smax, pol as polk
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'sim', 'projects', 'crescent.json')
def pol(c, r, a_deg): return (c[0] + r * math.cos(math.radians(a_deg)), c[1] + r * math.sin(math.radians(a_deg)))
def polr(c, r, a): return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
def rnd(p, n=4): return [round(p[0], n), round(p[1], n)]
P = DS.PIV; B, C, T, I, Fo, E, F, Bc, Q, L, H, K = (P[k] for k in ('B', 'C', 'T', 'I', 'Fo', 'E', 'F', 'Bc', 'Q', 'L', 'H', 'K'))
K = pol(C, 30.0, -30)                                        # keyless pinion under the plate meshes the setting wheel (48) on the centre arbor
LV = json.load(open(os.path.join(HERE, 'levels.json')))   # from levels.py
KG = json.load(open(os.path.join(HERE, 'keyless_geo.json')))
EG = json.load(open(os.path.join(HERE, 'escapement_geo.json')))   # from escapement.py: escape wheel, fork, impulse pin, and their motion, proven there   # from keyless.py: winding pinion and pin wheel, mesh proven there
# ---------- mechanism numbers from the kinematic prototype ----------
ML = json.load(open(os.path.join(HERE, 'mech_lever.json')))
LF = ML['LF']; R0, R1 = ML['R0'], ML['R1']; th8, th20 = ML['th8'], ML['th20']; psi = ML['psi']; TH_STOP = ML['TH_STOP']
DIR = 1                                                      # centre arbor anticlockwise, so the seconds (three meshes on) run clockwise
T_FB, T_POSE = -48.0, 3602.0                                 # snail phase from the prototype; draw everything as it stands just after a fly-back
omega = DIR * 2 * math.pi / 3600
th_snail_pose = psi + DIR * 1e-4 + omega * (T_POSE + T_FB)
# lever angle at the pose and over the hour (re-run the prototype's continuous solve)
exec(open(os.path.join(HERE, 'mech.py')).read().split('# ---- time loop')[0].split('P = {k:')[0])
def pol(c, r, a_deg): return (c[0] + r * math.cos(math.radians(a_deg)), c[1] + r * math.sin(math.radians(a_deg)))   # mech.py's pol takes radians; ours takes degrees
def rot(p, c, a): x, y = p[0] - c[0], p[1] - c[1]; ca, sa = math.cos(a), math.sin(a); return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)
TRACK0_PRE = 210.0   # the minute track's 0 (degrees); the hand pinion's pose follows from it
SLANT = math.radians(-6)   # undercut cliff (a beak): the nose drops clear in one step
SNAIL_L = [polr((0, 0), R0 + (R1 - R0) * k / 720, -DIR * 2 * math.pi * k / 720) for k in range(720)] + [polr((0, 0), R1 - (R1 - R0) * j / 8, -DIR * (2 * math.pi + SLANT * j / 8)) for j in range(9)]
def snail_w(a): return [rot((C[0] + x, C[1] + y), C, a) for x, y in SNAIL_L]
def nose(th): return polr(L, LF, th)
def solve(a_cam, th_prev, step=math.radians(0.05)):
    sw = snail_w(a_cam)
    def bis(a, b):
        for _ in range(30):
            m = (a + b) / 2
            if inside(nose(m), sw): a = m
            else: b = m
        return b
    th = th_prev
    if inside(nose(th), sw):
        while inside(nose(th), sw): th += step
        return bis(th - step, th)
    while th - step > TH_STOP and not inside(nose(th - step), sw): th -= step
    if th - step <= TH_STOP: return TH_STOP
    return bis(th - step, th)
th = th8; ths = {}
for t in range(0, int(T_POSE) + 3700, 10):
    th = solve(psi + DIR * 1e-4 + omega * (t + T_FB), th); ths[t] = th
TH_POSE = ths[int(T_POSE) - int(T_POSE) % 10]
TH_HI = max(v for t, v in ths.items() if T_POSE <= t < T_POSE + 3580)
SWING = TH_HI - TH_POSE
print('lever pose', round(math.degrees(TH_POSE), 3), 'top', round(math.degrees(TH_HI), 3), 'swing', round(math.degrees(SWING), 3), 'deg -> hand sweep', round(3 * math.degrees(SWING), 2))
# ---- linear snail (a conjugate cam) ----
# An Archimedean snail moves the lever unevenly over the hour (about ±28 %), so the hand would read minutes off on a uniform track.
# Instead the cam is the path the nose must follow in the snail's own frame for the lever, and so the hand, to turn at a constant rate:
# lever angle = TH_POSE + SWING * t / 3600, with the snail at its drawn angle at t = 0 (12:00:00, just after a fly-back).
A0 = th_snail_pose
def snail_local(te_, th_):
    a = A0 + omega * te_; p = rot(nose(th_), C, -a); return (p[0] - C[0], p[1] - C[1])
LOC = [snail_local(3600 * k / 720, TH_POSE + SWING * k / 720) for k in range(721)]
# the cliff: the nose's own drop path (an arc about the lever pivot with the snail held at the hour), undercut progressively to 5 deg at its foot,
# so the edge releases the nose and the face falls away beneath it (one clean step, nothing to slide down)
drop = [snail_local(3600, TH_POSE + SWING * (1 - j / 12)) for j in range(13)]
UNDER = math.radians(5) * DIR
SNAIL_L = LOC[:720] + [rot(p, (0, 0), UNDER * j / 12) for j, p in enumerate(drop)]
rads = [math.hypot(*p) for p in LOC]
assert all(b > a for a, b in zip(rads, rads[1:])), 'snail radius must grow over the hour'
# pressure angle: between the nose's direction of travel and the cam's normal at the contact (kinematic only)
pa = []
for k in range(1, 720):
    a = A0 + omega * 3600 * k / 720; th_ = TH_POSE + SWING * k / 720
    tx, ty = LOC[k + 1][0] - LOC[k - 1][0], LOC[k + 1][1] - LOC[k - 1][1]
    tx, ty = tx * math.cos(a) - ty * math.sin(a), tx * math.sin(a) + ty * math.cos(a)
    vx, vy = -math.sin(th_), math.cos(th_)
    nl = math.hypot(tx, ty); cosn = abs(-ty * vx + tx * vy) / nl     # |normal . v|, normal = (-ty, tx)/|t|
    pa.append(math.degrees(math.acos(min(1, cosn))))
SNAIL_INFO = {'r_min': round(min(rads), 3), 'r_max': round(max(rads), 3), 'pressure_max': round(max(pa), 1), 'pressure_mean': round(sum(pa) / len(pa), 1)}
print('linear snail: r', SNAIL_INFO['r_min'], '->', SNAIL_INFO['r_max'], '| pressure angle max', SNAIL_INFO['pressure_max'], 'mean', SNAIL_INFO['pressure_mean'])
# pawl, ratchet, star (kick prototype numbers)
LK, GAMMA = 9.0, math.radians(-80)
th_mid = (th8 + th20) / 2; BETA = GAMMA - th_mid
def tip(th_): return polr(L, LK, th_ + BETA)
PITCH = 2 * math.pi / 12; GAP = math.radians(9)
SEAT0 = math.atan2(tip(th20)[1] - H[1], tip(th20)[0] - H[0]) + GAP      # steep face 9 deg ahead of the pawl at the top of the hour
# ---------- outlines ----------
def sdf_outline(d, step=2.0):
    cs = plt.contour(X, Y, d, levels=[0]); segs = cs.allsegs[0]; plt.close('all')
    def area(s_): return abs(sum(s_[i][0] * s_[(i + 1) % len(s_)][1] - s_[(i + 1) % len(s_)][0] * s_[i][1] for i in range(len(s_)))) / 2
    big = sorted(segs, key=area, reverse=True)
    from matplotlib.path import Path as MP_
    outer = MP_(np.array(big[0]))
    for s_ in big[1:]:
        if area(s_) > 1.0 and not outer.contains_point(tuple(s_[0])): raise SystemExit(f'outline has a separate piece of {area(s_):.1f} mm² near {tuple(round(float(v), 1) for v in np.mean(s_, axis=0))} (a boss cut off from its bridge?)')
    seg = big[0]; pts = [tuple(p) for p in seg]
    if math.dist(pts[0], pts[-1]) < 1e-6: pts = pts[:-1]
    cum = [0.0]
    for i in range(1, len(pts)): cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
    total = cum[-1] + math.dist(pts[-1], pts[0]); n = max(12, int(total / step)); out = []; j = 0
    for k in range(n):
        s = total * k / n
        while j < len(pts) - 1 and cum[j + 1] < s: j += 1
        a, b = pts[j], pts[(j + 1) % len(pts)]; seglen = math.dist(a, b) or 1e-9; t_ = (s - cum[j]) / seglen
        out.append((a[0] + (b[0] - a[0]) * t_, a[1] + (b[1] - a[1]) * t_))
    area = sum(out[i][0] * out[(i + 1) % n][1] - out[(i + 1) % n][0] * out[i][1] for i in range(n))
    if area < 0: out = out[::-1]
    return out
def dots(pts, smooth=True): return [{'u': round(x, 4), 'v': round(y, 4), 'smooth': smooth} for x, y in pts]
def circ_pts(c, r, n=None):
    n = n or max(16, int(2 * math.pi * r / 2.0)); return [pol(c, r, 360 * k / n) for k in range(n)]
SK, DR, MOUNTS, ENGRAVE = [], [], {}, {}
def add_part(name, pts, z, t, cuts=(), plane='z', smooth=True, grow='plus', mount=None, engrave=None, mill=None):
    kid = f'K{len(SK) + 1}'; did = f'D{len(DR) + 1}'
    SK.append({'id': kid, 'name': f'{name} outline', 'plane': {'axis': plane, 'offset': round(z, 4)}, 'closed': True, 'points': dots(pts, smooth) if pts and isinstance(pts[0], tuple) else pts})
    cl = [{'id': f'h{i + 1}', **c} for i, c in enumerate(cuts)]
    DR.append({'id': did, 'name': name, 'sketch': kid, 'thickness': round(t, 4), 'grow': grow, 'back': None, 'edges': None, **({'cuts': cl} if cl else {}), **({'mill': mill} if mill else {})})
    if mount: MOUNTS[did] = mount
    if engrave: ENGRAVE[did] = engrave
    return did
def cut(kind, name, d, at, depth=None, frm='front', seat=None, csk=None, axis=None):
    c = {'kind': kind, 'name': name, 'from': frm, 'depth': depth, 'seat': seat, 'csk': csk, 'at': rnd(at), 'd': d}
    if axis: c['axis'] = axis
    return c
BIG = dict(d=6.0, depth=2.5, seat={'d': 7.2, 'depth': 0.6})            # 3x6x2.5 flanged (barrel, centre)
SMALL = dict(d=3.0, depth=1.0)                                       # 681: 1x3x1 (light train, mechanism)
def brg(name, at, axis, big=False, frm='front', through=False):
    spec = BIG if big else SMALL
    if big and frm == 'front':   # in a 2.8 mm bridge milled from below the flange sits against the underside: the 1.9 mm body pocket leaves a 0.9 mm lip
        out = [cut('bearing', f'Bearing · {name} (3×6×2.5 flanged; the flange sits under the bridge)', spec['d'], at, 1.9, frm, None, None, axis)]
        through = through and True
    elif big:                    # milled from the top: the flange sits in a 0.6 mm seat, flush with the top face, over a bore right through
        out = [cut('bearing', f'Bearing · {name} (3×6×2.5 flanged; the flange in a seat flush with the top)', spec['d'], at, None, frm, spec.get('seat'), None, axis)]
        through = False
    else:
        out = [cut('bearing', f'Bearing · {name} ({"3×6×2.5" if big else "1×3×1"})', spec['d'], at, spec['depth'], frm, spec.get('seat'), None, axis)]
    if through: out.append(cut('clear', f'{name}: arbor through', 3.2 if big else 1.2, at, axis=axis))
    return out
def screw(name, at, frm='back'): return cut('screw', f'Screw · {name} (M2 countersunk)', 2.2, at, None, frm, None, {'d': 4.2})
def pilot(name, at, depth=3.0): return cut('pilot', f'Screw pilot · {name} (M2)', 1.6, at, depth, 'back')
# ---- levels (z, mm from the case back) ----
# Every plate and bridge is cut from Adam's acrylic sheet (1/2", 3/8", 1/4", 2.8 mm) and milled from one face on the Z1.
Z_PLATE, T_PLATE = 0.0, 12.7   # 1/2" main plate with a recess for every wheel; the bridges and the rim plates screw onto its top
Z_L2, T_L2 = 12.7, 2.8           # train bridges (2.8 mm sheet)
Z_MECH, T_MECH = 16.0, 1.6       # the cams: snail and hour ratchet
Z_LEV, T_LEV = 18.0, 1.2         # the retrograde lever (one piece with its rack) and the hand pinion; steel pins reach down from it to the cams
Z_STAR, T_STAR = 19.6, 1.2       # hour star, jumper, barrel ratchet and click
T_RIM = 9.525                    # rim plates (3/8") on the main plate carry the top level: no risers
Z_TOP, T_TOP = Z_PLATE + T_PLATE + T_RIM, 2.8    # crescent and hand cock (2.8 mm sheet), on the rim plates
Z_SET, T_SET = -6.35, 6.35       # setting plate (1/4") under the main plate
Z_KP, T_KP = Z_SET - 9.525, 9.525   # keyless plate (3/8") under the setting plate
PIN_R = 0.5                      # the lever's feeler and pawl are Ø1 steel pins
# ---------- fixed parts ----------
feet = {  # every foot screws into the main plate's solid rim (r 61.75 to 66) or an island between recesses
    'barrel': [DS.edge(55), DS.edge(112)], 'right': [DS.edge(45), DS.edge(-38)], 'bottom': [DS.edge(-62), DS.edge(232)],
    'crescent': None, 'handcock': None}
# recesses: each wheel's space plus 0.75 mm all round, cut from the top down to 0.5 mm under the wheel
TOPZ = Z_PLATE + T_PLATE
RECESS = [  # (name, centre, tip radius, bottom z, axis)
    ('barrel', B, 42 / 2 + 0.7, LV['s_bc'], 'barrel'), ('centre pinion', C, 6 + 1.3, LV['s_bc'], 'center'), ('centre wheel', C, 24 + 0.7, LV['s_ct'], 'center'),
    ('third pinion', T, 6 + 1.3, LV['s_ct'], 'third'), ('third wheel', T, 22.5 + 0.7, LV['s_ti'], 'third'),
    ('intermediate pinion', I, 6 + 1.3, LV['s_ti'], 'inter'), ('intermediate wheel', I, 24 + 0.7, LV['s_if'], 'inter'),
    ('seconds pinion', Fo, 6 + 1.3, LV['s_if'], 'fourth'), ('seconds wheel', Fo, 18 + 0.7, LV['s_fe'], 'fourth'),
    ('escape pinion', E, 6 + 1.3, LV['s_fe'], 'escape'), ('escape wheel', E, EG['R_TIP'], LV['escape_wheel'], 'escape'),
    ('pallet fork sweep', F, 10.6, LV['escape_wheel'], 'fork'), ('balance well', Bc, 18.75, 2.2, 'balance')]
plate_cuts = [cut('hole', f'Recess · {nm}', round(2 * (r + 0.75), 3), c_, round(TOPZ - (z - 0.5), 3), 'back', axis=ax) for nm, c_, r, z, ax in RECESS]
floor = {}
for nm, c_, r, z, ax in RECESS: floor[ax] = min(floor.get(ax, 99), z - 0.5)
for nm, p, ax, big in (('barrel', B, 'barrel', True), ('centre', C, 'center', True), ('third', T, 'third', False), ('intermediate', I, 'inter', False),
                       ('seconds', Fo, 'fourth', False), ('escape', E, 'escape', False), ('pallet fork', F, 'fork', False), ('balance', Bc, 'balance', False)):
    spec = BIG if big else SMALL
    plate_cuts.append(cut('bearing', f'Bearing · {nm} ({"3×6×2.5" if big else "1×3×1"}, at its recess floor)', spec['d'], p, round(TOPZ - floor[ax] + spec['depth'], 3), 'back', None, None, ax))
def floor_at(p):   # the plate's top surface at p: the lowest floor of the recesses over it (or the top face)
    return min([z - 0.5 for nm, c_, r, z, ax in RECESS if math.dist(p, c_) < r + 0.75] + [TOPZ])
plate_cuts += [cut('clear', 'Centre arbor through to the setting wheel', 3.2, C, None, 'back', axis='center'),
               cut('bearing', 'Bearing · keyless arbor (upper, 1×3×1, at the recess floor over it)', 3.0, K, round(TOPZ - floor_at(K) + 1.0, 3), 'back', None, None, 'keyless'),
               cut('clear', 'Keyless arbor through the plate', 1.2, K, None, 'back', axis='keyless')]
for grp in ('barrel', 'right', 'bottom'):
    for i, p in enumerate(feet[grp]): plate_cuts.append(pilot(f'{grp} foot {i + 1}', p, 4.0))
# ---- keyless works under the plate ----
# Two plates under the main plate hold it all, so its underside stays flat: the setting plate (1/4", milled from below) and the keyless
# plate (3/8", milled from the top). The stem lies on the face between them, half in a channel in each. Its 8-leaf winding pinion sits
# in a window in the setting plate and a pocket in the keyless plate and meshes 24 steel pins standing up from the pin wheel (on the
# keyless arbor), whose 12-leaf keyless pinion turns the setting wheel 48 on the centre arbor. One crown turn = 1/3 pin wheel turn = 5 min.
R_PIN, R_TIP = KG['R_PIN'], KG['R_TIP']; Z_STEM = Z_SET + KG['Z_STEM']     # keyless_geo.json is drawn with the stem at 0
X_P = K[0] + R_PIN                                   # the winding pinion's mid-plane (over the pin circle, on the crown side)
FW = 2.6                                             # pinion face width along the stem
STEM_X0, STEM_X1 = 55.2, 68.4                        # stem runs from the setting plate's opening to 2 mm into the crown
CROWN_X0 = 66.4
WIN = (X_P - FW / 2 - 0.4, X_P + FW / 2 + 0.4)       # the winding pinion's window (3.4 wide: a 1/8" end mill fits)
KSCREWS = [pol(K, 16.0, 60), pol(K, 16.0, -60)]      # M2 x 20 from below: through the keyless and setting plates into the main plate
PIN_Z0, PIN_T = Z_SET + KG['DISC_TOP'], KG['PIN_TIP'] - KG['DISC_TOP']
DISC_T = 1.6
def rect(x0, x1, y0, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
def pocket(name, pts, depth, frm='front', plane='z', offset=0.0):
    kid = f'K{len(SK) + 1}'
    SK.append({'id': kid, 'name': f'{name} (pocket outline)', 'plane': {'axis': plane, 'offset': round(offset, 4)}, 'closed': True, 'points': dots(pts, False)})
    return {'kind': 'pocket', 'name': name, 'from': frm, 'depth': depth, 'sketch': kid}
for i, p in enumerate(KSCREWS): plate_cuts.append(cut('pilot', f'Screw pilot · keyless plates {i + 1} (M2, drilled through; the screw comes up from below)', 1.6, p, None, 'back'))
# a side window onto the balance: a slot from the plate's edge into the balance well, cut from the top down to the well's floor;
# the crescent rim plate closes it above, so it reads as a window in the movement's side
WIN_Y = Bc[1]; SIDEWIN = rect(-67.0, Bc[0] - 12.0, WIN_Y - 4.0, WIN_Y + 4.0)
plate_cuts.append(pocket('Side window onto the balance (closed above by the crescent rim plate)', SIDEWIN, round(TOPZ - (2.2 - 0.5), 3), 'back'))
# thin fins between neighbouring recesses (closer than 0.8 mm) would snap in acrylic: cut each fin away down to the shallower recess's floor,
# so the two pockets merge there (a strip ±3.2 mm along the fin, reaching 1.5 mm into each pocket)
FINS = []
for i_, (n1, c1, r1, z1, a1) in enumerate(RECESS):
    for n2, c2, r2, z2, a2 in RECESS[i_ + 1:]:
        R1, R2 = r1 + 0.75, r2 + 0.75; dd = math.dist(c1, c2); gap = dd - R1 - R2
        if not (0 < gap < 0.8): continue
        u_ = ((c2[0] - c1[0]) / dd, (c2[1] - c1[1]) / dd); t_ = (-u_[1], u_[0]); mid = (c1[0] + u_[0] * (R1 + gap / 2), c1[1] + u_[1] * (R1 + gap / 2))
        hu, ht = gap / 2 + 1.5, 3.2
        quad = [(mid[0] + su * hu * u_[0] + st * ht * t_[0], mid[1] + su * hu * u_[1] + st * ht * t_[1]) for su, st in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        floor_ = max(z1, z2) - 0.5
        FINS.append((n1, n2, round(gap, 2)))
        plate_cuts.append(pocket(f'Fin removed between the {n1} and {n2} recesses (they were {gap:.2f} mm apart)', quad, round(TOPZ - floor_, 3), 'back'))
print('fins removed:', FINS)
# cusps: where two round recesses overlap, the plate between them ends in a knife edge at each crossing point. Cut each one back
# (down to the shallower floor) to where it is at least 1.0 mm wide.
def cusp_trim(c1, R1, c2, R2):
    d_ = math.dist(c1, c2); a_ = (d_ * d_ + R1 * R1 - R2 * R2) / (2 * d_); hh = math.sqrt(max(0.0, R1 * R1 - a_ * a_))
    u_ = ((c2[0] - c1[0]) / d_, (c2[1] - c1[1]) / d_); t_ = (-u_[1], u_[0]); base = (c1[0] + u_[0] * a_, c1[1] + u_[1] * a_)
    out = []
    for sg in (1, -1):
        X_ = (base[0] + sg * hh * t_[0], base[1] + sg * hh * t_[1]); b_ = (sg * t_[0], sg * t_[1])
        for s_ in np.arange(0.05, 8.0, 0.05):
            p_ = (X_[0] + b_[0] * s_, X_[1] + b_[1] * s_)
            def exit_(c, R, sgn):     # along +-u from p_, where the line meets circle (c, R)
                px, py = p_[0] - c[0], p_[1] - c[1]; B_ = px * u_[0] + py * u_[1]; C_ = px * px + py * py - R * R; disc = B_ * B_ - C_
                if disc < 0: return None
                r1_, r2_ = -B_ - math.sqrt(disc), -B_ + math.sqrt(disc); return max(r1_, r2_) if sgn < 0 else min(r1_, r2_)
            l1, l2 = exit_(c1, R1, -1), exit_(c2, R2, 1)
            width = (l2 - l1) if (l1 is not None and l2 is not None) else 99
            if width >= 1.0:
                if s_ >= 0.45: out.append((X_, s_ + 0.15))      # a cusp already that blunt needs nothing (and a tiny trim couldn't be milled)
                break
    return out
CUSPS = 0
for i_, (n1, c1, r1, z1, a1) in enumerate(RECESS):
    for n2, c2, r2, z2, a2 in RECESS[i_ + 1:]:
        if a1 == a2: continue                                  # the same arbor's pinion and wheel recesses are concentric
        R1, R2 = r1 + 0.75, r2 + 0.75; dd = math.dist(c1, c2)
        if not (abs(R1 - R2) < dd < R1 + R2): continue
        for X_, rho in cusp_trim(c1, R1, c2, R2):
            CUSPS += 1
            plate_cuts.append(cut('hole', f'Cusp trimmed where the {n1} and {n2} recesses cross', round(max(2 * rho, 3.3), 3), X_, round(TOPZ - (max(z1, z2) - 0.5), 3), 'back'))   # at least 3.3: a 1/8" end mill cuts it
print('cusps trimmed:', CUSPS)
# where three recesses cross, a small three-sided island of plate is left between them: cut the whole island out
# (down to the shallowest of the three floors) with one round cut that covers it
def circ_x(c1, R1, c2, R2):
    d_ = math.dist(c1, c2)
    if not (abs(R1 - R2) < d_ < R1 + R2): return []
    a_ = (d_ * d_ + R1 * R1 - R2 * R2) / (2 * d_); hh = math.sqrt(max(0.0, R1 * R1 - a_ * a_))
    u_ = ((c2[0] - c1[0]) / d_, (c2[1] - c1[1]) / d_); b_ = (c1[0] + u_[0] * a_, c1[1] + u_[1] * a_)
    return [(b_[0] - u_[1] * hh, b_[1] + u_[0] * hh), (b_[0] + u_[1] * hh, b_[1] - u_[0] * hh)]
REC = [(n, c_, r + 0.75, z - 0.5, ax) for n, c_, r, z, ax in RECESS]
ISLANDS = 0
for i_ in range(len(REC)):
    for j_ in range(i_ + 1, len(REC)):
        for k_ in range(j_ + 1, len(REC)):
            A_, B_, C_ = REC[i_], REC[j_], REC[k_]
            if len({A_[4], B_[4], C_[4]}) < 3: continue
            pts_ = []
            for (P1, P2, P3) in ((A_, B_, C_), (A_, C_, B_), (B_, C_, A_)):
                for X_ in circ_x(P1[1], P1[2], P2[1], P2[2]):
                    e_ = math.dist(X_, P3[1]) - P3[2]
                    if 0 < e_ < 3.0: pts_.append(X_)           # a crossing just outside the third recess: the island corner
            if len(pts_) < 2: continue
            cx_ = sum(p[0] for p in pts_) / len(pts_); cy_ = sum(p[1] for p in pts_) / len(pts_)
            rad_ = max(math.dist((cx_, cy_), p) for p in pts_) + 0.4
            if rad_ > 3.0: continue
            ISLANDS += 1
            plate_cuts.append(cut('hole', f'Island removed where the {A_[0]}, {B_[0]} and {C_[0]} recesses meet', round(max(2 * rad_, 3.3), 3), (cx_, cy_),
                                  round(TOPZ - max(A_[3], B_[3], C_[3]), 3), 'back'))
print('three-way islands removed:', ISLANDS)
# ---- screws for the rim plates and the parts on them (found on the drawn shapes, with a wall round each hole) ----
gx_ = X[0]; gy_ = Y[:, 0]
def sdf_at(sdf, p): return float(sdf[np.argmin(abs(gy_ - p[1])), np.argmin(abs(gx_ - p[0]))])
def plate_margin(p):   # distance from p to the nearest recess or the side window: solid full-height plate to screw into
    m = min(math.dist(p, c_) - (r + 0.75) for nm, c_, r, z, ax in RECESS)
    (x0_, y0_), (x1_, y1_) = SIDEWIN[0], SIDEWIN[2]
    dx = max(x0_ - p[0], 0, p[0] - x1_); dy = max(y0_ - p[1], 0, p[1] - y1_)
    m = min(m, math.hypot(dx, dy) if (dx or dy) else -1.0)
    return min(m, 66.0 - math.hypot(*p))
def find_spot(ang, conds, taken, r_lo=40, r_hi=64, spread=14, min_sep=6.0):
    best = None
    for rr in np.arange(r_lo, r_hi + 1e-9, 0.25):
        for da in np.arange(-spread, spread + 1e-9, 0.5):
            p = pol((0, 0), rr, ang + da)
            if any(math.dist(p, q) < min_sep for q in taken): continue
            m = min(f(p) for f in conds)
            if m < 0: continue
            score = abs(da) - 0.4 * min(m, 3.0)
            if best is None or score < best[0]: best = (score, p)
    if best is None: raise SystemExit(f'no room for a screw near {ang} deg')
    taken.append(best[1]); return best[1]
TAKEN = [p for g_ in ('barrel', 'right', 'bottom') for p in feet[g_]] + KSCREWS
feet['crescent'] = [find_spot(a_, [lambda p: -sdf_at(DS.crescent, p) - 2.4, lambda p: -sdf_at(DS.rim_left, p) - 2.4], TAKEN) for a_ in (125, 160, 196, 216)]
RIMSCREWS_L = [find_spot(a_, [lambda p: -sdf_at(DS.crescent, p) - 2.6, lambda p: -sdf_at(DS.rim_left, p) - 2.6, lambda p: plate_margin(p) - 2.6], TAKEN) for a_ in (142, 186, 206)]
feet['handcock'] = [find_spot(10, [lambda p: -sdf_at(DS.handcock, p) - 1.6, lambda p: -sdf_at(DS.rim_right, p) - 2.4], TAKEN, spread=6)]
RIMSCREWS_R = [find_spot(a_, [lambda p: -sdf_at(DS.rim_right, p) - 2.6, lambda p: plate_margin(p) - 2.6], TAKEN) for a_ in (28, 2)]
print('screws: crescent', [rnd(p, 1) for p in feet['crescent']], '| left rim', [rnd(p, 1) for p in RIMSCREWS_L], '| hand cock', [rnd(p, 1) for p in feet['handcock']], '| right rim', [rnd(p, 1) for p in RIMSCREWS_R])
for i, p in enumerate(RIMSCREWS_L): plate_cuts.append(pilot(f'crescent rim plate {i + 1}', p, 4.0))
for i, p in enumerate(RIMSCREWS_R): plate_cuts.append(pilot(f'right rim plate {i + 1}', p, 4.0))
# ---- towers: plate left standing between recesses that holds nothing up is cut down to the floor beside it ----
# Level by level from the top: a piece of plate at or above a level that is nowhere 5 mm wide and carries no screw is a tower;
# it comes down to the highest floor next to it (then it is looked at again on that level).
def plate_towers(cuts, h=0.05):
    from matplotlib.path import Path as MP_
    from scipy import ndimage
    xs_ = np.arange(-67, 67, h); GXt, GYt = np.meshgrid(xs_, xs_)
    body = np.hypot(GXt, GYt) <= 66.0
    def m_of(c):
        pts = [(q['u'], q['v']) for q in next(k for k in SK if k['id'] == c['sketch'])['points']] if c['kind'] == 'pocket' else circ_pts(c['at'], c['d'] / 2, 96)
        a_, b_ = np.min(pts, 0), np.max(pts, 0)
        ix0, ix1 = max(0, int((a_[0] + 67) / h) - 2), min(len(xs_), int((b_[0] + 67) / h) + 3)
        iy0, iy1 = max(0, int((a_[1] + 67) / h) - 2), min(len(xs_), int((b_[1] + 67) / h) + 3)
        m = np.zeros(body.shape, bool)
        m[iy0:iy1, ix0:ix1] = MP_(np.array(pts)).contains_points(np.c_[GXt[iy0:iy1, ix0:ix1].ravel(), GYt[iy0:iy1, ix0:ix1].ravel()]).reshape(iy1 - iy0, ix1 - ix0)
        return m
    top = np.where(body, TOPZ, -1.0)
    for c in cuts:
        if c.get('from') != 'back' or c.get('depth') is None or c['kind'] in ('pilot', 'bearing', 'clear', 'screw'): continue
        m = m_of(c) & body; top = np.where(m, np.minimum(top, TOPZ - c['depth']), top)
    orig = top.copy()
    keep = np.zeros(body.shape, bool)
    for c in cuts:
        if c['kind'] == 'pilot' and c.get('from') == 'back': keep |= np.hypot(GXt - c['at'][0], GYt - c['at'][1]) < 2.6
    n_t = 0
    for lev in sorted(set(np.round(top[body], 3)), reverse=True)[:-1]:
        mask = (top >= lev - 1e-6) & body
        core = ndimage.distance_transform_edt(mask) * h > 2.5
        lab, n = ndimage.label(mask)
        has = np.zeros(n + 1, bool); has[np.unique(lab[core | (keep & mask)])] = True
        for j in range(1, n + 1):
            if has[j]: continue
            sel = lab == j
            ring = ndimage.binary_dilation(sel, iterations=int(0.6 / h) + 1) & ~sel & body & (top < lev - 1e-6)
            top[sel] = float(top[ring].max()) if ring.any() else 0.0
            n_t += 1
    out = []
    for f in sorted(set(np.round(top[(top < orig - 1e-6) & body], 3))):
        R = (np.abs(top - f) < 1e-3) & (orig > f + 1e-6) & body
        R = R | (ndimage.binary_dilation(R, iterations=int(0.3 / h)) & (top <= f + 1e-6) & body)
        cs_ = plt.contour(GXt, GYt, R.astype(float), levels=[0.5]); segs_ = cs_.allsegs[0]; plt.close('all')
        for sg in segs_:
            sg = np.asarray(sg)
            if len(sg) < 8: continue
            ar = 0.5 * abs(np.dot(sg[:, 0], np.roll(sg[:, 1], 1)) - np.dot(sg[:, 1], np.roll(sg[:, 0], 1)))
            if ar < 0.5: continue
            pts = [tuple(sg[0])]
            for q in sg[1:]:
                if math.dist(q, pts[-1]) >= 0.15: pts.append(tuple(q))
            out.append((pts, round(TOPZ - f, 3), round(ar, 1), tuple(round(float(v), 1) for v in sg.mean(0))))
    return out, n_t
TOWERS, N_TOW = plate_towers(plate_cuts)
for pts, dep, ar, at in TOWERS:
    plate_cuts.append(pocket(f'Tower removed near ({at[0]}, {at[1]}): plate between recesses that held nothing up', pts, dep, 'back'))
print('towers found', N_TOW, '-> pockets', [(t[3], t[1], t[2]) for t in TOWERS])
D_PLATE = add_part('Main plate', circ_pts((0, 0), 66.0, 104), Z_PLATE, T_PLATE, plate_cuts, mill='back')
from matplotlib.path import Path as _MP
def bridge(name, sdf, bearings, screws_at, extra=(), mill='front'):
    pts = sdf_outline(sdf); cuts_ = list(bearings) + [screw(f'{name} foot {i + 1}', p) for i, p in enumerate(screws_at)] + list(extra)
    path = _MP(np.array(pts + [pts[0]]))
    for c_ in cuts_:
        if not path.contains_point(c_['at']): raise SystemExit(f'{name}: {c_["name"]} sits outside the bridge (nothing to hold it)')
    return add_part(name, pts, Z_L2, T_L2, cuts_, mill=mill)
D_BARREL = bridge('Barrel bridge', DS.barrel, brg('barrel', B, 'barrel', True, through=True), feet['barrel'])
STUD_SPRING = (47.5, 15.5); STUD_STOP = None
# the right bridge carries two lower bearings (the hand and hour arbors stand on it), so it is milled from the top: every bearing from the top
D_RIGHT = bridge('Right bridge', DS.mech, brg('centre (upper)', C, 'center', True, frm='back') + brg('third (upper)', T, 'third', frm='back', through=True) +
                 brg('hand arbor (lower)', Q, 'retro', frm='back') + brg('hour star (lower)', H, 'hourstar', frm='back') +
                 [cut('hole', 'Lever stud (1 mm steel pin, pressed)', 1.0, L), cut('hole', 'Return spring stud (1 mm)', 1.0, STUD_SPRING)], feet['right'], mill='back')
JSTUD = (14.0, -33.5)
D_BOTTOM = bridge('Bottom bridge', DS.train, brg('intermediate (upper)', I, 'inter') + brg('seconds (upper)', Fo, 'fourth', through=True) + brg('escape (upper)', E, 'escape') + brg('pallet fork (upper)', F, 'fork') + [cut('hole', 'Jumper stud (1 mm)', 1.0, JSTUD)], feet['bottom'])
# crescent with its balance cock, the minute track engraved on it
TRACK0 = TRACK0_PRE; SWEEP = round(3 * math.degrees(SWING), 3); TRACK1 = TRACK0 - SWEEP
cres_pts = sdf_outline(DS.crescent, 2.0)
D_CRES = add_part('Crescent', cres_pts, Z_TOP, T_TOP, brg('balance (upper)', Bc, 'balance', frm='back', through=True) + [screw(f'crescent {i + 1}, into the rim plate', p) for i, p in enumerate(feet['crescent'])], mill='back',
                  engrave=[{'kind': 'arc', 'c': rnd(Q), 'r': round(DS.RI + 0.9, 3), 'a0': TRACK0, 'a1': round(TRACK1, 3), 'n': 60, 'major': 5, 'len': [1.6, 3.3],
                            'labels': {'0': '0', '15': '15', '30': '30', '45': '45', '60': '60'}, 'rl': round(DS.RI + 6.6, 3), 'size': 2.6},
                           {'kind': 'text', 'at': rnd(pol((0, 0), 57.0, 186)), 'text': 'C R E S C E N T', 'size': 1.9, 'angle': 96.0},
                           {'kind': 'text', 'at': rnd(pol((0, 0), 57.2, 166)), 'text': 'BSPK · CALIBRE 01', 'size': 1.6, 'angle': 76.0}])
# the rim plates (3/8"), on the main plate: the crescent and the hand cock screw onto them, so nothing stands on a riser
def multi_outline(d, min_area=0.4):   # every closed piece of a field's zero contour, as dots (for pockets that come in several pieces)
    cs_ = plt.contour(X, Y, d, levels=[0]); segs_ = cs_.allsegs[0]; plt.close('all'); out = []
    for sg in segs_:
        sg = np.asarray(sg)
        if len(sg) < 6: continue
        ar = 0.5 * abs(np.dot(sg[:, 0], np.roll(sg[:, 1], 1)) - np.dot(sg[:, 1], np.roll(sg[:, 0], 1)))
        if ar < min_area: continue
        pts = [tuple(sg[0])]
        for q in sg[1:]:
            if math.dist(q, pts[-1]) >= 0.3: pts.append(tuple(q))
        out.append(pts)
    return out
def straddle(rim_sdf, name):   # where a bridge's foot runs under the rim plate: a pocket in the plate's underside, 0.1 deeper than the bridge
    out = []
    for bn, bsdf in (('barrel bridge', DS.barrel), ('right bridge', DS.mech), ('bottom bridge', DS.train)):
        for k_, pts in enumerate(multi_outline(np.maximum(rim_sdf - 1.0, bsdf - 0.5))):   # runs 1 mm past the plate's edge, so no sliver is left along it
            out.append(pocket(f'Clears the {bn}\'s foot (the rim plate sits over it)', pts, round(T_L2 + 0.1, 3), 'front'))
    return out
rimL_pts = sdf_outline(DS.rim_left, 1.5)
D_RIML = add_part('Crescent rim plate (3/8", under the crescent)', rimL_pts, Z_PLATE + T_PLATE, T_RIM,
                  straddle(DS.rim_left, 'left') + [cut('pilot', f'Screw pilot · crescent {i + 1} (M2, drilled through)', 1.6, p, None, 'back') for i, p in enumerate(feet['crescent'])] +
                  [screw(f'crescent rim plate {i + 1}', p) for i, p in enumerate(RIMSCREWS_L)], mill='front')
rimR_pts = sdf_outline(DS.rim_right, 1.5)
D_RIMR = add_part('Right rim plate (3/8", under the hand cock)', rimR_pts, Z_PLATE + T_PLATE, T_RIM,
                  straddle(DS.rim_right, 'right') + [cut('pilot', 'Screw pilot · hand cock (M2, drilled through)', 1.6, feet['handcock'][0], None, 'back')] +
                  [screw(f'right rim plate {i + 1}', p) for i, p in enumerate(RIMSCREWS_R)], mill='front')
# hand cock: carries the hand arbor and the hour star on top; its spur is the hour index (pointing at the star's top)
IDX = 90.0
hc = U(DS.handcock, curve(bez((51.0, -3.5), (50.5, 2.5), (45.0, 4.0), pol(H, 15.4, IDX), 24), 1.1, 0.32), k=1.5)   # the index: a spur pointing at the star's top number from outside
D_HC = add_part('Hand cock', sdf_outline(hc, 1.6), Z_TOP, T_TOP, brg('hand arbor (upper)', Q, 'retro', through=True) + brg('hour star (upper)', H, 'hourstar') + [screw('hand cock, into the right rim plate', feet['handcock'][0])], mill='front')
# keyless works in two plates under the main plate: the setting plate (milled from below) and the keyless plate (milled from the top)
ky = K[1]
k_strip = curve([(X_P - 2.0, ky), (70.0, ky)], 4.0)
S_sdf = smax(smax(smax(U(circle(K, 19.5), k_strip, k=2.0), circle((0, 0), 65.9), 0.5), -circle(C, 25.7), 0.6), -circle(K, 8.05), 0.6)   # a C round the keyless pinion, clear of the setting wheel
K_sdf = smax(U(circle(K, 19.5), k_strip, k=2.0), circle((0, 0), 65.9), 0.5)
CH = rect(55.0, 66.5, ky - 1.05, ky + 1.05)                                       # the stem's channel: 1.05 deep in each plate
def stadium(c, half_w, half_l, n=12):   # a slot along y with round ends (no square corners: a 1/8" end mill cuts it to full depth)
    out = []
    for j in range(n + 1): t_ = math.pi * j / n; out.append((c[0] + half_w * math.cos(t_), c[1] + half_l - half_w + half_w * math.sin(t_)))
    for j in range(n + 1): t_ = math.pi + math.pi * j / n; out.append((c[0] + half_w * math.cos(t_), c[1] - half_l + half_w + half_w * math.sin(t_)))
    return out
# the winding pinion seen from above is 2.6 x 9.6: a round-ended slot 3.4 wide, long enough that its corners sit 0.3 inside the ends
WIN_SLOT = stadium(((WIN[0] + WIN[1]) / 2, ky), (WIN[1] - WIN[0]) / 2, R_TIP + 1.2)   # end centres 4.32 out: the pinion's corners clear the round ends by 0.3
add_part('Setting plate (1/4", under the main plate)', sdf_outline(S_sdf, 1.0), Z_SET, T_SET,
         [pocket('Stem channel, upper half (from the underside)', CH, 1.05, 'front'),
          pocket('Window for the winding pinion (through, round ends)', WIN_SLOT, None)] +
         [cut('hole', f'Screw · keyless plates {i + 1} (M2 clearance)', 2.2, p) for i, p in enumerate(KSCREWS)], mill='front')
PW_FLOOR = PIN_Z0 - DISC_T - 0.5                                                   # 0.5 under the pin wheel's disc
add_part('Keyless plate (3/8", under the setting plate)', sdf_outline(K_sdf, 1.0), Z_KP, T_KP,
         [cut('hole', 'Recess · pin wheel and its pins', 2 * (12.5 + 0.75), K, round(Z_SET - PW_FLOOR, 3), 'back', axis='keyless'),
          pocket('Winding pinion pocket (lower half, round ends)', WIN_SLOT, round(R_TIP + 0.4, 3), 'back'),
          pocket('Stem channel, lower half', CH, 1.05, 'back'),
          cut('bearing', 'Bearing · keyless arbor (lower, 1×3×1, at the recess floor)', 3.0, K, round(Z_SET - PW_FLOOR + 1.0, 3), 'back', None, None, 'keyless')] +
         [cut('screw', f'Screw · keyless plates {i + 1} (M2 × 20 from below; countersink by hand)', 2.2, p, None, 'front', None, {'d': 4.2}) for i, p in enumerate(KSCREWS)], mill='back')
# 24 steel pins (Ø1) pressed into the pin wheel, standing 2 mm proud: one outline of 24 circles joined by out-and-back hairlines
pins_pts, inner = [], []
for k in range(24):
    c_ = pol(K, R_PIN, 15 * k); a_in = 15 * k + 180
    ring = [pol(c_, 0.5, a_in + 360 * j / 16) for j in range(17)]
    pins_pts += ring; inner.append(ring[0])
pins_pts += inner[::-1][1:]
add_part('Pin wheel pins (24 × Ø1 steel)', pins_pts, PIN_Z0, PIN_T, smooth=False, mount={'axis': 'keyless'})
# stem, winding pinion and crown turn about the stem's axis: 3 turns for every turn of the pin wheel
SPIN = {'axisX': [round(K[1], 4), Z_STEM], 'from': 'keyless', 'ratio': round(R_PIN / KG['R_P'], 6)}
add_part('Winding stem (Ø2 steel, flat for the pinion and crown)', circ_pts((K[1], Z_STEM), 1.0, 24), STEM_X0, STEM_X1 - STEM_X0, plane='x', smooth=False, mount=dict(SPIN))
wp_pts = [(K[1] + u, Z_STEM + v) for u, v in KG['pinion_outer']]
add_part('Winding pinion (8 leaves, on the stem)', wp_pts, X_P - FW / 2, FW, [pocket('D bore for the stem', [(K[1] + u, Z_STEM + v) for u, v in KG['pinion_bore']], None, plane='x', offset=X_P - FW / 2)],
         plane='x', smooth=False, mount=dict(SPIN))
crown = [(K[1] + 4.2 * math.cos(math.radians(7.5 + 15 * k)) * (1 if k % 2 == 0 else 0.93), Z_STEM + 4.2 * math.sin(math.radians(7.5 + 15 * k)) * (1 if k % 2 == 0 else 0.93)) for k in range(24)]
add_part('Crown', crown, CROWN_X0, 5.0, plane='x', smooth=False, mount=dict(SPIN))
# stop pin for the lever, and the return spring's stud
# ---------- moving drawn parts ----------
th_snail = th_snail_pose
def shrink(poly_local, r, h=0.015):
    from scipy import ndimage
    from matplotlib.path import Path as MP_
    P_ = np.array(poly_local); ext = np.abs(P_).max() + 1.0
    gg = np.arange(-ext, ext + h, h); GX, GY = np.meshgrid(gg, gg)
    ins = MP_(P_).contains_points(np.c_[GX.ravel(), GY.ravel()]).reshape(GX.shape)
    sdf = ndimage.distance_transform_edt(~ins) * h - ndimage.distance_transform_edt(ins) * h
    cs_ = plt.contour(GX, GY, sdf, levels=[-r]); seg_ = max(cs_.allsegs[0], key=len); plt.close('all')
    out = [seg_[0]]
    for q in seg_[1:]:
        if math.dist(q, out[-1]) >= 0.08: out.append(q)
    return [(float(x), float(y)) for x, y in out]
SNAIL_CAM = shrink(SNAIL_L, PIN_R)     # the feeler pin's centre runs on SNAIL_L; the cam's edge is a pin's radius inside it
D_SNAIL = add_part('Snail (minute cam)', [rot((C[0] + x, C[1] + y), C, th_snail) for x, y in SNAIL_CAM],
                   Z_MECH, T_MECH, [cut('hole', 'Bore (pressed on the centre arbor)', 3.0, C)], smooth=False, mount={'axis': 'center'})
# retrograde lever at its pose: boss, feeler (nose), rack sector (36 teeth, module 1) toward the hand pinion, pawl, spring lug, stop tail
nose_p = nose(TH_POSE); a_LQ = math.atan2(Q[1] - L[1], Q[0] - L[0])
def sector_teeth(c, z, m, a_from, a_to):
    rp = m * z / 2; ra = rp + m * 0.7; rf = rp - 1.15 * m; pts = []; p = 2 * math.pi / z
    k0 = math.floor(a_from / p); k1 = math.ceil(a_to / p)
    for k in range(k0, k1 + 1):
        a = k * p
        pts += [polr(c, rf, a - 0.5 * p), polr(c, rf, a - 0.27 * p), polr(c, ra, a - 0.13 * p), polr(c, ra, a + 0.13 * p), polr(c, rf, a + 0.27 * p)]
    return pts
# sector spans the contact direction over the swing (the sector turns with the lever; the contact stays toward Q)
s_from = a_LQ - SWING - math.radians(9); s_to = a_LQ + math.radians(9)
# The rack is a sector of a 36-tooth involute wheel (module 1) meshing the hand pinion (12, shift +0.3). The arbors are 23.952 apart, not the
# 24.3 a standard sector would need, so the sector is shifted -0.40: it meshes there with a little backlash and 0.3 mm tip clearance both ways.
import gearing as GR
G_SEC = GR.compute(1.0, 36, -0.40); G_HP = GR.compute(1.0, 12, 0.3)
HP_OFF = math.radians(TRACK0_PRE - 90)                      # the hand pinion's turn at the pose (the minute hand points at the track's 0)
hp_local = GR.outline(G_HP)
def hp_at(lam): return GR.place(hp_local, Q, HP_OFF - 3 * lam)          # lever turned lam (rad): the pinion turns 3x the other way
k0 = math.floor(s_from / G_SEC['step']) - 1; k1 = math.ceil(s_to / G_SEC['step']) + 1
def sector_poly(psi):
    pts = [p for i in range(k0, k1 + 1) for p in GR.tooth(G_SEC, i)]
    a_end = (k1 + 1) * G_SEC['step'] - G_SEC['root_half']; a_start = k0 * G_SEC['step'] - G_SEC['half']
    pts += [(11.5 * math.cos(a_end - (a_end - a_start) * j / 16), 11.5 * math.sin(a_end - (a_end - a_start) * j / 16)) for j in range(17)]
    return GR.place(pts, L, psi)
# phase the teeth to the pinion: the middle of the range of phases that mesh at the pose
ok_ps = [ps for ps in np.arange(0, G_SEC['step'], math.radians(0.05)) if not GR.overlaps(sector_poly(ps), hp_at(0.0))]
runs, cur = [], [ok_ps[0]]
for a_, b_ in zip(ok_ps, ok_ps[1:]):
    if b_ - a_ < math.radians(0.06): cur.append(b_)
    else: runs.append(cur); cur = [b_]
runs.append(cur); best_run = max(runs, key=len)
if len(runs) > 1 and abs(runs[0][0]) < 1e-9 and abs(runs[-1][-1] - (G_SEC['step'] - math.radians(0.05))) < 1e-6:   # the free band wraps round
    best_run = runs[-1] + [x + G_SEC['step'] for x in runs[0]] if len(runs[-1]) + len(runs[0]) > len(best_run) else best_run
PSI_SEC = (best_run[0] + best_run[-1]) / 2
sector = [tuple(p) for p in sector_poly(PSI_SEC)]
# prove it over the whole swing (and a little past): never overlapping, and always within a small turn of driving either way
def free(lam, sgn, lim=math.radians(6), stp=math.radians(0.05)):
    d = 0.0; S_ = sector_poly(PSI_SEC + lam)
    while d < lim:
        d += stp
        if GR.overlaps(S_, GR.place(hp_local, Q, HP_OFF - 3 * lam + sgn * d)): return d
    return None
rack_int, back = [], []
for lam in np.arange(math.radians(-1), SWING + math.radians(1), math.radians(0.25)):
    if GR.overlaps(sector_poly(PSI_SEC + lam), hp_at(lam)): rack_int.append(round(math.degrees(lam), 2))
    f_, b_ = free(lam, 1), free(lam, -1); back.append((f_, b_))
RACK_PROOF = {'interference_at_lever_deg': rack_int, 'drives_both_ways': all(f_ and b_ for f_, b_ in back),
              'pinion_play_deg': [round(math.degrees(min(f_ + b_ for f_, b_ in back if f_ and b_)), 2), round(math.degrees(max(f_ + b_ for f_, b_ in back if f_ and b_)), 2)] if back else None,
              'tip_clearance_mm': [round((math.dist(L, Q) - G_HP['ra']) - G_SEC['rf'], 3), round((math.dist(L, Q) - G_SEC['ra']) - G_HP['rf'], 3)]}
print('rack and hand pinion:', RACK_PROOF)
tip_p = tip(TH_POSE)
lug = polr(L, 9.5, TH_POSE + math.radians(118))
from matplotlib.path import Path as MPath
def lever_outline(h=0.015):
    from scipy import ndimage
    pts_ = np.array([L, nose_p, tip_p, lug] + sector); x0_, y0_ = pts_.min(0) - 2.5; x1_, y1_ = pts_.max(0) + 2.5
    GX, GY = np.meshgrid(np.arange(x0_, x1_, h), np.arange(y0_, y1_, h))
    def c_(c, r): return np.hypot(GX - c[0], GY - c[1]) - r
    def tap(a, b, r0, r1):
        a = np.asarray(a); b = np.asarray(b); d = b - a; L2 = (d * d).sum()
        t = np.clip(((GX - a[0]) * d[0] + (GY - a[1]) * d[1]) / L2, 0, 1)
        return np.hypot(GX - (a[0] + t * d[0]), GY - (a[1] + t * d[1])) - (r0 + (r1 - r0) * t)
    def sm(a, b, k=0.8):
        hh = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - hh) + a * hh - k * hh * (1 - hh)
    body = c_(L, 4.2)
    body = sm(body, tap(L, nose_p, 1.6, 0.85)); body = sm(body, c_(nose_p, 1.3), 0.4)                 # the arm out over the snail to the feeler pin
    body = sm(body, tap(L, tip_p, 1.3, 0.45)); body = sm(body, c_(tip_p, 1.3), 0.3)                    # the pawl blade (a flexure) to the pawl pin
    body = sm(body, tap(L, lug, 1.5, 1.2)); body = sm(body, c_(lug, 1.3), 0.4)                         # the spring's lug
    body = sm(body, tap(L, polr(L, 13.0, a_LQ - SWING / 2), 2.4, 2.0))                                  # the arm out to the rack
    ins = MPath(np.array(sector)).contains_points(np.c_[GX.ravel(), GY.ravel()]).reshape(GX.shape)   # the rack, exact
    sec = ndimage.distance_transform_edt(~ins) * h - ndimage.distance_transform_edt(ins) * h
    allf = sm(body, sec, 0.6)
    cs_ = plt.contour(GX, GY, allf, levels=[0]); segs_ = sorted(cs_.allsegs[0], key=len, reverse=True); plt.close('all')
    big_ = [s_ for s_ in segs_ if len(s_) > 20]
    outer_ = MPath(segs_[0])
    for s_ in big_[1:]:
        if not outer_.contains_point(tuple(s_[0])): raise SystemExit('lever outline came apart: a piece is not joined to the hub')
    seg_ = segs_[0]; out = [seg_[0]]
    for q in seg_[1:]:
        if math.dist(q, out[-1]) >= 0.04: out.append(q)
    return [(float(x), float(y)) for x, y in out]
D_LEVER = add_part('Retrograde lever (rack, feeler arm, pawl blade)', lever_outline(), Z_LEV, T_LEV,
                   [cut('bearing', 'Bearing · lever (1×3×1) on its stud', 3.0, L), cut('hole', 'Feeler pin (Ø1, pressed)', 1.0, nose_p), cut('hole', 'Pawl pin (Ø1, pressed)', 1.0, tip_p)],
                   smooth=False, mount={'pivot': rnd(L), 'angle': 'lever'})
LPIN_Z0 = Z_MECH + 0.1
D_FEELER = add_part('Feeler pin (Ø1 steel, rides the snail)', circ_pts(nose_p, PIN_R, 24), LPIN_Z0, Z_LEV + T_LEV - LPIN_Z0, smooth=False, mount={'pivot': rnd(L), 'angle': 'lever'})
D_PAWLPIN = add_part('Pawl pin (Ø1 steel, kicks the hour ratchet)', circ_pts(tip_p, PIN_R, 24), LPIN_Z0, Z_LEV + T_LEV - LPIN_Z0, smooth=False, mount={'pivot': rnd(L), 'angle': 'lever'})
# hour ratchet: 12 teeth, radial steep face, back slope falling over 80 % of the pitch
rat = []
for k in range(12):
    a0 = SEAT0 + PITCH * k
    rat += [polr(H, 8.0, a0 - 1e-3), polr(H, 11.0, a0), polr(H, 8.0, a0 + 0.8 * PITCH)] + [polr(H, 8.0, a0 + 0.8 * PITCH + 0.2 * PITCH * j / 4) for j in range(1, 4)]
D_RAT = add_part('Hour ratchet (kicked by the pawl)', rat, Z_MECH, T_MECH, [cut('hole', 'Bore', 1.0, H)], smooth=False, mount={'pivot': rnd(H), 'angle': 'hour'})
# hour star: 12 points, '12' under the index at the pose, numbers increase clockwise (the star steps anticlockwise)
star = []
for k in range(24):
    a = math.radians(IDX) + math.pi * k / 12; star.append(polr(H, 14.5 if k % 2 == 0 else 10.2, a))
numerals = []
for j in range(12):
    a = IDX - 30 * j; numerals.append({'kind': 'text', 'at': rnd(pol(H, 11.2, a)), 'text': str(j if j else 12), 'size': 2.6, 'angle': round(a - IDX, 3), 'weight': 700})
D_STAR = add_part('Hour star', star, Z_STAR, T_STAR, [cut('hole', 'Bore', 1.0, H)], smooth=False, mount={'pivot': rnd(H), 'angle': 'hour'}, engrave=numerals)
# jumper: a long thin spring from its stud on the bottom bridge round to a V nose in the star's valley at IDX + 75 deg (165 deg)
PSI_J = math.radians(IDX + 75); nose_j = polr(H, 10.4, PSI_J)
jpath = bez(JSTUD, (16.0, -22.0), (24.0, -15.0), nose_j, 30)
j_sdf = U(curve(jpath, 0.9, 0.6), circle(JSTUD, 2.2), k=1.2)
D_JUMP = add_part('Jumper (hour star detent)', sdf_outline(j_sdf, 0.8), Z_STAR, T_STAR, [cut('hole', 'Stud', 1.0, JSTUD)], smooth=False,
                  mount={'pivot': rnd(JSTUD), 'angle': 'jumper'})
# barrel ratchet and click on the barrel bridge (the click blocks reverse turning)
brat = []
# teeth face the running direction (the barrel turns clockwise): the click rides up each gentle back slope and drops off the steep face;
# turned backwards the steep faces drive the click deeper in, so the train (and the snail's cliff) can't be driven in reverse
BP = 2 * math.pi / 30
for k in range(30):
    a0 = BP * k
    brat += [polr(B, 10.6, a0), polr(B, 12.0, a0 + 0.85 * BP), polr(B, 10.6, a0 + 0.85 * BP + 0.02)]
D_BRAT = add_part('Barrel ratchet', brat, Z_STAR, 1.2, [cut('hole', 'Square', 3.0, B)], smooth=False, mount={'axis': 'barrel'})
CLK = pol(B, 16.5, 150); click_nose = pol(B, 11.0, 125)
# a hooked click: the blade stays outside the teeth's tips and a short beak drops in to the nose, so only the nose ever touches a tooth
CLK_ELBOW = pol(B, 13.6, 131)
c_sdf = U(curve([CLK, CLK_ELBOW], 1.3, 0.75), curve([CLK_ELBOW, click_nose], 0.75, 0.55), circle(CLK, 2.0), k=0.6)
D_CLICK = add_part('Click', sdf_outline(c_sdf, 0.3), Z_STAR, 1.2, [cut('hole', 'Click screw', 1.6, CLK)], smooth=False, mount={'pivot': rnd(CLK), 'angle': 'click'})
# ---- the click's logic, from the drawn shapes: running forward every face that pushes its nose must lift it (it rides);
# turned backwards the steep face it meets must drive it deeper (it locks), so the snail's cliff can never be driven into the lever ----
def click_logic(ratchet, centre, pivot, nose0, run_sign, nose_r=0.0):
    R = [np.array(p) for p in ratchet]; n_ = len(R)
    def placed_pts(theta): return np.array([rot(tuple(q), centre, theta) for q in R])
    def nose_at(phi): return np.array(rot(nose0, pivot, phi))
    out_dir = np.array(nose0) - np.array(centre); out_dir /= np.linalg.norm(out_dir)
    m_ = nose_at(1e-4) - nose_at(-1e-4); lift_sign = 1 if m_ @ out_dir > 0 else -1     # which way of turning lifts the nose off the wheel
    def seg_dist(p, theta):
        pts = placed_pts(theta); a_ = pts; b_ = np.roll(pts, -1, 0); d = b_ - a_
        t = np.clip(((p - a_) * d).sum(1) / (d * d).sum(1), 0, 1); return np.sqrt(((p - (a_ + d * t[:, None])) ** 2).sum(1)).min()
    def inside(p, theta): return _MP(placed_pts(theta)).contains_point(tuple(p)) or (nose_r > 0 and seg_dist(p, theta) < nose_r)
    def rest_phi(theta, lo=-0.6, hi=0.6):         # the spring holds the nose down: lowest lift with the nose clear of the wheel
        a, b = (-lift_sign * 0.6, lift_sign * 0.6)
        if not inside(nose_at(a), theta): return a
        for _ in range(40):
            mm = (a + b) / 2
            if inside(nose_at(mm), theta): a = mm
            else: b = mm
        return b
    def contact(theta, phi):
        p = nose_at(phi); pts = placed_pts(theta); best = None
        for i in range(n_):
            a_, b_ = pts[i], pts[(i + 1) % n_]; d = b_ - a_; t = max(0, min(1, (p - a_) @ d / (d @ d))); q = a_ + d * t; dist = np.linalg.norm(p - q)
            if best is None or dist < best[0]: best = (dist, a_, b_, q)
        _, a_, b_, q = best
        if nose_r > 0 and np.linalg.norm(p - q) > 1e-9: nrm = (p - q) / np.linalg.norm(p - q)   # a round nose: the push is along the line to its centre
        else:
            d = b_ - a_; nrm = np.array([d[1], -d[0]]) / np.linalg.norm(d)
            if _MP(placed_pts(theta)).contains_point(tuple(q + nrm * 0.02)): nrm = -nrm   # point it out of the wheel
        lift = nose_at(phi + lift_sign * 1e-4) - nose_at(phi - lift_sign * 1e-4); lift /= np.linalg.norm(lift)
        return q, nrm, lift
    pitch = 2 * math.pi / 30
    ride_min, lock_min, lifted = 9.0, None, 0
    phi = rest_phi(0.0)
    for k in range(1, 721):                        # one tooth forward in fine steps
        th = run_sign * pitch * k / 720; new = rest_phi(th)
        if (new - phi) * lift_sign > 1e-7:         # the wheel is pushing the nose up here
            q, nrm, lift = contact(th, new); lifted += 1
            ride_min = min(ride_min, float(nrm @ lift))
        phi = new
    # backwards from where the nose rests: the first face that comes against it, and which way it pushes
    phi = rest_phi(0.0)
    for k in range(1, 1441):
        th2 = -run_sign * pitch * k / 720
        if inside(nose_at(phi), th2):
            q, nrm, lift = contact(th2, phi); lock_min = float(nrm @ lift); break
    return {'ride_min': round(ride_min, 3), 'pressure_max_deg': round(math.degrees(math.acos(max(-1, min(1, ride_min)))), 1), 'lock': None if lock_min is None else round(lock_min, 3), 'lifted_samples': lifted}
CLICK_PROOF = click_logic(brat, B, CLK, click_nose, -1, 0.55)   # the barrel turns clockwise; the click's nose is round, r 0.55
print('click logic:', CLICK_PROOF)
# barrel cover with the mainspring cut through it: a 1 mm disc set into the drum's top; a spiral slot (1.1 wide, a 1 mm end mill's pass)
# leaves a 1.1 mm strip coiling 6 1/2 turns from the arbor hub to the drum wall, which reads as the blued mainspring over the gold barrel
SPR_R0, SPR_R1, SPR_P, SPR_W = 3.6, 17.5, 2.2, 1.1
def spiral_slot(c, r0, r1, p, w, n_per_turn=96):
    turns = (r1 - r0) / p; n = int(turns * n_per_turn) + 1
    cl = [(r0 + p * t, 2 * math.pi * t) for t in (turns * k / (n - 1) for k in range(n))]
    outer = [pol(c, r + w / 2, math.degrees(a)) for r, a in cl]; inner = [pol(c, r - w / 2, math.degrees(a)) for r, a in cl]
    end_cap = [pol(pol(c, cl[-1][0], math.degrees(cl[-1][1])), w / 2, math.degrees(cl[-1][1]) - 180 * j / 8) for j in range(1, 8)]
    start_cap = [pol(pol(c, cl[0][0], math.degrees(cl[0][1])), w / 2, math.degrees(cl[0][1]) + 180 + 180 * j / 8) for j in range(1, 8)]
    return outer + end_cap + inner[::-1] + start_cap
D_SPRING = add_part('Barrel cover (mainspring cut through)', circ_pts(B, 18.4, 120), 10.9, 1.0,   # its top at the drum's top (11.9), 0.5 under the bearing flange
                    [cut('clear', 'Arbor through', 3.2, B), pocket('Mainspring slot (spiral, 1.1 wide, through)', spiral_slot(B, SPR_R0, SPR_R1, SPR_P, SPR_W), None)],
                    smooth=False, mount={'axis': 'barrel'})
# pallet fork: see the escapement block below
# escapement (escapement.py): the escape wheel's 15 ramp teeth lift the fork's two noses in turn, so the wheel rocks the fork both ways
# with no spring and no lock; the fork's slot holds the balance's impulse pin, so the balance swings with it (tick, pause, tock, pause)
Z_ESC, T_ESC = LV['escape_wheel'], 2.0      # escape wheel and fork 2 mm Delrin: more face on every contact
D_EWHEEL = add_part('Escape wheel (15 ramp teeth)', [(E[0] + x, E[1] + y) for x, y in EG['wheel_local']], Z_ESC, T_ESC,
                    [cut('hole', 'Bore (pressed on the escape arbor)', 1.0, E)], smooth=False, mount={'axis': 'escape'})
P0 = tuple(EG['P0']); uFB = EG['u_FB']
D_FORK = add_part('Pallet fork (two noses; a ring round the balance staff carries the impulse pin)', [tuple(p) for p in EG['fork']], Z_ESC, T_ESC,
                  [cut('hole', 'Bore (pressed on the fork arbor)', 1.0, F), pocket('Window round the balance staff (through)', [tuple(p) for p in EG['fork_window']], None),
                   cut('hole', 'Impulse pin (Ø1 steel, pressed)', 1.0, P0)], smooth=False, mount={'axis': 'fork'})
def slot_pts(c, u, r0, r1, w, n=10):   # a radial slot from r0 to r1 along u, w wide, round ends
    v = (-u[1], u[0]); a_ = (c[0] + u[0] * (r0 + w / 2), c[1] + u[1] * (r0 + w / 2)); b_ = (c[0] + u[0] * (r1 - w / 2), c[1] + u[1] * (r1 - w / 2))
    ang = math.atan2(u[1], u[0]); pts = []
    for j in range(n + 1): t_ = ang - math.pi / 2 + math.pi * j / n; pts.append((b_[0] + w / 2 * math.cos(t_), b_[1] + w / 2 * math.sin(t_)))
    for j in range(n + 1): t_ = ang + math.pi / 2 + math.pi * j / n; pts.append((a_[0] + w / 2 * math.cos(t_), a_[1] + w / 2 * math.sin(t_)))
    return pts
Z_ROLL = Z_ESC + T_ESC + 0.2
add_part('Roller (on the balance staff; the impulse pin runs in its closed slot)', circ_pts(Bc, EG['ROLLER_R'], 40), Z_ROLL, 2.0,
         [cut('hole', 'Staff (pressed)', 1.0, Bc), pocket('Slot for the impulse pin (closed, through)', slot_pts(Bc, uFB, EG['SLOT_R0'], EG['SLOT_R1'], EG['SLOT_W']), None)],
         smooth=False, mount={'axis': 'balance'})
add_part('Impulse pin (Ø1 steel, pressed in the fork, runs in the roller\'s slot)', circ_pts(P0, EG['PIN_R'], 20), Z_ESC, Z_ROLL + 1.8 - Z_ESC, smooth=False, mount={'axis': 'fork'})
# ---------- colours (materials): gold train, silver bridges, dark plate, steel mechanism, blued hands, ivory star ----------
GOLD, SILVER, PLATE, STEEL, BLUE, IVORY = '#c9a24a', '#d9dcdf', '#6e6a64', '#a9afb5', '#2f5191', '#ebe5d4'
COLORS = {f'group:{g_}': GOLD for g_ in ('power', 'train', 'escapement', 'keyless')}
COLORS.update({'retro': STEEL, 'hourstar': STEEL, 'minute_hand': BLUE, 'seconds_hand': BLUE})
for d_ in DR:
    n_ = d_['name']
    COLORS[d_['id']] = PLATE if (n_ == 'Main plate' or 'rim plate' in n_ or n_.startswith(('Setting plate', 'Keyless plate'))) else BLUE if n_.startswith('Barrel cover') else IVORY if n_ == 'Hour star' else STEEL if any(w in n_ for w in ('Snail', 'lever', 'ratchet', 'Ratchet', 'Click', 'fork', 'Jumper', 'stem', 'Crown', 'pinion')) else SILVER
# ---------- arbors, gears, hands ----------
P_, W_ = 0.3, -0.3
def g(id_, label, z, t, x=0.0, **k): return {'id': id_, 'label': label, 'z': z, 't': t, **({'x': x} if x else {}), **k}
arbors = [
  {'id': 'barrel', 'name': 'Barrel', 'group': 'power', 'level': 0, 'drumH': 4.7, 'role': 'The barrel: 42 teeth on a drum with its mainspring. In the motion study it turns as the crown drives the train; its ratchet and click (on the barrel bridge) block turning backwards, which protects the snail.',
   'gears': [g('barrel_teeth', 'Barrel teeth', 42, 2.0, W_)]},
  {'id': 'center', 'name': 'Centre arbor', 'group': 'train', 'level': 1, 'role': 'Turns once an hour. Its pinion is driven by the barrel; its wheel drives the third; the setting wheel under the plate takes the crown; the snail on top drives the retrograde minute.',
   'gears': [g('center_pinion', 'Centre pinion', 12, 2.0, P_), g('center_wheel', 'Centre wheel', 48, 2.0, W_), g('setting_wheel', 'Setting wheel (under the plate)', 48, 2.0, W_)]},
  {'id': 'third', 'name': 'Third wheel', 'group': 'train', 'level': 2, 'role': 'Going train: centre wheel 48 → third pinion 12.', 'gears': [g('third_pinion', 'Third pinion', 12, 2.0, P_), g('third_wheel', 'Third wheel', 45, 2.0, W_)]},
  {'id': 'inter', 'name': 'Intermediate wheel', 'group': 'train', 'level': 3, 'role': 'Going train: third wheel 45 → intermediate pinion 12. With module 1 teeth a true 60:1 to the seconds needs three steps (4 × 3.75 × 4).', 'gears': [g('inter_pinion', 'Intermediate pinion', 12, 2.0, P_), g('inter_wheel', 'Intermediate wheel', 48, 2.0, W_)]},
  {'id': 'fourth', 'name': 'Seconds wheel', 'group': 'train', 'level': 4, 'role': 'Turns once a minute (60 × the centre); carries the small seconds hand above the bottom bridge.', 'gears': [g('fourth_pinion', 'Seconds pinion', 12, 2.0, P_), g('fourth_wheel', 'Seconds wheel', 36, 2.0, W_)]},
  {'id': 'escape', 'name': 'Escape wheel (faux)', 'group': 'escapement', 'level': 5, 'role': 'Turns once every 20 s with the train (3 × the seconds wheel). Its wheel (a drawn part) has 15 ramp teeth that lift the pallet fork\'s two noses in turn: 30 beats a turn, 1.5 a second. No lock, so the train never stalls; a real escapement would lock and need the balance\'s hairspring.', 'gears': [g('escape_pinion', 'Escape pinion', 12, 2.0, P_)]},
  {'id': 'fork', 'name': 'Pallet fork', 'group': 'escapement', 'level': 5, 'role': 'Rocked ±4.3° by the escape wheel: one nose lifted turns it one way, the other nose turns it back, with a rest between (it never locks). Its tail closes into a ring round the balance staff; a steel pin on the ring runs in the roller\'s closed slot, so it can never let go of the balance.', 'gears': [g('fork_hub', 'Fork hub', 6, 0.6, plain=True)]},
  {'id': 'balance', 'name': 'Balance', 'group': 'escapement', 'level': 5, 'role': f'Ø34 balance in a well under the crescent\'s cock. The fork\'s pin runs in the closed slot of its roller, so it swings ±{EG["check"]["balance_swing_deg"]:.0f}° with every beat and can\'t come loose. No hairspring: it is driven, it doesn\'t regulate.', 'gears': [g('balance_wheel', 'Balance wheel', 34, 2.0, plain=True)]},
  {'id': 'keyless', 'name': 'Keyless pinion and pin wheel (under the plate)', 'group': 'keyless', 'level': 6, 'role': 'The crown turns the stem; the stem\'s 8-leaf winding pinion drives the pin wheel\'s 24 steel pins (a contrate: the pins stand up from the disc); its 12-leaf pinion turns the setting wheel 48 on the centre arbor. One crown turn = 5 minutes on the minute hand.',
   'gears': [g('keyless_pinion', 'Keyless pinion', 12, 2.0, P_), g('pin_wheel', 'Pin wheel disc (Ø25, carries 24 steel pins)', 25, DISC_T, plain=True)]},
  {'id': 'retro', 'name': 'Minute hand arbor (retrograde)', 'group': 'display', 'level': 7, 'role': 'Carries the 12-leaf pinion turned by the lever\'s 36-tooth rack (3:1) and the long minute hand, which sweeps the crescent\'s track and flies back on the hour.', 'gears': [g('hand_pinion', 'Hand pinion (12, meshes the rack)', 12, 1.6, P_)]},
  {'id': 'hourstar', 'name': 'Hour star arbor', 'group': 'display', 'level': 7, 'role': 'Carries the hour ratchet and the numbered hour star. Kicked once an hour by the lever\'s pawl, seated by the jumper.', 'gears': [g('hour_hub', 'Hour arbor hub', 4, 0.3, plain=True)]},
]
stages = {'s_bc': ['barrel_teeth', 'center_pinion'], 's_ct': ['center_wheel', 'third_pinion'], 's_ti': ['third_wheel', 'inter_pinion'], 's_if': ['inter_wheel', 'fourth_pinion'], 's_fe': ['fourth_wheel', 'escape_pinion'], 's_set': ['setting_wheel', 'keyless_pinion']}
LV = json.load(open(os.path.join(HERE, 'levels.json')))   # from levels.py: no two gears that overlap in plan share a height
stage_z = {sid: {'m': 1, 'z': LV[sid]} for sid in ('s_bc', 's_ct', 's_ti', 's_if', 's_fe')}; stage_z['s_set'] = {'m': 1, 'z': -2.6}
solo = {'fork_hub': {'m': 1, 'z': Z_ESC + T_ESC}, 'balance_wheel': {'m': 1, 'z': 2.2}, 'pin_wheel': {'m': 1, 'z': round(PIN_Z0 - DISC_T, 4)}, 'hand_pinion': {'m': 1, 'z': Z_LEV - 0.2}, 'hour_hub': {'m': 1, 'z': Z_MECH + T_MECH}}
hands = [
  {'id': 'minute_hand', 'name': 'Minute hand (retrograde)', 'arbor': 'retro', 'group': 'display', 'level': 8, 'w0': 2.6, 'w1': 1.0, 'tail': 9.0, 'role': 'Long blued hand: sweeps the crescent\'s minute track over the hour and flies back to 0 when the snail drops.'},
  {'id': 'seconds_hand', 'name': 'Seconds hand', 'arbor': 'fourth', 'group': 'display', 'level': 8, 'w0': 1.0, 'w1': 0.45, 'tail': 2.5, 'role': 'Small seconds on the bottom bridge\'s lobe.'},
]
hand_set = {'minute_hand': {'length': round(DS.RI + 2.2, 3), 'z': Z_TOP + T_TOP + 0.6, 't': 0.5}, 'seconds_hand': {'length': 9.0, 'z': Z_L2 + T_L2 + 0.5, 't': 0.4}}
pos = {k: [v[0], v[1]] for k, v in (('barrel', B), ('center', C), ('third', T), ('inter', I), ('fourth', Fo), ('escape', E), ('fork', F), ('balance', Bc), ('keyless', K), ('retro', Q), ('hourstar', H))}   # full precision: the sim checks centre distances to 1e-6
# ---------- mechanism definition for the sim's motion engine ----------
mech = {
  'mounts': MOUNTS,
  'solve': [
    {'id': 'lever', 'kind': 'follower', 'part': D_FEELER, 'pivot': rnd(L), 'nose': rnd(nose_p, 5), 'noseR': PIN_R, 'cam': D_SNAIL, 'spring': -1,
     'min': round(math.degrees(TH_STOP - TH_POSE), 4), 'max': round(math.degrees(SWING) + 6, 3), 'label': 'Retrograde lever on the snail'},
    {'id': 'hour', 'kind': 'ratchet', 'pivot': rnd(H), 'wheel': D_RAT, 'pawl': {'follow': 'lever', 'pivot': rnd(L), 'tip': rnd(tip_p, 5), 'tipR': PIN_R, 'part': D_PAWLPIN}, 'pitch': 30, 'apex': 15, 'advance': 1, 'label': 'Hour star kicked by the pawl'},
    {'id': 'jumper', 'kind': 'follower', 'part': D_JUMP, 'pivot': rnd(JSTUD), 'nose': rnd(nose_j, 5), 'noseR': 0.6, 'cam': D_STAR, 'camAngle': 'hour', 'spring': 1, 'min': -6, 'max': 6, 'label': 'Jumper on the hour star'},
    {'id': 'click', 'kind': 'follower', 'part': D_CLICK, 'pivot': rnd(CLK), 'nose': rnd(click_nose, 5), 'noseR': 0.55, 'cam': D_BRAT, 'min': -25, 'max': 25, 'label': 'Click on the barrel ratchet', 'detent': 'click'},
  ],
  'links': [
    {'arbor': 'retro', 'from': 'lever', 'ratio': -3.0, 'offset': round(TRACK0 - 90, 4), 'label': 'Rack 36 → hand pinion 12'},
    {'arbor': 'hourstar', 'from': 'hour', 'ratio': 1.0, 'offset': 0},
    {'arbor': 'fork', 'kind': 'table', 'from': 'escape', 'period': EG['pitch_deg'], 'values': EG['fork_table'], 'label': 'Fork rocked by the escape wheel\'s teeth (escapement.py)'},
    {'arbor': 'balance', 'kind': 'table', 'from': 'escape', 'period': EG['pitch_deg'], 'values': EG['balance_table'], 'label': 'Balance swung by the impulse pin in the fork\'s slot'},
  ],
  'springs': [{'id': 'return', 'label': 'Return spring (steel wire)', 'from': rnd(STUD_SPRING), 'to': {'part': D_LEVER, 'at': rnd(lug)}, 'z': Z_LEV + T_LEV / 2, 'r': 0.25, 'push': -1}],
  'expect': {'flyback_every': 3600, 'hand_sweep': SWEEP, 'hour_steps': 12, 'pawl_flex_max': 2.5},
  'meshes': [{'part': D_LEVER, 'gear': 'hand_pinion'}],
  'proofs': [
    {'label': 'Rack sector and hand pinion', 'by': 'make_crescent.py', 'ok': not RACK_PROOF['interference_at_lever_deg'] and RACK_PROOF['drives_both_ways'] and min(RACK_PROOF['tip_clearance_mm']) > 0.1,
     'text': f"involute teeth, sector shifted -0.40 for the 23.95 mm centres: over the whole swing in 0.25° steps the teeth never overlap and the pinion is always driven both ways ({RACK_PROOF['pinion_play_deg'][0]}–{RACK_PROOF['pinion_play_deg'][1]}° of play); tip clearance {RACK_PROOF['tip_clearance_mm'][0]} and {RACK_PROOF['tip_clearance_mm'][1]} mm"},
    {'label': 'Click and barrel ratchet', 'by': 'make_crescent.py · click_logic', 'ok': CLICK_PROOF['ride_min'] > 0.3 and (CLICK_PROOF['lock'] or 1) < -0.1,
     'text': f"running forward the click rides up every tooth (push angle at most {CLICK_PROOF['pressure_max_deg']}°) and drops off the steep face; turned backwards the first steep face drives it in ({CLICK_PROOF['lock']}), so it locks: the train, and the snail's cliff, can't be driven in reverse"},
    {'label': 'Keyless: winding pinion on the pin wheel', 'by': 'keyless.py', 'ok': not KG['check']['interference_at_deg'] and KG['check']['drives_both_ways_every_angle'],
     'text': f"the 8-leaf pinion, as a 1 mm end mill cuts it, never cuts into the 24 steel pins and drives them both ways at every angle ({KG['check']['free_turn_forward_deg'][0]}–{KG['check']['free_turn_forward_deg'][1]}° of play); one crown turn moves the minute hand 5 minutes"},
    {'label': 'Escapement over a full turn', 'by': 'escapement.py', 'ok': EG['check']['jams_in_a_full_turn'] == 0 and EG['check']['fork_outline_deepest_cut_mm'] < 0.005 and EG['check']['pin_captive'],
     'text': f"in 0.02° steps the fork never jams (tightest margin {EG['check']['narrowest_band_deg']}°), every tooth lifts both noses, the fork swings ±{EG['check']['fork_swing_deg'][1]:.1f}° and rests {EG['check']['rests_fraction'] * 100:.0f} % of the time. Its ring holds the balance staff (the window clears it by {EG['check']['window_clears_staff_mm']} mm over the swing) and its pin runs in the roller's closed slot, so the balance swings ±{EG['check']['balance_swing_deg']:.0f}° and the pin can never leave; ramp push angle {EG['check']['ramp_pressure_angle_deg']}°"},
    {'label': 'Linear snail', 'by': 'make_crescent.py', 'ok': True,
     'text': f"generated from the lever motion it must give (constant rate over the hour), radius {SNAIL_INFO['r_min']} → {SNAIL_INFO['r_max']} mm, growing all the way; steepest push on the nose {SNAIL_INFO['pressure_max']}° (mean {SNAIL_INFO['pressure_mean']}°)"},
  ],
  'read': {'minute': {'arbor': 'retro', 'zero': TRACK0, 'full': round(TRACK1, 4)}, 'hour': {'solve': 'hour', 'step': 30}, 'seconds': {'arbor': 'fourth'}},
  'rods': {'barrel': 3.0, 'center': 3.0, 'third': 1.0, 'inter': 1.0, 'fourth': 1.0, 'escape': 1.0, 'fork': 1.0, 'balance': 1.0, 'keyless': 1.0, 'retro': 1.0, 'hourstar': 1.0},
}
project = {
  'format': 'bspk-studio-project', 'id': 'crescent', 'name': 'Crescent (Claude\'s movement)', 'title': 'Crescent · Calibre 01',
  'blurb': 'Claude\'s own movement, designed in BSPK Studio. A crescent bridge sweeps up the left and carries a 120° retrograde minute track; a long blued hand pivots off-centre and crosses the movement over the balance, then flies back on the hour. The same fly-back kicks the hour star one step through a pawl on the lever. Barrel, going train (true 60:1 to the small seconds), faux escapement, keyless works in two plates under the main plate. Module 1 throughout, Ø132. A 1/2" main plate with a recess for every wheel; rim plates carry the crescent and the hand cock (no risers); every plate and bridge is cut from acrylic sheet and milled from one face.',
  'source': ['Design and engineering: Claude, 2026-11-15, from Adam\'s brief ("HAUTE", "NOT CHEAP": crescents, thin bridges, layers) and five research passes (research/movement-brief.md). The lever kick follows the single-event idea in US10928777: the fly-back itself advances the hour. Mechanism proven in tools/crescent/kick.py before the sim.'],
  'groups': {'power': 'Power', 'train': 'Going train', 'escapement': 'Escapement (faux)', 'keyless': 'Keyless works', 'display': 'Display', 'drawn': 'Plates, bridges and mechanism parts'},
  'focus': [{'id': 'train', 'label': 'Going train: barrel → centre → third → intermediate → seconds → escape', 'parts': ['barrel', 'center', 'third', 'inter', 'fourth', 'escape']},
            {'id': 'display', 'label': 'Display: snail, lever, hand, hour star', 'parts': ['center', 'retro', 'hourstar', 'minute_hand', 'seconds_hand']}],
  'rules': {'minModule': 1, 'fixedModule': True, 'why': 'the 1 mm end mill has to fit between the pinion teeth'},
  'rate': {'arbor': 'center', 'period': 3600, 'dir': DIR},
  'targets': [{'label': 'Centre arbor (snail, minutes)', 'arbor': 'center', 'period': 3600, 'dir': DIR}, {'label': 'Seconds wheel (clockwise)', 'arbor': 'fourth', 'period': 60, 'dir': -1}],
  'arbors': arbors, 'hands': hands, 'stages': stages,
  'plate': {'name': 'Work surface', 'z': round(Z_KP - 0.5, 3), 'role': 'Just the ground, set below the keyless works; the movement\'s own main plate is the drawn part "Main plate".'},
  'defaults': {'movementD': 132, 'minGap': 0.5, 'zMax': 30, 'view': {'height': 44, 'mid': 4}, 'stages': stage_z, 'solo': solo, 'pos': pos, 'hands': hand_set,
               'locks': {k: True for k in ('barrel_teeth', 'center_wheel', 'third_wheel', 'inter_wheel', 'fourth_wheel', 'balance_wheel', 'pin_wheel', 'hand_pinion', 'setting_wheel', 'hour_hub', 'fork_hub', 'minute_hand', 'seconds_hand')}},
  'mechanisms': mech, 'decor': {'engrave': ENGRAVE, 'colors': COLORS},
}
scene = {'format': 'bspk-studio-scene', 'version': 3, 'savedAt': '2026-11-15T00:00:00.000Z', 'state': {'sketches': SK, 'drawn': DR}, 'project': project}
json.dump(scene, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('written', OUT, '|', len(DR), 'drawn parts,', sum(len(d.get('cuts', [])) for d in DR), 'cuts | sweep', SWEEP, 'track', TRACK0, '->', round(TRACK1, 2))
