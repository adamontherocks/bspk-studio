# H-88 "Spectrum" (1988 AMC Hemistitch): a case for Beta 2 · layered, first trace (2026-11-25). From Adam's Meshy model and product render
# (octagon body, vented shoulders, retro screws front and back, a big crown at 3) and his stack sketch:
#   faceplate/body (one piece: the front and the walls; the movement drops in from the back) -> crystal (one piece, 1 mm acrylic, the
#   window's shape + 1.0, stepped and glued up against a ledge round the window, its centre flush with the ring) -> dial plate (1/16", clamped
#   between the plates and the cavity's ceiling, the discs turning in its two apertures 0.3 under the crystal) -> Beta 2 -> lug plate (a flat frame under
#   the body walls with the four lugs; it can't be 5-axis, so the lugs are a two-view part: plan outline cut through the side profile, on the
#   Air's 4th axis) -> back plate (in the lug plate's rabbet, under the movement). A slit in the body's 3 o'clock wall takes the stem, so the
#   movement, stem and crown drop in from the back as one, the crown into a well open to the back.
# Everything goes in from the back: the crystal into its own pocket (the window + 1.1), glued against the ledge; then the dial plate up against
# the cavity's ceiling, the movement, the back plate and the lug plate, clamped by four back screws threading up into the body; four front
# screws thread down into the same through-tapped holes (AXIS's two-direction screws), and four more clamp the lugs into the body.
# Lugs (Adam, 2026-11-25: "lugs going up, not drooping... an etched space in the side of the main case the lugs could slide into"): each lug
# rises from the lug plate into a slot in the body, open to the 12 or 6 face and keyed there, so the strap's pull goes into the body; outside
# it drops 45° onto its eye. The lug plate is a two-view part (plan outline x side profile, for the 4th axis); the sim shows its frame and four
# lug profiles. The screws sit on the octagon's chamfer corners, clear of the slots.
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
SIDE_Y, CH_RAIL = 5.8, 1.0      # the side rails: the floor's half-length (the end chamfers stop 0.6 short of the side screws' heads); rim chamfer
CF_W, CF_DEPTH, CF_S = 3.0, 1.0, (8.6, 15.0)     # corner facets: the floor's width in from the octagon's chamfer edge, its depth, its extent along
                                                 # the edge; chamfered all round 45° by its depth (the top edge 1.0 further in and longer)
CF_SLOT = (1.5, 2.6, 9.8, 14.0) # the slot in each facet's floor (in from the edge, from-to; along the edge, from-to), down at the crystal's level
CH_SLOT, CH_VENT, CH_CB, CH_RIM = 0.3, 0.2, 0.2, 0.5   # chamfers: the facet slots' rims, the vents, the screw counterbores, the outer rim
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
# match, so the corner walls stay 3.0. Eight front screws where the render has them: four at the plaques' ends, over the lugs, threading
# down into the lug risers (they clamp the lugs into the body), 1.8 further out than the render so they keep a wall to Beta 2's cavity; and
# four on the side rails (M1.6, low heads), through-tapped, with four back screws coming up into the same holes to clamp the lug plate.
W, H, CH = 54.5, 49.2, 12.8     # the body (the render's)
LUG_X = (14.0, 17.5)            # lug inner and outer faces: the render's lugs, at the octagon's corners (a 28 mm strap)
RISE, SLOT_Y0 = 6.5, 17.5       # Adam (lugs up): each lug rises this far into a slot cut up into the body from its back, open to the 12/6 face
PLQ_SCR = (15.75, 19.1)         # the plaque screws (M2): over each lug riser's centre, into it
SIDE_SCR = (24.65, 9.0)         # the side-rail screws (M1.6, the render's spots)
EYE_R, EYE_OUT, HOLE = 2.5, 2.7, 1.2    # the lug's eye (spring bar boss) just outside the body: radius, its centre this far out, bar hole

