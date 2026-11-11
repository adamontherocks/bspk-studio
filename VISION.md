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

### 2026-11-06/07 — First use of the record and sketcher; quick edit

Adam tried the record and the 2D sketcher on a Hemistitch-style layout: hour and minute wheels enlarged to 18 mm and lifted to 13 mm, off the plate, to isolate them. He liked grid snap and inserting dots anywhere on the polyspline ("epic"). His log showed every remaining clash came from arbors modelled down to the mainplate (the §6.3 problem, now with a real example), and that his 21.46 mm center wheel had been shrunk back to 12.05 mm by later edits because it was unlocked.

He asked for two speed-ups, both built 2026-11-07 (§5):

> "on the label displayed in the orbit viewer, we need to have the ability to lock and unlock there … to move around and then lock again."
>
> "when you select the part to edit, maybe have the adjustments pop up beside it in a small window … a quick edit box when you unlock it and a manual close if you wanna leave it unlocked. or it closes when you lock it. beats having to go over to the right toolbar and scroll."

That evening the Mac's battery ran out mid-session (it hibernated, nothing on disk lost). The sim's autosave restored the layout exactly; only the in-page log and undo history were gone. The full log was recovered from the chat transcript into `scenes/bspk-scene-2026-11-06_1604-recovered.json`.

### 2026-11-07 — Freedom first: axes, not shafts

Claude proposed shafts with real ends as the next step. Adam turned it around:

> "how do we just ignore shafts until i decide i want shaft? techincally all the gears will require them, but i dont know if i want the shaft as a pinion, or the gear on a bearing. i dont know if i want bearings, or jewels. i dont know if i want a bridge or a plate.... how do we remove the shafts and simply add what i need when i decide i need that."
>
> "as the designer and goal of this program, i want freedom to move, add, subtract, create, build any part or any thing i dream up necessary. so no interference unless a part collides is the real start … let me do what i think needs to be done, then i can ask you for guidance or interference resolutions."

Agreed as the rule for the whole tool (§6.0). First step built the same day: arbors became bare **axes** (§5). He also wants a parts library eventually, including saving his own parts to it.

### 2026-11-07 — A colour code for red-green colour blindness

Adam asked why the hour wheel and hour intermediate were clashing. They weren't: the Hours group was pink, and pink reads as red to him.

> "i have a red green color deficiency so the pink shows up as red for me … what about everything is white. selected parts are blue. and interferences are red?"

Built the same day (§5, *Colour code*). Rule from here on: nothing in the tool signals by red vs green (or pink, amber vs red) alone; every colour that means something also has a shape, symbol or word. Cost: transmissions can no longer be told apart by colour; labels name every part and Focus still isolates one transmission.

### 2026-11-07 — Every part is a shape; boundaries are opt-in

The minute wheel was flagged for hanging past the movement edge. Adam: the mainplate "doesnt have a part nature… if i want to bore a hole through it or edit its edge profile i would need some polysplines … i just want total freedom and control to quickly and easily manipulate shapes." Claude proposed one model for every non-gear part (§7 step 3): an outline of sharp/smooth dots, pushed to a thickness, with cuts and edge rounds, all editable; gears share it, with the teeth generated and everything inside them the designer's.

On the edge flag: "technically in this situation i should be checking myself so a perimeter flag on floating parts isnt a normal flag … i would need to assign something as a boundary for it to need to normally flag." Built the same day: the plate edge no longer flags or pulls parts in (§5); a part becomes a boundary only when Adam marks it (§6.0 rule 5). The minimum gap stays a clash. He then floated a project setup box (§8 Q13).

### 2026-11-07 — Sketch to part, slice 1

