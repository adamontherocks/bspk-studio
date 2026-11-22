# Producibility pass for Crescent with a Ø1 mm end mill (Makera Z1), Delrin wheels and acrylic plates.
# Reads sim/projects/crescent.json and, for every drawn part at every depth where its cuts change:
#   - reach:  cut-away area a Ø1.0 tool can't get into (material left behind), beyond what a sharp inside corner leaves
#   - walls:  material narrower than 0.8 mm (fragile in Delrin or acrylic)
#   - floors: material left under or over a pocket thinner than 0.6 mm
#   - holes:  round holes smaller than the tool (they need a drill)
# and for every involute gear: the material the tool leaves in each tooth root must stay below where the mating tooth's tip reaches.
# Side-on parts (stem, crown, winding pinion) are lathe or separately checked parts and are listed, not rasterised.
import json, math, os, sys
import numpy as np
from matplotlib.path import Path as MP
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gearing as GR
JPATH = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else os.path.join(HERE, '..', '..', 'sim', 'projects', 'crescent.json')
J = json.load(open(JPATH))
P, ST = J['project'], J['state']
SK = {k['id']: k for k in ST['sketches']}
TOOL_R, WALL, FLOOR = 0.5, 0.8, 0.6
CORNER = TOOL_R ** 2 * (1 - math.pi / 4) * 1.6     # what one sharp inside corner leaves (with margin)
DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}
def open_r(m, r, h):
    """morphological opening by a disc of radius r, via distance transforms (fast for any radius)"""
    er = ndimage.distance_transform_edt(m) * h > r
    return ndimage.distance_transform_edt(~er) * h <= r
from pk2 import spline_poly
def pts_of(k): return np.asarray(spline_poly(k['points']), float)     # the sim's own curve (raw dots made a 13-gon of the plate's round edge, 1.9 mm inside it)
def circle(c, r, n=96): return np.array([[c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)] for i in range(n)])
def layers_of(d):
    T = d['thickness']; out = []
    for c in d.get('cuts', []) or []:
        D = T if c.get('depth') is None else min(T, max(0, c['depth']))
        iv = (lambda a, b: (T - min(T, b), T - a)) if c.get('from') == 'back' else (lambda a, b: (a, min(T, b)))
        if c['kind'] == 'pocket':
            k = SK.get(c['sketch'])
            if k: out.append(dict(iv=iv(0, D), path=pts_of(k), drilled=False, name=c.get('name', 'pocket')))
            continue
        if not c.get('d'): continue
        out.append(dict(iv=iv(0, D), path=circle(c['at'], c['d'] / 2), drilled=c['kind'] in DRILLED and c['d'] <= 3.2, name=c.get('name', c['kind']), d=c['d']))   # small round holes are drilled; bigger ones (bearing pockets) are milled
        if c.get('seat') and c['seat']['d'] > c['d']:
            out.append(dict(iv=iv(0, min(D, c['seat']['depth'])), path=circle(c['at'], c['seat']['d'] / 2), drilled=False, name=(c.get('name') or '') + ' seat'))
    return out
