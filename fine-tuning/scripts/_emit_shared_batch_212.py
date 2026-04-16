"""One-off emitter for shared-base batch-212 — personal domain (journaling practices and tools: Morning Pages, bullet journals, decision journals, Stoic journals, fountain pens, inks, notebooks, digital journaling apps).

Writes 50 rows to data/v2/shared/batch_212.tmp.jsonl with ids shared-10551..10600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_212.tmp.jsonl"
ID_OFFSET = 10550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Committed to Morning Pages every weekday after reading The Artist's Way by Julia Cameron; three longhand pages before coffee beats journaling in the evening when the day has already drained the tank.", "decision", "personal", False,
     [("Morning Pages", "activity"), ("The Artist's Way", "publication"), ("Julia Cameron", "person")],
     [("The Artist's Way", "Julia Cameron", "AUTHORED_BY"), ("Morning Pages", "The Artist's Way", "RELATED_TO")],
     "which daily writing practice did the household adopt and which book made the case for doing it first thing",
     "morning pages artist way julia cameron longhand weekday coffee"),
    # --- 2. architecture ---
    ("The journal stack is layered: a Hobonichi Techo A6 for one-line daily logs, a Leuchtturm1917 A5 for bullet-journal collections, and a Midori Traveler's Notebook for trip memories kept in refillable inserts.", "architecture", "personal", False,
     [("Hobonichi Techo", "tool"), ("Leuchtturm1917", "tool"), ("Midori Traveler's Notebook", "tool"), ("bullet-journal", "activity")],
     [("Leuchtturm1917", "bullet-journal", "APPLIES_TO")],
     "how is the paper journaling setup split across daily, collections, and travel use cases",
     "hobonichi techo leuchtturm1917 midori travelers notebook stack daily"),
    # --- 3. milestone ---
    ("Hit the one-year mark of the Ryder Carroll Bullet Journal Method this October; the monthly migration ritual finally clicks and tasks no longer calcify in an old spread for weeks.", "milestone", "personal", False,
     [("Ryder Carroll", "person"), ("Bullet Journal Method", "activity"), ("monthly migration", "method"), ("October", "date")],
     [("Bullet Journal Method", "Ryder Carroll", "AUTHORED_BY")],
     "when did the bullet journal practice cross twelve months and which ritual finally made it stick",
     "ryder carroll bullet journal method monthly migration october year"),
    # --- 4. fact ---
    ("Decision journals in the Shane Parrish style record the decision, the expected outcome, the confidence level, and the reasoning, then schedule a review date six months out to check calibration.", "fact", "personal", False,
     [("Shane Parrish", "person"), ("Decision journals", "method"), ("calibration", "concept")],
     [("Decision journals", "Shane Parrish", "AUTHORED_BY")],
     "which four fields anchor a Shane Parrish style decision journal entry and how is calibration checked",
     "shane parrish decision journal outcome confidence reasoning review"),
    # --- 5. reference ---
    ("Meditations by Marcus Aurelius is the touchstone for the evening Stoic journal; the prompts lean on Book 5 and Book 7 where the premeditatio malorum and view-from-above passages live.", "reference", "personal", False,
     [("Meditations", "publication"), ("Marcus Aurelius", "person"), ("Stoic journal", "activity"), ("premeditatio malorum", "concept")],
     [("Meditations", "Marcus Aurelius", "AUTHORED_BY"), ("Stoic journal", "Meditations", "RELATED_TO")],
     "which Stoic text anchors the evening reflection journal and which two books supply most prompts",
     "meditations marcus aurelius stoic journal book 5 7 premeditatio"),
    # --- 6. preference ---
    ("Prefer a Pilot Custom 823 over the Lamy 2000 for long journaling sessions; the vacuum-fill barrel holds enough Iroshizuku ink for a full week of Morning Pages without a refill break.", "preference", "personal", False,
     [("Pilot Custom 823", "tool"), ("Lamy 2000", "tool"), ("Iroshizuku", "tool"), ("Morning Pages", "activity")],
     [("Pilot Custom 823", "Lamy 2000", "PREFERS"), ("Pilot Custom 823", "Iroshizuku", "USES")],
     "which fountain pen wins for long sessions and which ink brand sits in it",
     "pilot custom 823 lamy 2000 iroshizuku morning pages vacuum fill"),
    # --- 7. problem ---
    ("The Moleskine classic bled through with Sailor Jentle Yama-dori on every dotted page; swapped to Midori MD paper and the ghosting dropped to a faint shadow on the back side.", "problem", "personal", False,
     [("Moleskine", "tool"), ("Sailor Jentle Yama-dori", "tool"), ("Midori MD", "tool")],
     [("Midori MD", "Moleskine", "REPLACES")],
     "which paper swap fixed the bleed-through from a saturated Sailor ink on daily journaling pages",
     "moleskine sailor yama-dori midori md bleed through ghost paper"),
    # --- 8. decision ---
    ("Picked Day One over Journey for the digital journal after the end-to-end-encryption audit; Day One's on-device keys and iCloud sync fit the threat model while Journey's Google Drive path did not.", "decision", "personal", False,
     [("Day One", "tool"), ("Journey", "tool"), ("end-to-end-encryption", "concept"), ("iCloud", "service")],
     [("Day One", "Journey", "PREFERS"), ("Day One", "iCloud", "USES")],
     "which digital journal app won the encryption evaluation and how does it sync",
     "day one journey end to end encryption icloud sync audit threat"),
    # --- 9. decision ---
    ("Chose Obsidian daily notes over a plain Markdown folder for the reflective journal; a Templater template seeds each note with Morning Pages, a gratitude list, and a decision-log callout pulling from a single MOC.", "decision", "personal", False,
     [("Obsidian", "tool"), ("Templater", "tool"), ("Morning Pages", "activity"), ("gratitude list", "activity"), ("MOC", "concept")],
     [("Obsidian", "Templater", "USES"), ("Templater", "Morning Pages", "APPLIES_TO")],
     "which note tool was picked for the reflective journal and how does it bootstrap each day",
     "obsidian daily note templater morning pages gratitude decision moc"),
    # --- 10. noise ---
    ("The studio window has one particular pigeon that lands on the sill every morning around ten and stares at the ink bottles on the desk.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision ---
    ("Chose the Leuchtturm1917 A5 dotted in anthracite as the bullet journal body after cycling through Rhodia Webnotebook and Moleskine; the numbered pages and double table-of-contents sheets seal the deal.", "decision", "personal", False,
     [("Leuchtturm1917", "tool"), ("Rhodia Webnotebook", "tool"), ("Moleskine", "tool"), ("bullet journal", "activity")],
     [("Leuchtturm1917", "Rhodia Webnotebook", "PREFERS"), ("Leuchtturm1917", "Moleskine", "PREFERS")],
     "which dotted notebook won the bullet-journal role and which two competitors got cycled out",
     "leuchtturm1917 a5 dotted anthracite rhodia moleskine numbered bullet"),
    # --- 12. fact ---
    ("Gratitude journaling with three specific items per evening outperformed a single general entry in the 2003 Emmons and McCullough study; specificity is what moves the well-being needle, not volume.", "fact", "personal", False,
     [("Gratitude journaling", "activity"), ("Emmons and McCullough", "person"), ("2003", "date")],
     [("Gratitude journaling", "Emmons and McCullough", "RELATED_TO")],
     "which format of gratitude entry beat a generic single-line entry in the 2003 Emmons study",
     "gratitude journal three specific emmons mccullough 2003 well being"),
    # --- 13. reference ---
    ("The Bullet Journal Method book by Ryder Carroll sits on the desk as the primary reference for the quarterly Future Log setup and the index conventions used for the daily log.", "reference", "personal", False,
     [("The Bullet Journal Method", "publication"), ("Ryder Carroll", "person"), ("Future Log", "method"), ("daily log", "method")],
     [("The Bullet Journal Method", "Ryder Carroll", "AUTHORED_BY")],
     "which book anchors the Future Log and daily-log conventions on the home desk",
     "bullet journal method ryder carroll future log daily index quarterly"),
    # --- 14. architecture ---
    ("Logseq journal handles the research side: the left rail is a chronological journal and every block can be transcluded into topic pages, so the decision journal threads through projects without duplication.", "architecture", "personal", False,
     [("Logseq", "tool"), ("transcluded", "method"), ("decision journal", "method")],
     [("Logseq", "transcluded", "USES")],
     "how does Logseq thread decision-journal blocks into topic pages without duplicating entries",
     "logseq journal rail chronological transclude block topic decision"),
    # --- 15. milestone ---
    ("Crossed the thirtieth ink-swap on the TWSBI Eco piston filler this week; the workday journal has cycled through a full Diamine sampler without the piston seal complaining once.", "milestone", "personal", False,
     [("TWSBI Eco", "tool"), ("piston filler", "concept"), ("Diamine", "tool")],
     [("TWSBI Eco", "piston filler", "IS_A"), ("TWSBI Eco", "Diamine", "USES")],
     "when did the TWSBI Eco cross thirty ink swaps and which ink line carried the testing",
     "twsbi eco piston filler diamine workday journal swap flush"),
    # --- 16. decision ---
    ("Decided to keep the Stoic evening journal on paper rather than in Day One; typing prompts sent the reflection into performative mode, while pen on Midori MD keeps the cadence slower and more honest.", "decision", "personal", False,
     [("Stoic evening journal", "activity"), ("Day One", "tool"), ("Midori MD", "tool")],
     [("Midori MD", "Day One", "PREFERS")],
     "why did the Stoic evening journal stay on paper instead of moving into the digital app",
     "stoic evening journal day one midori md paper performative cadence"),
    # --- 17. milestone ---
    ("Finished the first full Hobonichi Techo Planner cover-to-cover in December; the Tomoe River paper survived a year of Sailor Pro Gear Slim work without a single tear at the binding.", "milestone", "personal", False,
     [("Hobonichi Techo Planner", "tool"), ("December", "date"), ("Tomoe River", "tool"), ("Sailor Pro Gear Slim", "tool")],
     [("Hobonichi Techo Planner", "Tomoe River", "USES")],
     "when did the first Hobonichi Techo fill up and which paper and pen carried it through the year",
     "hobonichi techo planner december tomoe river sailor pro gear slim"),
    # --- 18. fact ---
    ("The School of Life's prompt deck rotates through eight themes including Self-Knowledge, Relationships, Work, and Calm; one card a day is enough to seed a journaling session when the well runs dry.", "fact", "personal", False,
     [("The School of Life", "organization"), ("prompt deck", "tool"), ("Self-Knowledge", "concept"), ("Relationships", "concept")],
     [("The School of Life", "prompt deck", "PRODUCES")],
     "which publisher's card deck seeds journaling prompts and how many themes does it rotate through",
     "school of life prompt deck self knowledge relationships themes card"),
    # --- 19. decision ---
    ("Adopted a five-column CBT journal format after a month of free-form entries went nowhere: situation, automatic thought, cognitive distortion, evidence for and against, and balanced response, each on a two-page Leuchtturm1917 spread.", "decision", "personal", False,
     [("CBT journal", "activity"), ("automatic thought", "concept"), ("cognitive distortion", "concept"), ("Leuchtturm1917", "tool")],
     [("CBT journal", "Leuchtturm1917", "USES")],
     "which structured format replaced free-form CBT journaling and how is it laid out physically",
     "cbt journal column situation automatic thought distortion leuchtturm"),
    # --- 20. decision ---
    ("Dropped the Apple Journal after two months; the suggestions are polished but the walled garden and the thin export story make a decade-long archive a bet against Apple's product roadmap.", "decision", "personal", False,
     [("Apple Journal", "tool"), ("walled garden", "concept"), ("export", "concept")],
     [("Apple Journal", "export", "RELATED_TO")],
     "why was Apple Journal abandoned despite its polished suggestion engine",
     "apple journal walled garden export archive decade roadmap abandon"),
    # --- 21. reference ---
    ("The Morning Pages rules are non-negotiable per Julia Cameron: three pages, longhand, stream-of-consciousness, no re-reading for at least eight weeks, no one else reads them ever.", "reference", "personal", False,
     [("Morning Pages", "activity"), ("Julia Cameron", "person"), ("stream-of-consciousness", "method")],
     [("Morning Pages", "Julia Cameron", "AUTHORED_BY")],
     "which five rules does Julia Cameron set for Morning Pages and how long before a re-read",
     "morning pages julia cameron three longhand stream no reread weeks"),
    # --- 22. preference ---
    ("Prefer Iroshizuku Kon-peki for day-to-day journaling over Sailor Shikiori Yonaga; the sky-blue shade on Tomoe River has enough sheen to stay interesting without drifting into peacock territory.", "preference", "personal", False,
     [("Iroshizuku Kon-peki", "tool"), ("Sailor Shikiori Yonaga", "tool"), ("Tomoe River", "tool")],
     [("Iroshizuku Kon-peki", "Sailor Shikiori Yonaga", "PREFERS")],
     "which blue ink wins for daily journaling and why on Tomoe River",
     "iroshizuku kon peki sailor shikiori yonaga tomoe river blue sheen"),
    # --- 23. architecture ---
    ("The Midori Traveler's Notebook is configured with four inserts: a lined for daily log, a grid for sketches, a Kraft folder for ticket stubs, and a zip pocket for polaroids and receipts.", "architecture", "personal", False,
     [("Midori Traveler's Notebook", "tool"), ("Kraft folder", "tool"), ("zip pocket", "tool"), ("daily log", "method")],
     [("Midori Traveler's Notebook", "Kraft folder", "HAS_PART"), ("Midori Traveler's Notebook", "zip pocket", "HAS_PART")],
     "how are the four inserts of the Traveler's Notebook organised across daily log, sketches, and memorabilia",
     "midori travelers notebook insert lined grid kraft zip daily sketch"),
    # --- 24. problem ---
    ("The Platinum 3776 Century kept hard-starting after a weekend away; the slip-and-seal cap does its job, but only the inner cap's silicone ring was dried out and a single drop of pen lube restored the Monday glide.", "problem", "personal", False,
     [("Platinum 3776 Century", "tool"), ("slip-and-seal cap", "concept"), ("pen lube", "tool")],
     [("pen lube", "Platinum 3776 Century", "FIXES")],
     "what caused the Monday hard-start on the Platinum 3776 Century and what fixed it",
     "platinum 3776 century hard start slip seal cap silicone lube"),
    # --- 25. decision ---
    ("Picked Diarium over Journey for the cross-platform digital journal; Diarium's Windows, Android, and web presence covers the actual device fleet while Journey trailed on desktop.", "decision", "personal", False,
     [("Diarium", "tool"), ("Journey", "tool"), ("Windows", "platform"), ("Android", "platform")],
     [("Diarium", "Journey", "PREFERS"), ("Diarium", "Windows", "DEPLOYED_ON"), ("Diarium", "Android", "DEPLOYED_ON")],
     "which cross-platform digital journal won for a mixed Windows Android workflow",
     "diarium journey windows android web desktop cross platform digital"),
    # --- 26. fact ---
    ("Bullet-journal signifiers in the Ryder Carroll system are a dot for task, a circle for event, a dash for note, an x through a completed dot, and a right-arrow for a migrated task.", "fact", "personal", False,
     [("Bullet-journal", "activity"), ("Ryder Carroll", "person"), ("signifier", "concept"), ("migrated task", "concept")],
     [("Bullet-journal", "Ryder Carroll", "AUTHORED_BY")],
     "which five bullet-journal glyphs distinguish tasks, events, notes, completion, and migration",
     "bullet journal signifier dot circle dash x arrow task event note"),
    # --- 27. architecture ---
    ("The decision journal is a separate Leuchtturm1917 A5 kept in the drawer; each spread has date, context, options, expected outcomes, confidence, and a six-month review slot left blank on the right page.", "architecture", "personal", False,
     [("decision journal", "method"), ("Leuchtturm1917", "tool"), ("six-month review", "method")],
     [("decision journal", "Leuchtturm1917", "USES")],
     "how is a decision-journal spread physically laid out across the Leuchtturm pages",
     "decision journal leuchtturm1917 a5 spread context option confidence review"),
    # --- 28. milestone ---
    ("Closed out a 100-day streak of the evening Stoic journal on the spring equinox; the prompts were drawn from Meditations and The Daily Stoic and not a single day got skipped except when the flu hit mid-February.", "milestone", "personal", False,
     [("Stoic journal", "activity"), ("spring equinox", "date"), ("Meditations", "publication"), ("The Daily Stoic", "publication")],
     [("Stoic journal", "Meditations", "USES"), ("Stoic journal", "The Daily Stoic", "USES")],
     "when did the evening Stoic journal hit a 100-day streak and which two books fed the prompts",
     "stoic journal 100 day streak spring equinox meditations daily"),
    # --- 29. milestone ---
    ("Finished the fifth bottle of Taccia Jet Black as the daily workhorse ink on Sunday; Sailor Kiwa-Guro stayed in reserve and the desk lamp still reads the older entries with room to spare.", "milestone", "personal", False,
     [("Taccia Jet Black", "tool"), ("Sailor Kiwa-Guro", "tool"), ("desk lamp", "tool")],
     [("Taccia Jet Black", "Sailor Kiwa-Guro", "PREFERS")],
     "when did the fifth bottle of Taccia Jet Black finish and what sat in reserve",
     "taccia jet black sailor kiwa guro dry time warm lamp daily"),
    # --- 30. architecture ---
    ("Daily pages route through three discrete zones on the spread: top-left for Morning Pages overflow, top-right for a three-item gratitude list, and a full bottom band for the day's decision notes.", "architecture", "personal", False,
     [("Morning Pages", "activity"), ("gratitude list", "activity"), ("decision notes", "method")],
     [("gratitude list", "Morning Pages", "RELATED_TO")],
     "how is each daily-page spread zoned across morning pages, gratitude, and decisions",
     "spread zone morning pages gratitude three item decision note band"),
    # --- 31. decision ---
    ("Bought a Sailor Pro Gear Slim with a 14k music nib specifically for calligraphic gratitude entries; the stub-ish line variation makes a three-item list feel like a visual object rather than a chore.", "decision", "personal", False,
     [("Sailor Pro Gear Slim", "tool"), ("14k music nib", "tool"), ("gratitude", "activity")],
     [("Sailor Pro Gear Slim", "14k music nib", "HAS_PART"), ("Sailor Pro Gear Slim", "gratitude", "APPLIES_TO")],
     "which pen and nib combination got dedicated to gratitude journaling and why",
     "sailor pro gear slim 14k music nib gratitude calligraphic stub"),
    # --- 32. reference ---
    ("Tim Ferriss popularised the Five-Minute Journal format in a 2014 blog post; the morning side asks for gratitude, daily intention, and an affirmation, and the evening side logs wins and one improvement.", "reference", "personal", False,
     [("Tim Ferriss", "person"), ("Five-Minute Journal", "tool"), ("2014", "date"), ("affirmation", "concept")],
     [("Five-Minute Journal", "Tim Ferriss", "AUTHORED_BY")],
     "who popularised the Five-Minute Journal format and which six fields frame the morning and evening halves",
     "tim ferriss five minute journal 2014 gratitude intention affirmation"),
    # --- 33. reference ---
    ("Tomoe River paper specs list the classic Hobonichi stock at 52 gsm with a specific rosin sizing profile; the pairing notes with Diamine Oxblood in the Sanzen reference sheet explain why the older batches handle saturated inks cleanly.", "reference", "personal", False,
     [("Tomoe River", "tool"), ("Diamine Oxblood", "tool"), ("Hobonichi", "tool"), ("Sanzen", "organization")],
     [("Hobonichi", "Tomoe River", "USES"), ("Sanzen", "Tomoe River", "PRODUCES")],
     "which paper spec sheet documents Tomoe River's 52 gsm and the Diamine Oxblood pairing notes",
     "tomoe river diamine oxblood 52 gsm hobonichi sanzen sizing spec"),
    # --- 34. architecture ---
    ("The Hobonichi Techo Cousin holds the yearly Future Log alongside the daily Hobonichi Techo; each month gets a two-page grid with significant events mapped to the owner-drawn timeline and linked by page reference across both books.", "architecture", "personal", False,
     [("Hobonichi Techo Cousin", "tool"), ("Future Log", "method"), ("Hobonichi Techo", "tool")],
     [("Hobonichi Techo Cousin", "Future Log", "USES"), ("Hobonichi Techo Cousin", "Hobonichi Techo", "RELATED_TO")],
     "how does the Techo Cousin host the Future Log and link forward to daily Techo pages",
     "hobonichi techo cousin future log yearly two page grid timeline link"),
    # --- 35. decision ---
    ("Settled on a Rhodia Goalbook for quarterly planning after testing a Moleskine Pro; the Goalbook's dotted pages and cleaner index outperformed the Pro's rigid GTD scaffolding for a self-directed cadence.", "decision", "personal", False,
     [("Rhodia Goalbook", "tool"), ("Moleskine Pro", "tool"), ("GTD", "method")],
     [("Rhodia Goalbook", "Moleskine Pro", "PREFERS"), ("Moleskine Pro", "GTD", "USES")],
     "which quarterly-planning notebook won over the Moleskine Pro and which methodology did the competitor lean on",
     "rhodia goalbook moleskine pro gtd dotted quarterly planning index"),
    # --- 36. fact ---
    ("The Traveler's Factory Tokyo station edition of the brown leather cover patinas faster than the regular Midori brown; the tannery batch uses a lighter finish that takes fingerprints like a welcome sign.", "fact", "personal", False,
     [("Traveler's Factory", "organization"), ("Tokyo station", "place"), ("Midori", "organization")],
     [("Traveler's Factory", "Tokyo station", "LOCATED_IN"), ("Traveler's Factory", "Midori", "RELATED_TO")],
     "which Traveler's Factory edition patinas faster than the regular Midori brown and why",
     "travelers factory tokyo station midori brown leather patina finish"),
    # --- 37. architecture ---
    ("Decision journal entries cross-reference the bullet journal by page number; a one-line 'decision log' block on each daily page points to the decision journal spread when a choice is captured during the day.", "architecture", "personal", False,
     [("decision journal", "method"), ("bullet journal", "activity"), ("daily page", "method")],
     [("bullet journal", "decision journal", "RELATED_TO")],
     "how does the daily bullet-journal page link into the decision journal without duplicating content",
     "decision journal bullet journal page reference daily log cross link"),
    # --- 38. preference ---
    ("Prefer longhand on Midori MD over any mechanical keyboard for emotional entries; the slower cadence forces a pause between thought and paper that a Das Keyboard 4 Pro will never give.", "preference", "personal", False,
     [("Midori MD", "tool"), ("Das Keyboard 4 Pro", "tool"), ("emotional entries", "activity")],
     [("Midori MD", "Das Keyboard 4 Pro", "PREFERS")],
     "why does longhand on Midori MD win over a mechanical keyboard for emotionally-charged journaling",
     "midori md longhand das keyboard emotional pause cadence slow thought"),
    # --- 39. milestone ---
    ("Finished the first Traveler's Notebook passport-size refill on the Lisbon trip; every day got a full spread, ticket stubs went into the Kraft folder, and the trip closed with a two-page map-and-index key.", "milestone", "personal", False,
     [("Traveler's Notebook", "tool"), ("Lisbon", "place"), ("Kraft folder", "tool")],
     [("Traveler's Notebook", "Lisbon", "VISITED"), ("Traveler's Notebook", "Kraft folder", "HAS_PART")],
     "when and where did the first passport-size Traveler's Notebook refill fill up during travel",
     "travelers notebook passport lisbon trip refill kraft folder map"),
    # --- 40. decision ---
    ("Retired the Montblanc 146 from the journaling rotation; the weight cramped the hand on a thirty-minute Morning Pages session and a lighter TWSBI Eco picked up the slot without drama.", "decision", "personal", False,
     [("Montblanc 146", "tool"), ("Morning Pages", "activity"), ("TWSBI Eco", "tool")],
     [("TWSBI Eco", "Montblanc 146", "REPLACES")],
     "why did the Montblanc 146 leave the daily journaling rotation and which pen replaced it",
     "montblanc 146 morning pages weight cramp twsbi eco retire replace"),
    # --- 41. fact ---
    ("Negative visualisation in Stoic journaling, per William B. Irvine's A Guide to the Good Life, asks the writer to imagine losing what they currently have, which amplifies gratitude without inviting actual loss.", "fact", "personal", False,
     [("Negative visualisation", "method"), ("William B. Irvine", "person"), ("A Guide to the Good Life", "publication"), ("Stoic journaling", "activity")],
     [("A Guide to the Good Life", "William B. Irvine", "AUTHORED_BY"), ("Stoic journaling", "Negative visualisation", "USES")],
     "which Stoic technique from A Guide to the Good Life turns imagined loss into gratitude",
     "negative visualisation irvine good life stoic journal gratitude loss"),
    # --- 42. architecture ---
    ("Obsidian's Daily Notes plus Periodic Notes plugins drive the weekly review workflow; Sunday rolls up the seven daily notes into a single weekly page with open tasks surfaced through a Dataview block.", "architecture", "personal", False,
     [("Obsidian", "tool"), ("Daily Notes", "tool"), ("Periodic Notes", "tool"), ("Dataview", "tool")],
     [("Obsidian", "Daily Notes", "USES"), ("Obsidian", "Periodic Notes", "USES"), ("Periodic Notes", "Dataview", "USES")],
     "which Obsidian plugin stack drives the Sunday weekly-review page and how are open tasks surfaced",
     "obsidian daily notes periodic dataview weekly review sunday rollup"),
    # --- 43. noise ---
    ("The downstairs neighbour practises tuba on Sunday afternoons and the ink on the drying page wobbles slightly with the low notes.", "fact", "noise", True, [], [], None, None),
    # --- 44. problem ---
    ("Morning Pages momentum cratered when the pen ran dry mid-page twice in one week; loaded a spare Pilot Custom 823 with full Iroshizuku Take-sumi so any primary failure never costs more than a cap-swap.", "problem", "personal", False,
     [("Morning Pages", "activity"), ("Pilot Custom 823", "tool"), ("Iroshizuku Take-sumi", "tool")],
     [("Pilot Custom 823", "Iroshizuku Take-sumi", "USES")],
     "how did a spare pen keep Morning Pages from breaking when the primary ran dry mid-session",
     "morning pages pen dry pilot custom 823 iroshizuku take sumi spare"),
    # --- 45. decision ---
    ("Switched the gratitude journaling anchor from evenings to breakfast; writing three items with coffee in hand plants the intention before the day's pressures hit rather than reconstructing it after.", "decision", "personal", False,
     [("gratitude journaling", "activity"), ("breakfast", "event"), ("intention", "concept")],
     [("gratitude journaling", "breakfast", "HAPPENED_ON")],
     "why did gratitude journaling move from evening to breakfast and what did the new timing unlock",
     "gratitude journal evening breakfast coffee intention morning anchor"),
    # --- 46. reference ---
    ("Austin Kleon's Steal Like an Artist journal sits next to the bullet journal as the creativity overflow buffer; doodles, quotes, and clippings that would choke the bullet format breathe freely over there.", "reference", "personal", False,
     [("Austin Kleon", "person"), ("Steal Like an Artist", "publication"), ("bullet journal", "activity")],
     [("Steal Like an Artist", "Austin Kleon", "AUTHORED_BY")],
     "which Austin Kleon title acts as the creativity overflow journal next to the bullet format",
     "austin kleon steal like artist journal doodle quote overflow"),
    # --- 47. architecture ---
    ("The home setup partitions tools by use: Day One for searchable text journal on iPhone, a paper Hobonichi Techo for daily planning, and the Leuchtturm1917 decision journal gated to the desk drawer.", "architecture", "personal", False,
     [("Day One", "tool"), ("iPhone", "tool"), ("Hobonichi Techo", "tool"), ("Leuchtturm1917", "tool")],
     [("Day One", "iPhone", "DEPLOYED_ON")],
     "how are digital and paper journaling tools partitioned by use across the home setup",
     "day one iphone hobonichi techo leuchtturm1917 digital paper partition"),
    # --- 48. milestone ---
    ("The decision journal crossed its first batch of forty reviewed entries last week; calibration landed at 62 percent on 70-percent-confidence predictions, right in the overconfident band Shane Parrish warns about.", "milestone", "personal", False,
     [("decision journal", "method"), ("calibration", "concept"), ("Shane Parrish", "person")],
     [("decision journal", "Shane Parrish", "AUTHORED_BY")],
     "when did the decision journal hit its first forty-entry review and what did calibration reveal",
     "decision journal forty review calibration 62 70 overconfident parrish"),
    # --- 49. fact ---
    ("Marcus Aurelius wrote Meditations in Greek during the Marcomannic Wars around 170 to 180 AD; the manuscripts were not published in his lifetime and only survived as personal notebooks found after his death.", "fact", "personal", False,
     [("Marcus Aurelius", "person"), ("Meditations", "publication"), ("Marcomannic Wars", "event")],
     [("Meditations", "Marcus Aurelius", "AUTHORED_BY"), ("Meditations", "Marcomannic Wars", "HAPPENED_ON")],
     "under which circumstances did Marcus Aurelius compose Meditations and when did it reach readers",
     "marcus aurelius meditations greek marcomannic wars 170 180 notebook"),
    # --- 50. preference ---
    ("Prefer the Kakimori brass nib holder with a Zebra G nib dipped in Sailor Jentle Sky-High for occasional calligraphic journal headers; a full pen would be overkill but a dip lasts a page and feels ritualised.", "preference", "personal", False,
     [("Kakimori", "organization"), ("Zebra G", "tool"), ("Sailor Jentle Sky-High", "tool"), ("brass nib holder", "tool")],
     [("brass nib holder", "Kakimori", "AUTHORED_BY"), ("brass nib holder", "Zebra G", "USES")],
     "which dip-pen setup handles calligraphic journal headers without moving to a full fountain pen",
     "kakimori brass nib zebra g sailor sky high dip calligraphic header"),
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
