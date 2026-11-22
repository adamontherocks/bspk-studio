# Drawing kit for movement concepts: signed-distance bridges (smooth, tangent blends) + vector wheels, hands, jewels, screws.
import math, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, PathPatch
from matplotlib.path import Path
L = 70; N = 1150
xs = np.linspace(-L, L, N); X, Y = np.meshgrid(xs, xs)
PAL = dict(page='#141619', case='#2b2f35', plate='#8b8378', well='#6c655b', bridge='#c3c6c9', bedge='#565b61', bevel='#f3f4f5',
           gold='#c9a24a', goldd='#86662a', steel='#9aa0a6', steeld='#5d6268', ruby='#9e2139', chaton='#d8b86e', screw='#2a2e34',
           blue='#2d4c8c', bluel='#a9bde3', ink='#3b4047', paper='#e9e4d8')
def pol(c, r, a): return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
# ---------- distance fields ----------
def circle(c, r): return np.hypot(X - c[0], Y - c[1]) - r
def seg(a, b, r):
    ax_, ay_ = b[0] - a[0], b[1] - a[1]; L2 = ax_ * ax_ + ay_ * ay_
    t = np.clip(((X - a[0]) * ax_ + (Y - a[1]) * ay_) / L2, 0, 1)
    return np.hypot(X - (a[0] + ax_ * t), Y - (a[1] + ay_ * t)) - r
def taper(a, b, ra, rb):
    ax_, ay_ = b[0] - a[0], b[1] - a[1]; L2 = ax_ * ax_ + ay_ * ay_
    t = np.clip(((X - a[0]) * ax_ + (Y - a[1]) * ay_) / L2, 0, 1)
    return np.hypot(X - (a[0] + ax_ * t), Y - (a[1] + ay_ * t)) - (ra + (rb - ra) * t)
def curve(pts, ra, rb=None):           # a tapered stroke along a polyline (smooth if the points are dense)
    rb = ra if rb is None else rb; d = None; n = len(pts) - 1
    for i in range(n):
        di = taper(pts[i], pts[i + 1], ra + (rb - ra) * i / n, ra + (rb - ra) * (i + 1) / n)
        d = di if d is None else np.minimum(d, di)
    return d
def bez(p0, p1, p2, p3, n=40):
    return [tuple((1-t)**3*np.array(p0) + 3*(1-t)**2*t*np.array(p1) + 3*(1-t)*t*t*np.array(p2) + t**3*np.array(p3)) for t in np.linspace(0, 1, n)]
def arcpts(c, r, a0, a1, n=60): return [pol(c, r, a0 + (a1 - a0) * k / n) for k in range(n + 1)]
def smin(a, b, k=3.0):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)
def smax(a, b, k=3.0): return -smin(-a, -b, k)
def U(*ds, k=3.0):
    d = ds[0]
    for e in ds[1:]: d = smin(d, e, k)
    return d
def cut(d, *holes, k=1.0):
    for h in holes: d = smax(d, -h, k)
    return d
def fill(ax, d, color, z, edge=None, bevel=True, alpha=1.0):
    ax.contourf(X, Y, d, levels=[-1e9, 0], colors=[color], zorder=z, alpha=alpha)
    ax.contour(X, Y, d, levels=[0], colors=[edge or PAL['bedge']], linewidths=0.9, zorder=z + 0.01)
    if bevel: ax.contour(X, Y, d, levels=[-0.55], colors=[PAL['bevel']], linewidths=1.0, alpha=0.85, zorder=z + 0.02)
# ---------- vector parts ----------
def ring(ax, c, ro, ri, color, z, edge=None, lw=0.6):
    t = np.linspace(0, 2 * math.pi, 180)
    outer = np.c_[c[0] + ro * np.cos(t), c[1] + ro * np.sin(t)]; inner = np.c_[c[0] + ri * np.cos(t[::-1]), c[1] + ri * np.sin(t[::-1])]
    verts = np.r_[outer, [outer[0]], inner, [inner[0]]]; codes = [Path.MOVETO] + [Path.LINETO] * 180 + [Path.MOVETO] + [Path.LINETO] * 180
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor=edge or 'none', lw=lw, zorder=z))
def teeth(c, z, m, rot=0.0, club=False):
    rp = m * z / 2; ra = rp + m; rf = rp - 1.15 * m; pts = []
    for k in range(z):
        a = rot + 360 * k / z; p = 360 / z
        if club: seq = [(rf, a - .5 * p), (ra, a - .05 * p), (ra, a + .12 * p), (rf + .3 * m, a + .3 * p)]
        else: seq = [(rf, a - .5 * p), (rf, a - .28 * p), (ra, a - .14 * p), (ra, a + .14 * p), (rf, a + .28 * p)]
        pts += [pol(c, r, ang) for r, ang in seq]
    return pts, rf
