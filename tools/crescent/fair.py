# Fair walls (2026-11-21, Adam: "radii should be smooth and consistent. if there is a sudden unusual radius change, that should
# be a flag"; "the user got this close, i see it, ill make it geometrically correct"). walls.py finds the spots; this redraws them.
#
# A back-milled plate is a stack of floor levels: A[i] = the plan region cut down to floor L[i] or deeper (outside the plate
# included), nested deepest first. Each level is redrawn as one fair wall, deepest first, inside a corridor:
#   must stay cut   = the level below (nesting) and the space every part needs in that height band (keepout.py), where cut now
#   must stay plate = a ring round every bearing, screw and pilot hole; the floor under a part that sits on it
# 1. small steps and bumps of plate (under BUMP_H tall) are smoothed out with a round of radius RB, so a wall that jogged now
#    eases across on a soft curve (Adam's own fix at the barrel slot: "i mostly flattened that wall to a softer curve")
# 2. narrow fingers and notches of cut (under 2 RO wide) are filled with plate, wherever no part needs the space
# 3. one family of radii: inside corners R_IN (the cutter: 1/8" through the plate, 2 mm on the ledges), outside corners R_OUT
# 4. a floor strip under STRIP wide between two levels (a wall that steps instead of running straight down) is closed: the upper
#    wall comes in to the lower one where no part needs the space, else the lower floor drops to meet the upper wall
# The result is written back as one exact pocket per piece per level (like plate_clean.rebuild), the outline from the through level.
import json, math, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, close, opening, circle, spline_poly, simplify, dots_sharp
import plate_clean as PC
import keepout as K

RB, BUMP_H, RO, R_OUT, R_IN_THRU, R_IN_LEDGE, STRIP = 3.0, 1.25, 2.0, 1.2, 1.6, 1.06, 1.5
RS, S_H, RC, C_H = 12.0, 1.2, 4.5, 1.0   # RC: inside corners close together on a short end are made one round (the end of a slot or lobe)
NOTE_WIN = None   # extra windows: Adam's wall notes (set by fair_plate from the scene's pins)
#         # gentle S-bends (a wall that wobbles on radii of 3-7 mm) eased to radii of at least RS, moving the wall under S_H
BOX = [P([[-200, -200], [200, -200], [200, 200], [-200, 200]])]
INNER = [P([[-120, -120], [120, -120], [120, 120], [-120, 120]])]   # (material is read inside this: easing may round the far box's corners)
def ar(q): return abs(pc.Area(q)) / S / S
def pos(a): return [q for q in a if pc.Orientation(q)]
def thinner(q, h):
    """the piece fits between two lines h apart somewhere along all of it (nothing in it is h thick)"""
    return not offset([q], -h / 2)

class Plate:
    def __init__(s, J, pid):
        s.J, s.pid = J, pid; st = J['state']; s.d = next(x for x in st['drawn'] if x['id'] == pid)
        s.k = next(x for x in st['sketches'] if x['id'] == s.d['sketch']); s.z0, s.T = s.k['plane']['offset'], s.d['thickness']
        SK = {x['id']: x for x in st['sketches']}
        s.pockets = [c for c in s.d.get('cuts') or [] if c['kind'] == 'pocket' and c.get('from') == 'back']
        s.rest = [c for c in s.d.get('cuts') or [] if c not in s.pockets]
        s.outline = union([P(spline_poly(s.k['points']))]); s.outside = diff(BOX, s.outline)
        by = {}
        for c in s.pockets:
            D = s.T if c.get('depth') is None else min(s.T, max(0.0, c['depth'])); L = round(s.T - D, 4)
            by.setdefault(L, []).append((PC.cut_paths(c, SK), c.get('name') or 'pocket'))
        s.by = by; s.L = sorted(by); prev = s.outside; s.A = []
        for L in s.L: prev = union(prev, *[p for p, _ in by[L]]); s.A.append(prev)
    def band(s, i): return s.z0 + s.L[i], s.z0 + (s.L[i + 1] if i + 1 < len(s.L) else s.T)
    def holes_ring(s, w=1.0):
        return union(*[[P(PC.ring_sim(c['at'], c['d'] / 2 + w))] for c in s.rest if c.get('at') and c.get('d')])

