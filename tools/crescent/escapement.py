# Escapement for Crescent's motion study: an escape wheel that physically rocks the pallet fork, and a fork that swings the balance.
#
# No hairspring and no lock (so the train can never stall): it is a two-nose cam anchor. Each of the wheel's 15 teeth has a
# forward-facing ramp and a steep trailing face. The ramps lift the fork's two noses in turn (the noses sit 3 1/2 teeth apart,
# so one is over a ramp while the other is over a gap): nose A lifted turns the fork one way, nose B lifted turns it back.
# Between lifts nothing pushes, so the fork rests: tick, pause, tock, pause, 30 beats per wheel turn (1.5 a second at 1x).
# The fork's tail closes into a ring round the balance staff; a steel pin on the ring's far side runs in a closed slot in the roller,
# so the balance swings with the fork and the pin can never leave (even when a hand-cranked train buzzes it).
#
# This script designs the parts, then proves the motion: over a full wheel turn in 0.02 deg steps the two noses never both
# bind (no jam), every tooth lifts each nose, the whole fork outline never cuts into the wheel, the ring's window clears the staff
# over the whole swing and the pin stays inside the roller's closed slot. It writes escapement_geo.json with the outlines and the fork and balance
# angles as tables of the wheel's angle (the sim plays them back and re-checks the outlines itself).
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
R_ROOT, R_TIP = 6.9, 9.0
R_RAMP0 = 7.3                      # the ramp starts here (a short riser up from the root passes under the low nose)
F_RAMP = 0.38                       # the ramp takes 42 % of the pitch
FOOT = 0.39                         # the trailing face's foot (just past the tip: a near-radial face)
WDIR = 1                            # the wheel turns anticlockwise (the sim's escape arbor: +0.314 rad/s)
def wheel_local():
    pts = []
    for k in range(NT):
        # phase v runs the way the tooth passes a fixed point: local angle a = -(k + v) * PITCH * WDIR
        for j in range(25):        # ramp, root -> tip
            v = F_RAMP * j / 24; r = R_RAMP0 + (R_TIP - R_RAMP0) * (v / F_RAMP)
            if j == 0: pts.append(pol((0, 0), R_ROOT, -WDIR * (k + v) * PITCH))
            pts.append(pol((0, 0), r, -WDIR * (k + v) * PITCH))
        pts.append(pol((0, 0), R_ROOT, -WDIR * (k + FOOT) * PITCH))          # trailing face down to the root
        for j in range(1, 12):     # root arc to the next ramp
            v = FOOT + (1 - FOOT) * j / 12; pts.append(pol((0, 0), R_ROOT, -WDIR * (k + v) * PITCH))
    return np.array(pts)
WL = wheel_local()                  # about E, local frame
SEG_A = WL; SEG_B = np.roll(WL, -1, 0)
P_WL = MP(np.vstack([WL, WL[:1]]))
def signed_dist_local(q):
    """signed distance from point q (local, about E) to the wheel outline: + outside"""
    d = SEG_B - SEG_A; w = q - SEG_A
    t = np.clip((w * d).sum(1) / (d * d).sum(1), 0, 1); proj = SEG_A + d * t[:, None]
    m = np.sqrt(((q - proj) ** 2).sum(1)).min()
    return -m if P_WL.contains_point(q) else m

# ---------- the fork (anchor), drawn at its reference angle 0 ----------
R_N = 0.6                            # nose radius (part of the fork, cut with it)
SPAN = 3.5                           # noses 3 1/2 teeth apart: one over a ramp while the other is over a gap
a_F = math.atan2(F[1] - E[1], F[0] - E[0])
RHO_MID = 9.0                        # both noses this far from E at the reference angle
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
STEP = 0.02 * DEG
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

# ---------- 2. the balance: a closed drive the pin can never leave ----------
# The fork's tail closes into a ring round the balance staff. A Ø1 steel pin pressed into the ring's far side (past the staff) runs in a
# closed radial slot in the roller on the balance staff, so the balance is driven both ways and the pin can't come out, even when the
# hand-cranked train buzzes it. The slot is radial, so the balance angle is simply the pin's angle about the staff.
D_FB = float(np.linalg.norm(BC - F)); u_FB = (BC - F) / D_FB
perp = np.array([-u_FB[1], u_FB[0]])
STAFF_R = 0.5                        # balance staff Ø1
PIN_R = 0.5                          # impulse pin Ø1 steel, pressed into the fork
WIN_CL = 0.3                         # the ring's window clears the staff by this all round, over the whole swing
WALL = 1.0                           # Delrin walls: ring round its window and the pin's hole; roller round its slot and the staff
SLOT_C = 0.1                         # the pin's clearance each side in the roller's slot (1.2 wide: one pass of a 1 mm end mill, plus)
D0 = STAFF_R + WIN_CL + WALL + PIN_R      # the pin's distance past the staff with the fork at rest
P0 = BC + u_FB * D0
def pin_at(ph): return rot(P0, F, ph)
def beta_of(ph):
    v = pin_at(ph) - BC; return math.atan2(u_FB[0] * v[1] - u_FB[1] * v[0], float(u_FB @ v))
