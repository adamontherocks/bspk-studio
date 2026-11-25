# Beta 2 · layered (2026-11-24): Adam's modification lists on Beta 2 · haute, as a stack of plates that each host the wheels at their own
# heights. Second pass, from his 19 markup notes and 2 sketches:
#   - The main plate stays high on the hour side and steps right down on the minute side, to seat the secondary plate (1/8"). The
#     secondary plate is the cradle: it holds the stem down, pivots the crown, transfer and minute arbors, and gives every top-layer wheel
#     one unbroken floor (P1, P3: "no breaks in plates below wheels").
#   - The transfer plate (1/8") and the NE plate (1/8", milled from underneath) sit on the secondary plate, tops flush with the discs (P2).
#     The transfer plate runs along the south and east walls. Its twin arms carry the first intermediate's top pivot, lowered to the
#     pad's surface from the round anchor foot (P4, P16-P18, Adam's K55), with the corner by the transfer wheel redrawn from his K56 and
#     the whole anchor merged as one outline and one step (P14, P15, P19).
#   - The hour side's top plate runs along the north edge to the NE plate (P5), and follows the main plate's walls (P10-P13).
#   - Rules: every plate's reliefs come from the train (a pocket 0.3 round a wheel's tips, its floor AX under it); a plate sitting in
#     another sits in a well WELL bigger than it, so their walls read as one; any strip of a plate under 1 mm wide left showing beside a
#     relief or an upper plate is lowered into the floor next to it (P6-P9: no ledges, no peninsulas, no notches).
# The train is as in the first pass: A1 deep (its pinion tops out at 2.49) so the transfer pinion clears the secondary plate, A2 and the
# hour wheel lower with it. Discs and the movement's height unchanged.
# Production pass (review + Adam's P27, 2026-11-24): A2's flanged bearing sits down on A1's floor, clear under A1's wheel (P27); A2 drops
# into the gap over A1's wheel (Adam), so the hour side's top plate becomes 1/8" like the transfer and NE plates and its twin arms carry
# A2's top pivot, lowered to the pad under the discs, the mirror of the transfer plate's arms to A1. The minute arbor gets a collar under
# the back face; the worm window's deep corners are opened to r 1.05 (the 2 mm end mill); fins beside bearing seats come down to the
# seat; wells 0.10 a side; 0.05 of backlash per mesh (teeth thinned); bearings are solids in the clash check.
# Bridges and hands (Adam's K268, K269, P28, P29): two mirrored 1/16" bridges set flush into the transfer plate and the top plate carry the
# minute and hour arbors' top pivots (plain delrin); the minute pinion drops 0.3 (level with the transfer and crown wheels) to turn under
# its bridge, which also keeps it from lifting (no collar). The arbors run on up as posts and the discs (1/16") ride 0.3 over the plates,
# like hands over a dial: 1.89 more height, the movement itself unchanged.
import copy, math
from shapely.geometry import Point, Polygon, LineString, box as sbox
from shapely.ops import unary_union

T38, TS, TT = 9.525, 3.175, 1.5875
GAP = 0.3          # tip clearance, and wheel to wheel (the sim's minGap)
AX = 0.2           # a plate's face under or over a wheel
MIN_WEB = 0.8      # a relief floor this close to the plate's underside is cut through instead
DISC_AX = 0.3      # under the discs
WELL = 0.10        # a plate sitting in another's well: the well is this much bigger (0.10 a side: the Air's tolerance; the arbors locate the plates)
BACKLASH = 0.05    # each mesh's backlash: half off each gear's teeth at the pitch circle (rules.backlash)
R_DEEP = 1.05      # inside corners deeper than the small cutters reach: the 2 mm end mill's radius, and a little
BOSS_R, ANCHOR_R, WAIST = 2.6, 2.8, 3.0   # the disc bridges: pivot boss (as A1's and A2's pads), round anchor about its screw, narrowest width
WAFER_D, WAFER_DEPTH = 4.4, 0.9
MOV_CH, MOV_R = 4.5, 1.5            # the movement's corners: 45° chamfers 4.5 on the leg, rounded r 1.5 (the H-88 case's octagon, 2026-11-25)    # an M2 wafer head (Ø4, under 0.8 tall) in a counterbore: what a 1/16" bridge can hold
SLIVER = 0.5       # strips narrower than twice this are lowered into the floor beside them
HEAD_R, HEAD_H = 1.9, 1.3
CB_D, CB_DEPTH = 4.2, 1.4            # counterbore for an M2 cheese head (fit m2_cb)
BOSS = 1.15 + 0.5                    # clearance hole Ø2.3 with 0.5 of plate round it
CB_KEEP = CB_D / 2 + 0.6             # a counterbore with 0.6 round it (the minimum wall)
TAP_SOLID, TAP_DEPTH = 1.2, 3.0      # an M2 thread: 0.4 of solid round its Ø1.6 hole, 3 mm deep at least
BEARING = dict(d=5.98, seat=7.3, seat_depth=0.65, body=1.9)
R_IN = 1.5                           # every inside corner of the anchor's outline
m = 0.6
def ra(z, x): return m * z / 2 + m * (1 + x)

def pieces(g): return [] if g.is_empty else [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon']
def largest(g): ps = pieces(g); return max(ps, key=lambda p: p.area) if ps else Polygon()
def smooth(g, ro=0.3, rc=0.6):
    g = g.buffer(-ro, join_style=1).buffer(ro, join_style=1)
    return g.buffer(rc, join_style=1).buffer(-rc, join_style=1).buffer(0) if rc else g
def C(c, r, n=128): return Point(c).buffer(r, n)
def U(gs): gs = [g for g in gs if not g.is_empty]; return unary_union(gs) if gs else Polygon()
def arc(c, r, a0, a1, step=0.1):
    n = max(2, math.ceil(abs(a1 - a0) * math.pi / 180 * r / step))
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
def deg(c, p): return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))

