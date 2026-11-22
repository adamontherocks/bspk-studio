# Escapement for Crescent's motion study, version 2 (2026-11-18, Adam's note P15 and "beef it up"): an escape wheel that physically
# rocks the pallet fork, and a fork that swings the balance. Changes from escapement.py:
#   - the fork stops short of the balance staff: its impulse pin sits on the NEAR side (between the fork's pivot and the staff), so
#     nothing has to reach round or through the staff; the roller's closed slot faces the fork
#   - beefed up for a hand-assembled demonstration (wider in xy, thicker in z): the fork's shaft 4.0 wide (was 1.8) ending in a round
#     end concentric with the pin; the nose arms 2.0 wide (were 1.1 / 0.84); the noses r 0.85 (were 0.6); the hub r 2.6; the
#     wheel's tooth tips get a flat land instead of a point; the impulse pin Ø1.5 steel (was Ø1); fork and wheel 2.4 thick (2.0),
#     the roller 3.0 (2.0) and its bore a friction fit on the staff (the slip clutch)
#   - the balance swings less (about ±19 deg, was ±33): smaller accelerations on every part when the train is cranked fast
#
# No hairspring and no lock (so the train can never stall): it is a two-nose cam anchor. Each of the wheel's 15 teeth has a
# forward-facing ramp, a flat land and a steep trailing face. The ramps lift the fork's two noses in turn (the noses sit 3 1/2 teeth
# apart, so one is over a ramp while the other is over a gap): nose A lifted turns the fork one way, nose B lifted turns it back.
# Between lifts nothing pushes, so the fork rests: tick, pause, tock, pause, 30 beats per wheel turn.
# The fork's shaft ends short of the balance staff; a steel pin at its end (the near side of the staff) runs in a closed slot in the
# roller, so the balance swings with the fork and the pin can never leave.
#
# This script designs the parts, then proves the motion: over a full wheel turn in 0.02 deg steps the two noses never both bind (no
# jam), every tooth lifts each nose, the whole fork outline never cuts into the wheel, the shaft's end clears the staff over the whole
# swing and the pin stays inside the roller's closed slot. It writes escapement2_geo.json (esc2_apply.py puts it into a scene).
# Settings used (2026-11-18): R_N=0.8 LAND=0.06 RHO=9.35 R_TIPARM=0.65 ELBOW=2.1 D_NEAR=2.85
#   R_N=0.8 LAND=0.06 RHO=9.35 R_TIPARM=0.65 ELBOW=2.1 D_NEAR=2.85 python3 escapement2.py [OUT_DIR]
# Settings used since P46 (2026-11-19, Adam's sketch: short teeth, valleys only as deep as the noses need, round tops):
#   RT1=0.8 RT2=0.8 RO=0.3 RV=1.2 LAND=0.12 FOOT_EXTRA=0.01 R_ROOT=7.8 R_TIP=9.12 R_N=0.8 RHO=9.35 R_TIPARM=0.65 ELBOW=2.1 D_NEAR=2.85 python3 escapement2.py
import json, math, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import design as DS
from kit import X, Y, circle, curve, U
P = DS.PIV
E, F, BC = (np.array(P[k], float) for k in ('E', 'F', 'Bc'))
DEG = math.pi / 180
def pol(c, r, a): return np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a)])
def rot(p, c, a):
    p = np.asarray(p, float); c = np.asarray(c, float); ca, sa = math.cos(a), math.sin(a); d = p - c
    return np.stack([c[0] + d[..., 0] * ca - d[..., 1] * sa, c[1] + d[..., 0] * sa + d[..., 1] * ca], -1)

