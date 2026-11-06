# BSPK Studio — Vision and Working Record

**Owner:** Adam Williams · **Engineering partner:** Claude · **Written:** 2026-11-06
**Covers:** the full conversation of 2026-11-03 → 2026-11-06 that produced this tool, plus every plan, decision and open question it raised.

This is the source of truth for *what BSPK Studio is for and how we build it*. `SIMULATOR_SPEC.md` (2026-11-03) is superseded by this document; it describes an earlier, Fusion-centred, watch-specific plan that was abandoned (see §4).

Status tags used below:
- **AGREED** — Adam said yes, or it's built and he accepted it.
- **PROPOSED** — discussed, Adam reacted positively, not yet built or not yet confirmed in detail.
- **OPEN** — a question nobody has answered yet.

---

## Contents

1. [The goal](#1-the-goal)
2. [The people and the tools around it](#2-the-people-and-the-tools-around-it)
3. [Working agreements](#3-working-agreements-non-negotiable)
4. [How we got here: decision history](#4-how-we-got-here-decision-history)
5. [What exists today](#5-what-exists-today)
6. [The product model going forward](#6-the-product-model-going-forward)
7. [Build order](#7-build-order)
8. [Open questions](#8-open-questions)
9. [Lessons paid for](#9-lessons-paid-for)
10. [Reference data](#10-reference-data)
11. [Glossary](#11-glossary)

---

## 1. The goal

**Ultimate goal (Adam):** hand Claude a sketch or an image and work together until it's a STEP file. Not "Claude converts a picture to geometry" — that doesn't work and pretending it does is the failure this project exists to get past. Instead: a design surface where Adam shapes parts directly, Claude does the engineering, and both can see the same model.

**What BSPK Studio is:** a universal **parts builder** — a browser simulator where a designer has complete control over the design of parts and their locations, and an engineer (Claude, plus automatic validation built into the sim) checks fit, function and physics, reports conflicts, and proposes or makes corrections.

> "my 'goal' is to build a sim that can bridge engineer with builder. 2 different thought processes and specialties boxed into one user friendly sim."

> "this ui is essentially a bridge or partnership for a designer and engineer. but the designer holds the reins."

**The kind of machine it's for.** Hudson's phrase, which Adam adopted: *Rube Goldberg machines.* Individual, multi-part packages of parts that interact, with strict tolerances, that also "go swoop, and whirr, as the designer sees fit."

> "this isnt going to be a barrel. this is going to be three swirly whirlys that go round and round with multiple transmissions, and may end up wanting to change the size of one because the designer says so and then you have to figure out all the new interferences and transmissions … that size is the new truth and the rest will need to be discussed as it needs repair."

**The watch/clock movement is the beta, not the product.** It's the test bed because it's a strong foundation: gears, transmissions, rates, supports, tight packaging. Everything built for it must be universal (gears, shafts, plates, bridges, sketched parts), with watch-specific logic kept in project data, never in the core.

**Why it matters to Adam.** He is half designer, half engineer:

> "you have no idea what its like to be 50% designer and 50% engineer. i can do both sides, but i cant do either side well. try explaining why the wall needs to go swoopy woopy dippy dive to an engineer and listening to the rebuttal. meanwhile if they can understand it enough to accept my why, im talented enough to hear the actual reasons it cant and what compromises can be made. this ui is potentially the tool that lets me design and build, while being assisted by ai, and automatic validation."

**Speed is the point.** A sketched-part approach that is far faster than Fusion or Plasticity for getting a concept shaped, fitted and checked in context; then export STEP to Fusion/Plasticity for detailing and manufacturing prep.

**Long horizon (Adam, 2026-11-03).** Learn the workflow while the machines arrive and the tech matures: 3D printing now; Makera Z1 (owned) and xHorse WM-100 (on the way) for 3-axis; in 2–5 years 5-axis milling or metal printing (XSnow's ~40-micron metal printer was about to hit Kickstarter). "eventually i want all this learning to land me as a skilled designer and developer for these types of machines."

---

## 2. The people and the tools around it

| Who / what | Role |
|---|---|
| **Adam** | Designer holding the reins. Places and shapes parts, decides what is locked, decides intent. Also does electronics, firmware, materials, CAM. |
| **Claude** | Engineer: research real dimensions, gear math, kinematics, interference and support logic, conflict reports, code for the sim and the CAD export. Asks the engineering questions ("is this going to fabrication? fixed axles or bearings?"). |
| **The sim's built-in engineer** | Deterministic code Claude writes: meshing solver, collision checks, auto-adjust. Fast and exact at geometry, but it is *rules*, not judgment. Judgment needs Claude in the loop (§6.2). |
| **Hudson** | Collaborator; coined "Rube Goldberg machines". |
| **ChatGPT** | Earlier ideation partner: Hemistitch concept artifacts and the Motion Works Study 029 viewer. Good at kinematic animation; blind to geometry, space and manufacturing. |
| **Gemini** | Renders/concepts as inputs. |
| **CadQuery (OpenCASCADE)** | Generates true-B-rep STEP and STL from Python. Replaced Fusion in the generation path (§4, 2026-11-04). |
| **Fusion 360 / Plasticity** | Manual detailing and manufacturing prep *after* export. Optional; one-way handoff (§6.7). |
| **Makera Studio / machine CAM** | Toolpaths. "all the cnc machines im intending to use have ai assisted cad so that helps." |

**Lane boundaries (agreed 2026-11-03):** Claude owns sim architecture, parametric geometry, checks, export. Adam owns electronics selection, firmware, timing scheme, materials, finishing, CAM. Shared: geometry decisions, assembly order, access points.

---

## 3. Working agreements (non-negotiable)

These came from hard corrections. Every future session should read them first.

1. **Listen, ask, research, be available. One step at a time.** "i want this to build slowly, accurately, efficiently, and in single paced steps." Adam: "you usually get an idea from me and attempt to build a skyscraper."
2. **"Can you X" is a capability question, not a go-order.** In exploratory chats answer how it would work; build only on a clear go. Confirm in one sentence when unsure.
3. **Chat before building.** When Adam says "lets just chat" or "dont build yet", produce no code.
4. **The canonical response pattern:**
   > "i want the center wheel larger" → "ok, let me take a look at that.... i see interference at the x. what do you wanna do about that"
   NOT "i saw interference so i rebuilt your whole thing."
5. **Never silently change things.** Every automatic change is logged, explained and undoable. One undo reverses a change and all its automatic fixes.
6. **The designer holds the reins.** The engineer makes the cost of a design choice visible and offers compromises; "no" is reserved for real physics/manufacturing limits and always comes with reasons and options.
7. **No false confidence.** Never claim something works, matches or is validated without checking it in the running sim and, for shapes, comparing against the reference visually. "I validated that JavaScript didn't throw" is not validation.
8. **Reference first.** For any part based on an image, open the reference *before* writing geometry. Describe what you see; Adam corrects; then build; then compare render to reference; iterate.
9. **Words can't carry shape.** "describing tonneau isnt a thing… you have to see it, reference it … produce it, compare it, adjust it, compare, adjust, compare, then validate." Shape needs direct manipulation (control points, polysplines) and image references, not prose specs.
10. **Universal, not watch-specific.** No watch-named folders, primitives or assumptions in the core.
11. **Don't ask Adam for impossible inputs.** "ok human, give me the x,y,z coordinates of a multifaceted chamfer" is not an acceptable ask. Give him tools to show it instead.
12. **Report honestly at the end of a turn:** what changed, what was tested and how, what's not done, what's not verified, what's uncommitted.

---

## 4. How we got here: decision history

### 2026-11-03 — Workflow theory

- **Fusion MCP vs "the API".** No API gives Claude direct sight of geometry; everything is pixels or numbers. Structured state dumps are the real feedback channel; screenshots are the sanity check.
- **Adam's original workflow idea:** ideate with ChatGPT → Claude validates the geometry → Python → STL to print / STEP for the Makera Z1.
- **What "validate" means**, four checks: kinematic (ratios, direction), geometric (involute profiles, module, undercut, centre distance), spatial (fit, interference, clearances), manufacturable (can the printer/mill resolve it).
- **Scale decision:** desktop size for 3D-printed proofs, "inches even… a 8"x1.5" movement package". Electric-motor driven; no balance wheels or springs for now ("i want to prove mech, not make my own oscillating organs"). Makera later to downsize and learn CAM.
- **Gear Composer** artifact built prematurely ([link](https://claude.ai/artifact/L3UrsmLntHYJRhg7twhLCb)). Lesson #2 above was recorded.
- **Hemistitch review** (ChatGPT artifacts): Compact Candidate C1 and Motion Works Study 029 (numbers in §10.4).
- **Simulator idea confirmed:** Adam talks through the design and provides sketches; Claude places parts in a simulator to check spatial relationships, interference and compatibility; converge to a proofed model; then CAD.
- **Image → case parts:** honest self-rating 5–6/10 first pass, 7–8 after iteration. Inventing a mechanism the photos don't show (e.g. how lugs articulate) rated 3–4/10 and must always be flagged.
- **Hemistitch desktop demonstrator concept** (the first project in mind, still **OPEN**): articulating-lug case (case middle, bezel, caseback, 4 lugs, faux crown, optional printed crystal, bought metal screws) plus a custom movement (main plate, bridges, gears, two time-telling discs, dial plate, motor + ESP32 + battery bracket "attached to or inside the movement the way a battery or the barrel spring would. keep the concept cohesive to a true mechanical watch"). Confidence 6–7/10 for a bench demonstrator in 2–4 months of weekend work; electronics the softest piece.
- **Motor "bible"** chosen and ordered (§10.5).
- **AXIS vs Hemistitch:** AXIS (repo `Next-Step-Inc/bspk-axis-v1`) is the *case* reference, scaled ~4× to ~8" wide; the ChatGPT movement was an arbitrary package.
- **Capability list for the sim** (most still valid as a backlog, §6.13): orbit/zoom, view presets, sections, visibility, x-ray, explode, measurement, parametric parts, add/remove/duplicate, groups, locks, colour by function, materials and methods with constraint callouts, interference, clearance targets, articulation sweeps, time-driven gear rotation, save/load JSON, snapshots, undo, export, reference images pinned to planes, SVG import, notes on parts, screenshots. Adam: "yeah, id say all the stuff. undo stack sounds awesome. highlightable labels… click on the label and it highlights the part… or even hide the part(s)… both on demand and save sweeps." Hosting on GitHub so it's accessible anywhere.
- **Universal architecture** (library of primitives + project compositions), repo named `bspk-studio`.
- **v0.1 built** (cushion case, sliders, parts panel, undo, save/load) as an artifact and local files.

### 2026-11-04 — The reset

- **The cushion failure.** v0.1's "cushion case" was a tonneau-proportioned slab, built from the word, without opening the reference images Adam had asked repeatedly to be the ground truth. Adam: this is the same failure as his attempts 6+ months earlier. Lessons 7–9 in §3. Claude's later correction from the reference: Hemistitch case is near-square, big corner radii (~¼ of side), very subtle sagitta on all four sides, lug tabs projecting straight up/down from top and bottom edges (not 45° corners).
- **Repo and hosting set up:** `adamontherocks/bspk-studio` (public; Pages needs public on a free plan), Pages deploys `/sim` through a GitHub Actions workflow. Commit cadence, all three tiers (Adam: "do a and b and c"): `[iter]` granular commits, `[checkpoint] <name>` + tag at rest points, `[session-start]`/`[session-end]` + tag at session boundaries.
- **Adam's core statement of intent** (the message that redefined the project): narrow specs for progress; watch movements are the example vehicle; ultimate goal is image/sketch → STEP together; he wants to say "use this part X", have Claude research real dimensions and build it in the sim; give a picture ("two discs like this"), rough dimensions, then Claude does the watch logic, transmissions and math to fit the package, connects parts and evaluates interference. Plus:
  > "id love to have a way to indicate areas on the model that i want or dont want. or a way to mark something with the mouse so you can 'see' where i am talking about. id love to have the same control over every part in the sim … and be able to add things like polysplines to the parts so i can physically change the parts shape myself … a part doesnt just need to fit, it needs a cool swooping curve that twists and narrows and then gets wide at the end again.... words cant do that.... i need to be able to use a polyspline to change a parts x, y, and z surfaces."
- **Seven layers** Claude proposed, which Adam said were "way more in line": primitives, scene (JSON source of truth), rendering, **marking** (click a face/edge/point and name it so both can refer to it), parameter editing, analysis (interference, transmission, clearance, sections), freeform (polyspline profiles; full 3D control later). Lock/unlock so "one brain doesn't always overrule the other."
- **Pipeline proven:** a parametric involute gear built in Fusion via the MCP bridge, exported STEP; then the same gear in **CadQuery** (pure Python) with identical bounding box; its STEP re-imported to Fusion as one clean body (627 faces).
- **Fusion removed from the generation path (AGREED):** "yeah i see no reason for fusion then. manual if i want it and in that case we just open and export … 90% of this will be 3d printed till we get it going then we add a 3axis to improve material, decrease size of parts, and improve tolerances."
- **Sim restarted from scratch:** single involute gear page with CadQuery export script; browser-computed volume matches CadQuery exactly (207.7252 mm³ for m0.5 z24; 288.7127 mm³ for m0.3 z60). Fixed a too-shallow root that would have interfered by 0.14 mm.
- **Watch train built** at Adam's request: no cannon pinion (each hand on its own arbor), barrel as the motor, faux escape wheel stepping per beat, labels, hover, explode, focus, separated parts. Tooth counts from a sourced 43 mm example (§10.2).
- **"Step 1": sizeable, movable, collaborative gears.** Adam: "the real magic comes when you let me control the parts … if i scale one, it automatically scales the others and avoids interferences … add more gears … define new functions… 'i want this wheel to turn at 1rpm, or 1rph' you can add reductions and teeth as necessary but a living machine. the input and outputs defined by me while the engineering is built by you." Split into: step 1 resize/move with a solver (built), step 2 add gears (not built), step 3 rate targets with teeth/stage synthesis (not built).

### 2026-11-05 — Locks and parts

Adam's feedback on step 1:
1. Thickness control; "future parts will need x, y, z, and scale."
2. The solver rejected his placement (stacking hour wheel, minute wheel and minute hand at 10 mm) and moved his parts. "i want the ui to let me put parts where i want them and the gear train adapt."
3. The minute wheel must be its own gear on its own driven shaft.
4. Reduction gears should adapt to the gears around them.
5. An X/Y/Z move controller; click-dragging was unreliable.

Then: "i would want control over the hand placement so maybe we need a way to lock and unlock parts as user defined vs claude adjustable … lock and unlock control for every part. user defined." Much of his mainplate clashing came from the UI difficulty of moving parts, "especially the minute hand since it was trying to do two things."

**Built and accepted ("this is pretty good… i think we can move forward with this"):** lock per gear and hand; X/Y/Z/scale/thickness per part; move arrows; minute wheel on its own arbor via a minute intermediate; solver that never moves locked parts; logged conflict reports with concrete options; merged repeat edits. Details in §5.

### 2026-11-06 — From clock to parts builder

Adam: thickness changes were buggy on gears with reductions. More importantly, many conflicts are artificial:

> "things like shaft diameter, and where the assembled shafts are presenting are creating potentially unnecessary conflicts. in a watch for instance, bridges and main plates can cantilever those parts so having a main plate suspend all the shafts is creating conflicts … the ui should really be 'parts'. i want control over the parts and their locations, then have you run conflict tests on them … if i were to manufacture these parts i would use shafts, bridges, additional plates, reductions that are attached to their relative gear, etc. how can we proceed, while also releasing these constraints, and still give you conflict resolution opportunities?"

The chat that followed produced the model in §6: a lock-driven workflow, parts-first modelling, the x-ray sketcher and cage modeller, editable sketched parts, STEP export to Fusion/Plasticity, intent notes, and a small-steps build order.

---

## 5. What exists today

### Files

- `sim/index.html` — the editable watch train (the clock beta), plus pins, part records, autosave, scene files and the report. ~2,200 lines.
- `sim/sketch.js` — the 2D sketcher (loaded by `index.html`).
- `sim/gear.html` — single involute gear page with a CadQuery export script.
- `sim/involute.js` — shared involute outline math; `gear.html`'s Python template mirrors it.
- `.github/workflows/deploy-sim.yml` — deploys `/sim` to Pages on push to `main`.
- `.venv/` — CadQuery 2.8.0 + cadquery-ocp 7.9.3.1.1 on Python 3.14.4 (ignored by git).
- Stale from the abandoned plan: `SIMULATOR_SPEC.md`, `lib/*/.gitkeep`, `projects/hemistitch/` (watch-specific placeholders). Keep or delete is Adam's call (OPEN).

### Running it

- Locally: `python3 -m http.server 8765 --bind 127.0.0.1 --directory sim`, then http://localhost:8765/. (The Claude Code browser pane uses `.claude/launch.json` in the AXIS worktree, config name `bspk-studio-sim`.)
- Public: https://adamontherocks.github.io/bspk-studio/ shows whatever is on `main` (the watch train since commit `cc6b5bd`, 2026-11-06).

### What the watch train does (as of 2026-11-05/06)

- **Train:** barrel (motor) → center (1 rev/h) → third → fourth (seconds, 1 rev/min) → faux escape wheel (18,000 vph, steps per beat). Minutes on their own **minute wheel** driven from the center arbor through a **minute intermediate** (40→20, then 40→80 = 1:1, clockwise). Hours from the center arbor through the hour intermediate (12→48, 14→42 = 12:1). No cannon pinion.
- **Locks:** a lock button on every gear and hand. Default locked: barrel teeth, minute wheel, fourth wheel, escape wheel, hour wheel, all three hands. Every reduction gear starts unlocked. Lock icons on labels and in the parts list.
- **Controls per part:** X, Y (arbor), Z (height), scale (pitch Ø; length for hands), thickness. The Z arrow moves the gear you clicked; click a gear card to switch.
- **Move arrows:** red X, green Y, blue Z on the selected part; dragging moves along that axis only. (A library bug that made parts jump when an arrow was pressed without hovering first is fixed.)
- **Keeping it meshed:** a mesh's size is fixed if either gear is locked or you're resizing it; then its two shafts sit exactly one centre distance apart. Unlocked meshes take their size from the spacing. Tooth counts never change, so every speed stays exact.
- **Auto-adjust (toggle):** on release, searches unlocked parts (swing around a locked partner, slide, raise/lower a mesh) in rounds for the smallest change that clears clashes, touching as few parts as possible. It only keeps a result that fully clears at least one clash and starts none.
- **Conflict reports:** when it can't clear something, the log says what's blocking and gives concrete options, e.g. "raise Minute hand to 10.65 mm, shorten it to 8.75 mm or unlock it."
- **Log and undo:** every change and automatic fix logged; clashes that already existed aren't repeated; quick repeats of the same edit merge into one undo step; tiny side effects counted, not listed.
- **Also:** motion with speed and beat stepping, labels, hover, explode, focus by transmission, dial-side/back/side views, print scale, minimum gap in real mm, movement Ø.

### The record (added 2026-11-06)

- **Pins:** "Drop pins", then click any part to drop a numbered pin (P1, P2…) on that spot, each with a note. Pins live in their part's own frame, so they move with it; labels in the view, a list in the panel.
- **Names and notes per part:** a Name field and a "Notes · why it is the way it is" field in the Selected panel (design intent). Names show on labels, the parts list and the panel.
- **Save this part / Show part record:** one part as a JSON record (teeth, module, sizes, heights, locks, what it meshes with, its pins and notes).
- **Autosave:** every change saves in the browser; a reload picks up where you left off. **Save scene / Load scene** write and read a file (state, every part's record, the change log). Loading accepts only what it recognises, so an older or partial file can't half-build the sim.
- **Report for Claude:** a text summary (rates, locks, clashes, pins, names and notes, sketches, recent changes) to paste into a chat. Claude can also read it from the sim directly.
- **Reset train** resets the mechanism but keeps pins, notes and sketches.
- Clicking the 3D view ends typing in the panel, so a half-typed note or value is saved first.

### The 2D sketcher (added 2026-11-06, first feel version)

- **Start sketching** (Sketch section). Parts go x-ray (adjustable), a see-through drawing plane appears: Top (XY), Front (XZ) or Side (YZ), or "Match my view", at any position. "Look straight at the plane" squares the camera to it and orbits around it.
- **What the plane cuts is shown on it:** parts shaded red with crisp outlines, hand sweeps amber dashed, shafts blue (dots snap to shaft centres on the top plane), plate and movement edge grey. Optional cut-away hides everything between you and the plane.
- **Dots:** click the plane to add; filled = sharp corner, double-click = hollow/smooth (curve through it). Drag a dot to move it; click a line to insert a dot; drag a line to move the whole drawing; click the first dot (or Enter) to close; Delete removes the selected dot; type exact coordinates for the selected dot. Snap to a 0.05/0.1/0.5/1 mm grid or off. A dashed rubber band shows the next segment while drawing.
- Sketches are part of the scene: they autosave, save to files, undo, and go in the report. Quick edits to one sketch merge into one log line listing every action.
- Not yet: extruding to a part, more than one plane per sketch, moving the plane by dragging (use the position slider).

### Known bugs and limits

- **Thickness revert (unreproduced):** in Adam's 2026-11-06 session some thickness changes were logged but reverted (center pinion, intermediate wheel, third pinion). Not reproduced on a clean layout; Adam's layout was lost when the page was reloaded to test.
- **Pinion below the plate:** a thick pinion on a thin mating wheel is centred on the wheel and sinks below z=0 with no warning (2 mm center pinion → z −0.5).
- **False conflicts by design (the §6.3 problem):** full-height shafts from the mainplate, one plate, shaft top tied to gear thickness, pinion height tied to its mate.
- **Edge case behaviour:** some layouts are genuinely infeasible with a given lock set (e.g. an 18 mm center wheel with the hour wheel locked). The sim says so; unlocking the right part fixes it.
- No add/remove parts, no rate targets, no train export, no extruding sketches into parts yet.

---

## 6. The product model going forward

### 6.1 Roles: who decides what

- **Locks are the whole permission system (AGREED).** Locked = the designer's; auto-adjust never moves, resizes or re-heights it. Unlocked = the engineer may adjust it. The designer can always edit anything, locked or not.
- Adam's flow: "the wheel is the part, i unlock it, i work on it, i lock it where and how i want it, then have something like 'evaluate and discuss conflicts' or 'auto correct everything else'."
- "i determine whats locked and anything not locked is essentially on auto."
- Physical consequences of the designer's own edit still apply and are reported. Meshing gears must share a tooth size, so resizing a gear resizes its mate even if locked. Moving a locked part brings a locked part meshed directly with it. An unlocked part being dragged can only swing around a locked part it meshes with. (Built.)

### 6.2 Interaction workflow (PROPOSED, Adam: "i like the idea of multiple options")

- **Design freely.** Nothing moves except what you touch. Clashes show live in red, quietly.
- **"Unlocked parts follow live" toggle.**
  - On: unlocked parts adapt *while* you drag, so you can throw a part around and watch the rest respond. Technical note: the full search takes 50–200 ms, so during the drag unlocked parts make small continuous adjustments from where they are (no jumping between solutions), and the full search runs on release.
  - Off: self-diagnose mode. "select the part move it, see the active interference, leave that part, select the interfering part, move it, select the next interference, move it… so im moving parts around as i self diagnose interferences."
- **Clickable clash list.** Click a clash to select the other part and frame it; a "next interference" button walks through them.
- **Report / Evaluate.** On demand, after locking things in: each conflict, why it happens, and options with what each costs. Engineering questions surface here, not as up-front forms ("hey adam, is this going to fabrication? were you gonna use fixed axis' or bearings…").
- **Auto-correct with preview.** Hand the engineer the pencil: proposed changes shown ghosted over the design; accept or reject.
- **"Claude, intervene" button** for when you can't get away from conflicts ("a claude suggest an alternative here sort of interference report, or … just text with you about a solution").
  - Now: it means talking to Claude in chat. In the Claude Code desktop app Claude can open, screenshot and read the sim's live state through the browser pane, so the visual loop closes without Adam taking screenshots.
  - Later (OPEN): the sim calls the Claude API directly from an "Evaluate with Claude" button. Needs API keys and has a cost.
- Honesty about the two engineers: the sim's solver is rules (fast, exact geometry); judgment, trade-offs and design conversation need Claude.

### 6.3 Parts model: build it the way it would be made (PROPOSED)

Today every shaft runs from the mainplate up past its top gear, there's a single mainplate, shaft height follows gear thickness, and a pinion is pinned to its mating wheel's height instead of fused to its own wheel. Those are simplifications, and they cause false conflicts. Replace them with real parts:

| Part | What it has |
|---|---|
| Gear (wheel or pinion) | teeth, module/size, thickness, bore, crossing/spoke design (sketchable) |
| Compound | wheel + pinion fused as one printed/machined part ("reductions attached to their relative gear") |
| Shaft / arbor / pin | diameter, bottom height, top height, turning or fixed; a gear is fixed to it or spins on it |
| Plate | outline at a height (the mainplate is just one plate) |
| Bridge | outline at a height, standing on pillars; can cantilever |
| Pillar / standoff | joins plates and bridges |
| Anchor / bearing seat | where a shaft end is held: jewel, bushing, bearing, press fit |
| Hand | length, height, thickness, shape |
| Motor / input | real motor footprint (e.g. the N20 with its mounting plate) |
| Sketched part | anything drawn in the sketcher (§6.5): bridges, levers, adaptors, connectors, supports, "any intermediary space-filling part" |

**Attachments:** gear fixed to / free on a shaft; gear meshes with gear; shaft end held by plate or bridge; bridge held by pillars or fasteners.

**The clock becomes one preset assembly** built from these parts.

### 6.4 Conflict and validation model

- Test only real bodies: a shaft only between its ends, a bridge only at its height and inside its outline, turning parts as the circle they sweep.
- New checks: every shaft held at both ends or flagged as cantilevered; every gear actually on a shaft; meshing (module and centre distance); speeds and directions; minimum gap (real mm, set for the process); printability (wall thickness, bore clearance); later, machinability ("can this be milled 3-axis from the top, or does it have undercuts?").
- **Boundary to be honest about:** the automatic checks are geometry. Structural questions (will a swoopy cantilevered bridge flex, will a printed tooth strip) get rough estimates and flags at most, plus Claude reasoning through them; real numbers come from Fusion simulation or a test print.
- **Geometry model:** 2.5D (everything a disc or outline around Z, with a height band) is exact and fast while every shaft is parallel. Angled parts (bevel and crown wheels) and fully 3D sketched parts need mesh-to-mesh collision (e.g. a BVH library in the browser); turning parts with odd shapes are the hard case.

### 6.5 The x-ray sketcher and cage modeller (PROPOSED)

**Adam's picture of it (2026-11-06):**

> "a simple orbit of the current project model with zoom in and out. lets say i find myself in the x plane looking into the void between two parts. i can click points that become polysplines... im essentially tracing the empty space between parts and have sketched the 2d map. now i can orbit to the y plane. im in a 'xray' mode and now i can extrude my sketch into the void to the next stop point. that is now a 6 sided object … if i click on one of the 6 edges i can add an edit 'ball'. one click creates a darkened ball that lets me move the ball around in the 3d space based on the plane im viewing it in. the darkened ball creates a straight line break in the polyspline line. double click on the ball and it goes hollow and becomes a curved line as a part of the polyspline. this concept is common in things like 'xtool studio' … im able to orbit the viewer and move the lines of the new object around inside the space between, around, on, under other parts.... this is how i could build a bridge that isnt stuck in a 2d, 90 degree angle shape... once the part is decided, a 'make it a part' button lets it become a 'solid'. and now we can assign it the same features the other parts get."

Earlier he described the same direction: an x-ray sketch pad as "an adjustable semi transparent screen over the model so i could sketch on the model, and move the polyspline drawing around to match shapes, and contours", with multi-side views, "orbit a sketch pad into the 3d model and move all (6) sides of a part by polyspline control… live control of every surface inside a 3d model."

**How it works (Claude's read, which Adam confirmed by building on it):**

1. **Sketch in the void.** Pick a view plane while orbiting the live mechanism. Other parts go see-through (x-ray). Shaft centres become snap points; turning parts show as hatched keep-out circles so you see where material can't go. Click points to trace an outline. Points snap to neighbouring parts offset by the minimum gap.
2. **Extrude** to a depth, or **to next contact**: the sim stops the push at the first part it would hit, less the gap.
3. **Edit with balls.** Click any edge to add a ball. Filled = sharp corner with straight segments; double-click to hollow = smooth curve point. Drag a ball and it moves in the plane you're viewing from; orbit plus drag gives full 3D control.
4. **Faces follow edges.** The block is a cage of edges; each side face is bounded by four edges and fills in as a smooth surface between them (Coons patches; OpenCASCADE has this built in for export).
5. **"Make it a part"** turns it into a solid with locks, X/Y/Z, conflict checks and export.
6. **It stays editable (AGREED).** "letting it revert back to an editable thing is delicious. the whole point of this ui is design." The balls are the source of truth; the solid is rebuilt from them whenever one moves, even while the part sits in the mechanism.

**Known hard parts:** validity (dragging a ball too far can fold the shape over itself, so a check must say where); topology is fixed (balls can't punch holes or branch, so holes, bearing seats and screw points are features added after "make it a part", snapped to shafts, and a Y-shaped bridge is two shapes joined); moving end faces off-plane is harder than bending long edges; the browser mesh preview and the CAD-kernel export must agree (same volume-match check used for gears).

**Capability tiers, near to far:**
1. One sketch plus a thickness: bridges, plates, levers, wheel spoke designs. Easy.
2. Two or three sketches that intersect (top, front, side outlines carving a block). Covers most real parts; matches how a 3-axis CNC part is planned. Moderate.
3. Lofts: a different outline at each end, blended. Tapers, organic transitions. Moderate–hard.
4. Free push/pull of any surface anywhere: true freeform (Rhino/Plasticity territory). Hard; no promise.

Adam's cage idea sits between tiers 2 and 4 and is reachable in stages (§7).

**Prior art, honestly:** sketching on faces exists (Plasticity, Shapr3D); xTool Studio uses the sharp/smooth node idea in 2D. What's novel is doing it *inside a running mechanism*, x-raying the live layout with an engineer checking fit, function and machinability as you draw.

**UI placement (PROPOSED):** a mode in the same scene, not a separate app, so the mechanism is always the context. Same camera, different tools.

### 6.6 Design intent

Like `[INTENT]` tags in the AXIS repo's `PARAMETERS.md`: a part can carry its "why" ("this wall dips because the dial reads through it"). Evaluate treats intent as the thing to protect; compromises change something else (thickness, a support underneath, the attachment point). Rebuttals come back as specifics ("the dip leaves 0.4 mm of wall; 3-axis needs 1.2; options: …"), not a vague no. (PROPOSED)

### 6.7 Export and the handoff

- **STEP as true curved B-rep** (not a triangle mesh) via CadQuery/OpenCASCADE, so Fusion and Plasticity can fillet, shell, cut and prep it. **STL** for printing. Proven for gears.
- **One-way handoff (AGREED in discussion):** once in Fusion, Fusion edits it; those edits don't flow back into the balls. The habit: iterate here until the shape is right, then export. Studio = concept, fit, editable, fast. Fusion/Plasticity = detail, tolerances, toolpaths, material.
- Adam: "if we can export these parts as files i can upload to fusion or plasticity and then further modify them or prep for manufacturing process and material, then we just gave me one of the most useful tools ive ever had."
- Print clearances (bore, gap) applied at export per process.

### 6.8 Manufacturing context

- 90% 3D printed first (desktop scale, print scale multiplier in the sim).
- Then 3-axis CNC (Makera Z1, xHorse WM-100) for functional parts; "for now id expect to be working on the 3 axis cnc for a lot of the functional parts."
- Later 5-axis milling and metal printing for "bridges, connectors, levers, adaptors, anchors, supports, any intermediary space filling part."
- The minimum gap and future per-method rules (min wall, min internal radius = cutter, overhangs) are real-mm settings independent of print scale.

### 6.9 Gear and kinematics engine

Built: involute gears, rates and directions from tooth counts, tooth phasing so meshes interleave, involute interference warnings.

Planned, from Adam's step-1 request:
- **Add gears** (now part of the parts library step).
- **Rate targets:** "i want this wheel to turn at 1rpm, or 1rph"; the engineer chooses teeth and adds reduction stages.
- **Tooth form:** watch pinions of 8–14 leaves are below the ~17-tooth involute minimum, so every mesh in the clock shows 0.016–0.077 mm interference. Options: cycloidal teeth (what watch trains use), profile-shifted pinions, or more leaves. (OPEN)

### 6.10 Marking and pointing

Adam asked for a way to mark areas on the model with the mouse, "so you can 'see' where i am talking about", and to indicate areas he wants or doesn't want. Proposed shape: click a face, edge or point and name it; marks persist in the scene so both sides can say "move P1 up 2 mm". (BUILT 2026-11-06 as numbered pins with notes, §5. Marking faces or edges, and "want / don't want" areas, are not built.)

### 6.11 Reference images

Pin an image to a plane as a backdrop to trace and check proportions against (in the sketcher this pairs naturally with x-ray). Reference-first rule applies (§3.8). (PROPOSED)

### 6.12 State and history

- Scene state in plain JSON, file-based, versioned in the repo; save/load; named snapshots; full undo/redo (AGREED 2026-11-03; undo/redo, autosave and save/load scene files built 2026-11-06; named snapshots not yet).
- Change log of every user and automatic change (built).

### 6.13 Backlog from the 2026-11-03 capability list (still wanted)

Section views, measurement, dimension overlays, groups, colour by function, materials and manufacturing methods per part with constraint callouts, mass and cost (later), articulation (e.g. lug swing with collision at every angle, an articulation sweep), screenshot export, notes on parts, SVG import.

---

## 7. Build order

Small steps, each usable on its own, each discussed before it's built. The clock stays the test bed.

On 2026-11-06 Adam chose to do the record and the 2D sketcher first, to get the sim usable and to feel the sketcher before the rest: "start with just the 2d sketcher so i can get the feel for it on the orbit, how the dots work, moving lines around, the xray parts... then we add all the fancy 3d parts." He also declined a print-calibration step for now: parts will go through Plasticity or Fusion before any production testing.

| # | Step | Status |
|---|---|---|
| A | **The record:** pins with notes, part names and intent notes, save a part, autosave, scene files, report for Claude | BUILT 2026-11-06 |
| B | **2D sketcher, feel version:** x-ray plane on any axis, cut outlines, sharp/smooth dots, move/insert/close, orbit around it | BUILT 2026-11-06 |
| 0 | Fix the thickness bugs (revert, pinion below plate) | PROPOSED |
| 1 | **Lock-driven workflow:** "unlocked parts follow live" toggle, clickable clash list + next-interference, Report/Evaluate, auto-correct with ghosted preview, "Claude, intervene" (= chat for now) | PROPOSED |
| 2 | **Shafts as parts:** diameter, real ends, turning/fixed; wheel + pinion as one compound part; conflicts only where shafts really are | PROPOSED |
| 3 | **Plates and bridges as parts:** any height, editable outline, pillars; shaft ends must land in one; unsupported/cantilevered shafts flagged | PROPOSED |
| 4 | **Engineer proposes supports:** shaft lengths, which plate/bridge holds each end, bridge outlines that avoid moving parts; designer edits or locks them | PROPOSED |
| 5 | **X-ray sketch plane** | done as part of B |
| 6 | **Sketch → part:** extrude a sketch by depth or to next contact, "make it a part", stays editable; holes snap to shafts | PROPOSED, the natural next sketcher step |
| 7 | **Shape editing:** front and back outlines independently (tapers/lofts); then balls on the long edges (curved faces); validity check | PROPOSED |
| 8 | **Parts library:** add/remove/duplicate parts; the clock becomes a preset (absorbs "add gears") | PROPOSED |
| 9 | **Rate targets:** "this turns at 1 rph" → teeth and stages chosen by the engineer | PROPOSED (from 2026-11-04) |
| 10 | **Export:** each part to STEP/STL with print clearances; preview/export volume check | PROPOSED |
| later | Intent notes in Evaluate; "Evaluate with Claude" API button; mesh collision for 3D parts; machinability checks; reference images; materials/methods; articulation; sections; measurement; tooth form | backlog |

---

## 8. Open questions

1. **Shafts:** for the printed beta, bought steel rod (fixed or turning) with printed gears, or printed shafts? Bearings, bushings, jewels or plain holes? Adam's direction: these belong in the engineer's evaluation conversation, asked when relevant.
2. **Evaluate format:** a written report inside the sim, a conversation starter for chat, or both. Adam leaned toward both: a report, plus "claude intervene" / text with Claude.
3. **Claude API in the sim:** whether and when to add an "Evaluate with Claude" button (keys, cost).
4. **Sketcher sides:** confirmed multi-side and orbit-based; how far toward free push/pull (tier 4) to go is open.
5. **Tooth form:** cycloidal teeth, profile shift, or more pinion leaves.
6. **Old scaffolding:** delete or restructure `lib/` folders, `projects/hemistitch/`, `SIMULATOR_SPEC.md`.
7. **Commits:** resume the three-tier cadence now? Pushing redeploys the public Pages site.
8. **Reference images:** the Hemistitch photos/renders shared in chat live only in a session scratchpad. Copy into the repo (it's public) or keep elsewhere?
9. **Hemistitch demonstrator anchors** (on hold while the tool is built): case envelope at desktop scale, disc diameter, lug articulation mechanism (single pin, paired shoulder screws, pin + bushing + detent, or Adam's sketch), battery form factor (18650, LiPo pouch, coin cell), motor coupling (D-bore press fit vs round bore + setscrew), crown function.
10. **Default minute wheel position** in the clock preset (currently right of centre with a 9 mm hand; Adam will place it).

---

## 9. Lessons paid for

- **Bulldozing a question** (Gear Composer, 2026-11-03): a "can you" became a shipped artifact. → §3.2.
- **Never looked at the reference** (cushion case, 2026-11-04): built from a word, called a tonneau a cushion, "validated" by reading own code. → §3.7–3.9.
- **Repo-and-pipeline motion instead of listening** (2026-11-04): repo, Pages, commit cadence and watch-named folders, while the real question ("is this what you were hoping for?") went unasked. → §3.1, §3.10.
- **Prose descriptions as validation:** rejected outright. Visual compare loops only.
- **Solver protected only the last touch** (step 1): it moved parts Adam had placed earlier, and swung/lifted before resizing. → locks.
- **Wrong engineering call caught in testing:** driving the minute wheel off the third arbor tied it to the going train; switched to a minute intermediate off the center arbor.
- **Half-fixes:** auto-adjust once kept rearrangements that created new clashes. → only keep results that fully clear something and start nothing.
- **Real-mouse testing finds real bugs:** the move-arrow jump only showed up with a real mouse press.
- **Save the user's state before reloading:** reloading the sim to reproduce a bug wiped Adam's layout (2026-11-06).
- **Log flooding:** 1,153 of 1,328 log lines once were the same repeated warnings. → report standing clashes once.

---

## 10. Reference data

### 10.1 Gear math used in the sim

- Pitch radius rp = m·z/2; base rb = rp·cos α; tip ra = rp + m; root rf = rp − 1.25m; α = 20°.
- Involute flank at parameter t: radius rb·√(1+t²), angle −half + t − atan t, with half = π/(2z) + inv α. If rf < rb, a radial foot from rf; valley arc at rf.
- Centre distance = m·(z1 + z2)/2. Driven speed ω₂ = −ω₁·z₁/z₂.
- Tooth phase for meshing: ψ₂ = θ + π − π/z₂ + (θ − ψ₁)·z₁/z₂.
- Involute interference if ra > √(rb² + (a·sin α)²) for the partner's centre distance a. Undercut threshold z_min = 2/sin²α ≈ 17 at 20°.
- Collision model (2.5D): every element a disc/cylinder about Z; separation = max(side gap, vertical gap); clash if under the minimum gap (real mm ÷ print scale); envelope check against movement Ø.

### 10.2 The clock preset (as built 2026-11-05)

Going train from the 43 mm (19‴) example in [Chapter VI: The Train](https://abbeyclock.com/gbk/gbk6.html): barrel 90 → center pinion 12; center wheel 80 → third pinion 10; third wheel 75 → fourth pinion 10; fourth wheel 75 → escape pinion 8; escape wheel 16. → 18,000 vph (5 beats/s), barrel 1 rev / 7.5 h.

| Mesh | Gears | Module | Height (mm) |
|---|---|---|---|
| s_barrel | barrel teeth 90 / center pinion 12 | 0.20 | 0.30 |
| s_center | center wheel 80 / third pinion 10 | 0.15 | 3.00 |
| s_third | third wheel 75 / fourth pinion 10 | 0.15 | 3.70 |
| s_fourth | fourth wheel 75 / escape pinion 8 | 0.15 | 4.40 |
| s_mdrive | minute-drive wheel 40 / minute intermediate pinion 20 | 0.22 | 4.85 |
| s_minute | minute intermediate wheel 40 / minute wheel 80 | 0.15 | 5.35 |
| s_hour1 | hour-drive pinion 12 / intermediate wheel 48 | 0.25 | 5.90 |
| s_hour2 | intermediate pinion 14 / hour wheel 42 | 0.25 | 6.60 |
| solo | escape wheel 16 | 0.35 | 5.10 |

Rates: center 1 h CW; barrel 7.5 h CCW; third 7.5 min CCW; fourth 60 s CW; escape 6 s CCW; minute intermediate 30 min CCW; minute wheel 1 h CW; hour intermediate 4 h CCW; hour wheel 12 h CW.
Hands: hour 5 mm @ 7.6; seconds 4.5 mm @ 7.6; minute 9 mm @ 8.0. Movement Ø 43 mm; minimum gap 0.05 mm.

### 10.3 Proven export numbers

- Gear m0.5, z24, 3 mm bore, 2 mm thick: CadQuery bbox 12.9995 × 12.9995 × 2.0000 mm; Fusion 12.999 × 12.999 × 2.000; Fusion re-import of the CadQuery STEP: 1 body, 627 faces.
- Browser vs CadQuery volume: 207.7252 mm³ (m0.5 z24), 288.7127 mm³ (m0.3 z60), exact match.
- True bounding box needs `BRepBndLib.AddOptimal_s(shape, box, False, False)`; the default box is tolerance-enlarged.

### 10.4 Hemistitch (ChatGPT artifacts, wrist scale)

- **Compact Candidate C1:** 43 × 30 mm envelope, Ø20 hour and minute discs. Hours R12 → A36 (3:1) → A12/B24 (1:2) → B20/HL40 (1:2) = 1:12. Minutes R40 → M20 → MR40 = 1:1. Rides on an NH35 base.
- **Motion Works Study 029:** 37 × 37 mm, three transmissions (seconds 100:173:100 idler-coupled, minutes 15→90→15→150 = 1:60, hours 12→48→12→36 = 1:12), modules 0.072–0.1875, Z 6.1–11.2 mm, bridges 5 mm wide × 2 mm thick.
- **Case read from Adam's reference (top-down):** near-square body, big corner radii (~¼ side), barely-there sagitta on all four sides, four lug tabs projecting straight up and down from the top and bottom edges, separate bezel step, crown at 3, four caseback screws, exhibition back with 4-spoke balance.

### 10.5 Motor and electronics "bible" (Hemistitch demonstrator, ordered 2026-11-03)

- HiLetgo GA12-N20 metal gearbox, **3 V, 15 RPM output** (≈1000:1), 3 mm D-shaft × 9 mm, body 24 × 12 × 10 mm, comes plate-mounted (2-pack).
- DRV8833 dual H-bridge; ESP32-C from Adam's bin; RTC modules on hand; NTP/RTC timing; PWM speed trim; continuous DC drive, not a stepper (keep "see the gear train do the reduction").
- Notes: PWM burst for cold start; a single Li cell (3.0–4.2 V) sits inside the motor range; output drifts with cell voltage and firmware trims it. Proof-of-concept accuracy, not GMT precision.

### 10.6 AXIS v1 (case reference)

Repo `Next-Step-Inc/bspk-axis-v1`: 50 × 29 mm tonneau case, 16.72 mm tall, two NH05/NH35 movements each driving a 16 mm × 0.20 mm carbon-fibre disc, 24 mm strap width. Scale ~4× for an ~8" desktop piece. Its `PARAMETERS.md` `[INTENT]` tags inspired §6.6.

### 10.7 Toolchain and links

- Three.js r128 (cdnjs) + OrbitControls and TransformControls from `three@0.128.0/examples/js`.
- CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1, Python 3.14.4, venv at `.venv`.
- Repo: https://github.com/adamontherocks/bspk-studio · Pages: https://adamontherocks.github.io/bspk-studio/
- Artifacts: Gear Composer v0.1 https://claude.ai/artifact/L3UrsmLntHYJRhg7twhLCb · BSPK Studio v0.1 (cushion, superseded) https://claude.ai/artifact/MghKPXzLwiGdi7rEAjep1b
- Hardware: 3D printer (FDM), Makera Z1, xHorse WM-100 (incoming), XSnow metal printer (watching).

---

## 11. Glossary

- **Arbor / shaft** — the axle a gear turns on or with. **Pinion** — a small gear (few teeth, "leaves"). **Wheel** — a large gear.
- **Module (m)** — tooth size; meshing gears must share it. **Mesh / stage** — one pair of meshing gears. **Compound** — wheel and pinion fused on one arbor.
- **Plate / bridge / pillar** — the structure holding shaft ends; bridges can cantilever.
- **Lock** — designer-owned; auto-adjust never touches it. **Unlocked** — engineer may adjust.
- **Live-follow** — unlocked parts adapt while you drag. **Report / Evaluate** — conflict report with options. **Auto-correct** — engineer applies fixes, previewed. **Intervene** — ask Claude.
- **X-ray** — see-through mode over the live mechanism while sketching. **Keep-out zone** — area swept by a moving part. **Snap** — points lock to shaft centres and part edges.
- **Ball** — an edit point on a sketched edge: filled = sharp, hollow = smooth. **Cage** — the edges that define a sketched part; surfaces fill between them.
- **Extrude to next contact** — push a sketch until it would hit a part, less the minimum gap.
- **Minimum gap** — clearance in real mm between non-meshing parts, sideways and vertical; independent of print scale.
- **Print scale** — multiplier from design size to printed size for the desktop beta.
