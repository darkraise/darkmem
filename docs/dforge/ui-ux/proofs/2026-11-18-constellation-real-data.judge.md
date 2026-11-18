## Verdict
verdict: fix 5502e386a9073533
scores: coverage 12 / fidelity 12 / states 13 / deviations 11

## What was opened

- Criteria `criteria/ui-ux-proof.md`, the contract (spec "## UI/UX contract" plus Architecture and Acceptance), and the proof report.
- The reference image `graph.jpg`.
- These boards: default-1000 (1280 and 1920 dark, 1920 light), entity-layer 1280 dark plus the UI-2 white crop, high-edges 1280 dark, small-200 1280 dark, all 1920 dark, ui-5 hover 1280 dark, ui-5 zoomed 1280 dark and 1920 light, selected 1920 dark, the OP-5 before/after pairs for code worst-2000 (1280 dark) and code mixed (1920 light), the keyboard capture, and the previous proof's live capture `.playwright-mcp/constellation-real-data/live-default-1280x800-dark.png`.
- Every other cited file exists in `.dforge/ui-ux/constellation-real-data/`.
- I grepped `frontend/src/features/graph` for the cited test names. The A1–A5 and A9–A14 tests the report names are present (`constellation-layout.test.ts`, `real-corpus-roles.test.ts`, `hubs.test.ts`, `graph-prefs.test.ts`, `real-corpus-fixture.test.ts`, `constellation-graphs.acceptance.test.tsx`, `constellation-real-data.acceptance.test.tsx`). I did not run them, so the pass counts and the A14 timings are the report's own figures.

## Criterion notes

**Every Item Has Evidence (12).** Most UI and UX items have evidence I opened that shows them.
- OP-1, OP-2's live half and acceptance items A15–A18 have no evidence for this branch. The only live capture is from the old build (image `6042f0d7`): four large colour wedges, zoomed in, with labels on most nodes.
- No row carries an `**Accepted by:**` line, so these items are unproven, not accepted.
- A18 (the boards match the live page) cannot be shown at all.

**Built Matches Promised (12).** On the memory-only boards (Default1000, Small200, HighEdges, All), dark theme, the contract's arrangement is visible: a multi-coloured core with a soft, irregular edge, tiny clumps, and a faint halo thinning outward. Zooming in restores full size and brightness, with hub labels only. Light theme shows crisp, saturated points.

Three things break the promise:
- **Entity layer saturates.** With the entity layer on, the board sums to white. The crop shows white-centred cyan glows and white-washed diamond outlines. This breaks UI-2's "never sum to white at the fit view".
- **Core is pale on All.** On All at 1920 dark, the core centre is pale and near-white pink. It stays under the report's 250 threshold, but it reads close to saturation.
- **Not yet read against the reference.** Against `graph.jpg`, the core is drawn as merged glowing blobs, where the reference shows crisp, interleaved points. The clumps are specks, not visible groups. A faint web of rest edges crosses the halo. The contract's own test of the look is OP-1 against `graph.jpg`, and that test has not passed.

**Every State Is Shown (13).** All UX-5 matrix rows are captured at both viewports and in both themes on the boards.
- Hover, zoomed and selected states are captured, and the WebGL-unavailable state and reduced motion are covered by tests.
- The entity-layer state is shown, but it fails UI-2.
- No state is shown on the live page.
- The keyboard walk covers only the bare Storybook board, which has no focusable control. The page's own controls (the Edges slider, the node limit and the entity toggle) were never walked by keyboard on this branch, even though a local dev frontend could have served them.

**Deviations Are Cited (11).** The report lists three differences from `graph.jpg` under UI-1 (discs instead of crisp points, speck clumps, the rest-edge web) and still marks UI-1 pass.
- None of the three cites an owner answer, a profile decision or an accessibility need.
- The light-theme rest-edge mesh, which competes with the points, is waved off as "outside this contract", with no decision cited.
- The spec says `localSpacing` uses the densest 5% of nodes, but the code uses 2%. The report flags this but cites no decision, and the spec was not corrected.

## Disputed items

- UI-2: The entity-layer board measures 173 white pixels at 1280x800 and 101 at 1920x1080 at the fit view. The crop `ui-2-entity-layer-white-crop-1280x800-dark.png` shows white-centred glows under the diamonds. The density control does not hold with the entity layer on, which is a state named in UX-5. (The report itself marks this fail.)
- OP-1: The only live capture (`live-default-1280x800-dark.png`) is the old build: four large colour wedges, zoomed in, with labels on most nodes. It does not read as `graph.jpg`. The branch is not deployed, so the live default view has not been shown.
- OP-2: The board half is met (24 captures). The live half has no capture of this branch at either viewport or in either theme, and no light-theme live capture exists at all.
- UI-1: The boards show the promised core, clumps and halo, but the report itself lists three uncited differences from the reference: blob-like cores, speck clumps and a rest-edge web. The reference is the contract's stated target. These differences are marked pass instead of being recorded as deviations with a cited decision.

## What it takes to ship

1. Keep entity diamonds out of the core and satellite density measurement, or otherwise keep the glow under the coverage target with the entity layer on. Then show the EntityLayer board at 0 white pixels at both viewports.
2. Deploy the branch. Capture the live page at both viewports and in both themes, at 1,000, all, 200, Edges 0.8 and with the entity layer on, beside `graph.jpg` (A15–A18).
3. Either record the owner's acceptance of the UI-1 differences from the reference and the light-theme edge mesh, or fix them.
4. Make the spec and the code agree on the `localSpacing` percentile (5% in the spec, 2% in the code).
5. Walk the page's controls by keyboard on the deployed build.

Verdict: fix 5502e386a9073533
