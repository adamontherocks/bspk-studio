# Retrograde lever, version 2 (2026-11-18, Adam's notes P26, P27): the feeler pin beefed up to Ø1.5 steel and moved closer to the
# lever's body, on a straight 4 mm arm with a round end concentric with the pin (the fork's shaft family), and the snail re-cut for it.
#
# The snail is a conjugate cam: over the hour the lever must turn at a constant rate (lever angle = pose + swing * t / 3600) so the
# retrograde hand reads a uniform minute track. Its edge is the path of the feeler pin's centre in the snail's own frame, a pin's
# radius in, closed by the cliff: the pin's own drop path about the lever pivot (undercut 5 deg so the pin falls clear in one step).
# The same recipe as make_crescent.py; this rebuilds it from the scene (pivot, pose, swing) so it can be re-run for a new pin.
#
#   apply(J, log, LF=15.0, PIN_R=0.75)   (refine.py calls it); python3 retro2.py SCENE.json checks it rebuilds the current snail
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, offset, union, diff, inter, circle, area, ccw
import pyclipper as pc

UNDER = math.radians(5.0)
def polr(c, r, a): return np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a)])
def rotp(p, c, a):
    x, y = p[0] - c[0], p[1] - c[1]; ca, sa = math.cos(a), math.sin(a); return np.array([c[0] + x * ca - y * sa, c[1] + x * sa + y * ca])
def capsule(a, b, r):
    o = pc.PyclipperOffset(); o.ArcTolerance = 0.002 * 1e4; o.AddPath(P([a, b]), pc.JT_ROUND, pc.ET_OPENROUND); return o.Execute(r * 1e4)
def pin_locus(L, C, LF, th0, swing):
    """the feeler pin's centre over the hour in the snail's frame as drawn (t = 0), closed by the undercut cliff"""
    loc = [rotp(polr(L, LF, th0 + swing * k / 720), C, -2 * math.pi * k / 720) for k in range(720)]
    drop = [rotp(polr(L, LF, th0 + swing * (1 - j / 12)), C, UNDER * j / 12) for j in range(13)]
    return np.array(loc + drop)
def cam(L, C, LF, th0, swing, pin_r):
    loc = pin_locus(L, C, LF, th0, swing)
    return offset([P(ccw(loc))], -pin_r)
def parts(J):
    st = J['state']; m = J['project']['mechanisms']; D = {d['id']: d for d in st['drawn']}
    sv = next(s for s in m['solve'] if s['id'] == 'lever')
    return st, m, D, sv
def apply(J, log, LF=15.0, PIN_R=0.75, ARM_R=2.0):
    st, m, D, sv = parts(J); SK = {k['id']: k for k in st['sketches']}
    L = np.array(sv['pivot'], float); C = np.array(st['pos']['center'], float); N0 = np.array(sv['nose'], float)
    th0 = math.atan2(N0[1] - L[1], N0[0] - L[0]); LF0 = float(np.hypot(*(N0 - L)))
    swing = math.radians(m['expect']['hand_sweep'] / 3)
    snail, lever, feeler = D[sv['cam']], next(d for d in st['drawn'] if d['name'].startswith('Retrograde lever')), D[sv['part']]
    if abs(LF0 - LF) < 1e-3 and abs(sv['noseR'] - PIN_R) < 1e-3: return            # already done
    old_cam = [P(ccw(np.array([(q['u'], q['v']) for q in SK[snail['sketch']]['points']])))]
    new_cam = cam(L, C, LF, th0, swing, PIN_R)
    big = max([p for p in new_cam if pc.Orientation(p)], key=lambda p: abs(pc.Area(p)))
    SK[snail['sketch']]['points'] = [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in F(big)]
    snail['name'] = f'Snail (minute cam, cut for the Ø{2 * PIN_R:g} feeler pin)'
    N1 = polr(L, LF, th0)
    # the lever: the old feeler arm's tip goes, a straight 4 mm arm runs from the hub to a round end on the new pin
    lev = [P(ccw(np.array([(q['u'], q['v']) for q in SK[lever['sketch']]['points']])))]
    arm = capsule(L, N1, ARM_R)
    old_tip = diff(union([circle(N0, 1.3 + 0.6)], capsule(N1, N0, 1.3 + 0.6)), arm)
    lev2 = union(diff(lev, old_tip), arm)
    lev2 = [max([p for p in lev2 if pc.Orientation(p)], key=lambda p: abs(pc.Area(p)))]
    SK[lever['sketch']]['points'] = [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in F(lev2[0])]
    for c in lever.get('cuts', []):
        if c['kind'] == 'hole' and c['name'].startswith('Feeler pin'):
            c['at'] = [round(float(N1[0]), 4), round(float(N1[1]), 4)]; c['d'] = 2 * PIN_R; c['name'] = f'Feeler pin (Ø{2 * PIN_R:g}, pressed)'
    lever['name'] = 'Retrograde lever (rack, feeler arm, pawl blade)'
    SK[feeler['sketch']]['points'] = [{'u': round(float(N1[0] + PIN_R * math.cos(2 * math.pi * k / 24)), 4), 'v': round(float(N1[1] + PIN_R * math.sin(2 * math.pi * k / 24)), 4), 'smooth': False} for k in range(24)]
    feeler['name'] = f'Feeler pin (Ø{2 * PIN_R:g} steel, rides the snail)'
    sv['nose'] = [round(float(N1[0]), 5), round(float(N1[1]), 5)]; sv['noseR'] = PIN_R
    rads = np.hypot(*(pin_locus(L, C, LF, th0, swing)[:720] - C).T)
    log.append(f'retrograde lever 2: feeler pin Ø{2 * PIN_R:g} (was Ø{2 * sv.get("_oldR", 0.5):g}), {LF0 - LF:.1f} mm closer to the pivot (arm {LF0:.1f} -> {LF:.1f}), '
               f'on a straight {2 * ARM_R:g} mm arm with a round end on the pin; snail re-cut: pin path r {rads.min():.2f}-{rads.max():.2f} (was 8.0-19.9)')
if __name__ == '__main__':                                                     # check: the recipe rebuilds the current snail
    J = json.load(open(sys.argv[1])); st, m, D, sv = parts(J); SK = {k['id']: k for k in st['sketches']}
    L = np.array(sv['pivot'], float); C = np.array(st['pos']['center'], float); N0 = np.array(sv['nose'], float)
    th0 = math.atan2(N0[1] - L[1], N0[0] - L[0]); LF0 = float(np.hypot(*(N0 - L))); swing = math.radians(m['expect']['hand_sweep'] / 3)
    old = [P(ccw(np.array([(q['u'], q['v']) for q in SK[D[sv['cam']]['sketch']]['points']])))]
    re_ = cam(L, C, LF0, th0, swing, sv['noseR'])
    print('LF0', round(LF0, 4), 'pose', round(math.degrees(th0), 3), 'swing', round(math.degrees(swing), 3))
    print('old area', round(area(old), 2), 'rebuilt area', round(area(re_), 2), 'differ (xor) mm2', round(area(diff(old, re_)) + area(diff(re_, old)), 3))
    for w in (0.05, 0.1, 0.2):
        print(f'  outside a {w} band:', round(area(diff(old, offset(re_, w))) + area(diff(re_, offset(old, w))), 4))
