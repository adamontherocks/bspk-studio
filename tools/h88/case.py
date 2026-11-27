# H-88 "Spectrum" (1988 AMC Hemistitch): a case for Beta 2 · layered, first trace (2026-11-25). From Adam's Meshy model and product render
# (octagon body, vented shoulders, a big crown at 3), his stack sketch and his edits in the sim. Three parts and the glass (2026-11-25):
#   faceplate (the front, the top chamfers, the window, the top of the cavity) -> crystal (one piece, 1 mm acrylic, the window's shape + 1.0,
#   stepped and glued up against a ledge round the window, its centre flush with the window chamfer's foot) -> dial plate (1/16", clamped
#   between the plates and the cavity's ceiling, the discs turning in its two apertures 0.3 under the crystal) -> Beta 2 -> case middle (a
#   ring round the movement carrying the four lugs, the back bevel and the stem's slit) -> back plate (under it all).
# Everything goes in from the back: the crystal into its own pocket in the faceplate, glued against the ledge; the dial plate up against the
# cavity's ceiling; the faceplate onto the case middle on two dowels; Beta 2 with its stem and crown down into the ring (the stem through a
# slit open to the back, the crown outside the 3 o'clock wall); the back plate under it; six screws up through the back
# plate and the ring into the faceplate. No screw heads on the front: the exterior chamfers took the render's front screws' seats.
# Heights in Beta 2 · layered's frame: the movement from -3.6625 (back face) to 7.45 (plates), discs 7.75..9.3375.
import copy, math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

TT, TS = 1.5875, 3.175
CLR = 0.2                       # movement to cavity, all round
DIAL_T = 1.5875                 # the dial plate's face over the plates (the discs ride 0.3 over it)
# The crystal and dial plate (Adam, 2026-11-26): no glue, no screws. A flat 1 mm crystal (the stepped one's 0.4 edge was fragile: "it can
# just sit in the faceplate") drops in from the back against a LIP; the dial plate carries a perimeter ridge under the crystal's edge
# (hidden under the lip) and the movement backs the dial plate, so the case screws clamp the stack: lip / crystal / ridge / dial / movement.
LIP = 0.6                       # the faceplate's lip over the crystal's edge, at the window
RIDGE = dict(inner=0.15, outer=0.95, gap=0.1)   # the ridge: from the window + 0.15 to + 0.95 (inside the crystal's 1.0 overlap); the dial
#   pocket's ceiling stands 0.1 clear of the dial plate's face, so the ridge does the pressing
DISC_TO_CRYSTAL = 0.3           # the discs' tops to the crystal's underside
CRY_OUT, CRY_POCKET = 1.0, 1.1  # the crystal: the window's outline + 1.0 (Adam: cut to the viewing area, glued against a ledge); its pocket + 0.1
# The front's relief (Adam: "plaques are flush. chamfers descend from there... keep the chamfers close to the model", then, of the first
# half-depth pass: "whats on the screen is ledges... this model requires chamfers... build geometry to the most reasonable chamferable
# areas"). Levels from the Meshy model's height map at half its depth; every drop from the flush top is a 45° chamfer (the sim's
# cut.chamfer, cut with a 90° chamfer mill or V-bit), sized to the room each one has:
#   - the window: falls the whole RELIEF from the flush top (plaques, shoulders, ribs) to the crystal on a 45° chamfer, plaques included
#     (a 1/4" or 6 mm 90° chamfer mill: a 1/8" one reaches about 1.4);
#   - the sides: no rails or notches (their faces run clean; see the side chamfer below);
#   - the corner facets: a floor CF_DEPTH down along each of the octagon's chamfer edges, chamfered all round by its depth, with a slot in
#     the floor down at the crystal's level;
#   - the vents, counterbores and outer rim: small chamfers (CH_VENT, CH_CB, CH_RIM).
RELIEF = 2.0                    # flush top to the crystal: the window's chamfer
CH_WIN = RELIEF - LIP           # the window's chamfer: 45° from the flush top, then the lip straight down to the crystal (the drop stays RELIEF)
RIB_X = (RELIEF + 21.7, RELIEF + 22.7)            # the side rib, flush: from the window chamfer's top edge, 1.0 wide

CH_VENT = 0.15                  # the vents' rims
# The exterior (Adam, 2026-11-25, showing it on the 6 o'clock face and the 4:30 corner by pulling the top outline in: "exterior chamfers
# that stop this from being a brick and start making it architecturally interesting and more watch like... i know these are heavy
# chamfer but this is what the design calls for"): the walls stand straight from the back, then fall in on one 45° chamfer per face
# to a smaller top deck. His edit: about 48°, 6.3 in at 6 o'clock, 4.9 at the corner, the 3 o'clock face left straight. Here: 45° on
# every face (a straight pass of a 1/2" 90° chamfer mill along each face, run on past its ends, so neighbouring faces meet in crisp
# ridges; 1/4" collet), the widths by side:
#   - 12 and 6: 6.0 (the chamfer from 6.0 under the top: walls 5.8 to the cavity at its top);
#   - the four corners: 4.8 (it stops 1.0 short of the window's bezel; the corner walls keep 1.85 at the top of the cavity);
#   - 3 and 9: a 0.5 break (the window's bezel, the rib and the rail fill the sides; the crown is at 3).
# What sat where the chamfers now are moves: the plaque screws thread up from the back through the lug risers (no front heads), the
# side screws come in from the back only, the vents sit on the deck behind the plaques, the rails shorten, the corner facets go.
# The sides (Adam, 2026-11-26, tracing it on the 3 o'clock wall: "lowering the pocket above the crown down several mm and then running a
# chamfer along the sidewall down to the new pockets height... feel free to take some freedom to make it look good"): 3 and 9 fall in too,
# from the deck at the rib's outer edge down to the corners' foot height, so their ridges with the corner faces land on the octagon's
# corners and one foot line runs round the corners and sides. Steeper than 45° (that far in, 45° would take the window's bezel).
EXT_ANGLE = 45.0
SIDE_W = 27.25 - (RELIEF + 22.7)  # 3/9: from the rib's outer edge (x 24.7) to the wall
EXT_W = {'12/6': 6.0, 'corner': 4.8, '3/9': SIDE_W}
SIDE_ANGLE = math.degrees(math.atan2(EXT_W['corner'], SIDE_W))      # down 4.8 like the corners: 62.0°
EXT_ANGLES = [[0, SIDE_ANGLE], [45, EXT_ANGLE], [90, EXT_ANGLE], [135, EXT_ANGLE], [180, SIDE_ANGLE], [225, EXT_ANGLE], [270, EXT_ANGLE], [315, EXT_ANGLE]]
# The side faces run clean from corner to corner: a notch over the crown (floor z 7.0, 45° ends) was built and dropped (Adam: "the
# angled ledge cut out thing doesnt seem to go with the other rounded cut outs... drop and clean"); the side rails went with it.
EXT_WIDTHS = [[0, EXT_W['3/9']], [45, EXT_W['corner']], [90, EXT_W['12/6']], [135, EXT_W['corner']], [180, EXT_W['3/9']], [225, EXT_W['corner']],
              [270, EXT_W['12/6']], [315, EXT_W['corner']]]   # (facing direction in degrees, 0 = 3 o'clock, 90 = 12) -> width
