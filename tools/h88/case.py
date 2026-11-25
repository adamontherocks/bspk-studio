# H-88 "Spectrum" (1988 AMC Hemistitch): a case for Beta 2 · layered, first trace (2026-11-25). From Adam's Meshy model and product render
# (octagon body, vented shoulders, retro screws front and back, a big crown at 3) and his stack sketch:
#   faceplate/body (one piece: the front and the walls; the movement drops in from the back) -> crystal (one piece, 1 mm acrylic, the
#   movement's shape, stepped so its edge sits under the faceplate's lip) -> dial plate (the retention plate: holds the crystal up against
#   the lip and the movement down, the discs turning in its two apertures 0.49 under the crystal) -> Beta 2 -> lug plate (a flat frame under
#   the body walls with the four lugs; it can't be 5-axis, so the lugs are a two-view part: plan outline cut through the side profile, on the
#   Air's 4th axis) -> back plate (in the lug plate's rabbet, under the movement). A slit in the body's 3 o'clock wall takes the stem, so the
#   movement, stem and crown drop in from the back as one, the crown into a well open to the back.
# Everything that goes in from the back must pass the cavity, so the only shoulder is the faceplate's lip: lip -> crystal -> dial plate ->
# movement -> back plate -> lug plate, clamped by four back screws threading up into the body; four front screws thread down into the same
# through-tapped holes (AXIS's two-direction screws) and hold the badges later.
# Lugs (Adam, 2026-11-25: "lugs going up, not drooping... an etched space in the side of the main case the lugs could slide into"): each lug
# rises from the lug plate into a slot in the body, open to the 12 or 6 face and keyed there, so the strap's pull goes into the body; outside
# it drops 45° onto its eye. The lug plate is a two-view part (plan outline x side profile, for the 4th axis); the sim shows its frame and four
# lug profiles. The screws sit on the octagon's chamfer corners, clear of the slots.
# Heights in Beta 2 · layered's frame: the movement from -3.6625 (back face) to 7.45 (plates), discs 7.75..9.3375.
import copy, math
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

