# Turned parts for the 4th axis (generic; any project). VISION.md §7, R7.
# A turned part is drawn as half its profile: a closed sketch on a plane through its axis (the axis is the line v = turn.v; the
# profile is what is above it), turned about that line. On it, a worm (a helical groove cut into the blank over a span of the axis:
# module, starts, hand; its pitch diameter is the blank's diameter there less 2 modules) and flutes (round-bottomed grooves along the
# axis, as a ball end mill cuts them: count, width, depth). It is cut whole from rod on the Air's 4th axis, so it isn't resolved
# into floors: the export is the true solid (STEP for Fusion, STL for MakeraCAM's rotation toolpath) straight from the profile.
#   d.turn = {v}            d.worm = {from, to, module, starts, hand, pa}            d.flutes = {from, to, count, width, depth}
#   d.stock = rod Ø it is cut from (optional: checked)
import json, math, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
VENV_PY = os.path.join(ROOT, '.venv', 'bin', 'python')
PLANE_IDX = {'z': (0, 1, 2), 'y': (0, 2, 1), 'x': (1, 2, 0)}      # model axis of u, of v, of the plane's normal (index.html)

def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40] or 'part'

def worm_numbers(w, r_blank):
    m = float(w['module']); n = int(w.get('starts') or 1); pa = math.radians(float(w.get('pa') or 20))
    rp = r_blank - m; p = math.pi * m
    return {'m': m, 'starts': n, 'pa': pa, 'rp': rp, 'rr': rp - 1.25 * m, 'ro': r_blank, 'pitch': p, 'lead': n * p,
            'lead_deg': math.degrees(math.atan(n * p / (2 * math.pi * rp))), 'hand': w.get('hand') or 'right'}

def plan(J, pid):
    """the profile as fitted lines and arcs in the part's own frame (x along the axis, y = radius), and where that frame sits"""
    import numpy as np
    from geo import spline_poly
    from fit import fit_chain
    st = J['state']; d = next(x for x in st['drawn'] if x['id'] == pid); k = next(s for s in st['sketches'] if s['id'] == d['sketch'])
    av = float(d['turn'].get('v', 0)); ax = k['plane']['axis']; off = k['plane']['offset']
    P = spline_poly(k['points'])
    X = np.column_stack([P[:, 0], np.maximum(0.0, P[:, 1] - av)])
    if (P[:, 1] - av).min() < -1e-3: raise ValueError(f"{pid}: part of its profile is below its axis (v {av:g}); draw only the half above it")
    a = 0.5 * float(np.dot(X[:, 0], np.roll(X[:, 1], -1)) - np.dot(X[:, 1], np.roll(X[:, 0], -1)))
    if a < 0: X = X[::-1]
    i0 = int(np.argmin(X[:, 0] + 1e-6 * X[:, 1])); X = np.roll(X, -i0, 0)
    segs = fit_chain(np.vstack([X, X[:1]]))
    def r_at(u):                                   # the blank's radius at u: the largest crossing of the profile there
        best = 0.0
        for (x0, y0), (x1, y1) in zip(X, np.roll(X, -1, 0)):
            if min(x0, x1) - 1e-9 <= u <= max(x0, x1) + 1e-9 and abs(x1 - x0) > 1e-12: best = max(best, y0 + (y1 - y0) * (u - x0) / (x1 - x0))
        return best
    job = {'name': d.get('name') or pid, 'start': X[0].tolist(), 'segs': [[s[0]] + [list(map(float, q)) for q in s[1:]] for s in segs],
           'u0': float(X[:, 0].min()), 'u1': float(X[:, 0].max()), 'rmax': float(X[:, 1].max()), 'axis': ax, 'offset': off, 'v': av,
           'place': d.get('place'), 'stock': d.get('stock')}
    if d.get('worm'):
        w = d['worm']; u_mid = (w['from'] + w['to']) / 2; wn = worm_numbers(w, r_at(u_mid))
        job['worm'] = dict(wn, **{'from': float(w['from']), 'to': float(w['to'])})
    if d.get('flutes'):
        f = d['flutes']; job['flutes'] = {'from': float(f['from']), 'to': float(f['to']), 'count': int(f['count']), 'width': float(f['width']),
                                          'depth': float(f['depth']), 'r': r_at((f['from'] + f['to']) / 2)}
    return job