VENT_Y, VENT_W, VENT_X = (13.8, 15.4, 17.0), 0.8, 9.0   # the vents on the deck behind each plaque: rows, width, half-length
CRYSTAL_T = 1.0                 # 1 mm acrylic, flat
# The viewing area (Adam: "that's a design feature that really makes this 1980s"), measured off the render with its discs 20.8 apart (as
# Beta 2's): an octagon 43.4 x 24.2, 45° chamfers 5.8 on the leg; the AMC and HEMISTITCH plaques bite 1.1 into its top and bottom edges
# across their 25 mm faces, with 45° ends; a thin red line runs round it just inside the edge (on the dial plate, engraved and filled).
WIN_HW, WIN_HH, WIN_CH = 21.7, 12.1, 5.8
# The plaques are a design element (Adam: "extend into the viewing area a little more... may even touch the top-down edges of the discs, that's
# part of the look"): each plaque's face comes down to the discs' edge (9.5 from the centre line), tangent to both discs' tops, and its 45°
# ends meet the window's top edge 1.5 short of the octagon's chamfer, as in the render.
DISC_R = 9.5
PLQ_HW, PLQ_BITE = 11.8, WIN_HH - DISC_R
RED_IN, RED_W, RED_D = 0.4, 0.7, 0.3
BACK_T = 0.8                    # back plate (1/32" acrylic: a display back, or delrin)
# The body's outline and screws, measured off the render at Beta 2's disc spacing (Adam: "compare the exterior profile including its chamfers
# as well as the screw location"): an octagon 54.5 x 49.2 with 45° chamfers 12.8 on the leg; Beta 2's own corners are chamfered 4.5 to
# match, so the corner walls stay 3.0. The render's eight front screws (four at the plaques' ends over the lugs, four on the side rails)
# sat where the exterior chamfers now fall, so the same eight positions are screwed from the back: up through each lug riser into the
# body (they clamp the lugs into it), and into the body's sides (they clamp the lug plate).
W, H, CH = 54.5, 49.2, 12.8     # the body (the render's)
LUG_X = (11.0, 17.0)            # lug inner and outer faces: a 22 mm strap, each lug 6.0 wide (Adam: "beefier wider lugs, 6mm"; earlier 4.0 "look dinky")
                                #  under the 12 and 6 faces, their outer halves out under the corners (the strap: 22 mm, as Adam set it)
RISE, SLOT_Y0 = 6.5, 17.5       # Adam (lugs up): each lug rises this far into a slot cut up into the body from its back, open to the 12/6 face
PLQ_SCR = (16.0, 19.6)          # the plaque screws (M2, from the back): up through each lug riser's centre into the body above its slot
SIDE_SCR = (24.65, 9.0)         # the side-rail screws (M1.6, the render's spots)
EYE_R, EYE_OUT = 2.5, 2.7      # the lug's eye: its boss (now faceted on the octagon round this radius) and its centre this far out from the body
SCREW_BAR = dict(tube=2.0, hole=2.05, head=2.6, seat=2.8, seat_depth=0.9)   # screw bars, not spring bars (Adam, 2026-11-25): a Ø2.0 tube across the strap, through both
#   lugs, a hex-head screw into each end from the outer faces, heads sunk flush in seats. Placeholder sizes: set them from the bars once they're in hand.
LUG_CHAMFER = dict(across=2.0, down=0.6)   # the lugs' outer top edges (Adam: "start the chamfer at 2mm to the edge"): 2.0 in across the top faces, 0.6 down the outer
#   face; steeper than 45° so the screw head's seat keeps 0.5 clear of it (a 2 x 2 chamfer would run into the seat)
# The case in three (Adam, 2026-11-25: "break the main case into two parts. the upper face plate, then... a lower plate that just sits
# there as separation... could the lug and back plate now be married?", and the lugs "more central... the lug holes will sit at the lower
# 1/3 line", their tops where the top chamfer starts "or a few mm below"):
#   - faceplate (D9), from the split up: the front, the top chamfers, the window and crystal, the cavity's top. 5/16" sheet, one flip.
#   - case middle (D12), from the movement's back face up to the split: a ring round Beta 2 with the four lugs (D14-D17, its horns), the
#     back bevel and the stem's slit. 3/8" sheet, cut flat from its back; then the lugs' side profiles and spring bar
#     holes on the Air's 4th axis (indexed to +-90°, the case's 12-6 line along the rotary axis, screwed to a fixture through its own
#     screw holes).
#   - back plate (D13): one 1/16" plate under it all (delrin, or clear acrylic as a display back), its edge carrying the bevel on. Six
#     M2 screws come up through it and the ring into the faceplate; two dowels line the faceplate and ring up.
Z_SPLIT = 5.0                   # faceplate / case middle: the lugs' tops, 1.64 under the top chamfer's foot
BEVEL_ANGLE = 67.5              # the back bevel (Adam's 9 o'clock edit): 22.5° off vertical, a 45° V-bit along each face
BEVEL_W = {'12/6': 2.8, 'corner': 1.2, '3/9': 2.8}   # its width at the back plate's bottom (the corner walls are 3.05)
SCREW_XY = [(x, sy * 18.2) for x in (-12.0, 0.0, 12.0) for sy in (1, -1)]   # the six M1.6 screws: in the 12 and 6 walls, between the cavity and the panels
SCREW = dict(tap=1.25, clear=1.8, head=3.8, head_depth=0.7, tap_depth=5.0)  # M1.6: tapped in the faceplate, clear through the ring and back plate;
#   ultra-thin wafer heads (Ø3.5 x 0.6 or less) sunk flush in the back plate (Adam: sunk; a cheese head's 1.0 stood 0.2 proud)
CROWN = dict(gap=0.4, neck_r=1.2)   # the crown proud of the 3 o'clock wall (Adam, 2026-11-26), on a longer stem; its neck Ø2.4 through the wall
# The chamfer panels (Adam traced them in the sim, 2026-11-25: "this area would be a shallow relief like the reference image"; then "stright
# down is fine. and a radius for the cutter is fine... just deeper towards the epicenter and shallower on the perimeter of the case"): a
# pocket in each of the six big chamfer faces (12, 6 and the four corners), cut straight down from the front with a flat floor, so it is
# shallow at the case's edge and deeper toward the middle (by the panel's width across: the faces are 45°); its inside corners r 1.0 (a Ø2
# cutter). The outlines are the faces' own, inset as he traced them (his three traces, mirrored to the 12 o'clock side).
PANEL_12 = dict(inner=1.44, outer=1.43, side=2.1, edge_depth=1.0)     # 12/6: in from the deck edge and the octagon edge (plan), off the ridges; depth at the outer edge
PANEL_CORNER = dict(inner=1.1, outer=1.5, side=1.6, end=1.75, edge_depth=0.75)   # corners: the same, and kept 1.75 off the 3/9 face; shallower (Beta 2's corner is behind)
PANEL_R = 1.0
DIAL_CORNER = 5.0                # the dial plate's corners cut back to 5.0 in from the case's corner chamfer lines, so the faceplate stays solid behind the corner panels
DOWEL_XY, DOWEL_D, DOWEL_DEPTH = [(25.1, -7.0), (-25.1, 7.0)], 1.5, 3.0     # faceplate to case middle (clear of the stem's slit)
HORN_IN = 21.0                  # each lug's root runs this far in (inside the ring's wall, under the octagon's corner)

