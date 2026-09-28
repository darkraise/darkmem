# Keyed document PATCH — open follow-ups

Carried from the plan ledger before its workspace was deleted. Items the
final fix wave closed (parity-note wording, `DocumentHashConflict`
docstring) are omitted.

## Deferred, tests

- **Task 1:** no test pins stale-hash-plus-uri-collision ordering
  (`DocumentHashConflict` vs `DocumentUriConflict`) or a pinned-only call
  with a stale hash. Both are closed by construction — the hash guard sits
  in the same UPDATE's WHERE clause — but nothing exercises them directly.
- **Task 2:** the REST stale-hash test checks only that the uri stayed put,
  not that `document_updated`/tags did too. The service-layer tests already
  prove both; nothing guards the route path itself.
- **Task 2:** no route-level test for an `expected_hash`-only body answering
  422 / `no_change`. The mapping predates this branch.

## Deferred, behaviour

- **Task 1:** `_refuse_unmatched_update`'s disambiguating read is unlocked,
  so a race could report `current_hash == expected_hash` on a conflict it
  lost. Nothing is written either way; a client retrying on `current_hash`
  retries correctly regardless.
- **Task 2 / final review:** `DocumentHashConflict`'s 409 text is
  hand-formatted at three call sites (put route, block mapper, page
  mapper) rather than built from `str(exc)`. Pre-existing pattern, not
  introduced by this branch; a future consolidation is a reasonable
  cleanup.

## Discovered

- **Task 1 / Task 2:** test output carries pre-existing `SAWarning`
  teardown noise (`transaction already deassociated from connection`) and
  177-1629 total warnings across runs; source not isolated to the new
  tests, but the warning is suite-wide and predates this branch.
- **Task 3:** a transient host disk-full incident hit the guards leg mid-run
  (`Postgres DiskFullError`); resolved by freeing the `uv` cache, and a
  clean rerun passed fully. Host condition, not a code defect.

## Cross-repo register note (not resolved by this session)

`docs/superpowers/registers/2026-09-24-darkmem-mirror.md` in the sibling
`darkraise-ai-plugins` checkout covers this plan's spec
(`docs/superpowers/specs/2026-09-28-darkmem-mirror-wiring-design.md`). Rows
#2 and #3 are noted "Needs the darkmem server half (§4) first" — that half
is now merged into darkmem `master` at `25ea1247`. Neither row is assigned
to this plan's path, so this session did not resolve them; the plugin repo's
register needs updating separately (out of scope for a darkmem-only merge).
