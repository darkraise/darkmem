"""One-off emitter for shared-base batch-036 — cross domain.

Slice: writing / blogging / publishing meets software tooling. Writes 50 rows
to data/v2/shared/batch_036.tmp.jsonl with ids shared-01751..01800. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_036.tmp.jsonl"
ID_OFFSET = 1750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the personal blog from Jekyll to Astro once the MDX component story made the longform essays on distributed systems easier to maintain.", "decision", "cross", False,
     [("Jekyll", "framework"), ("Astro", "framework"), ("MDX", "language"), ("distributed systems", "field")],
     [("Astro", "Jekyll", "REPLACES")],
     "why did the personal site leave the old Ruby static generator",
     "static site generator migration component stories longform technical essays"),
    # --- 2 ---
    ("Prefers Ghost over Substack for the Tuesday newsletter because the self-hosted Ghost instance on the Hetzner VPS keeps the subscriber list off someone else's ledger.", "preference", "cross", False,
     [("Ghost", "service"), ("Substack", "service"), ("Hetzner", "organization")],
     [("Ghost", "Substack", "PREFERS"), ("Ghost", "Hetzner", "DEPLOYED_ON")],
     "which newsletter platform won for the weekly publication and why",
     "self hosted newsletter subscriber ownership VPS independent publishing"),
    # --- 3 ---
    ("The novel manuscript sits in a private Git repo with one chapter per Markdown file, and Pandoc converts the whole thing to ePub for my beta readers.", "architecture", "cross", False,
     [("Git", "tool"), ("Markdown", "language"), ("Pandoc", "tool"), ("ePub", "concept")],
     [("Pandoc", "Markdown", "USES")],
     "how does the novel draft reach the beta reader circle in a portable format",
     "manuscript version control chapter files converter electronic book reviewers"),
    # --- 4 ---
    ("Swapped Scrivener for iA Writer on the MacBook Air once the project outline grew past 80 scenes and Scrivener started dragging on save.", "decision", "cross", False,
     [("Scrivener", "tool"), ("iA Writer", "tool"), ("MacBook Air", "infrastructure")],
     [("iA Writer", "Scrivener", "REPLACES")],
     "which writing app took over on the laptop after the outline got big",
     "long form writing app swap performance large project save lag"),
    # --- 5 ---
    ("The Substack archive feeds a Hugo site via a tiny Python exporter so readers without a Substack account can still browse the climate-policy essays.", "architecture", "cross", False,
     [("Substack", "service"), ("Hugo", "framework"), ("Python", "language"), ("climate-policy", "field")],
     [("Hugo", "Substack", "DEPENDS_ON")],
     "how do the paywalled climate columns stay reachable on an open site",
     "newsletter archive mirror static generator export script open access"),
    # --- 6. noise ---
    ("One moment while I pull that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Hooked Giscus up to the Astro blog so comments live inside the same GitHub Discussions thread where the repo issues already sit.", "architecture", "cross", False,
     [("Giscus", "service"), ("Astro", "framework"), ("GitHub Discussions", "service")],
     [("Astro", "Giscus", "DEPENDS_ON"), ("Giscus", "GitHub Discussions", "USES")],
     "where do reader comments on the blog actually get stored",
     "comment widget static site discussions backend unified repository"),
    # --- 8 ---
    ("Plausible replaced Google Analytics on the writing site because the cookie banner was scaring off exactly the privacy-minded readers the newsletter targets.", "decision", "cross", False,
     [("Plausible", "service"), ("Google Analytics", "service")],
     [("Plausible", "Google Analytics", "REPLACES")],
     "why did the privacy-focused site drop the big analytics platform",
     "analytics swap privacy first cookie banner newsletter audience fit"),
    # --- 9 ---
    ("The dictation pipeline runs Whisper on the MacBook, pipes the transcript through LanguageTool, and drops the cleaned Markdown into Obsidian under the drafts folder.", "architecture", "cross", False,
     [("Whisper", "library"), ("MacBook", "infrastructure"), ("LanguageTool", "service"), ("Markdown", "language"), ("Obsidian", "tool")],
     [("Whisper", "MacBook", "DEPLOYED_ON"), ("Obsidian", "LanguageTool", "DEPENDS_ON")],
     "how do voice memos end up as polished draft files in the note vault",
     "speech to text local grammar check markdown draft pipeline voice writing"),
    # --- 10 ---
    ("Cold Turkey Blocker locks social media across the whole weekend so the current Patreon short-story arc actually ships on schedule.", "decision", "cross", False,
     [("Cold Turkey Blocker", "tool"), ("Patreon", "service")],
     [],
     "what keeps the weekend writing sessions actually productive for the subscription serial",
     "focus blocker distraction control serial fiction deadline weekend"),
    # --- 11 ---
    ("Eleventy plus Decap CMS gave my spouse a Netlify admin panel for posts while the whole site still builds from a plain Git repo.", "architecture", "cross", False,
     [("Eleventy", "framework"), ("Decap CMS", "service"), ("Netlify", "service"), ("Git", "tool")],
     [("Eleventy", "Decap CMS", "DEPENDS_ON"), ("Decap CMS", "Netlify", "DEPLOYED_ON")],
     "how does the non-technical co-author post to the blog without touching the repo",
     "static generator headless cms deploy host author friendly workflow"),
    # --- 12 ---
    ("The 2026-03-22 book launch on Kindle Direct Publishing failed preflight because the embedded TTF font in the ePub broke Amazon's validator.", "problem", "cross", False,
     [("2026-03-22", "date"), ("Kindle Direct Publishing", "service"), ("TTF", "concept"), ("ePub", "concept"), ("Amazon", "organization")],
     [],
     "what blocked the self-publishing launch at the end of March",
     "KDP upload failure font embedding validator rejection launch delay"),
    # --- 13 ---
    ("The Zola theme on the poetry site got swapped for a hand-rolled one after the author notes started needing Katex math for the concrete-poetry pieces.", "decision", "cross", False,
     [("Zola", "framework"), ("Katex", "library"), ("concrete-poetry", "field")],
     [("Zola", "Katex", "USES")],
     "why did the poetry blog abandon its off-the-shelf theme",
     "theme rewrite math rendering experimental layout static generator"),
    # --- 14 ---
    ("BookFunnel handles the ARC delivery for the next thriller so my Mailchimp list never sees the raw ePub files directly.", "architecture", "cross", False,
     [("BookFunnel", "service"), ("Mailchimp", "service"), ("ePub", "concept")],
     [("BookFunnel", "Mailchimp", "COMMUNICATES_WITH")],
     "how do advance review copies actually reach the thriller launch team",
     "ARC delivery service email list decoupling DRM-light distribution"),
    # --- 15 ---
    ("Prefers Hemingway Editor for the final polish pass over LanguageTool because the paragraph readability flags catch my worst subordinate-clause habits.", "preference", "cross", False,
     [("Hemingway Editor", "tool"), ("LanguageTool", "service")],
     [("Hemingway Editor", "LanguageTool", "PREFERS")],
     "which editor wins the final pass on essay drafts",
     "readability editor grammar tool comparison prose polish late stage"),
    # --- 16 ---
    ("Self-hosted WordPress on the DigitalOcean droplet still powers the food blog because no static generator has matched the ACF custom fields for recipe cards.", "decision", "cross", False,
     [("WordPress", "service"), ("DigitalOcean", "service"), ("ACF", "library"), ("recipe cards", "pattern")],
     [("WordPress", "DigitalOcean", "DEPLOYED_ON"), ("WordPress", "ACF", "USES")],
     "why does the cooking blog stay on the classic dynamic CMS stack",
     "wordpress droplet advanced custom fields recipe schema dynamic content"),
    # --- 17 ---
    ("Moved the domain registrar from GoDaddy to Porkbun on 2026-01-18 because the whois privacy was free by default and the DNS API was scriptable.", "milestone", "cross", False,
     [("GoDaddy", "service"), ("Porkbun", "service"), ("2026-01-18", "date"), ("DNS", "service")],
     [("Porkbun", "GoDaddy", "REPLACES")],
     "when did the writing site's domain actually move registrars and why",
     "registrar migration privacy defaults scriptable DNS API date"),
    # --- 18 ---
    ("The FocusWriter full-screen mode plus a Yeti microphone turned the spare room into a surprisingly productive podcast-script studio.", "fact", "cross", False,
     [("FocusWriter", "tool"), ("Yeti microphone", "infrastructure"), ("podcast-script", "pattern")],
     [],
     "what made the spare-room setup work for podcast script drafting",
     "distraction free writer condenser mic home studio script production"),
    # --- 19 ---
    ("A GitHub Action builds the Beehiiv newsletter digest every Thursday by pulling the week's blog posts through the RSS feed and formatting them as MJML.", "architecture", "cross", False,
     [("GitHub Action", "service"), ("Beehiiv", "service"), ("RSS", "concept"), ("MJML", "language")],
     [("GitHub Action", "Beehiiv", "COMMUNICATES_WITH")],
     "how does the weekly subscriber digest assemble itself from the blog",
     "CI workflow newsletter automation feed consumption email markup template"),
    # --- 20 ---
    ("Frustration spiked when the TinaCMS upgrade silently dropped draft entries for the interview series before the Monday publish slot.", "problem", "cross", False,
     [("Frustration", "emotion"), ("TinaCMS", "service"), ("interview series", "pattern")],
     [],
     "what went wrong with the headless CMS right before a scheduled interview post",
     "CMS upgrade regression draft loss publishing slot panic"),
    # --- 21 ---
    ("On 2026-02-09 the Patreon tier restructure tied the monthly novella drop to the 10-dollar patrons and moved world-building notes to the 5-dollar tier.", "milestone", "cross", False,
     [("2026-02-09", "date"), ("Patreon", "service"), ("novella", "pattern"), ("world-building", "pattern")],
     [],
     "when did the subscription tiers get re-shaped around the novella cadence",
     "membership restructure tier mapping serial fiction cadence bonus content"),
    # --- 22 ---
    ("Simple Analytics replaced Plausible on the author site because the GDPR-friendly referrer breakdown was exactly what the literary agent kept asking about.", "decision", "cross", False,
     [("Simple Analytics", "service"), ("Plausible", "service"), ("GDPR", "pattern"), ("literary agent", "person")],
     [("Simple Analytics", "Plausible", "REPLACES")],
     "why did the author's site swap one privacy analytics tool for another",
     "analytics swap privacy compliance referrer report literary agent question"),
    # --- 23 ---
    ("The shared novella project with Malia runs on a HackMD space so we can co-edit Markdown in real time without setting up VS Code Live Share.", "architecture", "cross", False,
     [("Malia", "person"), ("HackMD", "service"), ("Markdown", "language"), ("VS Code Live Share", "service")],
     [("HackMD", "VS Code Live Share", "PREFERS")],
     "how do two co-authors edit the novella at the same time across different setups",
     "collaborative markdown editor realtime coauthoring lightweight tooling"),
    # --- 24 ---
    ("Cusdis beat Disqus for the minimalist tech blog because the privacy promise in the author notes would have looked silly with 40 tracking scripts below the fold.", "decision", "cross", False,
     [("Cusdis", "service"), ("Disqus", "service"), ("tech blog", "pattern")],
     [("Cusdis", "Disqus", "REPLACES")],
     "which comment widget fit the privacy stance of the tech blog",
     "minimal comments tracker-free comment engine value alignment blog"),
    # --- 25 ---
    ("Turned on the accountability Notion template with Cron webhooks so missed writing sessions auto-post an apology to the small Discord server.", "architecture", "cross", False,
     [("Notion", "tool"), ("Cron", "service"), ("Discord", "service")],
     [("Cron", "Notion", "DEPENDS_ON"), ("Cron", "Discord", "COMMUNICATES_WITH")],
     "how does the writing accountability streak announce itself when I slip",
     "habit tracker template scheduled webhook public accountability community"),
    # --- 26 ---
    ("The Freedom app schedule blocks Twitter on weekday mornings because the book-two revisions were losing two hours a day to the feed.", "decision", "cross", False,
     [("Freedom", "tool"), ("Twitter", "service"), ("book-two", "pattern")],
     [("Freedom", "Twitter", "USES")],
     "what rule keeps the morning revision time intact for the sequel work",
     "focus scheduler social media block revision time recovery sequel"),
    # --- 27 ---
    ("Ulysses stays on the iPad Pro for travel drafting, while Scrivener handles the desktop Windows sessions because the project format copies fine through iCloud.", "architecture", "cross", False,
     [("Ulysses", "tool"), ("iPad Pro", "infrastructure"), ("Scrivener", "tool"), ("Windows", "infrastructure"), ("iCloud", "service")],
     [("Ulysses", "iPad Pro", "DEPLOYED_ON"), ("Scrivener", "Windows", "DEPLOYED_ON")],
     "how does the two-device writing setup stay coherent across platforms",
     "tablet drafting desktop editing cross platform cloud sync novel project"),
    # --- 28 ---
    ("Hooked Aeon Timeline to the current trilogy's Scrivener project so the hundred-year family backstory finally stopped drifting between chapters.", "architecture", "cross", False,
     [("Aeon Timeline", "tool"), ("trilogy", "pattern"), ("Scrivener", "tool")],
     [("Aeon Timeline", "Scrivener", "DEPENDS_ON")],
     "how did the multi-generation family backstory stop contradicting itself",
     "timeline tool long fiction continuity Scrivener integration saga"),
    # --- 29 ---
    ("Decided the 2026-04-05 indie novella launch would ship through Draft2Digital instead of KDP Select because the Kobo and Apple Books reach mattered more than the KU royalties.", "decision", "cross", False,
     [("2026-04-05", "date"), ("Draft2Digital", "service"), ("KDP Select", "service"), ("Kobo", "service"), ("Apple Books", "service")],
     [("Draft2Digital", "KDP Select", "REPLACES")],
     "which distribution path was chosen for the early April indie launch",
     "wide distribution versus exclusive subscription royalty tradeoff launch"),
    # --- 30 ---
    ("Beta reader feedback now lives in Google Docs suggestion mode because the PDF annotations from the last round were impossible to reconcile across twelve readers.", "decision", "cross", False,
     [("Google Docs", "service"), ("PDF", "concept")],
     [("Google Docs", "PDF", "REPLACES")],
     "why did the beta reader workflow drop the PDF round-trip",
     "beta readers feedback channel change suggestion mode reconciliation twelve"),
    # --- 31 ---
    ("Joy bubbled up seeing the Plausible graph for the essay on Kafka's Castle hit 50k readers after HN front-paged the Astro-built post on 2026-03-11.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Plausible", "service"), ("Kafka's Castle", "publication"), ("HN", "service"), ("Astro", "framework"), ("2026-03-11", "date")],
     [],
     "when did the Kafka essay actually break through and how was it tracked",
     "analytics spike hacker news front page essay virality emotion milestone"),
    # --- 32 ---
    ("Prefers writing first drafts in Drafts app on the iPhone over FocusWriter on the desktop because the voice-to-text path through Siri is still the fastest idea capture I own.", "preference", "cross", False,
     [("Drafts", "tool"), ("iPhone", "infrastructure"), ("FocusWriter", "tool"), ("Siri", "service")],
     [("Drafts", "FocusWriter", "PREFERS"), ("Drafts", "Siri", "USES")],
     "which tool captures the earliest idea for a piece and why",
     "idea capture phone first draft voice input writing workflow"),
    # --- 33 ---
    ("My reader Sofia in Buenos Aires flagged the accessibility issue where the custom Astro theme never announced the footnote dialog to VoiceOver on iOS.", "problem", "cross", False,
     [("Sofia", "person"), ("Buenos Aires", "place"), ("Astro", "framework"), ("VoiceOver", "service"), ("iOS", "infrastructure")],
     [("VoiceOver", "iOS", "DEPLOYED_ON")],
     "what accessibility bug did an overseas reader catch in the footnote component",
     "screen reader footnote dialog a11y defect static theme reader report"),
    # --- 34 ---
    ("The 2026-04-12 serial-fiction milestone was the hundredth chapter of the webserial shipping through Royal Road while the mirror on the personal Ghost site stayed current.", "milestone", "cross", False,
     [("2026-04-12", "date"), ("Royal Road", "service"), ("Ghost", "service")],
     [],
     "when did the webserial cross chapter one hundred and where did it publish",
     "serial fiction chapter milestone reader platform personal mirror parity"),
    # --- 35 ---
    ("Confusion about royalty reports went away once the Amazon KDP monthly CSV got loaded into a DuckDB file and queried with a tiny Quarto notebook.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Amazon KDP", "service"), ("CSV", "concept"), ("DuckDB", "database"), ("Quarto", "tool")],
     [("Quarto", "DuckDB", "USES")],
     "how did the monthly royalty statements stop being a mystery",
     "royalty CSV local analytics notebook self publishing finances clarity"),
    # --- 36 ---
    ("Obsidian Publish replaced a custom Docusaurus build for the world-building wiki because the internal links finally stopped breaking on every rename.", "decision", "cross", False,
     [("Obsidian Publish", "service"), ("Docusaurus", "framework"), ("world-building", "pattern")],
     [("Obsidian Publish", "Docusaurus", "REPLACES")],
     "which site generator finally handled the fantasy wiki's rename churn",
     "world building wiki link integrity static site rename resilience"),
    # --- 37 ---
    ("Wired up ConvertKit to a Zapier path that auto-sends a LanguageTool-checked welcome letter to every new essay subscriber.", "architecture", "cross", False,
     [("ConvertKit", "service"), ("Zapier", "service"), ("LanguageTool", "service")],
     [("Zapier", "ConvertKit", "COMMUNICATES_WITH"), ("Zapier", "LanguageTool", "USES")],
     "how does the essay newsletter greet new subscribers with edited prose",
     "newsletter automation subscriber welcome grammar checked orchestration"),
    # --- 38 ---
    ("The Hugo site's deploy moved from Netlify to Cloudflare Pages on 2026-02-28 after the build-minute ceiling kept tripping on the weekly photo essays.", "milestone", "cross", False,
     [("Hugo", "framework"), ("Netlify", "service"), ("Cloudflare Pages", "service"), ("2026-02-28", "date")],
     [("Cloudflare Pages", "Netlify", "REPLACES")],
     "when did the photo essay site change hosts and why",
     "static site host migration build minutes cap photography content weekly"),
    # --- 39 ---
    ("Editor Priya in Mumbai prefers receiving the romance manuscript as a Docx with track changes because the Scrivener compile notes never survived the round trip.", "preference", "cross", False,
     [("Priya", "person"), ("Mumbai", "place"), ("Docx", "concept"), ("Scrivener", "tool")],
     [("Docx", "Scrivener", "PREFERS")],
     "which file format survives the editor round trip intact",
     "editor handoff format track changes compile note loss manuscript"),
    # --- 40 ---
    ("The Calibre library plus a small Python script keeps the ARC metadata consistent across three distribution uploads every launch week.", "architecture", "cross", False,
     [("Calibre", "service"), ("Python", "language"), ("ARC", "pattern")],
     [("Python", "Calibre", "USES")],
     "how does launch-week metadata stay identical across the distribution uploads",
     "ebook library metadata normalization distribution upload consistency script"),
    # --- 41 ---
    ("Sourcegraph-style code snippets on the engineering blog run through Shiki at build time so the Monokai theme matches the author headshot palette.", "architecture", "cross", False,
     [("Shiki", "library"), ("Monokai", "concept")],
     [("Shiki", "Monokai", "IMPLEMENTS")],
     "how do the blog's code samples get their themed syntax highlighting",
     "syntax highlighter build time theme engineering blog aesthetics cohesion"),
    # --- 42 ---
    ("Patreon tiers now map to GitHub Sponsors tiers via a small Go webhook because the open-source CLI readers and the fiction readers mostly don't overlap.", "architecture", "cross", False,
     [("Patreon", "service"), ("GitHub Sponsors", "service"), ("Go", "language"), ("CLI", "pattern")],
     [("Go", "Patreon", "USES"), ("Go", "GitHub Sponsors", "COMMUNICATES_WITH")],
     "how do the two sponsor platforms stay consistent across audiences",
     "sponsor tier sync webhook dual audience CLI readers fiction readers"),
    # --- 43 ---
    ("Outlining the epic-fantasy trilogy moved from Plottr to a plain Markdown board in Obsidian because exporting beats to the drafting folder was always manual.", "decision", "cross", False,
     [("Plottr", "tool"), ("Markdown", "language"), ("Obsidian", "tool"), ("epic-fantasy", "field")],
     [("Obsidian", "Plottr", "REPLACES")],
     "why did the trilogy outlining leave the dedicated beat-sheet tool",
     "plot beats outlining tool swap drafting integration markdown board"),
    # --- 44 ---
    ("Regret set in when the 2026-03-02 newsletter send through Mailchimp silently skipped the Gmail Promotions-safe preview and landed 40% of issues in spam.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-03-02", "date"), ("Mailchimp", "service"), ("Gmail", "service")],
     [],
     "what deliverability disaster hit the early March newsletter send",
     "newsletter spam folder preview skip email deliverability regret"),
    # --- 45 ---
    ("The R Markdown pipeline that turns the monthly reading diary into a PDF zine gets emailed to my mother-in-law Haruko every first Sunday.", "architecture", "cross", False,
     [("R Markdown", "framework"), ("PDF", "concept"), ("zine", "pattern"), ("Haruko", "person")],
     [("R Markdown", "PDF", "USES")],
     "how does the monthly reading zine get to the family reader",
     "reproducible zine family mailing list PDF monthly cadence reading log"),
    # --- 46 ---
    ("Grammarly stayed on the corporate-comms writing account but got pulled off the fiction laptop because the tone suggestions were homogenising the prose voice.", "decision", "cross", False,
     [("Grammarly", "service"), ("corporate-comms", "field"), ("fiction", "field")],
     [],
     "why does the grammar assistant only run on one of the writing accounts",
     "grammar assistant scope split voice preservation fiction vs corporate"),
    # --- 47 ---
    ("Backed the whole novel repo to a Backblaze B2 bucket nightly via Restic because losing Scrivener project files to a corrupted SSD in 2024 still stings.", "architecture", "cross", False,
     [("Backblaze B2", "service"), ("Restic", "tool"), ("Scrivener", "tool"), ("SSD", "infrastructure")],
     [("Restic", "Backblaze B2", "DEPENDS_ON")],
     "how does the novel project survive another storage disaster",
     "offsite backup encrypted snapshot writing files post incident recovery"),
    # --- 48 ---
    ("The poetry chapbook launch on 2026-04-02 shipped as a Nix-built Pandoc pipeline producing print-ready PDF for Mixam and a reflowable ePub for Gumroad.", "milestone", "cross", False,
     [("2026-04-02", "date"), ("Nix", "tool"), ("Pandoc", "tool"), ("PDF", "concept"), ("Mixam", "service"), ("ePub", "concept"), ("Gumroad", "service")],
     [("Nix", "Pandoc", "USES")],
     "when did the chapbook launch and how did it reach both print and digital",
     "chapbook launch reproducible build print ready digital store poetry"),
    # --- 49 ---
    ("Prefers Typora as the plain-prose editor over Obsidian when the piece is just a standalone op-ed without any cross-links into the personal knowledge base.", "preference", "cross", False,
     [("Typora", "tool"), ("Obsidian", "tool"), ("op-ed", "pattern")],
     [("Typora", "Obsidian", "PREFERS")],
     "which editor handles standalone op-eds better than the vault",
     "markdown editor choice standalone essay no backlinks prose focus"),
    # --- 50 ---
    ("Excitement ran high when the 2026-04-10 Substack note about the upcoming hardcover tipped Kaito in Osaka into pre-ordering a second copy for his reading circle.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("2026-04-10", "date"), ("Substack", "service"), ("Kaito", "person"), ("Osaka", "place"), ("hardcover", "concept")],
     [],
     "when did the hardcover announcement land and who was the first reader response",
     "announcement note preorder reader community signal hardcover launch"),
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
