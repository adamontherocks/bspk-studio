import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outline import outline as case_outline
lay = json.load(open(sys.argv[1]))
W = lay['world']
S = 2.5
C, H = [10.5 * S, 0.0], [-10.5 * S, 0.0]
# 2026-11-12 check: at 16.4 mm and module 0.4 the barrel's teeth reached 3.3 mm past the Slava's own Ø55.8 outline.
# Same direction, module 0.33, 72/10: 13.53 mm from the center arbor, tip radius 12.21, 2.2 mm inside the outline. Still an estimate.
BARREL_M = 0.33
BARREL_A = BARREL_M * (72 + 10) / 2
_fb = lay['frame']['sl_barrel']; _s = BARREL_A / math.hypot(*_fb); _fb = (_fb[0] * _s, _fb[1] * _s)
_cr, _sr = math.cos(lay['rot']), math.sin(lay['rot'])
W['sl_barrel'] = [C[0] + _fb[0] * _cr - _fb[1] * _sr, C[1] + _fb[0] * _sr + _fb[1] * _cr]
d, a, b = math.dist(C, H), 30.0, 28.0
along = (a * a - b * b + d * d) / (2 * d); up = math.sqrt(a * a - along * along)
M = [C[0] - along, C[1] + up]
P, Wsh = 0.3, -0.3
def g(id, label, z, t, x=0, **k):
    return {'id': id, 'label': label, 'z': z, 't': t, **({'x': x} if x else {}), **k}
def sl(id, label, z, t, **k):   # a Slava (bought) gear; size estimated unless confirmed
    return g(id, label, z, t, bought=True, estimate=k.pop('estimate', True), **k)
DZ = 4.0          # back of the Slava (balance cock side), sitting on the main plate P1 (4 mm)
PLATES = [('P1', 'P1 main plate / back', 4.0, '1/4" faced'), ('P2', 'P2 Slava plate, lower', 9.525, '3/8"'), ('P3', 'P3 Slava plate, upper', 9.525, '3/8"'),
          ('P4', 'P4 support plate', 3.0, '1/4" faced'), ('P5', 'P5 motion plate', 3.3, '1/4" faced'), ('P6', 'P6 top plate', 6.35, '1/4"')]
