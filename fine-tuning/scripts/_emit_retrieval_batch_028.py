"""One-off emitter for retrieval top-up batch-028 - hard-negative kind, target shared rows at line offsets 2700..2799.

Writes 100 rows to data/v2/retrieval/batch_028.tmp.jsonl with ids ret-02701..02800.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_028.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 2700
SHARED_OFFSET = 2700
QUERY_KIND = "hard-negative"

# One (query, negative_line_offset) per target row, in target-row order.
# `query` is about the TARGET row; `negative_line_offset` points to a different shared row
# whose text is topically close but does not answer the query.
ENTRIES: list[tuple[str, int]] = [
    # 2700 Moved public docs from Sphinx to MkDocs-Material
    ("Why did we move the public docs pipeline from Sphinx to MkDocs-Material?", 2701),
    # 2701 Kept Sphinx for Python SDK reference site
    ("Why did we keep Sphinx over MkDocs-Material for the Python SDK reference site?", 2700),
    # 2702 Adopted MyST Markdown across Sphinx site
    ("What Markdown flavour did we adopt across the Sphinx site?", 2703),
    # 2703 Docusaurus 3 with MDX 3 support
    ("What did Docusaurus 3's MDX 3 support finally fix for our live React demos?", 2716),
    # 2704 Multi-repo docs moved to Antora
    ("Which tool now assembles multi-repo content branches into one versioned site nightly?", 2739),
    # 2705 Linting switched from write-good to Vale
    ("How much did switching to Vale with a vocabulary-driven style cut false positives?", 2713),
    # 2706 Added cspell with shared workspace dictionary
    ("What spell-check tool fails CI on typos in code samples?", 2705),
    # 2707 Link checking lychee in CI, htmlproofer nightly
    ("Why does htmlproofer still run the nightly full-site crawl instead of lychee?", 2732),
    # 2708 NOISE office plant by window flowered
    ("What offhand remark was made about the office plant by the window?", 2770),
    # 2709 Every docs PR gets RTD preview and Netlify Deploy Preview
    ("Why do reviewers click through hosted diffs instead of pulling docs branches?", 2718),
    # 2710 axe-core accessibility audit on rendered preview
    ("Which tool blocks docs merges on missing alt text and low-contrast tokens?", 2728),
    # 2711 ADRs under docs/adr/ using adr-tools, four sections
    ("Which four sections does every file under docs/adr/ start with?", 2750),
    # 2712 Killed free-form design docs, templated RFC process
    ("Why did we kill the free-form design-doc pile in favour of a templated RFC?", 2753),
    # 2713 Glossary in single glossary.md, Vale flags non-glossary terms
    ("How does Vale enforce glossary usage across the docs site?", 2705),
    # 2714 REST reference from OpenAPI via Redoc; dropped Slate
    ("Why did we drop Slate for the REST reference after two years?", 2715),
    # 2715 Evaluated Stoplight Elements alongside Redoc
    ("Why did we reject Stoplight Elements after evaluating it against Redoc?", 2714),
    # 2716 GraphQL reference via Docusaurus plugin, introspection at build
    ("How does our GraphQL reference detect schema drift at CI time?", 2703),
    # 2717 Changelog hooks into conventional-changelog, banner 14 days
    ("How long does the release banner stay on the docs landing page?", 2748),
    # 2718 Screenshots rebuild nightly via Playwright, pixel-diff bot
    ("How does the docs pipeline catch unexpected product screenshot shifts on PRs?", 2709),
    # 2719 Python docs doctest in CI, extract fenced blocks
    ("How do we test Python fenced code snippets in our docs?", 2738),
    # 2720 Runbooks fixed schema symptom/scope/diagnosis/mitigation/follow-up
    ("What five-section schema do our runbooks follow?", 2711),
    # 2721 Content inventory audit 2026-03-20 flagged 412 stale pages
    ("How many pages did the 2026-03-20 content inventory audit flag as stale?", 2732),
    # 2722 Doc debt dashboard tracks broken links, stale dates, gaps; Monday 09:00 report
    ("When does the weekly docs debt report hit the Slack channel?", 2721),
    # 2723 Deprecation banners MDX component via deprecated_on front matter
    ("How does a deprecated_on front matter date trigger a deprecation banner?", 2735),
    # 2724 Localisation moved from Crowdin to Weblate
    ("Why did we move localisation from Crowdin to self-hosted Weblate?", 2725),
    # 2725 Rejected GitLocalize during the eval
    ("Why did we reject GitLocalize during the localisation tool evaluation?", 2724),
    # 2726 Docs SEO cleanup: canonical URLs, sitemap, og:image via satori
    ("What tool generates our og:image assets during the docs SEO pipeline?", 2727),
    # 2727 Versioned docs symlinked /en/<version>/, nginx redirect /latest/
    ("How does our versioned docs layout avoid build duplication?", 2726),
    # 2728 Dark-mode tokens in tokens.json, WCAG AA contrast in CI
    ("Where do the dark-mode tokens for the docs theme live?", 2710),
    # 2729 Search moved from Algolia DocSearch to self-hosted typesense
    ("Why did we move docs search from Algolia DocSearch to typesense?", 2730),
    # 2730 Considered Meilisearch, rejected for opaque ranking
    ("Why did we reject Meilisearch as our docs search engine?", 2729),
    # 2731 Lunr static index fallback for offline tarballs
    ("Why do we still ship a lunr index inside the downloadable docs zip?", 2729),
    # 2732 Stale-docs detection via git log --diff-filter=M, 12 months
    ("How does our stale-docs detection open auto-issues against old pages?", 2721),
    # 2733 Adopted Google developer docs style with exceptions
    ("Which external style guide does our writing-style guide build on?", 2736),
    # 2734 Tutorials split by persona cut time-to-first-success 22 to 7 minutes
    ("How much did persona-split tutorials cut the time-to-first-success?", 2747),
    # 2735 Front matter owner, last_reviewed, applies_to_version joined with CI data
    ("Which three front matter keys does every docs page carry?", 2723),
    # 2736 Contributor guide in CONTRIBUTING.md, larger style in docs/style/
    ("Why did we split docs style rules out of CONTRIBUTING.md?", 2733),
    # 2737 Diagrams moved to Mermaid in MDX, SVG only for hand-drawn
    ("Why do we still keep SVG assets around instead of only using Mermaid?", 2764),
    # 2738 Node script extracts js fences, runs in vm2 sandbox
    ("How do we test JavaScript fenced code snippets in the tutorials?", 2719),
    # 2739 Docs publishing on Turborepo graph, only affected sites rebuild
    ("How does touching a single content file avoid rebuilding the whole docs tree?", 2704),
    # 2740 Dedicated docs branch protected separately, merge without eng CI
    ("Why do docs-only PRs merge without waiting on the engineering CI suite?", 2773),
    # 2741 /docs/feedback endpoint thumbs widget, weekly review
    ("Where does the docs thumbs-up/down feedback data feed into?", 2722),
    # 2742 PR template asks for Diataxis mode
    ("What does the docs PR template ask reviewers to identify up front?", 2736),
    # 2743 Canonical examples at examples/ in main monorepo, imported by docs
    ("Why do our docs examples live at examples/ in the main monorepo?", 2746),
    # 2744 Dropped PDF export after usage fell under 0.3%
    ("Why did we drop the PDF export path from the docs site?", 2731),
    # 2745 NOISE neighbour replaced garage door
    ("What offhand remark was made about the neighbour replacing the garage door?", 2708),
    # 2746 Rejected hand-authored examples markdown tree (drift)
    ("Why did we reject a hand-authored examples markdown tree for the SDK?", 2743),
    # 2747 IA improves on alphabetical API index, task-grouped
    ("How did we restructure the documentation information architecture?", 2734),
    # 2748 Reference edits require linked changelog entry
    ("What rule does the PR template enforce on reference page edits?", 2717),
    # 2749 Picked MADR over Nygard original ADR template
    ("Why did we pick MADR over Michael Nygard's original ADR template?", 2772),
    # 2750 ADRs under doc/adr at repo root, adr-tools CLI
    ("Where do ADRs live and what CLI creates a new numbered file?", 2711),
    # 2751 ADRs start proposed, flip to accepted after 48h silent window
    ("How long is the silent window before an ADR flips from proposed to accepted?", 2752),
    # 2752 New ADR overrides old, old goes to superseded with back-link
    ("What happens to the older ADR when a new one overrides it?", 2786),
    # 2753 RFC lifecycle five stages: idea, draft, comment, decision, retro
    ("What are the five named stages of our RFC lifecycle?", 2754),
    # 2754 RFC comment window two calendar weeks, compress to one with note
    ("How long does the default RFC comment window run before decision?", 2753),
    # 2755 DACI over RACI for decisions, single Approver and Driver
    ("Why did we pick DACI over RACI for decision-making?", 2789),
    # 2756 Disagree and commit: same argument needs new evidence
    ("What does 'disagree and commit' require when reraising a settled argument?", 2761),
    # 2757 Tech spec template forces Non-Goals before Design
    ("What section does the tech spec template force before the Design section?", 2771),
    # 2758 NOISE neighbour's cat climbs fig tree
    ("What offhand remark was made about the neighbour's cat?", 2745),
    # 2759 Six-pager for strategy, two-page PRFAQ for launches
    ("When do we use Amazon's six-pager versus a two-page PRFAQ?", 2753),
    # 2760 Inception and design review separate, never collapse
    ("Why do the inception and design review checkpoints never collapse into one meeting?", 2796),
    # 2761 Rejected decisions get ghost ADR with not-accepted status
    ("Why do we keep ghost ADRs for decisions that got rejected?", 2779),
    # 2762 Layering conventions as fitness functions in CI
    ("How does CI block PRs that break our domain-to-infrastructure import rule?", 2763),
    # 2763 ATAM-style evaluation on ingestion redesign, latency risk
    ("What did the ATAM-style evaluation surface in the ingestion redesign?", 2762),
    # 2764 C4 context/container/component diagrams per system, code view generated
    ("Which three C4 diagram levels does every catalogue system ship?", 2737),
    # 2765 Design docs follow arc42 template
    ("Which template do our design docs follow for cross-cutting concerns?", 2767),
    # 2766 Team decision log flat table on wiki for lightweight rulings
    ("Where do lightweight rulings that don't deserve a full ADR get recorded?", 2767),
    # 2767 Lightweight ADRs in GitHub Discussions, heavy in Confluence
    ("Why do heavy cross-team ADRs still land in Confluence?", 2766),
    # 2768 Handbook distinguishes decision from conclusion
    ("How does the handbook distinguish a decision from a mere conclusion?", 2756),
    # 2769 Onboarding reading list curates latest ten accepted ADRs
    ("What do new hires get pulled into their onboarding reading list?", 2792),
    # 2770 NOISE south window plant flowered
    ("What offhand remark was made about the south-window office plant?", 2708),
    # 2771 RFC template requires Alternatives Considered with two rejected
    ("What section does the RFC template require with at least two rejected options?", 2757),
    # 2772 Meta-ADR zero defines the ADR process
    ("What does Meta-ADR zero govern in our decision system?", 2791),
    # 2773 PR-based ADR reviews require two approvals from different teams
    ("How many approvals does a PR-based ADR review require and from whom?", 2740),
    # 2774 Design doc graveyard under /docs/retired with redirect stub
    ("Where do retired design proposals live, and what banner do they carry?", 2788),
    # 2775 Decision expiry dates required on time-bound ADRs, 30-day bot issue
    ("How does the doc bot avoid letting a time-bound ADR quietly rot?", 2794),
    # 2776 ADR ids zero-padded four digits
    ("Why are ADR ids zero-padded to four digits across our tooling?", 2750),
    # 2777 Every RFC carries a one-line tl;dr
    ("What does every RFC carry at the very top of the document?", 2757),
    # 2778 Shadow-owners on every ADR: drafter, team, on-call architect
    ("Which three named roles sit on every ADR as shadow-owners?", 2773),
    # 2779 Rejected ADR still runs full review
    ("Why do we still run the full review on rejected ADRs?", 2761),
    # 2780 Decision retros six months later, append to original ADR
    ("When do decision retrospectives run and where do they land?", 2794),
    # 2781 Tech-radar entries tied to ADRs, never free-form
    ("How are tech-radar entries tied back to ADRs when technology is adopted?", 2783),
    # 2782 Engineering council monthly for cross-team RFCs
    ("Which council rules on RFCs that cross team boundaries?", 2785),
    # 2783 ADR style forbids marketing adjectives, linter flags robust/scalable
    ("Which marketing adjectives does our ADR linter flag for the author?", 2781),
    # 2784 API deprecation process promoted to its own ADR
    ("Why did the API deprecation process get promoted to its own dedicated ADR?", 2717),
    # 2785 RFC authors pick one primary decision-maker in header
    ("Why do RFC authors name exactly one primary decision-maker in the header?", 2782),
    # 2786 improves-on relation between ADRs when additive, older stays accepted
    ("When do we use the improves-on relation instead of superseded between ADRs?", 2752),
    # 2787 Design review checklist reversibility: sprint, quarter, never
    ("What reversibility question does the design review checklist ask?", 2760),
    # 2788 Kept design docs out of main repo, folded back under /docs
    ("Why did we fold design docs back under /docs after two years outside the repo?", 2774),
    # 2789 RFC decision format: consensus, consent, dictator-for-a-day
    ("Which three decision formats can an RFC author pick up front?", 2755),
    # 2790 Shifted RFC storage from shared-drive PDFs to markdown in repo 2025-11-03
    ("When did we move RFC storage from shared-drive PDFs to markdown in the repo?", 2792),
    # 2791 ADR-0000 lists five statuses
    ("Which five statuses does ADR-0000 define for our decision records?", 2772),
    # 2792 Two-hour architecture walk during onboarding, five ADRs
    ("What architecture activity happens during onboarding and how is it scoped?", 2769),
    # 2793 Rejected heavyweight RFC gate for bugfix-grade changes
    ("Why did we reject a heavyweight RFC gate for bugfix-grade changes?", 2740),
    # 2794 ADR confidence tag low/medium/high, low requires revisit
    ("What does a low-confidence tag on an ADR commit us to?", 2775),
    # 2795 Design spec Open Questions block ships with PR, bot assigns issue ids
    ("How do Open Questions on a design spec avoid slipping through after merge?", 2757),
    # 2796 Architecture office hours every Thursday, ADR skeleton or documented no
    ("What happens when engineers bring a half-formed idea to architecture office hours?", 2760),
    # 2797 Decision landed only once ADR merged and runbook/dashboard/alert updated
    ("When does a decision count as landed under our definition?", 2720),
    # 2798 Swapped quarterly architecture all-hands for rolling ADR digest email
    ("What replaced the quarterly architecture all-hands as the comms channel?", 2769),
    # 2799 Replaced f-string SQL concat in reporting service with psycopg bound params
    ("What did we replace f-string SQL concatenation with in the reporting service?", 2762),
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    targets = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(ENTRIES) == 100
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, ((query, neg_off), tgt) in enumerate(zip(ENTRIES, targets), start=1):
            neg_row = json.loads(lines[neg_off])
            if neg_row["id"] == tgt["id"]:
                raise ValueError(f"negative row must differ from target at index {i}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": tgt["id"],
                "query": query,
                "negative": neg_row["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
