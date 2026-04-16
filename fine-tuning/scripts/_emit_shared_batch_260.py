"""One-off emitter for shared-base batch-260 — personal domain (skiing and snowboarding: backcountry and resort skis, touring setups, bindings, boots, skins, snowboards, avalanche gear, avalanche education, big mountain, resorts).

Writes 50 rows to data/v2/shared/batch_260.tmp.jsonl with ids shared-12951..13000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_260.tmp.jsonl"
ID_OFFSET = 12950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Settled on the Völkl Mantra as the one-ski quiver after a season on the Blizzard Rustler left me wanting more edge hold on wind-scoured traverses at Jackson Hole; the titanal layer carves the groomers on ride-home runs too.", "decision", "personal", False,
     [("Völkl Mantra", "tool"), ("Blizzard Rustler", "tool"), ("Jackson Hole", "place"), ("titanal", "concept")],
     [("Völkl Mantra", "Blizzard Rustler", "REPLACES"), ("Völkl Mantra", "Jackson Hole", "APPLIES_TO")],
     "which ski took the one-quiver slot after a season testing the Blizzard Rustler on wind-scoured traverses",
     "volkl mantra blizzard rustler jackson hole titanal one quiver"),
    # --- 2. decision ---
    ("Chose the Atomic Backland over the Salomon MTN for the dedicated touring setup because the carbon backbone saves almost three hundred grams per foot across a full day in the Wasatch; weight at the binding compounds faster than stiffness at the shovel.", "decision", "personal", False,
     [("Atomic Backland", "tool"), ("Salomon MTN", "tool"), ("Wasatch", "place")],
     [("Atomic Backland", "Salomon MTN", "PREFERS"), ("Atomic Backland", "Wasatch", "APPLIES_TO")],
     "which dedicated touring ski beat the Salomon MTN for Wasatch day tours and what swayed the pick",
     "atomic backland salomon mtn wasatch carbon weight tour day"),
    # --- 3. architecture ---
    ("The backcountry kit is split into three bags by use case: a day-tour pack with Pomoca skins and a BCA Tracker S, a hut-trip duffel that adds a Mammut Barryvox as a backup beacon, and a lift-access side pack with just a probe and shovel for slackcountry laps.", "architecture", "personal", False,
     [("Pomoca", "tool"), ("BCA Tracker S", "tool"), ("Mammut Barryvox", "tool"), ("probe", "tool"), ("shovel", "tool")],
     [("BCA Tracker S", "Mammut Barryvox", "RELATED_TO")],
     "how does the backcountry kit partition skins, beacons, probe and shovel across day, hut and slackcountry bags",
     "pomoca skin bca tracker mammut barryvox probe shovel bag split"),
    # --- 4. milestone ---
    ("Passed AIARE Level 1 in January at Alta and the terrain-selection module finally made the Wasatch Snow Forecast click; booked AIARE Level 2 for the following winter before leaving the parking lot.", "milestone", "personal", False,
     [("AIARE Level 1", "event"), ("Alta", "place"), ("Wasatch Snow Forecast", "tool"), ("AIARE Level 2", "event")],
     [("AIARE Level 1", "Alta", "LOCATED_IN"), ("AIARE Level 1", "AIARE Level 2", "RELATED_TO")],
     "which avalanche course finally made the Wasatch forecast click and what follow-up got booked the same day",
     "aiare level 1 alta wasatch snow forecast level 2 terrain selection"),
    # --- 5. fact ---
    ("Candide Thovex dropped a new edit on the Faction Dictator last March and the top-sheet graphic shipped to retail within six weeks; the ski had been on the wait-list at the local shop all season.", "fact", "personal", False,
     [("Candide Thovex", "person"), ("Faction Dictator", "tool")],
     [("Candide Thovex", "Faction Dictator", "APPLIES_TO")],
     "which pro rider's edit on the Faction Dictator pushed the graphic into retail within six weeks",
     "candide thovex faction dictator edit retail top sheet graphic"),
    # --- 6. reference ---
    ("The Wasatch Snow Forecast from the Utah Avalanche Center sits as the first bookmark in the ski folder; the morning danger rose and the problem list anchor every trailhead conversation before skinning.", "reference", "personal", False,
     [("Wasatch Snow Forecast", "tool"), ("Utah Avalanche Center", "organization")],
     [("Wasatch Snow Forecast", "Utah Avalanche Center", "HAS_PART")],
     "which avalanche-center forecast anchors the morning trailhead conversation in the Wasatch",
     "wasatch snow forecast utah avalanche center danger rose trailhead"),
    # --- 7. decision ---
    ("Replaced the Marker Kingpin on the touring ski with a Fritschi Xenic because a retention test after a warm-to-cold refreeze showed the Kingpin toe springs had lost pre-load; Xenic's adjustable lateral release tested clean on the same bench.", "decision", "personal", False,
     [("Marker Kingpin", "tool"), ("Fritschi Xenic", "tool")],
     [("Fritschi Xenic", "Marker Kingpin", "REPLACES")],
     "which tech binding replaced the Marker Kingpin after a retention bench test flagged lost toe pre-load",
     "marker kingpin fritschi xenic retention spring pre load release"),
    # --- 8. preference ---
    ("Prefer the Atomic Hawx Ultra XTD over the Tecnica Zero G for mixed resort-and-tour days; the 130 flex in the Hawx drives the Völkl Mantra harder on the ride-home groomers without cooking my shins on the skin track.", "preference", "personal", False,
     [("Atomic Hawx Ultra XTD", "tool"), ("Tecnica Zero G", "tool"), ("Völkl Mantra", "tool")],
     [("Atomic Hawx Ultra XTD", "Tecnica Zero G", "PREFERS"), ("Atomic Hawx Ultra XTD", "Völkl Mantra", "APPLIES_TO")],
     "which mixed-duty boot edges out the Tecnica Zero G for days that pair a tour with resort groomers",
     "atomic hawx ultra xtd tecnica zero g volkl mantra 130 flex mixed"),
    # --- 9. architecture ---
    ("The quiver tree by the garage door holds four setups in rotation: the Völkl Mantra with Look Pivot for resort laps, the DPS Pagoda Tour with ATK R12 for spring corn, the Atomic Backland with Plum Oazo for cold smoke day tours, and the Jones Mountain Twin for resort snowboard days with Niseko friends.", "architecture", "personal", False,
     [("Völkl Mantra", "tool"), ("Look Pivot", "tool"), ("DPS Pagoda Tour", "tool"), ("ATK R12", "tool"), ("Atomic Backland", "tool"), ("Plum Oazo", "tool"), ("Jones Mountain Twin", "tool"), ("Niseko", "place")],
     [("Völkl Mantra", "Look Pivot", "USES"), ("DPS Pagoda Tour", "ATK R12", "USES"), ("Atomic Backland", "Plum Oazo", "USES")],
     "how are the four quiver setups paired across resort, spring corn, cold smoke, and snowboard days",
     "volkl dps atomic jones pivot atk plum oazo quiver pair setup"),
    # --- 10. noise ---
    ("The garage fluorescent tube flickers for a minute every morning and the hardware-store replacement on the shelf is the wrong length by half an inch.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Picked the Scarpa F1 over the Dynafit Radical Pro for fast-and-light missions after a hut-to-hut link in Chamonix; the Boa closure tightens one-handed on a ridgeline while the Radical's buckles fought frozen gloves every transition.", "decision", "personal", False,
     [("Scarpa F1", "tool"), ("Dynafit Radical Pro", "tool"), ("Chamonix", "place"), ("Boa", "concept")],
     [("Scarpa F1", "Dynafit Radical Pro", "PREFERS"), ("Scarpa F1", "Chamonix", "APPLIES_TO")],
     "which fast-and-light boot won out after a Chamonix hut link and what closure system sealed it",
     "scarpa f1 dynafit radical pro chamonix boa hut link transition"),
    # --- 12. milestone ---
    ("Skied the Grand Couloir at La Grave for the first time in March with a local guide from AvSar; the entry slot was firm Styrofoam over an ice plate, and the exit apron was reset corn by two p.m.", "milestone", "personal", False,
     [("La Grave", "place"), ("Grand Couloir", "place"), ("AvSar", "organization")],
     [("Grand Couloir", "La Grave", "LOCATED_IN")],
     "which La Grave line got its first descent in March and which guide service arranged the local",
     "la grave grand couloir avsar guide styrofoam ice plate corn"),
    # --- 13. fact ---
    ("Jeremy Jones's Teton Gravity Research segment on the Jones Mountain Twin had a thirty-second lap through Japanese birch that bumped the Niseko trip to the top of the winter calendar.", "fact", "personal", False,
     [("Jeremy Jones", "person"), ("Teton Gravity Research", "organization"), ("Jones Mountain Twin", "tool"), ("Niseko", "place")],
     [("Jeremy Jones", "Jones Mountain Twin", "APPLIES_TO"), ("Jones Mountain Twin", "Niseko", "LOCATED_IN")],
     "which Jeremy Jones edit pushed Niseko to the top of the winter calendar",
     "jeremy jones tgr jones mountain twin niseko birch segment"),
    # --- 14. reference ---
    ("The Wasatch touring gospel points at Andrew McLean's trip reports and the UAC observation feed; both feeds load in the ski folder before any dawn-patrol drive toward Alta or Snowbird.", "reference", "personal", False,
     [("Andrew McLean", "person"), ("UAC", "organization"), ("Alta", "place"), ("Snowbird", "place")],
     [("UAC", "Alta", "APPLIES_TO"), ("UAC", "Snowbird", "APPLIES_TO")],
     "which two feeds anchor a dawn-patrol call toward Alta or Snowbird in the Wasatch",
     "andrew mclean uac observation alta snowbird dawn patrol feed"),
    # --- 15. decision ---
    ("Chose the Black Crows Ova over the Rossignol Sender for the partner's all-mountain ski after a demo day at Snowbird; the Ova's rocker profile pivoted faster in tight trees without losing the carving feel on the ride back.", "decision", "personal", False,
     [("Black Crows Ova", "tool"), ("Rossignol Sender", "tool"), ("Snowbird", "place")],
     [("Black Crows Ova", "Rossignol Sender", "PREFERS"), ("Black Crows Ova", "Snowbird", "APPLIES_TO")],
     "which all-mountain ski edged the Rossignol Sender at a Snowbird demo day for a partner's daily driver",
     "black crows ova rossignol sender snowbird demo tree pivot rocker"),
    # --- 16. architecture ---
    ("Beacon-check flow before any backcountry drop is fixed: everyone powers on the Mammut Barryvox, the leader switches to search, every partner's unit confirms send range, and the leader flips back to send before skinning.", "architecture", "personal", False,
     [("Mammut Barryvox", "tool"), ("Beacon-check", "concept"), ("skinning", "activity")],
     [],
     "what is the Barryvox beacon-check flow the group runs before any backcountry drop",
     "mammut barryvox beacon check send search range leader skin flow"),
    # --- 17. preference ---
    ("Prefer Pomoca skins over Black Diamond Ascension for long days because the glide on the flat skin-track approach into Alta's Cardiac Ridge saves a measurable fifteen minutes over a Ascension set cut to the same ski.", "preference", "personal", False,
     [("Pomoca", "tool"), ("Black Diamond Ascension", "tool"), ("Alta", "place"), ("Cardiac Ridge", "place")],
     [("Pomoca", "Black Diamond Ascension", "PREFERS"), ("Cardiac Ridge", "Alta", "LOCATED_IN")],
     "which skin brand saves measurable time on Alta's Cardiac Ridge approach over the Ascension alternative",
     "pomoca black diamond ascension alta cardiac ridge skin glide approach"),
    # --- 18. decision ---
    ("The resort-only ski setup moved from the Nordica Enforcer to the Moment Wildcat after a week at Jackson Hole; the extra width under foot floated Corbet's entrance better and damp-cored the chop on Rendezvous lap-two.", "decision", "personal", False,
     [("Nordica Enforcer", "tool"), ("Moment Wildcat", "tool"), ("Jackson Hole", "place"), ("Corbet's", "place"), ("Rendezvous", "place")],
     [("Moment Wildcat", "Nordica Enforcer", "REPLACES"), ("Corbet's", "Jackson Hole", "LOCATED_IN"), ("Rendezvous", "Jackson Hole", "LOCATED_IN")],
     "which resort ski replaced the Nordica Enforcer after a Jackson Hole week and which features won the swap",
     "nordica enforcer moment wildcat jackson hole corbet rendezvous float"),
    # --- 19. architecture ---
    ("The avalanche rescue load order in my pack is deliberate: Ortovox Diract Voice goes on the chest strap with send confirmed, probe and shovel ride in the hydration sleeve for one-motion deploys, airbag handle stays clipped to the left shoulder so the right hand can ski a cornice exit unencumbered.", "architecture", "personal", False,
     [("Ortovox Diract Voice", "tool"), ("probe", "tool"), ("shovel", "tool"), ("airbag", "tool")],
     [("Ortovox Diract Voice", "airbag", "RELATED_TO")],
     "how does the rescue pack lay out beacon, probe, shovel, and airbag handle for one-motion deploys",
     "ortovox diract voice probe shovel airbag handle pack load order"),
    # --- 20. decision ---
    ("Replaced the Pieps Micro after the widely-circulated inadvertent power-off reports; the Ortovox Diract Voice took the slot because voice-prompt search coaching helps the less-experienced partners on rescue drills.", "decision", "personal", False,
     [("Pieps Micro", "tool"), ("Ortovox Diract Voice", "tool")],
     [("Ortovox Diract Voice", "Pieps Micro", "REPLACES")],
     "which beacon replaced the Pieps Micro after the inadvertent-power-off reports and what feature justified it",
     "pieps micro ortovox diract voice power off rescue drill voice prompt"),
    # --- 21. fact ---
    ("Lindsey Vonn's downhill line commentary during the Cortina coverage last winter hammered on ankle compression through compressions; the cue fed straight into a week of drills on the Salomon Assassin snowboard.", "fact", "personal", False,
     [("Lindsey Vonn", "person"), ("Cortina", "place"), ("Salomon Assassin", "tool")],
     [("Lindsey Vonn", "Cortina", "LOCATED_IN")],
     "which racer's Cortina commentary cue fed a week of compression drills on the Salomon Assassin",
     "lindsey vonn cortina downhill ankle compression salomon assassin drill"),
    # --- 22. architecture ---
    ("The Salomon S/Lab Shift goes on the sidecountry ski because the DIN-certified alpine heel holds through a Jackson Hole cliff-band exit while the pin-toe saves weight on the skin back to the tram; no other binding splits those two duties cleanly.", "architecture", "personal", False,
     [("Salomon S/Lab Shift", "tool"), ("Jackson Hole", "place"), ("DIN", "concept")],
     [("Salomon S/Lab Shift", "Jackson Hole", "APPLIES_TO")],
     "which binding splits DIN-alpine descents and pin-toe skin returns cleanly for Jackson Hole sidecountry",
     "salomon slab shift jackson hole sidecountry din alpine pin toe"),
    # --- 23. milestone ---
    ("Logged fifty backcountry days this winter by the second week of April; the Blizzard Zero G with Dynafit Ridge Pro carried most of the tally without a single binding service between November and March.", "milestone", "personal", False,
     [("Blizzard Zero G", "tool"), ("Dynafit Ridge Pro", "tool")],
     [("Blizzard Zero G", "Dynafit Ridge Pro", "USES")],
     "which touring setup carried a fifty-day backcountry tally through the winter without a service stop",
     "blizzard zero g dynafit ridge pro fifty backcountry day tally winter"),
    # --- 24. reference ---
    ("The Bruce Tremper book Staying Alive in Avalanche Terrain still sits on the nightstand every December re-read; pages on terrain traps and persistent slab problems anchor the partner's first-season coaching more than any video.", "reference", "personal", False,
     [("Bruce Tremper", "person"), ("Staying Alive in Avalanche Terrain", "publication")],
     [("Staying Alive in Avalanche Terrain", "Bruce Tremper", "AUTHORED_BY")],
     "which Bruce Tremper book re-read every December anchors a first-season partner's avalanche coaching",
     "bruce tremper staying alive avalanche terrain persistent slab trap"),
    # --- 25. decision ---
    ("Booked a week at Niseko over a repeat trip to Chamonix because the January storm cycle in Hokkaido produces more chest-deep tree days per week than the Aiguille du Midi gives in a fair season.", "decision", "personal", False,
     [("Niseko", "place"), ("Chamonix", "place"), ("Hokkaido", "place"), ("Aiguille du Midi", "place")],
     [("Niseko", "Hokkaido", "LOCATED_IN"), ("Aiguille du Midi", "Chamonix", "LOCATED_IN"), ("Niseko", "Chamonix", "PREFERS")],
     "which January destination beat a repeat Chamonix trip for reliable chest-deep tree days",
     "niseko chamonix hokkaido aiguille du midi january tree storm cycle"),
    # --- 26. problem ---
    ("A skin glue failure on the Gecko set at minus twenty in the Wasatch cost an hour of the tour to re-glue with a trailside kit; switched back to Pomoca for any day forecast below zero Fahrenheit.", "problem", "personal", False,
     [("Gecko", "tool"), ("Pomoca", "tool"), ("Wasatch", "place")],
     [("Pomoca", "Gecko", "REPLACES"), ("Gecko", "Wasatch", "APPLIES_TO")],
     "which skin brand failed at minus twenty in the Wasatch and what brand took its slot for cold days",
     "gecko pomoca wasatch skin glue failure cold minus twenty tour"),
    # --- 27. architecture ---
    ("The ski-trip budget is split three ways: fixed travel into the resort hub, a daily guide or lift pass block, and a contingency line for a rescue helicopter ride anywhere outside Jackson Hole or Alta where my insurance covers ambulance only.", "architecture", "personal", False,
     [("Jackson Hole", "place"), ("Alta", "place")],
     [("Jackson Hole", "Alta", "RELATED_TO")],
     "how does the ski-trip budget partition travel, pass, and helicopter-contingency lines by destination",
     "budget travel resort hub daily guide lift helicopter insurance ambulance"),
    # --- 28. fact ---
    ("The Yes Hybrid snowboard's magne-traction edges held a Niseko side-hit landing on refrozen crust that would have washed out the Burton Custom twin I demoed the prior week.", "fact", "personal", False,
     [("Yes Hybrid", "tool"), ("Burton Custom", "tool"), ("Niseko", "place")],
     [("Yes Hybrid", "Niseko", "APPLIES_TO")],
     "which snowboard edged out the Burton Custom on a refrozen Niseko side-hit landing",
     "yes hybrid burton custom niseko magne traction refrozen crust"),
    # --- 29. decision ---
    ("Decided to own a Weston Backwoods splitboard rather than rent at the trailhead for splitboard days; the per-day cost broke even at twelve days and the personal setup saves the hour of shop-time each morning.", "decision", "personal", False,
     [("Weston Backwoods", "tool"), ("splitboard", "activity")],
     [("Weston Backwoods", "splitboard", "APPLIES_TO")],
     "which splitboard did the math to own rather than rent and at how many days did it break even",
     "weston backwoods splitboard rent own break even twelve day shop"),
    # --- 30. architecture ---
    ("Avalanche decision making runs a three-filter stack before any ski-cut: the regional forecast danger rose, a trailhead observation round against the day's problem list, and a slope-scale pit or hand-shear on the first aspect at or above thirty degrees.", "architecture", "personal", False,
     [("danger rose", "concept"), ("problem list", "concept"), ("pit", "concept"), ("ski-cut", "activity")],
     [("danger rose", "problem list", "RELATED_TO")],
     "which three filters gate every ski-cut decision before dropping into avalanche terrain",
     "danger rose problem list pit hand shear ski cut aspect thirty filter"),
    # --- 31. fact ---
    ("The Dalbello Lupo fit the narrow navicular better than the Atomic Hawx Ultra XTD on the left foot; a custom Intuition liner bake closed the last half-size gap and killed the Achilles hot-spot on day-three tours.", "fact", "personal", False,
     [("Dalbello Lupo", "tool"), ("Atomic Hawx Ultra XTD", "tool"), ("Intuition", "tool")],
     [("Intuition", "Dalbello Lupo", "APPLIES_TO")],
     "which boot fit the narrow navicular better than the Hawx and which liner bake closed the gap",
     "dalbello lupo atomic hawx intuition liner navicular achilles hot spot"),
    # --- 32. decision ---
    ("Moved resort pass dollars from the multi-resort bundle to a single Jackson Hole pass this season because the driving radius from the cabin hit twelve days out of fifteen at Jackson and only four at the other resorts combined.", "decision", "personal", False,
     [("Jackson Hole", "place")],
     [],
     "which resort pass replaced the multi-resort bundle this season based on driving-radius day counts",
     "jackson hole resort pass multi bundle driving radius cabin day count"),
    # --- 33. architecture ---
    ("The pre-tour checklist is a paper card in the glovebox: beacon battery above seventy percent, probe length matched to partner count, shovel metal blade not plastic, skins dry from last outing, and a printout of the morning Wasatch Snow Forecast danger rose.", "architecture", "personal", False,
     [("Wasatch Snow Forecast", "tool"), ("beacon", "tool"), ("probe", "tool"), ("shovel", "tool")],
     [("beacon", "Wasatch Snow Forecast", "RELATED_TO")],
     "what five items does the glovebox pre-tour checklist gate before leaving the trailhead",
     "checklist glovebox beacon battery probe shovel skin wasatch forecast"),
    # --- 34. preference ---
    ("Prefer skinning in the Dynafit Radical Pro with the second buckle open and the cuff latch hooked at the calf; walk-mode range in that configuration beats the Scarpa F1 for anything steeper than thirty degrees on the up.", "preference", "personal", False,
     [("Dynafit Radical Pro", "tool"), ("Scarpa F1", "tool")],
     [("Dynafit Radical Pro", "Scarpa F1", "PREFERS")],
     "which boot and cuff configuration beats the Scarpa F1 on anything steeper than thirty degrees up",
     "dynafit radical pro scarpa f1 walk mode buckle cuff skin steep"),
    # --- 35. milestone ---
    ("Completed AIARE Level 2 at Alta the winter after Level 1 and the field day produced a textbook layered pit on a north aspect; the course debrief marked a clean jump in snowpack-reading confidence that the next Jackson Hole trip immediately cashed in.", "milestone", "personal", False,
     [("AIARE Level 2", "event"), ("Alta", "place"), ("Jackson Hole", "place")],
     [("AIARE Level 2", "Alta", "LOCATED_IN")],
     "which avalanche course finished at Alta bumped snowpack-reading confidence before the next Jackson Hole trip",
     "aiare level 2 alta jackson hole field day layered pit north aspect"),
    # --- 36. decision ---
    ("Bought the DPS Pagoda over the DPS Pagoda Tour for the resort ski because the heavier chassis damps Alta's afternoon chop; kept the Pagoda Tour for the dedicated touring quiver rather than trying to swing one ski across both jobs.", "decision", "personal", False,
     [("DPS Pagoda", "tool"), ("DPS Pagoda Tour", "tool"), ("Alta", "place")],
     [("DPS Pagoda", "DPS Pagoda Tour", "PREFERS"), ("DPS Pagoda", "Alta", "APPLIES_TO")],
     "which DPS model won the resort slot and why did the Pagoda Tour stay in the touring quiver",
     "dps pagoda pagoda tour alta resort touring chassis damp chop"),
    # --- 37. reference ---
    ("The Black Diamond Snow Study Kit card in the pack lists crystal-shape ID and the ECT scoring rubric; it has settled more trailside debates on a suspicious persistent slab than any phone app.", "reference", "personal", False,
     [("Black Diamond Snow Study Kit", "tool"), ("ECT", "method"), ("persistent slab", "concept")],
     [("Black Diamond Snow Study Kit", "ECT", "HAS_PART")],
     "which pocket card settles trailside debates on crystal ID and ECT scoring faster than a phone app",
     "black diamond snow study kit ect persistent slab crystal shape card"),
    # --- 38. fact ---
    ("A full day at Chamonix off the Aiguille du Midi with a UIAGM guide opened the Vallée Blanche variations I would never have strung together solo; the Grand Envers exit took four rappels and the guide's short-rope on the arete saved forty minutes.", "fact", "personal", False,
     [("Chamonix", "place"), ("Aiguille du Midi", "place"), ("UIAGM", "organization"), ("Vallée Blanche", "place"), ("Grand Envers", "place")],
     [("Aiguille du Midi", "Chamonix", "LOCATED_IN"), ("Vallée Blanche", "Chamonix", "LOCATED_IN"), ("Grand Envers", "Chamonix", "LOCATED_IN")],
     "which Chamonix descent off the Aiguille du Midi strung variations I couldn't link solo and saved forty minutes on the arete",
     "chamonix aiguille midi uiagm vallee blanche grand envers rappel"),
    # --- 39. architecture ---
    ("Backcountry partner vetting is a two-gate rule: they must show a current avalanche course card and run a clean beacon-probe-shovel rescue drill in under seven minutes before the first real tour together; no exceptions for old friendships.", "architecture", "personal", False,
     [("avalanche course", "concept"), ("beacon-probe-shovel", "concept"), ("rescue drill", "activity")],
     [("beacon-probe-shovel", "rescue drill", "USES")],
     "which two gates must a new backcountry partner clear before the first real tour together",
     "avalanche course card beacon probe shovel rescue drill seven minute"),
    # --- 40. fact ---
    ("Swapped the Dynafit Ridge Pro heel piece to the five-mil riser block after a trip in the Tetons; the standard riser cooked calves on the long low-angle skin-track out of the drainage into Garnet Canyon.", "fact", "personal", False,
     [("Dynafit Ridge Pro", "tool"), ("Tetons", "place"), ("Garnet Canyon", "place")],
     [("Garnet Canyon", "Tetons", "LOCATED_IN")],
     "which riser block change on the Ridge Pro came out of a Tetons skin-track into Garnet Canyon",
     "dynafit ridge pro riser block teton garnet canyon calf skin track"),
    # --- 41. reference ---
    ("The UAC observation page on snowpack.org reads like a journal each morning; clicking a pin drops the observer's full pit profile and the comment field is where the sharpest persistent-weak-layer calls surface first.", "reference", "personal", False,
     [("UAC", "organization"), ("snowpack.org", "tool"), ("persistent-weak-layer", "concept")],
     [("snowpack.org", "UAC", "HAS_PART")],
     "which UAC observation page surfaces persistent-weak-layer calls and pit profiles each morning",
     "uac snowpack org observation pit profile persistent weak layer pin"),
    # --- 42. preference ---
    ("Prefer the Look Pivot over every other alpine binding for the resort ski because the long elastic travel keeps the ski on through the hardest Jackson Hole landings; no amount of weight savings from a frame binding has closed that gap.", "preference", "personal", False,
     [("Look Pivot", "tool"), ("Jackson Hole", "place")],
     [("Look Pivot", "Jackson Hole", "APPLIES_TO")],
     "which alpine binding's elastic travel keeps skis on through Jackson Hole's hardest landings",
     "look pivot alpine binding jackson hole elastic travel landing retention"),
    # --- 43. noise ---
    ("The hall closet door swings half-open every time the furnace kicks on and the latch plate is due for a shim before winter.", "fact", "noise", True, [], [], None, None),
    # --- 44. milestone ---
    ("Hit a personal first by dropping a clean line down the east face at La Grave without a single side-slip section; the Völkl Mantra held the crux rollover on refrozen dust-on-crust that demanded full commitment.", "milestone", "personal", False,
     [("La Grave", "place"), ("Völkl Mantra", "tool")],
     [("Völkl Mantra", "La Grave", "APPLIES_TO")],
     "which La Grave east-face descent went clean with the Völkl Mantra on refrozen dust-on-crust",
     "la grave east face volkl mantra rollover dust crust side slip"),
    # --- 45. problem ---
    ("A tech-toe pre-release on the Fritschi Xenic at Alta's High Rustler traced to ice packed in the front pincer; cleared the ice with the probe pick and recalibrated the adjustable lateral step by step on the bench that night.", "problem", "personal", False,
     [("Fritschi Xenic", "tool"), ("Alta", "place"), ("High Rustler", "place")],
     [("High Rustler", "Alta", "LOCATED_IN")],
     "which pre-release on the Fritschi Xenic at Alta traced to ice in the toe pincer",
     "fritschi xenic alta high rustler pre release ice toe pincer"),
    # --- 46. milestone ---
    ("Logged a hundred-thousand vertical feet of human-powered skiing this winter for the first time; the tracking spreadsheet rolled over on a Wasatch dawn patrol up to Cardiac Ridge on the Atomic Backland.", "milestone", "personal", False,
     [("Wasatch", "place"), ("Cardiac Ridge", "place"), ("Atomic Backland", "tool")],
     [("Cardiac Ridge", "Wasatch", "LOCATED_IN"), ("Atomic Backland", "Cardiac Ridge", "APPLIES_TO")],
     "which Wasatch dawn patrol rolled the human-powered vertical spreadsheet past one hundred thousand feet",
     "hundred thousand vertical human powered wasatch cardiac ridge backland"),
    # --- 47. decision ---
    ("Chose the Black Crows Orb Freebird for a partner who wanted a forgiving touring ski over the Salomon MTN; the softer flex pattern matched their weight better and the turn radius closed tight trees without the tail-hook the MTN showed in slush.", "decision", "personal", False,
     [("Black Crows Orb Freebird", "tool"), ("Salomon MTN", "tool")],
     [("Black Crows Orb Freebird", "Salomon MTN", "PREFERS")],
     "which forgiving touring ski beat the Salomon MTN for a lighter partner and what failure mode swayed it",
     "black crows orb freebird salomon mtn forgiving touring flex slush"),
    # --- 48. milestone ---
    ("Summit-and-ski of Mount Baker in late May closed out the season; the volcanic corn on the Coleman-Deming was the best surface of the whole winter and the Salomon MTN handled the full carry to the top just fine.", "milestone", "personal", False,
     [("Mount Baker", "place"), ("Coleman-Deming", "place"), ("Salomon MTN", "tool")],
     [("Coleman-Deming", "Mount Baker", "LOCATED_IN"), ("Salomon MTN", "Mount Baker", "APPLIES_TO")],
     "which May summit-and-ski closed the season and which route served the volcanic corn",
     "mount baker coleman deming salomon mtn may corn summit ski volcanic"),
    # --- 49. reference ---
    ("The Dawn Patrol podcast episode with Kit DesLauriers on Grand Teton ski descents still gets a re-listen the night before any big Teton line; the terrain-choice logic on the Ford-Stettner couloir is a masterclass by itself.", "reference", "personal", False,
     [("Dawn Patrol", "publication"), ("Kit DesLauriers", "person"), ("Grand Teton", "place"), ("Ford-Stettner", "place")],
     [("Ford-Stettner", "Grand Teton", "LOCATED_IN"), ("Dawn Patrol", "Kit DesLauriers", "APPLIES_TO")],
     "which podcast episode with Kit DesLauriers gets a re-listen before any big Teton line",
     "dawn patrol kit deslauriers grand teton ford stettner couloir"),
    # --- 50. problem ---
    ("The ATK R12 heel tower loosened mid-tour on a rocky traverse out of Little Cottonwood Canyon; a fresh thread-locker application and a torque-wrench check every fourth tour cleared the repeat issue for the rest of the season.", "problem", "personal", False,
     [("ATK R12", "tool"), ("Little Cottonwood Canyon", "place"), ("thread-locker", "tool")],
     [("ATK R12", "Little Cottonwood Canyon", "APPLIES_TO")],
     "which ATK R12 failure mode came out of Little Cottonwood Canyon and what torque routine fixed it",
     "atk r12 little cottonwood heel tower thread locker torque traverse"),
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
