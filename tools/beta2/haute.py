# Beta 2 · haute (2026-11-23): the aligned train's plates and bridges done the way Adam put it: "eloquent, not cheap ... no part should be
# cheap, everything is intentional". A thick main plate (3/8" black delrin) stepped from the top, a recess for every wheel at that
# wheel's own height; three bridges, each sunk in its own well at its own height; two top plates flush with the discs, windows wherever a
# wheel turns beneath, a channel down the centre line so both intermediates' rods and the centre bridge's twin arms show.
# build() takes the aligned scene (the train, positions, stem) and returns the haute scene plus a report; check() checks every part
# against every gear, rod, disc, the worm, the stem, every other part and every screw head, and runs before anything is written.
import copy, math
from shapely.geometry import Point, Polygon, LineString, box as sbox
from shapely.ops import unary_union

T38, TS, TT, GAP, ENDSHAKE = 9.525, 3.175, 1.5875, 0.3, 0.15
HEAD_R, HEAD_H = 1.9, 1.3                  # M2 pan head Ø3.8 x 1.3
BOSS = 1.15 + 0.5                          # an M2 clearance hole (Ø2.3) with 0.5 of delrin round it
TAP_SOLID = 0.8 + 0.4                      # an M2 tapped hole (Ø1.6) needs 0.4 of solid round it all the way down
m = 0.6
def ra(z, x): return m * z / 2 + m * (1 + x)

def pieces(g): return [] if g.is_empty else list(g.geoms) if g.geom_type in ('MultiPolygon', 'GeometryCollection') else [g]
def largest(g): return max(pieces(g), key=lambda p: p.area) if not g.is_empty else g
def smooth(g, ro=0.3, rc=0.6):
    """outside corners rounded to ro (anything narrower than 2 ro goes), inside corners filled to rc (the 0.5 end mill's reach)"""
    g = g.buffer(-ro, join_style=1).buffer(ro, join_style=1)
    return g.buffer(rc, join_style=1).buffer(-rc, join_style=1).buffer(0) if rc else g
def capsule(p, q, w): return LineString([p, q]).buffer(w / 2, cap_style=1)
def C(c, r, n=128): return Point(c).buffer(r, n)