def rrect(w, h, r, c=(0.0, 0.0)): return box(c[0] - w / 2 + r, c[1] - h / 2 + r, c[0] + w / 2 - r, c[1] + h / 2 - r).buffer(r, 64)
def octagon():
    pts = [(W / 2 - CH, H / 2), (-(W / 2 - CH), H / 2), (-W / 2, H / 2 - CH), (-W / 2, -(H / 2 - CH)), (-(W / 2 - CH), -H / 2),
           (W / 2 - CH, -H / 2), (W / 2, -(H / 2 - CH)), (W / 2, H / 2 - CH)]
    return Polygon(pts)     # (sharp: the exterior chamfers meet in crisp ridges at its corners)
def stadium(x0, x1, y, w):
    from shapely.geometry import LineString
    return LineString([(x0 + w / 2, y), (x1 - w / 2, y)]).buffer(w / 2, 32)
def halves(ring):
    """a ring as two C-shaped pieces (a pocket's sketch is one outline, no holes)"""
    big = 200.0
    return [g for g in (ring.intersection(box(-big, -big, 0.0, big)), ring.intersection(box(0.0, -big, big, big))) if not g.is_empty]

def build(layered_scene, info, helpers):
    sketch, poly_dots = helpers['sketch'], helpers['poly_dots']
    S = copy.deepcopy(layered_scene); P, st = S['project'], S['state']
    st['fits'] = {**(st.get('fits') or {}),
                  'm16_tap': {'d': SCREW['tap'], 'seat': None, 'note': 'M1.6 tapped thread in delrin (placeholder until the coupon)'},
                  'm16_clear': {'d': SCREW['clear'], 'seat': None, 'note': 'M1.6 screw passing through'},
                  'm16_cb_back': {'d': SCREW['clear'], 'seat': {'d': SCREW['head'], 'depth': SCREW['head_depth']},
                                  'note': 'M1.6 case screw through the back plate, its ultra-thin wafer head (Ø3.5 x 0.6 or less) sunk flush'}}
    HX, HY = 22.75, 16.2
    z_back, z_plates, z_disc1 = -3.6625, 7.45, 7.75 + TT
    stem = next(d for d in st['drawn'] if d['id'] == 'D6'); kst = next(k for k in st['sketches'] if k['id'] == stem['sketch'])
    zw = stem['turn']['v']; prof = [(p['u'], p['v']) for p in kst['points']]
    crown_x0 = min(u for u, v in prof if v > 2.0 and u > 20); crown_r = max(v for u, v in prof) - zw
    # the crown out past the wall by CROWN['gap']: the stem made longer (in this case's copy), its neck fattened to Ø2.4 from just outside
    # the plates (they hold its Ø1.8 journal) to the crown, so the longer reach is stiffer and easier to turn
    dx_c = W / 2 + CROWN['gap'] - crown_x0; neck_from = HX + 0.6; neck_r = CROWN['neck_r']
    new_pts = []
    for q in kst['points']:
        u, v = q['u'], q['v']
        if abs(u - crown_x0) < 1e-6 and abs(v - zw - 0.9) < 1e-3:          # the neck's end at the crown: the step up to the fat neck first
            new_pts += [{'u': round(neck_from, 4), 'v': round(zw + 0.9, 4), 'smooth': False}, {'u': round(neck_from + 0.3, 4), 'v': round(zw + neck_r, 4), 'smooth': False},
                        {'u': round(u + dx_c, 4), 'v': round(zw + neck_r, 4), 'smooth': False}]
            continue
        new_pts.append({**q, 'u': round(u + dx_c, 4) if u >= crown_x0 - 1e-6 else u})
    kst['points'] = new_pts
    if stem.get('flutes'):                                              # the crown's grip flutes go out with it
        stem['flutes'] = {**stem['flutes'], 'from': round(stem['flutes']['from'] + dx_c, 4), 'to': round(stem['flutes']['to'] + dx_c, 4)}
    stem['name'] = ('Crown, stem and worm (one piece of 3/8" black delrin rod, cut on the 4th axis): in the H-88 the stem is %.1f longer, so the crown '
                    'stands %.1f proud of the 3 o\'clock wall, its neck Ø%.1f through the wall' % (dx_c, CROWN['gap'], 2 * neck_r))
    crown_x0 += dx_c
    # ---- heights
    z_dial0, z_dial1 = z_plates, z_plates + DIAL_T
    z_cry0 = z_disc1 + DISC_TO_CRYSTAL; z_cry1 = z_cry0 + CRYSTAL_T
    z_ridge = z_cry0                                   # the dial plate's ridge reaches the crystal's underside
    z_ring = z_cry1                                    # the inner ring: flush with the crystal
    z_top = z_ring + RELIEF                            # the flush top: shoulders, pads, ribs
    z_frame0 = z_back - TT                             # the back plate's bottom (the case's back)
    # ---- outlines
    main = next(d for d in st['drawn'] if d['id'] == 'D1'); kmain = next(k for k in st['sketches'] if k['id'] == main['sketch'])
    mov = Polygon([(p['u'], p['v']) for p in kmain['points']]).buffer(0)          # Beta 2's outline (its corners chamfered 4.5, as the case)
    cav = mov.buffer(CLR, 64, join_style=1)                                          # the movement + 0.2: everything from the back passes it
    insert = mov.buffer(CLR - 0.1, 64, join_style=1)                                 # crystal, dial plate, back plate: 0.1 inside it
    cc_ = W / 2 + H / 2 - CH - DIAL_CORNER * math.sqrt(2)                            # the dial plate: its corners cut back parallel to the case's corner
    dial_outline = insert.intersection(Polygon([(cc_, 0), (0, cc_), (-cc_, 0), (0, -cc_)])).buffer(-1.1, 64, join_style=1).buffer(1.1, 64, join_style=1)  # (r 1.1: its pocket's corners r 1.2)
    dial_pocket = dial_outline.buffer(0.1, 64, join_style=1)
    def oct_(hw, hh, ch): return Polygon([(hw - ch, hh), (-(hw - ch), hh), (-hw, hh - ch), (-hw, -(hh - ch)), (-(hw - ch), -hh), (hw - ch, -hh), (hw, -(hh - ch)), (hw, hh - ch)])
    win_oct = oct_(WIN_HW, WIN_HH, WIN_CH)
    yb = WIN_HH - PLQ_BITE
    plaques = [Polygon([(-PLQ_HW, sy * yb), (PLQ_HW, sy * yb), (PLQ_HW + 3.0, sy * (yb + 3.0)), (-PLQ_HW - 3.0, sy * (yb + 3.0))]) for sy in (1, -1)]
    window = win_oct.difference(unary_union(plaques))   # (sharp: its chamfer's corners are crisp mitres; the end mill's radius in its 135° corners is 0.02 off)
    red = win_oct.buffer(-RED_IN, join_style=2).difference(win_oct.buffer(-(RED_IN + RED_W), join_style=2))
    cry_out = window.buffer(CRY_OUT, 64, join_style=1).buffer(0.5, 64).buffer(-0.5, 64)   # the crystal: the window + 1.0 (its inside corners r 0.5, as cut)
    cry_pocket = window.buffer(CRY_POCKET, 64, join_style=1)                               # its pocket, up from the back to the lip
    ridge_in, ridge_out = window.buffer(RIDGE['inner'], 64, join_style=1), window.buffer(RIDGE['outer'], 64, join_style=1)   # the dial plate's ridge between
    body = octagon()
    # ---- the front's relief: the window chamfered down to the crystal; the deck the exterior chamfers leave
    win_top = window.buffer(CH_WIN, 64, join_style=2)                                     # the window chamfer's top edge
    def ext_w(deg):
        t = sorted(EXT_WIDTHS); a = deg % 360
        for (d0, w0), (d1, w1) in zip(t, t[1:] + [[t[0][0] + 360, t[0][1]]]):
            if d0 <= a <= d1: return w0 + (w1 - w0) * (a - d0) / (d1 - d0)
        return t[0][1]
    def ext_t(deg):        # each face's slope (tan of its angle from the deck)
        t = sorted(EXT_ANGLES); a = deg % 360
        for (d0, w0), (d1, w1) in zip(t, t[1:] + [[t[0][0] + 360, t[0][1]]]):
            if d0 <= a <= d1: return math.tan(math.radians(w0 + (w1 - w0) * (a - d0) / (d1 - d0)))
        return math.tan(math.radians(t[0][1]))
    def deck_at(depth):    # the exterior's section `depth` under the top: each face's half-plane moved in by what's left of its chamfer there
        cuts_ = []
        ring = list(body.exterior.coords)[:-1]
        if Polygon(ring).exterior.is_ccw is False: ring = ring[::-1]
        poly = body
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            L = math.hypot(x1 - x0, y1 - y0); nx, ny = (y1 - y0) / L, -(x1 - x0) / L          # outward normal (anticlockwise ring)
            dg = math.degrees(math.atan2(ny, nx)); w = max(0.0, ext_w(dg) - depth / ext_t(dg))
            if w > 0: poly = poly.difference(Polygon([(x0 + nx * 50 - ny * 99, y0 + ny * 50 + nx * 99), (x0 + nx * 50 + ny * 99, y0 + ny * 50 - nx * 99),
                                                       (x0 - nx * w + ny * 99, y0 - ny * w - nx * 99), (x0 - nx * w - ny * 99, y0 - ny * w + nx * 99)]))
        return poly
    deck = deck_at(0.0)
    # ---- the chamfer panels: each big face's own region (where its plane lies deepest), inset; a flat floor under its outer edge
    ring_e = list(body.exterior.coords)[:-1]
    if not Polygon(ring_e).exterior.is_ccw: ring_e = ring_e[::-1]
    faces_e = []
    for (x0, y0), (x1, y1) in zip(ring_e, ring_e[1:] + ring_e[:1]):
        L = math.hypot(x1 - x0, y1 - y0); nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        faces_e.append(dict(p=(x0, y0), q=(x1, y1), n=(nx, ny), w=ext_w(math.degrees(math.atan2(ny, nx))), t=ext_t(math.degrees(math.atan2(ny, nx)))))
    def half(a, b, c):             # the half-plane a x + b y + c >= 0, as a big polygon
        L = math.hypot(a, b); ux, uy = a / L, b / L; px, py = -c * ux / L, -c * uy / L
        return Polygon([(px - uy * 200, py + ux * 200), (px + uy * 200, py - ux * 200), (px + uy * 200 + ux * 200, py - ux * 200 + uy * 200), (px - uy * 200 + ux * 200, py + ux * 200 + uy * 200)])
    def dist_coef(f):              # dist in from face f's edge line = a x + b y + c
        (x0, y0), (nx, ny) = f['p'], f['n']; return -nx, -ny, nx * x0 + ny * y0
    panels = []
    for f in faces_e:
        if f['w'] < 2.0 or abs(f['n'][1]) < 1e-6: continue          # (3 and 9 run clean)
        PP = PANEL_12 if abs(f['n'][0]) < 1e-6 else PANEL_CORNER
        a, b, c = dist_coef(f); reg = body
        tf = f['t']
        for g2 in faces_e:              # where this face's plane lies deepest: t_f (w_f - dist_f) >= t_g (w_g - dist_g)
            if g2 is f: continue
            a2, b2, c2 = dist_coef(g2); tg = g2['t']
            reg = reg.intersection(half(tg * a2 - tf * a, tg * b2 - tf * b, tg * c2 - tf * c + tf * f['w'] - tg * g2['w']))
        band = half(a, b, c - PP['outer']).intersection(half(-a, -b, -c + f['w'] - PP['inner']))
        pan = reg.intersection(band)
        ridges = [LineString(seg) for seg in zip(list(reg.exterior.coords)[:-1], list(reg.exterior.coords)[1:])
                  if body.exterior.distance(LineString(seg).interpolate(0.5, normalized=True)) > 1e-3 and deck.exterior.distance(LineString(seg).interpolate(0.5, normalized=True)) > 1e-3]
        for rl in ridges: pan = pan.difference(rl.buffer(PP['side'], 32))
        if 'end' in PP: pan = pan.difference(box(W / 2 - PP['end'], -H, W, H)).difference(box(-W, -H, -W / 2 + PP['end'], H))
        pan = pan.buffer(-PANEL_R, 32, join_style=1).buffer(PANEL_R, 32, join_style=1)
        if pan.geom_type != 'Polygon' or pan.area < 1.0: continue
        floor = z_top - tf * (f['w'] - PP['outer']) - PP['edge_depth']   # under the outer edge by edge_depth
        panels.append(dict(poly=pan, face=round(math.degrees(math.atan2(f['n'][1], f['n'][0])) % 360), floor=floor, depth=z_top - floor,
                           edge=PP['edge_depth'], inner=round(tf * (f['w'] - PP['inner'] - PP['outer']) + PP['edge_depth'], 3)))
    front = dict(win_top=win_top, deck=deck, deck_at=deck_at, panels=panels)
    discs = [(10.4, 0.0), (-10.4, 0.0)]
    # the crown stands outside the 3 o'clock wall; the stem's neck passes the wall in a slit open to the back (and to the outside)
    slit = box(HX, -(neck_r + 0.2), W / 2 + 1.0, neck_r + 0.2)
    # ---- the case middle's lugs (horns): each one's side profile (y out from the centre, z up), drawn on its inner face's plane and grown
    # across its 6.0: flat on top at the split, 45° down toward its eye (the screw bar at the lower third of the case's height), the eye's end
    # faceted on the octagon round it (Adam: "lets facet off the round": faces square to 45°, 0°, -45° and -90°, each tangent to the old round),
    # flat underneath, its root running in under the octagon's corner into the ring's wall
    eye_y = H / 2 + EYE_OUT
    eye_z = z_frame0 + (z_top - z_frame0) / 3
    kq = EYE_R * math.sqrt(2) - EYE_R                                   # how far each octagon corner sits along a face from its tangent point
    lug_side = [(HORN_IN, Z_SPLIT), (eye_y + eye_z + EYE_R * math.sqrt(2) - Z_SPLIT, Z_SPLIT), (eye_y + EYE_R, eye_z + kq), (eye_y + EYE_R, eye_z - kq),
                (eye_y + kq, eye_z - EYE_R), (HORN_IN, eye_z - EYE_R)]
    # the back bevel: one plane per face at BEVEL_ANGLE, BEVEL_W in at the back plate's bottom; the ring carries what's left at its own bottom
    bev_drop = TT / math.tan(math.radians(BEVEL_ANGLE))                   # how much of it the back plate's thickness takes
    def bev_w(deg, at_back_plate=True):
        a = deg % 360; t = [(0, '3/9'), (45, 'corner'), (90, '12/6'), (135, 'corner'), (180, '3/9'), (225, 'corner'), (270, '12/6'), (315, 'corner'), (360, '3/9')]
        for (d0, k0), (d1, k1) in zip(t, t[1:]):
            if d0 <= a <= d1: w = BEVEL_W[k0] + (BEVEL_W[k1] - BEVEL_W[k0]) * (a - d0) / (d1 - d0); break
        return w if at_back_plate else w - bev_drop
    ring_widths = [[d, round(bev_w(d, False), 4)] for d in range(0, 360, 45)]
    def inset_by(poly, wf):    # the outline with each face moved in by its own width (mitred)
        ring = list(poly.exterior.coords)[:-1]
        if not Polygon(ring).exterior.is_ccw: ring = ring[::-1]
        out = poly
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            L = math.hypot(x1 - x0, y1 - y0); nx, ny = (y1 - y0) / L, -(x1 - x0) / L
            w = wf(math.degrees(math.atan2(ny, nx)))
            if w > 0: out = out.difference(Polygon([(x0 + nx * 50 - ny * 99, y0 + ny * 50 + nx * 99), (x0 + nx * 50 + ny * 99, y0 + ny * 50 - nx * 99),
                                                   (x0 - nx * w + ny * 99, y0 - ny * w - nx * 99), (x0 - nx * w - ny * 99, y0 - ny * w + nx * 99)]))
        return out
    back_outline = inset_by(body, lambda deg: bev_w(deg, False))           # the back plate: the ring's bottom outline, bevelled on under it
    scr = list(SCREW_XY)
    kn = [400]
    def newk(): kn[0] += 1; return f'K{kn[0]}'
    sks, parts = [], []
    def part(pid, name, outline, z0, t, cuts, mill='back', chamfer=None):
        k = newk(); sks.append(sketch(k, f'{name.split(" (")[0]} outline', 'z', round(z0, 5), poly_dots(outline)))
        parts.append({'id': pid, 'name': name, 'sketch': k, 'thickness': round(t, 5), 'grow': 'plus', 'mill': mill, 'minWall': 0.6, 'cuts': cuts,
                      **({'chamfer': chamfer} if chamfer else {})})
    def pocket(name, poly, frm, depth, hid, chamfer=None, chamfer_widths=None):
        if list(getattr(poly, 'interiors', [])): raise ValueError(f'{name}: a pocket with a hole (cut it as halves)')
        k = newk(); sks.append(sketch(k, name, 'z', 0.0, poly_dots(poly)))
        return {'id': f'h{hid}', 'kind': 'pocket', 'name': name, 'sketch': k, 'from': frm, 'depth': None if depth is None else round(depth, 4),
                **({'chamfer': chamfer} if chamfer else {}), **({'chamferWidths': chamfer_widths} if chamfer and chamfer_widths else {})}
    def hole(kind, name, at, d, frm, hid, depth=None, seat=None, fit=None, chamfer=None):
        c = {'id': f'h{hid}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': frm, 'depth': depth}
        if seat: c['seat'] = seat
        if fit: c['fit'] = fit
        if chamfer: c['chamfer'] = chamfer
        return c
    T_face, T_mid = z_top - Z_SPLIT, Z_SPLIT - z_back
    hn = [0]
    def nid(): hn[0] += 1; return hn[0]
    # ---- D9 faceplate: from the split to the deck
    bc = [pocket('Window: chamfered 45° %.1f down from the flush top, then the lip straight down %.1f to the crystal; plaques included' % (CH_WIN, LIP), window, 'back', None, nid(), chamfer=CH_WIN),
          pocket('Cavity: the top of Beta 2, up to its plates\' tops', cav, 'front', z_plates - Z_SPLIT, nid()),
          pocket('Dial plate pocket (the dial plate + 0.1; its corners cut back, so the faceplate stays solid under the corner panels): its ceiling stands %.1f clear of the dial plate, whose ridge presses the crystal' % RIDGE['gap'], dial_pocket, 'front', z_dial1 + RIDGE['gap'] - Z_SPLIT, nid()),
          pocket('Crystal pocket (the window + 1.1): the crystal drops in from the back against the %.1f lip; the dial plate\'s ridge holds it there (no glue)' % LIP, cry_pocket, 'front', z_cry1 - Z_SPLIT, nid())]
    for sy in (-1, 1):
        for y in VENT_Y: bc.append(pocket('Vent (on the deck behind the plaque)', stadium(-VENT_X, VENT_X, sy * y, VENT_W), 'back', 1.0, nid(), chamfer=CH_VENT))
    for s in scr: bc.append(hole('pilot', 'Case screw, M1.6x14: tapped %.1f up from the split (it comes up through the back plate and the case middle)' % SCREW['tap_depth'], s, SCREW['tap'], 'front', nid(), depth=SCREW['tap_depth'], fit='m16_tap'))
    for pn in panels:
        bc.append(pocket('Chamfer panel (%d°): cut straight down from the front to a flat floor at z %.2f, %.2f deep at its outer edge and %.2f at its inner edge; inside corners r %.1f'
                         % (pn['face'], pn['floor'], pn['edge'], pn['inner'], PANEL_R), pn['poly'], 'back', pn['depth'], nid()))
    for s in DOWEL_XY: bc.append(hole('dowel', f'Dowel Ø{DOWEL_D} (lines the faceplate up on the case middle)', s, DOWEL_D, 'front', nid(), depth=DOWEL_DEPTH))
    part('D9', 'Faceplate (black delrin, 5/16" faced to %.2f; milled from the front, then the back): the walls fall in on exterior chamfers (45°: 6.0 at 12 and 6, '
               '4.8 at the corners; %.1f° at 3 and 9, %.2f in, down to the corners\' foot) to the deck, the window chamfered down to the crystal, the vents; the cavity\'s top, the '
               'crystal\'s pocket and ledge, the screws\' tapped holes and the dowel holes from the back' % (T_face, SIDE_ANGLE, SIDE_W), body, Z_SPLIT, T_face, bc,
         chamfer={'face': 'back', 'size': EXT_W['3/9'], 'angle': EXT_ANGLE, 'widths': EXT_WIDTHS, 'angles': [[a_, round(v, 4)] for a_, v in EXT_ANGLES]})
    cry = []
    part('D10', 'Crystal (1 mm clear acrylic, flat, the window\'s shape + 1.0): in from the back against the faceplate\'s %.1f lip, held there by the dial plate\'s ridge' % LIP, cry_out, z_cry0, CRYSTAL_T, cry)
    parts[-1]['glass'] = True                         # (drawn see-through in the sim)
    dc = [hole('clear', f'Disc aperture ({nm})', c, 19.6, 'back', i + 1) for i, (c, nm) in enumerate(zip(discs, ('minute', 'hour')))]
    ridge_h = z_ridge - z_dial1
    dc += [pocket('The face, inside the ridge (%.1f down from its top)' % ridge_h, ridge_in, 'back', ridge_h, 20)]
    dc += [pocket('Round the ridge, out to the edge (%.1f down)' % ridge_h, hp, 'back', ridge_h, 21 + i) for i, hp in enumerate(halves(dial_outline.difference(ridge_out)))]
    red_cut = red.difference(ridge_out.difference(ridge_in))          # (the red line stops either side of the ridge, under the plaques)
    red_pcs = [g_ for hp in halves(red_cut) for g_ in (getattr(hp, 'geoms', None) or [hp]) if g_.area > 0.05]
    dc += [pocket('Red line (engraved, filled red): just inside the window, round under the plaques', hp, 'back', ridge_h + RED_D, 7 + i) for i, hp in enumerate(red_pcs)]
    part('D11', 'Dial plate (3/32" black delrin, faced to %.2f): on the plates, its perimeter ridge (%.1f wide, %.1f tall, hidden under the lip) pressing the crystal up; the discs turn in its apertures, ' % (DIAL_T + z_ridge - z_dial1, RIDGE['outer'] - RIDGE['inner'], z_ridge - z_dial1) + 
                '0.3 under the crystal; no screws or holes (the movement\'s screws are all sunk flush); its corners cut back %.1f in from the case\'s corner chamfer lines (hidden under the faceplate)' % DIAL_CORNER, dial_outline, z_dial0, DIAL_T + z_ridge - z_dial1, dc)
    # ---- D12 case middle: from the movement's back face to the split
    hn[0] = 0
    mc = [pocket('Opening: Beta 2 drops in from the back', cav, 'front', None, nid()),
          pocket('Stem slit (open to the back)', slit, 'front', zw + neck_r + 0.2 - z_back, nid())]
    for s in scr: mc.append(hole('clear', 'Case screw, M1.6: clearance up through the case middle', s, SCREW['clear'], 'front', nid(), fit='m16_clear'))
    for s in DOWEL_XY: mc.append(hole('dowel', f'Dowel Ø{DOWEL_D}', s, DOWEL_D, 'back', nid(), depth=DOWEL_DEPTH))
    part('D12', 'Case middle (black delrin, 3/8" faced to %.2f): a ring round Beta 2 carrying the four lugs (D14-D17), cut flat from its back: the outline, the back '
                'bevel (%.1f° from the face, a 45° V-bit along each face), the opening, the stem\'s slit, the screw and dowel holes; then the lugs\' '
                'side profiles and spring bar holes on the 4th axis (indexed to +-90°, the 12-6 line along the rotary axis, screwed to a fixture through its own '
                'screw holes)' % (T_mid, BEVEL_ANGLE), body, z_back, T_mid, mc,
         chamfer={'face': 'front', 'size': round(bev_w(0, False), 4), 'angle': BEVEL_ANGLE, 'widths': ring_widths})
    # ---- D13 back plate: one plate under it all
    bk = [hole('clear', 'Case screw, M1.6x14 ultra-thin wafer head (Ø3.5 x 0.6 or less): up through the back plate, sunk flush on the wrist side', s, SCREW['clear'], 'front', i + 1,
               seat={'d': SCREW['head'], 'depth': SCREW['head_depth']}, fit='m16_cb_back')
          for i, s in enumerate(scr)]
    part('D13', 'Back plate (1/16" black delrin, or clear acrylic as a display back): under the case middle and Beta 2, its edge carrying the back bevel on; the six case '
                'screws come up through it', back_outline, z_frame0, TT, bk, chamfer={'face': 'front', 'size': round(bev_drop, 4), 'angle': BEVEL_ANGLE})
    # ---- D14-D17 the lugs: the case middle's horns (one piece with it), each drawn as its side profile, grown across its 6.0
    side = lug_side
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        k = newk(); pts = [(sy * u, v) for u, v in side]
        if sy < 0: pts = pts[::-1]
        sks.append({'id': k, 'name': f'Lug {i + 1} side profile', 'plane': {'axis': 'x', 'offset': round(LUG_X[0] if sx > 0 else -LUG_X[1], 4)}, 'closed': True,
                    'points': [{'u': round(u, 4), 'v': round(v, 4), 'smooth': False} for u, v in pts]})
        outer = 'back' if sx > 0 else 'front'           # (the face away from its sketch plane is 'back')
        up = {0: 0, 45: 0, 90: 1, 135: 0, 180: 0, 225: 0, 270: 0, 315: 0}
        for a_ in ((0, 45) if sy > 0 else (135, 180)): up[a_] = 1                # the top flat, the 45° face and the end: the edges that get it
        parts.append({'id': f'D{14 + i}', 'name': f'Lug {i + 1} ({"3" if sx > 0 else "9"} o\'clock side, {"12" if sy > 0 else "6"} o\'clock end): part of the case middle, '
                                                  f'flat on top at the split, 45° down toward its eye, the end faceted; its outer top edges chamfered {LUG_CHAMFER["across"]:.1f} '
                                                  f'in; its side profile, chamfer and screw bar hole cut on the 4th axis',
                      'sketch': k, 'thickness': round(LUG_X[1] - LUG_X[0], 4), 'grow': 'plus', 'mill': 'back', 'minWall': 0.6,
                      'chamfer': {'face': outer, 'size': LUG_CHAMFER['down'], 'angle': round(math.degrees(math.atan2(LUG_CHAMFER['across'], LUG_CHAMFER['down'])), 4),
                                  'widths': [[a_, LUG_CHAMFER['down'] * up[a_]] for a_ in sorted(up)]},
                      'cuts': [{'id': 'h1', 'kind': 'clear', 'name': f'Screw bar: the Ø{SCREW_BAR["tube"]} tube\'s hole through the lug, its hex-head screw sunk flush in a '
                                                               f'Ø{SCREW_BAR["seat"]} x {SCREW_BAR["seat_depth"]} seat in the outer face',
                                'at': [round(sy * eye_y, 4), round(eye_z, 4)], 'd': SCREW_BAR['hole'], 'from': outer, 'depth': None,
                                'seat': {'d': SCREW_BAR['seat'], 'depth': SCREW_BAR['seat_depth']}}]})
    st['sketches'] = st['sketches'] + sks
    st['drawn'] = st['drawn'] + parts
    # ---- the project
    P.update({'id': 'h88-case', 'name': 'H-88 Spectrum · case', 'title': 'H-88 Spectrum: a case for Beta 2'})
    # ---- the discs' faces: the AXIS word discs (Adam, 2026-11-26, from the AXIS renders: "radial words, not stacked... no frame or tick
    # marks... accept the v bits 1.1mm"): the hours written out on the left disc, the minutes in fives on the right, each word along its
    # radius against the rim; they're read where the discs face each other, across the middle, as one phrase ("TWELVE FORTY-FIVE").
    # Letters 1.1 tall (V-carved and filled) in Orbitron (Adam, 2026-11-26: an 80s face, "michroma and orbitron are great... you make a
    # call": Orbitron, the narrower of the two; Michroma would squeeze even TWELVE to 79%), from 2.6 off the centre (where neighbouring words'
    # inner ends keep 0.25 apart: Orbitron's words are long enough that most reach the hub) to 0.4 off the rim; words longer than that are
    # narrowed to fit (TWENTY-FIVE to about 51%, THIRTY-FIVE 58%, FORTY-FIVE 59%, FIFTY-FIVE 66%, TWELVE 85%). :05 reads O'FIVE (Adam:
    # "reads more logical", twelve oh-five, rhyming with O'CLOCK). No ticks, no index drawn.
    words_h = ['TWELVE', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'ELEVEN']
    words_m = ["O'CLOCK", "O'FIVE", 'TEN', 'FIFTEEN', 'TWENTY', 'TWENTY-FIVE', 'THIRTY', 'THIRTY-FIVE', 'FORTY', 'FORTY-FIVE', 'FIFTY', 'FIFTY-FIVE']
    disc_x = dict(zip(('minute', 'hour'), (d_[0] for d_ in discs)))
    for hd in P.get('hands') or []:
        if hd.get('id') not in ('hour_disc', 'minute_disc'): continue
        mine = 'hour' if hd['id'] == 'hour_disc' else 'minute'
        hd.update({'marks': 0, 'labels': words_h if mine == 'hour' else words_m, 'pointer': False,
                   'words': {'r0': 2.6, 'r1': DISC_R - 0.4, 'cap': 1.1, 'font': '"Orbitron"', 'weight': 500, 'spacing': 0.0},   # (r0: neighbours' inner ends keep 0.25)
                   'indicator': 0.0 if disc_x[mine] < 0 else math.pi})    # (read on the side facing the other disc)
        hd['role'] = (hd.get('role') or '').split(' Its face:')[0] + (' Its face: the %s in words along the radii (the AXIS discs), letters 1.1 tall, V-carved and filled; '
                      'read where the discs face each other.' % ('hours' if mine == 'hour' else 'minutes in fives'))
    P['blurb'] = ('The 1988 AMC Hemistitch H-88 "Spectrum" case around Beta 2 · layered, from Adam\'s Meshy model, render, stack sketch and edits. '
                  f'Three parts: a faceplate ({W:.1f} x {H:.1f} mm octagon, its front relief at half the model\'s depth, every drop a 45° chamfer, heavy exterior chamfers to a raised deck), '
                  'a case middle (a ring round the movement carrying the four lugs, with a back bevel for the wrist) and a back plate, plus a 1 mm acrylic crystal in the window\'s shape '
                  'and a 1/16" dial plate with the discs turning in its apertures. Beta 2, its stem and crown drop into the ring from the back; six screws come up through the back plate '
                  f'and the ring into the faceplate. Spring bars at the lower third of the height; {z_top - z_frame0:.2f} mm from the back to the deck.')
    # ---- engravings (Adam, 2026-11-26: "BSPK can be larger and the name can be smaller... fit them wherever fits well"; the literary
    # HEMISTICH, "the correct word"; his logo on the back "like 60% coverage"): V-carved and filled white. On the dial plate's face, where
    # it shows between the discs, both in Orbitron like the discs: BSPK above, HEMISTICH '88 below (Adam: "50% smaller... if not whatever
    # the air can do"): BSPK 0.75 tall (half), the name 0.7 (the floor for a fine engraving V-bit; half would be 0.55), narrowed only if
    # they'd come within about 0.6 of the disc openings (maxw: the width there). The discs stay 1.1. On the back plate's wrist side: his shield logo, 60% of its height.
    bk_h = back_outline.bounds[3] - back_outline.bounds[1]
    P['decor'] = {**(P.get('decor') or {}), 'engrave': {
        'D11': {'face': 'top', 'z': round(z_dial1, 4), 'items': [
            {'kind': 'text', 'text': 'BSPK', 'at': [0.0, 8.4], 'cap': 0.75, 'font': '"Orbitron"', 'weight': 700, 'maxw': 6.9},
            {'kind': 'text', 'text': "HEMISTICH '88", 'at': [0.0, -8.6], 'cap': 0.7, 'font': '"Orbitron"', 'weight': 500, 'maxw': 8.4},
            # the caesura (Adam, P10: "a little hyphen or dash here... its where the point of 'hemistich' combines the time"): an en dash
            # at the reading point, between the hour's half-line and the minute's ("TWELVE – O'FIVE"). The dial plate shows only 1.2 wide
            # there (the disc openings come within 0.6 of the centre), so it's 0.9 long at most.
            {'kind': 'text', 'text': '\u2013', 'at': [0.0, 0.0], 'cap': 1.1, 'font': '"Orbitron"', 'weight': 500, 'maxw': 0.9}]},
        'D13': {'face': 'bottom', 'items': [
            {'kind': 'image', 'src': 'projects/assets/bspk-logo.png', 'at': [0.0, 0.0], 'w': round(0.6 * bk_h / 0.9773, 3), 'h': round(0.6 * bk_h, 3)}]}}}
    P['source'] = list(P.get('source') or []) + ['H-88 case: Claude, 2026-11-25, traced from Adam\'s Meshy model (1988 hemistitch) and render (H-88 "Spectrum"), his stack sketch '
                                                 '(face/body, calibre, lug plate, back plate) and notes (one-piece stepped crystal, dial plate, stem slit).']
    P['plate']['z'] = round(z_frame0 - 1.5, 4)
    P['groups']['drawn'] = 'Movement plates, stem and case'
    case_ids = ['D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'D16', 'D17']
    P['focus'] = [{'id': 'case', 'label': 'The case: faceplate, crystal, dial plate, case middle with its lugs, back plate', 'parts': case_ids + ['D6']},
                  {'id': 'inside', 'label': 'Inside the case: Beta 2 under the dial plate', 'parts': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D11', 'D12', 'D13', 'minute', 'hour', 'a1', 'a2', 'b', 'e']},
                  {'id': 'stack', 'label': 'Everything', 'parts': ['D%d' % i for i in range(1, 18)]}] + [f for f in P['focus'] if f['id'] in ('train',)]
    bev_top = z_frame0 + BEVEL_W['12/6'] * math.tan(math.radians(BEVEL_ANGLE))
    report = {'lugs': {'top': Z_SPLIT, 'eye': (round(eye_y, 3), round(eye_z, 3), EYE_R), 'lug_to_lug': round(2 * (eye_y + EYE_R), 2),
                       'width': LUG_X[1] - LUG_X[0], 'strap': 2 * LUG_X[0], 'profile': [tuple(round(v, 3) for v in q) for q in lug_side],
                       'screw bar: tube hole to the facets': round(EYE_R - SCREW_BAR['hole'] / 2, 2),
                       'screw bar: seat to the chamfer\'s foot (outer face)': round(EYE_R - LUG_CHAMFER['down'] - SCREW_BAR['seat'] / 2, 2), 'root to the case screws': round(min(abs(HORN_IN - abs(q[1])) for q in scr if abs(q[0]) + SCREW['clear'] / 2 > LUG_X[0]) - SCREW['clear'] / 2, 2),
                       'eye at the lower third of the height': round((eye_z - z_frame0) / (z_top - z_frame0), 3)},
              'z': {'back plate': (round(z_frame0, 4), round(z_back, 4)), 'case middle': (z_back, Z_SPLIT), 'faceplate': (Z_SPLIT, round(z_top, 4)), 'movement': (z_back, z_plates),
                    'discs': (7.75, round(z_disc1, 4)), 'dial plate': (round(z_dial0, 4), round(z_dial1, 4)), 'crystal': (round(z_cry0, 4), round(z_cry1, 4))},
              'stock': {'faceplate': round(T_face, 3), 'case middle': round(T_mid, 3), 'back plate': TT},
              'back bevel': {'top (12/6, 3/9)': round(bev_top, 3), 'top (corners)': round(z_frame0 + BEVEL_W['corner'] * math.tan(math.radians(BEVEL_ANGLE)), 3),
                             'ring walls at its bottom (12/6, corner, 3/9)': (round(H / 2 - bev_w(90, False) - (HY + CLR), 2),
                                                                             round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords) - bev_w(45, False), 2),
                                                                             round(W / 2 - bev_w(0, False) - (HX + CLR), 2)),
                             'stem slit top vs the split': round(zw + neck_r + 0.2, 3)},
              'screws': {'to the cavity': round(min(cav.exterior.distance(Point(q)) for q in scr) - SCREW['clear'] / 2, 2),
                         'to the 12/6 panels (tap hole)': round(min(pn['poly'].distance(Point(q)) for q in scr for pn in panels) - SCREW['tap'] / 2, 2),
                         'counterbore to the back plate edge (at its bottom)': round(min(inset_by(body, lambda d: bev_w(d)).exterior.distance(Point(q)) for q in scr) - SCREW['head'] / 2, 2),
                         'tap top to the deck surface over it': round(z_top - max(0.0, EXT_W['12/6'] - (H / 2 - max(abs(q[1]) for q in scr))) - (Z_SPLIT + SCREW['tap_depth']), 2),
                         'dowels to the stem slit': round(min(slit.distance(Point(q)) for q in DOWEL_XY) - DOWEL_D / 2, 2)},
              'front': {'top': round(z_top, 4), 'crystal (the window chamfer\'s foot)': round(z_ring, 4), 'lip over the crystal': (round(z_cry1, 4), round(z_cry1 + LIP, 4)), 'ridge': (round(z_dial1, 4), round(z_ridge, 4)),
                        'exterior chamfer feet (12/6, corners, 3/9)': tuple(round(z_top - EXT_W[k_] * ext_t(dg_), 3) for k_, dg_ in (('12/6', 90), ('corner', 45), ('3/9', 0))),
                        'side chamfer': {'angle': round(SIDE_ANGLE, 2), 'top edge x': round(W / 2 - SIDE_W, 2),
                                         'ridges meet the deck at y': round(min(abs(q[1]) for q in deck.exterior.coords if abs(q[0]) > W / 2 - SIDE_W - 1e-6), 3)},
                        'side chamfer over the dowel tops': round(z_top - ext_t(0) * (SIDE_W - (W / 2 - (DOWEL_XY[0][0] + DOWEL_D / 2))) - (Z_SPLIT + DOWEL_DEPTH), 2),
                        'deck bounds': [round(v, 2) for v in deck.bounds],
                        'flat between the window bezel and the exterior chamfer (12/6 stubs, corners, plaques)': (
                            round(H / 2 - EXT_W['12/6'] - (WIN_HH + CH_WIN), 2), round((W / 2 + H / 2 - CH) / math.sqrt(2) - EXT_W['corner'] - (WIN_HW + WIN_HH - WIN_CH + CH_WIN * math.sqrt(2)) / math.sqrt(2), 2),
                            round(H / 2 - EXT_W['12/6'] - (yb + CH_WIN), 2)),
                        'vents to the deck edge': round(min(deck.exterior.distance(stadium(-VENT_X, VENT_X, sy * y, VENT_W).buffer(CH_VENT)) for sy in (1, -1) for y in VENT_Y), 2),
                        'walls to the cavity at its top (12/6, corner, 3/9)': (
                            round(H / 2 - max(0, EXT_W['12/6'] - (z_top - z_dial1) / math.tan(math.radians(EXT_ANGLE))) - (HY + CLR), 2),
                            round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords) - max(0, EXT_W['corner'] - (z_top - z_dial1) / math.tan(math.radians(EXT_ANGLE))), 2),
                            round(W / 2 - max(0, EXT_W['3/9'] - (z_top - z_dial1) / ext_t(0)) - (HX + CLR), 2))},
              'panels': [{'face': pn['face'], 'floor z': round(pn['floor'], 3), 'depth at outer edge': pn['edge'], 'at inner edge': pn['inner'],
                          'bounds': [round(v, 2) for v in pn['poly'].bounds],
                          'floor over the cavity': round(pn['floor'] - z_plates, 2) if pn['poly'].intersects(cav) else None,
                          'to the dial pocket': round(pn['poly'].distance(dial_pocket), 2)} for pn in panels],
              'total': round(z_top - z_frame0, 3), 'disc_to_crystal': round(z_cry0 - z_disc1, 3), 'window': [round(v, 2) for v in window.bounds],
              'crown': {'x0': round(crown_x0, 3), 'r': crown_r, 'proud of the wall': CROWN['gap'], 'stem longer by': round(dx_c, 3), 'neck': 2 * neck_r,
                        'bottom above the case back': round(zw - crown_r - z_frame0, 3)}, 'screw positions': scr,
              'walls': {'side': round(W / 2 - (HX + CLR), 2), 'shoulder': round(H / 2 - (HY + CLR), 2),
                        'corner': round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords), 2)}}
    geo = dict(win_oct=win_oct, plaques=plaques, red=red, body=body, cav=cav, insert=insert, dial=dial_outline, panels=panels, window=window, slit=slit, scr=scr, discs=discs, side=side,
               back_outline=back_outline, eye=(eye_y, eye_z),
               cry_out=cry_out, cry_pocket=cry_pocket, front=front,
               z=dict(back=z_back, plates=z_plates, dial=(z_dial0, z_dial1), cry=(z_cry0, z_cry1), lip=(z_cry1, z_cry1 + LIP), ring=z_ring, top=z_top, frame0=z_frame0, disc1=z_disc1, split=Z_SPLIT),
               crown=(crown_x0, crown_r, zw))
    return S, report, geo
