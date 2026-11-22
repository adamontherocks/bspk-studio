# Adam's notes P61-P76 (2026-11-21), small fixes outside the plate cleanup:
#   P73: the template's plain "Fork hub" disc (Ø6.3, z 11.8-12.4) stuck 0.4 mm into the drawn pallet fork; the sim needs every arbor
#        to keep a disc, so it shrinks to Ø4.8 and sits inside the drawn fork's own hub (r 2.6, z 9.8-12.2), hidden
#   bumps and hooks on the other plates' outlines (crescent bridge, hand cock, rim plate, seconds bridge): rounded off r 1.0,
#        notches filled, faired, and written as exact geometry (a fitted spline had overshot into spikes and hooks)
def apply(J, log):
    import plate_clean as PC
    for pid in ('D2', 'D5', 'D6', 'D29'): PC.clean_outline(J, log, pid, r=1.0)
    st, pr = J['state'], J['project']
    for dct in (st.setdefault('solo', {}), pr.setdefault('defaults', {}).setdefault('solo', {})):
        dct['fork_hub'] = {'m': 0.8, 'z': 10.7}
    log.append('fork hub disc: Ø4.8 at z 10.7-11.3, inside the drawn fork\'s hub (P73)')
