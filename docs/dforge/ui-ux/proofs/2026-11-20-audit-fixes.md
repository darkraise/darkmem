# UI proof: audit fixes — Mermaid export, LLM save feedback, removed graph code

**Contract:** touch
**Fingerprint:** dec22c42ed49ced1
**Judge:** ship dec22c42ed49ced1 — docs/dforge/ui-ux/proofs/2026-11-20-audit-fixes.judge.md
**Platform:** web
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Evidence:** local

## Delta

**UI/UX depth:** touch — the 2026-11-20 codebase audit fixed two defects on existing surfaces and deleted frontend files nothing imported (`docs/2026-11-20-codebase-audit.md`, findings F1-3 and F2-1, and section 3). No screen, flow or control was added.

- **UI-1** — The Mermaid export dialog shows `flowchart TD`, then one line per step declaring a node as `nN["name"]`, then one `nA --> nB` line per consecutive pair of steps. Ids stay `n0…nN` at any step count, names are escaped so quotes, angle brackets, square brackets and braces cannot end the node syntax, and a one-step process shows its single node.
- **UX-1** — The Mermaid dialog opens from its trigger by pointer and by Enter. Escape closes it and returns focus to the trigger that opened it.
- **UX-2** — When the server refuses an LLM purpose save, an error toast reads "Couldn’t save the reasoning purpose" with the server's reason beneath it, no "Saved" toast appears, and the failure is announced through a live region.
- **UX-3** — When the server accepts an LLM purpose save, the toast "Saved — reasoning purpose updated" appears after the response, with no error toast, and is announced through a live region.
- **UX-4** — In the purpose dialog, Save is disabled until the draft differs from the stored value. The dialog opens with Enter on its Edit button and Save can be activated with Enter.
- **UI-2** — The screens that import from the directories the removed files lived in render with no page or console error and no horizontal overflow: Code Graph, Code Repositories, Code Wiki, Memory Graph, Memories, Notes, Jobs and Settings → LLM.
- **OP-1** — The walk writes nothing: demo mode makes 0 API calls on those screens, and in real mode the save is answered inside the browser and every other non-read request is aborted before it leaves.

## Results

