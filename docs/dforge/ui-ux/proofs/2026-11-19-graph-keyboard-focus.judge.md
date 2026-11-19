## Verdict
verdict: ship 002efcbdac9135e3
scores: coverage 18 / fidelity 17 / states 16 / deviations 17

Third round. I opened all 14 crops under ui-1-*, the ux-1 to ux-5 boards at both viewport/theme pairs, ui-2-open and ui-2-closing (1280x800 dark), both walk JSON files, both focus-anim JSON files, panel-change.diff, deployed-image.txt, the two scripts, both cited test files and the two changed source files. Every round-two dispute is resolved by evidence I could open.

## Coverage

Every Delta item (UX-1 to UX-5, UI-1, UI-2, OP-1) has a Results row whose evidence exists and shows that item.

- UX-1: both walk JSON files show Tab after "Show details panel" going to "Open chat panel" (h 40), then body (the end of the document), then "Skip to content". No content filter, "Any tag" or tag checkbox stop. Test "keeps the collapsed panel's controls out of the tab order..." (real-memory-graph-page.test.tsx:162) asserts the panel is inert when collapsed and not inert once Filters opens it. That test only proves the attribute; the live walk proves the Tab order. The row's "Before: ... 0 px" sentence rests on an earlier walk that is not in this evidence folder. It is context, not a claim the item depends on.
- UX-2: ux-2 boards (both) show "Any tag" focused with the panel open and visible. The JSON gives "Filter by content…" then "Any tag", 32 px each, and "Open chat panel" after the panel closes again.
- UX-3: the JSON walk is Node limit through Reset graph view, with the panel still open afterwards. The ux-3 boards show Reset ringed and the panel open. The test at graph-toolbar.test.tsx:50 covers the same edge.
- UX-4: JSON gives Shift+Tab from Reset to "Dim unrelated nodes, percent", Tab from the trigger to "Node limit", Shift+Tab from the first control to "Toggle graph settings", panel open. Three tests (lines 62, 72, 82) cover the three directions. The ux-4 boards show the trigger ringed with the panel open.
- UX-5: JSON gives focus on "Toggle graph settings" and the panel closed after Escape. The ux-5 boards show that. The in-panel Tab order is evidenced by the walk and the test at line 91. The "unchanged from 2026-11-18" comparison cannot be checked against a prior file here, but the order itself is shown.
- UI-1: all six landing points the change creates (Reset after Tab out, Dim after Shift+Tab from Reset, Node limit after Tab from the trigger, trigger after Shift+Tab, Open chat panel after Show details with filters collapsed, Filter by content… with filters open) have a crop at both pairs. Each also has focused and blurred style reads from focus-anim-*.json. In all 12 entries `focusVisible` is true and `ringDiffers` is true. This closes round two's UI-1 dispute.
- UI-2: panel-change.diff shows the className line (scale-y, opacity, transition-all duration-200 ease-out) as unchanged context, plus a comment and `inert={!filters.showFilters}`. I confirmed the current source at real-memory-graph-page.tsx:406-409 matches. The sampled counts in the report match the JSON exactly: 132 open at both pairs, 186 closing dark, 161 closing light. Scale and opacity ramp through intermediate values, and `inertAtEnd` is false after opening and true after closing. This closes round two's count dispute.
- OP-1: deployed-image.txt ties image id 289328138e85 to `latest`, built at f2cd2d25 (the log names both tags in one export). The tag file is thin, since it gives no container name and no in-image grep. The live walks behave as only the fixed code would (Tab from the trigger enters the open panel), which corroborates that the running page has the change. Both pairs have walk and focus-anim JSON.

## Fidelity

- The rings I saw in the crops come from the existing design-system focus style, with no new tokens.
  - Buttons and sliders: a solid 2 px outline (dark rgb(187,247,208), light rgb(22,167,75)).
  - The two inputs: a 3 px green box-shadow plus a green border.
- The Open chat panel crops show the ring around the green button, visible in both themes. The Node limit and content-filter crops show a clear green border. The light content-filter ring is the faintest of the set, but it is still distinct from the pale blurred border (rgb(226,238,228) against rgb(27,161,76)).
- The ux boards show no dropped or substituted elements. The settings panel in the ux-3 boards is scrolled so its top row is clipped. That follows from focus scrolling the panel's own overflow area, not from the change.
- The ux-1 boards end with focus on "Skip to content", which is not visible in the screenshot. The walk's `h: 37` and `ring: true` cover it. It is not a landing point this change creates.

## States

- Keyboard-only walk: evidenced live at 1280x800 dark and 1920x1080 light for all six landing points, and by six toolbar and page tests.
- Collapsed and open filter panel: both are shown on the boards (ux-1, ux-2) and sampled through both transitions.
- Error and loading data states are outside this touch's Delta.
- Coverage is the diagonal pairs only: dark at 1280x800 and light at 1920x1080. The report header lists both viewports and both themes, but OP-1 states the two pairs explicitly, so I did not dispute it. The 1280x800 light and 1920x1080 dark pairs are unshown (a minor limit; this is why states is 16, not higher).
- Mid-transition frames are shown only as computed samples. The ui-2-closing screenshot was taken after the panel had already closed, so it adds nothing beyond the JSON. The report does not cite it as mid-frame evidence.
- The report also records axe (0 violations), no console or page errors, no overflow and no production writes in both walk files.

## Deviations

- The report marks no row as a deviation and I found none.
  - The walk's `body` stop in UX-1 is the browser leaving the document, which the row describes as "the end of the document".
  - The changed Tab routing is the accessibility fix the contract asks for.
- The walk's `ring` flag, which round two found too weak, is explicitly marked as superseded by the style reads and crops.

## Disputed items

None.

Verdict: ship 002efcbdac9135e3
