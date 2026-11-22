# Export a resolved part for the machine (generic; VISION.md §7, R7).
# Writes, into OUTDIR:
#   <pid>-<name>.step / .stl   the solid, exactly what the sim shows for the resolved part: built as one slab per floor band (the plate's
#                              material there, from the tiers) glued into one solid, then the drilled holes cut as true circles (seats as
#                              counterbores, countersinks as true 90° cones). World coordinates, so parts line up when brought together.
#   <pid>-<name>.dxf           for 2.5D CAM (Makera Studio): the outline on layer OUTLINE, each tier's rings on layer DEPTH_<mm from the
#                              milled face>, each drilled hole a true circle on layer DRILL_<Ø>_DEPTH_<mm> (THROUGH for through cuts).
# Two steps, two Pythons: the slabs are cut with pyclipper (system python, like the resolver); the solid is made with CadQuery (.venv).
# Cutting each tier out of a block instead took over 10 minutes for one plate: the tiers share their walls exactly (one wall across
# heights), and solid booleans on coincident faces crawl. Stacked slabs only touch, and are glued.
#   python3 export_step.py SCENE.json PID OUTDIR
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
VENV_PY = os.path.join(ROOT, '.venv', 'bin', 'python')
DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}
DRILL_MAX = 3.2

def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40] or 'part'
def face_z(d, k):
    """(z of the front face, z of the back face), as the sim's faceOffsets: pushed out along +z, -z or both"""
    z0, T = k['plane']['offset'], d['thickness']; g = d.get('grow') or 'plus'
    if g == 'minus': return z0, z0 - T
    if g == 'both': return z0 - T / 2, z0 + T / 2
    return z0, z0 + T

def plan(J, pid):
    """step 1 (pyclipper): the slabs, the drilled holes and the DXF content, as plain data"""
    import pyclipper as pc
    from geo import P, F, union, diff
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid); k = next(s for s in st['sketches'] if s['id'] == d['sketch'])
    res = d.get('resolved')
    if not res: raise ValueError(f'{pid} is not resolved: resolve it first, so the file is what the machine will cut')
    T = d['thickness']; zf, zb = face_z(d, k); face = res.get('face', 'back')
    mz = zb if face == 'back' else zf; sgn = -1 if mz == max(zf, zb) else 1        # from the milled face into the part
    outline = union([P(res['outline'])])
    cuts = sorted({min(T, t['depth']) for t in res['tiers']})
    bounds = sorted(set([0.0] + cuts + [T]))
    slabs = []
    for s0, s1 in zip(bounds, bounds[1:]):
        air = [P(r) for t in res['tiers'] if t['depth'] >= s1 - 1e-6 for r in t['paths']]
        mat = diff(outline, union(air)) if air else outline
        if not mat: continue
        za, zb_ = mz + sgn * s0, mz + sgn * s1
        slabs.append({'z0': min(za, zb_), 'z1': max(za, zb_), 'rings': [[[round(x, 4), round(y, 4)] for x, y in F(p)] for p in mat]})
    holes = []
    for c in d.get('cuts') or []:
        own = c['kind'] in DRILLED and c.get('d') and c['d'] <= DRILL_MAX
        if c['kind'] == 'pocket' or not c.get('d') or not (own or (c.get('from') or 'front') != face): continue
        at = st['pos'].get(c['axis']) if c.get('axis') and st['pos'].get(c['axis']) else c['at']
        fz = zb if c.get('from') == 'back' else zf
        holes.append({'at': at, 'd': c['d'], 'z': fz, 'dir': -1 if fz == max(zf, zb) else 1, 'depth': T if c.get('depth') is None else min(T, c['depth']),
                      'seat': c.get('seat'), 'csk': c.get('csk'), 'through': c.get('depth') is None or c['depth'] >= T - 1e-6})
    def strictly_simple(paths):      # no ring touching itself at a point (the solid modeller rejects those)
        c = pc.Pyclipper(); c.StrictlySimple = True; c.AddPaths(paths, pc.PT_SUBJECT, True)
        return c.Execute(pc.CT_UNION, pc.PFT_NONZERO, pc.PFT_NONZERO)
    def grouped(paths):              # rings -> faces: each outer ring with the islands inside it
        rings = strictly_simple(paths); outs = [r for r in rings if pc.Orientation(r)]; isl = [r for r in rings if not pc.Orientation(r)]
        groups = {i: [] for i in range(len(outs))}
        for h in isl:
            inside = [i for i, o in enumerate(outs) if pc.PointInPolygon(h[0], o) == 1]
            if inside: groups[min(inside, key=lambda i: abs(pc.Area(outs[i])))].append(h)
        return [{'outer': F(o).round(4).tolist(), 'holes': [F(h).round(4).tolist() for h in groups[i]]} for i, o in enumerate(outs)]
    faces = [dict(f, depth=min(T, t['depth'])) for t in res['tiers'] for f in grouped([P(r) for r in t['paths']])]
    for sl in slabs: sl['faces'] = grouped([P(r) for r in sl['rings']])
    volume = sum(sum(pc.Area(p) for p in [P(r) for r in s_['rings']]) / 1e8 * (s_['z1'] - s_['z0']) for s_ in slabs)
    return {'T': T, 'slabs': slabs, 'faces': faces, 'holes': holes, 'outline': res['outline'], 'tiers': res['tiers'], 'name': d.get('name') or pid,
            'z': [min(zf, zb), max(zf, zb)], 'mill_z': mz, 'into': sgn, 'volume_exact': volume}

