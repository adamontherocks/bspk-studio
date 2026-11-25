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
# Heights in Beta 2 · layered's frame: the movement from -3.6625 (back face) to 7.45 (plates), discs 7.75..9.3375.
import copy, math
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

TT, TS = 1.5875, 3.175
CLR = 0.2                       # movement to cavity, all round
DIAL_T = 2.38                   # 3/32" (or 1/8" faced from the back): the discs' tops 0.49 under the crystal
CRYSTAL_T, CRYSTAL_STEP = 1.0, 0.6     # 1 mm acrylic; its edge 0.4 thick under the lip
LIP = 1.1                       # the faceplate's lip over the crystal's edge, all round
BACK_T = 0.8                    # back plate (1/32" acrylic: a display back, or delrin)
W, H, CH = 54.0, 48.0, 9.0      # the body: wider than tall (the render), its octagon's chamfers
LUG_X = (12.0, 15.5)            # lug inner and outer faces (a 24 mm strap)

def rrect(w, h, r, c=(0.0, 0.0)): return box(c[0] - w / 2 + r, c[1] - h / 2 + r, c[0] + w / 2 - r, c[1] + h / 2 - r).buffer(r, 64)
def octagon():
    pts = [(W / 2 - CH, H / 2), (-(W / 2 - CH), H / 2), (-W / 2, H / 2 - CH), (-W / 2, -(H / 2 - CH)), (-(W / 2 - CH), -H / 2),
           (W / 2 - CH, -H / 2), (W / 2, -(H / 2 - CH)), (W / 2, H / 2 - CH)]
    return Polygon(pts).buffer(-1.0, 32, join_style=1).buffer(1.0, 64, join_style=1)     # (its corners r 1)
