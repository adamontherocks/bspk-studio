# Movement brief: what we know before designing (2026-11-15)

Compiled from five research passes (Adam's BSPK repos; movement engineering; jump hour and retrograde mechanisms; haute design language incl. Adam's eight reference photos; demo-scale build practice). Nothing was downloaded; sources are linked. [mem] marks standard practice not verified this session; [judgement] marks a researcher's estimate to prove on a test piece.

## 1. What went wrong before, and the rules that follow
- No earlier Claude-designed movement exists; past failures were cases (AXIS lugs: engineer-mode tools on a designer-mode shape; drafting from one spec section) and the early bspk-studio "skyscraper" builds. Rules: reference first, one step at a time, compare to references visually, give Adam handles to edit, report what was and wasn't checked, and follow his drawing when words and drawing disagree.
- Adam's taste on record: restraint on the dial and drama in the mechanism, matte over polished, unusual proportions, at most one accent, anti-mass-market, "cool" required. Deal-breakers: chrome, dial logos, diamonds, generic black-and-aluminium. Red-green colour deficiency: never signal by red or green alone.

## 2. Going train and power [mem unless linked]
- Swiss lever escape wheel: 15 teeth, 2 beats per tooth. Escape rpm = vph / 1800: 18,000 → 10 rpm, 21,600 → 12, 28,800 → 16. Centre (1 rph) to escape = 600 / 720 / 960; the fourth wheel (seconds, 1 rpm) to escape = 10 / 12 / 16.
- Three stages of 7–10:1 in a real watch; barrel to centre ≈ 6–6.5:1 (barrel 80–96 teeth, centre pinion 12–14).
- Barrel: arbor ≈ 1/3 of the barrel's inner diameter; spring length L = π(DB² − DA²)/(8t) at about 50 % fill; 6–8 useful turns; reserve ≈ turns × barrel-to-centre ratio hours. https://watchesbysjx.com/2025/11/in-depth-balancing-mainspring-dimensions-inside-the-barrel.html · https://theindex.nawcc.org/CalcMainspringLength.php
- Teeth: watches use cycloidal (NIHS 20-25) for sharp ratios with few leaves; involute tolerates centre-distance error. https://watchesbysjx.com/?p=307033 · https://www.csparks.com/watchmaking/CycloidalGears/index.jxl

## 3. Escapement, balance, motion and keyless works [mem]
- Swiss lever (15 T): 24° pitch, 12° per beat; pallets span 2.5 teeth; impulse on the wheel ≈ 11°, drop ≈ 2°, lock 1.5–2°, draw 12–15°; fork swing ≈ 10–11° lock to lock; balance lift 40–50°; banking ≈ 1–1.5° past lock. Wheel-to-pallet centre distance ≈ escape radius × √2 in the 90° tangential layout. Drawing method: https://www.abbeyclock.com/wxeb13.html · best geometry source (unread): https://theindex.nawcc.org/Articles/Zoller-SwissEscModel.pdf
- Balance ≈ 0.5 × movement diameter; 2.5 / 3 / 4 Hz.
- Motion works 12:1, e.g. (30/10) × (40/10). Keyless: stem, sliding pinion, winding pinion, crown wheel (face teeth), ratchet and click, setting lever and yoke, setting wheel to minute wheel. https://wornandwound.com/watchmakers-bench-what-makes-it-tick-part-3-keyless-works-and-the-hand-setting-mechanism/
- Layout: main plate + barrel bridge + train bridge + pallet bridge + balance cock; endshake 0.02–0.05 mm (demo scale 0.1–0.2).
- Open designs to study: OpenMovement OM10 (open-source Swiss lever) https://hackaday.com/2025/06/03/open-source-watch-movement-really-ticks-all-the-boxes · Marco Lang's open files https://watchesbysjx.com/2023/09/marco-lang-open-source-movement.html

## 4. Retrograde minute and jumping hour
- **Retrograde:** a snail (Archimedean spiral) turning once an hour, a feeler on a pivoted rack, the rack's sector turning the hand's pinion, a return spring; the snail ends in a cliff (Blancpain adds a beak so the feeler drops cleanly). Sweep = (snail rise / feeler arm) × (rack radius / pinion radius). Fly-back can rebound: hand stop pin at zero, shaped jumper, play-catch rake. The feeler can't climb the cliff backward, so reverse driving must slip or be blocked (a ratchet and click on the drive does this). Urwerk UR-150 sweeps ≈ 240°. US10928777 / US20190086867A1 · EP3208665A1 · https://watchesbysjx.com/2025/05/urwerk-ur-150-scorpion-innovation.html · https://horopedia.org/retrograde-display/
- **Jumping hour:** a 12-point star stepping 30° an hour, driven by a finger on a wheel turning once an hour, detented by a jumper whose nose climbs a flank, passes an unstable apex and drops into the next seat. Instantaneous versions store energy over the hour and release it with a lever or cam. Failure modes: weak jumper (incomplete jump), poor indexing (early or late), crown forcing, train disturbance at release. WO2006108878A1 · https://horopedia.org/jumper-spring/ · https://monochrome-watches.com/meistersinger-salthora-jumping-hours-explained/
- **One event for both:** in US10928777 the rack's fly-back itself kicks the hour ring one step; the rack spring is the only energy store, and a shaped jumper stops the ring rebounding. The going train only loads the spring slowly through the snail.

