"""One-off emitter for shared-base batch-208 — personal domain (cycling: road, gravel, MTB, bikepacking, groupsets, wheelsets, power meters, races, bikepacking rigs).

Writes 50 rows to data/v2/shared/batch_208.tmp.jsonl with ids shared-10351..10400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_208.tmp.jsonl"
ID_OFFSET = 10350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Committed to a titanium gravel frame as the long-haul daily after two seasons on aluminum; the ride quality on washboard fire roads is night-and-day and the frame will outlive three groupsets.", "decision", "personal", False,
     [("titanium", "concept"), ("aluminum", "concept"), ("gravel frame", "tool")],
     [("titanium", "aluminum", "REPLACES")],
     "which frame material won the long-haul gravel slot and why was aluminum retired",
     "titanium aluminum gravel frame washboard fire road daily long haul"),
    # --- 2. architecture ---
    ("The stable is laid out by purpose: a carbon road bike for Sunday group rides, a steel all-road for commuting and winter, a titanium gravel rig for adventure, and a full-suspension MTB for the local trail network.", "architecture", "personal", False,
     [("carbon", "concept"), ("steel", "concept"), ("titanium", "concept"), ("road bike", "tool"), ("all-road", "tool"), ("gravel rig", "tool"), ("MTB", "tool")],
     [("carbon", "road bike", "APPLIES_TO"), ("steel", "all-road", "APPLIES_TO"), ("titanium", "gravel rig", "APPLIES_TO")],
     "how is the bike stable partitioned across road, gravel, and trail use cases",
     "carbon steel titanium road gravel mtb stable partition commute winter"),
    # --- 3. milestone ---
    ("Finished Unbound Gravel 200 in 13 hours 42 minutes on the titanium rig; the Pirelli P Zero tubeless setup held air through every flint section and not a single sealant top-up was needed at aid.", "milestone", "personal", False,
     [("Unbound Gravel 200", "event"), ("Pirelli P Zero", "tool"), ("titanium", "concept")],
     [("Pirelli P Zero", "Unbound Gravel 200", "APPLIES_TO")],
     "which gravel race did the titanium rig finish in under 14 hours and which tyre carried the day",
     "unbound gravel 200 pirelli p zero titanium tubeless flint 13 hour"),
    # --- 4. fact ---
    ("Shimano Dura-Ace Di2 R9200 runs a semi-wireless setup with a central battery in the seatpost, while SRAM Red AXS goes fully wireless with per-derailleur batteries that swap in seconds trailside.", "fact", "personal", False,
     [("Shimano Dura-Ace Di2 R9200", "tool"), ("SRAM Red AXS", "tool")],
     [],
     "how do the top-tier electronic groupsets from Shimano and SRAM differ on wiring and battery architecture",
     "shimano dura ace di2 r9200 sram red axs wireless battery seatpost"),
    # --- 5. reference ---
    ("Bike-fit notes all trace back to Steve Hogg's three-point contact framework in The Bike Fit Book; saddle height landed on 74.2 cm over bottom bracket and setback came in at 6 cm behind the BB centreline.", "reference", "personal", False,
     [("Steve Hogg", "person"), ("The Bike Fit Book", "publication"), ("saddle height", "concept"), ("setback", "concept")],
     [("The Bike Fit Book", "Steve Hogg", "AUTHORED_BY")],
     "which bike-fit reference and author anchor the current saddle height and setback numbers",
     "steve hogg bike fit book saddle height setback three point contact"),
    # --- 6. decision ---
    ("Settled on 1x12 GRX for the gravel bike after a full season on 2x; the front derailleur kept dropping the chain under power on rough climbs and a 10-51 cassette covered every useful gear anyway.", "decision", "personal", False,
     [("1x12", "concept"), ("GRX", "tool"), ("2x", "concept"), ("10-51 cassette", "tool")],
     [("1x12", "2x", "REPLACES")],
     "which drivetrain layout won on the gravel bike after the 2x setup dropped chains on climbs",
     "1x12 grx 2x front derailleur chain drop 10-51 cassette gravel"),
    # --- 7. architecture ---
    ("Hydraulic disc brakes on every bike in the stable: Shimano on the road and gravel rigs, SRAM on the MTB; the kitchen has a dedicated mini-bleed station with a Shimano funnel cup and SRAM Bleeding Edge syringes side by side.", "architecture", "personal", False,
     [("Hydraulic disc brakes", "tool"), ("Shimano", "organization"), ("SRAM", "organization"), ("mini-bleed station", "place"), ("Bleeding Edge", "tool")],
     [("Hydraulic disc brakes", "Shimano", "USES"), ("Hydraulic disc brakes", "SRAM", "USES")],
     "how is the home bleed setup organised across the two brake ecosystems in the stable",
     "hydraulic disc brake shimano sram bleed station funnel bleeding edge"),
    # --- 8. preference ---
    ("Prefer Shimano Ultegra Di2 over SRAM Force AXS on the road bike; the shift feel is crisper under load and the battery in the seatpost never runs out mid-ride the way the per-derailleur cells used to surprise me.", "preference", "personal", False,
     [("Shimano Ultegra Di2", "tool"), ("SRAM Force AXS", "tool")],
     [("Shimano Ultegra Di2", "SRAM Force AXS", "PREFERS")],
     "which mid-tier electronic groupset feels better on the road bike and which pain point sealed the call",
     "shimano ultegra di2 sram force axs shift feel battery seatpost"),
    # --- 9. milestone ---
    ("First sub-hour flat 40 km time trial came on the Zipp 303 Firecrest wheelset with 28 mm GP5000 S TR tubeless; splits were consistent and the deep front behaved under crosswind better than expected.", "milestone", "personal", False,
     [("Zipp 303 Firecrest", "tool"), ("GP5000 S TR", "tool"), ("40 km time trial", "event")],
     [("GP5000 S TR", "Zipp 303 Firecrest", "APPLIES_TO")],
     "which wheelset and tyre combo delivered the first sub-hour 40 km time trial",
     "zipp 303 firecrest gp5000 s tr 40 km time trial sub hour tubeless"),
    # --- 10. noise ---
    ("The garage cat has claimed the wool jersey from the laundry pile and now sleeps on it as a permanent throne.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Chose the Favero Assioma Duo pedal power meter over a Quarq spider for the road bike; moving it between the road and gravel bikes in under a minute matters more than the spider's slightly tighter accuracy number.", "decision", "personal", False,
     [("Favero Assioma Duo", "tool"), ("Quarq", "tool")],
     [("Favero Assioma Duo", "Quarq", "PREFERS")],
     "which power meter won for portability between bikes and what was the trade against a crank spider option",
     "favero assioma duo quarq pedal power meter portability accuracy"),
    # --- 12. fact ---
    ("Tubeless setup on the Enve SES 4.5 wheels uses 60 ml of Orange Seal per tyre with the GP5000 S TR at 26 mm actual width; the beads seat cleanly with a floor pump and an Airshot charger bumps them on stubborn days.", "fact", "personal", False,
     [("Enve SES 4.5", "tool"), ("Orange Seal", "tool"), ("GP5000 S TR", "tool"), ("Airshot", "tool")],
     [("GP5000 S TR", "Enve SES 4.5", "APPLIES_TO")],
     "what tubeless setup parameters work on the Enve wheelset with GP5000 tyres at home",
     "enve ses 4.5 orange seal gp5000 airshot tubeless bead seat pump"),
    # --- 13. decision ---
    ("Indoor training rig is built around a Wahoo Kickr V6 with a Kickr Climb for grade simulation; Zwift runs on a dedicated Apple TV while TrainerRoad drives the structured workouts on a tablet alongside.", "decision", "personal", False,
     [("Wahoo Kickr V6", "tool"), ("Kickr Climb", "tool"), ("Zwift", "tool"), ("Apple TV", "tool"), ("TrainerRoad", "tool")],
     [("Zwift", "Apple TV", "DEPLOYED_ON")],
     "how is the pain cave wired across smart trainer, grade simulator, and two separate training platforms",
     "wahoo kickr v6 climb zwift apple tv trainerroad indoor pain cave"),
    # --- 14. decision ---
    ("Picked TrainerRoad over Zwift for structured training blocks; the adaptive training plan actually moves workouts around when life gets in the way and the pure ERG focus keeps the head down on intervals.", "decision", "personal", False,
     [("TrainerRoad", "tool"), ("Zwift", "tool"), ("adaptive training", "method"), ("ERG", "concept")],
     [("TrainerRoad", "Zwift", "PREFERS")],
     "which training platform wins for structured blocks and which feature sealed the call over the virtual-world option",
     "trainerroad zwift adaptive training erg mode structured interval"),
    # --- 15. reference ---
    ("The training schedule draws from Joe Friel's The Cyclist's Training Bible; the annual training plan template in chapter six got adapted into a spreadsheet with weekly TSS targets and recovery weeks every fourth block.", "reference", "personal", False,
     [("Joe Friel", "person"), ("The Cyclist's Training Bible", "publication"), ("TSS", "concept")],
     [("The Cyclist's Training Bible", "Joe Friel", "AUTHORED_BY")],
     "which training book anchors the annual plan template and what weekly metric drives the structure",
     "joe friel cyclist training bible annual plan tss weekly recovery"),
    # --- 16. problem ---
    ("Creak on the carbon road bike traced back to the SRAM DUB bottom bracket after four wet rides in a row; a full strip, regrease with Dumonde Tech, and reinstall with the correct preload silenced it for the rest of the season.", "problem", "personal", False,
     [("SRAM DUB", "tool"), ("Dumonde Tech", "tool"), ("bottom bracket", "tool")],
     [("Dumonde Tech", "SRAM DUB", "APPLIES_TO")],
     "what was the source of the wet-weather creak on the carbon road bike and which service fixed it",
     "sram dub bottom bracket creak dumonde tech grease preload wet"),
    # --- 17. architecture ---
    ("Bikepacking load layout on the Salsa Cutthroat splits weight by axis: an Apidura frame pack for tools and food, a Revelate Terrapin seat pack for clothing, and a Tailfin AeroPack for the heavy camp kit behind the saddle.", "architecture", "personal", False,
     [("Salsa Cutthroat", "tool"), ("Apidura", "organization"), ("Revelate Terrapin", "tool"), ("Tailfin AeroPack", "tool")],
     [("Apidura", "Salsa Cutthroat", "APPLIES_TO"), ("Revelate Terrapin", "Salsa Cutthroat", "APPLIES_TO"), ("Tailfin AeroPack", "Salsa Cutthroat", "APPLIES_TO")],
     "how is bikepacking weight distributed across frame, seat pack, and rear rack on the Cutthroat",
     "salsa cutthroat apidura frame revelate terrapin tailfin aeropack load"),
    # --- 18. milestone ---
    ("Completed the Colorado Trail Race on a Tumbleweed Prospector in 7 days 18 hours; the 3.0 inch Maxxis Chronicle tyres floated over Kokomo's baby-heads and the Rohloff hub shifted flawlessly under load across every pass.", "milestone", "personal", False,
     [("Colorado Trail Race", "event"), ("Tumbleweed Prospector", "tool"), ("Maxxis Chronicle", "tool"), ("Rohloff", "tool")],
     [("Maxxis Chronicle", "Tumbleweed Prospector", "APPLIES_TO")],
     "which bikepacking rig and hub finished the Colorado Trail Race in under eight days",
     "colorado trail race tumbleweed prospector maxxis chronicle rohloff"),
    # --- 19. decision ---
    ("Went with a Roval Alpinist CLX II wheelset for the climbing bike over a Zipp 202; the 1248 g claimed weight and shallower profile made more sense for a dedicated hill-repeat bike than the Zipp's slightly better aero number.", "decision", "personal", False,
     [("Roval Alpinist CLX II", "tool"), ("Zipp 202", "tool")],
     [("Roval Alpinist CLX II", "Zipp 202", "PREFERS")],
     "which climbing wheelset won over the alternative Zipp and what weight number tipped the call",
     "roval alpinist clx ii zipp 202 climbing wheelset weight 1248"),
    # --- 20. fact ---
    ("The Garmin Rally RK200 pedals swap the cleat body to switch between road Look Keo and Shimano SPD-SL without changing the power-meter spindle; the trick keeps one power meter working across multiple bikes.", "fact", "personal", False,
     [("Garmin Rally RK200", "tool"), ("Look Keo", "tool"), ("Shimano SPD-SL", "tool")],
     [("Garmin Rally RK200", "Look Keo", "USES"), ("Garmin Rally RK200", "Shimano SPD-SL", "USES")],
     "which pedal power meter supports swapping cleat bodies between two road standards on one spindle",
     "garmin rally rk200 look keo shimano spd sl cleat swap spindle"),
    # --- 21. architecture ---
    ("Route planning runs through Komoot for gravel, RideWithGPS for road group rides, and Gaia GPS for the backcountry bikepacking routes; the Wahoo Elemnt Roam syncs all three via cloud so the head unit just shows today's track.", "architecture", "personal", False,
     [("Komoot", "tool"), ("RideWithGPS", "tool"), ("Gaia GPS", "tool"), ("Wahoo Elemnt Roam", "tool")],
     [("Komoot", "Wahoo Elemnt Roam", "COMMUNICATES_WITH"), ("RideWithGPS", "Wahoo Elemnt Roam", "COMMUNICATES_WITH"), ("Gaia GPS", "Wahoo Elemnt Roam", "COMMUNICATES_WITH")],
     "which planning apps feed the head unit and how are they split across ride types",
     "komoot ridewithgps gaia gps wahoo elemnt roam route plan sync"),
    # --- 22. decision ---
    ("Campagnolo Super Record Wireless lost the shootout against Shimano Dura-Ace Di2 R9200 for the special-occasion road build; the Campy aesthetic is unmatched but the ergonomics under heavy hoods-braking felt less secure to these hands.", "decision", "personal", False,
     [("Campagnolo Super Record Wireless", "tool"), ("Shimano Dura-Ace Di2 R9200", "tool")],
     [("Shimano Dura-Ace Di2 R9200", "Campagnolo Super Record Wireless", "PREFERS")],
     "which top-tier groupset took the flagship build and what ergonomics concern pushed Campy out",
     "campagnolo super record wireless shimano dura ace di2 r9200 hood brake"),
    # --- 23. reference ---
    ("Wheel-building notes come from Jobst Brandt's The Bicycle Wheel; the spoke tension target of 110 kgf on the rear drive-side and 70 kgf non-drive came straight out of that text and the Park TM-1 confirms within a kilo every build.", "reference", "personal", False,
     [("Jobst Brandt", "person"), ("The Bicycle Wheel", "publication"), ("Park TM-1", "tool")],
     [("The Bicycle Wheel", "Jobst Brandt", "AUTHORED_BY")],
     "which wheelbuilding text and tool anchor the spoke tension targets at home",
     "jobst brandt bicycle wheel park tm-1 spoke tension 110 kgf drive"),
    # --- 24. milestone ---
    ("Rode the SBT GRVL black course in 9 hours 3 minutes on the gravel rig; the Schwalbe G-One R in 45 mm held up across every cattle grate and the Kings Canyon descent felt controlled despite the rough washboard.", "milestone", "personal", False,
     [("SBT GRVL", "event"), ("Schwalbe G-One R", "tool"), ("Kings Canyon", "place")],
     [("Schwalbe G-One R", "SBT GRVL", "APPLIES_TO")],
     "which gravel race and tyre combo produced the sub-ten-hour black course finish",
     "sbt grvl black course schwalbe g one r 45 mm kings canyon"),
    # --- 25. fact ---
    ("Shimano 105 Di2 R7150 drops wireless shifting, semi-wireless cockpit wiring, and 12-speed cassettes down to the mid-tier price point; the gap to Ultegra is mostly weight and finish rather than functionality.", "fact", "personal", False,
     [("Shimano 105 Di2 R7150", "tool"), ("Ultegra", "tool")],
     [],
     "what functional gap remains between 105 Di2 and Ultegra now that 105 went electronic",
     "shimano 105 di2 r7150 ultegra 12 speed wireless mid tier weight"),
    # --- 26. architecture ---
    ("The bike-fit process goes bike, rider, pedals in that order: pedal stance width set first with Wellgo shims, cleat fore-aft and rotation on the Speedplays second, then saddle height and setback, then bar drop and reach last against video captured in MyVeloFit.", "architecture", "personal", False,
     [("Wellgo", "organization"), ("Speedplay", "tool"), ("MyVeloFit", "tool"), ("bike-fit", "method")],
     [("MyVeloFit", "bike-fit", "APPLIES_TO")],
     "how is the bike-fit sequence ordered from pedal stance up to bar reach at home",
     "bike fit wellgo speedplay cleat myvelofit stance saddle bar drop"),
    # --- 27. problem ---
    ("The Quarq DZero started reading 8 percent high after a battery swap; manual zero-offset had drifted because the battery door gasket was pinched, and a clean reseat with fresh silicone grease got it calibrating within 2 watts of the Assioma reference again.", "problem", "personal", False,
     [("Quarq DZero", "tool"), ("Assioma", "tool"), ("silicone grease", "tool")],
     [("silicone grease", "Quarq DZero", "FIXES")],
     "what caused the Quarq power meter drift after a battery swap and which fix restored agreement with the reference meter",
     "quarq dzero assioma battery gasket silicone grease zero offset drift"),
    # --- 28. decision ---
    ("Picked Rouvy over FulGaz for the real-world route library; the augmented-reality avatar placement on actual road footage beats a pure video playback, and the Alpe d'Huez climb route matched Strava elevation within a handful of metres.", "decision", "personal", False,
     [("Rouvy", "tool"), ("FulGaz", "tool"), ("Alpe d'Huez", "place"), ("Strava", "tool")],
     [("Rouvy", "FulGaz", "PREFERS")],
     "which real-road training platform won over the alternative and what route validated the choice",
     "rouvy fulgaz augmented reality alpe d huez strava elevation climb"),
    # --- 29. preference ---
    ("Chain wear rotation uses three chains in sequence on the same cassette: swap every 500 km, measure with a Park CC-3.2, and retire a chain at 0.5 percent; the cassette lasts the full life of a set of three chains that way.", "preference", "personal", False,
     [("Park CC-3.2", "tool"), ("cassette", "tool"), ("chain", "tool")],
     [("Park CC-3.2", "chain", "APPLIES_TO")],
     "how does the three-chain rotation stretch cassette life and which gauge enforces the retirement rule",
     "park cc-3.2 chain cassette rotation 500 km 0.5 percent wear"),
    # --- 30. milestone ---
    ("Watched the Tour de France stage 20 time trial live at the roadside in 2024 and pinned the Paris-Roubaix velodrome visit to the same trip; both Monuments bucket-list items in eleven days of travel felt surreal.", "milestone", "personal", False,
     [("Tour de France", "event"), ("Paris-Roubaix", "event"), ("velodrome", "place")],
     [("Tour de France", "Paris-Roubaix", "RELATED_TO")],
     "which two pro-cycling events got paired into a single trip and which venue anchored the Monument visit",
     "tour de france stage 20 time trial paris roubaix velodrome 2024"),
    # --- 31. fact ---
    ("Il Lombardia closes the Monument calendar in October with the Muro di Sormano as its defining climb; the 1700 metre wall averages 17 percent with pitches at 25 and the numbers painted on the tarmac count the gradient not the distance.", "fact", "personal", False,
     [("Il Lombardia", "event"), ("Muro di Sormano", "place")],
     [("Muro di Sormano", "Il Lombardia", "APPLIES_TO")],
     "which Monument closes the season and which signature climb defines it",
     "il lombardia muro di sormano october monument 17 percent climb"),
    # --- 32. decision ---
    ("Replaced the Surly Ogre with a Tumbleweed Prospector for dirt-road touring; the Rohloff-ready dropouts and bigger tyre clearance won out once the tour profile shifted toward singletrack segments on the Great Divide.", "decision", "personal", False,
     [("Surly Ogre", "tool"), ("Tumbleweed Prospector", "tool"), ("Rohloff", "tool"), ("Great Divide", "place")],
     [("Tumbleweed Prospector", "Surly Ogre", "REPLACES")],
     "which bikepacking frame replaced the Surly Ogre and which route profile justified the switch",
     "surly ogre tumbleweed prospector rohloff great divide singletrack"),
    # --- 33. preference ---
    ("Prefer a 4iiii Precision left-side power meter on the winter bike over a full dual-sided setup; the cost drops by more than half and the single-sided number is honest enough for zone-based training in bad weather.", "preference", "personal", False,
     [("4iiii Precision", "tool"), ("dual-sided", "concept"), ("winter bike", "tool")],
     [("4iiii Precision", "dual-sided", "PREFERS")],
     "which power meter tier fits the winter bike and what compromise makes the single-sided unit acceptable",
     "4iiii precision dual sided power meter winter bike zone training"),
    # --- 34. architecture ---
    ("Nutrition on long gravel events stacks Maurten gels at 30 minute intervals with a bottle of SIS Beta Fuel and a backup drop of Skratch chews in the top tube bag; total target is 90 grams of carbs per hour from about mile forty onward.", "architecture", "personal", False,
     [("Maurten", "organization"), ("SIS Beta Fuel", "tool"), ("Skratch", "organization"), ("top tube bag", "tool")],
     [("Maurten", "SIS Beta Fuel", "RELATED_TO"), ("Skratch", "top tube bag", "APPLIES_TO")],
     "how is long-gravel fueling layered across gel, drink mix, and chews to hit 90 grams of carbs per hour",
     "maurten sis beta fuel skratch chew 90 gram carb hour top tube"),
    # --- 35. milestone ---
    ("Watched the Giro d'Italia finish on top of the Passo dello Stelvio in 2025; the snow banks above the road were taller than the team cars and the crowds at Tornante 48 were three deep the whole climb.", "milestone", "personal", False,
     [("Giro d'Italia", "event"), ("Passo dello Stelvio", "place"), ("Tornante 48", "place")],
     [("Giro d'Italia", "Passo dello Stelvio", "LOCATED_IN")],
     "which Grand Tour summit finish was witnessed in person in 2025 and what defined the scene at Tornante 48",
     "giro d italia passo stelvio tornante 48 2025 snow bank summit"),
    # --- 36. decision ---
    ("Picked The Rift in Iceland over Badlands in Spain as the 2026 overseas gravel target; the volcanic terrain and Hekla backdrop won against Andalucia's heat because summer training has already been heat-focused for months.", "decision", "personal", False,
     [("The Rift", "event"), ("Badlands", "event"), ("Iceland", "place"), ("Hekla", "place")],
     [("The Rift", "Badlands", "PREFERS"), ("The Rift", "Iceland", "LOCATED_IN")],
     "which 2026 overseas gravel race won the slot and why did the Spanish alternative lose out",
     "the rift iceland badlands spain hekla volcanic 2026 overseas gravel"),
    # --- 37. reference ---
    ("The bikepacking ethos draws from Ryan Le Garrec's Bikepacking Scotland and Cass Gilbert's writing on Bikepacking.com; the light-kit philosophy of under 8 kg of gear including water comes from that body of work and holds up across four tours.", "reference", "personal", False,
     [("Ryan Le Garrec", "person"), ("Bikepacking Scotland", "publication"), ("Cass Gilbert", "person"), ("Bikepacking.com", "publication")],
     [("Bikepacking Scotland", "Ryan Le Garrec", "AUTHORED_BY"), ("Bikepacking.com", "Cass Gilbert", "AUTHORED_BY")],
     "which writers and publications anchor the light-kit bikepacking philosophy at under 8 kg",
     "ryan le garrec bikepacking scotland cass gilbert light kit 8 kg"),
    # --- 38. fact ---
    ("Road tubeless tyres prefer hooked rims with a tight bead-seat diameter tolerance; the Zipp 303 Firecrest went hookless and caps pressure at 72 psi, while Enve SES keeps hooks and allows a wider pressure window for heavier riders.", "fact", "personal", False,
     [("Zipp 303 Firecrest", "tool"), ("Enve SES", "tool"), ("hookless", "concept"), ("hooked", "concept")],
     [("Zipp 303 Firecrest", "hookless", "USES"), ("Enve SES", "hooked", "USES")],
     "how do the Zipp and Enve rim approaches differ on hook design and what pressure ceiling follows",
     "zipp 303 firecrest enve ses hookless hooked 72 psi tubeless pressure"),
    # --- 39. architecture ---
    ("The workshop is organised as three benches: a dedicated truing stand with a Park TS-2.2 and tensiometer, a wash bay with a Park PCS-10.3 repair stand, and a parts wall of drawers labelled by groupset generation for Dura-Ace, Ultegra, and 105.", "architecture", "personal", False,
     [("Park TS-2.2", "tool"), ("Park PCS-10.3", "tool"), ("Dura-Ace", "tool"), ("Ultegra", "tool"), ("105", "tool"), ("workshop", "place")],
     [("Park TS-2.2", "workshop", "LOCATED_IN"), ("Park PCS-10.3", "workshop", "LOCATED_IN")],
     "how is the home bike workshop partitioned across truing, wash, and parts storage",
     "park ts 2.2 pcs 10.3 truing wash bay dura ace ultegra 105 drawer"),
    # --- 40. decision ---
    ("Ran the Apidura Expedition full frame pack on the Cutthroat rather than a Revelate Ranger for the Trans-Ezo tour; the shaped nose cone cleared knees better on long pedal hours and the waterproof seams shrugged off three days of rain.", "decision", "personal", False,
     [("Apidura Expedition", "tool"), ("Revelate Ranger", "tool"), ("Cutthroat", "tool"), ("Trans-Ezo", "event")],
     [("Apidura Expedition", "Revelate Ranger", "PREFERS")],
     "which frame bag won over the Revelate option for the Trans-Ezo tour and what two features tipped it",
     "apidura expedition revelate ranger cutthroat trans ezo waterproof knee"),
    # --- 41. preference ---
    ("Prefer 28 mm road tyres over 25 mm on every surface that isn't a closed velodrome; rolling resistance at the same pressure is indistinguishable on smooth tarmac and clearly better on chip-seal and cracked pavement.", "preference", "personal", False,
     [("28 mm", "concept"), ("25 mm", "concept"), ("chip-seal", "concept")],
     [("28 mm", "25 mm", "PREFERS")],
     "which road tyre width is now the default and what surface comparison drove the preference",
     "28 mm 25 mm road tyre chip seal rolling resistance velodrome"),
    # --- 42. problem ---
    ("Disc brake rub on the gravel bike after a muddy Unbound recon kept returning within a day; the culprit was a slightly warped Shimano RT-MT900 rotor, and a swap to a fresh rotor plus a caliper re-centre with the wheel clamped in a stand fixed it.", "problem", "personal", False,
     [("Shimano RT-MT900", "tool"), ("Unbound", "event"), ("caliper", "tool")],
     [("Shimano RT-MT900", "caliper", "CAUSES")],
     "what caused the recurring disc brake rub after a muddy Unbound recon and which swap fixed it",
     "shimano rt mt900 rotor caliper rub unbound recon warp center"),
    # --- 43. noise ---
    ("The espresso machine in the shop corner has been grinding the same bag of beans for so long the dial stopped clicking between notches.", "fact", "noise", True, [], [], None, None),
    # --- 44. fact ---
    ("The Tour de France peloton averages roughly 42 km/h over a flat stage and the breakaway rarely survives without at least a 4 minute gap at 20 km to go; the modern radio-coordinated chase is ruthless on lone attackers.", "fact", "personal", False,
     [("Tour de France", "event"), ("peloton", "concept"), ("breakaway", "concept")],
     [("Tour de France", "peloton", "HAS_PART")],
     "what flat-stage average speed does the Tour de France peloton hold and how much gap does a breakaway need at 20 km to go",
     "tour de france peloton 42 km h breakaway 4 minute gap 20 km radio"),
    # --- 45. architecture ---
    ("Tyre quiver is organised by course: GP5000 S TR 28 mm for road, Pirelli P Zero Race TLR 30 mm for all-road, Schwalbe G-One R 45 mm for gravel, and Maxxis Rekon 2.4 for the MTB; each pair lives in a labelled bin on the workshop wall.", "architecture", "personal", False,
     [("GP5000 S TR", "tool"), ("Pirelli P Zero Race TLR", "tool"), ("Schwalbe G-One R", "tool"), ("Maxxis Rekon", "tool")],
     [("GP5000 S TR", "Pirelli P Zero Race TLR", "RELATED_TO"), ("Schwalbe G-One R", "Maxxis Rekon", "RELATED_TO")],
     "how is the tyre quiver partitioned by course across road, all-road, gravel, and MTB",
     "gp5000 s tr pirelli p zero race tlr schwalbe g one r maxxis rekon"),
    # --- 46. reference ---
    ("Training zone thresholds were set from a 20 minute field test anchored in Allen and Coggan's Training and Racing with a Power Meter; the FTP of 284 watts and five-zone distribution translated cleanly into every TrainerRoad plan since.", "reference", "personal", False,
     [("Allen and Coggan", "person"), ("Training and Racing with a Power Meter", "publication"), ("FTP", "concept"), ("TrainerRoad", "tool")],
     [("Training and Racing with a Power Meter", "Allen and Coggan", "AUTHORED_BY")],
     "which power-training reference and FTP test method set the current training zones",
     "allen coggan training racing power meter ftp 284 watt 20 minute"),
    # --- 47. decision ---
    ("Went with carbon over steel for the next road build; the weight saving of almost a kilo at the frame level mattered more than the comfort edge of steel once the 28 mm tubeless tyres took over most of the chatter absorption.", "decision", "personal", False,
     [("carbon", "concept"), ("steel", "concept"), ("road build", "project")],
     [("carbon", "steel", "PREFERS")],
     "which frame material won the next road build over steel and what compensated for the comfort gap",
     "carbon steel road build 28 mm tubeless chatter absorb weight frame"),
    # --- 48. milestone ---
    ("Closed the year at 13 500 km and 190 000 metres of elevation across the four bikes; the Strava year-in-review numbers came in ahead of last year's 11 800 km and unlocked the Local Legend segment on the canyon climb for the first time.", "milestone", "personal", False,
     [("Strava", "tool"), ("Local Legend", "concept"), ("canyon climb", "place")],
     [("Strava", "Local Legend", "PRODUCES")],
     "what annual mileage and elevation did the ride log close with and which Strava badge did it unlock",
     "strava 13500 km 190000 metre local legend canyon climb year review"),
    # --- 49. reference ---
    ("The gravel-race pacing plan drew on Ted King's race reports from Unbound; the steady endurance-zone approach through the first 80 miles with a willingness to surge in the final 40 matches the Ted King split pattern almost exactly.", "reference", "personal", False,
     [("Ted King", "person"), ("Unbound", "event"), ("endurance-zone", "concept")],
     [("Ted King", "Unbound", "RELATED_TO")],
     "which rider's race reports anchor the current Unbound pacing plan and how are the splits shaped",
     "ted king unbound gravel race pacing endurance zone 80 mile split"),
    # --- 50. architecture ---
    ("Bike storage at home is a vertical Feedback Sports Velo Hinge rack along one garage wall with hooks spaced for all four bikes; a small shelf above holds helmets and shoes by discipline, and the floor stays clear for the trainer bike to roll in and out of the pain cave.", "architecture", "personal", False,
     [("Feedback Sports Velo Hinge", "tool"), ("garage", "place"), ("pain cave", "place"), ("trainer bike", "tool")],
     [("Feedback Sports Velo Hinge", "garage", "LOCATED_IN"), ("trainer bike", "pain cave", "LOCATED_IN")],
     "how is home bike storage organised around a vertical rack and which bike stays floor-accessible",
     "feedback sports velo hinge garage wall rack helmet shoe pain cave"),
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