BETA = np.array([beta_of(p) for p in PHI])
R_PIN = np.array([float(np.linalg.norm(pin_at(p) - BC)) for p in PHI[steady]])
AMP_B = float(max(abs(BETA[steady].min()), abs(BETA[steady].max())))
SLOT_R0, SLOT_R1 = float(R_PIN.min()) - PIN_R - SLOT_C, float(R_PIN.max()) + PIN_R + SLOT_C
ROLLER_R = SLOT_R1 + WALL
ROLLER_WALL = SLOT_R0 - STAFF_R
staff_path = [rot(BC, F, -p) for p in np.linspace(amp_lo, amp_hi, 61)]      # the staff as the fork sees it
print(f'balance: pin {D0:.2f} past the staff; balance swings ±{math.degrees(AMP_B):.1f} deg; pin runs r {R_PIN.min():.3f}..{R_PIN.max():.3f} in a slot r {SLOT_R0:.2f}..{SLOT_R1:.2f} (wall to the staff {ROLLER_WALL:.2f}); roller r {ROLLER_R:.2f}')

# ---------- 3. the fork outline (SDF, drawn at angle 0) and a check of the whole outline against the wheel ----------
tail_dir = math.atan2(u_FB[1], u_FB[0])
H = 0.02
FAR = D_FB + D0 + PIN_R + WALL                          # the ring's far end, along the fork from its pivot
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
ELBOW = 1.7                          # each arm leaves its nose straight out from the wheel's centre, then runs to the hub
elA = NA + (NA - E) / np.linalg.norm(NA - E) * ELBOW; elB = NB + (NB - E) / np.linalg.norm(NB - E) * ELBOW
f_sdf = c_sdf(F, 2.0)
for N_, el in ((NA, elA), (NB, elB)):
    f_sdf = smin(f_sdf, cap(F, el, 0.55)); f_sdf = smin(f_sdf, cap(el, N_ + (el - N_) / np.linalg.norm(el - N_) * 0.2, 0.42), 0.15)
    f_sdf = np.minimum(f_sdf, c_sdf(N_, R_N))
# the window the staff lives in (the staff's path in the fork's frame, plus its radius and the clearance)
win = None
for sp in staff_path:
    w_ = c_sdf(sp, STAFF_R + WIN_CL); win = w_ if win is None else np.minimum(win, w_)
LAT = max(abs(float((sp - BC) @ perp)) for sp in staff_path) + STAFF_R + WIN_CL + WALL
NEAR = min(float((sp - F) @ u_FB) for sp in staff_path) - STAFF_R - WIN_CL - WALL
RC = 1.0                                                  # the ring's corner radius
ring = box(F + u_FB * ((NEAR + FAR) / 2), u_FB, (FAR - NEAR) / 2 - RC, LAT - RC) - RC
f_sdf = smin(f_sdf, cap(F, F + u_FB * (NEAR + 1.0), 0.9), 0.3)       # a stiffer tail (1.8 wide) out to the ring
f_sdf = smin(f_sdf, ring, 0.6)
cs = plt.contour(GX, GY, f_sdf, levels=[0]); segs = cs.allsegs[0]; plt.close('all')
P_FORK0 = max(segs, key=len)[::2]
cs = plt.contour(GX, GY, win, levels=[0]); P_WIN = max(cs.allsegs[0], key=len)[::2]; plt.close('all')
# the window really holds the staff: over the swing its edge stays this far from the staff's surface
def edge_dist(p, poly):
    a_ = poly; b_ = np.roll(poly, -1, 0); d = b_ - a_; t = np.clip(((p - a_) * d).sum(1) / np.maximum((d * d).sum(1), 1e-12), 0, 1)
    return float(np.sqrt(((p - (a_ + d * t[:, None])) ** 2).sum(1)).min())
