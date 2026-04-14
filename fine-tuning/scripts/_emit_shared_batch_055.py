"""One-off emitter for shared-base batch-055 — ai_coding domain (documentation / technical writing / docs-as-code workflows).

Writes 50 rows to data/v2/shared/batch_055.tmp.jsonl with ids shared-02701..02750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_055.tmp.jsonl"
ID_OFFSET = 2700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Restructured the handbook around the Diátaxis framework; the old mixed task-and-concept pages split cleanly into tutorials, how-tos, reference, and explanation sections.", "decision", "ai_coding", False,
     [("Diátaxis", "framework")],
     [],
     "which documentation structure did the handbook adopt after the rewrite",
     "diataxis four mode tutorial how to reference explanation split"),
    # --- 2 ---
    ("Moved the public docs pipeline from Sphinx to MkDocs-Material; editors stopped fighting reStructuredText and PR review cycles dropped by half.", "decision", "ai_coding", False,
     [("Sphinx", "tool"), ("MkDocs-Material", "tool"), ("reStructuredText", "language")],
     [("MkDocs-Material", "Sphinx", "REPLACES")],
     "why did the public documentation site migrate away from Sphinx",
     "mkdocs material swap editor friction markup rest review cycle"),
    # --- 3 ---
    ("Kept Sphinx over MkDocs-Material for the Python SDK reference site; autodoc plus intersphinx still beat everything else at cross-linking docstrings across releases.", "preference", "ai_coding", False,
     [("Sphinx", "tool"), ("MkDocs-Material", "tool"), ("autodoc", "tool"), ("intersphinx", "tool"), ("Python", "language")],
     [("Sphinx", "MkDocs-Material", "PREFERS")],
     "which toolchain stayed in place for the Python SDK reference and what carried the decision",
     "sphinx autodoc intersphinx python SDK cross link docstring keep"),
    # --- 4 ---
    ("Adopted MyST Markdown across the Sphinx site; directives now read like fenced code fences and contributors stopped hand-writing colon-heavy rST.", "milestone", "ai_coding", False,
     [("MyST Markdown", "language"), ("Sphinx", "tool"), ("rST", "language")],
     [("MyST Markdown", "rST", "REPLACES")],
     "which markup change made Sphinx contributions feel modern to outside writers",
     "myst markdown directive fenced code rst colon heavy migration"),
    # --- 5 ---
    ("Docusaurus 3 landed with MDX 3 support; embedding live React demos next to prose finally stopped corrupting the markdown AST in edge cases.", "fact", "ai_coding", False,
     [("Docusaurus 3", "framework"), ("MDX 3", "language"), ("React", "library")],
     [],
     "which Docusaurus release fixed the MDX parser edge cases around embedded components",
     "docusaurus three mdx live react demo prose ast regression"),
    # --- 6 ---
    ("Multi-repo docs moved to Antora; each product repo owns its own content branch and the playbook assembles them into a single versioned site nightly.", "architecture", "ai_coding", False,
     [("Antora", "tool"), ("playbook", "config")],
     [],
     "how do we assemble docs that live next to source across many repositories",
     "antora multi repo content branch playbook aggregate nightly build"),
    # --- 7 ---
    ("Linting switched from write-good to Vale with a vocabulary-driven style; the allowlist cut false positives on product names by about 80 percent.", "decision", "ai_coding", False,
     [("write-good", "tool"), ("Vale", "tool")],
     [("Vale", "write-good", "REPLACES")],
     "which prose linter replaced write-good and what tuning made it usable",
     "vale linter vocabulary allowlist product name false positive reduce"),
    # --- 8 ---
    ("Added cspell with a shared workspace dictionary; typos in code samples now fail CI the same way a broken import would.", "architecture", "ai_coding", False,
     [("cspell", "tool"), ("CI", "infrastructure")],
     [],
     "which spell checker gates docs builds and how are product-specific words handled",
     "cspell workspace dictionary typo CI gate code sample enforce"),
    # --- 9 ---
    ("Link checking runs lychee in CI on every PR; htmlproofer stays on the nightly full-site crawl because its retry and anchor-matching are more forgiving.", "architecture", "ai_coding", False,
     [("lychee", "tool"), ("htmlproofer", "tool"), ("CI", "infrastructure")],
     [],
     "which link checkers run at which cadence for the docs site",
     "lychee per PR htmlproofer nightly crawl anchor retry broken link"),
    # --- 10. noise ---
    ("The office plant by the window has started flowering again after I moved it a foot closer to the heater.", "fact", "noise", True, [], [], None, None),

    # --- 11 ---
    ("Every docs PR gets a Read the Docs preview build and a Netlify Deploy Preview; reviewers click through the hosted diff instead of pulling branches.", "fact", "ai_coding", False,
     [("Read the Docs", "platform"), ("Netlify Deploy Preview", "service")],
     [],
     "which preview builds attach to docs pull requests for reviewer click-through",
     "read the docs netlify preview build pull request reviewer diff"),
    # --- 12 ---
    ("Added an accessibility audit step using axe-core against the rendered preview; missing alt text and low-contrast tokens now block merge like any other CI check.", "milestone", "ai_coding", False,
     [("axe-core", "tool"), ("CI", "infrastructure")],
     [],
     "how do we stop inaccessible docs pages from shipping to production",
     "a11y audit axe core alt text contrast token CI block merge gate"),
    # --- 13 ---
    ("Architecture decisions live under docs/adr/ using adr-tools; each file starts with status, context, decision, and consequences sections and is immutable once accepted.", "architecture", "ai_coding", False,
     [("docs/adr/", "file"), ("adr-tools", "tool")],
     [],
     "where do architecture decision records live in the repo and what shape do they take",
     "adr folder tool status context decision consequence immutable record"),
    # --- 14 ---
    ("Killed the free-form design-doc pile in favour of a templated RFC process; every new proposal fills the same six headings and closes with an accept or reject.", "decision", "ai_coding", False,
     [("RFC", "pattern")],
     [],
     "which proposal format replaced the old free-form design doc tree",
     "rfc template heading accept reject proposal structure replace"),
    # --- 15 ---
    ("Glossary sits in a single glossary.md with term definitions and redirects; Vale flags any doc using a term that is not in the glossary or its alias list.", "architecture", "ai_coding", False,
     [("glossary.md", "file"), ("Vale", "tool")],
     [],
     "how does the docs toolchain enforce consistent terminology across authors",
     "glossary central term definition vale flag alias unknown word"),
    # --- 16 ---
    ("REST reference now builds from the OpenAPI spec via Redoc; dropped Slate after two years because keeping Markdown and YAML in sync became its own project.", "decision", "ai_coding", False,
     [("Redoc", "tool"), ("Slate", "tool"), ("OpenAPI", "protocol")],
     [("Redoc", "Slate", "REPLACES")],
     "which REST reference generator did the team settle on and what drove it",
     "redoc slate replace openapi source of truth yaml markdown drift"),
    # --- 17 ---
    ("Evaluated Stoplight Elements alongside Redoc; Elements' try-it panel was nice but the licensing tail was not worth the single feature.", "decision", "ai_coding", False,
     [("Stoplight Elements", "tool"), ("Redoc", "tool")],
     [],
     "which REST reference alternative lost the bake-off against Redoc and why",
     "stoplight elements evaluate try it licensing reject single feature"),
    # --- 18 ---
    ("GraphQL reference uses the Docusaurus GraphQL plugin; introspection runs at build time so schema drift surfaces as a red CI instead of a stale page.", "architecture", "ai_coding", False,
     [("Docusaurus GraphQL plugin", "library"), ("GraphQL", "language"), ("CI", "infrastructure")],
     [],
     "which plugin generates the GraphQL reference and how does it catch schema drift",
     "docusaurus graphql plugin introspection build schema drift ci fail"),
    # --- 19 ---
    ("Changelog generation hooks into conventional-changelog; a release tag pushes a new page to the docs site and a banner on the landing page for 14 days.", "architecture", "ai_coding", False,
     [("conventional-changelog", "tool")],
     [],
     "how does a release show up on the documentation site without manual authoring",
     "changelog automation conventional commit release tag landing banner"),
    # --- 20 ---
    ("Screenshots rebuild nightly via a Playwright job; a diff bot comments on the PR when any product screenshot shifts by more than a pixel threshold.", "architecture", "ai_coding", False,
     [("Playwright", "tool")],
     [],
     "how do we keep product screenshots in the docs from drifting silently",
     "playwright screenshot nightly diff bot pixel threshold PR comment"),
    # --- 21 ---
    ("Tested code snippets in Python docs run through doctest in CI; every fenced ```python``` block that imports our SDK is extracted and executed on a matrix of versions.", "architecture", "ai_coding", False,
     [("doctest", "tool"), ("Python", "language"), ("CI", "infrastructure")],
     [],
     "how do we prove Python code samples in the docs still work against the current SDK",
     "doctest python fence extract ci matrix SDK version snippet run"),
    # --- 22 ---
    ("Runbooks live under docs/runbooks/ with a fixed schema: symptom, scope, diagnosis, mitigation, follow-up; on-call templates scaffold a new one in under a minute.", "architecture", "ai_coding", False,
     [("docs/runbooks/", "file")],
     [],
     "which runbook shape did we settle on and how do on-call engineers scaffold new ones",
     "runbook symptom scope diagnose mitigate follow up schema template"),
    # --- 23 ---
    ("Content inventory audit on 2026-03-20 flagged 412 pages as stale by git-last-touched older than 18 months; owners got filed tickets grouped by team.", "milestone", "ai_coding", False,
     [("2026-03-20", "date")],
     [],
     "what did the last content inventory pass surface and how was follow-up distributed",
     "inventory audit stale page git timestamp eighteen month owner ticket"),
    # --- 24 ---
    ("Doc debt dashboard tracks broken links, stale-date pages, coverage gaps, and Vale severity; the weekly report goes to the docs Slack channel on Monday at 09:00.", "architecture", "ai_coding", False,
     [("Vale", "tool"), ("Slack", "platform")],
     [],
     "which doc-debt signals roll up into the weekly report and where does it land",
     "doc debt metric broken link stale coverage vale severity slack"),
    # --- 25 ---
    ("Deprecation banners are a reusable MDX component rendered at the top of any page whose front matter carries a deprecated_on date before today.", "architecture", "ai_coding", False,
     [("MDX", "language"), ("front matter", "config")],
     [],
     "how do deprecated doc pages signal their status to readers without hand-edited warnings",
     "deprecation banner reusable component front matter date render"),
    # --- 26 ---
    ("Moved the localisation pipeline from Crowdin to Weblate; self-hosting gave us translation-memory ownership and stopped the per-string pricing surprise.", "decision", "ai_coding", False,
     [("Crowdin", "service"), ("Weblate", "tool")],
     [("Weblate", "Crowdin", "REPLACES")],
     "which translation platform did docs move to and what drove the switch",
     "crowdin weblate self host translation memory pricing ownership"),
    # --- 27 ---
    ("Rejected GitLocalize during the eval; the round-trip on branches looked clean but its reviewer queue mixed in ML-pretranslated strings with no flag.", "decision", "ai_coding", False,
     [("GitLocalize", "service")],
     [],
     "which translation tool got cut from the shortlist and why",
     "gitlocalize reject reviewer queue machine translation flag missing"),
    # --- 28 ---
    ("Docs SEO cleanup shipped canonical URLs per version, a sitemap split by language, and og:image generation via satori; organic traffic recovered 18 percent in six weeks.", "milestone", "ai_coding", False,
     [("satori", "library"), ("og:image", "config")],
     [],
     "what SEO changes did the docs site ship and what did they move on the traffic graph",
     "docs seo canonical sitemap language og image satori traffic recover"),
    # --- 29 ---
    ("Versioned docs use symlinked directories under /en/<version>/ with a small nginx rule that redirects /latest/ to the most recent release; no build duplication.", "architecture", "ai_coding", False,
     [("nginx", "service")],
     [],
     "how is docs versioning laid out on disk and how does the latest alias work",
     "versioned docs symlink directory nginx redirect latest alias release"),
    # --- 30 ---
    ("Dark-mode tokens live in a single tokens.json consumed by both the docs theme and the marketing site; contrast ratios are tested in CI against WCAG AA.", "architecture", "ai_coding", False,
     [("tokens.json", "file"), ("CI", "infrastructure"), ("WCAG AA", "concept")],
     [],
     "where do docs colour tokens live and how is accessibility enforced on theme edits",
     "dark mode token json single source theme contrast wcag ci check"),
    # --- 31 ---
    ("Search moved from Algolia DocSearch to self-hosted typesense-docsearch; latency dropped and we finally got control over boosted sections per product.", "decision", "ai_coding", False,
     [("Algolia DocSearch", "service"), ("typesense-docsearch", "tool")],
     [("typesense-docsearch", "Algolia DocSearch", "REPLACES")],
     "which docs search tool replaced Algolia and what capability did the swap unlock",
     "algolia docsearch typesense self host latency boost section control"),
    # --- 32 ---
    ("Considered Meilisearch for docs search but its ranking rules felt too opaque for our tuning workflow; typesense won on explainability alone.", "decision", "ai_coding", False,
     [("Meilisearch", "service"), ("typesense", "tool")],
     [],
     "which search backend lost the docs bake-off against typesense and why",
     "meilisearch evaluate ranking opaque tuning workflow explainability reject"),
    # --- 33 ---
    ("Kept a static lunr index as a fallback for fully offline docs tarballs; it ships with the downloadable zip and works without any JavaScript runtime host.", "fact", "ai_coding", False,
     [("lunr", "library")],
     [],
     "which search index ships with the offline documentation bundle",
     "lunr static index offline tarball download no server javascript"),
    # --- 34 ---
    ("Stale-docs detection runs git log --diff-filter=M on every tracked page; anything untouched for 12 months gets an auto-opened issue tagged docs-review.", "architecture", "ai_coding", False,
     [("git log", "command")],
     [],
     "how does the repo auto-surface pages that have gone without edits for too long",
     "stale doc detect git log timestamp twelve month auto issue tag"),
    # --- 35 ---
    ("Adopted a writing-style guide that builds on the Google developer documentation style; carved out our own exceptions for product-specific casing and voice.", "reference", "ai_coding", False,
     [("Google developer documentation style", "publication")],
     [],
     "which public style guide does our internal writing guide extend",
     "style guide google developer extend exception product casing voice"),
    # --- 36 ---
    ("The tutorials section improves on the old getting-started single page; splitting by persona cut the average time-to-first-success in user tests from 22 to 7 minutes.", "milestone", "ai_coding", False,
     [("tutorials", "concept"), ("getting-started", "file")],
     [("tutorials", "getting-started", "IMPROVES_ON")],
     "what replaced the old single getting-started page and what did user tests show",
     "tutorials persona split time first success user test improvement"),
    # --- 37 ---
    ("Front matter on every page carries owner, last_reviewed, and applies_to_version keys; our dashboard joins these with CI data to show coverage by surface area.", "architecture", "ai_coding", False,
     [("Front matter", "config")],
     [],
     "which metadata fields on doc pages drive ownership and coverage dashboards",
     "front matter owner last reviewed applies to version dashboard coverage"),
    # --- 38 ---
    ("Contributor guide lives in CONTRIBUTING.md with a short how-to-edit-docs section; larger style rules stay in a separate docs/style/ to keep the main file scannable.", "preference", "ai_coding", False,
     [("CONTRIBUTING.md", "file"), ("docs/style/", "file")],
     [],
     "where do contributor instructions and style rules live and why are they split",
     "contributing file style split scannable long rule separate folder"),
    # --- 39 ---
    ("Diagrams moved to Mermaid embedded in MDX; SVG assets remained only for hand-drawn architectures where Mermaid's layout fell down in practice.", "decision", "ai_coding", False,
     [("Mermaid", "tool"), ("MDX", "language"), ("SVG", "protocol")],
     [],
     "which diagram source format does the docs site prefer and what stays as static SVG",
     "mermaid diagram mdx svg fallback hand draw layout complex"),
    # --- 40 ---
    ("Wrote a small Node script to extract every ```js fence from the tutorials, run it through a sandboxed vm2 context, and assert expected console output.", "architecture", "ai_coding", False,
     [("Node", "platform"), ("vm2", "library")],
     [],
     "how do JavaScript tutorial snippets get exercised in CI",
     "node script extract fence sandbox vm2 console assert ci run"),
    # --- 41 ---
    ("Docs publishing pipeline builds on the shared Turborepo graph; touching a content file only rebuilds the affected site, not the whole monorepo docs tree.", "architecture", "ai_coding", False,
     [("Turborepo", "tool"), ("monorepo", "concept")],
     [("Turborepo", "monorepo", "BUILDS_ON")],
     "how does the docs build avoid rebuilding every site when one page changes",
     "turborepo graph incremental docs monorepo affected build skip"),
    # --- 42 ---
    ("Kept a dedicated docs branch protected separately from main; docs-only PRs merge without waiting on the engineering CI suite.", "preference", "ai_coding", False,
     [("main", "concept")],
     [],
     "why does the docs workflow have its own branch protection rules",
     "docs branch protect separate main engineering ci wait skip policy"),
    # --- 43 ---
    ("Added a /docs/feedback endpoint that posts a tiny JSON blob from a thumbs-up thumbs-down widget; results feed a weekly content-quality review.", "architecture", "ai_coding", False,
     [("/docs/feedback", "api")],
     [],
     "how do readers send signal about doc quality and where does that data land",
     "feedback widget thumbs endpoint json blob weekly review content quality"),
    # --- 44 ---
    ("Pull request template for docs asks explicitly for the affected Diátaxis mode; reviewers have an easier time spotting a how-to masquerading as reference.", "preference", "ai_coding", False,
     [("Diátaxis", "framework")],
     [],
     "which prompt in the docs PR template keeps page types honest during review",
     "pr template diataxis mode prompt reviewer how to reference mismatch"),
    # --- 45 ---
    ("Canonical examples repo lives at examples/ in the main monorepo; every doc example imports from it so drift between prose and code simply cannot happen.", "architecture", "ai_coding", False,
     [("examples/", "file"), ("monorepo", "concept")],
     [],
     "how do we keep prose snippets and the canonical example code from drifting apart",
     "examples folder import docs reuse single source prose code no drift"),
    # --- 46 ---
    ("Dropped PDF export after usage fell under 0.3 percent of sessions; maintaining the pandoc path and the fonts was more work than the remaining readers justified.", "decision", "ai_coding", False,
     [("PDF", "concept"), ("pandoc", "tool")],
     [],
     "which export format got cut from the docs pipeline and what tipped the decision",
     "pdf export drop usage threshold pandoc font maintenance cost reader"),
    # --- 47. noise ---
    ("Neighbours finally replaced the garage door that had been sticking every cold morning since November.", "fact", "noise", True, [], [], None, None),
    # --- 48 ---
    ("Rejected a hand-authored examples markdown tree; too many examples silently drifted when the SDK surface moved and nobody caught it without a test harness.", "problem", "ai_coding", False,
     [("SDK", "concept")],
     [],
     "which authoring approach for code examples did we reject and what failure drove it",
     "hand authored example reject drift sdk surface test harness missing"),
    # --- 49 ---
    ("Documentation IA improves on the alphabetical API index by grouping endpoints around user tasks; the alphabetical view stays available as a secondary drawer.", "architecture", "ai_coding", False,
     [("Documentation IA", "concept"), ("alphabetical API index", "concept")],
     [("Documentation IA", "alphabetical API index", "IMPROVES_ON")],
     "which information-architecture change replaced the alphabetical API index and what remained",
     "information architecture task group endpoint alphabet secondary drawer"),
    # --- 50 ---
    ("Edits to reference pages require a linked changelog entry; the PR template enforces it and the bot blocks merge if the link is missing or points outside /changelog/.", "architecture", "ai_coding", False,
     [("/changelog/", "file")],
     [],
     "which rule ties reference page edits to changelog entries and how is it enforced",
     "reference edit changelog link PR template bot block merge enforce"),
]

# Non-entity graph source/target (for relationships that use names not in the entity list)
# None here — all relationship endpoints must appear as entity names in the same row.


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
