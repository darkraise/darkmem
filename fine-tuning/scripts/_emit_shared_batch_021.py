"""One-off emitter for shared-base batch-021 — cross domain.

Slice: learning / research / self-study meets software tooling. Writes 50 rows
to data/v2/shared/batch_021.tmp.jsonl with ids shared-01001..01050. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_021.tmp.jsonl"
ID_OFFSET = 1000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Piped my Readwise highlights into Zotero every Sunday evening so the PDF annotations sit next to the ebook quotes for thesis prep.", "architecture", "cross", False,
     [("Readwise", "service"), ("Zotero", "tool"), ("thesis", "goal")],
     [("Zotero", "Readwise", "DEPENDS_ON")],
     "how do my ebook quotes end up alongside PDF notes for graduate writing",
     "highlight aggregator citation manager weekly sync academic"),
    # --- 2 ---
    ("Bayesian statistics by Allen Downey replaced Gelman as my self-study spine because the Python notebooks match my tooling.", "decision", "cross", False,
     [("Bayesian statistics", "publication"), ("Allen Downey", "person"), ("Gelman", "person"), ("Python", "language")],
     [("Bayesian statistics", "Allen Downey", "AUTHORED_BY"), ("Bayesian statistics", "Gelman", "REPLACES")],
     "which probabilistic inference textbook became the primary study resource",
     "probabilistic inference textbook swap notebook ecosystem match"),
    # --- 3 ---
    ("A nightly cron pulls new Merriam-Webster word-of-the-day entries into a Python script that drops Anki cards tagged for the GRE prep deck.", "architecture", "cross", False,
     [("Merriam-Webster", "service"), ("Python", "language"), ("Anki", "tool"), ("GRE", "event")],
     [("Anki", "Merriam-Webster", "DEPENDS_ON")],
     "how do fresh vocabulary entries get scheduled for the standardised exam prep",
     "dictionary API scheduled flashcards admission test vocabulary"),
    # --- 4 ---
    ("The self-hosted JupyterHub on the Hetzner box keeps weekend mathematics notebooks off the work laptop.", "decision", "cross", False,
     [("JupyterHub", "service"), ("Hetzner", "organization"), ("mathematics", "field")],
     [("JupyterHub", "Hetzner", "DEPLOYED_ON")],
     "why did the hobby maths workspace leave the corporate device",
     "interactive notebook multi-user cloud VPS side-study separation"),
    # --- 5 ---
    ("Logseq holds all my molecular biology lecture notes and backlinks them to the Campbell textbook chapters by page number.", "architecture", "cross", False,
     [("Logseq", "service"), ("molecular biology", "field"), ("Campbell", "publication")],
     [],
     "how do my lecture notes and textbook chapters tie together for biology review",
     "outliner graph course notes backlink reference textbook chapters"),
    # --- 6 ---
    ("Spaced repetition intervals felt arbitrary until I read the Piotr Wozniak SM-17 paper and swapped the Anki FSRS scheduler in.", "reference", "cross", False,
     [("Piotr Wozniak", "person"), ("SM-17", "algorithm"), ("Anki", "tool"), ("FSRS", "algorithm")],
     [("FSRS", "SM-17", "BUILDS_ON")],
     "what research nudged me to change the flashcard review scheduler",
     "spaced repetition algorithm paper author scheduler upgrade"),
    # --- 7 ---
    ("Prefers Paperpile over Mendeley for the neuroscience reading group because the Google Docs citation injection just works during Wednesday calls.", "preference", "cross", False,
     [("Paperpile", "service"), ("Mendeley", "tool"), ("neuroscience", "field"), ("Google Docs", "service")],
     [("Paperpile", "Mendeley", "PREFERS")],
     "which reference manager won for the brain-science discussion group",
     "citation tool pick shared document integration journal club"),
    # --- 8 ---
    ("Hypothesis annotations on arXiv PDFs stream into Obsidian through a Pandoc filter so the Monday recap notebook stays current.", "architecture", "cross", False,
     [("Hypothesis", "service"), ("arXiv", "service"), ("Obsidian", "tool"), ("Pandoc", "tool")],
     [("Obsidian", "Hypothesis", "DEPENDS_ON")],
     "how do web-based paper annotations reach my weekly study notebook",
     "web highlight preprint server note vault conversion filter"),
    # --- 9 ---
    ("Grok the Linux kernel project finally clicked after Linux Kernel Development by Robert Love replaced the outdated Bovet edition on my desk.", "decision", "cross", False,
     [("Linux kernel", "project"), ("Linux Kernel Development", "publication"), ("Robert Love", "person"), ("Bovet", "person")],
     [("Linux Kernel Development", "Robert Love", "AUTHORED_BY"), ("Linux Kernel Development", "Bovet", "REPLACES")],
     "which systems text pushed the older one off my study stack",
     "operating system internals book swap author edition currency"),
    # --- 10. noise ---
    ("Give me a second to switch tabs.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Coursera deep-learning specialisation certificate landed on 2026-02-14 after four months of Saturday evenings.", "milestone", "cross", False,
     [("Coursera", "service"), ("deep-learning", "field"), ("2026-02-14", "date")],
     [],
     "when did the neural network MOOC certification actually finish",
     "online course completion machine learning weekend evenings date"),
    # --- 12 ---
    ("TiddlyWiki powers my Stoicism commonplace book on the old Chromebook; Dendron was too heavy for that machine.", "decision", "cross", False,
     [("TiddlyWiki", "tool"), ("Stoicism", "field"), ("Chromebook", "infrastructure"), ("Dendron", "tool")],
     [("TiddlyWiki", "Dendron", "PREFERS")],
     "which personal wiki runs my philosophy quote collection on the low-spec laptop",
     "lightweight wiki philosophy excerpts laptop performance choice"),
    # --- 13 ---
    ("Exported the Apple Health step history and ran a simple ARIMA fit in R to check whether the desk bike actually moved the needle.", "problem", "cross", False,
     [("Apple Health", "service"), ("ARIMA", "algorithm"), ("R", "language"), ("desk bike", "tool")],
     [],
     "how did I test whether the standing desk bike changed my activity baseline",
     "health export time series model personal statistics hardware trial"),
    # --- 14 ---
    ("Kindle highlights flow into Notion through the official Readwise integration so the linguistics tag shows every underlined phrase.", "architecture", "cross", False,
     [("Kindle", "tool"), ("Notion", "tool"), ("Readwise", "service"), ("linguistics", "field")],
     [("Notion", "Readwise", "DEPENDS_ON")],
     "how do e-reader underlines land in my tagged knowledge base",
     "ebook quote pipeline tagged workspace language subject filter"),
    # --- 15 ---
    ("Switched the LaTeX workflow from Overleaf to a local TeXLive install once the amateur quantum computing writeups grew past the free quota.", "decision", "cross", False,
     [("LaTeX", "language"), ("Overleaf", "service"), ("TeXLive", "tool"), ("quantum computing", "field")],
     [("TeXLive", "Overleaf", "REPLACES")],
     "why did the typesetting setup leave the browser for desktop",
     "scientific typesetting move cloud to local hobby writeups quota"),
    # --- 16 ---
    ("Lichess plus the Aimchess dashboard made it obvious that I lose most games to time pressure in the middlegame.", "fact", "cross", False,
     [("Lichess", "service"), ("Aimchess", "service"), ("middlegame", "concept")],
     [],
     "what did the chess analytics stack reveal about my losing pattern",
     "chess platform analytics clock management phase loss insight"),
    # --- 17 ---
    ("Turns out the SkySafari log syncs cleanly to a tiny Flask app so my amateur astronomy sessions show up on the bedroom TV.", "architecture", "cross", False,
     [("SkySafari", "tool"), ("Flask", "framework"), ("astronomy", "field")],
     [("Flask", "SkySafari", "DEPENDS_ON")],
     "how do my night-sky observation logs reach the living room display",
     "planetarium app observation export web dashboard hobby tracking"),
    # --- 18 ---
    ("Built a Streamlit dashboard on top of Kaggle's climate dataset for the Fellowship.ai bootcamp submission due 2026-05-01.", "milestone", "cross", False,
     [("Streamlit", "framework"), ("Kaggle", "service"), ("climate", "field"), ("Fellowship.ai", "organization"), ("2026-05-01", "date")],
     [("Streamlit", "Kaggle", "USES")],
     "when is the bootcamp climate visualisation project due and what powers it",
     "data app public dataset cohort deadline portfolio piece"),
    # --- 19 ---
    ("The CS229 lecture notes sit in DEVONthink alongside the Stanford problem sets so the full-text search covers both.", "architecture", "cross", False,
     [("CS229", "publication"), ("DEVONthink", "service"), ("Stanford", "organization")],
     [],
     "how is the machine learning course material organised for cross-search",
     "course notes document manager university problem set archive"),
    # --- 20 ---
    ("Duolingo plus Lingvist plus the Pimsleur audio files rotate weekly because relying on any single app plateaued my Korean after month three.", "problem", "cross", False,
     [("Duolingo", "tool"), ("Lingvist", "tool"), ("Pimsleur", "tool"), ("Korean", "language")],
     [],
     "why did the language-learning stack turn into three rotating apps",
     "multi-app rotation plateau hangul retention listening reading"),
    # --- 21 ---
    ("The Oura ring exports JSON nightly into a DuckDB file that I query with a Quarto notebook each Sunday.", "architecture", "cross", False,
     [("Oura", "tool"), ("DuckDB", "database"), ("Quarto", "tool")],
     [("Quarto", "DuckDB", "USES")],
     "how do my sleep ring readings end up in a weekly review notebook",
     "wearable export analytics database reproducible report cadence"),
    # --- 22 ---
    ("Prefers streaming Feynman's QED lectures through Plex over Griffiths' textbook when the kids ask how light behaves.", "preference", "cross", False,
     [("Feynman", "person"), ("QED", "publication"), ("Plex", "service"), ("Griffiths", "person"), ("light", "concept")],
     [("QED", "Feynman", "AUTHORED_BY"), ("QED", "Griffiths", "PREFERS")],
     "which physics resource do I pull out for children's questions about optics",
     "popular physics lectures against textbook family explanation photons"),
    # --- 23 ---
    ("Khan Academy progress for my cousin goes into a shared Airtable so grandma can see the calculus streak from Lisbon.", "architecture", "cross", False,
     [("Khan Academy", "service"), ("Airtable", "service"), ("calculus", "field"), ("Lisbon", "place")],
     [],
     "how does my cousin's online math progress become visible to a grandparent abroad",
     "tutoring platform tracker family visibility remote relative spreadsheet"),
    # --- 24 ---
    ("Solving the exercises in Sipser's Theory of Computation went faster once the pumping lemma notes lived in a tagged Obsidian folder.", "fact", "cross", False,
     [("Sipser", "person"), ("Theory of Computation", "publication"), ("pumping lemma", "concept"), ("Obsidian", "service")],
     [("Theory of Computation", "Sipser", "AUTHORED_BY")],
     "what organising trick made the automata textbook exercises tractable",
     "formal languages textbook proof technique note taxonomy study win"),
    # --- 25 ---
    ("Built a Discord bot in Go that rotates the arXiv machine learning digest into the paper-reading channel every morning at 8 AM sharp.", "architecture", "cross", False,
     [("Discord", "service"), ("Go", "language"), ("arXiv", "service"), ("machine learning", "field")],
     [("Discord", "arXiv", "COMMUNICATES_WITH")],
     "how does the paper reading group get its morning preprint feed",
     "chat bot preprint digest scheduled post reading club automation"),
    # --- 26. noise ---
     ("Sure, happy to help with that.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("The ChessBase opening tree now imports from Lichess studies so my Caro-Kann prep stays in one view.", "architecture", "cross", False,
     [("ChessBase", "tool"), ("Lichess", "service"), ("Caro-Kann", "concept")],
     [("ChessBase", "Lichess", "DEPENDS_ON")],
     "how is my chess opening preparation unified across two platforms",
     "desktop database online studies opening repertoire consolidation"),
    # --- 28 ---
    ("Hargrave's introduction to group theory, loaded into Calibre on the weekend laptop, finally replaced Dummit and Foote for the abstract algebra sessions.", "decision", "cross", False,
     [("Hargrave", "person"), ("group theory", "field"), ("Calibre", "service"), ("Dummit and Foote", "publication"), ("abstract algebra", "field")],
     [("Hargrave", "Dummit and Foote", "PREFERS")],
     "which algebra text took over the weekend self-study slot",
     "abstract math textbook swap approachable proof density weekend"),
    # --- 29 ---
    ("Logged 365 consecutive days of the Leitner box on 2026-03-30 after the paper cards got rebuilt in a Python reminder script.", "milestone", "cross", False,
     [("Leitner box", "method"), ("2026-03-30", "date"), ("Python", "language")],
     [],
     "when did the daily flashcard streak hit a full year",
     "spaced retrieval system anniversary scripted reminder habit"),
    # --- 30 ---
    ("A curl-driven pipeline dumps the MIT OpenCourseWare lecture transcripts into Whisper-corrected Markdown for the commute audio.", "architecture", "cross", False,
     [("curl", "tool"), ("MIT OpenCourseWare", "service"), ("Whisper", "library"), ("Markdown", "language")],
     [("curl", "MIT OpenCourseWare", "USES")],
     "how do open university lectures become walkable transcripts",
     "command line fetcher open coursework transcription cleanup commute"),
    # --- 31 ---
    ("Frustration peaked when Zotero's iPad sync silently dropped two chapters of annotations before the Tuesday seminar.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Zotero", "tool"), ("iPad", "infrastructure"), ("seminar", "event")],
     [],
     "what went wrong with the mobile reference sync before a class meeting",
     "annotation loss tablet cloud reference manager seminar prep"),
    # --- 32 ---
    ("The Karpathy zero-to-hero playlist drove the Sunday transformer build-along in PyTorch with my study buddy Mei in Taipei.", "reference", "cross", False,
     [("Karpathy", "person"), ("zero-to-hero", "publication"), ("transformer", "concept"), ("PyTorch", "framework"), ("Mei", "person"), ("Taipei", "place")],
     [("zero-to-hero", "Karpathy", "AUTHORED_BY")],
     "which video series anchors the weekly neural-net pair study call",
     "tutorial series architecture rebuild remote partner weekly session"),
    # --- 33 ---
    ("Turned the Open Library API into a Raycast extension so typing a title grabs the ISBN straight into my Zotero inbox.", "architecture", "cross", False,
     [("Open Library", "service"), ("Raycast", "tool"), ("Zotero", "tool")],
     [("Raycast", "Open Library", "USES")],
     "how do book titles get captured into the citation inbox in one keystroke",
     "public catalog launcher extension reference queue workflow"),
    # --- 34 ---
    ("Found that the Feynman technique, written out in Notion by hand, beats any AI summary when studying the Standard Model.", "fact", "cross", False,
     [("Feynman technique", "method"), ("Notion", "service"), ("Standard Model", "theory")],
     [],
     "what study method keeps winning for deep physics concepts over AI summaries",
     "plain language recap workspace particle physics active learning"),
    # --- 35 ---
    ("Locked in the conversation practice with Pablo through Tandem every Thursday because Italki tutors were never available late.", "decision", "cross", False,
     [("conversation practice", "method"), ("Pablo", "person"), ("Tandem", "service"), ("Italki", "service")],
     [("Tandem", "Italki", "PREFERS")],
     "which language exchange service won the evening slot",
     "tandem partner scheduling timezone tutor availability conversation"),
    # --- 36 ---
    ("The Rust Programming Language book replaced Programming Rust once the Tokio async chapter got rewritten in the 2024 edition.", "decision", "cross", False,
     [("Rust Programming Language", "publication"), ("Programming Rust", "publication"), ("Tokio", "library"), ("async", "concept")],
     [("Rust Programming Language", "Programming Rust", "REPLACES")],
     "which Rust reference took over my shelf after the async rewrite",
     "language book swap async chapter edition update study stack"),
    # --- 37 ---
    ("Reached the milestone of reading Goedel, Escher, Bach cover to cover on 2026-04-07 with margin notes collected in Supernote and synced to Obsidian.", "milestone", "cross", False,
     [("Goedel, Escher, Bach", "publication"), ("2026-04-07", "date"), ("Supernote", "tool"), ("Obsidian", "service")],
     [],
     "when did the long Hofstadter read finally wrap up and where do the notes live",
     "recursive systems classic completion e-ink notebook marginalia"),
    # --- 38 ---
    ("Hooked a raspberry Pi Pico to the microscope so the Drosophila behaviour video stamps timestamps into the SQLite lab journal automatically.", "architecture", "cross", False,
     [("raspberry Pi Pico", "infrastructure"), ("microscope", "tool"), ("Drosophila", "concept"), ("SQLite", "database")],
     [("raspberry Pi Pico", "SQLite", "COMMUNICATES_WITH")],
     "how does the fruit-fly observation rig log itself into the lab notebook",
     "microcontroller scope timestamp embedded database biology log"),
    # --- 39 ---
    ("Khan Academy progress tracking sat in a Google Sheet until the custom Apps Script finally pushed daily deltas into Habitica.", "decision", "cross", False,
     [("Khan Academy", "service"), ("Google Sheet", "tool"), ("Apps Script", "language"), ("Habitica", "service")],
     [("Habitica", "Google Sheet", "REPLACES")],
     "what app finally replaced the spreadsheet for study habit gamification",
     "learning tracker spreadsheet sunset automation habit RPG"),
    # --- 40 ---
    ("The Cambridge Handbook of Computing Education, pinned in Zotero, replaced a stack of blog posts because the cognitive load research is properly cited.", "reference", "cross", False,
     [("Cambridge Handbook of Computing Education", "publication"), ("Zotero", "service"), ("cognitive load", "theory"), ("blog posts", "pattern")],
     [("Cambridge Handbook of Computing Education", "blog posts", "REPLACES")],
     "which teaching resource displaced scattered online essays for pedagogy prep",
     "academic handbook cognitive theory citations programming education"),
    # --- 41 ---
    ("Prefers building Jupyter kernels for every class I teach over shared Colab notebooks because air-gapped demos still need to work.", "preference", "cross", False,
     [("Jupyter", "tool"), ("Colab", "service"), ("air-gapped", "pattern")],
     [("Jupyter", "Colab", "PREFERS")],
     "why do local notebooks still beat the cloud option for my teaching",
     "kernel local classroom offline backup pedagogical reliability"),
    # --- 42 ---
    ("The GitHub Classroom autograder stumbled on edge cases until I wired nbgrader into the same container image as the course Docker stack.", "problem", "cross", False,
     [("GitHub Classroom", "service"), ("nbgrader", "library"), ("Docker", "tool")],
     [("nbgrader", "Docker", "DEPLOYED_ON")],
     "how did the notebook grading setup stop missing edge cases",
     "autograder classroom container image combined grading pipeline"),
    # --- 43 ---
    ("My Coursera Scala specialisation capstone used a small Akka cluster on a single laptop to finally grok actor supervision.", "fact", "cross", False,
     [("Coursera", "service"), ("Scala", "language"), ("Akka", "framework"), ("actor supervision", "concept")],
     [("Akka", "actor supervision", "IMPLEMENTS")],
     "what hands-on project made the concurrency supervision idea click",
     "online specialisation functional language actor framework laptop cluster"),
    # --- 44 ---
    ("Self-study schedule for category theory keeps a Toggl timer running while Mac Lane's book sits open on the iPad Pro.", "architecture", "cross", False,
     [("category theory", "field"), ("Toggl", "service"), ("Mac Lane", "person"), ("iPad Pro", "infrastructure")],
     [],
     "how is study time logged while reading the tough abstract math book",
     "time tracker mathematician textbook tablet reading deep focus"),
    # --- 45 ---
    ("Wrote an R Markdown pipeline that turns the Polar heart rate export into a PDF exercise physiology journal mailed to my coach Saturday mornings.", "architecture", "cross", False,
     [("R Markdown", "framework"), ("Polar", "tool"), ("exercise physiology", "field"), ("journal", "pattern")],
     [("R Markdown", "Polar", "USES")],
     "how does the weekly training report reach the coach automatically",
     "reproducible doc heart-rate wearable PDF mail coaching loop"),
    # --- 46 ---
    ("The 2026-03-15 homework delay for the Harvard CS50x final came from a Linode outage that took the shared Docker registry offline.", "problem", "cross", False,
     [("2026-03-15", "date"), ("CS50x", "event"), ("Linode", "service"), ("Docker", "tool")],
     [],
     "what caused the online course final project to miss its deadline",
     "MOOC assignment slip VPS outage container registry downtime"),
    # --- 47 ---
    ("Confidence in Bayes grew when PyMC examples confirmed the bootstrap estimates from Efron's original 1979 paper.", "fact", "cross", False,
     [("Bayes", "theory"), ("PyMC", "library"), ("Efron", "person"), ("bootstrap", "method")],
     [("PyMC", "bootstrap", "IMPLEMENTS"), ("bootstrap", "Efron", "AUTHORED_BY")],
     "what built my trust in probabilistic inference code against classical statistics",
     "Bayesian library resampling classic paper agreement validation"),
    # --- 48 ---
    ("The Sabine reverberation theory shaped the room-correction script that runs in REW every time the study bookshelf moves.", "reference", "cross", False,
     [("Sabine", "person"), ("reverberation", "theory"), ("REW", "service")],
     [("REW", "reverberation", "IMPLEMENTS")],
     "which acoustics theory drives my study-room measurement routine",
     "acoustic pioneer physics theory measurement software home setup"),
    # --- 49 ---
    ("Curiosity peaked reading the Chincilla scaling paper so I spun up a tiny nanoGPT run on the RTX 3090 just to feel the token loss curve.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("Chincilla", "publication"), ("nanoGPT", "project"), ("RTX 3090", "infrastructure")],
     [("nanoGPT", "Chincilla", "BUILDS_ON")],
     "what paper made me run a small language model experiment on the home GPU",
     "scaling law study tiny transformer home training emotion spark"),
    # --- 50 ---
    ("Organic chemistry flashcards built in Remnote with the Clayden textbook structures beat the Sketchy videos for retention in the November retest.", "fact", "cross", False,
     [("Organic chemistry", "field"), ("Remnote", "tool"), ("Clayden", "publication"), ("Sketchy", "service")],
     [("Remnote", "Sketchy", "PREFERS")],
     "which study combination won for the chemistry exam do-over",
     "mechanism flashcards textbook structures video course retention retest"),
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
