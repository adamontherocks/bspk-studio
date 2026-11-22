# Main plate (D1): intent inventory

*First step of the resolver path (VISION.md §7, agreed 2026-11-22). This lists everything the main plate is for, so a resolver can
build the plate from it every time, instead of the plate being whatever a chain of passes left. Read from Adam's scene of
2026-11-22. Adam reviews it before anything is built from it.*

**Part:** 1/2" acrylic (12.7 mm), z 0 to 12.7, milled from the top face only. Every wheel of the going train sits in it; the
motion-works plate and the crescent rim plate stand on its top face.

## 1. Outline

| What | Intent | Today |
|---|---|---|
| Rim | A true circle, r 66 about (0, 0) (the movement is Ø132) | 13 smooth dots; the curve sags up to 0.083 mm between them, and the plates on top copy it (P97-P100) |

## 2. Wheel recesses: rule R1

**Recess Ø = the gear's tip Ø + 1.5 (0.75 all round); floor = the gear's underside - 0.5; centred on the arbor and moving with it.**
Eleven recesses follow it exactly:

| Recess | Gear (teeth, shift) | Tip Ø | Recess Ø | Floor | Gear underside |
|---|---|---|---|---|---|
| Barrel | 42, -0.3 | 43.40 | 44.90 | 6.7 | 7.2 |
| Centre pinion | 12, +0.3 | 14.60 | 16.10 | 6.7 | 7.2 |
| Centre wheel | 48, -0.3 | 49.40 | 50.90 | 4.1 | 4.6 |
| Third pinion | 12, +0.3 | 14.60 | 16.10 | 4.1 | 4.6 |
| Third wheel | 45, -0.3 | 46.40 | 47.90 | 9.3 | 9.8 |
| Intermediate pinion | 12, +0.3 | 14.60 | 16.10 | 9.3 | 9.8 |
| Intermediate wheel | 48, -0.3 | 49.40 | 50.90 | 6.7 | 7.2 |
| Seconds pinion | 12, +0.3 | 14.60 | 16.10 | 6.7 | 7.2 |
| Seconds wheel | 36, -0.3 | 37.40 | 38.90 | 4.1 | 4.6 |
| Escape pinion | 12, +0.3 | 14.60 | 16.10 | 4.1 | 4.6 |

Three don't:

| Recess | Today | The rule would give | Why it differs |
|---|---|---|---|
| Escape wheel | Ø19.5, floor 9.3 | Ø19.42 (the drawn wheel's tips reach r 8.96) | Sized for the wheel's earlier, taller teeth (P46 shortened them) |
| Pallet fork sweep | Ø22.7, floor 9.3 | the fork's swept outline over its swing + 0.75 | Sized for an earlier fork (escapement 2 and P46 changed it); the fork's shaft also reaches over the balance well |
| Balance well | Ø39, floor 1.7 | Ø35.5 (balance Ø34 + 1.5) | 2.5 mm all round instead of 0.75; reason not recorded (see question 1) |

## 3. Bearings: rule R2

**Each arbor's bearing is pressed into a bore under the lowest recess on that arbor, as deep as the bearing is wide.**
3×6×2.5 bearings (bore Ø6 × 2.5) for the barrel and centre arbors, 1×3×1 (Ø3 × 1) for the rest. All eight follow it:
barrel (floor 4.2), centre (1.6), third (3.1), intermediate (5.7), seconds (3.1), escape (3.1), pallet fork (8.3), balance (0.7).

## 4. Screw pilots: rule R3

**An M2 pilot, Ø1.6 × 4 deep, under every screw of a part that sits on this plate.** All ten land exactly under their screws
today: crescent rim plate × 3, motion-works plate × 6, seconds bridge × 1 (through the motion-works plate's own pilot).

## 5. Windows and the crown works

Shapes from Adam's design; sizes from the parts they serve.

| Cut | Intent | Today |
|---|---|---|
| Side window onto the balance | A slot 24 wide from the rim to the balance well, floor = the well's floor (1.7), closed above by the crescent rim plate | as intended |
| Side window onto the barrel | A slot 24 wide from the rim to the barrel's recess, floor = that recess floor (6.7), closed above by the motion-works plate | as intended |
| Worm pocket | Round the worm (its axis at z 5.6, along y), floor 0.3 under it (1.3); its end walls take the worm's thrust | as intended |
| Worm seat | Under the worm end of the worm and stem cap (one part after P91), floor 9.9 so the cap sits flush at 12.7; with r 0.5 corners where the cap's bar meets its square | today two caps; the merge is built in scratch, not loaded |
| Stem groove | 4.1 wide (the Ø4 stem + 0.1), floor 3.6 so the stem rests on it (axis 5.6 - 2), from the worm out through the rim | as intended |
| Crown flat | Vertical, square to the stem, through the plate; the crown stands 1 mm off it | as intended |

## 6. Plate too thin to keep: rule R4 (today's 35 "Clean" pockets are its output, not intent)

- Walls and points of plate under 2.4 mm wide come down to the floor beside them, rounded r 1.2 (a 1/8" cutter's corner is r 1.6, a 2 mm cutter's r 1.0).
- Islands of plate under 40 mm² standing above the floors round them come down.
- Floor strips under 1 mm wide drop to the floor below, so walls run straight down.
- **Not yet a rule:** where a cut meets the rim at a shallow angle (the stem groove at about 46°, the crown flat, the side windows), the plate between them is a knife edge. Today it is taken down and "rounded r 1", and that is exactly where the true r 66 rim broke (shallow notches and hairlines of rim). See question 3.

## 7. What the resolver must hold (its acceptance test)

- Milled from the top face only; every inside corner reachable by a cutter that can reach that depth (`produce.py`: 1 mm cutters within 3 mm of the face, 2 mm and 1/8" deeper).
- No plate thinner than the R4 limits; no towers.
- 0.75 round every gear's tips, 0.5 under every part, and the sim's 0.5 mm gap to every moving part's sweep.
- Plate removed only where a part needs the room or rule R4 says so.
- One wall across heights: no wall drawn twice, no notches or kinks; ledges that taper into a wall kept smooth (they are transitions, not defects).
- The plates standing on it (motion-works plate, crescent rim plate) keep their edges on this plate's walls where they sit on them, and their rims on this rim.

## 8. Decisions (Adam, 2026-11-22: "Use your answers")

1. **Balance well:** kept at Ø39, 2.5 mm round the balance: a deliberate well round the show piece (the one exception to R1).
2. **Escape wheel and fork sweep recesses:** re-derived from today's drawn wheel and fork with rule R1 (tips or swept outline + 0.75).
3. **Knife edges at the rim:** where a cut meets the rim at a shallow angle, the plate's corner is one r 1.2 arc into the rim (the family radius). The thin shelf where that arc runs into the rim is a taper, kept.
4. **Thin-plate numbers:** rule R4 keeps 2.4 mm and r 1.2.
