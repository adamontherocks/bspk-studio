# The gates every pass runs before anything is loaded into Adam's tab (2026-11-22; until then a scratch script). One command, one table.
#   python3 gates.py SCENE.json [BASE.json] [--z1]
#     overlaps     plate pairs sharing material at any height (none allowed)
#     hairlines    slivers the sim would draw (hairline_check, every milled part)
#     clean        thin walls, points and towers (clean_check), and against BASE what is new and what went
#     flow         breaks in a wall's flow seen from above (flow.scan)
#     walls        per plate: mm of one wall drawn twice across heights (a defect) and of ledges tapering into a wall (kept),
#                  as the sim's Walls check counts them (tapers.py)
#     creases      per plate: notches of 1 µm or more the sim shades as a line down a wall, and kinks where a wall leaves the one below
#     z1           (--z1, about a minute) the Made-on-the-Z1 proof (produce.py --no-write)
#   The sim's own checks (clashes, timekeeping, escapement) run in the browser: Run checks in the scratch copy, then in Adam's tab.
import json, sys, os, subprocess
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pyclipper as pc
import walls as W, hairline_check as HC, flow as FL, clean_check as CC, tapers as TP, creases as CR
from pk2 import inter, S

PLATES = ('D1', 'D3', 'D6', 'D29', 'D5', 'D2')

def overlaps(J):
    sl = {p: W.slabs(J, p) for p in PLATES}; out = []
    for i, a in enumerate(PLATES):
        for b in PLATES[i + 1:]:
            for za, zb, ma in sl[a]:
                for zc, zd, mb in sl[b]:
                    if min(zb, zd) - max(za, zc) < 1e-4: continue
                    area = sum(abs(pc.Area(q)) for q in inter(ma, mb)) / S / S
                    if area > 1e-3: out.append((a, b, round(max(za, zc), 2), round(area, 4)))
    return out

def clean(J):
    r = {}
    for d in J['state']['drawn']:
        if d['id'] in PLATES:
            r[d['id']] = sorted((x['kind'], round(x['at'][0]), round(x['at'][1])) for x in CC.findings(J, d)[0])
    return r

def run(J, B=None, z1_path=None):
    rows = []
    ov = overlaps(J); rows.append(('overlaps', 'none' if not ov else ov))
    hl = {d['id']: len(HC.check(J, d['id'])) for d in J['state']['drawn'] if d.get('mill') and d.get('cuts')}
    rows.append(('hairlines', sum(hl.values()) if not sum(hl.values()) else {k: v for k, v in hl.items() if v}))
    c = clean(J)
    if B:
        cb = clean(B)
        rows.append(('clean', {k: f"{len(v)} (base {len(cb.get(k, []))}, new {len([x for x in v if x not in cb.get(k, [])])}, gone {len([x for x in cb.get(k, []) if x not in v])})" for k, v in c.items()}))
    else:
        rows.append(('clean', {k: len(v) for k, v in c.items()}))
    fl = FL.scan(J); rows.append(('flow', f"{len(fl)} {dict(Counter(f['pid'] for f in fl))}"))
    wl = {}
    for pid in ('D3', 'D1'):
        _, tot = TP.summary(J, pid)
        wl[pid] = f"drawn twice {tot.get('copy', 0) + tot.get('cross', 0):.1f} mm, tapers {tot.get('taper', 0) + tot.get('shoulder', 0):.1f} mm"
    rows.append(('walls', wl))
    cr = {}
    for pid in ('D3', 'D1'):
        rr = CR.detail(J, pid)
        cr[pid] = f"notches >=1 um {sum(1 for r in rr if r[0] == 'notch' and r[2] and r[2][0] >= 1)}, kinks {sum(1 for r in rr if r[0] == 'kink')}"
    rows.append(('creases', cr))
    if z1_path:
        out = subprocess.run([sys.executable, os.path.join(HERE, 'produce.py'), '--json', z1_path, '--no-write'], capture_output=True, text=True).stdout
        tail = [l for l in out.splitlines() if l.strip()][-1:] or ['(no output)']
        rows.append(('z1', tail[0][:300]))
    return rows

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    J = json.load(open(args[0])); B = json.load(open(args[1])) if len(args) > 1 else None
    for k, v in run(J, B, args[0] if '--z1' in sys.argv else None): print(f'{k:10s} {v}')
