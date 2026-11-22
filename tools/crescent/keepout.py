# Keep-out (2026-11-21): the space each height band of the movement needs clear, so a wall may move into it only where nothing
# turns, swings or sits: the sim's gear and hand discs (elements.json, read from elements(S, D)), every moving drawn part swept
# over its real range (the sim's 12-hour sweep ranges; turning parts as full discs), the return spring's wire over the lever's
# range, the arbor rods, and the footprint of every static part, each with the sim's 0.5 mm gap.
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, union, offset, circle, spline_poly

EL = json.load(open(os.path.join(HERE, 'elements.json')))
PLATE_IDS = {'D1', 'D3', 'D5', 'D6', 'D2'}
SKIP = {'D33'}                                  # Adam's tooth-profile sketch (P46), not a part
ROD_D = {'barrel': 3, 'center': 3}
SWEEP_R, ANCHOR_R = 4.0, 1.5     # a swinging part's sweep rounded r SWEEP_R; a spring's fixed end given a clear disc ANCHOR_R

def rotp(Pn, c, deg):
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a); Q = np.asarray(Pn, float) - c
    return np.c_[Q[:, 0] * ca - Q[:, 1] * sa, Q[:, 0] * sa + Q[:, 1] * ca] + c

_cache = {}
def sweeps(J):
    key = id(J)
    if key in _cache: return _cache[key]
    st = J['state']; SK = {k['id']: k for k in st['sketches']}; M = J['project']['mechanisms']; mounts = M.get('mounts') or {}
    gap = EL['minGap']; out = []
    for name, x, y, r, z0, z1 in EL['els']:
        out.append((z0, z1, [circle((x, y), r + gap)], name))
    for d in st['drawn']:
        k = SK.get(d['sketch']); m = mounts.get(d['id'])
        if not k or k['plane']['axis'] != 'z' or d.get('place') or d['id'] in SKIP: continue
        z0 = k['plane']['offset']; z1 = z0 + d['thickness']; poly = np.array(spline_poly(k['points']))
        if m is None:
            if d['id'] in PLATE_IDS: continue
            out.append((z0, z1, offset([P(poly)], 0.2), d['id'])); continue
        if m.get('axisX') or m.get('axisY'): continue
        c = np.array(st['pos'][m['axis']] if m.get('axis') else m['pivot'], float); ang = m.get('angle')
        tab = next((l for l in M.get('links') or [] if l.get('kind') == 'table' and l.get('arbor') == m.get('axis')), None)
        if tab: lo, hi = min(tab['values']), max(tab['values'])          # rocked from a table (fork, balance): its real swing
        elif m.get('axis') or ang not in EL['ranges']:
            out.append((z0, z1, [circle(c, float(np.hypot(*(poly - c).T).max()) + gap)], d['id'])); continue
        else: lo, hi = EL['ranges'][ang]
        sw = union(*[[P(rotp(poly, c, a))] for a in np.arange(lo - 1.5, hi + 1.51, 0.5)])
        from pk2 import close as _close
        if ang == 'lever': sw = _close(sw, SWEEP_R)   # the hollows of the lever's arm outline filled in its sweep (only ever more clearance)
        out.append((z0, z1, offset(sw, gap), d['id']))
    for sp in M.get('springs') or []:
        to = sp['to']; d = next(x for x in st['drawn'] if x['id'] == to['part']); m = mounts[to['part']]
        lo, hi = EL['ranges'][m['angle']]; pts = []
        for a in np.arange(lo - 1.5, hi + 1.51, 1.0):
            q = rotp([to['at']], np.array(m['pivot'], float), a)[0]; pts.append(q)
        seg = union(*[offset([P([sp['from'], q, q + 1e-3])], sp['r'] + gap) for q in pts], [circle(sp['from'], ANCHOR_R)])
        out.append((sp['z'] - sp['r'], sp['z'] + sp['r'], seg, sp['id']))
    # (arbor rods run in the bearings' holes, which no wall pass touches)
    _cache[key] = out
    return out

def keepout(J, za, zb):
    """the plan region that must stay clear anywhere between heights za and zb"""
    return union(*[ps for z0, z1, ps, nm in sweeps(J) if min(z1, zb) - max(z0, za) > 1e-6])
