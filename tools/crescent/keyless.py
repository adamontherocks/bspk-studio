# Keyless works for Crescent: the crown's stem lies in a channel on the main plate's underside (z = 0),
# and its 8-leaf winding pinion meshes 24 steel pins (Ø1) standing up from the pin wheel underneath.
#
# This script
#   1. generates the winding pinion's leaves by rolling the real pins through a blank (a hob's cut, so the
#      pinion is conjugate to the pins by construction, with 0.1 mm clearance on each flank),
#   2. proves the mesh with an independent test on the finished outline: at every crown angle no pin is
#      inside a leaf, and a pin is always within a small turn of the crown in either direction (so the
#      crown always drives the pin wheel, both ways), and
#   3. writes keyless_geo.json for make_crescent.py and a picture of the mesh.
import json, math, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
HERE = os.path.dirname(os.path.abspath(__file__))

N_LEAF, N_PIN = 8, 24
PITCH = 3.0                         # pin pitch on the pin circle (mm)
R_PIN = N_PIN * PITCH / (2 * math.pi)   # pin circle radius 11.459
R_P = N_LEAF * PITCH / (2 * math.pi)    # winding pinion pitch radius 3.820
PIN_D = 1.0                         # Ø1 steel pins (bought dowels)
CLEAR = 0.1                         # flank clearance each side (backlash)
ADD = 1.0                           # leaf addendum: tip radius = R_P + ADD
R_TIP = R_P + ADD
Z_STEM = 0.0                        # stem axis at the plate's underside face (half in a plate channel, half in a strap)
PIN_TIP = Z_STEM - R_P + 0.6        # pins reach 0.6 mm past the pitch line: -3.22
ROOT_GAP = 0.25                     # pin tip to leaf root
DISC_TOP = Z_STEM - R_TIP - 0.4     # pin wheel disc top, 0.4 under the leaf tips: -5.22
BORE_R, BORE_FLAT = 1.0, 0.7        # D bore for the Ø2 stem, flat at 0.7 from the axis

# ---------- 1. generate one leaf space by rolling a pin through it ----------
h = 0.008
g = np.arange(-R_TIP - 0.2, R_TIP + 0.2 + h / 2, h)
U, V = np.meshgrid(g, g)
space = np.zeros_like(U, dtype=bool)
hw = PIN_D / 2 + CLEAR
top = PIN_TIP + ROOT_GAP
for phi in np.arange(-1.45, 1.45, 0.0015):
    psi = R_P * phi / R_PIN                       # pin wheel turns with the pinion's pitch circle
    if abs(psi) > math.pi / 2: continue
    uc, vshift = R_PIN * math.sin(psi), 0.0       # pin centre across the pinion plane (true circle, not a rack)
    c, s = math.cos(phi), math.sin(phi)
    # body-frame grid point -> world: rotate by +phi
    UW = c * U - s * V; VW = s * U + c * V
    inside = (np.abs(UW - uc) <= hw) & (VW <= top - hw)
    inside |= (UW - uc) ** 2 + (VW - (top - hw)) ** 2 <= hw ** 2     # rounded cutter tip
    space |= inside
# the pinion: blank minus 8 copies of the space, minus the D bore
pin_body = (U ** 2 + V ** 2 <= R_TIP ** 2)
for k in range(N_LEAF):
    a = 2 * math.pi * k / N_LEAF
    c, s = math.cos(a), math.sin(a)
    UR = c * U + s * V; VR = -s * U + c * V      # rotate the grid back by a to look up the bottom space
    # nearest-cell lookup into 'space'
    iu = np.clip(np.round((UR - g[0]) / h).astype(int), 0, len(g) - 1); iv = np.clip(np.round((VR - g[0]) / h).astype(int), 0, len(g) - 1)
    pin_body &= ~space[iv, iu]