def face_of(cq, f):
    """a face from the resolved part's exact dots, as straight lines (curve fitting was tried 2026-11-22: it gave an invalid solid
    on a plain pill outline, so it is out until walls are fitted as true arcs and lines)"""
    poly = lambda r: cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in r], close=True)
    return cq.Face.makeFromWires(poly(f['outer']), [poly(h) for h in f['holes']]), len(f['outer']) + sum(len(h) for h in f['holes']), 0

def build_dxf(job, base):
    """the 2.5D CAM file (Makera Studio): every floor exactly as resolved, one layer per depth; drilled holes as true circles"""
    import ezdxf
    doc = ezdxf.new('R2010', setup=True); msp = doc.modelspace(); doc.units = ezdxf.units.MM
    msp.add_lwpolyline(job['outline'], close=True, dxfattribs={'layer': 'OUTLINE'})
    for t in job['tiers']:
        lay = 'THROUGH' if t['depth'] >= job['T'] - 1e-6 else f"DEPTH_{t['depth']:.3f}"
        for r in t['paths']: msp.add_lwpolyline(r, close=True, dxfattribs={'layer': lay})
    for h in job['holes']:
        msp.add_circle(h['at'], h['d'] / 2, dxfattribs={'layer': f"DRILL_{h['d']:g}_" + ('THROUGH' if h['through'] else f"DEPTH_{h['depth']:.3f}")})
        if h.get('seat') and h['seat'].get('d', 0) > h['d']: msp.add_circle(h['at'], h['seat']['d'] / 2, dxfattribs={'layer': f"SEAT_{h['seat']['d']:g}_DEPTH_{h['seat']['depth']:.3f}"})
        if h.get('csk') and h['csk'].get('d', 0) > h['d']: msp.add_circle(h['at'], h['csk']['d'] / 2, dxfattribs={'layer': f"CSK90_{h['csk']['d']:g}"})
    doc.saveas(base + '.dxf')
    return {'dxf': base + '.dxf', 'layers': sorted({e.dxf.layer for e in msp})}

