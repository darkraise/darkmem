# Attachment backups — open follow-ups

Carried from the plan ledger before its workspace was deleted. Deferred minors closed by the final fix wave (the `ship_all` build-state and read guard, the dangling `current` link and its message, the tarball-content assertion, the `--index-file` listing buffer) and the Task 6 parked inventory masking (closed by Tasks 11 and 12) are omitted. The full text of the 16 plan amendments is in `attachment-backups-amendments.md` beside this file.

## Owner decisions and hazards

- **The nightly timer runs the merged script.** `darkmem-backup.service` executes `/root/repositories/darkmem/scripts/backup.sh` from this checkout. Once this is on `master`, every 03:30 run executes the new tarball stage against production. The dump leg and its prune are unchanged and run first; the stage fails closed (no `page_attachments` table or attachment volume on the production database/stack until it is redeployed), so the unit reports failed with the dump intact until then.
- **Deploy is owed and destructive.** CLAUDE.md's redeploy rule applies (`backend/`, `docker-compose.worker.yml` and scripts changed), but the schema baseline this branch inherits is a drop-and-recreate of the production database, which no task was authorised to do. Nothing was built, pushed or deployed.
- **Closes an earlier owner decision.** `docs/superpowers/notes/page-attachment-storage-followups.md` lists the row-less sweep wiping a restored volume against an empty database as an owner decision; Task 14 refuses that sweep on an empty table or beyond `rowless_bulk_limit` (default 100). Update or retire that entry.
- **The worker is untested against real tools here.** The restore-cycle, receiver and `backup.sh` changes are exercised only through stubbed harnesses; `age` is not installed on this host (3 skipped tests) and `shellcheck` was not run. Bring-up on the worker machine is `docs/runbook-backup-worker.md`.
- **Task 2's `--index-file` and GNU-tar assumptions** hold for the Debian-based image; the shell producer runs tar inside `docker run` and counts `./`-prefixed stderr lines instead, because an index file would land inside the container.

## Deferred minors, by task

