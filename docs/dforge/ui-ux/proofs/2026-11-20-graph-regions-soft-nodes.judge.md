## Verdict
verdict: ship c3b9bcdf3961c76e
scores: coverage 18 / fidelity 17 / states 17 / deviations 17

Contract judged: the report's Delta (touch): UI-1, UI-2, UI-3, UX-1, UI-4, OP-1. Round 2, re-stamped at c3b9bcdf3961c76e. Round 1 disputed UI-4 and UX-1; both are now resolved.

## What I opened

Round 1 evidence (the final-regions fit and zoomed captures at both viewports and themes, the before-regions capture, the run JSON, shot.mjs, and the region-chip, framed-hull and island-labels tests plus the geometry and renderer source). Round 2 evidence:
- compare-zoom-node, compare-fit-node and compare-fit-hover, dark and light.
- final-regions-unselected, final-regions-selected, final-regions-off-selected and final-regions-off, dark, with the unselected, selected and off light captures.
- final-sel-run and before-sel-run JSON, and sel2.mjs.
- `drawnDiscRadius` in node-glow-program.ts, its use in the renderer's `drawnDisc`, and the new test in node-glow-program.test.ts.

## Per item

- UI-1 (rounded hull outline): supported, unchanged from round 1. The final-regions captures show smooth convex outlines with a solid thin edge. The before capture shows dashed, pointed outlines. `framed-hull.test.ts` covers smooth joins, one full turn, a capsule and circle for two and one points, and arcs only with no dash. The 22 px pad, 1 px width and the 0.07 and 0.3 opacities are read from source.
- UI-2 (centre names hidden, chips at every zoom): supported. The run JSON shows 0 centre-name pixels with Regions on, against 27,971 before. I counted 12 chips for 12 regions at both fit views. The new unselected captures also show every region carrying a chip.
- UI-3 (chip placement): supported. `region-chip.test.ts` covers inside-top centring, edge and toolbar clamp, drops above and to either side, larger-first order, move-below, and drop-when-no-room. The zoomed captures show chips clamped below the toolbar band, and chips do not overlap in any capture. In dense areas a displaced chip sits well below its region's top, which the move-below rule allows.
- UX-1 (names return when Regions is off; chips recede under a selection): supported.
  - Dark and light `regions-selected` against `regions-unselected`: every chip and region fades with the rest of the canvas when a memory is selected, and the selected node keeps its ring and label.
  - Dark `regions-off-selected`: the centre names come back, receded, with the memory still selected.
  - Dark and light `regions-off`: the names return at full strength once the selection is cleared.
  - The four matrix-run pixel counts (27,971 / 27,964 / 27,986 / 27,990) agree.
  - The exact 0.35 opacity comes from `islandLabelAlpha`, which `island-labels.test.ts` pins. The report says so.
- UI-4 (soft memory discs, 2 px floor, rings follow the floor): supported.
  - The magnified comparisons put the deployed build beside this build.
  - Zoomed, dark and light: the before discs have stair-stepped one-pixel rims, and the after discs fade over several pixels. This is clearly visible in both themes.
  - Fit view, dark and light: the before lightest memories are 1 to 2 px square specks, and the after ones are rounder 2 px dots. This is visible at 4x.
  - Hover, dark and light: in both builds the ring encloses the drawn disc. The new test "rings a memory disc at the radius the shader draws, never under the 2 px floor" checks `drawnDiscRadius`, and the renderer's `drawnDisc` calls it. The shader define test still holds, with `SOFT_DISC` on the memory canvas only.
  - The crops show different memories in the two builds, which the report states.
- OP-1: supported. Every run JSON, including the new final-sel-run and before-sel-run files, shows `errors: []`, `blocked: 0`, `overflow: false`. Both shot.mjs and sel2.mjs abort non-GET requests.

## Disputed items

None.

## Notes on the other criteria

- Coverage: every Delta item has a row with evidence I opened that shows that item. Round 1's two gaps are closed by magnified before and after images and by selected and unselected captures.
- Fidelity: the chips ("name · count", mono pill, tinted stroke), the outlines, and the soft node edges match the promise in both themes. The 1280x800 fit view is crowded but readable.
- States: Regions on and off, fit and zoomed, unselected and selected, hover, and both themes and both viewports are covered. The 1280x800 viewport has fewer captures for selection and hover than 1920x1080, which does not change the verdict. Keyboard was not walked; no control or focus behaviour was added, and the report says so.
- Deviations: no row is marked deviation. The Decisions section lists rulings the report presents as its own, and each carries its reason. I found no difference marked as a pass.
- The "Not proven" section is accurate. The shot.mjs four-step zoom crops landed on empty canvas, and the compare images cover that case.

Verdict: ship c3b9bcdf3961c76e