bore = (U ** 2 + V ** 2 <= BORE_R ** 2) & (V <= BORE_FLAT)
pin_body &= ~bore
# what a Ø1.0 end mill actually leaves: open the cut-away region by r 0.5 (corners it can't reach stay as material)
from scipy import ndimage
rr = int(round(0.5 / h)); yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]; disk = xx ** 2 + yy ** 2 <= rr ** 2
designed = pin_body.copy()
cutaway = np.pad(~pin_body, rr + 2, constant_values=True)
made = ~ndimage.binary_dilation(ndimage.binary_erosion(cutaway, disk), disk)[rr + 2:-(rr + 2), rr + 2:-(rr + 2)]
left_by_tool = float((made & ~designed).sum() * h * h)
pin_body = made
cs = plt.contour(U, V, pin_body.astype(float), levels=[0.5]); segs = cs.allsegs[0]; plt.close('all')
def area(s_): return abs(np.sum(s_[:, 0] * np.roll(s_[:, 1], -1) - np.roll(s_[:, 0], -1) * s_[:, 1])) / 2
segs = sorted(segs, key=area, reverse=True)
outer, hole = segs[0], segs[1]
# thin the outline to about 0.05 mm steps
def thin(s_, step=0.05):
    out = [s_[0]]
    for p in s_[1:]:
        if np.hypot(*(p - out[-1])) >= step: out.append(p)
    return np.array(out)
outer, hole = thin(outer), thin(hole, 0.04)

# ---------- 2. prove the mesh on the finished outline ----------
P_OUT, P_HOLE = MP(outer), MP(hole)
def in_pinion(pts):
    return P_OUT.contains_points(pts) & ~P_HOLE.contains_points(pts)
# a pin seen in the pinion's plane: a 1.0 wide bar from the disc to its tip (0.15 chamfer), sampled densely on its boundary and inside
def pin_samples(uc):
    vs = np.linspace(DISC_TOP, PIN_TIP - 0.15, 60)
    side = [(uc - 0.5, v) for v in vs] + [(uc + 0.5, v) for v in vs]
    tipl = [(uc - 0.5 + 0.15 * t, PIN_TIP - 0.15 + 0.15 * t) for t in np.linspace(0, 1, 6)] + [(uc + 0.5 - 0.15 * t, PIN_TIP - 0.15 + 0.15 * t) for t in np.linspace(0, 1, 6)]
    topl = [(uc - 0.35 + 0.7 * t, PIN_TIP) for t in np.linspace(0, 1, 12)]
    fill = [(uc + du, v) for du in np.linspace(-0.45, 0.45, 7) for v in np.linspace(DISC_TOP, PIN_TIP - 0.2, 20)]
    return np.array(side + tipl + topl + fill)
def pins_world(theta):
    """pins in the pinion's plane when the pinion has turned theta (the pin wheel turns R_P/R_PIN as much)"""
    psi0 = R_P * theta / R_PIN
    out = []
    for k in range(N_PIN):
        psi = psi0 + 2 * math.pi * k / N_PIN
        psi = (psi + math.pi) % (2 * math.pi) - math.pi
        if abs(psi) < math.radians(40): out.append(R_PIN * math.sin(psi))
    return out
def hits(theta, pinion_extra):
    """does the pinion, turned theta + pinion_extra with the pins held at theta, touch a pin?"""
    c, s = math.cos(-(theta + pinion_extra)), math.sin(-(theta + pinion_extra))
    for uc in pins_world(theta):
        P = pin_samples(uc)
        B = np.c_[c * P[:, 0] - s * P[:, 1], s * P[:, 0] + c * P[:, 1]]   # pin points into the pinion's body frame
        if in_pinion(B).any(): return True
    return False
def free_turn(theta, sign, limit=math.radians(25), step=math.radians(0.1)):
    d = 0.0
    while d < limit:
        d += step
        if hits(theta, sign * d): return d
    return None
