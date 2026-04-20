/**
 * Where the re-embed progress page lives. During Phase 2 (PR 2) the old
 * `/pipeline` re-embed page is still at `/pipeline`, so we navigate there.
 * Phase 3 (PR 3, Task 24) flips this to `/reindex` once the rename happens.
 */
export const REEMBED_ROUTE = "/pipeline" as const
