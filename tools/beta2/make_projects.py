# Beta 2 (2026-11-23): Claude starts two projects from Adam's brief, as numbers the sim and the resolver take from there.
#   sim/projects/air-size-study.json   gear pairs at module 0.6, 0.5 and 0.4 between three 1/8" plates: the first Air cut from the sim
#   sim/projects/beta2.json            the hand-set Hemistitch's train (crown worm -> intermediate -> minute and hour discs), first layout
# Re-run to regenerate both (it overwrites them). Every hole names a fit, so the press-fit test's sizes drop into the table once.
import json, math, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'sim', 'projects')
FITS = {
    'rod_press': {'d': 2.95, 'seat': None, 'note': '3 mm brass rod pressed into a gear (placeholder until the press-fit test)'},
    'rod_free': {'d': 3.1, 'seat': None, 'note': '3 mm rod turning freely (placeholder)'},
    'bearing': {'d': 6.0, 'seat': {'d': 7.3, 'depth': 0.65}, 'note': '3 x 6 x 2.5 flanged bearing pressed in, its 7.2 x 0.6 flange in the seat (placeholder)'},
    'm2_clear': {'d': 2.2, 'seat': None, 'note': 'M2 screw passing through'},
    'm2_tap': {'d': 1.6, 'seat': None, 'note': 'M2 screw threading into acrylic (placeholder)'},
}
SHOP = {'machine': 'Makera Carvera Air', 'cutter': 0.5, 'note': 'all testing on the Air; fits are placeholders until the press-fit test'}
ARMS = {'rim': 1.0, 'arm': 0.8, 'hubWall': 1.2}
SHEET = 3.175          # 1/8"
GEAR_T = 1.6           # 1/16" delrin

def rrect(cx, cy, w, h, r, step=0.25):
    """a rounded rectangle as sharp dots on true arcs (anticlockwise), like the sim's other true outlines"""
    pts = []
    for (qx, qy, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)):
        n = max(2, math.ceil(math.pi / 2 * r / step))
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    out, seen = [], set()
    for x, y in pts:
        k = (round(x, 4), round(y, 4))
        if k not in seen: seen.add(k); out.append({'u': k[0], 'v': k[1], 'smooth': False})
    return out

def sketch(kid, name, axis, off, pts):
    return {'id': kid, 'name': name, 'plane': {'axis': axis, 'offset': off}, 'closed': True, 'points': pts}

def gear_ra(m, z, x): return m * z / 2 + m * (1 + x)

def scene(project, state):
    return {'format': 'bspk-studio-scene', 'version': 3, 'savedAt': time.strftime('%Y-%m-%dT%H:%M:%S'), 'state': state, 'project': project}

# ---------------------------------------------------------------- the size study
def size_study():
    pairs = []
    for m in (0.6, 0.5, 0.4):
        zp = math.ceil(5.0 / m + 1.9)        # the fewest pinion teeth whose root circle leaves 1 mm of wall round a 3 mm rod (shift +0.3)
        pairs.append({'m': m, 'zp': zp, 'zw': 3 * zp, 'tag': str(int(round(m * 10)))})
    rows, y, gap = [], 0.0, 2.5
    for i, p in enumerate(pairs):
        p['a'] = p['m'] * (p['zp'] + p['zw']) / 2; p['raw'] = gear_ra(p['m'], p['zw'], -0.3); p['rap'] = gear_ra(p['m'], p['zp'], 0.3)
        if i: y -= pairs[i - 1]['raw'] + gap + p['raw']
        p['y'] = y
        left = -(p['rap'] + p['a'] + p['raw']) / 2
        p['xp'] = round(left + p['rap'], 4); p['xw'] = round(p['xp'] + p['a'], 4); p['y'] = round(y, 4)
    mid = (pairs[0]['y'] + pairs[0]['raw'] + pairs[-1]['y'] - pairs[-1]['raw']) / 2
    for p in pairs: p['y'] = round(p['y'] - mid, 4)
    span_x = max(p['rap'] + p['a'] + p['raw'] for p in pairs); span_y = pairs[0]['raw'] * 2 + sum(2 * p['raw'] for p in pairs[1:]) + gap * (len(pairs) - 1)
    win_w, win_h = span_x + 2 * 1.5, span_y + 2 * 1.5          # the frame's window: 1.5 mm round every wheel
    W, H, R = win_w + 2 * 5.5, win_h + 2 * 5.5, 4.0            # the plates: a 5.5 mm rim carries the screws
    screws = [(sx * (W / 2 - 2.75), sy * (H / 2 - 2.75)) for sx in (-1, 1) for sy in (-1, 1)]
    arbors, stages, pos, defaults_st = [], {}, {}, {}
    for p in pairs:
        t = p['tag']
        arbors.append({'id': f'p{t}', 'name': f"Pinion arbor · module {p['m']}", 'group': f'm{t}', 'level': 0,
                       'role': f"{p['zp']} teeth, module {p['m']}, shift +0.3, pressed on a 3 mm rod that turns in a bearing in each plate.",
                       'gears': [{'id': f'p{t}_g', 'label': f"Pinion {p['zp']} · m{p['m']}", 'z': p['zp'], 't': GEAR_T, 'x': 0.3, 'bore': 'rod_press'}]})
        arbors.append({'id': f'w{t}', 'name': f"Wheel arbor · module {p['m']}", 'group': f'm{t}', 'level': 1,
                       'role': f"{p['zw']} teeth, module {p['m']}, shift -0.3, four arms; pressed on a 3 mm rod in a bearing in each plate.",
                       'gears': [{'id': f'w{t}_g', 'label': f"Wheel {p['zw']} · m{p['m']}", 'z': p['zw'], 't': GEAR_T, 'x': -0.3, 'bore': 'rod_press', 'arms': 4}]})
        stages[f's{t}'] = [f'w{t}_g', f'p{t}_g']
        defaults_st[f's{t}'] = {'m': p['m'], 'z': 0.8}
        pos[f'p{t}'] = [p['xp'], p['y']]; pos[f'w{t}'] = [p['xw'], p['y']]
    outline = rrect(0, 0, W, H, R)
    sk = [sketch('K1', 'Plate outline (base)', 'z', -SHEET, outline), sketch('K2', 'Plate outline (frame)', 'z', 0, outline),
          sketch('K3', 'Frame window', 'z', 0, rrect(0, 0, win_w, win_h, 2.0)), sketch('K4', 'Plate outline (top)', 'z', SHEET, outline)]
    bearing = lambda i, a, frm: {'id': f'h{i}', 'kind': 'bearing', 'name': f'Bearing · {a}', 'fit': 'bearing', 'at': pos[a], 'd': 5.98, 'axis': a, 'from': frm, 'depth': None, 'seat': {'d': 7.3, 'depth': 0.65}}
    ids = [a['id'] for a in arbors]
    base_cuts = [bearing(i + 1, a, 'back') for i, a in enumerate(ids)] + [{'id': f'h{10 + i}', 'kind': 'pilot', 'name': 'M2 thread', 'fit': 'm2_tap', 'at': list(s), 'd': 1.6, 'from': 'back', 'depth': None} for i, s in enumerate(screws)]
    frame_cuts = [{'id': 'h1', 'kind': 'pocket', 'name': 'Window for the gears', 'sketch': 'K3', 'from': 'back', 'depth': None}] + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through', 'fit': 'm2_clear', 'at': list(s), 'd': 2.3, 'from': 'back', 'depth': None} for i, s in enumerate(screws)]
    top_cuts = [bearing(i + 1, a, 'front') for i, a in enumerate(ids)] + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through (pan head on top)', 'fit': 'm2_clear', 'at': list(s), 'd': 2.3, 'from': 'front', 'depth': None} for i, s in enumerate(screws)]
    drawn = [{'id': 'D1', 'name': 'Base plate (1/8" black delrin; a bearing under each arbor, flange up; M2 threads)', 'sketch': 'K1', 'thickness': SHEET, 'grow': 'plus', 'mill': 'back', 'cuts': base_cuts},
             {'id': 'D2', 'name': 'Frame (1/8" black delrin; the space the gears turn in)', 'sketch': 'K2', 'thickness': SHEET, 'grow': 'plus', 'mill': 'back', 'cuts': frame_cuts},
             {'id': 'D3', 'name': 'Top plate (1/8" black delrin, milled from underneath; a bearing over each arbor, flange down)', 'sketch': 'K4', 'thickness': SHEET, 'grow': 'plus', 'mill': 'front', 'cuts': top_cuts}]
    project = {
        'format': 'bspk-studio-project', 'id': 'air-size-study', 'name': 'Air size study', 'title': 'Air size study · how small the teeth go',
        'blurb': (f"Three gear pairs, 3:1 each, at module {', '.join(str(p['m']) for p in pairs)}, cut in 1/16\" delrin with a {SHOP['cutter']} mm end mill on the Air, "
                  f"between three 1/8\" black delrin plates ({W:.1f} x {H:.1f} mm). Each pinion has the fewest teeth that leave 1 mm of wall round its 3 mm rod. "
                  "Cut it, spin each pair by hand, and the smallest pair that runs clean sets Beta 2's tooth size. Every hole names a fit, so the press-fit test's sizes drop in once."),
        'source': ['Claude, 2026-11-23, from Adam\'s Beta 2 brief: smallest envelope with 3 mm brass rod, 3 x 6 x 2.5 flanged bearings, acrylic and delrin; all testing on the Air.'],
        'groups': {f"m{p['tag']}": f"Module {p['m']}" for p in pairs},
        'focus': [{'id': f"m{p['tag']}", 'label': f"Module {p['m']}: pinion {p['zp']} / wheel {p['zw']}", 'parts': [f"p{p['tag']}", f"w{p['tag']}"]} for p in pairs],
        'rules': {'minModule': 0.4, 'fixedModule': True, 'why': 'the tooth sizes are what this rig tests', 'arms': ARMS},
        'shop': SHOP,
        'rate': {'arbor': f"p{pairs[1]['tag']}", 'period': 60, 'dir': -1},
        'targets': [],
        'arbors': arbors, 'hands': [], 'stages': stages,
        'plate': {'name': 'Bench', 'z': -SHEET - 0.5, 'role': 'Just the bench under the rig; the rig\'s own plates are the drawn parts.'},
        'defaults': {'movementD': round(max(W, H) + 10), 'minGap': 0.2, 'zMax': 12, 'view': {'height': 12, 'mid': 1.6}, 'stages': defaults_st, 'pos': pos, 'fits': FITS_DELRIN,
                     'locks': {g['id']: True for a in arbors for g in a['gears']}},
    }
    # module 0.4's tooth spaces (about 0.4 mm at the root) are narrower than the 0.5 mm end mill: that pair is cut with the 0.4
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS_DELRIN, 'gearCut': {f"G:{g}{p['tag']}_g": 0.4 for p in pairs if p['m'] < 0.45 for g in 'pw'}}
    return scene(project, state), pairs, (W, H)

