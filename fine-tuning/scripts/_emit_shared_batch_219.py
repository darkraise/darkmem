"""One-off emitter for shared-base batch-219 — personal domain (metalworking: manual lathe, milling, CNC routers, tooling, measurements, workholding, MIG/TIG/stick welding, welding codes, YouTube machinists).

Writes 50 rows to data/v2/shared/batch_219.tmp.jsonl with ids shared-10901..10950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_219.tmp.jsonl"
ID_OFFSET = 10900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Replaced the old South Bend lathe in the home shop with a Colchester Student 1800 because the Colchester has a proper gearbox for threading and enough swing to turn a brake rotor without fuss.", "decision", "personal", False,
     [("South Bend", "tool"), ("Colchester Student 1800", "tool"), ("brake rotor", "activity")],
     [("Colchester Student 1800", "South Bend", "REPLACES")],
     "which manual lathe took over the home shop from the South Bend and what capability sealed the choice",
     "colchester south bend lathe threading gearbox swing rotor"),
    # --- 2 architecture ---
    ("The milling side of the garage runs a Bridgeport knee mill for rough work and a Tormach 1100M for finished parts; the Bridgeport feeds rectangular blanks that the Tormach then takes through a full operation under G-code.", "architecture", "personal", False,
     [("Bridgeport", "tool"), ("Tormach 1100M", "tool"), ("G-code", "language")],
     [("Tormach 1100M", "Bridgeport", "BUILDS_ON")],
     "how are the Bridgeport knee mill and Tormach 1100M staged in the garage milling workflow",
     "bridgeport knee mill tormach 1100m g code stage blank finish"),
    # --- 3 decision ---
    ("Picked a Haas TM-1 over another Tormach 1100M for the second mill slot; the Haas control pays off on the longer production runs and the tool changer moves a lot faster between ops.", "decision", "personal", False,
     [("Haas TM-1", "tool"), ("Tormach 1100M", "tool")],
     [("Haas TM-1", "Tormach 1100M", "PREFERS")],
     "which CNC mill won the second-slot bake-off against the Tormach 1100M and why",
     "haas tm 1 tormach control tool changer production run"),
    # --- 4 milestone ---
    ("Finished the first full part on the Pocket NC this weekend: a 5-axis titanium bracket cut from 6Al-4V bar stock with a four-flute ball-nose finisher, and the surface came off the machine ready to anodise.", "milestone", "personal", False,
     [("Pocket NC", "tool"), ("6Al-4V", "technology"), ("ball-nose", "tool"), ("anodise", "activity")],
     [("ball-nose", "Pocket NC", "USES")],
     "which milestone part came off the Pocket NC and what stock and cutter produced the finish",
     "pocket nc titanium 6al 4v ball nose bracket anodise"),
    # --- 5 fact ---
    ("The Shapeoko in the garage is a Shapeoko 4 XXL running a Carbide Compact Router; I cut signs in walnut and aluminium plate on it and the belt drive is the obvious limit on hard materials.", "fact", "personal", False,
     [("Shapeoko 4 XXL", "tool"), ("Carbide Compact Router", "tool"), ("walnut", "food"), ("aluminium plate", "technology")],
     [("Shapeoko 4 XXL", "Carbide Compact Router", "USES")],
     "which hobby CNC router sits in the garage and which spindle and materials define its envelope",
     "shapeoko 4 xxl carbide compact router walnut aluminium belt"),
    # --- 6 decision ---
    ("Upgraded the shop CNC router from the Shapeoko 4 XXL to an Avid CNC PRO 4848; the rack-and-pinion drive and the servo option keep the head planted when hogging aluminium at real feedrates.", "decision", "personal", False,
     [("Shapeoko 4 XXL", "tool"), ("Avid CNC PRO 4848", "tool")],
     [("Avid CNC PRO 4848", "Shapeoko 4 XXL", "REPLACES")],
     "which larger CNC router replaced the Shapeoko 4 XXL and which drivetrain feature justified the cost",
     "avid cnc pro 4848 shapeoko rack pinion servo aluminium feed"),
    # --- 7 architecture ---
    ("The Langmuir MR-1 lives on the steel side of the shop and handles everything that will not fit on the Tormach 1100M; the water-cooled spindle and the cast-epoxy frame eat the mill-the-bed marathon sessions.", "architecture", "personal", False,
     [("Langmuir MR-1", "tool"), ("Tormach 1100M", "tool"), ("water-cooled spindle", "technology")],
     [("Langmuir MR-1", "Tormach 1100M", "EXTENDS")],
     "how does the Langmuir MR-1 fit alongside the Tormach 1100M in the steel-side workflow",
     "langmuir mr 1 tormach steel water spindle cast epoxy"),
    # --- 8 reference ---
    ("Kept the Atlas 10F as a second lathe for small soft-jaw work; the Atlas is small enough to live on the bench and the threading dial is original, which matters for restoring pre-war fasteners.", "reference", "personal", False,
     [("Atlas 10F", "tool"), ("threading dial", "tool"), ("soft-jaw", "tool")],
     [("Atlas 10F", "soft-jaw", "APPLIES_TO")],
     "which small lathe kept its bench slot for soft-jaw and restoration work and what makes it fit",
     "atlas 10f threading dial soft jaw pre war fastener bench"),
    # --- 9 preference ---
    ("Prefer ER32 collets over R8 holders on the Bridgeport for anything under half an inch; the ER32 pull-back grips a reground end mill without the drift an R8 shows after a few tool changes.", "preference", "personal", False,
     [("ER32", "tool"), ("R8", "tool"), ("Bridgeport", "tool"), ("end mill", "tool")],
     [("ER32", "R8", "PREFERS")],
     "which collet system do I reach for on the Bridgeport for small cutters and why",
     "er32 r8 bridgeport end mill collet drift pull back"),
    # --- 10 noise ---
    ("The shop cat knocked an empty coffee can off the bench three times this morning before the can finally rolled under the lathe for good.", "fact", "noise", True, [], [], None, None),
    # --- 11 fact ---
    ("The face mill on the Tormach 1100M is a 2-inch 5-insert body running CNMG inserts; the light cut is 0.015 inch at 2500 RPM and it leaves a mirror on 6061 without any climb-conventional games.", "fact", "personal", False,
     [("Tormach 1100M", "tool"), ("face mill", "tool"), ("CNMG", "tool"), ("6061", "technology")],
     [("face mill", "Tormach 1100M", "USES")],
     "which face mill and insert run on the Tormach 1100M and what cut yields a mirror on 6061",
     "face mill tormach cnmg 6061 mirror 2 inch insert rpm"),
    # --- 12 architecture ---
    ("Tooling on the Haas TM-1 is organised around a 24-pocket library of ER40 holders; the end mills live in pockets 1-10, the spot drill and reamers in 11-16, and the probe and face mill at the far end.", "architecture", "personal", False,
     [("Haas TM-1", "tool"), ("ER40", "tool"), ("spot drill", "tool"), ("probe", "tool"), ("face mill", "tool"), ("reamer", "tool")],
     [("ER40", "Haas TM-1", "USES")],
     "how is the 24-pocket tool library laid out on the Haas TM-1 and which tools live where",
     "haas tm 1 er40 pocket library spot drill reamer probe face"),
    # --- 13 decision ---
    ("Picked a woodruff cutter over a slot drill for the keyway on the motor shaft; the woodruff leaves a cleaner radius at the end of the slot and the shaft is only taking a square key under light torque.", "decision", "personal", False,
     [("woodruff cutter", "tool"), ("slot drill", "tool"), ("keyway", "concept")],
     [("woodruff cutter", "slot drill", "PREFERS")],
     "which cutter won the keyway job on the motor shaft and what trade-off decided it",
     "woodruff slot drill keyway radius motor shaft square key"),
    # --- 14 problem ---
    ("The 3D mould finish kept chipping out with a sharp square end mill on the Pocket NC; switching to a bull-nose with a 0.030 inch corner radius survived the long stepover passes and killed the chip-out on the next run.", "problem", "personal", False,
     [("Pocket NC", "tool"), ("bull-nose", "tool"), ("stepover", "method")],
     [("bull-nose", "Pocket NC", "APPLIES_TO")],
     "which cutter swap fixed the 3D mould chip-out on the Pocket NC and how did the corner radius help",
     "pocket nc bull nose 3d mould stepover corner chip out"),
    # --- 15 fact ---
    ("The Starrett 436 micrometer calibrates against a Mitutoyo gauge block set every Monday; the drift has stayed under 0.0001 inch across a year of daily use in the unheated garage.", "fact", "personal", False,
     [("Starrett 436", "tool"), ("Mitutoyo", "organization"), ("gauge block", "tool")],
     [("Starrett 436", "gauge block", "USES")],
     "how is the Starrett 436 micrometer calibrated and what drift has held across a year in the garage",
     "starrett 436 micrometer mitutoyo gauge block calibrate drift"),
    # --- 16 decision ---
    ("Moved from dial calipers to a Mitutoyo 500-196-30 digital on the shop bench; the absolute encoder holds zero through battery swaps and the IP67 body survives coolant splashes on the mill.", "decision", "personal", False,
     [("dial calipers", "tool"), ("Mitutoyo 500-196-30", "tool")],
     [("Mitutoyo 500-196-30", "dial calipers", "REPLACES")],
     "which digital caliper replaced the dial on the bench and which features locked in the choice",
     "mitutoyo 500 196 30 dial caliper absolute ip67 coolant"),
    # --- 17 architecture ---
    ("Inspection routine for the Tormach 1100M leans on a Haimer 3D Taster for part zeros and a Renishaw-style probe macro for the bore; the dial test indicator stays on the quill for tramming the head.", "architecture", "personal", False,
     [("Tormach 1100M", "tool"), ("Haimer 3D Taster", "tool"), ("dial test indicator", "tool"), ("probe macro", "method")],
     [("Haimer 3D Taster", "Tormach 1100M", "USES")],
     "how is part-zero and bore inspection split across probes and indicators on the Tormach 1100M",
     "tormach haimer 3d taster dial test indicator probe bore zero"),
    # --- 18 milestone ---
    ("Retrofit milestone on the Bridgeport: finished installing a Newall DRO with a three-axis readout, and the head no longer has to dance backlash games for a 0.0005 inch move.", "milestone", "personal", False,
     [("Bridgeport", "tool"), ("Newall DRO", "tool")],
     [("Newall DRO", "Bridgeport", "APPLIES_TO")],
     "which DRO retrofit landed on the Bridgeport and what manual-control pain did it retire",
     "bridgeport newall dro three axis readout backlash retrofit"),
    # --- 19 decision ---
    ("Standardised on the Kurt DX6 vise as the primary workholding on both CNC mills; the hardened jaws hold a tenth across a summer-to-winter temperature swing and the pull-down action saves a dial pass.", "decision", "personal", False,
     [("Kurt DX6", "tool"), ("hardened jaws", "tool"), ("pull-down", "method")],
     [("Kurt DX6", "hardened jaws", "USES")],
     "which vise is standard across the CNC mills and which feature keeps the parts flat across seasons",
     "kurt dx6 vise hardened jaw pull down tenth summer winter"),
    # --- 20 reference ---
    ("The Saunders SMW fixture plate on the Tormach 1100M uses the 25 mm grid with M12 clamps; fixtures move between the Tormach and the Haas TM-1 without re-indicating because both tables share the same layout.", "reference", "personal", False,
     [("Saunders SMW", "tool"), ("Tormach 1100M", "tool"), ("Haas TM-1", "tool"), ("M12 clamps", "tool")],
     [("Saunders SMW", "Tormach 1100M", "APPLIES_TO"), ("Saunders SMW", "Haas TM-1", "APPLIES_TO")],
     "how does the Saunders SMW grid let fixtures travel between the Tormach 1100M and Haas TM-1",
     "saunders smw fixture plate 25 mm m12 tormach haas travel"),
    # --- 21 architecture ---
    ("Workholding stack for thin parts runs parallels under the part, soft jaws milled in situ on the Kurt DX6, and a magnetic chuck for anything too thin to squeeze without bowing the centre.", "architecture", "personal", False,
     [("parallels", "tool"), ("soft jaws", "tool"), ("Kurt DX6", "tool"), ("magnetic chuck", "tool")],
     [("soft jaws", "Kurt DX6", "APPLIES_TO")],
     "how is thin-part workholding layered across parallels, soft jaws, and the magnetic chuck",
     "parallel soft jaw kurt dx6 magnetic chuck thin part bow"),
    # --- 22 decision ---
    ("Bought a Miller Multimatic 215 as the one-box solution for the new weld bench; the multi-process cart covers MIG for sheet, stick for farm repairs, and enough TIG headroom for the aluminium side projects.", "decision", "personal", False,
     [("Miller Multimatic 215", "tool"), ("MIG", "method"), ("stick", "method"), ("TIG", "method")],
     [("Miller Multimatic 215", "MIG", "SUPPORTS"), ("Miller Multimatic 215", "TIG", "SUPPORTS"), ("Miller Multimatic 215", "stick", "SUPPORTS")],
     "which welder became the one-box shop solution and which three processes does it cover",
     "miller multimatic 215 mig tig stick multi process weld bench"),
    # --- 23 preference ---
    ("Prefer the Lincoln Square Wave TIG 200 over an Everlast PowerTIG for my aluminium work; the balance and frequency controls let me chase a clean puddle on 1/8 inch 6061 without the arc wander the Everlast showed on my bench.", "preference", "personal", False,
     [("Lincoln Square Wave TIG 200", "tool"), ("Everlast PowerTIG", "tool"), ("6061", "technology")],
     [("Lincoln Square Wave TIG 200", "Everlast PowerTIG", "PREFERS")],
     "which TIG machine do I reach for on aluminium and which settings beat the Everlast on my bench",
     "lincoln square wave tig 200 everlast powertig 6061 balance"),
    # --- 24 fact ---
    ("The shop Hobart Handler 210 runs on a 230 V circuit and handles 1/4 inch mild steel in a single pass; I keep it set up with 0.035 inch ER70S-6 wire and the drive rolls are factory stock.", "fact", "personal", False,
     [("Hobart Handler 210", "tool"), ("ER70S-6", "technology"), ("230 V", "config")],
     [("Hobart Handler 210", "ER70S-6", "USES")],
     "which MIG welder sits on the 230 V circuit and which wire and setup does it run",
     "hobart handler 210 er70s 6 230 v wire mild steel"),
    # --- 25 decision ---
    ("Swapped from a cheap brand stick box to an ESAB Rebel EMP 215ic for field repairs on the trailer; the inverter drop keeps the arc alive at the end of a 100 ft extension when the 7018 starts sticking cold.", "decision", "personal", False,
     [("ESAB Rebel EMP 215ic", "tool"), ("7018", "technology"), ("inverter", "technology")],
     [("ESAB Rebel EMP 215ic", "7018", "USES")],
     "which field stick welder replaced the cheap box and what extension-cord behaviour justified it",
     "esab rebel emp 215ic 7018 inverter extension cord trailer"),
    # --- 26 architecture ---
    ("Shielding-gas layout on the weld bench: a 75/25 argon-CO2 mix feeds the MIG for carbon steel, a pure argon bottle feeds the TIG for aluminium, and a tri-mix cylinder sits on the stainless cart.", "architecture", "personal", False,
     [("75/25", "technology"), ("argon", "technology"), ("tri-mix", "technology"), ("MIG", "method"), ("TIG", "method")],
     [("75/25", "MIG", "APPLIES_TO"), ("argon", "TIG", "APPLIES_TO")],
     "how are the shielding gas bottles split across MIG, TIG, and stainless work on the bench",
     "75 25 argon co2 tri mix tig mig stainless cylinder bottle"),
    # --- 27 preference ---
    ("Prefer 2% lanthanated tungsten over 2% thoriated for all my AC and DC work; the lanthanated holds a point longer on DC steel and strikes cleaner on AC aluminium, and I stop breathing thoriated dust at the grinder.", "preference", "personal", False,
     [("lanthanated", "technology"), ("thoriated", "technology"), ("AC", "config"), ("DC", "config")],
     [("lanthanated", "thoriated", "PREFERS")],
     "which tungsten type do I prefer across AC and DC and what health angle tips the decision",
     "lanthanated thoriated tungsten ac dc steel aluminium dust"),
    # --- 28 reference ---
    ("Ceriated tungsten stays on the cart for low-amperage DC work on thin stainless; the ceriated starts reliably at 10 amps where the lanthanated wants a little more heat before the arc settles in.", "reference", "personal", False,
     [("ceriated", "technology"), ("lanthanated", "technology"), ("stainless", "technology")],
     [("ceriated", "lanthanated", "IMPROVES_ON")],
     "which tungsten do I keep for low-amp stainless and how does it compare to the lanthanated",
     "ceriated lanthanated stainless tungsten low amp dc strike"),
    # --- 29 milestone ---
    ("Passed the 3G MIG plate test at the community college on the first try; the root ran with a short-circuit transfer at 18 volts and the cap came out flat enough that the bend test showed no cracks at either edge.", "milestone", "personal", False,
     [("3G", "config"), ("MIG", "method"), ("short-circuit transfer", "method"), ("bend test", "method")],
     [("MIG", "3G", "APPLIES_TO")],
     "which welding position test did I pass on the first try and what transfer mode and test outcome",
     "3g mig plate test short circuit bend community college"),
    # --- 30 decision ---
    ("Decided to chase the 6G pipe ticket next spring rather than the 4G plate; the 6G opens the field pipefitter side jobs that the 4G would not, and my TIG hand is strong enough to pass the root.", "decision", "personal", False,
     [("6G", "config"), ("4G", "config"), ("TIG", "method")],
     [("6G", "4G", "PREFERS")],
     "which welding certification am I chasing next and why the 6G wins over the 4G path",
     "6g 4g pipe ticket plate tig pipefitter spring chase"),
    # --- 31 reference ---
    ("Welding positions 1G through 4G are the plate tests and 1G, 2G, 5G, and 6G are the pipe tests; the 6G is a 45-degree fixed pipe and covers everything below it on the AWS list.", "reference", "personal", False,
     [("1G", "config"), ("2G", "config"), ("4G", "config"), ("5G", "config"), ("6G", "config"), ("AWS", "organization")],
     [("6G", "AWS", "APPLIES_TO")],
     "how do the plate and pipe welding positions map and which single test covers the rest",
     "1g 2g 4g 5g 6g pipe plate aws position fixed 45"),
    # --- 32 architecture ---
    ("Destructive testing for the class runs a guided-bend fixture on 3/8 inch coupons; a face-bend and a root-bend come out of each 3G and 4G plate and a visual pass plus zero cracks over 1/8 inch is the accept rule.", "architecture", "personal", False,
     [("guided-bend fixture", "tool"), ("face-bend", "method"), ("root-bend", "method"), ("3G", "config"), ("4G", "config")],
     [("guided-bend fixture", "face-bend", "USES"), ("guided-bend fixture", "root-bend", "USES")],
     "how is destructive bend testing set up for the 3G and 4G plate coupons and what is the pass rule",
     "guided bend fixture face root 3g 4g coupon crack accept"),
    # --- 33 reference ---
    ("Code welders on our crew qualify to AWS D1.1 for structural steel and ASME Section IX for the pressure side; the D1.1 is enough for the building beams and the Section IX unlocks the boiler work.", "reference", "personal", False,
     [("AWS D1.1", "publication"), ("ASME Section IX", "publication"), ("structural steel", "technology"), ("boiler", "technology")],
     [("AWS D1.1", "structural steel", "APPLIES_TO"), ("ASME Section IX", "boiler", "APPLIES_TO")],
     "which welding codes qualify the crew for structural versus pressure work and what each unlocks",
     "aws d1 1 asme section ix structural boiler code welder"),
    # --- 34 decision ---
    ("Picked Tubalcain aka Mr. Pete as the first YouTube reference for the lathe work; the 1950s-shop-teacher pacing matches how I actually learn and the thread-cutting series got me through my first 8-TPI run.", "decision", "personal", False,
     [("Tubalcain", "person"), ("Mr. Pete", "person"), ("lathe", "tool"), ("8-TPI", "config")],
     [("Tubalcain", "Mr. Pete", "IS_A")],
     "which YouTube machinist did I pick as the first lathe reference and which series helped first",
     "tubalcain mr pete lathe youtube thread 8 tpi shop teacher"),
    # --- 35 preference ---
    ("Prefer Abom79 over This Old Tony for heavy-repair content; Abom's big-iron repairs match the scale of the Colchester and the Bridgeport, and This Old Tony fits the weekend-project slot instead.", "preference", "personal", False,
     [("Abom79", "person"), ("This Old Tony", "person"), ("Colchester", "tool"), ("Bridgeport", "tool")],
     [("Abom79", "This Old Tony", "PREFERS")],
     "which YouTube machinist do I prefer for heavy-repair content and where does This Old Tony land",
     "abom79 this old tony colchester bridgeport heavy repair weekend"),
    # --- 36 fact ---
    ("This Old Tony's fly-cutter video is the one I rewatched before running the first flycut on the Bridgeport; the chip-thickness explanation saved the part from a chatter pattern I did not know how to diagnose.", "fact", "personal", False,
     [("This Old Tony", "person"), ("fly-cutter", "tool"), ("Bridgeport", "tool")],
     [("fly-cutter", "Bridgeport", "APPLIES_TO")],
     "which This Old Tony video saved the first Bridgeport flycut from a chatter pattern",
     "this old tony fly cutter bridgeport chip thickness chatter"),
    # --- 37 problem ---
    ("The Tormach 1100M threw chatter on a 1/2 inch end mill in 4140 last night; diagnosed as spindle runout after a tool change, and re-seating the ER40 collet nut with the proper torque wrench killed the pattern on the second pass.", "problem", "personal", False,
     [("Tormach 1100M", "tool"), ("end mill", "tool"), ("4140", "technology"), ("ER40", "tool")],
     [("ER40", "Tormach 1100M", "USES")],
     "which chatter bug showed up on the Tormach 1100M in 4140 and what fix killed it",
     "tormach 1100m chatter 4140 er40 collet torque end mill"),
    # --- 38 problem ---
    ("TIG arc on the Lincoln Square Wave TIG 200 wandered all afternoon on a clean aluminium job; traced the fault to a 75/25 bottle accidentally connected instead of the pure argon, and the arc settled the moment the gas got right.", "problem", "personal", False,
     [("Lincoln Square Wave TIG 200", "tool"), ("75/25", "technology"), ("argon", "technology")],
     [("argon", "Lincoln Square Wave TIG 200", "APPLIES_TO")],
     "which gas mix mix-up made the Lincoln Square Wave TIG 200 wander and how did the right bottle fix it",
     "lincoln square wave tig 200 75 25 argon aluminium wander"),
    # --- 39 milestone ---
    ("Finished wiring the Avid CNC PRO 4848 to the new 100-amp subpanel in the garage; the NEMA 6-50 outlet feeds the servo drives and the router now runs through a full aluminium pocketing cycle without a breaker trip.", "milestone", "personal", False,
     [("Avid CNC PRO 4848", "tool"), ("NEMA 6-50", "config"), ("subpanel", "infrastructure")],
     [("Avid CNC PRO 4848", "NEMA 6-50", "USES")],
     "which power retrofit landed for the Avid CNC PRO 4848 and how did it prove out in production",
     "avid cnc pro 4848 nema 6 50 subpanel 100 amp servo"),
    # --- 40 architecture ---
    ("The measurement chain in the inspection drawer goes gauge blocks at the top, the Starrett 436 micrometer against the blocks, and the Mitutoyo 500-196-30 caliper for rough work; the dial test indicator lives on the mill for tramming only.", "architecture", "personal", False,
     [("gauge blocks", "tool"), ("Starrett 436", "tool"), ("Mitutoyo 500-196-30", "tool"), ("dial test indicator", "tool")],
     [("Starrett 436", "gauge blocks", "USES"), ("Mitutoyo 500-196-30", "Starrett 436", "IMPROVES_ON")],
     "how is the inspection drawer layered from gauge blocks down to calipers and where does the indicator sit",
     "gauge block starrett 436 mitutoyo caliper dial test indicator chain"),
    # --- 41 milestone ---
    ("Moved the thread-cutting work off the Atlas 10F and onto the Colchester Student 1800; the Colchester's quick-change gearbox handles metric and imperial without swapping change gears, and my Monday evenings got a lot shorter.", "milestone", "personal", False,
     [("Atlas 10F", "tool"), ("Colchester Student 1800", "tool"), ("change gears", "tool")],
     [("Colchester Student 1800", "Atlas 10F", "REPLACES")],
     "which lathe took over thread cutting from the Atlas 10F and what feature shortened the sessions",
     "colchester student 1800 atlas 10f thread gearbox metric"),
    # --- 42 fact ---
    ("The Pocket NC's 5-axis envelope is a 5-inch cube and the spindle tops out at 10000 RPM; small parts that would take three setups on the Bridgeport come off in one operation with the rotary-A tilting-B head.", "fact", "personal", False,
     [("Pocket NC", "tool"), ("Bridgeport", "tool"), ("rotary-A", "concept"), ("tilting-B", "concept")],
     [("Pocket NC", "Bridgeport", "IMPROVES_ON")],
     "what is the Pocket NC envelope and how does its 5-axis head beat three Bridgeport setups",
     "pocket nc 5 axis 5 inch cube 10000 rpm rotary tilting"),
    # --- 43 noise ---
    ("A neighbour dropped off half a peach cobbler in a foil pan and the smell of cinnamon is fighting with the cutting oil in the garage.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Went with a Haimer 3D Taster over an edge finder as the default on the Bridgeport; the Haimer registers within 0.0002 inch without spinning the spindle and the learning curve cost me one afternoon, not a week.", "decision", "personal", False,
     [("Haimer 3D Taster", "tool"), ("edge finder", "tool"), ("Bridgeport", "tool")],
     [("Haimer 3D Taster", "edge finder", "REPLACES")],
     "which probe replaced the edge finder on the Bridgeport and what precision and ramp-up does it offer",
     "haimer 3d taster edge finder bridgeport 0 0002 spin"),
    # --- 45 milestone ---
    ("Finished the first successful 8-TPI single-point thread on the Colchester Student 1800 this weekend; followed Tubalcain's pick-up technique to re-engage the half-nut, and a Starrett 436 micrometer confirmed the pitch-diameter was in class 2A.", "milestone", "personal", False,
     [("Colchester Student 1800", "tool"), ("8-TPI", "config"), ("Tubalcain", "person"), ("Starrett 436", "tool"), ("2A", "config")],
     [("Starrett 436", "Colchester Student 1800", "APPLIES_TO")],
     "which first-thread milestone landed on the Colchester Student 1800 and which reference and tool verified it",
     "colchester 8 tpi thread tubalcain starrett 436 2a class"),
    # --- 46 fact ---
    ("Fume extraction on the weld bench is a dedicated Lincoln Miniflex arm overhead of the stand, with a MERV-15 filter cartridge; the arm covers MIG and stick jobs and the TIG side stays upwind of the filter for tungsten-dust reasons.", "fact", "personal", False,
     [("Lincoln Miniflex", "tool"), ("MERV-15", "technology"), ("MIG", "method"), ("stick", "method"), ("TIG", "method")],
     [("Lincoln Miniflex", "MERV-15", "USES")],
     "how is weld-fume extraction arranged across MIG, stick, and TIG on the bench and why the TIG-side offset",
     "lincoln miniflex merv 15 fume arm mig tig stick tungsten"),
    # --- 47 milestone ---
    ("Completed the ASME Section IX practice coupon at the local community college; a 6G carbon-steel pipe with a 7018 root and a 7018 fill, and the bend coupons came out clean under the county inspector's eye.", "milestone", "personal", False,
     [("ASME Section IX", "publication"), ("6G", "config"), ("7018", "technology")],
     [("7018", "6G", "APPLIES_TO")],
     "which ASME practice coupon did I complete and which rod and position came out clean under inspection",
     "asme section ix 6g 7018 pipe bend coupon practice"),
    # --- 48 reference ---
    ("The ESAB Rebel EMP 215ic covers MIG, TIG, and stick on a single front panel; it is the field welder my Hobart Handler 210 is not, and the Hobart stays in the shop on the 230 V line as the daily MIG.", "reference", "personal", False,
     [("ESAB Rebel EMP 215ic", "tool"), ("Hobart Handler 210", "tool"), ("MIG", "method"), ("TIG", "method"), ("stick", "method")],
     [("ESAB Rebel EMP 215ic", "Hobart Handler 210", "EXTENDS")],
     "how do the ESAB Rebel EMP 215ic and Hobart Handler 210 split the field-versus-shop welder role",
     "esab rebel hobart handler field shop mig tig stick 230"),
    # --- 49 architecture ---
    ("Shop power layout keeps the Haas TM-1 on its own 30-amp three-phase rotary converter, the Bridgeport and both lathes on a shared 20-amp single-phase circuit, and the welders on their own 50-amp plug at the bench end.", "architecture", "personal", False,
     [("Haas TM-1", "tool"), ("rotary converter", "technology"), ("Bridgeport", "tool"), ("30-amp three-phase", "config"), ("50-amp", "config")],
     [("Haas TM-1", "rotary converter", "USES")],
     "how is shop power divided across the Haas TM-1, the mills and lathes, and the welder bench",
     "haas tm 1 30 amp three phase rotary converter 50 amp welder"),
    # --- 50 decision ---
    ("Standardised on 0.035 inch ER70S-6 wire across the Hobart Handler 210 and the Miller Multimatic 215; one wire size covers the range from 18 gauge to 1/4 inch with gas adjustments and stops the Friday-night spool shuffle.", "decision", "personal", False,
     [("ER70S-6", "technology"), ("Hobart Handler 210", "tool"), ("Miller Multimatic 215", "tool")],
     [("ER70S-6", "Hobart Handler 210", "APPLIES_TO"), ("ER70S-6", "Miller Multimatic 215", "APPLIES_TO")],
     "which MIG wire became the shop standard across both welders and what range does it cover",
     "er70s 6 0 035 hobart handler miller multimatic 215 18 gauge"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