TT, TS = 1.5875, 3.175
CLR = 0.2                       # movement to cavity, all round
DIAL_T = 2.38                   # 3/32" (or 1/8" faced from the back): the discs' tops 0.49 under the crystal
CRYSTAL_T, CRYSTAL_STEP = 1.0, 0.6     # 1 mm acrylic; its edge 0.4 thick under the lip
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
    z_cry0, z_cry1 = z_dial1, z_dial1 + CRYSTAL_T
    z_lip0 = z_cry0 + CRYSTAL_T - CRYSTAL_STEP
    z_top = z_cry1                                     # the faceplate's front, flush with the crystal
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
    window = win_oct.difference(unary_union(plaques)).buffer(-0.3, 32, join_style=1).buffer(0.3, 64, join_style=1)   # (its inside corners r 0.3 for the cutter)
    red = win_oct.buffer(-RED_IN, join_style=2).difference(win_oct.buffer(-(RED_IN + RED_W), join_style=2))
    boss = window.buffer(-0.1, 64)
    body = octagon()
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
    lug_side = [(SLOT_Y0, z_back), (SLOT_Y0, zr), (cc - zr, zr)] + [(eye_y + EYE_R * math.cos(math.radians(a)), eye_z + EYE_R * math.sin(math.radians(a))) for a in range(45, -91, -5)] \
               + [(H / 2, z_frame0), (H / 2, z_back)]
    slots = [box(min(sx * LX, sx * LX2) - 0.1, min(sy * (SLOT_Y0 - 0.1), sy * (H / 2 + 2.0)), max(sx * LX, sx * LX2) + 0.1, max(sy * (SLOT_Y0 - 0.1), sy * (H / 2 + 2.0)))
             for sx in (-1, 1) for sy in (-1, 1) for LX, LX2 in [LUG_X]]
    kn = [400]
    def newk(): kn[0] += 1; return f'K{kn[0]}'
    sks, parts = [], []
    def part(pid, name, outline, z0, t, cuts, mill='back'):
        k = newk(); sks.append(sketch(k, f'{name.split(" (")[0]} outline', 'z', round(z0, 5), poly_dots(outline)))
        parts.append({'id': pid, 'name': name, 'sketch': k, 'thickness': round(t, 5), 'grow': 'plus', 'mill': mill, 'minWall': 0.6, 'cuts': cuts})
    def pocket(name, poly, frm, depth, hid):
        if list(getattr(poly, 'interiors', [])): raise ValueError(f'{name}: a pocket with a hole (cut it as halves)')
        k = newk(); sks.append(sketch(k, name, 'z', 0.0, poly_dots(poly)))
        return {'id': f'h{hid}', 'kind': 'pocket', 'name': name, 'sketch': k, 'from': frm, 'depth': None if depth is None else round(depth, 4)}
    def hole(kind, name, at, d, frm, hid, depth=None, seat=None, fit=None):
        c = {'id': f'h{hid}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': frm, 'depth': depth}
        if seat: c['seat'] = seat
        if fit: c['fit'] = fit
        return c
    T_body = z_top - z_back
    bc = [pocket('Window (the crystal\'s raised centre shows through it)', window, 'back', None, 1),
          pocket('Cavity: the movement, dial plate and crystal go in from the back', cav, 'front', z_lip0 - z_back, 2),
          pocket('Crown well (open to the back: the crown drops in with the movement)', well, 'front', zw + crown_r + 0.3 - z_back, 3),
          pocket('Stem slit (open to the back)', slit, 'front', zw + neck_r + 0.2 - z_back, 4)]
    n = 5
    for sl in slots: bc.append(pocket('Lug slot (open to the back and the 12/6 face: the lug rises into it)', sl, 'front', RISE + 0.1, n)); n += 1
    vy = (18.3, 20.2, 22.1)
    for sy in (-1, 1):
        for y in vy: bc.append(pocket('Vent (the shoulders\' three slots)', stadium(-10.0, 10.0, sy * y, 1.0), 'back', 0.8, n)); n += 1
    for s in plq:
        bc.append(hole('clear', 'Plaque screw, M2: clear down to the lug riser (it threads into the riser and clamps the lug)', s, 2.3, 'back', n, depth=round(z_top - (z_back + RISE), 4), seat={'d': 4.4, 'depth': 0.9}, fit='m2_clear')); n += 1
    for s in side_scr:
        bc.append(hole('pilot', 'Side-rail screw, M1.6: tapped through (front screw down, back screw up)', s, 1.25, 'back', n)); n += 1
        bc.append(hole('clear', 'Side-rail screw head (M1.6, low)', s, 3.2, 'back', n, depth=0.5)); n += 1
    part('D9', 'Faceplate and body (black delrin, 5/8" faced to %.2f; milled from the front, then the back): the window and its lip, vents and front screws on the front; '
               'the movement\'s cavity, the crown well and the stem slit from the back' % T_body, body, z_back, T_body, bc)
    cry = [pocket('Step: the edge 0.4 thick, under the faceplate\'s lip', hp, 'back', CRYSTAL_STEP, 1 + i) for i, hp in enumerate(halves(insert.difference(boss)))]
    part('D10', 'Crystal (1 mm clear acrylic, one piece, the movement\'s shape): its raised centre fills the window, its stepped edge sits under the lip; glued in from the back', insert, z_cry0, CRYSTAL_T, cry)
    dc = [hole('clear', f'Disc aperture ({nm})', c, 19.6, 'back', i + 1) for i, (c, nm) in enumerate(zip(discs, ('minute', 'hour')))]
    dc += [pocket('Red line (engraved, filled red): just inside the window, round under the plaques', hp, 'back', RED_D, 7 + i) for i, hp in enumerate(halves(red))]
    for i, y in enumerate((7.8, -7.8)): dc.append(hole('clear', 'Dial foot (a screw head between the discs, as the render)', (0.0, y), 2.4, 'back', 10 + i, depth=0.3))
    ne_heads = [(5.05, 13.4), (10.55, 13.9)]
    for i, s in enumerate(ne_heads): dc.append(hole('clear', 'Relief over the NE plate\'s pan head', s, 4.6, 'front', 3 + i, depth=1.8))
    part('D11', 'Dial plate (3/32" black delrin): the retention plate. It holds the crystal up against the lip and the movement down; the discs turn in its apertures, '
                '0.49 under the crystal and 0.3 over the plates', insert, z_dial0, DIAL_T, dc)
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
    P['blurb'] = ('The 1988 AMC Hemistitch H-88 "Spectrum" case around Beta 2 · layered, first trace from Adam\'s Meshy model, render and stack sketch. '
                  f'Faceplate and body (one piece, {W:.0f} x {H:.0f} mm octagon), a one-piece 1 mm acrylic crystal stepped under the faceplate\'s lip, a 3/32" dial plate '
                  'that holds the crystal and the movement with the discs turning in its apertures, Beta 2, a lug plate (a frame with four lugs, a two-view part for the 4th axis) '
                  'and a back plate. The movement, stem and crown drop in from the back through a slit at 3. Four back screws thread up into the body; four front screws '
                  f'thread down into the same holes. {z_top - z_frame0:.2f} mm from the lug plate\'s back to the crystal.')
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
              'total': round(z_top - z_frame0, 3), 'disc_to_crystal': round(z_cry0 - z_disc1, 3), 'window': [round(v, 2) for v in window.bounds],
              'crown': {'x0': crown_x0, 'r': crown_r, 'below_back_face': round(z_back - (zw - crown_r), 3)}, 'screws': scr,
              'walls': {'side': round(W / 2 - (HX + CLR), 2), 'shoulder': round(H / 2 - (HY + CLR), 2),
                        'corner': round(min(body.exterior.distance(Point(q)) for q in cav.exterior.coords), 2),
                        'plaque screw to cavity': round(cav.exterior.distance(Point(plq[1])) - 1.15, 2),
                        'side screw to cavity / outside': (round(cav.exterior.distance(Point(side_scr[3])) - 0.625, 2), round(body.exterior.distance(Point(side_scr[3])) - 0.625, 2))}}
    geo = dict(win_oct=win_oct, plaques=plaques, red=red, body=body, cav=cav, insert=insert, window=window, boss=boss, well=well, slit=slit, frame=frame, scr=scr, discs=discs, side=side,
               z=dict(back=z_back, plates=z_plates, dial=(z_dial0, z_dial1), cry=(z_cry0, z_cry1), lip0=z_lip0, top=z_top, frame0=z_frame0, disc1=z_disc1), crown=(crown_x0, crown_r, zw))
    return S, report, geo