# ---------------------------------------------------------------- Beta 2 (the watch version, 2026-11-23)
FITS_DELRIN = {
    'rod_press': {'d': 2.96, 'seat': None, 'note': '3 mm brass rod pressed into a delrin gear (placeholder until the press-fit test, cut in delrin)'},
    'rod_free': {'d': 3.08, 'seat': None, 'note': '3 mm rod turning in a plain delrin hole (placeholder)'},
    'bearing': {'d': 5.98, 'seat': {'d': 7.3, 'depth': 0.65}, 'note': '3 x 6 x 2.5 flanged bearing pressed into delrin, flange in the seat (placeholder)'},
    'm2_clear': {'d': 2.3, 'seat': None, 'note': 'M2 screw passing through'},
    'm2_cb': {'d': 2.3, 'seat': {'d': 4.2, 'depth': 1.4}, 'note': 'M2 screw through, its cheese head sunk in a counterbore'},
    'm2_tap': {'d': 1.6, 'seat': None, 'note': 'M2 tapped thread in delrin'},
}
def circ_int(c1, r1, c2, r2):
    d = math.dist(c1, c2); a = (r1 * r1 - r2 * r2 + d * d) / (2 * d); h = math.sqrt(max(0.0, r1 * r1 - a * a))
    x2 = c1[0] + a * (c2[0] - c1[0]) / d; y2 = c1[1] + a * (c2[1] - c1[1]) / d
    return [(x2 + h * (c2[1] - c1[1]) / d, y2 - h * (c2[0] - c1[0]) / d), (x2 - h * (c2[1] - c1[1]) / d, y2 + h * (c2[0] - c1[0]) / d)]
def poly_dots(poly):
    """a shapely polygon's outer ring as the sim's sharp dots, anticlockwise"""
    xy = list(poly.exterior.coords)[:-1]
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]))
    if a < 0: xy = xy[::-1]
    return [{'u': round(x, 4), 'v': round(y, 4), 'smooth': False} for x, y in xy]
def box(x0, y0, x1, y1):
    from shapely.geometry import box as B
    return B(x0, y0, x1, y1)

VARIANTS = {
    'beta2': {'id': 'beta2', 'name': 'Beta 2', 'title': 'Beta 2 · hand-set Hemistitch, watch size', 'teeth': (12, 26, 12, 32, 13, 27),
              'ZE': 15, 'XE': 0.15, 'ZW': 18, 't': 2.446078946670053, 'A2near': (0.10, -5.80), 'Ey': -1, 'HX': 23.05, 'HY': 17.3, 'aligned': False},
}

