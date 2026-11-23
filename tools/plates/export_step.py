# Export a resolved part for the machine (generic; VISION.md §7, R7).
# Writes, into OUTDIR:
#   <pid>-<name>.step / .stl   the solid, what the sim shows for the resolved part: one slab per floor band (the plate's material
#                              there, from the tiers) glued into one solid, then the drilled holes cut as true circles (seats as
#                              counterbores, countersinks as true 90° cones). World coordinates, so parts line up when brought together.
#                              The walls are true arcs and straight lines through the resolved dots (fit.py: every dot within 2 µm),
#                              a wall shared by two floors fitted alike, so the floors meet exactly and glue into one solid.
#   <pid>-<name>.dxf           for 2.5D CAM (Makera Studio): the outline on layer OUTLINE, each tier's rings on layer DEPTH_<mm from the
#                              milled face>, each drilled hole a true circle on layer DRILL_<Ø>_DEPTH_<mm> (THROUGH for through cuts).
#                              Exactly the resolved dots.
# Two steps, two Pythons: the slabs are cut and fitted with pyclipper and numpy (system python, like the resolver); the solid is made
# with CadQuery (.venv). What did not work (2026-11-22): cutting each tier out of a block (over 10 minutes for one plate: the tiers
# share their walls, and solid booleans on coincident faces crawl); slabs with walls as the raw dots (12,000 edges a face: over an
# hour); spline fitting (an invalid solid on a plain pill outline).
#   python3 export_step.py SCENE.json PID OUTDIR
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
VENV_PY = os.path.join(ROOT, '.venv', 'bin', 'python')
DRILLED = {'hole', 'bearing', 'clear', 'screw', 'pilot', 'rod', 'dowel'}
DRILL_MAX = 3.2

SPECK_A = 1e-4      # mm²: a ring smaller than this is a speck, dropped (the resolver keeps tier rings from the same size)
SPECK_FLOOR = 1e-3  # mm²: a piece of floor smaller than this (about 30 × 30 µm) where two floors' walls meet is a speck, not a ledge

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
    # shared walls: each tier ring was thinned on its own, so two tiers carry the same wall with different dots; give them the same
    # dots first, so the floor bands cut from them meet exactly and their walls are fitted alike (fit.unify)
    from fit import unify, fit_faces, TOL
    flat = unify([res['outline']] + [r for t in res['tiers'] for r in t['paths']])
    tiers_u, i = [], 1
    for t in res['tiers']: tiers_u.append({'depth': t['depth'], 'paths': flat[i:i + len(t['paths'])]}); i += len(t['paths'])
    outline = union([P(flat[0])])
    cuts = sorted({min(T, t['depth']) for t in res['tiers']})
    bounds = sorted(set([0.0] + cuts + [T]))
    mats = []
    for s0, s1 in zip(bounds, bounds[1:]):
        air = [P(r) for t in tiers_u if t['depth'] >= s1 - 1e-6 for r in t['paths']]
        mats.append(diff(outline, union(air)) if air else outline)
    # floor specks: where a taper ends, two floors' walls can part for a few µm and meet again, leaving a speck of floor (µm²) between
    # them. Each goes to the band above, so its wall follows the band below there; from the far face up, so none is left behind.
    specks = 0
    for i in range(len(mats) - 2, -1, -1):
        if not mats[i]: continue
        sp = [q for q in diff(mats[i + 1], mats[i]) if pc.Orientation(q) and abs(pc.Area(q)) < SPECK_FLOOR * 1e8]
        if sp: mats[i] = union(mats[i], sp); specks += len(sp)
    slabs = []
    for (s0, s1), mat in zip(zip(bounds, bounds[1:]), mats):
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
        rings = [r for r in strictly_simple(paths) if abs(pc.Area(r)) >= SPECK_A * 1e8]     # (µm specks where two walls nearly meet: not features)
        outs = [r for r in rings if pc.Orientation(r)]; isl = [r for r in rings if not pc.Orientation(r)]
        groups = {i: [] for i in range(len(outs))}
        for h in isl:
            inside = [i for i, o in enumerate(outs) if pc.PointInPolygon(h[0], o) == 1]
            if inside: groups[min(inside, key=lambda i: abs(pc.Area(outs[i])))].append(h)
        return [{'outer': F(o).round(4).tolist(), 'holes': [F(h).round(4).tolist() for h in groups[i]]} for i, o in enumerate(outs)]
    for sl in slabs: sl['faces'] = grouped([P(r) for r in sl['rings']])
    volume = sum(sum(pc.Area(p) for p in [P(r) for r in s_['rings']]) / 1e8 * (s_['z1'] - s_['z0']) for s_ in slabs)
    # the walls as true arcs and straight lines (every dot within fit.TOL), stretches shared by two bands fitted alike
    allf = [f for sl in slabs for f in sl['faces']]
    fitted, fit_stats = fit_faces(allf)
    for f, fr in zip(allf, fitted): f['fit'] = fr
    return {'T': T, 'slabs': slabs, 'holes': holes, 'outline': res['outline'], 'tiers': res['tiers'], 'name': d.get('name') or pid,
            'z': [min(zf, zb), max(zf, zb)], 'mill_z': mz, 'into': sgn, 'volume_exact': volume, 'fit': dict(fit_stats, specks=specks, tol=TOL)}