def flag_windows(A, rad=5.0):
    """where a level's wall jogs, hooks or turns on an unusual radius (walls.scan_loop): a window round each"""
    import walls as W
    pts = []
    for q in A:
        Q = F(q)
        if np.abs(Q).max() > 150 or ar(q) < 0.05: continue
        pts += [f['at'] for f in W.scan_loop(Q)]
    return union(*[[P(PC.ring_sim(p, rad))] for p in pts]) if pts else [], len(pts)

def fair_level(A, must_air, must_mat, r_in):
    """one level's cut region made fair inside its corridor; steps 1-2 only where the wall is flagged"""
    win, nflag = flag_windows(A)
    if NOTE_WIN: win = union(win, NOTE_WIN)
    ma = offset(must_air, 0.3) if must_air else []
    add, fill = [], []
    if win:
        # 1. small plate steps and bumps eased out on a radius RB
        add = [x for q in pos(diff(close(A, RB), A)) if thinner(q, BUMP_H) for x in pos(inter([q], win)) if ar(x) > 0.005]
        add = [x for x in add if not inter([x], must_mat)]
    A1 = union(A, add) if add else A
    if win:
        # 2. narrow fingers and notches of cut filled where nothing needs them
        for q in pos(inter(diff(A1, opening(A1, RO)), win)):
            fill += [x for x in pos(diff([q], ma)) if ar(x) > 0.02]
    A2 = diff(A1, fill) if fill else A1
    if win:
        # 2b. gentle S-bends: both halves eased to radius RS (plate taken off the bulge, put back in the hollow), only thin changes
        add2 = [x for q in pos(diff(close(A2, RS), A2)) if thinner(q, S_H) for x in pos(inter([q], win)) if ar(x) > 0.005 and not inter([x], must_mat)]
        A2 = union(A2, add2) if add2 else A2
        fill2 = [x for q in pos(diff(A2, opening(A2, RS))) if thinner(q, S_H) for x in pos(diff(inter([q], win), ma)) if ar(x) > 0.005]
        A2 = diff(A2, fill2) if fill2 else A2
        # 2c. the end of a lobe or slot with two small corners and a flat between: one round of radius RC
        fill3 = []
        for rc in (3.0, RC):
            f3 = [x for q in pos(diff(A2, opening(A2, rc))) if thinner(q, C_H) for x in pos(diff(inter([q], win), ma)) if ar(x) > 0.005]
            if f3: A2 = diff(A2, f3); fill3 += f3
        add += add2; fill += fill2 + fill3
    if fill:
        # where plate was put back round a part's space, the shoulders are blended (r 2.5) instead of left at the raw space
        bl = [x for x in pos(diff(inter(close(A2, 2.5), offset(fill, 1.5)), A2)) if thinner(x, 0.8) and not inter([x], must_mat)]
        if bl: A2 = union(A2, bl)
    # 3. one family of radii, kept inside the corridor
    A3 = A2; keep = diff(must_mat, A)
    for _ in range(2):
        A3 = union(close(opening(A3, r_in), R_OUT), must_air)
        if keep: A3 = diff(A3, keep)
    out = union(opening(close(A3, 0.1), 0.1), must_air)
    fair_level.last = (add, fill)
    return union(pc.CleanPolygons(out, 0.0015 * S)), len(add), len(fill), nflag

def strips(P_, F_, KO, MM):
    """floor strips under STRIP between level i and the level below: returns how many closed"""
    n = 0
    for i in range(1, len(F_)):
        ring = diff(F_[i], F_[i - 1])
        thin = [q for q in pos(diff(ring, opening(ring, STRIP / 2))) if ar(q) > 0.03]
        thin = [q for q in thin if inter(offset([q], 0.05), F_[i - 1])]      # only a step down beside the deeper level
        for q in thin:
            qq = inter(offset([q], 0.05), ring)
            if not inter(qq, KO[i]):
                F_[i] = diff(F_[i], qq); F_[i] = union(F_[i], F_[i - 1]); n += 1           # the upper wall comes in
            elif not inter(qq, MM[i - 1]):
                for j in range(i - 1, -1, -1):
                    if inter(qq, F_[j + 1]): F_[j] = union(F_[j], inter(qq, F_[j + 1]))
                    break
                n += 1                                                                    # the lower floor drops to it
    return n

