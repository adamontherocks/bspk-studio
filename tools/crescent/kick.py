import os
HERE = os.path.dirname(os.path.abspath(__file__))
# Lever kick: pawl on the rack lever rides over one ratchet tooth per hour, kicks the hour star at fly-back; jumper snaps it home.
import math, json
exec(open(os.path.join(HERE, 'mech.py')).read().split("# ---- time loop")[0])          # snail, lever, solve_lever, th8, th20, TH_STOP
M = json.load(open(os.path.join(HERE, 'mech_lever.json'))); psi = M['psi']
omega = DIR * 2 * math.pi / 3600
T_FB = float(os.environ.get('T_FB', '0'))                                                      # measured: fly-back came 65 s after t = 0; shift so it lands on the hour
def thC(t): return psi + DIR * 1e-4 + omega * (t + T_FB)
# ---- hour arbor H, ratchet wheel (12 teeth, radial steep face), display star (12 points) and jumper
LK = 9.0; DLH = 18.5; GAMMA = math.radians(-80)
H = pol(L, DLH, GAMMA)
th_mid = (th8 + th20) / 2; BETA = GAMMA - th_mid                   # pawl direction on the lever: toward H at mid-swing
RT, RF = 11.0, 8.0                                               # ratchet tip and root radius
PITCH = 2 * math.pi / 12
def ratchet(sig):            # each tooth: radial steep face at a0 (material on its CCW side), back slope falling to the root over 80 % of the pitch
    pts = []
    for k in range(12):
        a0 = sig + PITCH * k
        pts += [pol(H, RF, a0 - 1e-3), pol(H, RT, a0), pol(H, RF, a0 + 0.8 * PITCH)]
        pts += [pol(H, RF, a0 + 0.8 * PITCH + (0.2 * PITCH) * j / 4) for j in range(1, 4)]
    return pts
def tip(th, defl=0.0):                                           # pawl tip; deflection moves it radially away from H
    p = pol(L, LK, th + BETA); dx, dy = p[0] - H[0], p[1] - H[1]; r = math.hypot(dx, dy)
    return (H[0] + dx / r * (r + defl), H[1] + dy / r * (r + defl))
APEX = math.radians(15)
phi = lambda p: math.atan2(p[1] - H[1], p[0] - H[0])
GAP = math.radians(16)
SEAT0 = phi(tip(th20)) + GAP            # a steep face 16 deg ahead of the tip at the top of the hour
def run(hours=12, dt=10, gap=None):
    global SEAT0
    if gap is not None: SEAT0 = phi(tip(th20)) + gap
    th = th8; k = 0; sig = SEAT0; max_defl = 0.0; pushes = []; peak = 0.0
    t = -60.0
    while t <= hours * 3600 + 60:
        th_new, touching = solve_lever(thC(t), th, TH_STOP)
        if th_new < th - 1e-6:                                     # returning: the pawl is rigid (on its stop) and pushes the ratchet
            a = th
            while a > th_new:
                a = max(th_new, a - math.radians(0.1)); p = tip(a); n = 0
                while inside(p, ratchet(sig)) and n < 4000: sig += math.radians(0.05); n += 1
            peak = max(peak, sig - (SEAT0 + k * PITCH))
        else:                                                      # climbing: the pawl's flexure rides over the back slopes
            d = 0.0
            while inside(tip(th_new, d), ratchet(sig)) and d < 6: d += 0.02
            max_defl = max(max_defl, d)
            off = sig - (SEAT0 + k * PITCH)
            if off > 1e-9:                                         # the push has ended: the jumper decides
                if off > APEX: k += 1
                pushes.append((round(t), round(math.degrees(peak), 2), k)); sig = SEAT0 + k * PITCH; peak = 0.0
        th = th_new; t += dt
    return pushes, max_defl
for g in (16, 12, 9, 6):
    pushes, md = run(12, gap=math.radians(g))
    ok = len(pushes) == 12 and all(p[2] == i + 1 for i, p in enumerate(pushes))
    print(f'gap {g:2d} deg: {len(pushes)} kicks, pushes {sorted(set(p[1] for p in pushes))} deg, final hour index {pushes[-1][2] if pushes else 0}, pawl deflection {md:.2f} mm, every hour advanced once: {ok}')
pushes, max_defl = run(12, gap=math.radians(9))
print('H', [round(v, 2) for v in H], '|H|', round(math.hypot(*H), 1), ' pawl max deflection on the forward stroke', round(max_defl, 2), 'mm')
print('fly-backs (time s, ratchet push deg, hour index):'); [print('  ', p) for p in pushes]
