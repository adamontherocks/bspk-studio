# Export the H-88 case parts as solids (STEP and STL), in the movement's frame so they line up with Beta 2's exported parts.
# The case parts aren't all flat parts milled from one face (the body is cut from the front and the back; the lug plate is a two-view
# part), so they're built here from the case geometry directly rather than through the plate resolver: prisms and cylinders, unioned and
# cut. Inside corners are as drawn: CAM leaves the cutter's radius in them. The flat parts (faceplate, crystal, dial, back plate) are built
# from the sim's own cut lists, chamfers included (tools/plates/chamfer.py), so the STEP is what the sim draws; the lug plate from the
# case geometry (its lugs are side profiles).
# Two steps, two Pythons (as tools/plates/export_step.py): plan the rings here (system python, shapely), build in .venv (CadQuery).
#   python3 tools/h88/export_case.py OUTDIR
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
VENV_PY = os.path.join(ROOT, '.venv', 'bin', 'python')

def plan():
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'beta2')); sys.path.insert(0, HERE)
    argv = sys.argv; sys.argv = ['x']
    import make_projects as mp, layered, case
    sys.argv = argv
    s3, info = mp.beta2_aligned()
    S5, rep5, _ = layered.build(s3, info, {'rrect': mp.rrect, 'sketch': mp.sketch, 'poly_dots': mp.poly_dots, 'FITS_DELRIN': mp.FITS_DELRIN})
    if rep5['problems']: raise SystemExit('Beta 2 has problems: ' + '; '.join(rep5['problems']))
    S, rep, g = case.build(S5, info, {'sketch': mp.sketch, 'poly_dots': mp.poly_dots})
    z = g['z']; zr = z['back'] + case.RISE
    def rings(poly):
        ps = list(poly.geoms) if hasattr(poly, 'geoms') else [poly]
        return [{'outer': [list(map(lambda v: round(v, 4), c)) for c in p.exterior.coords[:-1]],
                 'holes': [[list(map(lambda v: round(v, 4), c)) for c in r.coords[:-1]] for r in p.interiors]} for p in ps if p.geom_type == 'Polygon' and p.area > 1e-4]
    def prism(poly, z0, z1): return {'kind': 'prism', 'faces': rings(poly), 'z0': z0, 'z1': z1}
    def cyl(x, y, r, z0, z1): return {'kind': 'cyl', 'x': x, 'y': y, 'r': r, 'z0': z0, 'z1': z1}
    def draft(poly, z0, z1, taper): return {'kind': 'draft', 'faces': rings(poly), 'z0': z0, 'z1': z1, 'taper': taper}     # taper > 0 shrinks going up
    def inter(a, b): return {'kind': 'inter', 'a': a, 'b': b}
    E = 0.01
    # The flat case parts straight from the sim's own parts and cuts (the same cut list the sim draws): pockets and holes as prisms and
    # cylinders from their faces, seats, countersinks, and the 45° chamfers (tools/plates/chamfer.py, as the sim's chamferFeats)
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'plates'))
    import chamfer as chf
    from shapely.geometry import Polygon as SP
    st = S['state']; sk = {k_['id']: k_ for k_ in st['sketches']}
    def circ(x, y, r, n=96): return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    def zp(path, za, zb_): return {'kind': 'prism', 'faces': [{'outer': [[round(a, 5), round(b, 5)] for a, b in path], 'holes': []}], 'z0': min(za, zb_), 'z1': max(za, zb_)}
    def flat_part(pid, name):
        d = next(x for x in st['drawn'] if x['id'] == pid); k_ = sk[d['sketch']]
        T = d['thickness']; z0 = k_['plane']['offset']; gr = d.get('grow') or 'plus'
        zf, zb = (z0, z0 + T) if gr == 'plus' else (z0, z0 - T) if gr == 'minus' else (z0 - T / 2, z0 + T / 2)
        lo, hi = min(zf, zb), max(zf, zb)
        outline = [(q['u'], q['v']) for q in k_['points']]
        cuts, opens = [], []
        for c in d.get('cuts') or []:
            frm = 'back' if c.get('from') == 'back' else 'front'
            zc = zb if frm == 'back' else zf; into = -1 if zc == hi else 1
            D = T if c.get('depth') is None else min(T, c['depth']); ze = zc + into * (D + (E if D >= T - 1e-6 else 0))
            if c['kind'] == 'pocket':
                path = [(q['u'], q['v']) for q in sk[c['sketch']]['points']]
                cuts.append(zp(path, zc - into * E, ze)); opens.append({'c': c, 'from': frm, 'zc': zc, 'into': into, 'D': D, 'path': path})
                continue
            x, y = c['at']; za = zc - into * E
            cuts.append(cyl(x, y, c['d'] / 2, min(za, ze), max(za, ze)))
            seat = bool(c.get('seat')) and c['seat']['d'] > c['d'] and c['seat']['depth'] > 0
            if seat:
                zs = zc + into * min(D, c['seat']['depth']); cuts.append(cyl(x, y, c['seat']['d'] / 2, min(za, zs), max(za, zs)))
            if c.get('csk') and c['csk']['d'] > c['d']:
                h = (c['csk']['d'] - c['d']) / 2
                cuts.append({'kind': 'cone', 'x': x, 'y': y, 'r1': c['csk']['d'] / 2 + E, 'r2': c['d'] / 2, 'z': za, 'h': h + E, 'dir': into})
            opens.append({'c': c, 'from': frm, 'zc': zc, 'into': into, 'D': min(D, c['seat']['depth']) if seat else D,
                          'path': circ(x, y, (c['seat']['d'] if seat else c['d']) / 2)})
        for L in opens:
            size = L['c'].get('chamfer') or 0
            if not size > 0: continue
            Pp = SP(L['path']).buffer(0); zz = 0.0
            for M in opens:      # it starts on the floor of a cut it sits in
                if M is not L and M['from'] == L['from'] and zz < M['D'] < L['D'] - 1e-6 and SP(M['path']).buffer(1e-6).contains(Pp): zz = M['D']
            cc = min(size, L['D'] - zz)
            b = chf.bevel(L['path'], cc, L['zc'], L['into'], zz) if cc > 1e-4 else None
            if b: cuts.append(b)
        part = {'id': pid, 'name': name, 'solid': [zp(outline, lo, hi)], 'cuts': cuts}
        ch = d.get('chamfer')
        if ch and (ch.get('size', 0) > 0 or ch.get('widths')):      # the outline's edge on one face
            zc = zb if ch.get('face', 'back') == 'back' else zf; into = -1 if zc == hi else 1
            if ch.get('widths'): cuts.extend(chf.edge_wedges(outline, ch, zc, into))   # widths by side: one wedge per face, meeting in ridges
            else:                                                     # one width: keep the outline drafted in over it, at its angle
                cc = min(ch['size'] * math.tan(math.radians(ch.get('angle') or 45.0)), T); op = SP(outline); tp = 90 - (ch.get('angle') or 45.0)
                if cc >= T - 1e-6: part['keep'] = [draft(op, lo - E, hi, tp)] if zc == hi else [draft(op, hi, lo - E, tp)]   # (all through the part: the draft alone)
                else: part['keep'] = ([prism(op, lo - E, hi - cc), draft(op, hi - cc, hi + E, tp)] if zc == hi else [prism(op, lo + cc, hi + E), draft(op, lo + cc, lo - E, tp)])
        return part
    parts = [flat_part('D9', 'Faceplate'), flat_part('D10', 'Crystal'), flat_part('D11', 'Dial-plate')]
    # the case middle and its four lugs, one piece: the ring with all its cuts (the back bevel's wedges among them), then the lugs fused on
    # (so the bevel can't take them), then their spring bar holes drilled through from the outer faces
    mid = flat_part('D12', 'Case-middle-with-lugs')
    ey, ez = g['eye']; mid['add'], mid['cuts2'] = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            prof = [[round(sy * u, 4), round(v, 4)] for u, v in g['side']]
            mid['add'].append({'kind': 'xprism', 'ring': prof, 'x0': case.LUG_X[0] if sx > 0 else -case.LUG_X[1], 'x1': case.LUG_X[1] if sx > 0 else -case.LUG_X[0]})
            mid['cuts2'].append({'kind': 'xcyl', 'y': sy * ey, 'z': ez, 'r': case.HOLE / 2, 'x0': -case.LUG_X[1] - 1 if sx < 0 else case.LUG_X[0] - 0.01,
                                 'x1': -case.LUG_X[0] + 0.01 if sx < 0 else case.LUG_X[1] + 1})
    parts.append(mid)
    parts.append(flat_part('D13', 'Back-plate'))
    # Beta 2's discs (hands): blanks, numerals V-carved after
    for nm, c in (('minute', (10.4, 0.0)), ('hour', (-10.4, 0.0))):
        parts.append({'id': f'disc-{nm}', 'name': f'Beta2-{nm}-disc-blank', 'solid': [cyl(c[0], c[1], 9.5, 7.75, 7.75 + case.TT)],
                      'cuts': [cyl(c[0], c[1], 2.96 / 2, 7.75 - E, 7.75 + case.TT + E)]})
    return parts, rep