def fair_plate(J, log, pid, rounds=2, start=None, pl=None, align=False, need=None):
    pl = pl or Plate(J, pid); st = J['state']
    nL = len(pl.L); KO, MM = [], []
    ring = pl.holes_ring(1.0)
    import walls as W
    NEIGH = {'D3': ['D6'], 'D6': ['D3']}.get(pid, [])
    NB = offset(union(*[m for n in NEIGH for _, _, m in W.slabs(J, n)]), K.EL['minGap']) if NEIGH else []
    for i in range(nL):
        za, zb = pl.band(i); ko = K.keepout(J, za, zb)
        KO.append(inter(ko, pl.A[i]))                                 # what a part needs and is cut now
        mm = inter(ring, diff(BOX, pl.A[i]))
        if i == 0:                                                    # the floor under a part that sits on the plate
            for d in st['drawn']:
                k = next((x for x in st['sketches'] if x['id'] == d['sketch']), None)
                if not k or d['id'] in K.PLATE_IDS or k['plane']['axis'] != 'z': continue
                if abs(k['plane']['offset'] - (pl.z0 + pl.L[1] if nL > 1 else -1)) < 0.01 or d['id'] == 'D29':
                    mm = union(mm, inter(union([P(spline_poly(k['points']))]), diff(BOX, pl.A[0])))
        MM.append(mm)
    F_ = list(start or pl.A); tot = dict(bumps=0, fills=0, strips=0)
    global NOTE_WIN
    WALL_NOTES = {'unecessary', 'unnecessary', 'irregular', 'uneven', 'bump', 'indent', 'protrusion', 'overlap', 'align', 'walls'}
    pts = [(p['w'][:2], max(2.0, p.get('r', 1)) + 2.0) for p in st['pins'] if p.get('part') == pid and any(w in (p.get('note') or '').lower() for w in WALL_NOTES)]
    NOTE_WIN = union(*[[P(PC.ring_sim(c, r))] for c, r in pts]) if pts else None
    def contact(q, A):
        return sum(abs(pc.Area(x)) for x in inter(diff(offset([q], 0.06), [q]), A))
    for r in range(rounds):
        # shallowest first: a step or bump eased on a wall shared with deeper levels is eased in those levels too (same piece, so
        # the wall stays one surface); a notch filled is filled in every deeper level that has it (the levels stay nested)
        for i in range(nL - 1, -1, -1):
            A = F_[i]; must_air = union(F_[i - 1] if i else [], KO[i])
            Fi, nb, nf, nfl = fair_level(A, must_air, MM[i], R_IN_THRU if pl.L[i] <= 1e-6 else R_IN_LEDGE)
            add, fill = fair_level.last
            for j in range(i - 1, -1, -1):
                for q in add:
                    ci = contact(q, A); cj = contact(q, F_[j])
                    if ci > 0 and cj >= 0.6 * ci and not inter([q], MM[j]): F_[j] = union(F_[j], [q])
                if fill:
                    fj = [x for x in pos(inter(fill, F_[j])) if not inter([x], offset(KO[j], 0.3))]
                    if fj: F_[j] = diff(F_[j], fj)
            F_[i] = Fi; tot['bumps'] += nb; tot['fills'] += nf
            if os.environ.get('FAIR_V'): print(f'  round {r} level {pl.L[i]}: {nfl} flags, {nb} eased, {nf} filled', flush=True)
        for i in range(1, nL): F_[i] = union(F_[i], F_[i - 1])
        if os.environ.get('FAIR_STRIPS'):
            ns = strips(pl, F_, KO, MM); tot['strips'] += ns
    if align:
        if align_lower(J, pl, F_, KO, MM, log=log):
            prev = None
            for i in range(nL - 1, -1, -1):
                must_air = union(F_[i - 1] if i else [], KO[i])
                F_[i] = fair_level(F_[i], must_air, MM[i], R_IN_THRU if pl.L[i] <= 1e-6 else R_IN_LEDGE)[0]
            for i in range(1, nL): F_[i] = union(F_[i], F_[i - 1])
    # a ledge opened at the plate's edge by easing alone (no part needs it) goes back to plate at every level: the edge is the
    # through level's business, and a floor step on the rim is a step, not a sink
    outer0 = [q for q in diff(BOX, diff(BOX, F_[0])) if pc.Orientation(q)]
    outer0 = [max(pos(F_[0]), key=ar)] if F_[0] else []
    for i in range(1, nL):
        for q in pos(diff(F_[i], F_[i - 1])):
            if ar(q) < 25 and inter(offset([q], 0.05), outer0) and not inter([q], KO[i]):
                for j in range(i, nL):
                    if not inter([q], KO[j]): F_[j] = union(diff(F_[j], offset([q], 0.01)), F_[j - 1])
    F_ = finish(F_, KO, pl)
    # and once more after the finish: a small ledge it opened at the plate's edge, where no part needs it, goes back to plate
    outer0 = [max(pos(F_[0]), key=ar)] if F_[0] else []
    for i in range(1, nL):
        for q in pos(diff(F_[i], F_[i - 1])):
            if ar(q) < 2 and inter(offset([q], 0.05), outer0) and not inter([q], KO[i]):
                for j in range(i, nL):
                    if not inter([q], KO[j]): F_[j] = union(diff(F_[j], offset([q], 0.01)), F_[j - 1])
    # a neighbouring plate's footprint and the sim's gap round it stay clear at every level (the corner passes may not close the gap)
    if NB:
        for j in range(nL): F_[j] = union(F_[j], NB)
    # a last inside corner sharper than the cutter that no part needs: filled to the cutter's radius
    for i in range(1, nL):
        tips = [q for q in pos(diff(F_[i], opening(F_[i], R_IN_LEDGE))) if ar(q) > 1e-4 and not inter([q], offset(KO[i], 0.05)) and not inter([q], F_[i - 1])]
        if tips: F_[i] = diff(F_[i], tips)
    write_back(J, pl, F_)
    log.append(f'fair {pid}: {nL} levels redrawn; {tot["bumps"]} steps and bumps eased (r {RB:g}), {tot["fills"]} notches and fingers filled, '
               f'{tot["strips"]} floor strips under {STRIP:g} mm closed; inside corners r {R_IN_LEDGE:g}/{R_IN_THRU:g}, outside r {R_OUT:g}')
    return F_