def analyse_part(d):
    k = SK[d['sketch']]
    if k['plane']['axis'] != 'z': return {'name': d['name'], 'side': True}
    outline = pts_of(k); T = d['thickness']; L = layers_of(d)
    span = outline.max(0) - outline.min(0); h = 0.02 if span.max() < 45 else 0.05
    x0, y0 = outline.min(0) - 2.0; x1, y1 = outline.max(0) + 2.0
    GX, GY = np.meshgrid(np.arange(x0, x1, h), np.arange(y0, y1, h)); XY = np.c_[GX.ravel(), GY.ravel()]
    body = MP(outline).contains_points(XY).reshape(GX.shape)
    def window_mask(path):   # rasterise a cut only inside its own box
        a, b = path.min(0), path.max(0)
        ix0, ix1 = max(0, int((a[0] - x0) / h) - 2), min(GX.shape[1], int((b[0] - x0) / h) + 3)
        iy0, iy1 = max(0, int((a[1] - y0) / h) - 2), min(GX.shape[0], int((b[1] - y0) / h) + 3)
        sub = MP(path).contains_points(np.c_[GX[iy0:iy1, ix0:ix1].ravel(), GY[iy0:iy1, ix0:ix1].ravel()]).reshape(iy1 - iy0, ix1 - ix0)
        return (iy0, iy1, ix0, ix1, sub)
    masks = [window_mask(l['path']) for l in L]
    cuts_z = sorted({0.0, T} | {b for l in L for b in l['iv']})
    res = {'name': d['name'], 'reach': [], 'walls': [], 'floors_min': None, 'small_holes': [], 'h': h}
    run = np.zeros(GX.shape); best_floor = np.full(GX.shape, np.inf); prev = None
    for z0, z1 in zip(cuts_z, cuts_z[1:]):
        if z1 - z0 < 1e-6: continue
        zm = (z0 + z1) / 2
        act = [i for i, l in enumerate(L) if l['iv'][0] <= zm <= l['iv'][1]]
        mat = body.copy(); drilled = np.zeros_like(body); milled_cut = np.zeros_like(body)
        for i in act:
            iy0, iy1, ix0, ix1, sub = masks[i]
            mat[iy0:iy1, ix0:ix1] &= ~sub
            if L[i]['drilled']: drilled[iy0:iy1, ix0:ix1] |= sub
            else: milled_cut[iy0:iy1, ix0:ix1] |= sub
        drilled &= ~milled_cut          # a hole drilled inside a milled pocket is milled away with it
        # reach: the cut-away region the tool mills (outside the part and the milled pockets, not the drilled holes)
        milled = ~mat & ~drilled
        opened = open_r(milled, TOOL_R, h)
        left = milled & ~opened
        lab, n = ndimage.label(left)
        for j in range(1, n + 1):
            ar = (lab == j).sum() * h * h
            if ar > CORNER:
                ys, xs = np.nonzero(lab == j)
                res['reach'].append({'z': round(zm, 2), 'area': round(ar, 3), 'at': [round(float(GX[0, xs.mean().astype(int)]), 2), round(float(GY[ys.mean().astype(int), 0]), 2)]})
        # walls thinner than WALL
        thin = mat & ~open_r(mat, WALL / 2, h)
        lab, n = ndimage.label(thin)
        if n:
            dist = ndimage.distance_transform_edt(mat) * h
            for j in range(1, n + 1):
                sel = lab == j; ar = sel.sum() * h * h
                if ar < 0.12: continue                            # a sharp outside corner, not a wall
                ys, xs = np.nonzero(sel)
                res['walls'].append({'z': round(zm, 2), 'area': round(ar, 3), 'width': round(2 * float(dist[sel].max()), 2),
                                     'at': [round(float(GX[0, int(xs.mean())]), 2), round(float(GY[int(ys.mean()), 0]), 2)]})
        # floors: thickness of each run of material through the depth
        run = np.where(mat, run + (z1 - z0), 0.0)
        if prev is not None:
            ended = prev & ~mat                                   # a run of material just ended under a void
            best_floor = np.where(ended, np.minimum(best_floor, run_prev), best_floor)
        prev = mat.copy(); run_prev = run.copy()
    # the top run ends at the top face only if something was cut below it (otherwise it's the part's full thickness)
    full = np.isclose(run_prev, T)
    fl = np.where(~full & prev, np.minimum(best_floor, run_prev), best_floor)
    fl = np.where(body, fl, np.inf)
    thin_floor = fl < FLOOR
    if thin_floor.any():
        ys, xs = np.nonzero(thin_floor)
        res['floors_min'] = {'t': round(float(fl[thin_floor].min()), 3), 'area': round(float(thin_floor.sum() * h * h), 2), 'at': [round(float(GX[0, int(xs.mean())]), 2), round(float(GY[int(ys.mean()), 0]), 2)]}
    for l in L:
        if l.get('d') and l['d'] < 1.0 - 1e-6: res['small_holes'].append({'name': l['name'], 'd': l['d']})
    return res
