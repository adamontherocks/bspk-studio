# BSPK Studio — Simulator Specification

> **Superseded (2026-11-06) by [`VISION.md`](VISION.md).** Kept for history: this was the 2026-11-03 plan (Fusion-centred, watch-specific), abandoned on 2026-11-04.

**Version:** 0.1-spec (scaffold spec; v1 capability list)
**Date:** 2026-11-03
**Owner:** Adam Williams
**Status:** Spec locked; v0.1 implemented; v0.2+ scope defined below.

---

## 1. Purpose

A browser-based parametric design simulator for mechanical hardware. Composes parts from a shared library of parametric primitives (cushion profiles, extrudes, pivots, gears, bosses, etc.), supports live parameter iteration in 3D, checks interference and articulation, and exports Fusion-Python scripts that author the authoritative CAD in Fusion 360.

**Role in the workflow:**
1. **Sim (this tool):** design, iterate, interference-check, articulation-test, spec export. 48 of 50 design decisions happen here.
2. **Fusion 360:** authoritative parametric CAD, tolerance stack, manufacturing-specific features, STEP/STL export. Last 2 decisions + all manufacturing decisions.
3. **Shop (Makera CAM / print slicer):** workholding, toolpaths, feeds/speeds. Not CAD.

Each tier inherits from the one above. The sim is cheap/fast/forgiving; Fusion is slow/deterministic; the shop is final.

---

## 2. Architecture

### 2.1 Library + project compositions

Parts are built by composing generic parametric primitives from `lib/`. Project folders under `projects/` hold the per-part compositions and the orchestrator that assembles them.

```
bspk-studio/
├── sim/                                # Simulator UI (HTML/JS/Three.js)
├── lib/                                # Generic parametric library — JS + Python mirrors
│   ├── profiles/   (cushion, circle, polygon, spline)
│   ├── operations/ (extrude, revolve, sweep, loft, boolean)
│   ├── features/   (hex_boss, threaded_hole, fillet, chamfer, pivot_bracket)
│   ├── gears/      (involute_spur, bevel)
│   └── primitives/ (disc, cylinder, box)
├── projects/
│   └── hemistitch/
│       ├── parts/          # One file per part, composes library primitives
│       ├── assembly.py     # Thin orchestrator — imports parts, builds the assembly
│       └── params.json     # Parameter block exported from the sim
└── docs/
```

### 2.2 Dual implementation

The library exists in **two languages**: JavaScript for the sim's in-browser preview mesh generation, Python for Fusion-Python output. Two implementations kept in sync by convention and tests. If/when the library grows substantial, consider unifying on OpenCascade WASM (Replicad) as a single kernel.

---

## 3. Capability list

### 3.1 In v0.1 (shipped in initial scaffold)

- Three.js scene with orbit / zoom / pan
- Reference grid
- One part type: cushion case (parametric)
- Parameter panel with live sliders / inputs
- Interactive parts panel (click label to highlight; hide toggle)
- Save / load scene state as JSON (local file download / upload)
- Undo / redo stack (full history)
- Light / dark theme, viewer-driven
- Z-up coordinate system; millimeters throughout

### 3.2 v0.2–v1 (roadmap)

**Core rendering & interaction**
- View presets (iso, top, side, front) — partial in v0.1; polish in v0.2
- Section views (slice through arbitrary plane)
- Exploded-view toggle (parts separate along assembly axis)
- Transparency / x-ray mode
- Measurement tools (point-to-point distance, face-to-face angle)
- Dimension overlays on the model (toggle; default off)

**Parametric part system**
- Add / remove / duplicate parts
- Group parts into assemblies (case / movement / drive unit)
- Lock parameters once committed
- Color-code parts by function or group
- New part types beyond cushion case: circle profile, polygon profile, SVG import, spline profile

**Material and manufacturing representation**
- Per-part material from library: PLA, PETG, SLA resin, MJF nylon, aluminum, brass, steel, titanium, custom
- Per-part manufacturing method: FDM print, SLA print, MJF, CNC mill, waterjet, laser-cut, off-the-shelf
- Method-specific constraints: min wall thickness, min internal radius, overhang angle
- Visual callout on parts violating their method's constraints
- Appearance per material (brushed, matte, clear) — v2 polish
- Mass + rough cost summary — v2 (density + cost tables)

**Interference, fit, and clearance**
- AABB overlap check (fast, approximate)
- Triangle-mesh intersection (precise) for named critical interfaces
- Boolean subtract: movement envelope ÷ case internal, report free space
- Per-interface clearance targets with pass/fail
- Visual callout on clashing parts
- Automatic sweep on every save + on-demand "Run Checks" button

