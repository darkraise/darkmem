"""One-off emitter for shared-base batch-115 — ai_coding domain (internationalization / localization mechanics: gettext, ICU, Fluent, CLDR, react-intl / i18next / LinguiJS / next-intl, TMS integrations, pseudo-loc, RTL, Intl/Temporal formatting).

Writes 50 rows to data/v2/shared/batch_115.tmp.jsonl with ids shared-05701..05750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_115.tmp.jsonl"
ID_OFFSET = 5700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the catalog message pipeline from raw template strings to FormatJS so every plural and select branch gets compiled and typechecked at build time.", "decision", "ai_coding", False,
     [("FormatJS", "library"), ("template strings", "pattern"), ("catalog", "pattern")],
     [("FormatJS", "template strings", "REPLACES")],
     "which library replaced raw template string interpolation in the catalog pipeline and why",
     "formatjs replace template string catalog plural select compile type check"),
    # --- 2 ---
    ("Adopted ICU MessageFormat for every user-facing string; English source now carries `{count, plural, one {# item} other {# items}}` so translators see the branches directly.", "architecture", "ai_coding", False,
     [("ICU MessageFormat", "protocol"), ("plural", "pattern")],
     [],
     "which message syntax do source strings use so translators can edit plural branches in place",
     "icu messageformat plural one other branch source string translator"),
    # --- 3 ---
    ("LinguiJS replaced i18next on the TypeScript front end; the macro-based extraction and automatic message IDs cut the catalog drift we kept seeing in PR review.", "decision", "ai_coding", False,
     [("LinguiJS", "library"), ("i18next", "library"), ("TypeScript", "language")],
     [("LinguiJS", "i18next", "IMPROVES_ON")],
     "which i18n library replaced i18next on the TypeScript front end and what improved",
     "linguijs replace i18next typescript macro extract auto message id drift"),
    # --- 4 ---
    ("Crowdin replaced the manual spreadsheet round-trip the ops team maintained; GitHub integration now opens translation PRs directly against the catalogs folder.", "milestone", "ai_coding", False,
     [("Crowdin", "service"), ("spreadsheet", "pattern"), ("catalogs", "file")],
     [("Crowdin", "spreadsheet", "REPLACES")],
     "which translation tool took over from the spreadsheet workflow and how do strings reach the repo now",
     "crowdin swap sheet round trip github pull request catalog folder"),
    # --- 5 ---
    ("Locale-aware formatting moved to the Intl API across the browser build; moment-with-locales dropped out of the bundle saving 310 KB gzipped.", "decision", "ai_coding", False,
     [("Intl", "library"), ("moment", "library"), ("browser", "platform")],
     [("Intl", "moment", "REPLACES")],
     "which native API replaced moment for locale-aware formatting in the browser bundle",
     "intl api replace moment locale format browser bundle size reduce"),
    # --- 6 ---
    ("The Temporal API powers the new date-range picker; PlainDate plus Intl.DateTimeFormat finally killed the timezone juggling we had layered on top of moment.", "architecture", "ai_coding", False,
     [("Temporal", "library"), ("PlainDate", "method"), ("Intl.DateTimeFormat", "method"), ("moment", "library")],
     [("Temporal", "moment", "REPLACES")],
     "which modern date API replaced moment for the picker and what timezone problem did it fix",
     "temporal api plaindate intl datetimeformat replace moment timezone juggling"),
    # --- 7 ---
    ("Fluent from Mozilla ships the desktop app's catalogs; per-locale asymmetric plural counts and inline term references are easier to express than in raw gettext.", "architecture", "ai_coding", False,
     [("Fluent", "protocol"), ("gettext", "tool"), ("desktop app", "project")],
     [("Fluent", "gettext", "IMPROVES_ON")],
     "which message format did the desktop app pick over gettext and what made it a better fit",
     "fluent mozilla catalog asymmetric plural term reference gettext desktop"),
    # --- 8 ---
    ("gettext still drives the legacy Python web UI; the build runs `xgettext` plus `msgmerge` and then `msgfmt --check` as a release gate so malformed .po files never ship.", "reference", "ai_coding", False,
     [("gettext", "tool"), ("xgettext", "command"), ("msgmerge", "command"), ("msgfmt", "command"), (".po", "file")],
     [],
     "which gettext commands does the legacy Python UI run and what gate prevents broken catalogs from shipping",
     "gettext xgettext msgmerge msgfmt check release gate po legacy python"),
    # --- 9 ---
    ("CLDR data drives every plural form decision; the build pins cldr-json 45.0 and a unit test fails if the installed version does not match the lockfile.", "architecture", "ai_coding", False,
     [("CLDR", "publication"), ("cldr-json", "library"), ("plural form", "concept")],
     [],
     "which data source drives plural form decisions and how is its version pinned in CI",
     "cldr json plural form version pin lockfile unit test enforce"),
    # --- 10. noise ---
    ("The thermos on the kitchen shelf still keeps coffee hot for exactly six hours and forty minutes.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("react-intl wraps the React tree via IntlProvider at the layout root; useIntl replaced the old context.formatMessage spreading we had scattered across class components.", "architecture", "ai_coding", False,
     [("react-intl", "library"), ("IntlProvider", "method"), ("useIntl", "method")],
     [],
     "how does react-intl plug into the React tree and which hook superseded the class-component pattern",
     "react intl intlprovider useintl hook class component formatmessage context"),
    # --- 12 ---
    ("next-intl replaced a homegrown locale router on the Next.js app; the middleware handles the `[locale]` segment and falls back through the Accept-Language list automatically.", "milestone", "ai_coding", False,
     [("next-intl", "library"), ("homegrown locale router", "pattern"), ("Next.js", "framework"), ("Accept-Language", "config")],
     [("next-intl", "homegrown locale router", "REPLACES"), ("next-intl", "Next.js", "USES")],
     "which library replaced the homegrown locale router on Next.js and what does the middleware handle",
     "next intl replace homegrown router locale segment accept language fallback"),
    # --- 13 ---
    ("Vue I18n v10 landed on the storefront; the composition API integration removed the last Options-style mixin and unlocked tree-shaking on unused locale messages.", "milestone", "ai_coding", False,
     [("Vue I18n", "library"), ("composition API", "pattern"), ("storefront", "project")],
     [],
     "which Vue i18n upgrade landed on the storefront and what did composition-API integration unlock",
     "vue i18n composition api mixin tree shake storefront upgrade"),
    # --- 14 ---
    ("Kotlin Android uses the standard `res/values-es/strings.xml` layout; quantity strings go through the `plurals` tag so CLDR rules apply without extra runtime code.", "fact", "ai_coding", False,
     [("Kotlin", "language"), ("strings.xml", "file"), ("plurals", "pattern")],
     [],
     "how does the Kotlin Android side handle plural strings without custom runtime logic",
     "kotlin android res values strings xml plurals tag cldr rule"),
    # --- 15 ---
    ("iOS builds rely on `.stringsdict` for plural variants; a pre-commit check runs `plutil -lint` on every dict so a stray comma can't brick the app at runtime.", "preference", "ai_coding", False,
     [(".stringsdict", "file"), ("plutil", "command"), ("iOS", "platform")],
     [],
     "which iOS plural mechanism do we use and how do we catch malformed files before they ship",
     "ios stringsdict plural plutil lint pre commit check malformed"),
    # --- 16 ---
    ("Flutter app wires the `intl` package plus `intl_utils` generator; the ARB files live in `lib/l10n` and a pubspec hook runs the generator on every flutter build.", "architecture", "ai_coding", False,
     [("Flutter", "framework"), ("intl", "library"), ("intl_utils", "tool"), ("ARB", "file")],
     [("intl_utils", "ARB", "USES")],
     "how is the Flutter intl tooling wired and where do the ARB source files live",
     "flutter intl intl utils arb lib l10n pubspec generator hook"),
    # --- 17 ---
    ("Lokalise runs as the primary TMS for mobile; the CLI `lokalise2 file download` step in Fastlane pulls the latest bundle before every beta upload.", "architecture", "ai_coding", False,
     [("Lokalise", "service"), ("lokalise2", "tool"), ("Fastlane", "tool")],
     [("Lokalise", "Fastlane", "COMMUNICATES_WITH")],
     "which TMS backs mobile releases and how does Fastlane fetch the latest translation bundle",
     "lokalise lokalise2 cli fastlane mobile beta download bundle tms"),
    # --- 18 ---
    ("Weblate hosts the open-source component's translations; self-hosting it on the docs VM let the maintainers keep the round-trip fully inside the project infrastructure.", "decision", "ai_coding", False,
     [("Weblate", "service"), ("docs VM", "infrastructure")],
     [],
     "which self-hosted TMS handles the OSS component's translations and where does it live",
     "weblate self host translation open source component docs vm"),
    # --- 19 ---
    ("Phrase replaced Lokalise on the marketing site because the in-context editor overlay matched the content team's workflow of editing strings live on the staging page.", "decision", "ai_coding", False,
     [("Phrase", "service"), ("Lokalise", "service"), ("marketing site", "project")],
     [("Phrase", "Lokalise", "REPLACES")],
     "which TMS swap happened on the marketing site and which feature drove the switch",
     "phrase replace lokalise marketing in context editor overlay staging"),
    # --- 20 ---
    ("Pseudo-localization runs in CI on every PR; the `accented` and `expand` transforms from formatjs-pseudo-locale shift each letter and pad by 40 percent so truncation shows up in visual diffs.", "architecture", "ai_coding", False,
     [("Pseudo-localization", "pattern"), ("formatjs-pseudo-locale", "library"), ("CI", "infrastructure")],
     [],
     "how does CI surface i18n truncation and layout issues before translators see them",
     "pseudo localization formatjs accented expand ci truncation visual diff"),
    # --- 21 ---
    ("The release pipeline enforces a string freeze 72 hours before tag; a Semgrep rule flags new message IDs in the catalog and the job fails so translators always see a stable corpus.", "architecture", "ai_coding", False,
     [("string freeze", "concept"), ("Semgrep", "tool"), ("release pipeline", "infrastructure")],
     [],
     "which release gate keeps translators from chasing a moving corpus before every tag",
     "string freeze 72 hour release tag semgrep catalog message id gate"),
    # --- 22 ---
    ("ICU ordinal selectors power the leaderboard; `{rank, selectordinal, one {#st} two {#nd} few {#rd} other {#th}}` handles English and every other CLDR-listed ordinal rule without extra code.", "fact", "ai_coding", False,
     [("ICU", "protocol"), ("selectordinal", "pattern"), ("leaderboard", "project")],
     [],
     "how does the leaderboard render ordinal suffixes without custom per-locale code",
     "icu selectordinal leaderboard st nd rd th cldr ordinal rule"),
    # --- 23 ---
    ("Gender-aware strings use ICU `select`; the profile page picks `{gender, select, female {...} male {...} other {...}}` rather than stitching phrases so translators preserve agreement.", "architecture", "ai_coding", False,
     [("ICU", "protocol"), ("select", "pattern"), ("profile page", "project")],
     [],
     "which ICU construct keeps gender-aware profile strings grammatical instead of stitched together",
     "icu select gender female male other agreement profile stitch"),
    # --- 24 ---
    ("The Arabic storefront renders with `dir=\"rtl\"` on the html tag plus logical CSS properties everywhere; `margin-inline-start` replaced the old `margin-left` usage across components.", "milestone", "ai_coding", False,
     [("dir=\"rtl\"", "config"), ("margin-inline-start", "pattern"), ("margin-left", "pattern"), ("Arabic", "language")],
     [("margin-inline-start", "margin-left", "REPLACES")],
     "which RTL plumbing shipped for the Arabic storefront and which CSS swap enabled it",
     "rtl direction arabic margin inline start replace margin left logical css"),
    # --- 25 ---
    ("Bidi isolation for user-supplied content wraps strings in `<bdi>` or uses the Unicode FSI character; an RLO smuggled through a filename once flipped the whole file list for Hebrew viewers.", "problem", "ai_coding", False,
     [("<bdi>", "pattern"), ("FSI", "protocol"), ("RLO", "pattern"), ("Hebrew", "language")],
     [],
     "which bidi primitive prevents user-supplied content from flipping layout for Hebrew viewers",
     "bidi isolation bdi fsi rlo hebrew user content flip filename"),
    # --- 26 ---
    ("Number formatting uses `Intl.NumberFormat` with currency style and the `signDisplay: \"exceptZero\"` option; the homegrown `formatPrice` helper with hardcoded `.toFixed(2)` is gone.", "milestone", "ai_coding", False,
     [("Intl.NumberFormat", "method"), ("signDisplay", "config"), ("formatPrice", "method"), (".toFixed", "method")],
     [("Intl.NumberFormat", "formatPrice", "REPLACES")],
     "which native formatter replaced the homegrown formatPrice helper and which option did we pick for signs",
     "intl numberformat currency sign display except zero format price tofixed"),
    # --- 27 ---
    ("Accept-Language negotiation runs on the edge via Cloudflare Workers; the worker resolves to one of the catalog locales and sets a cookie so subsequent loads skip the header parse.", "architecture", "ai_coding", False,
     [("Accept-Language", "config"), ("Cloudflare Workers", "platform")],
     [("Cloudflare Workers", "Accept-Language", "USES")],
     "how does the edge negotiate a locale on the first request and avoid re-parsing headers",
     "accept language cloudflare workers edge catalog locale cookie"),
    # --- 28 ---
    ("Fallback chain is defined as `es-AR -> es-419 -> es -> en`; missing keys fall through deterministically instead of the previous alphabetical-sibling accident that surfaced `de` on a Latin-American page.", "architecture", "ai_coding", False,
     [("es-AR", "language"), ("es-419", "language"), ("Fallback chain", "pattern")],
     [],
     "which fallback chain did we pin after a bug surfaced a wrong-language sibling on missing keys",
     "fallback chain es ar 419 spanish deterministic missing key sibling"),
    # --- 29 ---
    ("Screenshot context is attached to every extracted message via `formatjs extract --extract-source-location` plus a Puppeteer crawl that posts the rendered frame to Crowdin.", "architecture", "ai_coding", False,
     [("formatjs extract", "command"), ("Puppeteer", "tool"), ("Crowdin", "service")],
     [("Puppeteer", "Crowdin", "COMMUNICATES_WITH")],
     "how do translators see the rendered context around each extracted message",
     "screenshot context formatjs extract source location puppeteer crowdin"),
    # --- 30 ---
    ("Parameter escaping in ICU strings uses single-quoted apostrophes to keep the original behavior; the linter flags any `'` that would accidentally disable the `{}` placeholder parser.", "problem", "ai_coding", False,
     [("ICU", "protocol"), ("apostrophe", "pattern"), ("linter", "tool")],
     [],
     "which ICU gotcha around apostrophes does the linter catch before the build",
     "icu apostrophe escape single quote placeholder disable linter"),
    # --- 31 ---
    ("User-supplied content passes through DOMPurify after locale-specific formatting; the chain runs format first then sanitise so bidi overrides inside user text cannot break surrounding RTL layout.", "architecture", "ai_coding", False,
     [("DOMPurify", "library"), ("user text", "pattern"), ("RTL", "pattern")],
     [],
     "which order do we apply locale formatting and sanitisation to untrusted content and why",
     "dompurify sanitize format order user content bidi override rtl"),
    # --- 32 ---
    ("Date ranges use `Intl.DateTimeFormat.formatRange`; the `2026-04-01 – 2026-04-15` dash is now locale-correct and the hand-rolled en-dash fallback got deleted from the utility module.", "milestone", "ai_coding", False,
     [("Intl.DateTimeFormat", "method"), ("formatRange", "method"), ("en-dash", "pattern"), ("2026-04-01", "date"), ("2026-04-15", "date")],
     [("formatRange", "en-dash", "REPLACES")],
     "which API produces locale-correct date ranges and what did we delete after adopting it",
     "intl datetimeformat format range en dash locale correct utility delete"),
    # --- 33 ---
    ("Timezone names render via `Intl.DateTimeFormat` with `timeZoneName: \"longGeneric\"`; this replaced a static lookup table that had gone stale during the 2022 IANA zone merges.", "problem", "ai_coding", False,
     [("Intl.DateTimeFormat", "method"), ("longGeneric", "config"), ("lookup table", "pattern"), ("IANA", "organization")],
     [("Intl.DateTimeFormat", "lookup table", "REPLACES")],
     "which timezone-name source replaced the stale lookup table after the IANA merges",
     "intl timezone name long generic iana merge lookup table stale"),
    # --- 34 ---
    ("Message IDs use the dotted domain convention like `checkout.button.pay_now`; the old prose IDs that embedded English fragments broke whenever copy shifted.", "decision", "ai_coding", False,
     [("Message IDs", "pattern"), ("checkout.button.pay_now", "pattern"), ("prose IDs", "pattern")],
     [("Message IDs", "prose IDs", "REPLACES")],
     "which message-ID convention replaced the prose IDs and why did the old style keep breaking",
     "message id dotted domain prose checkout pay now copy shift"),
    # --- 35 ---
    ("Locale bundles are split per route via dynamic imports; the shell loads the base `en` bundle and lazy-loads additional locales so the first paint is never blocked by 40 language packs.", "architecture", "ai_coding", False,
     [("Locale bundles", "pattern"), ("dynamic imports", "pattern"), ("en", "language")],
     [],
     "how are locale bundles split to keep first paint fast across many languages",
     "locale bundle split dynamic import lazy load first paint shell base"),
    # --- 36 ---
    ("Catalog files live in `packages/i18n/catalogs/<locale>.po` and `<locale>.json` side by side; the build tolerates both because the migration from gettext to LinguiJS is still in flight.", "fact", "ai_coding", False,
     [("packages/i18n/catalogs", "file"), ("gettext", "tool"), ("LinguiJS", "library")],
     [],
     "where do catalog files live and why does the build tolerate two formats right now",
     "catalog packages i18n po json gettext linguijs migration flight"),
    # --- 37 ---
    ("Translator comments ride on every source string via `/* i18n: */` JSDoc blocks; `formatjs extract` picks them up and Crowdin surfaces the hint next to the translation field.", "preference", "ai_coding", False,
     [("i18n:", "pattern"), ("JSDoc", "pattern"), ("formatjs extract", "command"), ("Crowdin", "service")],
     [],
     "how do developer hints reach translators through extraction and the TMS",
     "translator comment i18n jsdoc formatjs extract crowdin hint field"),
    # --- 38 ---
    ("Pluralization bugs surfaced when `ru` fell back to English plural rules because the CLDR bundle wasn't loaded; we now fail the build if any shipped locale lacks a plural rules entry.", "problem", "ai_coding", False,
     [("ru", "language"), ("CLDR", "publication"), ("plural rules", "concept")],
     [],
     "which Russian plural bug did we hit and what build check prevents it now",
     "russian plural rule cldr bundle not loaded fallback english build fail"),
    # --- 39 ---
    ("Crowdin's OTA SDK pushes hotfixes for mobile strings without a new app store build; the 24-hour cache window is small enough for urgent copy fixes and large enough to keep API quota sane.", "architecture", "ai_coding", False,
     [("Crowdin", "service"), ("OTA SDK", "library"), ("app store", "platform")],
     [],
     "how do mobile string fixes ship without a new app store build and what cache window do we use",
     "crowdin ota sdk mobile string hotfix app store cache window 24 hour"),
    # --- 40 ---
    ("The CI pseudo-locale run catches hardcoded strings: any node whose `textContent` is unchanged after the `en-XA` transform is flagged by a Playwright snapshot test as un-externalised.", "architecture", "ai_coding", False,
     [("en-XA", "language"), ("Playwright", "tool"), ("textContent", "method")],
     [],
     "which test technique surfaces hardcoded strings that were never extracted into the catalog",
     "pseudo locale en xa hardcoded string playwright snapshot text content"),
    # --- 41 ---
    ("List formatting runs through `Intl.ListFormat`; the `and`/`or` variants handle Arabic's serial comma absence and the old `.join(\", \")` helper is now only used for CSV export.", "milestone", "ai_coding", False,
     [("Intl.ListFormat", "method"), (".join", "method"), ("Arabic", "language")],
     [("Intl.ListFormat", ".join", "REPLACES")],
     "which native formatter replaced the naive join for user-facing lists and what locale quirk did it handle",
     "intl list format and or arabic serial comma join csv replace"),
    # --- 42 ---
    ("Relative-time strings use `Intl.RelativeTimeFormat` with `numeric: \"auto\"` so English gets `yesterday` instead of `1 day ago`; the homegrown `humanize` function retired on that switch.", "milestone", "ai_coding", False,
     [("Intl.RelativeTimeFormat", "method"), ("humanize", "method"), ("numeric", "config")],
     [("Intl.RelativeTimeFormat", "humanize", "REPLACES")],
     "which native API produces locale-aware relative times and which helper did it retire",
     "intl relative time format numeric auto yesterday humanize retire"),
    # --- 43 ---
    ("Unit formatting uses `Intl.NumberFormat` with `style: \"unit\"`; `1.5 km` versus `1,5 км` renders correctly for Russian with zero custom code in the distance widget.", "fact", "ai_coding", False,
     [("Intl.NumberFormat", "method"), ("unit", "config"), ("Russian", "language"), ("distance widget", "project")],
     [],
     "which native formatter handles unit-aware output like km across English and Russian",
     "intl numberformat style unit km russian distance widget locale"),
    # --- 44 ---
    ("Locale detection for logged-in users preferred-locale in the DB wins over Accept-Language; anonymous traffic falls back to geo-IP then to `en` if the header is unparseable.", "architecture", "ai_coding", False,
     [("preferred-locale", "config"), ("Accept-Language", "config"), ("geo-IP", "pattern"), ("en", "language")],
     [],
     "which locale detection precedence handles logged-in users versus anonymous traffic",
     "locale detection preferred accept language geo ip anonymous fallback en"),
    # --- 45 ---
    ("Message collisions in the monorepo land through a namespace-per-package rule; the extractor errors if two packages emit the same ID so catalogs never get silently overwritten.", "problem", "ai_coding", False,
     [("monorepo", "pattern"), ("extractor", "tool"), ("namespace", "pattern")],
     [],
     "which rule prevents silent message ID collisions across packages in the monorepo",
     "monorepo message id collision namespace package extractor error"),
    # --- 46 ---
    ("Right-to-left reviews land through a Playwright matrix that runs every route under `ar` and `he` locales; the screenshot diff gates PRs so layout regressions are caught before translators see them.", "architecture", "ai_coding", False,
     [("Playwright", "tool"), ("ar", "language"), ("he", "language")],
     [],
     "how does CI catch RTL layout regressions for Arabic and Hebrew before translation cycles",
     "rtl playwright matrix ar he screenshot diff gate pr regression"),
    # --- 47 ---
    ("Emoji and non-BMP plural keys survive the pipeline because every catalog step runs with `ensure_ascii=False`; a 2025 incident where JSON escaping mangled flag emoji taught us to pin the flag.", "problem", "ai_coding", False,
     [("ensure_ascii", "config"), ("non-BMP", "pattern"), ("JSON", "protocol")],
     [],
     "which JSON serialisation flag did we pin after flag emoji got mangled in catalog round-trips",
     "ensure ascii false non bmp flag emoji json escape catalog incident"),
    # --- 48 ---
    ("Translation memory leverage is tracked per release; Crowdin's TM match score feeds a Grafana panel so the i18n lead can see when a copy refactor nukes translator savings.", "preference", "ai_coding", False,
     [("Crowdin", "service"), ("Grafana", "tool"), ("Translation memory", "concept")],
     [("Crowdin", "Grafana", "COMMUNICATES_WITH")],
     "which metric does the i18n lead watch per release to spot copy refactors that destroy TM leverage",
     "translation memory leverage crowdin grafana panel release copy refactor"),
    # --- 49. noise ---
    ("A single orange pushpin has outlasted every other pin on the shared corkboard for three years running.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("The i18n README now points at a runnable `pnpm i18n:doctor` script that checks catalog parity, plural coverage, and ICU syntax in one pass; new contributors ran it successfully on day one.", "milestone", "ai_coding", False,
     [("pnpm", "tool"), ("i18n:doctor", "command"), ("README", "file"), ("ICU", "protocol")],
     [],
     "which single command do new contributors run to verify catalog parity, plurals, and ICU syntax",
     "pnpm i18n doctor script catalog parity plural icu syntax readme"),
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