Z, z = {}, 0.0
for pid, _, t, _ in PLATES: Z[pid] = round(z, 4); z += t
TOP = round(z, 4)   # 35.7
FP = 19.5         # our front plate starts here (Slava is 19 mm deep)
LAY = lambda n: round(FP + 3.3 * n, 4)   # our layers above the front plate: n = 1 motion works, 2 motion works, 3 discs
project = {
  'format': 'bspk-studio-project', 'id': 'hemistitch-slava', 'name': 'Hemistitch + Slava donor',
  'title': 'Hemistitch · Slava 5671 engine',
  'blurb': 'Phase 1 of the fully mechanical plan: a Slava 5671 alarm-clock movement (Swiss lever, 18,000 beats an hour) is the engine. Its barrel, train, escapement and balance stay in its own plates; we tap its center arbor for our motion works and the two discs. Slava parts are bought, and their sizes are estimates from the 1987 factory manual until the clock arrives. Our parts are module 1 in 2.8 mm acrylic.',
  'source': ['Slava 5671: Shamonova, Repair of Mechanical Alarm Clocks (1987): 55.8 mm, 19 mm deep, 11 jewels, free (Swiss) lever, 15-tooth escape wheel, brass balance with a 0.4 s period, both springs in barrels, 36 h per wind, friction cannon pinion on the center arbor. Arbor positions are scaled from its Fig. 1 drawing; tooth counts and the balance diameter are guesses, to measure on the real one. Discs and motion works: VISION §10.8.'],
  'groups': {'donor': 'Slava engine (bought)', 'motion': 'Motion works', 'discs': 'Discs'},
  'focus': [
    {'id': 'donor', 'label': 'Slava engine: barrel → center → third → seconds → escape → balance', 'parts': ['sl_barrel', 'center', 'sl_third', 'sl_fourth', 'sl_escape', 'sl_fork', 'sl_balance']},
    {'id': 'motion', 'label': 'Motion works and discs: center → minute wheel → hour wheel', 'parts': ['center', 'mwheel', 'hour', 'minute_disc', 'hour_disc']},
  ],
  'rules': {'minModule': 1, 'fixedModule': True, 'why': 'the 1 mm end mill has to fit between the pinion teeth'},
  'rate': {'arbor': 'center', 'period': 3600, 'dir': -1},
  'targets': [
    {'label': 'Minute disc', 'arbor': 'center', 'period': 3600, 'dir': -1},
    {'label': 'Hour disc', 'arbor': 'hour', 'period': 43200, 'dir': -1},
    {'label': 'Seconds wheel (Slava)', 'arbor': 'sl_fourth', 'period': 60, 'dir': -1},
    {'label': 'Escape wheel (Slava, 18,000 bph)', 'arbor': 'sl_escape', 'period': 6, 'dir': 1},
  ],
  'beat': {'gear': 'sl_escape_wheel', 'label': 'Escape wheel (Slava)'},
  'arbors': [
    {'id': 'sl_barrel', 'name': 'Slava going barrel', 'group': 'donor', 'level': 0, 'staticArbor': True, 'drumH': 4.0,
     'role': 'Bought (Slava). The mainspring (2.9 × 0.2 × 611 mm) in a closed barrel, inside about Ø20.8; at least 36 hours per wind. Drives the center pinion. Position, tooth count and size are estimates (about 13.5 mm from the center arbor, so its teeth stay inside the movement’s Ø55.8); measure the real one.',
     'gears': [sl('sl_barrel_teeth', 'Barrel teeth (Slava)', 72, 0.6)]},
    {'id': 'center', 'name': 'Center arbor', 'group': 'donor', 'level': 1,
     'role': 'The Slava’s center arbor: turns once an hour. Inside the Slava its pinion is driven by the barrel and its wheel drives the third wheel. Above the Slava our transfer tube (3 mm OD brass, in bearings in P4 and P6) slips over it and grips it by friction, so you can still set the time. The tube carries our module-1 transfer gear in P5, which drives the minute wheel, and the minute disc on top.',
     'gears': [sl('sl_center_pinion', 'Center pinion (Slava)', 10, 1.0), sl('sl_center_wheel', 'Center wheel (Slava)', 60, 0.4),
               g('cannon_pinion', 'Transfer gear (ours)', 12, 2.8, P)]},
    {'id': 'sl_third', 'name': 'Third wheel (Slava)', 'group': 'donor', 'level': 2,
     'role': 'Bought (Slava): the intermediate wheel. Position scaled from the manual’s drawing; tooth counts are guesses.',
     'gears': [sl('sl_third_pinion', 'Third pinion (Slava)', 8, 0.8), sl('sl_third_wheel', 'Third wheel (Slava)', 64, 0.4)]},
    {'id': 'sl_fourth', 'name': 'Seconds wheel (Slava)', 'group': 'donor', 'level': 3,
     'role': 'Bought (Slava): turns once a minute and drives the escape pinion. Tooth counts are guesses.',
     'gears': [sl('sl_fourth_pinion', 'Seconds pinion (Slava)', 8, 0.8), sl('sl_fourth_wheel', 'Seconds wheel (Slava)', 60, 0.3)]},
    {'id': 'sl_escape', 'name': 'Escape wheel (Slava)', 'group': 'donor', 'level': 4,
     'role': 'Bought (Slava): 15 club teeth (confirmed), jeweled pivots. At 18,000 beats an hour it turns every 6 seconds, released half a tooth per beat. Size estimated.',
     'gears': [sl('sl_escape_pinion', 'Escape pinion (Slava)', 6, 0.6), sl('sl_escape_wheel', 'Escape wheel (Slava)', 15, 0.4)]},
    {'id': 'sl_fork', 'name': 'Pallet fork (Slava)', 'group': 'donor', 'level': 4,
     'role': 'Bought (Slava): the jeweled pallet fork, shown as the space it sweeps. Between the escape wheel and the balance, in line with both (Playtner’s proportions). It rocks each beat; the sim doesn’t animate that yet.',
     'gears': [sl('sl_fork_body', 'Pallet fork (its sweep)', 18, 0.5, plain=True)]},
    {'id': 'sl_balance', 'name': 'Balance (Slava)', 'group': 'donor', 'level': 4,
     'role': 'Bought (Slava): brass balance with its hairspring, a 0.4 s swing (18,000 beats an hour), under its own cock on the back: the beating heart behind the case-back window. About Ø15 and about 18 mm from the center arbor, both estimated from the manual’s drawing. It swings; the sim doesn’t animate that yet.',
     'gears': [sl('sl_balance_wheel', 'Balance wheel (Slava)', 30, 0.8, plain=True)]},
    {'id': 'mwheel', 'name': 'Minute wheel', 'group': 'motion', 'level': 5,
     'role': 'Ours. Its 3 mm rod turns in bearings in P4 and P6. The transfer gear turns its 48-tooth wheel 4:1 (in P5); its 14-leaf pinion turns the hour wheel 3:1 (in the pocket under P6), so 12:1 in all.',
     'gears': [g('minute_wheel', 'Minute wheel', 48, 2.8, Wsh), g('minute_pinion', 'Minute pinion', 14, 2.8, P)]},
    {'id': 'hour', 'name': 'Hour wheel', 'group': 'motion', 'level': 6,
     'role': 'Ours. Its 3 mm rod turns in bearings in P4 and P6; the wheel sits in the pocket under P6, turns once in 12 hours, and the hour disc is pressed on the rod above the top plate.',
     'gears': [g('hour_wheel', 'Hour wheel', 42, 2.8, Wsh)]},
  ],
  'hands': [
    {'id': 'minute_disc', 'name': 'Minute disc', 'arbor': 'center', 'group': 'discs', 'level': 7, 'shape': 'disc', 'marks': 60,
     'labels': [str(5 * k) for k in range(12)], 'indicator': 0,
     'role': 'Ours: 2.8 mm acrylic, Ø47.5, on the transfer tube 0.5 mm above the top plate. One turn an hour; the minutes pass the index at 3 o’clock.'},
    {'id': 'hour_disc', 'name': 'Hour disc', 'arbor': 'hour', 'group': 'discs', 'level': 7, 'shape': 'disc', 'marks': 12,
     'labels': ['12'] + [str(k) for k in range(1, 12)], 'indicator': 0,
     'role': 'Ours: 2.8 mm acrylic, Ø47.5, fixed on top of the hour wheel. One number passes the index at 3 o’clock each hour.'},
  ],
  'stages': {
    's_barrel': ['sl_barrel_teeth', 'sl_center_pinion'], 's_center': ['sl_center_wheel', 'sl_third_pinion'],
    's_third': ['sl_third_wheel', 'sl_fourth_pinion'], 's_fourth': ['sl_fourth_wheel', 'sl_escape_pinion'],
    's_minute': ['cannon_pinion', 'minute_wheel'], 's_hour': ['minute_pinion', 'hour_wheel'],
  },
  'plate': {'name': 'Work surface',
            'role': 'Just the ground under the model; the movement’s real plates are the six drawn parts P1–P6. Yellow outlines: the AXIS case grown 2.5× with its top and bottom bow deepened to 4.25 mm (reference), and the Slava movement’s Ø55.8 footprint at its back and its front (estimated position: rotated so its balance points at the case’s center line).'},
  'defaults': {
    'movementD': 150, 'minGap': 0.5, 'zMax': 40, 'view': {'height': 34, 'mid': 15},
    'stages': {'s_barrel': {'m': BARREL_M, 'z': DZ + 8.0}, 's_center': {'m': 0.3, 'z': DZ + 6.8}, 's_third': {'m': 0.25, 'z': DZ + 5.6}, 's_fourth': {'m': 0.2, 'z': DZ + 4.5},
               's_minute': {'m': 1, 'z': Z['P5'] + 0.25}, 's_hour': {'m': 1, 'z': Z['P6'] + 0.25}},
    'solo': {'sl_escape_wheel': {'m': 0.45, 'z': DZ + 3.4}, 'sl_fork_body': {'m': 0.5, 'z': DZ + 2.4}, 'sl_balance_wheel': {'m': 0.5, 'z': DZ + 1.0}},
    'pos': {'center': C, 'sl_barrel': W['sl_barrel'], 'sl_third': W['sl_third'], 'sl_fourth': W['sl_fourth'], 'sl_escape': W['sl_escape'],
            'sl_fork': W['sl_fork'], 'sl_balance': W['sl_balance'], 'mwheel': M, 'hour': H},
    'hands': {'minute_disc': {'length': 9.5 * S, 'z': TOP + 0.5, 't': 2.8}, 'hour_disc': {'length': 9.5 * S, 'z': TOP + 0.5, 't': 2.8}},
    'locks': {'minute_disc': True, 'hour_disc': True, 'sl_barrel_teeth': True, 'sl_center_wheel': True, 'sl_third_wheel': True,
              'sl_fourth_wheel': True, 'sl_escape_wheel': True, 'sl_fork_body': True, 'sl_balance_wheel': True},
  },
}
# Case outline (outline.py): straight sides, r 10 corners, top and bottom bows (4.25 deep, deepened 2026-11-11) tangent to the corners.
# 80 evenly spaced smooth dots: the sim's spline then stays within 0.03 mm of that shape (the old 14 dots strayed up to 1.2 mm).
case, _ = case_outline(20)
circle = [{'u': round(C[0] + 27.9 * math.cos(2 * math.pi * k / 16), 4), 'v': round(C[1] + 27.9 * math.sin(2 * math.pi * k / 16), 4), 'smooth': True} for k in range(16)]
# ---- the six plates: cuts from the layer plan (front = a plate's bottom face, back = its top face) ----
SCR = {'A': [(-55.5, 29), (-55.5, -29), (-20, 34), (-20, -34), (55.5, 29), (55.5, -29)],     # P1 into P2, from the case back
       'B': [(-57, 0), (-40, 32), (-40, -32), (0, -35.5), (40, 31.5), (40, -31.5)],               # P3 into P2
       'C': [(-55.5, 29), (-55.5, -29), (-20, -34), (20, -34), (55.5, 29), (55.5, -29)]}     # P6, P5, P4 into P3
