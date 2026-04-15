"""One-off emitter for shared-base batch-131 — ai_coding domain (CSS architecture / design systems / token pipelines / component libraries).

Writes 50 rows to data/v2/shared/batch_131.tmp.jsonl with ids shared-06501..06550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_131.tmp.jsonl"
ID_OFFSET = 6500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the marketing site from Tailwind CSS v3 to Tailwind CSS v4; the new CSS-first config lives in @theme blocks and the old tailwind.config.js got deleted alongside the postcss.config.js shim.", "milestone", "ai_coding", False,
     [("Tailwind CSS v3", "library"), ("Tailwind CSS v4", "library"), ("@theme", "pattern"), ("tailwind.config.js", "file"), ("postcss.config.js", "file")],
     [("Tailwind CSS v4", "Tailwind CSS v3", "IMPROVES_ON")],
     "which Tailwind upgrade landed on the marketing site and what configuration moved out of JavaScript",
     "tailwind v4 upgrade css first theme block config delete postcss"),
    # --- 2 ---
    ("Dropped Emotion in favour of vanilla-extract across the checkout UI; static extraction gives us zero-runtime CSS and the bundle shrank by 38 kilobytes gzipped.", "decision", "ai_coding", False,
     [("Emotion", "library"), ("vanilla-extract", "library"), ("checkout UI", "project")],
     [("vanilla-extract", "Emotion", "REPLACES")],
     "which CSS-in-JS swap shrank the checkout UI bundle and why did static extraction matter",
     "vanilla extract replace emotion static css zero runtime checkout"),
    # --- 3 ---
    ("shadcn/ui replaced Material UI as the component substrate; copy-paste ownership of Radix-backed primitives gave the design team room to ship brand tokens without fighting MUI's theme runtime.", "decision", "ai_coding", False,
     [("shadcn/ui", "library"), ("Material UI", "library"), ("Radix", "library")],
     [("shadcn/ui", "Material UI", "REPLACES"), ("shadcn/ui", "Radix", "USES")],
     "which component library swap gave the design team ownership over brand tokens without a theme runtime",
     "shadcn ui replace material mui radix primitive copy paste theme"),
    # --- 4 ---
    ("Style Dictionary builds the token pipeline; JSON source files under tokens/ transform into CSS custom properties, Swift enums, and Android XML in one pnpm run.", "architecture", "ai_coding", False,
     [("Style Dictionary", "tool"), ("tokens/", "file"), ("CSS custom properties", "pattern")],
     [("Style Dictionary", "CSS custom properties", "PRODUCES")],
     "how does the token pipeline turn a single JSON source into web, iOS, and Android outputs",
     "style dictionary token json css variable swift android build"),
    # --- 5 ---
    ("Design tokens now ship from Figma through Tokens Studio into a Git repo; the PR bot opens a tokens-update PR nightly and Style Dictionary regenerates the platform outputs on merge.", "architecture", "ai_coding", False,
     [("Figma", "tool"), ("Tokens Studio", "tool"), ("Style Dictionary", "tool")],
     [("Tokens Studio", "Figma", "USES")],
     "which tooling chain moves design tokens from Figma to code and how do updates land in the repo",
     "figma tokens studio git pr style dictionary nightly pipeline"),
    # --- 6 ---
    ("Replaced Headless UI with Radix Primitives across the dashboard; better keyboard semantics on the popover and the Portal primitive solved the z-index stacking mess that Tailwind alone couldn't fix.", "decision", "ai_coding", False,
     [("Headless UI", "library"), ("Radix Primitives", "library"), ("Portal", "pattern"), ("Tailwind", "library")],
     [("Radix Primitives", "Headless UI", "REPLACES")],
     "why did the dashboard team swap Headless UI for Radix Primitives and what concrete problem did it solve",
     "radix primitives replace headless ui portal z index popover"),
    # --- 7 ---
    ("Panda CSS landed as the zero-runtime CSS-in-JS for the new admin app; the recipes API expresses variants cleanly and the build emits static atomic classes with no client JS cost.", "architecture", "ai_coding", False,
     [("Panda CSS", "library"), ("recipes", "pattern"), ("admin app", "project")],
     [],
     "which CSS-in-JS solution did the new admin app pick and what does its recipes API replace",
     "panda css recipes zero runtime atomic class admin app variant"),
    # --- 8 ---
    ("BEM naming is frozen for the legacy marketing templates; new work uses Tailwind utilities instead, but touching a .block__element--modifier file requires keeping the existing convention for diff clarity.", "preference", "ai_coding", False,
     [("BEM", "pattern"), ("Tailwind", "library"), ("marketing templates", "project")],
     [],
     "what is the policy on BEM naming across legacy versus new CSS work",
     "bem block element modifier legacy template tailwind new work"),
    # --- 9 ---
    ("CSS container queries replaced the JS-driven ResizeObserver layout dance in the product card grid; the card shuffles between stacked and side-by-side based on its own inline-size, not the viewport.", "milestone", "ai_coding", False,
     [("container queries", "pattern"), ("ResizeObserver", "api"), ("product card", "project")],
     [("container queries", "ResizeObserver", "REPLACES")],
     "which CSS feature killed a ResizeObserver-based layout hack in the product card grid",
     "container query inline size product card resize observer replace"),
    # --- 10. noise ---
    ("The little paper crane on the standing desk survived another office move, which nobody expected.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("CSS cascade layers organise the global sheet into reset, tokens, primitives, components, and overrides; Tailwind utilities sit in their own layer above components so authors can stop writing !important.", "architecture", "ai_coding", False,
     [("cascade layers", "pattern"), ("Tailwind", "library"), ("!important", "pattern")],
     [],
     "how do cascade layers arrange the global stylesheet and why do they remove !important from authored CSS",
     "cascade layer reset token primitive component override tailwind"),
    # --- 12 ---
    ("Tailwind preflight got selectively overridden in the email-editor workspace; the contenteditable surface needs native list bullets and heading margins back, so the workspace imports a scoped restore sheet.", "fact", "ai_coding", False,
     [("Tailwind preflight", "pattern"), ("contenteditable", "api"), ("email-editor", "project")],
     [],
     "how did the email editor restore native heading and list styling without globally disabling Tailwind preflight",
     "tailwind preflight override contenteditable email editor restore"),
    # --- 13 ---
    ("Storybook 8 runs under the Vite builder with composition pulling in the packages/ui stories; the old Webpack config was a 20-second cold-start tax that Vite shaves to under three.", "milestone", "ai_coding", False,
     [("Storybook 8", "tool"), ("Vite", "tool"), ("Webpack", "tool"), ("packages/ui", "file")],
     [("Vite", "Webpack", "REPLACES")],
     "which Storybook builder swap cut cold-start time and how much faster did it get",
     "storybook 8 vite builder webpack cold start composition ui"),
    # --- 14 ---
    ("Ladle replaced Storybook in the mobile-web package; startup latency on a low-end laptop was blocking contributor PRs and Ladle's ESM-first story format loads fast enough to unblock them.", "decision", "ai_coding", False,
     [("Ladle", "tool"), ("Storybook", "tool"), ("mobile-web", "project")],
     [("Ladle", "Storybook", "REPLACES")],
     "why did the mobile-web package drop Storybook for Ladle and what contributor pain did it fix",
     "ladle replace storybook mobile web esm startup contributor"),
    # --- 15 ---
    ("Chromatic guards visual regressions on the design-system package; every PR uploads a build and the diff UI blocks merges when a token change ripples into unexpected component screenshots.", "architecture", "ai_coding", False,
     [("Chromatic", "tool"), ("design-system", "project")],
     [("Chromatic", "design-system", "APPLIES_TO")],
     "which visual-regression service guards the design-system package and what does it block on",
     "chromatic visual regression design system pr diff token ripple"),
    # --- 16 ---
    ("Loki runs local visual regression against a Percy-free Storybook; each PR pins a reference snapshot set and the Docker-driven Chrome shot matches what Chromatic does without the subscription.", "decision", "ai_coding", False,
     [("Loki", "tool"), ("Percy", "tool"), ("Chromatic", "tool"), ("Storybook", "tool")],
     [("Loki", "Percy", "REPLACES")],
     "which self-hosted visual-regression tool stood in for Percy in the Storybook workflow",
     "loki percy storybook visual regression local docker chrome"),
    # --- 17 ---
    ("Dark mode uses a data-theme attribute on the root element plus CSS custom properties; a single prefers-color-scheme media query hydrates the initial value and the theme toggle then writes to localStorage.", "architecture", "ai_coding", False,
     [("data-theme", "pattern"), ("CSS custom properties", "pattern"), ("prefers-color-scheme", "pattern"), ("localStorage", "api")],
     [],
     "which dark-mode architecture did we settle on and how does initial value hydration work",
     "dark mode data theme attribute custom property prefers color"),
    # --- 18 ---
    ("Theme switching avoids a flash of unstyled theme by inlining a blocking pre-hydration script that reads localStorage and sets data-theme before the stylesheet parses.", "problem", "ai_coding", False,
     [("data-theme", "pattern"), ("localStorage", "api"), ("pre-hydration script", "pattern")],
     [],
     "how does the theme system prevent a flash of incorrect theme on first paint",
     "theme flash pre hydration script local storage data theme inline"),
    # --- 19 ---
    ("Stitches is on the deprecation list; the README now directs readers to Panda CSS for new work, since Stitches stopped receiving releases after late 2023.", "reference", "ai_coding", False,
     [("Stitches", "library"), ("Panda CSS", "library")],
     [("Panda CSS", "Stitches", "REPLACES")],
     "which CSS-in-JS library is being sunset in favour of Panda CSS and why",
     "stitches deprecation panda css replacement maintenance sunset"),
    # --- 20 ---
    ("linaria lives in the email-template package because the runtime there is a Node worker rendering HTML strings; linaria's build-time extraction produces plain CSS the worker can inline without a browser.", "architecture", "ai_coding", False,
     [("linaria", "library"), ("email-template", "project"), ("Node", "platform")],
     [],
     "why does the email-template package use linaria specifically instead of a runtime CSS-in-JS library",
     "linaria email template node worker build time extract css"),
    # --- 21 ---
    ("CSS Modules are the default for the marketing monolith; the team didn't want a runtime and BEM-style naming collisions had become a daily review headache before modules arrived.", "decision", "ai_coding", False,
     [("CSS Modules", "pattern"), ("BEM", "pattern"), ("marketing monolith", "project")],
     [("CSS Modules", "BEM", "REPLACES")],
     "which styling approach is the marketing monolith standard and what naming problem did it fix",
     "css modules default marketing monolith bem naming collision"),
    # --- 22 ---
    ("Chakra UI got deprecated in the internal tools bundle; Mantine landed as the replacement because its form hooks and data-table component cut the amount of custom glue we were writing by half.", "decision", "ai_coding", False,
     [("Chakra UI", "library"), ("Mantine", "library"), ("internal tools", "project")],
     [("Mantine", "Chakra UI", "REPLACES")],
     "which component library replaced Chakra UI in the internal tools bundle and why",
     "mantine replace chakra internal tool form hook data table"),
    # --- 23 ---
    ("Ark UI powers the framework-agnostic primitives behind the Vue 3 admin and the React marketing site; one state machine per component means both apps get identical keyboard semantics.", "architecture", "ai_coding", False,
     [("Ark UI", "library"), ("Vue 3", "framework"), ("React", "framework")],
     [("Ark UI", "Vue 3", "APPLIES_TO"), ("Ark UI", "React", "APPLIES_TO")],
     "which primitive library gives the Vue admin and React marketing site the same keyboard semantics",
     "ark ui primitive vue react state machine keyboard parity"),
    # --- 24 ---
    ("Bits UI is the Svelte team's Radix equivalent; the Svelte 5 rewrite of the public pricing page uses Bits UI's dialog and dropdown to match the Radix-based main app exactly.", "fact", "ai_coding", False,
     [("Bits UI", "library"), ("Svelte 5", "framework"), ("Radix", "library"), ("pricing page", "project")],
     [],
     "which primitives library did the Svelte 5 pricing page pick and how does it stay consistent with Radix",
     "bits ui svelte 5 radix parity dialog dropdown pricing"),
    # --- 25 ---
    ("The Material design system reference sits in docs/design/material-reference.md; we borrow elevation tokens verbatim but reject the ripple effect because the brand team considers it off-voice.", "reference", "ai_coding", False,
     [("Material", "concept"), ("elevation tokens", "pattern"), ("ripple", "pattern"), ("docs/design/material-reference.md", "file")],
     [],
     "which parts of Material do we borrow and which ones do we reject in the house design language",
     "material design reference elevation ripple brand voice"),
    # --- 26 ---
    ("IBM's Carbon design system donates its grid breakpoints to our tokens file; the numeric scale (sm=320, md=672, lg=1056, xl=1312, max=1584) maps cleanly to our Tailwind screens config.", "reference", "ai_coding", False,
     [("Carbon", "concept"), ("Tailwind", "library"), ("tokens file", "file")],
     [("tokens file", "Carbon", "USES")],
     "which external design system contributes the breakpoint scale in our tokens file",
     "carbon grid breakpoint token tailwind screen scale ibm"),
    # --- 27 ---
    ("Fluent 2 is the inspiration for the surface elevation model on the desktop client; the specific depth values are ours but the acrylic-versus-mica decision framework came directly from Fluent's guidance.", "reference", "ai_coding", False,
     [("Fluent 2", "concept"), ("desktop client", "project"), ("acrylic", "pattern"), ("mica", "pattern")],
     [],
     "which design system informs the surface elevation decisions on the desktop client",
     "fluent 2 elevation surface desktop acrylic mica guidance"),
    # --- 28 ---
    ("Atlassian's design system is cited in the confluence-plugin package; the link button variants and the focus-ring treatment match Atlassian's tokens so the plugin feels native inside the host app.", "architecture", "ai_coding", False,
     [("Atlassian", "organization"), ("confluence-plugin", "project"), ("focus-ring", "pattern")],
     [],
     "why does the confluence-plugin package align with Atlassian's token choices rather than our house system",
     "atlassian design system confluence plugin focus ring native"),
    # --- 29 ---
    ("The @apply directive debate settled in favour of banning it in application code; component authors either write CSS Module classes or inline utilities, and @apply stays only inside the design-system package's base layer.", "decision", "ai_coding", False,
     [("@apply", "pattern"), ("CSS Module", "pattern"), ("design-system", "project")],
     [],
     "what is the policy on Tailwind @apply across application code versus the design-system package",
     "apply directive ban application code design system base"),
    # --- 30 ---
    ("Theo is no longer a token build option; Style Dictionary has absorbed Theo's role since Salesforce archived the repo in 2022, and the migration guide lives in docs/design/theo-migration.md.", "reference", "ai_coding", False,
     [("Theo", "tool"), ("Style Dictionary", "tool"), ("docs/design/theo-migration.md", "file")],
     [("Style Dictionary", "Theo", "REPLACES")],
     "which archived Salesforce tool did Style Dictionary supersede in our token pipeline",
     "theo salesforce archive style dictionary migration guide"),
    # --- 31 ---
    ("Knapsack hosts the public documentation site for the shared design system; each MDX page embeds a live Storybook iframe, so API docs and interactive demos stay in the same URL.", "architecture", "ai_coding", False,
     [("Knapsack", "tool"), ("MDX", "technology"), ("Storybook", "tool")],
     [("Knapsack", "Storybook", "USES")],
     "which platform hosts the public design-system docs and how do live component demos embed there",
     "knapsack design system docs mdx storybook iframe embed"),
    # --- 32 ---
    ("The utility-first CSS camp won the internal debate for the app shell; the semantic CSS faction survives only where marketing SEO content needs named hooks, since Tailwind's HTML-as-source-of-truth fit the component review flow better.", "decision", "ai_coding", False,
     [("utility-first", "pattern"), ("semantic CSS", "pattern"), ("Tailwind", "library"), ("app shell", "project")],
     [("utility-first", "semantic CSS", "PREFERS")],
     "how did the app shell resolve the utility-first versus semantic CSS debate",
     "utility first semantic css tailwind app shell debate decision"),
    # --- 33 ---
    ("Playwright traces now capture the full rendered DOM plus computed styles on a failed snapshot test; the trace viewer replaced a screenshot-only workflow that couldn't explain layout regressions.", "milestone", "ai_coding", False,
     [("Playwright", "tool"), ("trace viewer", "tool")],
     [("Playwright", "trace viewer", "USES")],
     "which debugging upgrade made layout regressions easier to triage in visual tests",
     "playwright trace viewer dom computed style layout regression"),
    # --- 34 ---
    ("Design tokens are versioned through Changesets; a semver-major token rename forces a migration codemod published in the same PR, so downstream apps don't hit silent colour drift.", "architecture", "ai_coding", False,
     [("Changesets", "tool"), ("semver", "concept"), ("codemod", "pattern")],
     [],
     "how do design-token breaking changes propagate to downstream apps without silent drift",
     "token semver changeset codemod rename major migration ship"),
    # --- 35 ---
    ("Picked Stitches over styled-components back in 2022; we're now unwinding that choice in favour of vanilla-extract, so the historical ADR is the reference for why we moved and why we're moving again.", "reference", "ai_coding", False,
     [("Stitches", "library"), ("styled-components", "library"), ("vanilla-extract", "library")],
     [("Stitches", "styled-components", "REPLACES"), ("vanilla-extract", "Stitches", "REPLACES")],
     "what is the historical trail of CSS-in-JS choices we've made and where does the rationale live",
     "stitches styled components vanilla extract adr history"),
    # --- 36 ---
    ("The tokens-as-code stance means the JSON source is the single owner of every brand colour; Figma Variables sync through the nightly bot, and any code reviewer who sees a hex literal in a PR rejects it.", "preference", "ai_coding", False,
     [("tokens-as-code", "concept"), ("Figma Variables", "tool"), ("JSON", "technology")],
     [],
     "what does tokens-as-code mean in this repo and how is it enforced during code review",
     "tokens as code json source figma variable review reject hex"),
    # --- 37 ---
    ("Storybook docs addon renders a live props table straight off the TypeScript types; the prop-types PropDoc legacy path got removed since every component in packages/ui is typed at the source.", "milestone", "ai_coding", False,
     [("Storybook", "tool"), ("TypeScript", "technology"), ("packages/ui", "file")],
     [],
     "how does the Storybook docs addon build the live props table for every component",
     "storybook docs addon props table typescript packages ui"),
    # --- 38 ---
    ("CSS reset moved from normalize.css to modern-normalize plus a small house reset layer; the layered approach keeps the reset auditable and removes form-control styles the design-system intentionally overrides.", "decision", "ai_coding", False,
     [("normalize.css", "library"), ("modern-normalize", "library"), ("design-system", "project")],
     [("modern-normalize", "normalize.css", "REPLACES")],
     "which CSS reset stack replaced normalize.css and what did the layered approach clean up",
     "modern normalize replace reset layer form control override"),
    # --- 39 ---
    ("The design-token JSON contract pins colour values in OKLCH; the Style Dictionary build emits sRGB fallbacks for Safari 15 but writes the OKLCH original into a @supports (color: oklch(0 0 0)) block.", "architecture", "ai_coding", False,
     [("OKLCH", "pattern"), ("sRGB", "pattern"), ("Style Dictionary", "tool"), ("Safari 15", "platform")],
     [],
     "which colour space does the design-token contract use and how is Safari 15 handled",
     "oklch token srgb fallback safari 15 supports at rule"),
    # --- 40 ---
    ("The container queries and cascade layers features get a guarded polyfill only on the self-serve signup flow where analytics still show a Safari 15 long tail; the admin apps drop the polyfill entirely.", "fact", "ai_coding", False,
     [("container queries", "pattern"), ("cascade layers", "pattern"), ("Safari 15", "platform"), ("self-serve signup", "project")],
     [],
     "which CSS features carry a polyfill only on the self-serve signup flow and why",
     "container query cascade layer polyfill safari 15 signup admin"),
    # --- 41 ---
    ("styled-components v6 is pinned in the legacy reporting app because an unfixed server-side rendering regression hit any v6.1 build; the package carries a comment explaining the pin stays until upstream ships the fix.", "problem", "ai_coding", False,
     [("styled-components v6", "library"), ("reporting app", "project")],
     [],
     "why is styled-components pinned in the reporting app and what unblocks removing the pin",
     "styled components v6 pin legacy reporting ssr regression upstream"),
    # --- 42 ---
    ("Kept vanilla-extract and Tailwind on the same page via a vanilla-extract recipe that composes Tailwind class strings; the hybrid keeps static extraction while letting page authors stay in Tailwind's mental model.", "architecture", "ai_coding", False,
     [("vanilla-extract", "library"), ("Tailwind", "library"), ("recipe", "pattern")],
     [],
     "how do vanilla-extract and Tailwind coexist on the same page without a styling turf war",
     "vanilla extract tailwind recipe compose class hybrid static"),
    # --- 43 ---
    ("Every component in packages/ui exports a cva-based variants definition; cva plus tailwind-merge gives type-safe class combos that survive downstream Tailwind rules without specificity surprises.", "architecture", "ai_coding", False,
     [("packages/ui", "file"), ("cva", "library"), ("tailwind-merge", "library"), ("Tailwind", "library")],
     [("cva", "Tailwind", "USES"), ("tailwind-merge", "Tailwind", "USES")],
     "which two utilities back the variants API inside packages/ui and what do they solve together",
     "cva tailwind merge variant packages ui type safe class"),
    # --- 44 ---
    ("Focus-ring treatment standardised on outline plus outline-offset with the focus-visible pseudo-class; the old box-shadow trick survived years of Safari quirks but broke Windows High Contrast mode.", "problem", "ai_coding", False,
     [("focus-visible", "pattern"), ("outline-offset", "pattern"), ("box-shadow", "pattern"), ("Windows High Contrast", "platform")],
     [("outline-offset", "box-shadow", "REPLACES")],
     "which focus-ring technique replaced the box-shadow hack and what accessibility mode broke the old one",
     "focus visible outline offset box shadow high contrast windows"),
    # --- 45 ---
    ("Radix Primitives got wrapped with a house theme in packages/ui; the raw Primitives stay accessible under /unstyled for escape-hatch cases where a prototype needs to diverge from the brand.", "architecture", "ai_coding", False,
     [("Radix Primitives", "library"), ("packages/ui", "file"), ("prototype", "concept")],
     [],
     "how does packages/ui expose both the themed and unstyled Radix Primitives for divergent prototypes",
     "radix primitive packages ui theme unstyled escape hatch brand"),
    # --- 46 ---
    ("Mantine's hooks package ships without CSS to the hooks-only consumers; the tree-shaken import path drops 110 kilobytes from the marketing bundle where the visual components are not used.", "fact", "ai_coding", False,
     [("Mantine", "library"), ("hooks package", "pattern"), ("marketing bundle", "project")],
     [],
     "how does importing only Mantine's hooks package avoid shipping visual component CSS to the marketing bundle",
     "mantine hook tree shake marketing bundle css drop"),
    # --- 47 ---
    ("Wrote a custom Style Dictionary transform that emits a CSS @property registration for every animatable token; browsers that support @property get typed interpolation for gradients, and the rest fall back to discrete swaps.", "architecture", "ai_coding", False,
     [("Style Dictionary", "tool"), ("@property", "pattern"), ("gradients", "pattern")],
     [("Style Dictionary", "@property", "PRODUCES")],
     "which Style Dictionary transform made gradient interpolation work across capable browsers",
     "style dictionary at property transform gradient interpolation"),
    # --- 48 ---
    ("Headless UI stays in the marketing monolith for now; migrating it to Radix is on the backlog but the marketing templates are stable enough that the swap cost outweighs the benefit this quarter.", "reference", "ai_coding", False,
     [("Headless UI", "library"), ("Radix", "library"), ("marketing monolith", "project")],
     [],
     "what is the current position on migrating Headless UI to Radix inside the marketing monolith",
     "headless ui radix marketing monolith backlog defer quarter"),
    # --- 49. noise ---
    ("Somebody left a half-finished crossword in the kitchen and the 12-down clue has started a small territorial dispute.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Component documentation lives alongside the code in .mdx files; Storybook autodocs picks them up and the Knapsack site mirrors the same source, so the docs never drift from the shipped component.", "preference", "ai_coding", False,
     [("Storybook", "tool"), ("Knapsack", "tool"), (".mdx", "file")],
     [("Knapsack", "Storybook", "USES")],
     "how does component documentation stay in sync between Storybook and the public Knapsack site",
     "component docs mdx storybook autodocs knapsack mirror sync"),
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