# ---------- the wheel (local frame = as drawn, wheel angle 0) ----------
NT = 15; PITCH = 2 * math.pi / NT
R_ROOT, R_TIP = float(os.environ.get('R_ROOT', 6.9)), float(os.environ.get('R_TIP', 9.0))   # (P46: with round tips the drawn tip starts higher; the rounding brings it back)
R_RAMP0 = 7.3                      # the ramp starts here (a short riser up from the root passes under the low nose)
F_RAMP = float(os.environ.get('F_RAMP', 0.38))   # the ramp takes this share of the pitch
LAND = float(os.environ.get('LAND', 0.06))   # then a flat land at the tip (0.23 mm at r 9): no knife-edge tips
FOOT = F_RAMP + LAND + float(os.environ.get('FOOT_EXTRA', 0.01))   # the trailing face's foot (0.01: near radial; more leans it back, so the nose slides off)
WDIR = 1                            # the wheel turns anticlockwise (the sim's escape arbor: +0.314 rad/s)
def wheel_local():
    pts = []
    for k in range(NT):
        # phase v runs the way the tooth passes a fixed point: local angle a = -(k + v) * PITCH * WDIR
        for j in range(25):        # ramp, root -> tip
            v = F_RAMP * j / 24; r = R_RAMP0 + (R_TIP - R_RAMP0) * (v / F_RAMP)
            if j == 0: pts.append(pol((0, 0), R_ROOT, -WDIR * (k + v) * PITCH))
            pts.append(pol((0, 0), r, -WDIR * (k + v) * PITCH))
        for j in range(1, 5): pts.append(pol((0, 0), R_TIP, -WDIR * (k + F_RAMP + LAND * j / 4) * PITCH))   # the land
        pts.append(pol((0, 0), R_ROOT, -WDIR * (k + FOOT) * PITCH))          # trailing face down to the root
        for j in range(1, 12):     # root arc to the next ramp
            v = FOOT + (1 - FOOT) * j / 12; pts.append(pol((0, 0), R_ROOT, -WDIR * (k + v) * PITCH))
    return np.array(pts)
WL = wheel_local()                  # about E, local frame
# P46 (2026-11-19): the tooth's tip rounded like the fork's noses. The teeth are too slender near the top for one radius all round
# (r 0.8 would shave the tips off), so each tip corner gets its own fillet: the crest (ramp into land, where the nose rolls over the
# top) r RT1, the drop-off edge (land into the trailing face, where the nose leaves) r RT2. RT1 = RT2 = 0 keeps the sharp corners.
RT1, RT2 = float(os.environ.get('RT1', 0.0)), float(os.environ.get('RT2', 0.0))
RT = max(RT1, RT2)
def _fillet(path, iv, r, n=24):
    """replace the corner at path[iv] with an arc of radius r tangent to the (locally straight) edges either side"""
    if r <= 0: return path
    V = path[iv]
    def walk(step, dist):                         # the point `dist` along the path from V (step -1: back, +1: on)
        acc, i = 0.0, iv
        while True:
            j = i + step; seg = np.linalg.norm(path[j] - path[i])
            if acc + seg >= dist: return path[i] + (path[j] - path[i]) * (dist - acc) / seg, j
            acc += seg; i = j
    a1, _ = walk(-1, 0.05); b1, _ = walk(1, 0.05)
    u1 = (a1 - V) / np.linalg.norm(a1 - V); u2 = (b1 - V) / np.linalg.norm(b1 - V)
    phi = math.acos(np.clip(u1 @ u2, -1, 1)); t = r / math.tan(phi / 2)
    A, ia = walk(-1, t); B, ib = walk(1, t)
    bis = (u1 + u2) / np.linalg.norm(u1 + u2); Cc = V + bis * r / math.sin(phi / 2)
    a0, a1_ = math.atan2(*(A - Cc)[::-1]), math.atan2(*(B - Cc)[::-1])
    da = (a1_ - a0 + math.pi) % (2 * math.pi) - math.pi
    arc = [Cc + r * np.array([math.cos(a0 + da * k / n), math.sin(a0 + da * k / n)]) for k in range(n + 1)]
    return np.vstack([path[:ia], arc, path[ib:]])