ROUNDS_FINISH, MICRO, GROW = 2, False, 0.003
KO_GROW = 0.56
FA_BLEND = 2.0
def finish(F_, KO, pl, thin=0.4, ledge_thin=1.95):
    """last pass: plate thinner than `thin` left between a level's wall and another (a sliver the sim draws as a fragment) is cut
    to that level; then each level's inside corners to the cutter's radius again, where no part needs the corner"""
    nL = len(F_)
    def micro():
        for i in range(1, nL):
            X = diff(F_[i], F_[i - 1])
            mic = [q for q in pos(diff(X, opening(X, 0.05))) if ar(q) > 1e-7 and not inter([q], offset(KO[i], 0.01))]
            if mic:
                for j in range(i, nL): F_[j] = union(diff(F_[j], offset(mic, 0.002)), F_[j - 1])
    removed = [[] for _ in range(nL)]
    for _ in range(ROUNDS_FINISH):
        if MICRO: micro()
        for i in range(nL):
            m = diff(INNER, F_[i])
            w = ledge_thin if pl.L[i] > 1e-6 else thin              # on a ledge, plate under 2 mm comes down to the floor below; through, only slivers
            sl = [q for q in pos(diff(m, opening(m, w / 2))) if ar(q) > 1e-4 and (w == thin or inter(offset([q], 0.05), F_[i]))]
            if sl:
                g = offset(sl, GROW)
                for j in range(i, nL): F_[j] = union(F_[j], g); removed[j] = union(removed[j], g)
        for i in range(nL):
            r_in = R_IN_THRU if pl.L[i] <= 1e-6 else R_IN_LEDGE
            keep = union(F_[i - 1] if i else [], KO[i], removed[i])      # (the corner pass never puts back plate just taken off as too thin)
            F_[i] = union(opening(F_[i], r_in), keep)
            for j in range(i + 1, nL): F_[j] = union(F_[j], F_[i])
    return [union(pc.CleanPolygons(a, 0.0015 * S)) for a in F_]

