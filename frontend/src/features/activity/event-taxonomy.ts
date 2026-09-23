import type { FeedCategory } from "@/features/activity/types"

/**
 * Display-only grouping of the closed `event_type` vocabulary
 * (`app/services/events.py` EVENT_TYPES) into the feed's five filter tabs.
 * This is a UI convenience, not a taxonomy the backend enforces — an
 * event_type absent from every bucket below still shows under "all", it
 * just has no dedicated tab. (This once cited inject/inject_curbed as the
 * open example; T3.12 landed the writer module and both are recorded in
 * EVENT_TYPES_WITHOUT_TAB below, resolving that deferral. Only `inject_curbed`
 * has a caller today — see there.)
 *
 * T2.102 (2026-08-07) closed the gap that let three straight rounds each
 * find one value missing here and fix only that one (`contradiction_scanned`
 * T2.11, `citation_stale` T2.48): every EVENT_TYPES value with a live
 * `record_event` call site is now covered, either by a tab below or by an
 * explicit entry in `EVENT_TYPES_WITHOUT_TAB`. A value with no emitter yet
 * (landed taxonomy-first, ahead of its feature) owes neither, since
 * punishing that discipline is worse than the gap it closes.
 * `backend/tests/test_event_taxonomy_map.py` scans `backend/app` for live
 * emitters and fails the build the moment a value has one but lands in
 * neither list — that test, not this comment, is what keeps this true.
 *
 * T2.103 (2026-08-07) landed the auth/setup family into EVENT_TYPES (they
 * were emitted all along but outside the closed vocabulary) and fixed the
 * `setup_completed`/`setup_complete` spelling drift; see EVENT_TYPES_WITHOUT_TAB
 * below for where they landed in this map.
 */
const EVENT_TYPE_CATEGORY: Record<string, FeedCategory> = {
  created: "capture",
  document_filed: "capture",
  // Increment 8's block verbs. A block edit is a capture-side write to a
  // filed document, the same tab document_filed lands on.
  blocks_edited: "capture",
  // The metadata verb and the subtree rename. A retitle, move, pin or re-tag
  // is a capture-side write to a filed document, the same tab the other two
  // document writes land on.
  document_updated: "capture",
  // The subtree delete (increment 2). Capture, the same tab its three
  // document siblings land on: it is a write to filed documents.
  documents_deleted: "capture",
  // The page tree's lifecycle (increment A). Capture, the same tab the
  // document lifecycle events land on.
  page_created: "capture",
  page_updated: "capture",
  page_moved: "capture",
  page_deleted: "capture",
  page_restored: "capture",
  page_purged: "capture",
  // The Notion import's own row. Capture, the same tab the page lifecycle
  // events land on: it is a bulk write of pages into the tree.
  pages_imported: "capture",
  extracted: "pipeline",
  sources_changed: "pipeline",
  verified: "verification",
  contradiction_scanned: "verification",
  contradiction_dismissed: "verification",
  citation_stale: "verification",
  human_verdict: "verification",
  consolidated: "consolidation",
  merged: "consolidation",
  superseded: "consolidation",
  // An article labelled stale (T3.05). Consolidation rather than verification:
  // it says the knowledge under an article moved, and the re-synthesis it
  // precedes journals `superseded` into this same tab. Nothing about the
  // article's grounding is being asserted.
  article_stale: "consolidation",
  // A re-synthesis measured below the coverage bar. Verification rather than
  // consolidation: unlike `article_stale`, which says the knowledge moved,
  // this row carries a *measurement* of whether prose is entailed by facts,
  // which is the question the verification tab collects.
  resynthesis_held: "verification",
  deprecated: "consolidation",
  expired: "consolidation",
  invalidated: "consolidation",
  undone: "consolidation",
  repo_registered: "code",
  repo_synced: "code",
  repo_indexed: "code",
  repo_webhook_received: "code",
  repo_reindex_requested: "code",
  mcp_proxied_refused: "code",
  repo_hint_rejected: "code",
}

/**
 * EVENT_TYPES values with a live emitter that deliberately get no tab —
 * recorded here rather than left as a silent absence from
 * EVENT_TYPE_CATEGORY, so the next reader can tell "considered and
 * excluded" from "missed" (that ambiguity is what T2.102 was minted to
 * close). Each reason is why it does not fit one of the five tabs, not why
 * it lacks an emitter.
 *
 * Membership here does NOT mean a value is emitted today. `inject` is listed
 * and has no producer at all (below); it is here because the exclusion
 * decision was made, not because rows exist. Reading this list as "these are
 * all live" is invariant 23's mis-triage. The sentence that used to sit here
 * — "all four below are emitted for real" — was true when written (`19a19695`,
 * four members, every one emitted); by the commit before T3.12 the set held
 * twelve, so the count was stale by eight while the claim still held for every
 * member; T3.12 then added the first member with no emitter and made the claim
 * false. Corrected 2026-08-10.
 */
