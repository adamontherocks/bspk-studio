# Export the H-88 case parts as solids (STEP and STL), in the movement's frame so they line up with Beta 2's exported parts.
# The case parts aren't all flat parts milled from one face (the body is cut from the front and the back; the lug plate is a two-view
# part), so they're built here from the case geometry directly rather than through the plate resolver: prisms and cylinders, unioned and
# cut. Inside corners are as drawn: CAM leaves the cutter's radius in them.
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
    E = 0.01
    x0c, cr, zw = g['crown']
    parts = []
    # faceplate and body
    cuts = [prism(g['cav'], z['back'] - E, z['lip0']), prism(g['window'], z['lip0'] - E, z['top'] + E),
            prism(g['well'], z['back'] - E, zw + cr + 0.3), prism(g['slit'], z['back'] - E, zw + 0.9 + 0.2)]
    from shapely.geometry import box
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = sorted((sx * case.LUG_X[0], sx * case.LUG_X[1])); ly = sorted((sy * (case.SLOT_Y0 - 0.1), sy * (case.H / 2 + 2.0)))
            cuts.append(prism(box(lx[0] - 0.1, ly[0], lx[1] + 0.1, ly[1]), z['back'] - E, zr + 0.1))
            for yv in (18.3, 20.2, 22.1): pass
    for sy in (-1, 1):
        for yv in (18.3, 20.2, 22.1): cuts.append(prism(case.stadium(-10.0, 10.0, sy * yv, 1.0), z['top'] - 0.8, z['top'] + E))
    plq, side = g['scr'][:4], g['scr'][4:]
    for x, y in plq: cuts += [cyl(x, y, 1.15, zr, z['top'] + E), cyl(x, y, 2.2, z['top'] - 0.9, z['top'] + E)]
    for x, y in side: cuts += [cyl(x, y, 0.625, z['back'] - E, z['top'] + E), cyl(x, y, 1.6, z['top'] - 0.5, z['top'] + E)]
    parts.append({'id': 'D9', 'name': 'Faceplate-and-body', 'solid': [prism(g['body'], z['back'], z['top'])], 'cuts': cuts})
    # crystal
    parts.append({'id': 'D10', 'name': 'Crystal', 'solid': [prism(g['insert'], z['cry'][0], z['cry'][1])],
                  'cuts': [prism(g['insert'].buffer(0.05).difference(g['boss']), z['cry'][1] - case.CRYSTAL_STEP, z['cry'][1] + E)]})
    # dial plate
    dc = [cyl(c[0], c[1], 9.8, z['dial'][0] - E, z['dial'][1] + E) for c in g['discs']]
    dc += [cyl(x, y, 2.3, z['dial'][0] - E, z['dial'][0] + 1.8) for x, y in ((5.05, 13.4), (10.55, 13.9))]
    dc += [prism(g['red'], z['dial'][1] - case.RED_D, z['dial'][1] + E)]
    dc += [cyl(0.0, yv, 1.2, z['dial'][1] - 0.3, z['dial'][1] + E) for yv in (7.8, -7.8)]
    parts.append({'id': 'D11', 'name': 'Dial-plate', 'solid': [prism(g['insert'], z['dial'][0], z['dial'][1])], 'cuts': dc})
    # lug plate: the frame and its four lugs (one two-view part)
    lugs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            prof = [[round(sy * u, 4), round(v, 4)] for u, v in g['side']]
            lugs.append({'kind': 'xprism', 'ring': prof, 'x0': case.LUG_X[0] if sx > 0 else -case.LUG_X[1], 'x1': case.LUG_X[1] if sx > 0 else -case.LUG_X[0]})
    eye_y = case.H / 2 + case.EYE_OUT; eye_z = z['frame0'] + case.EYE_R
    lc = [prism(g['cav'].buffer(-1.0), z['frame0'] - E, z['back'] + E), prism(g['cav'], z['back'] - 0.8, z['back'] + E), prism(g['well'], z['back'] - 0.6, z['back'] + E)]
    for x, y in side: lc += [cyl(x, y, 0.9, z['frame0'] - E, z['back'] + E), cyl(x, y, 1.6, z['frame0'] - E, z['frame0'] + 0.9)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            lc.append({'kind': 'xcyl', 'y': sy * eye_y, 'z': eye_z, 'r': case.HOLE / 2, 'x0': -case.LUG_X[1] - 1 if sx < 0 else case.LUG_X[0] - 0.01,
                       'x1': -case.LUG_X[0] + 0.01 if sx < 0 else case.LUG_X[1] + 1})
    for x, y in plq: lc.append(cyl(x, y, 0.8, zr - 5.0, zr + E))          # the plaque screws' threads, 5 deep into each riser
    parts.append({'id': 'D12', 'name': 'Lug-plate-with-lugs', 'solid': [prism(g['frame'], z['frame0'], z['back'])] + lugs, 'cuts': lc})
    # back plate
    parts.append({'id': 'D13', 'name': 'Back-plate', 'solid': [prism(g['insert'], z['back'] - case.BACK_T, z['back'])], 'cuts': []})
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
        if p['cuts']: body = body.cut(*[solid(o) for o in p['cuts']]).clean()
        base = os.path.join(outdir, f"{p['id']}-{p['name']}")
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.005, angularTolerance=0.05)
        back = cq.importers.importStep(base + '.step').vals()
        bb = body.BoundingBox()
        out.append({'id': p['id'], 'file': os.path.basename(base) + '.step', 'valid': bool(body.isValid() and back and all(v.isValid() for v in back)),
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