def rrect(w, h, r, c=(0.0, 0.0)): return box(c[0] - w / 2 + r, c[1] - h / 2 + r, c[0] + w / 2 - r, c[1] + h / 2 - r).buffer(r, 64)
def octagon():
    pts = [(W / 2 - CH, H / 2), (-(W / 2 - CH), H / 2), (-W / 2, H / 2 - CH), (-W / 2, -(H / 2 - CH)), (-(W / 2 - CH), -H / 2),
           (W / 2 - CH, -H / 2), (W / 2, -(H / 2 - CH)), (W / 2, H / 2 - CH)]
    return Polygon(pts).buffer(-1.0, 32, join_style=1).buffer(1.0, 64, join_style=1)     # (its corners r 1)
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
    z_frame0 = z_back - TT                             # the lug plate under the body walls
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
    # ---- the front's relief: the window chamfered down to the crystal; side rails; corner facets with their slots
    rails = [box(min(sx * (RIB_X[1] + CH_RAIL), sx * (W / 2 + 1.0)), -SIDE_Y, max(sx * (RIB_X[1] + CH_RAIL), sx * (W / 2 + 1.0)), SIDE_Y) for sx in (1, -1)]
    corners = []
    for sx in (1, -1):
        for sy in (1, -1):
            p1 = (sx * (W / 2 - CH), sy * H / 2); t = (sx / math.sqrt(2), -sy / math.sqrt(2)); nv = (-sx / math.sqrt(2), -sy / math.sqrt(2))
            def at(s_, m_, p1=p1, t=t, nv=nv): return (p1[0] + s_ * t[0] + m_ * nv[0], p1[1] + s_ * t[1] + m_ * nv[1])
            m0, m1, s0, s1 = CF_SLOT; wi = m1 - m0
            corners.append({'p1': p1, 't': t, 'n': nv,
                            'floor': Polygon([at(CF_S[0], -1.0), at(CF_S[1], -1.0), at(CF_S[1], CF_W), at(CF_S[0], CF_W)]),
                            'top': Polygon([at(CF_S[0] - CF_DEPTH, -1.0), at(CF_S[1] + CF_DEPTH, -1.0), at(CF_S[1] + CF_DEPTH, CF_W + CF_DEPTH), at(CF_S[0] - CF_DEPTH, CF_W + CF_DEPTH)]),
                            'slot': LineString([at(s0 + wi / 2, (m0 + m1) / 2), at(s1 - wi / 2, (m0 + m1) / 2)]).buffer(wi / 2, 32)})
    win_top = window.buffer(CH_WIN, 64, join_style=2)                                     # the window chamfer's top edge
    front = dict(rails=rails, corners=corners, win_top=win_top)
    discs = [(10.4, 0.0), (-10.4, 0.0)]
    # the crown sits outside the 3 o'clock wall in a well open to the back; the stem's neck passes the wall in a slit open to the back
    well = box(crown_x0 - 0.3, -(crown_r + 0.3), W / 2 + 2.0, crown_r + 0.3)
    slit = box(HX, -(neck_r + 0.2), crown_x0, neck_r + 0.2)
    # the screws: four through-tapped holes in the shoulders, back screws up into them, front screws down into them
    plq = [(sx * PLQ_SCR[0], sy * PLQ_SCR[1]) for sx in (-1, 1) for sy in (-1, 1)]
    side_scr = [(sx * SIDE_SCR[0], sy * SIDE_SCR[1]) for sx in (-1, 1) for sy in (-1, 1)]
    scr = plq + side_scr
    # ---- the lug plate: a frame under the body walls, a rabbet for the back plate, four lugs (their droop is the side profile, K below)
    frame = body
    # each lug's side profile (y out from the centre, z up): riser up the slot, 45° down onto the eye, the eye, back along the plate's bottom
    eye_y, eye_z = H / 2 + EYE_OUT, z_frame0 + EYE_R
    zr = z_back + RISE
    tp = (eye_y + EYE_R * math.cos(math.radians(45)), eye_z + EYE_R * math.sin(math.radians(45))); cc = tp[0] + tp[1]
    lug_side = [(SLOT_Y0, z_frame0), (SLOT_Y0, zr), (cc - zr, zr)] + [(eye_y + EYE_R * math.cos(math.radians(a)), eye_z + EYE_R * math.sin(math.radians(a))) for a in range(45, -91, -5)]
    # (down to the lug plate's back all along: at the octagon's corners the frame's edge is the chamfer, so the lug fills under its riser)
    slots = [box(min(sx * LX, sx * LX2) - 0.1, min(sy * (SLOT_Y0 - 0.1), sy * (H / 2 + 2.0)), max(sx * LX, sx * LX2) + 0.1, max(sy * (SLOT_Y0 - 0.1), sy * (H / 2 + 2.0)))
             for sx in (-1, 1) for sy in (-1, 1) for LX, LX2 in [LUG_X]]
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
    T_body = z_top - z_back
    hn = [0]
    def nid(): hn[0] += 1; return hn[0]
    ne_heads = [(5.05, 13.4), (10.55, 13.9)]
    z_head = z_plates + 1.8                            # the NE plate's pan heads stand 1.6 over the plates: clear them by 0.2
    bc = [pocket('Window: chamfered 45° from the flush top down to the crystal (whose raised centre fills it), plaques included', window, 'back', None, nid(), chamfer=CH_WIN),
          pocket('Cavity: the movement and dial plate go in from the back; its ceiling is the dial plate\'s shoulder', cav, 'front', z_dial1 - z_back, nid()),
          pocket('Crystal pocket (the window + 1.1): the crystal goes in from the back and is glued up against the ledge, 0.6 under the ring', cry_pocket, 'front', z_lip0 - z_back, nid()),
          pocket('Crown well (open to the back: the crown drops in with the movement)', well, 'front', zw + crown_r + 0.3 - z_back, nid()),
          pocket('Stem slit (open to the back)', slit, 'front', zw + neck_r + 0.2 - z_back, nid())]
    for s in ne_heads: bc.append(hole('clear', 'Relief over the NE plate\'s pan head (in the cavity\'s ceiling)', s, 4.6, 'front', nid(), depth=round(z_head - z_back, 4)))
    for sl in slots: bc.append(pocket('Lug slot (open to the back and the 12/6 face: the lug rises into it)', sl, 'front', RISE + 0.1, nid()))
    for rl in rails: bc.append(pocket('Side rail, down at the crystal\'s level (its rib side and ends chamfered)', rl, 'back', RELIEF, nid(), chamfer=CH_RAIL))
    for c in corners:
        bc.append(pocket('Corner facet: a floor along the octagon\'s chamfer edge, chamfered 45° all round', c['floor'], 'back', CF_DEPTH, nid(), chamfer=CF_DEPTH))
        bc.append(pocket('Corner facet slot (in the floor, down at the crystal\'s level)', c['slot'], 'back', RELIEF, nid(), chamfer=CH_SLOT))
    vy = (18.3, 20.2, 22.1)
    for sy in (-1, 1):
        for y in vy: bc.append(pocket('Vent (the shoulders\' three slots)', stadium(-10.0, 10.0, sy * y, 1.0), 'back', 1.0, nid(), chamfer=CH_VENT))
    for s in plq:
        bc.append(hole('clear', 'Plaque screw, M2x14 wafer head: clear down to the lug riser (it threads 5.1 into the riser and clamps the lug)', s, 2.3, 'back', nid(), depth=round(z_top - (z_back + RISE), 4), seat={'d': 4.4, 'depth': 0.9}, fit='m2_clear', chamfer=CH_CB))
    for s in side_scr:
        bc.append(hole('pilot', 'Side-rail screw, M1.6: drilled through, tapped 5 from each end (front screw down, back screw up)', s, 1.25, 'back', nid()))
        bc.append(hole('clear', 'Side-rail screw head (M1.6, low)', s, 3.2, 'back', nid(), depth=0.5, chamfer=CH_CB))
    part('D9', 'Faceplate and body (black delrin, 3/4" faced to %.2f; milled from the front, then the back): the window chamfered down to the crystal, the side rails, '
               'the corner facets, vents and front screws on the front, every rim chamfered 45°; the movement\'s cavity, the crystal\'s pocket and ledge, the crown well and the '
               'stem slit from the back' % T_body, body, z_back, T_body, bc, chamfer={'face': 'back', 'size': CH_RIM})
    cry = [pocket('Step: the edge 0.4 thick, glued up against the ledge', hp, 'back', CRYSTAL_STEP, 1 + i) for i, hp in enumerate(halves(cry_out.difference(boss)))]
    part('D10', 'Crystal (1 mm clear acrylic, the window\'s shape + 1.0): its raised centre fills the window flush with the ring, its stepped edge is glued up against the ledge from the back', cry_out, z_cry0, CRYSTAL_T, cry)
    dc = [hole('clear', f'Disc aperture ({nm})', c, 19.6, 'back', i + 1) for i, (c, nm) in enumerate(zip(discs, ('minute', 'hour')))]
    dc += [pocket('Red line (engraved, filled red): just inside the window, round under the plaques', hp, 'back', RED_D, 7 + i) for i, hp in enumerate(halves(red))]
    for i, y in enumerate((7.8, -7.8)): dc.append(hole('clear', 'Dial foot (a screw head between the discs, as the render)', (0.0, y), 2.4, 'back', 10 + i, depth=0.3))
    for i, s in enumerate(ne_heads): dc.append(hole('clear', 'Opening for the NE plate\'s pan head', s, 4.6, 'back', 3 + i))
    part('D11', 'Dial plate (1/16" black delrin): clamped between the plates and the cavity\'s ceiling; the discs turn in its apertures, '
                '0.3 under the crystal', insert, z_dial0, DIAL_T, dc)
    fc = [pocket('Opening under the movement', cav.buffer(-1.0, 64), 'back', None, 1),
          pocket('Rabbet for the back plate', cav, 'back', BACK_T, 2),
          pocket('Relief under the crown', well, 'back', 0.6, 3)]
    n = 4
    for s in side_scr: fc.append(hole('clear', 'Back screw, M1.6: up into the side rail\'s tapped hole (head in a counterbore from the wrist side)', s, 1.8, 'front', n, seat={'d': 3.2, 'depth': 0.9})); n += 1
    part('D12', 'Lug plate (black delrin, cut as one two-view part on the 4th axis: plan outline x side profile): its frame under the body walls, '
                'a rabbet for the back plate; its four lugs are D14-D17', frame, z_frame0, TT, fc)
    part('D13', 'Back plate (1/32" clear acrylic, a display back; or delrin): in the lug plate\'s rabbet, the movement sits on it', insert, z_back - BACK_T, BACK_T, [])
    # the four lugs (part of the lug plate): the side profile drawn on the lug's inner-x face plane, grown across its width
    side = lug_side
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        k = newk(); pts = [(sy * u, v) for u, v in side]
        if sy < 0: pts = pts[::-1]
        sks.append({'id': k, 'name': f'Lug {i + 1} side profile', 'plane': {'axis': 'x', 'offset': round(LUG_X[0] if sx > 0 else -LUG_X[1], 4)}, 'closed': True,
                    'points': [{'u': round(u, 4), 'v': round(v, 4), 'smooth': False} for u, v in pts]})
        parts.append({'id': f'D{14 + i}', 'name': f'Lug {i + 1} ({"3" if sx > 0 else "9"} o\'clock side, {"12" if sy > 0 else "6"} o\'clock end): part of the lug plate. It rises {RISE} into its slot in the body and drops 45° onto its eye',
                      'sketch': k, 'thickness': round(LUG_X[1] - LUG_X[0], 4), 'grow': 'plus', 'mill': 'back', 'minWall': 0.6,
                      'cuts': [{'id': 'h1', 'kind': 'clear', 'name': f'Spring bar hole Ø{HOLE}', 'at': [round(sy * eye_y, 4), round(eye_z, 4)], 'd': HOLE, 'from': 'back', 'depth': None}]})
    st['sketches'] = st['sketches'] + sks
    st['drawn'] = st['drawn'] + parts
    # ---- the project
    P.update({'id': 'h88-case', 'name': 'H-88 Spectrum · case', 'title': 'H-88 Spectrum: a case for Beta 2'})
    P['blurb'] = ('The 1988 AMC Hemistitch H-88 "Spectrum" case around Beta 2 · layered, traced from Adam\'s Meshy model, render and stack sketch. '
                  f'Faceplate and body (one piece, {W:.1f} x {H:.1f} mm octagon; its front relief at half the model\'s depth, every drop a 45° chamfer: the window falls from the flush top '
                  'to the crystal, side rails, corner facets with slots), a 1 mm acrylic crystal in the window\'s shape glued against a ledge, a 1/16" dial plate with the discs turning in its apertures, '
                  'Beta 2, a lug plate (a frame with four lugs, a two-view part for the 4th axis) '
                  'and a back plate. The movement, stem and crown drop in from the back through a slit at 3. Four back screws thread up into the body; four front screws '
                  f'thread down into the same holes. {z_top - z_frame0:.2f} mm from the lug plate\'s back to the faceplate\'s top.')
    P['source'] = list(P.get('source') or []) + ['H-88 case: Claude, 2026-11-25, traced from Adam\'s Meshy model (1988 hemistitch) and render (H-88 "Spectrum"), his stack sketch '
                                                 '(face/body, calibre, lug plate, back plate) and notes (one-piece stepped crystal, dial plate, stem slit).']
    P['plate']['z'] = round(z_frame0 - 1.5, 4)
    P['groups']['drawn'] = 'Movement plates, stem and case'
    case_ids = ['D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'D16', 'D17']
    P['focus'] = [{'id': 'case', 'label': 'The case: faceplate and body, crystal, dial plate, lug plate, back plate', 'parts': case_ids + ['D6']},
                  {'id': 'inside', 'label': 'Inside the case: Beta 2 under the dial plate', 'parts': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D11', 'D12', 'D13', 'minute', 'hour', 'a1', 'a2', 'b', 'e']},
                  {'id': 'stack', 'label': 'Everything', 'parts': ['D%d' % i for i in range(1, 18)]}] + [f for f in P['focus'] if f['id'] in ('train',)]
    report = {'lugs': {'riser_top': round(zr, 4), 'eye': (round(eye_y, 3), round(eye_z, 3), EYE_R), 'lug_to_lug': round(2 * (eye_y + EYE_R), 2)},
              'z': {'lug plate': (round(z_frame0, 4), round(z_back, 4)), 'back plate': (round(z_back - BACK_T, 4), round(z_back, 4)), 'movement': (z_back, z_plates),
                    'discs': (7.75, round(z_disc1, 4)), 'dial plate': (round(z_dial0, 4), round(z_dial1, 4)), 'crystal': (round(z_cry0, 4), round(z_cry1, 4)),
                    'body': (z_back, round(z_top, 4))},
              'front': {'top': round(z_top, 4), 'crystal (the window chamfer\'s foot, the rails\' floor)': round(z_ring, 4), 'facet floor': round(z_top - CF_DEPTH, 4),
                        'ledge': (round(z_lip0, 4), round(z_ring, 4)),
                        'window chamfer top to facet top (flush band)': round(min(win_top.distance(c['top']) for c in corners), 2),
                        'facet top to plaque / side screw head': (round(min(c['top'].distance(Point(q)) for c in corners for q in plq) - 2.2, 2),
                                                                  round(min(c['top'].distance(Point(q)) for c in corners for q in side_scr) - 1.6, 2)),
                        'rail chamfer top to side screw head': round(min(r.buffer(CH_RAIL, join_style=2).distance(Point(q)) for r in rails for q in side_scr) - 1.6, 2),
                        'rib (flush) width': round(RIB_X[1] - RIB_X[0], 2), 'window chamfer top to plaque screw head': round(min(win_top.distance(Point(q)) for q in plq) - 2.2, 2),
                        'vent webs at the top': round(1.9 - 1.0 - 2 * CH_VENT, 2),
                        'NE head relief to crystal pocket': round(min(cry_pocket.distance(Point(q)) for q in ne_heads) - 2.3, 2)},
              'total': round(z_top - z_frame0, 3), 'disc_to_crystal': round(z_cry0 - z_disc1, 3), 'window': [round(v, 2) for v in window.bounds],
              'crown': {'x0': crown_x0, 'r': crown_r, 'below_back_face': round(z_back - (zw - crown_r), 3)}, 'screws': scr,
              'walls': {'side': round(W / 2 - (HX + CLR), 2), 'shoulder': round(H / 2 - (HY + CLR), 2),
                        'corner': round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords), 2),
                        'plaque screw to cavity': round(cav.exterior.distance(Point(plq[1])) - 1.15, 2),
                        'side screw to cavity / outside': (round(cav.exterior.distance(Point(side_scr[3])) - 0.625, 2), round(body.exterior.distance(Point(side_scr[3])) - 0.625, 2))}}
    geo = dict(win_oct=win_oct, plaques=plaques, red=red, body=body, cav=cav, insert=insert, window=window, boss=boss, well=well, slit=slit, frame=frame, scr=scr, discs=discs, side=side,
               cry_out=cry_out, cry_pocket=cry_pocket, front=front, ne_heads=ne_heads,
               z=dict(back=z_back, plates=z_plates, dial=(z_dial0, z_dial1), cry=(z_cry0, z_cry1), lip0=z_lip0, ring=z_ring, top=z_top, frame0=z_frame0, disc1=z_disc1, head=z_head),
               crown=(crown_x0, crown_r, zw))
    return S, report, geo
