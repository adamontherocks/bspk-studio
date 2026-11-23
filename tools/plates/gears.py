# Gears for the machine (generic; any project). VISION.md §7, R7.
# A gear part is what comes off the machine as one piece: one wheel or pinion, or a compound (a pinion standing on its wheel, cut
# from one sheet and milled from the pinion's side, one floor per gear). Its intent is the sim's numbers for those gears (module,
# teeth, profile shift, thickness, height, bore, crossing arms), sent by the sim with the scene (scene['gearParts'][pid]) because
# the sim works them out (a mesh's module, a pinion's height in its mesh). Resolve makes the part the cutter will leave, through
# the same floors loop as a plate (what the end mill can't reach at the bottom of each tooth space and in the arms' corners stays
# plate), and reports how far short of the root circle the cutter gets; export writes it as DXF, STEP and STL like any plate.
# Same involute as the sim (sim/involute.js), drawn finer (the sim draws 10 dots a flank; here 24, so the walls fit to 2 µm arcs).
import math, time
import numpy as np
from shapely.geometry import LineString, Point
from geo import P, union, diff, BOX
import resolve as R
import onewall as OW

N_FLANK, N_TIP, N_VALLEY = 24, 8, 12
DRILL_MAX = 3.2       # a bore this size or smaller is a drilled hole (its own true circle); larger is milled with the floors
SPECK = 0.005         # mm: only plate under 10 µm wide comes down (tooth tips are cut as drawn; see resolve.floors_from)
SEG = 0.02            # mm: arcs (plain wheels, the arms' windows, a milled bore) drawn with chords this long at most

def involute(m, z, x=0.0, pa_deg=20.0, at=(0.0, 0.0), phase=0.0):
    """the sim's involute spur gear outline (involute.js computeGear + outline), anticlockwise, and its circles"""
    pa = math.radians(pa_deg)
    rp = m * z / 2; rb = rp * math.cos(pa); ra = rp + m * (1 + x); rf = rp - m * (1.25 - x)
    half = math.pi / (2 * z) + 2 * x * math.tan(pa) / z + (math.tan(pa) - pa)
    t0 = math.sqrt((rf / rb) ** 2 - 1) if rf > rb else 0.0
    t1 = math.sqrt((ra / rb) ** 2 - 1)
    flank = [(rb * math.sqrt(1 + t * t), -half + t - math.atan(t)) for t in np.linspace(t0, t1, N_FLANK + 1)]
    tip_half = -flank[-1][1]; root_half = half if rf < rb else -flank[0][1]; step = 2 * math.pi / z
    pt = lambda r, a: (at[0] + r * math.cos(a + phase), at[1] + r * math.sin(a + phase))
    pts = []
    for i in range(z):
        a = i * step
        if rf < rb: pts.append(pt(rf, a - half))
        pts += [pt(r, a + g) for r, g in flank]
        pts += [pt(ra, a - tip_half + 2 * tip_half * j / N_TIP) for j in range(1, N_TIP)]
        pts += [pt(r, a - g) for r, g in reversed(flank)]
        if rf < rb: pts.append(pt(rf, a + half))
        v0, v1 = a + root_half, a + step - root_half
        pts += [pt(rf, v0 + (v1 - v0) * j / N_VALLEY) for j in range(1, N_VALLEY)]
    return pts, {'rp': rp, 'rb': rb, 'ra': ra, 'rf': rf, 'pointed': tip_half <= 0, 'crowded': step - 2 * root_half <= 0,
                 'space_root': rf * (step - 2 * root_half)}

def arc(c, r, a0, a1):
    n = max(8, int(math.ceil(abs(a1 - a0) * r / SEG)))
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def windows(c, w, phase=0.0):
    """the crossing arms' windows, as the sim draws them (index.html addCrossings): w = {rOut, rIn, arm, n} worked out by the sim"""
    if not w or w.get('n', 0) < 2: return []
    rO, rI, arm, n = w['rOut'], w['rIn'], w['arm'], int(w['n'])
    if rO - rI < 0.5: return []
    step = 2 * math.pi / n; dO = math.asin(arm / 2 / rO); dI = math.asin(min(0.95, arm / 2 / rI))
    if step - 2 * dI < 0.15: return []
    out = []
    for k in range(n):
        a0 = k * step + phase
        out.append(arc(c, rO, a0 + dO, a0 + step - dO) + arc(c, rI, a0 + step - dI, a0 + dI))
    return out

