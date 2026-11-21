## Verdict
verdict: ship 23b95bcca2d1f103
scores: coverage 16 / fidelity 16 / states 17 / deviations 15

Inputs read:
- the criteria (`ui-ux-proof.md`)
- the contract's "UI/UX contract" section and its Acceptance list
- the proof report
- my round-1 report (verdict fix 472f19c67f8bc722)
- the ruling the OP-4 row cites (`.dforge/rulings-preexec-4-report.md`)
- the changed source: `page-pane.tsx`, `block-editor.tsx`, `graph-detail-panel.tsx`, `real-memory-graph-page.tsx`
- the three new tests: `page-pane.test.tsx` "Title not saved", `block-editor.test.tsx` "Waiting — not sent until", and `graph-interactions.test.tsx` "takes focus when opened from its button and gives it back on close"
- the run files `op-2-run-*` (switcher, chat-return, board-keyboard), `ui-5-run-*`, `ux-6-run-*`, `ux-4-run-*` and `ux-9-run-1920x1080-dark-worklog.json`

No row is marked unverifiable, so no `**Accepted by:**` line applies. I did not re-read the two Storybook state boards this round; their stills are the same files I judged in round 1.

## Round-1 disputes, re-checked

All four are resolved.

- **UX-6: resolved.**
  - All four `ux-6-*-refused.png` shots show a red "Title not saved" beside the typed title "A title that the server refuses". No "Saved" label appears, and the sidebar still shows "Original title".
  - `ux-6-*-renamed-after-refusal.png` shows the label back to "Saved" after a successful rename.
  - `page-pane.tsx` sets `titleRefused` on error, clears it on success, and clears it on a page switch. The run files agree (`savedLabelBesideTitle: 0`, `labelRole: "status"`).
- **UX-4: resolved.**
  - All six `ux-4-*-queued-edit-held.png` shots I opened read "Waiting — not sent until the unsaved edit is retried or discarded" under the second edit. No "Saving…" appears.
  - The `ux-4-run-*` files show one PATCH while waiting, and both PATCHes after Discard is pressed by keyboard.
  - The `*-discarded.png` shots show the first block back to its stored text and the queued edit applied.
- **OP-2: resolved.**
  - Header switcher: opened, picked and retried by keyboard (`op-2-*-switcher-*.png`). The label changes to "project: proof-docs". The failed load shows "Projects could not be loaded" with Retry.
  - Chat: returned to the first conversation by Tab and Shift+Tab, with a visible focus ring and `aria-pressed` (`op-2-*-returned-to-first-by-keyboard.png`).
  - Board: a register card moved `open` to `planned` by keyboard (`op-2-*-board-after-keyboard-drag.png`).
  - Table view: "State of #2" changed `open` to `doing` by keyboard (`op-2-*-table-after-keyboard-state-edit.png`).
  - Memory graph details panel: focus now lands on "Close details" and returns to "Show details panel" (`ui-5-run-*`, and the four `ui-5-*-opened-by-keyboard.png` shots show the focus ring on Close).
  - The false "no keyboard path" claim is gone.
- **OP-4: now a cited deviation.**
  - The demo Triage tab still lacks "Failed captures" (`op-4-1280x800-light-demo-triage-no-failed-captures.png`).
  - The row cites the ruling, and the quoted sentence and the "report must state that the section is hidden in demo mode" condition both appear in `.dforge/rulings-preexec-4-report.md` (lines 3 and 13).
  - The citation is a delegated ruling seat, not the owner's own words. I accept it as the recorded decision under the owner's "Full dforge flow" choice.

## Scores

**Every Item Has Evidence: 16.** All 22 items have a row with evidence I opened that shows the item. The round-1 gaps are closed: UX-7 cites the re-centre test, UI-1 cites the switcher loading stills, and UX-2 cites `test_websocket.py`. These remaining note errors keep the score from going higher:
- **UX-6:** the note says the toast reads "API error: 500". Every shot reads "Could not rename the page — title store unavailable".
- **UI-3:** the note and "Not proven here" say the success toast text was not captured. All four `ui-3-*-copied-over-plain-http.png` shots show "Copied to clipboard".
- **UX-4:** "Not proven here" still says "Discard was shown but not pressed". The row and the run files show Discard pressed by keyboard.
- **UX-7:** the row claims "a failing request toasts 'Blast radius failed: …'" but cites no shot for it. `ux-7-1280x800-light-blast-failed-toast.png` exists and is not cited.
- **OP-4:** the note says "Demo views stay parallel to the real ones", which contradicts its own deviation verdict.

**Built Matches Promised: 16.** Library components are used throughout: `empty-state` with Retry, `pagination` (Previous and Next with `aria-disabled` at the ends), clipboard with toasts, and dialogs. The copy matches the contract, and the round-1 label contradictions are fixed. Two things hold the score at 16:
- **Code Graph at 1280x800:** the canvas is still about 176 px wide. The report now says `git diff master -- frontend/src/features/code` changes no pane width or inspector. I did not verify that diff, because I had no shell.
- **UX-5 wording:** the inline result banner says "1 applied, 2 refused" while the toast beside it says "1 succeeded, 2 failed" (`ux-5-1280x800-dark-partial-failure-failed-rows-selected.png`). This is minor.

