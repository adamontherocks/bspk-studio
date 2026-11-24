# Beta 2 · fit coupon (2026-11-24): cut this before the 3/8" main plate. Every fit in Beta 2 · layered is a placeholder; one small 1/8"
# black delrin plate tries each at a few sizes, read left to right, smallest first (the notch is top left):
#   - bearing bores for the 3 x 6 x 2.5 flanged bearing (each with its Ø7.3 x 0.65 flange seat)
#   - a 3 mm brass rod pressed in (a gear on its rod) and turning free (a plain delrin bushing or pivot)
#   - M2 tap holes (hand taper tap) and M2 clearance holes
#   - three wells with a 1/16" plug each, 0.05, 0.10 and 0.15 a side (how a plate sits in the one under it)
#   - a module 0.6 pinion 12 / wheel 18 (Beta 2's minute pinion and transfer wheel) and three holes for the wheel, at the exact
#     centre distance and opened 0.07 and 0.14 (about 0.05 and 0.10 of backlash): the one that runs clean sets rules.backlash
import math

T8, T16 = 3.175, 1.5875
M, ZP, ZW = 0.6, 12, 18
A0 = M * (ZP + ZW) / 2                      # 9.0: the exact centre distance (shifts +0.3 / -0.3)
TAN = math.tan(math.radians(20))