if RT > 0:
    pts = []; corners = []
    for k in range(NT):
        for j in range(161):       # ramp, root -> tip, finely
            v = F_RAMP * j / 160; r = max(R_ROOT, R_RAMP0 + (R_TIP - R_RAMP0) * (v / F_RAMP))   # (P46b: a shallow valley cuts the ramp's foot off)
            if j == 0: pts.append(pol((0, 0), R_ROOT, -WDIR * k * PITCH))
            pts.append(pol((0, 0), r, -WDIR * (k + v) * PITCH))
        corners.append(len(pts) - 1)
        for j in range(1, 41): pts.append(pol((0, 0), R_TIP, -WDIR * (k + F_RAMP + LAND * j / 40) * PITCH))
        corners.append(len(pts) - 1)
        for j in range(1, 61): pts.append(pol((0, 0), R_TIP + (R_ROOT - R_TIP) * j / 60, -WDIR * (k + F_RAMP + LAND + (FOOT - F_RAMP - LAND) * j / 60) * PITCH))
        for j in range(1, 12): v = FOOT + (1 - FOOT) * j / 12; pts.append(pol((0, 0), R_ROOT, -WDIR * (k + v) * PITCH))
    WL = np.array(pts)
    for ci in sorted(corners, reverse=True):      # from the end, so earlier indices stay valid
        r_ = RT1 if corners.index(ci) % 2 == 0 else RT2
        WL = _fillet(WL, ci, r_)
# P46b (2026-11-19, Adam's sketch): the valleys only as deep as the noses need (they never come closer than r 8.1 to the wheel's
# centre), so the teeth are short and sturdy, and the valleys rounded r RV (bigger than the noses, so nothing can wedge in them)
RO = float(os.environ.get('RO', 0.0))                # (2026-11-21) a last round-off of any point the fillets leave where they meet (r RO)
if RO > 0:
    from pk2 import P as _P, F as _F, opening as _op
    import pyclipper as _pc
    _o = [q for q in _op([_P(WL)], RO) if _pc.Orientation(q)]
    WL = _F(max(_o, key=lambda q: abs(_pc.Area(q))))[::-1]
RV = float(os.environ.get('RV', 0.0))
if RV > 0:
    from pk2 import P as _P, F as _F, close as _close
    import pyclipper as _pc
    _o = [q for q in _close([_P(WL)], RV) if _pc.Orientation(q)]
    WL = _F(max(_o, key=lambda q: abs(_pc.Area(q))))[::-1]
SEG_A = WL; SEG_B = np.roll(WL, -1, 0)
P_WL = MP(np.vstack([WL, WL[:1]]))
def signed_dist_local(q):
    """signed distance from point q (local, about E) to the wheel outline: + outside"""
    d = SEG_B - SEG_A; w = q - SEG_A
    t = np.clip((w * d).sum(1) / (d * d).sum(1), 0, 1); proj = SEG_A + d * t[:, None]
    m = np.sqrt(((q - proj) ** 2).sum(1)).min()
    return -m if P_WL.contains_point(q) else m

# ---------- the fork (anchor), drawn at its reference angle 0 ----------
R_N = float(os.environ.get('R_N', 0.85))   # nose radius (part of the fork, cut with it)
SPAN = 3.5                           # noses 3 1/2 teeth apart: one over a ramp while the other is over a gap
a_F = math.atan2(F[1] - E[1], F[0] - E[0])
RHO_MID = float(os.environ.get('RHO', 9.0))   # both noses this far from E at the reference angle
NA, NB = pol(E, RHO_MID, a_F + SPAN * PITCH / 2), pol(E, RHO_MID, a_F - SPAN * PITCH / 2)
def noses(phi): return rot(NA, F, phi), rot(NB, F, phi)
def clear(n, theta):                  # nose clearance to the wheel turned theta (+ = clear)
    q = rot(n, E, -theta) - E
    return signed_dist_local(q) - R_N