DOWELS = [(-46, 22), (48, -28)]
ALARM_KEY = [18.25, 11.3]   # alarm winding square: estimated from the manual's drawing (not an arbor in the model)
WINDOW_D, KEY_D = 25, 8
# 2026-11-12 check: that estimate overlapped the balance window. Slide it straight away from the balance until 2 mm of acrylic is left between them.
_bx, _by = W['sl_balance']; _dx, _dy = ALARM_KEY[0] - _bx, ALARM_KEY[1] - _by; _L = math.hypot(_dx, _dy); _want = WINDOW_D / 2 + KEY_D / 2 + 2.0
ALARM_KEY = [round(_bx + _dx / _L * _want, 3), round(_by + _dy / _L * _want, 3)]
def cut(kind, name, d=None, at=None, axis=None, depth=None, frm='front', seat=None, csk=None):
    c = {'kind': kind, 'name': name, 'from': frm, 'depth': depth, 'seat': seat, 'csk': csk}
    if at is not None: c['at'] = list(at)
    if axis: c['axis'] = axis; c['at'] = list({'center': C, 'mwheel': M, 'hour': H, 'sl_balance': W['sl_balance'], 'sl_barrel': W['sl_barrel']}[axis])
    if d is not None: c['d'] = d
    return c
BEARING = dict(d=6.0, depth=2.5, seat={'d': 7.2, 'depth': 0.6})
CLR = 0.75   # pocket clearance over the tooth tips: the 0.5 mm gap rule plus 0.25 for machining (±0.15)
pocket_d = lambda z, x: round(2 * (z / 2 + 1 + x + CLR), 3)   # module 1, profile shift x
def screws(s, how):
    out = []
    for i, p in enumerate(SCR[s]):
        if how == 'csk-front': out.append(cut('screw', f'Screw {s}{i + 1} · M3 countersunk', 3.4, p, frm='front', csk={'d': 6.3}))
        elif how == 'csk-back': out.append(cut('screw', f'Screw {s}{i + 1} · M3 countersunk', 3.4, p, frm='back', csk={'d': 6.3}))
        elif how == 'clear': out.append(cut('hole', f'Screw {s}{i + 1} · clearance', 3.4, p))
        elif how == 'pilot-through': out.append(cut('pilot', f'Screw {s}{i + 1} · pilot (through)', 2.5, p))
        elif how.startswith('pilot'): out.append(cut('pilot', f'Screw {s}{i + 1} · pilot', 2.5, p, depth=6.5, frm=how.split('-')[1]))
    return out
