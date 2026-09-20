# Page attachment storage — open follow-ups

Carried from the plan ledger before its workspace was deleted. Items the final
fix wave closed (read-only guard ordering, the unguarded `.staging` listing,
the CLAUDE.md `pages.attachments` mention and inventory count, dev-compose
volume, cancel-after-commit unlink, logging deleted ids) are omitted.

## Owner decision

- **Final review, spec §3.6 arm 2:** `page_attachment_cleanup` deletes every
  row-less file older than one hour. An app booting against a wrong or freshly
  recreated database while `ATTACHMENTS_DIR` points at the real volume wipes
  the attachments within about 80 minutes. The drop/recreate runbook relies on
  this. Raised options: bound deletions per run, refuse when the table is empty
  but files are many, or use `grace_hours`. Unchanged on this branch.

## Deferred before the schema freeze

- **Final review 7:** `uploaded_for_page_id` has no index, so a hard page purge
  seq-scans `page_attachments` for the `SET NULL`. The plan's Contracts fixed
  the index set at two; adding one regenerates the baseline.
- **Task 1:** the attachment `project` is not tied to its page's project by the
  schema; the door decides.

## Deferred, behaviour

- **Task 4:** zero-byte uploads are accepted (service and route).
- **Task 4:** `is_attachment_upload_path` ignores the request method, so any
  method on that path shape skips the edge cap (non-POST 405s without reading a
  body).
- **Task 4 / final review 11:** `ScopedGZipMiddleware` may compress attachment
  responses under an uncompressed-bytes ETag.
- **Final review 5:** upload `open()`/`write()` run on the event loop; a 50 MB
  body is several hundred blocking writes.
- **Task 6:** staging arm and shard/entry checks follow symlinks; no writer
  creates any.
- **Task 6 / final review 9:** the reference scan reads `blocks.text` only.
  Increment 2's editor upload must keep the URL in `blocks.text`; pin it with a
  test there.
- **Task 6:** the `_HAS_EXPIRED` gate stops bounding cost after one week
  (steady-state regexp scan each tick).
- **Task 3 / spec §3.7:** `docker-compose.worker.yml` has no attachments volume,
  so the read-only worker 404s attachment GETs (backups sub-project).

## Deferred, tests

- **Task 1:** `test_created_at_defaults` asserts only `is not None`.
- **Task 2:** `test_dir_check_refuses_an_unwritable_dir` skips as root, so the
  `AttachmentsDirUnusable` raise path has no executed coverage.
- **Task 3:** the deployment tests assert the Dockerfile `mkdir`, the compose
  `ATTACHMENTS_DIR`/mount path and the boot call by literal string, so comments
  or reformatting can false-pass or break them.
- **Task 4:** no route-level test for a non-UUID id (422) or a traversal-shaped
  `X-Filename`; `store_upload`'s DB-failure unlink has no executed test
  (parked; the row-less arm is the backstop).
- **Task 6:** the `in_table` case is a paragraph with a pipe, not a
  `table_row`; no row-with-missing-file test; no exact grace-boundary test;
  commit-before-unlink order is asserted by source reading only (parked).

## Discovered

- **Task 5:** `runbook-deployment.md`'s volumes paragraph sits after the
  `COOKIE_SECURE` line rather than at the section end.
- **Task 5:** `deps.py:95` docstring first line is about 96 columns; lint not run.
- **Task 5:** CLAUDE.md carries an orphan short line ("allowlist review B1
  rejected — that") from the plan-mandated wrap.
