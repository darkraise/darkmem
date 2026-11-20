## Verdict
verdict: ship dec22c42ed49ced1
scores: coverage 17 / fidelity 17 / states 15 / deviations 16

## What I opened

- Criteria file, the report and its Delta section.
- All four run-*.json files and `scripts/walk.mjs`.
- 4 Mermaid dialog screenshots; all 8 `llm-save-*` screenshots; 8 of the 16 `llm-dialog-*` pairs (1280 refused light and dark, 1920 accepted light and dark); `llm-tab-1280x800-dark`.
- 8 of the 32 demo screenshots (code graph, repositories, wiki, memory graph, memories, notes, jobs, settings LLM), which covers every screen named in UI-2.
- `explore.test.ts`, `settings-llm.real.test.tsx`, `real-code-graph-view.test.tsx`, `explore.ts` (`escapeMermaid`, `mermaidForProcess`) and `use-llm-tab-binding.ts`.
- The profile.

Screenshots I did not open: the other 24 demo images, and `llm-tab` at the three other viewport and theme combinations. The run JSONs carry the same overflow and landing keys for them.

## Per-item findings

- UI-1, proven.
  - All four Mermaid dialog screenshots show `flowchart TD`, five `nN["name"]` lines, then four `nA --> nB` lines.
  - The `--> ` arrows are drawn as a ligature. The run JSON `mermaid` field holds the literal `-->`, and `walk.mjs` reads it from the dialog's `pre` text, so the report's explanation holds.
  - `everyChartValid: true` and `charts: 3` appear in all four runs. The regex in `walk.mjs` matches the two line shapes and forbids `"`, `[` and `]` inside a name.
  - The 40-step, escaping and one-step cases are only in `explore.test.ts` (read). That file asserts n0..n39 ids, quote, bracket, angle, brace and ampersand escaping, and the exact single-node output `flowchart TD\n  n0["main"]`. The assertions agree with `escapeMermaid` and `mermaidForProcess`.
  - Whether Mermaid itself renders the `&quot;` and `#91;` forms is not shown anywhere.
- UX-1, proven for the demo dialog, from the run JSON.
  - `focusReturned: true` and `reopenedByKeyboard: true` appear in all four runs.
  - `walk.mjs` does this by pointer click, Escape, a check that `activeElement`'s aria-label equals the trigger's, then `trigger.focus()` and Enter.
  - There is no screenshot of the focus ring on the trigger.
- UX-2, proven.
  - All four refused screenshots show the error toast "Couldn’t save the reasoning purpose" with "verification-judge serves the verification purpose only" beneath it, and no success toast. The title uses the curly apostrophe the contract uses.
  - The run JSON shows `failureToast: 1`, `successToast: 0`, `reasonShown: 1` and `announcedLive: 2` in every run.
  - The 409 was fulfilled inside the browser by `walk.mjs`.
  - The test `reports a refused save as a failure and never as saved` asserts one `toast.error` with the description and no `toast.success`.
- UX-3, proven.
  - All four accepted screenshots show "Saved — reasoning purpose updated", with the changed field name `params` beneath it. The JSON shows `successToast: 1` and `failureToast: 0`.
  - `use-llm-tab-binding.ts` calls `announceSave` only from `onSuccess`, so "after the response" holds by construction.
  - The test `announces a save only once the server has accepted it` checks only that the toast arrives, and exercises `setClassifierKind` rather than `savePurpose`. It does not show that no toast fires before the response.
- UX-4, proven.
  - The before and after pairs show Save dimmed before the edit and bright after it, in both themes at 1280 (refused) and 1920 (accepted). `saveDisabledBeforeEdit` and `saveEnabledAfterEdit` are true in both scenarios of all four runs.
  - The refused scenario opens the dialog with Enter on the focused Edit button and activates Save with Enter, in every viewport and theme. The accepted scenario clicks Save.
  - The Edit button's focus ring is visible in the refused shots.
- UI-2, proven.
  - Every screen in the list was shot and looks intact, with no blank page.
  - Every `*-overflow` key is false and every `*-landed` path matches the route requested.
  - The demo shows no page or console errors. The real tab's 5 errors match the 4 aborted model-probe POSTs plus the forced 409. The report's account is consistent with `writesAborted`, though the ERR_FAILED lines carry no URL.
- OP-1, proven.
  - `demo.apiCalls: 0` in all runs.
  - `writesReachingBackend: 0`, and `walk.mjs` aborts every non-read request except the one `POST /api/v1/config/llm` it fulfils itself.

## Observations that are not disputes

- The comment in `walk.mjs` says "Tab to Save", but the code calls `edit.focus()` and `save.focus()` and does not Tab. So the walk proves Enter activation, which is what the contract states. It does not prove the trigger, Edit button or Save are reachable by Tab. The states score is held at the threshold because of this.
- The accepted toast carries a second line, the raw field name `params`. The contract names only the title, and the profile Voice says "no developer-facing copy". The code comment says the fields were kept on purpose, but the report does not record this as a difference. Minor.
- A refused save closes the purpose dialog and the edit is lost. The report discloses this under audit finding F2-7 and it predates the change, so it is not scored as a deviation.
- On the 1920 light memory graph, node labels sit on edges and neighbouring nodes ("hybrid_search", "reranker", "pgvector"). The contract asks only for no error and no overflow, and there is no before state to compare, so this is unproven either way. It is outside this contract.
- The save's pending state and invalid-JSON state have no screenshot. They are not Delta items.
- The report's "Not proven here" list (real Code Graph Mermaid dialog, classifier-kind switch, Copy button, before and after of the UI-2 screens) is honest and matches what I found. `real-code-graph-view.test.tsx` renders the real view's Mermaid dialog and asserts only `flowchart TD` and `process_batch`, which is consistent with the report's claim.

## Disputed items

None.

Verdict: ship dec22c42ed49ced1
