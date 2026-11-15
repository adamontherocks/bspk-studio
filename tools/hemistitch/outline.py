# The case outline as true geometry: straight sides, r 10 corners, top/bottom bows tangent to the corners.
# Sampled with evenly spaced smooth dots so the sim's uniform Catmull-Rom follows it without wiggles.
import math
S = 2.5
HX, HY, CR, SAG = 25 * S, 14.5 * S, 4 * S, 4.25
APEX = HY + SAG                       # 40.5
CX, CY = HX - CR, HY - CR             # corner centre (52.5, 26.25)
# bow circle centre (0, APEX - R), internally tangent to the corner circle: |(CX, CY - APEX + R)| = R - CR
R = (CX ** 2 + (CY - APEX) ** 2 - CR ** 2) / (2 * (CY - APEX) + 2 * CR) * -1
R = (CX ** 2 + (APEX - CY) ** 2 - CR ** 2) / (2 * (APEX - CY) - 2 * CR)
BY = APEX - R
ux, uy = CX / (R - CR), (CY - BY) / (R - CR)          # bow centre → corner centre, unit
TANG = math.degrees(math.atan2(uy, ux))              # corner arc runs 0° → TANG in the first quadrant
def quarter():   # first quadrant, from (HX, 0) counter-clockwise to (0, APEX): list of primitives
    return [('line', (HX, 0), (HX, CY)),
            ('arc', (CX, CY), CR, 0.0, TANG),
            ('arc', (0.0, BY), R, TANG, 90.0)]
def length(p):
    if p[0] == 'line': return math.dist(p[1], p[2])
    return p[2] * math.radians(p[4] - p[3])
def at(p, s):    # point at arc length s along primitive p
    if p[0] == 'line':
        L = length(p); t = s / L
        return (p[1][0] + (p[2][0] - p[1][0]) * t, p[1][1] + (p[2][1] - p[1][1]) * t)
    a = math.radians(p[3]) + s / p[2]
    return (p[1][0] + p[2] * math.cos(a), p[1][1] + p[2] * math.sin(a))
def quarter_points(n):   # n points from (HX,0) inclusive to (0,APEX) exclusive, evenly by arc length
    Q = quarter(); L = sum(length(p) for p in Q); out = []
    for k in range(n):
        s = L * k / n
        for p in Q:
            if s <= length(p) + 1e-9: out.append(at(p, s)); break
            s -= length(p)
    return out, L
def outline(nq):
    q, L = quarter_points(nq)
    q2 = [(-x, y) for x, y in reversed(q[1:])] + [(0.0, APEX)]   # second quadrant: mirror, from just past apex
    top = q + [(0.0, APEX)] + [(-x, y) for x, y in reversed(q[1:])] + [(-HX, 0.0)]
    pts = top + [(x, -y) for x, y in reversed(top[1:-1])]
    return [{'u': round(x, 4), 'v': round(y, 4), 'smooth': True} for x, y in pts], 4 * L
if __name__ == '__main__':
    print('bow R', round(R, 2), 'tangent at', round(TANG, 2), '°')
    def bez(P, s, t):
        n = len(P); a, b = P[s], P[(s + 1) % n]
        tan = lambda i: ((P[(i + 1) % n]['u'] - P[(i - 1) % n]['u']) / 6, (P[(i + 1) % n]['v'] - P[(i - 1) % n]['v']) / 6)
        ta, tb = tan(s), tan((s + 1) % n); m = 1 - t
        c1 = (a['u'] + ta[0], a['v'] + ta[1]); c2 = (b['u'] - tb[0], b['v'] - tb[1])
        return (m**3*a['u'] + 3*m*m*t*c1[0] + 3*m*t*t*c2[0] + t**3*b['u'], m**3*a['v'] + 3*m*m*t*c1[1] + 3*m*t*t*c2[1] + t**3*b['v'])
    def true_dist(x, y):   # distance from the true outline (first quadrant by symmetry)
        x, y = abs(x), abs(y)
        d = [abs(x - HX) if y <= CY else 1e9]
        ang = math.degrees(math.atan2(y - CY, x - CX))
        if 0 <= ang <= TANG: d.append(abs(math.dist((x, y), (CX, CY)) - CR))
        ang2 = math.degrees(math.atan2(y - BY, x))
        if TANG <= ang2 <= 90: d.append(abs(math.dist((x, y), (0, BY)) - R))
        return min(d)
    for nq in (6, 8, 10, 12, 16):
        P, L = outline(nq)
        samp = [bez(P, s, j / 24) for s in range(len(P)) for j in range(24)]
        dev = max(true_dist(*p) for p in samp)
        n = len(samp); cross = [(samp[(i+1)%n][0]-samp[i][0])*(samp[(i+2)%n][1]-samp[(i+1)%n][1]) - (samp[(i+1)%n][1]-samp[i][1])*(samp[(i+2)%n][0]-samp[(i+1)%n][0]) for i in range(n)]
        concave = sum(1 for c in cross if c < -1e-9)
        print(f'{len(P)} dots, spacing {L / len(P):.2f} mm: max deviation {dev:.4f} mm, concave turns {concave}, extents x {max(p[0] for p in samp):.3f} y {max(p[1] for p in samp):.3f}')
    # the current outline, for comparison
    hx, hy, cr = HX, HY, CR; case = []
    def corner(cx, cy, a0):
        for k in range(3):
            a = math.radians(a0 + 45 * k); case.append({'u': cx + cr * math.cos(a), 'v': cy + cr * math.sin(a)})
    corner(hx - cr, hy - cr, 0); case.append({'u': 0, 'v': hy + SAG}); corner(-(hx - cr), hy - cr, 90); corner(-(hx - cr), -(hy - cr), 180); case.append({'u': 0, 'v': -(hy + SAG)}); corner(hx - cr, -(hy - cr), 270)
    samp = [bez(case, s, j / 24) for s in range(len(case)) for j in range(24)]
    n = len(samp); cross = [(samp[(i+1)%n][0]-samp[i][0])*(samp[(i+2)%n][1]-samp[(i+1)%n][1]) - (samp[(i+1)%n][1]-samp[i][1])*(samp[(i+2)%n][0]-samp[(i+1)%n][0]) for i in range(n)]
    print(f'current 14 dots: max deviation {max(true_dist(*p) for p in samp):.4f} mm, concave turns {sum(1 for c in cross if c < -1e-9)}, extents x {max(p[0] for p in samp):.3f} y {max(p[1] for p in samp):.3f}')
