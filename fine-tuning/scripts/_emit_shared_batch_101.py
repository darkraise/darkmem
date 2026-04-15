"""One-off emitter for shared-base batch-101 — ai_coding domain (accessibility (a11y) as a coding practice: semantic HTML, ARIA, focus management, keyboard nav, screen-reader testing, CI a11y tooling, contrast, reduced motion, i18n overlap, accessible component libs, WCAG 2.1/2.2, EAA compliance).

Writes 50 rows to data/v2/shared/batch_101.tmp.jsonl with ids shared-05001..05050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_101.tmp.jsonl"
ID_OFFSET = 5000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Ripped out the div-soup navigation on the marketing site and rebuilt it as a single nav landmark with a ul; screen-reader rotor listings immediately showed every link under Navigation.", "milestone", "ai_coding", False,
     [("nav", "pattern"), ("ul", "pattern"), ("landmark", "pattern")],
     [("nav", "landmark", "IS_A")],
     "which semantic-HTML rewrite made the marketing nav show up in the screen-reader rotor",
     "semantic html nav landmark ul rotor screen reader marketing"),
    # --- 2 ---
    ("Adopted Radix Primitives for the dialog, popover, and menu widgets; the home-grown modal had been missing role=dialog and aria-modal and leaked focus to the page behind.", "decision", "ai_coding", False,
     [("Radix Primitives", "library"), ("dialog", "pattern"), ("aria-modal", "pattern"), ("role=dialog", "pattern")],
     [("Radix Primitives", "dialog", "REPLACES")],
     "which component library replaced the in-house modal after focus and ARIA bugs piled up",
     "radix primitives dialog popover menu modal aria focus leak"),
    # --- 3 ---
    ("React Aria now backs the combobox and listbox in the search header; the pile of aria-activedescendant, aria-expanded, and aria-controls attributes we had hand-wired is gone.", "decision", "ai_coding", False,
     [("React Aria", "library"), ("combobox", "pattern"), ("listbox", "pattern"), ("aria-activedescendant", "pattern")],
     [("React Aria", "aria-activedescendant", "IMPROVES_ON")],
     "which hook library took over combobox wiring so we stopped hand-writing ARIA attributes",
     "react aria combobox listbox aria activedescendant expanded controls"),
    # --- 4 ---
    ("Focus traps on every modal are implemented with focus-trap-react; the trap records the opener, moves focus to the first tabbable on open, and restores on close.", "architecture", "ai_coding", False,
     [("focus-trap-react", "library"), ("modal", "pattern"), ("tabbable", "pattern")],
     [("focus-trap-react", "modal", "APPLIES_TO")],
     "how does the SPA trap and restore focus around modals without leaking to the background page",
     "focus trap restore opener tabbable modal react library"),
    # --- 5 ---
    ("Keyboard-only QA pass found three dropdown menus that opened on hover but never on Enter or Space; they now respond to both pointer and keyboard activation and expose aria-haspopup.", "problem", "ai_coding", False,
     [("aria-haspopup", "pattern"), ("dropdown", "pattern"), ("Enter", "pattern"), ("Space", "pattern")],
     [],
     "which keyboard-activation gap did QA catch on the dropdown menus and how did we close it",
     "dropdown keyboard enter space hover aria haspopup activate"),
    # --- 6 ---
    ("Replaced manual NVDA-only spot checks in QA with jest-axe running on every component test; CI now fails on serious or critical axe-core violations before PR review.", "decision", "ai_coding", False,
     [("jest-axe", "tool"), ("NVDA", "tool"), ("axe-core", "tool")],
     [("jest-axe", "NVDA", "REPLACES")],
     "which automated a11y tool replaced manual NVDA spot checks as the CI gate for components",
     "jest axe nvda axe core component test ci gate violation"),
    # --- 7 ---
    ("Pa11y CI runs against the staging URL on every deploy and uploads the HTML report as an artefact; the threshold is set at zero errors and ten warnings, tightening each sprint.", "architecture", "ai_coding", False,
     [("Pa11y", "tool"), ("staging", "infrastructure"), ("HTML report", "pattern")],
     [],
     "which deploy-time tool scans the staging site for a11y issues and what thresholds does it enforce",
     "pa11y ci staging deploy html report threshold error warning"),
    # --- 8 ---
    ("Lighthouse-CI runs a mobile profile audit on every PR preview; the accessibility category must score 95 or higher or the workflow fails with a link to the failing audits.", "preference", "ai_coding", False,
     [("Lighthouse-CI", "tool"), ("PR preview", "infrastructure"), ("mobile", "platform")],
     [],
     "which lighthouse-based gate enforces an a11y score floor on every PR preview build",
     "lighthouse ci pr preview mobile accessibility score 95 gate"),
    # --- 9 ---
    ("Shipped a color token audit: every foreground-on-background pair is recomputed with WCAG contrast ratios in Storybook's a11y addon and any pair under 4.5:1 is flagged.", "milestone", "ai_coding", False,
     [("WCAG", "publication"), ("Storybook", "tool"), ("contrast", "concept")],
     [("Storybook", "WCAG", "IMPLEMENTS")],
     "how does the design system now police color-contrast regressions on every token change",
     "color contrast wcag 4.5 storybook addon audit token pair"),
    # --- 10. noise ---
    ("Someone left a half-eaten croissant on the printer again and nobody will admit to it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("All motion-heavy transitions check prefers-reduced-motion via matchMedia before running; the parallax hero falls back to a static image for users who opted out at the OS level.", "architecture", "ai_coding", False,
     [("prefers-reduced-motion", "config"), ("matchMedia", "method"), ("parallax", "pattern")],
     [],
     "how does the site honour user motion preferences on the parallax hero",
     "prefers reduced motion matchmedia parallax fallback static"),
    # --- 12 ---
    ("Changed every img without alt to either a meaningful alt string or alt=''; the eslint-plugin-jsx-a11y rule jsx-a11y/alt-text is set to error and gates PRs.", "preference", "ai_coding", False,
     [("eslint-plugin-jsx-a11y", "tool"), ("jsx-a11y/alt-text", "config"), ("alt", "pattern")],
     [],
     "which lint rule enforces meaningful or empty alt text on every img in the JSX codebase",
     "eslint jsx a11y alt text img rule gate pr empty meaningful"),
    # --- 13 ---
    ("The multi-step form now wraps each step in a fieldset with a legend and announces step changes via an aria-live=polite region; VoiceOver reads the new heading on navigation.", "architecture", "ai_coding", False,
     [("fieldset", "pattern"), ("legend", "pattern"), ("aria-live", "pattern"), ("VoiceOver", "tool")],
     [],
     "how does the multi-step form announce step transitions to screen-reader users",
     "fieldset legend aria live polite multi step form voiceover"),
    # --- 14 ---
    ("Adopted Headless UI on the settings pages for disclosure, tabs, and listbox; it ships the right keyboard behaviour out of the box and we stopped maintaining our own roving-tabindex code.", "decision", "ai_coding", False,
     [("Headless UI", "library"), ("disclosure", "pattern"), ("tabs", "pattern"), ("roving-tabindex", "pattern")],
     [("Headless UI", "roving-tabindex", "REPLACES")],
     "which headless library replaced the hand-rolled tabs and listbox on the settings pages",
     "headless ui disclosure tabs listbox roving tabindex keyboard"),
    # --- 15 ---
    ("Every custom icon button carries an aria-label because the only child is an SVG; Storybook's a11y addon catches missing labels at author time so they never reach review.", "fact", "ai_coding", False,
     [("aria-label", "pattern"), ("SVG", "technology"), ("Storybook", "tool")],
     [],
     "how do we make sure icon-only buttons always carry an accessible name for screen readers",
     "icon button aria label svg storybook author time catch"),
    # --- 16 ---
    ("Logical tab order is enforced by keeping DOM order equal to visual order; positive tabindex values are banned in the lint config because they routinely broke keyboard flow.", "preference", "ai_coding", False,
     [("tabindex", "pattern"), ("DOM order", "pattern"), ("lint", "tool")],
     [],
     "which tabindex rule of thumb does the codebase enforce to keep keyboard navigation predictable",
     "tabindex positive ban dom visual order keyboard flow lint"),
    # --- 17 ---
    ("The modal's Escape-to-close and outside-click-to-close paths also restore focus to the opener button; regression tests assert document.activeElement after close using testing-library.", "architecture", "ai_coding", False,
     [("Escape", "pattern"), ("document.activeElement", "api"), ("testing-library", "tool")],
     [],
     "how does the modal guarantee focus restoration after Escape or outside-click close",
     "escape close modal focus restore opener active element test"),
    # --- 18 ---
    ("WCAG 2.2 is now the conformance target; the new 2.2 success criteria on Focus Not Obscured, Dragging Movements, and Target Size got dedicated component-level acceptance checks.", "decision", "ai_coding", False,
     [("WCAG 2.2", "publication"), ("Focus Not Obscured", "pattern"), ("Target Size", "pattern")],
     [("WCAG 2.2", "Focus Not Obscured", "HAS_PART")],
     "which new WCAG conformance target did we pick and which fresh criteria got acceptance checks",
     "wcag 2.2 focus not obscured dragging target size criteria"),
    # --- 19 ---
    ("Moved the official conformance target from WCAG 2.1 AA to WCAG 2.2 AA across all product surfaces; the audit checklist and VPAT both got rewritten against the newer spec.", "milestone", "ai_coding", False,
     [("WCAG 2.1", "publication"), ("WCAG 2.2", "publication"), ("VPAT", "concept")],
     [("WCAG 2.2", "WCAG 2.1", "REPLACES")],
     "which WCAG version did the organisation bump to as its conformance target and where is it tracked",
     "wcag 2.1 2.2 aa conformance vpat audit checklist rewrite"),
    # --- 20 ---
    ("The EAA compliance project kicked off on 2026-02-10 with a gap analysis against EN 301 549; every product surface got a named accessibility owner and a dated remediation plan.", "milestone", "ai_coding", False,
     [("EAA", "publication"), ("EN 301 549", "publication"), ("2026-02-10", "date")],
     [("EAA", "EN 301 549", "RELATED_TO")],
     "when did the EAA compliance programme start and which standard did the gap analysis cite",
     "eaa european accessibility act en 301 549 gap analysis owner"),
    # --- 21 ---
    ("RTL support ships via the dir attribute on html and logical CSS properties like padding-inline-start; hard-coded left and right values in the design tokens were all replaced.", "architecture", "ai_coding", False,
     [("dir", "pattern"), ("padding-inline-start", "config"), ("RTL", "concept")],
     [("padding-inline-start", "dir", "SUPPORTS")],
     "how does the design system support right-to-left languages without branching stylesheets",
     "rtl dir logical property padding inline start token replace"),
    # --- 22 ---
    ("Every page now sets lang on the html element and marks inline language shifts with lang on spans; screen readers switch voices correctly on the English bios inside the German press page.", "fact", "ai_coding", False,
     [("lang", "pattern"), ("html", "pattern"), ("span", "pattern")],
     [],
     "which language-attribute practice lets screen readers switch voices on mixed-language pages",
     "lang attribute html span inline shift voice switch screen reader"),
    # --- 23 ---
    ("A skip-link at the top of every template jumps to #main-content; the link is visible on focus and the target carries tabindex='-1' so it takes focus without appearing in tab order.", "architecture", "ai_coding", False,
     [("skip-link", "pattern"), ("#main-content", "config"), ("tabindex", "pattern")],
     [],
     "how does the skip-link pattern land focus on main content without polluting tab order",
     "skip link main content focus visible tabindex minus one target"),
    # --- 24 ---
    ("The data grid switched from a bespoke keyboard handler to React Aria's useGrid; arrow-key navigation, Home and End, and type-ahead all follow the APG authoring practices without extra code.", "decision", "ai_coding", False,
     [("React Aria", "library"), ("useGrid", "method"), ("APG", "publication")],
     [("React Aria", "APG", "IMPLEMENTS")],
     "which hook took over grid keyboard handling and which authoring-practice guide does it follow",
     "react aria use grid keyboard apg arrow home end type ahead"),
    # --- 25 ---
    ("JAWS on Windows is the primary screen reader for QA regression; NVDA is the secondary and VoiceOver on macOS covers the Safari path for release smoke.", "preference", "ai_coding", False,
     [("JAWS", "tool"), ("NVDA", "tool"), ("VoiceOver", "tool"), ("Safari", "platform")],
     [],
     "which screen readers does QA drive on which operating systems for each release",
     "jaws nvda voiceover windows macos safari screen reader qa"),
    # --- 26 ---
    ("TalkBack on Android and VoiceOver on iOS are part of the mobile regression sweep; the QA script covers landing, signup, checkout, and account on both platforms each sprint.", "architecture", "ai_coding", False,
     [("TalkBack", "tool"), ("VoiceOver", "tool"), ("Android", "platform"), ("iOS", "platform")],
     [],
     "how does the mobile QA sweep cover Android and iOS screen readers across the funnel",
     "talkback voiceover android ios mobile regression sweep script"),
    # --- 27 ---
    ("Form inputs pair each label with its control by htmlFor and id; placeholder-as-label was ripped out after a usability test showed the hint vanished as soon as users typed.", "problem", "ai_coding", False,
     [("htmlFor", "pattern"), ("placeholder", "pattern"), ("label", "pattern")],
     [("htmlFor", "placeholder", "REPLACES")],
     "which label pattern replaced placeholder-as-label after the usability test caught the problem",
     "label htmlfor id placeholder usability test hint vanish input"),
    # --- 28 ---
    ("Error messages on form fields use aria-describedby pointing at a live region; invalid inputs also carry aria-invalid=true so assistive tech announces both the state and the reason.", "architecture", "ai_coding", False,
     [("aria-describedby", "pattern"), ("aria-invalid", "pattern"), ("live region", "pattern")],
     [],
     "how does the form surface validation errors to screen-reader users alongside visual callouts",
     "aria describedby invalid live region form error announce"),
    # --- 29 ---
    ("Replaced every custom click-on-div with a real button or anchor; keyboard users regained Enter and Space activation and focus rings came back for free from the UA stylesheet.", "problem", "ai_coding", False,
     [("button", "pattern"), ("anchor", "pattern"), ("div", "pattern")],
     [("button", "div", "REPLACES")],
     "which blanket refactor replaced click-on-div handlers with real interactive elements",
     "button anchor div click keyboard enter space focus ring"),
    # --- 30 ---
    ("The live chat widget's new-message announcement uses aria-live=polite on a visually hidden region; busy queues previously clobbered each other because assertive was firing interrupt storms.", "problem", "ai_coding", False,
     [("aria-live", "pattern"), ("polite", "pattern"), ("assertive", "pattern"), ("live chat", "project")],
     [("polite", "assertive", "REPLACES")],
     "which aria-live politeness setting did live chat settle on and why not assertive",
     "aria live polite assertive chat announce busy interrupt storm"),
    # --- 31 ---
    ("Headings are now a strict single-h1-per-document with sequential h2 and h3 underneath; the previous stylistic h4-only hierarchy broke the rotor's heading list for blind users.", "problem", "ai_coding", False,
     [("h1", "pattern"), ("h2", "pattern"), ("h3", "pattern"), ("rotor", "pattern")],
     [],
     "which heading-hierarchy rule did the team adopt after the rotor list showed up broken",
     "heading h1 h2 h3 rotor blind reader hierarchy sequential"),
    # --- 32 ---
    ("Focus ring is enforced via :focus-visible with a custom outline token; the global outline:none reset that the design team had shipped in 2022 was banned in the lint rules.", "decision", "ai_coding", False,
     [(":focus-visible", "pattern"), ("outline:none", "pattern"), ("lint", "tool")],
     [(":focus-visible", "outline:none", "IMPROVES_ON")],
     "which CSS primitive brought visible focus back after a 2022 reset nuked every outline",
     "focus visible outline none reset lint ring token css"),
    # --- 33 ---
    ("Color is never the sole carrier of meaning; status pills now pair the hue with an icon and a text label so the red warning reads as Warning even without color perception.", "fact", "ai_coding", False,
     [("status pills", "pattern"), ("icon", "pattern"), ("color", "concept")],
     [],
     "which design rule stops status from relying on color alone across the component set",
     "color meaning icon label status pill red warning perception"),
    # --- 34 ---
    ("Touch targets meet WCAG 2.2's 24-by-24 CSS pixel minimum everywhere; icon buttons that looked fine at 16px got padded via a hit-area pseudo-element without resizing the glyph.", "architecture", "ai_coding", False,
     [("WCAG 2.2", "publication"), ("hit-area", "pattern"), ("icon buttons", "pattern")],
     [],
     "how did we hit the WCAG 2.2 target-size minimum on icon buttons without resizing the glyphs",
     "touch target 24 css pixel hit area icon button pseudo"),
    # --- 35 ---
    ("The cookie banner was rewritten so the accept and decline buttons have equal visual weight and reachable focus order; dark-pattern reviews flagged the prior version for EAA risk.", "problem", "ai_coding", False,
     [("cookie banner", "pattern"), ("EAA", "publication"), ("dark-pattern", "concept")],
     [],
     "which consent-UI rewrite closed an EAA dark-pattern risk on the cookie banner",
     "cookie banner accept decline equal weight focus order eaa"),
    # --- 36 ---
    ("The video player ships with captions by default, an audio-description track for key marketing spots, and a transcript link below the frame; WCAG 1.2.3 and WCAG 1.2.5 are both covered.", "architecture", "ai_coding", False,
     [("WCAG 1.2.3", "publication"), ("WCAG 1.2.5", "publication"), ("captions", "pattern"), ("transcript", "pattern")],
     [],
     "which media-accessibility criteria does the video player cover and how",
     "video caption audio description transcript wcag 1.2.3 1.2.5"),
    # --- 37 ---
    ("Charts render with a visually hidden data table as the fallback; screen-reader users navigate the table while sighted users see the SVG, and the underlying dataset is the same.", "architecture", "ai_coding", False,
     [("SVG", "technology"), ("data table", "pattern"), ("visually hidden", "pattern")],
     [],
     "how do charts stay accessible to screen-reader users without dumbing down the visual",
     "chart svg visually hidden data table fallback screen reader"),
    # --- 38 ---
    ("Introduced aria-current='page' on the active nav link; the CSS-only 'is-active' class had no semantic signal and users with screen readers couldn't tell which page they were on.", "problem", "ai_coding", False,
     [("aria-current", "pattern"), ("is-active", "pattern"), ("nav", "pattern")],
     [("aria-current", "is-active", "IMPROVES_ON")],
     "which ARIA attribute signals the active navigation item to assistive tech",
     "aria current page active nav link is active class screen"),
    # --- 39 ---
    ("Async loading states announce via an aria-live=polite status region; spinners alone were invisible to JAWS so users didn't know the dashboard was still fetching.", "problem", "ai_coding", False,
     [("aria-live", "pattern"), ("status", "pattern"), ("JAWS", "tool"), ("spinner", "pattern")],
     [],
     "how did the dashboard make async loading states audible to JAWS users",
     "aria live status polite spinner jaws loading announce"),
    # --- 40 ---
    ("Wrote custom axe-core rules for the design-system primitives; the rules catch class-based dialog markup without role=dialog so nobody reinvents an inaccessible modal.", "milestone", "ai_coding", False,
     [("axe-core", "tool"), ("design-system", "project"), ("role=dialog", "pattern")],
     [],
     "which custom linting move catches design-system primitives missing their ARIA roles",
     "axe core custom rule design system dialog role class detect"),
    # --- 41 ---
    ("The sign-in flow now passes Playwright a11y tests driven by @axe-core/playwright; the suite runs headless with a reduced-motion media query forced on to catch motion-dependent UI bugs.", "architecture", "ai_coding", False,
     [("Playwright", "tool"), ("@axe-core/playwright", "library"), ("reduced-motion", "pattern")],
     [],
     "which end-to-end a11y harness covers the sign-in flow and how does it catch motion issues",
     "playwright axe core reduced motion sign in end to end a11y"),
    # --- 42 ---
    ("The autocomplete attributes now match WCAG 1.3.5 tokens on the checkout form; shipping and billing fields carry cc-name, cc-number, postal-code, and friends so password managers and AT behave.", "fact", "ai_coding", False,
     [("autocomplete", "pattern"), ("WCAG 1.3.5", "publication"), ("cc-number", "pattern"), ("postal-code", "pattern")],
     [],
     "which WCAG criterion drove the autocomplete-token cleanup on checkout fields",
     "autocomplete wcag 1.3.5 cc number postal code checkout form"),
    # --- 43 ---
    ("Reference baseline for ARIA is the WAI-ARIA 1.2 spec plus the ARIA Authoring Practices Guide; component docs link the matching APG pattern for every widget we ship.", "reference", "ai_coding", False,
     [("WAI-ARIA 1.2", "publication"), ("APG", "publication")],
     [("APG", "WAI-ARIA 1.2", "BUILDS_ON")],
     "which ARIA spec and authoring-practice doc do component docs cite as the baseline",
     "wai aria 1.2 apg authoring practice widget pattern reference"),
    # --- 44 ---
    ("Shipped a visually-hidden utility class using the clip-path zero-sized inset trick; it replaced the older display:none-on-mobile pattern that also hid content from screen readers.", "architecture", "ai_coding", False,
     [("visually-hidden", "pattern"), ("clip-path", "config"), ("display:none", "pattern")],
     [("clip-path", "display:none", "REPLACES")],
     "which CSS technique did the visually-hidden utility switch to and why it matters for AT",
     "visually hidden clip path display none screen reader utility"),
    # --- 45 ---
    ("Language toggle persists via a cookie and rewrites the lang attribute plus the dir attribute server-side; client-side-only toggles used to leave the html tag stale for AT until reload.", "problem", "ai_coding", False,
     [("lang", "pattern"), ("dir", "pattern"), ("cookie", "pattern"), ("html", "pattern")],
     [],
     "which language-toggle refactor stopped leaving a stale html lang attribute for assistive tech",
     "language toggle cookie server lang dir html stale assistive"),
    # --- 46 ---
    ("Hover-only tooltips were replaced with focus-and-hover tooltips using WAI-ARIA APG's tooltip pattern; keyboard users and touch users now see the same supporting text.", "problem", "ai_coding", False,
     [("tooltip", "pattern"), ("APG", "publication"), ("focus", "pattern")],
     [("APG", "tooltip", "APPLIES_TO")],
     "which tooltip pattern did we adopt so keyboard and touch users get the same hint",
     "tooltip hover focus keyboard touch apg pattern support text"),
    # --- 47 ---
    ("The animated CAPTCHA got swapped for an accessible alternative that combines a honeypot with a Cloudflare Turnstile challenge; the old image-only CAPTCHA failed WCAG 1.1.1 outright.", "decision", "ai_coding", False,
     [("CAPTCHA", "pattern"), ("Cloudflare Turnstile", "service"), ("WCAG 1.1.1", "publication")],
     [("Cloudflare Turnstile", "CAPTCHA", "REPLACES")],
     "which CAPTCHA replacement closed the WCAG 1.1.1 gap on the signup form",
     "captcha cloudflare turnstile honeypot wcag 1.1.1 signup swap"),
    # --- 48 ---
    ("The VPAT got regenerated from a Conformance Report generator driven by our test-suite output; each criterion cites the passing suite and file so auditors can trace the claim.", "architecture", "ai_coding", False,
     [("VPAT", "concept"), ("Conformance Report", "publication"), ("test-suite", "pattern")],
     [],
     "how is the VPAT generated now and what makes each criterion independently verifiable",
     "vpat conformance report generator test suite criterion trace"),
    # --- 49. noise ---
    ("The coffee-machine filter light blinks in a pattern suspiciously close to morse code for help.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Accessibility acceptance criteria are now part of every feature ticket template; the reviewer checklist cites WCAG 2.2 AA and EN 301 549 sections so PRs can't land without coverage.", "preference", "ai_coding", False,
     [("WCAG 2.2", "publication"), ("EN 301 549", "publication"), ("ticket template", "pattern")],
     [("EN 301 549", "WCAG 2.2", "BUILDS_ON")],
     "how are a11y acceptance criteria enforced at the ticket and PR review level now",
     "accessibility acceptance criteria ticket template wcag 2.2 en 301 549"),
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
