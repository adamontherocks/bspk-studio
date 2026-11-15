# Estimated layout of the Slava 5671 engine, in its own frame seen from the dial side (x right, y up, mm).
# From the manual's Fig. 1 (back view, mirrored here): going barrel ~16.4 mm from the center arbor toward upper right,
# balance staff ~18.2 mm away toward lower left. Train in between; tooth counts are plausible guesses (not published)
# chosen to give the published rates: center 1/h, seconds wheel 1/min, 15-tooth escape wheel at 18,000 bph.
import math, json
R_MOV = 55.8 / 2
B = (16.4 * math.cos(math.radians(38.8)), 16.4 * math.sin(math.radians(38.8)))
BAL = (-7.4, -16.6)
L_CT, L_TF, L_FE, L_EB = 0.3 * (60 + 8) / 2, 0.25 * (64 + 8) / 2, 0.2 * (60 + 6) / 2, 1.366 * 6.75
R = {'cw': 9.0 + 0.3, 'tw': 8.0 + 0.25, 'fw': 6.0 + 0.2, 'esc': 3.375 + 0.45, 'drum': 14.4 - 0.5 - 0.5}
def inter(c1, r1, c2, r2):
    d = math.dist(c1, c2)
    if d > r1 + r2 or d < abs(r1 - r2) or d == 0: return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d); h = math.sqrt(max(0, r1 * r1 - a * a))
    ux, uy = (c2[0] - c1[0]) / d, (c2[1] - c1[1]) / d; mx, my = c1[0] + a * ux, c1[1] + a * uy
    return [(mx - h * uy, my + h * ux), (mx + h * uy, my - h * ux)]
best = None
for ai in range(360):
    a = math.radians(ai); T = (L_CT * math.cos(a), L_CT * math.sin(a))
    for bi in range(360):
        b = math.radians(bi); F = (T[0] + L_TF * math.cos(b), T[1] + L_TF * math.sin(b))
        for E in inter(F, L_FE, BAL, L_EB):
            pts = {'T': T, 'F': F, 'E': E}
            pen = 0
            for k, p in pts.items():
                pen += max(0, 14.6 - math.dist(p, B)) * 5                     # clear of the barrel drum
                pen += max(0, math.hypot(*p) + {'T': R['tw'], 'F': R['fw'], 'E': R['esc']}[k] - (R_MOV - 1)) * 5
            pen += max(0, 10.0 - math.hypot(*F)) * 5 + max(0, 10.0 - math.hypot(*E)) * 5   # center wheel clear of their arbors
            pen += max(0, 9.0 - math.dist(T, E)) * 2 + max(0, R['tw'] + 0.7 - math.dist(T, E)) * 5
            score = pen + 0.01 * (math.dist(T, B) < 20)
            if best is None or score < best[0]: best = (score, T, F, E)
score, T, F, E = best
P = (E[0] + (3.9 / L_EB) * (BAL[0] - E[0]), E[1] + (3.9 / L_EB) * (BAL[1] - E[1]))
frame = {'center': (0.0, 0.0), 'sl_barrel': B, 'sl_third': T, 'sl_fourth': F, 'sl_escape': E, 'sl_fork': P, 'sl_balance': BAL}
print('penalty', round(score, 3))
for k, p in frame.items(): print(f'{k:11s} ({p[0]:7.2f}, {p[1]:7.2f})  r {math.hypot(*p):5.2f}')
# Rotate the whole engine about its center arbor so the balance points at the case's center line, then sit it on the minute disc arbor.
C = (26.25, 0.0)
rot = math.pi - math.atan2(BAL[1], BAL[0])
cr, sr = math.cos(rot), math.sin(rot)
world = {k: [C[0] + p[0] * cr - p[1] * sr, C[1] + p[0] * sr + p[1] * cr] for k, p in frame.items()}
print('rotation', round(math.degrees(rot), 2))
for k, p in world.items(): print(f'world {k:11s} ({p[0]:7.2f}, {p[1]:7.2f})')
json.dump({'rot': rot, 'world': world, 'frame': frame}, open(__file__.replace('layout.py', 'layout.json'), 'w'))
