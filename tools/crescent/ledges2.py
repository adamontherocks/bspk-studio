# Ledges drawn from the parts (2026-11-21, Adam: walls "should all be smooth continuous surfaces", "radii should be smooth and
# consistent"). The motion-works plate's three ledge levels (15.5, 17.1, 19.1) came from pixel rasters and were rounded and
# patched pass after pass, which left jogs, hooks and dips where their walls meet. They are drawn again here the way a watch
# plate's sinks are drawn: each level is the space the parts in its height band need (keepout.py: every wheel's disc, every
# lever's sweep over its real range, the spring's wire, each with the sim's 0.5 mm gap) plus CLEAR for the cutter, joined into
# one region by a round of radius R_ENV (so two sinks closer than 2 R_ENV run into one, and every join is the same radius),
# nested on the level below. The through level (the windows and the crown's flat, Adam's shapes) is kept and only given its
# corner radii. Walls then are arcs about the parts at one clearance, joined by arcs of one radius.
import json, sys, os
import numpy as np
import pyclipper as pc
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pk2 import P, F, S, union, diff, inter, offset, close, opening
import fair as FA, keepout as K

CLEAR, R_ENV, R_IN, R_NEED = 0.6, 2.0, 1.06, 3.0   # R_NEED: each band's parts' space rounded on its own first (a spring's wire fan, a lever's arm)

def derive(J, log, pid='D3', fair=True):
    pl = FA.Plate(J, pid); nL = len(pl.L)
    ring = pl.holes_ring(1.0)
    A0 = pl.A[0]
    ko0 = inter(K.keepout(J, *pl.band(0)), A0)
    A0 = union(close(opening(A0, FA.R_IN_THRU), FA.R_OUT), ko0)
    F_ = [A0]; NEED = [None]
    for i in range(1, nL):
        need = close(offset(K.keepout(J, *pl.band(i)), CLEAR), R_NEED); NEED.append(need)
        Ai = close(union(need, F_[i - 1]), R_ENV)
        # (no bosses kept on the ledges: a hole sits in the floor below, as before; a boss standing up to the top face is a tower)
        Ai = union(close(opening(Ai, R_IN), FA.R_OUT), F_[i - 1], need)
        F_.append(union(pc.CleanPolygons(Ai, 0.0015 * S)))
    if fair: F_ = FA.fair_plate(J, log, pid, start=F_, pl=pl, align=(pid == 'D3'))
    else: FA.write_back(J, pl, F_)
    log.append(f'ledges {pid}: levels {", ".join(f"{pl.z0 + L:.2f}" for L in pl.L[1:])} drawn from the parts in each band '
               f'(their space + {CLEAR:g} mm, joined r {R_ENV:g}), through level kept with its corner radii')
    return pl, F_

if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; derive(J, log); print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
