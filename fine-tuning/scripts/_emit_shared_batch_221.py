"""One-off emitter for shared-base batch-221 — personal domain (3D printing hobbyist: FDM, SLA, SLS printers, firmware, slicers, materials, calibration).

Writes 50 rows to data/v2/shared/batch_221.tmp.jsonl with ids shared-11001..11050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_221.tmp.jsonl"
ID_OFFSET = 11000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the daily-driver FDM from an Ender 3 V3 SE to a Bambu Labs P1S; enclosed chamber plus AMS handling of PLA and PETG cut my failed-print rate on long overnight runs by more than half.", "decision", "personal", False,
     [("Ender 3 V3 SE", "technology"), ("Bambu Labs P1S", "technology"), ("AMS", "technology"), ("PLA", "technology"), ("PETG", "technology")],
     [("Bambu Labs P1S", "Ender 3 V3 SE", "REPLACES")],
     "which enclosed FDM machine replaced the Ender for overnight jobs and what multi-material feeder does it pair with",
     "bambu p1s ender 3 v3 se ams pla petg overnight enclosed"),
    # --- 2 architecture ---
    ("The Voron 2.4 runs Klipper on a BTT Pi with a CAN-bus toolhead; the umbilical is a single wire instead of the classic spaghetti loom and Fluidd serves the web UI on the local network.", "architecture", "personal", False,
     [("Voron 2.4", "technology"), ("Klipper", "framework"), ("BTT Pi", "technology"), ("CAN-bus", "protocol"), ("Fluidd", "tool")],
     [("Voron 2.4", "Klipper", "USES"), ("Fluidd", "Klipper", "APPLIES_TO")],
     "how is the Voron wired and which web UI handles the local network face of the Klipper host",
     "voron 2 4 klipper btt pi can bus fluidd umbilical toolhead"),
    # --- 3 milestone ---
    ("Finished a 72-hour dual-colour print of a topographic wall map on the Bambu Labs X1 Carbon with PLA from two AMS slots; first completed overnight job since moving the printer into the garage.", "milestone", "personal", False,
     [("Bambu Labs X1 Carbon", "technology"), ("PLA", "technology"), ("AMS", "technology")],
     [("AMS", "Bambu Labs X1 Carbon", "APPLIES_TO")],
     "which dual-colour long print did the X1 Carbon finish in the garage and what filament was loaded in the feeder",
     "bambu x1 carbon topographic map pla ams 72 hour garage milestone"),
    # --- 4 fact ---
    ("My Prusa MK4S ships with a textured PEI sheet that leaves a factory-lithophane finish on the first layer; the smooth PEI is still on the shelf for minis where detail beats grip.", "fact", "personal", False,
     [("Prusa MK4S", "technology"), ("textured PEI", "technology"), ("smooth PEI", "technology")],
     [("textured PEI", "Prusa MK4S", "APPLIES_TO")],
     "which build plate ships on the MK4S by default and which one do I keep aside for minis",
     "prusa mk4s textured pei smooth sheet minis first layer"),
    # --- 5 reference ---
    ("PrusaSlicer, SuperSlicer, and OrcaSlicer all share the same Slic3r fork lineage; profiles migrate between them with only a handful of machine-limit tweaks for the Voron Trident.", "reference", "personal", False,
     [("PrusaSlicer", "tool"), ("SuperSlicer", "tool"), ("OrcaSlicer", "tool"), ("Voron Trident", "technology")],
     [("SuperSlicer", "PrusaSlicer", "IS_A"), ("OrcaSlicer", "PrusaSlicer", "IS_A")],
     "which three slicers share a common fork and what tweaks make profiles portable across them",
     "prusaslicer superslicer orcaslicer slic3r fork voron trident profile"),
    # --- 6 preference ---
    ("Prefer OrcaSlicer over Bambu Studio for the P1S; the calibration wizard for pressure advance and flow ratio is far more exposed than the vendor fork and handles non-Bambu filaments more cleanly.", "preference", "personal", False,
     [("OrcaSlicer", "tool"), ("Bambu Studio", "tool"), ("P1S", "technology"), ("pressure advance", "method"), ("flow ratio", "method")],
     [("OrcaSlicer", "Bambu Studio", "PREFERS")],
     "which slicer do I prefer driving the P1S and which calibration wizards made the choice",
     "orcaslicer bambu studio p1s pressure advance flow calibration"),
    # --- 7 problem ---
    ("First-layer adhesion on the Creality K1 kept failing on ABS until a wipe with isopropyl alcohol fixed it; dish-soap residue on a fresh PEI sheet was silently killing bed contact.", "problem", "personal", False,
     [("Creality K1", "technology"), ("ABS", "technology"), ("isopropyl alcohol", "technology"), ("PEI", "technology")],
     [("isopropyl alcohol", "PEI", "APPLIES_TO")],
     "which cleaning step fixed the ABS first-layer issue on the K1 and what residue was the hidden culprit",
     "creality k1 abs isopropyl alcohol pei first layer dish soap residue"),
    # --- 8 decision ---
    ("Moved the Ender 3 V3 SE off Marlin onto Klipper with a Sonic Pad clone; input shaping at 7 kHz and pressure advance turned a 60 mm/s machine into a dependable 180 mm/s workhorse.", "decision", "personal", False,
     [("Ender 3 V3 SE", "technology"), ("Marlin", "framework"), ("Klipper", "framework"), ("Sonic Pad", "technology"), ("input shaping", "method"), ("pressure advance", "method")],
     [("Klipper", "Marlin", "REPLACES"), ("Klipper", "input shaping", "USES")],
     "which firmware swap took the Ender from crawler speeds to triple and which two calibrations unlocked it",
     "ender klipper marlin sonic pad input shape pressure advance"),
    # --- 9 architecture ---
    ("The Rat Rig V-Core runs RepRapFirmware on a Duet 3 with Mainsail sitting on a separate Raspberry Pi; print jobs land by Moonraker upload and the camera stream lives behind the same interface.", "architecture", "personal", False,
     [("Rat Rig V-Core", "technology"), ("RepRapFirmware", "framework"), ("Duet 3", "technology"), ("Mainsail", "tool"), ("Raspberry Pi", "technology"), ("Moonraker", "service")],
     [("Rat Rig V-Core", "RepRapFirmware", "USES"), ("Mainsail", "Moonraker", "DEPENDS_ON")],
     "how is the Rat Rig split between board firmware and web UI host and what API moves the jobs",
     "rat rig v core reprapfirmware duet mainsail raspberry pi moonraker"),
    # --- 10 noise ---
    ("The cat has claimed the top of the filament dry-box cabinet as a sunlit nap perch and refuses to accept that it is not furniture.", "fact", "noise", True, [], [], None, None),
    # --- 11 fact ---
    ("PA-CF on the Bambu Labs X1 Carbon needs a hardened steel nozzle and 100 C chamber to print cleanly; the standard brass nozzle shows visible wear inside one kilogram of carbon-filled nylon.", "fact", "personal", False,
     [("PA-CF", "technology"), ("Bambu Labs X1 Carbon", "technology"), ("hardened steel nozzle", "technology"), ("brass nozzle", "technology")],
     [("hardened steel nozzle", "brass nozzle", "REPLACES")],
     "which nozzle swap is non-negotiable for PA-CF on the X1 Carbon and what chamber temperature does it want",
     "pa cf x1 carbon hardened steel nozzle brass wear chamber 100"),
    # --- 12 decision ---
    ("Retired the Anycubic Kobra from the active bench to the garage as a dedicated PLA-only machine; the Prusa Mini+ now handles small PETG jobs and frees the big printers for production runs.", "decision", "personal", False,
     [("Anycubic Kobra", "technology"), ("Prusa Mini+", "technology"), ("PLA", "technology"), ("PETG", "technology")],
     [("Prusa Mini+", "Anycubic Kobra", "REPLACES")],
     "which printer took over small PETG duties after the Kobra moved to garage PLA duty",
     "anycubic kobra prusa mini petg pla garage small job"),
    # --- 13 architecture ---
    ("OctoPrint runs on an old Raspberry Pi 3B and only drives the Voron Trident; Klipper talks to the toolhead directly and OctoPrint is effectively a timelapse camera and queue front-end.", "architecture", "personal", False,
     [("OctoPrint", "tool"), ("Raspberry Pi 3B", "technology"), ("Voron Trident", "technology"), ("Klipper", "framework")],
     [("OctoPrint", "Klipper", "APPLIES_TO")],
     "what role does OctoPrint still play on the Voron Trident once Klipper owns the motion path",
     "octoprint raspberry pi 3b voron trident klipper timelapse queue"),
    # --- 14 milestone ---
    ("First successful PEEK print came off the Rat Rig V-Core after swapping to a Mosquito Magnum Plus and a tungsten-carbide nozzle; print chamber held 130 C for the full seven hours.", "milestone", "personal", False,
     [("PEEK", "technology"), ("Rat Rig V-Core", "technology"), ("Mosquito Magnum Plus", "technology"), ("tungsten-carbide nozzle", "technology")],
     [("Mosquito Magnum Plus", "Rat Rig V-Core", "APPLIES_TO")],
     "which hotend and nozzle combo unlocked the first PEEK print and what chamber temperature did it need",
     "peek rat rig mosquito magnum plus tungsten carbide 130 chamber"),
    # --- 15 reference ---
    ("Textured PEI bites PLA and PETG strongly enough that I skip glue entirely; smooth PEI still wants a wipe with isopropyl alcohol between prints or the nylons peel layers mid-job.", "reference", "personal", False,
     [("Textured PEI", "technology"), ("smooth PEI", "technology"), ("PLA", "technology"), ("PETG", "technology"), ("isopropyl alcohol", "technology")],
     [("smooth PEI", "isopropyl alcohol", "APPLIES_TO")],
     "which build surface skips glue outright and which still needs an alcohol wipe between prints",
     "textured pei smooth pla petg glue isopropyl nylon peel"),
    # --- 16 decision ---
    ("Moved my resin workflow from an Anycubic Photon to an Elegoo Saturn for the bigger build volume; the tiling workarounds for tabletop terrain just weren't worth the screen real estate anymore.", "decision", "personal", False,
     [("Anycubic Photon", "technology"), ("Elegoo Saturn", "technology"), ("tabletop terrain", "activity")],
     [("Elegoo Saturn", "Anycubic Photon", "REPLACES")],
     "which SLA machine replaced the Photon for bigger parts and what class of hobby prints drove the upgrade",
     "elegoo saturn anycubic photon sla tabletop terrain build volume"),
    # --- 17 architecture ---
    ("The Formlabs Form 3 lives on a dedicated cart with its wash and cure stations on the shelf below; the whole stack rolls to the kitchen sink for tank swaps without dripping resin across the hallway.", "architecture", "personal", False,
     [("Formlabs Form 3", "technology"), ("wash and cure", "method")],
     [("wash and cure", "Formlabs Form 3", "APPLIES_TO")],
     "how is the Form 3 staged in the house and which ancillary stations live on the cart with it",
     "formlabs form 3 cart wash cure station resin tank kitchen sink"),
    # --- 18 fact ---
    ("Water-washable resin on the Elegoo Mars is dramatically easier to clean up than tough resin on the Formlabs Form 3; plain tap water handles supports while the tough still needs isopropyl alcohol baths.", "fact", "personal", False,
     [("Water-washable resin", "technology"), ("Elegoo Mars", "technology"), ("tough resin", "technology"), ("Formlabs Form 3", "technology"), ("isopropyl alcohol", "technology")],
     [("Water-washable resin", "Elegoo Mars", "APPLIES_TO")],
     "which resin chemistry on which printer avoids the alcohol bath entirely during cleanup",
     "water washable resin mars tough form 3 alcohol bath cleanup"),
    # --- 19 preference ---
    ("Prefer ASA over ABS for outdoor brackets; UV resistance of ASA keeps printed garden parts looking fresh for two summers where ABS went chalky in one season on the south fence.", "preference", "personal", False,
     [("ASA", "technology"), ("ABS", "technology")],
     [("ASA", "ABS", "PREFERS")],
     "which outdoor filament do I prefer over ABS for garden parts and what UV failure tipped the choice",
     "asa abs uv outdoor garden bracket chalky south fence"),
    # --- 20 problem ---
    ("Pressure advance on the Bambu Labs A1 showed ringing on vertical edges no matter the value; input shaping was not re-run after swapping to the high-flow hotend and caused the ghosting.", "problem", "personal", False,
     [("Bambu Labs A1", "technology"), ("Pressure advance", "method"), ("input shaping", "method"), ("high-flow hotend", "technology")],
     [("input shaping", "high-flow hotend", "APPLIES_TO")],
     "which calibration step got skipped after the A1 hotend swap and what artifact did pressure advance not fix",
     "bambu a1 pressure advance ringing ghosting input shape high flow"),
    # --- 21 architecture ---
    ("The drying rack is an eSun eBox stack of three, one for PLA, one for PETG, one for nylon; a temperature and humidity logger writes to Home Assistant over Zigbee and alerts when any box drifts.", "architecture", "personal", False,
     [("eSun eBox", "technology"), ("PLA", "technology"), ("PETG", "technology"), ("nylon", "technology"), ("Home Assistant", "tool"), ("Zigbee", "protocol")],
     [("eSun eBox", "Home Assistant", "COMMUNICATES_WITH")],
     "how is the filament drying rack split by material and what home-automation backbone tracks the humidity",
     "esun ebox pla petg nylon home assistant zigbee humidity drying"),
    # --- 22 decision ---
    ("Dropped Cura as my secondary slicer and standardised on OrcaSlicer across every printer in the workshop; supporting two slicer profile sets for the same spool was eating time I didn't have.", "decision", "personal", False,
     [("Cura", "tool"), ("OrcaSlicer", "tool")],
     [("OrcaSlicer", "Cura", "REPLACES")],
     "which slicer did I cut loose to keep a single profile per spool across the workshop",
     "cura orcaslicer slicer profile spool workshop standardise"),
    # --- 23 milestone ---
    ("The Voron 2.4 build wrapped after nine weekends; first print was a Voron tap calibration cube in ABS and came off the bed clean on the first layer without a fuss.", "milestone", "personal", False,
     [("Voron 2.4", "technology"), ("Voron tap", "technology"), ("ABS", "technology"), ("calibration cube", "activity")],
     [("Voron tap", "Voron 2.4", "APPLIES_TO")],
     "how long did the Voron build take and what was the first print that came off its bed cleanly",
     "voron 2 4 tap calibration cube abs build nine weekend milestone"),
    # --- 24 fact ---
    ("The Creality K1 Max has a larger 300 mm build volume than the K1 but shares the same hotend and accelerometer; swapping parts between them is a direct fit once the belt spacing is re-measured.", "fact", "personal", False,
     [("Creality K1 Max", "technology"), ("K1", "technology")],
     [("Creality K1 Max", "K1", "IS_A")],
     "which two Creality machines share hotend and accelerometer parts despite different build volumes",
     "creality k1 max 300 build volume hotend accelerometer belt spacing"),
    # --- 25 reference ---
    ("Klipper input shaping accepts several algorithms: MZV and EI are the ones I actually use, with MZV for rigid frames like the Voron 2.4 and EI for lighter bedslingers like the A1 Mini.", "reference", "personal", False,
     [("Klipper", "framework"), ("MZV", "algorithm"), ("EI", "algorithm"), ("Voron 2.4", "technology"), ("A1 Mini", "technology")],
     [("MZV", "Voron 2.4", "APPLIES_TO"), ("EI", "A1 Mini", "APPLIES_TO")],
     "which Klipper input-shaping algorithms do I pick for rigid CoreXY versus a lighter bedslinger",
     "klipper input shape mzv ei voron 2 4 a1 mini rigid bedslinger"),
    # --- 26 decision ---
    ("Chose the Prusa XL over building a second Voron 2.4 for production-run workload; five toolheads with automatic tool change beats waiting out long PETG and PA-CF swaps by hand every fifteen minutes.", "decision", "personal", False,
     [("Prusa XL", "technology"), ("Voron 2.4", "technology"), ("PETG", "technology"), ("PA-CF", "technology")],
     [("Prusa XL", "Voron 2.4", "PREFERS")],
     "which production printer beat a second Voron build and what capability did the choice lean on",
     "prusa xl voron 2 4 toolchanger pa cf petg production run"),
    # --- 27 decision ---
    ("Firmware and profile backups rsync nightly from every Raspberry Pi to a Synology NAS on the basement rack; Klipper config, Mainsail macros, and OrcaSlicer profiles are versioned in a local Gitea.", "decision", "personal", False,
     [("Raspberry Pi", "technology"), ("Synology NAS", "technology"), ("Klipper", "framework"), ("Mainsail", "tool"), ("OrcaSlicer", "tool"), ("Gitea", "tool")],
     [("Klipper", "Gitea", "APPLIES_TO"), ("OrcaSlicer", "Gitea", "APPLIES_TO")],
     "how are printer configs and slicer profiles backed up and versioned across every machine in the shop",
     "rsync raspberry synology nas klipper mainsail orcaslicer gitea backup"),
    # --- 28 milestone ---
    ("Hit 10,000 cumulative print hours across the fleet this month; the Prusa MK4S alone carries 4,200 hours and has only eaten two nozzles and one PEI sheet over the two years of daily use.", "milestone", "personal", False,
     [("Prusa MK4S", "technology"), ("PEI", "technology")],
     [("PEI", "Prusa MK4S", "APPLIES_TO")],
     "which fleet-wide print-hour milestone did I hit and how much of it sits on the MK4S alone",
     "10000 hour fleet prusa mk4s 4200 nozzle pei two year milestone"),
    # --- 29 fact ---
    ("TPU 95A feeds cleanly through the Prusa MK4S direct drive but jams every time in the Ender 3 V3 SE Bowden tube; the short, rigid feed path on the Prusa makes all the difference.", "fact", "personal", False,
     [("TPU 95A", "technology"), ("Prusa MK4S", "technology"), ("Ender 3 V3 SE", "technology"), ("direct drive", "method"), ("Bowden", "method")],
     [("direct drive", "Prusa MK4S", "APPLIES_TO"), ("Bowden", "Ender 3 V3 SE", "APPLIES_TO")],
     "which machine feeds TPU 95A reliably and which extruder architecture keeps jamming on the flexible",
     "tpu 95a mk4s direct drive ender bowden jam flexible feed"),
    # --- 30 decision ---
    ("Sold the Elegoo Neptune to fund the Prusa MK4S upgrade; the Klipper-capable replacement board saved the Neptune from the recycling bin but not from changing hands.", "decision", "personal", False,
     [("Elegoo Neptune", "technology"), ("Prusa MK4S", "technology"), ("Klipper", "framework")],
     [("Prusa MK4S", "Elegoo Neptune", "REPLACES")],
     "which older FDM did I sell to fund the MK4S move and what firmware did its replacement board finally run",
     "elegoo neptune prusa mk4s klipper sell fund upgrade board"),
    # --- 31 reference ---
    ("PET-CF and PA-CF look similar on the spool but behave very differently under load; PET-CF is stiffer and more brittle while PA-CF absorbs impact and moisture much more readily.", "reference", "personal", False,
     [("PET-CF", "technology"), ("PA-CF", "technology")],
     [("PET-CF", "PA-CF", "RELATED_TO")],
     "how do PET-CF and PA-CF compare under load and which is the moisture-hungry one on the shelf",
     "pet cf pa cf stiff brittle impact moisture carbon nylon"),
    # --- 32 architecture ---
    ("The Formlabs Fuse 1+ SLS machine runs in the basement workshop with its own ventilation duct to the outside; the Fuse Sift powder-handling station sits beside it on a sealed bench.", "architecture", "personal", False,
     [("Formlabs Fuse 1+", "technology"), ("Fuse Sift", "technology")],
     [("Fuse Sift", "Formlabs Fuse 1+", "DEPENDS_ON")],
     "where does the Fuse 1+ live and which companion powder-handling station is paired with it",
     "formlabs fuse 1 sls basement vent fuse sift powder station"),
    # --- 33 preference ---
    ("Prefer castable resin on the Elegoo Mars for lost-wax jewellery casting over flexible resin; burnout leaves no ash residue and the sprue geometry survives a shell investment intact.", "preference", "personal", False,
     [("castable resin", "technology"), ("Elegoo Mars", "technology"), ("flexible resin", "technology"), ("lost-wax", "method")],
     [("castable resin", "flexible resin", "PREFERS")],
     "which resin do I reach for on the Mars for jewellery casting and which burnout behaviour drove the pick",
     "castable resin mars flexible lost wax burnout sprue shell jewellery"),
    # --- 34 problem ---
    ("First-layer ghosting on the A1 Mini traced to a loose Y-axis belt after a nozzle-change job; a 2 mm deflection at the mid-point fixed with a proper belt tensioning pass and the BED_MESH re-ran clean.", "problem", "personal", False,
     [("A1 Mini", "technology"), ("BED_MESH", "command")],
     [("BED_MESH", "A1 Mini", "APPLIES_TO")],
     "which mechanical slack caused the A1 Mini first-layer ghosting and what command re-ran after tensioning",
     "a1 mini ghosting y belt tension bed mesh deflection first layer"),
    # --- 35 decision ---
    ("Moved every printer's web UI behind a Caddy reverse proxy on the homelab LXC with per-printer subdomains; Mainsail and Fluidd now share SSO instead of exposing random ports on the LAN.", "decision", "personal", False,
     [("Caddy", "tool"), ("Mainsail", "tool"), ("Fluidd", "tool"), ("LXC", "infrastructure")],
     [("Caddy", "Mainsail", "APPLIES_TO"), ("Caddy", "Fluidd", "APPLIES_TO")],
     "which reverse proxy fronts the printer UIs and what authentication story did subdomains unlock",
     "caddy reverse proxy mainsail fluidd lxc subdomain sso printer"),
    # --- 36 architecture ---
    ("Calibration pipeline on a new machine: PID tune the hotend and bed, run INPUT_SHAPER on both axes, then a pressure advance tower and a flow ratio cube in OrcaSlicer before cutting a production print.", "architecture", "personal", False,
     [("PID tune", "method"), ("INPUT_SHAPER", "command"), ("pressure advance", "method"), ("flow ratio", "method"), ("OrcaSlicer", "tool")],
     [("INPUT_SHAPER", "pressure advance", "DEPENDS_ON"), ("OrcaSlicer", "flow ratio", "APPLIES_TO")],
     "what five-step calibration does a new printer walk through before its first production job lands",
     "pid input shaper pressure advance flow ratio orcaslicer new machine"),
    # --- 37 milestone ---
    ("The garage shelf now holds 42 kilograms of filament across twelve spool brands; the tracker spreadsheet flipped from a scratchpad into a proper SQLite-backed inventory with a Home Assistant card.", "milestone", "personal", False,
     [("SQLite", "database"), ("Home Assistant", "tool")],
     [("SQLite", "Home Assistant", "APPLIES_TO")],
     "how much filament is on the garage shelf now and which backend finally replaced the scratchpad inventory",
     "42 kg filament spool sqlite home assistant inventory shelf garage"),
    # --- 38 decision ---
    ("Stuck with Marlin on the Prusa MK4S rather than flashing a custom Klipper config; Prusa's firmware handles input shaping well enough that the custom build wasn't worth giving up factory support.", "decision", "personal", False,
     [("Marlin", "framework"), ("Prusa MK4S", "technology"), ("Klipper", "framework"), ("input shaping", "method")],
     [("Marlin", "Klipper", "PREFERS")],
     "why did the MK4S stay on factory firmware instead of moving to Klipper like the other machines",
     "prusa mk4s marlin klipper factory input shape custom flash"),
    # --- 39 fact ---
    ("The Anycubic Kobra uses a magnetic PEI-coated spring steel sheet; pulling the sheet off and flexing it releases even stubborn ABS prints without touching a scraper.", "fact", "personal", False,
     [("Anycubic Kobra", "technology"), ("PEI", "technology"), ("spring steel", "technology"), ("ABS", "technology")],
     [("PEI", "Anycubic Kobra", "APPLIES_TO")],
     "which build-plate design on the Kobra lets stubborn ABS parts pop off without reaching for a scraper",
     "anycubic kobra pei spring steel magnetic flex abs release"),
    # --- 40 reference ---
    ("PC blends and polycarbonate pure filament both want chamber temperatures above 60 C for layer adhesion; PC-PETG blends print acceptably open-bed but snap along layer lines under any real stress.", "reference", "personal", False,
     [("PC", "technology"), ("polycarbonate", "technology"), ("PC-PETG", "technology")],
     [("PC-PETG", "PC", "IS_A")],
     "which chamber temperature do PC blends need for adhesion and which compromise PC blend delaminates in use",
     "pc polycarbonate pc petg chamber 60 layer adhesion delaminate"),
    # --- 41 architecture ---
    ("The print farm dashboard aggregates Moonraker API feeds from six printers into a single Grafana board; status, chamber, nozzle, and remaining time land in Prometheus via a small exporter per machine.", "architecture", "personal", False,
     [("Moonraker", "service"), ("Grafana", "tool"), ("Prometheus", "tool")],
     [("Grafana", "Prometheus", "DEPENDS_ON"), ("Prometheus", "Moonraker", "COMMUNICATES_WITH")],
     "how does the home print farm collect and visualise printer telemetry across six machines",
     "moonraker grafana prometheus dashboard exporter chamber nozzle farm"),
    # --- 42 milestone ---
    ("The Formlabs Form 4 halves print time on tough resin versus the Form 3 for the same nested tray; the larger LCD plus LPU light source burn a full layer in a handful of seconds.", "milestone", "personal", False,
     [("Formlabs Form 4", "technology"), ("Form 3", "technology"), ("tough resin", "technology"), ("LPU", "technology")],
     [("Formlabs Form 4", "Form 3", "IMPROVES_ON")],
     "how much does the Form 4 cut tough-resin print time compared to the Form 3 and what optical change drives it",
     "formlabs form 4 form 3 tough resin lpu lcd nested tray halve"),
    # --- 43 noise ---
    ("The neighbour's chickens have started roosting on my garage workbench and the hens seem oddly fond of the smell of cured resin trays.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Picked Mainsail over Fluidd as the default web UI across the workshop; the macro editor and the job queue visuals fit my habits better and every printer ends up flashed to the same skin.", "decision", "personal", False,
     [("Mainsail", "tool"), ("Fluidd", "tool")],
     [("Mainsail", "Fluidd", "PREFERS")],
     "which Klipper web UI won the workshop bake-off and what ergonomic wins drove the call",
     "mainsail fluidd klipper web ui macro queue workshop default"),
    # --- 45 preference ---
    ("Prefer a 0.6 mm nozzle over the default 0.4 mm nozzle on the P1S for functional parts; the thicker walls print faster and stronger while the cosmetic loss barely shows on matte PETG.", "preference", "personal", False,
     [("0.6 mm nozzle", "technology"), ("0.4 mm nozzle", "technology"), ("P1S", "technology"), ("PETG", "technology")],
     [("0.6 mm nozzle", "0.4 mm nozzle", "PREFERS")],
     "which nozzle size do I default to on the P1S for functional parts and why does the cosmetic hit barely show",
     "0 6 nozzle 0 4 p1s petg matte functional wall thick fast"),
    # --- 46 milestone ---
    ("The Voron Trident finished its first full CoreXY speed benchy under three minutes on ABS after dialling MZV input shaping at 78 and 82 Hz; that benchmark went on the wall of first-prints.", "milestone", "personal", False,
     [("Voron Trident", "technology"), ("CoreXY", "method"), ("ABS", "technology"), ("MZV", "algorithm")],
     [("MZV", "Voron Trident", "APPLIES_TO")],
     "which sub-three-minute benchmark did the Trident hit and what input-shaping parameters dialled it in",
     "voron trident corexy speed benchy abs mzv 78 82 three minute"),
    # --- 47 decision ---
    ("Random layer shifts on the K1 Max traced to an eccentric nut that had worked loose on the X gantry; a 1/8 turn tightening plus a CANCEL_PRINT macro on skew detection locked the fleet back into green.", "decision", "personal", False,
     [("K1 Max", "technology"), ("eccentric nut", "technology"), ("CANCEL_PRINT", "command")],
     [("CANCEL_PRINT", "K1 Max", "APPLIES_TO")],
     "which mechanical fault caused the K1 Max layer shifts and which Klipper macro now protects against it",
     "k1 max layer shift eccentric nut x gantry cancel print skew"),
    # --- 48 fact ---
    ("ABS-like resin on the Anycubic Photon feels the closest to an injection-moulded part of any consumer resin I've tried; flex is still low but the edges stop chipping when a wrench slips.", "fact", "personal", False,
     [("ABS-like resin", "technology"), ("Anycubic Photon", "technology")],
     [("ABS-like resin", "Anycubic Photon", "APPLIES_TO")],
     "which resin class on the Photon gets closest to injection-moulded feel and what failure mode does it cure",
     "abs like resin anycubic photon injection mould edge chip wrench"),
    # --- 49 architecture ---
    ("The slicer-to-printer path for the MK4S is a Prusa Connect upload rather than an SD card; jobs queue in the browser and the printer pulls the G-code over the local network without a physical handoff.", "architecture", "personal", False,
     [("MK4S", "technology"), ("Prusa Connect", "service"), ("G-code", "technology"), ("SD card", "technology")],
     [("Prusa Connect", "SD card", "REPLACES")],
     "how does the MK4S pull jobs off the slicer now and what hand-off did Prusa Connect retire at the bench",
     "mk4s prusa connect sd card g code browser queue network"),
    # --- 50 reference ---
    ("Z-offset values on a textured PEI sheet run roughly 0.02 mm higher than on smooth PEI for the same first-layer squish; swapping sheets without re-homing Z is how most of my first-layer mishaps start.", "reference", "personal", False,
     [("textured PEI", "technology"), ("smooth PEI", "technology"), ("Z-offset", "method")],
     [("Z-offset", "textured PEI", "APPLIES_TO")],
     "how does Z-offset differ between textured and smooth PEI and what habit avoids a first-layer mishap on a swap",
     "z offset textured pei smooth first layer squish swap rehome"),
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