| ID | Verdict | Evidence | Note |
|---|---|---|---|
| UI-1 | pass | .dforge/ui-ux/audit-2026-11-20/mermaid-dialog-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/mermaid-dialog-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/mermaid-dialog-1920x1080-light.png, .dforge/ui-ux/audit-2026-11-20/mermaid-dialog-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/run-1280x800-light.json | All three fixture processes export a chart whose every line matches the two shapes (`everyChartValid: true`, `charts: 3` in each run file). The 40-step, escaping and one-step cases have no fixture and are pinned by `src/demo/__tests__/explore.test.ts > mermaidForProcess` (four tests); `escapes names that would break the node syntax` asserts quotes, square brackets, angle brackets, braces and the ampersand. The dialog's font draws `-->` as an arrow ligature; the text is `-->`. |
| UX-1 | pass | .dforge/ui-ux/audit-2026-11-20/run-1280x800-dark.json, .dforge/ui-ux/audit-2026-11-20/run-1280x800-light.json, .dforge/ui-ux/audit-2026-11-20/run-1920x1080-dark.json, .dforge/ui-ux/audit-2026-11-20/run-1920x1080-light.json | `focusReturned: true` (`focusAfterEscape` equals the trigger's label) and `reopenedByKeyboard: true` in all four runs. |
| UX-2 | pass | .dforge/ui-ux/audit-2026-11-20/llm-save-refused-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-save-refused-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/llm-save-refused-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-save-refused-1920x1080-light.png | The POST was answered 409 in the browser. Each run file records `failureToast: 1`, `successToast: 0`, `reasonShown: 1`, `announcedLive: 2`. Also `settings-llm.real.test.tsx > reports a refused save as a failure and never as saved`. |
| UX-3 | pass | .dforge/ui-ux/audit-2026-11-20/llm-save-accepted-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-save-accepted-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/llm-save-accepted-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-save-accepted-1920x1080-light.png | The POST was answered 200 in the browser. Each run file records `successToast: 1`, `failureToast: 0`. Also `settings-llm.real.test.tsx > announces a save only once the server has accepted it`. |
| UX-4 | pass | .dforge/ui-ux/audit-2026-11-20/llm-dialog-before-edit-refused-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-after-edit-refused-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-before-edit-refused-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-after-edit-refused-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-before-edit-accepted-1920x1080-light.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-after-edit-accepted-1920x1080-light.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-before-edit-accepted-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/llm-dialog-after-edit-accepted-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/run-1920x1080-dark.json | Each pair was shot after the dialog's open animation finished: before the edit Save is greyed out, after it Save is enabled. `saveDisabledBeforeEdit: true` and `saveEnabledAfterEdit: true` in both scenarios of all four runs. The refused scenario opens the dialog with Enter and activates Save with Enter (`walk.mjs`, the `scenario === "refused"` branch); the accepted scenario clicks Save. |
| UI-2 | pass | .dforge/ui-ux/audit-2026-11-20/demo-code-graph-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/demo-code-repositories-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/demo-code-wiki-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/demo-memory-graph-1920x1080-light.png, .dforge/ui-ux/audit-2026-11-20/demo-memories-1280x800-dark.png, .dforge/ui-ux/audit-2026-11-20/demo-notes-1280x800-light.png, .dforge/ui-ux/audit-2026-11-20/demo-jobs-1920x1080-dark.png, .dforge/ui-ux/audit-2026-11-20/demo-settings-llm-1920x1080-light.png, .dforge/ui-ux/audit-2026-11-20/llm-tab-1280x800-dark.png | Each screen was shot at both viewports in both themes (32 demo images, 4 of the real LLM tab). Every `*-overflow` key is `false` and every `*-landed` path is the route asked for. Demo page and console errors: 0 in all four runs. |
| OP-1 | pass | .dforge/ui-ux/audit-2026-11-20/run-1280x800-dark.json, .dforge/ui-ux/audit-2026-11-20/run-1280x800-light.json, .dforge/ui-ux/audit-2026-11-20/run-1920x1080-dark.json, .dforge/ui-ux/audit-2026-11-20/run-1920x1080-light.json | `demo.apiCalls: 0`. In real mode the only non-read requests were the save, fulfilled in the browser, and four provider model-probe POSTs the purpose dialog sends on open, all aborted (`writesAborted`). |

**Harness:** Vite dev on :3637 with `VITE_DEMO=1` for the demo screens, with every `/api/` request aborted and counted. Vite dev on :3636 running this tree for Settings → LLM, proxying reads to the local backend on :8000, signed in with a one-hour session minted inside the container and deleted after the run. One script, `.dforge/ui-ux/audit-2026-11-20/scripts/walk.mjs`, run once per viewport and theme. Both servers were stopped afterwards.

## Automated checks

- page and console errors, demo: 0 in all four runs.
- page and console errors, real: 5 per run, all produced by the harness. Four are `net::ERR_FAILED` for the aborted model-probe POSTs and one is the 409 the refused scenario forces.
- Two earlier attempts at 1920x1080 dark each recorded nine `net::ERR_NETWORK_CHANGED` errors. Another project's short-lived container (`dc-run-lock`) starts periodically on this host, and each start changes a network interface, which makes Chromium cancel requests in flight. Those attempts were discarded and the combination re-run until it recorded none; the run files kept are the clean ones.
- horizontal overflow: none on any screen at either viewport.
- `npm test`: 300 files, 2,437 tests, all passed. `npm run typecheck` (`tsc -b`) clean. `npm run build` passed.
- `ui-lint` on the changed files: four findings in `globals.css`, all on lines the change did not touch (the change only deleted an 18-line block).
- accessibility scan: not run; the change adds no element.

## Not proven here

- Reaching Edit and Save with Tab. The script puts focus on each control directly and then presses Enter, so it shows both respond to the keyboard, not that Tab arrives at them.
- The success toast's second line is the raw field name that changed (`params`). That copy predates this change and is not in the delta.
- That no "Saved" toast shows before the response arrives. The code calls it only from the mutation's success callback, and the walk sees it after a fulfilled response, but no test holds a response open to look.
- The real Code Graph view's Mermaid dialog. It uses the same generator, but production holds no indexed repository to open it on. `real-code-graph-view.test.tsx` renders it.
- The classifier-kind switch on the LLM tab, which shares the new success and failure paths. It is covered by `settings-llm.real.test.tsx` only.
- The Copy Mermaid button, which this change did not touch. Audit finding F1-11 records that it misreports a failed copy.
- A refused LLM save closes the purpose dialog, so the typed edit is gone when the error toast appears (`dialogStillOpen: 0`). That behaviour predates this change and belongs with audit finding F2-7; the toast now at least says the save failed.
- Before-and-after comparison of the UI-2 screens. The removed files had no importer, which the import graph, `knip`, `tsc -b` and the build each confirm, so there was no before state to differ from.
