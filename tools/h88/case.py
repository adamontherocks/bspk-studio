# H-88 "Spectrum" (1988 AMC Hemistitch): a case for Beta 2 · layered, first trace (2026-11-25). From Adam's Meshy model and product render
# (octagon body, vented shoulders, a big crown at 3), his stack sketch and his edits in the sim. Three parts and the glass (2026-11-25):
#   faceplate (the front, the top chamfers, the window, the top of the cavity) -> crystal (one piece, 1 mm acrylic, the window's shape + 1.0,
#   stepped and glued up against a ledge round the window, its centre flush with the window chamfer's foot) -> dial plate (1/16", clamped
#   between the plates and the cavity's ceiling, the discs turning in its two apertures 0.3 under the crystal) -> Beta 2 -> case middle (a
#   ring round the movement carrying the four lugs, the back bevel, the crown's well and the stem's slit) -> back plate (under it all).
# Everything goes in from the back: the crystal into its own pocket in the faceplate, glued against the ledge; the dial plate up against the
# cavity's ceiling; the faceplate onto the case middle on two dowels; Beta 2 with its stem and crown down into the ring (the stem through a
# slit open to the back, the crown into a well through the 3 o'clock wall); the back plate under it; six M2 screws up through the back
# plate and the ring into the faceplate. No screw heads on the front: the exterior chamfers took the render's front screws' seats.
# Heights in Beta 2 · layered's frame: the movement from -3.6625 (back face) to 7.45 (plates), discs 7.75..9.3375.
import copy, math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

TT, TS = 1.5875, 3.175
CLR = 0.2                       # movement to cavity, all round
DIAL_T = 1.5875                 # 1/16": with the crystal glued into the faceplate, the dial only frames the discs (they ride 0.3 over it)
DISC_TO_CRYSTAL = 0.3           # the discs' tops to the crystal's underside
CRY_OUT, CRY_POCKET = 1.0, 1.1  # the crystal: the window's outline + 1.0 (Adam: cut to the viewing area, glued against a ledge); its pocket + 0.1
# The front's relief (Adam: "plaques are flush. chamfers descend from there... keep the chamfers close to the model", then, of the first
# half-depth pass: "whats on the screen is ledges... this model requires chamfers... build geometry to the most reasonable chamferable
# areas"). Levels from the Meshy model's height map at half its depth; every drop from the flush top is a 45° chamfer (the sim's
# cut.chamfer, cut with a 90° chamfer mill or V-bit), sized to the room each one has:
#   - the window: falls the whole RELIEF from the flush top (plaques, shoulders, ribs) to the crystal on a 45° chamfer, plaques included
#     (a 1/4" or 6 mm 90° chamfer mill: a 1/8" one reaches about 1.4);
#   - the side rails: RELIEF deep, their rib side and ends chamfered CH_RAIL, the rest of the wall straight;
#   - the corner facets: a floor CF_DEPTH down along each of the octagon's chamfer edges, chamfered all round by its depth, with a slot in
#     the floor down at the crystal's level;
#   - the vents, counterbores and outer rim: small chamfers (CH_VENT, CH_CB, CH_RIM).
RELIEF = 2.0                    # flush top to the crystal: the window's chamfer, and the side rails' depth
CH_WIN = RELIEF                 # the window's chamfer: 45° all the way down to the crystal
RIB_X = (RELIEF + 21.7, RELIEF + 22.7)            # the side rib, flush: from the window chamfer's top edge, 1.0 wide
SIDE_Y, CH_RAIL = 4.0, 1.0      # the side rails: the floor's half-length (inside the sides' flat top, clear of the corner chamfers); rim chamfer
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
EXT_ANGLE = 45.0
EXT_W = {'12/6': 6.0, 'corner': 4.8, '3/9': 0.5}
EXT_WIDTHS = [[0, EXT_W['3/9']], [45, EXT_W['corner']], [90, EXT_W['12/6']], [135, EXT_W['corner']], [180, EXT_W['3/9']], [225, EXT_W['corner']],
              [270, EXT_W['12/6']], [315, EXT_W['corner']]]   # (facing direction in degrees, 0 = 3 o'clock, 90 = 12) -> width