def build(h):
    rrect, sketch, poly_dots = h['rrect'], h['sketch'], h['poly_dots']
    from shapely.geometry import Point
    W, H = 64.0, 46.0
    cuts, hid = [], [1]
    def hole(kind, name, at, d, seat=None, axis=None):
        c = {'id': f'h{hid[0]}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': 'back', 'depth': None}
        if seat: c['seat'] = seat
        if axis: c['axis'] = axis
        cuts.append(c); hid[0] += 1
    for x, d in zip((-24, -12, 0, 12, 24), (5.94, 5.96, 5.98, 6.00, 6.02)):
        hole('bearing', f'Bearing bore Ø{d:.2f} (flanged 3 x 6 x 2.5; Beta 2 uses 5.98)', (x, 15), d, seat={'d': 7.3, 'depth': 0.65})
    for x, d in zip((-26, -20, -14, -8), (2.90, 2.93, 2.96, 2.99)):
        hole('rod', f'Rod pressed in Ø{d:.2f} (a gear on its 3 mm rod; Beta 2 uses 2.96)', (x, 5), d)
    for x, d in zip((0, 6, 12), (3.04, 3.08, 3.12)):
        hole('rod', f'Rod turning Ø{d:.2f} (a plain bushing or pivot; Beta 2 uses 3.08)', (x, 5), d)
    for x, d in zip((-26, -21, -16), (1.5, 1.6, 1.7)):
        hole('pilot', f'M2 tap hole Ø{d:.1f} (Beta 2 uses 1.6)', (x, -3), d)
    for x, d in zip((-9, -4, 1), (2.2, 2.3, 2.4)):
        hole('clear', f'M2 clearance Ø{d:.1f} (Beta 2 uses 2.3)', (x, -3), d)
    P0 = (24.0, -15.0)
    hole('rod', 'Gear test: the pinion\'s rod (Ø3.08, turning)', P0, 3.08, axis='fp')
    wheel_at = {}
    for ang, da in ((90, 0.0), (120, 0.07), (150, 0.14)):          # (the exact one straight above the pinion, so its centre distance is exact)
        a = A0 + da; q = (P0[0], P0[1] + a) if ang == 90 else (P0[0] + a * math.cos(math.radians(ang)), P0[1] + a * math.sin(math.radians(ang)))
        wheel_at[da] = q
        hole('rod', f'Gear test: the wheel\'s rod at centre distance {a:.2f} (about {2 * da * TAN:.2f} of backlash)', q, 3.08, axis='fw' if da == 0 else None)
    # the notch (orientation: top left) and the three wells
    sk = [sketch('K1', 'Fit coupon outline', 'z', 0.0, rrect(0, 0, W, H, 3.0)),
          sketch('K2', 'Notch (top left: read every row from here)', 'z', 0.0, poly_dots(Point(-W / 2 + 6, H / 2).buffer(1.5, 64)))]
    cuts.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': 'Notch (top left)', 'sketch': 'K2', 'from': 'back', 'depth': None}); hid[0] += 1
    drawn = []
    well = lambda cx: rrect(cx, -14.0, 8.2, 8.2, 1.2)
    for i, (cx, c) in enumerate(zip((-24, -12, 0), (0.05, 0.10, 0.15))):
        kw, kp = f'K{3 + 2 * i}', f'K{4 + 2 * i}'
        sk.append(sketch(kw, f'Well {i + 1} (8.2 square, r 1.2 corners)', 'z', 0.0, well(cx)))
        cuts.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': f'Well {i + 1}: its plug {c:.2f} a side smaller', 'sketch': kw, 'from': 'back', 'depth': 1.0}); hid[0] += 1
        plug = rrect(cx, -14.0, 8.2 - 2 * c, 8.2 - 2 * c, 1.2 - c)
        sk.append(sketch(kp, f'Plug {i + 1} ({c:.2f} a side)', 'z', T8 - 1.0, plug))
        drawn.append({'id': f'D{2 + i}', 'name': f'Plug {i + 1} (1/16" black delrin): {c:.2f} a side in well {i + 1}, the fit of a plate in the one under it ({"Beta 2 uses 0.10" if c == 0.10 else "try"})',
                      'sketch': kp, 'thickness': T16, 'grow': 'plus', 'mill': 'back', 'minWall': 0.6, 'cuts': []})
    drawn.insert(0, {'id': 'D1', 'name': 'Fit coupon (1/8" black delrin, milled from the top): every Beta 2 fit at a few sizes, smallest first from the notch',
                     'sketch': 'K1', 'thickness': T8, 'grow': 'plus', 'mill': 'back', 'minWall': 0.6, 'cuts': cuts})
    pos = {'fp': list(P0), 'fw': [round(wheel_at[0.0][0], 4), round(wheel_at[0.0][1], 4)]}
    arbors = [{'id': 'fp', 'name': 'Test pinion', 'group': 'pair', 'level': 0, 'role': f'{ZP} teeth, module {M}, shift +0.3 (Beta 2\'s minute pinion), pressed on a 3 mm rod turning in the coupon.',
               'gears': [{'id': 'fp_g', 'label': f'Pinion {ZP} · m{M}', 'z': ZP, 't': T16, 'x': 0.3, 'bore': 'rod_press'}]},
              {'id': 'fw', 'name': 'Test wheel', 'group': 'pair', 'level': 1, 'role': f'{ZW} teeth, module {M}, shift -0.3 (Beta 2\'s transfer wheel). Move its rod between the three holes; the hole where the pair turns clean without rattle sets the backlash.',
               'gears': [{'id': 'fw_g', 'label': f'Wheel {ZW} · m{M}', 'z': ZW, 't': T16, 'x': -0.3, 'bore': 'rod_press', 'arms': 0}]}]
    FITS = h['FITS_DELRIN']
    project = {
        'format': 'bspk-studio-project', 'id': 'beta2-fits', 'name': 'Beta 2 · fit coupon', 'title': 'Beta 2 · fit coupon: cut this first',
        'blurb': ('One 1/8" black delrin plate that tries every Beta 2 fit at a few sizes before the 3/8" main plate gets cut: bearing bores, a rod pressed in and turning, '
                  'M2 tap and clearance holes, three wells with 1/16" plugs (0.05, 0.10 and 0.15 a side), and Beta 2\'s minute pinion and transfer wheel with three holes for the wheel '
                  '(exact centre distance, then about 0.05 and 0.10 of backlash). Read each row from the notch, smallest first; the sizes that fit go into the fits table and rules.backlash.'),
        'source': ['Claude, 2026-11-24, from the fine-tooth review of Beta 2 · layered: every fit was a placeholder.'],
        'groups': {'pair': 'Gear test'}, 'focus': [{'id': 'pair', 'label': f'Gear test: pinion {ZP} / wheel {ZW}, module {M}', 'parts': ['fp', 'fw']}],
        'rules': {'minModule': M, 'fixedModule': True, 'why': 'Beta 2\'s module', 'arms': {'rim': 1.0, 'arm': 0.8, 'hubWall': 1.2}},
        'shop': {'machine': 'Makera Carvera Air', 'cutter': 0.5, 'note': 'black delrin; the sizes here are what the coupon tests'},
        'rate': {'arbor': 'fp', 'period': 60, 'dir': -1}, 'targets': [], 'arbors': arbors, 'hands': [], 'stages': {'sfit': ['fw_g', 'fp_g']},
        'plate': {'name': 'Bench', 'z': -0.5, 'role': 'Just the bench under the coupon.'},
        'defaults': {'movementD': 76, 'minGap': 0.2, 'zMax': 8, 'view': {'height': 8, 'mid': 2.0}, 'stages': {'sfit': {'m': M, 'z': round(T8 + 0.2, 4)}}, 'pos': pos, 'fits': FITS,
                     'locks': {'fp_g': True, 'fw_g': True}},
    }
    state = {'pos': pos, 'sketches': sk, 'drawn': drawn, 'fits': FITS}
    return {'format': 'bspk-studio-scene', 'version': 3, 'state': state, 'project': project}