## 5. Design language (principles, not copies)
1. Layers are a hierarchy, not a stack: one quiet ground, a few bridges, a few wheels, one hero; 3–4 clear levels.
2. Bridge outlines come from the wheels they carry: arcs, crescents and lobes concentric with a wheel, or tangent sweeps that leave a ring of teeth visible; never a pocket cut into a slab.
3. Organized asymmetry: one axis, one weight, one counterweight.
4. Straight against curved, every junction a clean tangent or a deliberate angle.
5. Few strong openings, each a designed shape; reveal only the wheels worth seeing.
6. Raised vs sunken stated by edges: a bevel follows every raised outline; sunken wells are cut into the plate.
7. Inside corners are a decision (hand-finished sharp corners are a luxury tell; end-mill radii read as machine-made).
8. Screws and jewels are composition: at bridge feet and ends, in pairs or on the bridge's axis, slots aligned; jewels relate to wheel centres; never sprinkled evenly.
9. A limited palette: one ground, one bridge finish, one train colour, one accent.
10. Show a selected part of the train and keep the hero in view.
11. Proportion: bridges about a third to a half of the wheel they carry, generous margins, engraving follows a curve.
12. Five don'ts: uniform margins and round-hole skeletons; evenly scattered screws and jewels; end-mill radii as a feature; opening everything; many finishes at equal weight.
- Adam's references, read: Mickaël Gaspar No.1 and Date Rétrograde (sweeping arms spiralling to jewels, retrograde date arc, sand-brown ground); R.W. Smith S6 prototype (engraved double-lobe bridge, blue screws on the diagonal); a cut-away dial revealing barrel and balance under thin arms; "Calibre Ouréa" (quiet grey plate, few dark curved bridges, gold wheels, empty space as a shape); a grained plate with a sunken copper barrel and a ring-bridged balance; Cleguer Inspiration One (sinuous bridge, three-lobed train bridge, big ratchet wheel); FVF Genève (stepped, angular, consistent bridge widths). Attributions marked uncertain in the report where not legible.

## 6. Building the motion study (module 1, about 110–120 mm, Makera Z1) [judgement: prove on test pieces]
- Involute teeth (forgive centre-distance error). The 1 mm end mill just fits a module-1 root: shorten the dedendum to 1.1–1.15 m and make the CAM tooth space the tool path. Pinions 12 leaves minimum with x ≈ +0.3 to +0.4.
- Backlash 0.08–0.15 mm total: centre distance nominal + 0.05–0.08; cut a test pair first.
- POM (Delrin) for wheels and pinions, cast acrylic for plates and bridges (acrylic gears are brittle). Crossings ≥ 1.5–2 mm in POM, ≥ 2.5 mm in acrylic; inside corners r ≥ 0.5; rim ≥ 2 m under the root; ≥ 3–4 mm from a bearing seat to an edge.
- Bearing seats: POM OD − 0.02…0.05 (light press); acrylic OD + 0…0.03 (slip) with a cap plate (don't press acrylic: it crazes). Wheels on rods: a metal collar with a grub screw, or retaining compound on a flatted rod (POM press fits creep).
- Right-angle crown: a pin wheel (1 mm steel pins in a disc, 3 mm pitch) driven by a ≥ 12-leaf pinion on the stem; no worm (self-locking), no bevels.
- Springs: the retrograde return spring is always loaded, so steel (wire 0.2–0.3 mm or shim), clamped with a screw and a stop pin — Delrin creeps (modulus 2900 → 1600 MPa over 1000 h). A jumper can be Delrin: length ≥ 25–30 × thickness, 0.8–1.2 mm thick, strain ≈ 1.5·t·δ/L² under 1 %, unloaded between jumps.
- Faux balance: a crank and link from a train wheel swinging the balance ±150–250°; a decorative hairspring; a slip coupling on any faux escape wheel.

## 7. Gaps
No published star-wheel or jumper angles, snail rise or rack radii; no NIHS tables or ETA datasheets read; no scale-model failure data. These get designed from first principles and proven in the sim's contact checks and on test pieces.