def stadium(x0, x1, y, w): return box(x0 + w / 2, y - w / 2, x1 - w / 2, y + w / 2).buffer(w / 2, 32)

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
    cav = rrect(2 * HX + 2 * CLR, 2 * HY + 2 * CLR, 4.0 + CLR)          # the movement + 0.2: everything from the back passes it
    insert = rrect(2 * HX + 2 * CLR - 0.2, 2 * HY + 2 * CLR - 0.2, 4.0 + CLR - 0.1)   # crystal, dial plate, back plate: 0.1 inside it
    window = rrect(2 * HX + 2 * CLR - 2 * LIP, 2 * HY + 2 * CLR - 2 * LIP, 4.0 + CLR - LIP + 0.5)   # what shows: the crystal's raised centre
    boss = window.buffer(-0.1, 64)
    body = octagon()
    discs = [(10.4, 0.0), (-10.4, 0.0)]
    # the crown sits outside the 3 o'clock wall in a well open to the back; the stem's neck passes the wall in a slit open to the back
    well = box(crown_x0 - 0.3, -(crown_r + 0.3), W / 2 + 2.0, crown_r + 0.3)
    slit = box(HX, -(neck_r + 0.2), crown_x0, neck_r + 0.2)
    # the screws: four through-tapped holes in the shoulders, back screws up into them, front screws down into them
    scr = [(sx * 14.5, sy * 20.6) for sx in (-1, 1) for sy in (-1, 1)]
    # ---- the lug plate: a frame under the body walls, a rabbet for the back plate, four lugs (their droop is the side profile, K below)
    lug_len = 7.5
    lugs = [rrect(LUG_X[1] - LUG_X[0], lug_len + 3.0, 1.75, (sx * (LUG_X[0] + LUG_X[1]) / 2, sy * (H / 2 + lug_len / 2 - 1.5))) for sx in (-1, 1) for sy in (-1, 1)]
    frame = unary_union([body] + lugs).buffer(0)
    kn = [400]
    def newk(): kn[0] += 1; return f'K{kn[0]}'
    sks, parts = [], []
    def part(pid, name, outline, z0, t, cuts, mill='back'):
        k = newk(); sks.append(sketch(k, f'{name.split(" (")[0]} outline', 'z', round(z0, 5), poly_dots(outline)))
        parts.append({'id': pid, 'name': name, 'sketch': k, 'thickness': round(t, 5), 'grow': 'plus', 'mill': mill, 'minWall': 0.6, 'cuts': cuts})
    def pocket(name, poly, frm, depth, hid):
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
    vy = (18.3, 20.2, 22.1); n = 5
    for sy in (-1, 1):
        for y in vy: bc.append(pocket('Vent (the shoulders\' three slots)', stadium(-10.0, 10.0, sy * y, 1.0), 'back', 0.8, n)); n += 1
    for s in scr: bc.append(hole('pilot', 'M2 thread, through (back screw up, front screw down)', s, 1.6, 'back', n, fit='m2_tap')); n += 1
    for s in scr: bc.append(hole('clear', 'Front screw head: M2 wafer in a counterbore', s, 4.4, 'back', n, depth=0.9)); n += 1
    part('D9', 'Faceplate and body (black delrin, 5/8" faced to %.2f; milled from the front, then the back): the window and its lip, vents and front screws on the front; '
               'the movement\'s cavity, the crown well and the stem slit from the back' % T_body, body, z_back, T_body, bc)
    cry = [pocket('Step: the edge 0.4 thick, under the faceplate\'s lip', insert.difference(boss), 'back', CRYSTAL_STEP, 1)]
    part('D10', 'Crystal (1 mm clear acrylic, one piece, the movement\'s shape): its raised centre fills the window, its stepped edge sits under the lip; glued in from the back', insert, z_cry0, CRYSTAL_T, cry)
    dc = [hole('clear', f'Disc aperture ({nm})', c, 19.6, 'back', i + 1) for i, (c, nm) in enumerate(zip(discs, ('minute', 'hour')))]
    ne_heads = [(5.05, 13.4), (10.55, 13.9)]
    for i, s in enumerate(ne_heads): dc.append(hole('clear', 'Relief over the NE plate\'s pan head', s, 4.6, 'front', 3 + i, depth=1.8))
    part('D11', 'Dial plate (3/32" black delrin): the retention plate. It holds the crystal up against the lip and the movement down; the discs turn in its apertures, '
                '0.49 under the crystal and 0.3 over the plates', insert, z_dial0, DIAL_T, dc)
    fc = [pocket('Opening under the movement', cav.buffer(-1.0, 64), 'back', None, 1),
          pocket('Rabbet for the back plate', cav, 'back', BACK_T, 2),
          pocket('Relief under the crown', well, 'back', 0.6, 3)]
    n = 4
    for s in scr: fc.append(hole('clear', 'Back screw: M2 wafer head in a counterbore from the wrist side', s, 2.3, 'front', n, seat={'d': 4.4, 'depth': 0.9}, fit='m2_clear')); n += 1
    part('D12', 'Lug plate (black delrin): a frame under the body walls with the four lugs. Here flat; the lugs\' droop toward the wrist is the side profile '
                '(sketch "Lug side profile"): cut as a two-view part on the 4th axis', frame, z_frame0, TT, fc)
    part('D13', 'Back plate (1/32" clear acrylic, a display back; or delrin): in the lug plate\'s rabbet, the movement sits on it', insert, z_back - BACK_T, BACK_T, [])
    # the lugs' side profile (on the 3 o'clock lug's outer face): down from the frame to the spring bar, for Adam to shape
    yb, zf0, zf1 = H / 2 - 3.0, z_frame0, z_back
    side = [(yb, zf1), (H / 2, zf1), (H / 2 + 3.5, zf1 - 1.1), (H / 2 + 6.2, zf1 - 2.9), (H / 2 + 7.3, zf1 - 4.4), (H / 2 + 6.9, zf1 - 5.9),
            (H / 2 + 5.6, zf1 - 6.3), (H / 2 + 4.2, zf1 - 5.3), (H / 2 + 2.0, zf0 - 0.9), (H / 2, zf0), (yb, zf0)]
    sks.append({'id': newk(), 'name': 'Lug side profile (the lugs droop to the strap: the second view of the lug plate; spring bar at the round end)',
                'plane': {'axis': 'x', 'offset': LUG_X[1]}, 'closed': True, 'points': [{'u': round(u, 4), 'v': round(v, 4), 'smooth': 1 <= i <= 8} for i, (u, v) in enumerate(side)]})
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
    case_ids = ['D9', 'D10', 'D11', 'D12', 'D13']
    P['focus'] = [{'id': 'case', 'label': 'The case: faceplate and body, crystal, dial plate, lug plate, back plate', 'parts': case_ids + ['D6']},
                  {'id': 'inside', 'label': 'Inside the case: Beta 2 under the dial plate', 'parts': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D11', 'D12', 'D13', 'minute', 'hour', 'a1', 'a2', 'b', 'e']},
                  {'id': 'stack', 'label': 'Everything', 'parts': ['D%d' % i for i in range(1, 14)]}] + [f for f in P['focus'] if f['id'] in ('train',)]
    report = {'z': {'lug plate': (round(z_frame0, 4), round(z_back, 4)), 'back plate': (round(z_back - BACK_T, 4), round(z_back, 4)), 'movement': (z_back, z_plates),
                    'discs': (7.75, round(z_disc1, 4)), 'dial plate': (round(z_dial0, 4), round(z_dial1, 4)), 'crystal': (round(z_cry0, 4), round(z_cry1, 4)),
                    'body': (z_back, round(z_top, 4))},
              'total': round(z_top - z_frame0, 3), 'disc_to_crystal': round(z_cry0 - z_disc1, 3), 'window': [round(v, 2) for v in window.bounds],
              'crown': {'x0': crown_x0, 'r': crown_r, 'below_back_face': round(z_back - (zw - crown_r), 3)}, 'screws': scr,
              'walls': {'side': round(W / 2 - (HX + CLR), 2), 'shoulder': round(H / 2 - (HY + CLR), 2),
                        'corner': round(body.exterior.distance(Point(HX + CLR - (4.0 + CLR) + (4.0 + CLR) / math.sqrt(2), HY + CLR - (4.0 + CLR) + (4.0 + CLR) / math.sqrt(2))), 2)}}
    geo = dict(body=body, cav=cav, insert=insert, window=window, boss=boss, well=well, slit=slit, frame=frame, scr=scr, discs=discs, side=side,
               z=dict(back=z_back, plates=z_plates, dial=(z_dial0, z_dial1), cry=(z_cry0, z_cry1), lip0=z_lip0, top=z_top, frame0=z_frame0, disc1=z_disc1), crown=(crown_x0, crown_r, zw))
    return S, report, geo