def build(aligned_scene, info, helpers):
    rrect, sketch, poly_dots, FITS = helpers['rrect'], helpers['sketch'], helpers['poly_dots'], helpers['FITS_DELRIN']
    S = copy.deepcopy(aligned_scene)
    P, st = S['project'], S['state']
    M, H = (10.4, 0.0), (-10.4, 0.0)
    A1, A2, B, E = (tuple(info[k]) for k in ('A1', 'A2', 'B', 'E'))
    hz, zw = info['heights'], info['worm_axis']
    z_top = hz['disc']                     # the main plate's top face: the discs' underside (the top plates sit on it, flush with the discs)
    z_bot = z_top - T38
    HX, HY = 22.75, 16.2
    edge = HX
    # ---- the train's heights as the sim places them (stage z; a compound's wheel then its pinion; a stage pinion centred on its wheel + dz)
    dz_bp = -0.11                          # B's pinion 0.11 lower on A1's wheel (still its full face): room for the transfer bridge
    zA1w, zA2w, zHw, zBw = hz['a1w'], hz['a2w'], hz['hw'], 3.975
    TW = 1.2
    G = {   # name: (arbor, centre, tip radius, z0, z1)
        'transfer pinion': ('b', B, ra(11, .3), zA1w + TW / 2 - TT / 2 + dz_bp, zA1w + TW / 2 + TT / 2 + dz_bp),
        'first intermediate wheel': ('a1', A1, ra(22, -.3), zA1w, zA1w + TW),
        'first intermediate pinion': ('a1', A1, ra(11, .3), zA1w + TW, zA1w + TS),
        'second intermediate wheel': ('a2', A2, ra(22, -.3), zA2w, zA2w + TW),
        'second intermediate pinion': ('a2', A2, ra(13, .3), zA2w + TW, zA2w + TS),
        'hour wheel': ('hour', H, ra(26, -.3), zHw, zHw + TT),
        'transfer wheel': ('b', B, ra(18, -.3), zBw, zBw + TT),
        'minute pinion': ('minute', M, ra(12, .3), zBw + 0.3, zBw + 0.3 + TT),
        'crown arbor worm wheel': ('e', E, ra(15, .15), zw - TT / 2, zw + TT / 2),
        'crown arbor wheel': ('e', E, ra(18, -.3), zBw, zBw + TT)}
    discs = {'hour disc': ('hour', H, 9.5, z_top, z_top + TT), 'minute disc': ('minute', M, 9.5, z_top, z_top + TT)}
    arbor_at = {'minute': M, 'hour': H, 'a1': A1, 'a2': A2, 'b': B, 'e': E}
    names = {'a1': 'first intermediate', 'a2': 'second intermediate', 'hour': 'hour arbor', 'b': 'transfer arbor', 'minute': 'minute arbor', 'e': 'crown arbor'}
    # the stem: journals Ø1.8, the worm (Ø6.5) over wa..wb, out through the plate's edge to the crown. Its inner journal is 0.6 long here
    # (0.9 in the aligned build) so the stem's channel stops 0.6 short of the minute arbor's bushing
    wa, wb = E[0] - 2.5, E[0] + 2.5; x0 = wa - 0.6; jr = 0.9; wro = 3.25; xc = edge + 2.0
    solids = dict(G); solids.update(discs)
    things = [(n, a, C(c, r), z0, z1) for n, (a, c, r, z0, z1) in solids.items()]
    worm_plan = Polygon([(wa, -2.95), (wa + 0.3, -wro), (wb - 0.3, -wro), (wb, -2.95), (wb, 2.95), (wb - 0.3, wro), (wa + 0.3, wro), (wa, 2.95)])   # (its 0.3 chamfers)
    things.append(('worm', 'stem', worm_plan, zw - wro, zw + wro))
    things.append(('stem journals', 'stem', sbox(x0, -jr, xc, jr), zw - jr, zw + jr))
    outline_pts = rrect(0.0, 0.0, 2 * HX, 2 * HY, 4.0)
    outline = Polygon([(q['u'], q['v']) for q in outline_pts])

    # ---- bridges (1/16" black delrin, milled from the top, plain delrin pivots, M2 pan heads), each in its own well in the main plate
    zc = G['first intermediate pinion'][4] + GAP                 # centre bridge: over A1's pinion
    zb = G['transfer pinion'][4] + GAP                           # transfer bridge: between B's pinion and its wheel
    zr = zw + jr + 0.1                                           # crown bridge: 0.1 over the stem's journals (it holds the stem down)
    rod_top = {a: max(z1 for n, (aa, c, r, z0, z1) in solids.items() if aa == a) for a in arbor_at}
    rod_top['a1'] = max(rod_top['a1'], zc + TT)                  # A1's rod runs on up into the centre bridge
    for a, c in arbor_at.items(): things.append((f'{a} rod', a, C(c, 1.5, 48), z_bot, rod_top[a]))

    def keepout(z0, z1, skip_arbors=(), only=None, gap=GAP):
        zs = [g.buffer(gap, 64) for n, a, g, t0, t1 in things
              if a not in skip_arbors and (only is None or n in only) and t0 < z1 + gap - 1e-9 and t1 > z0 - gap + 1e-9]
        return unary_union(zs) if zs else Polygon()

    B_ = []
    # Centre bridge: A1's top pivot on the centre line, on twin arms running straight down the centre line to two feet at the edge
    feet_c = [(-2.0, -13.15), (2.0, -13.15)]          # (heads 0.3 clear of the transfer wheel; wells 1.0 inside the edge)
    cb = unary_union([C(A1, 2.9), *[capsule((sx * 1.75, A1[1] - 1.5), (sx * 1.75, -12.8), 1.5) for sx in (-1, 1)],
                      *[C(f, BOSS + 0.1) for f in feet_c], capsule(feet_c[0], feet_c[1], 1.6)])
    B_.append(dict(id='centre', z0=zc, arbors=['a1'], screws=feet_c, shape=cb,
                   name='Centre bridge (1/16" black delrin): the first intermediate\'s top pivot, on twin arms down the centre line'))
    # Transfer bridge: B's middle pivot (between its pinion and its wheel), two arms out to the bottom-right corner
    feet_t = [(16.0, -13.15), (19.7, -10.8)]
    tb = unary_union([C(B, 2.9), *[capsule(B, f, 1.6) for f in feet_t], *[C(f, BOSS + 0.1) for f in feet_t], capsule(feet_t[0], feet_t[1], 2.2)])
    B_.append(dict(id='transfer', z0=zb, arbors=['b'], screws=feet_t, shape=tb,
                   name='Transfer bridge (1/16" black delrin): the transfer arbor\'s middle pivot, under its wheel, two arms to the corner'))
    # Crown bridge: a frame round the worm (which rises through it). It holds both journals down and carries the crown arbor's middle pivot
    feet_r = [(16.6, -5.6), (21.0, -3.0)]
    win_r = sbox(wa - ENDSHAKE, -wro - GAP, wb + ENDSHAKE, wro + GAP)
    frame = sbox(M[0] + 1.5 + GAP + 0.01, -5.8, edge, 5.6).difference(win_r)
    rb = unary_union([frame, C(E, 2.9), capsule((wb + 1.2, 5.0), E, 2.4), *[C(f, BOSS + 0.1) for f in feet_r]])
    B_.append(dict(id='crown', z0=zr, arbors=['e', 'stem'], screws=feet_r, shape=rb,
                   name='Crown bridge (1/16" black delrin): a frame round the worm; holds the stem down and the crown arbor\'s middle pivot'))
    for b in B_:
        ko = keepout(b['z0'], b['z0'] + TT, skip_arbors=b['arbors'])
        own = [n for n, a, g, t0, t1 in things if a in b['arbors'] and not n.endswith(' rod') and n != 'stem journals']
        ko_own = keepout(b['z0'], b['z0'] + TT, only=own, gap=ENDSHAKE)
        inside = outline if b['id'] == 'crown' else outline.buffer(-1.3)   # (a 1.0 wall between its well and the edge; the crown bridge closes the stem's channel right out to the edge)
        b['shape'] = largest(smooth(b['shape'].difference(ko.buffer(0.01)).difference(ko_own.buffer(0.01)).intersection(inside)))
    for i, b1 in enumerate(B_):                                 # bridges at overlapping heights keep apart (room for a wall between the wells)
        for b2 in B_[i + 1:]:
            if b1['z0'] < b2['z0'] + TT + GAP and b2['z0'] < b1['z0'] + TT + GAP:
                b2['shape'] = largest(smooth(b2['shape'].difference(b1['shape'].buffer(1.6))))

    # ---- the main plate's pockets (from the top face): a recess for every wheel down to 0.3 under it, a well for every bridge at its seat,
    # the discs' clearance, the worm window right through, the stem's channel under the crown bridge
    pockets = []                                                 # (name, polygon, floor z; None = right through)
    for n, (a, c, r, z0, z1) in G.items(): pockets.append((f'recess for the {n}', C(c, r + GAP), z0 - GAP))
    for n, (a, c, r, z0, z1) in discs.items(): pockets.append((f'clearance under the {n}', C(c, r + GAP), z0 - GAP))
    for b in B_: pockets.append((f'well for the {b["id"]} bridge', Polygon(b['shape'].buffer(GAP, join_style=1).exterior), b['z0']))
    pockets.append(('worm window (see through the movement)', sbox(wa - GAP, -wro - GAP, wb + GAP, wro + GAP), None))
    pockets.append(('stem channel (the crown bridge closes it)', sbox(x0 - 0.1, -jr - 0.075, edge + 0.6, jr + 0.075), zw - jr - 0.05))
    def floor_under(poly):
        """the main plate's lowest floor under any of poly (its top face if nothing is cut there)"""
        f = z_top
        for n, g, fl in pockets:
            if g.intersects(poly): f = min(f, z_bot if fl is None else fl)
        return f
    # bores: a bearing (its flange in a seat on the recess floor) for every arbor a bridge doesn't hold at both ends; the hour arbor and the
    # second intermediate, cantilevered under the discs, get a second (unflanged) bearing pressed into the same bore from the back
    bearings = {'a1': 1, 'b': 1, 'a2': 2, 'hour': 2}

    # ---- top plates (1/16", on the main plate's top face, flush with the discs): the frame round the discs, split by a channel down the
    # centre line that opens round the centre bridge (its arms and screw heads show); windows over every wheel that turns beneath
    cbs = B_[0]
    heads_up = [(b, s) for b in B_ for s in b['screws'] if b['z0'] + TT + HEAD_H > z_top - GAP]   # heads up at the top plates' level
    # (the channel's edges are arcs concentric with both intermediate wheels, 0.3 outside their tips: the top plates follow the wheels below)
    channel = unary_union([sbox(-2.7, -HY - 1, 2.7, HY + 1), cbs['shape'].buffer(0.6, join_style=1), C(A1, G['first intermediate wheel'][2] + GAP),
                           C(A2, G['second intermediate wheel'][2] + GAP)] + [C(s, HEAD_R + 0.4) for b, s in heads_up])
    frame = outline.difference(unary_union([C(H, 9.5 + GAP), C(M, 9.5 + GAP)])).difference(channel)
    tops = []
    for side, sx in (('left', -1), ('right', 1)):
        half = largest(smooth(frame.intersection(sbox(min(0, sx * 2 * HX), -HY - 1, max(0, sx * 2 * HX), HY + 1)), 0.6, 0.6))
        seen = unary_union([C(c, r + 0.2) for n, (a, c, r, z0, z1) in G.items()]).intersection(half.buffer(-1.2))
        wins = []
        for p in pieces(smooth(seen, 0.5, 0)):
            if p.area < 3.0: continue
            under = [n for n, (a, c, r, z0, z1) in sorted(G.items(), key=lambda kv: -kv[1][4]) if C(c, r).intersection(p).area > 0.5]
            wins.append((' and '.join(under[:2]) or 'train', p))
        tops.append(dict(id=side, shape=half, windows=wins))
    def screw_spots(tp):
        """top plate screws: on the main plate's top face (nothing cut within reach of the thread), inside the plate clear of its windows,
        the solid spots nearest the plate's corners"""
        inner = tp['shape'].buffer(-BOSS)
        for n, w in tp['windows']: inner = inner.difference(w.buffer(BOSS))
        x0_, y0_, x1_, y1_ = inner.bounds; cand = []
        for i in range(int((x1_ - x0_) / 0.25) + 1):
            for j in range(int((y1_ - y0_) / 0.25) + 1):
                q = (x0_ + 0.25 * i, y0_ + 0.25 * j)
                if inner.contains(Point(q)) and floor_under(C(q, TAP_SOLID, 32)) >= z_top - 1e-9: cand.append(q)
        bx0, by0, bx1, by1 = tp['shape'].bounds; picks = []
        for corner in ((bx0, by0), (bx0, by1), (bx1, by0), (bx1, by1)):
            if not cand: break
            q = min(cand, key=lambda p: math.dist(p, corner))
            if all(math.dist(q, p) > 8 for p in picks): picks.append(q)
        return [(round(x, 2), round(y, 2)) for x, y in picks]
    for tp in tops:
        tp['screws'] = screw_spots(tp)
        tp['head_holes'] = [s for b, s in heads_up if tp['shape'].intersects(C(s, HEAD_R + GAP))]   # a round hole over any head beneath
    G_ = dict(G=G, discs=discs, things=things, arbor_at=arbor_at, rod_top=rod_top, pockets=pockets, bridges=B_, tops=tops, outline=outline,
              z_top=z_top, z_bot=z_bot, floor_under=floor_under, keepout=keepout, bearings=bearings, heads_up=heads_up)
    problems = check(G_)

    # ---- the parts, as the sim's drawn parts
    sks, cuts = [sketch('K1', 'Main plate outline', 'z', round(z_bot, 4), outline_pts)], []
    for n, g, fl in pockets:
        k = f'K{20 + len(cuts)}'
        sks.append(sketch(k, f'Main plate: {n}', 'z', round(z_bot, 4), poly_dots(g)))
        cuts.append({'id': f'h{len(cuts) + 1}', 'kind': 'pocket', 'name': n[0].upper() + n[1:], 'sketch': k, 'from': 'back',
                     'depth': None if fl is None else round(z_top - fl, 4)})
    hid = [len(cuts) + 1]
    def hole(lst, kind, name, at, d, depth=None, fit=None, axis=None):
        c = {'id': f'h{hid[0]}', 'kind': kind, 'name': name, 'at': [round(at[0], 4), round(at[1], 4)], 'd': d, 'from': 'back', 'depth': depth}
        if fit: c['fit'] = fit
        if axis: c['axis'] = axis
        lst.append(c); hid[0] += 1
    for a, nb in bearings.items():
        f = floor_under(C(arbor_at[a], 0.01))
        hole(cuts, 'bearing', f'Bearing seat, {names[a]} (on its recess floor; the flange shows like a jewel)', arbor_at[a], 7.3, round(z_top - f + 0.65, 4), axis=a)
        hole(cuts, 'bearing', f'Bearing bore, {names[a]}' + (' (a second, unflanged bearing pressed in from the back)' if nb == 2 else ''), arbor_at[a], 5.98, fit='bearing', axis=a)
    hole(cuts, 'rod', 'Minute arbor: a long plain delrin bushing (the worm lies too close for a bearing)', M, 3.08, fit='rod_free', axis='minute')
    hole(cuts, 'rod', 'Crown arbor: plain delrin bushing under its worm wheel', E, 3.08, fit='rod_free', axis='e')
    for b in B_:
        for s in b['screws']: hole(cuts, 'pilot', f'M2 thread ({b["id"]} bridge)', s, 1.6, fit='m2_tap')
    for tp in tops:
        for s in tp['screws']: hole(cuts, 'pilot', f'M2 thread ({tp["id"]} top plate)', s, 1.6, fit='m2_tap')
    drawn = [{'id': 'D1', 'name': 'Main plate (3/8" black delrin, milled from the top: a recess for every wheel at its own height, a well for every bridge, bearings seated on the recess floors)',
              'sketch': 'K1', 'thickness': T38, 'grow': 'plus', 'mill': 'back', 'minWall': 0.6, 'cuts': cuts}]
    for i, b in enumerate(B_):
        k = f'K{2 + i}'
        sks.append(sketch(k, f'{b["id"].title()} bridge outline', 'z', round(b['z0'], 5), poly_dots(b['shape'])))
        bc = []; hid[0] = 1
        for a in b['arbors']:
            if a in arbor_at: hole(bc, 'rod', f'Pivot, {names[a]} (plain delrin)', arbor_at[a], 3.08, fit='rod_free', axis=a)
        for s in b['screws']: hole(bc, 'clear', 'M2 through (pan head on top)', s, 2.3, fit='m2_clear')
        for j, ring in enumerate(b['shape'].interiors):          # (the crown bridge's frame: the worm rises through it)
            hk = f'K{90 + 3 * i + j}'
            sks.append(sketch(hk, f'{b["id"].title()} bridge: opening', 'z', round(b['z0'], 5), poly_dots(Polygon(ring))))
            bc.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': 'The worm rises through it' if b['id'] == 'crown' else 'Opening', 'sketch': hk, 'from': 'back', 'depth': None}); hid[0] += 1
        drawn.append({'id': f'D{2 + i}', 'name': b['name'], 'sketch': k, 'thickness': TT, 'grow': 'plus', 'mill': 'back', 'cuts': bc})
    for i, tp in enumerate(tops):
        k = f'K{5 + i}'
        sks.append(sketch(k, f'Top plate, {tp["id"]}', 'z', round(z_top, 5), poly_dots(tp['shape'])))
        tc = []; hid[0] = 1
        for j, (n, w) in enumerate(tp['windows']):
            wk = f'K{100 + 20 * i + j}'
            sks.append(sketch(wk, f'Top plate, {tp["id"]}: window over the {n}', 'z', round(z_top, 5), poly_dots(w)))
            tc.append({'id': f'h{hid[0]}', 'kind': 'pocket', 'name': f'Window over the {n}', 'sketch': wk, 'from': 'back', 'depth': None}); hid[0] += 1
        for s in tp['head_holes']: hole(tc, 'clear', 'Round window over a bridge screw head', s, round(2 * (HEAD_R + 0.4), 3))
        for s in tp['screws']: hole(tc, 'clear', 'M2 through (pan head)', s, 2.3, fit='m2_clear')
        drawn.append({'id': f'D{5 + i}', 'name': f'Top plate, {tp["id"]} (1/16" black delrin, flush with the discs; windows over the wheels turning beneath)',
                      'sketch': k, 'thickness': TT, 'grow': 'plus', 'mill': 'back', 'cuts': tc})
    # the stem: the aligned build's, with its inner journal 0.6 long
    stem = copy.deepcopy(next(d for d in st['drawn'] if d.get('turn'))); stem['id'] = 'D7'
    ksk = next(k for k in st['sketches'] if k['id'] == stem['sketch'])
    xs = sorted({p['u'] for p in ksk['points']}); old_x0 = xs[0]
    for p in ksk['points']:
        if abs(p['u'] - old_x0) < 1e-6: p['u'] = round(x0, 4)
        elif abs(p["u"] - (old_x0 + 0.2)) < 1e-3: p['u'] = round(x0 + 0.2, 4)
    drawn.append(stem)
    st['sketches'] = [ksk] + sks
    st['drawn'] = drawn
    st['fits'] = FITS
    # ---- the project: the aligned train in these plates
    P.update({'id': 'beta2-haute', 'name': 'Beta 2 · haute', 'title': 'Beta 2 · haute: plates and bridges'})
    P['blurb'] = (P['blurb'].split(' Module 0.6')[0] + ' Module 0.6, black delrin, brass rods. A 3/8" main plate stepped from the top: every wheel turns in '
                  'its own recess at its own height, bearings seated on the recess floors. Three bridges, each sunk in its own well: the centre bridge holds the first '
                  'intermediate on twin arms down the centre line; the transfer bridge sits between the transfer arbor\'s pinion and wheel; the crown bridge is a frame '
                  'round the worm, holding the stem down. Two top plates flush with the discs, windows over the wheels beneath, a channel down the centre where both '
                  f'intermediates\' rods and the centre bridge show. Movement {2 * HX:.1f} x {2 * HY:.1f} mm, {z_top + TT - z_bot:.2f} mm from the back of the main plate to the top of the discs.')
    P['source'] = list(P.get('source') or []) + ['Plates and bridges: Claude, 2026-11-23, from Adam\'s brief ("eloquent, not cheap ... everything is intentional": a thicker main plate that comes up as high as it '
                                                 'needs to, two or three top plate and bridge hybrids, seats cut in different plates, windows where wheels turn below, bridges with arms "just because").']
    P['rules']['rod'] = {'d': 3.0, 'from': round(z_bot, 4), 'top': {'a1': round(rod_top['a1'], 5)}}
    P['plate']['z'] = round(z_bot - 1.5, 4)
    P['defaults']['stages']['s_ba1']['dz'] = dz_bp
    P['groups']['drawn'] = 'Plates, bridges and stem'
    P['focus'] = [{'id': 'train', 'label': 'Crown → E → minute → transfer → first and second intermediate → hour', 'parts': ['e', 'minute', 'b', 'a1', 'a2', 'hour', 'D7']},
                  {'id': 'crown', 'label': 'Crown works: stem, worm, crown arbor, crown bridge', 'parts': ['e', 'minute', 'D4', 'D7']},
                  {'id': 'bridges', 'label': 'Bridges: centre, transfer, crown', 'parts': ['D2', 'D3', 'D4', 'a1', 'b', 'e']},
                  {'id': 'guts', 'label': 'Under the top plates: main plate, bridges, train', 'parts': ['D1', 'D2', 'D3', 'D4', 'D7', 'minute', 'b', 'a1', 'a2', 'hour', 'e']},
                  {'id': 'plates', 'label': 'Main plate and bridges only', 'parts': ['D1', 'D2', 'D3', 'D4', 'D7']}]
    report = {'z': (round(z_bot, 4), round(z_top + TT, 4)), 'bridges': {b['id']: (round(b['z0'], 4), round(b['z0'] + TT, 4), round(b['shape'].area, 1)) for b in B_},
              'windows': {tp['id']: [n for n, w in tp['windows']] for tp in tops}, 'top screws': {tp['id']: tp['screws'] for tp in tops},
              'head holes': {tp['id']: tp['head_holes'] for tp in tops}, 'pockets': len(pockets), 'problems': problems}
    return S, report, G_

