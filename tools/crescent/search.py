import math, itertools, json, sys
def pol(c, r, a): return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
R_EDGE = float(sys.argv[1]) if len(sys.argv) > 1 else 61.0
TIP = lambda z: z / 2 + 0.7
Bc = (-22.0, 6.0); F = pol(Bc, 17.0, -52); E = pol(F, 12.0, -12)
chain = [('Fo', 24.0, 18.7), ('I', 30.0, 24.7), ('T', 28.5, 23.2), ('C', 30.0, 24.7), ('B', 27.0, 21.7)]   # name, distance from previous, tip radius
fixed = {'Bc': (Bc, 17.0), 'F': (F, 12.0), 'E': (E, 8.0)}
best = []
def ok(name, p, r, placed, prev):
    if math.hypot(*p) + r > R_EDGE: return False
    for n2, (q, r2) in placed.items():
        if n2 == prev: continue
        d = math.dist(p, q)
        if d < max(r, r2) + 2.0: return False        # an arbor may not sit inside another's wheel (plus 2 mm)
    return True
def dfs(i, placed, prev, score):
    if i == len(chain):
        best.append((score, dict(placed))); return
    name, dist, r = chain[i]; pp = placed[prev][0]
    for a in range(0, 360, 4):
        p = pol(pp, dist, a)
        if not ok(name, p, r, placed, prev): continue
        s = score + math.hypot(*p) * 0.2 + (max(0, -p[0] - 4) * 3 if name in ('I', 'T', 'C', 'B') else 0)
        placed[name] = (p, r); dfs(i + 1, placed, name, s); del placed[name]
dfs(0, dict(fixed), 'E', 0.0)
best.sort(key=lambda x: x[0])
print('solutions', len(best), 'edge', R_EDGE)
for s, pl in best[:5]:
    print(round(s, 1), {k: tuple(round(v, 1) for v in pl[k][0]) for k in ('Fo', 'I', 'T', 'C', 'B')})
if best: json.dump({k: v[0] for k, v in best[0][1].items()}, open('search_best.json', 'w'))
