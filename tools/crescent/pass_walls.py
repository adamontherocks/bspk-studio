# One wall pass (2026-11-21): rim circle, D3's ledges from the parts with fair walls and its edge on the main plate's walls.
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tiers2 as T, ledges2 as L2
def apply(J, log):
    T.rim(J, log)
    L2.derive(J, log, 'D3')
    T.align_outline(J, log, 'D6', ['D1'], ['D3'])
    T.align_outline(J, log, 'D2', ['D3', 'D6'], ['D5'])
    T.align_outline(J, log, 'D5', ['D3', 'D6'], ['D2'])
if __name__ == '__main__':
    J = json.load(open(sys.argv[1])); log = []; apply(J, log); print('\n'.join(log)); json.dump(J, open(sys.argv[2], 'w'))
