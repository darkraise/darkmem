# UI proof: computed memory graph cluster names

**Contract:** touch
**Fingerprint:** 346d8c9f0a595105
**Judge:** ship 346d8c9f0a595105 — docs/dforge/ui-ux/proofs/2026-11-20-graph-cluster-quality.judge.md
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

## Delta

**UI/UX depth:** touch — the only visible change is the text of cluster names on the memory graph; the cluster naming prompt leaves the API, and no Settings surface ever showed it; no layout changes. (Spec `docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md`, ## UI/UX, as corrected by the ruling-seat report `.dforge/sdd/2026-11-20-graph-cluster-quality/rulings-blocked-plan-7-report.md`.)

- **UI-1** — On the live memory graph (cloned corpus, default view), each island name and each region chip shows the computed name (`<project> · term · term`, or terms alone), at 1280x800 and 1920x1080, light and dark. Names within 40 characters show without an ellipsis.
- **UI-2** — With a project selected in the graph's project scope, no name carries a project prefix.
- **UI-3** — The filter panel's cluster list shows the same names as the canvas.
- **UI-4** — No Settings surface shows a cluster naming prompt: the LLM tab offers a System prompt only on the extraction, classification, reasoning and summarization purpose cards, and the Integration tab's "View injected MCP prompt" still opens the agent instructions prompt.
- **OP-1** — Proven on the live page with 0 console or page errors and 0 attempted writes, after the change is deployed to this host.

## Decisions

- **UI-4 was reworded before capture.** The approved draft named a Settings → Assistant Prompts section showing the chat and agent instructions prompts. The SPA has no such section and never showed `chat` or `cluster_naming`; the ruling seat amended the plan (A7) and the spec (commit 118aeae9) to name the two surfaces that do render prompts.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .dforge/ui-ux/graph-cluster-quality/ui1-regions-off-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-off-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-off-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-off-1280x800-light.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-on-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-on-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-on-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui1-regions-on-1280x800-light.png, .dforge/ui-ux/graph-cluster-quality/run-1920x1080-dark.json, .dforge/ui-ux/graph-cluster-quality/run-1920x1080-light.json, .dforge/ui-ux/graph-cluster-quality/run-1280x800-dark.json, .dforge/ui-ux/graph-cluster-quality/run-1280x800-light.json; tests `tests/unit/test_cluster_names.py`, `tests/test_graph_scale.py::test_arm_names_come_from_the_namer_and_never_call_the_llm` | Each run JSON records `cluster_names` from the page's own `/api/v1/graph/unified` response (limit 1000, threshold 0.5): 17 clusters, identical in all four runs, e.g. "darkraise-modder · dst · lua · anim", "claude code · codex · llm", "darkraise-ai-plugins · dr-superpowers", "GamexV2 · ecashier · pgsoft · zerotier". The longest is 40 characters; no name exceeds 40, and the captures show every centre name (Regions off) and every chip (Regions on) in full, with no ellipsis. |
| UI-2 | pass | .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-1280x800-light.png, .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-regions-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui2-project-scope-regions-1280x800-light.png; test `tests/unit/test_cluster_names.py::test_single_project_view_has_no_prefix_and_skips_its_project` | Scope `darkraise-framework` set through the project store. The page's response (`...&project=darkraise-framework`) carries 18 names, none starting with a project name, e.g. "codedisplay · editor · keybindings", "theming · primary · accessibility", "nodegraph · graphnode · connectmode". Known difference, not caused by this change: in the scoped Regions captures 17 of 18 chips draw at 1920x1080 (16 at 1280x800). The missing ones ("disposal · ondisposing · ownerwindow"; also "planning · documentation · docs" at 1280x800) are regions whose top point lies between already-placed chips, which the existing chip placement drops when no free position remains (`frontend/src/features/graph/lib/__tests__/region-chip.test.ts` "drops a chip that collides and has no room left inside its region"; recorded as UI-3 of the 2026-11-20 regions proof). Those names still show as centre names with Regions off (ui2-project-scope captures) and in the filter panel. |
| UI-3 | pass | .dforge/ui-ux/graph-cluster-quality/ui3-filters-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui3-filters-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui3-filters-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui3-filters-1280x800-light.png, the four run JSON files (key `ui3`) | The run reads the filter panel's labels under "Clusters"; every cluster's name plus its count from the response appears among them, in all four runs (17 of 17). |
| UI-4 | pass | .dforge/ui-ux/graph-cluster-quality/ui4-llm-tab-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui4-llm-tab-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui4-llm-tab-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui4-llm-tab-1280x800-light.png, .dforge/ui-ux/graph-cluster-quality/ui4-integration-agent-instructions-1920x1080-dark.png, .dforge/ui-ux/graph-cluster-quality/ui4-integration-agent-instructions-1920x1080-light.png, .dforge/ui-ux/graph-cluster-quality/ui4-integration-agent-instructions-1280x800-dark.png, .dforge/ui-ux/graph-cluster-quality/ui4-integration-agent-instructions-1280x800-light.png, the four run JSON files (key `ui4`); test `tests/test_llm_pipeline_config.py::test_cluster_naming_is_not_a_prompt_key` | LLM tab: 4 "System prompt" buttons, on extraction, classification, reasoning and summarization only. Integration tab: "View injected MCP prompt" opens "Injected MCP instructions" with the agent instructions text loaded ("darkmem is a centralized memory and code knowledge system…"). No "cluster naming" string on either surface, in any run. The test proves the key is gone from `GET /api/v1/config/system-prompts` and refused (422) by `PUT`. |
| OP-1 | pass | .dforge/ui-ux/graph-cluster-quality/run-1920x1080-dark.json, .dforge/ui-ux/graph-cluster-quality/run-1920x1080-light.json, .dforge/ui-ux/graph-cluster-quality/run-1280x800-dark.json, .dforge/ui-ux/graph-cluster-quality/run-1280x800-light.json, .dforge/ui-ux/graph-cluster-quality/scripts/shot.mjs, .dforge/ui-ux/graph-cluster-quality/deployed-image.txt | All four runs: `errors: []`, `blocked: 0`, `overflow: false`. The running container's image is 0927c74c03a7, tagged 4098dca2 (the branch head that carries the change). |

**Harness:** the production app on :8000, rebuilt locally from 4098dca2 (`DARKMEM_PUSH=0 ./scripts/build-push.sh`, `docker compose up -d`, healthy), holding the cloned 192.168.0.199 corpus (4,759 memories; the page requests 1,000). A session was minted inside the container (a JWT mint, no write) and set as the `darkmem_session` cookie; `localStorage['darkmem-auth']` and `darkmem-project` were seeded before load. Every request other than GET, HEAD and OPTIONS was routed to abort; none was attempted. Light runs answered `GET /api/v1/config/theme` with the stored settings plus `mode: "light"`. Chromium on SwiftShader, 20 s after the canvas appears; Regions is switched through the toolbar's settings popover.

## Automated checks

- console and page errors: 0 in all four live runs.
- attempted writes: 0.
- horizontal overflow: none at either viewport.
- Gate legs (gate.sh is GATE BLOCKED on this checkout by the missing F1 bench cache, so its legs ran one by one): alembic one head; backend pytest 8,476 passed, 26 skipped; frontend typecheck, `npm test` (2,474 passed) and build; extension; both SDK suites; SDK build; benchlib 1,062 passed.
- A4 (clustering over the newest 1,000 production memories): 17 clusters, largest 104, churn ARI 0.882 (`.dforge/ui-ux/graph-cluster-quality/measurements/a4-shipped.out`).

## Not proven here

- Keyboard: the change adds no control and changes no focus behaviour; not walked.
- Frame rate: not measured (SwiftShader; profile decision 2026-11-18). Naming adds no per-frame work.
- Adjacent, outside this change (no frontend code changed): after switching Regions back off, the region outlines and chips stay drawn beside the returned centre names until something repaints that layer (.dforge/ui-ux/graph-cluster-quality/ui1-regions-back-off-1920x1080-dark.png and the three other `ui1-regions-back-off-*` captures; the `ui3-filters-*` captures, taken after it, show the same layer). Reported, not fixed.