# which way each nose is freed (its constraint direction)
dA = 1 if clear(noses(1e-3)[0], 0) > clear(noses(-1e-3)[0], 0) else -1
dB = 1 if clear(noses(1e-3)[1], 0) > clear(noses(-1e-3)[1], 0) else -1
assert dA == -dB, 'the two noses must be freed in opposite directions'
def bound(which, theta, lo=-0.4, hi=0.4):
    """the fork angle at which nose `which` just touches: angles on the free side of it are clear"""
    d = dA if which == 0 else dB
    f = lambda ph: clear(noses(ph)[which], theta)
    a, b = (lo, hi) if d > 0 else (hi, lo)          # a: blocked side, b: free side
    if f(b) < 0: return None                        # can't free it in range
    if f(a) >= 0: return a                          # never touches in range
    for _ in range(40):
        m = (a + b) / 2
        if f(m) >= 0: b = m
        else: a = m
    return b
# ---------- 1. the motion over a full wheel turn ----------
STEP = float(os.environ.get('STEP_DEG', 0.02)) * DEG
thetas = np.arange(0, 2 * math.pi + 2 * PITCH, STEP)
phi = 0.0; PHI = []; jam = []; gap_min = 9.0; lifts_A = lifts_B = 0; pushed = None
for th in thetas:
    bA, bB = bound(0, WDIR * th), bound(1, WDIR * th)
    lo_, hi_ = (bA, bB) if dA > 0 else (bB, bA)      # admissible fork angles [lo_, hi_]
    gap_min = min(gap_min, hi_ - lo_)
    if lo_ > hi_ - 1e-6: jam.append(math.degrees(th))
    new = min(max(phi, lo_), hi_)
    who = None if abs(new - phi) < 1e-9 else ('A' if (new - phi) * dA > 0 else 'B')
    if who and who != pushed: lifts_A += who == 'A'; lifts_B += who == 'B'
    if who: pushed = who
    phi = new; PHI.append(phi)
PHI = np.array(PHI)
steady = thetas >= 2 * PITCH                                  # after the first two teeth
amp_lo, amp_hi = PHI[steady].min(), PHI[steady].max()
# periodicity: one pitch later the fork does the same thing
n_p = int(round(PITCH / STEP))
per_err = np.abs(PHI[steady][n_p:] - PHI[steady][:-n_p]).max()
# fraction of the time the fork rests
moving = np.abs(np.diff(PHI[steady])) > 1e-7
rest_frac = 1 - moving.mean()
print(f'fork: noses freed {dA:+d}/{dB:+d}; swing {math.degrees(amp_lo):.2f} to {math.degrees(amp_hi):.2f} deg; narrowest admissible band {math.degrees(gap_min):.2f} deg; jams {len(jam)}; repeats each tooth to {math.degrees(per_err):.4f} deg; rests {rest_frac * 100:.0f} % of the time; lifts A {lifts_A} B {lifts_B}')

# ---------- 2. the balance: a closed drive, the pin on the near side of the staff ----------
# A Ø1.5 steel pin pressed into the end of the fork's shaft, on the near side of the staff (between the fork's pivot and the staff),
# runs in a closed radial slot in the roller on the balance staff, so the balance is driven both ways and the pin can't come out.
# The slot is radial, so the balance angle is simply the pin's angle about the staff.
D_FB = float(np.linalg.norm(BC - F)); u_FB = (BC - F) / D_FB
perp = np.array([-u_FB[1], u_FB[0]])
STAFF_R = 0.5                        # balance staff Ø1
PIN_R = 0.75                         # impulse pin Ø1.5 steel, pressed into the fork
STAFF_CL = 0.3                       # the shaft's end clears the staff by at least this over the whole swing
WALL = 1.25                          # Delrin round the pin's hole (the shaft's end is a round end on the pin: r = pin + wall)
ROLLER_WALL_MIN = 1.2                # roller wall round its slot
SLOT_C = 0.1                         # the pin's clearance each side in the roller's slot
D0 = float(os.environ.get('D_NEAR', 3.0))   # the pin's distance short of the staff, fork at rest
P0 = BC - u_FB * D0
u_SLOT = -u_FB                       # the roller's slot points back at the fork
def pin_at(ph): return rot(P0, F, ph)
def beta_of(ph):
    v = pin_at(ph) - BC; return math.atan2(u_SLOT[0] * v[1] - u_SLOT[1] * v[0], float(u_SLOT @ v))
