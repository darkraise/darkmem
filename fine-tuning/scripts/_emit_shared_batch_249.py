"""One-off emitter for shared-base batch-249 — personal domain (amateur astronomy and astrophotography: telescopes, mounts, eyepieces, cameras, filters, software, guiding, objects, dark-sky sites).

Writes 50 rows to data/v2/shared/batch_249.tmp.jsonl with ids shared-12401..12450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_249.tmp.jsonl"
ID_OFFSET = 12400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped my Celestron C8 for a Celestron C11 after a year of aperture fever; the bigger Schmidt-Cassegrain pulls out the dust lane in M31 from my Bortle 5 backyard like nothing the eight-inch managed.", "decision", "personal", False,
     [("Celestron C8", "technology"), ("Celestron C11", "technology"), ("Schmidt-Cassegrain", "technology"), ("M31", "place"), ("Bortle 5", "config")],
     [("Celestron C11", "Celestron C8", "REPLACES"), ("Celestron C11", "M31", "APPLIES_TO")],
     "which Schmidt-Cassegrain upgrade finally pulled the Andromeda dust lane out of a suburban backyard",
     "celestron c8 c11 schmidt cassegrain aperture m31 andromeda bortle 5"),
    # --- 2 ---
    ("Mounted the C11 on a Celestron CGX-L after the smaller CGEM started tracking-jittering under load; guiding RMS dropped from 1.4 arcsec to 0.6 arcsec on the same imaging night.", "milestone", "personal", False,
     [("Celestron CGX-L", "technology"), ("CGEM", "technology"), ("C11", "technology"), ("guiding RMS", "concept"), ("arcsec", "concept")],
     [("Celestron CGX-L", "CGEM", "REPLACES"), ("Celestron CGX-L", "C11", "APPLIES_TO")],
     "how much did guiding RMS improve after mounting the eleven-inch on the heavier CGX-L",
     "celestron cgx l cgem c11 mount guiding rms arcsec jitter load"),
    # --- 3 ---
    ("Picked the Takahashi FSQ-106 over the William Optics refractor for the wide-field rig; the flat field corner-to-corner on APS-C is worth the price tag on a full moon night.", "decision", "personal", False,
     [("Takahashi FSQ-106", "technology"), ("William Optics", "technology"), ("APS-C", "technology")],
     [("Takahashi FSQ-106", "William Optics", "PREFERS")],
     "which wide-field refractor won the bake-off for flat corner stars on the APS-C imaging train",
     "takahashi fsq 106 william optics refractor wide field aps c flat"),
    # --- 4 ---
    ("Bought a used Takahashi TOA-150 at the Cherry Springs star party; the triplet apo replaced the old achromatic refractor that was bleeding purple around every bright star.", "decision", "personal", False,
     [("Takahashi TOA-150", "technology"), ("Cherry Springs", "place"), ("triplet apo", "technology"), ("achromatic refractor", "technology")],
     [("Takahashi TOA-150", "achromatic refractor", "REPLACES")],
     "which Takahashi triplet replaced the chromatic-aberration-prone achromat after the Cherry Springs trip",
     "takahashi toa 150 cherry springs triplet apo achromatic purple fringe"),
    # --- 5 ---
    ("The Sky-Watcher EQ6-R Pro sits on the grab-and-go pier; it handles the FSQ-106 plus a guide scope without breaking a sweat and cost a third of the 10Micron I was eyeing.", "decision", "personal", False,
     [("Sky-Watcher EQ6-R Pro", "technology"), ("FSQ-106", "technology"), ("guide scope", "technology"), ("10Micron", "technology"), ("pier", "technology")],
     [("Sky-Watcher EQ6-R Pro", "10Micron", "PREFERS")],
     "which mount ended up on the grab-and-go pier for the wide-field rig and why not the premium Italian option",
     "sky watcher eq6 r pro fsq 106 guide scope 10micron pier grab go"),
    # --- 6 ---
    ("The 10Micron GM1000 HPS lives on the observatory pier driving the TOA-150; absolute encoders mean I can slew without guiding for sub-three-minute subs and still hit round stars.", "architecture", "personal", False,
     [("10Micron GM1000", "technology"), ("observatory pier", "place"), ("TOA-150", "technology"), ("absolute encoders", "technology"), ("subs", "concept")],
     [("10Micron GM1000", "TOA-150", "APPLIES_TO")],
     "which premium mount drives the observatory TOA-150 and what does the encoder stack unlock for unguided subs",
     "10micron gm1000 hps observatory pier toa 150 absolute encoder unguided"),
    # --- 7 ---
    ("The iOptron CEM70 is the travel mount for Atacama trips; center-balanced encoder design survives airline handling and sets up on the concrete pad at La Serena in under twenty minutes.", "fact", "personal", False,
     [("iOptron CEM70", "technology"), ("Atacama", "place"), ("La Serena", "place"), ("center-balanced", "pattern")],
     [("iOptron CEM70", "Atacama", "APPLIES_TO")],
     "which travel mount survives airline handling for Atacama trips and sets up fast on the La Serena pad",
     "ioptron cem70 atacama la serena travel mount center balance airline"),
    # --- 8 ---
    ("Retired the Losmandy G11 after its worm-gear backlash cost me two full imaging runs on the Helix; a regrease helped once but the repeat problem made the upgrade to 10Micron inevitable.", "problem", "personal", False,
     [("Losmandy G11", "technology"), ("worm-gear backlash", "pattern"), ("Helix", "place"), ("10Micron", "technology")],
     [("10Micron", "Losmandy G11", "REPLACES")],
     "which mount problem cost two Helix imaging runs and triggered the upgrade to the premium mount",
     "losmandy g11 worm gear backlash helix ngc 7293 regrease 10micron"),
    # --- 9 ---
    ("The ZWO ASI2600MM Pro is the mono workhorse on the TOA-150; Sony IMX571 sensor plus the narrowband wheel gives clean Ha frames at unity gain on the Eagle Nebula without amp glow.", "architecture", "personal", False,
     [("ZWO ASI2600MM Pro", "technology"), ("TOA-150", "technology"), ("IMX571", "technology"), ("narrowband wheel", "technology"), ("Ha", "config"), ("Eagle Nebula", "place")],
     [("ZWO ASI2600MM Pro", "TOA-150", "APPLIES_TO"), ("ZWO ASI2600MM Pro", "Eagle Nebula", "APPLIES_TO")],
     "which mono camera rides the premium refractor for Eagle Nebula narrowband and what sensor drives it",
     "zwo asi2600mm pro mono imx571 toa 150 narrowband ha eagle m16"),
    # --- 10. noise ---
    ("The neighbour's porch light finally went off at 11 pm last Tuesday and I stood there slack-jawed at how dark the yard suddenly felt.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The ZWO ASI533MC Pro is the one-shot-colour scope camera for the FSQ-106; square sensor means no stitching fuss and the 3.76 micron pixels match the focal length cleanly.", "fact", "personal", False,
     [("ZWO ASI533MC Pro", "technology"), ("FSQ-106", "technology"), ("square sensor", "technology"), ("3.76 micron", "concept")],
     [("ZWO ASI533MC Pro", "FSQ-106", "APPLIES_TO")],
     "which one-shot-colour camera pairs with the wide-field apo and why does pixel pitch matter here",
     "zwo asi533mc pro fsq 106 one shot colour square sensor 3 76 micron"),
    # --- 12 ---
    ("Upgraded from the ASI533 to a ZWO ASI6200MM Pro on the C11 at native focal length; full-frame IMX455 wants a proper flat field corrector and the C11 meets it barely.", "decision", "personal", False,
     [("ASI533", "technology"), ("ZWO ASI6200MM Pro", "technology"), ("C11", "technology"), ("IMX455", "technology"), ("flat field corrector", "technology")],
     [("ZWO ASI6200MM Pro", "ASI533", "REPLACES")],
     "which full-frame mono replaced the small-sensor camera on the C11 and what accessory does it demand",
     "zwo asi6200mm pro asi533 c11 imx455 full frame flat field corrector"),
    # --- 13 ---
    ("The Player One Poseidon-M sits on the guide scope as a bright-star OAG alternative; fan-cooled and the USB hub pass-through cleaned up the cable snake on the dovetail.", "fact", "personal", False,
     [("Player One", "technology"), ("Poseidon-M", "technology"), ("guide scope", "technology"), ("OAG", "technology"), ("USB hub", "technology")],
     [],
     "which camera replaced an OAG setup for guiding and how did it tidy the cable routing on the dovetail",
     "player one poseidon m guide scope oag usb hub cable snake fan"),
    # --- 14 ---
    ("Kept a QHY5L-II Mono as the backup autoguider; tiny body fits the finder-guider slot on the travel rig and drivers under NINA on Windows have been rock solid for three seasons.", "reference", "personal", False,
     [("QHY5L-II Mono", "technology"), ("NINA", "tool"), ("finder-guider", "technology"), ("Windows", "platform")],
     [],
     "which backup autoguider fits the finder-guider slot and how have the NINA drivers held up",
     "qhy5l ii mono autoguider finder guider nina windows backup travel"),
    # --- 15 ---
    ("Optolong L-eXtreme filter sits in the 2-inch drawer for dual-narrowband on the OSC rig; Ha plus OIII in a single pass over suburban Bortle 6 makes the Veil Nebula glow without a mono wheel.", "architecture", "personal", False,
     [("Optolong L-eXtreme", "technology"), ("2-inch drawer", "technology"), ("Ha", "config"), ("OIII", "config"), ("Bortle 6", "config"), ("Veil Nebula", "place")],
     [("Optolong L-eXtreme", "Veil Nebula", "APPLIES_TO")],
     "which dual-narrowband filter lets the one-shot-colour rig pull the Veil out of suburban skies",
     "optolong l extreme dual narrowband oiii ha veil bortle 6 osc"),
    # --- 16 ---
    ("Narrowband wheel loaded with 3nm Ha, OIII, and SII from Antlia; the 3nm Ha pulls filaments out of the Eagle that the 7nm Optolong was smearing under the full moon.", "decision", "personal", False,
     [("Antlia", "technology"), ("Ha", "config"), ("OIII", "config"), ("SII", "config"), ("Optolong", "technology"), ("Eagle", "place")],
     [("Antlia", "Optolong", "REPLACES")],
     "which narrowband filter upgrade pulled Eagle Nebula filaments back under moonlit skies",
     "antlia 3nm ha oiii sii optolong 7nm eagle m16 full moon filament"),
    # --- 17 ---
    ("NINA drives the imaging rig end to end: plate solve, autofocus with the hocus-focus plugin, meridian flip, and dither between subs all fire without me in the loop.", "architecture", "personal", False,
     [("NINA", "tool"), ("plate solve", "method"), ("hocus-focus", "tool"), ("meridian flip", "concept"), ("dither", "method")],
     [],
     "which capture software owns the automation chain from plate solve to meridian flip and which autofocus plugin does it run",
     "nina plate solve autofocus hocus focus meridian flip dither automate"),
    # --- 18 ---
    ("Dropped APT for NINA after the plate-solve loop in APT kept stalling on the M42 centering routine; NINA's ASTAP backend recovers from a failed solve in seconds.", "decision", "personal", False,
     [("APT", "tool"), ("NINA", "tool"), ("M42", "place"), ("ASTAP", "tool"), ("plate-solve", "method")],
     [("NINA", "APT", "REPLACES")],
     "which capture tool replaced APT after its M42 centering routine kept stalling on plate solve",
     "nina apt astap plate solve stall m42 orion nebula center capture"),
    # --- 19 ---
    ("SharpCap handles the planetary and lunar runs on the Maksutov-Cassegrain; the sensor analysis tool measured the ASI533 read noise and set gain defaults for the rest of the season.", "decision", "personal", False,
     [("SharpCap", "tool"), ("Maksutov-Cassegrain", "technology"), ("ASI533", "technology"), ("read noise", "concept")],
     [],
     "which software runs planetary captures on the Mak and what calibration did it contribute to the main rig",
     "sharpcap planetary lunar maksutov cassegrain asi533 read noise gain"),
    # --- 20 ---
    ("PixInsight is the processing pipeline of record; WBPP runs calibration, registration, and integration, then GraXpert handles gradient removal before BlurXTerminator and NoiseXTerminator finish stars and background.", "architecture", "personal", False,
     [("PixInsight", "tool"), ("WBPP", "tool"), ("GraXpert", "tool"), ("BlurXTerminator", "tool"), ("NoiseXTerminator", "tool")],
     [],
     "which processing pipeline runs from calibration through gradient removal to star and noise reduction",
     "pixinsight wbpp graxpert blurxterminator noisexterminator process pipeline"),
    # --- 21 ---
    ("Tried Siril as a free alternative when the PixInsight licence lapsed for a month; stacking was fine but the lack of multiscale linear transform ended the experiment within two sessions.", "problem", "personal", False,
     [("Siril", "tool"), ("PixInsight", "tool"), ("multiscale linear transform", "method")],
     [("PixInsight", "Siril", "PREFERS")],
     "which free processing tool filled in for a month and which missing feature pushed the return to PixInsight",
     "siril pixinsight licence free multiscale linear transform stacking"),
    # --- 22 ---
    ("DeepSkyStacker still owns the Milky Way panorama stacks because it handles registration on star-sparse wide-field frames better than the PixInsight StarAlignment defaults.", "reference", "personal", False,
     [("DeepSkyStacker", "tool"), ("Milky Way", "place"), ("PixInsight", "tool"), ("StarAlignment", "method")],
     [],
     "which stacker still handles Milky Way panorama frames because StarAlignment defaults struggle on star-sparse data",
     "deep sky stacker milky way panorama star sparse wide field staralign"),
    # --- 23 ---
    ("Stellarium runs on the laptop for planning the night; I use it with the ocular plugin loaded with the Ethos 13 and the Delos 10 to preview a target before dragging the scope out.", "fact", "personal", False,
     [("Stellarium", "tool"), ("ocular plugin", "tool"), ("Ethos 13", "technology"), ("Delos 10", "technology")],
     [],
     "which planning tool previews eyepiece fields of view before setup and which two eyepieces are loaded in the ocular plugin",
     "stellarium ocular plugin ethos 13 delos 10 preview target plan"),
    # --- 24 ---
    ("SkySafari Pro on the iPad drives the evening's observing list; the Messier Marathon March plan loads from a saved search and tapping an object slews the Sky-Watcher via BT.", "fact", "personal", False,
     [("SkySafari Pro", "tool"), ("iPad", "technology"), ("Messier Marathon", "event"), ("Sky-Watcher", "technology"), ("BT", "protocol")],
     [],
     "which tablet app drives the Messier Marathon observing list and how does it command the mount",
     "sky safari pro ipad messier marathon sky watcher bluetooth slew"),
    # --- 25 ---
    ("TheSkyX Professional drove the observatory for two years before I moved to KStars with Ekos; the cross-platform story on the Raspberry Pi mini-PC sealed the move.", "decision", "personal", False,
     [("TheSkyX Professional", "tool"), ("KStars", "tool"), ("Ekos", "tool"), ("Raspberry Pi", "platform")],
     [("KStars", "TheSkyX Professional", "REPLACES")],
     "which observatory control suite replaced TheSkyX and which platform story drove the switch",
     "theskyx professional kstars ekos raspberry pi cross platform observatory"),
    # --- 26 ---
    ("PHD2 handles guiding on every rig; the multi-star guiding feature with the ASI120MM Mini on the OAG dropped total RMS below 0.5 arcsec on the TOA-150 under good seeing.", "architecture", "personal", False,
     [("PHD2", "tool"), ("multi-star guiding", "method"), ("ASI120MM Mini", "technology"), ("OAG", "technology"), ("TOA-150", "technology"), ("arcsec", "concept")],
     [("PHD2", "TOA-150", "APPLIES_TO")],
     "which guiding software and OAG camera combo dropped RMS below half an arcsecond on the premium refractor",
     "phd2 multi star guide asi120mm mini oag toa 150 arcsec rms seeing"),
    # --- 27 ---
    ("An OAG replaces the guide scope on every Schmidt-Cassegrain imaging run; mirror flop on the C11 was drifting guide stars in the scope even while the primary subject dithered cleanly.", "problem", "personal", False,
     [("OAG", "technology"), ("guide scope", "technology"), ("Schmidt-Cassegrain", "technology"), ("C11", "technology"), ("mirror flop", "pattern")],
     [("OAG", "guide scope", "REPLACES")],
     "which guiding problem on the Schmidt-Cassegrain drove the move from a guide scope to an OAG",
     "oag guide scope schmidt cassegrain c11 mirror flop drift guide"),
    # --- 28 ---
    ("Shot M42 Orion Nebula last January at f/5 on the FSQ-106; the core-dodge HDR blend of 30-second and five-minute subs finally held the Trapezium without blowing out the Running Man.", "milestone", "personal", False,
     [("M42", "place"), ("Orion Nebula", "place"), ("FSQ-106", "technology"), ("HDR blend", "method"), ("Trapezium", "place"), ("Running Man", "place")],
     [("FSQ-106", "M42", "APPLIES_TO")],
     "which HDR technique on the wide-field apo finally held the Trapezium core while keeping the Running Man",
     "m42 orion nebula fsq 106 hdr blend trapezium running man core dodge"),
    # --- 29 ---
    ("Helix Nebula NGC 7293 from two nights in September under Bortle 3 skies; the ASI2600MM Pro with Antlia 3nm Ha and OIII pulled the halo structure that years of OSC never resolved.", "milestone", "personal", False,
     [("Helix Nebula", "place"), ("NGC 7293", "place"), ("Bortle 3", "config"), ("ASI2600MM Pro", "technology"), ("Antlia", "technology"), ("Ha", "config"), ("OIII", "config"), ("OSC", "technology")],
     [("ASI2600MM Pro", "Helix Nebula", "APPLIES_TO")],
     "which two-night Bortle 3 session and camera combo finally resolved the Helix halo",
     "helix nebula ngc 7293 bortle 3 asi2600mm pro antlia ha oiii halo"),
    # --- 30 ---
    ("Eagle Nebula M16 Pillars of Creation bicolour Ha-OIII mapped to the Hubble palette is the desktop wallpaper; the C11 reach at f/7 with a reducer held the pillars in focus corner to corner.", "milestone", "personal", False,
     [("Eagle Nebula", "place"), ("M16", "place"), ("Pillars of Creation", "place"), ("Hubble palette", "method"), ("C11", "technology"), ("reducer", "technology")],
     [("C11", "Eagle Nebula", "APPLIES_TO")],
     "which bicolour palette and optical setup let the eleven-inch hold the Pillars sharp across the frame",
     "eagle nebula m16 pillars creation hubble palette c11 reducer bicolour"),
    # --- 31 ---
    ("Dumbbell Nebula M27 in SHO from the Cherry Springs trip last August; the SII layer added the outer halo structure that the OSC-only version was completely missing.", "milestone", "personal", False,
     [("Dumbbell Nebula", "place"), ("M27", "place"), ("SHO", "method"), ("Cherry Springs", "place"), ("SII", "config"), ("OSC", "technology")],
     [("SHO", "OSC", "IMPROVES_ON")],
     "which narrowband palette on which dark-sky trip revealed the Dumbbell's outer halo that OSC missed",
     "dumbbell nebula m27 sho cherry springs sii outer halo palette"),
    # --- 32 ---
    ("Veil Nebula mosaic ran six panels across two weekends; the FSQ-106 field barely wraps the Eastern Veil and Western Veil regions together and the mosaic overlap came in at exactly 15 percent.", "milestone", "personal", False,
     [("Veil Nebula", "place"), ("FSQ-106", "technology"), ("Eastern Veil", "place"), ("Western Veil", "place"), ("mosaic", "method")],
     [("FSQ-106", "Veil Nebula", "APPLIES_TO")],
     "how many panels did the Veil mosaic need and what overlap was used to join them",
     "veil nebula mosaic fsq 106 eastern western overlap panel weekend"),
    # --- 33 ---
    ("Visual-only session with the Televue Ethos 21mm on the C11 at Bortle 3 last October; the 100-degree apparent field framed the entire Veil in one pan and ended the urge to buy a bigger eyepiece.", "fact", "personal", False,
     [("Televue Ethos 21mm", "technology"), ("C11", "technology"), ("Bortle 3", "config"), ("100-degree", "concept"), ("Veil", "place")],
     [("Televue Ethos 21mm", "Veil", "APPLIES_TO")],
     "which visual eyepiece framed the entire Veil in one pan on the eleven-inch under Bortle 3 skies",
     "televue ethos 21mm c11 bortle 3 100 degree apparent field veil"),
    # --- 34 ---
    ("The Delos 10mm stays in the eyepiece case for planetary visual; 72-degree field with the long eye relief means glasses stay on during a two-hour Jupiter watch without neck strain.", "preference", "personal", False,
     [("Delos 10mm", "technology"), ("Jupiter", "place")],
     [],
     "which eyepiece stays in the case for planetary visual sessions and what ergonomic feature keeps it there",
     "delos 10mm jupiter planetary eye relief glasses 72 degree field"),
    # --- 35 ---
    ("Prefer the Nagler 9mm Type 6 over the newer Ethos 8mm for lunar terminator work; slightly more contrast on the flat-field eyepiece projection beats the wider apparent field at the Moon.", "preference", "personal", False,
     [("Nagler 9mm", "technology"), ("Type 6", "technology"), ("Ethos 8mm", "technology"), ("Moon", "place")],
     [("Nagler 9mm", "Ethos 8mm", "PREFERS")],
     "which Nagler wins against the newer Ethos for lunar terminator visual and why",
     "nagler 9mm type 6 ethos 8mm moon terminator lunar contrast"),
    # --- 36 ---
    ("Baader Hyperion 24mm is the loaner eyepiece I hand to visitors at outreach nights; forgiving eye position and no click-stop hassles makes the first look easy for kids.", "fact", "personal", False,
     [("Baader Hyperion 24mm", "technology"), ("outreach nights", "event")],
     [],
     "which eyepiece gets handed to visitors on outreach nights and why is it the right loaner",
     "baader hyperion 24mm outreach loan visitor kid eye position click"),
    # --- 37 ---
    ("Retired the Newtonian after coma-corrector alignment ate an entire imaging evening at Dark Sky Park; the Ritchey-Chrétien on the CGX-L was sharp in minutes with no secondary collimation dance.", "decision", "personal", False,
     [("Newtonian", "technology"), ("coma-corrector", "technology"), ("Dark Sky Park", "place"), ("Ritchey-Chrétien", "technology"), ("CGX-L", "technology")],
     [("Ritchey-Chrétien", "Newtonian", "REPLACES")],
     "which reflector replaced the Newtonian after a coma-corrector collimation disaster at the Dark Sky Park",
     "newtonian coma corrector dark sky park ritchey chretien cgx l"),
    # --- 38 ---
    ("The observatory pier is bolted into a one-metre concrete footing I poured two summers ago; cold-climate frost heave on the wood pad was spoiling polar alignment by second-night margins.", "architecture", "personal", False,
     [("observatory pier", "technology"), ("concrete footing", "technology"), ("polar alignment", "method"), ("wood pad", "technology")],
     [("concrete footing", "wood pad", "REPLACES")],
     "which pier foundation replaced the wood pad after polar alignment drifted overnight from frost heave",
     "observatory pier concrete footing wood pad frost heave polar align"),
    # --- 39 ---
    ("La Palma travel trip scheduled for next April at the Roque de los Muchachos visitor site; packing list has the CEM70, FSQ-106, ASI533MC Pro, and a single carry-on bag of cables.", "reference", "personal", False,
     [("La Palma", "place"), ("Roque de los Muchachos", "place"), ("CEM70", "technology"), ("FSQ-106", "technology"), ("ASI533MC Pro", "technology")],
     [("CEM70", "La Palma", "APPLIES_TO")],
     "which travel-trip packing list pairs with which site on the La Palma astronomy trip",
     "la palma roque muchachos cem70 fsq 106 asi533 travel carry on"),
    # --- 40 ---
    ("Atacama ELQUI Domos trip in July lined up after the Cherry Springs practice run; the Bortle 1 sky there should make the southern Ha regions visible that never clear Bortle 5 back home.", "milestone", "personal", False,
     [("Atacama", "place"), ("ELQUI Domos", "place"), ("Cherry Springs", "place"), ("Bortle 1", "config"), ("Bortle 5", "config"), ("Ha", "config")],
     [("Atacama", "Cherry Springs", "IMPROVES_ON")],
     "which Atacama dark-sky lodge and Bortle class stands to reveal southern Ha regions beyond home skies",
     "atacama elqui domos cherry springs bortle 1 5 ha southern hemisphere"),
    # --- 41 ---
    ("Messier Marathon 2025 attempt ended at 104 of 110 objects when M30 rose in the dawn glow; the 2026 plan moves the site thirty miles west to cut the eastern horizon trees.", "reference", "personal", False,
     [("Messier Marathon", "event"), ("M30", "place"), ("dawn glow", "pattern")],
     [],
     "which object ended the last Messier Marathon attempt and what site change is planned for next year",
     "messier marathon m30 dawn glow 104 110 objects eastern horizon"),
    # --- 42 ---
    ("The Summer Triangle asterism is the naked-eye anchor I teach at outreach nights; Vega, Deneb, and Altair make it trivial to point a new observer at the Veil, Dumbbell, and North America in one pan.", "reference", "personal", False,
     [("Summer Triangle", "place"), ("Vega", "place"), ("Deneb", "place"), ("Altair", "place"), ("Veil", "place"), ("Dumbbell", "place"), ("North America", "place")],
     [],
     "which naked-eye asterism anchors the outreach tour of summer deep-sky objects and what three stars define it",
     "summer triangle vega deneb altair veil dumbbell north america outreach"),
    # --- 43. noise ---
    ("The club coffee pot in the warm-up room started making a weird gurgle sound halfway through last Friday's session and nobody has the nerve to diagnose it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Bortle scale at home sits at 5 per the light-pollution-map overlay; the neighbouring sports field floodlights drop it to 6 on Friday game nights from September through May.", "reference", "personal", False,
     [("Bortle scale", "concept"), ("light-pollution-map", "tool"), ("sports field", "place")],
     [],
     "which Bortle class sits at the home site and what weekly event degrades it one rung",
     "bortle scale 5 6 light pollution map sports field floodlight friday"),
    # --- 45 ---
    ("Dew heaters on the TOA-150 objective and the C11 corrector plate are driven by a Pegasus Pocket Powerbox; PWM control from NINA means the heater only fires when the humidity sensor says it needs to.", "architecture", "personal", False,
     [("TOA-150", "technology"), ("C11", "technology"), ("Pegasus Pocket Powerbox", "technology"), ("PWM", "protocol"), ("NINA", "tool"), ("humidity sensor", "technology")],
     [],
     "which power controller drives the dew heaters and what logic keeps them from running unnecessarily",
     "pegasus pocket powerbox dew heater toa 150 c11 pwm nina humidity"),
    # --- 46 ---
    ("Prefer collimating the Schmidt-Cassegrain on a defocused star over an artificial collimation source; temperature-matched optics always show up differently under a real seeing column than they do in the living room.", "preference", "personal", False,
     [("Schmidt-Cassegrain", "technology"), ("defocused star", "method"), ("artificial collimation source", "technology"), ("seeing column", "pattern")],
     [("defocused star", "artificial collimation source", "PREFERS")],
     "which Schmidt-Cassegrain collimation method beats the indoor artificial source and why",
     "schmidt cassegrain collimate defocused star artificial source seeing"),
    # --- 47 ---
    ("Sub exposure length on the ASI2600MM Pro locked at 300 seconds for narrowband after a SharpCap sky-background calculation at Bortle 3; longer just buries signal in read noise stack margin.", "decision", "personal", False,
     [("ASI2600MM Pro", "technology"), ("SharpCap", "tool"), ("Bortle 3", "config"), ("read noise", "concept"), ("narrowband", "config")],
     [],
     "which sub exposure length settled for narrowband at Bortle 3 and what tool computed the optimum",
     "asi2600mm pro sharpcap bortle 3 sub exposure 300 narrowband read noise"),
    # --- 48 ---
    ("Flat frames on the ASI6200MM Pro are taken with an Alnitak Flip-Flat at dusk; reusing the library across a week is fine because the C11 corrector holds orientation between nights on the CGX-L.", "preference", "personal", False,
     [("ASI6200MM Pro", "technology"), ("Alnitak Flip-Flat", "technology"), ("C11", "technology"), ("CGX-L", "technology"), ("corrector", "technology")],
     [],
     "which flat panel lives on the imaging rig and when is it safe to reuse flats across multiple nights",
     "alnitak flip flat asi6200mm pro c11 corrector cgx l dusk reuse"),
    # --- 49 ---
    ("The observatory roll-off roof jammed on the east rail after an ice storm; a teflon-strip retrofit on both rails replaced the stock nylon wheels and the roof has opened cleanly every session since.", "decision", "personal", False,
     [("roll-off roof", "technology"), ("ice storm", "event"), ("teflon-strip", "pattern"), ("nylon wheels", "technology")],
     [("teflon-strip", "nylon wheels", "REPLACES")],
     "which observatory-roof retrofit replaced the stock wheels after an ice-storm jam",
     "roll off roof ice storm teflon strip nylon wheel east rail jam"),
    # --- 50 ---
    ("The imaging log lives in a SQLite file with columns for target, filter, sub count, sub length, seeing, and transparency; a Grafana dashboard on the observatory Raspberry Pi plots integration hours per target per month.", "architecture", "personal", False,
     [("SQLite", "database"), ("Grafana", "tool"), ("Raspberry Pi", "platform"), ("imaging log", "concept"), ("integration hours", "concept")],
     [],
     "which stack stores and visualises the imaging log and what metric does the Grafana dashboard plot",
     "sqlite grafana raspberry pi imaging log integration hours target filter"),
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