- Task 2: Family.matches uses `self is DUMPS` identity check (attachment_archive.py:63), redundant with disjoint suffixes and fragile for a by-value Family
- Task 2: save_state commits the caller's session (attachment_archive.py:131)
- Task 2: unused `from pathlib import Path` in test_attachment_archive.py:12
- Task 2: no test drives tar-failure branch (:177-181), .part cleanup on tar failure, or load_state partial-row None path
- Task 2: GNU-tar-only options and listing format are assumed but unstated in the module
- Task 2: the shell producer in scripts/backup.sh captures tar's stderr the same way, so it inherits the same inflated-member-count defect; the repair (an index file lands inside `docker run`'s container) is a design choice spec §4 would have to be amended for — the owner's call, raised by the seat, not amended
- Task 2: cancellation while awaiting tar's stderr does not kill the tar subprocess, so an orphan could recreate .part/.index after cleanup (pre-existing exposure for .part, the fix adds .index); neither suffix matches a family so no prune sees it
- Task 2: _TAR_FILE_CHANGED = 1 also matches tar's "some files differ" status, indistinguishable from other exit-1 causes
- Task 3: SshDestination.ship/read_back_sha256 per-call bound resolution on scp/mv/cat has no test (only _remote_names is exercised); a dropped `timeout or` would pass the suite — Task 6 passes these bounds, consider a monkeypatched _run assertion there
- Task 3: `timeout or CONST` treats timeout=0 as unset; Task 6 must never pass a computed bound that can be zero
- Task 3: SshDestination.ship's caller bound (7200s on the attachments leg) also bounds the post-upload mv that used to get 900s — brief-mandated, nothing shortens
- Task 3: JOB_PREFIX duplicates attachment_archive.DUMP_PREFIX with one user (run_dump); Task 5 rewrites run_dump and should collapse it
- Task 3: GREEN report shows 21 warnings unexplained (presumed pre-existing); mid-file noqa E402 import brief-verbatim
- Task 4: _StreamingFakeS3.__init__ drops the base _FakeS3's page_size kwarg (test_backup_ship.py:1162-1165)
- Task 4: S3Destination.stream closes the body only on exhaustion/aclose; a consumer that raises mid-loop (backup_pull.pull sink.write ENOSPC) defers close to the asyncgen finalizer — wrap call sites in aclosing before anyone adds an early break
- Task 4: body.close() raising inside the finally (backup_ship.py:872) could mask an in-flight read error
- Task 4: two new tests take an unused tmp_path (test_backup_ship.py:1173,1191)
- Task 5: constants comment in backup_ship.py (~:592-594) says the bounds "are passed" in present tense and implies all destinations resolve them; nothing passes them until Task 6 and only SshDestination resolves — reword when Task 6 lands the caller
- Task 5: BACKUP_SHIP_MAX_RUN_SECONDS sits under the ssh banner in backup_ship.py:594-601 though it is a job-registration constant (brief-mandated placement)
- Task 5: test_main_registers_the_job_with_that_budget asserts a substring anywhere in main.py; would survive the line migrating to another job (brief-verbatim)
- Task 5: test_the_run_budget_covers_one_destination_end_to_end is arithmetic over constants only; 6300s headroom for dump build, tarball build and other destinations is unmeasured
- Task 5: "Task N" section headers in tests (test_backup_config.py:232, test_backup_ship.py:1079,1155,1223) reference the task; retire all together at branch end
- Task 5: no test loads a stored backup_destinations row that predates attachments_retention_keep
- Task 6: a destination whose client fails to build is appended to attachments["verify_failed"] with no attachments-family journal row (plan-mandated); add a one-line comment saying the dump row carries the cause
- Task 6: with any unencrypted destination the plaintext tarball stays in DUMP_DIR (/dumps) and only a local destination prunes it; a worker-only unencrypted config accumulates one multi-GB tarball per changed night — record where retention advice lives (Task 16 docs)
- Task 6: ArchiveIncomplete imported but unused in backup_ship.py (brief-mandated so tests reach backup_ship.ArchiveIncomplete)
- Task 6: test helper _the_dump in test_backup_ship.py:386 lost its only caller; ARCHIVE_STAMP/ARCHIVE_NAME unused; _journal_attachment ignores destination/stamp params (brief-verbatim dead weight)
- Task 6: _NEWEST_ATTACHMENT_OUTCOME scans every monthly events partition with no created_at bound and no docstring justifying it
- Task 6: no tests for the listing-raises→ship path, the dump leg failing while the tarball still ships, or build_destination failure landing in attachments["verify_failed"]
- Task 7: test_backup_script.py:102 `assert _dumps(dest) == [dump]` is a tautology after the edit; the exact-directory guard is gone (only .part half recovered at :254) — assert the exact name set {dump, tar, tar.manifest}
- Task 7: backup.sh:135 `tail -5 "$TAR_LIST"` prints member lines, not diagnostics; :155-157 `trap - EXIT` precedes the mv so a failed rename leaves $TAR_PART (matches no glob); :163 non-integer BACKUP_ATTACHMENTS_KEEP silently skips prune (inherited convention); orphaned sidecars never pruned
- Task 7: mid-module imports with noqa E402 in test_backup_script.py:150-152; report narrative says twelve tests, diff has eleven
- Task 9: restore-cycle.sh:77 tar member safety rests on GNU tar defaults, unstated; no --no-same-owner/--no-same-permissions on a root-run cycle
- Task 9: restore-cycle.sh:119-120 DUMP_STAMP="${DUMP_STAMP%%.*}" truncates a hand-named dump with dots in the stamp; tighten the dump regex to [0-9]{8}-[0-9]{6}
- Task 9: restore-cycle.sh:97 a `current` that is a real directory makes mv -T fail inside the post-rename window; refuse in section 1 with [ -e current ] && [ ! -L current ]
- Task 9: missing tests — swap position between rename and $COMPOSE start (stub could log readlink current on stop/start); torn newer tarball while a generation is already served; leftover gen-<stamp>.tmp discarded; age stub -d|-i branch reads "$1" unguarded
- Task 9: the worker pairs only `.tar.gz.age` (restore-cycle.sh:132), silently ignoring a plain .tar.gz, consistent with the dump regex — say so in the Task 16 runbook
- Task 12: backups.test.tsx:21-28 imports waitFor and `waitFor as waitForHook` from the same module in one statement; drop the alias
- Task 12: outcomeKey's `family: string` (use-backups-tab-binding.ts:30) is weaker than BackupOutcome["family"], so a typo compiles and silently renders "no run yet" — plan-mandated by the Contracts signature
- Task 12: use-backups-tab-binding.ts:79 folds any family other than "attachments" into the dump bucket (brief-prescribed ternary); a guard with a `continue` on unknown families is safer
- Task 12: the destination fixtures carry no attachments_retention_keep, so the PUT-body assertion cannot observe the round trip, and the inventory fixtures go through an untyped routes() table with an `as DestinationInventory[]` cast — a typed fixture builder would help Task 13
- Task 13: the attachment <ul> in backups-tab.tsx (~255-271) is a verbatim 15-line copy of the dump <ul>; extract SnapshotList({snapshots, emptyText}) (plan-mandated)
- Task 13: the attachments_retention_keep input has no client-side bound and Number(e.target.value)||0 maps empty to 0 which the server rejects (loud 422; the sibling retention_keep has the same pattern) — fix both fields in one edit
- Task 13: no test asserts the OutcomeBadge "database:"/"attachments:" text or the second OutcomeLine; an implementation rendering only the dump family would pass all 17 tests (gap inherited from the brief)
- Task 13: DestinationRow shows only "keeps {retention_keep}" — no trace of the attachment retention in the list
- Task 14: test_page_attachment_cleanup.py:349 `assert len(list(root.rglob("*"))) >= 3` is near-vacuous (shard directories count); assert each staged path still exists (plan-mandated verbatim)
- Task 14: the third test's remedy row has no session.commit() unlike the two brief-named tests (:247, :273) — works via the shared connection, inconsistent
- Task 14: the refusal log names the count and reason but no sample of skipped paths, unlike the collecting branch's up-to-50 (brief-verbatim)
- Task 14: no test drives the runner with rowless_bulk_limit in the config dict, so the forwarding at page_attachment_cleanup.py:186 is only exercised through the default
- Task 7: the shell stage's tests never assert `.part`/`.list` absence on failure paths, the socket test does not assert the "Archive holds no files" message, and nothing covers the dump prune sparing tarballs or `psql` failing after a good dump (the tarball-content assertion was added in the final fix wave).

