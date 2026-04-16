"""One-off emitter for shared-base batch-263 — personal domain (tabletop role-playing games).

Writes 50 rows to data/v2/shared/batch_263.tmp.jsonl with ids shared-13101..13150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_263.tmp.jsonl"
ID_OFFSET = 13100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("After three sessions of wrestling with grapple rules, the group moved the Friday home game from D&D 5e to Pathfinder 2e Remaster; the tighter action economy settled most of our combat arguments.", "decision", "personal", False,
     [("D&D 5e", "framework"), ("Pathfinder 2e Remaster", "framework"), ("Friday home game", "project")],
     [("Pathfinder 2e Remaster", "D&D 5e", "REPLACES")],
     "which system did the Friday game switch to after the grapple-rules frustration and what sold the group",
     "pathfinder 2e remaster dnd 5e friday grapple action economy switch"),
    # --- 2 --- decision
    ("Set up the campaign on Foundry VTT rather than Roll20 because the Pathfinder 2e system module handles conditions natively and the GM doesn't have to track persistent damage manually.", "decision", "personal", False,
     [("Foundry VTT", "tool"), ("Roll20", "tool"), ("Pathfinder 2e", "framework"), ("system module", "pattern")],
     [("Foundry VTT", "Roll20", "REPLACES")],
     "which virtual tabletop did the Pathfinder 2e campaign land on and what automation justified the move",
     "foundry vtt roll20 pathfinder 2e system module condition persistent damage"),
    # --- 3 --- milestone
    ("Finished the one-year Shadowdark campaign last night; the party cleared the Crypt of the Sunless Sky and we rolled retirement boons for all four surviving characters.", "milestone", "personal", False,
     [("Shadowdark", "framework"), ("Crypt of the Sunless Sky", "project"), ("retirement boons", "concept")],
     [("Crypt of the Sunless Sky", "Shadowdark", "APPLIES_TO")],
     "which Shadowdark campaign wrapped up last night and what end-of-arc ritual did we do for survivors",
     "shadowdark crypt sunless sky one year campaign retirement boon survive"),
    # --- 4 --- preference
    ("Prefer running Old-School Essentials over any retroclone when I want a pure B/X feel; the Gavin Norman layout reads faster at the table than any other OSR book I own.", "preference", "personal", False,
     [("Old-School Essentials", "framework"), ("B/X", "concept"), ("Gavin Norman", "person"), ("OSR", "concept")],
     [("Old-School Essentials", "B/X", "APPLIES_TO")],
     "which OSR book do I reach for when I want a B/X feel and why the layout matters at the table",
     "old school essentials ose bx retroclone gavin norman layout osr"),
    # --- 5 --- fact
    ("Jeremy Crawford handed off the D&D 2024 rules-design lead role during the playtest cycle, and the final Player's Handbook launch notes credited Mike Mearls only in the historical acknowledgments.", "fact", "personal", False,
     [("Jeremy Crawford", "person"), ("D&D 2024", "framework"), ("Mike Mearls", "person"), ("Player's Handbook", "project")],
     [("Jeremy Crawford", "D&D 2024", "APPLIES_TO")],
     "which designer led the D&D 2024 rules handoff and where did Mearls end up in the credits",
     "jeremy crawford mearls dnd 2024 player handbook lead designer credit"),
    # --- 6 --- decision
    ("Dropped D&D Beyond for character sheets and moved the table to Pathbuilder after the third time the subscription renewal surprised a player mid-combat.", "decision", "personal", False,
     [("D&D Beyond", "tool"), ("Pathbuilder", "tool")],
     [("Pathbuilder", "D&D Beyond", "REPLACES")],
     "which character-sheet tool replaced D&D Beyond for the table and what pushed the migration",
     "dnd beyond pathbuilder character sheet subscription renewal mid combat"),
    # --- 7 --- architecture
    ("The Blades in the Dark crew sheet lives in a shared Obsidian vault; clocks get stored as markdown tables and I mirror the crew XP triggers into a dataview inline query for quick review.", "architecture", "personal", False,
     [("Blades in the Dark", "framework"), ("Obsidian", "tool"), ("crew sheet", "concept"), ("dataview", "tool")],
     [("Blades in the Dark", "Obsidian", "USES")],
     "how is the Blades in the Dark crew sheet structured in Obsidian and what handles XP triggers",
     "blades in the dark obsidian crew sheet clock dataview xp trigger"),
    # --- 8 --- reference
    ("Chris McDowall's Electric Bastionland is the reference I point new Into the Odd GMs to; the Failed Careers table alone teaches the Bastion-and-Downtime loop faster than any how-to-run essay.", "reference", "personal", False,
     [("Chris McDowall", "person"), ("Electric Bastionland", "framework"), ("Into the Odd", "framework"), ("Failed Careers", "concept")],
     [("Electric Bastionland", "Into the Odd", "APPLIES_TO")],
     "which book teaches the Into the Odd loop fastest and which table inside it does the heavy lifting",
     "electric bastionland chris mcdowall into the odd failed careers bastion"),
    # --- 9 --- milestone
    ("Hit session fifty on the Stars Without Number sector; the players have rebuilt three collapsed jumpgates and I rolled the faction turn for the first time since session thirty.", "milestone", "personal", False,
     [("Stars Without Number", "framework"), ("sector", "project"), ("faction turn", "concept"), ("jumpgates", "concept")],
     [("faction turn", "Stars Without Number", "APPLIES_TO")],
     "how far has the Stars Without Number sector run and what faction mechanic finally came back around",
     "stars without number sector fifty sessions faction turn jumpgate rebuild"),
    # --- 10. noise ---
    ("The cat knocked the dice tower off the shelf again and the d20 rolled straight under the fridge for the third time this month.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- decision
    ("Went with Mothership 1e for the horror one-shot over Alien RPG; the Panic die produces sharper table moments than the stress-track push and my players wanted short escalation.", "decision", "personal", False,
     [("Mothership", "framework"), ("Alien RPG", "framework"), ("Panic die", "concept")],
     [("Mothership", "Alien RPG", "PREFERS")],
     "which sci-fi horror system did the one-shot pick over Alien RPG and what mechanic sealed it",
     "mothership alien rpg panic die stress horror one shot sci fi"),
    # --- 12 --- architecture
    ("Prep for the Mausritter hex crawl uses one index card per location with the encounter die on the back; Owlbear Rodeo serves as the shared map so I never have to redraw during play.", "architecture", "personal", False,
     [("Mausritter", "framework"), ("Owlbear Rodeo", "tool"), ("hex crawl", "concept"), ("encounter die", "concept")],
     [("Mausritter", "Owlbear Rodeo", "USES")],
     "how is the Mausritter hex crawl prepped physically and which VTT carries the shared map",
     "mausritter owlbear rodeo hex crawl index card encounter die prep"),
    # --- 13 --- fact
    ("Paolo Greco's Lost Pages catalogue is where Knave 2e's treasure tables come from originally; the d100 magical-junk roll is lifted almost wholesale from his Evlyn quartos.", "fact", "personal", False,
     [("Paolo Greco", "person"), ("Knave", "framework"), ("Lost Pages", "project"), ("Evlyn quartos", "project")],
     [("Knave", "Paolo Greco", "APPLIES_TO")],
     "which designer's Lost Pages material seeded Knave's treasure tables and which quartos are the source",
     "paolo greco lost pages knave 2e treasure evlyn quarto magical junk"),
    # --- 14 --- reference
    ("Keep a dog-eared copy of Matt Colville's Running the Game playlist bookmarked in my notes; episodes 1, 16, and 45 are the ones I re-watch before running any first session of a new group.", "reference", "personal", False,
     [("Matt Colville", "person"), ("Running the Game", "project"), ("first session", "concept")],
     [],
     "which Matt Colville episodes do I rewatch before a first session and why bookmark that specific set",
     "matt colville running the game episode 1 16 45 first session new"),
    # --- 15 --- decision
    ("Picked Dungeon World over Powered by the Apocalypse generic hacks for the pickup fantasy table; the custom moves around bonds made character hooks self-generating in session one.", "decision", "personal", False,
     [("Dungeon World", "framework"), ("Powered by the Apocalypse", "framework"), ("bonds", "concept"), ("custom moves", "concept")],
     [("Dungeon World", "Powered by the Apocalypse", "PREFERS")],
     "which PbtA descendant won the pickup fantasy slot and which mechanic sold it in session one",
     "dungeon world pbta powered by the apocalypse bonds custom move pickup"),
    # --- 16 --- decision
    ("The Lancer campaign uses Comp/Con as the mech-builder backbone and Foundry VTT for play; exporting a pilot JSON from Comp/Con imports directly into the Lancer system module without fiddling.", "decision", "personal", False,
     [("Lancer", "framework"), ("Comp/Con", "tool"), ("Foundry VTT", "tool"), ("pilot JSON", "pattern")],
     [("Comp/Con", "Lancer", "APPLIES_TO"), ("Foundry VTT", "Comp/Con", "USES")],
     "how does the Lancer campaign wire Comp/Con builds into Foundry VTT without manual re-entry",
     "lancer comp con foundry vtt pilot json mech builder import module"),
    # --- 17 --- preference
    ("I prefer John Harper's Blades in the Dark original text over the Forged in the Dark hacks for any heist campaign; the Doskvol setting does specific lifting that a reskin flattens.", "preference", "personal", False,
     [("John Harper", "person"), ("Blades in the Dark", "framework"), ("Forged in the Dark", "framework"), ("Doskvol", "concept")],
     [("Blades in the Dark", "Forged in the Dark", "PREFERS")],
     "which heist system do I prefer over FitD hacks and what does Doskvol contribute that generic loses",
     "john harper blades in the dark forged in the dark doskvol heist"),
    # --- 18 --- problem
    ("Roll20's dynamic lighting kept desyncing on mobile players during the Call of Cthulhu 7e investigation; swapped to Foundry VTT mid-campaign and the mobile fog issues stopped.", "problem", "personal", False,
     [("Roll20", "tool"), ("Foundry VTT", "tool"), ("Call of Cthulhu 7e", "framework"), ("dynamic lighting", "concept")],
     [("Foundry VTT", "Roll20", "REPLACES")],
     "which VTT issue forced a mid-campaign swap during Call of Cthulhu 7e and what fixed it",
     "roll20 foundry dynamic lighting mobile fog call of cthulhu 7e swap"),
    # --- 19 --- architecture
    ("The Delta Green black ops vault is a Demiplane nexus: operative sheets, Home bonds, and Bond damage all persist there, and I share a read-only nexus link with the players between sessions.", "architecture", "personal", False,
     [("Delta Green", "framework"), ("Demiplane", "tool"), ("Home bonds", "concept"), ("nexus", "concept")],
     [("Delta Green", "Demiplane", "USES")],
     "how is the Delta Green campaign state persisted between sessions and what do players get to see",
     "delta green demiplane nexus operative sheet home bond read only"),
    # --- 20 --- milestone
    ("Ran my first Brennan Lee Mulligan-style prep for the Brindlewood Bay finale; writing the mystery clues without a pre-decided murderer shipped in five prep hours versus the usual fifteen.", "milestone", "personal", False,
     [("Brennan Lee Mulligan", "person"), ("Brindlewood Bay", "framework"), ("mystery clues", "concept")],
     [("Brindlewood Bay", "Brennan Lee Mulligan", "USES")],
     "which prep style shipped the Brindlewood Bay finale in a fraction of the usual time and how much",
     "brennan lee mulligan brindlewood bay prep mystery clue murderer five"),
    # --- 21 --- decision
    ("Chose Trail of Cthulhu over Call of Cthulhu 7e for the 1930s Armitage game; the Gumshoe core clue rule removed the failure-to-investigate dead-ends my players kept bumping into.", "decision", "personal", False,
     [("Trail of Cthulhu", "framework"), ("Call of Cthulhu 7e", "framework"), ("Gumshoe", "framework"), ("Armitage game", "project")],
     [("Trail of Cthulhu", "Call of Cthulhu 7e", "PREFERS")],
     "which Mythos system did the Armitage game pick and which core-clue rule justified the swap",
     "trail of cthulhu call of cthulhu gumshoe core clue armitage 1930s"),
    # --- 22 --- architecture
    ("Session-zero worksheets for the Monsterhearts table run on a shared Google Doc template; Skins go in a table at the top and Strings between characters live in a sub-table I reset each arc.", "architecture", "personal", False,
     [("Monsterhearts", "framework"), ("Google Doc", "tool"), ("Skins", "concept"), ("Strings", "concept")],
     [("Monsterhearts", "Google Doc", "USES")],
     "how are Skins and Strings tracked for the Monsterhearts table and what resets between arcs",
     "monsterhearts google doc skins strings session zero worksheet arc"),
    # --- 23 --- fact
    ("Gary Gygax and Dave Arneson co-authored the original 1974 D&D booklets, but the Blackmoor supplement was authored by Arneson solo and Gygax's editing tension with it is well documented.", "fact", "personal", False,
     [("Gary Gygax", "person"), ("Dave Arneson", "person"), ("Blackmoor", "project"), ("D&D", "framework")],
     [("Dave Arneson", "Blackmoor", "APPLIES_TO")],
     "which of the original D&D co-authors wrote Blackmoor solo and where did the editing tension surface",
     "gygax arneson blackmoor 1974 dnd booklet supplement edit co author"),
    # --- 24 --- reference
    ("dScryb's boxed text subscription is the read-aloud reference I lean on when I prep a published adventure on short notice; piping it into Foundry VTT journal entries takes two clicks.", "reference", "personal", False,
     [("dScryb", "tool"), ("Foundry VTT", "tool"), ("boxed text", "concept"), ("journal entries", "pattern")],
     [("dScryb", "Foundry VTT", "APPLIES_TO")],
     "which read-aloud source do I lean on for short-notice prep and how does it land in Foundry",
     "dscryb boxed text foundry journal entry read aloud subscribe short notice"),
    # --- 25 --- preference
    ("Prefer Cairn over Knave for a one-shot OSR introduction; the two-page rules insert ships out with the pregens and new players start rolling in under ten minutes every time.", "preference", "personal", False,
     [("Cairn", "framework"), ("Knave", "framework"), ("OSR", "concept"), ("pregens", "concept")],
     [("Cairn", "Knave", "PREFERS")],
     "which OSR system do I reach for first in a one-shot intro and why two pages beats Knave here",
     "cairn knave osr one shot pregen two page rules intro new player"),
    # --- 26 --- decision
    ("Switched the Scum and Villainy crew from Fantasy Grounds to Alchemy for the second season; the ambient scene audio and free-form scenes made the downtime phases actually feel lived in.", "decision", "personal", False,
     [("Scum and Villainy", "framework"), ("Fantasy Grounds", "tool"), ("Alchemy", "tool"), ("downtime phases", "concept")],
     [("Alchemy", "Fantasy Grounds", "REPLACES")],
     "which VTT did Scum and Villainy move to for season two and which feature justified the swap",
     "scum and villainy fantasy grounds alchemy ambient audio downtime crew"),
    # --- 27 --- architecture
    ("The Vampire the Masquerade V5 chronicle tracks Hunger dice with a shared Discord bot; every roll posts to a pinned channel so the Storyteller can see Hunger escalation without asking each scene.", "architecture", "personal", False,
     [("Vampire the Masquerade V5", "framework"), ("Discord", "tool"), ("Hunger dice", "concept"), ("Storyteller", "concept")],
     [("Vampire the Masquerade V5", "Discord", "USES")],
     "how does the V5 chronicle surface Hunger escalation to the Storyteller without interrupting scenes",
     "world of darkness v5 vampire masquerade hunger discord bot channel storyteller"),
    # --- 28 --- milestone
    ("Finally ran the Burning Wheel Duel of Wits at the table after months of reading the rules cold; two Point-Parry exchanges resolved a succession crisis in twenty real minutes and nobody died.", "milestone", "personal", False,
     [("Burning Wheel", "framework"), ("Duel of Wits", "concept"), ("Point-Parry", "concept")],
     [("Duel of Wits", "Burning Wheel", "APPLIES_TO")],
     "which Burning Wheel subsystem finally got table time and how long did the succession scene take",
     "burning wheel duel of wits point parry succession crisis first table"),
    # --- 29 --- fact
    ("Fate Core's Aspects evolved from Spirit of the Century's version, and Evil Hat's team documented the rewrite in the Fate Core System introduction rather than in a designer blog post.", "fact", "personal", False,
     [("Fate Core", "framework"), ("Spirit of the Century", "framework"), ("Aspects", "concept"), ("Evil Hat", "organization")],
     [("Fate Core", "Spirit of the Century", "IMPROVES_ON")],
     "where did Fate Core's Aspect rewrite story actually get published and how did it evolve",
     "fate core aspects spirit of the century evil hat rewrite system intro"),
    # --- 30 --- reference
    ("Keep Worlds Without Number's Heroic rules chapter bookmarked as my reference for running low-magic OSR-adjacent games; the foci system grafts cleanly onto Old-School Essentials with minimal friction.", "reference", "personal", False,
     [("Worlds Without Number", "framework"), ("Heroic rules", "concept"), ("Old-School Essentials", "framework"), ("foci", "concept")],
     [("Worlds Without Number", "Old-School Essentials", "APPLIES_TO")],
     "which Worlds Without Number chapter do I keep open for low-magic OSR prep and which subsystem grafts in",
     "worlds without number heroic foci ose old school essentials low magic"),
    # --- 31 --- problem
    ("GURPS 4e character creation for new players kept stalling out past the three-hour mark; swapping to a point-bracket template sheet cut creation to forty minutes and got the table into session one.", "problem", "personal", False,
     [("GURPS", "framework"), ("point-bracket template", "pattern"), ("character creation", "concept")],
     [("point-bracket template", "GURPS", "APPLIES_TO")],
     "which GURPS onboarding problem did the template sheet solve and how much time did creation lose",
     "gurps 4e character creation point bracket template three hour stall forty"),
    # --- 32 --- architecture
    ("The Coriolis campaign uses a Roll20 Character Mancer module plus a shared Miro board for relationship diagrams; the board updates each Bakshi encounter so NPC webs stay legible.", "architecture", "personal", False,
     [("Coriolis", "framework"), ("Roll20", "tool"), ("Character Mancer", "tool"), ("Miro", "tool")],
     [("Coriolis", "Roll20", "USES")],
     "how does the Coriolis campaign keep NPC webs legible across Roll20 and a relationship board",
     "coriolis roll20 character mancer miro board relationship diagram bakshi"),
    # --- 33 --- decision
    ("Moved the Savage Worlds pulp game from theatre-of-the-mind to a hex grid on Owlbear Rodeo after the third range-band argument; the Adventure Edition explicit ranges needed a picture.", "decision", "personal", False,
     [("Savage Worlds", "framework"), ("Owlbear Rodeo", "tool"), ("Adventure Edition", "concept"), ("range-band", "concept")],
     [("Owlbear Rodeo", "Savage Worlds", "APPLIES_TO")],
     "which Savage Worlds table problem pushed us to Owlbear Rodeo and which edition made it unavoidable",
     "savage worlds owlbear rodeo adventure edition range band hex grid pulp"),
    # --- 34 --- architecture
    ("Mutant Year Zero Zone Wear is modelled as a Notion database per character with a rollup for total Gear Points; the weekly expedition adds a row and the rollup re-computes automatically.", "architecture", "personal", False,
     [("Mutant Year Zero", "framework"), ("Notion", "tool"), ("Zone Wear", "concept"), ("Gear Points", "concept")],
     [("Mutant Year Zero", "Notion", "USES")],
     "how is Zone Wear tracked across Mutant Year Zero expeditions without manual totalling each week",
     "mutant year zero notion zone wear gear points rollup expedition weekly"),
    # --- 35 --- milestone
    ("The Thirsty Sword Lesbians mini-series wrapped at session eight after the confession-in-the-rain scene; two players asked to keep their Playbooks for a potential Monsterhearts sequel table.", "milestone", "personal", False,
     [("Thirsty Sword Lesbians", "framework"), ("Monsterhearts", "framework"), ("Playbooks", "concept"), ("mini-series", "project")],
     [("Playbooks", "Thirsty Sword Lesbians", "APPLIES_TO")],
     "where did the Thirsty Sword Lesbians mini-series wrap up and what did players want to carry forward",
     "thirsty sword lesbians monsterhearts playbook eight session confession sequel"),
    # --- 36 --- decision
    ("Elected Starfinder Enhanced over the upcoming Starfinder 2e playtest for the February arc; running Enhanced lets me reuse the existing Pact Worlds notes without re-statting everything.", "decision", "personal", False,
     [("Starfinder Enhanced", "framework"), ("Starfinder 2e", "framework"), ("Pact Worlds", "concept"), ("February arc", "project")],
     [("Starfinder Enhanced", "Starfinder 2e", "IMPROVES_ON")],
     "which Starfinder edition did the February arc choose and what did staying with it save in prep",
     "starfinder enhanced 2e playtest pact worlds february arc restat notes"),
    # --- 37 --- reference
    ("When the table stalls on a Forged in the Dark clock, I reread John Harper's Agenda essay from the Blades in the Dark GM chapter; the three bullets on escalation vs consequences unstick every time.", "reference", "personal", False,
     [("Forged in the Dark", "framework"), ("Blades in the Dark", "framework"), ("John Harper", "person"), ("Agenda essay", "concept")],
     [("Agenda essay", "John Harper", "APPLIES_TO")],
     "which Blades GM chapter do I reread when a FitD clock stalls and what in it unsticks the table",
     "forged in the dark blades john harper agenda clock escalation consequence"),
    # --- 38 --- fact
    ("The Shadowdark torch-timer rule is a real-time fifteen-minute clock, not an in-fiction measure; Kelsey Dionne's designer notes confirm the wall-clock is intentional to keep pressure unbroken.", "fact", "personal", False,
     [("Shadowdark", "framework"), ("Kelsey Dionne", "person"), ("torch-timer", "concept"), ("designer notes", "concept")],
     [("torch-timer", "Shadowdark", "APPLIES_TO")],
     "which Shadowdark mechanic runs on a wall clock and where did the designer confirm the intent",
     "shadowdark kelsey dionne torch timer fifteen minute wall clock design"),
    # --- 39 --- fact
    ("The Lancer GM screen kept hiding the Structure/Stress table during boss fights; printed the table as a standalone card and propped it next to the dice tray, and the lookup-mid-turn delays stopped.", "fact", "personal", False,
     [("Lancer", "framework"), ("GM screen", "tool"), ("Structure/Stress", "concept")],
     [],
     "which Lancer lookup problem got fixed with a printed card and where did the card sit at the table",
     "lancer gm screen structure stress printed card dice tray lookup boss"),
    # --- 40 --- preference
    ("Prefer running Deadlands Savage Worlds over Deadlands Classic for new groups now; the initiative card draw is easier to teach than the old Trait die escalation across five minutes.", "preference", "personal", False,
     [("Savage Worlds", "framework"), ("Deadlands", "project"), ("Deadlands Classic", "framework"), ("initiative card", "concept")],
     [("Savage Worlds", "Deadlands Classic", "PREFERS")],
     "which Deadlands edition do I prefer for new groups and what initiative mechanic makes it teachable",
     "savage worlds deadlands classic initiative card trait die teach new"),
    # --- 41 --- architecture
    ("Our Alien RPG cinematic uses Foundry VTT with the Year Zero Engine module plus a shared Stress tracker widget; when anyone rolls Panic the widget pings the whole table at once.", "architecture", "personal", False,
     [("Alien RPG", "framework"), ("Foundry VTT", "tool"), ("Year Zero Engine", "framework"), ("Stress tracker", "pattern")],
     [("Alien RPG", "Foundry VTT", "USES")],
     "how does the Alien RPG cinematic handle Stress and Panic across the table in real time",
     "alien rpg foundry year zero engine stress tracker panic widget ping"),
    # --- 42 --- decision
    ("The sandbox moved from Dungeon World to Stars Without Number after three arcs; SWN's sector-generation tools let me prep less and improvise more without breaking the players' sense of place.", "decision", "personal", False,
     [("Dungeon World", "framework"), ("Stars Without Number", "framework"), ("sector-generation", "concept"), ("sandbox", "project")],
     [("Stars Without Number", "Dungeon World", "REPLACES")],
     "which system displaced Dungeon World for the sandbox and what did its generation tooling unlock",
     "dungeon world stars without number sector generation sandbox improvise prep"),
    # --- 43. noise ---
    ("The mini-painting rack by the window warped last summer and half the shelf now lists to the left like a tiny miniatures ship.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- milestone
    ("Closed out the Vampire the Masquerade V5 chronicle at the Elysium finale after fourteen months; the Anarch coterie split the Primogen down the middle and both players rolled Beast frenzy on the same turn.", "milestone", "personal", False,
     [("Vampire the Masquerade V5", "framework"), ("Elysium finale", "project"), ("Anarch coterie", "concept"), ("Beast frenzy", "concept")],
     [("Elysium finale", "Vampire the Masquerade V5", "APPLIES_TO")],
     "how did the V5 chronicle end at the Elysium finale and what twin-frenzy moment capped it",
     "vampire v5 masquerade elysium anarch coterie primogen beast frenzy fourteen"),
    # --- 45 --- architecture
    ("Prep for the Powered by the Apocalypse anthology table rotates GMs each arc; the shared binder holds Fronts per arc in section tabs, and an index front page maps player Characters to the arc they first appeared in.", "architecture", "personal", False,
     [("Powered by the Apocalypse", "framework"), ("anthology table", "project"), ("Fronts", "concept"), ("binder", "concept")],
     [("Fronts", "Powered by the Apocalypse", "APPLIES_TO")],
     "how is Front tracking organised across a rotating PbtA anthology with multiple GMs and arcs",
     "pbta anthology rotate gm front binder arc tab index character"),
    # --- 46 --- decision
    ("Swapped our house initiative in D&D 5e from rolled initiative to side-based initiative after session twenty; the spotlight spread evened out and the combat turn-count dropped by roughly a third.", "decision", "personal", False,
     [("D&D 5e", "framework"), ("side-based initiative", "pattern"), ("rolled initiative", "pattern")],
     [("side-based initiative", "rolled initiative", "REPLACES")],
     "which D&D 5e house rule replaced rolled initiative and what did it do to the combat turn-count",
     "dnd 5e side based initiative house rule spotlight turn count swap"),
    # --- 47 --- fact
    ("Call of Cthulhu 7e's Pulp Cthulhu supplement explicitly tunes HP, Luck, and sanity loss to survive higher-tension adventures; Chaosium's own text recommends it for Mythos action over straight 7e.", "fact", "personal", False,
     [("Call of Cthulhu 7e", "framework"), ("Pulp Cthulhu", "framework"), ("Chaosium", "organization"), ("Luck", "concept")],
     [("Pulp Cthulhu", "Call of Cthulhu 7e", "IMPROVES_ON")],
     "which Call of Cthulhu supplement does Chaosium itself point to for higher-tension Mythos action",
     "pulp cthulhu call of cthulhu 7e chaosium hp luck sanity supplement"),
    # --- 48 --- reference
    ("The Old-School Essentials Advanced Fantasy Referee's Tome is my reference for overland travel pacing; the 5-mile-hex watch table is the one I reuse across every hex crawl, system-agnostic.", "reference", "personal", False,
     [("Old-School Essentials", "framework"), ("Advanced Fantasy", "project"), ("Referee's Tome", "project"), ("hex crawl", "concept")],
     [("Advanced Fantasy", "Old-School Essentials", "APPLIES_TO")],
     "which OSE book gives the hex-crawl pacing table I reuse system-agnostic and what's the scale",
     "old school essentials advanced fantasy referee tome 5 mile hex watch"),
    # --- 49 --- problem
    ("The Demiplane Pathfinder 2e nexus kept desyncing condition icons after a player closed their tab mid-session; moving the condition tracking to the physical GM screen stopped the icon drift.", "problem", "personal", False,
     [("Demiplane", "tool"), ("Pathfinder 2e", "framework"), ("nexus", "concept"), ("GM screen", "tool")],
     [("Demiplane", "Pathfinder 2e", "APPLIES_TO")],
     "which Demiplane sync bug bit the Pathfinder 2e table and what manual fallback stopped it",
     "demiplane pathfinder 2e nexus condition icon desync tab close gm screen"),
    # --- 50 --- milestone
    ("The West Marches-style D&D 2024 rotation uses Discord for scheduling, Foundry VTT for sessions, and a shared Airtable for the hex grid state so any GM can pick up where the last left off.", "milestone", "personal", False,
     [("D&D 2024", "framework"), ("West Marches", "concept"), ("Discord", "tool"), ("Foundry VTT", "tool"), ("Airtable", "tool")],
     [("D&D 2024", "Foundry VTT", "USES"), ("D&D 2024", "Airtable", "USES")],
     "how does the West Marches D&D 2024 rotation hand off hex-grid state between rotating GMs",
     "west marches dnd 2024 discord foundry airtable hex grid rotation gm"),
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
