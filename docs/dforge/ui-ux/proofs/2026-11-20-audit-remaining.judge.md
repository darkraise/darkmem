## Verdict
verdict: ship baf4bc9b68e67280
scores: coverage 16 / fidelity 16 / states 17 / deviations 15

## What I read

- **Criteria:** `ui-ux-proof.md`.
- **Contract:** the "UI/UX contract" section of `docs/dforge/specs/2026-11-20-audit-remaining-design.md` (UI-1 to UI-6, UX-1 to UX-12, OP-1 to OP-4) and its Acceptance list.
- **Report:** `docs/dforge/ui-ux/proofs/2026-11-20-audit-remaining.md`, including the "Fix-wave re-proof (2026-11-21)" section.
- **Previous judgment:** `docs/dforge/ui-ux/proofs/2026-11-20-audit-remaining.judge.md` (ship at 23b95bcca2d1f103).
- **Walker's results:** `.dforge/ui-ux/audit-remaining/fix-wave-results.md`.
- **Run files:**
  - `fw-ui-1-run-1280x800-dark.json`, `fw-ux-2-run-1920x1080-light.json`, `fw-ux-4-run-1280x800-dark.json`, `fw-ux-5-run-1920x1080-dark.json`, `fw-ux-1-flags-run-1920x1080-dark.json`
  - the earlier `ux-4-run-1280x800-light-409.json`, for comparison
- **Source and tests:**
  - `frontend/src/features/documents/components/block-editor.tsx` and its test file (the Discard, Retry and "Waiting" tests)
  - `frontend/src/features/activity/components/failed-captures-section.tsx` and its test file
  - the disabled conditions in `frontend/src/features/knowledge/components/hygiene-queue.tsx`

**Limit:** I had no shell, so I could not run `git diff 312cc2f5..e3652924 -- frontend/src`. I checked each fix-wave behaviour against the current source and the commit-to-item mapping the report gives. I did not check it against the diff itself. So I cannot confirm that the 13 changed files map one-to-one onto the 11 re-walked flows. That is Unknown; running that diff and comparing its file list with the report's commit list would settle it.

No row is marked unverifiable, so no `**Accepted by:**` line applies.

## Fix-wave evidence, item by item

I opened every `fw-*` screenshot the report cites: 37 shots across 9 rows. Each one shows the state its name claims.

- **UI-1:**
  - All six after-refetch shots (switcher, Code Graph and Wiki, at both viewports and both themes) show the loaded content still in place, with no failure state.
  - The three first-load-failed shots show the library empty-state with Retry: "Projects could not be loaded", "Repositories could not be loaded" ("forced 500"), and "Failed to load wiki".
  - A screenshot cannot show that the refetch actually failed. `fw-ui-1-run-1280x800-dark.json` does: 2 x 500 each for `/projects`, `/repos` and `/code/wiki/r1`, `failureStateCount: 0`, and `retryRecovered: true`.
- **UX-1:**
  - Flags dialog, at 1280 light and 1920 dark: 999 in the field, a red "Enter a value from 0 to 5." under it, and the edits kept. The run file records `aria-invalid="true"`, `aria-describedby` pointing at the `role="alert"` paragraph, and `saveDisabled: true`.
  - Notifications: chat id 77 with the token masked shows "Enter the bot token again to send alerts to another chat." The real 422 is toasted as "Couldn't save notification settings" with that same reason, and the typed chat id is kept.
- **UX-2:**
  - Both shots are the dashboard, because the minute check draws nothing.
  - The claim rests on the run file: 5 failed `/auth/me` reads at boot with 0 refreshes, then after one 61 s clock step, 1 good read and 1 `POST /auth/refresh`, still on `/`. I accept this as evidence for the minute-check path only.
- **UX-4:**
  - At both viewports, block 1 shows "Not saved: The document changed since it was read" with Retry and Discard. Block 2 shows "Waiting — not sent until the unsaved edit is retried or discarded", and no "Saving…" label is visible.
  - The after-Retry shots show both edited blocks persisted. The run file records 1 PATCH while waiting and 3 after Retry.
  - Discard was not pressed in this walk. It is covered at the current code by `block-editor.test.tsx` ("retry resends the box's text and discard drops it").
- **UX-5:**
  - Prune and Prune now are washed out while the prune request is held (1280 light). Confirm dedup and Supersede instead are disabled while their requests are held.
  - `fw-ux-5-run-1920x1080-dark.json` records every disabled flag and exactly 1 POST per action.
  - `hygiene-queue.tsx` disables every bulk button on an empty on-screen selection or while its request is pending.
- **UX-6:**
  - "Renamed by the proof" keeps the red "Title not saved" label, and the toast shows the server's reason.
  - After the stored title is typed back, the label reads "Saved", which is true. "Title not saved" is gone, and no PATCH was sent.
- **UX-7:**
  - With a file node selected, Run Blast Radius is disabled and the panel shows "Select a symbol to see its blast radius". The source pane reads "main.py is a file — select a symbol within it to view its source."
  - A symbol node enables the button.
  - In Edit repository, Save is disabled while the PUT is held, with the typed branch "develop" kept and the clone URL shown as text.
- **UX-8:** a truncated node's panel shows "Showing a preview; loading the full text…" while its read is held, and "Showing a preview: the full text could not be loaded." after the read fails. Once the full text loads, it is shown with no notice.
- **UX-12:**
  - Row 1's Requeue is disabled while its request is held, and row 2's Requeue stays enabled.
  - After the second Discard confirm, the list is unchanged and row 2's Requeue is disabled. The run files record 1 DELETE.

I compared each of these with the current source; the files are listed under "What I read". Every changed behaviour the re-proof claims is present in that code.

