## Verdict
verdict: ship 1b80fcaade5ed8da
scores: coverage 17 / fidelity 16 / states 17 / deviations 15

## What was opened

- The criteria file, the contract (UI/UX contract, Architecture §1–11, Acceptance A1–A23), the proof report at fingerprint 1b80fcaade5ed8da (including the "Second round, e5cb25e0" paragraph), and `graph.jpg`.
- **Round 1, still standing at c04859e0:**
  - Live: default at 1280 and 1920 dark and 1920 light, both A15 side-by-sides, all, entity layer and high Edges at 1920 dark, light high Edges at 1920, small 200 and high Edges at 1280 dark, hover at 1280 dark and 1920 light, the label-layer capture, and the keyboard captures.
  - Boards: default-1000 and all at 1920 dark, selected at 1920 dark, ui-5 hover at 1280 dark, ui-5 zoomed at 1920 light.
  - The OP-5 before/after pairs and the previous build's noise capture.
- **Round 2, new or changed:**
  - `board-entity-layer-1280x800-dark.png`, `board-entity-layer-1920x1080-dark.png` and `board-entity-layer-1920x1080-light.png`; `board-entity-layer-1280x800-light.png` exists.
  - `board-entity-layer-all-1280x800-dark.png`.
  - `live/live-entity-layer-e5cb25e0-1280x800-dark.png`.
  - `op5-load1/op-5-board-code--worst-2000-1280x800-dark.png`. The other five `op5-load1/` files and the four `prev-c04859e0/` captures exist.
- **Code:** `real-corpus-board.stories.tsx` and `use-graph-filters.ts`.
  - The board now filters with the exported `entityVisible(e, memoryIds, sharedEntitiesOnly)`, defaulting to shared only. The page's hook calls the same function (line 103).
  - `EntityLayerAll` passes `sharedEntitiesOnly: false`.
- **Tests:** I read the A20, A21, A9, A10 and A22 tests and confirmed the A3, A11, A12, A14 and A23 test names by grep. I ran none of them, so the counts and timings are the report's own figures.

## Round-1 disputed item

- **A18 / UX-5 (entity layer): resolved.**
  - The EntityLayer board now draws the page's default entity set, through the same `entityVisible` call the page uses. At both viewports and in both themes, its diamonds ride on the core and sit in the clumps and halo without covering the core.
  - Its density matches the live entity-layer captures at c04859e0 and at e5cb25e0.
  - The unfiltered state is kept as its own board (`EntityLayerAll`), and the report describes it as the "Shared"-off state.
  - No capture shows white saturation.

## Criterion notes

**Every Item Has Evidence (17).** Every UI, UX and OP item has a row whose evidence I opened, and the evidence shows that item.
- **OP-5 noise:** both loads of the code boards are now on disk. `op5-load1`'s worst-2000 core is about as bright as the top-level load, which supports the claim that the between-build differences are load-to-load noise.
- **Remaining gaps:**
  - The keyboard walk covers 1280 dark and 1920 light only.
  - The UX-3 storage readback has no capture; the A11 tests cover it.

**Built Matches Promised (16).** The live default reads as `graph.jpg`'s arrangement: a multi-coloured core of crisp, separate points, small scattered clumps, a sparse, cluster-tinted halo thinning outward, and no white saturation.
- **Live states:** all, 200 and Edges 0.8 hold that arrangement, and the entity layer matches between board and page.
- **Light theme:** crisp points, a pale halo, and faint rest edges behind the core.
- **Labels:** only on hover or selection at the fit view; only hubs once zoomed in.
- **Code canvas:** unchanged within load noise.
- **One note, not a dispute:** the core's lobes are near-hexagonal lattices that end abruptly. The edge is irregular, but its softness comes only from the background glow. UI-1 says "soft, irregular edge". The lattice is the consequence of A22 and §5 (`CORE_GAP`), which the contract itself specifies.

**Every State Is Shown (17).** Every row of the UX-5 matrix is shown on the boards and live, at both viewports and in both themes.
- The entity layer is now shown in its default and unfiltered forms.
- Hover, selection, zoom and twinkle are captured.
- The WebGL-unavailable state, reduced motion and the canvas keys are covered by tests.
- The page controls were walked by keyboard on the deployed build.

**Deviations Are Cited (15).** The four remaining differences from `graph.jpg` are recorded. They are colour lobes, the lattice texture, a sparser halo with a smaller core share, and small clumps. Each is argued against OP-1's "exact positions and colours may differ" and the contract's UI-1/UI-2/A22 wording.
- Colour placement and clump size fall within OP-1.
- The lattice and the uniform core point size follow contract clauses. Those clauses came from the fix wave as the agent's own calls, not owner rulings, which keeps this criterion at the threshold.
- The board-versus-page difference I disputed in round 1 is fixed. The unfiltered state is labelled as such.
- I found no other uncited difference.

## Disputed items

None.

## For the owner

- Judge the core's lattice texture and hard lobe edges on the live instance. They meet the contract as written, but they are the most visible remaining difference from `graph.jpg`.
- **Pre-existing focus defects** the report records, outside this contract:
  - Tab lands on three hidden 0 px filter controls.
  - Tabbing out of the settings panel drops focus to `<body>`.

Verdict: ship 1b80fcaade5ed8da
