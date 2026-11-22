# Cleanliness check for milled plates, at the scale Adam sees (2026-11-19, after notes P44-P60).
# The Z1 check (produce.py) asks "can a 1 mm cutter make it?". This asks "does it look engineered?":
#   - thin:   material at any level narrower than 2 mm, or a point sharper than r 1 (slivers, towers' edges, knife edges, bumps)
#   - corner: an inside corner tighter than r 1, or a slot narrower than 2 mm (unblended junctions, notches)
#   - tower:  an island of material standing above everything round it, smaller than 40 mm2
# Outlines are drawn with the sim's own polyspline (index.html outlinePointAt), so what is checked is what the sim shows.
# Small drilled holes, bearings and screws are left out of the corner check (they are round on purpose).
#
#   python3 clean_check.py SCENE.json [--parts D1,D3] [--png OUT.png] [--json OUT.json]
import json, math, sys, os
import numpy as np
from matplotlib.path import Path as MP
from scipy import ndimage

H = 0.05
THIN_R, CORNER_R, TOWER_A, MIN_A = 1.0, 1.0, 40.0, 0.03
DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}

def spline(k, N=24):
    P = k['points']; n = len(P); closed = k.get('closed', True); at = lambda i: P[i % n]
    def tan(i):
        p = at(i)
        if not p.get('smooth'): return (0.0, 0.0)
        pr = at(i - 1) if closed else P[max(0, i - 1)]; nx = at(i + 1) if closed else P[min(n - 1, i + 1)]
        return ((nx['u'] - pr['u']) / 6, (nx['v'] - pr['v']) / 6)
    out = []
    for s in range(n if closed else n - 1):
        a, b = at(s), at(s + 1); ta, tb = tan(s), tan(s + 1)
        M = 1 if (not a.get('smooth') and not b.get('smooth')) else N
        c1 = (a['u'] + ta[0], a['v'] + ta[1]); c2 = (b['u'] - tb[0], b['v'] - tb[1])
        for j in range(0 if s == 0 else 1, M + 1):
            t = j / M; m = 1 - t
            out.append((m**3 * a['u'] + 3*m*m*t*c1[0] + 3*m*t*t*c2[0] + t**3 * b['u'], m**3 * a['v'] + 3*m*m*t*c1[1] + 3*m*t*t*c2[1] + t**3 * b['v']))
    return np.array(out)
def circle(c, r, n=180): return np.array([[c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)] for i in range(n)])

def open_r(m, r):
    er = ndimage.distance_transform_edt(m) * H > r
    return ndimage.distance_transform_edt(~er) * H <= r

def height_map(J, d):
    """top surface z (nan = no material) of a z-plane drawn part, plus a mask of small round holes"""
    SK = {k['id']: k for k in J['state']['sketches']}; k = SK[d['sketch']]
    z0, T = k['plane']['offset'], d['thickness']
    o = spline(k); x0, y0 = o.min(0) - 3; x1, y1 = o.max(0) + 3
    xs = np.arange(x0, x1, H); ys = np.arange(y0, y1, H); X, Y = np.meshgrid(xs, ys); Q = np.c_[X.ravel(), Y.ravel()]
    def inside(p):
        bx0, by0 = p.min(0); bx1, by1 = p.max(0)
        i0, i1 = np.searchsorted(xs, bx0) - 1, np.searchsorted(xs, bx1) + 1; j0, j1 = np.searchsorted(ys, by0) - 1, np.searchsorted(ys, by1) + 1
        i0, j0 = max(i0, 0), max(j0, 0); m = np.zeros(X.shape, bool)
        sub = np.c_[X[j0:j1, i0:i1].ravel(), Y[j0:j1, i0:i1].ravel()]
        if len(sub): m[j0:j1, i0:i1] = MP(p).contains_points(sub).reshape(X[j0:j1, i0:i1].shape)
        return m
    body = inside(o); top = np.where(body, T, -1.0); bot = np.zeros(X.shape); drilled = np.zeros(X.shape, bool)
    for c in d.get('cuts', []) or []:
        D = T if c.get('depth') is None else min(T, max(0, c['depth']))
        if c['kind'] == 'pocket':
            kk = SK.get(c['sketch'])
            if not kk: continue
            m = inside(spline(kk))
        else:
            if not c.get('d'): continue
            m = inside(circle(c['at'], c['d'] / 2))
            if c['kind'] in DRILLED and c['d'] <= 3.2: drilled |= m
            if c.get('seat') and c['seat']['d'] > c['d']:
                ms = inside(circle(c['at'], c['seat']['d'] / 2)); sd = min(D, c['seat']['depth'])
                if c.get('from') == 'back': top = np.where(ms, np.minimum(top, T - sd), top)
                else: bot = np.where(ms, np.maximum(bot, sd), bot)
                if c['kind'] in DRILLED: drilled |= ms
        if c.get('from') == 'back': top = np.where(m, np.minimum(top, T - D), top)
        else: bot = np.where(m, np.maximum(bot, D), bot)
    mat = body & (top > bot + 1e-6)
    Z = np.where(mat, top + z0, np.nan)
    return Z, drilled, (x0, y0), z0

