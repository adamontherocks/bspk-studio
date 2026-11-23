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
    bearing = lambda i, a, frm: {'id': f'h{i}', 'kind': 'bearing', 'name': f'Bearing · {a}', 'fit': 'bearing', 'at': pos[a], 'd': 6.0, 'axis': a, 'from': frm, 'depth': None, 'seat': {'d': 7.3, 'depth': 0.65}}
    ids = [a['id'] for a in arbors]
    base_cuts = [bearing(i + 1, a, 'back') for i, a in enumerate(ids)] + [{'id': f'h{10 + i}', 'kind': 'pilot', 'name': 'M2 thread', 'fit': 'm2_tap', 'at': list(s), 'd': 1.6, 'from': 'back', 'depth': None} for i, s in enumerate(screws)]
    frame_cuts = [{'id': 'h1', 'kind': 'pocket', 'name': 'Window for the gears', 'sketch': 'K3', 'from': 'back', 'depth': None}] + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through', 'fit': 'm2_clear', 'at': list(s), 'd': 2.2, 'from': 'back', 'depth': None} for i, s in enumerate(screws)]
    top_cuts = [bearing(i + 1, a, 'front') for i, a in enumerate(ids)] + [{'id': f'h{10 + i}', 'kind': 'clear', 'name': 'M2 through (pan head on top)', 'fit': 'm2_clear', 'at': list(s), 'd': 2.2, 'from': 'front', 'depth': None} for i, s in enumerate(screws)]
    drawn = [{'id': 'D1', 'name': 'Base plate (1/8" acrylic; a bearing under each arbor, flange up; M2 threads)', 'sketch': 'K1', 'thickness': SHEET, 'grow': 'plus', 'mill': 'back', 'cuts': base_cuts},
             {'id': 'D2', 'name': 'Frame (1/8" acrylic; the space the gears turn in)', 'sketch': 'K2', 'thickness': SHEET, 'grow': 'plus', 'mill': 'back', 'cuts': frame_cuts},
             {'id': 'D3', 'name': 'Top plate (1/8" acrylic, milled from underneath; a bearing over each arbor, flange down)', 'sketch': 'K4', 'thickness': SHEET, 'grow': 'plus', 'mill': 'front', 'cuts': top_cuts}]
    project = {
        'format': 'bspk-studio-project', 'id': 'air-size-study', 'name': 'Air size study', 'title': 'Air size study · how small the teeth go',
        'blurb': (f"Three gear pairs, 3:1 each, at module {', '.join(str(p['m']) for p in pairs)}, cut in 1/16\" delrin with a {SHOP['cutter']} mm end mill on the Air, "
                  f"between three 1/8\" acrylic plates ({W:.1f} x {H:.1f} mm). Each pinion has the fewest teeth that leave 1 mm of wall round its 3 mm rod. "
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
        'defaults': {'movementD': round(max(W, H) + 10), 'minGap': 0.2, 'zMax': 12, 'view': {'height': 12, 'mid': 1.6}, 'stages': defaults_st, 'pos': pos, 'fits': FITS,
                     'locks': {g['id']: True for a in arbors for g in a['gears']}},
    }
    # module 0.4's tooth spaces (about 0.4 mm at the root) are narrower than the 0.5 mm end mill: that pair is cut with the 0.4
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS, 'gearCut': {f"G:{g}{p['tag']}_g": 0.4 for p in pairs if p['m'] < 0.45 for g in 'pw'}}
    return scene(project, state), pairs, (W, H)