def write_back(J, pl, F_, fixed=None):
    """fixed: per level, air the plate's other cuts already make there (round recesses, bearing seats): left out of the pockets"""
    st = J['state']
    for c in pl.pockets: st['sketches'] = [x for x in st['sketches'] if x['id'] != c['sketch']]
    SK = {x['id']: x for x in st['sketches']}
    # the outline: the outer edge of the through level's plate
    M0 = pos(diff(INNER, F_[0]) if pl.L[0] <= 1e-6 else pl.outline)
    big = max(M0, key=ar); lp = simplify(np.vstack([F(big), F(big)[:1]]), 0.001)[:-1]
    pl.k['points'] = dots_sharp(lp)
    outside = diff(BOX, [big]); ids = PC.next_cut_id(J); new = []; prev = outside
    for i, (L, A2) in enumerate(zip(pl.L, F_)):
        new_air = diff(A2, prev)
        if fixed and fixed[i]: new_air = diff(new_air, fixed[i])
        extra = PC.opening(new_air, 0.003) if hasattr(PC, 'opening') else opening(new_air, 0.003)
        reg = inter(offset(extra, PC.OVERLAP), A2); used = {}
        for p in PC.pieces(reg):
            if ar(p) < 0.0001: continue
            # 5 µm proud toward the pieces beside it, so no speck of plate is left where two pieces' edges meet; but never past its
            # own level's wall (2026-11-22: proud there left a 5 µm step wherever a pocket ran along a wall, and a notch where it began,
            # which the sim shaded as a thin vertical line across the wall)
            p = max(pos(inter(offset([p], 0.005), offset(A2, 0.0005))), key=ar)
            pts = simplify(np.vstack([F(p), F(p)[:1]]), 0.001)[:-1]
            ov = [(abs(sum(pc.Area(q) for q in inter([p], cp))), nm) for cp, nm in pl.by.get(L, [])]
            nm = max(ov)[1] if ov and max(ov)[0] > 0 else f'Ledge at {L + pl.z0:.2f} mm'
            nm = nm.split(' (')[0] if nm.endswith(')') and nm.rsplit('(', 1)[-1][:-1].isdigit() else nm
            used[nm] = used.get(nm, 0) + 1; j = used[nm] - 1
            sid = f'KF{len(new) + 1}_{pl.pid}'
            while sid in SK: sid += 'x'
            st['sketches'].append({'id': sid, 'name': f'{pl.pid} level {L + pl.z0:.2f}', 'plane': {'axis': 'z', 'offset': pl.z0}, 'closed': True, 'points': dots_sharp(pts)})
            new.append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(pl.T - L, 4), 'name': nm if j == 0 else f'{nm} ({j + 1})'})
        prev = A2
    pl.d['cuts'] = pl.rest + new
    pl.d['back'] = None; pl.d['edges'] = None
    # a speck of plate a few µm thick (where three walls meet) is merged into the pocket beside it that floors that slab
    import hairline_check as HC
    SKn = {x['id']: x for x in st['sketches']}
    for x in HC.check(J, pl.pid):
        if x['area'] > 0.005: continue
        D = round(pl.T - x['slab'][0], 4)
        for c in new:
            if abs(c['depth'] - D) > 1e-6: continue
            k = SKn[c['sketch']]; reg = union([P([(q['u'], q['v']) for q in k['points']])])
            if not inter(offset([x['poly']], 0.01), reg): continue
            m = pos(union(reg, offset([x['poly']], 0.004)))
            if len(m) == 1: k['points'] = dots_sharp(F(m[0])); break

TIER_TOL = 1e-4             # write_tiers(): outlines kept to 0.1 µm of the model (the sim's own grid), so walls shared by two tiers stay one wall
TIER_REACH = 0.3            # each tier's region reaches this far past the plate's edge, so no tier edge lies exactly on the outline