def build(job, base):
    import cadquery as cq
    t0 = time.time(); V = cq.Vector
    p = V(job['start'][0], job['start'][1], 0); edges = []
    for s in job['segs']:
        if s[0] == 'L': q = V(s[1][0], s[1][1], 0); e = cq.Edge.makeLine(p, q)
        else: m, q = V(s[1][0], s[1][1], 0), V(s[2][0], s[2][1], 0); e = cq.Edge.makeThreePointArc(p, m, q)
        if (q - p).Length > 1e-7: edges.append(e)
        p = q
    face = cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))
    body = cq.Solid.revolve(face, 360, V(0, 0, 0), V(1, 0, 0))
    notes = []
    w = job.get('worm')
    if w:
        # the groove as an axial section swept along a helix (Frenet keeps it an axial section all the way), one per start,
        # run a lead past each end and trimmed to the span, so the thread ends square at the span's ends
        rp, rr, ro, pa, P_ = w['rp'], w['rr'], w['ro'], w['pa'], w['pitch']
        top = ro + 0.3; width = lambda r: P_ / 2 + 2 * (r - rp) * math.tan(pa)
        prof = [(rr, -width(rr) / 2), (rr, width(rr) / 2), (top, width(top) / 2), (top, -width(top) / 2)]
        L = (w['to'] - w['from']) + 2 * w['lead']
        helix = cq.Wire.makeHelix(w['lead'], L, rp, lefthand=w['hand'] == 'left')
        sec = cq.Workplane('XZ').polyline([(x - rp + rp, z) for x, z in prof]).close()
        groove = sec.sweep(cq.Workplane('XY').add(helix), isFrenet=True).val()
        grooves = [groove.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * k / w['starts']) for k in range(w['starts'])]
        tool = grooves[0].fuse(*grooves[1:]) if len(grooves) > 1 else grooves[0]
        tool = tool.rotate(V(0, 0, 0), V(0, 1, 0), 90).translate(V(w['from'] - w['lead'], 0, 0))    # helix axis Z -> the part's X
        span = cq.Solid.makeBox(w['to'] - w['from'], 4 * top, 4 * top, V(w['from'], -2 * top, -2 * top))
        body = body.cut(tool.intersect(span))
        notes.append(f"worm: module {w['m']:g}, {w['starts']} start{'s' if w['starts'] > 1 else ''}, {w['hand']}-hand, pitch Ø{2 * rp:.3f}, outside Ø{2 * ro:.3f}, root Ø{2 * rr:.3f}, "
                     f"lead {w['lead']:.3f} mm ({w['lead_deg']:.2f}° lead angle), groove {width(rr):.3f} mm wide at the root, over {w['to'] - w['from']:g} mm")
    f = job.get('flutes')
    if f and f['count'] >= 2:
        rc = f['width'] / 2; rc_at = f['r'] - f['depth'] + rc; tools = []
        for k in range(f['count']):
            a = 2 * math.pi * k / f['count']; y, z = rc_at * math.cos(a), rc_at * math.sin(a)
            t = cq.Solid.makeCylinder(rc, f['to'] - f['from'], V(f['from'], y, z), V(1, 0, 0))
            t = t.fuse(cq.Solid.makeSphere(rc, V(f['from'], y, z), angleDegrees1=-90, angleDegrees2=90), cq.Solid.makeSphere(rc, V(f['to'], y, z), angleDegrees1=-90, angleDegrees2=90))
            tools.append(t)
        body = body.cut(*tools)
        notes.append(f"crown: {f['count']} flutes, Ø{f['width']:g} ball, {f['depth']:g} deep, over {f['to'] - f['from']:g} mm")
    # into the scene: the part's x is the sketch's u axis; its y the sketch's v (up from the axis line); its z the plane's normal
    iu, iv, ic = PLANE_IDX[job['axis']]
    def basis(i): e = [0.0, 0.0, 0.0]; e[i] = 1.0; return V(*e)
    o = [0.0, 0.0, 0.0]; o[iv] = job['v']; o[ic] = job['offset']
    xd, yd = basis(iu), basis(iv); zd = xd.cross(yd)
    loc = cq.Location(cq.Plane(origin=V(*o), xDir=xd, normal=zd))
    body = body.moved(loc)
    pl = job.get('place')
    if pl and pl.get('deg'): body = body.rotate(V(*pl['pivot']), V(*pl['pivot']) + V(*pl['axis']), pl['deg'])
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.step')
    cq.exporters.export(cq.Workplane('XY').add(body), base + '.stl', tolerance=0.002, angularTolerance=0.05)
    mem = body.isValid(); back = cq.importers.importStep(base + '.step').vals(); ok = mem and bool(back) and all(v.isValid() for v in back)
    D = 2 * job['rmax']; st = job.get('stock')
    log = (f"one solid turned about its axis; {job['u1'] - job['u0']:.2f} mm long, Ø{D:.3f} at its widest"
           + (f" (from Ø{st:g} rod: {(st - D) / 2:.3f} mm to turn off)" if st and st >= D else f" (WIDER than the Ø{st:g} rod it is to be cut from)" if st else '')
           + ('; ' + '; '.join(notes) if notes else '') + f"; volume {body.Volume():.2f} mm³; "
           + ("valid, checked by reading the file back" if ok else "NOT valid" + (" once written and read back" if mem else '')) + f"; {time.time() - t0:.1f} s")
    return {'path': base + '.step', 'step': base + '.step', 'stl': base + '.stl', 'valid': ok, 'volume_mm3': round(body.Volume(), 3), 'log': log}

def export(J, pid, outdir):
    t0 = time.time()
    job = plan(J, pid)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{re.sub(r'[^A-Za-z0-9]+', '-', pid).strip('-')}-{slug(job['name'])}")
    try: run = subprocess.run([VENV_PY, __file__, '--build', base], input=json.dumps(job).encode(), capture_output=True, timeout=300)
    except subprocess.TimeoutExpired: return {'error': 'the solid took longer than 5 minutes'}
    if run.returncode != 0: return {'error': run.stderr.decode(errors='replace')[-2000:]}
    out = json.loads(run.stdout)
    out['log'] = ("Turned part for the 4th axis: STEP (Fusion) and STL (MakeraCAM's rotation toolpath), no DXF (it isn't cut in floors).\n"
                  + out['log'] + f".\nAll in {time.time() - t0:.1f} s.")
    return out

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--build':
        sys.stdout.write(json.dumps(build(json.load(sys.stdin), sys.argv[2])))
    else:
        print(json.dumps(export(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]), indent=1))
