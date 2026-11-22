# Restore (2026-11-21, Adam, P92-P94, P101: "your smoothing passes dissolved the whole retention wall" for the return spring's
# wire, and the bridge between two lands of the motion-works plate). The ledge redraw (ledges2) drew every ledge from the parts'
# keep-outs alone, so it dropped material that no part needed the room of but the design did: the finger the spring wire bears
# on, the bridge joining two lands, lobes and a raised band. The rule from now on: a pass removes material only where a part
# needs the room.
#   restore(J, old, log, pid)  puts back every piece of the old plate's material that is air now and at least MIN_AREA, except
#     where a part at that height or below needs the room (its keep-out + CLEAR), thin strips (double walls closed on purpose)
#     and pieces near Adam's notes that asked for a removal ("protrusion", "remove", "unnecessary protrusion")
#   python3 restore.py NOW.json OLD.json OUT.json [D3]
import json, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import F, S, union, inter, diff, offset, opening
import fair as FA, smooth as SM, keepout as K

MIN_AREA, STRIP, NEAR = 4.0, 0.4, 3.0
SPRINGS = ('return',)
REMOVE_WORDS = ('protrusion', 'remove', 'delete')

def restore(J, old, log, pid='D3'):
    pn = FA.Plate(J, pid); po = FA.Plate(old, pid)
    if [round(x, 4) for x in pn.L] != [round(x, 4) for x in po.L]:
        log.append(f'restore {pid}: the levels differ from the old plate, nothing restored'); return []
    KO, MM, NB = SM.setup(J, pid, pn); nL = len(pn.L)
    asked = [np.asarray(p['w'][:2]) for p in J['state'].get('pins', []) if p.get('part') in (pid, 'D1') and any(w in (p.get('note') or '').lower() for w in REMOVE_WORDS)]
    A = list(pn.A); back = []
    for i in range(nL):
        lost = opening(inter(diff(pn.A[i], po.A[i]), FA.INNER), STRIP)
        # what parts need: their keep-outs as the sim checks them (the 0.5 mm gap included), heights up to this level; the
        # return spring's wire is left out (it bears on the finger and sits in the slot's end: those walls are what hold it)
        need = union(*[g for z0, z1, g, nm in K.sweeps(J) if nm not in SPRINGS and z0 < pn.z0 + (pn.L[i + 1] if i + 1 < nL else pn.T) - 1e-6 and z1 > pn.z0 + 1e-6])
        X = opening(diff(lost, need) if need else lost, 0.3)
        keep = []
        for q in X:
            if not pc.Orientation(q) or abs(pc.Area(q)) / S / S < MIN_AREA: continue
            c = F(q).mean(0)
            if any(np.hypot(*(c - a)) < NEAR for a in asked): continue
            keep.append(q); back.append((i, c, abs(pc.Area(q)) / S / S, q))
        if keep:
            for j in range(i + 1): A[j] = diff(A[j], keep)
    if NB: A = [union(a, NB) for a in A]
    # specks where a restored edge almost meets a wall that stayed, and plate slivers under 0.2 mm, cleaned; levels kept nested
    for j in range(nL):
        M = diff(FA.INNER, A[j]); A[j] = diff(FA.BOX, opening(M, SM.SPECK))
        if j: A[j] = union(A[j], A[j - 1])
        A[j] = SM.clean_level(A[j])
    FA.write_back(J, pn, A)
    log.append(f'restore {pid}: {len(back)} pieces of the old plate put back (' + ', '.join(f'{pn.z0 + pn.L[i]:.1f} floor at ({c[0]:.0f},{c[1]:.0f}) {a:.0f} mm2' for i, c, a, q in back) + ')')
    return back

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); old = json.load(open(sys.argv[2])); log = []
    restore(J, old, log, sys.argv[4] if len(sys.argv) > 4 else 'D3')
    print('\n'.join(log)); json.dump(J, open(sys.argv[3], 'w'))