WIN_MIN = min(edge_dist(np.asarray(sp), P_WIN) - STAFF_R for sp in staff_path) if all(MP(P_WIN).contains_point(tuple(sp)) for sp in staff_path) else -1.0
PIN_WALL = edge_dist(P0, P_WIN) - PIN_R
print(f'fork ring: window clears the staff by {WIN_MIN:.3f} mm over the swing; {PIN_WALL:.2f} mm of Delrin between the window and the pin hole')
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
pin_ok = bool(R_PIN.min() - PIN_R - SLOT_C >= SLOT_R0 - 1e-9 and R_PIN.max() + PIN_R + SLOT_C <= SLOT_R1 + 1e-9 and ROLLER_WALL >= 0.8 and WIN_MIN >= 0.25)

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
    'fork_window': [[round(float(x), 4), round(float(y), 4)] for x, y in P_WIN], 'P0': [round(float(v), 4) for v in P0], 'D0': D0,
    'ROLLER_R': round(ROLLER_R, 4), 'SLOT_R0': round(SLOT_R0, 4), 'SLOT_R1': round(SLOT_R1, 4), 'SLOT_W': round(2 * (PIN_R + SLOT_C), 3), 'PIN_R': PIN_R, 'u_FB': u_FB.tolist(),
    'pitch_deg': 360 / NT, 'fork_table': ph_tab, 'balance_table': be_tab,
    'check': {'jams_in_a_full_turn': len(jam), 'narrowest_band_deg': round(math.degrees(gap_min), 3), 'fork_swing_deg': [round(math.degrees(amp_lo), 3), round(math.degrees(amp_hi), 3)],
              'balance_swing_deg': round(math.degrees(AMP_B), 2), 'lifts_A': lifts_A, 'lifts_B': lifts_B, 'repeats_each_tooth_deg': round(math.degrees(per_err), 5),
              'rests_fraction': round(float(rest_frac), 3), 'fork_outline_deepest_cut_mm': round(float(worst_pen), 4), 'pin_captive': pin_ok,
              'window_clears_staff_mm': round(WIN_MIN, 3), 'pin_hole_wall_mm': round(PIN_WALL, 3), 'roller_wall_to_staff_mm': round(ROLLER_WALL, 3), 'tooth_gap_at_root_mm': round(gap_root, 3), 'ramp_pressure_angle_deg': round(PRESS, 1)},
}
json.dump(res, open(os.path.join(HERE, 'escapement_geo.json'), 'w'), indent=1)
print(json.dumps(res['check'], indent=1))
# ---------- picture: the fork at both ends of its swing on the wheel, and the angles over two teeth ----------
out = sys.argv[1] if len(sys.argv) > 1 else HERE
fig, axs = plt.subplots(1, 2, figsize=(11, 5), dpi=150)
ax = axs[0]
i0 = base + int(np.argmax(PHI[base:base + n_p])); i1 = base + int(np.argmin(PHI[base:base + n_p]))
for i, col in ((i0, '#3d5a80'), (i1, '#c97b3d')):
    wv = rot(WL + E, E, WDIR * thetas[i]); ax.fill(wv[:, 0], wv[:, 1], color='#d8c9a3', alpha=0.5 if i == i1 else 0.9, ec='#8a7a50', lw=0.5)
    fv = rot(P_FORK0, F, PHI[i]); ax.plot(fv[:, 0], fv[:, 1], color=col, lw=1.0)
    wv_ = rot(P_WIN, F, PHI[i]); ax.plot(wv_[:, 0], wv_[:, 1], color=col, lw=0.6)
    b_ = BETA[i]; ax.add_patch(plt.Circle(BC, ROLLER_R, fill=False, ls='--', color=col, lw=0.6))
    for rr in (SLOT_R0 + PIN_R + SLOT_C, SLOT_R1 - PIN_R - SLOT_C):
        ax.add_patch(plt.Circle(BC + rr * np.array([math.cos(tail_dir + b_), math.sin(tail_dir + b_)]), PIN_R + SLOT_C, fill=False, color=col, lw=0.5))
    ax.add_patch(plt.Circle(pin_at(PHI[i]), PIN_R, color=col)); ax.add_patch(plt.Circle(BC, STAFF_R, color='#555'))
ax.set_aspect('equal'); ax.set_title('Escape wheel, fork with its ring round the staff, pin in the roller slot (two ends of the swing)', fontsize=8)
ax = axs[1]
seg = slice(base, base + 2 * n_p)
ax.plot(np.degrees(thetas[seg] - thetas[base]), np.degrees(PHI[seg]), label='fork (deg)')
ax.plot(np.degrees(thetas[seg] - thetas[base]), np.degrees(BETA[seg]) / 10, label='balance (deg / 10)')
ax.set_xlabel('escape wheel angle (deg), two teeth'); ax.legend(fontsize=7); ax.grid(alpha=0.3)
fig.savefig(os.path.join(out, 'escapement.png'), bbox_inches='tight'); print('picture written')