def wheel(ax, c, z, m=1.0, color=None, edge=None, spokes=5, z_=5, rot=0, hub=None, curl=28, club=False, solid=False, label=None):
    color = color or PAL['gold']; edge = edge or PAL['goldd']
    pts, rf = teeth(c, z, m, rot, club)
    rim_in = max(rf - max(2.2, 0.18 * rf), 0)
    if solid or rf < 7:
        ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=edge, lw=0.5, zorder=z_))
    else:
        # toothed rim as one path with a hole
        t = np.linspace(0, 2 * math.pi, 180); inner = np.c_[c[0] + rim_in * np.cos(t[::-1]), c[1] + rim_in * np.sin(t[::-1])]
        verts = np.r_[pts, [pts[0]], inner, [inner[0]]]; codes = [Path.MOVETO] + [Path.LINETO] * len(pts) + [Path.MOVETO] + [Path.LINETO] * 180
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor=edge, lw=0.5, zorder=z_))
        hr = hub or max(2.5, 0.16 * rf)
        for s in range(spokes):
            a0 = rot + 360 * s / spokes; cen = []
            for t_ in np.linspace(0, 1, 24):
                r = hr + (rim_in + 0.6 - hr) * t_; cen.append(pol(c, r, a0 + curl * math.sin(math.pi * t_ / 1.0) * (1 - t_) + curl * t_ * 0.0 + curl * t_ ** 1.5))
            w0, w1 = 1.5, 1.0; left, right = [], []
            for i, p in enumerate(cen):
                q = cen[min(i + 1, len(cen) - 1)] if i < len(cen) - 1 else cen[i]; o = cen[i - 1] if i else cen[0]
                dx, dy = q[0] - o[0], q[1] - o[1]; L_ = math.hypot(dx, dy) or 1; nx, ny = -dy / L_, dx / L_; w = w0 + (w1 - w0) * i / (len(cen) - 1)
                left.append((p[0] + nx * w, p[1] + ny * w)); right.append((p[0] - nx * w, p[1] - ny * w))
            ax.add_patch(Polygon(left + right[::-1], closed=True, facecolor=color, edgecolor=edge, lw=0.4, zorder=z_))
        ax.add_patch(Circle(c, hr, facecolor=color, edgecolor=edge, lw=0.5, zorder=z_))
    if label: ax.text(c[0], c[1] - 0.2, label, fontsize=4.2, color='#2b2b2b', ha='center', va='center', zorder=z_ + 0.5)
def pinion(ax, c, z, m=1.0, z_=6): wheel(ax, c, z, m, color=PAL['steel'], edge=PAL['steeld'], solid=True, z_=z_)
def jewel(ax, c, z_=20, r=1.25):
    ax.add_patch(Circle(c, r + 0.8, facecolor=PAL['chaton'], edgecolor='#8a7440', lw=0.4, zorder=z_))
    ax.add_patch(Circle(c, r, facecolor=PAL['ruby'], edgecolor='#5e1222', lw=0.3, zorder=z_ + 0.1))
    ax.add_patch(Circle((c[0] - 0.35, c[1] + 0.35), 0.35, facecolor='#e6a3b0', edgecolor='none', zorder=z_ + 0.2))
def screw(ax, c, ang=35, z_=20, r=1.7):
    ax.add_patch(Circle(c, r, facecolor=PAL['blue'], edgecolor='#16243f', lw=0.5, zorder=z_))
    a = math.radians(ang); ax.plot([c[0] - r * .8 * math.cos(a), c[0] + r * .8 * math.cos(a)], [c[1] - r * .8 * math.sin(a), c[1] + r * .8 * math.sin(a)], color='#0d1526', lw=1.0, zorder=z_ + 0.1)
