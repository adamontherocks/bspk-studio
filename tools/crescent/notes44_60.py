# Adam's notes P44-P60 (2026-11-19), the clean-up half (the crown and the escape wheel come after):
#   - the main plate's outline back where it was (an accidental drag moved it +2.38, +9.02 and left its cuts behind)
#   - the crescent rim plate's screw 2 moved 0.5 mm off the balance side window (its pilot left a 1.8 mm wall)
#   - the main plate's levels rebuilt from the cuts that do a job (plate_clean.py): every old patch goes
#   - the motion-works plate's edge rounded and faired, and its levels rebuilt the same way
#   apply(J, log)       python3 notes44_60.py IN.json OUT.json
import json, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import plate_clean as PC
from pk2 import spline_poly

def recentre_main_plate(J, log):
    st = J['state']; SK = {k['id']: k for k in st['sketches']}
    d = next(x for x in st['drawn'] if x['name'] == 'Main plate'); k = SK[d['sketch']]
    q = np.array([(p['u'], p['v']) for p in k['points']], float)          # its dots all sit on one circle: fit its centre
    A = np.c_[2 * q, np.ones(len(q))]; c = np.linalg.lstsq(A, (q ** 2).sum(1), rcond=None)[0][:2]
    if np.hypot(*c) < 0.01: return
    for p in k['points']: p['u'] = round(p['u'] - c[0], 4); p['v'] = round(p['v'] - c[1], 4)
    log.append(f'main plate outline moved back by ({-c[0]:.2f}, {-c[1]:.2f}) to the movement centre')

def nudge_screw(J, log, name='Screw · crescent rim plate 2', pilot='Screw pilot · crescent rim plate 2', dy=-0.5):
    hits = [c for d in J['state']['drawn'] for c in (d.get('cuts') or []) if (c.get('name') or '').startswith((name, pilot))]
    if not hits or abs(hits[0]['at'][1] + 8.6099) > 1e-3: return
    for c in hits: c['at'] = [c['at'][0], round(c['at'][1] + dy, 4)]
    log.append(f'crescent rim plate screw 2 moved {abs(dy)} mm away from the balance side window ({len(hits)} holes)')

def barrel_slot(J, log):
    """P47-P49: the slot over the barrel redrawn from its r 3 end: a straight left wall keeping Adam's taper (tangent to the
    end), a straight right wall, both blended r 1.5 into the big opening; the hand-drawn wobbles and two hooks go"""
    import math, pyclipper as pc, refit as RF
    from pk2 import P, F, union, diff, inter, opening, circle
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == 'D3'); k = next(s for s in st['sketches'] if s['id'] == d['sketch'])
    if len(k['points']) > 100 and not any(q.get('smooth') for q in k['points']): return   # already redrawn (exact)
    M = union([P(spline_poly(k['points']))])
    c, r = (-14.58, 33.5), 3.0
    dv = np.array([2.75, -7.5]); dv /= np.hypot(*dv); nv = np.array([-dv[1], dv[0]]) * -1           # down the left wall; its outward normal
    if nv[0] > 0: nv = -nv
    t0 = np.array(c) + r * nv; t1 = t0 + dv * (t0[1] - 23.0) / -dv[1]
    slot = union([circle(c, r)], [P([t0, t1, (-11.58, 23.0), (-11.58, c[1])])])
    fill = [P([(-18.6, 25.6), (-11.0, 25.6), (-11.0, 37.0), (-18.6, 37.0)])]
    M2 = diff(union(M, fill), slot)
    box = [P([(-20.5, 22.5), (-7.5, 22.5), (-7.5, 38.5), (-20.5, 38.5)])]
    M3 = diff(M2, inter(diff(M2, opening(M2, 1.5)), box))
    big = max([p for p in M3 if pc.Orientation(p)], key=lambda p: abs(pc.Area(p)))
    Pn = F(big); L = np.hypot(*(np.roll(Pn, -1, 0) - Pn).T); keep = [Pn[0]]
    for q in Pn[1:]:
        if np.hypot(*(q - keep[-1])) >= 0.3: keep.append(q)
    from pk2 import simplify as _simp
    lp = _simp(np.vstack([F(big), F(big)[:1]]), 0.003)[:-1]
    k['points'] = [{'u': round(float(x), 4), 'v': round(float(y), 4), 'smooth': False} for x, y in lp]   # exact (a fitted spline hooked here: P67)
    log.append(f'barrel slot (P47-P49): redrawn 6 wide from its r 3 end, straight walls (the left keeps its taper), blended r 1.5 into the opening; outline now {len(k["points"])} dots')

def apply(J, log):
    recentre_main_plate(J, log)
    nudge_screw(J, log)
    PC.apply(J, log, 'D1')
    PC.clean_outline(J, log, 'D3')
    barrel_slot(J, log)
    PC.rebuild(J, log, 'D3')

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; apply(J, log); print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
