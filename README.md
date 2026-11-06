# BSPK Studio

A browser-based **parts builder** that bridges designer and engineer. The designer places and shapes parts and decides what's locked; the engineer (Claude, plus validation built into the sim) checks fit, meshing and supports, reports conflicts with options, and adjusts what's unlocked. Parts export to STEP/STL through CadQuery — no Fusion in the generation path; Fusion or Plasticity are for detailing after export.

**Read [`VISION.md`](VISION.md) first.** It holds the goal, the working agreements, the full decision history, the product model, the build order and the open questions. `SIMULATOR_SPEC.md` is an earlier plan and is superseded.

## Status

A watch/clock movement is the beta test bed (not the product):

- `sim/index.html` — editable watch train: per-part locks, X/Y/Z/scale/thickness, move arrows, a meshing solver that never moves locked parts, auto-adjust for unlocked parts, logged conflict reports with options, undo.
- `sim/gear.html` — single involute gear with a CadQuery export script (STEP + STL).
- `sim/involute.js` — shared involute math.

Next steps are in `VISION.md` §7.

## Running locally

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory sim
```

Then open http://localhost:8765/.

The CadQuery environment lives in `.venv` (CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1, Python 3.14). Run an exported script with `.venv/bin/python <script>.py`.

## Deployment

`.github/workflows/deploy-sim.yml` uploads `/sim` to GitHub Pages on every push to `main`: https://adamontherocks.github.io/bspk-studio/. Pushing to `main` updates the public site.

## Conventions

- Millimetres throughout; Z up.
- Minimum gap is in real mm; print scale is a separate multiplier.
- Commit prefixes: `[iter]` for granular changes, `[checkpoint] <name>` + tag `checkpoint/<name>-vNN` at rest points, `[session-start]` / `[session-end]` + tag `session/YYYY-MM-DD-slug` at session boundaries.
