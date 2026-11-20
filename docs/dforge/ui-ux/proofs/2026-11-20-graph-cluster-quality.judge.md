## Verdict
verdict: ship 346d8c9f0a595105
scores: coverage 17 / fidelity 17 / states 16 / deviations 16

## Method

I read the criteria, the contract (the spec's `## UI/UX`, which the report's Delta copies verbatim), the report, all four `run-*.json` files, `scripts/shot.mjs` and `deployed-image.txt`. I opened 15 of the 32 cited screenshots. I read the named tests in `test_cluster_names.py`, `test_llm_pipeline_config.py`, `test_graph_scale.py` and `region-chip.test.ts`.

Screenshots opened:
- ui1 regions-off: 1920 dark, 1920 light, 1280 light
- ui1 regions-on: 1920 dark, 1280 dark, 1280 light
- ui2 scope: 1920 dark
- ui2 scope-regions: 1280 light
- ui3 filters: 1920 dark, 1280 light
- ui4 llm-tab: 1280 light, 1920 dark
- ui4 integration dialog: 1920 dark

The unopened ones are the other theme/viewport variants of the same captures. The four run JSONs record the same names, errors and counts for them.

## Every Item Has Evidence (coverage) 17

- **UI-1:**
  - The JSON from the page's own `/api/v1/graph/unified` response lists 17 names. The longest is exactly 40 characters ("darkraise-modder · documenthost · studio"), so no ellipsis is expected.
  - Regions off (1920 dark, 1920 light, 1280 light): all 17 centre names are drawn in full.
  - Regions on (1920 dark, 1280 dark, 1280 light): all 17 chips are drawn in full with their counts.
  - The theme x viewport matrix is complete in the run JSONs.
- **UI-2:**
  - The header shows "project: darkraise-framework".
  - The JSON response holds 18 names and none carries a project prefix.
  - `test_single_project_view_has_no_prefix_and_skips_its_project` exists and asserts it.
  - The 16 chips drawn at 1280 light match the report's count.
- **UI-3:**
  - The cluster list under CLUSTERS in the filter panel matches the canvas names ("darkraise-modder · dst · lua · anim 44", "layout · sidebar · treeview 80").
  - The full 17 of 17 rests on the DOM-text capture in the run JSON `ui3` key, not on pixels. The panel scrolls and shows only 2 rows in the 1280 capture and 10 in the 1920 capture.
  - The JSON entries are the same names with the response counts. This is adequate.
- **UI-4:**
  - The LLM tab shows System prompt buttons on extraction, classification, reasoning and summarization only. The 1920 dark capture shows all eight cards, and the 1280 capture shows six.
  - The JSON gives `purposesWithPromptButton` = those four, `promptButtons` 4 and `mentionsClusterNaming` false.
  - The integration dialog "Injected MCP instructions" shows the agent instructions text.
  - `test_cluster_naming_is_not_a_prompt_key` asserts that the key is absent from GET and that PUT answers 422.
- **OP-1:**
  - All four JSONs have `errors: []`, `blocked: 0` and `overflow: false`.
  - `shot.mjs` aborts every non-GET/HEAD/OPTIONS request and counts it, and it listens for page and console errors.
  - `deployed-image.txt` shows the first line `4098dca2 0927c74c03a7`, with `latest` pointing at the same image id.

## Built Matches Promised (fidelity) 17

- Names use the `<project> · term · term` shape or terms alone, as promised.
- No ellipsis appears on any name I opened.
- Chips and centre labels use the existing design system. The change adds no layout and no new component.
- In the scoped view, "darkraise-framework" and its own project name are absent from every name, as UI-2 requires.
- Some centre names overlap data points or each other at 1280x800 (for example "darkraise-ai-plugins · dr-superpowers"). This is the existing label placement. The contract promises full text, not zero overlap.

## Every State Is Shown (states) 16

- The contract is touch depth and has no state matrix. The relevant states are two themes, two viewports, Regions off and on, and project scoped versus all projects. All are captured.
- The keyboard walk is declared unproven because no control or focus behaviour changed. For a touch contract that is acceptable.
- Frame rate is not measured, and the report says so, citing the profile decision.

## Deviations Are Cited (deviations) 16

There are no deviation rows. Two differences are disclosed:
- **Scoped chips dropped.** In scoped Regions captures, 1 or 2 region chips are not drawn (17 of 18 at 1920, 16 of 18 at 1280). This is attributed to existing chip placement. It is backed by `region-chip.test.ts` "drops a chip that collides and has no room left inside its region", which I read and which exists. The same names still appear as centre names with Regions off and in the filter panel. UI-1 promises chips only for the default view, where all 17 are drawn, so the contract is not breached.
- **Stale regions layer.** After Regions is switched off, outlines and chips stay drawn beside the centre names. This is disclosed under "Not proven here" as adjacent and out of scope, because no frontend code changed. The same doubled layer is visible in the `ui3-filters` captures, which are taken after the back-off. The report lists only the `ui1-regions-back-off-*` captures.
- Neither difference cites a user answer or an accessibility need. Both are pre-existing behaviour outside the contract, which is why the score is not higher.

## Disputed items

None.

Verdict: ship 346d8c9f0a595105