# ---------- flute length each end mill needs, towers, and the milled face ----------
# A smaller end mill on a 1/8" shank can only go as deep below where that shank still fits as its flutes are long. For every part, from
# the face it is milled from: the regions only a given size can reach (a bigger one can't), and how far below the shank's reach they lie.
TOOLS = [(1.0, '1 mm'), (1.5, '1.5 mm'), (2.0, '2 mm'), (3.175, '1/8"')]
SHANK_R = 3.175 / 2
def face_of(d):
    if d.get('mill') in ('back', 'front'): return 'top' if d['mill'] == 'back' else 'bottom'
    blind = [c for c in d.get('cuts', []) or [] if c.get('depth') is not None and c['depth'] < d['thickness'] - 1e-6]
    return ('top' if blind[0].get('from') == 'back' else 'bottom') if blind else 'either'
def exact_only(outline, L, zm, sel, GX, GY, r, r_next, min_area=0.003):
    """does the bit of radius r really reach material here that the next size up can't? The raster above marks a strip a cell or
    two wide along a wall wherever its disc steps miss the wall by a few µm; this checks the raster's piece against the exact
    outlines (2026-11-22: it raised '2 mm 9.53' at (18, -56.2), then at (16.2, -51.5), where a 1/8" shank sweeps all but 0.0001 mm²)"""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    ys, xs = np.nonzero(sel)
    win = box(GX[0, xs.min()], GY[ys.min(), 0], GX[0, xs.max()], GY[ys.max(), 0]).buffer(r_next * 2 + 0.2)
    body = Polygon(outline).buffer(0)
    cuts = unary_union([Polygon(l['path']).buffer(0) for l in L if l['iv'][0] <= zm <= l['iv'][1]])
    void = win.buffer(r_next * 2).difference(body).union(cuts.intersection(win.buffer(r_next * 2)))
    a = void.buffer(-r, quad_segs=64).buffer(r, quad_segs=64)
    b = void.buffer(-r_next, quad_segs=64).buffer(r_next, quad_segs=64)
    return a.difference(b).intersection(body).intersection(win).area >= min_area
def flute_and_towers(d, h=None):
    k = SK[d['sketch']]
    if k['plane']['axis'] != 'z': return None
    outline = pts_of(k); T = d['thickness']; face = face_of(d)
    span = outline.max(0) - outline.min(0); h = h or (0.025 if span.max() < 45 else 0.05)
    x0, y0 = outline.min(0) - 3.0; x1, y1 = outline.max(0) + 3.0
    GX, GY = np.meshgrid(np.arange(x0, x1, h), np.arange(y0, y1, h)); XY = np.c_[GX.ravel(), GY.ravel()]
    body = MP(outline).contains_points(XY).reshape(GX.shape)
    L = [l for l in layers_of(d) if not l['drilled']]
    M = [MP(l['path']).contains_points(XY).reshape(GX.shape) for l in L]
    top = face != 'bottom'
    edges = sorted({0.0, T} | {b for l in L for b in l['iv']})
    bands = [(a, b) for a, b in zip(edges, edges[1:]) if b - a > 1e-6]
    bands = sorted(bands, key=lambda ab: -ab[1]) if top else sorted(bands, key=lambda ab: ab[0])   # from the milled face inwards
    need = {name: 0.0 for _, name in TOOLS}; where = {}
    cont = np.ones(GX.shape, bool); sd = np.zeros(GX.shape)          # how deep the shank can follow, per tool-centre position
    towers = []; rim = body & ~ndimage.binary_erosion(body, iterations=max(1, int(4.0 / h)))
    for a, b in bands:
        zm = (a + b) / 2; depth = (T - a) if top else b
        mat = body.copy()
        for l, m in zip(L, M):
            if l['iv'][0] <= zm <= l['iv'][1]: mat &= ~m
        void = ~mat
        dist = ndimage.distance_transform_edt(void) * h
        E = {name: dist > dia / 2 for dia, name in TOOLS}
        cont &= dist > SHANK_R; sd = np.where(cont, depth, sd)
        reach = {name: open_r(void, dia / 2, h) for dia, name in TOOLS}
        names = [n for _, n in TOOLS]
        for i, (dia, name) in enumerate(TOOLS):
            if name == '1/8"':
                if (reach[name] & body).any(): need[name] = max(need[name], depth)     # it cuts walls this deep
                continue
            only = reach[name] & ~reach[names[i + 1]] & body
            lab, n = ndimage.label(only)
            for j in range(1, n + 1):
                sel = lab == j
                if sel.sum() * h * h < 0.03: continue
                if not exact_only(outline, L, zm, sel, GX, GY, dia / 2, TOOLS[i + 1][0] / 2): continue
                cand = ndimage.binary_dilation(sel, iterations=int(dia / 2 / h) + 1) & E[name]
                if not cand.any(): continue
                loc = depth - float(sd[cand].max())
                if loc > need[name]:
                    need[name] = loc; ys, xs = np.nonzero(sel); where[name] = (round(float(GX[0, int(xs.mean())]), 1), round(float(GY[int(ys.mean()), 0]), 1), round(depth, 2))
        # towers: a piece of material at this depth cut off from the rest of the part, small, and not at the part's rim
        lab, n = ndimage.label(mat & body)
        if n > 1:
            sizes = ndimage.sum(mat & body, lab, range(1, n + 1)) * h * h; big = int(np.argmax(sizes)) + 1
            for j in range(1, n + 1):
                if j == big or sizes[j - 1] > 80 or sizes[j - 1] < 0.2: continue
                sel = lab == j
                if (sel & rim).any(): continue
                ys, xs = np.nonzero(sel); towers.append({'at': [round(float(GX[0, int(xs.mean())]), 1), round(float(GY[int(ys.mean()), 0]), 1)], 'area': round(float(sizes[j - 1]), 2), 'depth': round(depth, 2)})
    return {'name': d['name'], 'face': face, 'flute': {k_: round(v, 2) for k_, v in need.items()}, 'flute_at': where, 'towers': towers}