def check(G_):
    """every part against everything at its height; every screw on solid at its seat, its head clear; every arbor held at two places"""
    out = []; things, B_, tops, floor_under = G_['things'], G_['bridges'], G_['tops'], G_['floor_under']
    z_top, arbor_at = G_['z_top'], G_['arbor_at']
    for b in B_:
        z0, z1 = b['z0'], b['z0'] + TT; sh = b['shape']
        if sh.geom_type != 'Polygon': out.append(f"{b['id']} bridge is in pieces")
        for n, a, g, t0, t1 in things:
            if a in b['arbors']:
                if n.endswith(' rod') or n == 'stem journals': continue
                if t0 < z1 + ENDSHAKE - 1e-9 and t1 > z0 - ENDSHAKE + 1e-9 and sh.distance(g) < ENDSHAKE - 1e-3: out.append(f"{b['id']} bridge: within {ENDSHAKE} of its own {n}")
            elif t0 < z1 + GAP - 1e-9 and t1 > z0 - GAP + 1e-9 and sh.distance(g) < GAP - 1e-3:
                out.append(f"{b['id']} bridge comes {sh.distance(g):.3f} from the {n} (z {t0:.3f}..{t1:.3f})")
        for a in b['arbors']:
            if a in arbor_at and not sh.buffer(-0.6).contains(C(arbor_at[a], 1.54)): out.append(f"{b['id']} bridge: under 0.6 of delrin round the {a} pivot")
        for s in b['screws']:
            if not sh.buffer(-0.5 + 1e-3).contains(C(s, 1.15, 32)): out.append(f"{b['id']} bridge: screw {s} under 0.5 from its edge")
            f = floor_under(C(s, TAP_SOLID, 32))
            if f < z0 - 1e-6: out.append(f"{b['id']} bridge: screw {s}'s thread runs into a pocket (floor {f:.3f} under its seat {z0:.3f})")
            hz0, hz1 = z1, z1 + HEAD_H; head = C(s, HEAD_R, 32)
            for n, a, g, t0, t1 in things:
                if t0 < hz1 + GAP - 1e-9 and t1 > hz0 - GAP + 1e-9 and head.distance(g) < GAP - 1e-3: out.append(f"{b['id']} bridge: screw head at {s} hits the {n}")
            for b2 in B_:
                if b2 is not b and b2['z0'] < hz1 + GAP and b2['z0'] + TT > hz0 - GAP and head.distance(b2['shape']) < GAP - 1e-3: out.append(f"{b['id']} bridge: screw head at {s} hits the {b2['id']} bridge")
            if hz1 > z_top - GAP:
                for tp in tops:
                    if tp['shape'].distance(head) < GAP - 1e-3 and s not in tp['head_holes']: out.append(f"{b['id']} bridge: screw head at {s} under the {tp['id']} top plate with no hole")
    for i, b1 in enumerate(B_):
        for b2 in B_[i + 1:]:
            if b1['z0'] < b2['z0'] + TT + GAP and b2['z0'] < b1['z0'] + TT + GAP and b1['shape'].distance(b2['shape']) < 1.6 - 1e-3:
                out.append(f"{b1['id']} and {b2['id']} bridges closer than 1.6 at overlapping heights (the wall between their wells)")
    for tp in tops:
        if tp['shape'].geom_type != 'Polygon': out.append(f"{tp['id']} top plate is in pieces")
        for n, a, g, t0, t1 in things:
            if t0 < z_top + TT + GAP - 1e-9 and t1 > z_top - GAP + 1e-9 and tp['shape'].distance(g) < GAP - 1e-3: out.append(f"{tp['id']} top plate comes {tp['shape'].distance(g):.3f} from the {n}")
        thin = tp['shape'].difference(tp['shape'].buffer(-0.6).buffer(0.6 + 1e-3))
        if thin.area > 0.05: out.append(f"{tp['id']} top plate has {thin.area:.2f} mm² narrower than 1.2")
        for n, w in tp['windows']:
            if not tp['shape'].buffer(-1.0 + 1e-3).contains(w): out.append(f"{tp['id']} top plate: window over the {n} under 1.0 from the edge")
        if len(tp['screws']) < 2: out.append(f"{tp['id']} top plate has {len(tp['screws'])} screw(s)")
        for s in tp['screws']:
            if floor_under(C(s, TAP_SOLID, 32)) < z_top - 1e-6: out.append(f"{tp['id']} top plate: screw {s} over a pocket")
    # every arbor held at two places: a pair of bearings, or a bearing or bushing in the main plate and a bridge pivot
    held = {a: [] for a in arbor_at}
    for a, nb in G_['bearings'].items(): held[a] += ['main plate bearing'] * nb
    held['minute'].append('main plate bushing, 9.5 long'); held['e'].append('main plate bushing')
    for b in B_:
        for a in b['arbors']:
            if a in held: held[a].append(f"{b['id']} bridge")
            if a in G_['rod_top'] and G_['rod_top'][a] < b['z0'] + TT - 1e-6: out.append(f"{a}'s rod stops below the top of the {b['id']} bridge")
    for a, h in held.items():
        if len(h) < 2 and not h[0].endswith('9.5 long'): out.append(f'{a} is held at only one place ({h})')
    return out
