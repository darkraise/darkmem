"""One-off emitter for shared-base batch-109 — cross domain.

Slice: reading as personal hobby meeting software (e-readers, library-borrow
apps, highlight pipelines, read-later tools, book trackers, audiobook platforms,
DRM/calibre, book-club tooling). Writes 50 rows to data/v2/shared/batch_109.tmp.jsonl
with ids shared-05401..05450. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_109.tmp.jsonl"
ID_OFFSET = 5400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Readwise Reader replaced Pocket as the read-later inbox on 2026-02-11 once Mozilla's maintenance-mode announcement made the Pocket API feel like a dead end for long-form articles.", "decision", "cross", False,
     [("Readwise Reader", "service"), ("Pocket", "service"), ("2026-02-11", "date"), ("Mozilla", "organization")],
     [("Readwise Reader", "Pocket", "REPLACES")],
     "when did the read-later inbox migrate off Pocket and what triggered it",
     "read later app migration maintenance mode long form article inbox"),
    # --- 2 ---
    ("Swapped the Kindle Paperwhite for a Kobo Libra Colour after Amazon's 2026-02-26 policy killed the download-and-transfer option that the calibre workflow depended on.", "decision", "cross", False,
     [("Kindle Paperwhite", "infrastructure"), ("Kobo Libra Colour", "infrastructure"), ("Amazon", "organization"), ("2026-02-26", "date"), ("calibre", "tool")],
     [("Kobo Libra Colour", "Kindle Paperwhite", "REPLACES")],
     "why did the primary e-reader change this spring",
     "e-reader swap download transfer policy sideload library workflow"),
    # --- 3 ---
    ("Libby replaced the old OverDrive app on the iPhone once the Toronto Public Library pushed the sunset notice and the hold history refused to migrate automatically.", "decision", "cross", False,
     [("Libby", "service"), ("OverDrive", "service"), ("iPhone", "infrastructure"), ("Toronto Public Library", "organization")],
     [("Libby", "OverDrive", "REPLACES")],
     "how did the library borrowing app move off OverDrive for Toronto holds",
     "library borrow app sunset migration hold history branch card"),
    # --- 4 ---
    ("The reMarkable 2 replaced a stack of paper margin notes for the 2026-03-15 Dostoevsky reread because the handwriting export to Readwise landed the scribbles alongside the Kindle highlights.", "milestone", "cross", False,
     [("reMarkable 2", "infrastructure"), ("2026-03-15", "date"), ("Dostoevsky", "person"), ("Readwise", "service"), ("Kindle", "infrastructure")],
     [("reMarkable 2", "Readwise", "COMMUNICATES_WITH")],
     "when did the margin-note workflow go fully digital for classic novels",
     "handwriting capture margin note export highlight pipeline classics"),
    # --- 5 ---
    ("Prefers Storygraph over Goodreads for year-end stats because the mood and pace breakdown actually surfaces why the 2025 reading slump happened in the thriller stretch.", "preference", "cross", False,
     [("Storygraph", "service"), ("Goodreads", "service")],
     [("Storygraph", "Goodreads", "PREFERS")],
     "which book tracker won for end-of-year analytics and why",
     "reading tracker stats mood pace breakdown slump analysis thriller"),
    # --- 6. noise ---
    ("Hold on, I need to grab a glass of water.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Matter replaced Instapaper on the daily commute reader because Matter's text-to-speech voices on iOS made the New Yorker longreads actually listenable on the subway.", "decision", "cross", False,
     [("Matter", "service"), ("Instapaper", "service"), ("iOS", "infrastructure"), ("New Yorker", "publication")],
     [("Matter", "Instapaper", "REPLACES")],
     "which read-later app handles the subway commute now and why",
     "read later text to speech voice quality commute longreads subway"),
    # --- 8 ---
    ("Obsidian's Readwise Official plugin pulls every new highlight into a per-book note at 6am, and the Dataview query rolls the month's new quotes into the daily journal without any copy-paste.", "architecture", "cross", False,
     [("Obsidian", "tool"), ("Readwise Official", "tool"), ("Dataview", "tool")],
     [("Obsidian", "Readwise Official", "USES"), ("Dataview", "Readwise Official", "USES")],
     "how do book highlights land in the Obsidian vault every morning",
     "highlight sync plugin schedule dataview rollup per book note"),
    # --- 9 ---
    ("Calibre 7.18 on the ThinkPad handles the DRM-removed EPUB pipeline, feeding the Kobo Libra Colour over USB because the Kobo cloud hates sideloads above 60 megabytes.", "architecture", "cross", False,
     [("Calibre 7.18", "tool"), ("ThinkPad", "infrastructure"), ("EPUB", "concept"), ("Kobo Libra Colour", "infrastructure"), ("USB", "protocol")],
     [("Calibre 7.18", "Kobo Libra Colour", "USES")],
     "how do the sideloaded EPUBs reach the e-reader without the cloud choking",
     "calibre sideload USB transfer EPUB size limit cloud bypass"),
    # --- 10 ---
    ("Frustration spiked when Audible yanked three credits after the 2026-01-19 account review and Libro.fm took over for every future audiobook purchase.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Audible", "service"), ("2026-01-19", "date"), ("Libro.fm", "service")],
     [("Libro.fm", "Audible", "REPLACES")],
     "what triggered the audiobook platform switch in January",
     "audiobook credit claw back account review indie shop switch"),
    # --- 11 ---
    ("The Boox Palma 2 replaced the iPhone's Kindle app for bedtime reading because the e-ink screen kept the melatonin from cratering the sleep-cycle data on the Oura ring.", "decision", "cross", False,
     [("Boox Palma 2", "infrastructure"), ("iPhone", "infrastructure"), ("Kindle", "service"), ("Oura", "infrastructure")],
     [("Boox Palma 2", "iPhone", "REPLACES")],
     "why did bedtime reading move off the phone to a pocket e-ink device",
     "pocket e-ink reader bedtime blue light sleep tracking data"),
    # --- 12 ---
    ("Omnivore's shutdown on 2026-02-07 forced a panicked export to Readwise Reader because the 1,400 saved longreads would have vanished with the managed instance.", "milestone", "cross", False,
     [("Omnivore", "service"), ("2026-02-07", "date"), ("Readwise Reader", "service")],
     [("Readwise Reader", "Omnivore", "REPLACES")],
     "when did the read-later archive have to be rescued from the shuttered host",
     "service shutdown export rescue read later archive managed instance"),
    # --- 13 ---
    ("Prefers Anna's Archive over Library Genesis for academic PDFs because the SciDb mirror actually serves the 2020-and-later papers that LibGen's scimag torrents are missing.", "preference", "cross", False,
     [("Anna's Archive", "service"), ("Library Genesis", "service"), ("SciDb", "service"), ("PDF", "concept")],
     [("Anna's Archive", "Library Genesis", "PREFERS")],
     "which shadow library actually has the recent academic papers",
     "shadow library academic PDF mirror coverage gap recent papers"),
    # --- 14 ---
    ("Raindrop.io replaced the mess of Chrome bookmarks for recipe-adjacent reading after the 2026-03-03 export from Pinboard finally landed cleanly in the Raindrop nested collections.", "decision", "cross", False,
     [("Raindrop.io", "service"), ("Chrome", "service"), ("2026-03-03", "date"), ("Pinboard", "service")],
     [("Raindrop.io", "Pinboard", "REPLACES"), ("Raindrop.io", "Chrome", "REPLACES")],
     "where do the saved recipe-adjacent articles live after the Pinboard export",
     "bookmark manager migration nested collections recipe reading archive"),
    # --- 15 ---
    ("LibriVox covered the 2026-01-04 Moby Dick listen because the public-domain narration on BookFusion cost nothing and the Audible version wanted two credits for the same unabridged text.", "decision", "cross", False,
     [("LibriVox", "service"), ("2026-01-04", "date"), ("Moby Dick", "concept"), ("BookFusion", "service"), ("Audible", "service")],
     [("LibriVox", "Audible", "PREFERS")],
     "how did the Moby Dick audiobook end up costing nothing",
     "public domain audiobook volunteer narration unabridged credit free"),
    # --- 16 ---
    ("Readwise's daily review email pushes five highlights every morning at 7am, and the spaced-repetition tag resurrects the 2019 Slaughterhouse-Five margin notes exactly when they're needed.", "architecture", "cross", False,
     [("Readwise", "service"), ("Slaughterhouse-Five", "concept")],
     [],
     "how do old book highlights resurface on a recurring schedule",
     "spaced repetition highlight resurface daily review email schedule"),
    # --- 17 ---
    ("Joy hit when the 2026-03-09 book-club Discord call on Piranesi ran Zoom-in-Discord-embed cleanly across five people and the Storygraph buddy-read badge popped for all of us.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-03-09", "date"), ("Discord", "service"), ("Piranesi", "concept"), ("Zoom", "service"), ("Storygraph", "service")],
     [("Discord", "Zoom", "USES")],
     "when did the Piranesi book-club call and buddy-read both click into place",
     "book club discord zoom embed buddy read badge group novel"),
    # --- 18 ---
    ("The Kobo sync-to-calibre-companion setup on a Raspberry Pi 5 now handles nightly backups of 2,300 EPUBs so nothing is lost if the Kobo bricks again like it did in 2024.", "architecture", "cross", False,
     [("Kobo", "infrastructure"), ("calibre-companion", "tool"), ("Raspberry Pi 5", "infrastructure"), ("EPUB", "concept")],
     [("calibre-companion", "Raspberry Pi 5", "DEPLOYED_ON"), ("calibre-companion", "Kobo", "COMMUNICATES_WITH")],
     "how does the e-reader library get backed up every night",
     "nightly backup ebook library pi self host plugin sidecar"),
    # --- 19 ---
    ("Goodreads' 2026-02-20 reading-challenge reset bug double-counted every finished book, so the year-to-date number on the feed cratered once the manual recount landed.", "problem", "cross", False,
     [("Goodreads", "service"), ("2026-02-20", "date")],
     [],
     "what went wrong with the Goodreads yearly reading challenge counter",
     "reading challenge counter double count bug annual goal feed"),
    # --- 20 ---
    ("Prefers Hoopla for graphic novels over Libby because the Hoopla flex-borrow model doesn't hold the Saga omnibus volumes hostage behind a three-month wait list.", "preference", "cross", False,
     [("Hoopla", "service"), ("Libby", "service"), ("Saga", "concept")],
     [("Hoopla", "Libby", "PREFERS")],
     "which library app wins for graphic novels and why",
     "graphic novel library app comparison wait list flex borrow model"),
    # --- 21 ---
    ("The Obsidian Book Search plugin autopopulates the ISBN, cover, and publication date for every finished read, so the reading log for 2026 has never had a manual metadata entry.", "architecture", "cross", False,
     [("Obsidian", "tool"), ("Book Search", "tool"), ("ISBN", "concept")],
     [("Obsidian", "Book Search", "USES")],
     "how does the reading log avoid manual ISBN and cover entry each book",
     "book metadata autopopulate plugin reading log cover ISBN lookup"),
    # --- 22 ---
    ("Moved the annotations pipeline from Notion to Logseq on 2026-03-01 because Logseq's block-level references let the Sanderson series recaps link every plot beat back to the source highlight.", "milestone", "cross", False,
     [("Notion", "tool"), ("Logseq", "tool"), ("2026-03-01", "date"), ("Sanderson", "person")],
     [("Logseq", "Notion", "REPLACES")],
     "when did the book annotation system leave Notion for Logseq",
     "annotation pipeline migration block reference series recap linking"),
    # --- 23 ---
    ("Anxiety spiked when Amazon's 2026-02-26 download lockdown made the 11-year Kindle library feel fragile, and the DeDRM 10.0.9 plugin for calibre became non-negotiable for future purchases.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("Amazon", "organization"), ("2026-02-26", "date"), ("Kindle", "service"), ("DeDRM 10.0.9", "tool"), ("calibre", "tool")],
     [("DeDRM 10.0.9", "calibre", "DEPLOYED_ON")],
     "what pushed the Kindle library toward DRM-removal tooling in February",
     "download lockdown library fragility DRM removal plugin future proof"),
    # --- 24 ---
    ("The 2026-04-02 book-club kickoff for Gravity's Rainbow runs weekly on Zoom and the shared progress tracker lives in a Notion database that Rafael set up with a status-property rollup.", "milestone", "cross", False,
     [("2026-04-02", "date"), ("Gravity's Rainbow", "concept"), ("Zoom", "service"), ("Notion", "tool"), ("Rafael", "person")],
     [("Notion", "Zoom", "COMMUNICATES_WITH")],
     "when did the Gravity's Rainbow group read start and where does progress live",
     "book club kickoff weekly zoom shared progress tracker rollup"),
    # --- 25 ---
    ("Reader from Readwise replaced Instapaper, Matter, and Pocket simultaneously in early 2026 because running three different highlight pipelines into Readwise was ridiculous once Reader shipped native PDF support.", "decision", "cross", False,
     [("Reader", "service"), ("Readwise", "service"), ("Instapaper", "service"), ("Matter", "service"), ("Pocket", "service"), ("PDF", "concept")],
     [("Reader", "Instapaper", "REPLACES"), ("Reader", "Matter", "REPLACES"), ("Reader", "Pocket", "REPLACES")],
     "which tool consolidated three separate read-later apps at once",
     "consolidation read later highlight pipeline native PDF support"),
    # --- 26 ---
    ("Prefers Libro.fm over Chirp for audiobook deals because the local bookstore affiliation funnels royalties back to the Brookline shop that hosts the monthly in-person meetup.", "preference", "cross", False,
     [("Libro.fm", "service"), ("Chirp", "service"), ("Brookline", "place")],
     [("Libro.fm", "Chirp", "PREFERS")],
     "which audiobook store wins on deals and what drives the choice",
     "audiobook store affiliation indie bookstore royalty local meetup"),
    # --- 27 ---
    ("The Apprehension about sideloading cracked EPUBs onto the work-issued iPad finally passed once the Boox Palma 2 became the dedicated sideload target and the iPad stayed clean.", "decision", "cross", False,
     [("Apprehension", "emotion"), ("EPUB", "concept"), ("iPad", "infrastructure"), ("Boox Palma 2", "infrastructure")],
     [("Boox Palma 2", "iPad", "REPLACES")],
     "how did the sideload-on-work-device worry get resolved",
     "sideload device separation work device compliance dedicated reader"),
    # --- 28 ---
    ("The Storygraph Plus annual at 35 dollars is worth it for the nemesis-recommendation engine because the anti-rec for genre fatigue actually surfaced Tomasz Różycki after a year of thrillers.", "decision", "cross", False,
     [("Storygraph Plus", "service"), ("Tomasz Różycki", "person")],
     [],
     "why does the paid Storygraph tier earn its keep each year",
     "nemesis recommendation anti rec genre fatigue poetry discovery annual"),
    # --- 29 ---
    ("Readwise's Kindle sync broke on 2026-01-12 after the Kindle app v7.4 rewrote the My Clippings file schema, and the manual CSV export from calibre filled the gap for six days.", "problem", "cross", False,
     [("Readwise", "service"), ("Kindle", "service"), ("2026-01-12", "date"), ("calibre", "tool"), ("CSV", "concept")],
     [("calibre", "Readwise", "COMMUNICATES_WITH")],
     "what broke in the Kindle highlight sync in mid-January and how was it patched",
     "clippings schema change sync break manual export CSV workaround"),
    # --- 30 ---
    ("The Matter-to-Obsidian daily export runs at midnight UTC via a Cloudflare Worker cron because the official plugin only syncs on app open and the workflow needed deterministic timing.", "architecture", "cross", False,
     [("Matter", "service"), ("Obsidian", "tool"), ("Cloudflare Worker", "service"), ("UTC", "concept")],
     [("Matter", "Cloudflare Worker", "USES"), ("Cloudflare Worker", "Obsidian", "COMMUNICATES_WITH")],
     "how does Matter's nightly export reach Obsidian deterministically",
     "cron worker nightly sync deterministic timing highlight pipeline"),
    # --- 31 ---
    ("Pnin by Nabokov finally finished on 2026-04-09 after seven weeks of 15-minute Boox Palma 2 sessions during the morning train ride on the MBTA Red Line.", "milestone", "cross", False,
     [("Pnin", "concept"), ("Nabokov", "person"), ("2026-04-09", "date"), ("Boox Palma 2", "infrastructure"), ("MBTA", "organization")],
     [],
     "when did the slow-burn Nabokov reread actually wrap",
     "slow read pocket reader commute session completion anniversary"),
    # --- 32 ---
    ("Prefers the Kobo Elipsa 2E over the reMarkable 2 for textbook annotation because the Elipsa's direct EPUB support skips the PDF-conversion step that the reMarkable workflow forces.", "preference", "cross", False,
     [("Kobo Elipsa 2E", "infrastructure"), ("reMarkable 2", "infrastructure"), ("EPUB", "concept"), ("PDF", "concept")],
     [("Kobo Elipsa 2E", "reMarkable 2", "PREFERS")],
     "which large-format e-ink device wins for textbook annotation and why",
     "large e-ink textbook annotation EPUB native format comparison"),
    # --- 33 ---
    ("The Fairfax County Library system's Libby card covers 80% of the Kindle-library wishlist because the digital collection runs on OverDrive Advantage and has three copies of most new releases.", "fact", "cross", False,
     [("Fairfax County Library", "organization"), ("Libby", "service"), ("Kindle", "service"), ("OverDrive Advantage", "service")],
     [("Libby", "OverDrive Advantage", "USES")],
     "how much of the wishlist does the county library actually cover",
     "library consortium overdrive advantage digital collection holds wait"),
    # --- 34. noise ---
    ("Okay, give me a moment to pull that up.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Zotero 7.0.11 PDF reader handles academic highlights now, and the Zotero-to-Readwise bridge script pushes them into the same Readwise library as the Kindle quotes.", "architecture", "cross", False,
     [("Zotero 7.0.11", "tool"), ("PDF", "concept"), ("Readwise", "service"), ("Kindle", "service")],
     [("Zotero 7.0.11", "Readwise", "COMMUNICATES_WITH")],
     "how do academic PDF highlights land in the same place as the Kindle ones",
     "academic highlight bridge unified library pdf reader integration"),
    # --- 36 ---
    ("Anna's Archive's Fast Downloads membership at 30 dollars a year replaced the Z-Library Tor workflow after the 2026-01-28 seizure scare made the onion address unreliable.", "decision", "cross", False,
     [("Anna's Archive", "service"), ("Z-Library", "service"), ("Tor", "protocol"), ("2026-01-28", "date")],
     [("Anna's Archive", "Z-Library", "REPLACES")],
     "why did the shadow-library access switch away from the Tor workflow",
     "fast download membership tor seizure reliability access swap"),
    # --- 37 ---
    ("The Reader shortcut pack on iOS from Federico Viticci's MacStories post captures any Safari article into Reader with a single long-press, which cut the daily save friction to nothing.", "reference", "cross", False,
     [("Reader", "service"), ("iOS", "infrastructure"), ("Federico Viticci", "person"), ("MacStories", "publication"), ("Safari", "service")],
     [],
     "which MacStories post made saving articles on iPhone frictionless",
     "shortcut pack mobile save friction long press article capture"),
    # --- 38 ---
    ("Pride hit on 2026-04-11 when the 50-book annual goal cleared four months early and the Storygraph stats showed 22,000 pages at an average of 18 minutes per session.", "milestone", "cross", False,
     [("Pride", "emotion"), ("2026-04-11", "date"), ("Storygraph", "service")],
     [],
     "when did this year's reading goal get cleared and what did the stats show",
     "annual reading goal pace ahead schedule session length pages"),
    # --- 39 ---
    ("Moved the audiobook listening from Audible to Libro.fm's Libro Perks family plan on 2026-02-01 because Mei and I split credits and Audible wouldn't allow non-spouse household linking.", "decision", "cross", False,
     [("Audible", "service"), ("Libro.fm", "service"), ("Libro Perks", "service"), ("2026-02-01", "date"), ("Mei", "person")],
     [("Libro.fm", "Audible", "REPLACES")],
     "when did the shared audiobook credits leave Audible and why",
     "family plan household sharing credit split audiobook service swap"),
    # --- 40 ---
    ("The KOReader firmware on the Kobo Libra 2 replaced the stock Kobo reader because the per-book dictionary lookup actually works with the custom ODict files for the 2026 Italian-literature kick.", "decision", "cross", False,
     [("KOReader", "tool"), ("Kobo Libra 2", "infrastructure"), ("ODict", "concept"), ("Italian", "language")],
     [("KOReader", "Kobo Libra 2", "DEPLOYED_ON")],
     "why did the e-reader firmware get swapped for KOReader this year",
     "custom firmware dictionary lookup ODict language learning e-reader"),
    # --- 41 ---
    ("Prefers Bookwyrm over Goodreads for reviews because the federated timeline through the calckey.social instance keeps the recommendations clear of Amazon-owned algorithmic feeds.", "preference", "cross", False,
     [("Bookwyrm", "service"), ("Goodreads", "service"), ("calckey.social", "service"), ("Amazon", "organization")],
     [("Bookwyrm", "Goodreads", "PREFERS")],
     "which federated book tracker won over Goodreads for social reviews",
     "federated book review timeline fediverse recommendation algorithm"),
    # --- 42 ---
    ("The Calibre-Web server on the Unraid NAS at 192.168.1.42 streams the shared family library to every device so the nieces can grab the Rick Riordan backlog from their Kobo Clara BWs.", "architecture", "cross", False,
     [("Calibre-Web", "tool"), ("Unraid", "service"), ("192.168.1.42", "infrastructure"), ("Rick Riordan", "person"), ("Kobo Clara BW", "infrastructure")],
     [("Calibre-Web", "Unraid", "DEPLOYED_ON"), ("Kobo Clara BW", "Calibre-Web", "USES")],
     "how does the family share a central ebook library across devices",
     "shared library self host NAS streaming family nieces access"),
    # --- 43 ---
    ("The Bookly app on the iPhone replaced a paper reading-minutes tracker because the start-reading tap logs the session automatically and the streak counter syncs to the iCloud backup.", "decision", "cross", False,
     [("Bookly", "service"), ("iPhone", "infrastructure"), ("iCloud", "service")],
     [("Bookly", "iPhone", "DEPLOYED_ON"), ("Bookly", "iCloud", "USES")],
     "how did the daily reading-minutes log go digital",
     "reading minutes tracker session log streak sync automatic start"),
    # --- 44 ---
    ("Confusion hit when Libby's 2026-03-22 update broke the auto-return on Kindle-format loans and three holds expired mid-chapter on the Kindle Oasis before the fix shipped.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Libby", "service"), ("2026-03-22", "date"), ("Kindle", "service"), ("Kindle Oasis", "infrastructure")],
     [],
     "what broke in the Libby Kindle flow in late March",
     "auto return loan expiry mid chapter kindle format regression"),
    # --- 45 ---
    ("The Readwise Ghostreader summaries running on Claude replaced the hand-written chapter notes for non-fiction reads because the AI-generated TLDR catches the thesis reliably on the first pass.", "decision", "cross", False,
     [("Readwise Ghostreader", "service"), ("Claude", "service"), ("TLDR", "concept")],
     [("Readwise Ghostreader", "Claude", "USES")],
     "how do non-fiction chapter notes get generated now",
     "AI chapter summary thesis extraction ghostreader tldr non fiction"),
    # --- 46 ---
    ("Prefers the 6-inch Kindle Colorsoft Signature over the Kobo Libra Colour for comic-book consumption because the Amazon Kids profile on the household account lets the kids read Dog Man without the adult library leaking over.", "preference", "cross", False,
     [("Kindle Colorsoft Signature", "infrastructure"), ("Kobo Libra Colour", "infrastructure"), ("Amazon Kids", "service"), ("Dog Man", "concept")],
     [("Kindle Colorsoft Signature", "Kobo Libra Colour", "PREFERS")],
     "which color e-reader wins for shared kids-and-adults households and why",
     "color e-ink comic kids profile household account content isolation"),
    # --- 47 ---
    ("The 2026-03-28 Discord book-club for The Power Broker runs monthly with a 200-page pace, and the shared reading tracker lives in a Google Sheet that Priya maintains with conditional formatting for stragglers.", "architecture", "cross", False,
     [("2026-03-28", "date"), ("Discord", "service"), ("The Power Broker", "concept"), ("Google Sheet", "service"), ("Priya", "person")],
     [],
     "where does the Power Broker book-club track monthly progress",
     "monthly book club pace tracker shared spreadsheet conditional format"),
    # --- 48 ---
    ("Migrated the full Kindle 2013-to-2025 highlight archive out through the Readwise ExportBot on 2026-03-05 because relying on Amazon to keep the notebook.html format stable felt naive after the download lockdown.", "milestone", "cross", False,
     [("Kindle", "service"), ("Readwise", "service"), ("ExportBot", "service"), ("2026-03-05", "date"), ("Amazon", "organization"), ("notebook.html", "concept")],
     [("Readwise", "ExportBot", "USES")],
     "when did the full Kindle highlight history get exported and why",
     "highlight archive export bulk migration format stability vendor risk"),
    # --- 49 ---
    ("The Five Books interview with Tyler Cowen on 2026-02-18 drove the 2026 political-philosophy reading list, and every recommendation landed in the Storygraph to-read pile within an hour.", "reference", "cross", False,
     [("Five Books", "publication"), ("Tyler Cowen", "person"), ("2026-02-18", "date"), ("Storygraph", "service")],
     [],
     "which interview shaped the political-philosophy reading list this year",
     "curated interview reading list recommendations to read pile"),
    # --- 50 ---
    ("The IFTTT applet that pushes every finished Goodreads book into a Trakt-style Notion database finally broke on 2026-03-14 and a Make.com scenario replaced it with proper OAuth against the Hardcover API.", "decision", "cross", False,
     [("IFTTT", "service"), ("Goodreads", "service"), ("Notion", "tool"), ("2026-03-14", "date"), ("Make.com", "service"), ("OAuth", "protocol"), ("Hardcover", "service")],
     [("Make.com", "IFTTT", "REPLACES"), ("Make.com", "Hardcover", "USES")],
     "when did the finished-book automation swap backends and why",
     "automation swap oauth integration book tracker webhook scenario"),
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
