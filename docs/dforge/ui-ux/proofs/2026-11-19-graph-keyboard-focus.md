# UI proof: memory graph keyboard focus

**Contract:** touch
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local
**Fingerprint:** 002efcbdac9135e3
**Judge:** ship 002efcbdac9135e3 — docs/dforge/ui-ux/proofs/2026-11-19-graph-keyboard-focus.judge.md

## Delta

**UI/UX depth:** touch — register rows #12 and #13 of `docs/dforge/registers/2026-11-18-constellation-real-data.md`: focus entering the collapsed filter panel, and focus leaving the settings panel to `<body>`

- **UX-1** — With the filter panel collapsed, Tab after "Show details panel" never lands on its content filter, "Any tag" or a tag checkbox.
- **UX-2** — With the filter panel open, its controls are reachable by Tab and visible; collapsing it removes them from the Tab order again.
- **UX-3** — In the open settings panel, Tab past its last control ("Dim unrelated nodes, percent") moves focus to "Reset graph view", and the panel stays open.
- **UX-4** — Shift+Tab from the panel's first control returns to "Toggle graph settings"; with the panel open, Tab from the trigger enters its first control and Shift+Tab from "Reset graph view" enters its last, as if the panel sat right after its trigger.
- **UX-5** — Escape inside the panel still closes it and returns focus to the trigger, and the Tab order within the panel is unchanged.
- **UI-1** — Every control focus lands on carries a visible focus ring.
- **UI-2** — The filter panel's open and close animation is unchanged (the hiding classes are untouched; `inert` is added beside them).
- **OP-1** — Proven on the live page (deployed image `f2cd2d25`, cloned 192.168.0.199 corpus) at 1280x800 dark and 1920x1080 light.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UX-1 | pass | .dforge/ui-ux/graph-keyboard-focus/ux-1-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ux-1-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/walk-1280x800-dark.json, .dforge/ui-ux/graph-keyboard-focus/walk-1920x1080-light.json; test "keeps the collapsed panel's controls out of the tab order until Filters opens it" | Tab after "Show details panel" goes to "Open chat panel" (40 px), then the end of the document; no 0 px stop. Before: content filter, "Any tag", a tag checkbox, each 0 px high. |
| UX-2 | pass | .dforge/ui-ux/graph-keyboard-focus/ux-2-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ux-2-1920x1080-light.png, walk JSON "UX-2" keys | Open: "Filter by content…" then "Any tag", 32 px each. Closed again: Tab goes to "Open chat panel". |
| UX-3 | pass | .dforge/ui-ux/graph-keyboard-focus/ux-3-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ux-3-1920x1080-light.png, walk JSON "UX-3" keys; test "Tab past the panel's last control moves to the next toolbar button and leaves the panel open" | Walk: Node limit > All nodes > 2D > Cluster > None > Weight > Entity layer > Edge similarity threshold > Minimum cluster size > Accent > Dim unrelated nodes, percent > Reset graph view; panel open after leaving it. |
| UX-4 | pass | .dforge/ui-ux/graph-keyboard-focus/ux-4-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ux-4-1920x1080-light.png, walk JSON "UX-4" keys; tests "Shift+Tab from the panel's first control returns to the settings trigger", "Tab from the trigger enters the open panel at its first control", "Shift+Tab from the next toolbar button returns to the open panel's last control" | Shift+Tab from Reset: Dim unrelated nodes. Tab from trigger: Node limit. Shift+Tab from Node limit: trigger. The trigger and Reset halves were added after the first live walk showed the open panel could be skipped from the trigger. |
| UX-5 | pass | .dforge/ui-ux/graph-keyboard-focus/ux-5-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ux-5-1920x1080-light.png, walk JSON "UX-5" key; test "Tab between the panel's own controls stays in the panel" | Escape from Node limit closes the panel and focuses "Toggle graph settings"; the in-panel order matches the 2026-11-18 walk. |
| UI-1 | pass | .dforge/ui-ux/graph-keyboard-focus/ui-1-reset-after-tab-out-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-reset-after-tab-out-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-dim-after-shift-tab-from-reset-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-dim-after-shift-tab-from-reset-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-first-control-after-tab-from-trigger-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-first-control-after-tab-from-trigger-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-trigger-after-shift-tab-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-trigger-after-shift-tab-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-chat-after-show-details-filters-collapsed-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-chat-after-show-details-filters-collapsed-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-content-filter-after-show-details-filters-open-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-1-content-filter-after-show-details-filters-open-1920x1080-light.png, .dforge/ui-ux/graph-keyboard-focus/focus-anim-1280x800-dark.json, .dforge/ui-ux/graph-keyboard-focus/focus-anim-1920x1080-light.json | Every landing point this change creates, each reached by keyboard: Reset graph view after Tab out of the panel, Dim after Shift+Tab from Reset, Node limit after Tab from the trigger, the trigger after Shift+Tab, Open chat panel after Tab from Show details panel with filters collapsed, and Filter by content… after Tab from Show details panel with filters open. Each matches `:focus-visible`; its style is read 300 ms after focus and again 300 ms after blur, over the element and three ancestors. Focused: a solid 2 px outline (dark rgb(187,247,208), light rgb(22,167,75)), or on the two inputs a 3 px green box-shadow ring (Node limit draws it on its number-input wrapper, plus a green border). Blurred: outline none, no ring. Each crop shows the ring. The walk JSON's `ring` flag is superseded by these reads. |
| UI-2 | pass | .dforge/ui-ux/graph-keyboard-focus/panel-change.diff, .dforge/ui-ux/graph-keyboard-focus/focus-anim-1280x800-dark.json, .dforge/ui-ux/graph-keyboard-focus/focus-anim-1920x1080-light.json, .dforge/ui-ux/graph-keyboard-focus/ui-2-open-1280x800-dark.png, .dforge/ui-ux/graph-keyboard-focus/ui-2-open-1920x1080-light.png | `panel-change.diff` (the full `git show 9127019c` of the page) adds two lines, a comment and `inert={!filters.showFilters}`; the className line with scale-y, opacity and `transition-all duration-200 ease-out` is context, unchanged. Computed `scale` and `opacity` sampled through each transition (132 samples opening, 161 to 186 closing, over 320 ms) still ramp: dark open 0.00 > 0.43 > 0.69 > 0.83 > 0.90 > 0.95 > 0.97 > 0.99 > 1.00, close 1.00 > 0.57 > 0.17 > 0.10 > 0.05 > 0.01 > 0.00. The panel is `inert` only once closed. |
| OP-1 | pass | .dforge/ui-ux/graph-keyboard-focus/deployed-image.txt, both walk and focus-anim JSON files | 1280x800 dark and 1920x1080 light. `deployed-image.txt`: the running container's image id 289328138e85 is `darkraise/darkmem:latest`, built from `f2cd2d25` (the build log names `latest` and `f2cd2d25` in the same export; the sha tag was later untagged locally). |

## Automated checks

- **axe** (axe-core 4.11.4), live page after the walk: 0 violations at 1280x800 dark and at 1920x1080 light.
- **Page errors / console errors:** 0 in both runs.
- **Writes attempted against production:** 0. Every non-GET request was routed to abort, and none occurred.
- **Horizontal overflow:** none in either run.
- **Tests:** `npm test` 304 files, 2465 tests pass at `f2cd2d25`; `tsc -b` clean; `npm run build` passes. Mutation checks: removing the halo `glowOnly` filter, the `inert` attribute's effect (red before the fix), the edge check in the panel handler, and the Shift-key guard on the toolbar handler each fail a test.
- **Gate:** `./scripts/gate.sh` reported `GATE BLOCKED` (exit 2, extraction-bench cache missing since the 2026-10-08 re-clone); the change is frontend-only, so its frontend legs were run individually as above.
