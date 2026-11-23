## Verdict
verdict: ship a31bf894b7e471db
scores: coverage 18 / fidelity 17 / states 16 / deviations 16

## Scope of this judgement

I read the criteria (`criteria/ui-ux-proof.md`), the contract's "UI/UX contract" section and its review rulings (no new state board was ruled, so the contract names none), and the proof report. Every file cited under `.dforge/ui-ux/audit-followups/` exists: 192 `-r2` PNGs, the pre-fix-wave PNGs and all 62 JSON records. I opened at least one capture per state per row, in both themes, and the records that carry the measured claims (`r2-documents-*.json`, `retake-caret-1280x800-light.json`). I also checked that every test the report names exists under `frontend/src`. I did not re-run any test.

## Per-row findings

- **UI-1 (kept).** All three failed states show the library `empty-state` in its failed kind, with the envelope message and one Retry. I checked destinations at 1280 light, inventory at 1920 dark and outcomes at 1280 light. No failed read claims "No destinations configured" or "no run yet". With the outcomes read failed, the row shows only "keeps 14". Add destination is disabled while the destinations read is failed or loading. The empty board ("No destinations configured") appears only after a successful empty read (1280 dark). The "Retrying…" label shows when a refetch follows an earlier success (1920 dark).
- **UI-2 (kept).** The banner text matches the contract sentence exactly (1280 light, 1280 dark). It is gone after the save (1920 dark).
- **UI-3 (kept).** In both themes the twins show the disabled button, input and select visibly dimmer than the enabled ones, and still readable (1280 dark, 1920 light). The report states plainly that the controls were cloned and disabled by script.
- **UI-4 (kept).** The Copy Mermaid trigger keeps its own width and sits at the end of its row. Its focus ring shows in dark (1280 light, 1920 dark).
- **UI-5 (kept).** The review queue renders cleanly (1920 dark). In the chat list after the clip fix, the meta line wraps whole with no truncated counts (1280 light). The tests named in the report exist.
- **UI-6 (kept).** The Integration tab shows no inject log (1280 dark). Test `renders no inject log` exists.
- **UX-1 (kept).** After the address changes, the hint text matches the contract, sits under the key field, and Save is disabled (1280 dark). After a key is typed, the hint is gone and Save is enabled (1920 light).
- **UX-2 (kept).** While a requeue runs, both of that row's buttons are disabled and the other row stays enabled (1280 light; discard at 1280 dark). After a failure, focus returns to Requeue with a toast (1920 dark). Zero rows and 200 of 237 rows render (1920 light, 1280 dark).
- **UX-3 (kept, with an Important finding below).** All four records show `selectionStart = selectionEnd = 2000` and `typedAppendsAtEnd: true`. A typed character lands after the last word (1280 dark, 1920 dark).
- **UX-4 (kept).** The leave dialog's title, body and buttons match the contract (1280 light). In the queued-behind-refused state, the "Waiting — not sent…" line shows (1920 dark). After Stay, focus is in the edit box with the edited text (1280 dark). The late-refusal toast capture caught the toast mid-animation; its text is in the record.
- **UX-5 (kept).** The inspector opens on the demo canvas (1280 light). The resize numbers are in `demo-code.json` and the test exists.
- **UX-6 (kept).** A 409 shows "A backup run is already in progress." (1280 light). A 500 whose message mentions 409 shows that message, not the busy sentence (1920 dark).
- **UX-7 (kept).** An envelope 500 shows "Destination disk is not writable" (1920 light). An empty-object 500 shows "API error: 500" (1280 dark). The 502 HTML case shows the status text; the report records it as an observation, which I accept, because the contract's fallback rule concerns the body.
- **OP-1 to OP-4 (kept).** Both viewports and both themes are present for every row I sampled. The worst-case data is covered, and the re-proof used a 2,000-character block.

## The walker's UI-1 observation: does it keep UI-1 and the contract?