dowels = lambda: [cut('dowel', f'Dowel {i + 1}', 3.0, p) for i, p in enumerate(DOWELS)]
CUTS = {
  'P1': [cut('window', 'Balance window (estimated position)', WINDOW_D, axis='sl_balance'),
         cut('hole', 'Winding key access · going barrel (estimated)', KEY_D, axis='sl_barrel'),
         cut('hole', 'Winding key access · alarm (estimated, kept 2 mm off the window)', KEY_D, ALARM_KEY)] + screws('A', 'csk-front') + dowels(),
  'P2': [cut('hole', 'Slava recess · Ø56.1 (55.8 + fit)', 56.1, axis='center')] + screws('A', 'pilot-through') + screws('B', 'pilot-through') + dowels(),
  'P3': [cut('hole', 'Slava recess · Ø56.1 (55.8 + fit)', 56.1, axis='center')] + screws('B', 'csk-back') + screws('C', 'pilot-back') + dowels(),
  'P4': [cut('bearing', 'Bearing · transfer tube (lower)', axis='center', frm='back', **BEARING),
         cut('clear', 'Slava center arbor clearance', 4.0, axis='center'),
         cut('bearing', 'Bearing · minute wheel arbor (lower)', axis='mwheel', frm='back', **BEARING),
         cut('bearing', 'Bearing · hour arbor (lower)', axis='hour', frm='back', **BEARING)] + screws('C', 'clear') + dowels(),
  'P5': [cut('hole', 'Minute wheel pocket (48 teeth, tips + 0.75)', pocket_d(48, Wsh), axis='mwheel'),
         cut('hole', 'Transfer gear pocket (12 teeth, tips + 0.75)', pocket_d(12, P), axis='center'),
         cut('clear', 'Hour arbor clearance', 4.0, axis='hour'),
         {'kind': 'pocket', 'name': 'Hour rod hole joined to the minute wheel pocket (no sliver)', 'sketch': 'K10', 'from': 'front', 'depth': None, 'seat': None, 'csk': None}]
        + screws('C', 'clear') + dowels(),
  'P6': [cut('hole', 'Hour wheel pocket (42 teeth, tips + 0.75)', pocket_d(42, Wsh), axis='hour', depth=3.3, frm='front'),
         cut('hole', 'Minute pinion pocket (14 leaves, tips + 0.75)', pocket_d(14, P), axis='mwheel', depth=3.3, frm='front'),
         cut('bearing', 'Bearing · transfer tube (upper)', axis='center', frm='back', **BEARING),
         cut('bearing', 'Bearing · minute wheel arbor (upper)', axis='mwheel', frm='back', **BEARING),
         cut('bearing', 'Bearing · hour arbor (upper)', axis='hour', frm='back', **BEARING),
         cut('clear', 'Transfer tube clearance', 3.5, axis='center'),
         cut('clear', 'Minute wheel arbor clearance', 3.5, axis='mwheel'),
         cut('clear', 'Hour arbor clearance', 3.5, axis='hour')] + screws('C', 'csk-back') + dowels(),
}
_ux, _uy = M[0] - H[0], M[1] - H[1]; _L = math.hypot(_ux, _uy); _ux, _uy = _ux / _L, _uy / _L; _nx, _ny = -_uy, _ux
_w, _len = 1.99, 4.0   # just inside the Ø4 hole's 72-sided ring, so the two join without a step
BRIDGE = [{'u': round(H[0] + a * _ux + b * _nx, 4), 'v': round(H[1] + a * _uy + b * _ny, 4), 'smooth': False}
          for a, b in ((0, -_w), (_len, -_w), (_len, _w), (0, _w))]
