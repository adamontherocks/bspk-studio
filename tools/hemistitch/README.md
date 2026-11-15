# Hemistitch plate generators

How `sim/projects/hemistitch-slava.json` was made (2026-11-11 → 13). Run from this folder with Python 3 (matplotlib only for the plot).

- `layout.py` → `layout.json`: the estimated Slava 5671 train inside its own frame, rotated so the balance points at the case's center line.
- `outline.py`: the case outline as true geometry (AXIS × 2.5, r 10 corners, 4.25 mm bows tangent to them), sampled as 80 evenly spaced smooth dots.
- `make_slava.py layout.json out.json`: the project and the six stacked plates with every cut (the seven 2026-11-12 fixes included).
- `engineer.py adam-scene.json generated.json out.json`: Claude's pass on Adam's 2026-11-13 plate mods (motion layer split into left bridge, crescent and right top plate; discs sunk into P6). Reads his autosaved scene and the generated project; writes the version now in `sim/projects/`.
- `plot2.py scene.json out.png`: top views of the motion layer and P6.
- `geo.py`: the sim's outline spline (Catmull-Rom as Béziers), ported.