def anchor(O, A1, B, rB, HX, HY, dM, dH, zoneA1w, bay):
    """the transfer plate's outline and its step (Adam's K55, K56, P19): returns (footprint, the region lowered to the pad's surface, notes)"""
    xa, xi = 2.35, 0.85                                       # the arms' outer and inner edges
    c0, r0 = (0.0, -13.4), 2.8                                # the round foot, about its anchor screw
    phi = -144                                                # K56: the straight run meets the transfer wheel's opening on a tangent here
    T = (B[0] + rB * math.cos(math.radians(phi)), B[1] + rB * math.sin(math.radians(phi)))
    d = (math.cos(math.radians(phi + 90)), math.sin(math.radians(phi + 90))); nrm = (-d[1], d[0])
    corner = (xa, T[1] - d[1] * (T[0] - xa) / d[0]); turn = math.degrees(math.acos(-d[1]))
    yk = corner[1] + R_IN * math.tan(math.radians(turn / 2))  # where the outline leaves the right arm's edge in its r 1.5 round
    opening = C(B, rB, 512)
    # the outline: the arms' column straight from A1's pad, the foot, the band east under K56's edge; every inside corner r 1.5
    W = sbox(-3.8, -HY - 0.5, 6.5, 0.0)
    half_ne = Polygon([(corner[0] - 20 * d[0], corner[1] - 20 * d[1]), T, (T[0] + 20 * nrm[0], T[1] + 20 * nrm[1]),
                       (corner[0] - 20 * d[0] + 20 * nrm[0], corner[1] - 20 * d[1] + 20 * nrm[1])])
    east = sbox(2.0, -HY - 0.5, 7.5, -9.0).difference(half_ne.intersection(sbox(-20, -40, T[0], 40))).difference(opening)
    Uq = U([sbox(-xa, -HY - 0.5, xa, A1[1]), C(A1, 2.6, 256), C(c0, r0, 256), east])
    Uc = Uq.buffer(R_IN, 256, join_style=1).buffer(-R_IN, 256, join_style=1)
    local = Uc.intersection(W.buffer(0.02, join_style=2)).intersection(O).difference(opening)
    base = O.intersection(sbox(-xa, -HY - 1, HX + 1, 0.0)).difference(U([dM, dH, zoneA1w, bay]))
    F = largest(base.difference(opening).difference(W).union(local).buffer(0))
    slot = sbox(-xi, -12.0, xi, A1[1]).difference(C(A1, 2.6, 256)).difference(C(c0, r0, 256))
    slot = slot.buffer(-0.5, 64, join_style=1).buffer(0.5, 64, join_style=1)          # (its corners rounded r 0.5)
    F = largest(F.difference(slot))
    # the step (Adam's K266, P20-P21: one arch, no shoulders): the foot's own r 2.8 circle from where the outline's left round joins it,
    # over the top, then a sweep tangent to the foot's circle and to the transfer wheel's opening, which it meets on that tangent (so the
    # lowered corner by the opening thins to nothing there). Its radius is the one that fits his dots best (0.04 mm).
    rl = R_IN
    lc = (-(xa + rl), c0[1] + math.sqrt((r0 + rl) ** 2 - (xa + rl) ** 2))
    jl = (c0[0] + r0 * (lc[0] - c0[0]) / (r0 + rl), c0[1] + r0 * (lc[1] - c0[1]) / (r0 + rl))      # the left round meets the foot here
    th = 78.05                                                                                     # where the sweep leaves the foot (deg)
    u = (math.cos(math.radians(th)), math.sin(math.radians(th)))
    lo_, hi_ = r0 + 1e-3, 60.0
    fR = lambda R: math.dist((c0[0] - (R - r0) * u[0], c0[1] - (R - r0) * u[1]), B) - (R + rB)
    for _ in range(80):
        mid = (lo_ + hi_) / 2
        if fR(lo_) * fR(mid) <= 0: hi_ = mid
        else: lo_ = mid
    Rw = (lo_ + hi_) / 2; cw = (c0[0] - (Rw - r0) * u[0], c0[1] - (Rw - r0) * u[1])
    tw = (c0[0] + r0 * u[0], c0[1] + r0 * u[1])
    tb = (cw[0] + Rw * (B[0] - cw[0]) / math.dist(cw, B), cw[1] + Rw * (B[1] - cw[1]) / math.dist(cw, B))
    step = arc(c0, r0, deg(c0, jl), th) + arc(cw, Rw, deg(cw, tw), deg(cw, tb))[1:]
    xe = 6.5
    low = Polygon([(-xa - 1.2, 1.0), (-xa - 1.2, jl[1])] + step + [(xe, tb[1]), (xe, 1.0)]).buffer(0).union(C(A1, 3.0))
    notes = [f'anchor: the outline leaves the right arm\'s edge at y {yk:.3f}; step: foot circle from ({jl[0]:.3f},{jl[1]:.3f}) to {th} deg, then a sweep r {Rw:.3f} '
             f'tangent to the transfer wheel\'s opening at ({tb[0]:.3f},{tb[1]:.3f}); K56 tangent at {phi} deg']
    return F, low, step, notes