def layer_outline(L, at, phase):
    if L.get('plain'): return arc(at, L['rp'], 0, 2 * math.pi)[:-1], {'rp': L['rp'], 'ra': L['rp'], 'rf': L['rp'], 'pointed': False, 'crowded': False}
    return involute(L['m'], int(L['z']), L.get('x') or 0.0, L.get('pa') or 20.0, at, phase)

def stack(spec):
    """the layers far face first, the face milled, the thickness: each layer must stand inside the one under it"""
    Ls = sorted(spec['layers'], key=lambda L: L['z0'])
    for a, b in zip(Ls, Ls[1:]):
        if abs(a['z0'] + a['t'] - b['z0']) > 1e-3:
            raise ValueError(f"{a['label']} and {b['label']} don't touch ({b['z0'] - a['z0'] - a['t']:+.3f} mm), so they can't be one piece")
    at, ph = (0.0, 0.0), 0.0                      # resolved in the part's own frame: moving the arbor doesn't change the part
    geo = [layer_outline(L, at, ph) for L in Ls]
    big = [g[1]['ra'] for g in geo]
    if len(Ls) == 1 or all(x >= y for x, y in zip(big, big[1:])): face = 'back'        # shrinking upward: mill from the top
    elif all(x <= y for x, y in zip(big, big[1:])): Ls, geo, face = Ls[::-1], geo[::-1], 'front'
    else: raise ValueError('each gear of a compound part must stand inside the one below it (or above it), so it can be milled from one face')
    return Ls, geo, face, sum(L['t'] for L in Ls)

def resolve_spec(spec):
    t0 = time.time()
    Ls, geo, face, T = stack(spec)
    at, ph = (0.0, 0.0), 0.0
    shop = dict(R.SHOP); shop.update({k: float(v) for k, v in (spec.get('shop') or {}).items() if k in R.SHOP})
    base = union([P(geo[0][0])])
    func, h = [], 0.0
    for i, (L, g) in enumerate(zip(Ls, geo)):
        if i: func.append((diff(BOX, union([P(g[0])])), round(h, 4)))                  # around this gear: cut down to the one below
        h += L['t']
    win = windows(at, Ls[0].get('windows'), ph)
    if win: func.append((union([P(w) for w in win]), 0.0))
    bore = spec.get('bore') or 0
    if bore > DRILL_MAX: func.append((union([P(arc(at, bore / 2, 0, 2 * math.pi)[:-1])]), 0.0))
    Ls_f, A, notes, near = R.floors_from(base, func, T, shop, speck=SPECK)
    KO = [None] * len(A)
    A, moved = OW.regrade_levels(A, KO)
    A, cut, fill = OW.fair_levels(A, KO)
    outline, tl, extra = R.tiers({'thickness': T}, Ls_f, A, near)
    if outline is None: raise ValueError(f"{spec['name']}: nothing is left of it")
    # how close the cutter gets to each gear's root circle: the nearest the resolved wall comes to the axis, against the root circle
    reach = []
    O = np.array(outline, float); rO = np.hypot(O[:, 0] - at[0], O[:, 1] - at[1])
    for i, (L, g) in enumerate(zip(Ls, geo)):
        if L.get('plain'): continue
        info = g[1]
        if i == 0: r = float(rO.min())
        else:
            hgt = round(sum(x['t'] for x in Ls[:i]), 4); depth = round(T - hgt, 4)
            ring = [q for t in tl if abs(t['depth'] - depth) < 1e-3 for q in t['paths']]
            rr = [math.hypot(x - at[0], y - at[1]) for q in ring for x, y in q if math.hypot(x - at[0], y - at[1]) < info['ra'] + 0.05]
            r = min(rr) if rr else info['rf']
        # the root fillet the cutter leaves: the highest point where the cut wall leaves the drawn tooth by more than 5 µm. The partner's
        # tip touches this flank only from the start of the active profile up (r_sap, where the line of action meets the partner's tip
        # circle); a fillet reaching above that is in its path. (Below the base circle the involute check in the sim already warns.)
        wall = [(x, y) for x, y in (O if i == 0 else [p for q in ring for p in q]) if math.hypot(x - at[0], y - at[1]) < info['rp']]
        drawn = LineString(g[0] + g[0][:1])
        off = [math.hypot(x - at[0], y - at[1]) for x, y in wall if drawn.distance(Point(x, y)) > 0.005]
        top = max(off) if off else None
        sap = None
        if L.get('mate') and not L.get('plain'):
            mt = L['mate']; pa = math.radians(L.get('pa') or 20.0)
            u = mt['a'] * math.sin(pa) - math.sqrt(max(0.0, mt['ra'] ** 2 - mt['rb'] ** 2))
            sap = math.hypot(info['rb'], u) if u > 0 else info['rb']
        reach.append((L['label'], info, r, top, sap, L.get('mate')))
    words, clash = [], []
    for lab, info, r, top, sap, mate in reach:
        short = (r - info['rf']) * 1000
        w = (f"{lab}: tooth spaces {info['space_root']:.2f} mm wide at the root circle; the Ø{shop['cutter']:g} cutter gets "
             + ("to the root circle" if short < 2 else f"to {short:.0f} µm short of the root circle") + (" (POINTED teeth)" if info['pointed'] else ''))
        if top is not None and sap is not None:
            if top > sap + 0.002:
                w += f", but its root fillet climbs to r {top:.3f}, {(top - sap) * 1000:.0f} µm up the part of the flank {mate['label']} works on (from r {sap:.3f}): INTERFERENCE"
                clash.append(lab)
            else: w += f"; its root fillet stays {(sap - top) * 1000:.0f} µm below where {mate['label']} touches the flank"
        words.append(w)
    msg = ((f"{len(Ls)} gears in one piece" if len(Ls) > 1 else "one gear") + f", milled from the {'top' if face == 'back' else 'bottom'} face, {T:g} mm thick; " + '; '.join(words)
           + f"; {notes['cutter_filled']:.4f} mm² of corners left as plate" + (f"; bore Ø{bore:g} " + ('drilled' if bore <= DRILL_MAX else 'milled') if bore else '')
           + (f"; {extra} separate piece{'s' if extra > 1 else ''} dropped" if extra else '') + f"; {time.time() - t0:.1f} s")
    return {'outline': outline, 'tiers': tl, 'face': face, 'shop': shop, 'log': msg, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'key': None, 'kind': 'gear', 'interference': clash,
            'reach': [{'gear': lab, 'rf': round(info['rf'], 4), 'r': round(r, 4), 'fillet': None if top is None else round(top, 4)} for lab, info, r, top, _, _ in reach]}

