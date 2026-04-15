"""One-off emitter for shared-base batch-124 — cross domain.

Slice: personal knowledge management and journaling meets tech (Obsidian,
Logseq, Roam, Tana, Capacities, Notion, Bear, Craft, Reflect, Mem.ai, Day One,
Standard Notes, zettelkasten-in-plaintext, git-versioned vaults, Pandoc,
Mermaid, reMarkable/Supernote/Boox handwriting sync, PKM authors like Tiago
Forte, Sönke Ahrens, Andy Matuschak). Writes 50 rows to
data/v2/shared/batch_124.tmp.jsonl with ids shared-06151..06200. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_124.tmp.jsonl"
ID_OFFSET = 6150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the personal vault from Roam Research to Obsidian on 2026-02-12 after the Roam subscription renewal stung and self-hosting the plaintext markdown finally won out.", "milestone", "cross", False,
     [("Roam Research", "tool"), ("Obsidian", "tool"), ("2026-02-12", "date")],
     [("Obsidian", "Roam Research", "REPLACES")],
     "when did the personal knowledge base leave Roam and land in Obsidian",
     "pkm vault migration plaintext markdown self host subscription price"),
    # --- 2 ---
    ("Prefers Logseq over Notion for the daily-notes graph because Logseq's outliner blocks link back cleanly without Notion's database overhead for a solo journaling practice.", "preference", "cross", False,
     [("Logseq", "tool"), ("Notion", "tool")],
     [("Logseq", "Notion", "PREFERS")],
     "which outliner wins for solo daily-notes journaling",
     "outliner block graph daily notes journaling solo practice preference"),
    # --- 3 ---
    ("The Dataview plugin replaced a hand-maintained index note in the Obsidian vault on 2026-03-05 because querying the frontmatter tag cloud beat grepping the 1200 notes by hand.", "decision", "cross", False,
     [("Dataview", "library"), ("Obsidian", "tool"), ("2026-03-05", "date")],
     [("Dataview", "Obsidian", "USES")],
     "why did the vault index stop being maintained by hand",
     "dataview plugin frontmatter query index automation tag scan vault"),
    # --- 4 ---
    ("Templater handles the daily-notes boilerplate that Obsidian's core Templates plugin couldn't because Templater's JavaScript hooks run the weather fetch and the calendar pull at note-open time.", "architecture", "cross", False,
     [("Templater", "library"), ("Obsidian", "tool"), ("JavaScript", "language")],
     [("Templater", "Obsidian", "DEPLOYED_ON"), ("Templater", "JavaScript", "USES")],
     "how do the daily note templates get weather and calendar inline",
     "templater javascript hook note open time weather calendar dynamic"),
    # --- 5 ---
    ("Tana improves_on Notion for the meeting-notes workflow because supertags auto-propagate the attendee backlinks that Notion's relation property never kept in sync after rename.", "decision", "cross", False,
     [("Tana", "tool"), ("Notion", "tool")],
     [("Tana", "Notion", "IMPROVES_ON")],
     "which PKM tool handled meeting notes better than Notion",
     "supertag attendee backlink relation rename sync meeting workflow"),
    # --- 6. noise ---
    ("Hmm, I'll circle back on that in a moment.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Sönke Ahrens's How to Take Smart Notes reshaped the atomic-note practice after the 2026-01-18 weekend reread because the literature-note versus permanent-note split finally clicked.", "fact", "cross", False,
     [("Sönke Ahrens", "person"), ("How to Take Smart Notes", "publication"), ("2026-01-18", "date")],
     [("How to Take Smart Notes", "Sönke Ahrens", "AUTHORED_BY")],
     "which book reshaped the atomic note split in January",
     "zettelkasten literature note permanent note atomic practice reread"),
    # --- 8 ---
    ("Andy Matuschak's evergreen-notes style replaced the daily-journal dumping ground in my vault because the title-as-claim rule forced the claims to actually stand on their own.", "decision", "cross", False,
     [("Andy Matuschak", "person"), ("evergreen-notes", "pattern")],
     [("evergreen-notes", "Andy Matuschak", "AUTHORED_BY")],
     "whose note style replaced the journal-dump approach in the vault",
     "evergreen notes title as claim standalone writing vault practice"),
    # --- 9 ---
    ("Tiago Forte's Second Brain PARA method got shelved after six weeks because the Projects-Areas-Resources-Archive hierarchy fought every link the zettelkasten wanted to make.", "problem", "cross", False,
     [("Tiago Forte", "person"), ("Second Brain", "publication"), ("PARA", "pattern")],
     [("Second Brain", "Tiago Forte", "AUTHORED_BY")],
     "which PKM method got dropped for fighting the link structure",
     "para hierarchy zettelkasten link conflict folder organization shelf"),
    # --- 10 ---
    ("The vault lives in a git repo on a Hetzner box and pushes every 15 minutes through the Obsidian Git plugin so the 2026-03-20 laptop-drive failure lost exactly zero notes.", "architecture", "cross", False,
     [("git", "tool"), ("Hetzner", "organization"), ("Obsidian Git", "library"), ("2026-03-20", "date")],
     [("Obsidian Git", "git", "USES")],
     "how did the vault survive the March laptop drive failure with no data loss",
     "git versioned vault auto push interval disaster recovery self host"),
    # --- 11 ---
    ("Bear replaced Apple Notes on the iPad for the reading-commonplace book because Bear's markdown export through Pandoc actually survived round-trip to the vault.", "decision", "cross", False,
     [("Bear", "tool"), ("Apple Notes", "service"), ("iPad", "infrastructure"), ("Pandoc", "tool")],
     [("Bear", "Apple Notes", "REPLACES"), ("Bear", "Pandoc", "USES")],
     "which note app handled the commonplace book on the tablet",
     "markdown export round trip commonplace book tablet reading capture"),
    # --- 12 ---
    ("Reflect's AI-assisted backlink suggestions beat Mem.ai for the 2026-02-27 to 2026-03-14 trial because Reflect's end-to-end encryption meant the therapy-journal entries stayed off the training set.", "decision", "cross", False,
     [("Reflect", "tool"), ("Mem.ai", "tool"), ("2026-02-27", "date"), ("2026-03-14", "date")],
     [("Reflect", "Mem.ai", "PREFERS")],
     "which AI journaling app won the late-February trial window",
     "ai backlink suggestion encrypted journal privacy trial evaluation"),
    # --- 13 ---
    ("Standard Notes holds the locked therapy journal because the Extended subscription's daily encrypted backups to Dropbox beat Day One's iCloud-only sync for the paranoia threshold.", "architecture", "cross", False,
     [("Standard Notes", "tool"), ("Dropbox", "service"), ("Day One", "tool"), ("iCloud", "service")],
     [("Standard Notes", "Dropbox", "USES"), ("Standard Notes", "Day One", "PREFERS")],
     "where does the sensitive therapy journal actually live and sync to",
     "encrypted journal backup destination paranoia sync therapy private"),
    # --- 14 ---
    ("Day One's 2026-01-01 year-in-review export to PDF through Pandoc produced a 184-page photobook that the Blurb upload accepted without a single layout complaint.", "milestone", "cross", False,
     [("Day One", "tool"), ("2026-01-01", "date"), ("PDF", "concept"), ("Pandoc", "tool"), ("Blurb", "service")],
     [("Day One", "Pandoc", "COMMUNICATES_WITH")],
     "how did the year-in-review journal become a printed photobook",
     "year review export pdf photobook print pipeline yearly recap journal"),
    # --- 15 ---
    ("Capacities replaced Notion as the object-based knowledge store on 2026-02-08 because Capacities's native Object type for books, people, and places stopped me from building three redundant Notion databases.", "decision", "cross", False,
     [("Capacities", "tool"), ("Notion", "tool"), ("2026-02-08", "date")],
     [("Capacities", "Notion", "REPLACES")],
     "which object-based PKM tool took over for Notion in February",
     "object based pkm native type book person place database redundancy"),
    # --- 16 ---
    ("Craft lost out for the travel journal in 2026 because the cross-vault link into the main Obsidian notes required a manual deep-link paste every single entry.", "problem", "cross", False,
     [("Craft", "tool"), ("Obsidian", "tool")],
     [],
     "what tripped up Craft as the travel journal this year",
     "cross app deep link manual paste travel journal backlink friction"),
    # --- 17 ---
    ("Prefers plaintext zettelkasten over any database-backed PKM because when Roam shut its research lab doors the 2024 vault was already safe as flat markdown files.", "preference", "cross", False,
     [("zettelkasten", "pattern"), ("Roam", "tool")],
     [("zettelkasten", "Roam", "PREFERS")],
     "why does the PKM system stay on plaintext rather than a database",
     "plaintext portability database shutdown risk pkm longevity archive"),
    # --- 18 ---
    ("The Mermaid code blocks in the vault render natively in Obsidian's reading view, so the 2026-03-30 project-architecture diagram stopped living in a separate diagrams.net file.", "architecture", "cross", False,
     [("Mermaid", "library"), ("Obsidian", "tool"), ("2026-03-30", "date"), ("diagrams.net", "tool")],
     [("Obsidian", "Mermaid", "USES"), ("Mermaid", "diagrams.net", "REPLACES")],
     "where did the project architecture diagram move to in late March",
     "mermaid diagram inline markdown reading view diagrams net replace"),
    # --- 19 ---
    ("Pandoc turns the weekly-review note into a nicely typeset LaTeX PDF every Sunday because the Beamer output prints out on the Brother laser for the fridge-door review ritual.", "architecture", "cross", False,
     [("Pandoc", "tool"), ("LaTeX", "language"), ("PDF", "concept"), ("Beamer", "library"), ("Brother", "organization")],
     [("Pandoc", "LaTeX", "USES"), ("Pandoc", "Beamer", "USES")],
     "how does the weekly review note become a printed artifact each Sunday",
     "pandoc latex pdf beamer weekly review printout ritual export"),
    # --- 20 ---
    ("The reMarkable 2 handwritten notes sync to a watched folder on the laptop through the rmapi CLI and a cron job converts them to searchable PDFs via OCRmyPDF for the vault.", "architecture", "cross", False,
     [("reMarkable 2", "infrastructure"), ("rmapi", "tool"), ("cron", "tool"), ("OCRmyPDF", "tool"), ("PDF", "concept")],
     [("rmapi", "reMarkable 2", "USES"), ("OCRmyPDF", "rmapi", "USES")],
     "how do the paper-tablet handwritten notes become searchable in the vault",
     "remarkable handwriting sync ocr pdf cli cron pipeline watched folder"),
    # --- 21 ---
    ("The Supernote A5X kept the 2026-03-12 meeting shorthand intact while the iPad with Procreate lost the palm-rejection fight three times in the same meeting.", "decision", "cross", False,
     [("Supernote A5X", "infrastructure"), ("2026-03-12", "date"), ("iPad", "infrastructure"), ("Procreate", "tool")],
     [("Supernote A5X", "iPad", "PREFERS")],
     "which handwriting device kept the March 12 meeting notes clean",
     "eink handwriting meeting shorthand palm rejection tablet comparison"),
    # --- 22 ---
    ("The Boox Note Air 3C replaced the reMarkable on 2026-03-25 because the color e-ink finally let the Zettelkasten color-tag system survive the paper-to-vault crossover.", "milestone", "cross", False,
     [("Boox Note Air 3C", "infrastructure"), ("reMarkable", "infrastructure"), ("2026-03-25", "date"), ("Zettelkasten", "pattern")],
     [("Boox Note Air 3C", "reMarkable", "REPLACES")],
     "when did the color e-ink tablet take over from the reMarkable",
     "color eink handwriting tablet zettelkasten color tag migration"),
    # --- 23 ---
    ("Curiosity sparked a weekend rabbit hole when Maggie Appleton's garden post explained why my Obsidian vault's graph looked like yarn and hers looked like a living network.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Maggie Appleton", "person"), ("Obsidian", "tool")],
     [],
     "whose blog post set off the weekend rabbit hole on graph shape",
     "digital garden graph topology essayist blog inspiration weekend read"),
    # --- 24 ---
    ("The daily-notes discipline finally stuck after 2026-01-20 because the Templater morning-pages template pre-fills yesterday's unresolved TODO blocks so the blank page never appeared.", "milestone", "cross", False,
     [("Templater", "library"), ("2026-01-20", "date")],
     [],
     "what finally made the daily-notes habit actually stick",
     "daily notes discipline habit template morning pages todo carryover"),
    # --- 25 ---
    ("The Periodic Notes plugin drives the weekly and monthly review pages in Obsidian because stacking it with Dataview aggregates last week's tagged mood entries into a single table.", "architecture", "cross", False,
     [("Periodic Notes", "library"), ("Obsidian", "tool"), ("Dataview", "library")],
     [("Periodic Notes", "Obsidian", "DEPLOYED_ON"), ("Periodic Notes", "Dataview", "COMMUNICATES_WITH")],
     "how do the weekly and monthly review pages get assembled in the vault",
     "periodic notes weekly monthly review dataview aggregate mood tag"),
    # --- 26 ---
    ("The Readwise to Obsidian export replaced the manual Kindle-highlights copy-paste on 2026-02-01 because the literature-note stub per book finally kept up with my reading pace.", "decision", "cross", False,
     [("Readwise", "service"), ("Obsidian", "tool"), ("2026-02-01", "date"), ("Kindle", "infrastructure")],
     [("Readwise", "Kindle", "REPLACES")],
     "when did the reading highlights stop being copy-pasted by hand",
     "readwise kindle highlight import literature note reading capture"),
    # --- 27 ---
    ("Frustration hit when the Logseq Sync service choked on a 60MB asset folder mid-save and the native Logseq graph rolled back two mornings of dream-journal entries.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Logseq Sync", "service"), ("Logseq", "tool")],
     [("Logseq Sync", "Logseq", "IS_A")],
     "what PKM sync service wiped out two days of dream journaling",
     "logseq sync asset size rollback dream journal data loss"),
    # --- 28 ---
    ("Prefers Obsidian Sync over Syncthing for the vault now because the end-to-end encryption plus iOS background refresh actually wins against Syncthing's sleeping-iPhone quirks.", "preference", "cross", False,
     [("Obsidian Sync", "service"), ("Syncthing", "tool"), ("iOS", "infrastructure"), ("iPhone", "infrastructure")],
     [("Obsidian Sync", "Syncthing", "PREFERS")],
     "which sync tool actually keeps the vault current on the phone",
     "obsidian sync syncthing ios background refresh encrypted comparison"),
    # --- 29 ---
    ("Linking Your Thinking's 2026-01 cohort from Nick Milo pushed the MOC approach into the vault and the maps-of-content finally replaced the tag-index notes that never got read.", "milestone", "cross", False,
     [("Linking Your Thinking", "organization"), ("2026-01", "date"), ("Nick Milo", "person"), ("MOC", "pattern")],
     [("Nick Milo", "Linking Your Thinking", "KNOWS")],
     "what cohort reshaped the vault navigation with maps of content",
     "moc map of content cohort course nick milo tag index replacement"),
    # --- 30 ---
    ("The Hugo static-site publish pipeline from a Quartz-powered Obsidian subfolder went live on 2026-03-15 so the public digital garden stopped being a manual copy-paste job.", "milestone", "cross", False,
     [("Hugo", "tool"), ("Quartz", "library"), ("Obsidian", "tool"), ("2026-03-15", "date")],
     [("Quartz", "Hugo", "USES"), ("Quartz", "Obsidian", "DEPLOYED_ON")],
     "when did the public digital garden stop needing manual publishing",
     "digital garden static site publish pipeline quartz hugo vault subset"),
    # --- 31 ---
    ("Joy hit when the 2026-03-28 morning review noticed Dad's 70th-birthday toast draft was already half-written in a fleeting note from three weeks earlier.", "fact", "cross", False,
     [("Joy", "emotion"), ("2026-03-28", "date"), ("Dad", "person")],
     [],
     "what surprise did the end-of-March review pull out of the fleeting-notes folder",
     "fleeting note surprise birthday toast pkm compounding return pleasant"),
    # --- 32 ---
    ("Prefers handwritten morning pages in the Leuchtturm1917 over typed entries in Obsidian because the slower pace actually surfaces the anxieties a keyboard skips over.", "preference", "cross", False,
     [("Leuchtturm1917", "infrastructure"), ("Obsidian", "tool")],
     [("Leuchtturm1917", "Obsidian", "PREFERS")],
     "which journaling medium actually gets at the underlying anxieties",
     "morning pages handwritten notebook typed journal pace surface anxiety"),
    # --- 33 ---
    ("The Zotero integration with the Better BibTeX plugin drops citation keys straight into the Obsidian literature notes, so the 2026-03-09 thesis-draft bibliography exported cleanly through Pandoc.", "architecture", "cross", False,
     [("Zotero", "tool"), ("Better BibTeX", "library"), ("Obsidian", "tool"), ("2026-03-09", "date"), ("Pandoc", "tool")],
     [("Better BibTeX", "Zotero", "DEPLOYED_ON"), ("Zotero", "Obsidian", "COMMUNICATES_WITH")],
     "how did the thesis bibliography flow from reference manager to final PDF",
     "zotero citation key bibtex literature note bibliography pandoc pipeline"),
    # --- 34. noise ---
    ("Let me pull that thread for a moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The 750 Words daily prompt service lost to a local Obsidian template on 2026-02-19 because exporting the 2024 archive as CSV took the site 11 days and a support ticket.", "decision", "cross", False,
     [("750 Words", "service"), ("Obsidian", "tool"), ("2026-02-19", "date"), ("CSV", "concept")],
     [("Obsidian", "750 Words", "REPLACES")],
     "when did the morning-pages service get dropped for a local template",
     "morning pages daily prompt service export lag portability migration"),
    # --- 36 ---
    ("The Kanban plugin replaced Trello for the writing-projects board inside Obsidian because the Kanban cards link directly to the draft notes instead of copying titles by hand.", "decision", "cross", False,
     [("Kanban", "library"), ("Trello", "service"), ("Obsidian", "tool")],
     [("Kanban", "Trello", "REPLACES"), ("Kanban", "Obsidian", "DEPLOYED_ON")],
     "which writing-projects board replaced Trello in the vault",
     "kanban board writing projects plugin vault draft link replace"),
    # --- 37 ---
    ("Mem.ai improves_on Apple Notes for the captured voice memos because Mem's Whisper-based transcription tags the speaker and the topic before the note even hits the inbox.", "decision", "cross", False,
     [("Mem.ai", "tool"), ("Apple Notes", "service"), ("Whisper", "library")],
     [("Mem.ai", "Apple Notes", "IMPROVES_ON"), ("Mem.ai", "Whisper", "USES")],
     "which app handles the captured voice memos better than Apple Notes",
     "voice memo whisper transcription tag inbox capture ai improvement"),
    # --- 38 ---
    ("The vault's Smart Connections plugin runs a local OpenAI-compatible endpoint against a llama.cpp server so the semantic backlinks stop leaking the therapy-journal passages to OpenAI proper.", "architecture", "cross", False,
     [("Smart Connections", "library"), ("OpenAI", "service"), ("llama.cpp", "tool")],
     [("Smart Connections", "llama.cpp", "USES"), ("Smart Connections", "OpenAI", "REPLACES")],
     "how do the AI backlink suggestions stay off the cloud for private notes",
     "smart connections local inference llama cpp private semantic backlink"),
    # --- 39 ---
    ("Relief washed over me when the 2026-03-22 power outage killed the desktop mid-save and the Syncthing-backed vault on the phone had already rolled the last paragraph forward.", "milestone", "cross", False,
     [("Relief", "emotion"), ("2026-03-22", "date"), ("Syncthing", "tool")],
     [],
     "what saved the draft paragraph when the desktop crashed during the outage",
     "sync recovery power outage crash mid save vault resilience relief"),
    # --- 40 ---
    ("The Obsidian Publish monthly bill got canceled once the Quartz on Cloudflare Pages setup matched the feature set for the Second Brain-adjacent digital garden for free.", "decision", "cross", False,
     [("Obsidian Publish", "service"), ("Quartz", "library"), ("Cloudflare Pages", "service"), ("Second Brain", "publication")],
     [("Quartz", "Obsidian Publish", "REPLACES"), ("Quartz", "Cloudflare Pages", "DEPLOYED_ON")],
     "which setup replaced the paid publish subscription for the public vault",
     "obsidian publish quartz cloudflare pages self host cost swap"),
    # --- 41 ---
    ("Grief after Nana's death on 2026-02-11 pushed me into a locked Day One journal for six weeks because the main vault felt too public even with the folder-hidden tag.", "fact", "cross", False,
     [("Grief", "emotion"), ("Nana", "person"), ("2026-02-11", "date"), ("Day One", "tool")],
     [],
     "what prompted the six-week move to a locked journal after February",
     "grief private journal separate space locked day one emotional safety"),
    # --- 42 ---
    ("Prefers the Minimal theme over the default Obsidian theme because the tighter typography matches the printed Leuchtturm1917 aesthetic and the weekly-review page feels less like a terminal.", "preference", "cross", False,
     [("Minimal", "library"), ("Obsidian", "tool"), ("Leuchtturm1917", "infrastructure")],
     [("Minimal", "Obsidian", "DEPLOYED_ON")],
     "which Obsidian theme matches the paper-notebook aesthetic best",
     "obsidian theme typography minimal paper notebook aesthetic preference"),
    # --- 43 ---
    ("The PARA-to-LYT refactor took 2026-01-26 through 2026-02-14 to finish because the 1400 notes had to get touched one by one for the new MOC backlinks to take hold.", "milestone", "cross", False,
     [("PARA", "pattern"), ("LYT", "pattern"), ("2026-01-26", "date"), ("2026-02-14", "date"), ("MOC", "pattern")],
     [("LYT", "PARA", "REPLACES")],
     "how long did the vault refactor from PARA to LYT actually take",
     "para lyt refactor vault reorganize map of content migration duration"),
    # --- 44 ---
    ("The Advanced Tables plugin rescued the reading-log markdown table after 2026-03-03 because hand-editing 300-row pipe tables in plain vim was eating 40 minutes a week.", "decision", "cross", False,
     [("Advanced Tables", "library"), ("vim", "tool"), ("2026-03-03", "date")],
     [],
     "what plugin replaced hand-editing the reading-log markdown table",
     "advanced tables markdown editing vim reading log pipe table pain"),
    # --- 45 ---
    ("Reading Christian Tietze's zettelkasten-method blog on 2026-02-06 set the unique-ID-as-timestamp rule for every new note so that renaming never broke a link again.", "reference", "cross", False,
     [("Christian Tietze", "person"), ("2026-02-06", "date"), ("zettelkasten", "pattern")],
     [],
     "whose blog set the timestamp-as-ID rule in the zettelkasten",
     "unique id timestamp rename stable link zettelkasten method blog"),
    # --- 46 ---
    ("Tana improves_on Roam Research for the CRM-style people notes because Tana's supertag templates propagate the birthday and last-contact fields that Roam's attributes needed a query per view.", "decision", "cross", False,
     [("Tana", "tool"), ("Roam Research", "tool")],
     [("Tana", "Roam Research", "IMPROVES_ON")],
     "which tool handles the CRM-style people notes better than Roam",
     "tana supertag template people crm birthday last contact propagation"),
    # --- 47 ---
    ("Obsidian Sync replaced the self-hosted Syncthing relay on 2026-03-18 after the relay box died during a kernel upgrade and the phone vault went stale mid-trip to Porto.", "milestone", "cross", False,
     [("Obsidian Sync", "service"), ("Syncthing", "tool"), ("2026-03-18", "date"), ("Porto", "place")],
     [("Obsidian Sync", "Syncthing", "REPLACES")],
     "when did the vault sync finally leave the self-hosted relay behind",
     "obsidian sync syncthing relay failure kernel upgrade stale mobile vault"),
    # --- 48 ---
    ("The QuickAdd macro triggers the Mermaid-flowchart template plus the frontmatter stub plus the daily-note backlink in one keystroke, so capturing a shower-thought takes six seconds flat.", "architecture", "cross", False,
     [("QuickAdd", "library"), ("Mermaid", "library")],
     [("QuickAdd", "Mermaid", "USES")],
     "how does the shower-thought capture stay under six seconds in the vault",
     "quickadd macro template mermaid frontmatter daily backlink capture speed"),
    # --- 49 ---
    ("Prefers Jupyter inside the Obsidian vault through the Execute Code plugin over a separate notebook folder because the daily lab notebook and the journal finally share the same backlink graph.", "preference", "cross", False,
     [("Jupyter", "tool"), ("Obsidian", "tool"), ("Execute Code", "library")],
     [("Execute Code", "Jupyter", "USES"), ("Execute Code", "Obsidian", "DEPLOYED_ON")],
     "which setup unites the lab notebook and the journal backlinks",
     "jupyter execute code plugin lab notebook journal backlink unify"),
    # --- 50 ---
    ("Satisfaction hit on 2026-03-31 when the quarterly review pulled 47 evergreen notes written since January out of the vault and the monthly mood chart actually correlated with the fiction-reading tag.", "milestone", "cross", False,
     [("Satisfaction", "emotion"), ("2026-03-31", "date"), ("evergreen", "pattern")],
     [],
     "what did the end-of-March quarterly review surface from the vault",
     "quarterly review evergreen note count mood correlation fiction reading tag"),
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
