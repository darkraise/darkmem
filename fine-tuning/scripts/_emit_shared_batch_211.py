"""One-off emitter for shared-base batch-211 — personal domain (productivity and knowledge management systems: GTD, Zettelkasten, PARA, BASB, Bullet Journal, Deep Work, Anki, Obsidian, Roam, Tana, Logseq, Heptabase, evergreen notes, LYT, Pomodoro, FSRS).

Writes 50 rows to data/v2/shared/batch_211.tmp.jsonl with ids shared-10501..10550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_211.tmp.jsonl"
ID_OFFSET = 10500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Settled on Obsidian as the primary knowledge vault after a two-month trial against Roam Research and Logseq; the local markdown folder and the community plugin ecosystem won over outliner-first flows.", "decision", "personal", False,
     [("Obsidian", "tool"), ("Roam Research", "tool"), ("Logseq", "tool"), ("markdown", "concept")],
     [("Obsidian", "Roam Research", "PREFERS"), ("Obsidian", "Logseq", "PREFERS")],
     "which note-taking app became the household default after pitting outliner-style tools against a markdown-folder approach",
     "obsidian roam research logseq markdown vault trial plugin local"),
    # --- 2. architecture ---
    ("The vault is laid out as four top-level folders following PARA: Projects, Areas, Resources, and Archive, with a separate Daily Notes folder sitting outside the hierarchy for bullet-journal-style capture.", "architecture", "personal", False,
     [("PARA", "method"), ("Projects", "concept"), ("Areas", "concept"), ("Resources", "concept"), ("Archive", "concept"), ("Daily Notes", "concept")],
     [("PARA", "Projects", "HAS_PART"), ("PARA", "Areas", "HAS_PART"), ("PARA", "Resources", "HAS_PART"), ("PARA", "Archive", "HAS_PART")],
     "how is the Obsidian vault organised at the top level and where does daily capture live relative to that",
     "para projects areas resources archive daily notes vault folder"),
    # --- 3. milestone ---
    ("Finished reading How to Take Smart Notes by Sonke Ahrens over the long weekend; the zettelkasten-as-thinking-partner framing finally clicked after the chapter on Niklas Luhmann's slip-box workflow.", "milestone", "personal", False,
     [("How to Take Smart Notes", "publication"), ("Sonke Ahrens", "person"), ("Niklas Luhmann", "person"), ("zettelkasten", "method"), ("slip-box", "concept")],
     [("How to Take Smart Notes", "Sonke Ahrens", "AUTHORED_BY"), ("zettelkasten", "Niklas Luhmann", "AUTHORED_BY")],
     "which book explained the slip-box workflow and which historical scholar is credited with the method",
     "how take smart notes ahrens luhmann zettelkasten slip box weekend"),
    # --- 4. fact ---
    ("David Allen's Getting Things Done defines the five-step capture-clarify-organize-reflect-engage loop; the weekly review is the load-bearing step that keeps the trusted system trusted.", "fact", "personal", False,
     [("David Allen", "person"), ("Getting Things Done", "publication"), ("weekly review", "activity"), ("trusted system", "concept")],
     [("Getting Things Done", "David Allen", "AUTHORED_BY")],
     "which five-step loop anchors GTD and which recurring step keeps the whole system credible",
     "getting things done allen five step capture weekly review trust"),
    # --- 5. decision ---
    ("Chose Anki over Mochi and RemNote for long-term spaced repetition; the FSRS-4.5 scheduler add-on gives better retention curves than SM-2 and the deck sharing ecosystem is decades deep.", "decision", "personal", False,
     [("Anki", "tool"), ("Mochi", "tool"), ("RemNote", "tool"), ("FSRS-4.5", "algorithm"), ("SM-2", "algorithm")],
     [("Anki", "Mochi", "PREFERS"), ("FSRS-4.5", "SM-2", "REPLACES")],
     "which spaced repetition app won the bake-off and which scheduler did it pick over the classic one",
     "anki mochi remnote fsrs sm-2 spaced repetition deck share scheduler"),
    # --- 6. reference ---
    ("Tiago Forte's Building a Second Brain is the anchor reference for the capture workflow; the CODE method and progressive summarization both come straight from the Forte Labs cohort materials.", "reference", "personal", False,
     [("Tiago Forte", "person"), ("Building a Second Brain", "publication"), ("CODE", "method"), ("progressive summarization", "method"), ("Forte Labs", "organization")],
     [("Building a Second Brain", "Tiago Forte", "AUTHORED_BY"), ("Tiago Forte", "Forte Labs", "WORKS_AT")],
     "which book and which method names anchor the capture workflow at home",
     "tiago forte second brain code progressive summarization labs cohort"),
    # --- 7. preference ---
    ("Prefer time blocking on a paper Bullet Journal over Google Calendar for the morning planning pass; the Ryder Carroll rapid-logging notation is faster than dragging calendar blocks around at 6 am.", "preference", "personal", False,
     [("time blocking", "method"), ("Bullet Journal", "tool"), ("Google Calendar", "tool"), ("Ryder Carroll", "person"), ("rapid-logging", "method")],
     [("Bullet Journal", "Google Calendar", "PREFERS"), ("Bullet Journal", "Ryder Carroll", "AUTHORED_BY")],
     "which planning surface wins the morning pass and what notation system does it rely on",
     "time block bullet journal google calendar ryder carroll rapid log"),
    # --- 8. problem ---
    ("The zettelkasten hit a dead-link sprawl after migrating from Roam Research to Obsidian; a dataview query listing orphan notes and the Janitor plugin cleared the backlog over two weekly review sessions.", "problem", "personal", False,
     [("zettelkasten", "method"), ("Roam Research", "tool"), ("Obsidian", "tool"), ("dataview", "tool"), ("Janitor plugin", "tool"), ("orphan notes", "concept")],
     [("dataview", "orphan notes", "APPLIES_TO"), ("Janitor plugin", "orphan notes", "FIXES")],
     "which migration caused the dead-link sprawl in the slip-box and which tools cleaned it up",
     "zettelkasten roam obsidian migration dead link orphan dataview janitor"),
    # --- 9. architecture ---
    ("Evergreen notes follow the Andy Matuschak discipline: one concept per note, titles phrased as full-sentence claims, and bidirectional links only to other evergreens never to literature notes.", "architecture", "personal", False,
     [("Evergreen notes", "concept"), ("Andy Matuschak", "person"), ("literature notes", "concept"), ("bidirectional links", "concept")],
     [("Evergreen notes", "Andy Matuschak", "AUTHORED_BY")],
     "which discipline governs the evergreen note layer and what linking rule separates it from literature notes",
     "evergreen notes matuschak full sentence title bidirectional literature"),
    # --- 10. noise ---
    ("The cat walked across the keyboard during a focus block and somehow opened seventeen terminal tabs before settling on the scanner.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Adopted Cal Newport's Deep Work protocol for the Tuesday and Thursday mornings; the phone goes into a drawer, Slack stays closed, and the session timer runs for a hard ninety minutes with no context switches.", "decision", "personal", False,
     [("Cal Newport", "person"), ("Deep Work", "publication"), ("Slack", "tool")],
     [("Deep Work", "Cal Newport", "AUTHORED_BY")],
     "which focused-work protocol governs the midweek mornings and which communication tools get exiled during it",
     "cal newport deep work tuesday thursday slack drawer ninety minute"),
    # --- 12. architecture ---
    ("The Zettelkasten layer in Obsidian uses three note classes: fleeting notes captured on mobile, literature notes tied to highlights, and permanent notes that cite the prior two and nothing else.", "architecture", "personal", False,
     [("Zettelkasten", "method"), ("Obsidian", "tool"), ("fleeting notes", "concept"), ("literature notes", "concept"), ("permanent notes", "concept")],
     [("Zettelkasten", "fleeting notes", "HAS_PART"), ("Zettelkasten", "literature notes", "HAS_PART"), ("Zettelkasten", "permanent notes", "HAS_PART")],
     "which three note classes form the zettelkasten layer in the vault and what is each one allowed to cite",
     "zettelkasten fleeting literature permanent note obsidian three class"),
    # --- 13. fact ---
    ("The Pomodoro Technique was invented by Francesco Cirillo in the late 1980s using a tomato-shaped kitchen timer; the canonical unit is a 25-minute focus block followed by a 5-minute break.", "fact", "personal", False,
     [("Pomodoro Technique", "method"), ("Francesco Cirillo", "person"), ("kitchen timer", "tool")],
     [("Pomodoro Technique", "Francesco Cirillo", "AUTHORED_BY")],
     "who invented the Pomodoro Technique and what are the canonical focus and break durations",
     "pomodoro cirillo kitchen timer 25 minute 5 break 1980s invent"),
    # --- 14. decision ---
    ("Picked Heptabase over Tana for visual thinking on research projects; the whiteboard-as-first-class surface with embedded cards beats the supertag model when the output is a long-form essay.", "decision", "personal", False,
     [("Heptabase", "tool"), ("Tana", "tool"), ("whiteboard", "concept"), ("supertag", "concept")],
     [("Heptabase", "Tana", "PREFERS")],
     "which visual-thinking app won for research projects and what distinction between whiteboard and supertag drove the call",
     "heptabase tana whiteboard supertag visual thinking research essay"),
    # --- 15. reference ---
    ("Nick Milo's Linking Your Thinking course is the primary reference for the map-of-content pattern; the MOC hub notes sit at /MOCs and link out to evergreen clusters by theme.", "reference", "personal", False,
     [("Nick Milo", "person"), ("Linking Your Thinking", "publication"), ("map-of-content", "concept"), ("MOC", "concept")],
     [("Linking Your Thinking", "Nick Milo", "AUTHORED_BY")],
     "which course anchors the map-of-content pattern in the vault and where do the hub notes live",
     "nick milo linking your thinking moc map content hub evergreen cluster"),
    # --- 16. preference ---
    ("Prefer Logseq for the daily journal and Obsidian for the permanent-note archive; outliner blocks feel right for morning pages while the markdown files survive the tool choice better long-term.", "preference", "personal", False,
     [("Logseq", "tool"), ("Obsidian", "tool"), ("morning pages", "activity"), ("markdown", "concept")],
     [("Logseq", "morning pages", "APPLIES_TO")],
     "which tool handles morning pages versus the permanent archive and what drives the split",
     "logseq obsidian daily journal morning pages outliner markdown archive"),
    # --- 17. milestone ---
    ("Hit a one-thousand-card Anki milestone for the Japanese vocabulary deck on the 183-day streak; the FSRS-4.5 retention target of 90 percent held across the whole deck at the milestone check.", "milestone", "personal", False,
     [("Anki", "tool"), ("Japanese vocabulary", "concept"), ("FSRS-4.5", "algorithm")],
     [("Anki", "FSRS-4.5", "USES")],
     "which Anki milestone landed on the Japanese deck and what retention target the scheduler held at that point",
     "anki japanese vocabulary 1000 card 183 day streak fsrs 90 percent"),
    # --- 18. architecture ---
    ("The daily shutdown routine is a five-minute closing ritual: process the inbox to zero, review tomorrow's time blocks, and write a one-line journal entry; Cal Newport calls this the shutdown complete signal.", "architecture", "personal", False,
     [("daily shutdown", "activity"), ("inbox", "concept"), ("time blocks", "method"), ("Cal Newport", "person")],
     [("daily shutdown", "Cal Newport", "AUTHORED_BY")],
     "what does the end-of-day routine consist of and who coined the name for the closing signal",
     "daily shutdown inbox zero time block journal cal newport complete"),
    # --- 19. problem ---
    ("Anki review pile exploded to 600 cards after a two-week trip because the SM-2 add-on kept scheduling aggressively; switching to the FSRS-4.5 scheduler authored by Jarrett Ye rebuilt the intervals and drained the backlog in four days.", "problem", "personal", False,
     [("Anki", "tool"), ("SM-2", "algorithm"), ("FSRS-4.5", "algorithm"), ("Jarrett Ye", "person")],
     [("FSRS-4.5", "SM-2", "REPLACES"), ("FSRS-4.5", "Jarrett Ye", "AUTHORED_BY")],
     "which scheduler swap cleared the post-trip Anki backlog and who authored the replacement algorithm",
     "anki review pile 600 sm2 fsrs jarrett ye trip backlog scheduler"),
    # --- 20. decision ---
    ("Moved the task manager from Todoist to plain Markdown checklists in Obsidian; the GTD next-actions list lives in a pinned note and the weekly review queries it with a dataview snippet.", "decision", "personal", False,
     [("Todoist", "tool"), ("Obsidian", "tool"), ("GTD", "method"), ("next-actions", "concept"), ("dataview", "tool")],
     [("Obsidian", "Todoist", "REPLACES"), ("dataview", "next-actions", "APPLIES_TO")],
     "which task manager got retired and how are GTD next actions tracked in the vault now",
     "todoist obsidian markdown checklist gtd next action dataview weekly"),
    # --- 21. reference ---
    ("Cal Newport's Slow Productivity is the follow-up reference to Deep Work and shifts the frame from session intensity to seasonal workload shaping; the do-fewer-things principle is the one that stuck.", "reference", "personal", False,
     [("Cal Newport", "person"), ("Slow Productivity", "publication"), ("Deep Work", "publication"), ("do-fewer-things", "concept")],
     [("Slow Productivity", "Cal Newport", "AUTHORED_BY"), ("Slow Productivity", "Deep Work", "BUILDS_ON")],
     "which Newport book follows Deep Work and what frame shift did it introduce",
     "slow productivity newport deep work follow up do fewer things season"),
    # --- 22. fact ---
    ("Niklas Luhmann's slip-box accumulated roughly 90,000 zettels over thirty years and was cited as the engine behind his 70 books and 400 papers in sociology.", "fact", "personal", False,
     [("Niklas Luhmann", "person"), ("slip-box", "concept"), ("zettels", "concept"), ("sociology", "field")],
     [("Niklas Luhmann", "sociology", "WORKS_AT")],
     "how large was the Luhmann slip-box and what academic output was attributed to it",
     "luhmann slip box 90000 zettel thirty year 70 book sociology"),
    # --- 23. architecture ---
    ("The weekly review runs every Friday afternoon and follows the GTD checklist: get clear, get current, get creative; each of the three phases has its own sub-checklist pinned in the vault.", "architecture", "personal", False,
     [("weekly review", "activity"), ("GTD", "method"), ("get clear", "concept"), ("get current", "concept"), ("get creative", "concept")],
     [("weekly review", "GTD", "USES"), ("GTD", "get clear", "HAS_PART"), ("GTD", "get current", "HAS_PART"), ("GTD", "get creative", "HAS_PART")],
     "when does the weekly review happen and which three-phase checklist structure does it follow",
     "weekly review friday gtd get clear current creative phase checklist"),
    # --- 24. decision ---
    ("Killed the Notion workspace that had been doubling as a second brain; the offline-first, markdown-native story of Obsidian matters more than Notion's database views for personal knowledge.", "decision", "personal", False,
     [("Notion", "tool"), ("Obsidian", "tool"), ("second brain", "concept"), ("database views", "concept")],
     [("Obsidian", "Notion", "REPLACES")],
     "which workspace app got retired from the personal stack and what property drove the switch",
     "notion obsidian second brain offline markdown database view kill"),
    # --- 25. preference ---
    ("Prefer Reflect over Mem for the mobile capture app; the end-to-end encryption story and the keyboard-first design feel closer to a proper notebook than an AI chat surface.", "preference", "personal", False,
     [("Reflect", "tool"), ("Mem", "tool"), ("end-to-end encryption", "concept")],
     [("Reflect", "Mem", "PREFERS")],
     "which mobile capture app wins and which two properties made it feel more like a notebook",
     "reflect mem mobile capture encryption keyboard notebook ai chat"),
    # --- 26. architecture ---
    ("Progressive summarization runs in four layers on every saved article: raw text, bolded passages, highlighted sentences within the bold, and a one-paragraph executive summary written in the reader's own words.", "architecture", "personal", False,
     [("Progressive summarization", "method"), ("raw text", "concept"), ("executive summary", "concept")],
     [],
     "which four layers does progressive summarization stack on each saved article",
     "progressive summarization four layer raw bold highlight executive summary"),
    # --- 27. milestone ---
    ("Closed the 52-week Bullet Journal cycle with a full year of migration logs intact; the monthly migration pass caught three long-running goals that would have otherwise rolled over unacknowledged.", "milestone", "personal", False,
     [("Bullet Journal", "tool"), ("migration", "method"), ("monthly migration", "activity")],
     [("monthly migration", "Bullet Journal", "APPLIES_TO")],
     "which 52-week journal milestone landed and what did the monthly migration pass catch",
     "bullet journal 52 week migration monthly pass goal roll over"),
    # --- 28. fact ---
    ("FSRS-4.5 is a three-component memory model with stability, difficulty, and retrievability as its state variables; Jarrett Ye's paper on Anki forums showed a 30 percent workload reduction at matched retention compared to SM-2.", "fact", "personal", False,
     [("FSRS-4.5", "algorithm"), ("stability", "concept"), ("difficulty", "concept"), ("retrievability", "concept"), ("Jarrett Ye", "person"), ("SM-2", "algorithm")],
     [("FSRS-4.5", "Jarrett Ye", "AUTHORED_BY"), ("FSRS-4.5", "SM-2", "IMPROVES_ON")],
     "which three state variables drive FSRS-4.5 and what workload improvement over SM-2 did the author claim",
     "fsrs three component stability difficulty retrievability ye sm2 30"),
    # --- 29. decision ---
    ("Adopted the Capacities object-based workspace for the book notes project; object types for Book, Author, and Quote beat tag-first notes when the point is to see every quote from one author across every book.", "decision", "personal", False,
     [("Capacities", "tool"), ("Book", "concept"), ("Author", "concept"), ("Quote", "concept")],
     [("Capacities", "Book", "HAS_PART"), ("Capacities", "Author", "HAS_PART"), ("Capacities", "Quote", "HAS_PART")],
     "which object-based tool got picked for book notes and which three object types drive the layout",
     "capacities object book author quote tag first note workspace"),
    # --- 30. reference ---
    ("Andy Matuschak's essays on Notes Against the Grain and Evergreen Notes are the canonical web reference for permanent-note practice; they ship with their own note graph as a live demo at andymatuschak.org.", "reference", "personal", False,
     [("Andy Matuschak", "person"), ("Notes Against the Grain", "publication"), ("Evergreen Notes", "concept"), ("permanent-note", "concept")],
     [("Notes Against the Grain", "Andy Matuschak", "AUTHORED_BY")],
     "which web essays anchor permanent-note practice and where does the live demo live",
     "matuschak notes against grain evergreen permanent web essay demo"),
    # --- 31. problem ---
    ("The daily note template broke after an Obsidian update because the Templater plugin changed its tag syntax; pinning the plugin to version 2.2.3 and reverting the syntax to the legacy form restored the morning capture flow.", "problem", "personal", False,
     [("Obsidian", "tool"), ("Templater plugin", "tool"), ("daily note template", "concept"), ("2.2.3", "concept")],
     [("Templater plugin", "daily note template", "APPLIES_TO")],
     "which plugin change broke the daily note template and which pinning fixed the morning capture",
     "obsidian templater plugin daily note template 2.2.3 syntax legacy"),
    # --- 32. architecture ---
    ("Time blocking runs as two-tier: a weekly skeleton laid down during the Sunday planning block and daily re-plans at the start of each morning; the skeleton holds strategic commitments while the morning pass handles tactical reality.", "architecture", "personal", False,
     [("Time blocking", "method"), ("weekly skeleton", "concept"), ("Sunday planning", "activity"), ("morning pass", "activity")],
     [("weekly skeleton", "Sunday planning", "APPLIES_TO")],
     "how is time blocking split across weekly and daily cadences and what does each tier handle",
     "time block weekly skeleton sunday planning daily morning strategic tactical"),
    # --- 33. decision ---
    ("Picked the PARA framework over Johnny Decimal for folder organisation; the actionability-over-topic axis matches how projects actually move through the pipeline at home.", "decision", "personal", False,
     [("PARA", "method"), ("Johnny Decimal", "method"), ("actionability", "concept")],
     [("PARA", "Johnny Decimal", "PREFERS")],
     "which folder-organisation framework won the comparison and what axis did it trade on",
     "para johnny decimal framework folder actionability topic pipeline"),
    # --- 34. fact ---
    ("Roam Research popularised bidirectional linking and block references in 2020, which Obsidian, Logseq, and Tana all adopted within eighteen months; the industry-wide term tools for thought traces back to Conor White-Sullivan's launch essays.", "fact", "personal", False,
     [("Roam Research", "tool"), ("Obsidian", "tool"), ("Logseq", "tool"), ("Tana", "tool"), ("tools for thought", "concept"), ("Conor White-Sullivan", "person")],
     [("Obsidian", "Roam Research", "BUILDS_ON"), ("Logseq", "Roam Research", "BUILDS_ON"), ("Tana", "Roam Research", "BUILDS_ON")],
     "which app popularised bidirectional links and block refs and who is credited with the tools-for-thought phrase",
     "roam research bidirectional block ref obsidian logseq tana conor"),
    # --- 35. preference ---
    ("Prefer pen-and-paper Bullet Journal for habit tracking and mood tracking over any digital habit app; the act of drawing the monthly tracker by hand ends up being its own commitment device.", "preference", "personal", False,
     [("Bullet Journal", "tool"), ("habit tracking", "activity"), ("mood tracking", "activity"), ("commitment device", "concept")],
     [("Bullet Journal", "habit tracking", "APPLIES_TO"), ("Bullet Journal", "mood tracking", "APPLIES_TO")],
     "which tracker medium wins for habits and mood and why does the manual version stick",
     "bullet journal paper mood habit tracker digital commitment device"),
    # --- 36. milestone ---
    ("Reached the 2000-note evergreen threshold in the vault after eighteen months; the Matuschak rule of thumb says a graph-like structure starts revealing adjacent-possible jumps around this scale.", "milestone", "personal", False,
     [("evergreen", "concept"), ("Matuschak", "person"), ("adjacent-possible", "concept")],
     [],
     "which evergreen note count got hit and which heuristic says graph-scale effects kick in there",
     "evergreen 2000 note eighteen month matuschak adjacent possible graph"),
    # --- 37. architecture ---
    ("Anki decks follow a single-subject per deck rule with nested subdecks for granularity; mixing subjects in one deck confuses the FSRS-4.5 scheduler because parameters get fit to a blended difficulty distribution.", "architecture", "personal", False,
     [("Anki", "tool"), ("subdecks", "concept"), ("FSRS-4.5", "algorithm"), ("difficulty distribution", "concept")],
     [("Anki", "FSRS-4.5", "USES")],
     "how are Anki decks partitioned by subject and why does the scheduler care about that",
     "anki deck single subject nested subdeck fsrs parameter difficulty"),
    # --- 38. decision ---
    ("Dropped the three-column index card zettelkasten experiment after six weeks; the physical workflow was charming but capture latency killed the habit by the fourth week and digital Obsidian wins on retrieval.", "decision", "personal", False,
     [("index card", "tool"), ("zettelkasten", "method"), ("Obsidian", "tool"), ("capture latency", "concept")],
     [("Obsidian", "index card", "PREFERS")],
     "which physical zettelkasten experiment got dropped and which failure mode killed the habit",
     "index card zettelkasten physical obsidian capture latency six week"),
    # --- 39. reference ---
    ("Sonke Ahrens's How to Take Smart Notes is cross-referenced with Niklas Luhmann's Kommunikation mit Zettelkasten essay; the latter is the primary-source account and the former is the English-language practitioner adaptation.", "reference", "personal", False,
     [("Sonke Ahrens", "person"), ("How to Take Smart Notes", "publication"), ("Niklas Luhmann", "person"), ("Kommunikation mit Zettelkasten", "publication")],
     [("Kommunikation mit Zettelkasten", "Niklas Luhmann", "AUTHORED_BY"), ("How to Take Smart Notes", "Kommunikation mit Zettelkasten", "BUILDS_ON")],
     "which two texts pair as primary source and practitioner adaptation for the slip-box tradition",
     "ahrens smart notes luhmann kommunikation zettelkasten primary source"),
    # --- 40. architecture ---
    ("Capture funnel runs in three layers: voice memo on the phone during walks, Reflect inbox at the end of the walk, and Obsidian permanent notes during the Friday review; nothing escapes the funnel without a decision.", "architecture", "personal", False,
     [("Capture funnel", "method"), ("voice memo", "tool"), ("Reflect", "tool"), ("Obsidian", "tool"), ("Friday review", "activity")],
     [("Reflect", "voice memo", "BUILDS_ON"), ("Obsidian", "Reflect", "BUILDS_ON")],
     "what three stages does the capture funnel flow through and which cadence closes each item out",
     "capture funnel voice memo reflect obsidian friday review three layer"),
    # --- 41. fact ---
    ("SM-2 was published by Piotr Wozniak in 1987 as part of the SuperMemo project in Poland; the algorithm's ease factor and inter-repetition interval formula are still the default in most spaced repetition apps that predate FSRS.", "fact", "personal", False,
     [("SM-2", "algorithm"), ("Piotr Wozniak", "person"), ("SuperMemo", "tool"), ("Poland", "place"), ("ease factor", "concept")],
     [("SM-2", "Piotr Wozniak", "AUTHORED_BY"), ("SM-2", "SuperMemo", "USES"), ("Piotr Wozniak", "Poland", "LIVES_IN")],
     "when and where did SM-2 originate and which two parameters does it schedule on",
     "sm2 wozniak 1987 supermemo poland ease factor inter repetition"),
    # --- 42. decision ---
    ("Chose Tana for the work-project knowledge graph because supertags enforce consistent fields across meeting-note, decision, and action-item types; Obsidian's free-form markdown loses that discipline at scale.", "decision", "personal", False,
     [("Tana", "tool"), ("supertags", "concept"), ("meeting-note", "concept"), ("decision", "concept"), ("action-item", "concept"), ("Obsidian", "tool")],
     [("Tana", "Obsidian", "PREFERS"), ("Tana", "supertags", "USES")],
     "which tool won for the work graph and which feature enforced consistent fields across entry types",
     "tana supertag meeting decision action item obsidian markdown work"),
    # --- 43. noise ---
    ("The neighbour's toddler discovered the intercom at 6:47 am and now the whole building knows what a bulldozer sounds like in a polite child's voice.", "fact", "noise", True, [], [], None, None),
    # --- 44. architecture ---
    ("The BASB capture system reads everything through Readwise first; highlights sync into Obsidian as per-book literature notes with a source block, and the Readwise daily review surfaces old highlights on a spaced rotation.", "architecture", "personal", False,
     [("BASB", "method"), ("Readwise", "tool"), ("Obsidian", "tool"), ("literature notes", "concept"), ("daily review", "activity")],
     [("BASB", "Readwise", "USES"), ("Readwise", "Obsidian", "COMMUNICATES_WITH")],
     "which capture tool fronts the Building-a-Second-Brain flow and how do highlights land in the vault",
     "basb readwise obsidian literature note daily review highlight sync"),
    # --- 45. problem ---
    ("The Pomodoro habit collapsed during a crunch month because 25-minute blocks were too short for the Deep Work tasks; switched to 50-minute blocks with 10-minute breaks and the rhythm came back within a week.", "problem", "personal", False,
     [("Pomodoro", "method"), ("Deep Work", "publication"), ("25-minute blocks", "concept"), ("50-minute blocks", "concept")],
     [("50-minute blocks", "25-minute blocks", "REPLACES")],
     "which block-length change rescued the focus habit during a crunch and what tradeoff motivated it",
     "pomodoro 25 minute 50 deep work crunch month rhythm break"),
    # --- 46. decision ---
    ("Settled on a single tag taxonomy across Obsidian, Anki, and Readwise: area tags prefix with area/, project tags with project/, and topic tags with topic/; the three-way split mirrors how queries actually get asked.", "decision", "personal", False,
     [("Obsidian", "tool"), ("Anki", "tool"), ("Readwise", "tool"), ("tag taxonomy", "concept")],
     [("tag taxonomy", "Obsidian", "APPLIES_TO"), ("tag taxonomy", "Anki", "APPLIES_TO"), ("tag taxonomy", "Readwise", "APPLIES_TO")],
     "which tag-prefix scheme covers the three main tools and what does the three-way split map to",
     "tag taxonomy obsidian anki readwise area project topic prefix"),
    # --- 47. milestone ---
    ("Completed the first full GTD onboarding pass on all open loops in one Saturday; the mind sweep surfaced 184 incomplete items and the two-minute rule dispatched 61 of them before lunch.", "milestone", "personal", False,
     [("GTD", "method"), ("mind sweep", "method"), ("two-minute rule", "method"), ("open loops", "concept")],
     [("GTD", "two-minute rule", "HAS_PART"), ("GTD", "mind sweep", "HAS_PART")],
     "which GTD onboarding pass landed in one day and what numbers did the mind sweep and two-minute rule produce",
     "gtd onboarding saturday mind sweep 184 two minute rule 61 loop"),
    # --- 48. fact ---
    ("Ryder Carroll introduced the Bullet Journal Method through a 2013 video and formalised it in the 2018 book of the same name; the rapid-logging system and the migration discipline are the two load-bearing inventions.", "fact", "personal", False,
     [("Ryder Carroll", "person"), ("Bullet Journal Method", "publication"), ("rapid-logging", "method"), ("migration", "method")],
     [("Bullet Journal Method", "Ryder Carroll", "AUTHORED_BY")],
     "who introduced the Bullet Journal and which two practices are the load-bearing inventions of the method",
     "ryder carroll bullet journal 2013 2018 rapid log migration book"),
    # --- 49. architecture ---
    ("Anki card templates separate prompt, answer, and source fields; cloze deletions sit in their own note type so the FSRS-4.5 parameter fit doesn't mix cloze and basic difficulty distributions.", "architecture", "personal", False,
     [("Anki", "tool"), ("cloze deletions", "concept"), ("FSRS-4.5", "algorithm"), ("note type", "concept")],
     [("Anki", "FSRS-4.5", "USES")],
     "how are Anki note types partitioned between basic and cloze and why does the scheduler care",
     "anki note type cloze basic prompt answer source fsrs difficulty"),
    # --- 50. preference ---
    ("Prefer keeping meeting notes inside the permanent-note graph rather than in a separate meeting-notes app like Granola; a meeting that doesn't produce a linkable idea wasn't worth attending anyway.", "preference", "personal", False,
     [("meeting notes", "concept"), ("permanent-note", "concept"), ("Granola", "tool")],
     [("permanent-note", "Granola", "PREFERS")],
     "where do meeting notes live and what filtering principle falls out of that choice",
     "meeting notes permanent graph granola linkable idea attend worth"),
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
