# Page editor images and files — open follow-ups

Carried from the plan ledger before its workspace was deleted. The final review's 8 parked minors are not itemised in the ledger and are not recoverable here; the two Important findings and four of the minors were closed by the fix wave (`d9ac23a..69aec60`).

## Owner decisions and hazards

- **Deployed 2026-09-20, without a drop.** The only baseline change since production's stamp (`fe0313068316`, the `bb82d1a9` baseline) was the `page_attachments` table and its two indexes, so the runbook's additive path applied: DDL derived from a fresh migrate, backup `darkmem-20260920-192607.sql.gz`, stamp re-adopted as `4ba88074cac57ced`, live schema diffed equal to a fresh migrate. Documents stayed at 477. This also retires the "deploy is owed and destructive" entry in `attachment-backups-followups.md`, and the nightly attachment-tarball stage now has its table and its `darkmem-prod_attachment_data` volume.
- **Any image URL becomes an `image` block**, attachment or external (owner ruling, spec §2), which is why `img-src` is `'self' data: https:`. `http:` is absent on purpose; adding it is the owner's call.
- **An upload that resolves after its pane unmounts is lost** to the editor, and the attachment row stays orphaned until the sweep. Recorded as a design change in spec §8 and CLAUDE.md rather than fixed.
- **A pasted captioned figure loses its caption and width on reload** (cv-3-1): markdown keeps only `url` and `name`, so there is no place to store them, and no phantom edit is sent.
- **`frontend/nginx.conf:37` caps `/api/` bodies at 25m**, below the app's own attachment limit. Not live while the nginx-in-image fallback is not taken.

## Deferred minors, by task

- **Task 3** — `block-mapping.ts:223` early return for an empty url also skips walking `block.children`, so children under an unfilled placeholder drop out of the desired tree (the server would refuse them anyway). `:217,226` `String(props.url ?? "")` coerces a non-string prop to a non-empty string; unreachable now that Task 4 declares the props. `asStandaloneFile` gates only links on `isAttachmentUrl`, so an existing paragraph holding an external image now becomes an image block; it round-trips byte for byte and no test covers it. Line-length nits at `block-mapping.ts:2` and `block-mapping.test.tsx:28`. Parked: the block-mapping test mirrors the URL pattern as a literal (the cross-file pin is `attachments.test.ts`).
- **Task 4** — `editor-schema.tsx:94-96` comment cites "the installed matcher", a BlockNote internal not verifiable from this repo. `mountEditor` duplicates `mountHook` in `use-page-editor.test.tsx`.
- **Task 5** — parked: the flip-on-failure recording assertion for a foreign prop on a paragraph (spec §13 sanctions it).
- **Task 6** — `INLINE_IMAGE_TYPES` is re-declared with a hand-written pin and no derivation guard; drift only turns an image into a download chip. The `subscribeUploads` unsubscribe is never asserted, and no test covers two concurrent uploads composing to 2 then 0. `setInFlight` notifies listeners in a bare `for`, so a throwing listener aborts the rest and would leak the count at the increment site. `uploadAttachment` has no `AbortSignal` or timeout, so a stalled request holds the unload warning for the tab's lifetime.
- **Task 8** — `use-page-editor.ts:88-90` failure path retypes the block to an empty paragraph, but for a list item that still holds a child the nesting guard refuses that, so the loader would persist; the comment overstates the outcome. The sonner mock is never reset between tests; the `!anchor` empty-document branch and a call with no `blockId` are untested. Parked: the `uploadFile` closure reads `editor` inside its own declaration, and the recovery insert assumes sibling placement.
- **Task 9** — `use-page-sync.ts:195` `as SyncStatus` could be `as const`; the module-global upload count would paint "Saving…" on another page if the pane switches mid-upload (theoretical); the test mock's listener set is never cleared between tests.
- **Task 10** — parked: the download-button assertion reads source text (paired with a real export check).
- **Plan header** — states eleven tasks and six self-implemented; the index lists twelve and seven.
