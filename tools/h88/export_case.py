# Export the H-88 case parts as solids (STEP and STL), in the movement's frame so they line up with Beta 2's exported parts.
# The case parts aren't all flat parts milled from one face (the body is cut from the front and the back; the lug plate is a two-view
# part), so they're built here from the case geometry directly rather than through the plate resolver: prisms and cylinders, unioned and
# cut. Inside corners are as drawn: CAM leaves the cutter's radius in them. The front's 45° bevels (the outer rim, the window's edge at the
# ring, the corner faces' inner side) are true chamfers here; the sim draws them as straight walls.
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
    def bevel(poly, z0, z1, under=0.05):
        # a 45° bevel as a ruled loft: the outline at z0 to its mitred offset (z1 - z0) at z1, vertex for vertex, so every face is a flat
        # trapezoid (a drafted extrude of a many-sided outline meshes with cracks). It starts `under` lower and inside, on the same 45°, so its
        # foot crosses the wall below cleanly instead of lying on it
        from shapely.geometry.polygon import orient
        pts = []
        z0 = z0 - under
        for q in list(orient(poly.buffer(-under, 32, join_style=2).simplify(0.002), 1.0).exterior.coords)[:-1]:      # (no slivers: a tiny edge at a reflex corner flips when offset)
            if not pts or math.dist(q, pts[-1]) > 0.1: pts.append(q)
        if math.dist(pts[0], pts[-1]) <= 0.1: pts.pop()
        d = z1 - z0; out = []
        for i, (x, y) in enumerate(pts):
            ax, ay = pts[i - 1]; bx, by = pts[(i + 1) % len(pts)]
            def nrm(ux, uy): l = math.hypot(ux, uy); return (uy / l, -ux / l)
            n1, n2 = nrm(x - ax, y - ay), nrm(bx - x, by - y); k = 1.0 + n1[0] * n2[0] + n1[1] * n2[1]
            out.append((x + d * (n1[0] + n2[0]) / k, y + d * (n1[1] + n2[1]) / k))
        from shapely.geometry import Polygon as _P
        if not _P(out).is_valid: raise SystemExit('bevel: its offset outline folds (a short edge at a reflex corner)')
        return {'kind': 'loft', 'w0': [[x, y, z0] for x, y in pts], 'w1': [[x, y, z1] for x, y in out]}     # (unrounded: the side faces must stay flat)
    E = 0.01
    x0c, cr, zw = g['crown']
    parts = []
    # faceplate and body
    f = g['front']; zt, zg = z['top'], z['ring']
    cuts = [prism(g['cav'], z['back'] - E, z['dial'][1]), prism(g['cry_pocket'], z['dial'][1] - E, z['lip0']), prism(g['window'], z['lip0'] - E, zt + E),
            prism(g['well'], z['back'] - E, zw + cr + 0.3), prism(g['slit'], z['back'] - E, zw + 0.9 + 0.2)]
    cuts += [cyl(x, y, 2.3, z['dial'][1] - E, z['head']) for x, y in g['ne_heads']]
    from shapely.geometry import box
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = sorted((sx * case.LUG_X[0], sx * case.LUG_X[1])); ly = sorted((sy * (case.SLOT_Y0 - 0.1), sy * (case.H / 2 + 2.0)))
            cuts.append(prism(box(lx[0] - 0.1, ly[0], lx[1] + 0.1, ly[1]), z['back'] - E, zr + 0.1))
    # the front's relief: the ring round the window and the side rails down to the crystal's level, their slots, the corner faces
    for rp in f['ring'] + f['rails']: cuts.append(prism(rp, zg, zt + E))
    for sl in f['side_slots']: cuts.append(prism(sl, zt - case.RELIEF - case.SIDE_SLOT[2], zt + E))
    for c in f['corners']:
        (px, py), (tx, ty), (nx, ny) = c['p1'], c['t'], c['n']; s0, s1 = case.CF_S[0] - 1.0, case.CF_S[1] + 1.0
        (ma, za), (mb, zb), (mc, zc) = case.CF_PROF
        ze = zc - (zb - zc) / (mb - mc) * 1.0                                                        # (the outer slope carried 1.0 past the edge)
        prof = [(-1.0, zt + E), (ma + 0.02, zt + E), (ma, zt + za), (mb, zt + zb), (mc, zt + zc), (-1.0, zt + ze)]     # (m in from the edge, z)
        pts = [[px + s0 * tx + m * nx, py + s0 * ty + m * ny, zz] for m, zz in prof]
        wedge = {'kind': 'pprism', 'pts': pts, 'vec': [(s1 - s0) * tx, (s1 - s0) * ty, 0.0]}
        cuts.append(inter(wedge, prism(c['plan'], zt + ze - E, zt + 2 * E)))                      # (clipped to the facet's plan: its ends, the pads)
        cuts.append(prism(c['slot'], zt - case.RELIEF, zt + E))
    for sy in (-1, 1):
        for yv in (18.3, 20.2, 22.1): cuts.append(prism(case.stadium(-10.0, 10.0, sy * yv, 1.0), zt - 1.0, zt + E))
    # 45° bevels: the window's edge where the ring meets it (not at the plaques' faces), and the outer rim where the top is flush
    bw = case.BEVEL_WIN
    # (the bevel's tool follows the window without its plaques, all convex, so its offset can't fold; the plaque zone is clipped off)
    oct_r = g['win_oct'].buffer(-0.3, 32, join_style=1).buffer(0.3, 64, join_style=1)
    cuts.append(inter(bevel(oct_r, zg - bw, zg + E), prism(f['ring_all'].buffer(0.2, join_style=2).difference(f['plq_zone']), zg - bw - E, zg + E)))
    cf = case.CH_FRAME                                                                              # the flush top's inner edges, 45°
    cuts.append(bevel(f['opening'], zt - cf, zt + E))
    bm = case.BEVEL_RIM
    keep = [prism(g['body'], z['back'] - E, zt - bm), draft(g['body'], zt - bm, zt + E, 45)]
    plq, side = g['scr'][:4], g['scr'][4:]
    for x, y in plq: cuts += [cyl(x, y, 1.15, zr, zt + E), cyl(x, y, 2.2, zt - 0.9, zt + E)]
    for x, y in side: cuts += [cyl(x, y, 0.625, z['back'] - E, zt + E), cyl(x, y, 1.6, zt - 0.5, zt + E)]
    parts.append({'id': 'D9', 'name': 'Faceplate-and-body', 'solid': [prism(g['body'], z['back'], zt)], 'keep': keep, 'cuts': cuts})
    # crystal
    parts.append({'id': 'D10', 'name': 'Crystal', 'solid': [prism(g['cry_out'], z['cry'][0], z['cry'][1])],
                  'cuts': [prism(g['cry_out'].buffer(0.05).difference(g['boss']), z['cry'][1] - case.CRYSTAL_STEP, z['cry'][1] + E)]})
    # dial plate
    dc = [cyl(c[0], c[1], 9.8, z['dial'][0] - E, z['dial'][1] + E) for c in g['discs']]
    dc += [cyl(x, y, 2.3, z['dial'][0] - E, z['dial'][1] + E) for x, y in g['ne_heads']]
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
    for x, y in plq: lc.append(cyl(x, y, 0.8, zr - 5.5, zr + E))          # the plaque screws' threads (M2x14 reaches 5.1), 5.5 deep into each riser
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
        if op['kind'] == 'draft':         # a face grown along z with a draft angle (45: a chamfer)
            ss = [cq.Solid.extrudeLinear(face(f), cq.Vector(0, 0, op['z1'] - op['z0']), taper=op['taper']).translate(cq.Vector(0, 0, op['z0'])) for f in op['faces']]
            return ss[0] if len(ss) == 1 else ss[0].fuse(*ss[1:])
        if op['kind'] == 'pprism':        # a planar polygon in space grown along a vector
            w = cq.Wire.makePolygon([cq.Vector(*q) for q in op['pts']], close=True)
            return cq.Solid.extrudeLinear(cq.Face.makeFromWires(w), cq.Vector(*op['vec']))
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
        base = os.path.join(outdir, f"{p['id']}-{p['name']}")
        ok = body.isValid()                      # (checked before the STL: meshing it can upset OCC's checker on a sound solid)
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
        cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.005, angularTolerance=0.05)
        back = cq.importers.importStep(base + '.step').vals()
        bb = body.BoundingBox()
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
