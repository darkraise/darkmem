## Verdict
verdict: ship b2c54fce74dbe1b8
scores: coverage 18 / fidelity 17 / states 15 / deviations 18

Re-judged at fingerprint b2c54fce74dbe1b8 (the proof header carries it). Every round-3 finding is answered by code, evidence or an honest restatement. I found no false claim and no unproven item. The remaining findings are low and are wording or disclosure points that do not need another round.

## What changed since the round-3 fix verdict
Read from code, tests and PNGs, not from the report's summary.

- `island-labels.ts`: `islandLabelAlpha(hasSelection)` now takes one argument and returns 0.35 or 1. Zoom and Regions no longer hide names. The test "keeps names at full strength unless something is selected" matches.
- `placeIslandLabels` takes `viewport.top` (default 0). y is clamped to `[top + h/2, height - h/2]`, and `fits` requires `b.y - h/2 >= top`. `near` still bounds every candidate to the island's radius, so a name that would need a position past its radius is dropped.
- `graph-2d-renderer.tsx`: `TOOLBAR_BAND_PX = 48` is passed as `top`. The toolbar is `top-3` with `h-8` buttons, so it ends at 44 px. The filter button is `top-3 left-3 h-8` (real-memory-graph-page.tsx:330-336), also ending at 44 px. The top-centre "Updating graph" badge is `top-3` with `py-1.5 text-sm`, about 32 px tall. The 48 px band covers all three. The bottom-centre warning badge is 3D-only.
- `drawIslandLabels` calls `islandLabelAlpha(selectedNodeIdRef.current !== null)`. `hullModeRef` is still used elsewhere (chips), and `LABEL_ZOOM_RATIO` is still used for hub labels and chips, so nothing is orphaned.
- `memory-size.ts` line 11 now reads "among the memories the filters keep".
- The default size mode is `importance` (`DEFAULT_SIZE_MODE`), so the live captures do exercise the rank-by-importance mapping the proof describes.
- All four final run JSONs record `base: 127.0.0.1:3636`, `errors: []`, `blocked: 0`, `overflow: false`. The before run records `:8000` and `-1` label counts. before-image.txt line 1 equals the e3f67821 and `latest` tags, and e3f67821 is HEAD.

## Round-3 findings, one by one

1. **Regions on and zoomed: names hidden for chips that are off screen. Answered by code and evidence.**
   - Names are never hidden now. In final-regions-zoomed-1280x800-dark.png I count nine names (Gate Failures, Translation Eval, CodeDisplay, File Replace, UI Framework, DST Asset Manifest, App Zoom, Arcuz, Rendering Bugs). The "File Replace Retry Failures · 90" chip is cut by the header and its name is on screen. The "darkraise-framework …" chip is cut by the right edge and CodeDisplay's name is on screen.
   - final-regions-zoomed-1920x1080-light.png also shows nine names.
   - The label-layer pixel counts in the proof (22,618 / 22,626 / 22,641 / 22,634) equal `labelsRegionsZoomed` in the four JSONs. The Regions-off zoomed counts (2,889 / 2,897 / 2,886 / 2,885) equal `labelsZoomed`.
   - Two islands whose centres lie above the canvas stay unnamed in that capture. I see their partial hulls at the top (about x 460-600 at 1280 dark, and x 640-900 and x 1720-1780 at 1920 light). The proof states this in the UI-1 note, and it follows from the "within the island's radius" rule.
   - Duplication of names and chips is not hidden. Decisions says a cluster "can show both its chip (with the member count) and its name", and UX-1 says "beside the region chips". The zoomed captures show exactly that.

2. **"At any canvas width": answered.** The Delta now says "from about 700 px wide (the 1280x800 page with the detail panel open) up". The panel-open canvas is 960 - 256 = 704 px, so this is accurate. A name wider than the canvas is dropped, and the Delta says so. Captured canvas widths are 704, 1024 and 1664 px. Calling "700 and up" proven is a small generalisation but fair.

3. **`memory-size.ts` "in view" comment: answered.**

4. **Names under the toolbar or over a neighbouring hull: answered.**
   - Toolbar: the band is in code, pinned by "keeps a name out of the toolbar band at the top of the canvas" (centre 30 clamps to a top edge of exactly 48; with radius 24 the name is dropped, as 28.5 > 24). In the regions-zoomed captures "darkraise-modder Translation Eval" sits at page y 113, which is the band edge (56 + 48 = 104, minus half a label height). That shows the pull-down working, though the proof does not cite it as such.
   - Neighbouring hull: Decisions now says "Its text can run across a neighbouring island or hull". final-regions-1920x1080-light.png shows it (App Zoom against the UI Framework hull edge, CodeDisplay past its own hull).
   - The chat button at the bottom-right is stated as not avoided and not captured. This is honest.

5. **3D labels unlisted: answered.** "Not proven here" now says the 3D renderer gets no island names and keeps `computeNodeVal`.

6. **"About 21" should be about 22: answered.** 10 + 36 · 0.5^1.6 = 21.9. Decisions says "about 22" for the flat view. See finding 3 below for a small residue.

## New findings, graded by what each breaks