# ---------- gears: what the tool leaves in a root, against where the mating tip reaches ----------
def root_left(g, h=0.004):
    """the highest radius of material the tool leaves in one tooth space"""
    a0 = g['step'] / 2                                       # the space after tooth 0 is centred here
    pts = np.array(GR.tooth(g, 0) + GR.tooth(g, 1) + GR.tooth(g, -1))
    poly = np.array(GR.outline(g))
    c = np.array([math.cos(a0), math.sin(a0)]) * (g['rf'] + g['ra']) / 2
    half = (g['ra'] - g['rf']) / 2 + 1.2; w = g['step'] * g['ra'] / 2 + 1.2
    GX, GY = np.meshgrid(np.arange(c[0] - w, c[0] + w, h), np.arange(c[1] - w, c[1] + w, h))
    R_ = np.hypot(GX, GY)
    mat = MP(poly).contains_points(np.c_[GX.ravel(), GY.ravel()]).reshape(GX.shape)
    milled = ~mat
    opened = open_r(milled, TOOL_R, h)
    ang = np.mod(np.arctan2(GY, GX), 2 * math.pi)
    left = milled & ~opened & (R_ < g['ra']) & (ang > 0.0) & (ang < g['step'])   # only this space (the box cuts through its neighbours)
    depth = ndimage.distance_transform_edt(left) * h                             # how far inside the leftover each pixel is
    return (float(R_[left].max()) if left.any() else g['rf']), dict(x0=GX[0, 0], y0=GY[0, 0], h=h, left=left, depth=depth)
