## Verdict
verdict: ship 4083c6ca12a023e4
scores: coverage 18 / fidelity 17 / states 17 / deviations 16

## What was read (round 2)

- Criteria: `/root/.claude-alt/plugins/cache/darkraise/dforge/5.1.1/criteria/ui-ux-proof.md`
- Contract: `docs/dforge/specs/2026-11-23-audit-followups-design.md`, "UI/UX contract" (UI-1..UI-6, UX-1..UX-7, OP-1..OP-4).
- Report: `docs/dforge/ui-ux/proofs/2026-11-23-audit-followups.md`, re-stamped at 4083c6ca12a023e4.
- My round-1 report (fingerprint 1e5f93ad97b66a0f). Its evidence reading for UI-2, UI-3, UI-4, UI-6, UX-2, UX-4..UX-7 and OP-1..OP-4 still stands; none of those rows or their files changed.
- Code I re-checked myself:
  - `frontend/src/features/settings/components/backups-tab.tsx`, lines 202-224 and 444-509.
  - `frontend/src/features/settings/use-backups-tab-binding.ts`, in full from line 40.
  - `frontend/src/features/chat/components/chat-sidebar.tsx`, lines 120-145.
  - `frontend/src/features/settings/__tests__/backups.test.tsx`, lines 490-541, including the new test at 515.
- Stories confirmed at their exports: `BackupsDestinationsFailed`, `BackupsInventoryFailed` and `BackupsOutcomesFailed` (`load-failure-states.stories.tsx` 391-393), and `RequeuePending` (`failed-captures-section.stories.tsx` 88).
- New evidence I opened:
  - UI-1: `UI-1-1280x800-light-outcomes-failed-fixed-real.png`, `UI-1-1920x1080-dark-outcomes-failed-fixed-story.png` and `UI-1-1920x1080-dark-outcomes-retried-ok-fixed-real.png`, plus `sb3-results.json` (all four viewport and theme pairs).
  - UI-5: `UI-5-1280x800-light-chat-many-fixed.png`, `UI-5-1280x800-dark-chat-many-clip-fix.png`, `UI-5-1280x800-light-chat-delete-confirm-clip-fix.png`, `UI-5-1920x1080-light-chat-many-clip-fix.png` and `retake2-chat-1280x800-light.json`.
  - UX-1: `UX-1-1280x800-light-dialog-address-changed-settled.png`, `UX-1-1920x1080-dark-dialog-api-kind-changed-closed.png` and `retake-provider-1920x1080-dark.json`.
  - UX-3: `UX-3-1280x800-light-caret-at-end-visible-0.png`, `UX-3-1920x1080-dark-caret-at-end-visible-1.png` and `retake-caret-1280x800-light.json`.
  - Every other re-capture the report cites exists on disk (checked by glob).

## Round-1 disputes, re-judged

- **UI-1: resolved.**
  - The code fix is correct. `DestinationRow` renders the two `OutcomeLine`s only when `outcomesKnown`. The tab passes `!outcomesError`, and `outcomesError` is `shipped.error ?? failed.error`, so a failure of either events query hides both lines.
  - Both harnesses show it. The story (1920 dark) and real mode (1280 light) show the row as "disk local keeps 14" with no outcome lines, above the failed state and Retry. `sb3-results.json` records `noRunYet: 0` at all four pairs.
  - The control shot (1920 dark, retried OK) shows "database: no run yet  attachments: no run yet" coming back after a successful read, so the lines are suppressed only while the read has failed.
  - The new test fails a regression. Its mock answers the outcomes read with `items: []` when it succeeds, so without the gate "no run yet" would render and `queryByText(/no run yet/)` would fail.
- **UI-5: resolved.**
  - The meta line is now `flex flex-wrap items-center gap-x-2`, with time and count each in a `whitespace-nowrap` span.
  - At 1280x800 the clip-fix captures show "just now" on one line and "120 msgs" whole on the next. Nothing is split word by word and nothing is cut.
  - `retake2-chat-1280x800-light.json` agrees: 30 rows, 55 spans, `clipped: 0`, `outside: 0`, `multiLine: 0`, row width 168.
  - At 1920x1080 every row holds time and count on one line.
  - The delete-confirm capture is now taken with the dialog settled: it is opaque, its copy is exact and focus is on Cancel.

