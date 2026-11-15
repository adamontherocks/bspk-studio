import json, math, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from geo import outline
a = json.load(open(sys.argv[1])); st = a['state']; out = sys.argv[2]
K = {k['id']: k for k in st['sketches']}; Dd = {d['id']: d for d in st['drawn']}; pos = st['pos']
M, C, H = pos['mwheel'], pos['center'], pos['hour']
fig, axs = plt.subplots(1, 2, figsize=(20, 7.5))
def poly(ax, k, **kw):
    o = outline(k); ax.plot([p[0] for p in o], [p[1] for p in o], **kw); return o
def circ(ax, c, r, **kw): ax.add_patch(plt.Circle(c, r, fill=False, **kw))
def cuts(ax, d, col):
    for c in d.get('cuts', []):
        if c['kind'] == 'pocket': poly(ax, K[c['sketch']], color=col, lw=0.8, ls='-.'); continue
        at = pos[c['axis']] if c.get('axis') else c['at']
        circ(ax, at, c['d'] / 2, color=col, lw=0.8, ls='-' if c.get('depth') is None else ':')
        if c.get('csk'): circ(ax, at, c['csk']['d'] / 2, color=col, lw=0.5)
        if c.get('seat'): circ(ax, at, c['seat']['d'] / 2, color=col, lw=0.5)
for ax, title in zip(axs, ['Motion layer z 26.05–29.35 (engineered): left bridge, P5 crescent, right top plate', 'P6 top plate (engineered): recesses, openings, screws; discs and gears']):
    poly(ax, K['K1'], color='0.75', lw=1, ls='--'); ax.set_aspect('equal'); ax.set_title(title, fontsize=10); ax.grid(alpha=0.2); ax.set_xlim(-66, 66); ax.set_ylim(-44, 44)
    for nm, p in [('C', C), ('M', M), ('H', H)]: ax.plot(*p, 'k+', ms=10); ax.annotate(nm, p, xytext=(3, 3), textcoords='offset points')
ax = axs[0]
for did, col in [('D8', 'tab:green'), ('D5', 'tab:blue'), ('D7', 'tab:orange')]:
    o = poly(ax, K[Dd[did]['sketch']], color=col, lw=1.5, label=f"{did} {Dd[did]['name']}"); ax.fill([p[0] for p in o], [p[1] for p in o], color=col, alpha=0.15); cuts(ax, Dd[did], col)
    for q in K[Dd[did]['sketch']]['points']: ax.plot(q['u'], q['v'], 'o', ms=1.8 if q['smooth'] else 3.5, color=col, mfc='white' if q['smooth'] else col)
circ(ax, M, 24.7, color='k', lw=1); circ(ax, C, 7.3, color='k', lw=1)
ax.legend(loc='lower left', fontsize=8)
ax = axs[1]
o = poly(ax, K['K9'], color='tab:purple', lw=1.5, label='P6'); cuts(ax, Dd['D6'], 'tab:purple')
circ(ax, H, 21.7, color='k', lw=1); circ(ax, M, 8.3, color='k', lw=1); circ(ax, C, 7.3, color='k', lw=1)
circ(ax, C, 23.75, color='tab:red', lw=1.2); circ(ax, H, 23.75, color='tab:red', lw=1.2)
ax.legend(loc='lower left', fontsize=8)
plt.tight_layout(); plt.savefig(out, dpi=110); print('saved', out)