## Left by the final review

- Final review, `backup_ship.py`: when the attachments leg is skipped by the new read guard, every destination lands in `attachments["skipped"]` and the attachment prune still runs; `skipped` normally means "already holds it", so the summary's `error` key is the only signal of the cause, and no event is journalled.
- Final review, tests: no dedicated test for an encryption failure after a successful build (the `build_error` mechanism is exercised by the build-failure test).
- Final review, `restore-cycle.sh`: the spec §7.3 wording says `mv -T gen-<A>.tmp gen-<A>` is guarded by `test -d`; the script does `rm -rf gen-<A>` then `mv -T`. Equivalent in effect (that directory was never served) but not what the spec says.
- Final review, `restore-cycle.sh`: `tar -x` runs as root with GNU defaults, so `--same-owner` applies; the viewer needs files owned by the app uid in the archive, so `--no-same-owner` must NOT be added. State the assumption in the script.
- Final review, docs: `docs/runbook-deployment.md` unpacks over the live attachment volume without emptying it; files added after the dump stay behind as row-less files that the cleanup job refuses past `rowless_bulk_limit`. Say whether to empty `/dst` first or that the refusal is expected.
- Final review, `backup.sh`: `tail -5 "$TAR_LIST"` on a tar failure prints member lines, not diagnostics (`grep -v '^\./' | tail -5` would); a non-integer `$ROWS` or `$KEEP_TARS` silently skips the check or prune (inherited convention for `KEEP`).
- Final review, `attachment_archive.py:63`: `self is DUMPS` is an identity check; `self.prefix == DUMP_PREFIX` is the by-value form. `JOB_PREFIX` in `backup_ship.py` still duplicates `DUMP_PREFIX`.
- Final review, frontend: `Number(...) || 0` maps an emptied retention field to 0 (server 422, loud) on both retention inputs; `DestinationRow` shows only `keeps {retention_keep}`.
- Final review, `backup_ship.py`: a destination whose client fails to build is appended to `attachments["verify_failed"]` with no attachments-family journal row, so the tab's attachments line keeps showing the previous outcome while the dump line shows the failure.
