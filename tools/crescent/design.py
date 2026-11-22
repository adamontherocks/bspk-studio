import os
HERE = os.path.dirname(os.path.abspath(__file__))
# The Crescent movement: every position, size and bridge shape in one place (mm, dial side up, z from the case back).
import math, json
from kit import *
O = (0, 0); RP = 66.0; RF = 63.9          # plate radius; bridge feet screw into the plate's solid rim at r 63.9
def P_(p): return tuple(round(v, 3) for v in p)
LAY = {k: tuple(v) for k, v in json.load(open(os.path.join(HERE, 'search_best.json'))).items()}
GEO = json.load(open(os.path.join(HERE, 'crescent_geo.json'))); ML = json.load(open(os.path.join(HERE, 'mech_lever.json')))
Bc, F, E, Fo, I, T, C, B = (LAY[k] for k in ('Bc', 'F', 'E', 'Fo', 'I', 'T', 'C', 'B'))
Q = tuple(GEO['Q']); RI = GEO['RI']; L = tuple(ML['L'])
H = pol(L, 18.5, -80)                                    # hour star arbor (from the kick prototype)
K = pol(C, 30.0, -30)                                    # keyless pin-wheel arbor (setting wheel 48 on the centre arbor)
PIV = dict(B=B, C=C, T=T, I=I, Fo=Fo, E=E, F=F, Bc=Bc, Q=Q, L=L, H=H, K=K)
def edge(a, r=RF): return pol(O, r, a)
# ---- bridge shapes (signed distance fields, smooth tangent blends) ----
def arm(pts, w0, w1=None): return curve(pts, w0, w1)
def boss(p, r=4.6): return circle(p, r)
# Right bridge: a slender crescent facing the big one, rim to rim (45 -> -40 deg), through the lever stud, the third wheel and the hour star;
# short branches in to the centre arbor and to the hand arbor
def arcpath(c, r0, a0, a1, r1=None, n=30):
    r1 = r0 if r1 is None else r1
    return [pol(c, r0 + (r1 - r0) * k / n, a0 + (a1 - a0) * k / n) for k in range(n + 1)]
RS = 40.5                                                           # the right bridge follows a circle concentric with the movement
spine = bez(edge(45, 64.6), pol(O, 56, 49), pol(O, 46, 52), pol(O, RS, 50), 16) + [pol(O, RS, a) for a in range(48, -31, -4)][1:] + bez(pol(O, RS, -32), pol(O, 46, -36), pol(O, 56, -38), edge(-38, 64.6), 16)[1:]
mech = U(curve(spine, 3.0, 3.2),
         arm([pol(O, RS, math.degrees(math.atan2(L[1], L[0]))), L], 2.6), boss(L, 4.0),
         arm(bez(pol(O, RS, -8), pol(O, 39, -10), pol(O, 37.5, -12), T, 8), 2.8), boss(T, 4.6),
         arm([pol(O, RS, math.degrees(math.atan2(H[1], H[0]))), H], 2.8), boss(H, 5.0),
         arm(bez(pol(O, RS, 36), (30, 22), (26, 20), C), 2.8, 2.6), boss(C, 5.0),
         arm(bez(T, (30, -11), (24, -11), Q), 2.4, 2.3), boss(Q, 4.3),
         arm([pol(O, RS, 20), (47.5, 15.5)], 2.2), boss((47.5, 15.5), 2.4), k=3.0)   # a spur out to the return-spring stud
# Bottom bridge: a smile from rim to rim (-52 -> 232 deg) through the intermediate wheel and the seconds lobe
train = U(arm(bez(edge(-62, 64.6), (34, -50), (26, -38), I), 3.2, 3.0), boss(I, 4.8),
          arm(bez(I, (8, -38), (-2, -38), Fo), 3.0, 2.8), circle(Fo, 10.6),
          arm(bez(Fo, (-20, -38), (-28, -44), edge(232, 64.6)), 2.8, 3.2),
          arm(bez((3.0, -37.5), (4, -28), (2, -18), E, 20), 2.4, 2.2), boss(E, 3.6), arm([E, F], 2.0), boss(F, 3.4), k=3.5)
# Barrel bridge: a moon over the barrel, feet under the crescent's top horn
barrel = U(smax(circle(B, 19.5), -circle(pol(B, 13, 270), 16.0), 2.5), circle(B, 7.6),   # the moon's inner edge reaches the boss, so the arbor's bearing is carried
           arm(bez(pol(B, 17, 30), pol(B, 24, 35), edge(55, 62), edge(55, 64.6)), 3.2), arm(bez(pol(B, 17, 150), pol(B, 24, 140), edge(112, 62), edge(112, 64.6)), 3.2), k=3.0)