def write_tiers(J, pl, F_):
    """(test A, 2026-11-22) the plate written as one region per tier instead of pocket pieces: tier i's pocket is the whole air of
    level i (nested: it contains every deeper tier's air), cut from the top to that floor, so at any height the sim's union of the
    pockets reaching it is exactly that level's region and a wall shared by two tiers is the same edge in both. No piece is drawn
    oversize and no outline is simplified on its own (only to 0.1 µm, the sim's grid)."""
    st = J['state']
    for c in pl.pockets: st['sketches'] = [x for x in st['sketches'] if x['id'] != c['sketch']]
    SK = {x['id']: x for x in st['sketches']}
    M0 = pos(diff(INNER, F_[0]) if pl.L[0] <= 1e-6 else pl.outline)
    big = max(M0, key=ar)
    pl.k['points'] = dots_sharp(simplify(np.vstack([F(big), F(big)[:1]]), TIER_TOL)[:-1])
    reach = offset([big], TIER_REACH)
    ids = PC.next_cut_id(J); new = []
    for i, (L, A2) in enumerate(zip(pl.L, F_)):
        R = inter(A2, [big]) if i == 0 and L <= 1e-6 else inter(A2, reach)      # tier 0 over a through cut: its holes; above: all the air
        names = [nm for _, nm in pl.by.get(L, [])]
        label = f'Tier: floor {L + pl.z0:.2f} mm' + (f" ({', '.join(n.split(' (')[0] for n in names[:3])}{', ...' if len(names) > 3 else ''})" if names else '')
        for j, p in enumerate(PC.pieces(R)):
            if ar(p) < 1e-4: continue
            pts = simplify(np.vstack([F(p), F(p)[:1]]), TIER_TOL)[:-1]
            sid = f'KT{len(new) + 1}_{pl.pid}'
            while sid in SK: sid += 'x'
            st['sketches'].append({'id': sid, 'name': f'{pl.pid} tier {L + pl.z0:.2f}', 'plane': {'axis': 'z', 'offset': pl.z0}, 'closed': True, 'points': dots_sharp(pts)})
            SK[sid] = st['sketches'][-1]
            new.append({'id': next(ids), 'kind': 'pocket', 'sketch': sid, 'from': 'back', 'depth': round(pl.T - L, 4), 'name': label if j == 0 else f'{label} ({j + 1})'})
    pl.d['cuts'] = pl.rest + new
    pl.d['back'] = None; pl.d['edges'] = None
    return new

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []
    for pid in (sys.argv[3].split(',') if len(sys.argv) > 3 else ['D3']): fair_plate(J, log, pid)
    print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))

# ---------- the plate below: one wall where two plates' edges run close (Adam: "i sketched it to be consistent with the lower plate") ----------
def align_lower(J, pl, F_, KO, MM, lower='D1', neighbours=('D6',), w=1.5, log=None):
    """this plate stands on `lower`: where its edge (its through level) runs within w of the lower plate's top-face wall, its edge
    comes to that wall. A thin strip of the lower plate's top showing beside this plate's edge: this plate grows over it, as far
    up its levels as no part needs the space. A thin overhang of this plate over the lower plate's recess: cut back through.
    A strip that also borders a neighbouring plate is the gap between two plates and stays."""
    import walls as W
    ML = W.slabs(J, lower)[-1][2]
    MU = diff(BOX, F_[0]); nL = len(F_)
    NB = union(*[W.slabs(J, n)[0][2] for n in neighbours]) if neighbours else []
    grow = trim = 0
    led = diff(ML, union(MU, NB) if NB else MU)
    def wedge_or_rim(q):
        Q = F(q); per = float(np.hypot(*(np.roll(Q, -1, 0) - Q).T).sum())
        return per / 2 < 2.5 or np.hypot(Q[:, 0], Q[:, 1]).max() > 64.5   # a corner's wedge, or the rim (the rim pass owns it)
    for q in pos(diff(led, opening(led, w / 2))):
        if ar(q) < 0.02 or not inter(offset([q], 0.05), MU) or wedge_or_rim(q): continue
        if NB and inter(offset([q], 0.6), NB): continue
        jt = -1
        for j in range(nL):
            if inter([q], offset(KO[j], 0.05)): break
            jt = j
        if jt < 0: continue
        qq = offset([q], 0.02)
        for j in range(jt + 1): F_[j] = diff(F_[j], qq)
        for j in range(1, nL): F_[j] = union(F_[j], F_[j - 1])
        grow += 1
    over = diff(MU, ML)
    for q in pos(diff(over, opening(over, w / 2))):
        if ar(q) < 0.02 or not inter(offset([q], 0.05), ML) or wedge_or_rim(q): continue
        if inter([q], MM[0]): continue
        qq = offset([q], 0.02)
        for j in range(nL): F_[j] = union(F_[j], qq)
        trim += 1
    if log is not None: log.append(f'{pl.pid} on {lower}: {grow} edge strips grown over the lower plate\'s top, {trim} thin overhangs cut back (under {w:g} mm)')
    return grow + trim