BETA = np.array([beta_of(p) for p in PHI])
R_PIN = np.array([float(np.linalg.norm(pin_at(p) - BC)) for p in PHI[steady]])
AMP_B = float(max(abs(BETA[steady].min()), abs(BETA[steady].max())))
SLOT_R0, SLOT_R1 = float(R_PIN.min()) - PIN_R - SLOT_C, float(R_PIN.max()) + PIN_R + SLOT_C
ROLLER_R = SLOT_R1 + ROLLER_WALL_MIN
ROLLER_WALL = SLOT_R0 - STAFF_R
staff_path = [rot(BC, F, -p) for p in np.linspace(amp_lo, amp_hi, 61)]      # the staff as the fork sees it
print(f'balance: pin {D0:.2f} short of the staff; balance swings ±{math.degrees(AMP_B):.1f} deg; pin runs r {R_PIN.min():.3f}..{R_PIN.max():.3f} in a slot r {SLOT_R0:.2f}..{SLOT_R1:.2f} (wall to the staff {ROLLER_WALL:.2f}); roller r {ROLLER_R:.2f}')

# ---------- 3. the fork outline (SDF, drawn at angle 0) and a check of the whole outline against the wheel ----------
tail_dir = math.atan2(u_FB[1], u_FB[0])
H = 0.02
FAR = D_FB - D0 + PIN_R + WALL                          # the shaft's end, along the fork from its pivot
pts_all = np.array([F, NA, NB, F + u_FB * (FAR + 2.0), BC + perp * 5, BC - perp * 5])
x0, y0 = pts_all.min(0) - 3; x1, y1 = pts_all.max(0) + 3
GX, GY = np.meshgrid(np.arange(x0, x1, H), np.arange(y0, y1, H))
def c_sdf(c, r): return np.hypot(GX - c[0], GY - c[1]) - r
def cap(a, b, r):
    a = np.asarray(a); b = np.asarray(b); d = b - a; L2 = (d * d).sum()
    t = np.clip(((GX - a[0]) * d[0] + (GY - a[1]) * d[1]) / L2, 0, 1)
    return np.hypot(GX - (a[0] + t * d[0]), GY - (a[1] + t * d[1])) - r
def smin(a, b, k=0.2):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)
def box(c, u, half_u, half_v):   # a rectangle centred at c, long axis u
    v = np.array([-u[1], u[0]]); px = (GX - c[0]) * u[0] + (GY - c[1]) * u[1]; py = (GX - c[0]) * v[0] + (GY - c[1]) * v[1]
    qx, qy = np.abs(px) - half_u, np.abs(py) - half_v
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
ELBOW = float(os.environ.get('ELBOW', 1.7))   # each arm leaves its nose straight out from the wheel's centre, then runs to the hub
elA = NA + (NA - E) / np.linalg.norm(NA - E) * ELBOW; elB = NB + (NB - E) / np.linalg.norm(NB - E) * ELBOW
R_HUBF, R_ARM, R_TIPARM = 2.6, float(os.environ.get('R_ARM', 1.0)), float(os.environ.get('R_TIPARM', 0.85))
f_sdf = c_sdf(F, R_HUBF)
for N_, el in ((NA, elA), (NB, elB)):
    f_sdf = smin(f_sdf, cap(F, el, R_ARM), 0.4); f_sdf = smin(f_sdf, cap(el, N_ + (el - N_) / np.linalg.norm(el - N_) * 0.2, R_TIPARM), 0.3)
    f_sdf = np.minimum(f_sdf, c_sdf(N_, R_N))
# the shaft: one straight bar 4.0 wide from the hub to a round end concentric with the pin (no ring, nothing round the staff)
TAIL_R = PIN_R + WALL
f_sdf = smin(f_sdf, cap(F, P0, TAIL_R), 0.6)
cs = plt.contour(GX, GY, f_sdf, levels=[0]); segs = cs.allsegs[0]; plt.close('all')
P_FORK0 = max(segs, key=len)[::2]