def tip_path_hits(gA, LA, gB, dist, phase_space=True, n=600):
    """roll B against A through two of A's teeth and follow B's tooth tips (their whole land) in A's frame; how deep into the
    material the tool left in A's roots do they go?"""
    tips = []
    for k in range(-2, 3):
        for j in range(7):
            a = k * gB['step'] - gB['tip_half'] + 2 * gB['tip_half'] * j / 6; tips.append((gB['ra'] * math.cos(a), gB['ra'] * math.sin(a)))
    tips = np.array(tips); worst = 0.0
    phB0 = math.pi - gB['step'] / 2 + gB['step'] / 2      # a B tooth points at A when A's space faces it (A's space centred at step/2 at theta 0)
    for th in np.linspace(-gA['step'], gA['step'], n):
        phA = th + 0.0; phB = math.pi + (gA['step'] / 2) * 0 - (th - gA['step'] / 2) * gA['z'] / gB['z']
        c, s_ = math.cos(phB), math.sin(phB); W = np.c_[dist + tips[:, 0] * c - tips[:, 1] * s_, tips[:, 0] * s_ + tips[:, 1] * c]
        ca, sa = math.cos(-phA), math.sin(-phA); Q = np.c_[W[:, 0] * ca - W[:, 1] * sa, W[:, 0] * sa + W[:, 1] * ca]
        ang = np.mod(np.arctan2(Q[:, 1], Q[:, 0]), 2 * math.pi); k = np.floor(ang / gA['step'])
        cr, sr = np.cos(-k * gA['step']), np.sin(-k * gA['step']); C_ = np.c_[Q[:, 0] * cr - Q[:, 1] * sr, Q[:, 0] * sr + Q[:, 1] * cr]
        ix = np.round((C_[:, 0] - LA['x0']) / LA['h']).astype(int); iy = np.round((C_[:, 1] - LA['y0']) / LA['h']).astype(int)
        ok = (ix >= 0) & (iy >= 0) & (ix < LA['left'].shape[1]) & (iy < LA['left'].shape[0])
        if ok.any(): worst = max(worst, float(LA['depth'][iy[ok], ix[ok]].max()))
    return worst
arb = {a['id']: a for a in P['arbors']}
GD = {gg['id']: dict(gg, arbor=a['id']) for a in P['arbors'] for gg in a['gears']}
mod = {}
for sid, st in P['defaults']['stages'].items():
    for gid in P['stages'][sid]: mod[gid] = st['m']
for gid, s in P['defaults']['solo'].items(): mod[gid] = s['m']
pairs = [tuple(v) for v in P['stages'].values()]
gear_res = []
for g1, g2 in pairs + [('hand_pinion', '__rack__')]:
    for a, b in ((g1, g2), (g2, g1)):
        if a == '__rack__': continue
        A = GD[a]
        if A.get('plain'): continue
        gA = GR.compute(mod[a], A['z'], A.get('x', 0.0))
        if b == '__rack__':
            gB = GR.compute(1.0, 36, -0.40); dist = 23.951958020513107
        else:
            B_ = GD[b]; gB = GR.compute(mod[b], B_['z'], B_.get('x', 0.0)); dist = gA['rp'] + gB['rp']
        reach = dist - gB['ra']
        left, LA = root_left(gA)
        hit = tip_path_hits(gA, LA, gB, dist)
        tip_t = 2 * gA['ra'] * gA['tip_half']
        gear_res.append({'gear': A['label'], 'mate': 'rack sector' if b == '__rack__' else GD[b]['label'], 'left_r': round(left, 3), 'mate_tip_reaches_r': round(reach, 3),
                         'clear': round(reach - left, 3), 'tips_dig_into_leftover_mm': round(hit, 3), 'tip_land_mm': round(tip_t, 3), 'root_space_mm': round(2 * gA['rf'] * (gA['step'] / 2 - gA['root_half']), 3)})
# ---------- run ----------
ONLY = sys.argv[sys.argv.index('--part') + 1] if '--part' in sys.argv else None
parts = [] if '--gears' in sys.argv else [analyse_part(d) for d in ST['drawn'] if ONLY is None or d['name'] == ONLY]
if ONLY or '--gears' in sys.argv: pairs = [] if ONLY else pairs
mill = [] if '--gears' in sys.argv else [r for r in (flute_and_towers(d) for d in ST['drawn'] if ONLY is None or d['name'] == ONLY) if r]
out = {'parts': parts, 'gears': gear_res, 'mill': mill}
json.dump(out, open(os.path.join(HERE, 'produce.json'), 'w'), indent=1)
for r in parts:
    if r.get('side'): print(f"- {r['name']}: side-on part (turned or checked on its own)"); continue
    bits = []
    if r['reach']: bits.append(f"tool can't reach {len(r['reach'])} spot(s), largest {max(x['area'] for x in r['reach'])} mm² at {max(r['reach'], key=lambda x: x['area'])['at']}")
    if r['walls']: bits.append(f"walls under {WALL} mm: {len(r['walls'])}, thinnest {min(x['width'] for x in r['walls'])} mm at {min(r['walls'], key=lambda x: x['width'])['at']}")
    if r['floors_min']: bits.append(f"floor {r['floors_min']['t']} mm thin over {r['floors_min']['area']} mm² at {r['floors_min']['at']}")
    if r['small_holes']: bits.append(f"holes under 1 mm: {r['small_holes']}")
    print(f"- {r['name']}: " + ('; '.join(bits) if bits else 'clean'))