const EVENT_TYPES_WITHOUT_TAB = new Set<string>([
  // Inject records (T3.12). Doc 13 section 6.5 puts them in the
  // timeline/calendar and the Settings -> Distribution log, not in the feed's
  // five tabs: an inject is neither a capture nor a lifecycle step, it is
  // this installation telling a tool what it already knows. The docstring
  // above deferred this decision as one "this task does not own" -- T3.12,
  // which landed the writer, is the task that owns it, and it resolves to an
  // exclusion rather than a sixth tab because the surface doc 13 names
  // already exists.
  //
  // Of the two, only `inject_curbed` has a producer: PUT
  // /api/v1/distribution/policy journals the human turning the curb on.
  // `record_inject` has NO caller -- T3.10 owns the content fill and is held
  // by G-D -- so no `inject` row exists anywhere yet, and nothing will render
  // here until it does. `backend/app/services/inject_journal.py` states the
  // same split at the writer; this comment claimed T3.12 "made both types
  // live", which was never true of `inject`.
  "inject",
  "inject_curbed",
  // A session checkpoint is operational, not vault knowledge (T3.16): it is
  // an agent's note about its own run, so it is not a memory, fact or repo
  // lifecycle step and none of the five tabs models it. Its own surface --
  // the session-checkpoints / resume view in the Activity shell -- is
  // T3.21's, which is where this will be rendered rather than in the feed.
  "checkpoint_saved",
  // T3.17's resume. Same reasoning as its sibling above and the same
  // destination: a resume is one agent run reading another's note, which is
  // operational state rather than a memory, fact or repo lifecycle step. It
  // belongs on T3.21's session-checkpoints / resume view, beside the
  // checkpoint it resumed from, not scattered through the feed.
  "resumed",
  // The work-log lane's lifecycle (spec 2026-09-23). Operational state like
  // the checkpoint pair above: a client's own work, not a memory, fact or
  // repo lifecycle step, so none of the five tabs models it. Its surface is
  // the project workspace's Work log view.
  "workstream_opened",
  "workstream_closed",
  "workstream_reopened",
  "workstream_purged",
  // A research run's own row (T3.07). Excluded rather than tabbed under
  // capture: every memory the run filed journals its own `created` row, so
  // tabbing the run alongside them would show one research run twice in the
  // capture feed. The run row exists for the manufactured-origin audit — how
  // many rows this installation researched into itself, and when — which is a
  // measurement surface, not a lifecycle step.
  "research_run",
  // Generic system housekeeping (re-embed sweeps, maintenance jobs) —
  // not a memory/fact/repo lifecycle step any of the five tabs models.
  "maintenance_run",
  // The block-embedding backstop job's run summary (spec 2026-08-23):
  // how many document blocks it embedded this tick. Same reasoning as
  // maintenance_run above — housekeeping on the embedding partitions, not
  // a memory/fact/repo lifecycle step any of the five tabs models.
  "block_embeddings_refreshed",
  // A human accepting/dismissing a topic pin suggestion — curation on a
  // subject, not a memory or fact transition; no tab covers that surface
  // yet and T2.53's scheduler that would drive it hasn't landed.
  "pin_decision",
  // memory_buffer poison-row triage (requeue/discard), surfaced by the
  // buffer monitor rather than the feed's capture tab, which is about
  // completed captures, not the retry queue behind them.
  "buffer_requeued",
  "buffer_discarded",
  // The auth/setup security-audit family (T2.103): served by its own
  // GET /auth/audit surface, not the memory/fact/repo lifecycle feed —
  // none of the five tabs models a login, logout, password change, admin
  // setup, or a rate-limit lockout.
  "auth_setup",
  "auth_login_success",
  "auth_login_failed",
  "auth_logout",
  "auth_password_change",
  "auth_lockout",
  "setup_complete",
  // The API-key lifecycle (T4.01). Same reasoning as the auth family above,
  // and the same destination: a credential mint or revocation is a security
  // event about the box, not a memory, fact or repo lifecycle step, so none
  // of the five tabs models it. Doc 18 section 5 puts it on the Settings key
  // list beside `last_used_at`; T4.04 owns rendering the keyed calls
  // themselves on the per-object timeline, which is a different surface again.
  "api_key_created",
  "api_key_revoked",
  // The off-host ship's outcomes (increment 6). Same reasoning as the auth
  // family and the API-key pair above: a snapshot leaving the host is an
  // operational fact about the box, not a memory, fact or repo lifecycle
  // step, so none of the five tabs models it. Its surface is the Backups
  // settings tab, which reads these rows back per destination — including
  // the verify failure, which an operator needs beside the destination it
  // belongs to rather than scattered through a lifecycle feed.
  "backup_shipped",
  "backup_verify_failed",
])

export function categoryOfEventType(eventType: string): FeedCategory | null {
  return EVENT_TYPE_CATEGORY[eventType] ?? null
}

export function isDeliberatelyUntabbed(eventType: string): boolean {
  return EVENT_TYPES_WITHOUT_TAB.has(eventType)
}
