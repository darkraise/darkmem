# UI proof: memory graph cluster labels and node size contrast

**Contract:** touch
**Fingerprint:** b2c54fce74dbe1b8
**Judge:** ship b2c54fce74dbe1b8 — docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-labels.judge.md
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

## Delta

**UI/UX depth:** touch — owner request 2026-11-20 on the memory graph: "let show the cluster label on graph, and make the size differentiation of nodes more obvious"

- **UI-1** — Each clustered island 24 px or more in radius on screen shows its cluster name, with hull mode off or on, on canvases from about 700 px wide (the 1280x800 page with the detail panel open) up. The name sits at the island's centre. When it would collide with a placed name it sits just above or below that name. When it would cross a canvas edge, or run into the 48 px toolbar band at the canvas top, it is pulled inside. Every position keeps the name's centre within the island's radius of the island's centre; a name wider than the canvas, or with no such position, is dropped. The loose island is not named. A cluster with no derived name shows "Cluster N", as the filter panel does.
- **UI-2** — Island names never overlap one another: larger islands are placed first. Font is 11 to 15 px, larger for larger islands; names over 40 characters end in an ellipsis.
- **UI-3** — Names read in both themes: 600-weight foreground text stroked with a 4 px line in the canvas colour at 0.9 opacity (about 2 px of halo outside the glyph), drawn above the nodes and below sigma's node labels and hover tags.
- **UX-1** — Names stay at every zoom and with Regions on, beside the region chips; while a memory is selected they draw at 35% opacity.
- **UI-4** — Node size follows each memory's rank among the memories the filters keep, from 10 to 46 (drawn 2.5 to 11.5): on a fixture with the production importance mix, the 0.8-importance memories are 4.5 times the radius of the 0.4 ones (1.5 times before), and 0.7 against 0.5 is 3.4 times (1.2 before). Equal weights share one size; uniform mode is unchanged.
- **OP-1** — Proven on the live page with the cloned corpus at 1280x800 and 1920x1080, light and dark, with 0 console or page errors and 0 attempted writes.

## Decisions

Rulings that are mine, reported for review:

- **Sizes rank within the filtered set, not on an absolute scale.** Of 4,812 active memories, 97.9% have importance 0.4 to 0.7 and 50.8% exactly 0.6 (.dforge/ui-ux/graph-cluster-labels/importance-distribution.txt, whole corpus, 2026-11-20; the page shows 1,000 of them), so any linear map of importance draws them alike. Ranking spreads the band over the full range; the cost is that a memory's size can change when filters change.
- **The size range and curve.** 12–40 became 10–46, and size = 10 + 36·p^1.6 for the mid-rank percentile p. The 1.6 curve keeps most memories small (a median memory lands near size 21) so the heaviest stand out. Ties share the middle of their block: in connections mode the zero-degree memories share one small size, and a view where every weight is equal draws at about 22.
- **Names are never hidden by zoom or Regions.** An earlier build hid them when zoomed in, which left no name on screen with Regions off; the next build hid them only when zoomed in with Regions on, but region chips hang off each hull's top edge and are often off screen, so clusters went unnamed. Names now stay; with Regions on and zoomed in, a cluster can show both its chip (with the member count) and its name.
- **A pulled-in name stays over its own island by its centre only.** Its text can run across a neighbouring island or hull.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .dforge/ui-ux/graph-cluster-labels/final-default-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-labels/final-default-1920x1080-light.png, .dforge/ui-ux/graph-cluster-labels/final-default-1280x800-dark.png, .dforge/ui-ux/graph-cluster-labels/final-default-1280x800-light.png, .dforge/ui-ux/graph-cluster-labels/final-selected-1280x800-dark.png, .dforge/ui-ux/graph-cluster-labels/final-selected-1280x800-light.png, .dforge/ui-ux/graph-cluster-labels/final-regions-1280x800-dark.png, .dforge/ui-ux/graph-cluster-labels/final-regions-1920x1080-light.png, .dforge/ui-ux/graph-cluster-labels/final-regions-zoomed-1280x800-dark.png, .dforge/ui-ux/graph-cluster-labels/before-default-1920x1080-dark.png; tests `island-labels.test.ts` "names each island at its centre", "builds one input per clustered island: derived name, else Cluster <id>; the loose island unnamed", "leaves an island too small on screen unnamed, until zooming in grows it", "never lets two labels overlap: the larger island keeps its centre, the smaller moves a line", "tries above, then below, and drops a name with no free position", "pulls a name that would cross the canvas edge inside it, over its own island", "keeps a name out of the toolbar band at the top of the canvas" | Eleven islands named in all four default captures, the Regions-on captures and the 1280x800 selected captures (canvas about 700 px wide); before, none was named. Earlier builds dropped "hcd-inbox UAT Design" and "darkraise-framework App Zoom" at 1280x800 (collision), "darkraise-framework CodeDisplay" with the detail panel open (canvas edge), and drew "hcd-inbox UAT Design" under the toolbar buttons. In the zoomed Regions capture, the two islands whose bodies lie mostly above the canvas ("… Translation Work", "hcd-inbox UAT Design") are unnamed: their centres are more than a radius from any position below the toolbar band. The "Cluster N" fallback is tested; every live cluster had a derived name. |
| UI-2 | pass | same captures; tests "never lets two labels overlap …", "tries above, then below …", "draws a larger island's name in a larger font, within 11 to 15 px", "skips an island whose label would sit off screen", "cuts a long name with an ellipsis and keeps a short one whole" | A first cut at 28 characters made two islands read "darkraise-modder Translatio…"; at 40 they read "… Translation Work" and "… Translation Eval". No two names overlap in any capture. |
| UI-3 | pass | .dforge/ui-ux/graph-cluster-labels/final-default-1920x1080-light.png, .dforge/ui-ux/graph-cluster-labels/final-crop-light.png, .dforge/ui-ux/graph-cluster-labels/final-default-1280x800-dark.png | Dark text on the light canvas and light text on the dark canvas. In light mode a dot can show through a word gap ("UI Framework", "Translation Eval"); the text stays legible. The layer sits before sigma's `labels` canvas in the DOM, so node labels and hover tags paint over it; no capture shows the two overlapping. |
| UX-1 | pass | .dforge/ui-ux/graph-cluster-labels/final-zoomed-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-labels/final-zoomed-1280x800-light.png, .dforge/ui-ux/graph-cluster-labels/final-regions-zoomed-1280x800-dark.png, .dforge/ui-ux/graph-cluster-labels/final-selected-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-labels/final-selected-1280x800-light.png; test "keeps names at full strength unless something is selected" | Four wheel steps in with Regions off: the island in view keeps its name (label-layer pixels 2,889 / 2,897 / 2,886 / 2,885). One step in with Regions on: names drawn in all four runs (22,618 / 22,626 / 22,641 / 22,634), and the capture shows nine names beside the chips. The selected captures show the names receded behind the selected memory's tag; the 0.35 opacity is pinned by the test, not measured. |
| UI-4 | pass | .dforge/ui-ux/graph-cluster-labels/final-crop-dark.png against .dforge/ui-ux/graph-cluster-labels/before-crop-dark.png (the same screen region; the layouts differ by a few px per dot), .dforge/ui-ux/graph-cluster-labels/final-crop-light.png, .dforge/ui-ux/graph-cluster-labels/final-zoomed-1920x1080-dark.png; tests `memory-size.test.ts` "spreads a narrow band of importances across the whole size range", "grows each step of importance by 1.2x in area, and the steps round the median by 2x", "draws equal weights at one size and orders unequal ones", "draws a view where every weight is equal at the middle size", "ranks by connection count in connections mode", "draws every memory alike in uniform mode" | Before, one dot size throughout. After, the spread is clear in light mode and zoomed in; in the dark fit view the glow softens it but it is visible. The 4.5x and 3.4x ratios come from the test's 100-row fixture built from the production percentages, not from the live 1,000-memory view. `lib/memory-size.ts` replaces `computeSize` (old: 12 + importance·28, connections 12 + min(28, 8·ln(1+c)), uniform 18). The glow program's density pass scales each role's discs by one factor, so ratios within a role hold. |
| OP-1 | pass | .dforge/ui-ux/graph-cluster-labels/final-run-1920x1080-dark.json, .dforge/ui-ux/graph-cluster-labels/final-run-1920x1080-light.json, .dforge/ui-ux/graph-cluster-labels/final-run-1280x800-dark.json, .dforge/ui-ux/graph-cluster-labels/final-run-1280x800-light.json, .dforge/ui-ux/graph-cluster-labels/before-run-1920x1080-dark.json; script .dforge/ui-ux/graph-cluster-labels/scripts/sel.mjs | Final runs record `base: http://127.0.0.1:3636`, the before run `base: http://127.0.0.1:8000` (label counts -1: no label layer exists there). All: `errors: []`, `blocked: 0`, `overflow: false`. |

