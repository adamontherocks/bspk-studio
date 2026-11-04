# BSPK Studio

A browser-based parametric design simulator for mechanical hardware projects. Compose parts from a shared library of parametric primitives, iterate on dimensions and spatial relationships in 3D, check interference and articulation, then export Fusion-Python scripts that build the authoritative CAD in Fusion 360.

**Role in the workflow:** pre-Fusion design surface. The sim is where 48 of 50 design decisions happen. Fusion is where the last 2 decisions and all the manufacturing-specific features live. Shop (Makera CAM / print slicer) comes after that.

## Status

v0.1 — architectural scaffold. Three.js scene, one part type (cushion case), parameter panel, interactive parts panel, save/load JSON, undo/redo. Material/method system, interference engine, articulation, and the Fusion-Python export all come in v0.2+.

See [`SIMULATOR_SPEC.md`](SIMULATOR_SPEC.md) for the full capability spec and roadmap.

## Layout

```
bspk-studio/
├── sim/            Interactive simulator (HTML/JS/Three.js) — opens in browser
├── lib/            Shared parametric library (profiles, operations, features, gears, primitives)
├── projects/       Per-project compositions (hemistitch is the first)
└── docs/           Reference material
```

## Running locally

Open `sim/index.html` directly in a browser. No build step. Scene state loads from `projects/<name>/params.json`.

## Deployment (GitHub Pages)

Sim is served from the `/sim` folder of this repo's `main` branch. To enable Pages on a fresh clone: Settings → Pages → Source: `main` branch, `/sim` folder. Live URL in ~1 minute at `https://<username>.github.io/bspk-studio/sim/`.

## Conventions

- Units: **millimeters** throughout
- Coordinate system: **Z up** (Fusion-consistent)
- Scene state: plain JSON, deterministic key order (git-friendly diffs)

## Commit cadence — three tiers

Every meaningful change lands on `main` as its own commit so the history reads as a design-revision log. Three prefixes mark the kind of change:

- **`[iter]`** — per-iteration commits. A primitive's dimensions shift, a new parameter slot is added, a bug is fixed, a doc gets a pointer update. Small, atomic, frequent.
- **`[checkpoint] <name>`** — a natural rest point in a primitive's design (case silhouette approved, lug geometry locked, bezel step tuned). Also gets a lightweight tag: `checkpoint/<name>-vNN`, e.g. `checkpoint/case-body-v01`. Use the tag to jump to "what did this look like when we called it done."
- **`[session-start] …` / `[session-end] …`** — session boundary markers. Each session also gets a lightweight tag: `session/YYYY-MM-DD-slug`, e.g. `session/2026-11-04-initial-scaffold`.

All three go to `main`. The prefix is the only differentiation; tags give quick jump points. Branches/PRs are reserved for experiments the design might reject wholesale (a parallel case primitive, an alternate interference algorithm) — mainline iteration is trunk-based.