1. **Low: `TOOLBAR_BAND_PX = 48` is a constant coupled to Tailwind classes in another file (`top-3`, `h-8`).** Its comment names the coupling, but no test or shared constant ties them. The toolbar's own comment warns that "an offset picked to clear one is a number that rots". Today 44 px of toolbar against a 48 px band is correct. It breaks only if the toolbar grows, and then names pass under the buttons without any test failing.

2. **Low: the Delta still says "4.5 times the radius" for what is the size attribute.** Round 3 suggested "size attribute". "On a fixture" and the Results note ("the glow program's density pass scales each role's discs by one factor, so ratios within a role hold") cover it. "Drawn 2.5 to 11.5" is also in sigma size units, not pixels. The numbers themselves are right. I recomputed 4.52 for 0.8 against 0.4 and 3.37 for 0.7 against 0.5 from the fixture, and `MEMORY_SIZE_SCALE = 0.25` gives 2.5 to 11.5.

3. **Low: two small wording leftovers on numbers.**
   - The memory-size.test.ts fixture comment still says "importance 0.4 to 0.8". The corpus has 0.3 to 0.9, six memories in total (importance-distribution.txt). The fixture rounds that to 100, so this is harmless.
   - Decisions says "a median memory lands near size 22". 22 is the flat-view value (percentile 0.5). In the test fixture the median-importance (0.6) block lands at about 21.0, because its mid-rank percentile is 0.475.

4. **Low: UI-4 in the dark fit view is subtle.** final-default-1920x1080-dark.png shows modest size variation, and final-crop-dark.png against before-crop-dark.png shows it clearly only in the crop. The proof says the glow softens it in the dark fit view and shows it clearly in light mode and zoomed in. That is disclosed. It is the weakest part against the owner's "more obvious", and it is not misreported.

5. **Low: the band-edge pull-down evidence is not cited.** The UI-1 note lists earlier builds' failures and the unnamed islands, but it does not name the capture where a name sits at the band edge (the Translation Eval name in the regions-zoomed captures). No capture shows a name beside the toolbar buttons horizontally. The band makes that case impossible by construction (names stay below y 48), so I count this as evidence tidy-up only.

6. **Info: the work is uncommitted and undeployed.** `git status` shows the renderer, `graph-utils.ts`, both acceptance tests and the new lib files as modified or untracked. `graph.jpg` is also untracked at the repo root. The proof does not claim a deploy, and it states that the gate is BLOCKED on the missing bench cache. Per CLAUDE.md the host redeploy is owed once this lands. The before capture is the HEAD image, so it is a valid baseline.

## Per item
- **UI-1: covered.** Eleven named islands in the default captures at both viewports and themes (opened 1280 light, 1920 dark), in Regions-on (1280 dark, 1920 light) and in the 1280 selected pair. CodeDisplay sits at the panel edge, named. Zoomed Regions-on shows nine names, and the two unnamed islands are disclosed.
- **UI-2: covered.** I traced the overlap and above/below/drop tests by hand against the code (the big, small and far case; the a, b, c, d crowd). They hold. No overlap in any capture I opened. The ellipsis cut is 40 characters, as tested.
- **UI-3: covered.** Names read in both themes. The proof discloses the dots showing through gaps in light mode. final-crop-light.png shows it.
- **UX-1: covered.** Names persist at zoom with Regions off (final-zoomed 1280 light and 1920 dark, one island, clamped at the right edge) and with Regions on. The 0.35 opacity in the selected captures is pinned by the test and visible in them.
- **UI-4: covered.** Rank mapping, curve, numbers and tests are mutually consistent. I hand-computed the memory-size test thresholds: areas 1.26, 3.45, 3.29 and 1.43 against thresholds 1.2, 2, 2 and 1.2, and 10.04 and 45.4 at the ends.
- **OP-1: covered.** The five JSONs agree with the proof. The harness blocks every non-read request, as `sel.mjs` shows, and its pixel counter reads the `sigma-islandLabels` canvas.

## Disputed
None.

## Could not confirm
- I ran no test, typecheck, build, ui-lint or eslint. The counts (307 files, 2,461 tests; 5 eslint errors and 1 warning, all pre-existing and moved by added constants) are the proof's own. I traced the island-label and memory-size tests by hand and expect them to pass.
- I did not open every PNG. Opened: final-default 1280 light and 1920 dark, final-selected 1280 dark and light, final-zoomed 1280 light and 1920 dark, final-regions 1280 dark and 1920 light, final-regions-zoomed 1280 dark and 1920 light, final-hover 1920 dark, final-crop dark and light, before-crop-dark. Not opened: the 1920 selected, 1280 hover, selected-hovered and 1920 regions dark captures, the remaining before captures, and final-regions-1280x800-light.
- The claim that the island canvas paints below sigma's labels and hovers rests on `beforeLayer: "labels"` in code. The hover capture shows a hover tag clear of any name, so it does not test the layering.
- That a session was minted inside the production container, and the stated eslint line numbers, are not checkable from the files.
- The `document.fonts` width-cache clear path was not exercised, and the proof says so.
- The 1,000-memory default view's own importance distribution was not checked against the whole-corpus figures. The proof says the figures are whole-corpus.

Verdict: ship b2c54fce74dbe1b8