def findings(J, d):
    Z, drilled, (x0, y0), z0 = height_map(J, d)
    out = []
    lv = sorted(set(np.round(Z[~np.isnan(Z)], 3)))
    def blobs(mask, kind, level, extra=None):
        lab, n = ndimage.label(mask)
        if not n: return
        idx = np.arange(1, n + 1)
        area = ndimage.sum(np.ones_like(lab), lab, idx) * H * H
        com = ndimage.center_of_mass(mask, lab, idx)
        for a, (j, i) in zip(area, com):
            if a >= MIN_A: out.append(dict(kind=kind, level=round(float(level), 3), at=[round(x0 + i * H, 2), round(y0 + j * H, 2)], area=round(float(a), 3), **(extra or {})))
    # the footprint and every level: material standing above level L, air at or below it
    for L in [z0 - 1] + lv[:-1]:
        mat = np.nan_to_num(Z, nan=-1e9) > L + 1e-6
        air = ~mat
        thin = mat & ~open_r(mat, THIN_R)
        blobs(thin, 'thin', L)
        corner = air & ~open_r(air, CORNER_R) & ~ndimage.binary_dilation(drilled, iterations=3)
        # air outside the part's own outline is not a corner of the part (the outline's own corners are)
        blobs(corner, 'corner', L)
        if L > z0 - 1:
            lab, n = ndimage.label(mat)
            if n > 1:
                idx = np.arange(1, n + 1); area = ndimage.sum(np.ones_like(lab), lab, idx) * H * H; com = ndimage.center_of_mass(mat, lab, idx)
                for a, (j, i) in zip(area, com):
                    if MIN_A <= a < TOWER_A: out.append(dict(kind='tower', level=round(float(L), 3), at=[round(x0 + i * H, 2), round(y0 + j * H, 2)], area=round(float(a), 3)))
    return out, Z, (x0, y0), lv

if __name__ == '__main__':
    J = json.load(open(sys.argv[1]))
    ids = sys.argv[sys.argv.index('--parts') + 1].split(',') if '--parts' in sys.argv else [d['id'] for d in J['state']['drawn'] if d.get('mill')]
    res = {}
    for d in J['state']['drawn']:
        if d['id'] not in ids: continue
        f, Z, org, lv = findings(J, d)
        res[d['id']] = f
        by = {}
        for x in f: by[x['kind']] = by.get(x['kind'], 0) + 1
        print(d['id'], d['name'][:40], 'levels', lv, by or 'clean', flush=True)
        if '--png' in sys.argv:
            import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
            png = sys.argv[sys.argv.index('--png') + 1].replace('.png', f'_{d["id"]}.png')
            fig, ax = plt.subplots(figsize=(11, 11), dpi=100)
            ax.imshow(Z, origin='lower', extent=(org[0], org[0] + Z.shape[1] * H, org[1], org[1] + Z.shape[0] * H), cmap='viridis')
            mk = {'thin': ('o', 'white'), 'corner': ('s', 'cyan'), 'tower': ('^', 'magenta')}
            for x in f:
                m, c = mk[x['kind']]; ax.plot(*x['at'], m, mfc='none', mec='k', ms=11, mew=2.2); ax.plot(*x['at'], m, mfc='none', mec=c, ms=11, mew=1.2)
            ax.set_title(f"{d['name'][:60]}: thin o, corner s, tower ^", fontsize=9); plt.tight_layout(); plt.savefig(png); plt.close(fig)
    if '--json' in sys.argv: json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=0)
    print('TOTAL', sum(len(v) for v in res.values()))