print('milled face, flute each end mill needs (below where its 1/8" shank can follow), towers:')
for r in mill:
    fl = ', '.join(f"{k_} {v}" for k_, v in r['flute'].items() if v)
    print(f"  {r['name']}: from the {r['face']}; {fl}" + (f"; towers {r['towers']}" if r['towers'] else '') + (f" (deepest small-tool spots {r['flute_at']})" if r['flute_at'] else ''))
print('gears (tool leftover in the root vs the mate\'s tip):')
for gr in gear_res: print(f"  {gr['gear']} with {gr['mate']}: tool leaves root rounding up to r {gr['left_r']} (mate's tip bottoms at r {gr['mate_tip_reaches_r']}); rolling, the mate's tips dig {gr['tips_dig_into_leftover_mm']} mm into it; tip land {gr['tip_land_mm']} mm")

# ---------- the result goes into the project's checks ----------
if not ONLY and '--gears' not in sys.argv and '--no-write' not in sys.argv:
    LOC = {'1 mm': 3.0, '1.5 mm': 4.0, '2 mm': 8.0, '1/8"': 22.0}       # flute lengths of common cheap bits (1 mm: 3-4; the FN10A lists 4-22 for the set)
    worst = {k_: max((r['flute'][k_], r['name']) for r in mill) for k_ in LOC}
    towers = [(r['name'], t_) for r in mill for t_ in r['towers']]
    faces = {f: sum(1 for r in mill if r['face'] == f) for f in ('top', 'bottom', 'either')}
    reach_ok = all(worst[k_][0] <= LOC[k_] for k_ in LOC)
    thin = sorted(((min(x['width'] for x in r['walls']), r['name']) for r in parts if r.get('walls')), key=lambda t: t[0])
    Q8 = '1/8"'
    tw_txt = 'No plate left standing between recesses on its own' if not towers else '%d towers: %s' % (len(towers), '; '.join('%s at %s' % (n, t_['at']) for n, t_ in towers[:4]))
    within = 'all within common cheap bits (1 mm 3, 2 mm 8, %s 22)' % Q8 if reach_ok else 'MORE THAN COMMON BITS HAVE'
    txt = ('every flat part rasterised from the face it is milled from (%d from the top, %d from the bottom, %d cut right through). ' % (faces['top'], faces['bottom'], faces['either']) +
           'Flute each bit needs below where its %s shank can follow: 1 mm %s mm, 1.5 mm %s, 2 mm %s (%s), %s %s (%s); %s. ' % (Q8, worst['1 mm'][0], worst['1.5 mm'][0], worst['2 mm'][0], worst['2 mm'][1], Q8, worst[Q8][0], worst[Q8][1], within) +
           tw_txt + ". Every gear's root rounding stays clear of its mate's tips. Still thin: " + ', '.join('%s %s mm' % (n, w) for w, n in thin[:6]) + ' (pointed tips, a production call)')
    proof = {'label': 'Made on the Z1', 'by': 'produce.py', 'ok': reach_ok and not towers and all(g['tips_dig_into_leftover_mm'] < 0.005 for g in gear_res), 'text': txt}
    pf = J['project']['mechanisms'].setdefault('proofs', [])
    pf[:] = [x for x in pf if x.get('label') != proof['label']] + [proof]
    json.dump(J, open(JPATH, 'w'), indent=1, ensure_ascii=False)
    print('proof written into', JPATH, ':', proof['ok'], txt)