def build(aligned_scene, info, helpers):
    rrect, sketch, poly_dots, FITS = helpers['rrect'], helpers['sketch'], helpers['poly_dots'], helpers['FITS_DELRIN']
    S = copy.deepcopy(aligned_scene)
    P, st = S['project'], S['state']
    M, H = (10.4, 0.0), (-10.4, 0.0)
    A1, A2, B, E = (tuple(info[k]) for k in ('A1', 'A2', 'B', 'E'))
    zw = info['worm_axis']
    z_top = info['heights']['disc']            # 5.8625: the discs' underside, the main plate's top on the hour side
    z_bot = z_top - T38
    z_cap = zw + 0.9 + 0.1                     # 1.425: the secondary plate's underside, 0.1 over the stem's journals
    z_hi = z_top + TT                          # 7.45: the top of the discs and of every top plate
    z_tp = z_hi - TS                           # 4.275: the transfer and NE plates' underside (on the secondary plate)
    HX, HY = 22.75, 16.2
    TW, TP = 1.2, TS - 1.2
    # ---- the train's heights (positions and teeth as aligned); as the first pass
    zA1w = -0.6875                                             # A1's wheel (its pinion right on it, one piece of 1/8"), deep in the main plate
    zA1p_top = zA1w + TS                                       # 2.4875
    zA2w = zA1w + TW + GAP                                     # 0.8125: A2's wheel 0.3 over A1's wheel (Adam: drop it into that gap), so its
                                                               #   pinion tops out at 3.99 and the top plate's arms pass over it
    zHw = zA1p_top + GAP                                       # 2.7875: the hour wheel clears A1's pinion (they overlap in plan)
    dz_bp = 0.2                                                # B's pinion 0.2 high on A1's wheel (still its full face)
    zBw = 3.975
    G = {   # name: (arbor, centre, tip radius, z0, z1)
        'transfer pinion': ('b', B, ra(11, .3), zA1w + TW / 2 - TT / 2 + dz_bp, zA1w + TW / 2 + TT / 2 + dz_bp),
        'first intermediate wheel': ('a1', A1, ra(22, -.3), zA1w, zA1w + TW),
        'first intermediate pinion': ('a1', A1, ra(11, .3), zA1w + TW, zA1w + TS),
        'second intermediate wheel': ('a2', A2, ra(22, -.3), zA2w, zA2w + TW),
        'second intermediate pinion': ('a2', A2, ra(13, .3), zA2w + TW, zA2w + TS),
        'hour wheel': ('hour', H, ra(26, -.3), zHw, zHw + TT),
        'transfer wheel': ('b', B, ra(18, -.3), zBw, zBw + TT),
        'minute pinion': ('minute', M, ra(12, .3), zBw, zBw + TT),          # (level with the wheels it meshes: it turns under its bridge)
        'crown arbor worm wheel': ('e', E, ra(15, .15), zw - TT / 2, zw + TT / 2),
        'crown arbor wheel': ('e', E, ra(18, -.3), zBw, zBw + TT)}
    MESH = {frozenset(p) for p in [('transfer pinion', 'first intermediate wheel'), ('first intermediate pinion', 'second intermediate wheel'),
                                   ('second intermediate pinion', 'hour wheel'), ('minute pinion', 'transfer wheel'), ('minute pinion', 'crown arbor wheel')]}
    z_d = z_hi + DISC_AX                                       # 7.75: the discs ride 0.3 over the plates and bridges, on their arbors
    discs = {'hour disc': ('hour', H, 9.5, z_d, z_d + TT), 'minute disc': ('minute', M, 9.5, z_d, z_d + TT)}
    arbor_at = {'minute': M, 'hour': H, 'a1': A1, 'a2': A2, 'b': B, 'e': E}
    names = {'a1': 'first intermediate', 'a2': 'second intermediate', 'hour': 'hour arbor', 'b': 'transfer arbor', 'minute': 'minute arbor', 'e': 'crown arbor'}
    wa, wb = E[0] - 2.5, E[0] + 2.5; x0 = wa - 0.6; jr = 0.9; wro = 3.25; xc = HX + 2.0
    worm_plan = Polygon([(wa, -2.95), (wa + 0.3, -wro), (wb - 0.3, -wro), (wb, -2.95), (wb, 2.95), (wb - 0.3, wro), (wa + 0.3, wro), (wa, 2.95)])
    things = [(n, a, C(c, r), z0, z1, GAP, AX) for n, (a, c, r, z0, z1) in G.items()]
    things += [(n, a, C(c, r), z0, z1, GAP, DISC_AX) for n, (a, c, r, z0, z1) in discs.items()]
    # the worm's window through the main plate: one wall top to bottom, its corners r 1.05 so the 2 mm end mill cuts them through the 3/8";
    # its ends stay put and its sides go 0.45 out from the worm's room so those corners still clear the worm (the secondary plate's window
    # over it stays the worm's room, overhanging the main plate's by up to 0.45)
    room_w = worm_plan.buffer(GAP, 64)
    from shapely.affinity import translate
    open_w = U([translate(room_w, 0, 0.45), translate(room_w, 0, -0.45)]).convex_hull.buffer(-R_DEEP, 64).buffer(R_DEEP, 64)
    assert room_w.difference(open_w).area < 1e-6, room_w.difference(open_w).area
    things.append(('worm', 'stem', worm_plan, zw - wro, zw + wro, GAP, AX))
    things.append(('stem journals', 'stem', sbox(x0, -jr, xc, jr), zw - jr, zw + jr, 0.075, 0.05))
    zt_of = {}
    for n, (a, c, r, z0, z1) in list(G.items()) + list(discs.items()): zt_of[a] = max(zt_of.get(a, -99), z1)
    rod_top = dict(zt_of); rod_top['a1'] = z_top - DISC_AX               # A1's rod runs up into the transfer plate's pad
    rod_top['a2'] = z_top - DISC_AX                                      # and A2's into the top plate's pad (its mirror)
    rod_bottom = {}
    for a, c in arbor_at.items(): things.append((f'{a} rod', a, C(c, 1.5, 48), z_bot, rod_top[a], GAP, 0.0))

    # ---- footprints
    # the outline: chamfered at the corners to follow the H-88 case's octagon (3 mm of case wall at the corners), rounded r 1.5
    O = Polygon([(HX - MOV_CH, HY), (-(HX - MOV_CH), HY), (-HX, HY - MOV_CH), (-HX, -(HY - MOV_CH)), (-(HX - MOV_CH), -HY), (HX - MOV_CH, -HY),
                 (HX, -(HY - MOV_CH)), (HX, HY - MOV_CH)]).buffer(-MOV_R, 64, join_style=1).buffer(MOV_R, 64, join_style=1)
    zA1w_ = C(A1, G['first intermediate wheel'][2] + GAP); zA2w_ = C(A2, G['second intermediate wheel'][2] + GAP)
    zA1p_ = C(A1, G['first intermediate pinion'][2] + GAP)
    dH, dM = C(H, 9.5 + GAP), C(M, 9.5 + GAP)
    bay = C((HX, 0.0), 5.0)                                    # the crown's bay: the secondary plate shows round the stem
    rB = G['transfer wheel'][2] + GAP
    F_S = largest(smooth(O.intersection(sbox(2.7, -HY - 1, HX + 1, HY + 1)).difference(zA2w_).difference(zA1p_)))
    F_P, LOW, step, anchor_notes = anchor(O, A1, B, rB, HX, HY, dM, dH, zA1w_, bay)
    F_N = largest(smooth(O.intersection(sbox(2.7, 0.0, HX + 1, HY + 1)).difference(U([dM, zA2w_, bay]))))
    plates = {
        'main': dict(id='main', zb=z_bot, zt=z_top, F=O, pivots=[], holds=[f'{a} rod' for a in arbor_at], mill='back', T=T38, stock='3/8"'),
        'sec': dict(id='sec', zb=z_cap, zt=z_cap + TS, F=F_S, pivots=['minute', 'b', 'e'], holds=['stem journals'], mill='back', T=TS, stock='1/8"'),
        'tp': dict(id='tp', zb=z_tp, zt=z_hi, F=F_P, pivots=['a1'], holds=[], mill='back', T=TS, stock='1/8"'),
        'ne': dict(id='ne', zb=z_tp, zt=z_hi, F=F_N, pivots=[], holds=[], mill='front', T=TS, stock='1/8"'),   # (milled from underneath)
        'top': dict(id='top', zb=z_tp, zt=z_hi, F=Polygon(), pivots=['a2'], holds=[], mill='back', T=TS, stock='1/8"'),
    }
    # ---- the disc bridges (Adam's K268, K269): mirrored, from the transfer plate (minute) and the top plate (hour) to the arbors' top
    # pivots, flush with the plates' tops. Each is a round boss about its arbor and a round anchor about its screw, 12 apart on the line
    # Adam drew (45° below the disc's centre line, outward), joined by concave flanks: arcs tangent to both circles, WAIST at the narrowest.
    def bridge(cb, ca):
        D = math.dist(cb, ca); u = ((ca[0] - cb[0]) / D, (ca[1] - cb[1]) / D); nv = (-u[1], u[0])
        def geo(R):
            x = ((R + BOSS_R) ** 2 - (R + ANCHOR_R) ** 2 + D * D) / (2 * D); h = math.sqrt(max(0.0, (R + BOSS_R) ** 2 - x * x))
            return 2 * (h - R), x, h
        lo, hi = 0.3, 500.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if geo(mid)[0] > WAIST: hi = mid
            else: lo = mid
        R = (lo + hi) / 2; _, x, h = geo(R)
        P1 = (cb[0] + x * u[0] + h * nv[0], cb[1] + x * u[1] + h * nv[1]); P2 = (cb[0] + x * u[0] - h * nv[0], cb[1] + x * u[1] - h * nv[1])
        g = U([C(cb, BOSS_R, 256), C(ca, ANCHOR_R, 256)]).convex_hull.difference(C(P1, R, 512)).difference(C(P2, R, 512))
        return largest(g.buffer(0)), R
    S_m = (M[0] + 12.0 * math.cos(math.radians(-45)), M[1] + 12.0 * math.sin(math.radians(-45)))
    S_h = (-S_m[0], S_m[1])
    F_bm, R_flank = bridge(M, S_m); F_bh, _ = bridge(H, S_h)
    plates['bm'] = dict(id='bm', zb=z_hi - TT, zt=z_hi, F=F_bm, pivots=['minute'], holds=[], mill='back', T=TT, stock='1/16"', screws=[S_m])
    plates['bh'] = dict(id='bh', zb=z_hi - TT, zt=z_hi, F=F_bh, pivots=['hour'], holds=[], mill='back', T=TT, stock='1/16"', screws=[S_h])

    def solid(X, z):
        cut = U([p for n, p, face, f in X['pockets'] if face == 'through' or (face == 'top' and f <= z + 1e-9) or (face == 'bottom' and f >= z - 1e-9)])
        return X['F'].difference(cut)
    def floor_at(X, poly):
        f = X['zt']
        for n, p, face, fl in X['pockets']:
            if p.intersects(poly): f = min(f, X['zb'] if face != 'top' else fl)
        return f
    def rests_on(Y, X): return Y is not X and X['zb'] + 1e-9 < Y['zb'] <= X['zt'] + 1e-9 and Y['F'].intersection(X['F']).area > 1.0
    def make_pockets(X):
        pk = []
        for n, a, g, t0, t1, rg, ag in things:
            if n in X['holds'] or (n.endswith(' rod') and a in X['pivots']): continue
            if t1 + ag <= X['zb'] + 1e-9 or t0 - ag >= X['zt'] - 1e-9: continue
            poly = g.buffer(rg, 64).intersection(X['F'].buffer(0.6))
            if n == 'worm' and X['id'] == 'main': poly = open_w.intersection(X['F'].buffer(0.6))
            if poly.is_empty: continue
            if X['mill'] == 'back':
                fl = t0 - ag
                pk.append((n, poly, 'through', None) if fl < X['zb'] + MIN_WEB - 1e-9 else (n, poly, 'top', fl))
            else:
                ce = t1 + ag
                pk.append((n, poly, 'through', None) if ce > X['zt'] - MIN_WEB + 1e-9 else (n, poly, 'bottom', ce))
        for Y in plates.values():
            if rests_on(Y, X) and Y['zb'] < X['zt'] - 1e-9:
                # (0.05 round the plate inside X; past X's outer edge it runs on 0.6, clear of the resolver's 0.3 band there)
                poly = Y['F'].buffer(WELL, join_style=1).union(Y['F'].buffer(0.6).difference(X['F'])).intersection(X['F'].buffer(0.6))
                if not poly.is_empty: pk.append((f'well for the {Y["id"]} plate', poly, 'top', Y['zb']))
        if X['id'] == 'main':   # P27: A2's flanged bearing sits down on A1's floor, under A1's wheel (its seat cut from there)
            pk.append(('second intermediate\'s bearing, down on the first intermediate\'s floor (P27)', C(A2, BEARING['seat'] / 2), 'top', zA1w - AX))
        if X['id'] == 'top' and not LOW2.is_empty:
            pk.append(('the arms and the second intermediate\'s pad, at the pad\'s surface', LOW2.intersection(X['F'].buffer(0.05)), 'top', z_top - DISC_AX))
        if X['id'] == 'tp':
            pk.append(('the arms and the first intermediate\'s pad, at the pad\'s surface', LOW.intersection(X['F'].buffer(0.05)), 'top', z_top - DISC_AX))
        if X['id'] == 'ne':     # a crescent window over the crown arbor's wheel, 1.2 inside the plate's edges (the rest is a ceiling over it)
            ew = G['crown arbor wheel']
            for wp in pieces(smooth(C(ew[1], ew[2] + 0.2).intersection(X['F'].buffer(-1.2)), 0.5, 0)):
                if wp.area > 3.0: pk.append(('window over the crown arbor wheel', wp, 'through', None))
        X['pockets'] = pk + X.get('lowered', [])
    LOW2 = Polygon()
    for k in ('main', 'sec', 'tp', 'ne', 'bm', 'bh'): make_pockets(plates[k])
    # the hour side's top plate: the main plate's top face on the hour side (and along the north edge to the NE plate, P5), clear of the
    # transfer and NE plates by a 0.05 joint; its corners rounded (the main plate's corners under them come down to match: the ledge rule)
    deck = solid(plates['main'], z_top - 1e-6).intersection(sbox(-HX - 1, -HY - 1, 3.0, HY + 1))   # (the main plate's top face ends at the step, 2.65)
    F_L = deck.difference(U([dH, dM, F_P.buffer(WELL, 64), F_N.buffer(WELL, 64)]))     # (exactly the main plate's top face: its corners are not rounded,
    F_L = largest(F_L.buffer(0))                                              #  so its edges are the main plate's walls; WELL joints to its neighbours)
    # its twin arms down to A2's pad (the mirror of the transfer plate's arms to A1): the column from A2 up to the north band, rounded r 1.5
    # into it; a slot between the arms; the arms and pad lowered to the pad's surface (under the discs), the step on the band's edge
    xa2, xi2 = 2.35, 0.85
    col = U([sbox(-xa2, A2[1], xa2, HY + 0.5), C(A2, 2.6, 256)])
    near = col.buffer(2 * R_IN + 0.5)
    closed = F_L.union(col).buffer(R_IN, 256, join_style=1).buffer(-R_IN, 256, join_style=1)
    F_T = F_L.union(closed.intersection(near)).intersection(O).difference(U([F_P.buffer(WELL, 64), F_N.buffer(WELL, 64)]))
    # the discs' floor rings on the hour side (the main plate's surface 0.3 under the discs) become the top plate's too, lowered with the
    # arms: the plate's inner edge is then the wheels' rooms, one wall with the main plate's under it, and its well cuts no groove beside a disc
    ring = solid(plates['main'], z_top - 1e-6).intersection(U([dH, dM])).intersection(sbox(-HX - 1, -HY - 1, 3.0, HY + 1))
    ring = U([q for q in pieces(ring.buffer(0)) if q.area > 0.5 and q.buffer(1e-3).intersects(F_T)])
    F_T = F_T.union(ring.buffer(1e-4)).difference(U([F_P.buffer(WELL, 64), F_N.buffer(WELL, 64)]))
    slot2 = sbox(-xi2, A2[1], xi2, HY + 1).difference(C(A2, 2.6, 256)).difference(F_L)
    slot2 = slot2.buffer(-0.5, 64, join_style=1).buffer(0.5, 64, join_style=1)
    F_T = largest(F_T.difference(slot2).buffer(0))
    LOW2 = F_T.difference(F_L).buffer(0)
    plates['top']['F'] = F_T
    make_pockets(plates['top'])
    for k in ('main', 'sec', 'tp', 'ne', 'bm', 'bh'): make_pockets(plates[k])
    # ---- the ledge rule: any strip of a plate under 1 mm wide, showing from above (not under a plate that rests on it) beside a floor or
    # an edge, comes down to that floor. Run from each plate's highest floor down, so a strip steps down with the floor it borders.
    lowered_log = {}
    # (not the transfer plate: its shoulders taper to nothing on purpose.) Each pass looks at every surface of the plate by its height t
    # (the plate whose top is exactly t, not under a plate that rests on it); a strip of it under 1 mm wide, beside an upper plate's edge or
    # a near copy of a wall (under 0.3 wide on average), comes down once, to the highest floor it borders, so it joins that floor; a taper
    # where two walls cross at an angle is kept, and nothing cascades further down.
    for k in ('sec', 'main'):
        X = plates[k]; X['lowered'] = []
        covered = U([Y['F'].buffer(WELL + 0.01, join_style=1) for Y in plates.values() if rests_on(Y, X)])   # (a well's clearance ring goes with its plate)
        near_cover = covered.buffer(0.05)
        done = Polygon()                                  # (a strip comes down once: it has joined the floor it borders)
        for _ in range(4):
            changed = False
            tops = sorted({f for _, _, face, f in X['pockets'] if face == 'top'} | {X['zt']}, reverse=True)
            surfs = {t: solid(X, t - 1e-6).difference(solid(X, t + 1e-6) if t < X['zt'] - 1e-9 else Polygon()) for t in tops}
            hole = X['F'].difference(solid(X, X['zb'] + 1e-6))
            for t in tops:
                surf = surfs[t].difference(covered)
                thin = surf.difference(surf.buffer(-SLIVER, 32, join_style=1).buffer(SLIVER, 32, join_style=1))
                for p in pieces(thin):
                    if p.area < 1e-5 or p.buffer(-0.005).is_empty: continue          # (not a real strip: a rounding hairline)
                    if p.difference(done).area < 0.5 * p.area: continue
                    if any(abs(t - (z0 - AX)) < 1e-6 and p.intersects(C(c, r + GAP)) for _, c, r, z0, z1 in G.values()): continue   # (a wheel's floor stays whole)
                    if any(abs(t - (z0 - DISC_AX)) < 1e-6 and p.intersects(C(c, r + GAP)) for _, c, r, z0, z1 in discs.values()): continue   # (and a disc's)
                    if not (p.intersects(near_cover) or 2 * p.area / max(p.length, 1e-9) < 0.3): continue
                    ring = p.buffer(0.03).difference(p.buffer(0.001))          # the surfaces actually beside it, lower than it
                    nb = [t2 for t2 in tops if t2 < t - 1e-9 and surfs[t2].difference(covered).intersection(ring).area > 1e-6]   # (floors you can see)
                    if hole.intersection(ring).area > 1e-6: nb.append(X['zb'])
                    if not nb: continue
                    f = max(nb)
                    X['lowered'].append(('strip lowered into the floor beside it', p.buffer(0.005), 'through' if f <= X['zb'] + 1e-9 else 'top', None if f <= X['zb'] + 1e-9 else f))
                    lowered_log[k] = lowered_log.get(k, 0.0) + p.area; changed = True; done = done.union(p.buffer(0.02))
                if changed: make_pockets(X); break
            if not changed: break
    # ---- bearings and bushings in the main plate
    main = plates['main']
    bearings = {'a1': 1, 'b': 1, 'a2': 1, 'hour': 2}     # (A2: one, on A1's floor, P27; its top pivot in the top plate)
    bore_notes = []
    for a, nb in bearings.items():
        f = floor_at(main, C(arbor_at[a], 0.01))
        bore_notes.append((a, nb, f, f - BEARING['seat_depth'] - BEARING['body']))
    # a fin of the main plate under 0.6 wide left between a bearing's seat and a relief beside it comes down to the seat's floor
    fins = 0.0
    for a, nb, f, bottom in bore_notes:
        sb, Sc = f - BEARING['seat_depth'], C(arbor_at[a], BEARING['seat'] / 2)
        lv = sorted({sb, f} | {fl for _, _, face, fl in main['pockets'] if face == 'top' and sb < fl < f})
        for z0_, z1_ in zip(lv, lv[1:]):
            sl = solid(main, (z0_ + z1_) / 2).difference(Sc)
            thin = sl.difference(sl.buffer(-0.3, 32, join_style=1).buffer(0.3, 32, join_style=1))
            for q in pieces(thin):
                if q.area > 0.1 and q.distance(Sc) < 0.01 and 2 * q.area / q.length < 0.5:
                    main['lowered'].append((f'fin beside the {names[a]}\'s bearing seat, down to the seat', q.buffer(0.01), 'top', sb)); fins += q.area
    if fins: make_pockets(main)
    # ---- screws
    def tap_ok(z_seat, s): return floor_at(main, C(s, TAP_SOLID, 32)) >= z_seat - 1e-9 and z_seat - z_bot >= TAP_DEPTH
    def keep(X): return BOSS + 0.6 if X['id'] == 'ne' else WAFER_D / 2 + 0.6 if X['id'] in ('bm', 'bh') else CB_KEEP   # (pan heads on the NE plate: Ø4)
    def path_ok(X, s):
        if floor_at(X, C(s, keep(X), 32)) < X['zt'] - 1e-9: return None
        if X['id'] in ('tp', 'ne'):
            sec = plates['sec']
            if sec['F'].buffer(-TAP_SOLID).contains(Point(s)):
                if floor_at(sec, C(s, TAP_SOLID, 32)) < X['zb'] - 1e-9: return None
                return ('main', z_cap) if tap_ok(z_cap, s) else None
            if sec['F'].buffer(BOSS).contains(Point(s)): return None
            return ('main', X['zb']) if tap_ok(X['zb'], s) else None
        if X['id'] == 'sec': return ('main', z_cap) if tap_ok(z_cap, s) else None
        if X['id'] == 'top': return ('main', X['zb']) if tap_ok(X['zb'], s) else None
        if X['id'] in ('bm', 'bh'):     # through the plate it's set into (whole round the screw under the bridge's well), then on as that plate's
            Y = plates['tp'] if X['id'] == 'bm' else plates['top']
            if not Y['F'].buffer(-TAP_SOLID).contains(Point(s)) or floor_at(Y, C(s, TAP_SOLID, 32)) < X['zb'] - 1e-9: return None
            sec = plates['sec']
            if X['id'] == 'bm' and sec['F'].buffer(-TAP_SOLID).contains(Point(s)):
                if floor_at(sec, C(s, TAP_SOLID, 32)) < Y['zb'] - 1e-9: return None
                return ('main', z_cap) if tap_ok(z_cap, s) else None
            return ('main', Y['zb']) if tap_ok(Y['zb'], s) else None
        return None
    def pick(X, n, spacing=7.0, region=None):
        inner = X['F'].buffer(-(CB_KEEP if X['id'] != 'ne' else HEAD_R + 0.2))
        if region is not None: inner = inner.intersection(region)
        cand = []
        if not inner.is_empty:
            x0_, y0_, x1_, y1_ = inner.bounds
            for i in range(int((x1_ - x0_) / 0.25) + 1):
                for j in range(int((y1_ - y0_) / 0.25) + 1):
                    q = (round(x0_ + 0.25 * i, 2), round(y0_ + 0.25 * j, 2))
                    if inner.contains(Point(q)) and path_ok(X, q): cand.append(q)
        bx0, by0, bx1, by1 = X['F'].bounds
        anchors_ = [(bx0, by0), (bx1, by1), (bx1, by0), (bx0, by1), ((bx0 + bx1) / 2, by0), ((bx0 + bx1) / 2, by1), (bx0, (by0 + by1) / 2), (bx1, (by0 + by1) / 2)]
        picks = []
        for an in anchors_:
            if len(picks) >= n or not cand: break
            q = min(cand, key=lambda p: math.dist(p, an))
            if all(math.dist(q, p) >= spacing for p in picks): picks.append(q)
        def spread(picks):
            picks = list(picks)
            while cand and len(picks) < n:
                q = max(cand, key=lambda p: min(math.dist(p, r) for r in picks) if picks else 0)
                if picks and min(math.dist(q, r) for r in picks) < spacing: break
                picks.append(q)
            return picks
        picks = spread(picks)
        if len(picks) < n and len(cand) > 1:
            a, b = max(((p, q) for i, p in enumerate(cand) for q in cand[i + 1:: 3]), key=lambda t: math.dist(*t))
            alt = spread([a, b]) if math.dist(a, b) >= spacing else []
            if len(alt) > len(picks): picks = alt
        return picks
    def pick_near(X, targets):
        inner = X['F'].buffer(-CB_KEEP); out = []
        for tx, ty in targets:
            cand = [(round(tx + 0.25 * i, 2), round(ty + 0.25 * j, 2)) for i in range(-12, 13) for j in range(-12, 13)]
            cand = [q for q in cand if inner.contains(Point(q)) and path_ok(X, q)]
            if cand: out.append(min(cand, key=lambda q: math.dist(q, (tx, ty))))
        return out
    plates['tp']['screws'] = pick_near(plates['tp'], [(0.0, -13.4)])         # (and the minute bridge's anchor screw, which clamps it too)
    plates['ne']['screws'] = pick(plates['ne'], 2, spacing=4.5)
    exposed_sec = plates['sec']['F'].difference(U([plates['tp']['F'], plates['ne']['F']]).buffer(WELL + CB_KEEP))
    plates['sec']['screws'] = pick(plates['sec'], 2, region=exposed_sec)
    plates['top']['screws'] = pick(plates['top'], 4, spacing=8.0)
    plates['main']['screws'] = []
    G_ = dict(G=G, MESH=MESH, discs=discs, things=things, arbor_at=arbor_at, rod_top=rod_top, plates=plates, solid=solid, floor_at=floor_at,
              bearings=bearings, bore_notes=bore_notes, z_bot=z_bot, z_top=z_top, z_cap=z_cap, z_tp=z_tp, z_hi=z_hi, path_ok=path_ok, O=O,
              rests_on=rests_on, worm=(worm_plan, zw - wro, zw + wro), step=step, rod_bottom=rod_bottom, worm_window=open_w)
    problems, notes = check(G_)
    notes = anchor_notes + [f'ledge rule: {k} {v:.2f} mm² lowered' for k, v in lowered_log.items()] + [f'fins beside bearing seats: {fins:.2f} mm² lowered',
             f'worm window (main plate): one wall, sides 0.45 out from the worm\'s room, corners r {R_DEEP}'] + notes

    # ---- the parts
    outline_pts = poly_dots(O)
    sks, drawn = [], []
    PID = {'main': 'D1', 'sec': 'D2', 'tp': 'D3', 'ne': 'D4', 'top': 'D5', 'bm': 'D7', 'bh': 'D8'}
    TITLE = {'main': 'Main plate', 'sec': 'Secondary plate', 'tp': 'Transfer plate', 'ne': 'NE plate', 'top': 'Top plate', 'bm': 'Minute bridge', 'bh': 'Hour bridge'}
    NAME = {
        'main': 'Main plate (3/8" black delrin, milled from the top): high on the hour side, stepped down on the minute side for the secondary plate; a recess for every wheel at its own height, bearings on the recess floors',
        'sec': 'Secondary plate (1/8" black delrin, milled from the top): the cradle: holds the stem down, pivots the crown, transfer and minute arbors, one unbroken floor under every top-layer wheel; NE and SE corners',
        'tp': 'Transfer plate (1/8" black delrin, milled from the top): along the south and east walls; the first intermediate\'s top pivot on twin arms lowered to its pad from the round anchor foot; the minute bridge set flush into it',
        'ne': 'NE plate (1/8" black delrin, milled from underneath so its top stays the factory face): fills the NE corner to the plates\' top, a ceiling over the crown arbor\'s wheel and a crescent window onto it',
        'top': 'Top plate, hour side (1/8" black delrin, milled from the top; along the north edge to the NE plate; twin arms down to the second intermediate\'s top pivot, lowered to its pad: the mirror of the transfer plate\'s arms; the hour bridge set flush into it)',
        'bm': 'Minute bridge (1/16" black delrin, set flush into the transfer plate): the minute arbor\'s top pivot, over its pinion (which it keeps from lifting); the minute disc rides 0.3 above it. Adam\'s K268, made exact',
        'bh': 'Hour bridge (1/16" black delrin, set flush into the top plate): the hour arbor\'s top pivot; the hour disc rides 0.3 above it. Adam\'s K269, made exact (the mirror of the minute bridge)',
    }
    kn = [199]
    def newk(): kn[0] += 1; return f'K{kn[0]}'
    for key, X in plates.items():
        k = newk(); pid = PID[key]
        outline = outline_pts if key == 'main' else poly_dots(X['F'])
        sks.append(sketch(k, f'{TITLE[key]} outline', 'z', round(X['zb'], 5), outline))
        cuts = []; hid = [1]
        def hole(kind, name, at, d, depth=None, fit=None, axis=None, seat=None):
            c = {'id': f'h{hid[0]}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': X['mill'], 'depth': depth}
            if fit: c['fit'] = fit
            if axis: c['axis'] = axis
            if seat: c['seat'] = seat
            cuts.append(c); hid[0] += 1
        for n, p, face, fl in X['pockets']:
            for piece in pieces(p.buffer(0)):
                if piece.area < 1e-4: continue
                pk = newk()
                sks.append(sketch(pk, f'{TITLE[key]}: {n}', 'z', round(X['zb'], 5), poly_dots(piece)))
                cuts.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': n[0].upper() + n[1:], 'sketch': pk, 'from': X['mill'],
                             'depth': None if face == 'through' else round(X['zt'] - fl, 4) if face == 'top' else round(fl - X['zb'], 4)}); hid[0] += 1
        for ring in (X['F'].interiors if key != 'main' else []):
            pk = newk(); sks.append(sketch(pk, f'{TITLE[key]}: opening', 'z', round(X['zb'], 5), poly_dots(Polygon(ring))))
            cuts.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': 'Opening', 'sketch': pk, 'from': X['mill'], 'depth': None}); hid[0] += 1
        if key == 'main':
            for a, nb, f, bottom in bore_notes:
                hole('bearing', f'Bearing seat, {names[a]} (on its recess floor: the flange shows like a jewel)', arbor_at[a], BEARING['seat'], round(z_top - f + BEARING['seat_depth'], 4), axis=a)
                hole('bearing', f'Bearing bore, {names[a]}' + (' (a second, unflanged bearing pressed in from the back)' if nb == 2 else ''), arbor_at[a], BEARING['d'], fit='bearing', axis=a)
            hole('rod', 'Minute arbor: plain delrin bushing (up to the step; the secondary plate carries it on)', M, 3.08, fit='rod_free', axis='minute')
            hole('rod', 'Crown arbor: plain delrin bushing under its worm wheel', E, 3.08, fit='rod_free', axis='e')
        for a in X['pivots']: hole('rod', f'Pivot, {names[a]} (plain delrin)', arbor_at[a], 3.08, fit='rod_free', axis=a)
        for s in X['screws']:
            if key in ('bm', 'bh'): hole('clear', 'M2 through, wafer head (Ø4, under 0.8 tall) in a counterbore', s, 2.3, fit='m2_clear', seat={'d': WAFER_D, 'depth': WAFER_DEPTH}); continue
            if key == 'ne': hole('clear', 'M2 through (pan head on the factory face)', s, 2.3, fit='m2_clear')
            else: hole('clear', 'M2 through, cheese head in a counterbore', s, 2.3, fit='m2_cb', seat={'d': CB_D, 'depth': CB_DEPTH})
        for Y, under in (('bm', 'tp'), ('bh', 'top')):
            if key == under:
                for s in plates[Y]['screws']: hole('clear', f'M2 through (the {TITLE[Y].lower()}\'s screw)', s, 2.3, fit='m2_clear')
        if key == 'sec':
            for Y in ('tp', 'ne', 'bm'):
                for s in plates[Y]['screws']:
                    if X['F'].contains(Point(s)): hole('clear', f'M2 through (the {TITLE[Y].lower()}\'s screw)', s, 2.3, fit='m2_clear')
        if key == 'main':
            for Y in ('sec', 'tp', 'ne', 'top', 'bm', 'bh'):
                for s in plates[Y]['screws']: hole('pilot', f'M2 thread ({TITLE[Y].lower()})', s, 1.6, fit='m2_tap')
        drawn.append({'id': pid, 'name': NAME[key], 'sketch': k, 'thickness': X['T'], 'grow': 'plus', 'mill': X['mill'], 'minWall': 0.6, 'cuts': cuts})
    stem = copy.deepcopy(next(d for d in st['drawn'] if d.get('turn'))); stem['id'] = 'D6'
    ksk = next(k for k in st['sketches'] if k['id'] == stem['sketch'])
    old_x0 = min(p['u'] for p in ksk['points'])
    for p in ksk['points']:
        if abs(p['u'] - old_x0) < 1e-3: p['u'] = round(x0, 4)
        elif abs(p['u'] - (old_x0 + 0.2)) < 1e-3: p['u'] = round(x0 + 0.2, 4)
    drawn.append(stem)
    st['sketches'] = [ksk] + sks
    st['drawn'] = drawn
    st['fits'] = FITS
    # ---- the project
    P.update({'id': 'beta2-layered', 'name': 'Beta 2 · layered', 'title': 'Beta 2 · layered: plates that host the train'})
    P['blurb'] = (P['blurb'].split(' Module 0.6')[0] + ' Module 0.6, black delrin, brass rods. Plates in layers, each hosting the wheels at its own heights: '
                  'the 3/8" main plate high on the hour side and stepped down on the minute side; a 1/8" secondary plate on that step, the cradle that holds the stem down, '
                  'carries the crown, transfer and minute arbors and gives every top-layer wheel one unbroken floor; a 1/8" transfer plate along the south and east walls whose twin arms '
                  'carry the first intermediate down from a round anchor foot; a 1/8" NE plate; and the hour side\'s top plate, all flush. Two mirrored 1/16" bridges set flush into '
                  'the transfer plate and the top plate carry the minute and hour arbors\' top pivots, and the discs ride 0.3 above them on the arbors, like hands over a dial. '
                  f'Movement {2 * HX:.1f} x {2 * HY:.1f} mm: {z_hi - z_bot:.2f} mm from the back of the main plate to the top of the plates, {z_d + TT - z_bot:.2f} to the top of the discs.')
    P['source'] = list(P.get('source') or []) + ['Layered plates: Claude, 2026-11-24, from Adam\'s modification lists on Beta 2 · haute, then his 19 markup notes and sketches K55 and K56 (the cradle, '
                                                 'no breaks under wheels, the anchor merge, no ledges).']
    P['rules']['rod'] = {'d': 3.0, 'from': round(z_bot, 4), 'top': {'a1': round(rod_top['a1'], 5), 'a2': round(rod_top['a2'], 5)}}
    P['rules']['backlash'] = BACKLASH
    P['plate']['z'] = round(z_bot - 1.5, 4)
    for hd in P['defaults']['hands'].values(): hd['z'] = round(z_d, 5); hd['t'] = TT
    for hd in P.get('hands') or []:
        if hd['id'] == 'hour_disc': hd['role'] = 'Ø19 black delrin, numerals V-carved and filled; pressed on the hour arbor\'s post 0.3 above the hour bridge, like a hand over a dial. Turns the same way as the minute disc (four reductions).'
        if hd['id'] == 'minute_disc': hd['role'] = 'Ø19 black delrin, numerals V-carved and filled; pressed on the minute arbor\'s post 0.3 above the minute bridge, like a hand over a dial.'
    stg = P['defaults']['stages']
    stg['s_ba1'] = {'m': m, 'z': round(zA1w, 5), 'dz': dz_bp}
    stg['s_a1a2'] = {'m': m, 'z': round(zA2w, 5), 'dz': round((zA1w + TW) - (zA2w + TW / 2 - TP / 2), 5)}
    stg['s_a2h'] = {'m': m, 'z': round(zHw, 5), 'dz': round((zA2w + TW) - (zHw + TT / 2 - TP / 2), 5)}
    stg['s_mb'] = {'m': m, 'z': round(zBw, 5), 'dz': 0.0}; stg['s_em'] = {'m': m, 'z': round(zBw, 5), 'dz': 0.0}   # (the minute pinion level with both wheels)
    for a in P['arbors']:
        if a['id'] == 'hour': a['role'] = 'Turns once in 12 hours; its wheel runs low in the main plate (under the first intermediate\'s pinion level), the hour disc pressed on its rod above.'
        if a['id'] == 'a1': a['role'] = ('On the centre line. Its 22-tooth wheel is driven by the transfer pinion; its 11-tooth pinion drives the second intermediate. One piece of 1/8" delrin, '
                                         'deep in the main plate (bearing below), its top pivot in the transfer plate\'s pad on twin arms.')
        if a['id'] == 'a2': a['role'] = ('On the centre line, north of A1. Its 22-tooth wheel, 0.3 over A1\'s wheel, is driven by A1\'s pinion; its 13-tooth pinion drives the hour wheel. '
                                         'One piece of 1/8" delrin; one bearing down on A1\'s floor (P27), its top pivot in the top plate\'s pad on twin arms.')
        if a['id'] == 'minute': a['role'] = ('Turns once an hour. Its 12-tooth pinion, level with the transfer and crown wheels, takes the crown and drives the transfer arbor; it turns in plain delrin '
                                             '(the main plate, the secondary plate) and its top pivot is in the minute bridge, which keeps it from lifting. Its rod runs on up as the minute disc\'s post.')
        if a['id'] == 'hour': a['role'] = 'Turns once in 12 hours: two bearings in the main plate under its wheel, its top pivot in the hour bridge; its rod runs on up as the hour disc\'s post.'
        if a['id'] == 'b': a['role'] = 'Under the minute disc\'s lower edge: its wheel is driven by the minute pinion and turns on the secondary plate\'s floor; its pinion drives the first intermediate. Pivots: a bearing in the main plate, the secondary plate under its wheel.'
    P['groups']['drawn'] = 'Plates and stem'
    P['focus'] = [{'id': 'train', 'label': 'Crown → E → minute → transfer → first and second intermediate → hour', 'parts': ['e', 'minute', 'b', 'a1', 'a2', 'hour', 'D6']},
                  {'id': 'stack', 'label': 'The plates and bridges', 'parts': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8']},
                  {'id': 'under', 'label': 'Under the top layer: main and secondary plates, train', 'parts': ['D1', 'D2', 'D6', 'minute', 'b', 'a1', 'a2', 'hour', 'e']},
                  {'id': 'main', 'label': 'Main plate and train', 'parts': ['D1', 'D6', 'minute', 'b', 'a1', 'a2', 'hour', 'e']}]
    report = {'z': {k: (round(X['zb'], 4), round(X['zt'], 4)) for k, X in plates.items()}, 'screws': {k: X['screws'] for k, X in plates.items()},
              'areas': {k: round(X['F'].area, 1) for k, X in plates.items()}, 'pockets': {k: len(X['pockets']) for k, X in plates.items()},
              'bearings': [(a, nb, round(f, 4), round(b, 4)) for a, nb, f, b in bore_notes], 'notes': notes, 'problems': problems}
    return S, report, G_

def check(G_):
    out, notes = [], []
    things, plates, solid, floor_at = G_['things'], G_['plates'], G_['solid'], G_['floor_at']
    G, MESH, arbor_at = G_['G'], G_['MESH'], G_['arbor_at']
    items = list(G.items())
    for i, (n1, (a1, c1, r1, s1, e1)) in enumerate(items):
        for n2, (a2, c2, r2, s2, e2) in items[i + 1:]:
            if a1 == a2 or frozenset((n1, n2)) in MESH: continue
            if math.dist(c1, c2) < r1 + r2 + GAP - 1e-6 and s1 < e2 + GAP - 1e-6 and s2 < e1 + GAP - 1e-6:
                out.append(f'{n1} and {n2} clash (z {s1:.3f}..{e1:.3f} and {s2:.3f}..{e2:.3f})')
        for a, c in arbor_at.items():
            if a != a1 and math.dist(c1, c) < r1 + 1.5 + GAP - 1e-6 and s1 < G_['rod_top'][a] + GAP and e1 > G_['z_bot']:
                if not any(frozenset((n1, n)) in MESH for n, v in G.items() if v[0] == a): out.append(f'{n1} hits the {a} rod')
    for a, nb, f, bottom in G_['bore_notes']:
        if bottom < G_['z_bot'] - 1e-6: out.append(f'{a}\'s bearing would stand {G_["z_bot"] - bottom:.3f} out of the back')
        # the bearings are solids: flange (Ø7.2 x 0.6 in its seat), body (Ø6) and a second bearing pressed in from the back (Ø6 x 2.5)
        seat = f - BEARING['seat_depth']
        cyl = [('flange', C(arbor_at[a], 3.6), seat, seat + 0.6), ('body', C(arbor_at[a], 3.0), bottom, seat)]
        if nb == 2:
            cyl.append(('back bearing', C(arbor_at[a], 3.0), G_['z_bot'], G_['z_bot'] + 2.5))
            if G_['z_bot'] + 2.5 > bottom - 1e-6: out.append(f'{a}\'s back bearing overlaps its flanged bearing by {G_["z_bot"] + 2.5 - bottom:.3f}')
        for nm, g, z0, z1 in cyl:
            for n, a2_, g2, t0, t1, rg, ag in things:
                if a2_ == a or n.endswith(' rod') or n == 'stem journals': continue
                if t0 < z1 + AX - 1e-6 and t1 > z0 - AX + 1e-6 and g.distance(g2) < GAP - 1e-6:
                    out.append(f'{a}\'s bearing {nm} (z {z0:.3f}..{z1:.3f}) is within {g.distance(g2):.3f} of the {n} (z {t0:.3f}..{t1:.3f})')
    for X in plates.values():
        for n, a, g, t0, t1, rg, ag in things:
            if n in X['holds'] or (n.endswith(' rod') and a in X['pivots']): continue
            lo, hi = max(X['zb'], t0 - ag), min(X['zt'], t1 + ag)
            if lo >= hi - 1e-9: continue
            zs = {lo + 1e-6, hi - 1e-6} | {f + d for _, _, face, f in X['pockets'] if face != 'through' and lo < f < hi for d in (-1e-6, 1e-6)}
            ov = max(solid(X, z).intersection(g.buffer(rg - 1e-3, 64)).area for z in zs)
            if ov > 1e-4: out.append(f"{X['id']} plate has {ov:.4f} mm² inside the {n}'s room (z {t0:.3f}..{t1:.3f})")
        if 'stem journals' in X['holds']:
            t1 = next(t[4] for t in things if t[0] == 'stem journals')
            if not 0.04 < X['zb'] - t1 < 0.2: out.append(f"{X['id']} plate isn't just over the stem's journals ({X['zb'] - t1:.3f})")
        bottom = solid(X, X['zb'] + 1e-6)
        if len(pieces(bottom)) != 1: out.append(f"{X['id']} plate is in {len(pieces(bottom))} pieces")
        for a in X['pivots']:
            if not bottom.buffer(-0.6).contains(C(arbor_at[a], 1.54)): out.append(f"{X['id']} plate: under 0.6 of delrin round the {a} pivot")
            notes.append(f"{X['id']} pivots {a} over {floor_at(X, C(arbor_at[a], 1.54)) - X['zb']:.2f} mm")
    ps = list(plates.values())
    for X in ps:
        for Y in ps:
            if X is Y: continue
            if X['zb'] < Y['zb'] < X['zt'] - 1e-9:
                ov = solid(X, Y['zb'] + 1e-6).intersection(Y['F'].buffer(WELL * 0.8)).area
                if ov > 1e-4: out.append(f"{X['id']} plate stands {ov:.4f} mm² into the {Y['id']} plate above it")
    for i, X in enumerate(ps):
        for Y in ps[i + 1:]:
            if abs(X['zb'] - Y['zb']) < 1e-9 and X['F'].distance(Y['F']) < WELL - 1e-3: out.append(f"{X['id']} and {Y['id']} plates touch")
    for X in ps:
        for s in X['screws']:
            if not G_['path_ok'](X, s): out.append(f"{X['id']} plate: screw {s} has no solid path into the main plate")
        over = {'sec': ('tp', 'ne', 'bm'), 'tp': ('bm',), 'top': ('bh',)}.get(X['id'], ())
        through = len(X['screws']) + sum(1 for Y in over for q in plates[Y]['screws'] if X['F'].contains(Point(q)))
        if X['id'] not in ('main', 'bm', 'bh') and through < 2: out.append(f"{X['id']} plate is held by {through} screw(s)")
    held = {a: [] for a in arbor_at}
    for a, nb, f, b in G_['bore_notes']: held[a] += ['main plate bearing'] * nb
    held['minute'].append('main plate bushing'); held['e'].append('main plate bushing')
    for X in ps:
        for a in X['pivots']: held[a].append(f"{X['id']} plate")
    for a, h in held.items():
        if len(h) < 2: out.append(f'{a} is held at only one place ({h})')
        notes.append(f'{a}: ' + ', '.join(h))
    # Adam's rule (P3): under every wheel's whole sweep, one floor from one plate at one height. Allowed under it: the wheel's own arbor
    # (rod, bore, seat), the wheels it meshes, any wheel or the worm turning below it (the train's own layering).
    worm_g, w0, w1 = G_['worm']
    for n, (a, c, r, z0, z1) in G.items():
        want = z0 - AX
        sup = []
        for X in ps:
            if X['mill'] != 'back' or X['zb'] > want + 1e-6: continue
            for nn, p, face, f in X['pockets']:
                if face == 'top' and abs(f - want) < 1e-6: sup.append(p.intersection(X['F']).difference(U([q for _, q, fc, ff in X['pockets'] if fc == 'through' or (fc == 'top' and ff < want - 1e-6)])))
            if abs(X['zt'] - want) < 1e-6: sup.append(solid(X, X['zt'] - 1e-6))
        allowed = [C(c, BEARING['seat'] / 2 + 0.05)]
        for n2, (a2, c2, r2, s2, e2) in G.items():
            if n2 == n: continue
            if frozenset((n, n2)) in MESH or e2 <= z0 + 1e-6: allowed.append(C(c2, r2 + GAP))
        if w1 <= z0 + 1e-6 or n == 'crown arbor worm wheel': allowed += [worm_g.buffer(GAP), G_['worm_window']]   # (the worm turns under them, or meshes it: its window)
        allowedU = U(allowed).buffer(0.3, 64).buffer(-0.3, 64)       # (a gap under 0.6 between two allowed openings is one opening: a fin there comes down)
        brk = C(c, r).difference(U(sup)).difference(allowedU)
        if brk.area > 0.05:
            bx = [round(v, 1) for v in brk.bounds]
            notes.append(f'break under the {n}: {brk.area:.2f} mm² at x {bx[0]}..{bx[2]}, y {bx[1]}..{bx[3]}')
    return out, notes