pallet = U(arm(bez(pol(F, 9, 235), pol(F, 5, 250), pol(F, 2, 240), F, 10) + [E, pol(E, 8, -25)], 2.0), circle(F, 3.3), circle(E, 3.5), circle(pol(F, 9, 235), 2.6), circle(pol(E, 8, -25), 2.6), k=2.0)
# Crescent (top level) with the balance cock grown out of it
cres = smax(smax(circle(O, 62.0), -circle(Q, RI), 1.5), -circle(O, 1.0), 0)
cres = smax(cres, np.maximum(-(math.cos(math.radians(70)) * Y - math.sin(math.radians(70)) * X), (math.cos(math.radians(236)) * Y - math.sin(math.radians(236)) * X)), 4.0)
cock = U(arm(bez(edge(168, 52), (-44, 12), (-34, 8), Bc), 3.4, 2.3), circle(Bc, 4.4), k=2.5)
crescent = U(cres, cock, k=3.5)
# Hand cock (top level): a slender arm from the right rim over the hour star to the hand arbor, its tip pointing at the hour
handcock = U(arm(bez(edge(10, 64.6), (55, 4), (50, -8), H), 2.6, 2.2), boss(H, 3.6), arm(bez(H, (32, -16), (24, -14), Q), 2.2, 1.9), boss(Q, 3.4), k=2.0)
# Rim plates (3/8" acrylic) stand on the main plate's rim and carry the top level, so nothing stands on a riser:
# a big crescent under the crescent bridge on the left, a small counter-crescent on the right under the hand cock's foot.
# Each is inside the movement's edge and outside a bigger offset circle: widest in the middle, running out to points at both ends.
RIM_OUT = 65.0                                           # 1 mm in from the main plate's edge, so the layers read as steps
def moon(r_out, mid_deg, r_in_mid, d, k=2.0):
    a = math.radians(mid_deg + 180); pc = (d * math.cos(a), d * math.sin(a))
    return smax(circle(O, r_out), -circle(pc, r_in_mid + d), k)
rim_left = moon(RIM_OUT, 172, 48.0, 47.0)
rim_right = smax(moon(RIM_OUT, 8, 53.0, 160.0), -circle(H, 14.5 + 1.0), 1.5)    # and clear of the hour star's points by 1 mm
SHAPES = dict(train=train, mech=mech, barrel=barrel, pallet=pallet, crescent=crescent, handcock=handcock, rim_left=rim_left, rim_right=rim_right)
if __name__ == '__main__':
    fig = plt.figure(figsize=(7.4, 7.4), dpi=150); fig.patch.set_facecolor(PAL['page'])
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); ax.set_xlim(-69, 69); ax.set_ylim(-69, 69); ax.set_aspect('equal'); ax.axis('off')
    ring(ax, O, 67.5, 64.3, PAL['case'], 1, edge='#4a4f56'); fill(ax, circle(O, 64.2), PAL['plate'], 2, bevel=False)
    fill(ax, circle(Bc, 19.5), PAL['well'], 2.5, bevel=False)
    wheel(ax, B, 42, color='#b98a36', solid=True, z_=5)
    for p, z in ((C, 48), (T, 45), (I, 48), (Fo, 36)): wheel(ax, p, z, z_=5, rot=7)
    wheel(ax, E, 15, m=1.07, color=PAL['steel'], edge=PAL['steeld'], club=True, spokes=4, curl=0, z_=7); balance(ax, Bc, 17, z_=8)
    wheel(ax, K, 18, m=0.955, color=PAL['steel'], edge=PAL['steeld'], solid=True, z_=6)
    for nm, z, col in (('barrel', 14, '#a9adb1'), ('pallet', 14, '#a9adb1'), ('train', 14, '#a9adb1'), ('mech', 14.5, '#a9adb1'), ('crescent', 18, PAL['bridge']), ('handcock', 18.5, PAL['bridge'])): fill(ax, SHAPES[nm], col, z)
    for k_, p in PIV.items(): ax.plot(*p, 'o', ms=3, color='#c0392b', zorder=30); ax.annotate(k_, p, xytext=(3, 3), textcoords='offset points', color='w', fontsize=7, zorder=30)
    fig.savefig('design.png', facecolor=fig.get_facecolor()); print('ok', 'H', P_(H), 'K', P_(K))
