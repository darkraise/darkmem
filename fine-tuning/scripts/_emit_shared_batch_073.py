"""One-off emitter for shared-base batch-073 — personal domain (learning and self-study slice, non-career, non-formal).

Writes 50 rows to data/v2/shared/batch_073.tmp.jsonl with ids shared-03601..03650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_073.tmp.jsonl"
ID_OFFSET = 3600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched my evening Spanish habit from Duolingo to Anki with a Spanish-frequency deck on 2026-02-14; the cloze cards stuck where the streak-chasing never did.", "decision", "personal", False,
     [("Duolingo", "platform"), ("Anki", "platform"), ("Spanish", "language"), ("2026-02-14", "date"), ("cloze cards", "concept")],
     [("Anki", "Duolingo", "REPLACES")],
     "when did my after-work language drill tool change and what made it stick",
     "evening study tool swap flashcards over gamified app retention reason"),
    # --- 2 ---
    ("The book club at Harbourside Library meets the last Thursday of each month at 19:30; we alternate fiction and non-fiction, and Priya picks the March slot.", "architecture", "personal", False,
     [("book club", "event"), ("Harbourside Library", "place"), ("Thursday", "date"), ("Priya", "person"), ("March", "date")],
     [("book club", "Harbourside Library", "LOCATED_IN")],
     "how is the reading circle scheduled and who chooses the spring title",
     "book club monthly cadence venue genre alternation picker rotation"),
    # --- 3 ---
    ("Picked up the ukulele on 2025-11-09 as a non-lesson project; just working through Andy Guitar's free curriculum and a Jake Shimabukuro tab collection.", "milestone", "personal", False,
     [("ukulele", "hobby"), ("2025-11-09", "date"), ("Andy Guitar", "person"), ("Jake Shimabukuro", "person")],
     [],
     "when did I start the self-taught string instrument project and what am I following",
     "ukulele start date self teaching free curriculum tab collection source"),
    # --- 4 ---
    ("Prefers Pimsleur audio lessons over Babbel for my commute German; the no-screen drill fits cycling, and the spaced recall beats the fill-in-the-blank drills.", "preference", "personal", False,
     [("Pimsleur", "platform"), ("Babbel", "platform"), ("German", "language"), ("commute", "activity")],
     [("Pimsleur", "Babbel", "PREFERS")],
     "which language course wins for my bike-to-work study slot and why",
     "audio lesson over app commute hands-free drill cycling suitability"),
    # --- 5 ---
    ("The kindle highlights export pipeline drops into Readwise, syncs to Obsidian nightly, and lands in a weekly review note I skim on Sundays.", "architecture", "personal", False,
     [("kindle", "tool"), ("Readwise", "service"), ("Obsidian", "tool"), ("Sundays", "date")],
     [("Readwise", "Obsidian", "COMMUNICATES_WITH"), ("kindle", "Readwise", "COMMUNICATES_WITH")],
     "how does my e-reader note flow get from highlights into the weekly review",
     "kindle highlight export readwise obsidian sync weekly cadence review"),
    # --- 6 ---
    ("Started a year-long history reading project on 2026-01-01: one thick book a month, starting with Mary Beard's SPQR, ending with Tooze's Deluge in December.", "milestone", "personal", False,
     [("history reading project", "goal"), ("2026-01-01", "date"), ("Mary Beard", "person"), ("SPQR", "publication"), ("Tooze", "person"), ("Deluge", "publication"), ("December", "date")],
     [("SPQR", "Mary Beard", "AUTHORED_BY"), ("Deluge", "Tooze", "AUTHORED_BY")],
     "when did the twelve-month heavy-history reading plan kick off and how is it bookended",
     "annual reading project start book per month opening closing title author"),
    # --- 7 ---
    ("The calligraphy kit lives in the second drawer of the bureau: two Pilot Parallel pens, a bottle of Higgins Eternal, Rhodia dot-grid pad, a ruled guide sheet.", "reference", "personal", False,
     [("calligraphy kit", "tool"), ("bureau", "place"), ("Pilot Parallel", "tool"), ("Higgins Eternal", "tool"), ("Rhodia", "tool")],
     [("calligraphy kit", "bureau", "LOCATED_IN")],
     "where is the pen-lettering gear stored and what is in the set",
     "calligraphy inventory drawer pens ink pad guide brand list location"),
    # --- 8 ---
    ("The MOOC queue for leisure is two courses live: MIT 6.042J Mathematics for Computer Science on OCW, and Coursera's Roman Architecture with Diana Kleiner.", "reference", "personal", False,
     [("MOOC", "platform"), ("MIT 6.042J", "publication"), ("OCW", "platform"), ("Coursera", "platform"), ("Roman Architecture", "publication"), ("Diana Kleiner", "person")],
     [("Roman Architecture", "Diana Kleiner", "AUTHORED_BY"), ("MIT 6.042J", "OCW", "PUBLISHED_IN")],
     "which two free online courses am I working through for fun right now",
     "MOOC queue maths CS course roman architecture platform instructor"),
    # --- 9 ---
    ("Replaced my morning news scroll with a philosophy audiobook block on 2026-03-16; currently midway through Nagel's What Does It All Mean? at 0.9x speed.", "decision", "personal", False,
     [("morning news scroll", "activity"), ("philosophy audiobook", "activity"), ("2026-03-16", "date"), ("Nagel", "person"), ("What Does It All Mean?", "publication")],
     [("philosophy audiobook", "morning news scroll", "REPLACES"), ("What Does It All Mean?", "Nagel", "AUTHORED_BY")],
     "what took over my early-day scrolling habit and what am I listening to now",
     "morning routine swap news feed audiobook philosophy current title speed"),
    # --- 10. noise ---
    ("Let me grab a tea before I try that passage again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Anki review load is pinned at 20 new cards a day across decks; crossing 30 wrecks the retention on the oldest German noun gender cards.", "problem", "personal", False,
     [("Anki", "platform"), ("new cards", "concept"), ("German", "language"), ("noun gender", "concept")],
     [],
     "what is my safe daily new-card ceiling and what breaks when I push past it",
     "anki daily limit breakage retention german gender oldest cards threshold"),
    # --- 12 ---
    ("Prefers the Loeb parallel-text editions over the Oxford World's Classics for Tacitus; the facing Latin keeps me honest even when I'm reading for pleasure.", "preference", "personal", False,
     [("Loeb", "publication"), ("Oxford World's Classics", "publication"), ("Tacitus", "person"), ("Latin", "language")],
     [("Loeb", "Oxford World's Classics", "PREFERS")],
     "which classics imprint wins for leisure Roman history reading and why",
     "loeb over oxford parallel latin facing page honesty tacitus reason"),
    # --- 13 ---
    ("The sourdough notebook is up to attempt 41 on 2026-04-02; the bulk-ferment cue that actually works for me is dough surface domed and jiggling, not clock-based.", "fact", "personal", False,
     [("sourdough", "food"), ("2026-04-02", "date"), ("bulk-ferment", "method")],
     [],
     "how many bread bakes in and what did I learn about proofing cues",
     "sourdough log attempt count bulk cue dough surface jiggle over timer"),
    # --- 14 ---
    ("Hmm, where did I leave that bookmark.", "fact", "noise", True, [], [], None, None),
    # --- 15 ---
    ("The sourdough notebook on 2026-04-02 logs attempt 41; dome-and-jiggle is my proofing cue now, not a timer, and the crumb is finally even.", "reference", "personal", False,
     [("sourdough", "food"), ("2026-04-02", "date"), ("proofing cue", "concept"), ("crumb", "concept")],
     [],
     "what is logged in my bread-baking journal and what cue do I trust",
     "sourdough journal attempt tally fermentation visual cue crumb result"),
    # --- 16 ---
    ("The history reading project slid two weeks behind by 2026-03-20; Wolfram's Peacemakers took a second pass and I underestimated the map sections.", "problem", "personal", False,
     [("history reading project", "goal"), ("2026-03-20", "date"), ("Wolfram", "person"), ("Peacemakers", "publication")],
     [("Peacemakers", "Wolfram", "AUTHORED_BY")],
     "what knocked the year-long reading plan off pace and by how much",
     "history plan slip duration cause re-read map section underestimate date"),
    # --- 17 ---
    ("Prefers morning reading of dense non-fiction to evening; the Piketty chapter I tried at 22:00 had to be redone entirely over breakfast.", "preference", "personal", False,
     [("dense non-fiction", "concept"), ("morning", "date"), ("evening", "date"), ("Piketty", "person")],
     [("morning", "evening", "PREFERS")],
     "which time of day wins for hard reading and what proved it",
     "morning over evening heavy nonfiction retention redo chapter case"),
    # --- 18 ---
    ("The podcast learning stack for 2026 Q2 is History of Philosophy Without Any Gaps, In Our Time archive, and the Ezra Klein Show on backlog mode at 1.3x.", "reference", "personal", False,
     [("History of Philosophy Without Any Gaps", "publication"), ("In Our Time", "publication"), ("Ezra Klein Show", "publication")],
     [],
     "what audio education is in my rotation for the current quarter",
     "podcast lineup quarter philosophy history interview backlog speed"),
    # --- 19 ---
    ("Moved my Anki reviews from desktop to mobile on the commute after 2026-01-08; daily reviews went from sporadic to a 91-day unbroken streak.", "decision", "personal", False,
     [("Anki", "platform"), ("desktop", "tool"), ("mobile", "tool"), ("2026-01-08", "date")],
     [("mobile", "desktop", "REPLACES")],
     "when did the flashcard drill move off the laptop and what changed",
     "anki device shift laptop to phone streak length reviews consistency date"),
    # --- 20 ---
    ("The knot-tying project picked up on 2026-02-28 with an Ashley Book of Knots used copy; working through the splicing section one knot a week.", "milestone", "personal", False,
     [("knot-tying project", "goal"), ("2026-02-28", "date"), ("Ashley Book of Knots", "publication"), ("splicing", "method")],
     [],
     "when did the rope-craft hobby start and what is the reference text",
     "knot tying start date reference book splicing weekly cadence pace"),
    # --- 21 ---
    ("The cooking-as-learning theme for April 2026 is Sichuan; three mother sauces, mapo tofu test every Sunday, Fuchsia Dunlop as the anchor book.", "architecture", "personal", False,
     [("Sichuan", "concept"), ("April 2026", "date"), ("mapo tofu", "food"), ("Sunday", "date"), ("Fuchsia Dunlop", "person")],
     [],
     "how is the month's food-education theme structured and what anchors it",
     "cuisine focus month sauces weekly dish test author reference plan"),
    # --- 22 ---
    ("Prefers the Manning Grokking series over the O'Reilly animal books for self-study CS topics; the repetitive worked examples stick better when there is no deadline.", "preference", "personal", False,
     [("Manning", "organization"), ("Grokking series", "publication"), ("O'Reilly", "organization"), ("animal books", "publication")],
     [("Grokking series", "animal books", "PREFERS")],
     "which computer-science publisher format wins for no-deadline home study",
     "manning grokking over oreilly worked examples retention leisure CS"),
    # --- 23 ---
    ("The Kindle Oasis died on 2026-03-22 after the screen froze mid-chapter; replaced it with a Kobo Libra Colour, which handles sideloaded epubs without Calibre gymnastics.", "decision", "personal", False,
     [("Kindle Oasis", "tool"), ("2026-03-22", "date"), ("Kobo Libra Colour", "tool"), ("epubs", "concept"), ("Calibre", "tool")],
     [("Kobo Libra Colour", "Kindle Oasis", "REPLACES")],
     "when did the old e-reader die and what took its slot and why",
     "ereader replacement date failure mode new model sideload workflow"),
    # --- 24 ---
    ("The Duolingo French owl is officially retired on 2026-02-20 after a 612-day streak; translation exercises plateaued and I want grammar drills instead.", "milestone", "personal", False,
     [("Duolingo", "platform"), ("French", "language"), ("2026-02-20", "date")],
     [],
     "when did the long French streak end and what triggered the stop",
     "duolingo retirement date streak length plateau grammar pivot reason"),
    # --- 25 ---
    ("The philosophy reading group on Discord meets Wednesdays 20:00 UTC; we're on Parfit's Reasons and Persons for six weeks, chapter 9 this week.", "architecture", "personal", False,
     [("philosophy reading group", "organization"), ("Discord", "platform"), ("Wednesdays", "date"), ("Parfit", "person"), ("Reasons and Persons", "publication")],
     [("Reasons and Persons", "Parfit", "AUTHORED_BY"), ("philosophy reading group", "Discord", "LOCATED_IN")],
     "how is the online theory circle structured and what is the current text",
     "discord reading group weekday cadence current book chapter progress"),
    # --- 26 ---
    ("Chose to learn the piano again from scratch with Alfred's Adult All-in-One instead of the childhood Suzuki books; adult pacing beats nostalgia.", "decision", "personal", False,
     [("piano", "hobby"), ("Alfred's Adult All-in-One", "publication"), ("Suzuki books", "publication")],
     [("Alfred's Adult All-in-One", "Suzuki books", "REPLACES")],
     "which piano method won out for the restart and why not the childhood one",
     "piano restart method choice adult over suzuki pacing rationale"),
    # --- 27 ---
    ("The Readwise daily review is capped at 10 highlights each morning on iOS; pushing it to 20 killed engagement within a week.", "problem", "personal", False,
     [("Readwise", "service"), ("daily review", "concept"), ("iOS", "platform")],
     [],
     "what is my working ceiling on the morning highlight review and what proved it",
     "readwise review size ceiling engagement drop experiment result morning"),
    # --- 28 ---
    ("Prefers physical index cards to Notion for ukulele chord memorisation; shuffling the stack before practice randomises in a way Notion's review mode can't.", "preference", "personal", False,
     [("index cards", "tool"), ("Notion", "platform"), ("ukulele", "hobby"), ("chord memorisation", "concept")],
     [("index cards", "Notion", "PREFERS")],
     "which memorisation medium wins for chord practice and why",
     "paper cards over notion shuffle randomisation chord drill reason"),
    # --- 29 ---
    ("The curry-night learning project at home has rotated through Madhur Jaffrey's index on Sundays since 2025-09-14; eighteen recipes in, chickpea masala is the keeper.", "fact", "personal", False,
     [("curry-night", "event"), ("Madhur Jaffrey", "person"), ("Sundays", "date"), ("2025-09-14", "date"), ("chickpea masala", "food")],
     [],
     "how has the weekly home-kitchen Indian cooking rotation been going",
     "curry night sunday tally start date author index favourite dish"),
    # --- 30 ---
    ("The pop-science shelf for 2026 is headed by The Goodness Paradox by Wrangham and The Song of the Cell by Mukherjee; both flagged for book club pitches.", "reference", "personal", False,
     [("The Goodness Paradox", "publication"), ("Wrangham", "person"), ("The Song of the Cell", "publication"), ("Mukherjee", "person"), ("book club", "event")],
     [("The Goodness Paradox", "Wrangham", "AUTHORED_BY"), ("The Song of the Cell", "Mukherjee", "AUTHORED_BY")],
     "which popular-science titles are queued for the year and flagged for pitching",
     "pop science shelf year lineup anthropology biology club pitch candidates"),
    # --- 31 ---
    ("The autodidact electronics project lives on the dining sideboard: an Arduino Uno, a breadboard, Paul Scherz's Practical Electronics for Inventors, Sundays only.", "architecture", "personal", False,
     [("electronics project", "goal"), ("dining sideboard", "place"), ("Arduino Uno", "tool"), ("breadboard", "tool"), ("Paul Scherz", "person"), ("Practical Electronics for Inventors", "publication"), ("Sundays", "date")],
     [("Practical Electronics for Inventors", "Paul Scherz", "AUTHORED_BY"), ("electronics project", "dining sideboard", "LOCATED_IN")],
     "where does the circuits hobby live in the house and what is the weekly cadence",
     "electronics hobby location kit book day of week practice cadence"),
    # --- 32 ---
    ("Swapped evening fiction for technical reading on 2025-10-20 and regretted it by December; swapped back after the nightly reading minutes collapsed below ten.", "problem", "personal", False,
     [("evening fiction", "activity"), ("technical reading", "activity"), ("2025-10-20", "date"), ("December", "date")],
     [("evening fiction", "technical reading", "REPLACES")],
     "what reading experiment failed in late 2025 and how did I back out",
     "evening reading swap fiction vs technical minutes collapse reverse month"),
    # --- 33 ---
    ("The Anki shared decks I trust: Refold Spanish 1k, Core 2k German, Pleco-exported Mandarin HSK4, nothing auto-generated by AI in the last six months.", "preference", "personal", False,
     [("Anki", "platform"), ("Refold Spanish 1k", "tool"), ("Core 2k German", "tool"), ("Mandarin HSK4", "tool")],
     [],
     "which shared flashcard sets do I actually trust and what do I avoid",
     "anki deck allowlist human curated avoid AI generated recent window"),
    # --- 34. noise ---
    ("Hold on, I need to mark my place before I lose the page.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Joined the Stoic Reading Saturdays meetup on 2026-01-17 at the Brewhouse Cafe; we work through Long's Hellenistic Philosophy in forty-five minute chunks.", "milestone", "personal", False,
     [("Stoic Reading Saturdays", "event"), ("2026-01-17", "date"), ("Brewhouse Cafe", "place"), ("Long", "person"), ("Hellenistic Philosophy", "publication")],
     [("Hellenistic Philosophy", "Long", "AUTHORED_BY"), ("Stoic Reading Saturdays", "Brewhouse Cafe", "LOCATED_IN")],
     "when did I start the weekend philosophy meetup and what is the format",
     "stoic meetup start date cafe venue author chunk length cadence"),
    # --- 36 ---
    ("The learning log spreadsheet tracks eight fields per session: date, topic, medium, minutes, source, notes, next-action, energy level out of five.", "reference", "personal", False,
     [("learning log spreadsheet", "tool"), ("energy level", "concept")],
     [],
     "what does my self-study tracker actually capture per session",
     "learning log schema fields columns session capture tracker"),
    # --- 37 ---
    ("Prefers the Teaching Company's Great Courses audio over YouTube lectures for philosophy; less algorithm drift, better pacing, and chapter markers actually work offline.", "preference", "personal", False,
     [("Great Courses", "platform"), ("YouTube", "platform"), ("philosophy", "field")],
     [("Great Courses", "YouTube", "PREFERS")],
     "which lecture source wins for philosophy listening and why",
     "great courses over youtube pacing algorithm drift offline chapter"),
    # --- 38 ---
    ("The science-popular reading queue is paused on 2026-03-30 until the history project finishes; the split attention was costing me in both.", "decision", "personal", False,
     [("science-popular reading queue", "goal"), ("2026-03-30", "date"), ("history project", "goal")],
     [("history project", "science-popular reading queue", "REPLACES")],
     "when did I shelve one reading track for the other and why",
     "pop science pause date history priority split focus cost reason"),
    # --- 39 ---
    ("The Obsidian learning vault has 312 notes as of 2026-04-11; zettelkasten-lite, no templater, just daily notes and a map-of-content per topic.", "fact", "personal", False,
     [("Obsidian", "tool"), ("2026-04-11", "date"), ("zettelkasten-lite", "method"), ("map-of-content", "concept")],
     [],
     "how big is my notes vault and what structure does it use",
     "obsidian vault size structure method simplicity map content approach"),
    # --- 40 ---
    ("Replaced the Bose QC35 with Sony WH-1000XM5 on 2026-02-05 specifically for audiobook listening in the kitchen; better noise floor over the extractor fan.", "decision", "personal", False,
     [("Bose QC35", "tool"), ("Sony WH-1000XM5", "tool"), ("2026-02-05", "date"), ("extractor fan", "infrastructure")],
     [("Sony WH-1000XM5", "Bose QC35", "REPLACES")],
     "which headphones took over and what problem did they solve",
     "headphones swap date audiobook kitchen fan noise floor rationale"),
    # --- 41 ---
    ("The origami learning project followed John Montroll's Animal Origami for the Enthusiast cover-to-cover; eighteen models folded by 2026-03-27, the buffalo twice.", "milestone", "personal", False,
     [("origami learning project", "goal"), ("John Montroll", "person"), ("Animal Origami for the Enthusiast", "publication"), ("2026-03-27", "date"), ("buffalo", "concept")],
     [("Animal Origami for the Enthusiast", "John Montroll", "AUTHORED_BY")],
     "how did the paper-folding project progress against its reference book",
     "origami project book coverage model count re-fold date progress"),
    # --- 42 ---
    ("Chose cursive over italic for the calligraphy focus this quarter; the muscle memory carries into my handwriting letters, which italic never does.", "decision", "personal", False,
     [("cursive", "concept"), ("italic", "concept"), ("calligraphy", "hobby")],
     [("cursive", "italic", "PREFERS")],
     "which lettering style won the quarter and what practical win forced it",
     "cursive over italic quarter pick handwriting transfer muscle memory"),
    # --- 43 ---
    ("The Spanish conversation partner on iTalki is Lucia from Valencia; Tuesday 20:30 for thirty minutes, always discussing the week's El Pais article we traded.", "reference", "personal", False,
     [("Spanish", "language"), ("iTalki", "platform"), ("Lucia", "person"), ("Valencia", "place"), ("Tuesday", "date"), ("El Pais", "publication")],
     [("Lucia", "Valencia", "LIVES_IN")],
     "who is my weekly Spanish chat partner and what is our routine",
     "italki partner city weekday time duration article trade publication"),
    # --- 44 ---
    ("The kindle highlights weekly review pipeline broke on 2026-03-01 when Readwise dropped pre-2024 Kindle book imports; manual CSV export restored last month's.", "problem", "personal", False,
     [("kindle highlights", "concept"), ("2026-03-01", "date"), ("Readwise", "service"), ("CSV", "concept"), ("Kindle", "tool")],
     [("Readwise", "Kindle", "COMMUNICATES_WITH")],
     "what broke in the highlight sync and how did I recover the older month",
     "readwise import failure date older book cutoff csv manual recovery"),
    # --- 45 ---
    ("Prefers the hardback over the kindle for the history project; underlining and margin arrows survive better and I skim back chapters more often in a deep-history book.", "preference", "personal", False,
     [("hardback", "tool"), ("kindle", "tool"), ("history project", "goal")],
     [("hardback", "kindle", "PREFERS")],
     "which format wins for the deep-history reading and what behaviour forces it",
     "print over ereader history deep reading margin arrows chapter skim"),
    # --- 46 ---
    ("Started a mandarin tone-pair drill on 2026-02-08 using Mandarin Blueprint audio; the second-third tone contrast is still my weakest pair at 71% on Anki.", "milestone", "personal", False,
     [("mandarin tone-pair drill", "activity"), ("2026-02-08", "date"), ("Mandarin Blueprint", "platform"), ("Anki", "platform")],
     [],
     "when did the tone-pair practice start and what is still my worst contrast",
     "mandarin tone drill start date source weakest pair accuracy percent"),
    # --- 47 ---
    ("The history of philosophy podcast backlog hit episode 460 on 2026-04-08; two behind the feed after two weeks of evening walks skipped for storms.", "fact", "personal", False,
     [("history of philosophy podcast", "publication"), ("2026-04-08", "date"), ("evening walks", "activity"), ("storms", "event")],
     [],
     "how close am I on the long philosophy podcast and what caused the slip",
     "philosophy podcast episode tally current gap weather walk cause date"),
    # --- 48 ---
    ("Prefers the Sunday-morning cooking-as-learning slot over the Saturday one; fewer errands, the kitchen is cold, and the sourdough schedule lines up with it.", "preference", "personal", False,
     [("cooking-as-learning", "activity"), ("Sunday", "date"), ("Saturday", "date"), ("sourdough", "food")],
     [("Sunday", "Saturday", "PREFERS")],
     "which weekend slot wins for learning-to-cook sessions and what anchors it",
     "sunday over saturday cook learn errands schedule sourdough anchor"),
    # --- 49 ---
    ("The self-study plan board on the fridge lists three active tracks for 2026 Q2: Spanish to B1, Roman history to 180 AD, piano to RCM grade 3 equivalent.", "architecture", "personal", False,
     [("self-study plan board", "tool"), ("fridge", "place"), ("Spanish", "language"), ("Roman history", "field"), ("piano", "hobby"), ("RCM grade 3", "concept")],
     [("self-study plan board", "fridge", "LOCATED_IN")],
     "what are the current quarter's home-learning goals and where are they posted",
     "plan board fridge tracks target level spanish history piano quarter"),
    # --- 50 ---
    ("The Anki retention report on 2026-04-13 shows 87% mature retention across all decks, up from 81% after the 20-card daily cap and the commute mobile switch.", "fact", "personal", False,
     [("Anki", "platform"), ("2026-04-13", "date"), ("mature retention", "concept"), ("20-card daily cap", "concept")],
     [],
     "how is my flashcard retention trending after the workload and device changes",
     "anki mature retention percent delta cap mobile switch date tracking"),
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