## Scores

**Every Item Has Evidence: 16.** All 22 contract items have a row with evidence I opened that shows the item. For the rows unchanged since the ship verdict, I relied on the previous judgment's sampling and re-opened `ux-4-1280x800-light-409-refused.png` to compare caret behaviour. The fix-wave evidence is complete for the items it re-walks. Three things in the report keep this at 16:
- **The UX-4 row note is stale.** It describes the earlier Discard walk ("those shots were replaced by the Discard ones"). Its first four cited shots are now the fix wave's Retry shots, which the note does not mention. Only the separate fix-wave section explains them.
- **The UX-6 row note no longer matches every cited shot.** It quotes the toast "Could not rename the page — title store unavailable". The fix-wave shots read "Could not rename the page — Internal Server Error".
- **The 13-file claim is unverified by me** (see Limit above).

**Built Matches Promised: 16.**
- Library components are used throughout: `empty-state` with Retry, `alert` text for the range error, disabled buttons, and toasts. The copy in every fix-wave shot matches the report's quoted strings and the contract's wording.
- Two observations hold the score at 16. Neither breaks a promise.
  - **Caret placement.** A block opened by click puts the caret at the start, so typed text lands before the existing text ("edited oneFirst paragraph.").
  - **Disabled primary buttons in dark theme.** They are hard to tell from enabled ones. The flags-dialog Save at 999 (1920 dark) and Confirm dedup with 0 pairs selected both look enabled, while the run file and the code say they are disabled.

**Every State Is Shown: 17.**
- This round adds these states, each at both viewports and both themes:
  - after a failed background refetch
  - pending and disabled for Requeue, Discard confirm, Prune, Prune now, Confirm dedup, Supersede instead, Edit repository Save and Run Blast Radius
  - invalid with `aria-invalid` and `aria-describedby`
  - refused and waiting
  - loading and failed for the preview
  - "Title not saved" cleared when the stored title is restored
- Keyboard: the disabled buttons are skipped by Tab, and Retry and Save were pressed by keyboard.
- Gaps the report names itself: the folded file-level graph, the successful Edit-repository save, the other Flags dialogs, and the 3D view for the preview notice.

**Deviations Are Cited: 15.**
- OP-4 is still the one deviation, and it still cites the ruling seat.
- The new observations are disclosed, but one is mislabelled. The report lists "the failed-captures Discard trigger stays enabled while a request runs (its confirm is guarded and silently sends nothing)" under "Observations outside this wave's diff". Its own fix-wave bullet credits ab64a325 with adding that guard ("a second Discard confirm while one runs sends nothing"). The silent no-op is therefore a product of this wave. That is inference from the report's commit mapping; I could not run the diff.
- It breaks no contract sentence (UX-12 promises deletion only on confirm, and that holds), so I do not dispute an item. It is the main reason this score is not higher.

## Disputed items

None.

## Findings outside the disputes

- **Important: a confirmed Discard can be silently dropped.**
  - Where: `failed-captures-section.tsx` lines 60-62 and 106-112.
  - What happens: the `discard` handler returns early when the row is `busy`, but the Discard trigger is not disabled while busy. Requeue sets that same flag. So an operator who presses Requeue and then Discard, or who confirms Discard twice, sees the dialog open, confirms the destructive action, and the dialog closes with no request and no message.
  - Why it is Important: no test covers it. `failed-captures-section.test.tsx` checks only the Requeue double-press.
  - Fix: disable the trigger while busy, or toast that a request is already running.
- **Minor: caret at the start of an opened block.**
  - Where: `block-editor.tsx` line 177. `area.current?.focus()` sets no selection, so in Chromium the caret starts at position 0.
  - Effect: the fix-wave walk typed " edited one" and got "edited oneFirst paragraph." The earlier walk got "First paragraph TYPED-TEXT-KEPT".
  - Probably not a fix-wave regression: the report says the earlier walk filled fields programmatically, which would explain the difference. That is inference; whether this line changed in b02b81c6 is Unknown.
- **Minor: disabled buttons in dark theme look enabled.**
  - Examples: `fw-ux-1-flags-1920x1080-dark-dialog-out-of-range-invalid.png` (Save) and `fw-ux-5-1920x1080-dark-hygiene-before.png` (Confirm dedup with 0 pairs selected). Both are disabled per the run file and the code, but look enabled.
  - Disabled controls are exempt from WCAG contrast. It is still a visual cue the fix wave relies on in dark theme. This is library styling, not in this diff.
- **Minor: the UX-12 shot after the second confirm still lists row 1 after "Capture requeued".** This is routed fixture data, and the report says queue data is fixtures. Not graded.
- **Carried from the previous round, unchanged:** the chat row's `nested-interactive` (not compared against master), the Table-view state select starting on "done", and the 14 Right-arrow presses to move a board card.

## Screenshots not opened

- **Fix-wave:** I opened every `fw-*` screenshot the report cites (37). I did not open uncited `fw-*` shots, such as the `*-loaded`, `*-before` and `*-settled` states, beyond `fw-ux-5-1920x1080-dark-hygiene-before.png` and `fw-ux-5-1920x1080-dark-confirm-dedup-held-disabled.png`, which I opened for comparison.
- **Rows unchanged since the ship verdict:** I re-opened only `ux-4-1280x800-light-409-refused.png`. For the rest I relied on the previous judgment's sampling, as the dispatch allows. Its "Screenshots not opened" list still applies.
- **Older evidence on the re-walked rows:** I did not re-open the non-fw shots of the nine re-walked rows (for example the Task 50 and Task 55 board stills and the earlier `ux-*` shots), apart from the UX-4 one above.

Verdict: ship baf4bc9b68e67280
