"""One-off emitter for shared-base batch-248 — personal domain (rock climbing: grades, disciplines, gear, ropes, shoes, routes, crags, personalities).

Writes 50 rows to data/v2/shared/batch_248.tmp.jsonl with ids shared-12351..12400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_248.tmp.jsonl"
ID_OFFSET = 12350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Swapped my old Black Diamond Momentum harness for a Petzl Sama before the Ceüse trip; the leg-loop padding on the Sama held up way better on two-hour hanging belays at the base of Biographie.", "decision", "personal", False,
     [("Black Diamond Momentum", "tool"), ("Petzl Sama", "tool"), ("Ceüse", "place"), ("Biographie", "concept")],
     [("Petzl Sama", "Black Diamond Momentum", "REPLACES"), ("Petzl Sama", "Ceüse", "APPLIES_TO")],
     "which harness did I switch to for long hanging belays in France and what replaced my previous one",
     "petzl sama black diamond momentum harness ceuse biographie belay"),
    # --- 2. architecture ---
    ("My sport-climbing rack is built around twelve Petzl Spirit quickdraws for onsight attempts and six fixed Dyneema draws I clip and leave on projects; the bail biner on the last draw is always a cheap steel oval.", "architecture", "personal", False,
     [("Petzl Spirit", "tool"), ("Dyneema", "technology"), ("quickdraws", "tool"), ("bail biner", "tool")],
     [("Petzl Spirit", "quickdraws", "APPLIES_TO")],
     "how is my sport rack split between onsight draws and project draws and what goes on the bail biner",
     "petzl spirit quickdraw dyneema bail biner sport rack project onsight"),
    # --- 3. milestone ---
    ("Sent my first 5.12a on lead at Red Rock yesterday — a route called Integrity on the Panty Wall; took three redpoint burns after clipping the chains on toprope the day before.", "milestone", "personal", False,
     [("5.12a", "concept"), ("Red Rock", "place"), ("Integrity", "concept"), ("Panty Wall", "place")],
     [("Integrity", "Red Rock", "APPLIES_TO"), ("Integrity", "5.12a", "APPLIES_TO")],
     "which 5.12a route did I finally redpoint at Red Rock and how many burns did it take me",
     "red rock integrity panty wall 5.12a redpoint first lead burn"),
    # --- 4. decision ---
    ("Moved from the Petzl GriGri to the Petzl NEOX for sport belays; the cam-assist catch feels identical but the rope feed during lead paying-out is finally smooth enough that I stop short-roping my partner.", "decision", "personal", False,
     [("Petzl GriGri", "tool"), ("Petzl NEOX", "tool"), ("cam-assist", "pattern")],
     [("Petzl NEOX", "Petzl GriGri", "REPLACES")],
     "which assisted belay device replaced my GriGri for sport and what problem did the switch solve",
     "petzl neox grigri assisted belay rope feed short rope lead"),
    # --- 5. fact ---
    ("Adam Ondra first-ascended Silence at 5.15d in the Hanshelleren Cave in 2017 and it's still the only confirmed route at that grade in the world.", "fact", "personal", False,
     [("Adam Ondra", "person"), ("Silence", "concept"), ("5.15d", "concept"), ("Hanshelleren Cave", "place")],
     [("Adam Ondra", "Silence", "APPLIES_TO"), ("Silence", "Hanshelleren Cave", "APPLIES_TO")],
     "who established the world's hardest confirmed sport route and what grade did he propose for it",
     "adam ondra silence 5.15d hanshelleren cave first ascent world"),
    # --- 6. reference ---
    ("The Yosemite Decimal System tops out practically at 5.15d, while the French sport scale runs parallel with 9c sitting at the same approximate difficulty; 5.10 through 5.13 cover most recreational climbing.", "reference", "personal", False,
     [("Yosemite Decimal System", "concept"), ("5.15d", "concept"), ("9c", "concept"), ("5.10", "concept"), ("5.13", "concept")],
     [("Yosemite Decimal System", "5.15d", "APPLIES_TO")],
     "how does the Yosemite Decimal top grade line up with the French sport scale and which range covers most recreational climbers",
     "yosemite decimal system 5.15d 9c french grade sport scale recreational"),
    # --- 7. preference ---
    ("I prefer La Sportiva Solution over Scarpa Instinct VS for steep limestone; the rubber wraps around the toe better for heel-toe cams even though I size the Solution a full Euro tighter.", "preference", "personal", False,
     [("La Sportiva Solution", "tool"), ("Scarpa Instinct VS", "tool"), ("limestone", "concept"), ("heel-toe", "method")],
     [("La Sportiva Solution", "Scarpa Instinct VS", "PREFERS")],
     "which climbing shoe do I reach for on steep limestone and why does it beat the Scarpa option",
     "la sportiva solution scarpa instinct vs limestone heel toe cam"),
    # --- 8. architecture ---
    ("My trad rack for single-pitch Squamish granite is a single set of Black Diamond C4 cams from 0.3 to 4, a single set of Black Diamond Stopper nuts, four offset nuts for the scooped placements, and eight alpine draws.", "architecture", "personal", False,
     [("Squamish", "place"), ("Black Diamond C4", "tool"), ("Black Diamond Stopper", "tool"), ("offset nuts", "tool"), ("alpine draws", "tool"), ("granite", "concept")],
     [("Black Diamond C4", "Squamish", "APPLIES_TO"), ("offset nuts", "granite", "APPLIES_TO")],
     "what is the standard trad rack I carry for single-pitch granite at Squamish",
     "squamish granite black diamond c4 stopper offset nut alpine draw trad"),
    # --- 9. milestone ---
    ("Topped out The Nose on El Capitan in four days with one night on El Cap Tower and two on Camp 4 ledge; French-freed the Great Roof pitch because my fingers were wrecked by then.", "milestone", "personal", False,
     [("The Nose", "concept"), ("El Capitan", "place"), ("El Cap Tower", "place"), ("Camp 4", "place"), ("Great Roof", "concept")],
     [("The Nose", "El Capitan", "APPLIES_TO")],
     "how long did my Nose ascent take and which pitch forced me into French-free tactics",
     "the nose el capitan four day el cap tower camp great roof french free"),
    # --- 10. noise ---
    ("The café near the crag parking started putting cardamom in their flat whites and it completely changed my post-climb breakfast ritual.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Settled on the Mammut 9.5 Infinity as my everyday single rope; the Edelrid Swift is lighter at 8.9 mm but I wanted more durability for top-roping laps at the gym between outdoor trips.", "decision", "personal", False,
     [("Mammut 9.5 Infinity", "tool"), ("Edelrid Swift", "tool"), ("single rope", "tool")],
     [("Mammut 9.5 Infinity", "Edelrid Swift", "PREFERS")],
     "which single rope did I pick for daily use and why did I pass on the lighter Edelrid option",
     "mammut infinity edelrid swift single rope durability top rope gym"),
    # --- 12. reference ---
    ("Bouldering uses two parallel grade systems: the Hueco V-scale runs V0 through V16, while Fontainebleau numbers go from roughly 4 to 8B+ with a slash between 6A and 6A+ for font-specific friction climbing.", "reference", "personal", False,
     [("Hueco", "place"), ("V0", "concept"), ("V16", "concept"), ("Fontainebleau", "place"), ("6A", "concept"), ("8B+", "concept")],
     [("Hueco", "V0", "APPLIES_TO"), ("Fontainebleau", "6A", "APPLIES_TO")],
     "how do the V-scale and Fontainebleau bouldering grades map against each other and where do they top out",
     "hueco v scale fontainebleau 6a 8b+ boulder grade v0 v16 friction"),
    # --- 13. fact ---
    ("Alex Honnold free-soloed Freerider on El Capitan on June 3 2017, which the Free Solo documentary captured and won an Oscar for in 2019.", "fact", "personal", False,
     [("Alex Honnold", "person"), ("Freerider", "concept"), ("El Capitan", "place"), ("Free Solo", "concept")],
     [("Alex Honnold", "Freerider", "APPLIES_TO"), ("Freerider", "El Capitan", "APPLIES_TO")],
     "which El Capitan route did Alex Honnold free-solo and which film documented the ascent",
     "alex honnold freerider el capitan free solo documentary oscar 2017"),
    # --- 14. decision ---
    ("Carrying the Petzl Reverso instead of the ATC Guide on multi-pitch now; both do guide-mode auto-blocking fine but the Reverso rope grooves wear slower on the 8.5 mm half ropes I pair it with.", "decision", "personal", False,
     [("Petzl Reverso", "tool"), ("ATC Guide", "tool"), ("guide-mode", "pattern"), ("half ropes", "tool")],
     [("Petzl Reverso", "ATC Guide", "PREFERS"), ("Petzl Reverso", "half ropes", "APPLIES_TO")],
     "which tube belay device do I carry for multi-pitch now and which wear pattern drove the switch",
     "petzl reverso atc guide multi pitch auto block half rope groove"),
    # --- 15. problem ---
    ("Short-roped my partner on the third clip of a Rocklands highball last spring because the Edelrid Pinch was new to me and I hadn't dialled the lead-feed hand position yet; we switched back to the GriGri for the rest of the trip.", "problem", "personal", False,
     [("Edelrid Pinch", "tool"), ("Rocklands", "place"), ("GriGri", "tool"), ("highball", "concept")],
     [("GriGri", "Edelrid Pinch", "REPLACES")],
     "which new belay device caused me to short-rope my partner in Rocklands and which one I fell back on",
     "edelrid pinch rocklands grigri short rope highball lead feed"),
    # --- 16. architecture ---
    ("My alpine rack for non-glaciated rock routes in the Bugaboos is a single rack of Totem cams in four sizes, a set of Black Diamond Stopper nuts, three Omega Pacific tricams for parallel pods, and four 120 cm Dyneema slings.", "architecture", "personal", False,
     [("Bugaboos", "place"), ("Totem", "tool"), ("Black Diamond Stopper", "tool"), ("Omega Pacific", "tool"), ("tricams", "tool"), ("Dyneema", "technology")],
     [("Totem", "Bugaboos", "APPLIES_TO"), ("Omega Pacific", "tricams", "APPLIES_TO")],
     "what is my alpine rock rack for the Bugaboos and which piece handles parallel pods",
     "bugaboos alpine rack totem stopper omega pacific tricam dyneema sling"),
    # --- 17. milestone ---
    ("Flashed my first V7 at Fontainebleau last November — the classic slab problem Fat Man Traverse at Bas Cuvier — after warming up on three 6A+ circuit problems.", "milestone", "personal", False,
     [("V7", "concept"), ("Fontainebleau", "place"), ("Fat Man Traverse", "concept"), ("Bas Cuvier", "place"), ("6A+", "concept")],
     [("Fat Man Traverse", "Bas Cuvier", "APPLIES_TO"), ("Fat Man Traverse", "V7", "APPLIES_TO")],
     "which V7 did I flash at Fontainebleau and where on the forest did it sit",
     "fontainebleau v7 fat man traverse bas cuvier flash 6a+ slab"),
    # --- 18. reference ---
    ("The UIAA grade scale uses Roman numerals with plus and minus modifiers; UIAA VII roughly equals 5.10d YDS and a solid F6b+ French, which trips up American climbers reading Alpine guidebooks for the first time.", "reference", "personal", False,
     [("UIAA", "concept"), ("VII", "concept"), ("5.10d", "concept"), ("F6b+", "concept")],
     [("UIAA", "VII", "APPLIES_TO")],
     "how does UIAA VII compare to American and French sport grades and where does that confuse climbers",
     "uiaa vii 5.10d f6b+ roman numeral grade compare alpine guidebook"),
    # --- 19. decision ---
    ("Replaced all my screw-gate carabiners at the anchor with HMS pear-shape models; the wider basket gives enough room for a Munter hitch in an emergency when the GriGri jams on muddy rope.", "decision", "personal", False,
     [("screw-gate carabiners", "tool"), ("HMS", "tool"), ("Munter hitch", "method"), ("GriGri", "tool")],
     [("HMS", "screw-gate carabiners", "REPLACES"), ("Munter hitch", "HMS", "APPLIES_TO")],
     "which anchor carabiner shape did I standardise on and what backup technique does that enable",
     "hms pear screw gate carabiner munter hitch anchor grigri muddy"),
    # --- 20. fact ---
    ("Tommy Caldwell and Kevin Jorgeson first-freed the Dawn Wall on El Capitan in January 2015 after nineteen days on the wall; pitch 15 at 5.14d held Jorgeson up for eleven days.", "fact", "personal", False,
     [("Tommy Caldwell", "person"), ("Kevin Jorgeson", "person"), ("Dawn Wall", "concept"), ("El Capitan", "place"), ("5.14d", "concept")],
     [("Tommy Caldwell", "Dawn Wall", "APPLIES_TO"), ("Dawn Wall", "El Capitan", "APPLIES_TO")],
     "who first-freed the Dawn Wall and which pitch was the hardest for one of the partners",
     "tommy caldwell kevin jorgeson dawn wall el capitan 5.14d pitch 15"),
    # --- 21. preference ---
    ("I prefer Tenaya Oasi over Evolv Shaman for long vertical granite days; the Oasi flat last keeps my toes from cramping on edges when I'm hanging on the wall for six hours on something like Astroman.", "preference", "personal", False,
     [("Tenaya Oasi", "tool"), ("Evolv Shaman", "tool"), ("granite", "concept"), ("Astroman", "concept")],
     [("Tenaya Oasi", "Evolv Shaman", "PREFERS"), ("Tenaya Oasi", "Astroman", "APPLIES_TO")],
     "which climbing shoe do I choose for long vertical granite routes and why over the Evolv option",
     "tenaya oasi evolv shaman granite astroman flat last edge comfort"),
    # --- 22. architecture ---
    ("For sport projecting I rack gear on a single gear sling over one shoulder: twelve Dyneema-sling quickdraws, a GriGri pre-loaded on the belay loop, a chalk bag on elastic around the waist, and one stiff nylon runner for tat replacements at the anchor.", "architecture", "personal", False,
     [("gear sling", "tool"), ("Dyneema", "technology"), ("quickdraws", "tool"), ("GriGri", "tool"), ("chalk bag", "tool"), ("nylon runner", "tool")],
     [("Dyneema", "quickdraws", "APPLIES_TO")],
     "how is my gear arranged when I'm working a sport project over a session",
     "gear sling dyneema quickdraw grigri chalk bag nylon runner tat"),
    # --- 23. problem ---
    ("Core-shot my rope on a hanging belay at Ceüse last June when the rope edged over a sharp limestone flake during a take; retired the rope on the spot and finished the day on my partner's spare Mammut.", "problem", "personal", False,
     [("Ceüse", "place"), ("limestone", "concept"), ("Mammut", "tool"), ("Core-shot", "concept")],
     [("limestone", "Ceüse", "APPLIES_TO")],
     "how did I core-shot a rope in France and what got me through the rest of that day",
     "ceuse limestone core shot rope mammut hanging belay flake take"),
    # --- 24. milestone ---
    ("Climbed The Naked Edge in Eldorado Canyon in a single push last Saturday; the 5.11b crux pitch finally went clean on my third attempt that season after two winters of hangboard work.", "milestone", "personal", False,
     [("The Naked Edge", "concept"), ("Eldorado Canyon", "place"), ("5.11b", "concept"), ("hangboard", "tool")],
     [("The Naked Edge", "Eldorado Canyon", "APPLIES_TO"), ("The Naked Edge", "5.11b", "APPLIES_TO")],
     "which Eldorado Canyon classic did I finally send and how did my training feed into it",
     "naked edge eldorado canyon 5.11b hangboard single push send"),
    # --- 25. decision ---
    ("Chose Black Diamond Z4 offset cams over standard C4s for the thin flared placements on Indian Creek splitters; the Z4 narrower head fits into constrictions the C4 flares out of.", "decision", "personal", False,
     [("Black Diamond Z4", "tool"), ("C4", "tool"), ("Indian Creek", "place"), ("splitters", "concept")],
     [("Black Diamond Z4", "C4", "PREFERS"), ("Black Diamond Z4", "Indian Creek", "APPLIES_TO")],
     "which offset cam model did I pick for Indian Creek splitters and which geometry problem did it solve",
     "black diamond z4 c4 offset indian creek splitter flared narrow head"),
    # --- 26. fact ---
    ("Midnight Lightning is a V8 boulder problem on the Columbia Boulder in Camp 4 at Yosemite, first climbed by Ron Kauk in 1978 and named after a lightning bolt chalked on by Jim Bridwell.", "fact", "personal", False,
     [("Midnight Lightning", "concept"), ("V8", "concept"), ("Columbia Boulder", "place"), ("Camp 4", "place"), ("Yosemite", "place"), ("Ron Kauk", "person"), ("Jim Bridwell", "person")],
     [("Midnight Lightning", "Camp 4", "APPLIES_TO"), ("Ron Kauk", "Midnight Lightning", "APPLIES_TO")],
     "who first climbed Midnight Lightning and where does the problem live in Yosemite",
     "midnight lightning v8 columbia boulder camp 4 yosemite ron kauk bridwell"),
    # --- 27. reference ---
    ("Half ropes run paired and get clipped alternately to reduce rope drag on wandering trad routes, while twin ropes must be clipped together through every piece and are lighter per strand; I use half ropes in the Bugaboos and twins for ice.", "reference", "personal", False,
     [("half ropes", "tool"), ("twin ropes", "tool"), ("Bugaboos", "place")],
     [("half ropes", "Bugaboos", "APPLIES_TO")],
     "how do half ropes and twin ropes differ in clipping technique and which type goes on ice for me",
     "half rope twin rope clip alternate drag bugaboos ice wandering"),
    # --- 28. architecture ---
    ("My ice rack is one set of Black Diamond Express screws in 13, 16, 19, and 22 cm lengths, two Petzl Laser screws for quick re-racking, a V-thread hooker, and six Dyneema quickdraws with a steel lower biner to resist frozen cracking.", "architecture", "personal", False,
     [("Black Diamond Express", "tool"), ("Petzl Laser", "tool"), ("V-thread", "method"), ("Dyneema", "technology"), ("quickdraws", "tool")],
     [("Black Diamond Express", "quickdraws", "APPLIES_TO")],
     "which ice screws and V-thread tooling make up my ice rack",
     "black diamond express petzl laser ice screw v thread quickdraw dyneema"),
    # --- 29. milestone ---
    ("First V10 sent at Rocklands this winter — a sloper problem called Black Shadow on the Roadcrew sector — after two sessions projecting it over a week's trip.", "milestone", "personal", False,
     [("V10", "concept"), ("Rocklands", "place"), ("Black Shadow", "concept"), ("Roadcrew", "place")],
     [("Black Shadow", "Rocklands", "APPLIES_TO"), ("Black Shadow", "V10", "APPLIES_TO")],
     "which V10 did I finally send on my Rocklands trip and where did it sit",
     "rocklands v10 black shadow roadcrew sloper send project session"),
    # --- 30. decision ---
    ("Dropped hexes from the rack entirely after switching to the full Black Diamond C4 range; modern cams cover the parallel-sided placements hexes used to handle and the weight saving on long approaches is real.", "decision", "personal", False,
     [("hexes", "tool"), ("Black Diamond C4", "tool")],
     [("Black Diamond C4", "hexes", "REPLACES")],
     "why did I stop carrying hexes and what covers those placements on my rack now",
     "hexes black diamond c4 cam parallel placement weight approach drop"),
    # --- 31. problem ---
    ("Pumped out halfway up a 6c+ at Ceüse because I gripped the rope harder on each clip with my right hand; forearm recovery training with Tindeq and the newer Edelrid GriGri-like Jul2 taught me to relax between clips.", "problem", "personal", False,
     [("6c+", "concept"), ("Ceüse", "place"), ("Tindeq", "tool"), ("Jul2", "tool")],
     [("Tindeq", "6c+", "APPLIES_TO")],
     "why did I pump out on a 6c+ in France and what training closed the gap",
     "ceuse 6c+ pump forearm tindeq jul2 clip grip relax recover"),
    # --- 32. architecture ---
    ("Deep-water soloing kit is stripped: Scarpa Instinct VS shoes because they drain fast, a rash guard, a chalk ball instead of loose chalk in a bag, and zero hardware — the fallback is the sea.", "architecture", "personal", False,
     [("Deep-water soloing", "concept"), ("Scarpa Instinct VS", "tool"), ("chalk ball", "tool")],
     [("Scarpa Instinct VS", "Deep-water soloing", "APPLIES_TO")],
     "what goes in my deep-water soloing kit and why is it stripped down to almost nothing",
     "deep water solo scarpa instinct vs chalk ball drain rash guard"),
    # --- 33. fact ---
    ("The Lead Climbing World Cup has been running under IFSC since 1991 and rotates through about eight host cities a year; Janja Garnbret and Adam Ondra dominated the 2019 overall rankings on the lead discipline.", "fact", "personal", False,
     [("Lead Climbing World Cup", "concept"), ("IFSC", "concept"), ("Janja Garnbret", "person"), ("Adam Ondra", "person")],
     [("Janja Garnbret", "Lead Climbing World Cup", "APPLIES_TO"), ("Adam Ondra", "Lead Climbing World Cup", "APPLIES_TO")],
     "which organisation runs the lead climbing world cup and which two athletes dominated the 2019 season",
     "lead climbing world cup ifsc janja garnbret adam ondra 2019"),
    # --- 34. preference ---
    ("I prefer brushing holds with a boar's-hair Lapis brush over a synthetic Friction Labs brush for sandstone; the softer bristles lift chalk without polishing the micro-texture that makes Fontainebleau slopers stick.", "preference", "personal", False,
     [("Lapis", "tool"), ("Friction Labs", "tool"), ("sandstone", "concept"), ("Fontainebleau", "place")],
     [("Lapis", "Friction Labs", "PREFERS"), ("Lapis", "Fontainebleau", "APPLIES_TO")],
     "which brush do I use on sandstone holds and why over the synthetic option",
     "lapis boar hair friction labs brush sandstone fontainebleau sloper"),
    # --- 35. architecture ---
    ("Big-wall haulbag system for El Capitan is a Metolius Sentinel haulbag, a 2:1 Petzl Pro Traxion raising setup, a portaledge on the second night, and a second rope dedicated as the haul line separate from the lead rope.", "architecture", "personal", False,
     [("Metolius Sentinel", "tool"), ("Petzl Pro Traxion", "tool"), ("portaledge", "tool"), ("haul line", "tool"), ("El Capitan", "place")],
     [("Metolius Sentinel", "El Capitan", "APPLIES_TO"), ("Petzl Pro Traxion", "haul line", "APPLIES_TO")],
     "how is my big-wall hauling and bivy system organised for an El Cap push",
     "metolius sentinel petzl pro traxion haul bag portaledge el capitan"),
    # --- 36. decision ---
    ("Bought the Arc'teryx FL-365 harness as a dedicated alpine setup; the fixed leg loops shed weight versus the Petzl Sama and the ice-clipper slots fit Petzl Caritool hangers cleanly.", "decision", "personal", False,
     [("Arc'teryx FL-365", "tool"), ("Petzl Sama", "tool"), ("Petzl Caritool", "tool"), ("ice-clipper", "tool")],
     [("Arc'teryx FL-365", "Petzl Sama", "REPLACES"), ("Petzl Caritool", "Arc'teryx FL-365", "APPLIES_TO")],
     "which harness do I use for alpine now and what ice-clipper system fits it",
     "arcteryx fl 365 petzl sama alpine caritool ice clipper leg loop"),
    # --- 37. milestone ---
    ("Led Astroman free in a day on Washington Column at Yosemite this September; the Harding Slot pitch was the crux for me mentally, not physically, because the fist-jams felt good once I wriggled through the first body-length.", "milestone", "personal", False,
     [("Astroman", "concept"), ("Washington Column", "place"), ("Yosemite", "place"), ("Harding Slot", "concept")],
     [("Astroman", "Washington Column", "APPLIES_TO"), ("Harding Slot", "Astroman", "APPLIES_TO")],
     "which Yosemite classic did I lead in a day and which pitch was the mental crux",
     "astroman washington column yosemite harding slot lead free fist jam"),
    # --- 38. reference ---
    ("Climbing disciplines fall into sport, trad, boulder, alpine, big wall, ice, mixed, and deep-water soloing; most recreational climbers move between sport and boulder, while big wall and alpine draw specialists willing to sleep on the wall.", "reference", "personal", False,
     [("sport", "concept"), ("trad", "concept"), ("boulder", "concept"), ("alpine", "concept"), ("big wall", "concept"), ("ice", "concept"), ("mixed", "concept"), ("deep-water soloing", "concept")],
     [("big wall", "alpine", "APPLIES_TO")],
     "what are the major climbing disciplines and which ones draw specialist commitment",
     "sport trad boulder alpine big wall ice mixed dws discipline specialist"),
    # --- 39. fact ---
    ("Ceüse sits above the village of Sigottier in the French Alps with an hour-long uphill approach; the cliff is Jurassic limestone and Biographie, graded 9a+, was the first 9a+ in the world when Chris Sharma first-ascended it in 2001.", "fact", "personal", False,
     [("Ceüse", "place"), ("Biographie", "concept"), ("9a+", "concept"), ("Chris Sharma", "person"), ("Sigottier", "place")],
     [("Biographie", "Ceüse", "APPLIES_TO"), ("Chris Sharma", "Biographie", "APPLIES_TO")],
     "what makes Ceüse a noteworthy sport crag and which route did Chris Sharma first-ascend there",
     "ceuse sigottier biographie 9a+ chris sharma 2001 limestone france"),
    # --- 40. problem ---
    ("Botched a cam placement in a flared piton scar on a Yosemite 5.10 trad pitch because I weighted a Black Diamond C4 #0.5 before it had finished walking into the constriction; switched to a Totem 0.5 which held because of its single-stem cable flex.", "problem", "personal", False,
     [("Black Diamond C4", "tool"), ("Totem", "tool"), ("Yosemite", "place"), ("5.10", "concept"), ("piton scar", "concept")],
     [("Totem", "Black Diamond C4", "REPLACES")],
     "why did a C4 0.5 fail in a Yosemite piton scar and which cam replaced it",
     "cam flared piton scar black diamond c4 totem 0.5 yosemite walk"),
    # --- 41. architecture ---
    ("My bouldering pad setup for Fontainebleau is two Black Diamond Drop Zone pads arranged in an L for highball landing coverage and a spotter blanket to fill the seam; chalk goes in a Friction Labs Unicorn Dust bucket at the base.", "architecture", "personal", False,
     [("Black Diamond Drop Zone", "tool"), ("Friction Labs", "tool"), ("Unicorn Dust", "tool"), ("Fontainebleau", "place"), ("spotter blanket", "tool")],
     [("Black Diamond Drop Zone", "Fontainebleau", "APPLIES_TO"), ("Unicorn Dust", "Friction Labs", "APPLIES_TO")],
     "how do I set up pads for a Fontainebleau highball session and which chalk lives in the bucket",
     "black diamond drop zone pad fontainebleau friction labs unicorn dust spotter"),
    # --- 42. decision ---
    ("Picked Sterling Evolution Velocity 9.8 mm as the gym-and-crag workhorse rope over the Mammut 9.5 Infinity for a year; the thicker diameter paid for itself on top-rope laps but I rotated back when I wanted one-rope quiver for sport.", "decision", "personal", False,
     [("Sterling Evolution Velocity", "tool"), ("Mammut 9.5 Infinity", "tool"), ("top-rope", "concept")],
     [("Sterling Evolution Velocity", "Mammut 9.5 Infinity", "PREFERS")],
     "which 9.8 mm gym rope did I run for a year and what drove the swap back",
     "sterling evolution velocity mammut infinity gym crag top rope 9.8"),
    # --- 43. noise ---
    ("My neighbour's new puppy figured out the stairs over the weekend and now it races me to the front door every time a package arrives.", "fact", "noise", True, [], [], None, None),
    # --- 44. milestone ---
    ("Onsighted my first F7a at Ceüse last Tuesday — a tufa route called Carte Blanche on the Cascade sector; stayed calm through the rest at two-thirds height and clipped the chains without a take.", "milestone", "personal", False,
     [("F7a", "concept"), ("Ceüse", "place"), ("Carte Blanche", "concept"), ("Cascade", "place"), ("tufa", "concept")],
     [("Carte Blanche", "Ceüse", "APPLIES_TO"), ("Carte Blanche", "F7a", "APPLIES_TO")],
     "which F7a did I onsight at Ceüse and which sector was it on",
     "ceuse f7a carte blanche cascade tufa onsight rest chain"),
    # --- 45. fact ---
    ("Squamish granite is Chief granodiorite, a coarse-crystalline stock with steep cracks that reward wide-hand and fist jamming; classic trad testpieces there include Exasperator at 5.10c and University Wall at 5.12a.", "fact", "personal", False,
     [("Squamish", "place"), ("Chief", "place"), ("Exasperator", "concept"), ("5.10c", "concept"), ("University Wall", "concept"), ("5.12a", "concept")],
     [("Exasperator", "Squamish", "APPLIES_TO"), ("University Wall", "Squamish", "APPLIES_TO")],
     "what kind of rock is Squamish and which classic trad routes show off the jamming style",
     "squamish chief granodiorite granite exasperator 5.10c university wall"),
    # --- 46. reference ---
    ("Standard carabiner-gate types: screw-gate for belay and anchor masterpoints, twist-lock for guide-mode, wiregate for rack quickdraws to shed weight and resist gate-flutter, and HMS pear for Munter-hitch escape setups.", "reference", "personal", False,
     [("screw-gate", "tool"), ("twist-lock", "tool"), ("wiregate", "tool"), ("HMS", "tool"), ("Munter-hitch", "method")],
     [("HMS", "Munter-hitch", "APPLIES_TO")],
     "which carabiner gate types do I use for which jobs on a rack",
     "screw gate twist lock wire gate hms carabiner belay anchor guide munter"),
    # --- 47. preference ---
    ("I prefer Friction Labs Gorilla Grip chalk over Black Diamond White Gold for Yosemite granite; the chunkier grain gives more texture through sweat on long belay stints and the Yosemite heat is brutal in July.", "preference", "personal", False,
     [("Friction Labs", "tool"), ("Gorilla Grip", "tool"), ("Black Diamond White Gold", "tool"), ("Yosemite", "place")],
     [("Gorilla Grip", "Black Diamond White Gold", "PREFERS"), ("Gorilla Grip", "Yosemite", "APPLIES_TO")],
     "which chalk blend do I pick for Yosemite granite and what problem did it solve",
     "friction labs gorilla grip black diamond white gold chalk yosemite sweat"),
    # --- 48. architecture ---
    ("My gym training split is a three-day cycle: hangboard repeaters on a Beastmaker 2000 on day one, limit bouldering on the Moonboard on day two, and aerobic capacity 4x4s on lead terrain day three.", "architecture", "personal", False,
     [("Beastmaker 2000", "tool"), ("Moonboard", "tool"), ("hangboard", "tool"), ("4x4s", "concept")],
     [("Beastmaker 2000", "hangboard", "APPLIES_TO")],
     "how is my gym training split across a three-day cycle",
     "beastmaker 2000 moonboard hangboard 4x4 aerobic capacity lead cycle"),
    # --- 49. decision ---
    ("Chose Petzl Sirocco as my ice-and-alpine helmet over the Black Diamond Vapor; the EPP foam construction survived a 20 metre leader fall when a block dislodged above me in the Bugaboos, and the weight difference was negligible.", "decision", "personal", False,
     [("Petzl Sirocco", "tool"), ("Black Diamond Vapor", "tool"), ("EPP foam", "technology"), ("Bugaboos", "place")],
     [("Petzl Sirocco", "Black Diamond Vapor", "PREFERS"), ("Petzl Sirocco", "Bugaboos", "APPLIES_TO")],
     "which alpine helmet won my comparison and what real incident confirmed the choice",
     "petzl sirocco black diamond vapor epp foam bugaboos helmet fall"),
    # --- 50. milestone ---
    ("Topped out the Rostrum in Yosemite on Sunday — my first 5.11c trad lead without hanging; the thin hand crack on pitch three flowed once I stopped muscling and trusted the ring-lock over the thin-hand cam.", "milestone", "personal", False,
     [("Rostrum", "concept"), ("Yosemite", "place"), ("5.11c", "concept"), ("ring-lock", "method"), ("thin-hand", "method")],
     [("Rostrum", "Yosemite", "APPLIES_TO"), ("Rostrum", "5.11c", "APPLIES_TO")],
     "which 5.11c Yosemite trad route did I lead clean for the first time and which jam sealed pitch three",
     "rostrum yosemite 5.11c trad lead ring lock thin hand crack clean"),
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
