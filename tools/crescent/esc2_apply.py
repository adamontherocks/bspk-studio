# Puts escapement version 2 (escapement2.py -> escapement2_geo.json) into a Crescent scene: the escape wheel with flat tooth tips,
# the beefed-up fork whose shaft stops short of the balance staff with the Ø1.5 pin on the near side, the roller with its slot facing
# the fork (3 mm thick, pressed on the staff), the pin, and the fork and balance tables. The slip clutch is the escape wheel: it rides
# on a Ø3 brass bush pressed onto its arbor, a reamed friction fit, so cranking the train fast slips the wheel on its arbor and caps
# the force on every part of the escapement (teeth, noses, fork, pin, roller, balance). (2026-11-18: first put at the roller, which
# only protected the balance; moved after Adam asked.)
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
def circ(c, r, n): return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
def slot_pts(c, u, r0, r1, w, n=10):
    a_ = (c[0] + u[0] * (r0 + w / 2), c[1] + u[1] * (r0 + w / 2)); b_ = (c[0] + u[0] * (r1 - w / 2), c[1] + u[1] * (r1 - w / 2))
    ang = math.atan2(u[1], u[0]); pts = []
    for j in range(n + 1): t = ang - math.pi / 2 + math.pi * j / n; pts.append((b_[0] + w / 2 * math.cos(t), b_[1] + w / 2 * math.sin(t)))
    for j in range(n + 1): t = ang + math.pi / 2 + math.pi * j / n; pts.append((a_[0] + w / 2 * math.cos(t), a_[1] + w / 2 * math.sin(t)))
    return pts
def egg(c, R, u, s_end, r_end, n=96):
    """the convex hull of the roller's circle and a circle round its slot's outer end: an egg, beefy where the pin works (P30)"""
    pts = circ(c, R, n) + circ((c[0] + u[0] * s_end, c[1] + u[1] * s_end), r_end, n)
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p_ in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0: lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p_) <= 0: hi.pop()
        hi.append(p_)
    return lo[:-1] + hi[:-1]