def face_of(cq, f):
    """a face from the fitted walls (true arcs and straight lines through the resolved part's own dots)"""
    def wire(fr):
        p = cq.Vector(fr['start'][0], fr['start'][1], 0); edges = []
        for sg in fr['segs']:
            if sg[0] == 'L': q = cq.Vector(sg[1][0], sg[1][1], 0); edges.append(cq.Edge.makeLine(p, q))
            else:
                m, q = cq.Vector(sg[1][0], sg[1][1], 0), cq.Vector(sg[2][0], sg[2][1], 0); edges.append(cq.Edge.makeThreePointArc(p, m, q))
            p = q
        return cq.Wire.assembleEdges(edges)
    fr = f['fit']
    return cq.Face.makeFromWires(wire(fr['outer']), [wire(h) for h in fr['holes']]), len(fr['outer']['segs']) + sum(len(h['segs']) for h in fr['holes']), 0

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
    """the solid (CadQuery): one solid per floor band, glued into one body when `single`, else kept as stacked bodies; the drilled
    holes in one cut; STEP and STL. Then the STEP is read back and checked: a solid can be valid in memory and not once written (µm
    edges that cross at the file's tolerance: D3, 2026-11-22)."""
    import cadquery as cq
    t0 = time.time(); n = 0; solids = []
    for sl in job['slabs']:
        for f in sl['faces']:
            face, k, _ = face_of(cq, f); n += k
            solids.append(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, sl['z1'] - sl['z0'])).translate(cq.Vector(0, 0, sl['z0'])))
    if single and len(solids) > 1: body = solids[0].fuse(*solids[1:], glue=True)
    else: body = cq.Compound.makeCompound(solids) if len(solids) > 1 else solids[0]
    V0 = body.Volume(); tools = []
    for h in job['holes']:
        s, x, y = h['dir'], h['at'][0], h['at'][1]; D = h['depth'] + (0.01 if h['through'] else 0)
        cut = cq.Solid.makeCylinder(h['d'] / 2, D + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s))
        if h.get('seat') and h['seat'].get('d', 0) > h['d']:
            cut = cut.fuse(cq.Solid.makeCylinder(h['seat']['d'] / 2, min(h['depth'], h['seat']['depth']) + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s)))
        if h.get('csk') and h['csk'].get('d', 0) > h['d']:
            c = (h['csk']['d'] - h['d']) / 2
            cut = cut.fuse(cq.Solid.makeCone(h['csk']['d'] / 2 + 0.005, h['d'] / 2, c + 0.005, cq.Vector(x, y, h['z'] - s * 0.005), cq.Vector(0, 0, s)))
        tools.append(cut)
    if tools: body = body.cut(*tools)          # all holes in one cut (one at a time rebuilt the whole plate each time: 15 holes, 66 s)
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.005, angularTolerance=0.05)
    mem = body.isValid(); back = cq.importers.importStep(base + '.step').vals()
    ok = mem and bool(back) and all(v.isValid() for v in back)
    bb = body.BoundingBox(); V = body.Volume(); nb = len(body.Solids()); F = job['fit']
    dv = (V0 - job['volume_exact']) / job['volume_exact'] * 100
    return {'path': base + '.step', 'stl': base + '.stl', 'volume_mm3': round(V, 2), 'valid': ok, 'bodies': nb,
            'log': ("one solid" if nb == 1 else f"{nb} stacked bodies, one per floor band (join them in Fusion for one body; CAM reads them from the top as one part)")
                   + f"; {len(job['tiers'])} tiers, {len(job['holes'])} drilled holes; walls as {n:,} true arcs and straight lines ({F['arcs']:,} arcs), every resolved dot within {F['tol'] * 1000:g} µm"
                   + (f" ({F['exact_faces']} face{'s' if F['exact_faces'] > 1 else ''} with µm spikes kept as exact segments there)" if F.get('exact_faces') else '')
                   + (f" ({F['mended']} face{'s' if F['mended'] > 1 else ''} where the resolved wall crosses itself by less than the 0.1 µm grid, uncrossed)" if F.get('mended') else '')
                   + (f", {F['specks']} µm specks of floor where tapers end taken into the wall" if F.get('specks') else '')
                   + f"; {bb.xlen:.2f} × {bb.ylen:.2f} mm, {job['T']:g} thick; volume {V:,.1f} mm³ (before the drilled holes {V0:,.1f}; the resolved tiers give {job['volume_exact']:,.1f}, {dv:+.3f}%); "
                   + ("valid, checked by reading the file back" if ok else "NOT valid" + (" once written and read back" if mem else ""))
                   + f"; {time.time() - t0:.1f} s"}