def as_drawn(J, pid):
    """the gear part as a drawn part the plate exporter reads: its resolved floors, its drilled bore, its faces' heights"""
    spec = (J.get('gearParts') or {}).get(pid)
    res = ((J.get('state') or {}).get('made') or {}).get(pid)
    if not spec: raise ValueError(f'{pid}: the sim sent no numbers for this gear part')
    if not res: raise ValueError(f'{pid} is not resolved: resolve it first, so the file is what the machine will cut')
    Ls, geo, face, T = stack(spec)
    zb = min(L['z0'] for L in spec['layers'])
    bore = spec.get('bore') or 0
    # into the scene: turned to the gear's tooth phase and moved onto its arbor, so the file lines up with the plates
    (ax, ay), ph = spec['at'], spec.get('phase') or 0.0; c, s_ = math.cos(ph), math.sin(ph)
    tf = lambda ring: [[round(ax + c * x - s_ * y, 4), round(ay + s_ * x + c * y, 4)] for x, y in ring]
    res = dict(res, outline=tf(res['outline']), tiers=[{'depth': t['depth'], 'paths': [tf(q) for q in t['paths']]} for t in res['tiers']])
    cuts = [{'id': 'bore', 'kind': 'rod', 'd': bore, 'at': [ax, ay], 'depth': None, 'from': face}] if 0 < bore <= DRILL_MAX else []
    d = {'id': pid, 'name': spec['name'], 'sketch': 'K', 'thickness': T, 'grow': 'plus', 'resolved': res, 'cuts': cuts}
    return {'state': {'drawn': [d], 'sketches': [{'id': 'K', 'plane': {'axis': 'z', 'offset': zb}, 'points': []}], 'pos': {}}}

def resolve_scene(J, pids):
    out = {}
    for pid in pids:
        try:
            spec = (J.get('gearParts') or {}).get(pid)
            if not spec: raise ValueError('the sim sent no numbers for this gear part')
            out[pid] = resolve_spec(spec)
        except Exception as e: out[pid] = {'error': f'{type(e).__name__}: {e}'}
    return out
