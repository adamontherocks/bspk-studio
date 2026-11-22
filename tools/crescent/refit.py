# Refit drawn parts' outlines with as few dots as hold their shape, so a designer can edit them by hand.
# The generator traced every outline with a dot every 1-2 mm (100-190 dots on a bridge). This keeps each outline's shape
# (whatever it is now, the designer's edits included) and puts back the fewest smooth dots that reproduce it, on the sim's
# own curve: a closed Catmull-Rom spline through the dots (index.html outlinePointAt), sharp dots with no tangent.
#
#   python3 refit.py IN.json OUT.json [--tol 0.05] [--parts "Main plate,Barrel bridge,..."]
#
# Every new dot sits exactly on the old outline. A fit is accepted when no point of either curve is further than --tol from
# the other (both directions, sampled every 0.01 mm). Dots the old outline had as sharp corners stay sharp, at the same spot.
import json, math, sys
import numpy as np
from scipy.spatial import cKDTree

DEFAULT_PARTS = ['Main plate', 'Barrel bridge', 'Right bridge', 'Bottom bridge', 'Crescent', 'Crescent rim plate', 'Right rim plate',
                 'Hand cock', 'Setting plate', 'Keyless plate']

def spline(P, closed=True, N=24):
    """the sim's outline through dots P = [(u, v, smooth)], sampled N per segment (closed)"""
    n = len(P); out = []
    def tan(i):
        u, v, sm = P[i % n]
        if not sm: return (0.0, 0.0)
        a = P[(i - 1) % n]; b = P[(i + 1) % n]
        return ((b[0] - a[0]) / 6, (b[1] - a[1]) / 6)
    for s in range(n):
        a = P[s]; b = P[(s + 1) % n]; ta = tan(s); tb = tan(s + 1)
        c1 = (a[0] + ta[0], a[1] + ta[1]); c2 = (b[0] - tb[0], b[1] - tb[1])
        nn = N if (a[2] or b[2]) else 1
        for j in range(nn):
            t = j / nn; m = 1 - t
            out.append((m ** 3 * a[0] + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * b[0],
                        m ** 3 * a[1] + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * b[1]))
    return np.array(out)

def resample(poly, step):
    """a closed polyline resampled every `step` along its length; returns points and their arc positions"""
    p = np.vstack([poly, poly[:1]]); seg = np.hypot(*(p[1:] - p[:-1]).T); s = np.r_[0, np.cumsum(seg)]
    L = s[-1]; t = np.arange(0, L, step)
    x = np.interp(t, s, p[:, 0]); y = np.interp(t, s, p[:, 1])
    return np.c_[x, y], t, L

def two_way(A, B):
    """largest distance from any point of A to B and from any point of B to A (both densely sampled)"""
    da, _ = cKDTree(B).query(A); db, _ = cKDTree(A).query(B)
    return max(float(da.max()), float(db.max()))

R_SHARP, NEAR, TOL_TIP = 1.0, 1.0, 0.35   # a bend tighter than r 1 is a tip: a sharp dot there, and 0.35 mm of give within 1 mm of it