DRAWN = []
for i, (pid, name, t, stock) in enumerate(PLATES):
    cuts = [{'id': f'h{j + 1}', **c} for j, c in enumerate(CUTS[pid])]
    DRAWN.append({'id': f'D{i + 1}', 'name': name, 'sketch': f'K{4 + i}', 'thickness': t, 'grow': 'plus', 'back': None, 'edges': None, 'cuts': cuts})
scene = {'format': 'bspk-studio-scene', 'version': 3, 'savedAt': '2026-11-12T00:00:00.000Z',
         'state': {'sketches': [
           {'id': 'K1', 'name': 'Case outline (AXIS × 2.5, bow 4.25, reference)', 'plane': {'axis': 'z', 'offset': 0}, 'closed': True, 'points': case},
           {'id': 'K2', 'name': 'Slava 5671 footprint, back (Ø55.8, estimated position)', 'plane': {'axis': 'z', 'offset': DZ}, 'closed': True, 'points': circle},
           {'id': 'K3', 'name': 'Slava 5671 footprint, front (19 mm deep)', 'plane': {'axis': 'z', 'offset': DZ + 19}, 'closed': True, 'points': [dict(p) for p in circle]}]
           + [{'id': f'K{4 + i}', 'name': f'{name} outline', 'plane': {'axis': 'z', 'offset': Z[pid]}, 'closed': True, 'points': [dict(p) for p in case]}
              for i, (pid, name, t, stock) in enumerate(PLATES)]
           + [{'id': 'K10', 'name': 'P5 hour rod slot (joins the minute wheel pocket)', 'plane': {'axis': 'z', 'offset': Z['P5']}, 'closed': True, 'points': BRIDGE}],
           'drawn': DRAWN},
         'project': project}
json.dump(scene, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print('barrel', [round(v, 3) for v in W['sl_barrel']], 'alarm key', ALARM_KEY, 'pockets P5', pocket_d(48, Wsh), pocket_d(12, P), 'P6', pocket_d(42, Wsh), pocket_d(14, P), 'case dots', len(case))
print('written; plates', Z, 'top', TOP, 'discs', TOP + 0.5, '-', TOP + 3.3, '; cuts per plate', {d['name']: len(d['cuts']) for d in DRAWN})