# ---------------------------------------------------------------- Beta 2
def beta2():
    m = 0.5
    zp, zi, zh = 12, 36, 48
    a1, a2 = m * (zp + zi) / 2, m * (zp + zh) / 2                # minute pinion -> intermediate wheel; intermediate pinion -> hour wheel
    H_, M_ = (-10.0, 0.0), (10.0, 0.0)                            # the discs side by side: hour left, minute right (Hemistitch)
    d = math.dist(H_, M_); x = (a2 ** 2 - a1 ** 2 + d * d) / (2 * d); y = -math.sqrt(a2 ** 2 - x * x)
    I_ = (H_[0] + x, y)                                          # exact: the sim checks meshes to 1 µm
    # heights: the intermediate wheel and pinion are one piece of 1/8" delrin, the wheel 1.2 thick under a 1.975 pinion; the hour wheel
    # (1/16") is centred on that pinion, which leaves it 0.19 mm above the intermediate wheel it overlaps in plan
    TW, TP = 1.2, SHEET - 1.2
    L1 = 0.8; L2 = round(L1 + TW - GEAR_T / 2 + TP / 2, 4)
    # the worm meshes the intermediate wheel from below, its axis level with that wheel's middle
    rp_worm, shift_w = 3.0, -0.3
    yw = round(I_[1] - (m * zi / 2 + shift_w * m + rp_worm), 4); zw = round(L1 + TW / 2, 4)
    xs = I_[0]
    # the crown, stem and worm: one delrin part, tip on the left, crown on the right (profile: u = model x, r above the axis)
    u0 = xs - 2.5 - 2.5
    prof = [(0, 0), (0, 1.3), (0.2, 1.5), (2.5, 1.5), (2.5, 3.2), (2.8, 3.5), (7.2, 3.5), (7.5, 3.2), (7.5, 1.5), (10.5, 1.5),
            (10.5, 4.2), (10.8, 4.5), (14.1, 4.5), (14.5, 4.1), (14.5, 0)]
    stem_pts = [{'u': round(u0 + u, 4), 'v': round(zw + r, 4), 'smooth': False} for u, r in prof]
    arbors = [
        {'id': 'minute', 'name': 'Minute arbor', 'group': 'display', 'level': 0,
         'role': 'Turns once an hour and carries the minute disc. Its 12-tooth pinion is driven by the intermediate wheel (3:1 up from it).',
         'gears': [{'id': 'minute_pinion', 'label': 'Minute pinion', 'z': zp, 't': GEAR_T, 'x': 0.3, 'bore': 'rod_press'}]},
        {'id': 'inter', 'name': 'Intermediate arbor', 'group': 'train', 'level': 1, 'partNames': {'inter': 'Intermediate wheel and pinion (one piece, 1/8" delrin)'},
         'role': 'The crown\'s worm turns its wheel (one tooth per crown turn); the same wheel drives the minute pinion and its own pinion drives the hour wheel. Wheel and pinion are one piece, milled from the pinion\'s side.',
         'gears': [{'id': 'inter_wheel', 'label': 'Intermediate wheel', 'z': zi, 't': TW, 'x': -0.3, 'bore': 'rod_press', 'arms': 4, 'part': 'inter'},
                   {'id': 'inter_pinion', 'label': 'Intermediate pinion', 'z': zp, 't': TP, 'x': 0.3, 'bore': 'rod_press', 'part': 'inter'}]},
        {'id': 'hour', 'name': 'Hour arbor', 'group': 'display', 'level': 2,
         'role': 'Turns once in 12 hours and carries the hour disc. Driven 4:1 down by the intermediate pinion.',
         'gears': [{'id': 'hour_wheel', 'label': 'Hour wheel', 'z': zh, 't': GEAR_T, 'x': -0.3, 'bore': 'rod_press', 'arms': 4}]},
    ]
    disc_r, disc_z = 9.5, 6.4
    hands = [
        {'id': 'hour_disc', 'name': 'Hour disc', 'arbor': 'hour', 'group': 'display', 'level': 3, 'shape': 'disc', 'marks': 12,
         'labels': ['12', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'], 'indicator': math.pi / 2,
         'role': 'Hours 1 to 12, V-carved into acrylic and inked. The hour under the index at its top is the hour.'},
        {'id': 'minute_disc', 'name': 'Minute disc', 'arbor': 'minute', 'group': 'display', 'level': 3, 'shape': 'disc', 'marks': 60,
         'labels': ['0', '5', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'], 'indicator': math.pi / 2,
         'role': 'Minutes, V-carved and inked; the minute under the index at its top.'},
    ]
    sk = [{'id': 'K1', 'name': 'Crown, stem and worm (half profile, turned about z = %g)' % zw, 'plane': {'axis': 'y', 'offset': yw}, 'closed': True, 'points': stem_pts}]
    drawn = [{'id': 'D1', 'name': 'Crown, stem and worm (one delrin part from 3/8" rod, cut on the 4th axis)', 'sketch': 'K1', 'thickness': 0.1, 'grow': 'plus',
              'turn': {'v': zw}, 'stock': 9.525,
              'worm': {'from': round(u0 + 2.5, 4), 'to': round(u0 + 7.5, 4), 'module': m, 'starts': 1, 'hand': 'right', 'pa': 20},
              'flutes': {'from': round(u0 + 10.5, 4), 'to': round(u0 + 14.5, 4), 'count': 12, 'width': 1.0, 'depth': 0.45}}]
    pos = {'hour': list(H_), 'minute': list(M_), 'inter': list(I_)}
    project = {
        'format': 'bspk-studio-project', 'id': 'beta2', 'name': 'Beta 2', 'title': 'Beta 2 · hand-set Hemistitch',
        'blurb': ('A two-disc time teller, wound by hand like Crescent: the crown\'s worm turns an intermediate wheel that drives the minute disc 3:1 up '
                  'and the hour disc 12:1 below it, so the two discs always keep true time against each other. 12 crown turns an hour. '
                  'Module 0.5 in 1/16" delrin until the size study says otherwise; 3 mm brass rod in 3 x 6 x 2.5 flanged bearings; plates in acrylic (next).'),
        'source': ['Claude, 2026-11-23, from Adam\'s brief: a mid-complexity Hemistitch, manually wound, standard movement layering, smallest envelope; '
                   'the worm on the crown stem (one delrin part with the crown) for the Air\'s 4th axis. First layout: plates come once the layout is agreed.'],
        'groups': {'display': 'Discs', 'train': 'Train', 'drawn': 'Crown and plates'},
        'focus': [{'id': 'train', 'label': 'Crown → intermediate → minute and hour', 'parts': ['inter', 'minute', 'hour', 'D1']}],
        'rules': {'minModule': 0.4, 'fixedModule': True, 'why': 'module 0.5 for the Air\'s 0.5 mm end mill, until the size study', 'arms': ARMS},
        'shop': SHOP,
        'rate': {'arbor': 'minute', 'period': 3600, 'dir': -1},
        'targets': [{'label': 'Minute disc', 'arbor': 'minute', 'period': 3600, 'dir': -1}, {'label': 'Hour disc', 'arbor': 'hour', 'period': 43200, 'dir': -1}],
        'arbors': arbors, 'hands': hands, 'stages': {'s_mi': ['inter_wheel', 'minute_pinion'], 's_ih': ['hour_wheel', 'inter_pinion']},
        'plate': {'name': 'Bench', 'z': -6, 'role': 'Just the bench; the main plate comes next, once the layout is agreed.'},
        'defaults': {'movementD': 56, 'minGap': 0.15, 'zMax': 14, 'view': {'height': 16, 'mid': 3},
                     'stages': {'s_mi': {'m': m, 'z': L1}, 's_ih': {'m': m, 'z': L2}}, 'pos': pos, 'fits': FITS,
                     'hands': {'hour_disc': {'length': disc_r, 'z': disc_z, 't': GEAR_T}, 'minute_disc': {'length': disc_r, 'z': disc_z, 't': GEAR_T}},
                     'locks': {'minute_pinion': True, 'inter_wheel': True, 'inter_pinion': True, 'hour_wheel': True, 'hour_disc': True, 'minute_disc': True}},
    }
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS}
    return scene(project, state), {'I': I_, 'worm_y': yw, 'worm_z': zw}

if __name__ == '__main__':
    s1, pairs, WH = size_study()
    json.dump(s1, open(os.path.join(OUT, 'air-size-study.json'), 'w'), indent=1)
    s2, info = beta2()
    json.dump(s2, open(os.path.join(OUT, 'beta2.json'), 'w'), indent=1)
    print('size study plates %.1f x %.1f mm;' % WH, '; '.join(f"m{p['m']}: {p['zp']}/{p['zw']} at CD {p['a']:g}" for p in pairs))
    print('beta2:', info)
