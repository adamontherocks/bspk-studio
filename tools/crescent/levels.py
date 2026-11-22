# Assign each mesh a height so that gears overlapping in plan never share a level (module 1, every gear 2.0 thick).
import json, math, itertools, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = {k: tuple(v) for k, v in json.load(open(os.path.join(HERE, 'search_best.json'))).items()}
def pol(c, r, a): return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
P['K'] = pol(P['C'], 30.0, -30)
tip = lambda z, x: z / 2 + 1 + x
G = {  # gear: (arbor, tip radius)
 'barrel_teeth': ('B', tip(42, -.3)), 'center_pinion': ('C', tip(12, .3)), 'center_wheel': ('C', tip(48, -.3)),
 'third_pinion': ('T', tip(12, .3)), 'third_wheel': ('T', tip(45, -.3)), 'inter_pinion': ('I', tip(12, .3)), 'inter_wheel': ('I', tip(48, -.3)),
 'fourth_pinion': ('Fo', tip(12, .3)), 'fourth_wheel': ('Fo', tip(36, -.3)), 'escape_pinion': ('E', tip(12, .3)), 'escape_wheel': ('E', 8.6)}
stages = {'s_bc': ('barrel_teeth', 'center_pinion'), 's_ct': ('center_wheel', 'third_pinion'), 's_ti': ('third_wheel', 'inter_pinion'), 's_if': ('inter_wheel', 'fourth_pinion'), 's_fe': ('fourth_wheel', 'escape_pinion')}
LV = [4.6, 7.2, 9.8, 12.4]; T_ = 2.0; GAP = 0.5; DRUM = 5.0
best = None
for combo in itertools.product(range(len(LV)), repeat=len(stages) + 1):           # + the escape wheel's own level
    z = {}
    for (sid, gs), li in zip(stages.items(), combo): z[gs[0]] = z[gs[1]] = LV[li]
    z['escape_wheel'] = LV[combo[-1]]
    ok = True
    span = {g: (z[g], z[g] + (DRUM if g == 'barrel_teeth' else T_)) for g in G}
    for g1, g2 in itertools.combinations(G, 2):
        a1, r1 = G[g1]; a2, r2 = G[g2]
        partners = any(set(s) == {g1, g2} for s in stages.values())
        if partners: continue
        if a1 == a2:
            if not (span[g1][1] + 0.1 <= span[g2][0] or span[g2][1] + 0.1 <= span[g1][0]): ok = False; break
            continue
        if math.dist(P[a1], P[a2]) < r1 + r2 + GAP and not (span[g1][1] + GAP <= span[g2][0] or span[g2][1] + GAP <= span[g1][0]): ok = False; break
    if not ok: continue
    top = max(v[1] for v in span.values())
    if best is None or top < best[0]: best = (top, dict(zip(list(stages) + ['escape_wheel'], [LV[i] for i in combo])))
print('best', best)
if best: json.dump(best[1], open(os.path.join(HERE, 'levels.json'), 'w'))
