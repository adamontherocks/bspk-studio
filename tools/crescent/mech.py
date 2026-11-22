import os
HERE = os.path.dirname(os.path.abspath(__file__))
# Kinematic prototype of the retrograde minute + lever kick + jumping hour star (2.5D, contact from shapes).
import math, json, sys
def pol(c, r, a): return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
def rot(p, c, a): x, y = p[0] - c[0], p[1] - c[1]; ca, sa = math.cos(a), math.sin(a); return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)
def inside(p, poly):
    c = False; n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < a[0] + (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]): c = not c
    return c
P = {k: tuple(v) for k, v in json.load(open(os.path.join(HERE, 'search_best.json'))).items()}
G = json.load(open(os.path.join(HERE, 'crescent_geo.json')))
C = P['C']; Q = tuple(G['Q']); L = tuple(G['L_options'][0])
# ---- snail on the centre arbor: r 8 -> 20 over one turn (CCW in its own frame), then a radial cliff
R0, R1 = 8.0, 20.0
DIR = 1   # the centre arbor turns anticlockwise (so the seconds, three meshes on, turn clockwise); the spiral grows clockwise in its own frame
SLANT = math.radians(-6)   # the cliff is undercut 6 deg (a beak), so the nose drops clear in one step instead of sliding down the face
SNAIL = [pol((0, 0), R0 + (R1 - R0) * k / 720, -DIR * 2 * math.pi * k / 720) for k in range(720)] + [pol((0, 0), R1 - (R1 - R0) * j / 8, -DIR * (2 * math.pi + SLANT * j / 8)) for j in range(9)]
def snail_world(thC): return [rot((C[0] + x, C[1] + y), C, thC) for x, y in SNAIL]
# ---- lever: nose at Lf from L, spring pushes toward smaller angle (clockwise); rack ratio 36/12
LF = 17.0; RATIO = 36 / 12
th_LC = math.atan2(C[1] - L[1], C[0] - L[0])
def nose(th): return pol(L, LF, th)
def solve_lever(thC, th_prev, th_stop, step=math.radians(0.05)):
    sw = snail_world(thC)
    def bis(a, b):           # a inside, b outside
        for _ in range(30):
            m = (a + b) / 2
            if inside(nose(m), sw): a = m
            else: b = m
        return b
    th = th_prev
    if inside(nose(th), sw):                    # the snail pushed the nose: move out (CCW)
        while inside(nose(th), sw): th += step
        return bis(th - step, th), True
    while th - step > th_stop and not inside(nose(th - step), sw): th -= step   # the spring pulls it in until it touches
    if th - step <= th_stop: return th_stop, False
    return bis(th - step, th), True
# which side of L->C does the nose sit on? choose the branch where |nose-C| grows with angle
alpha_min = math.acos((22 ** 2 + LF ** 2 - R0 ** 2) / (2 * 22 * LF)) if False else None
dLC = math.dist(L, C)
def r_at(th): return math.dist(nose(th), C)
cands = []
for sgn in (1, -1):
    a8 = math.acos((dLC ** 2 + LF ** 2 - R0 ** 2) / (2 * dLC * LF)); a20 = math.acos((dLC ** 2 + LF ** 2 - R1 ** 2) / (2 * dLC * LF))
    cands.append((sgn, th_LC + sgn * a8, th_LC + sgn * a20))
sgn, th8, th20 = [c for c in cands if c[2] > c[1]][0]            # lever turns CCW (increasing angle) as the snail grows
TH_STOP = th8 - math.radians(1.5)                                 # stop pin 1.5 deg below the snail's lowest contact
print('lever: dLC', round(dLC, 2), 'nose angle range', round(math.degrees(th8), 2), '->', round(math.degrees(th20), 2), 'swing', round(math.degrees(th20 - th8), 2), 'hand sweep', round(math.degrees(th20 - th8) * RATIO, 1))
# ---- time loop: centre arbor turns clockwise once an hour; find the snail phase that puts the cliff under the nose at minute 0
psi = math.atan2(nose(th8)[1] - C[1], nose(th8)[0] - C[0])        # direction from C to the nose at its lowest
# local angle under the nose = psi - thC; want local angle 0+ (just after the cliff) at t = 0 -> thC(0) = psi - tiny
omega = DIR * 2 * math.pi / 3600
def thC(t): return psi + DIR * 1e-4 + omega * t
out = []; th = th8
for t in range(-120, 7201, 10):
    th, touching = solve_lever(thC(t), th, TH_STOP)
    out.append((t, math.degrees(th), touching))
def at(t): return [o for o in out if o[0] == t][0]
for t in (0, 900, 1800, 2700, 3590, 3600, 3610, 5400):
    o = at(t); print(f'  t {t:5d} s  lever {o[1]:8.3f}  touching {o[2]}')
lin = [(o[0], o[1]) for o in out if 0 <= o[0] <= 3580]
d = [lin[i + 1][1] - lin[i][1] for i in range(len(lin) - 1)]
print('lever step per 10 s over the hour: min', round(min(d), 4), 'max', round(max(d), 4), '(steady = linear minutes)'); print('fly-back between', [ (out[i][0], round(out[i][1],2), round(out[i+1][1],2)) for i in range(len(out)-1) if out[i+1][1] < out[i][1] - 5])
json.dump({'L': L, 'Q': Q, 'C': C, 'LF': LF, 'th8': th8, 'th20': th20, 'TH_STOP': TH_STOP, 'psi': psi, 'R0': R0, 'R1': R1}, open(os.path.join(HERE, 'mech_lever.json'), 'w'))