**Yes, it keeps both.** I confirmed the behaviour in two places.
- In `UI-1-1280x800-dark-destinations-retry-pending-r2.png` and `UI-1-1920x1080-light-outcomes-retry-pending-r2.png`, the failed section disappears while Retry is in flight.
- In `backups-tab.tsx`, the failed state renders only while `isError` is true. TanStack Query moves a query that holds no data back to `pending` when it refetches, so `isError` drops and the label `retrying ? "Retrying…" : "Retry"` can never render on the first-load path.

Why this keeps the contract:
- UI-1 promises a failed state with a Retry button, an empty inventory only after a successful read, and (through A29) that Retry re-reads. All three hold.
- The contract promises no pending label for Retry.
- In the gap the section makes no false claim: no "No destinations configured", no "no run yet", and Add destination stays disabled.
- The gap looks exactly like the tab's own first load (`UI-1-1280x800-light-add-destination-loading-r2.png`): a blank region with Add destination disabled. That is existing loading behaviour, not a new wrong state.

What it costs, graded Minor:
- After a first-load failure, the operator's only feedback that Retry is running is the error block vanishing. If the read fails again, the block reappears, and that can look like nothing happened.
- The "Retrying…" branch is reachable only after an earlier success, and no unit test asserts it (none of the cited `backups.test.tsx` tests names it). A regression there would go unnoticed.

Making the label reachable would need either the failed state to stay up while `isFetching`, or a loading presentation for the destinations section. Neither is a contract obligation.

## Findings outside the contract's wording

- **Important: UX-3's caret is no longer scrolled into view, a regression from the fix wave that the report marks pass.**
  - Before the fix wave, `retake-caret-1280x800-light.json` recorded `scrollTop: 910` with `scrollHeight: 980` and `clientHeight: 70`, so the caret was in view.
  - At this fingerprint, all four `r2-documents-*.json` record `scrollTop: 0` with `scrollHeight: 1044` and `clientHeight: 70`.
  - So opening a 2,000-character block shows its first three lines in a 70 px box, with the caret about 1,000 px below the visible area. The captures named `caret-at-end` (for example `UX-3-1280x800-light-caret-at-end-r2.png`) show the start of the text, not the caret.
  - Text still lands at the end (`typedAppendsAtEnd: true`), so the contract sentence and register row 389's complaint ("typed text lands before the existing text") are met. But the user cannot see where they will type until the first keystroke scrolls the box.
  - The report's note "did not move the caret" is true of the selection only, and the report never mentions the scroll change it measured.
  - No test checks textarea scroll: `block-editor.test.tsx` "opening a block puts the caret at the end" asserts only `selectionStart`.
  - The likely fix is to scroll the textarea to `scrollHeight` after `setSelectionRange` in `block-editor.tsx` (lines 203–208), plus a scroll assertion. This is inference: I did not identify which d0cc0369 change caused the regression.
- **Minor: UI-2's second clear path is not driven.** The purposes dialog's save (`useUpdateLlmConfig`) relies on the `["health"]` invalidation with no named test. The report says so under "Not proven here". UI-2's wording does not require this path.
- **Pre-existing, not this plan's:** the light-theme axe `color-contrast` findings on the provider dialog's field captions and the review queue's "disputed" badge are correctly listed under Adjacent findings. Neither is a changed control, so OP-2 is unaffected.

## Scores

- **Every Item Has Evidence: 18.** Every UI, UX and OP item has a row whose evidence I opened, showing that item. UI-3's evidence uses injected twins, and the report discloses this.
- **Built Matches Promised: 17.** Copy, components and tokens match the contract in both themes. The UX-3 caret-visibility regression keeps this below the top band.
- **Every State Is Shown: 16.** Failed, loading, empty, recovered, pending, focus-returned, refused, queued-behind and worst-case data are all captured at both viewports and both themes. Points come off for two gaps: the first-load Retry pending state is a blank region, and the "Retrying…" label is untested.
- **Deviations Are Cited: 16.** The UX-7 502 observation and the UI-1 retry observation are recorded openly. The UX-3 scroll change was measured but left uncited, and the row is marked pass.

## Disputed items

None.

Verdict: ship a31bf894b7e471db