VENT_Y, VENT_W, VENT_X = (13.8, 15.4, 17.0), 0.8, 9.0   # the vents on the deck behind each plaque: rows, width, half-length
CRYSTAL_T, CRYSTAL_STEP = 1.0, 0.6     # 1 mm acrylic; its edge 0.4 thick, glued up against the ledge
LIP = 1.1                       # (the first trace's lip; the window is now the render's octagon, below)
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
LUG_X = (11.0, 15.0)            # lug inner and outer faces: a 22 mm strap (Adam: "that needs to be a normal number like 20-22mm"; the render's lugs
                                #  sat out at the octagon's corners, 28 apart), so the lugs sit under the 12 and 6 faces; 4.0 thick
RISE, SLOT_Y0 = 6.5, 17.5       # Adam (lugs up): each lug rises this far into a slot cut up into the body from its back, open to the 12/6 face
PLQ_SCR = (16.0, 19.6)          # the plaque screws (M2, from the back): up through each lug riser's centre into the body above its slot
SIDE_SCR = (24.65, 9.0)         # the side-rail screws (M1.6, the render's spots)
EYE_R, EYE_OUT, HOLE = 2.5, 2.7, 1.2    # the lug's eye (spring bar boss) just outside the body: radius, its centre this far out, bar hole
# The case in three (Adam, 2026-11-25: "break the main case into two parts. the upper face plate, then... a lower plate that just sits
# there as separation... could the lug and back plate now be married?", and the lugs "more central... the lug holes will sit at the lower
# 1/3 line", their tops where the top chamfer starts "or a few mm below"):
#   - faceplate (D9), from the split up: the front, the top chamfers, the window and crystal, the cavity's top. 5/16" sheet, one flip.
#   - case middle (D12), from the movement's back face up to the split: a ring round Beta 2 with the four lugs (D14-D17, its horns), the
#     back bevel, the crown's well and the stem's slit. 3/8" sheet, cut flat from its back; then the lugs' side profiles and spring bar
#     holes on the Air's 4th axis (indexed to +-90°, the case's 12-6 line along the rotary axis, screwed to a fixture through its own
#     screw holes).
#   - back plate (D13): one 1/16" plate under it all (delrin, or clear acrylic as a display back), its edge carrying the bevel on. Six
#     M2 screws come up through it and the ring into the faceplate; two dowels line the faceplate and ring up.
Z_SPLIT = 5.0                   # faceplate / case middle: the lugs' tops, 1.64 under the top chamfer's foot; the crown's well tops out at 4.97
BEVEL_ANGLE = 67.5              # the back bevel (Adam's 9 o'clock edit): 22.5° off vertical, a 45° V-bit along each face
BEVEL_W = {'12/6': 2.8, 'corner': 1.2, '3/9': 2.8}   # its width at the back plate's bottom (the corner walls are 3.05)
SCREW_XY = [(x, sy * 19.0) for x in (-12.0, 0.0, 12.0) for sy in (1, -1)]   # the six M2 screws: in the 12 and 6 walls
DOWEL_XY, DOWEL_D, DOWEL_DEPTH = [(25.1, -7.0), (-25.1, 7.0)], 1.5, 3.0     # faceplate to case middle (clear of the crown's well)
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
    HX, HY = 22.75, 16.2
    z_back, z_plates, z_disc1 = -3.6625, 7.45, 7.75 + TT
    stem = next(d for d in st['drawn'] if d['id'] == 'D6'); kst = next(k for k in st['sketches'] if k['id'] == stem['sketch'])
    zw = stem['turn']['v']; prof = [(p['u'], p['v']) for p in kst['points']]
    crown_x0 = min(u for u, v in prof if v > 2.0 and u > 20); crown_r = max(v for u, v in prof) - zw; neck_r = 0.9
    # ---- heights
    z_dial0, z_dial1 = z_plates, z_plates + DIAL_T
    z_cry0 = z_disc1 + DISC_TO_CRYSTAL; z_cry1 = z_cry0 + CRYSTAL_T
    z_lip0 = z_cry0 + CRYSTAL_T - CRYSTAL_STEP          # the ledge the crystal's edge is glued against
    z_ring = z_cry1                                    # the inner ring and side rails: flush with the crystal
    z_top = z_ring + RELIEF                            # the flush top: shoulders, pads, ribs
    z_frame0 = z_back - TT                             # the back plate's bottom (the case's back)
    # ---- outlines
    main = next(d for d in st['drawn'] if d['id'] == 'D1'); kmain = next(k for k in st['sketches'] if k['id'] == main['sketch'])
    mov = Polygon([(p['u'], p['v']) for p in kmain['points']]).buffer(0)          # Beta 2's outline (its corners chamfered 4.5, as the case)
    cav = mov.buffer(CLR, 64, join_style=1)                                          # the movement + 0.2: everything from the back passes it
    insert = mov.buffer(CLR - 0.1, 64, join_style=1)                                 # crystal, dial plate, back plate: 0.1 inside it
    def oct_(hw, hh, ch): return Polygon([(hw - ch, hh), (-(hw - ch), hh), (-hw, hh - ch), (-hw, -(hh - ch)), (-(hw - ch), -hh), (hw - ch, -hh), (hw, -(hh - ch)), (hw, hh - ch)])
    win_oct = oct_(WIN_HW, WIN_HH, WIN_CH)
    yb = WIN_HH - PLQ_BITE
    plaques = [Polygon([(-PLQ_HW, sy * yb), (PLQ_HW, sy * yb), (PLQ_HW + 3.0, sy * (yb + 3.0)), (-PLQ_HW - 3.0, sy * (yb + 3.0))]) for sy in (1, -1)]
    window = win_oct.difference(unary_union(plaques))   # (sharp: its chamfer's corners are crisp mitres; the end mill's radius in its 135° corners is 0.02 off)
    red = win_oct.buffer(-RED_IN, join_style=2).difference(win_oct.buffer(-(RED_IN + RED_W), join_style=2))
    boss = window.buffer(-0.1, 64)
    cry_out = window.buffer(CRY_OUT, 64, join_style=1).buffer(0.5, 64).buffer(-0.5, 64)   # the crystal: the window + 1.0 (its inside corners r 0.5, as cut)
    cry_pocket = window.buffer(CRY_POCKET, 64, join_style=1)                               # its pocket, up from the back to the ledge
    body = octagon()
    # ---- the front's relief: the window chamfered down to the crystal; side rails; the deck the exterior chamfers leave
    rails = [box(min(sx * (RIB_X[1] + CH_RAIL), sx * (W / 2 + 1.0)), -SIDE_Y, max(sx * (RIB_X[1] + CH_RAIL), sx * (W / 2 + 1.0)), SIDE_Y) for sx in (1, -1)]
    win_top = window.buffer(CH_WIN, 64, join_style=2)                                     # the window chamfer's top edge
    def ext_w(deg):
        t = sorted(EXT_WIDTHS); a = deg % 360
        for (d0, w0), (d1, w1) in zip(t, t[1:] + [[t[0][0] + 360, t[0][1]]]):
            if d0 <= a <= d1: return w0 + (w1 - w0) * (a - d0) / (d1 - d0)
        return t[0][1]
    def deck_at(depth):    # the exterior's section `depth` under the top: each face's half-plane moved in by what's left of its chamfer there
        cuts_ = []
        ring = list(body.exterior.coords)[:-1]
        if Polygon(ring).exterior.is_ccw is False: ring = ring[::-1]
        poly = body
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            L = math.hypot(x1 - x0, y1 - y0); nx, ny = (y1 - y0) / L, -(x1 - x0) / L          # outward normal (anticlockwise ring)
            w = max(0.0, ext_w(math.degrees(math.atan2(ny, nx))) - depth / math.tan(math.radians(EXT_ANGLE)))
            if w > 0: poly = poly.difference(Polygon([(x0 + nx * 50 - ny * 99, y0 + ny * 50 + nx * 99), (x0 + nx * 50 + ny * 99, y0 + ny * 50 - nx * 99),
                                                       (x0 - nx * w + ny * 99, y0 - ny * w - nx * 99), (x0 - nx * w - ny * 99, y0 - ny * w + nx * 99)]))
        return poly
    deck = deck_at(0.0)
    front = dict(rails=rails, win_top=win_top, deck=deck, deck_at=deck_at)
    discs = [(10.4, 0.0), (-10.4, 0.0)]
    # the crown sits outside the 3 o'clock wall in a well open to the back; the stem's neck passes the wall in a slit open to the back
    well = box(crown_x0 - 0.3, -(crown_r + 0.3), W / 2 + 2.0, crown_r + 0.3)
    slit = box(HX, -(neck_r + 0.2), crown_x0, neck_r + 0.2)
    # ---- the case middle's lugs (horns): each one's side profile (y out from the centre, z up), drawn on its inner face's plane and grown
    # across its 4.0: flat on top at the split, 45° down onto its eye (the spring bar at the lower third of the case's height), round the
    # eye, flat underneath, its root running in under the octagon's corner into the ring's wall
    eye_y = H / 2 + EYE_OUT
    eye_z = z_frame0 + (z_top - z_frame0) / 3
    tp = (eye_y + EYE_R * math.cos(math.radians(45)), eye_z + EYE_R * math.sin(math.radians(45)))
    lug_side = [(HORN_IN, Z_SPLIT), (tp[0] + tp[1] - Z_SPLIT, Z_SPLIT)] + \
               [(eye_y + EYE_R * math.cos(math.radians(a)), eye_z + EYE_R * math.sin(math.radians(a))) for a in range(45, -91, -5)] + [(HORN_IN, eye_z - EYE_R)]
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
    def pocket(name, poly, frm, depth, hid, chamfer=None):
        if list(getattr(poly, 'interiors', [])): raise ValueError(f'{name}: a pocket with a hole (cut it as halves)')
        k = newk(); sks.append(sketch(k, name, 'z', 0.0, poly_dots(poly)))
        return {'id': f'h{hid}', 'kind': 'pocket', 'name': name, 'sketch': k, 'from': frm, 'depth': None if depth is None else round(depth, 4),
                **({'chamfer': chamfer} if chamfer else {})}
    def hole(kind, name, at, d, frm, hid, depth=None, seat=None, fit=None, chamfer=None):
        c = {'id': f'h{hid}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': frm, 'depth': depth}
        if seat: c['seat'] = seat
        if fit: c['fit'] = fit
        if chamfer: c['chamfer'] = chamfer
        return c
    T_face, T_mid = z_top - Z_SPLIT, Z_SPLIT - z_back
    hn = [0]
    def nid(): hn[0] += 1; return hn[0]
    ne_heads = [(5.05, 13.4), (10.55, 13.9)]
    z_head = z_plates + 1.8                            # the NE plate's pan heads stand 1.6 over the plates: clear them by 0.2
    # ---- D9 faceplate: from the split to the deck
    bc = [pocket('Window: chamfered 45° from the flush top down to the crystal (whose raised centre fills it), plaques included', window, 'back', None, nid(), chamfer=CH_WIN),
          pocket('Cavity: the top of Beta 2 and the dial plate; its ceiling is the dial plate\'s shoulder', cav, 'front', z_dial1 - Z_SPLIT, nid()),
          pocket('Crystal pocket (the window + 1.1): the crystal goes in from the back and is glued up against the ledge, 0.6 under the ring', cry_pocket, 'front', z_lip0 - Z_SPLIT, nid())]
    for s in ne_heads: bc.append(hole('clear', 'Relief over the NE plate\'s pan head (in the cavity\'s ceiling)', s, 4.6, 'front', nid(), depth=round(z_head - Z_SPLIT, 4)))
    for rl in rails: bc.append(pocket('Side rail, down at the crystal\'s level (its rib side and ends chamfered)', rl, 'back', RELIEF, nid(), chamfer=CH_RAIL))
    for sy in (-1, 1):
        for y in VENT_Y: bc.append(pocket('Vent (on the deck behind the plaque)', stadium(-VENT_X, VENT_X, sy * y, VENT_W), 'back', 1.0, nid(), chamfer=CH_VENT))
    for s in scr: bc.append(hole('pilot', 'Case screw, M2x14: tapped 5 up from the split (it comes up through the back plate and the case middle)', s, 1.6, 'front', nid(), depth=5.0, fit='m2_tap'))
    for s in DOWEL_XY: bc.append(hole('dowel', f'Dowel Ø{DOWEL_D} (lines the faceplate up on the case middle)', s, DOWEL_D, 'front', nid(), depth=DOWEL_DEPTH))
    part('D9', 'Faceplate (black delrin, 5/16" faced to %.2f; milled from the front, then the back): the walls fall in on 45° exterior chamfers (6.0 at 12 and 6, '
               '4.8 at the corners, a 0.5 break at 3 and 9) to the deck, the window chamfered down to the crystal, the side rails and vents; the cavity\'s top, the '
               'crystal\'s pocket and ledge, the screws\' tapped holes and the dowel holes from the back' % T_face, body, Z_SPLIT, T_face, bc,
         chamfer={'face': 'back', 'size': EXT_W['3/9'], 'angle': EXT_ANGLE, 'widths': EXT_WIDTHS})
    cry = [pocket('Step: the edge 0.4 thick, glued up against the ledge', hp, 'back', CRYSTAL_STEP, 1 + i) for i, hp in enumerate(halves(cry_out.difference(boss)))]
    part('D10', 'Crystal (1 mm clear acrylic, the window\'s shape + 1.0): its raised centre fills the window flush with the ring, its stepped edge is glued up against the ledge from the back', cry_out, z_cry0, CRYSTAL_T, cry)
    dc = [hole('clear', f'Disc aperture ({nm})', c, 19.6, 'back', i + 1) for i, (c, nm) in enumerate(zip(discs, ('minute', 'hour')))]
    dc += [pocket('Red line (engraved, filled red): just inside the window, round under the plaques', hp, 'back', RED_D, 7 + i) for i, hp in enumerate(halves(red))]
    for i, y in enumerate((7.8, -7.8)): dc.append(hole('clear', 'Dial foot (a screw head between the discs, as the render)', (0.0, y), 2.4, 'back', 10 + i, depth=0.3))
    for i, s in enumerate(ne_heads): dc.append(hole('clear', 'Opening for the NE plate\'s pan head', s, 4.6, 'back', 3 + i))
    part('D11', 'Dial plate (1/16" black delrin): clamped between the plates and the cavity\'s ceiling; the discs turn in its apertures, '
                '0.3 under the crystal', insert, z_dial0, DIAL_T, dc)
    # ---- D12 case middle: from the movement's back face to the split
    hn[0] = 0
    mc = [pocket('Opening: Beta 2 drops in from the back', cav, 'front', None, nid()),
          pocket('Crown well (through: the crown drops in with the movement; the faceplate closes it)', well, 'front', None, nid()),
          pocket('Stem slit (open to the back)', slit, 'front', zw + neck_r + 0.2 - z_back, nid())]
    for s in scr: mc.append(hole('clear', 'Case screw, M2: clearance up through the case middle', s, 2.3, 'front', nid(), fit='m2_clear'))
    for s in DOWEL_XY: mc.append(hole('dowel', f'Dowel Ø{DOWEL_D}', s, DOWEL_D, 'back', nid(), depth=DOWEL_DEPTH))
    part('D12', 'Case middle (black delrin, 3/8" faced to %.2f): a ring round Beta 2 carrying the four lugs (D14-D17), cut flat from its back: the outline, the back '
                'bevel (%.1f° from the face, a 45° V-bit along each face), the opening, the crown\'s well and the stem\'s slit, the screw and dowel holes; then the lugs\' '
                'side profiles and spring bar holes on the 4th axis (indexed to +-90°, the 12-6 line along the rotary axis, screwed to a fixture through its own '
                'screw holes)' % (T_mid, BEVEL_ANGLE), body, z_back, T_mid, mc,
         chamfer={'face': 'front', 'size': round(bev_w(0, False), 4), 'angle': BEVEL_ANGLE, 'widths': ring_widths})
    # ---- D13 back plate: one plate under it all
    bk = [hole('clear', 'Case screw, M2x14 wafer head: up through the back plate (counterbored from the wrist side)', s, 2.3, 'front', i + 1, seat={'d': 4.4, 'depth': 0.9}, fit='m2_clear')
          for i, s in enumerate(scr)]
    bk.append(pocket('Relief under the crown (it dips %.2f under the movement\'s back face)' % (z_back - (zw - crown_r)), well.intersection(back_outline.buffer(1.0)), 'back', 0.4, len(bk) + 1))
    part('D13', 'Back plate (1/16" black delrin, or clear acrylic as a display back): under the case middle and Beta 2, its edge carrying the back bevel on; the six case '
                'screws come up through it', back_outline, z_frame0, TT, bk, chamfer={'face': 'front', 'size': round(bev_drop, 4), 'angle': BEVEL_ANGLE})
    # ---- D14-D17 the lugs: the case middle's horns (one piece with it), each drawn as its side profile, grown across its 4.0
    side = lug_side
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        k = newk(); pts = [(sy * u, v) for u, v in side]
        if sy < 0: pts = pts[::-1]
        sks.append({'id': k, 'name': f'Lug {i + 1} side profile', 'plane': {'axis': 'x', 'offset': round(LUG_X[0] if sx > 0 else -LUG_X[1], 4)}, 'closed': True,
                    'points': [{'u': round(u, 4), 'v': round(v, 4), 'smooth': False} for u, v in pts]})
        parts.append({'id': f'D{14 + i}', 'name': f'Lug {i + 1} ({"3" if sx > 0 else "9"} o\'clock side, {"12" if sy > 0 else "6"} o\'clock end): part of the case middle, '
                                                  f'flat on top at the split, 45° down onto its eye; its side profile and spring bar hole cut on the 4th axis',
                      'sketch': k, 'thickness': round(LUG_X[1] - LUG_X[0], 4), 'grow': 'plus', 'mill': 'back', 'minWall': 0.6,
                      'cuts': [{'id': 'h1', 'kind': 'clear', 'name': f'Spring bar hole Ø{HOLE} (drilled through from the outer face)', 'at': [round(sy * eye_y, 4), round(eye_z, 4)], 'd': HOLE, 'from': 'back', 'depth': None}]})
    st['sketches'] = st['sketches'] + sks
    st['drawn'] = st['drawn'] + parts
    # ---- the project
    P.update({'id': 'h88-case', 'name': 'H-88 Spectrum · case', 'title': 'H-88 Spectrum: a case for Beta 2'})
    P['blurb'] = ('The 1988 AMC Hemistitch H-88 "Spectrum" case around Beta 2 · layered, from Adam\'s Meshy model, render, stack sketch and edits. '
                  f'Three parts: a faceplate ({W:.1f} x {H:.1f} mm octagon, its front relief at half the model\'s depth, every drop a 45° chamfer, heavy exterior chamfers to a raised deck), '
                  'a case middle (a ring round the movement carrying the four lugs, with a back bevel for the wrist) and a back plate, plus a 1 mm acrylic crystal in the window\'s shape '
                  'and a 1/16" dial plate with the discs turning in its apertures. Beta 2, its stem and crown drop into the ring from the back; six screws come up through the back plate '
                  f'and the ring into the faceplate. Spring bars at the lower third of the height; {z_top - z_frame0:.2f} mm from the back to the deck.')
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
                       'eye at the lower third of the height': round((eye_z - z_frame0) / (z_top - z_frame0), 3)},
              'z': {'back plate': (round(z_frame0, 4), round(z_back, 4)), 'case middle': (z_back, Z_SPLIT), 'faceplate': (Z_SPLIT, round(z_top, 4)), 'movement': (z_back, z_plates),
                    'discs': (7.75, round(z_disc1, 4)), 'dial plate': (round(z_dial0, 4), round(z_dial1, 4)), 'crystal': (round(z_cry0, 4), round(z_cry1, 4))},
              'stock': {'faceplate': round(T_face, 3), 'case middle': round(T_mid, 3), 'back plate': TT},
              'back bevel': {'top (12/6, 3/9)': round(bev_top, 3), 'top (corners)': round(z_frame0 + BEVEL_W['corner'] * math.tan(math.radians(BEVEL_ANGLE)), 3),
                             'ring walls at its bottom (12/6, corner, 3/9)': (round(H / 2 - bev_w(90, False) - (HY + CLR), 2),
                                                                             round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords) - bev_w(45, False), 2),
                                                                             round(W / 2 - bev_w(0, False) - (HX + CLR), 2)),
                             'crown well top vs the split': round(zw + crown_r + 0.3, 3)},
              'screws': {'to the cavity': round(min(cav.exterior.distance(Point(q)) for q in scr) - 1.15, 2),
                         'counterbore to the back plate edge (at its bottom)': round(min(inset_by(body, lambda d: bev_w(d)).exterior.distance(Point(q)) for q in scr) - 2.2, 2),
                         'tap top to the deck surface over it': round(z_top - max(0.0, EXT_W['12/6'] - (H / 2 - 19.0)) - (Z_SPLIT + 5.0), 2),
                         'dowels to the crown well': round(min(well.distance(Point(q)) for q in DOWEL_XY) - DOWEL_D / 2, 2)},
              'front': {'top': round(z_top, 4), 'crystal (the window chamfer\'s foot, the rails\' floor)': round(z_ring, 4), 'ledge': (round(z_lip0, 4), round(z_ring, 4)),
                        'exterior chamfer feet (12/6, corners, 3/9)': tuple(round(z_top - w * math.tan(math.radians(EXT_ANGLE)), 3) for w in (EXT_W['12/6'], EXT_W['corner'], EXT_W['3/9'])),
                        'deck bounds': [round(v, 2) for v in deck.bounds],
                        'flat between the window bezel and the exterior chamfer (12/6 stubs, corners, plaques)': (
                            round(H / 2 - EXT_W['12/6'] - (WIN_HH + CH_WIN), 2), round((W / 2 + H / 2 - CH) / math.sqrt(2) - EXT_W['corner'] - (WIN_HW + WIN_HH - WIN_CH + CH_WIN * math.sqrt(2)) / math.sqrt(2), 2),
                            round(H / 2 - EXT_W['12/6'] - (yb + CH_WIN), 2)),
                        'vents to the deck edge': round(min(deck.exterior.distance(stadium(-VENT_X, VENT_X, sy * y, VENT_W).buffer(CH_VENT)) for sy in (1, -1) for y in VENT_Y), 2),
                        'walls to the cavity at its top (12/6, corner, 3/9)': (
                            round(H / 2 - max(0, EXT_W['12/6'] - (z_top - z_dial1) / math.tan(math.radians(EXT_ANGLE))) - (HY + CLR), 2),
                            round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords) - max(0, EXT_W['corner'] - (z_top - z_dial1) / math.tan(math.radians(EXT_ANGLE))), 2),
                            round(W / 2 - max(0, EXT_W['3/9'] - (z_top - z_dial1)) - (HX + CLR), 2)),
                        'rails inside the deck': deck.buffer(1e-6).contains(unary_union([r.buffer(CH_RAIL, join_style=2) for r in rails]).intersection(body.buffer(-EXT_W['3/9'] - 1e-3))),
                        'NE head relief to crystal pocket': round(min(cry_pocket.distance(Point(q)) for q in ne_heads) - 2.3, 2)},
              'total': round(z_top - z_frame0, 3), 'disc_to_crystal': round(z_cry0 - z_disc1, 3), 'window': [round(v, 2) for v in window.bounds],
              'crown': {'x0': crown_x0, 'r': crown_r, 'below_back_face': round(z_back - (zw - crown_r), 3)}, 'screw positions': scr,
              'walls': {'side': round(W / 2 - (HX + CLR), 2), 'shoulder': round(H / 2 - (HY + CLR), 2),
                        'corner': round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords), 2)}}
    geo = dict(win_oct=win_oct, plaques=plaques, red=red, body=body, cav=cav, insert=insert, window=window, boss=boss, well=well, slit=slit, scr=scr, discs=discs, side=side,
               back_outline=back_outline, eye=(eye_y, eye_z),
               cry_out=cry_out, cry_pocket=cry_pocket, front=front, ne_heads=ne_heads,
               z=dict(back=z_back, plates=z_plates, dial=(z_dial0, z_dial1), cry=(z_cry0, z_cry1), lip0=z_lip0, ring=z_ring, top=z_top, frame0=z_frame0, disc1=z_disc1, head=z_head, split=Z_SPLIT),
               crown=(crown_x0, crown_r, zw))
    return S, report, geo
