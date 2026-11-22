# serve.py's bridge to the plate tools: one request as JSON on stdin, the answer as JSON on stdout. Run as its own process, so a
# change to the tools needs no server restart and a crash never takes the server down.
#   {"op": "resolve", "scene": {...}, "pids": ["D1", ...]}          -> {pid: resolved part, or {"error": text}}
#   {"op": "export", "scene": {...}, "pid": "D3", "outdir": "..."}  -> {"path", "log", ...} or {"error": text}
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

if __name__ == '__main__':
    req = json.load(sys.stdin)
    if req.get('op') == 'resolve':
        import resolve
        out = resolve.resolve_scene(req['scene'], req['pids'])
    elif req.get('op') == 'export':
        import export_step
        try: out = export_step.export(req['scene'], req['pid'], req['outdir'])
        except Exception as e: out = {'error': f'{type(e).__name__}: {e}'}
    else:
        out = {'error': f"unknown op {req.get('op')!r}"}
    sys.stdout.write(json.dumps(out))