def sharp(pts): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in pts]
def apply(J, log):
    EG = json.load(open(os.path.join(HERE, 'escapement2_geo.json')))
    st, pr = J['state'], J['project']; mech = pr['mechanisms']; SK = {k['id']: k for k in st['sketches']}
    by_axis = {}
    for d in st['drawn']:
        mt = mech['mounts'].get(d['id'])
        if mt and mt.get('axis') in ('escape', 'fork', 'balance'): by_axis.setdefault(mt['axis'], []).append(d)
    wheel = next(d for d in by_axis['escape'] if d['name'].startswith('Escape wheel'))
    fork = next(d for d in by_axis['fork'] if d['name'].startswith('Pallet fork'))
    pin = next(d for d in by_axis['fork'] if d['name'].startswith('Impulse pin'))
    roller = next(d for d in by_axis['balance'] if d['name'].startswith('Roller'))
    E, F, Bc, P0 = EG['E'], EG['F'], EG['Bc'], EG['P0']
    T, Z_ESC = EG['T_ESC'], SK[wheel['sketch']]['plane']['offset']
    SK[wheel['sketch']]['points'] = sharp([(E[0] + x, E[1] + y) for x, y in EG['wheel_local']]); wheel['thickness'] = T
    rt, rd = EG['check'].get('tip_radius_mm', 0), EG['check'].get('dropoff_radius_mm', 0)
    rr, rv = EG['check'].get('root_r_mm', 0), EG['check'].get('valley_radius_mm', 0)
    tips = f'rounded tips: crest r {rt:g} like the fork\'s noses, drop-off r {rd:g}' if rt else 'flat tips'
    if rt and rv: tips = f'short teeth with round tops r {rt:g} like the fork\'s noses, valleys at r {rr:g} rounded r {rv:g}'
    wheel['name'] = f'Escape wheel (15 ramp teeth, {tips}; friction-driven on its arbor: the slip clutch)'
    for c in wheel['cuts']:
        if c['kind'] == 'hole' and c['name'].startswith('Bore'):
            c['d'] = 3.0; c['name'] = 'Bore on a Ø3 brass bush pressed on the arbor (a reamed friction fit: the slip clutch)'
    SK[fork['sketch']]['points'] = sharp(EG['fork']); fork['thickness'] = T
    fork['name'] = 'Pallet fork (two noses; its 4 mm shaft stops short of the balance staff and carries the impulse pin)'
    dead = [c['sketch'] for c in fork['cuts'] if c['kind'] == 'pocket']
    fork['cuts'] = [c for c in fork['cuts'] if c['kind'] != 'pocket']
    for c in fork['cuts']:
        if c['name'].startswith('Impulse pin'): c['at'] = [round(P0[0], 4), round(P0[1], 4)]; c['d'] = 2 * EG['PIN_R']; c['name'] = f'Impulse pin (Ø{2 * EG["PIN_R"]:g} steel, pressed)'
    st['sketches'] = [k for k in st['sketches'] if k['id'] not in dead]
    z_roll = Z_ESC + T + 0.2
    S_END = EG['SLOT_R1'] - EG['SLOT_W'] / 2; R_END = EG['SLOT_W'] / 2 + 2.0              # 2 mm of Delrin all round the slot's working end
    SK[roller['sketch']]['points'] = sharp(egg(Bc, EG['ROLLER_R'], EG['u_slot'], S_END, R_END)); SK[roller['sketch']]['plane']['offset'] = round(z_roll, 4); roller['thickness'] = EG['T_ROLL']
    roller['name'] = 'Roller (egg-shaped, pressed on the balance staff; 2 mm of wall round the closed slot the impulse pin runs in)'
    for c in roller['cuts']:
        if c['kind'] == 'pocket': SK[c['sketch']]['points'] = sharp(slot_pts(Bc, EG['u_slot'], EG['SLOT_R0'], EG['SLOT_R1'], EG['SLOT_W']))
        if c['kind'] == 'hole' and c['name'].startswith('Staff'): c['name'] = 'Staff (pressed)'
    SK[pin['sketch']]['points'] = sharp(circ(P0, EG['PIN_R'], 24)); pin['thickness'] = round(z_roll + EG['T_ROLL'] - 0.2 - Z_ESC, 4)
    pin['name'] = f'Impulse pin (Ø{2 * EG["PIN_R"]:g} steel, pressed in the fork\'s shaft, runs in the roller\'s slot)'
    for l in mech['links']:
        if l.get('kind') == 'table' and l['arbor'] == 'fork': l['values'] = EG['fork_table']
        if l.get('kind') == 'table' and l['arbor'] == 'balance': l['values'] = EG['balance_table']; l['label'] = 'Balance swung by the impulse pin in the roller\'s slot (escapement2.py)'
    for a in pr.get('arbors', []):
        if a['id'] == 'fork': a['role'] = (f'Rocked ±{EG["check"]["fork_swing_deg"][1]:.1f}° by the escape wheel: one nose lifted turns it one way, the other turns it back, with a rest '
                                         'between (it never locks). Its 4 mm shaft stops short of the balance staff; the Ø1.5 steel pin at its end runs in the roller\'s closed slot.')
        if a['id'] == 'balance': a['role'] = (f'Ø34 balance in a well under the crescent\'s cock. The fork\'s pin runs in its roller\'s closed slot, so it swings ±{EG["check"]["balance_swing_deg"]:.0f}° '
                                            'every beat. No hairspring: it is driven, it doesn\'t regulate.')
        if a['id'] == 'escape': a['role'] = ('Turns once every 20 s with the train (3 × the seconds wheel). Its wheel has 15 ramp teeth with round tips that lift the pallet fork\'s two noses in turn: '
                                           '30 beats a turn, 1.5 a second. The wheel is the slip clutch: it rides on a Ø3 brass bush on its arbor (a reamed friction fit), so when the crown cranks '
                                           'the train fast (one crown turn is about 112 beats) it slips instead of hammering the fork and balance. No lock, so the train never stalls.')
    c = EG['check']
    for pf in mech.get('proofs', []):
        if pf.get('label', '').startswith('Escapement'):
            pf['by'] = 'escapement2.py'
            pf['text'] = (f'in 0.02° steps over a full turn the fork never jams (tightest play {c["narrowest_band_deg"]:.1f}°), every tooth lifts both noses, '
                          f'the fork swings ±{c["fork_swing_deg"][1]:.1f}° and rests {c["rests_fraction"] * 100:.0f} % of the time, and no part of it cuts into the wheel. '
                          f'Its 4 mm shaft stops {c["shaft_clears_staff_mm"]:.2f} mm short of the balance staff; the Ø{2 * EG["PIN_R"]:g} pin on its near side runs in the roller\'s closed slot, '
                          f'so the balance swings ±{c["balance_swing_deg"]:.0f}° and the pin can never leave. Noses r {EG["R_N"]}, tooth tips {"rounded (crest r " + format(c.get("tip_radius_mm", 0), "g") + ", drop-off r " + format(c.get("dropoff_radius_mm", 0), "g") + ")" if c.get("tip_radius_mm") else "flat"}, ramp push angle {c["ramp_pressure_angle_deg"]}°. '
                          f'The escape wheel is friction-driven on its arbor (the slip clutch), so cranking fast slips it instead of hammering the escapement')
            pf['ok'] = bool(c['jams_in_a_full_turn'] == 0 and c['pin_captive'] and c['fork_outline_deepest_cut_mm'] < 0.02)
    log.append(f'escapement 2: pin on the near side ({EG["D0"]} short of the staff, Ø{2 * EG["PIN_R"]:g}); fork shaft {2 * EG["TAIL_R"]:.1f} wide, noses r {EG["R_N"]}, fork and wheel {T} thick, '
               f'roller {EG["T_ROLL"]} thick r {EG["ROLLER_R"]:.2f}; fork ±{c["fork_swing_deg"][1]:.2f}°, balance ±{c["balance_swing_deg"]:.1f}°, jams {c["jams_in_a_full_turn"]}, '
               f'narrowest play {c["narrowest_band_deg"]}°, shaft clears the staff by {c["shaft_clears_staff_mm"]} mm, deepest cut into the wheel {c["fork_outline_deepest_cut_mm"]} mm')