SOLID_PIECES = 20000  # fitted wall pieces: more than this, the solid isn't tried (the main plate has about 800, the motion-works plate 3,200)
SOLID_S = 120         # seconds allowed for each try at the solid (STEP/STL); both big plates build in under 5

def export(J, pid, outdir):
    """both steps: plan here (system python), build in .venv (CadQuery). The solid is tried as one glued body first; if that isn't
    valid read back from the file, as stacked bodies (each band its own solid)."""
    t0 = time.time()
    if pid.startswith('G:'):                      # a gear part: the sim's gear numbers and its resolved floors, read like a plate
        import gears
        J = gears.as_drawn(J, pid)
    else:
        d = next((x for x in J['state']['drawn'] if x['id'] == pid), None)
        if d and d.get('turn'):                   # a turned part (4th axis): a true solid straight from its profile, worm and flutes
            import turned
            return turned.export(J, pid, outdir)
    job = plan(J, pid)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{re.sub(r'[^A-Za-z0-9]+', '-', pid).strip('-')}-{slug(job['name'])}")
    data = json.dumps(job).encode()
    run = subprocess.run([VENV_PY, __file__, '--build', base, 'dxf'], input=data, capture_output=True, timeout=300)
    if run.returncode != 0: return {'error': run.stderr.decode(errors='replace')[-2000:]}
    out = json.loads(run.stdout); out['path'] = out['dxf']
    note = f"DXF for 2.5D CAM (Makera Studio): every floor exactly as resolved, one layer per depth ({', '.join(out['layers'])})."
    pieces = job['fit']['pieces']
    if pieces > SOLID_PIECES:
        out['log'] = note + f"\nSTEP and STL: not made. Even as arcs and lines its walls are {pieces:,} pieces, too many for the solid modeller in reasonable time."
        return out
    tried = []
    for mode in (['single'] if len(job['slabs']) == 1 else ['single', 'stack']):
        try:
            run = subprocess.run([VENV_PY, __file__, '--build', base, mode], input=data, capture_output=True, timeout=SOLID_S)
        except subprocess.TimeoutExpired:
            tried.append(f"{'one body' if mode == 'single' else 'stacked bodies'}: over {SOLID_S} s"); continue
        if run.returncode != 0:
            tried.append(f"{'one body' if mode == 'single' else 'stacked bodies'}: the solid modeller failed ({run.stderr.decode(errors='replace')[-200:].strip()})"); continue
        sol = json.loads(run.stdout)
        if sol['valid'] or mode == 'stack':
            out.update(step=sol['path'], stl=sol['stl'], valid=sol['valid'], volume_mm3=sol['volume_mm3'])
            note += f"\nSTEP and STL: {sol['log']}." + (f" (Tried first: {'; '.join(tried)}.)" if tried else '')
            break
        tried.append("one body: not valid read back from the file")
    else:
        note += f"\nSTEP and STL: not made ({'; '.join(tried)})."
    out['log'] = note + f"\nAll in {time.time() - t0:.1f} s."
    return out

if __name__ == '__main__':
    if sys.argv[1] == '--build':
        job = json.load(sys.stdin)
        sys.stdout.write(json.dumps(build_dxf(job, sys.argv[2]) if sys.argv[3] == 'dxf' else build(job, sys.argv[2], sys.argv[3] == 'single')))
    else:
        print(json.dumps(export(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]), indent=1))