## Round-1 weak evidence, re-judged

- **UX-1:**
  - The settled capture (1280 light) shows the exact hint under the key field, the key field in its invalid style, and Save disabled.
  - The listbox-closed capture (1920 dark) shows API kind set to "OpenAI-compatible", the hint, Save disabled and no listbox. `retake-provider-1920x1080-dark.json` records `listbox: 0`, `dialogOpen: 1`, `hint: 1` and `saveDisabled: true`.
- **UX-3:** the caret is now visible right after the last "word" in both captures I opened. `retake-caret-*.json` records `start = end = length = 1999` and `focused: true`.

## Criterion notes

**Every Item Has Evidence (18).**
- Every contract item has a row, and the evidence opens and shows that item.
- I took points off for evidence hygiene in the UI-5 row. Its Evidence column still lists the superseded `…chat-many-fixed.png` and `…delete-confirm-fixed.png` captures (the overflow-hidden attempt). Those visibly clip the count ("1 ms", "2 ms" in `UI-5-1280x800-light-chat-many-fixed.png`).
- The note says the clip-fix captures supersede them, but the names read the wrong way round: "-fixed" is the clipped attempt and "-clip-fix" is the final one. A later reader could easily cite the wrong one.

**Built Matches Promised (17).**
- UI-1 now matches the contract's intent: a failed read never presents as a definite empty answer.
- The UI-5 rows are two sibling buttons with a legible meta line.
- The UX-1 hint copy is exact, Save is disabled, and no PUT is sent.
- The UX-3 caret sits at the end of the text.
- The other items are unchanged from round 1 and match.
- Remaining minor issue, outside the contract: a refused Run now renders in the same muted text as a success (round-1 observation, still true).

**Every State Is Shown (17).**
- Failed, recovered, empty, zero/one/many, worst-case titles and counts, pending, refused, saving, invalid and keyboard focus are each shown at both viewports and both themes.
- The animation-time and open-listbox captures from round 1 have been replaced.
- These still rest on tests alone, which the criteria accept:
  - UX-2's return to enabled after the action settles.
  - UX-4's write queued behind a refused one.
  - UX-5's node click after a resize.

**Deviations Are Cited (16).** The report cites the 1,999-character block, the cloned UI-3 controls, the unrun `disabled-opacity.spec.ts`, the 502 status-text case and the withdrawn chat re-captures. Points off for two loosely stated differences, neither of which breaks the contract:
- **UX-3 scroll position:** the note says the captures were "re-taken with the textarea scrolled to its end". It does not say whether the app or the harness did the scrolling. In round 1, the capture without that step showed the textarea scrolled to the top.
  - Inference: on opening a long block, the caret is at the end but out of view until the user types.
  - The contract promises only the caret position, so this is recorded, not disputed.
- **Stale header:** the report header still says "Proven on the working tree at d27d27bf plus the uncommitted register edit". The re-captures were taken on a tree that also carries the uncommitted `backups-tab.tsx` and `chat-sidebar.tsx` fixes.

## Disputed items

None.

## Other observations (not disputed)

- **UI-1, loading state (Minor, new, inferred from code):**
  - `outcomesKnown` is false only on error, not while loading. While the destinations read has answered and the events reads are still in flight, each row briefly shows "database: no run yet" and "attachments: no run yet".
  - This is the same false claim as the round-1 dispute, held for the length of one request.
  - Gating on "the outcomes read has succeeded" rather than "has not failed" would close it. No capture or test covers it.
- **UI-5, no test pins the meta-line layout (Minor):** nothing would catch a regression of the `whitespace-nowrap` spans except a screenshot.
- **UX-6/UX-7:** a failed Run now is styled like a success (carried from round 1).
- **UX-4:** the keyboard Discard after a refusal is still not visible in `ux4_kbdFocusOrderAfterRefusal` (carried from round 1). It is unverified, not disputed; the named tests cover the behaviour.
- **Adjacent findings:** the review queue's "disputed" badge (4.47:1) and the provider dialog's field captions, both in the light theme, are in code this plan did not change. They are recorded, not fixed and not scored.
- **UX-1 disabled Save:** the dark-theme disabled Save is low-contrast. Disabled controls are exempt from WCAG 1.4.3.

Verdict: ship 4083c6ca12a023e4
