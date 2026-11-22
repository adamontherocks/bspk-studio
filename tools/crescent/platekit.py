# Shared geometry for engineering Adam's plate edits in a scene file (rasters at 0.05 mm, smooth outlines back out).
# Used by staircase.py (and the same helpers rework.py carries inline).
import json, math, os, sys
import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MP
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import refit as RF

H = 0.05
xs = np.arange(-70.0, 70.0 + H / 2, H); GX, GY = np.meshgrid(xs, xs)
def ij(x, y): return int(round((y + 70) / H)), int(round((x + 70) / H))
def poly_of(dots, N=32): return RF.spline([(q['u'], q['v'], bool(q.get('smooth'))) for q in dots], N=N)
def raster(poly):
    poly = np.asarray(poly); a, b = poly.min(0), poly.max(0)
    i0, j0 = max(0, int((a[1] + 70) / H) - 2), max(0, int((a[0] + 70) / H) - 2)
    i1, j1 = min(len(xs), int((b[1] + 70) / H) + 3), min(len(xs), int((b[0] + 70) / H) + 3)
    m = np.zeros(GX.shape, bool)
    if i1 > i0 and j1 > j0:
        m[i0:i1, j0:j1] = MP(poly).contains_points(np.c_[GX[i0:i1, j0:j1].ravel(), GY[i0:i1, j0:j1].ravel()]).reshape(i1 - i0, j1 - j0)
    return m
def disc(c, r): return np.hypot(GX - c[0], GY - c[1]) <= r
def dilate(m, r): return ndimage.distance_transform_edt(~m) * H <= r
def erode(m, r): return ndimage.distance_transform_edt(m) * H > r
def close(m, r): return erode(dilate(m, r), r)
def opening(m, r): return dilate(erode(m, r), r)
def loops(m, min_area=0.3, sigma=3.0):   # the mask's edge as smooth loops (contoured on a smoothed distance field, not the pixel steps)
    sdf = (ndimage.distance_transform_edt(~m) - ndimage.distance_transform_edt(m)) * H
    sdf = ndimage.gaussian_filter(sdf, sigma)
    cs = plt.contour(GX, GY, sdf, levels=[0.0]); segs = cs.allsegs[0]; plt.close('all'); out = []
    for sg in segs:
        sg = np.asarray(sg)
        if len(sg) < 6: continue
        ar = 0.5 * (np.dot(sg[:, 0], np.roll(sg[:, 1], 1)) - np.dot(sg[:, 1], np.roll(sg[:, 0], 1)))
        if abs(ar) >= min_area: out.append((sg, abs(ar)))
    return out
def rdp(P, eps):                       # Douglas-Peucker on a closed loop (pocket outlines: sharp dots, exact to eps)
    P = np.asarray(P)
    def rec(a, b):
        if b <= a + 1: return [a]
        seg = P[b] - P[a]; L = np.hypot(*seg) or 1e-12
        d = np.abs(seg[0] * (P[a + 1:b, 1] - P[a, 1]) - seg[1] * (P[a + 1:b, 0] - P[a, 0])) / L
        k = int(np.argmax(d))
        if d[k] > eps: return rec(a, a + 1 + k) + rec(a + 1 + k, b)
        return [a]
    n = len(P); far = int(np.argmax(np.hypot(*(P - P[0]).T)))
    return P[sorted(set(rec(0, far) + rec(far, n - 1) + [n - 1]))]
def ccw(P):
    P = np.asarray(P, float); a = 0.5 * (np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
    return P if a >= 0 else P[::-1]
def dots_sharp(P): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in ccw(P)]
def dots_smooth(P): return [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': True} for x, y in P]
def rot(P, c, a_deg):
    a = math.radians(a_deg); ca, sa = math.cos(a), math.sin(a); P = np.asarray(P, float) - c
    return np.c_[P[:, 0] * ca - P[:, 1] * sa, P[:, 0] * sa + P[:, 1] * ca] + c

class Scene:
    def __init__(self, J):
        self.J = J; self.st = J['state']; self.pr = J['project']; self.mech = self.pr['mechanisms']
        self.SK = {k['id']: k for k in self.st['sketches']}
    @property
    def DR(self): return {d['id']: d for d in self.st['drawn']}
    def byname(self, prefix): return next(d for d in self.st['drawn'] if d['name'].startswith(prefix))
    def zband(self, d):
        z = self.SK[d['sketch']]['plane']['offset']; return (z, z + d['thickness'])
    def outline(self, d, N=32): return poly_of(self.SK[d['sketch']]['points'], N)
    def add_sketch(self, name, dots, z=0.0):
        n = 1
        while f'K{n}' in self.SK: n += 1
        k = {'id': f'K{n}', 'name': name, 'plane': {'axis': 'z', 'offset': z}, 'closed': True, 'points': dots}
        self.st['sketches'].append(k); self.SK[k['id']] = k; return k['id']
    def next_cut_id(self, d):
        n = 1; used = {c['id'] for c in d.get('cuts', [])}
        while f'h{n}' in used: n += 1
        return f'h{n}'
    def pocket_cut(self, d, name, poly, depth, frm='back'):
        kid = self.add_sketch(f'{name} (pocket outline)', dots_sharp(rdp(np.vstack([poly, poly[:1]]), 0.03)[:-1]))
        d.setdefault('cuts', []).append({'id': self.next_cut_id(d), 'kind': 'pocket', 'name': name, 'from': frm, 'depth': round(depth, 3), 'sketch': kid, 'seat': None, 'csk': None})
    def remove_parts(self, ids):
        dead = [d for d in self.st['drawn'] if d['id'] in ids]
        sk = {d['sketch'] for d in dead} | {c['sketch'] for d in dead for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
        self.st['drawn'] = [d for d in self.st['drawn'] if d['id'] not in ids]
        used = {d['sketch'] for d in self.st['drawn']} | {c['sketch'] for d in self.st['drawn'] for c in d.get('cuts', []) if c.get('kind') == 'pocket'}
        self.st['sketches'] = [k for k in self.st['sketches'] if k['id'] in used or k['id'] not in sk]
        self.SK = {k['id']: k for k in self.st['sketches']}
