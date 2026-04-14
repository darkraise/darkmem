"""One-off emitter for shared-base batch-049 — cross domain.

Slice: parenting meets tech (kid-facing software, safety, monitoring,
education). Writes 50 rows to data/v2/shared/batch_049.tmp.jsonl with ids
shared-02401..02450. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_049.tmp.jsonl"
ID_OFFSET = 2400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the household from Qustodio to Mobicip on 2026-01-15 once the Chromebook reports started missing the school-issued browser sessions that my daughter Amara used every afternoon.", "decision", "cross", False,
     [("Qustodio", "service"), ("Mobicip", "service"), ("2026-01-15", "date"), ("Chromebook", "infrastructure"), ("Amara", "person")],
     [("Mobicip", "Qustodio", "REPLACES")],
     "what parental control tool took over after the Chromebook reporting gap",
     "parental control swap chromebook reporting schoolday after school browsing"),
    # --- 2 ---
    ("Prefers Apple Family Sharing over Google Family Link for the two iPad minis because the Screen Time summary email every Sunday is easier to share with my co-parent Joelle.", "preference", "cross", False,
     [("Apple Family Sharing", "service"), ("Google Family Link", "service"), ("iPad", "infrastructure"), ("Screen Time", "service"), ("Joelle", "person")],
     [("Apple Family Sharing", "Google Family Link", "PREFERS"), ("Apple Family Sharing", "Screen Time", "USES")],
     "which family device manager won for the household iPads and why",
     "family sharing screen time weekly report co-parent coordination tablets"),
    # --- 3 ---
    ("The Bark monitoring trial wrapped on 2026-03-20 with a green light from both parents and a keep-decision driven by the sextortion alert that flagged a stranger DM to my son Rohan.", "milestone", "cross", False,
     [("Bark", "service"), ("2026-03-20", "date"), ("Rohan", "person")],
     [],
     "when did the safety monitoring tool earn its permanent slot in the house",
     "monitoring trial outcome stranger alert direct message keep decision kid"),
    # --- 4 ---
    ("Circle Home Plus on the living-room router now filters the kid VLAN so the guest laptop my brother brought last Thanksgiving can't accidentally open unfiltered YouTube for my niece Priya.", "architecture", "cross", False,
     [("Circle Home Plus", "service"), ("YouTube", "service"), ("Priya", "person")],
     [("Circle Home Plus", "YouTube", "USES")],
     "how does the home network keep visiting devices inside the kid-safe filter",
     "router filter kid network segment guest device unfiltered video block"),
    # --- 5 ---
    ("Eero Secure plus the built-in parental controls replaced the aging Circle Home Plus box once the whole-home Wi-Fi upgrade on 2026-02-11 made the extra hardware redundant.", "decision", "cross", False,
     [("Eero Secure", "service"), ("Circle Home Plus", "service"), ("2026-02-11", "date"), ("Wi-Fi", "protocol")],
     [("Eero Secure", "Circle Home Plus", "REPLACES")],
     "why did the extra filtering box disappear after the mesh upgrade",
     "mesh router native parental controls hardware consolidation upgrade date"),
    # --- 6. noise ---
    ("Hang on a second, the kettle just went off.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Set up a dedicated kid VLAN on the UniFi Dream Machine so the Fire HD 8 tablets my twins share never see the smart-home broker that runs the nursery automations.", "architecture", "cross", False,
     [("UniFi Dream Machine", "infrastructure"), ("Fire HD 8", "infrastructure"), ("VLAN", "protocol"), ("nursery", "place")],
     [("Fire HD 8", "UniFi Dream Machine", "DEPLOYED_ON")],
     "how are the kid tablets kept off the smart home network at home",
     "network segmentation kid devices tablets home automation isolation"),
    # --- 8 ---
    ("Prefers Khan Academy Kids on the Fire tablet over Prodigy Math on the school Chromebook because my five-year-old Kai finishes sessions instead of bouncing between unlocked games.", "preference", "cross", False,
     [("Khan Academy Kids", "service"), ("Fire tablet", "infrastructure"), ("Prodigy Math", "service"), ("Chromebook", "infrastructure"), ("Kai", "person")],
     [("Khan Academy Kids", "Prodigy Math", "PREFERS")],
     "which learning app held the five-year-old's attention during practice time",
     "early learning app focus retention math drill tablet chromebook comparison"),
    # --- 9 ---
    ("Frustration boiled over when the 2026-03-08 iOS 18 update silently reset the Screen Time downtime schedule and my daughter Mei got three unsupervised hours back before bedtime.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-03-08", "date"), ("iOS", "infrastructure"), ("Screen Time", "service"), ("Mei", "person")],
     [],
     "what went wrong with the bedtime device lockdown in early March",
     "operating system update reset downtime regression unsupervised evening kid"),
    # --- 10 ---
    ("YouTube Kids profiles got locked to the curated Learning collection on the Nest Hub in the kitchen because the open Explore feed kept surfacing toy-unboxing clickbait during breakfast.", "decision", "cross", False,
     [("YouTube Kids", "service"), ("Nest Hub", "infrastructure"), ("kitchen", "place")],
     [("YouTube Kids", "Nest Hub", "DEPLOYED_ON")],
     "why did the kitchen display lose the open kids video feed",
     "curated profile hub display breakfast routine clickbait content control"),
    # --- 11 ---
    ("The family calendar in Google Calendar feeds the Echo Show 8 in the hallway so the morning routine announces piano practice for Aiko before the school bus pickup.", "architecture", "cross", False,
     [("Google Calendar", "service"), ("Echo Show 8", "infrastructure"), ("hallway", "place"), ("piano practice", "activity"), ("Aiko", "person")],
     [("Echo Show 8", "Google Calendar", "DEPENDS_ON")],
     "how does the hallway display know which kid activity is coming up next",
     "shared family calendar display routine announcement child practice schedule"),
    # --- 12 ---
    ("Replaced the LEGO Boost kit with a LEGO Spike Prime set for my ten-year-old Teo on 2026-04-06 because the Scratch-style blocks stopped feeling like a stretch at the after-school robotics club.", "decision", "cross", False,
     [("LEGO Boost", "tool"), ("LEGO Spike Prime", "tool"), ("Teo", "person"), ("2026-04-06", "date"), ("Scratch", "language"), ("robotics club", "activity")],
     [("LEGO Spike Prime", "LEGO Boost", "REPLACES")],
     "which robotics kit took over once the starter set got too easy",
     "robotics kit upgrade block programming after school club age appropriate"),
    # --- 13 ---
    ("The Scratch Jr to Scratch handoff for my daughter Ingrid moved onto the household iMac last weekend because the iPad version kept losing large sprite projects mid-save.", "problem", "cross", False,
     [("Scratch Jr", "platform"), ("Scratch", "language"), ("Ingrid", "person"), ("iMac", "infrastructure"), ("iPad", "infrastructure")],
     [("Scratch", "Scratch Jr", "IMPROVES_ON")],
     "why did the kid's coding projects move off the tablet onto the desktop",
     "coding beginner progression desktop save reliability sprite project loss"),
    # --- 14 ---
    ("Minecraft Education Edition on the kitchen iPad during dinner prep replaced regular Minecraft for my son Felix because the world-sharing codes were easier to hand to the grandparents over FaceTime.", "decision", "cross", False,
     [("Minecraft Education Edition", "service"), ("iPad", "infrastructure"), ("Minecraft", "service"), ("Felix", "person"), ("FaceTime", "service"), ("kitchen", "place")],
     [("Minecraft Education Edition", "Minecraft", "REPLACES")],
     "which Minecraft variant became the dinner-prep game and why",
     "education edition world sharing grandparent join dinner time tablet"),
    # --- 15 ---
    ("Prefers the Kindle Kids over the Kobo Clara 2E for my third-grader Nora because the FreeTime progress reports give her grandmother concrete pages-per-week numbers to praise.", "preference", "cross", False,
     [("Kindle Kids", "infrastructure"), ("Kobo Clara 2E", "infrastructure"), ("Nora", "person"), ("FreeTime", "service")],
     [("Kindle Kids", "Kobo Clara 2E", "PREFERS"), ("Kindle Kids", "FreeTime", "USES")],
     "which e-reader won for the third-grader's reading streak reports",
     "kid e-reader progress tracking grandparent feedback reading motivation"),
    # --- 16 ---
    ("Life360 stayed on the family phones after the 2026-02-26 incident when my teen Sasha's school bus broke down on the I-90 shoulder and the last-seen pin saved a half-hour of panic.", "milestone", "cross", False,
     [("Life360", "service"), ("2026-02-26", "date"), ("Sasha", "person"), ("I-90", "place")],
     [],
     "when did the family location sharing app prove itself worth keeping",
     "location sharing school bus breakdown last seen pin peace of mind"),
    # --- 17 ---
    ("An AirTag clipped inside the backpack of my kindergartener Oliver pings the living-room HomePod mini whenever the bag goes missing between the mudroom and the breakfast table.", "architecture", "cross", False,
     [("AirTag", "infrastructure"), ("Oliver", "person"), ("HomePod mini", "infrastructure"), ("living-room", "place"), ("mudroom", "place")],
     [("AirTag", "HomePod mini", "COMMUNICATES_WITH")],
     "how does the missing backpack actually get found before school mornings",
     "tracker beacon home speaker proximity ping morning routine lost backpack"),
    # --- 18 ---
    ("DuckDuckGo's kid-safe setup replaced the default Google search on my son Milo's laptop because the image results on a dinosaur project last September were not remotely PG.", "decision", "cross", False,
     [("DuckDuckGo", "service"), ("Google", "service"), ("Milo", "person")],
     [("DuckDuckGo", "Google", "REPLACES")],
     "why did the kid's laptop lose the default search engine",
     "search engine swap kid safe image filtering school project incident"),
    # --- 19 ---
    ("Relief washed over me when the Bark weekly digest on 2026-04-03 caught zero concerning messages in my daughter Lena's Discord DMs for the first month in a row.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Bark", "service"), ("2026-04-03", "date"), ("Lena", "person"), ("Discord", "service")],
     [("Bark", "Discord", "USES")],
     "when did the Discord monitoring finally show a clean month for the teen",
     "monitoring digest clean week teen chat app peace of mind emotion milestone"),
    # --- 20 ---
    ("The Nanit baby monitor in the nursery replaced the older Owlet Cam on 2026-01-29 after the sleep analytics feature started driving our 2am feeding choices for baby Juno.", "decision", "cross", False,
     [("Nanit", "infrastructure"), ("nursery", "place"), ("Owlet Cam", "infrastructure"), ("2026-01-29", "date"), ("Juno", "person")],
     [("Nanit", "Owlet Cam", "REPLACES")],
     "which baby monitor earned the nursery slot after the swap",
     "nursery monitor upgrade sleep analytics night feeding decision support"),
    # --- 21 ---
    ("A self-hosted Pi-hole on the Raspberry Pi 4 in the basement blocks the ad domains that kept slipping past YouTube Kids on the living-room Apple TV.", "architecture", "cross", False,
     [("Pi-hole", "service"), ("Raspberry Pi 4", "infrastructure"), ("basement", "place"), ("YouTube Kids", "service"), ("Apple TV", "infrastructure"), ("living-room", "place")],
     [("Pi-hole", "Raspberry Pi 4", "DEPLOYED_ON")],
     "how do the ad-serving domains get blocked before the kids app ever sees them",
     "dns sinkhole home network ad block kid app living room streaming"),
    # --- 22 ---
    ("Prefers KidzSearch over Kiddle for homework lookups because the built-in encyclopedia cards let my fourth-grader Ravi cite sources without wandering into the open web.", "preference", "cross", False,
     [("KidzSearch", "service"), ("Kiddle", "service"), ("Ravi", "person"), ("homework", "activity")],
     [("KidzSearch", "Kiddle", "PREFERS")],
     "which kid search engine won for the grade-school homework routine",
     "kid search engine encyclopedia citation homework workflow comparison"),
    # --- 23 ---
    ("The Time-Boss rules on the family PC now pause Roblox after 45 minutes so my son Arash can actually finish the Khan Academy math set before dinner.", "architecture", "cross", False,
     [("Time-Boss", "tool"), ("Roblox", "service"), ("Arash", "person"), ("Khan Academy", "service")],
     [("Time-Boss", "Roblox", "USES")],
     "how does the PC enforce switching from games to homework before dinner",
     "time limit game pause homework priority enforcement desktop session kid"),
    # --- 24 ---
    ("The Bluey streaming schedule on Disney+ gets enforced through an IFTTT recipe that dims the living-room Hue lights to warm amber at the start of the nightly episode for my toddler Poppy.", "architecture", "cross", False,
     [("Bluey", "publication"), ("Disney+", "service"), ("IFTTT", "service"), ("Hue", "infrastructure"), ("Poppy", "person"), ("living-room", "place")],
     [("IFTTT", "Disney+", "COMMUNICATES_WITH"), ("IFTTT", "Hue", "COMMUNICATES_WITH")],
     "how does the nightly toddler show double as a wind-down light cue",
     "streaming schedule automation ambient lighting toddler routine wind down"),
    # --- 25 ---
    ("DuoABC replaced Starfall on the iPad mini for my preschooler Isla because the lesson streaks unlocked a Duolingo-style habit I actually recognised from my own Spanish practice.", "decision", "cross", False,
     [("DuoABC", "service"), ("Starfall", "service"), ("iPad mini", "infrastructure"), ("Isla", "person"), ("Duolingo", "service"), ("Spanish", "language")],
     [("DuoABC", "Starfall", "REPLACES")],
     "which early-reading app took over the preschool tablet",
     "preschool reading app swap habit streaks parent familiar pattern"),
    # --- 26 ---
    ("The micro:bit that my daughter Suri soldered at Saturday coding club now blinks the household dishwasher cycle status on the kitchen counter.", "architecture", "cross", False,
     [("micro:bit", "infrastructure"), ("Suri", "person"), ("coding club", "activity"), ("dishwasher", "infrastructure"), ("kitchen", "place")],
     [],
     "how did the kid-built microcontroller end up with a household job",
     "microcontroller family project dishwasher status display coding club output"),
    # --- 27 ---
    ("PhotoCircle replaced the shared iCloud Photos album for grandparent updates on 2026-03-14 once my father-in-law Haruki gave up on linking his Android tablet to our Apple ecosystem.", "decision", "cross", False,
     [("PhotoCircle", "service"), ("iCloud Photos", "service"), ("2026-03-14", "date"), ("Haruki", "person"), ("Android", "infrastructure")],
     [("PhotoCircle", "iCloud Photos", "REPLACES")],
     "which shared-photo service took over for the cross-platform grandparent audience",
     "family photo sharing cross platform grandparent android apple switch"),
    # --- 28 ---
    ("Duet Display turns my old iPad into a homework helper screen next to my son Yusuf's laptop so I can jump on the Zoom call with his tutor from the kitchen island.", "architecture", "cross", False,
     [("Duet Display", "tool"), ("iPad", "infrastructure"), ("Yusuf", "person"), ("Zoom", "service"), ("kitchen", "place")],
     [("Duet Display", "Zoom", "USES")],
     "how does remote homework help actually work without crowding the kid's desk",
     "second screen remote tutoring homework helper parent kid collaboration"),
    # --- 29 ---
    ("The Nest Hub routine in the kitchen announces chore rotations from the shared family Notion page every Saturday so my kids Nia and Bodhi cannot argue about whose turn it is.", "architecture", "cross", False,
     [("Nest Hub", "infrastructure"), ("kitchen", "place"), ("Notion", "tool"), ("Nia", "person"), ("Bodhi", "person")],
     [("Nest Hub", "Notion", "DEPENDS_ON")],
     "how do the weekend chores get assigned without a sibling argument",
     "smart display chore chart siblings rotation announcement shared workspace"),
    # --- 30 ---
    ("The 2026-02-05 family meeting settled on Mobicip as the single cross-platform parental control and the pilot data from Qustodio on my daughter Clara's Windows laptop sealed the call.", "milestone", "cross", False,
     [("2026-02-05", "date"), ("Mobicip", "service"), ("Qustodio", "service"), ("Clara", "person"), ("Windows", "infrastructure"), ("family meeting", "event")],
     [],
     "when did the household settle on one parental control tool for every device",
     "family decision meeting parental control pilot cross platform single tool"),
    # --- 31 ---
    ("Worry spiked the night Life360 showed my eldest Anika stopped at an unfamiliar address until the battery-saver note explained the stale pin and I drove over to confirm she was at her friend's house.", "problem", "cross", False,
     [("Worry", "emotion"), ("Life360", "service"), ("Anika", "person")],
     [],
     "what scared us about the location app one evening and how did it resolve",
     "location app false alarm battery saver stale pin teen worry parent check"),
    # --- 32 ---
    ("Prefers the Owlet Sock over the Nanit Pro cam for the second baby Arlo because the pulse-ox data on the iPhone app is more actionable at 3am than a grainy IR video feed.", "preference", "cross", False,
     [("Owlet Sock", "infrastructure"), ("Nanit Pro", "infrastructure"), ("Arlo", "person"), ("iPhone", "infrastructure")],
     [("Owlet Sock", "Nanit Pro", "PREFERS")],
     "which infant monitor won for the second baby's nighttime checks",
     "baby monitor wearable versus camera pulse oximetry overnight decision"),
    # --- 33 ---
    ("A Raspberry Pi baby cam running MotionEye in the nursery replaced the expensive Nanit subscription for my newborn Eden because the live feed over Tailscale was enough for the grandparents.", "decision", "cross", False,
     [("Raspberry Pi", "infrastructure"), ("MotionEye", "service"), ("nursery", "place"), ("Nanit", "service"), ("Eden", "person"), ("Tailscale", "service")],
     [("MotionEye", "Nanit", "REPLACES"), ("MotionEye", "Raspberry Pi", "DEPLOYED_ON")],
     "how did the household drop the paid baby monitor subscription without losing grandparent access",
     "diy baby cam self hosted subscription cut mesh vpn grandparent view"),
    # --- 34. noise ---
    ("Sorry, the baby monitor just started chirping, give me a sec.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Prefers Safe Browser Kiddle for the kid Chromebook over the default Chrome profile because the stripped toolbar stops my son Jonah from opening the bookmarks bar to his older cousin's links.", "preference", "cross", False,
     [("Safe Browser Kiddle", "tool"), ("Chromebook", "infrastructure"), ("Chrome", "tool"), ("Jonah", "person")],
     [("Safe Browser Kiddle", "Chrome", "PREFERS")],
     "which browser survives on the kid chromebook and why",
     "kid safe browser stripped ui bookmark bar sibling link risk chromebook"),
    # --- 36 ---
    ("The 2026-03-29 homework incident where my daughter Maren accidentally installed Omegle on the family iPad ended with a full MDM reset and Apple Configurator now managing installs.", "problem", "cross", False,
     [("2026-03-29", "date"), ("Maren", "person"), ("Omegle", "service"), ("iPad", "infrastructure"), ("Apple Configurator", "tool")],
     [("Apple Configurator", "iPad", "USES")],
     "what forced the household iPad onto proper device management",
     "accidental install risky app mdm reset device management parent control"),
    # --- 37 ---
    ("Grandparent video calls now happen on an Amazon Echo Show 5 on the kitchen counter because my toddler Sunni taps the big button without dialing herself into a stranger's room like the iPad FaceTime kept letting her.", "decision", "cross", False,
     [("Amazon Echo Show 5", "infrastructure"), ("kitchen", "place"), ("Sunni", "person"), ("iPad", "infrastructure"), ("FaceTime", "service")],
     [("Amazon Echo Show 5", "iPad", "REPLACES")],
     "why did the grandparent call setup leave the iPad for the Echo Show",
     "smart display toddler friendly call button stranger call risk replacement"),
    # --- 38 ---
    ("Cozi Family Organizer syncs the 2026-04-18 soccer tournament for my son Elio onto both parents' phones so nobody shows up at the wrong field again.", "architecture", "cross", False,
     [("Cozi Family Organizer", "service"), ("2026-04-18", "date"), ("Elio", "person"), ("soccer tournament", "event")],
     [],
     "how does the soccer weekend stay synced between two busy parents",
     "family calendar sync sports weekend event coordination both parents kid"),
    # --- 39 ---
    ("Hopefulness crept in when the 2026-04-09 Prodigy Math weekly report showed my second-grader Ada finally breaking into the fractions unit she had been stuck on since January.", "milestone", "cross", False,
     [("Hopefulness", "emotion"), ("2026-04-09", "date"), ("Prodigy Math", "service"), ("Ada", "person")],
     [],
     "when did the math app show a real breakthrough for the second-grader",
     "math app progress report fractions unit breakthrough second grader emotion"),
    # --- 40 ---
    ("Replaced the tangled mess of kid YouTube bookmarks with a Pinna audio-only subscription on the Sonos One in the bedroom because my six-year-old Leilani sleeps faster without a glowing screen.", "decision", "cross", False,
     [("Pinna", "service"), ("Sonos One", "infrastructure"), ("bedroom", "place"), ("Leilani", "person"), ("YouTube", "service")],
     [("Pinna", "YouTube", "REPLACES"), ("Pinna", "Sonos One", "DEPLOYED_ON")],
     "which bedtime audio setup replaced the kid video bookmarks",
     "audio only kid subscription bedtime smart speaker screen free sleep"),
    # --- 41 ---
    ("The home Wi-Fi on the kid VLAN resolves through NextDNS with a family profile so my son Caius can't reach the sketchy mods that were breaking his Minecraft world on the school laptop.", "architecture", "cross", False,
     [("Wi-Fi", "protocol"), ("VLAN", "protocol"), ("NextDNS", "service"), ("Caius", "person"), ("Minecraft", "service")],
     [("NextDNS", "Minecraft", "USES")],
     "how do the sketchy Minecraft mod sites get blocked at home",
     "dns filtering kid vlan game mod block household laptop school device"),
    # --- 42 ---
    ("Prefers the Bark phone over a hand-me-down iPhone SE for my eleven-year-old Harper because the default messaging stays inside the supervised app and the group chats with classmates actually work.", "preference", "cross", False,
     [("Bark", "service"), ("iPhone SE", "infrastructure"), ("Harper", "person")],
     [("Bark", "iPhone SE", "PREFERS")],
     "which first phone won for the eleven-year-old and why",
     "first phone supervised messaging group chat classmates tween comparison"),
    # --- 43 ---
    ("Frustration with the 2026-03-17 Google Family Link region bug that broke my daughter Zara's Pixel Tablet downtime schedule pushed the whole family off Android-first parental controls for the summer.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-03-17", "date"), ("Google Family Link", "service"), ("Zara", "person"), ("Pixel Tablet", "infrastructure"), ("Android", "infrastructure")],
     [],
     "what parental control bug soured the family on the android stack in March",
     "region bug downtime schedule broken android parental control frustration"),
    # --- 44 ---
    ("The 2026-04-07 robotics showcase at my kid's school paired an Arduino Uno with the Scratch-based interface so my daughter Imani could demo her light sensor without writing a single C line.", "milestone", "cross", False,
     [("2026-04-07", "date"), ("Arduino Uno", "infrastructure"), ("Scratch", "language"), ("Imani", "person"), ("C", "language"), ("robotics showcase", "event")],
     [("Arduino Uno", "Scratch", "USES")],
     "when did the robotics showcase happen and how did the kid present without coding text",
     "school showcase microcontroller block programming demo sensor kid project"),
    # --- 45 ---
    ("The Common Sense Media review page is the reference I send my sister Noor before she lets my nephew Dara try any new iPad app.", "reference", "cross", False,
     [("Common Sense Media", "publication"), ("Noor", "person"), ("Dara", "person"), ("iPad", "infrastructure")],
     [],
     "which outside reference gets cited when a new kid app shows up in the extended family",
     "media review reference site cousin new app vetting extended family link"),
    # --- 46 ---
    ("Prefers the Kindle Paperwhite Kids over a shared household Kobo for my reluctant-reader son Theo because the ten-minute vocabulary summary after each session finally gave him a sense of progress.", "preference", "cross", False,
     [("Kindle Paperwhite Kids", "infrastructure"), ("Kobo", "infrastructure"), ("Theo", "person")],
     [("Kindle Paperwhite Kids", "Kobo", "PREFERS")],
     "which e-reader moved the reluctant reader and how",
     "reluctant reader e-reader vocabulary summary progress signal motivation"),
    # --- 47 ---
    ("The 2026-01-22 migration off Disney+ Kids profiles onto a locked-down Plex library finally killed the surprise Marvel trailers that were giving my five-year-old Jax nightmares.", "decision", "cross", False,
     [("2026-01-22", "date"), ("Disney+", "service"), ("Plex", "service"), ("Marvel", "organization"), ("Jax", "person")],
     [("Plex", "Disney+", "REPLACES")],
     "when did the household switch from the streaming kids profile to a local library",
     "streaming swap locked library trailer block kid nightmares date milestone"),
    # --- 48 ---
    ("Calm settled back in after the Eero Secure family profile plus the NextDNS logs showed zero unfiltered requests from my teen Hadi's Windows gaming rig all of last week.", "milestone", "cross", False,
     [("Calm", "emotion"), ("Eero Secure", "service"), ("NextDNS", "service"), ("Hadi", "person"), ("Windows", "infrastructure")],
     [("Eero Secure", "NextDNS", "COMMUNICATES_WITH")],
     "when did the parental control logs finally show a clean week for the teen",
     "clean logs teen gaming rig parental controls dns mesh confidence week"),
    # --- 49 ---
    ("Moved the family photo pipeline off Google Photos onto Immich running on the basement NAS because the shared albums with my kids Wren and Kit now survive any subscription dispute with Google.", "architecture", "cross", False,
     [("Google Photos", "service"), ("Immich", "service"), ("basement", "place"), ("Wren", "person"), ("Kit", "person")],
     [("Immich", "Google Photos", "REPLACES")],
     "how did the family photo archive escape the big cloud subscription",
     "self hosted photo archive nas family album subscription independence"),
    # --- 50 ---
    ("Pride hit when my daughter Selene's Scratch project shipped to the 2026-04-11 school coding fair after a month of pair-programming sessions aimed at the ship-one-public-project goal we set in January.", "milestone", "cross", False,
     [("Pride", "emotion"), ("Selene", "person"), ("Scratch", "language"), ("2026-04-11", "date"), ("school coding fair", "event"), ("ship-one-public-project", "goal")],
     [],
     "when did the kid's first real coding project ship publicly and how did it get there",
     "school coding fair kid project pair programming goal milestone emotion"),
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
