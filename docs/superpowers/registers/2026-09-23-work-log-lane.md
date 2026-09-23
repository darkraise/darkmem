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