Adam: "the 3d extrude of the sketch to a part to test the experience with the polyspline edges and how that interfaces and interacts in the orbit view." Two decisions with it: "the hands are like any other part, manual control" (§8 Q11 answered: hands stay put, they don't ride with their wheels), and "any part we import or co-design at project start needs to be editable. so something like the mainplate needs that ability for sure. hands, etc." (§6.0 rule 6). Collisions for drawn parts wait until the design goals are clear ("we can work on collision requirements after we figure the design goals out"). Built the same day (§5, *Drawn parts*).

### 2026-11-07 — The back outline, and what this tool is for

Adam asked whether the new edges an extrusion makes could carry their own dots. Claude split it: the back outline (cheap, a loft) first, the edges running through the thickness (curved walls, Coons patches, medium) second. Built the back outline the same day (§5).

Adam on why this matters, worth keeping as the product's reason to exist:

> "so many projects ive done with you have suffered from not being able to communicate "parts" and youre always suggesting i go produce it in fusion, but 1 i dont have the skills to do a lot of the stuff i want to do, and 2, the parts are always design influenced, meaning i need to be able to manually adjust it around to make it do something complex, or most of all very difficult to use words to explain, and reference images just dont get you to "see" it. so this should be a useful translator. i could see me asking you to build a bridge have it connect to the axis of this gear and attach over here to a perimeter wall. maybe even give you a polyspline or a sketch in the ui as a guide. you make it a "part" and then i can go in and manually adjust it to look good, or do what i wanted it to do, and then you get to fact check it against function."

The loop: Adam asks (words plus a guide sketch or polyspline) → Claude builds the part in the scene → Adam shapes it by hand → Claude checks it against function. Claude can already drive the sim from a session (`window.studio`), so "Claude makes it a part" is reachable once parts can be requested by description.

### 2026-11-09 — A lost scene, a disk copy, and the joining edges

After a weekend away, the Claude app had restarted and the sim's scene (a demo part) was gone: the browser pane's storage doesn't survive an app restart, and "Save scene" can't download from the pane. No copy existed anywhere on disk. Adam: "no stakes … if there is a safety catch for that, then that was a good catch in beta." Built the same day: `serve.py` keeps the scene on disk with timed backups (§5 *Running it*). Then the joining-edge dots Adam had been reaching for ("i went looking for the side edge dots again"), with smooth walls and a flat-wall snap (§5 *Drawn parts*). He set aside lines between any two dots for now.

### 2026-11-07 — Snapping in true 3D

After shaping Part 1 by hand into a near-symmetric tapered part, Adam asked for alignment help, then sharpened it: "when im looking at a corner in 3d from across the plane and some random orbited angle, its hard to know ive created a 90 degree angle … i wont be able to know im at the same length when dragging a dot across a invisible grid at random viewing angles." He parked "Claude, make it perfectly symmetrical and fit it to the blank space" (§7 row F) in favour of this. Built the same day (§5, *Snapping*). His reaction:

> "this is the translator i have needed with you for so long.... no more "claude it needs 'more swooping'" just here is a 3d model that it should look like, now go see if you can make it fit there and tell me what breaks."

### 2026-11-10 — Hemistitch at prototype scale: the real project starts

Adam closed the beta ("its ok to abandone this one, it was just for beta") and started the project the tool exists for: the Hemistitch movement at desktop scale. One barrel and one escapement, a going train, and motion works turning an hour disc (left) and a minute disc (right). Claude's job: "produce the mechanical parts in a functional arrangement" in the sim, so Adam can move them and Claude can correct the engineering. Plates, bridges and supports come after, for the Makera Z1. He asked for a brief before anything is built. Decided that day (numbers in §10.8):

- **AGREED** 2.8 mm cast acrylic, 3×6×2.5 flanged bearings, 3 mm steel rod. Press fits everywhere: "id rather sand the hole a bit than fight epoxy."
- **AGREED** Machine rules come from Makera's own figures for the Z1 and its end mills. Adam will buy the cutter Claude specifies.
- **AGREED** Proportional growth: "the ratios of the discs, movement size, envelope, case is what we use to grow proportionally … equal proportions on the parts." The watch-sized package isn't the constraint.
- **AGREED** Hour disc: numbers 1–12, one fixed indicator at 3 o'clock, one number passes it each hour (one turn in 12 h).
- **AGREED** Discs are compound wheels: the 2.8 mm printed disc is fixed on top of a smaller gear that meshes with the motion works.
- **AGREED** Faux barrel and faux escapement (escape wheel, fork, balance) that take up their real space. Power enters at the barrel; later the barrel becomes a battery + ESP32-C + motor module that "acts outside like a barrel wheel." Adam asked Claude to suggest how to get the barrel's slow speed (stepper, other motor, or an internal transmission).
- **PROPOSED** Claude's train, scale, cutter and barrel drive (§10.8).
- **AGREED** (same day, after the brief) The barrel stays a faux barrel at its proportional size, with its own internal gearing standing in for the spring. The motor and electronics are a separate pod that clicks into the back of the movement and drives that gearing: "im not dead set on it all fitting inside a tiny faux barrel. a small motorozied aassembly that clicks into the back of the movemeent and engages the barrels transmission to power it is equally cool." New motor (geared stepper) to be bought and specced first.
- **AGREED** 1 mm cutter (module 1.0, 2.5× scale). Adam balked at a $93 premium bit for a machine that holds ±0.15 mm; any 1.0 mm flat end mill with enough cutting length will do.

### 2026-11-11 — The case bow deepens (design lock changed by Adam)

In the stacked-plate plan for the Slava version, the 48-tooth minute wheel's pocket (radius 25.2 around its arbor at −1.1, +12.3) reached y = 37.5, leaving 1.2 mm of acrylic under the case's top edge. The arbor can't move (it's set by its meshes with the center and hour arbors) and mirroring it below hits the bottom edge. Adam: "yeah top and bottom bow for y to compensate." **AGREED:** the top and bottom bow grows from 2.5 to **4.25 mm** at 2.5× (1.0 → 1.7 mm at watch scale), corners and flat height unchanged, for a 3 mm wall (2.98 measured on the sim's outline). The case at 2.5× is now about 125 × 72.5 mm at the flats and **81.0 at the middle**. Applied to the Hemistitch + Slava project's case outline; the older Hemistitch prototype project still has the 2.5 mm bow.

---

## 5. What exists today

### Files

- `sim/index.html` — the editable watch train (the clock beta), plus pins, part records, autosave, scene files, the report, label padlocks and the quick-edit box. ~2,400 lines.
- `scenes/` — saved scene files (currently one recovered from the 2026-11-06 session; not committed).
- `sim/sketch.js` — the 2D sketcher (loaded by `index.html`).
- `sim/gear.html` — single involute gear page with a CadQuery export script.
- `sim/involute.js` — shared involute outline math; `gear.html`'s Python template mirrors it.
- `.github/workflows/deploy-sim.yml` — deploys `/sim` to Pages on push to `main`.
- `.venv/` — CadQuery 2.8.0 + cadquery-ocp 7.9.3.1.1 on Python 3.14.4 (ignored by git).
- Stale from the abandoned plan: `SIMULATOR_SPEC.md`, `lib/*/.gitkeep`, `projects/hemistitch/` (watch-specific placeholders). Keep or delete is Adam's call (OPEN).

### Running it

- Locally: `python3 serve.py` (from the repo root), then http://localhost:8765/. It serves `sim/` and keeps a copy of the scene on disk: `scenes/autosave.json` after every change, plus a backup every 10 minutes in `scenes/autosave-backups/` (newest 30 kept; both git-ignored, the repo is public). If the browser's storage is empty or older, the sim reloads from that file. It also tells the browser not to cache, so a reload always gets new code. (The Claude Code browser pane uses `.claude/launch.json` in the AXIS worktree, config name `bspk-studio-sim`, now pointing at `serve.py`.) The old `python3 -m http.server` still works but keeps no disk copy, and the sim says so under Changes.
- Public: https://adamontherocks.github.io/bspk-studio/ shows whatever is on `main` (the watch train since commit `cc6b5bd`, 2026-11-06).

### Projects (added 2026-11-10)

- Everything specific to one machine is a **project**: its axes and gears (teeth, thickness), which gears mesh, its hands, the axis it's driven from and how fast, the speeds the checks hold it to, the beat (if any), its starting layout and locks, and the page's title, blurb, focus list and source note. It's data in `sim/index.html` (`CLOCK_PROJECT`) or in a scene file, never in the code (§3.10).
- Scene files and the autosave carry their project beside the state (file version 3). A file without one (version 2, everything before 2026-11-10) is the clock.
- Opening a scene of a different project (Load scene, the disk copy, or `studio.openScene(data)` from a script) hands it to browser storage and reloads the page, because every part on screen is built for one project. The log says so, and undo starts fresh there. A guard stops it reloading twice for the same project.
- Checked on 2026-11-10 against the code before the change: the default clock and Adam's autosave (v2 file, one drawn part) load with identical state, speeds, checks, clearances, parts list and report; a two-gear test project opens, and back again.
- **Project → Open** (2026-11-10) lists the projects that come with the sim (`sim/projects/*.json` plus the clock in the code). Opening one keeps the scene you leave: a copy per project in browser storage (opening that project again brings it back where you left it) and, under serve.py, an immediate backup (`PUT /autosave?backup=1`).
- Added for Hemistitch, available to any project: **discs** (a hand with `shape: 'disc'`: its length is the radius; numbers and ticks printed on top, placed so they reach the fixed index in order whichever way the disc turns, each upright at the index; a fixed index pointer beside the rim), **plain wheels** (`plain: true`: no teeth, just their outline; for faux parts), **profile shift** per gear (`x`, in modules), a **plate** name and role, view height, and **rules**: `minModule` (Checks warns about smaller teeth) and `fixedModule` (auto-adjust never resizes teeth; moving a part drags the parts it meshes with down the train instead).
- Not yet: starting a blank project from the page, and an internal (ring) gear for the barrel pod.
- **Holes and pockets in drawn parts** (2026-11-11): a flat drawn part (no back outline, dot depths or joining-edge dots) takes cuts and becomes a plate you can machine. A cut is a circle or a closed sketch on the same plane (a pocket), straight through or to a depth from either face, with an optional seat (counterbore) or 90° countersink. Presets: hole, 3 mm rod hole, bearing pocket for the 3×6×2.5 flanged bearing (Ø6 × 2.5 with a 7.2 × 0.6 flange seat, to check against the real bearings), clearance hole, M3 countersunk screw hole, M3 self-tapping pilot, 3 mm dowel hole, window, pocket from a sketch. A circle cut can follow an axis, so plate holes move with the arbors. The plate is built as flat slabs between cut depths (Clipper does the 2D unions and differences), which is exactly the 2.5D shape a 3-axis mill cuts; countersinks show as 4 steps and are meant to export as true cones. Edited from the part's panel (Holes and pockets) or by script: `studio.addSketch`, `studio.setPart`, `studio.addCut`, `studio.removeCut`, `studio.cuts`. Every change is logged and undoable, and cuts are saved with the scene.
- Still to come for plates: clash checks between plates and wheels (drawn parts aren't checked yet), the Z1 rules check (smallest inside corner, narrowest slot, stock per plate), dragging a cut in the view, and export.

### What the watch train does (as of 2026-11-05/06)

- **Train:** barrel (motor) → center (1 rev/h) → third → fourth (seconds, 1 rev/min) → faux escape wheel (18,000 vph, steps per beat). Minutes on their own **minute wheel** driven from the center arbor through a **minute intermediate** (40→20, then 40→80 = 1:1, clockwise). Hours from the center arbor through the hour intermediate (12→48, 14→42 = 12:1). No cannon pinion.
- **Locks:** a lock button on every gear and hand. Default locked: barrel teeth, minute wheel, fourth wheel, escape wheel, hour wheel, all three hands. Every reduction gear starts unlocked. Clickable padlocks on the labels in the view (§ Quick edit below); lock icons in the parts list.
- **Drawn parts (2026-11-07, slice 1 of sketch → part):** a closed sketch gets a **Make part** button (in the sketch list, and "Make it a part" while sketching). It becomes Part 1, 2…: the outline pushed out to a thickness (default 1 mm), growing toward + or − along the plane's normal, or both ways. The sketch stays its outline (the list shows "→ Part 1"), so the dots are the source of truth. Select the part in the normal view and its yellow dots appear on it: drag a dot, double-click for sharp ↔ smooth, click the outline to add a dot, Delete removes one (an outline keeps at least 3); the solid rebuilds as you drag. Editing its sketch in the sketch tool reshapes it too. The arrows move the whole part (along the plane the dots shift, across it the plane moves). Panel: thickness, grow side, plane position, name and notes, Remove (the sketch stays; removing the sketch removes the part). **Back outline (same day):** a drawn part is a loft from its front outline (the sketch) to its back outline. Selected, it shows both outlines and faint edges joining their dots; the bright one carries the dots. Click the faint one (or Front / Back in the panel) to edit that face instead. The back starts as a copy of the front; its first change gives it its own dots, so a drag makes a taper, flare or twist. Both outlines always have the same number of dots: adding a dot on one adds the matching dot on the other at the same spot along its edge, and deleting removes both. "Make the back match the front" undoes the loft. The arrows move both outlines together. While a part is being edited its name label lets clicks through, so it never covers a dot. **Dot movement lock (same day, after a drag flung two back dots metres away):** a dragged dot follows the cursor on its face when the face is turned toward you (within ~72° of face-on); seen nearly edge-on, it moves in a plane facing you and is dropped onto its face, so it can only slide along what you see and never flies off. A selected dot gets its own small arrows (orange X, cyan Y, white Z, with letters; only the two directions along its face) to move it along one axis; while a dot is selected the part's arrows step aside, and clicking the part away from its dots lets go of the dot. The panel shows the selected dot (which outline, sharp or smooth) with its two coordinates to type, plus sharp/smooth and delete. Clicking an outline adds the dot exactly on the line. Edge lines on drawn parts are the real edges only (both outlines, and a line at each sharp dot), not one on every facet of a twisted wall. The same arrows and safe dragging work in the sketch tool. **Dot depth (same day; Adam: "dont overlap faces and careful with geometry"):** on a part, a selected dot's arrows also include the third direction, in and out of its face, and the panel shows that third number too; a free drag still slides the dot along its face. Moving a front dot in or out moves only that dot (a back that still copied the front gets its own dots first). A front dot can't come closer than 0.05 mm to its back partner, and the thickness can't go below what that allows; the log says when it stopped ("as thin as it goes"). Faces with a dot in or out are no longer flat. On a part, the outline line is no longer a handle: a click on it adds a dot there, a drag from it orbits the view (the old "drag the line to move the whole outline", kept from the sketcher, sheared one face off the other by accident; the sketch tool still has it). Cmd+Z / Cmd+Shift+Z undo and redo when not typing in a box; quick edits to one outline within 3 s merge into one undo step. **Snapping (same day):** measured in true 3D, never on screen, so it holds from any orbit. A selected dot shows the true length of every edge touching it (including the edge through the part to its partner) and its corner angle. While dragging (by hand or by its arrows) it snaps when close: a corner at 90°, 45° or 135° (at the dot, or at a neighbour it pulls on), an edge exactly along X, Y or Z ("∥ Y"), an edge the length of any other edge ("= 1.92 mm", and the matched edge lights up too, even across the part), and the same X, Y or Z as another dot (dashed guide line, "same Z as dot 3"). Two snaps can hold at once. Snapped edges turn solid white and their tags go white (brightness and words, not colour). Tolerance: 2.5°, or 0.1 mm / 8 px at the current zoom, whichever is bigger. Hold Option to drag without snapping. A press on a dot always drags the dot; the arrows only take presses away from it. The part's hover tip stays hidden while a dot is dragged. Works in the sketch tool too. **Joining-edge dots (2026-11-09):** click one of the faint edges joining a front dot to its back dot and it becomes the live one (the panel says "Editing joining edge N"); click it to add a dot exactly on it, drag dots anywhere in 3D (a free drag moves on a plane facing you; the arrows offer all three directions), double-click for sharp ↔ smooth, Delete removes one (the edge can go back to straight). A joining-edge dot is stored relative to the straight line between its ends, so it travels with them when the outlines, thickness or part move. Each wall is now a surface stretched between its four edges (a Coons patch): a bent or curved joining edge curves the walls on both sides, and a wall whose four corners aren't in one plane is cut finely so it reads as a smooth saddle, not a crease. Adding or deleting an outline dot keeps every joining edge with its own dot. Snapping covers joining-edge dots (lengths and bends along the edge, lining up with any dot) and adds a **flat wall** snap (its four corners in one plane, for walls whose joining edges are straight). Dots on the joining edge of a front or back dot you drag ride along with it, so they aren't used as snap references for it. **Fixed the same day after Adam's first session with it ("the surfaces acted real real crazy … sides folded or warped"):** walls had been stitched by dot count, every link between dots getting an equal share of the wall, so a stray dot near one end took half a wall and steps at different depths were joined crosswise (up to 20 of 60 triangles flipped per wall). Walls are now stitched by depth: a point 70% along one joining edge meets the point 70% along the other, using each dot's real depth along its edge (so dragging a dot along the edge keeps it true), and straight links are walked at even speed. On his part that took every wall to 0 flipped. And a joining-edge dot dragged by hand now slides along the wall it borders that's turned most toward you (it had moved on a plane facing the camera and drifted off its walls), falling back to a plane facing you when both walls are edge-on. For a clean step, put its dots on the two edges at the same depth: the "same Y as …" guide does it. **Square jogs stay square (same day):** two dots on a joining edge at exactly the same depth (a jog straight out from the edge) each keep their own row in the walls, so the jog's face stays square instead of becoming a ramp. **No accidental dots (same day; Adam: "i attempted click the corner dot and it auto created a dot there … i cant see if there are two dots"):** a click within 14 px of a dot takes that dot, even if it misses its drawn disc; a click on a line never adds a dot within 14 px of an existing one (on a joining edge that includes its two corner ends, and a click there selects that corner on its face instead). To place a dot very close to another, add it further along the line and drag it over. His log showed four such accidents (outline dot 8, joining edges 2 and 7 twice) and one still hidden on a corner of joining edge 3. Front dots now sit on the front face even when the part grows both ways. White / blue / red like every part, in the parts list, saved, autosaved, undoable, in the report and part record. **Not checked for clashes yet:** its label says "not checked", and the checks list and report say so. Limits: an outline that crosses itself, or a back dragged so far the walls cross, makes a broken solid (no check yet); clicking within ~8 px of a selected part's bright outline adds a dot. In the sketch tool, a part grown both ways still draws its sketch on the sketch plane, mid-thickness.
- **The plate edge isn't a boundary (2026-11-07):** parts can hang past the mainplate without a flag, and auto-adjust no longer pulls them in. Checks shows the furthest reach and, if it's past the plate, by how much ("not flagged: the plate isn't a boundary"). Only parts within the minimum gap of each other, or overlapping, are clashes.
- **Colour code (2026-11-07, for red-green colour blindness):** every part is white, the mainplate grey. Hover tints a part pale blue; the selected part is solid blue; a part that collides is solid red (red wins over selected), and its label dot and parts-list swatch turn into a red warning triangle with "!". Nothing else in the view is red. The checks list marks each line ✓ ok, *i* note, ! warning, ✕ error. Group colours are gone (the group still shows as a chip on the selected part).
- **Axes, not shafts (2026-11-07):** each wheel and its pinions (and its hand) turn on an **axis**: a faint dashed centre line (white, or blue / red with its part), running from the lowest part on it to just past the highest. It has no size, isn't clickable and never collides. No shafts, rods or jewels are drawn or checked, and the mainplate is a plain plate. Collisions are only between parts that exist: gears, the barrel drum and hand sweeps. Shafts, studs, pinions on a shaft, jewels, bearings, plates and bridges come back as parts you add when you decide (§7). Cost: the sim no longer catches "a shaft would pass through that wheel" until you add that shaft. On Adam's lifted-wheel layout this cleared both remaining clashes (Fourth wheel × Minute wheel arbor, Minute wheel arbor × Seconds hand sweep).
- **Controls per part:** X, Y (axis), Z (height), scale (pitch Ø; length for hands), thickness. The Z arrow moves the gear you clicked; click a gear card to switch.
- **Move arrows:** orange X, light-cyan Y, white Z on the selected part, each with its letter at the tip (the library's red/green/blue replaced 2026-11-07; the small plane squares between arrows are plain white); dragging moves along that axis only. (A library bug that made parts jump when an arrow was pressed without hovering first is fixed.) A click on an arrow isn't a move: the part holds still until the pointer travels 4 px, and a drag that ends where it started (under 0.005 mm) isn't logged.
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
- **What the plane cuts is shown on it:** parts shaded white with solid outlines, hand sweeps pale grey with dashed outlines, axis centres as blue crosses on any top plane (dots snap to them), plate and movement edge dark grey. Your sketch lines and dots are yellow (were pink until 2026-11-07). Optional cut-away hides everything between you and the plane.
- **Dots:** click the plane to add; filled = sharp corner, double-click = hollow/smooth (curve through it). Drag a dot to move it; click a line to insert a dot; drag a line to move the whole drawing; click the first dot (or Enter) to close; Delete removes the selected dot; type exact coordinates for the selected dot. Snap to a 0.05/0.1/0.5/1 mm grid or off. A dashed rubber band shows the next segment while drawing.
- Sketches are part of the scene: they autosave, save to files, undo, and go in the report. Quick edits to one sketch merge into one log line listing every action.
- Not yet: extruding to a part, more than one plane per sketch, moving the plane by dragging (use the position slider).

### Quick edit (added 2026-11-07)

- **Padlock on every label** in the view (not the mainplate): amber closed = locked, open = unlocked. One click locks or unlocks the whole part; clicking the rest of the label still selects it.
- **What a padlock covers:** a wheel's own gears (a hand on its arbor has its own padlock). Unlocking remembers which gears were locked, so locking again restores exactly that set (e.g. only the Center pinion). A part that was never locked locks all its gears. If a locked hand still holds the arbor, the label, the box and the log say so.
- **Quick-edit box** beside the selected part, while it's unlocked: X and Y of the axis, then pitch Ø, height and thickness of the active gear (a switch picks the gear on multi-gear arbors; it's the same gear the Z arrow moves), or length, height and thickness for a hand. A short note says when locked neighbours limit where it can go.
- **Opens** when you unlock a part (label padlock or panel lock button) or click a part that's already unlocked. **Closes** when you lock it (the box's own Lock button or the label), on its ×, which leaves the part unlocked (clicking the part again reopens it), on Esc or clicking empty space, and while sketching or dropping pins.
- **Placement:** just right of the part's outline on screen, else just left, kept inside the view. It follows the part as you orbit and holds still while you drag the part's arrows or work a control in it, then moves beside the new outline when you let go. The right panel is unchanged and still holds names, notes and the part record.
- Known: the box can cover other parts' labels, so close it or orbit to reach a padlock underneath.

### Known bugs and limits

- **Thickness revert (unreproduced):** in Adam's 2026-11-06 session some thickness changes were logged but reverted (center pinion, intermediate wheel, third pinion). Not reproduced on a clean layout; Adam's layout was lost when the page was reloaded to test.
- **Pinion below the plate:** a thick pinion on a thin mating wheel is centred on the wheel and sinks below z=0 with no warning (2 mm center pinion → z −0.5).
- **False conflicts by design (the §6.3 problem):** the full-height shafts are gone (axes, 2026-11-07). Still simplified: one plate, and a pinion's height tied to its mate.
- **Auto-adjust runs without being asked:** on every edit it moves, resizes and re-heights unlocked parts (it shrank Adam's 21.46 mm center wheel back to 12.05 mm). That breaks the freedom-first rule (§6.0); making it something you ask for is the next step (§7 E).
- **Hands don't ride with their wheel:** raising a wheel leaves its hand at the old height (Adam's hands ended up ~5 mm below their own wheels). Whether they should follow is OPEN (§8).
- **Edge case behaviour:** some layouts are genuinely infeasible with a given lock set (e.g. an 18 mm center wheel with the hour wheel locked). The sim says so; unlocking the right part fixes it.
- No add/remove parts, no rate targets, no train export, no extruding sketches into parts yet.

---

## 6. The product model going forward

### 6.0 Freedom first (AGREED 2026-11-07, the rule over everything below)

1. **Only parts that exist collide.** Nothing is assumed: no implied shafts, jewels, bearings or supports. An axis is a centre line, not a part.
2. **The sim reports, it never forces.** The designer moves, adds, removes and builds anything; clashes show, nothing is blocked.
3. **Engineering guidance only when asked.** Supports, cantilevers, bridges, shaft choices and clash fixes come from Evaluate or from Claude on request, not as up-front warnings or automatic corrections.
4. **Supports are parts you add when you decide:** shaft, pinion on a shaft, fixed stud with the wheel on a bearing, jewel, bushing, bearing, plate, bridge. Plates and bridges are best drawn (sketch → part) rather than picked.
5. **Boundaries are opt-in (2026-11-07).** No part is a boundary until the designer marks it ("i would need to assign something as a boundary for it to need to normally flag"), or asks Claude to add one. A boundary flags anything poking past its outline. The minimum gap between parts is the designer's own setting and stays a live clash.
6. **Every part is editable (2026-11-07).** "any part we import or co-design at project start needs to be editable. so something like the mainplate needs that ability for sure. hands, etc." Shape, size and position of every part, generated or drawn, stay in the designer's hands; hands are manual like any other part.

Where §6.1–6.4 below assume the engineer acts or checks unasked (auto-adjust on every edit, "every shaft held at both ends" as a live check), §6.0 wins: those become things the designer asks for.

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

Until 2026-11-07 every shaft ran from the mainplate up past its top gear; that is gone (axes, §5). Still simplified: a single mainplate, and a pinion pinned to its mating wheel's height instead of fused to its own wheel. Replace them with real parts, each added only when the designer chooses (§6.0):

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
- New checks, run on request (Evaluate), not live (§6.0): every shaft held at both ends or flagged as cantilevered; every gear actually on a shaft; meshing (module and centre distance); speeds and directions; minimum gap (real mm, set for the process); printability (wall thickness, bore clearance); later, machinability ("can this be milled 3-axis from the top, or does it have undercuts?").
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

**Reference bank** (Adam, 2026-11-07: "a photo or reference bank could be useful for bringing in screenshots of the products, or pictures of the actual parts, or pdf of the parts dimensions"): per project, holding product screenshots, photos of real parts, datasheet PDFs and sketches. Each file can be linked to a part or a pin (a bearing's datasheet on the bearing), so a part shows where its numbers came from. Today Claude reads a PDF or screenshot given in chat and enters the sizes; the sim reading them itself needs the Claude API (Q3). Files probably stay local, since the repo is public (Q12). (PROPOSED)

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
| C | **Quick edit:** padlocks on the view labels, quick-edit box beside an unlocked part, arrow clicks and no-op moves no longer logged | BUILT 2026-11-07 |
| D | **Axes, not shafts:** arbors become dashed centre lines with no size or collisions; no rods or jewels; sketcher snaps to axis centres | BUILT 2026-11-07 |
| E | **Auto-adjust on request:** stop moving unlocked parts on every edit; a "resolve" action the designer triggers instead (folds into step 1) | PROPOSED, next |
| 0 | Fix the thickness bugs (revert, pinion below plate) | PROPOSED |
| 1 | **Lock-driven workflow:** "unlocked parts follow live" toggle, clickable clash list + next-interference, Report/Evaluate, auto-correct with ghosted preview, "Claude, intervene" (= chat for now) | PROPOSED |
| 2 | **Supports you add to an axis:** shaft (turning or fixed), pinion on a shaft, stud with the wheel on a bearing, jewel/bushing/bearing; diameter and real ends; wheel + pinion as one compound part; added from the quick-edit box when the designer decides. **Bought parts** (2026-11-07): the project lists the hardware you'll use (Adam's example: "3mm bearings and 1mm steel rods for the axis" on a Z1 / ¼" acrylic build), each a stock part with its datasheet sizes (bearing: bore × outside × width; rod: diameter, length set when placed). Placing one on an axis sizes what it touches: a rod sets the bore of each wheel on that axis, a bearing cuts its pocket in a plate, both adjusted by the chosen fit. Once placed they collide like any part. The parts list counts how many are used (a shopping list). Later: import supplier STEP models (McMaster, Misumi) for true shape and export. Watch sizes: a 1 mm rod needs a 1 mm-bore bearing (681 is 1 × 3 × 1 mm); a 3 mm bore would need a sleeve | PROPOSED |
| 3 | **Plates and bridges as parts:** any height, editable outline (drawn, via step 6), pillars; remove or replace the mainplate; unsupported/cantilevered shafts flagged on request. Model proposed 2026-11-07: every non-gear part = outline (sharp/smooth dots) + thickness + height + cuts (holes through first; pockets later, need a boolean library) + edge rounds/chamfers (a drawn edge profile later); select a part and its dots appear on it; "boundary" is a per-part checkbox, off by default. Gears share the model: teeth generated, everything inside them the designer's. Suggested order: mainplate as an editable part → holes → sketch to new part + blanks → edge rounds → save to library | PROPOSED |
| 4 | **Engineer proposes supports, when asked:** shaft lengths, which plate/bridge holds each end, bridge outlines that avoid moving parts; designer edits or locks them | PROPOSED |
| 5 | **X-ray sketch plane** | done as part of B |
| 6 | **Sketch → part:** extrude a sketch by depth or to next contact, "make it a part", stays editable; holes snap to axis centres | Slice 1 BUILT 2026-11-07 (make part, thickness, grow side, dots editable in the orbit view, arrows; not clash-checked). Still to come: extrude to next contact, holes, clash checks for drawn parts |
| 7 | **Shape editing:** front and back outlines independently (tapers/lofts); then balls on the long edges (curved faces); validity check | Back outline BUILT 2026-11-07; joining-edge dots and smooth (Coons) walls BUILT 2026-11-09. Next: a "this shape is broken" check. Lines between any two dots (a free cage) parked: Adam, 2026-11-09, "the edge clicking will let me do probably all that i need to do" |
| 8 | **Parts library:** add/remove/duplicate parts; save your own parts to the library; the clock becomes a preset (absorbs "add gears"); blanks (disc, bar, ring, bridge) and the project's bought parts (step 2) live here too | PROPOSED (Adam, 2026-11-07: "likely a good call") |
| F | **Claude cleans up and fits a part, on request** (first run 2026-11-09: Adam asked Claude to square Part 1 "using just the averages … pick one of the corners and use that to square off of". Done from the session as one logged change: every outline, back and joining-edge link classed by its main direction, the other two coordinates made equal along it (one union-find per axis), plus front-to-back links (walls straight back) and links between matching dots across a wall; each line's value is the reference corner's if it holds it, otherwise the average of its corner dots. Result on his 8-dot part with six stepped edges: all 48 edges within 0.001° of an axis (were up to 12°), both faces flat, back matching front, 0.27 mm average move. A "Square up" button is the obvious next form.) Original ask: "make it perfectly symmetrical based on me getting it this close, and fit it to the blank space and tolerance". Symmetry is cheap (read the dots, find the mirror line, pair and average, write back as one logged change). Fitting needs clash checks for drawn parts first | PARKED 2026-11-07 (Adam: snapping is "the real goal") |
| 9 | **Rate targets:** "this turns at 1 rph" → teeth and stages chosen by the engineer | PROPOSED (from 2026-11-04) |
| 10 | **Export:** each part to STEP/STL with print clearances; preview/export volume check | PROPOSED |
| later | Intent notes in Evaluate; "Evaluate with Claude" API button; mesh collision for 3D parts; machinability checks; reference images; materials/methods; articulation; sections; measurement; tooth form | backlog |

### Hemistitch plan (PROPOSED 2026-11-10)

The first real project (§10.8). It pulls forward the build-order rows it needs; each step is discussed before it's built. Adam: "the pod is the last part of the project."

| # | Step | Uses rows |
|---|---|---|
| H0 | Save the beta: commit the uncommitted sim work (drawn parts, snapping, disk autosave). Needs Adam's "commit"; a push redeploys the public site | DONE 2026-11-10, commit `8e146cf` (not pushed) |
| H1 | **The train moves into the project.** Today the clock's arbors, gears and tooth counts are written into the code ("Tooth counts are fixed for now"). Move them into the scene so each project brings its own train; the clock becomes one project file and must load unchanged | BUILT 2026-11-10 (§5 *Projects*); uses rows 8, 9 |
| H2 | **Hemistitch scene** at real size from §10.8: module 1.0, 2.8 mm layers, compound gears (wheel + pinion as one part), discs as compound parts, faux barrel / escape wheel / fork / balance, the pod as a placeholder block. Locks on disc size, spacing and speeds; the checks list shows disc speeds, meshes and layer clashes; profile shift so 12-leaf pinions don't flag | BUILT 2026-11-10 (`sim/projects/hemistitch-prototype.json`, opened from Project → Open; §10.8 *As built*). The pod placeholder is left for H8 |
| H3 | **Adam arranges it.** He moves parts; Claude checks meshes, clashes and speeds; loop until he locks the arrangement | 1, E |
| H4 | **Test piece** (as soon as the bit arrives, alongside H2–H3): 3 mm bores and 6 mm pockets in 0.05 mm steps, one 12-leaf pinion and a wheel segment, made in CadQuery for Makera Studio. The fits Adam finds become the project's press-fit sizes, and it proves the 1 mm bit can cut the teeth | 10 |
| H5 | **Rods and bearings** on the axes: real sizes, H4's fits, arbor lengths, a shopping list | 2 |
| H6 | **Plates, bridges, pillars:** drawn by Adam in the sketcher, or proposed by Claude on request; bearings cut their pockets; clash checks for drawn parts (not built yet) and Z1 checks (inside radius ≥ 0.5 mm, slots ≥ 1.1 mm) | 3, 4, 6. Holes and pockets BUILT 2026-11-11 (§5 *Projects*); the stacked-plate layer plan for the Slava version is agreed in chat (6 plates, about 39 mm). The six plates were generated 2026-11-11 as drawn parts in `sim/projects/hemistitch-slava.json` (P1 4.0, P2/P3 9.525, P4 3.0, P5 3.3, P6 6.35 mm; 80 cuts: Slava recess, balance window, key access, bearing pockets with seats on the arbors' axes, gear pockets, clearances, three staggered M3 screw sets and two dowels), with the gears and discs moved to the plan's heights. Clash checks and Z1 checks are next |
| H7 | **Export and cut:** each part to a file Makera Studio takes, cut on the Z1, assemble, turn the train by hand at the barrel | 10 |
| H8 | **Motor pod (last):** buy and measure the stepper, design the pod and its locating pins; firmware is Adam's lane | — |

---

## 8. Open questions

1. **Shafts:** for the printed beta, bought steel rod (fixed or turning) with printed gears, or printed shafts? Bearings, bushings, jewels or plain holes? Adam's direction: these belong in the engineer's evaluation conversation, asked when relevant. Since 2026-11-07 (§6.0) none of it is assumed: each axis gets a shaft, stud, jewel or bearing only when Adam adds one.
2. **Evaluate format:** a written report inside the sim, a conversation starter for chat, or both. Adam leaned toward both: a report, plus "claude intervene" / text with Claude.
3. **Claude API in the sim:** whether and when to add an "Evaluate with Claude" button (keys, cost).
4. **Sketcher sides:** confirmed multi-side and orbit-based; how far toward free push/pull (tier 4) to go is open.
5. **Tooth form:** cycloidal teeth, profile shift, or more pinion leaves. For Hemistitch, Claude proposes involute 20° with 12-leaf pinions (§10.8): it keeps the ratio exact when arbor spacing is off by machine error.
6. **Old scaffolding:** delete or restructure `lib/` folders, `projects/hemistitch/`, `SIMULATOR_SPEC.md`.
7. **Commits:** resume the three-tier cadence now? Pushing redeploys the public Pages site.
8. **Reference images:** the Hemistitch photos/renders shared in chat live only in a session scratchpad. Copy into the repo (it's public) or keep elsewhere?
9. **Hemistitch demonstrator anchors** (on hold while the tool is built): case envelope at desktop scale, disc diameter, lug articulation mechanism (single pin, paired shoulder screws, pin + bushing + detent, or Adam's sketch), battery form factor (18650, LiPo pouch, coin cell), motor coupling (D-bore press fit vs round bore + setscrew), crown function. Partly answered 2026-11-10: envelope and discs grow in proportion, set by the cutter (§10.8).
10. **Default minute wheel position** in the clock preset (currently right of centre with a 9 mm hand; Adam will place it).
11. **Hands and their wheels:** RESOLVED 2026-11-07. Adam: "the hands are like any other part, manual control." Hands stay put when their wheel moves; you place them.
12. **Scene files in the repo:** commit `scenes/` (the repo is public) or keep scene files local only?
13. **Project setup box** (Adam, 2026-11-07): a quick start when beginning a project, e.g. "im making this on my makera z1 out of .25" acrylic". Adam: it "will be open to new necessary parts as we proceed creating this ui." Claude proposes defaults from it (stock thickness → part thickness, cutter radius → smallest inside corner); everything can be changed later and is saved with the scene. Nothing in it forces anything (§6.0).
    - **Day one (proposed):** description and goal; starting point (blank, preset, or import: image / sketch / SVG now, STEP later); units (mm or inches, display only, mm underneath); default process with machine, material and stock; smallest cutter; minimum clearance; envelope / boundary parts.
    - **What you're making:** project description and goal, plus a short brief from a kickoff talk with Claude (today: the brief is saved into the scene file and "Report for Claude", so any Claude session starts from it; a talk inside the sim needs the Claude API, Q3); reference bank (§6.11); envelope; print / build scale; design intent that must not change.
    - **How it's made:** a default process that each part can override (the plan mixes printed parts, CNC parts and bought hardware); machine, material and stock per process; tooling (cutter list with smallest diameter and flute length, or nozzle and layer height); minimum clearance and fit types (press, sliding, bearing bore); **bought parts** (§7 step 2); workholding for CNC (top only or flipped, which decides what's an undercut).
    - **How we work:** how much Claude steps in (clashes only by default); which checks run live and which on request.
    - **Where it goes:** export targets (STEP for Fusion / Plasticity, STL, drawings); whether project files stay local or are committed (the repo is public, Q12).
    - Open: confirm the day-one list.

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
- **Dragging on a plane seen edge-on** (2026-11-07): a dot dragged on a vertical face while viewed from above follows a line of sight that runs almost along the face, so a pixel became metres; two of Part 1's back dots landed 25 mm and ~6 m away. → never map the cursor onto a plane at a grazing angle; fall back to a plane facing the camera, and offer axis-locked arrows.
- **A line's click band reached into the dots** (2026-11-09): clicking just beside a corner dot added a new dot on top of it, invisible under the first. → clicks near a dot select it; no new dot within 14 px of an existing one.
- **Stitching surfaces by count, not position** (2026-11-09): joining-edge dots shared each wall equally by link, so walls folded as soon as edges had different dots. → stitch by real depth along the edge.
- **The browser pane forgets** (2026-11-09): the Claude app's browser pane keeps the sim's storage only until the app restarts, and it can't download files, so "Save scene" did nothing there. A demo scene was lost over a weekend. → `serve.py` writes every change to `scenes/autosave.json` with timed backups, and the sim reloads from it when the browser has nothing.
- **Auto-adjust resized teeth a cutter fixes** (2026-11-10): moving a Hemistitch wheel, auto-adjust kept the meshes by changing module to 0.90 and 1.19, below what the 1 mm end mill can cut. → a project can fix tooth sizes (`rules.fixedModule`); then moving a part drags its meshed neighbours along instead, and Checks warns about any tooth smaller than `rules.minModule`.
- **Battery died mid-session** (2026-11-06): autosave kept the layout, but the log and undo history live only in the page and were lost on reload. A Save scene file is the durable copy. Test new code on a separate port (its own browser storage) so the designer's autosave is never touched.

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
- 2026-11-10: the N20 can't creep slowly enough to drive the barrel (it would need ~3,600:1 more). Claude proposes a geared micro stepper in its place (§10.8). The intent above still holds: the visible acrylic train does every reduction, and the stepper only stands in for the spring.

### 10.6 AXIS v1 (case reference)

Repo `Next-Step-Inc/bspk-axis-v1`: 50 × 29 mm tonneau case, 16.72 mm tall, two NH05/NH35 movements each driving a 16 mm × 0.20 mm carbon-fibre disc, 24 mm strap width. Scale ~4× for an ~8" desktop piece. Its `PARAMETERS.md` `[INTENT]` tags inspired §6.6.

### 10.7 Toolchain and links

- Three.js r128 (cdnjs) + OrbitControls and TransformControls from `three@0.128.0/examples/js`.
- CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1, Python 3.14.4, venv at `.venv`.
- Repo: https://github.com/adamontherocks/bspk-studio · Pages: https://adamontherocks.github.io/bspk-studio/
- Artifacts: Gear Composer v0.1 https://claude.ai/artifact/L3UrsmLntHYJRhg7twhLCb · BSPK Studio v0.1 (cushion, superseded) https://claude.ai/artifact/MghKPXzLwiGdi7rEAjep1b
- Hardware: 3D printer (FDM), Makera Z1, xHorse WM-100 (incoming), XSnow metal printer (watching).

### 10.8 Hemistitch prototype (desktop, started 2026-11-10)

Claude's numbers, **PROPOSED** until Adam approves; the givens are in the 2026-11-10 entry of §4. Once built, the scene carries the locks and this is the paper copy.

**Size chain.** The cutter sets the tooth size; the tooth size sets the smallest pinion and the wheel a 4:1 stage needs; the motion works' reach between the two disc arbors caps the scale.
- 1 mm cutter → module 1.0 → 12-leaf pinion Ø14 → 48-tooth wheel Ø50 → motion works reach 54 mm → **2.5× the AXIS layout**: case ≈ 125 × 73 mm (77.5 at the centre), discs Ø47.5, 52.5 mm apart (±26.25).
- Everything scales with the cutter: 0.8 mm → 2.0× (case ≈ 100 mm). 1 mm is proposed first for tooth strength where the barrel drives the whole train, and because ±0.15 mm machine error is a smaller share of a bigger tooth.

**As built (H2, 2026-11-10).** Opened from Project → Open. Changes from the proposal below, all found while laying it out:
- **Barrel 42 teeth, not 48** (3.5:1, the barrel turns once in 3.5 h). With 48 its drum hung ~10 mm past the case corner; with 42 it's 4.5 mm (the only part outside the 2.5× case). Center wheel 48 still clears the barrel's arbor.
- **Motion works 12 → 48 then 14 → 42, not 12 → 48 then 12 → 36.** The 48-tooth minute wheel reaches 24.7 mm; 24 mm from the hour arbor it would hit the hour wheel's stud. With a 14-leaf minute pinion the minute wheel sits 28 mm from the hour arbor (1.8 mm clear), and the hour wheel (42 teeth, Ø43.4) is still smaller than its disc (Ø47.5). Reach 30 + 28 = 58 mm.
- **Profile shift**: every pinion +0.3, every wheel −0.3, so 12-leaf pinions aren't undercut and no mesh shows tooth interference; centre distances unchanged. The 1 mm tool still fits the shifted 12-leaf pinion's root (about 0.04 mm to spare each side: the test piece will tell).
- **Layers** (2.8 mm acrylic, 0.5 mm apart, from z = 1.0): L0 barrel teeth and center pinion, fourth wheel and escape pinion; L0–L1 the barrel drum; L1 third wheel and fourth pinion; L2 center wheel and third pinion, escape wheel, faux fork and balance; L3 kept free for the front plate; L4 cannon pinion and minute wheel; L5 minute pinion and hour wheel; L6 the two discs (top at 23.6 mm). The minute disc sits over a one-layer spacer above the cannon pinion; the hour disc sits directly on the hour wheel.
- **Arbor rule used for the starting layout** (the sim doesn't check it yet; rods arrive in H5): a going-train wheel must stay 2 mm clear of every other going-train arbor, because the rods run plate to plate through all three train layers; arbors at least 8 mm apart for the bearing pockets. The minute wheel and hour wheel ride on studs above the front plate, so they're free of that rule. The layout was found by a search over swing angles and layers; tightest clearances 0.5 mm.
- Locked: both discs (so the disc size, the 52.5 mm spacing and the two disc arbors stay put). Speeds are checked: minute disc 1 turn / h, hour disc 1 turn / 12 h, faux escape wheel 1 turn / min. The minute disc reads 0–55 and the hour disc 12, 1–11, at an index at each disc's 3 o'clock (OPEN: one index or two).
- Export note for H7: gear.html's CadQuery template doesn't know profile shift yet; it has to before these gears are cut.
- The barrel numbers for the pod change with 42 teeth: with the 40-tooth ring, 19,867 steps per barrel turn, ~1.6 steps a second; barrel to escape is 210×, so ~3.8° of escape wheel per step.

**Train as proposed** (module 1.0, involute 20°, all pinions 12 leaves):

| Stage | Teeth | Ratio | Speed | Wheel Ø | Centres |
|---|---|---|---|---|---|
| Barrel → centre | 48 → 12 | 4:1 | barrel 1 turn / 4 h | 50 | 30.0 |
| Centre → third | 48 → 12 | 4:1 | centre 1 turn / h (minute disc) | 50 | 30.0 |
| Third → fourth | 45 → 12 | 3.75:1 | third 1 turn / 15 min | 47 | 28.5 |
| Fourth → escape | 48 → 12 | 4:1 | fourth 1 turn / 4 min; escape 1 turn / min | 50 | 30.0 |
| Cannon pinion (under the minute disc) → minute wheel | 12 → 48 | 4:1 | | 50 | 30.0 |
| Minute pinion → hour wheel (under the hour disc) | 12 → 36 | 3:1 | hour disc 1 turn / 12 h | 38 | 24.0 |

- Barrel to escape wheel: 240× faster. Same five arbors as a watch train, with ~4:1 stages instead of ~8:1, so the escape wheel turns once a minute instead of ~10×.
- The minute disc and the cannon pinion are one compound part on the centre arbor (no idler, so no slack in the minute reading). The hour disc sits on a 36-tooth wheel, smaller than the disc. The minute wheel's arbor lands at the hour disc's rim, so it must stop below the disc layer.
- Disc direction comes from which way the motor turns; no extra gears.

**Barrel drive.**
- Geared micro stepper: a 15 mm "15BY" stepper on an N20-size 12 × 10 mm gearbox (sold as GM12-15BY / GM15BY), 18° step, ~1:298 → 5,960 steps per output turn, 3 mm D-shaft. Seller specs disagree (coil 9 or 30 Ω, shaft length, ratio), so confirm the drawing before buying; a lower coil resistance gives more torque from one Li cell.
- A 12-leaf pinion on its shaft drives a 36-tooth internal ring in the drum (3:1): 17,880 steps per barrel turn, ~1.24 steps a second for 1 turn / 4 h. The ESP32-C keeps time and steps to match, so the speed is exact by program.
- Each step moves the escape wheel ~4.8°, so it ticks about once a second.
- Driver: the DRV8833 already on the list drives a 2-phase stepper in full steps. Pololu's DRV8834 carrier (2.5–10.8 V, microstepping) is the upgrade if the ticks should be smoother.
- **AGREED: a motor pod.** The motor (~25 mm long with its gearbox, to confirm), driver, ESP32 and LiPo live in a separate pod that clicks onto the back plate behind the barrel. Its pinion reaches through a hole in the back plate into the drum's internal ring. Two locating pins in the back plate set the mesh distance every time it clicks in; a clip or magnets hold it. Keep it to the barrel's footprint so the movement stays visible from the back. With the pod off, the train turns freely by hand. Until the motor is in hand, the sim carries the pod as a placeholder block.
- Pod detail for later: with a 36-tooth ring the pinion hole leaves only ~1 mm of plate beside the barrel's bearing pocket; a 40-tooth ring (14 mm off the barrel axis) leaves ~3 mm. 40 teeth → 19,867 steps per barrel turn, ~1.4 steps a second.
- Rejected: running the N20 slowly from the ESP32 (a DC motor can't creep 3,600× below its speed, and jumps get multiplied 240× at the escape wheel); a slower DC gearmotor (~1,000,000:1 overall); an acrylic reduction inside the drum (module-1 gears are too big for the ~3,600:1 needed).
- Risk: drag at the fast end is multiplied 240× at the barrel. Fast-end bearings run without shields or grease (a drop of light oil), and the train must turn freely by hand at the barrel before the motor goes on.

**Makera Z1 rules (Makera's figures).** Work area 200 × 200 × 100 mm; resolution 0.02 mm; spindle runout 0.01 mm; 150 W, up to 13,000 rpm; 1/8" collet. Derived: through-cuts with a 1 mm tool → inside corners ≥ 0.5 mm radius, slots ≥ 1.1 mm, module ≥ 1.0. Arbor spacing opened 0.1 mm for backlash (a review measured ±0.15 mm in aluminium). First cut: a test piece with 3 mm bores, 6 mm pockets and one pinion, to set the press-fit sizes.

**Cutter (1 mm AGREED).** What matters: 1.0 mm cutting diameter, flat (square) end, cutting length at least 3.2 mm (4 mm is better: 2.8 mm through plus a little into the spoilboard), 1/8" shank, carbide, 1 or 2 flutes. Budget packs with a 1.0 mm size (Genmitsu FN10A, FoxAlien flat-nose set) are fine if the listing confirms that length. Genmitsu FN10A ($27.99, sainsmart.com, 2026-11-10): ten 2-flute flat end mills, 1/8" shank, sizes 0.8 / 1.0 / 1.5 / 2.0 ×4 / 2.5 / 3.175 ×2, cutting lengths 4–22 mm, rated for acrylic; one 1.0 mm per pack. Rejected: a 1 mm × 20 mm-reach 4-flute coated steel bit on a 4 mm shank (Harfington 1309988): wrong collet, too many flutes for acrylic chips, needlessly long and whippy. Premium option, not needed at ±0.15 mm: Harvey Tool #989040 (1.02 mm, 3.05 mm cut, 8.3 mm reach, plastics grind, $93.50 on 2026-11-10).

**Bought parts.** About 14 bearings (two per train arbor, two for the hour arbor, two in the minute wheel); 3 mm rod for about 8 arbors.

**OPEN.** Does the hour number glide (what gears do) or jump once an hour (needs a jump mechanism)? Where is the minute disc's indicator? Time setting (a slip clutch on the centre arbor plus a knob) comes with the bridges.

---

## 11. Glossary

- **Axis** — the centre line a group of parts turns on. Not a part: no size, never collides. Shafts, studs, jewels and bearings are parts you add to an axis.
- **Arbor / shaft** — the axle a gear turns on or with. **Pinion** — a small gear (few teeth, "leaves"). **Wheel** — a large gear.
- **Module (m)** — tooth size; meshing gears must share it. **Mesh / stage** — one pair of meshing gears. **Compound** — wheel and pinion fused on one arbor.
- **Plate / bridge / pillar** — the structure holding shaft ends; bridges can cantilever.
- **Lock** — designer-owned; auto-adjust never touches it. **Unlocked** — engineer may adjust.
- **Live-follow** — unlocked parts adapt while you drag. **Report / Evaluate** — conflict report with options. **Auto-correct** — engineer applies fixes, previewed. **Intervene** — ask Claude.
- **X-ray** — see-through mode over the live mechanism while sketching. **Keep-out zone** — area swept by a moving part. **Snap** — points lock to axis centres and part edges.
- **Ball** — an edit point on a sketched edge: filled = sharp, hollow = smooth. **Cage** — the edges that define a sketched part; surfaces fill between them.
- **Extrude to next contact** — push a sketch until it would hit a part, less the minimum gap.
- **Minimum gap** — clearance in real mm between non-meshing parts, sideways and vertical; independent of print scale.
- **Print scale** — multiplier from design size to printed size for the desktop beta.