def build(job, base, single):
    """the solid (CadQuery): one solid per floor band (the plate's material there), fused into one body when `single`, else kept
    as stacked bodies; then the drilled holes; STEP and STL. (Cutting the tiers out of a block crawled: they share walls.)"""
    import cadquery as cq, math
    t0 = time.time(); n_edges = 0; fallback = 0; solids = []
    for sl in job['slabs']:
        for f in sl['faces']:
            face, k, fb = face_of(cq, f); n_edges += k; fallback += fb
            solids.append(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, sl['z1'] - sl['z0'])).translate(cq.Vector(0, 0, sl['z0'])))
    if single and len(solids) > 1: body = solids[0].fuse(*solids[1:], glue=True)
    else: body = cq.Compound.makeCompound(solids) if len(solids) > 1 else solids[0]
    for h in job['holes']:
        s, x, y = h['dir'], h['at'][0], h['at'][1]; D = h['depth'] + (0.01 if h['through'] else 0)
        cut = cq.Solid.makeCylinder(h['d'] / 2, D + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s))
        if h.get('seat') and h['seat'].get('d', 0) > h['d']:
            cut = cut.fuse(cq.Solid.makeCylinder(h['seat']['d'] / 2, min(h['depth'], h['seat']['depth']) + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s)))
        if h.get('csk') and h['csk'].get('d', 0) > h['d']:
            c = (h['csk']['d'] - h['d']) / 2
            cut = cut.fuse(cq.Solid.makeCone(h['csk']['d'] / 2 + 0.005, h['d'] / 2, c + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s)))
        body = body.cut(cut)
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.005, angularTolerance=0.05)
    bb = body.BoundingBox(); ok = body.isValid(); V = body.Volume(); nb = len(body.Solids())
    Vh = sum(math.pi * h['d'] ** 2 / 4 * h['depth'] for h in job['holes'])       # (approximate: seats, cones and overlaps not counted)
    return {'path': base + '.step', 'stl': base + '.stl', 'volume_mm3': round(V, 2), 'valid': ok, 'bodies': nb,
            'log': (f"one solid" if nb == 1 else f"{nb} stacked bodies, one per floor band (join them in Fusion for one body; CAM reads them from the top as one part)")
                   + f"; {len(job['tiers'])} tiers, {len(job['holes'])} drilled holes, walls as {n_edges} exact segments"
                   + (f", {fallback} face{'s' if fallback > 1 else ''} as exact straight lines" if fallback else '')
                   + f"; {bb.xlen:.2f} × {bb.ylen:.2f} × {bb.zlen:.3f} mm; volume {V:.1f} mm³ (the tiers give about {job['volume_exact'] - Vh:.1f}); "
                   + f"{'valid' if ok else 'NOT valid'}; {time.time() - t0:.1f} s"}

SOLID_SEGS = 15000   # more wall segments than this: the solid isn't tried (the bridges have 200-2,200 and build in a second or two)
SOLID_S = 120        # seconds allowed for the solid (STEP/STL). A big plate's walls are thousands of exact segments, which the solid modeller
                     # crawls through (the motion-works plate ran over an hour); fitting them as true arcs and lines is the next step for those.

def export(J, pid, outdir):
    """both steps: plan here (system python), build in .venv (CadQuery)"""
    job = plan(J, pid)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{pid}-{slug(job['name'])}")
    data = json.dumps(job).encode()
    run = subprocess.run([VENV_PY, __file__, '--build', base, 'dxf'], input=data, capture_output=True, timeout=300)
    if run.returncode != 0: return {'error': run.stderr.decode(errors='replace')[-2000:]}
    out = json.loads(run.stdout); out['path'] = out['dxf']
    note = f"DXF for 2.5D CAM (Makera Studio): every floor exactly as resolved, one layer per depth ({', '.join(out['layers'])})."
    segs = sum(len(r) for sl in job['slabs'] for r in sl['rings'])
    if segs > SOLID_SEGS:
        out['log'] = note + f"\nSTEP and STL: not made. Its walls are {segs:,} exact segments, too many for the solid modeller in reasonable time; fitting them as true arcs and lines is the next step."
        return out
    try:
        run = subprocess.run([VENV_PY, __file__, '--build', base, 'single' if len(job['slabs']) == 1 else 'stack'], input=data, capture_output=True, timeout=SOLID_S)
        if run.returncode == 0:
            sol = json.loads(run.stdout); out.update(step=sol['path'], stl=sol['stl'], valid=sol['valid'], volume_mm3=sol['volume_mm3'])
            note += f"\nSTEP and STL: {sol['log']}."
        else: note += '\nSTEP and STL: the solid modeller failed: ' + run.stderr.decode(errors='replace')[-300:]
    except subprocess.TimeoutExpired:
        note += f"\nSTEP and STL: not made. The solid took over {SOLID_S} s (its walls are thousands of exact segments; fitting them as true arcs and lines is the next step)."
    out['log'] = note
    return out

if __name__ == '__main__':
    if sys.argv[1] == '--build':
        job = json.load(sys.stdin)
        sys.stdout.write(json.dumps(build_dxf(job, sys.argv[2]) if sys.argv[3] == 'dxf' else build(job, sys.argv[2], sys.argv[3] == 'single')))
    else:
        print(json.dumps(export(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]), indent=1))