**Articulation / kinematics**
- Revolute joints (lug swing, gear rotation)
- Scrubbable joint parameters
- Time-driven gear rotation at ratio-correct rates
- Articulation sweep ("lug 0→45°, report max collision")
- Per-frame collision check during animation

**State management & handoff**
- Named snapshots with revert
- Per-part Fusion-Python stub export (THE handoff artifact)
- STL export for quick-look (not production)
- Spec JSON export (schema in `docs/SPEC_JSON.md`, TBD)

**Reference & input**
- Import reference image, pin to a plane as backdrop
- Import SVG or 2D sketch for tracing/scaling
- Reference geometry (planes, axes, points for alignment)

**Documentation**
- Markdown notes attached to parts
- Screenshot export at named viewpoints

### 3.3 Explicitly OUT of scope

- Full involute gear meshing (Study 029-style approximation is sufficient)
- Physics: mass / spring / friction / deflection — different tier of tool
- Toolpath / CAM preview — Fusion's job
- PBR lighting
- Multi-user collaboration
- Direct STEP export from sim — route through Fusion

---

## 4. Data model

### 4.1 Scene state JSON

```json
{
  "version": "0.1",
  "project": "hemistitch",
  "parts": [
    {
      "id": "case_middle",
      "type": "cushion_case",
      "visible": true,
      "params": {
        "width": 200,
        "height": 116,
        "depth": 67,
        "corner_radius": 16,
        "tonneau_sagitta": 4
      }
    }
  ],
  "view": {
    "camera_position": [120, -240, 180],
    "camera_target": [0, 0, 0]
  }
}
```

Key order deterministic (alphabetical) so git diffs are meaningful. Pretty-printed with 2-space indent.

### 4.2 Parameter definitions

Each part type registers a parameter schema: `{name, label, type, min, max, step, default, unit}`. The sim renders UI controls from the schema. The Python library reads the same schema for script generation.

---

## 5. Deployment

**GitHub Pages:** static hosting from the `/sim` folder of the `main` branch. URL: `https://<username>.github.io/bspk-studio/`. Works offline too: clone and open `sim/index.html` locally.

**Scene state workflow:** edit in sim → "Export JSON" downloads a file → place in `projects/<name>/params.json` → commit → push → changes visible on the live URL.

**Future:** optional GitHub API integration for direct read/write of scene state without download/upload. v2+.

---

## 6. Conventions

- **Units:** millimeters throughout. No cm, no inches, no mixed units. (Consistent with the AXIS v1 project's rule and Fusion's string-form input.)
- **Coordinate system:** Z up. XY is the horizontal plane. Fusion-consistent for clean handoff.
- **Naming:** `snake_case` for parameter names, part IDs, file names. `PascalCase` for JavaScript classes. `snake_case` for Python modules and functions.
- **Color coding:** groups get distinct colors (case = warm gray, movement = brass, drive = cool gray). Per-function tint within a group optional.

---

## 7. Roadmap

| Version | Scope | Status |
|---|---|---|
| v0.1 | Scaffold + cushion case + parameter panel + parts panel + save/load + undo | Shipped |
| v0.2 | Materials + methods + method constraint callouts | Planned |
| v0.3 | Interference engine (AABB + mesh intersect) + per-interface clearance targets | Planned |
| v0.4 | Articulation (revolute joints) + lug-swing sweep + gear rotation | Planned |
| v0.5 | Library expansion: circle, polygon, SVG profiles; extrude, revolve, sweep ops | Planned |
| v0.6 | Fusion-Python export: per-part scripts + orchestrator stub | Planned |
| v0.7 | Reference image pin + measurement tools + dimension overlays | Planned |
| v0.8 | Section views + exploded view + transparency + screenshots | Planned |
| v1.0 | All v0.2–v0.8 features polished; one Hemistitch build run end-to-end | Milestone |

---

## 8. Open questions

- Fusion-Python authoring: **one script per part + thin orchestrator** (locked for v0.6).
- Scene state storage: **local JSON file, GitHub-committed** (locked). API-based sync deferred to post-v1.
- Deployment: **GitHub Pages from `/sim`** (locked).
- Repo location: **separate `bspk-studio` repo**, not a subfolder of `axis-v1` (locked).

---

*Spec written 2026-11-03 as part of the BSPK design simulator project. Updated with each version milestone.*
