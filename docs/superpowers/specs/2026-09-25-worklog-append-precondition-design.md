# Work-log append precondition

Date: 2026-09-25
Status: design, owner-approved on 2026-09-25.
Source: darkraise-ai-plugins
`docs/superpowers/specs/2026-09-25-darkmem-sync-hardening-design.md` §1 (the
dr-superpowers mirror's hardening), which carries the client half.

## Why

The dr-superpowers mirror pushes a ledger as the bytes appended since its last
push. Two mirrors, or two syncs on one machine, can append the same suffix at
once, and nothing on the server refuses the second copy. A compare-and-set on
the append closes that window, as `expected_hash` does for `document_put`.

## Design

`POST /api/v1/worklog/entries` and `worklog_append` gain an optional
`expected_last_seq` (integer, ≥ 0), through `WorklogAppendRequest`, which both
doors already validate with.

- With the field set, every entry of the append shares one kind; otherwise the
  schema refuses the request (422, or a validation error from the tool), and
  `worklog.append` raises `ValueError` for an in-process caller.
- Under the workstream row lock `_lock_or_create` takes, `worklog.append`
  compares the field with the seq of the workstream's newest entry of that
  kind, `0` when it holds none (seq starts at 1). A mismatch raises
  `WorklogSeqConflict` inside the append's savepoint, so nothing is kept — no
  entry, no workstream creation, no reopen. The route answers 409; the tool
  answers a `seq_conflict` envelope naming the kind, the expected and the
  current seq, as `document_put` answers `hash_conflict`.
- The check is per kind: a checkpoint filed into a workstream never
  invalidates a ledger's expectation.
- `AppendResult` and both doors' answers gain `last_seq`, the seq of the last
  entry the append wrote, which is the caller's next expectation.
- Without the field, an append behaves exactly as today.

Seq is a database-wide identity, not a per-workstream counter, so the
precondition names the last seq seen rather than the next one expected. The
existing index `ix_worklog_entries_kind_latest (workstream_id, kind, seq DESC)`
serves the lookup; no migration.

## Testing

Service: a match writes; a mismatch writes nothing, creates no workstream and
leaves a closed one closed; `0` opens a new workstream; the check ignores
other kinds; a mixed-kind append with the field raises `ValueError`; two
concurrent appends expecting the same seq admit exactly one; `last_seq` is the
seq of the last written entry. Doors: the route answers `last_seq`, a stale
expectation answers 409 naming the current seq, and the schema refuses a
negative value or a mixed-kind append; the tool answers `last_seq` and
`seq_conflict`. The parity table states the 409 / `seq_conflict` asymmetry on
the `worklog.append` row.