def fit(points, tol=0.05):
    P0 = [(q['u'], q['v'], bool(q.get('smooth'))) for q in points]
    T, _, L = resample(spline(P0, N=64), 0.01)            # the shape to keep, every 0.01 mm
    Q, sQ, _ = resample(spline(P0, N=64), 0.05)          # where new dots may go, every 0.05 mm
    treeT = cKDTree(T); treeQ = cKDTree(Q)
    d1 = np.gradient(Q, axis=0); d2 = np.gradient(d1, axis=0)
    kap = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(np.hypot(*d1.T) ** 3, 1e-12)
    # sharp dots: the old sharp corners, and the tips of the outline (local peaks of bending tighter than R_SHARP, 1 mm apart at least)
    sharp = {int(treeQ.query((u, v))[1]) for u, v, sm in P0 if not sm}
    for i in np.argsort(-kap):
        if kap[i] < 1 / R_SHARP: break
        if all(min(abs(int(i) - j), len(Q) - abs(int(i) - j)) * 0.05 > NEAR for j in sharp): sharp.add(int(i))
    sharp = sorted(sharp)
    kap_s = np.convolve(np.r_[kap[-20:], kap, kap[:20]], np.ones(41) / 41, 'same')[20:-20]   # smoothed over 2 mm, for spacing
    tips = Q[sharp] if sharp else np.zeros((0, 2))
    nearT = (cKDTree(tips).query(T)[0] < NEAR) if len(tips) else np.zeros(len(T), bool)
    def err_of(idx, full=False):
        idx = sorted(set(idx)); P = [(Q[i][0], Q[i][1], i not in sharp) for i in idx]
        C = resample(spline(P, N=64), 0.01)[0]
        dc, _ = treeT.query(C); dt, _ = cKDTree(C).query(T)
        nearC = (cKDTree(tips).query(C)[0] < NEAR) if len(tips) else np.zeros(len(C), bool)
        e_far = max(float(dc[~nearC].max(initial=0)), float(dt[~nearT].max(initial=0)))
        e_tip = max(float(dc[nearC].max(initial=0)), float(dt[nearT].max(initial=0)))
        ok = e_far <= tol and e_tip <= TOL_TIP
        return (ok, e_far, e_tip) if full else ok
    def place(n, weight, phase):
        w = weight; cum = np.r_[0, np.cumsum((w[1:] + w[:-1]) / 2)]; tot = cum[-1] + (w[-1] + w[0]) / 2
        targets = (np.arange(n) + phase) * tot / n
        idx = set(np.searchsorted(cum, targets).clip(0, len(Q) - 1).tolist())
        idx = {i for i in idx if all(min(abs(i - j), len(Q) - abs(i - j)) > 6 for j in sharp)}   # no smooth dot crowding a tip
        return sorted(idx | set(sharp))
    # evenly spaced dots (plain, or closer where it bends) keep this spline well behaved (it loops where spacing jumps):
    # find the fewest that hold the shape, then drop and slide dots below
    def try_n(n):
        best_ = None
        for weight in (np.ones(len(Q)), 1.0 + np.sqrt(kap_s) * 6.0, 1.0 + np.sqrt(kap_s) * 12.0, 1.0 + np.sqrt(kap_s) * 24.0):
            for phase in (0.0, 0.25, 0.5, 0.75):
                cand = place(n, weight, phase)
                if (best_ is None or len(cand) < len(best_)) and err_of(cand): best_ = cand
        return best_
    lo, hi, found, n = 3, None, None, 8
    while n <= len(Q) // 4:
        f = try_n(n)
        if f is not None: hi, found = n, f; break
        lo = n; n = int(n * 1.25) + 1
    if found is None: raise SystemExit('no fit within tolerance')
    while hi - lo > 1:                        # the fewest that pass (passing isn't strictly monotone in n, but near enough)
        mid = (lo + hi) // 2; f = try_n(mid)
        if f is not None: hi, found = mid, f
        else: lo = mid
    best = found
    idx = best; changed = True                # then drop every dot the shape doesn't need
    while changed:
        changed = False
        for i in list(idx):
            if i in sharp or len(idx) <= 4: continue
            trial = [j for j in idx if j != i]
            if err_of(trial): idx = trial; changed = True
    # then harder: a dot that can't simply go may go if its two neighbours slide along the outline to make up for it.
    # Each trial is checked only where it changes the curve (four segments round each moved dot), then the whole outline once more.
    nQ = len(Q); treeTips = cKDTree(tips) if len(tips) else None
    def seg_pts(lst, p):
        m = len(lst); A = lambda k: lst[k % m]
        def tan(k):
            i = A(k)
            if i in sharp: return np.zeros(2)
            return (Q[A(k + 1)] - Q[A(k - 1)]) / 6
        a_, b_ = Q[A(p)], Q[A(p + 1)]; c1 = a_ + tan(p); c2 = b_ - tan(p + 1)
        if A(p) in sharp and A(p + 1) in sharp: c1, c2 = a_, b_
        N = max(24, int(np.hypot(*(b_ - a_)) / 0.02))
        t = np.linspace(0, 1, N, endpoint=False)[:, None]; mm = 1 - t
        return mm ** 3 * a_ + 3 * mm * mm * t * c1 + 3 * mm * t * t * c2 + t ** 3 * b_
    def window_ok(lst, pc):
        m = len(lst)
        C = np.vstack([seg_pts(lst, p) for p in range(pc - 2, pc + 2)])
        qa, qb = lst[(pc - 2) % m], lst[(pc + 2) % m]
        span = (qb - qa) % nQ
        ti = (np.arange(qa * 5, qa * 5 + span * 5) % len(T))
        dt, _ = cKDTree(C).query(T[ti]); allow_t = np.where(nearT[ti], TOL_TIP, tol)
        if (dt > allow_t).any(): return False
        dc, _ = treeT.query(C)
        nearC = (treeTips.query(C)[0] < NEAR) if treeTips is not None else np.zeros(len(C), bool)
        return not (dc > np.where(nearC, TOL_TIP, tol)).any()
    OFFS = [0, -8, 8, -16, 16, -30, 30]      # samples of 0.05 mm: up to 1.5 mm each way
    changed = True
    while changed:
        changed = False
        for i in list(idx):
            if i in sharp or len(idx) <= 6 or i not in idx: continue
            p = idx.index(i); trial = idx[:p] + idx[p + 1:]; m = len(trial)
            done = False
            for da in OFFS:
                for db in OFFS:
                    lst = list(trial); pa, pb = (p - 1) % m, p % m
                    if lst[pa] in sharp and da: continue
                    if lst[pb] in sharp and db: continue
                    na, nb = (lst[pa] + da) % nQ, (lst[pb] + db) % nQ
                    if na in lst and da or nb in lst and db: continue
                    lst[pa], lst[pb] = na, nb
                    if sorted(lst) != sorted(set(lst)): continue
                    order = sorted(range(m), key=lambda k: lst[k])
                    if [lst[k] for k in order] != sorted(lst) or order != sorted(order, key=lambda k: lst[k]): pass
                    lst = sorted(lst)
                    q = lst.index(na)
                    if all(window_ok(lst, q + o) for o in (-2, -1, 0, 1, 2)):
                        idx = lst; changed = True; done = True; break
                if done: break
    if not err_of(idx):                        # the local checks missed something at a window's edge: keep the plain result
        idx = best
        changed = True
        while changed:
            changed = False
            for i in list(idx):
                if i in sharp or len(idx) <= 4: continue
                trial = [j for j in idx if j != i]
                if err_of(trial): idx = trial; changed = True
    ok, e_far, e_tip = err_of(idx, True)
    if not ok: raise SystemExit('fit out of tolerance')      # never hand back a shape that doesn't hold
    return [{'u': round(float(Q[i][0]), 4), 'v': round(float(Q[i][1]), 4), 'smooth': i not in sharp} for i in idx], (e_far, e_tip, len(sharp)), L

def main():
    a = sys.argv[1:]
    src, dst = a[0], a[1]
    tol = float(a[a.index('--tol') + 1]) if '--tol' in a else 0.05
    names = a[a.index('--parts') + 1].split(',') if '--parts' in a else DEFAULT_PARTS
    J = json.load(open(src)); st = J['state']; SK = {k['id']: k for k in st['sketches']}
    for d in st['drawn']:
        if not any(d['name'] == n or d['name'].startswith(n + ' (') for n in names): continue
        if d.get('back') or d.get('edges'): print(f"  {d['name']}: has a back outline or joining-edge dots; left alone"); continue
        k = SK[d['sketch']]
        if not k.get('closed'): continue
        before = len(k['points'])
        pts, err, L = fit(k['points'], tol)
        k['points'] = pts
        print(f"  {d['name']}: {before} dots -> {len(pts)} ({err[2]} sharp tips; outline {L:.0f} mm; holds to {err[0]:.3f} mm, {err[1]:.3f} at the tips)")
    json.dump(J, open(dst, 'w'), indent=1, ensure_ascii=False)
    print('written', dst)

if __name__ == '__main__':
    main()
