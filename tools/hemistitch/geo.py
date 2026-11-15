import json, math
def pt_at(P, closed, s, t):
    n = len(P); at = lambda i: P[i % n]
    def tan(i):
        p = at(i)
        if not p.get('smooth'): return (0, 0)
        prev = at(i - 1) if closed else P[max(0, i - 1)]; nxt = at(i + 1) if closed else P[min(n - 1, i + 1)]
        return ((nxt['u'] - prev['u']) / 6, (nxt['v'] - prev['v']) / 6)
    a, b = at(s), at(s + 1); ta, tb = tan(s), tan(s + 1); m = 1 - t
    c1 = (a['u'] + ta[0], a['v'] + ta[1]); c2 = (b['u'] - tb[0], b['v'] - tb[1])
    return (m**3*a['u'] + 3*m*m*t*c1[0] + 3*m*t*t*c2[0] + t**3*b['u'], m**3*a['v'] + 3*m*m*t*c1[1] + 3*m*t*t*c2[1] + t**3*b['v'])
def outline(k):
    P = k['points']; n = len(P); out = []
    segs = n if k['closed'] else n - 1
    for s in range(segs):
        a, b = P[s], P[(s + 1) % n]; N = 1 if not a.get('smooth') and not b.get('smooth') else 24
        for j in range(0 if s == 0 else 1, N + 1): out.append(pt_at(P, k['closed'], s, j / N))
    return out