**Harness:** Vite dev on :3636 running this working tree and proxying `/api` to the production backend on :8000, which holds the cloned 192.168.0.199 corpus (1,000 memories in the default view). The before capture is the deployed image on :8000; .dforge/ui-ux/graph-cluster-labels/before-image.txt holds, in order, the running container's image id and the local `darkraise/darkmem` images with their tags, where that id carries tag e3f67821 (HEAD). A session was minted inside the production container (a JWT mint, no write). Every request other than GET, HEAD and OPTIONS was routed to abort; none was attempted. Light runs answered `GET /api/v1/config/theme` with the stored settings plus `mode: "light"`. Chromium on SwiftShader, 20 s after the canvas appears; Regions is switched on and off through the toolbar's settings popover.

## Automated checks

- console and page errors: 0 in all five live runs.
- attempted writes: 0.
- horizontal overflow: none at either viewport.
- `npm test`: 307 files, 2,461 tests, all passed (the two acceptance suites' sigma stand-ins gained `createCanvas`); `npm run typecheck` clean; `npm run build` passed.
- `ui-lint` on the changed source files: no findings.
- eslint on the changed files: 5 errors and 1 warning, all pre-existing: four refs read during render and one ref read in an effect cleanup in `graph-2d-renderer.tsx` (moved down by the added constants, none on a changed line), and a reassigned outer variable in `constellation-graphs.acceptance.test.tsx` (line 934 on HEAD, 939 after the five-line stub).
- `./scripts/gate.sh`: GATE BLOCKED (exit 2) on the missing extraction-bench cache in this checkout, a backend leg this change does not touch.

## Not proven here

- The renderer's draw call itself is untested beyond the pure helpers it calls; the acceptance stand-in never emits `afterRender`. The live runs exercise it.
- The entity layer on, entity selection, an empty graph and a single island were not captured; the empty case is covered by a unit test.
- A hub's memory label over an island name when zoomed in was not captured; nor a name pulled under the chat button at the canvas's bottom-right corner, which the placement does not avoid.
- The text-width cache is cleared when web fonts finish loading; that path was not exercised.
- The 3D renderer gets no island names and keeps its own linear sizing (`computeNodeVal`); it is out of scope.
- Keyboard selection was not walked; the change adds no control.
- Frame rate: not measured (SwiftShader; profile decision 2026-11-18). The label pass is one viewport projection and at most three placement tries per island per frame, with text widths cached.