def build(parts, outdir):
    import cadquery as cq
    def wire(pts): return cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in pts], close=True)
    def face(f):
        return cq.Face.makeFromWires(wire(f['outer']), [wire(h) for h in f['holes']])
    def solid(op):
        if op['kind'] == 'prism':
            ss = [cq.Solid.extrudeLinear(face(f), cq.Vector(0, 0, op['z1'] - op['z0'])).translate(cq.Vector(0, 0, op['z0'])) for f in op['faces']]
            return ss[0] if len(ss) == 1 else ss[0].fuse(*ss[1:])
        if op['kind'] == 'draft':         # a face grown along z with a draft angle (45: a chamfer)
            ss = [cq.Solid.extrudeLinear(face(f), cq.Vector(0, 0, op['z1'] - op['z0']), taper=op['taper']).translate(cq.Vector(0, 0, op['z0'])) for f in op['faces']]
            return ss[0] if len(ss) == 1 else ss[0].fuse(*ss[1:])
        if op['kind'] == 'pprism':        # a planar polygon in space grown along a vector
            w = cq.Wire.makePolygon([cq.Vector(*q) for q in op['pts']], close=True)
            return cq.Solid.extrudeLinear(cq.Face.makeFromWires(w), cq.Vector(*op['vec']))
        if op['kind'] == 'cone':          # a countersink: r1 at the face, r2 h in, along dir
            return cq.Solid.makeCone(op['r1'], op['r2'], op['h'], cq.Vector(op['x'], op['y'], op['z']), cq.Vector(0, 0, op['dir']))
        if op['kind'] == 'loft':
            return cq.Solid.makeLoft([cq.Wire.makePolygon([cq.Vector(*q) for q in op[k]], close=True) for k in ('w0', 'w1')], True)
        if op['kind'] == 'inter':
            return solid(op['a']).intersect(solid(op['b']))
        if op['kind'] == 'cyl':
            return cq.Solid.makeCylinder(op['r'], op['z1'] - op['z0'], cq.Vector(op['x'], op['y'], op['z0']), cq.Vector(0, 0, 1))
        if op['kind'] == 'xprism':        # a side profile (y, z) grown along x
            w = cq.Wire.makePolygon([cq.Vector(op['x0'], y, zz) for y, zz in op['ring']], close=True)
            return cq.Solid.extrudeLinear(cq.Face.makeFromWires(w), cq.Vector(op['x1'] - op['x0'], 0, 0))
        if op['kind'] == 'xcyl':
            return cq.Solid.makeCylinder(op['r'], op['x1'] - op['x0'], cq.Vector(op['x0'], op['y'], op['z']), cq.Vector(1, 0, 0))
        raise ValueError(op['kind'])
    out = []
    os.makedirs(outdir, exist_ok=True)
    for p in parts:
        body = solid(p['solid'][0])
        if len(p['solid']) > 1: body = body.fuse(*[solid(o) for o in p['solid'][1:]]).clean()
        if p.get('keep'):
            k = [solid(o) for o in p['keep']]; body = body.intersect(k[0].fuse(*k[1:]) if len(k) > 1 else k[0]).clean()
        if p['cuts']:
            cs = [solid(o) for o in p['cuts']]
            one = body.cut(*cs).clean()
            if not one.isValid() or len(one.Solids()) != len(body.Solids()):     # (OCC sometimes fumbles many cuts at once: one at a time holds)
                for c in cs: body = body.cut(c).clean()
            else: body = one
        if p.get('add'): body = body.fuse(*[solid(o) for o in p['add']]).clean()
        if p.get('cuts2'): body = body.cut(*[solid(o) for o in p['cuts2']]).clean()
        base = os.path.join(outdir, f"{p['id']}-{p['name']}")
        ok = body.isValid(); bb = body.BoundingBox()   # (both before the STL: meshing it can upset OCC's checker and loosen its box on a sound solid)
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.005, angularTolerance=0.05)
        back = cq.importers.importStep(base + '.step').vals()
        out.append({'id': p['id'], 'file': os.path.basename(base) + '.step', 'valid': bool(ok and back and all(v.isValid() for v in back)),
                    'solids': len(body.Solids()), 'volume': round(body.Volume(), 2), 'bbox': [round(v, 3) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)]})
    return out

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--build':
        print(json.dumps(build(json.load(sys.stdin), sys.argv[2])))
    else:
        outdir = os.path.abspath(sys.argv[1])
        parts, rep = plan()
        run = subprocess.run([VENV_PY, __file__, '--build', outdir], input=json.dumps(parts).encode(), capture_output=True, timeout=900)
        if run.returncode != 0: raise SystemExit(run.stderr.decode(errors='replace')[-3000:])
        for r in json.loads(run.stdout): print(r)