def hand(ax, piv, ang, length, tail=8, w=1.6, z_=30, color=None):
    color = color or PAL['blue']; a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    tip = (piv[0] + ux * length, piv[1] + uy * length); back = (piv[0] - ux * tail, piv[1] - uy * tail)
    pts = [tip, (piv[0] + nx * w + ux * length * 0.15, piv[1] + ny * w + uy * length * 0.15), (back[0] + nx * w * 0.9, back[1] + ny * w * 0.9),
           (back[0] - nx * w * 0.9, back[1] - ny * w * 0.9), (piv[0] - nx * w + ux * length * 0.15, piv[1] - ny * w + uy * length * 0.15)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=PAL['bluel'], lw=0.6, zorder=z_))
    ax.add_patch(Circle(back, w * 1.6, facecolor=color, edgecolor=PAL['bluel'], lw=0.6, zorder=z_))
    ax.add_patch(Circle(piv, 2.2, facecolor=color, edgecolor=PAL['bluel'], lw=0.6, zorder=z_ + 0.1)); ax.add_patch(Circle(piv, 0.8, facecolor='#0d1526', zorder=z_ + 0.2))
def balance(ax, c, r, z_=12, rot=20):
    ring(ax, c, r, r - 2.2, PAL['gold'], z_, edge=PAL['goldd'])
    for k in range(3):
        a = rot + 120 * k; p1 = pol(c, 2.5, a); p2 = pol(c, r - 1.6, a)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=PAL['gold'], lw=3.2, solid_capstyle='round', zorder=z_)
    for k in range(8):
        p = pol(c, r - 1.1, rot + 22.5 + 45 * k); ax.add_patch(Circle(p, 0.85, facecolor='#d9bf7a', edgecolor=PAL['goldd'], lw=0.3, zorder=z_ + 0.1))
    th = np.linspace(0, 2 * math.pi * 9, 900); rr = 2.6 + (r * 0.52 - 2.6) * th / th[-1]
    ax.plot(c[0] + rr * np.cos(th + 0.7), c[1] + rr * np.sin(th + 0.7), color='#d7dde3', lw=0.45, zorder=z_ + 0.2)
def scale_arc(ax, c, r0, a0, a1, n=60, major=5, labels=None, z_=24, inward=False, length=(1.8, 3.6), fs=5.5, rl=None):
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n; L_ = length[1] if k % major == 0 else length[0]; s = -1 if inward else 1
        p1 = pol(c, r0, a); p2 = pol(c, r0 + s * L_, a)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=PAL['ink'], lw=0.9 if k % major == 0 else 0.5, zorder=z_)
    if labels:
        for k, t in labels.items():
            a = a0 + (a1 - a0) * k / n; p = pol(c, rl or (r0 + (length[1] + 2.6) * (-1 if inward else 1)), a)
            ax.text(p[0], p[1], t, fontsize=fs, color=PAL['ink'], ha='center', va='center', rotation=a - 90, zorder=z_, family='serif')
def window(ax, c, w, h, ang, text, z_=26, fs=9):
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux; pts = []
    rr = min(w, h) * 0.32
    for cx_, cy_, a0 in [(w/2 - rr, h/2 - rr, 0), (-w/2 + rr, h/2 - rr, 90), (-w/2 + rr, -h/2 + rr, 180), (w/2 - rr, -h/2 + rr, 270)]:
        for k in range(8):
            t = math.radians(a0 + 90 * k / 7); px, py = cx_ + rr * math.cos(t), cy_ + rr * math.sin(t)
            pts.append((c[0] + px * ux + py * nx, c[1] + px * uy + py * ny))
    ax.add_patch(Polygon(pts, closed=True, facecolor=PAL['paper'], edgecolor=PAL['bedge'], lw=1.2, zorder=z_))
    ax.text(c[0], c[1], text, fontsize=fs, color='#1b1d20', ha='center', va='center', rotation=0, zorder=z_ + 0.1, family='serif', weight='bold')
def page(title, sub):
    fig = plt.figure(figsize=(7.2, 8.2), dpi=170); fig.patch.set_facecolor(PAL['page'])
    ax = fig.add_axes([0.02, 0.12, 0.96, 0.84]); ax.set_xlim(-L, L); ax.set_ylim(-L, L); ax.set_aspect('equal'); ax.axis('off')
    fig.text(0.05, 0.965, title, color='#eceae5', fontsize=15, family='serif', weight='bold', va='top')
    fig.text(0.05, 0.095, sub, color='#b9b6ae', fontsize=6.9, va='top', linespacing=1.5)
    ring(ax, (0, 0), 63.5, 60.4, PAL['case'], 1, edge='#4a4f56')
    return fig, ax
