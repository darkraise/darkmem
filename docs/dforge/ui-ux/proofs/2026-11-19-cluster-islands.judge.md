## Verdict
verdict: ship b3f4d413ee6a796f
scores: coverage 17 / fidelity 17 / states 16 / deviations 16

This re-judges the proof at fingerprint b3f4d413ee6a796f, after the UX-4 fix. It is judged against `docs/dforge/specs/2026-11-19-cluster-islands-design.md` (UI/UX contract, Decisions including the owner's island-arrangement ruling, and acceptance statements A1–A15) and the proof report `docs/dforge/ui-ux/proofs/2026-11-19-cluster-islands.md`.

For this pass I read:
- the rewritten UX-4 row and the new "UX-4 details" section
- the changed signature code in `graph-2d-renderer.tsx`
- the new A10 test in `constellation-graphs.acceptance.test.tsx`
- all four same-page before/after pairs (`live-entity-layer-before-*` against `live-entity-layer-*`)
- `entity-layer-overlap.txt` and `live-entity-run-1920x1080-light.json`

Everything else I opened in the earlier pass: every other cited screenshot, the board, live, keyboard and synthetic captures, the JSON logs, `cap.mjs`, `keys.mjs`, every other cited test, and `cluster-runner.ts`. The coordinator states that no other UI file changed. I did not run any test; my findings on tests come from reading them.

## UX-4 re-check

**Code.** `layoutSignature` is now built from `filteredMemories.map((m) => m.id)` only, with a comment that entities ride on their memories' centroid and never enter the simulation. The island signature (`islandSig`) was already built from memories only. Turning the entity layer on therefore changes neither signature. The `if (!layoutChanged && !islandsChanged)` early return is taken, and `runner.start()` is not called.

The rebuild still creates a new runner. Its constructor does one refit-and-spread pass (`arrange(startAt, SETTLE_ITERATIONS)`) from the settled positions. That is the small drift the report describes.

**Test.** "islands A10 (UX-4): turning the entity layer on after the layout settles starts no layout run and moves no memory" does the following:
1. Mounts the renderer with the layer off and advances 120 s.
2. Records the worker count and every memory position.
3. Rerenders the same mounted renderer with the layer on and advances 120 s.
4. Asserts the entity node exists, the worker count is unchanged, and every memory's x and y match to 2 decimal places (within 0.005).

This is exactly the transition my earlier report said no test covered. The report says the test fails without the fix (two layout runs instead of one). I did not run it to confirm.

**Captures.** All four pairs (dark and light, 1280x800 and 1920x1080) are taken on the same page just before and 15 s after the switch is pressed. In each pair every island keeps its place and shape, including the bottom-right red island and the top-right blue island that moved in the earlier separate-load comparison. Diamonds appear among their memories and in the gaps between islands.

`entity-layer-overlap.txt` supports this: the after-capture best matches the before-capture at offsets of at most 2 px (84.5%, 86.8%, 84.4% and 71.5% overlap). Shifting 3 px sideways drops the overlap to roughly 35–50%. The lower 1920x1080 light figure fits the denser diamond overdraw visible in that capture. The four run logs show no errors and no blocked writes (one opened; the report states the same for all four).

**Correction to my earlier report.** I had inferred that the live layout is reproducible across page loads. The new before-captures disprove that: for example, the 1920x1080 dark red island is already an arc before the toggle. The code defect I disputed was real, and it is fixed. But the earlier picture comparison also mixed in differences between separate page loads, as the report now says.

UX-4 is no longer disputed. The UX-3 concern that went with it (a rebuild with unchanged membership re-running the layout) is resolved by the same change.

## Scores

**Every Item Has Evidence (coverage): 17.** Every contract item (UI-1 to UI-3, UX-1 to UX-4, OP-1, OP-2) has a Results row whose evidence I opened, and that evidence shows the item. OP-2's timings were read from test output in the session that made them, and no log was saved. The A12 test itself is real and asserts a median of 5 runs at or under 50 ms.

**Built Matches Promised (fidelity): 17.**
- **UI-1:** a "Regions" switch named "Cluster regions", off by default. With it on, each cluster gets a region in its own colour, with a name chip when zoomed in (live, both themes). Off and Reset draw no region (keys captures, both themes).
- **UI-2:** at rest no line crosses between islands. Hover and selection light cross-island edges.
- **UI-3:** loose memories are dim and small on the synthetic boards. The brightness and size ratios are asserted by tests.
- **UX-1:** the owner's wide, hubless arrangement is visible on the All and default captures. A14 and A15 are tested as written.
- **UX-2:** sub-groups gather inside islands with no touching points; A4 and A5 are tested.
- **UX-3:** board islands are in place at 1.2 s.
- **UX-4:** now matches, as above.

**Every State Is Shown (states): 16.** Covered at both viewports and both themes unless noted:
- default, regions on, regions zoomed, hover, selection, the full corpus, the first frame, and the entity layer
- the entity-layer toggle on a mounted page, now with a same-page pair and a test
- the synthetic worst cases: a 20,000-memory scale board, an all-loose board and a mixed board (1280x800 only)
- keyboard focus and Space on the switch (1280x800 only, both themes)

Two gaps keep this from scoring higher. `keys.mjs` presses Reset with a mouse click, not the keyboard. The 1.2 s first-frame capture is not the literal first frame, which the report discloses.

**Deviations Are Cited (deviations): 16.** There are no deviation rows. The report discloses its limits: the first-frame timing, the slow first toggle after load, the undeployed build, no loose island on real data, and the earlier failed UX-4 and UI-1 passes with their causes. The one difference I found and nobody cited (UX-4) is fixed. The remaining mismatch is a wrong node name in a note, not a difference in the built UI.

## Disputed items

None.

## Other observations (not disputed)

- The UI-2 note names the hovered node "Memory 108", but `board-hover-1280x800-dark.png` shows "Memory 942". The picture still proves the item; the note should be corrected.
- With the entity layer on, membership edges from an entity sitting between islands to the island it was voted onto draw long lines across open space at rest. Examples: the fan in `board-entity-layer-1920x1080-light.png`, and the converging lines near the cyan centre island in `live-entity-layer-1920x1080-light.png`. UI-2 covers only memory-to-memory edges, so this is not a contract breach. It does contradict the renderer's own comment that the view "draws no lines across open space".
- The board Regions-zoomed captures show no name chip, because the zoom lands away from it. The chip is proven on the live zoomed captures in both themes.
- `keys-*.json` records `panelOpenAfterReset: false` while the after-reset screenshots show the panel open, because `keys.mjs` reopens it. That is consistent, but the report does not mention that Reset closes the panel.
- Not proven, as the report itself states: the deployed image on `:8000`. One live capture should be re-taken after deploy.
- Adjacent: the axe `region` finding (moderate, 21 nodes, settings panel outside any landmark) is reported as pre-existing. I did not verify that it predates this change.

Verdict: ship b3f4d413ee6a796f
