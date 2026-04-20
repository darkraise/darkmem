/**
 * Where the re-embed progress page lives. The old LLM-page flow used to
 * navigate to `/pipeline`; Phase 3 moved that page to `/reindex` and repurposed
 * `/pipeline` for the new pipeline UI, so this constant now points to
 * `/reindex`.
 */
export const REEMBED_ROUTE = "/reindex" as const
