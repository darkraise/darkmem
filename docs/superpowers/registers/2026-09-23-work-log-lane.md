# Register — separate working data from memories

**Source:** owner requests in the 2026-09-23 session (after the .195 → .199 memory migration and cleaning pass)
**Covers:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | separate memory(fact, decision, development notes, etc...) from working progress checkpoint, logs, etc... so pure memory will not polute by logs and other data, but coding cli still can store and retrieve their working data | docs/superpowers/plans/2026-09-23-work-log-increment-1-store-and-verbs.md | worklog store and verbs live on both doors (increment 1), searchable (2), UI (6); memory_search never returns an entry | doing | increment 1 (store and verbs, both doors) done; search (2), UI (6) remain |
| 2 | the checkpoint may already summarized by coding client | docs/superpowers/plans/2026-09-23-work-log-increment-1-store-and-verbs.md | checkpoint bodies stored verbatim, up to 65,536 characters, never re-summarised by the server | verify | increment 1 done on feat/work-log-lane; verbatim bodies to 65,536 chars; not yet deployed |
| 3 | they usually come with ledger and progress tracking documents (can see dr-superpowers plugin) | - | - | open | companion spec darkraise-ai-plugins 2026-09-23-darkmem-mirror-design.md; server half = keyed doc routes + manifest in increment 1, revisions in increment 3 |
| 4 | update the default injected promt in mcp to guide client not to create noised memory and logs-contained memories | docs/superpowers/plans/2026-09-23-work-log-increment-1-store-and-verbs.md | agent_instructions route working data to the work log; the no-log rule and its tests are committed | verify | instructions route working data to the work log; no-log rule and tests committed; not yet deployed |
| 5 | INtegrate with dr-superpowers to store the documents and progress tracking, reduce the repo polution | - | - | open | companion spec darkraise-ai-plugins 2026-09-23-darkmem-mirror-design.md |
| 6 | work-log schema tests: no accept/reject cases for the key/title length CHECKs or the two properties-size CHECKs | - | - | open | increment 1 follow-up (Task 1 minor) |
| 7 | work-log tests: a bad batch against a closed workstream must leave it closed and journal no workstream_reopened | - | - | open | increment 1 follow-up (Task 3 minor) |
| 8 | work-log tests: the first retention race test does not isolate FOR UPDATE (the reopen UPDATE takes the same lock) | - | - | open | increment 1 follow-up (Task 3 minor) |
| 9 | work-log tests: test_serializers_are_json_safe checks only json.dumps and seq, not field names or the ISO timestamp format | - | - | open | increment 1 follow-up (Task 3 minor) |
| 10 | work-log list tests: the list_workstreams id tie-break, the list_entries kind filter and the list_workstreams ordering are unpinned | - | - | open | increment 1 follow-up (Task 4 minors) |
| 11 | work-log list routes: a forged cursor with a timezone-less timestamp may answer 500 rather than 422; measure and map it | - | - | open | increment 1 follow-up (Task 4 minor; unmeasured) |
| 12 | work-log read routes: project, workstream and before query parameters are not NUL-checked and likely answer 500 | - | - | open | increment 1 follow-up (Task 5 minor; unmeasured) |
| 13 | document manifest: no test for a uri equal to the prefix (the uri = :prefix arm), and documents.py's require_scope bindings are not pinned like repos.py and memories.py | - | - | open | increment 1 follow-up (Task 7 minor) |
| 14 | document by-uri twin passes _user=None into document_blocks_route; safe only while that handler never reads _user | - | - | open | increment 1 follow-up (Task 7 minor) |
| 15 | agent-instructions test duplicates the every-tool test apart from one substring and does not assert the no-log rule survives | - | - | open | increment 1 follow-up (Task 9 minor) |
| 16 | CLAUDE.md: the seventh strict-journal caller says 'for the same reason' instead of stating it (an unrecoverable erase; the event is the only record of who ran it) | - | - | open | increment 1 follow-up (Task 9 minor) |
| 17 | worklog_append stamps actor as current_key_name() or source; worklog_update and worklog_purge use current_key_name() alone | - | - | open | increment 1 follow-up (final review F15) |
| 18 | spec §7 still says the wall allows no KnowledgeTripleRepository method; the implemented scan checks only write and promote methods | - | - | open | increment 1 follow-up (final review F16; preflight-28 park) |
| 19 | plan amendments A1-A14 live only in the untracked workspace; publish them with the plan | - | - | open | increment 1 follow-up (final review F13) |
| 20 | full final page of list_workstreams, list_entries and the manifest returns a cursor and one empty page follows (no limit+1 fetch) | - | - | deferred | harmless; plan-mandated (Task 4 and Task 7 minors) |
| 21 | update_workstream leaves the caller's Workstream expired after a CHECK rejection | - | - | deferred | parked: no door reads it after a rejection; fix is one session.refresh in the except IntegrityError branch if a later door does |
| 22 | list_workstreams/list_entries raise IndexError on limit=0 for an in-process caller | - | - | deferred | parked: both doors bound limit (ge=1); fix is one ValueError guard if an in-process caller appears |
| 23 | agent instructions dropped 'If nothing durable is left once the log is removed, save nothing.' | - | - | deferred | parked: spec §5 replaces the close; restore with one sentence plus an assertion if thin memories appear (increment 4 owns the warning) |
| 24 | test_worklog_wall.py imports are not isort-ordered | - | - | deferred | plan-mandated text; cosmetic |
| 25 | manifest shares the subtree rename/delete prefix blind spot (a leading-slash uri never appears under a non-empty prefix) | - | - | deferred | documented in CLAUDE.md; a mirror files only superpowers/... uris |