# the shaft's end stays clear of the staff over the whole swing
def edge_dist(p, poly):
    a_ = poly; b_ = np.roll(poly, -1, 0); d = b_ - a_; t = np.clip(((p - a_) * d).sum(1) / np.maximum((d * d).sum(1), 1e-12), 0, 1)
    return float(np.sqrt(((p - (a_ + d * t[:, None])) ** 2).sum(1)).min())
STAFF_GAP = min(edge_dist(np.asarray(sp), P_FORK0) - STAFF_R for sp in staff_path) if not any(MP(P_FORK0).contains_point(tuple(sp)) for sp in staff_path) else -1.0
PIN_WALL = TAIL_R - PIN_R
print(f'fork shaft: {2 * TAIL_R:.1f} wide, its end clears the staff by {STAFF_GAP:.3f} mm over the swing; {PIN_WALL:.2f} mm of Delrin round the pin')
# the whole outline against the wheel, at every 0.1 deg of a pitch (steady state)
worst_pen = 0.0
idx = np.where(steady)[0]
for i in idx[: n_p][::5]:
    th = thetas[i]; ph = PHI[i]
    fw = rot(rot(P_FORK0, F, ph), E, -WDIR * th) - E        # fork outline into the wheel's frame
    inside = P_WL.contains_points(fw)
    if inside.any():
        worst_pen = max(worst_pen, max(-signed_dist_local(q) for q in fw[inside]))
    wf = rot(WL + E, E, WDIR * th)                            # wheel outline into the world, then test against the fork
    inf = MP(rot(P_FORK0, F, ph)).contains_points(wf)
    if inf.any():
        worst_pen = max(worst_pen, 0.01 * inf.sum())
print(f'whole fork outline vs wheel over a pitch: deepest cut {worst_pen:.4f} mm')
# the pin in the roller's slot: in the roller's frame it only runs in and out along the slot (the slot is radial by construction)
pin_ok = bool(R_PIN.min() - PIN_R - SLOT_C >= SLOT_R0 - 1e-9 and R_PIN.max() + PIN_R + SLOT_C <= SLOT_R1 + 1e-9 and ROLLER_WALL >= 0.8 and STAFF_GAP >= STAFF_CL)

# ---------- producibility (1 mm end mill) ----------
gap_root = (1 - FOOT) * PITCH * R_ROOT
PRESS = math.degrees(math.atan2(R_TIP - R_RAMP0, F_RAMP * PITCH * (R_RAMP0 + R_TIP) / 2))
print(f'wheel tooth gap at the root {gap_root:.2f} mm (end mill 1.0); ramp pressure angle about {PRESS:.0f} deg')

# ---------- tables for the sim: fork and balance angle against the wheel's angle (mod one pitch) ----------
N_TAB = 480
ph_tab, be_tab = [], []
base = idx[0] - (idx[0] % n_p) + n_p * 2                      # a steady stretch starting at a whole pitch
for j in range(N_TAB):
    th = j / N_TAB * PITCH
    i = base + int(round(th / STEP))
    ph_tab.append(round(math.degrees(PHI[i]), 5)); be_tab.append(round(math.degrees(BETA[i]), 5))