**Every State Is Shown: 17.** Shown across the boards and the live shots:
- data states: loading, failed, empty, populated, zero, one and many rows, 230 rows, a 400-character unbroken error, a 64-character name and 20,000 nodes
- control states: pending ("Saving…" disabled), refused, out-of-range ("Enter a value from 1 to 20."), toggle reverted, disabled pager ends, and keyboard focus rings

The keyboard-only walk is now evidenced for every changed flow. The only gaps are the deliberately pointer-only canvas picks and the hygiene checkboxes, which were clicked rather than walked.

**Deviations Are Cited: 15.** Every difference I found is either cited or explained:
- OP-4 is marked deviation and cites the ruling.
- The 176 px canvas is attributed to pre-branch layout, with a stated diff.
- The harness artefacts from round 1 are each explained in the final "Not proven here" item.

Holding the score at 15: the chat row's axe `nested-interactive` finding is still "not compared against master", the same gap I raised in round 1 (see Findings).

## Disputed items

None.

## Findings outside the disputes

- **Important (unverified): chat row `nested-interactive`.**
  - What it is: `chat-sidebar.tsx` makes each conversation row `role="button" tabIndex={0}` and puts the Delete button (`aria-label="Delete conversation …"`) inside it. axe reports this as serious on the Chat page. It is a WCAG 4.1.2 problem for screen-reader users, and no test checks it.
  - Why it matters here: Delete is the control UX-3 changed, and Task 60 lists `chat-sidebar.tsx` as modified. Task 60's steps describe only a delete `onError` and stream changes, so the markup likely predates the branch. That is inference.
  - Status: Unknown whether this branch introduced it. Running `git diff master -- frontend/src/features/chat/components/chat-sidebar.tsx` would settle it.
- **Minor: Table view state select.** At 1920x1080 the open list starts focused on "done", not on the current value (`op-2-run-1920x1080-light-board-keyboard.json`). The report notes it; it still works.
- **Minor: keyboard board move.** The board card needed 14 Right-arrow presses to move one column. That is usable but slow, and the report does not discuss it.
- **Minor: work-log shot looks duplicated.** `ux-9-1920x1080-dark-filtered-after-append.png` lists "Ledger line 1-0" and "1-1" twice. The run file records three later reads all carrying `after=3`, even after two entries were appended. The hook advances `after` to the last held seq (`use-worklog-api.ts:212`), so this is most likely fixture text and request timing, not a defect. The report does not explain it.
- **Minor: harness state leaks across runs.** Pages and documents from earlier combinations appear in later shots (three "A title the server accepts" pages; several `waiting-*` documents). The `ux-4-run-1280x800-dark-500.json` file lists a `waiting-409-1280x800-light.md` block. None of this is graded.
- **Minor: UX-6 first shot.** `ux-6-1280x800-light-refused.png` shows a grey skeleton where the page body should be. The other three shots show "body". The state the row grades is still visible.
- **Adjacent, carried from round 1 (Minor): stale comment.** I did not re-check `frontend/src/features/activity/event-taxonomy.ts:123-124` this round. The file is modified in the working tree, so the comment may have been fixed.

## Screenshots not opened

**A42 items and round-1 disputes:** I opened every screenshot cited for UI-2, UI-3, UI-5, UX-6, UX-7, UX-8 and UX-9, including:
- both Task 53 stills
- all four Task 49 stills cited by UI-3 and UX-7
- all 10 new OP-2 shots
- every UX-6, UI-5 and UX-4 queued-edit-held shot

**Other rows:** I opened at least one shot per row per viewport.

Not opened:
- **Task 50 board:** 24 of the 26 cited stills. I opened `code-graph-failed-1280x800-light` and `llm-tab-failed-1920x1080-dark`, plus six others in round 1.
- **Task 45:** all four `flags-*` stills. The live `ui-4-1280x800-light-flags.png` was opened.
- **Task 55:** 6 of the 8 cited stills. I opened `flags-dialog-out-of-range-1920x1080-dark` and `toggle-reverted-1280x800-light`.
- **UI-1 live:** `ui-1-1920x1080-light-loading`, `ui-1-1280x800-light-failed`, `ui-1-1280x800-dark-retried`.
- **UI-4 live:** `ui-4-1920x1080-dark-flags`, and three of the four `distribution` shots.
- **UI-6:** four of six.
- **UX-1 live:** six of eight.
- **UX-2:** ten of twelve.
- **UX-3:** eight of ten.
- **UX-4:** all four `409-refused`, three `500-refused`, `409-discarded` at 1280x800 dark and 1920x1080 light, and `500-discarded` at 1920x1080 light.
- **UX-5:** eight of fourteen.
- **UX-10:** two of four.
- **UX-11:** two of four.
- **UX-12:** twelve of sixteen.
- **OP-1:** two of the four `ux-5-*-hygiene-one-and-many` shots it cites (the 1280x800 dark and 1920x1080 light ones).
- **OP-3:** `ux-7-1920x1080-dark-opened`, `ux-12-1280x800-dark-long-error`, `ux-12-1920x1080-light-long-error`, and three of the four `ux-8-*-graph-20k-2d` shots.
- **OP-4:** five of eight.

Verdict: ship 23b95bcca2d1f103