def beta2(v=VARIANTS['beta2']):
    from shapely.geometry import Point
    from shapely.ops import unary_union
    m, TS, TT = 0.6, 3.175, 1.5875                    # module; 1/8" and 1/16" delrin
    cd = lambda z1, z2: m * (z1 + z2) / 2
    M_, H_ = (10.4, 0.0), (-10.4, 0.0)                 # the discs on Dual_Dial_Concept's dial centres; the movement is centred on them
    # the train: minute pinion 12 -> wheel 26 | pinion 12 -> wheel 32 | pinion 13 -> hour wheel 27 (exactly 12:1): the only tooth counts
    # where every wheel clears the next arbor's rod (both bearings below, so each rod runs up through every layer) with the hour wheel
    # under its Ø19 disc. The crown arbor E drives the minute pinion with an 18-tooth wheel of its own, from the other side of it.
    P0, Z1, P1, Z2, P2, Z3 = v['teeth']
    ZE, XE, ZW = v['ZE'], v['XE'], v['ZW']             # E's worm wheel (teeth, shift) and its wheel on the minute pinion
    def place(t):
        a1 = (M_[0] + cd(P0, Z1) * math.cos(t), M_[1] + cd(P0, Z1) * math.sin(t))
        return a1, min(circ_int(a1, cd(P1, Z2), H_, cd(P2, Z3)), key=lambda p: math.dist(p, v['A2near']))
    if v['aligned']:                                   # A1's direction from M where the two intermediates share an x (bisection)
        n = v['A1near']; t0 = math.atan2(n[1] - M_[1], n[0] - M_[0]); lo, hi = t0 - 0.02, t0 + 0.02
        g = lambda t: place(t)[0][0] - place(t)[1][0]
        assert (g(lo) > 0) != (g(hi) > 0)
        for _ in range(80):
            mid = (lo + hi) / 2
            if (g(mid) > 0) == (g(lo) > 0): lo = mid
            else: hi = mid
        t = (lo + hi) / 2
    else: t = v['t']                                   # A1's direction from M, from the layout search (centred box, crown on y = 0)
    A1, A2 = place(t)
    worm_rp = 2.65
    cw = m * ZE / 2 + XE * m + worm_rp                 # the worm's axis lies on y = 0 (3 o'clock on the movement): E sits this far off it
    E = (M_[0] + math.sqrt(cd(ZW, P0) ** 2 - cw ** 2), v['Ey'] * cw)
    for a, b, want in ((M_, A1, cd(P0, Z1)), (A1, A2, cd(P1, Z2)), (A2, H_, cd(P2, Z3)), (E, M_, cd(ZW, P0))):
        assert abs(math.dist(a, b) - want) < 1e-9
    # heights (z = 0 is the top of the upper plate). The worm lies in the plates (axis 4.2 mm down); the stem's journals (Ø1.8) run in a
    # channel in the lower plate under the upper one; E's worm wheel sits beside the worm in a pocket in the lower plate.
    zw = -4.2
    L1 = 0.5                                           # A1's wheel 0.5 to 1.7; the 1/16" minute pinion and E's wheel centred on it
    TW, TP = 1.2, TS - 1.2                             # a compound from 1/8": wheel 1.2 under a 1.975 pinion
    z_a2w = max(L1 + TW, L1 + TW / 2 + TT / 2) + 0.3   # A2's wheel 0.3 over everything on layer 1 (it passes over the minute pinion and E's wheel)
    dz_a1a2 = (L1 + TW) - (z_a2w + TW / 2 - TP / 2)
    z_a2p = z_a2w + TW; z_hw = max(z_a2w + TW + 0.3, z_a2p + TP + 0.3 - TT)
    dz_a2h = z_a2p - (z_hw + TT / 2 - TP / 2)
    z_disc = z_hw + TT
    HX, HY = v['HX'], v['HY']                          # the plates: centred on the discs (from the layout search)
    edge = HX
    wa, wb = E[0] - 2.5, E[0] + 2.5                    # the worm's span along the stem
    x0 = wa - 0.9                                      # the stem's inner end (journal B)
    xc = edge + 2.0                                    # where the crown starts: past the case wall
    jr = 0.9                                           # journal radius (Ø1.8)
    R_ew = m * ZE / 2 + m * (1 + XE)
    screws = [(sx * (HX - 3.2), sy * (HY - 3.2)) for sx in (-1, 1) for sy in (-1, 1)]
    arbors = [
        {'id': 'minute', 'name': 'Minute arbor', 'group': 'display', 'level': 0,
         'role': f'Turns once an hour; carries the minute disc. Its {P0}-tooth pinion takes the crown (from E\'s wheel) and drives the first intermediate wheel. Runs in plain delrin holes (under the disc), so the worm can lie close beside its rod.',
         'gears': [{'id': 'minute_pinion', 'label': 'Minute pinion', 'z': P0, 't': TT, 'x': 0.3, 'bore': 'rod_press'}]},
        {'id': 'a1', 'name': 'First intermediate', 'group': 'train', 'level': 1, 'partNames': {'a1': 'First intermediate wheel and pinion (one piece, 1/8" delrin)'},
         'role': f'{"Above" if A1[1] > 0 else "Below"} the centre, between the discs. Its {Z1}-tooth wheel is driven by the minute pinion; its {P1}-tooth pinion drives the second intermediate. One piece of 1/8" delrin, milled from the pinion side.',
         'gears': [{'id': 'a1_wheel', 'label': 'First intermediate wheel', 'z': Z1, 't': TW, 'x': -0.3, 'bore': 'rod_press', 'arms': 0, 'part': 'a1'},
                   {'id': 'a1_pinion', 'label': 'First intermediate pinion', 'z': P1, 't': TP, 'x': 0.3, 'bore': 'rod_press', 'part': 'a1'}]},
        {'id': 'a2', 'name': 'Second intermediate', 'group': 'train', 'level': 2, 'partNames': {'a2': 'Second intermediate wheel and pinion (one piece, 1/8" delrin)'},
         'role': f'{"Above" if A2[1] > 0 else "Below"} the centre, between the discs. {Z2}:{P1} down from the first intermediate; its {P2}-tooth pinion drives the hour wheel {Z3}:{P2}. One piece of 1/8" delrin; four arms.',
         'gears': [{'id': 'a2_wheel', 'label': 'Second intermediate wheel', 'z': Z2, 't': TW, 'x': -0.3, 'bore': 'rod_press', 'arms': 4, 'part': 'a2'},
                   {'id': 'a2_pinion', 'label': 'Second intermediate pinion', 'z': P2, 't': TP, 'x': 0.3, 'bore': 'rod_press', 'part': 'a2'}]},
        {'id': 'hour', 'name': 'Hour arbor', 'group': 'display', 'level': 3,
         'role': 'Turns once in 12 hours; the hour disc sits right on its wheel (riding high on the second intermediate pinion so the disc clears it).',
         'gears': [{'id': 'hour_wheel', 'label': 'Hour wheel', 'z': Z3, 't': TT, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]},
        {'id': 'e', 'name': 'Crown arbor (E)', 'group': 'crown', 'level': 4,
         'role': f'Takes the crown: the worm on the stem turns its {ZE}-tooth worm wheel (in a pocket in the lower plate), and its {ZW}-tooth wheel turns the minute pinion. Runs in plain delrin holes. One crown turn = one tooth: {P0 * ZE / ZW:.3g} turns an hour.',
         'gears': [{'id': 'e_worm', 'label': 'Crown arbor worm wheel', 'z': ZE, 't': TT, 'x': XE, 'bore': 'rod_press', 'arms': 0},
                   {'id': 'e_wheel', 'label': 'Crown arbor wheel', 'z': ZW, 't': TT, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]},
    ]
    disc_r = 9.5
    hands = [
        {'id': 'hour_disc', 'name': 'Hour disc', 'arbor': 'hour', 'group': 'display', 'level': 5, 'shape': 'disc', 'marks': 12,
         'labels': ['12', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'], 'indicator': math.pi / 2,
         'role': 'Ø19 black delrin, numerals V-carved and filled. Sits right on the hour wheel. Turns the other way to the minute disc (three reductions).'},
        {'id': 'minute_disc', 'name': 'Minute disc', 'arbor': 'minute', 'group': 'display', 'level': 5, 'shape': 'disc', 'marks': 60,
         'labels': ['0', '5', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'], 'indicator': math.pi / 2,
         'role': 'Ø19 black delrin, V-carved and filled; on the minute rod at the hour disc\'s height.'},
    ]
    outline = rrect(0.0, 0.0, 2 * HX, 2 * HY, 4.0)
    win = box(wa - 0.3, -3.55, wb + 0.3, 3.55)                            # the worm, with 0.3 round it (both plates)
    chan = box(x0 - 0.2, -0.975, edge + 0.5, 0.975)                       # the journals' channel in the lower plate (Ø1.8 + 0.15)
    sk = [sketch('K1', 'Lower plate outline', 'z', -2 * TS, outline), sketch('K2', 'Upper plate outline', 'z', -TS, outline),
          sketch('K3', 'Worm window (lower plate)', 'z', -2 * TS, poly_dots(win)),
          sketch('K4', 'Crown arbor worm wheel pocket (lower plate)', 'z', -2 * TS, poly_dots(Point(E).buffer(R_ew + 0.3, 64))),
          sketch('K5', 'Stem channel (lower plate)', 'z', -2 * TS, poly_dots(chan)),
          sketch('K6', 'Worm window (upper plate)', 'z', -TS, poly_dots(win))]
    pos = {'minute': list(M_), 'a1': list(A1), 'a2': list(A2), 'hour': list(H_), 'e': list(E)}
    bearing = lambda i, a: {'id': f'h{i}', 'kind': 'bearing', 'name': f'Bearing · {a}', 'fit': 'bearing', 'at': pos[a], 'd': 5.98, 'axis': a, 'from': 'back', 'depth': None, 'seat': {'d': 7.3, 'depth': 0.65}}
    plain = lambda i, a: {'id': f'h{i}', 'kind': 'rod', 'name': f'Plain hole · {a}', 'fit': 'rod_free', 'at': pos[a], 'd': 3.08, 'axis': a, 'from': 'back', 'depth': None}
    lower = ([bearing(i + 1, a) for i, a in enumerate(['a1', 'a2', 'hour'])] + [plain(4, 'minute'), plain(5, 'e')]
             + [{'id': 'h6', 'kind': 'pocket', 'name': 'Worm window (shows it from the back)', 'sketch': 'K3', 'from': 'back', 'depth': None},
                {'id': 'h7', 'kind': 'pocket', 'name': 'Crown arbor worm wheel pocket', 'sketch': 'K4', 'from': 'back', 'depth': round(-TS - (zw - TT / 2 - 0.3), 4)},
                {'id': 'h8', 'kind': 'pocket', 'name': 'Stem channel (the upper plate closes it)', 'sketch': 'K5', 'from': 'back', 'depth': round(-TS - (zw - jr - 0.05), 4)}]
             + [{'id': f'h{10 + i}', 'kind': 'pilot', 'name': 'M2 thread (plate screw)', 'fit': 'm2_tap', 'at': list(sc), 'd': 1.6, 'from': 'back', 'depth': None} for i, sc in enumerate(screws)])
    upper = ([bearing(i + 1, a) for i, a in enumerate(['a1', 'a2', 'hour'])] + [plain(4, 'minute'), plain(5, 'e')]
             + [{'id': 'h6', 'kind': 'pocket', 'name': 'Worm window', 'sketch': 'K6', 'from': 'back', 'depth': None}]
             + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through, head in a counterbore', 'fit': 'm2_cb', 'at': list(sc), 'd': 2.3, 'from': 'back', 'depth': None, 'seat': {'d': 4.2, 'depth': 1.4}} for i, sc in enumerate(screws)])
    prof = [(x0, 0), (x0, jr - 0.2), (x0 + 0.2, jr), (wa, jr), (wa, 2.95), (wa + 0.3, 3.25), (wb - 0.3, 3.25), (wb, 2.95), (wb, jr),
            (xc, jr), (xc, 3.85), (xc + 0.4, 4.25), (xc + 3.6, 4.25), (xc + 4.0, 3.85), (xc + 4.0, 0)]
    sk.append({'id': 'K10', 'name': 'Crown, stem and worm (half profile, turned about z = %g)' % zw, 'plane': {'axis': 'y', 'offset': 0.0}, 'closed': True,
               'points': [{'u': round(u, 4), 'v': round(zw + r_, 4), 'smooth': False} for u, r_ in prof]})
    drawn = [
        {'id': 'D1', 'name': 'Lower plate (1/8" black delrin; bottom bearings flange-up, the worm\'s window, E\'s worm wheel pocket, the stem channel, M2 threads)', 'sketch': 'K1', 'thickness': TS, 'grow': 'plus', 'mill': 'back', 'cuts': lower},
        {'id': 'D2', 'name': 'Upper plate (1/8" black delrin; top bearings with their flanges showing like jewels, the worm window, counterbored plate screws)', 'sketch': 'K2', 'thickness': TS, 'grow': 'plus', 'mill': 'back', 'cuts': upper},
        {'id': 'D4', 'name': 'Crown, stem and worm (one piece of 3/8" black delrin rod, cut on the 4th axis)', 'sketch': 'K10', 'thickness': 0.1, 'grow': 'plus',
         'turn': {'v': zw}, 'stock': 9.525,
         'worm': {'from': round(wa, 4), 'to': round(wb, 4), 'module': m, 'starts': 1, 'hand': 'right', 'pa': 20, 'backlash': 0.3},
         'flutes': {'from': round(xc, 4), 'to': round(xc + 4.0, 4), 'count': 12, 'width': 1.0, 'depth': 0.45}},
    ]
    top_z = z_disc + TT
    turns = P0 * ZE / ZW
    project = {
        'format': 'bspk-studio-project', 'id': v['id'], 'name': v['name'], 'title': v['title'],
        'blurb': (f'Two Ø19 discs on Dual_Dial_Concept\'s dial centres, the movement centred on them, set by a crown at 3 o\'clock on the movement, between the swivel lugs. '
                  f'The crown\'s worm turns a small crown arbor whose wheel turns the minute pinion; the train runs on above and below the centre'
                  + (', the two intermediates on one line through the middle' if v['aligned'] else '') + f': minute pinion {P0} → wheel {Z1}, '
                  f'pinion {P1} → wheel {Z2}, pinion {P2} → hour wheel {Z3} (exactly 12:1), so the discs keep true time against each other. {turns:.3g} crown turns an hour. '
                  f'Module 0.6 (the 0.5 mm end mill has room in every tooth space), black delrin throughout, brass rods, bearings showing like jewels. '
                  f'Movement {2 * HX:.1f} x {2 * HY:.1f} mm, {top_z + 2 * TS:.1f} mm from the back of the plates to the top of the discs.'),
        'source': ['Claude, 2026-11-23, from Adam\'s brief: the watch version of Hemistitch, hand-set, discs centred on the movement, crown at 3 o\'clock on the movement '
                   'to clear the hinged lugs, standard movement layering with the guts on show, a reliable machining tolerance; the case scaled to fit afterwards. '
                   'Layout from a search over every rod, bearing, gear layer, the worm and the stem, scored on the box centred on the discs.'],
        'groups': {'display': 'Discs', 'train': 'Train', 'crown': 'Crown works', 'drawn': 'Plates and stem'},
        'focus': [{'id': 'train', 'label': 'Crown → E → minute → first and second intermediate → hour', 'parts': ['e', 'minute', 'a1', 'a2', 'hour', 'D4']},
                  {'id': 'crown', 'label': 'Crown works: stem, worm, E', 'parts': ['e', 'minute', 'D4']}],
        'rules': {'minModule': 0.6, 'fixedModule': True, 'why': 'module 0.6: the 0.5 mm end mill has room in every tooth space', 'arms': ARMS, 'rod': {'d': 3.0, 'from': -2 * TS}},
        'shop': {'machine': 'Makera Carvera Air', 'cutter': 0.5, 'note': 'black delrin throughout; fits are delrin placeholders until the press-fit test'},
        'rate': {'arbor': 'minute', 'period': 3600, 'dir': -1},
        'targets': [{'label': 'Minute disc', 'arbor': 'minute', 'period': 3600, 'dir': -1}, {'label': 'Hour disc', 'arbor': 'hour', 'period': 43200, 'dir': 1}],
        'arbors': arbors, 'hands': hands,
        'stages': {'s_ma1': ['a1_wheel', 'minute_pinion'], 's_a1a2': ['a2_wheel', 'a1_pinion'], 's_a2h': ['hour_wheel', 'a2_pinion'], 's_em': ['e_wheel', 'minute_pinion']},
        'plate': {'name': 'Bench', 'z': -2 * TS - 1.5, 'role': 'Just the bench under the movement; the plates are the drawn parts.'},
        'defaults': {'movementD': 60, 'minGap': 0.3, 'zMax': 12, 'view': {'height': 22, 'mid': 0.5},
                     'stages': {'s_ma1': {'m': m, 'z': L1}, 's_a1a2': {'m': m, 'z': round(z_a2w, 4), 'dz': round(dz_a1a2, 5)},
                                's_a2h': {'m': m, 'z': round(z_hw, 4), 'dz': round(dz_a2h, 5)}, 's_em': {'m': m, 'z': L1}},
                     'solo': {'e_worm': {'m': m, 'z': round(zw - TT / 2, 5)}},
                     'pos': pos, 'fits': FITS_DELRIN,
                     'hands': {'hour_disc': {'length': disc_r, 'z': round(z_disc, 5), 't': TT}, 'minute_disc': {'length': disc_r, 'z': round(z_disc, 5), 't': TT}},
                     'locks': {g['id']: True for a in arbors for g in a['gears']} | {'hour_disc': True, 'minute_disc': True}},
    }
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS_DELRIN}
    info = {'id': v['id'], 'A1': A1, 'A2': A2, 'E': E, 'turns': turns, 'heights': dict(a1w=L1, a2w=z_a2w, hw=z_hw, disc=z_disc, top=top_z), 'size': (2 * HX, 2 * HY, top_z + 2 * TS)}
    return scene(project, state), info

def beta2_aligned():
    v = {'id': 'beta2-aligned', 'name': 'Beta 2 · aligned', 'title': 'Beta 2 · intermediates on the centre line', 'aligned': True, 'HX': 22.75, 'HY': 16.2}
    from shapely.geometry import Point
    from shapely.ops import unary_union
    m, TS, TT = 0.6, 3.175, 1.5875                    # module; 1/8" and 1/16" delrin
    cd = lambda z1, z2: m * (z1 + z2) / 2
    M_, H_ = (10.4, 0.0), (-10.4, 0.0)                 # the discs on Dual_Dial_Concept's dial centres; the movement is centred on them
    # the train, four reductions so both intermediates sit exactly on the centre line (Adam: symmetry on the top plate): minute pinion 12
    # -> B 18 | B pinion 11 -> first intermediate 22 | its pinion 11 -> second intermediate 22 | its pinion 13 -> hour wheel 26: 12:1 exactly.
    # Three layers: layer 1 B's pinion and A1's wheel; layer 2 A1's pinion and A2's wheel; layer 3 the minute pinion with B's and E's wheels,
    # and A2's pinion with the hour wheel, so both discs sit on top.
    P0, ZB, PB, Z1, P1, Z2, P2, Z3 = 12, 18, 11, 22, 11, 22, 13, 26
    ZE, XE, ZW = 15, 0.15, 18
    y2 = math.sqrt(cd(P2, Z3) ** 2 - 10.4 ** 2)        # A2 on x = 0, one centre distance from the hour arbor
    A2 = (0.0, y2); A1 = (0.0, y2 - cd(P1, Z2))
    B = min(circ_int(M_, cd(P0, ZB), A1, cd(PB, Z1)), key=lambda p: math.dist(p, (8.90, -8.87)))
    worm_rp = 2.65
    cw = m * ZE / 2 + XE * m + worm_rp                 # the worm's axis lies on y = 0 (3 o'clock on the movement): E sits this far off it
    E = (M_[0] + math.sqrt(cd(ZW, P0) ** 2 - cw ** 2), cw)
    for a_, b_, want in ((M_, B, cd(P0, ZB)), (B, A1, cd(PB, Z1)), (A1, A2, cd(P1, Z2)), (A2, H_, cd(P2, Z3)), (E, M_, cd(ZW, P0))):
        assert abs(math.dist(a_, b_) - want) < 1e-9
    # heights (z = 0 is the top of the upper plate). The worm lies in the plates (axis 4.2 mm down); the stem's journals (Ø1.8) run in a
    # channel in the lower plate under the upper one; E's worm wheel sits beside the worm in a pocket in the lower plate.
    zw = -4.2
    L1 = 0.5                                           # A1's wheel 0.5 to 1.7; B's 1/16" pinion centred on it
    TW, TP = 1.2, TS - 1.2                             # a compound from 1/8": wheel 1.2 under a 1.975 pinion
    z_a2w = L1 + TW + 0.3                              # A2's wheel 0.3 over A1's (they overlap in plan)
    dz_a1a2 = (L1 + TW) - (z_a2w + TW / 2 - TP / 2)
    z_a2p = z_a2w + TW
    z_hw = max(z_a2w + TW + 0.3, z_a2p + TP + 0.3 - TT, L1 + TS + 0.3)   # the hour wheel clears A2's wheel and A1's pinion (it overhangs both)
    dz_a2h = z_a2p - (z_hw + TT / 2 - TP / 2)
    z_bw = L1 + TS + 0.3                               # B's wheel (and E's) 0.3 over A1's pinion, which they overlap in plan
    dz_mb = 0.3                                        # the minute pinion rides 0.3 above B's wheel, so the minute disc can sit on it ...
    dz_em = 0.3                                        # ... and E's wheel, centred low on it, stays 0.3 under the disc
    z_disc = z_bw + dz_mb + TT                         # both discs at the minute pinion's top
    # the worm rises out of the plates: at 3 o'clock nothing is on the two lower layers (the minute pinion and E's wheel are on top), so its
    # axis goes as high as clears the top layer by 0.3. That puts the crown at the movement's mid-height, not hanging under the back.
    zw = z_bw - 0.3 - (worm_rp + m)
    HX, HY = v['HX'], v['HY']                          # the plates: centred on the discs (from the layout search)
    edge = HX
    wa, wb = E[0] - 2.5, E[0] + 2.5                    # the worm's span along the stem
    x0 = wa - 0.9                                      # the stem's inner end (journal B)
    xc = edge + 2.0                                    # where the crown starts: past the case wall
    jr = 0.9                                           # journal radius (Ø1.8)
    R_ew = m * ZE / 2 + m * (1 + XE)
    screws = [(sx * (HX - 3.2), sy * (HY - 3.2)) for sx in (-1, 1) for sy in (-1, 1)]
    arbors = [
        {'id': 'minute', 'name': 'Minute arbor', 'group': 'display', 'level': 0,
         'role': f'Turns once an hour; the minute disc sits right on its {P0}-tooth pinion, which takes the crown (from E\'s wheel) and drives the transfer arbor. Runs in plain delrin holes (under the disc), so the worm can lie close beside its rod.',
         'gears': [{'id': 'minute_pinion', 'label': 'Minute pinion', 'z': P0, 't': TT, 'x': 0.3, 'bore': 'rod_press'}]},
        {'id': 'b', 'name': 'Transfer arbor (B)', 'group': 'train', 'level': 1,
         'role': f'Under the minute disc\'s lower edge: its {ZB}-tooth wheel (top layer) is driven by the minute pinion, its {PB}-tooth pinion (bottom layer) drives the first intermediate wheel, so both intermediates can sit on the centre line. Two pieces on one rod.',
         'gears': [{'id': 'b_pinion', 'label': 'Transfer pinion', 'z': PB, 't': TT, 'x': 0.3, 'bore': 'rod_press'},
                   {'id': 'b_wheel', 'label': 'Transfer wheel', 'z': ZB, 't': TT, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]},
        {'id': 'a1', 'name': 'First intermediate', 'group': 'train', 'level': 1, 'partNames': {'a1': 'First intermediate wheel and pinion (one piece, 1/8" delrin)'},
         'role': f'On the centre line, {abs(A1[1]):.1f} {"above" if A1[1] > 0 else "below"} the middle. Its {Z1}-tooth wheel is driven by the transfer pinion; its {P1}-tooth pinion drives the second intermediate. One piece of 1/8" delrin, milled from the pinion side.',
         'gears': [{'id': 'a1_wheel', 'label': 'First intermediate wheel', 'z': Z1, 't': TW, 'x': -0.3, 'bore': 'rod_press', 'arms': 0, 'part': 'a1'},
                   {'id': 'a1_pinion', 'label': 'First intermediate pinion', 'z': P1, 't': TP, 'x': 0.3, 'bore': 'rod_press', 'part': 'a1'}]},
        {'id': 'a2', 'name': 'Second intermediate', 'group': 'train', 'level': 2, 'partNames': {'a2': 'Second intermediate wheel and pinion (one piece, 1/8" delrin)'},
         'role': f'On the centre line, {abs(A2[1]):.1f} {"above" if A2[1] > 0 else "below"} the middle. {Z2}:{P1} down from the first intermediate; its {P2}-tooth pinion drives the hour wheel {Z3}:{P2}. One piece of 1/8" delrin.',
         'gears': [{'id': 'a2_wheel', 'label': 'Second intermediate wheel', 'z': Z2, 't': TW, 'x': -0.3, 'bore': 'rod_press', 'arms': 0, 'part': 'a2'},
                   {'id': 'a2_pinion', 'label': 'Second intermediate pinion', 'z': P2, 't': TP, 'x': 0.3, 'bore': 'rod_press', 'part': 'a2'}]},
        {'id': 'hour', 'name': 'Hour arbor', 'group': 'display', 'level': 3,
         'role': 'Turns once in 12 hours; the hour disc sits right on its wheel (riding high on the second intermediate pinion so the disc clears it).',
         'gears': [{'id': 'hour_wheel', 'label': 'Hour wheel', 'z': Z3, 't': TT, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]},
        {'id': 'e', 'name': 'Crown arbor (E)', 'group': 'crown', 'level': 4,
         'role': f'Takes the crown: the worm on the stem turns its {ZE}-tooth worm wheel (in a pocket in the lower plate), and its {ZW}-tooth wheel turns the minute pinion. Runs in plain delrin holes. One crown turn = one tooth: {P0 * ZE / ZW:.3g} turns an hour.',
         'gears': [{'id': 'e_worm', 'label': 'Crown arbor worm wheel', 'z': ZE, 't': TT, 'x': XE, 'bore': 'rod_press', 'arms': 0},
                   {'id': 'e_wheel', 'label': 'Crown arbor wheel', 'z': ZW, 't': TT, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]},
    ]
    disc_r = 9.5
    hands = [
        {'id': 'hour_disc', 'name': 'Hour disc', 'arbor': 'hour', 'group': 'display', 'level': 5, 'shape': 'disc', 'marks': 12,
         'labels': ['12', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'], 'indicator': math.pi / 2,
         'role': 'Ø19 black delrin, numerals V-carved and filled; on the hour rod at the minute disc\'s height, just above the hour wheel. Turns the same way as the minute disc (four reductions).'},
        {'id': 'minute_disc', 'name': 'Minute disc', 'arbor': 'minute', 'group': 'display', 'level': 5, 'shape': 'disc', 'marks': 60,
         'labels': ['0', '5', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'], 'indicator': math.pi / 2,
         'role': 'Ø19 black delrin, V-carved and filled; sits right on the minute pinion.'},
    ]
    outline = rrect(0.0, 0.0, 2 * HX, 2 * HY, 4.0)
    win = box(wa - 0.3, -3.55, wb + 0.3, 3.55)                            # the worm, with 0.3 round it (both plates: see through it)
    chan = box(x0 - 0.2, -0.975, edge + 0.5, 0.975)                       # the journals' channel in the upper plate's top (Ø1.8 + 0.15)
    # the stem bridge: two feet over the journals (a channel in their underside holds the journals' top halves) and a rail along the
    # bottom joining them; open over the worm (it stands above the bridge) and clear of E's worm wheel above the stem
    bx0, bx1, by0, by1 = x0, edge - 0.6, -6.0, E[1] - R_ew - 0.3
    feet = unary_union([box(bx0, by0, wa - 0.35, by1), box(wb + 0.35, by0, bx1, by1)])
    bridge = unary_union([feet, box(bx0, by0, bx1, -3.85)]).buffer(-0.6).buffer(0.6, 16)
    bscrews = [(bx0 + 1.4, -4.9), (bx1 - 1.4, -4.9)]
    sk = [sketch('K1', 'Lower plate outline', 'z', -2 * TS, outline), sketch('K2', 'Upper plate outline', 'z', -TS, outline),
          sketch('K3', 'Worm window (lower plate)', 'z', -2 * TS, poly_dots(win)),
          sketch('K4', 'Crown arbor worm wheel pocket (upper plate)', 'z', -TS, poly_dots(Point(E).buffer(R_ew + 0.3, 64))),
          sketch('K5', 'Stem channel (upper plate)', 'z', -TS, poly_dots(chan)),
          sketch('K6', 'Worm window (upper plate)', 'z', -TS, poly_dots(win)),
          sketch('K7', 'Stem bridge outline', 'z', 0.0, poly_dots(bridge)),
          sketch('K8', 'Stem bridge: journal channel in its underside', 'z', 0.0, poly_dots(box(bx0 - 0.5, -0.975, bx1 + 0.5, 0.975))),
          sketch('K9', 'Stem bridge: the worm rises through it', 'z', 0.0, poly_dots(box(wa - 0.3, -3.55, wb + 0.3, by1 + 1.0)))]
    pos = {'minute': list(M_), 'b': list(B), 'a1': list(A1), 'a2': list(A2), 'hour': list(H_), 'e': list(E)}
    bearing = lambda i, a: {'id': f'h{i}', 'kind': 'bearing', 'name': f'Bearing · {a}', 'fit': 'bearing', 'at': pos[a], 'd': 5.98, 'axis': a, 'from': 'back', 'depth': None, 'seat': {'d': 7.3, 'depth': 0.65}}
    plain = lambda i, a: {'id': f'h{i}', 'kind': 'rod', 'name': f'Plain hole · {a}', 'fit': 'rod_free', 'at': pos[a], 'd': 3.08, 'axis': a, 'from': 'back', 'depth': None}
    lower = ([bearing(i + 1, a) for i, a in enumerate(['a1', 'a2', 'hour'])] + [plain(4, 'minute'), plain(5, 'e'), bearing(9, 'b')]
             + [{'id': 'h6', 'kind': 'pocket', 'name': 'Window under the worm (see through the movement)', 'sketch': 'K3', 'from': 'back', 'depth': None}]
             + [{'id': f'h{10 + i}', 'kind': 'pilot', 'name': 'M2 thread (plate screw)', 'fit': 'm2_tap', 'at': list(sc), 'd': 1.6, 'from': 'back', 'depth': None} for i, sc in enumerate(screws)])
    upper = ([bearing(i + 1, a) for i, a in enumerate(['a1', 'a2', 'hour'])] + [plain(4, 'minute'), plain(5, 'e'), bearing(9, 'b')]
             + [{'id': 'h6', 'kind': 'pocket', 'name': 'Worm window', 'sketch': 'K6', 'from': 'back', 'depth': None},
                {'id': 'h7', 'kind': 'pocket', 'name': 'Crown arbor worm wheel pocket', 'sketch': 'K4', 'from': 'back', 'depth': round(max(0.0, -(zw - TT / 2)) + 0.3, 4)},
                {'id': 'h8', 'kind': 'pocket', 'name': 'Stem channel (the stem bridge closes it)', 'sketch': 'K5', 'from': 'back', 'depth': round(-(zw - jr) + 0.05, 4)}]
             + [{'id': f'h{20 + i}', 'kind': 'pilot', 'name': 'M2 thread (stem bridge)', 'fit': 'm2_tap', 'at': list(sc), 'd': 1.6, 'from': 'back', 'depth': None} for i, sc in enumerate(bscrews)]
             + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through, head in a counterbore', 'fit': 'm2_cb', 'at': list(sc), 'd': 2.3, 'from': 'back', 'depth': None, 'seat': {'d': 4.2, 'depth': 1.4}} for i, sc in enumerate(screws)])
    prof = [(x0, 0), (x0, jr - 0.2), (x0 + 0.2, jr), (wa, jr), (wa, 2.95), (wa + 0.3, 3.25), (wb - 0.3, 3.25), (wb, 2.95), (wb, jr),
            (xc, jr), (xc, 3.85), (xc + 0.4, 4.25), (xc + 3.6, 4.25), (xc + 4.0, 3.85), (xc + 4.0, 0)]
    sk.append({'id': 'K10', 'name': 'Crown, stem and worm (half profile, turned about z = %g)' % zw, 'plane': {'axis': 'y', 'offset': 0.0}, 'closed': True,
               'points': [{'u': round(u, 4), 'v': round(zw + r_, 4), 'smooth': False} for u, r_ in prof]})
    bcuts = ([{'id': 'h1', 'kind': 'pocket', 'name': 'Journal channel: its feet hold the stem down', 'sketch': 'K8', 'from': 'front', 'depth': round(zw + jr + 0.05, 4)},
              {'id': 'h2', 'kind': 'pocket', 'name': 'The worm rises through it (a window onto the worm)', 'sketch': 'K9', 'from': 'front', 'depth': None}]
             + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through (pan head on the top face)', 'fit': 'm2_clear', 'at': list(sc), 'd': 2.3, 'from': 'front', 'depth': None} for i, sc in enumerate(bscrews)])
    drawn = [
        {'id': 'D1', 'name': 'Lower plate (1/8" black delrin; bottom bearings flange-up, the worm\'s window, E\'s worm wheel pocket, the stem channel, M2 threads)', 'sketch': 'K1', 'thickness': TS, 'grow': 'plus', 'mill': 'back', 'cuts': lower},
        {'id': 'D2', 'name': 'Upper plate (1/8" black delrin; top bearings with their flanges showing like jewels, the worm window, counterbored plate screws)', 'sketch': 'K2', 'thickness': TS, 'grow': 'plus', 'mill': 'back', 'cuts': upper},
        {'id': 'D3', 'name': 'Stem bridge (1/8" black delrin, milled from underneath; its feet hold the stem\'s journals down, the worm rises through it, pan-head screws)', 'sketch': 'K7', 'thickness': TS, 'grow': 'plus', 'mill': 'front', 'cuts': bcuts},
        {'id': 'D4', 'name': 'Crown, stem and worm (one piece of 3/8" black delrin rod, cut on the 4th axis)', 'sketch': 'K10', 'thickness': 0.1, 'grow': 'plus',
         'turn': {'v': zw}, 'stock': 9.525,
         'worm': {'from': round(wa, 4), 'to': round(wb, 4), 'module': m, 'starts': 1, 'hand': 'right', 'pa': 20, 'backlash': 0.3},
         'flutes': {'from': round(xc, 4), 'to': round(xc + 4.0, 4), 'count': 12, 'width': 1.0, 'depth': 0.45}},
    ]
    top_z = z_disc + TT
    turns = P0 * ZE / ZW
    project = {
        'format': 'bspk-studio-project', 'id': v['id'], 'name': v['name'], 'title': v['title'],
        'blurb': (f'Two Ø19 discs on Dual_Dial_Concept\'s dial centres, the movement centred on them, set by a crown at 3 o\'clock on the movement, between the swivel lugs. '
                  f'The crown\'s worm turns a small crown arbor whose wheel turns the minute pinion; a transfer arbor under the minute disc lets both intermediates sit exactly on the centre line: '
                  f'minute pinion {P0} → {ZB}, pinion {PB} → {Z1}, pinion {P1} → {Z2}, pinion {P2} → hour wheel {Z3} (exactly 12:1), so the discs keep true time against each other and turn the same way. {turns:.3g} crown turns an hour. '
                  f'Module 0.6 (the 0.5 mm end mill has room in every tooth space), black delrin throughout, brass rods, bearings showing like jewels. '
                  f'Movement {2 * HX:.1f} x {2 * HY:.1f} mm, {top_z + 2 * TS:.1f} mm from the back of the plates to the top of the discs.'),
        'source': ['Claude, 2026-11-23, from Adam\'s brief: the watch version of Hemistitch, hand-set, discs centred on the movement, crown at 3 o\'clock on the movement '
                   'to clear the hinged lugs, standard movement layering with the guts on show, a reliable machining tolerance; the case scaled to fit afterwards. '
                   'Layout from a search over every rod, bearing, gear layer, the worm and the stem, scored on the box centred on the discs.'],
        'groups': {'display': 'Discs', 'train': 'Train', 'crown': 'Crown works', 'drawn': 'Plates and stem'},
        'focus': [{'id': 'train', 'label': 'Crown → E → minute → transfer → first and second intermediate → hour', 'parts': ['e', 'minute', 'b', 'a1', 'a2', 'hour', 'D4']},
                  {'id': 'crown', 'label': 'Crown works: stem, worm, E, stem bridge', 'parts': ['e', 'minute', 'D3', 'D4']}],
        'rules': {'minModule': 0.6, 'fixedModule': True, 'why': 'module 0.6: the 0.5 mm end mill has room in every tooth space', 'arms': ARMS, 'rod': {'d': 3.0, 'from': -2 * TS}},
        'shop': {'machine': 'Makera Carvera Air', 'cutter': 0.5, 'note': 'black delrin throughout; fits are delrin placeholders until the press-fit test'},
        'rate': {'arbor': 'minute', 'period': 3600, 'dir': -1},
        'targets': [{'label': 'Minute disc', 'arbor': 'minute', 'period': 3600, 'dir': -1}, {'label': 'Hour disc', 'arbor': 'hour', 'period': 43200, 'dir': -1}],
        'arbors': arbors, 'hands': hands,
        'stages': {'s_mb': ['b_wheel', 'minute_pinion'], 's_ba1': ['a1_wheel', 'b_pinion'], 's_a1a2': ['a2_wheel', 'a1_pinion'], 's_a2h': ['hour_wheel', 'a2_pinion'], 's_em': ['e_wheel', 'minute_pinion']},
        'plate': {'name': 'Bench', 'z': -2 * TS - 1.5, 'role': 'Just the bench under the movement; the plates are the drawn parts.'},
        'defaults': {'movementD': 60, 'minGap': 0.3, 'zMax': 12, 'view': {'height': 22, 'mid': 0.5},
                     'stages': {'s_mb': {'m': m, 'z': round(z_bw, 4), 'dz': dz_mb}, 's_ba1': {'m': m, 'z': L1}, 's_a1a2': {'m': m, 'z': round(z_a2w, 4), 'dz': round(dz_a1a2, 5)},
                                's_a2h': {'m': m, 'z': round(z_hw, 4), 'dz': round(dz_a2h, 5)}, 's_em': {'m': m, 'z': round(z_bw, 4), 'dz': dz_em}},
                     'solo': {'e_worm': {'m': m, 'z': round(zw - TT / 2, 5)}},
                     'pos': pos, 'fits': FITS_DELRIN,
                     'hands': {'hour_disc': {'length': disc_r, 'z': round(z_disc, 5), 't': TT}, 'minute_disc': {'length': disc_r, 'z': round(z_disc, 5), 't': TT}},
                     'locks': {g['id']: True for a in arbors for g in a['gears']} | {'hour_disc': True, 'minute_disc': True}},
    }
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS_DELRIN}
    info = {'id': v['id'], 'B': B, 'A1': A1, 'A2': A2, 'E': E, 'turns': turns, 'worm_axis': zw, 'crown_z': (zw - 4.25, zw + 4.25), 'heights': dict(a1w=L1, a2w=z_a2w, hw=z_hw, disc=z_disc, top=top_z), 'size': (2 * HX, 2 * HY, top_z + 2 * TS)}
    return scene(project, state), info

if __name__ == '__main__':
    s1, pairs, WH = size_study()
    json.dump(s1, open(os.path.join(OUT, 'air-size-study.json'), 'w'), indent=1)
    print('size study plates %.1f x %.1f mm;' % WH, '; '.join(f"m{p['m']}: {p['zp']}/{p['zw']} at CD {p['a']:g}" for p in pairs))
    for key, var in VARIANTS.items():
        s2, info = beta2(var)
        json.dump(s2, open(os.path.join(OUT, f'{key}.json'), 'w'), indent=1)
        print(key + ':', json.dumps(info, default=str))
    s3, info = beta2_aligned()
    json.dump(s3, open(os.path.join(OUT, 'beta2-aligned.json'), 'w'), indent=1)
    print('beta2-aligned:', json.dumps(info, default=str))
