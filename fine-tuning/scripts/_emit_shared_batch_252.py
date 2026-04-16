"""One-off emitter for shared-base batch-252 — personal domain (birding and ornithology: eBird, Merlin, BirdNET, xeno-canto, taxonomy, optics, field guides, target species, migration, citizen science).

Writes 50 rows to data/v2/shared/batch_252.tmp.jsonl with ids shared-12551..12600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_252.tmp.jsonl"
ID_OFFSET = 12550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Moved all daily bird lists from paper notebooks to eBird after the Cornell Lab of Ornithology rolled out offline checklist sync in the mobile app; trip totals now backfill to the life list automatically.", "decision", "personal", False,
     [("eBird", "tool"), ("Cornell Lab of Ornithology", "organization"), ("life list", "concept")],
     [("eBird", "Cornell Lab of Ornithology", "APPLIES_TO")],
     "which platform replaced paper notebooks for daily bird lists and who runs it",
     "ebird cornell lab ornithology paper notebook offline sync life list"),
    # --- 2 ---
    ("Switched phone-based ID from Merlin Bird ID photo pack to the Sound ID module after a pelagic trip off Cape Hatteras; the audio model picked up a distant Black-capped Petrel that the photo model missed.", "decision", "personal", False,
     [("Merlin Bird ID", "tool"), ("Sound ID", "method"), ("Black-capped Petrel", "concept"), ("Cape Hatteras", "place")],
     [("Sound ID", "Merlin Bird ID", "REPLACES"), ("Black-capped Petrel", "Cape Hatteras", "LOCATED_IN")],
     "which Merlin module replaced the photo pack after a pelagic trip and which species sealed the choice",
     "merlin bird sound photo pelagic cape hatteras black capped petrel"),
    # --- 3 ---
    ("Running BirdNET on a backyard Raspberry Pi picked up a Barred Owl duet at 2 a.m. that I would never have heard asleep; the nightly spectrograms now anchor the yard list for nocturnal species.", "architecture", "personal", False,
     [("BirdNET", "tool"), ("Raspberry Pi", "platform"), ("Barred Owl", "concept"), ("spectrogram", "concept")],
     [("BirdNET", "Raspberry Pi", "DEPLOYED_ON")],
     "which acoustic classifier running on a Pi caught the nocturnal owl duet nobody was awake for",
     "birdnet raspberry pi barred owl duet nocturnal spectrogram yard list"),
    # --- 4 ---
    ("Uploaded a tricky Empidonax flycatcher recording to xeno-canto; within a week a curator tagged it as Alder Flycatcher on fee-bee-o call alone, which nailed an ID the visual guide could not resolve.", "fact", "personal", False,
     [("xeno-canto", "tool"), ("Empidonax", "concept"), ("Alder Flycatcher", "concept")],
     [("Alder Flycatcher", "Empidonax", "IS_A")],
     "which recording archive confirmed the silent Empidonax and what call clinched the species",
     "xeno canto empidonax alder flycatcher fee bee recording curator"),
    # --- 5 ---
    ("Joined the local Audubon Society chapter in autumn and the winter feeder walks tripled the backyard list; the chapter newsletter also funnels rare-bird alert texts that the eBird needs-alert misses.", "decision", "personal", False,
     [("Audubon Society", "organization"), ("rare-bird alert", "concept"), ("eBird", "tool")],
     [("Audubon Society", "rare-bird alert", "PRODUCES")],
     "which membership unlocked winter feeder walks and rare-bird texts the eBird alerts did not carry",
     "audubon society chapter winter feeder walk rare bird alert ebird"),
    # --- 6 ---
    ("Adopted the Clements checklist as the life-list backbone because it is the eBird taxonomy of record; the IOC World Bird List still holds for overseas trip reports where splits land earlier in the year.", "architecture", "personal", False,
     [("Clements", "method"), ("eBird", "tool"), ("IOC World Bird List", "publication"), ("life-list", "concept")],
     [("eBird", "Clements", "USES")],
     "which two taxonomies split duty between the home life list and overseas trip reports",
     "clements ebird taxonomy ioc world bird list split life overseas"),
    # --- 7 ---
    ("BirdLife International's Data Zone underpins the conservation-status column in the spreadsheet; a yearly pull aligns the IUCN categories against the checklist so Endangered and Vulnerable highlights stay current.", "architecture", "personal", False,
     [("BirdLife International", "organization"), ("Data Zone", "tool"), ("IUCN", "organization")],
     [("Data Zone", "BirdLife International", "HAS_PART"), ("Data Zone", "IUCN", "USES")],
     "which conservation dataset feeds the life-list spreadsheet and what yearly sync keeps it current",
     "birdlife international data zone iucn conservation status endangered"),
    # --- 8 ---
    ("Committed to a Big Year across the ABA Area after hitting 400 species by March; logistics lean on weekly eBird county-level bar charts to route chase days around stakeouts rather than cold searching.", "milestone", "personal", False,
     [("Big Year", "event"), ("ABA Area", "place"), ("eBird", "tool")],
     [("Big Year", "ABA Area", "LOCATED_IN"), ("Big Year", "eBird", "USES")],
     "which Big Year kicked off after March crossed four hundred species and which planning tool drove chase routing",
     "big year aba area ebird county chart chase stakeout route"),
    # --- 9 ---
    ("Ran a Big Day in New Jersey on the second Saturday of May and cleared 178 species; the route hit Cape May at dawn, Brigantine midday, and the Kittatinny ridge for hawk flight at dusk.", "milestone", "personal", False,
     [("Big Day", "event"), ("New Jersey", "place"), ("Cape May", "place"), ("Brigantine", "place"), ("Kittatinny", "place")],
     [("Big Day", "New Jersey", "LOCATED_IN"), ("Big Day", "Cape May", "VISITED")],
     "which Big Day route ran Cape May to the Kittatinny ridge and cleared 178 in one Saturday",
     "big day new jersey cape may brigantine kittatinny hawk ridge"),
    # --- 10. noise ---
    ("The kitchen sink tap developed a slow drip that empties a mug overnight and the washer kit on the shelf is missing a gasket.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Pelagic birding off Monterey Bay on the Debi Lynn run produced a Laysan Albatross on the second drift; the chum slick pulled in Black-footed Albatross within ten minutes of engine shutdown.", "fact", "personal", False,
     [("Monterey Bay", "place"), ("Debi Lynn", "tool"), ("Laysan Albatross", "concept"), ("Black-footed Albatross", "concept")],
     [("Laysan Albatross", "Monterey Bay", "LOCATED_IN"), ("Black-footed Albatross", "Monterey Bay", "LOCATED_IN")],
     "which Monterey Bay charter produced the Laysan Albatross and what pulled in Black-footed on the same drift",
     "pelagic monterey bay debi lynn laysan black footed albatross chum"),
    # --- 12 ---
    ("Hawkwatching at Cape May Point in late September stacks Sharp-shinned Hawks into the thousands on a northwest front; the official counter posts daily tallies that make a one-day chase worthwhile.", "fact", "personal", False,
     [("Cape May Point", "place"), ("Sharp-shinned Hawk", "concept"), ("northwest front", "concept")],
     [("Sharp-shinned Hawk", "Cape May Point", "LOCATED_IN")],
     "which weather pattern stacks Sharp-shinned Hawks at Cape May Point in late September",
     "cape may point sharp shinned hawk northwest front september count"),
    # --- 13 ---
    ("Hawk Mountain in Pennsylvania runs the oldest raptor count in the world; the North Lookout tallies that underpin Broad-winged Hawk population trends date back to 1934.", "reference", "personal", False,
     [("Hawk Mountain", "place"), ("Pennsylvania", "place"), ("North Lookout", "place"), ("Broad-winged Hawk", "concept")],
     [("Hawk Mountain", "Pennsylvania", "LOCATED_IN"), ("North Lookout", "Hawk Mountain", "LOCATED_IN")],
     "which Pennsylvania lookout has counted raptors since 1934 and which species anchors the long-term trend",
     "hawk mountain pennsylvania north lookout broad winged 1934 count"),
    # --- 14 ---
    ("Participated in the Christmas Bird Count for the fifth straight year on the Lakeshore circle; the compiler pairs new volunteers with veteran teams so rare half-hardy species get logged consistently.", "decision", "personal", False,
     [("Christmas Bird Count", "event"), ("Lakeshore", "place"), ("compiler", "person")],
     [("Christmas Bird Count", "Lakeshore", "LOCATED_IN")],
     "which long-running winter census ran for a fifth year on the Lakeshore circle and how are new volunteers paired",
     "christmas bird count lakeshore circle compiler veteran half hardy"),
    # --- 15 ---
    ("Upgraded the daily carry to the Swarovski NL Pure 8x42 after a decade on Nikon Monarch; the field-flattener glass and the 159 m field of view make warbler neck a non-issue through the canopy.", "decision", "personal", False,
     [("Swarovski NL Pure 8x42", "tool"), ("Nikon Monarch", "tool")],
     [("Swarovski NL Pure 8x42", "Nikon Monarch", "REPLACES")],
     "which binocular replaced the Nikon Monarch as daily carry and what glass trait sold the upgrade",
     "swarovski nl pure 8x42 nikon monarch field flattener canopy warbler"),
    # --- 16 ---
    ("Picked Zeiss SF 10x42 over the Leica Noctivid for shorebird work; the SmartFocus wheel under a gloved finger beats the Leica's stiffer focus on a cold Delaware Bay morning.", "preference", "personal", False,
     [("Zeiss SF 10x42", "tool"), ("Leica Noctivid", "tool"), ("Delaware Bay", "place"), ("shorebird", "concept")],
     [("Zeiss SF 10x42", "Leica Noctivid", "PREFERS"), ("shorebird", "Delaware Bay", "LOCATED_IN")],
     "which binocular wins for Delaware Bay shorebird work and which feature breaks the tie with the Leica",
     "zeiss sf 10x42 leica noctivid smartfocus glove delaware bay shorebird"),
    # --- 17 ---
    ("Vortex Razor UHD 10x42 rides the loaner hook for group walks; the no-fault lifetime warranty means a dropped pair comes back rebuilt without an argument about who was holding it.", "fact", "personal", False,
     [("Vortex Razor UHD", "tool"), ("lifetime warranty", "concept")],
     [("Vortex Razor UHD", "lifetime warranty", "SUPPORTS")],
     "which binocular sits on the loaner hook and why does the warranty matter for group walks",
     "vortex razor uhd 10x42 loaner group walk lifetime warranty drop"),
    # --- 18 ---
    ("Spotting scope set long-settled on the Kowa TSN-88 after a head-to-head against the Swarovski ATX 85; the Kowa's pure-fluorite objective pulls gull primary projection on a distant sandbar that the ATX blurs.", "decision", "personal", False,
     [("Kowa TSN-88", "tool"), ("Swarovski ATX 85", "tool"), ("gull", "concept"), ("fluorite", "concept")],
     [("Kowa TSN-88", "Swarovski ATX 85", "PREFERS")],
     "which spotting scope won the head-to-head over the ATX 85 for distant gull work on a sandbar",
     "kowa tsn 88 swarovski atx 85 fluorite gull primary sandbar"),
    # --- 19 ---
    ("Meopta MeoStar 8x42 serves as the travel binocular because it survives checked baggage without a recollimation trip; the MeoBright coatings hold contrast on hazy tropical mornings too.", "fact", "personal", False,
     [("Meopta MeoStar 8x42", "tool"), ("MeoBright", "concept")],
     [("MeoBright", "Meopta MeoStar 8x42", "HAS_PART")],
     "which binocular handles checked baggage for travel and which coating keeps tropical contrast",
     "meopta meostar 8x42 meobright checked baggage travel tropical contrast"),
    # --- 20 ---
    ("David Sibley's Sibley Guide to Birds of North America lives on the kitchen table for daily reference; the second edition's expanded western coverage and side-by-side plumage panels made the Peterson go into storage.", "preference", "personal", False,
     [("Sibley Guide to Birds of North America", "publication"), ("Peterson", "publication"), ("David Sibley", "person")],
     [("Sibley Guide to Birds of North America", "Peterson", "REPLACES"), ("Sibley Guide to Birds of North America", "David Sibley", "AUTHORED_BY")],
     "which field guide replaced the Peterson on the kitchen table and who wrote it",
     "sibley guide birds north america peterson second edition western plumage"),
    # --- 21 ---
    ("Collins Bird Guide is the go-to for any UK or WP trip; the Svensson illustrations render pale fringes on immature gulls at a fidelity that photos still miss.", "preference", "personal", False,
     [("Collins Bird Guide", "publication"), ("Svensson", "person"), ("WP", "place")],
     [("Collins Bird Guide", "Svensson", "AUTHORED_BY")],
     "which guide travels on UK trips and which illustrator nails the fine gull fringes",
     "collins bird guide svensson wp uk immature gull pale fringe"),
    # --- 22 ---
    ("Kenn Kaufman's Field Guide to Birds of North America works as a beginner gift; the digitally enhanced photo plates and the plain-language captions lower the reading barrier for new birders.", "fact", "personal", False,
     [("Kenn Kaufman", "person"), ("Field Guide to Birds of North America", "publication")],
     [("Field Guide to Birds of North America", "Kenn Kaufman", "AUTHORED_BY")],
     "which guide works as a beginner gift and who authored the photo-plate approach",
     "kenn kaufman field guide birds digital photo plain language beginner"),
    # --- 23 ---
    ("The Crossley ID Guide sits on the shelf as a study tool rather than a field reference; the full-scene composites with birds at distance train the eye for jizz-based ID in a way plates cannot.", "fact", "personal", False,
     [("Crossley ID Guide", "publication"), ("jizz", "concept")],
     [("Crossley ID Guide", "jizz", "APPLIES_TO")],
     "which guide acts as a study tool rather than a field book and what ID skill do its composites train",
     "crossley id guide full scene composite jizz distance study tool"),
    # --- 24 ---
    ("Chased a California Condor at Big Sur in May and tag 82 soared the ridge within an hour; the Ventana Wildlife Society tracking feed said a carcass was below the parking area that morning.", "milestone", "personal", False,
     [("California Condor", "concept"), ("Big Sur", "place"), ("Ventana Wildlife Society", "organization")],
     [("California Condor", "Big Sur", "LOCATED_IN"), ("Ventana Wildlife Society", "California Condor", "RELATED_TO")],
     "which May chase landed a California Condor at Big Sur and which tracking feed narrowed the wait",
     "california condor big sur tag 82 ventana wildlife society carcass"),
    # --- 25 ---
    ("Kirtland's Warbler seen on territory in the Grayling jack pine plains during a guided USFWS tour; the birds used to be locked behind permit-only access and the tour system balances viewing against nesting pressure.", "milestone", "personal", False,
     [("Kirtland's Warbler", "concept"), ("Grayling", "place"), ("USFWS", "organization"), ("jack pine", "concept")],
     [("Kirtland's Warbler", "Grayling", "LOCATED_IN"), ("Kirtland's Warbler", "jack pine", "APPLIES_TO")],
     "which Michigan warbler showed on territory in the jack pine plains and which agency ran the tour",
     "kirtland warbler grayling jack pine usfws tour permit territory"),
    # --- 26 ---
    ("Ivory Gull stakeout in Plymouth Harbor on a January morning after a two-day nor'easter; the bird worked a half-eaten seal on a floe and gave scope views for over an hour before drifting out on the tide.", "milestone", "personal", False,
     [("Ivory Gull", "concept"), ("Plymouth Harbor", "place"), ("nor'easter", "event"), ("seal", "concept")],
     [("Ivory Gull", "Plymouth Harbor", "LOCATED_IN")],
     "which Plymouth Harbor stakeout produced the Ivory Gull and what weather brought it in",
     "ivory gull plymouth harbor nor easter seal floe january scope"),
    # --- 27 ---
    ("Resplendent Quetzal showed in the Monteverde cloud forest on a pre-dawn guide walk; the male flew in to a wild avocado (aguacatillo) and the tail streamers cleared a branch by a good half metre.", "milestone", "personal", False,
     [("Resplendent Quetzal", "concept"), ("Monteverde", "place"), ("aguacatillo", "food")],
     [("Resplendent Quetzal", "Monteverde", "LOCATED_IN"), ("Resplendent Quetzal", "aguacatillo", "USES")],
     "which Monteverde target landed on a pre-dawn walk and which food tree pulled the male in",
     "resplendent quetzal monteverde cloud forest aguacatillo avocado male"),
    # --- 28 ---
    ("Shoebill sighted from a dugout in the Mabamba Swamp papyrus on the Uganda leg; the bird stood motionless for forty minutes before the bill-clatter display broke the silence on the second approach.", "milestone", "personal", False,
     [("Shoebill", "concept"), ("Mabamba Swamp", "place"), ("Uganda", "place"), ("papyrus", "concept")],
     [("Shoebill", "Mabamba Swamp", "LOCATED_IN"), ("Mabamba Swamp", "Uganda", "LOCATED_IN")],
     "which Uganda swamp produced the Shoebill and what display broke the long motionless watch",
     "shoebill mabamba swamp uganda papyrus dugout bill clatter display"),
    # --- 29 ---
    ("Kakapo trip to Whenua Hou in New Zealand went through the Kakapo Recovery Programme volunteer roster; hand-reared chick Sirocco did a territorial scrape in the red beech leaf litter on the second night.", "decision", "personal", False,
     [("Kakapo", "concept"), ("Whenua Hou", "place"), ("New Zealand", "place"), ("Kakapo Recovery Programme", "organization"), ("Sirocco", "person")],
     [("Kakapo", "Whenua Hou", "LOCATED_IN"), ("Whenua Hou", "New Zealand", "LOCATED_IN"), ("Kakapo Recovery Programme", "Kakapo", "SUPPORTS")],
     "which New Zealand island produced the Kakapo target and which programme ran the volunteer roster",
     "kakapo whenua hou new zealand recovery programme sirocco red beech"),
    # --- 30 ---
    ("Migration planning leans on the Atlantic Flyway timing charts for shorebirds and the Central Flyway for passerine fallout; the Mississippi Flyway feeds the spring warbler wave at Magee Marsh each May.", "architecture", "personal", False,
     [("Atlantic Flyway", "concept"), ("Central Flyway", "concept"), ("Mississippi Flyway", "concept"), ("Magee Marsh", "place")],
     [("Mississippi Flyway", "Magee Marsh", "APPLIES_TO")],
     "which three flyways split migration planning and which one funnels warblers into Magee Marsh",
     "atlantic central mississippi flyway magee marsh warbler shorebird fallout"),
    # --- 31 ---
    ("Separating songs from calls tightened the breeding-season list a lot; a song is the long advertising phrase tied to territory and a call is the short contact or alarm note used year round.", "reference", "personal", False,
     [("song", "concept"), ("call", "concept"), ("territory", "concept")],
     [("song", "territory", "APPLIES_TO")],
     "which vocalisation distinction tightens the breeding-season list and how do song and call differ in role",
     "song call territory advertising contact alarm breeding year round"),
    # --- 32 ---
    ("Sonograms in Sibley Guide to Birds of North America and Raven Lite overlay each other well enough that I now read spectrograms before playback; the frequency-by-time pattern catches Traill's complex better than ear alone.", "architecture", "personal", False,
     [("Sonograms", "concept"), ("Sibley Guide to Birds of North America", "publication"), ("Raven Lite", "tool"), ("Traill's", "concept")],
     [("Sonograms", "Raven Lite", "USES")],
     "which sonogram tools got layered together and which flycatcher complex they resolve better than ear",
     "sonogram sibley raven lite traill frequency time spectrogram playback"),
    # --- 33 ---
    ("Pishing works on winter sparrow flocks but collapses on any breeding warbler after late May; the scold-mimicking 'psssh' pulls in chickadees fast enough that the whole flock flushes to eye level.", "reference", "personal", False,
     [("Pishing", "method"), ("chickadees", "concept"), ("sparrow", "concept")],
     [("Pishing", "chickadees", "APPLIES_TO")],
     "which technique pulls winter sparrow flocks but fails on breeding warblers and which species responds fastest",
     "pishing chickadee sparrow winter flock scold breeding warbler late may"),
    # --- 34 ---
    ("Yard feeder stack runs black-oil sunflower in the tube, safflower in the hopper, and nyjer in the sock; the safflower keeps grackles off without starving the cardinals or the tufted titmice.", "architecture", "personal", False,
     [("black-oil sunflower", "food"), ("safflower", "food"), ("nyjer", "food"), ("grackles", "concept"), ("cardinals", "concept"), ("tufted titmice", "concept")],
     [("safflower", "grackles", "APPLIES_TO")],
     "which three-seed feeder stack keeps grackles off while feeding cardinals and tufted titmice",
     "black oil sunflower safflower nyjer grackle cardinal titmouse feeder"),
    # --- 35 ---
    ("Volunteered on a bird banding station at Kiwanis Park for fall passage; the MAPS protocol runs ten mist nets for six hours and every bird gets a USGS aluminium ring and a wing-chord measurement.", "decision", "personal", False,
     [("bird banding", "activity"), ("Kiwanis Park", "place"), ("MAPS", "method"), ("USGS", "organization"), ("mist net", "tool")],
     [("MAPS", "mist net", "USES"), ("USGS", "bird banding", "SUPPORTS")],
     "which banding protocol runs ten mist nets on fall passage and which agency issues the rings",
     "banding kiwanis park maps protocol mist net usgs aluminium ring"),
    # --- 36 ---
    ("Ringing trip to the UK used the BTO scheme instead of the USGS ring; the BTO permit rules on retraps let me record a Reed Warbler caught nine years earlier on the same Norfolk reedbed.", "decision", "personal", False,
     [("Ringing", "activity"), ("BTO", "organization"), ("USGS", "organization"), ("Reed Warbler", "concept"), ("Norfolk", "place")],
     [("Ringing", "BTO", "USES"), ("Reed Warbler", "Norfolk", "LOCATED_IN")],
     "which UK ringing scheme replaced the USGS ring abroad and what retrap stood out on Norfolk reedbed",
     "ringing bto usgs reed warbler norfolk reedbed retrap nine year"),
    # --- 37 ---
    ("Citizen-science time budget splits eBird checklists daily, Project FeederWatch weekly from November, and Breeding Bird Survey routes twice each June; the three feeds answer different ecological questions.", "architecture", "personal", False,
     [("eBird", "tool"), ("Project FeederWatch", "method"), ("Breeding Bird Survey", "method"), ("Citizen-science", "concept")],
     [("Citizen-science", "eBird", "USES"), ("Citizen-science", "Breeding Bird Survey", "USES")],
     "which three citizen-science feeds split the yearly time budget and when does each run",
     "ebird project feederwatch breeding bird survey citizen science time"),
    # --- 38 ---
    ("Phoebe Snetsinger's Birding on Borrowed Time sits on the top shelf as a reminder that her 8,398-species world list came after a terminal diagnosis in 1981; the book drives the bucket-list discipline more than any guide does.", "reference", "personal", False,
     [("Phoebe Snetsinger", "person"), ("Birding on Borrowed Time", "publication")],
     [("Birding on Borrowed Time", "Phoebe Snetsinger", "AUTHORED_BY")],
     "which memoir sits as a reminder of a post-diagnosis 8,398-species world list and who wrote it",
     "phoebe snetsinger birding borrowed time 8398 species diagnosis 1981"),
    # --- 39 ---
    ("Kenn Kaufman's Kingbird Highway frames the seasonal chase ethic; the 1973 hitchhiking Big Year at seventeen is the template I keep in mind when budgeting a long dry spell between target species.", "reference", "personal", False,
     [("Kenn Kaufman", "person"), ("Kingbird Highway", "publication"), ("Big Year", "event")],
     [("Kingbird Highway", "Kenn Kaufman", "AUTHORED_BY")],
     "which Kaufman memoir anchors the chase ethic and which 1973 trip is the template",
     "kenn kaufman kingbird highway 1973 big year hitchhike seventeen"),
    # --- 40 ---
    ("David Sibley's What It's Like to Be a Bird supplanted the older behavioural references on the shelf; the short-essay plus plate format cross-links to species accounts in the Sibley Guide to Birds of North America.", "decision", "personal", False,
     [("David Sibley", "person"), ("What It's Like to Be a Bird", "publication"), ("Sibley Guide to Birds of North America", "publication")],
     [("What It's Like to Be a Bird", "David Sibley", "AUTHORED_BY"), ("What It's Like to Be a Bird", "Sibley Guide to Birds of North America", "RELATED_TO")],
     "which Sibley title replaced the older behaviour references and how does it cross-link to the main guide",
     "sibley what its like bird behaviour essay plate cross link"),
    # --- 41 ---
    ("Switched the rare-bird alert pipeline from a regional ABA Rare Bird Alert listserv to eBird needs-alerts with a 30-minute poll; a Fork-tailed Flycatcher notification landed four hours before the listserv digest.", "decision", "personal", False,
     [("ABA Rare Bird Alert", "tool"), ("eBird", "tool"), ("Fork-tailed Flycatcher", "concept")],
     [("eBird", "ABA Rare Bird Alert", "REPLACES")],
     "which needs-alert pipeline replaced the ABA listserv and which species proved the latency win",
     "aba rare bird alert ebird needs fork tailed flycatcher poll"),
    # --- 42 ---
    ("eBird hotspot 'Montrose Point Bird Sanctuary' in Chicago is the primary spring stakeout; the Magic Hedge traps fallout warblers against Lake Michigan when a south wind hits a cold front.", "reference", "personal", False,
     [("Montrose Point Bird Sanctuary", "place"), ("Chicago", "place"), ("Magic Hedge", "place"), ("Lake Michigan", "place")],
     [("Montrose Point Bird Sanctuary", "Chicago", "LOCATED_IN"), ("Magic Hedge", "Montrose Point Bird Sanctuary", "LOCATED_IN")],
     "which Chicago hotspot acts as primary spring stakeout and which feature traps warbler fallout",
     "montrose point bird sanctuary chicago magic hedge lake michigan fallout"),
    # --- 43. noise ---
    ("The neighbour's weekend leaf blower schedule has finally settled into a Saturday morning slot and nobody on the street complains anymore.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Hit a nemesis bird when a Cerulean Warbler finally sang on the Wissahickon ridge on the eleventh May visit; the canopy-height foraging kept me from seeing one for years despite regular breeding-season trips.", "problem", "personal", False,
     [("Cerulean Warbler", "concept"), ("Wissahickon", "place"), ("nemesis bird", "concept")],
     [("Cerulean Warbler", "Wissahickon", "LOCATED_IN")],
     "which nemesis warbler finally sang on the Wissahickon ridge and what foraging habit had hidden it",
     "cerulean warbler wissahickon nemesis canopy may eleventh visit breeding"),
    # --- 45 ---
    ("Pelagic seasickness ruined the first Hatteras trip; the switch to Stugeron an hour before the dock and a fixed gaze on the horizon made the second trip productive enough to log a Fea's Petrel.", "problem", "personal", False,
     [("Stugeron", "tool"), ("Hatteras", "place"), ("Fea's Petrel", "concept"), ("Pelagic", "activity")],
     [("Stugeron", "Pelagic", "FIXES"), ("Fea's Petrel", "Hatteras", "LOCATED_IN")],
     "which seasickness fix salvaged the second Hatteras pelagic and what target species confirmed the trip",
     "pelagic seasickness stugeron hatteras fea petrel horizon dock second"),
    # --- 46 ---
    ("Lost a potential Bicknell's Thrush ID on Mount Mansfield because the recording failed mid-song; backup workflow now writes directly to a Zoom H1n as well as the phone, so nothing hinges on one capture path.", "problem", "personal", False,
     [("Bicknell's Thrush", "concept"), ("Mount Mansfield", "place"), ("Zoom H1n", "tool")],
     [("Zoom H1n", "Mount Mansfield", "APPLIES_TO")],
     "which recording mishap cost a Bicknell's Thrush ID and what backup device fixed the workflow",
     "bicknell thrush mount mansfield zoom h1n backup recorder failed"),
    # --- 47 ---
    ("Prefer dawn-chorus recording with a Sennheiser ME66 shotgun over the built-in phone mic; the tight pickup pattern rejects the neighbour's HVAC hum that otherwise buries a distant Wood Thrush phrase.", "preference", "personal", False,
     [("Sennheiser ME66", "tool"), ("Wood Thrush", "concept"), ("dawn-chorus", "concept")],
     [("Sennheiser ME66", "dawn-chorus", "APPLIES_TO")],
     "which shotgun mic beats the phone for dawn-chorus work and which species benefits most from the rejection",
     "sennheiser me66 shotgun dawn chorus wood thrush hvac hum reject"),
    # --- 48 ---
    ("Keep a target list pinned to the fridge: Ivory-billed Woodpecker (longshot), Imperial Woodpecker (historical), Dusky Grouse, and Gunnison Sage-Grouse; the lek timing for Gunnison rules the March calendar every year.", "architecture", "personal", False,
     [("Ivory-billed Woodpecker", "concept"), ("Imperial Woodpecker", "concept"), ("Dusky Grouse", "concept"), ("Gunnison Sage-Grouse", "concept"), ("lek", "concept")],
     [("Gunnison Sage-Grouse", "lek", "USES")],
     "which four targets sit on the fridge list and which species' lek timing dictates the March calendar",
     "ivory billed imperial woodpecker dusky gunnison sage grouse lek march"),
    # --- 49 ---
    ("Trip reports live in a structured markdown folder per country, linked back to eBird checklists and xeno-canto uploads; the cross-link lets a species query jump to location, audio, and written notes in one hop.", "architecture", "personal", False,
     [("Trip reports", "concept"), ("eBird", "tool"), ("xeno-canto", "tool"), ("markdown", "concept")],
     [("Trip reports", "eBird", "USES"), ("Trip reports", "xeno-canto", "USES")],
     "which three-way cross-link binds trip reports to checklists and audio uploads in one hop",
     "trip report markdown country ebird xeno canto cross species jump"),
    # --- 50 ---
    ("Converted the eBird personal quick-entry short-codes after learning the four-letter banding codes from the USGS Bird Banding Lab; WIWA for Wilson's Warbler cuts entry time on a busy fall morning.", "decision", "personal", False,
     [("eBird", "tool"), ("USGS Bird Banding Lab", "organization"), ("Wilson's Warbler", "concept"), ("banding code", "concept")],
     [("banding code", "USGS Bird Banding Lab", "AUTHORED_BY"), ("eBird", "banding code", "USES")],
     "which four-letter coding scheme replaced the old eBird short-codes and which lab owns it",
     "ebird quick entry banding code usgs wilson warbler wiwa fall"),
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