res = {
    'E': E.tolist(), 'F': F.tolist(), 'Bc': BC.tolist(), 'NT': NT, 'R_ROOT': R_ROOT, 'R_TIP': R_TIP, 'WDIR': WDIR,
    'wheel_local': [[round(float(x), 4), round(float(y), 4)] for x, y in WL],
    'fork': [[round(float(x), 4), round(float(y), 4)] for x, y in P_FORK0],
    'P0': [round(float(v), 4) for v in P0], 'D0': D0, 'near_side': True, 'u_slot': u_SLOT.tolist(), 'TAIL_R': TAIL_R, 'R_N': R_N,
    'ROLLER_R': round(ROLLER_R, 4), 'SLOT_R0': round(SLOT_R0, 4), 'SLOT_R1': round(SLOT_R1, 4), 'SLOT_W': round(2 * (PIN_R + SLOT_C), 3), 'PIN_R': PIN_R, 'u_FB': u_FB.tolist(),
    'T_ESC': 2.4, 'T_ROLL': 3.0,
    'pitch_deg': 360 / NT, 'fork_table': ph_tab, 'balance_table': be_tab,
    'check': {'jams_in_a_full_turn': len(jam), 'narrowest_band_deg': round(math.degrees(gap_min), 3), 'fork_swing_deg': [round(math.degrees(amp_lo), 3), round(math.degrees(amp_hi), 3)],
              'balance_swing_deg': round(math.degrees(AMP_B), 2), 'lifts_A': lifts_A, 'lifts_B': lifts_B, 'repeats_each_tooth_deg': round(math.degrees(per_err), 5),
              'rests_fraction': round(float(rest_frac), 3), 'fork_outline_deepest_cut_mm': round(float(worst_pen), 4), 'pin_captive': pin_ok,
              'shaft_clears_staff_mm': round(STAFF_GAP, 3), 'pin_hole_wall_mm': round(PIN_WALL, 3), 'roller_wall_to_staff_mm': round(ROLLER_WALL, 3), 'tooth_gap_at_root_mm': round(gap_root, 3), 'ramp_pressure_angle_deg': round(PRESS, 1), 'tip_radius_mm': RT1, 'dropoff_radius_mm': RT2, 'valley_radius_mm': RV, 'root_r_mm': R_ROOT, 'land_frac': LAND, 'ramp_frac': F_RAMP,
              'tip_r_after_rounding_mm': round(float(np.hypot(*WL.T).max()), 3)},
}
json.dump(res, open(os.environ.get('OUTJSON', os.path.join(HERE, 'escapement2_geo.json')), 'w'), indent=1)
print(json.dumps(res['check'], indent=1))
# ---------- picture: the fork at both ends of its swing on the wheel, and the angles over two teeth ----------
out = sys.argv[1] if len(sys.argv) > 1 else HERE
fig, axs = plt.subplots(1, 2, figsize=(11, 5), dpi=150)
ax = axs[0]
i0 = base + int(np.argmax(PHI[base:base + n_p])); i1 = base + int(np.argmin(PHI[base:base + n_p]))
for i, col in ((i0, '#3d5a80'), (i1, '#c97b3d')):
    wv = rot(WL + E, E, WDIR * thetas[i]); ax.fill(wv[:, 0], wv[:, 1], color='#d8c9a3', alpha=0.5 if i == i1 else 0.9, ec='#8a7a50', lw=0.5)
    fv = rot(P_FORK0, F, PHI[i]); ax.plot(fv[:, 0], fv[:, 1], color=col, lw=1.0)
    b_ = BETA[i]; ax.add_patch(plt.Circle(BC, ROLLER_R, fill=False, ls='--', color=col, lw=0.6))
    for rr in (SLOT_R0 + PIN_R + SLOT_C, SLOT_R1 - PIN_R - SLOT_C):
        sd = math.atan2(u_SLOT[1], u_SLOT[0]); ax.add_patch(plt.Circle(BC + rr * np.array([math.cos(sd + b_), math.sin(sd + b_)]), PIN_R + SLOT_C, fill=False, color=col, lw=0.5))
    ax.add_patch(plt.Circle(pin_at(PHI[i]), PIN_R, color=col)); ax.add_patch(plt.Circle(BC, STAFF_R, color='#555'))
ax.set_aspect('equal'); ax.set_title('Escape wheel, fork (pin on the near side of the staff), pin in the roller slot (two ends of the swing)', fontsize=8)
ax = axs[1]
seg = slice(base, base + 2 * n_p)
ax.plot(np.degrees(thetas[seg] - thetas[base]), np.degrees(PHI[seg]), label='fork (deg)')
ax.plot(np.degrees(thetas[seg] - thetas[base]), np.degrees(BETA[seg]) / 10, label='balance (deg / 10)')
ax.set_xlabel('escape wheel angle (deg), two teeth'); ax.legend(fontsize=7); ax.grid(alpha=0.3)
fig.savefig(os.path.join(out, os.environ.get('OUTPNG', 'escapement2.png')), bbox_inches='tight'); print('picture written')