lead = 2 * math.pi / N_LEAF
worst_int, back_f, back_b = [], [], []
for th in np.linspace(0, lead, 91):
    if hits(th, 0.0): worst_int.append(math.degrees(th))
    f, b = free_turn(th, +1), free_turn(th, -1)
    back_f.append(math.degrees(f) if f else None); back_b.append(math.degrees(b) if b else None)
ok_int = not worst_int
ok_drive = all(x is not None for x in back_f + back_b)
# leaf thickness at the pitch circle and at the tip, and the narrowest space (for the 1 mm end mill)
def chord_at(r):
    a = np.linspace(-math.pi / 2 - lead / 2, -math.pi / 2 + lead / 2, 4000)
    pts = np.c_[r * np.cos(a), r * np.sin(a)]; m = in_pinion(pts)
    solid = m.sum() / len(m) * lead * r; return solid, lead * r - solid
leaf_pitch, space_pitch = chord_at(R_P); leaf_tip, _ = chord_at(R_TIP - 0.05); _, space_root = chord_at(PIN_TIP * -1 + 0.05 if False else (R_P - 0.6 + ROOT_GAP) + 0.05)
res = {
    'N_LEAF': N_LEAF, 'N_PIN': N_PIN, 'PITCH': PITCH, 'R_PIN': R_PIN, 'R_P': R_P, 'R_TIP': R_TIP, 'Z_STEM': Z_STEM,
    'PIN_TIP': PIN_TIP, 'DISC_TOP': DISC_TOP, 'PIN_D': PIN_D, 'CLEAR': CLEAR,
    'pinion_outer': [[round(float(a), 4), round(float(b), 4)] for a, b in outer],
    'pinion_bore': [[round(float(a), 4), round(float(b), 4)] for a, b in hole],
    'check': {'interference_at_deg': worst_int, 'drives_both_ways_every_angle': ok_drive,
              'free_turn_forward_deg': [round(min(x for x in back_f if x), 2), round(max(x for x in back_f if x), 2)] if ok_drive else None,
              'free_turn_back_deg': [round(min(x for x in back_b if x), 2), round(max(x for x in back_b if x), 2)] if ok_drive else None,
              'leaf_at_pitch_mm': round(leaf_pitch, 3), 'space_at_pitch_mm': round(space_pitch, 3), 'leaf_at_tip_mm': round(leaf_tip, 3),
              'space_near_root_mm': round(space_root, 3), 'material_the_1mm_tool_leaves_mm2': round(left_by_tool, 4), 'outline_is_as_machined_with_1mm_end_mill': True},
}
json.dump(res, open(os.path.join(HERE, 'keyless_geo.json'), 'w'), indent=1)
print(json.dumps(res['check'], indent=1))
print(f'pin circle R {R_PIN:.3f}, pinion pitch r {R_P:.3f}, tip r {R_TIP:.3f}, pins {DISC_TOP:.2f}..{PIN_TIP:.2f}')
# ---------- 3. picture ----------
fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=160)
ax.fill(outer[:, 0], outer[:, 1], color='#c9ccd1', ec='#555', lw=0.6); ax.fill(hole[:, 0], hole[:, 1], color='white', ec='#555', lw=0.6)
for uc in pins_world(0.0):
    ax.add_patch(plt.Rectangle((uc - 0.5, DISC_TOP), 1.0, PIN_TIP - DISC_TOP, color='#3d5a80'))
ax.add_patch(plt.Rectangle((-R_TIP - 2, DISC_TOP - 1.6), 2 * R_TIP + 4, 1.6, color='#d8c9a3'))
ax.add_patch(plt.Circle((0, 0), R_P, fill=False, ls='--', lw=0.5, color='#888'))
ax.set_aspect('equal'); ax.set_xlim(-6.5, 6.5); ax.set_ylim(-7.5, 5.5); ax.set_title('Winding pinion (8 leaves) on the pin wheel\'s steel pins, side view', fontsize=8)
fig.savefig(os.path.join(sys.argv[1] if len(sys.argv) > 1 else HERE, 'keyless_mesh.png'), bbox_inches='tight'); print('picture written')
