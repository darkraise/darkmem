"""The decided inventory of every front door that returns memory-derived data.

Three consecutive sweeps (T1.29a, T1.29c, T1.29d) enumerated this subsystem and
came back incomplete, and they failed the same way each time: each one
enumerated **retrieval channels** and stopped, while the rows that kept escaping
came out of **memory-content surfaces**. The two are different sets, and this
module exists so the next reader inherits the distinction rather than
rediscovering it.

* A **retrieval channel** answers a caller's question by *choosing* rows. The
  caller never named them, so which rows come back is the answer, and project /
  status / archived isolation is a correctness property of the choice. Every one
  of these filters in SQL; T1.29a-d closed the last of them.

* A **memory-content surface** returns memory-derived data as a side effect of
  an operational job — a backfill queue, a triage list, a dashboard, an
  append-only journal. Nothing here is answering a retrieval question, so
  isolation is not automatically the right default: a pipeline-failure screen
  that hid other projects' failures would be a worse tool, not a safer one.
  These carry a **decision**, and the decision may legitimately be
  deployment-wide. What is not acceptable is a surface nobody has decided.

Hence ``Scoping``. ``SCOPED`` means the predicates ride the SQL. ``ID_ADDRESSED``
means the caller named the row, so a scope predicate would be a tautology (and
would break lineage inspection, which is the one place a superseded row must be
reachable). ``OPERATOR_WIDE`` is a recorded decision to stay deployment-wide,
with the reason on the row. ``ESCALATED`` means the question is open and its
owner is the human, not this code.

``labels`` is the second half of the defence and the reason a wrong decision
degrades safely rather than silently: a surface that emits ``project`` and
``status`` on every row it returns is self-describing, so a row that escapes
through a consumer nobody enumerated arrives carrying the scope it came from.
T1.35's bar counts *unlabelled* cross-project and superseded rows, so labelling
is what makes an operator-wide surface honest instead of merely wide.

**Consumers.** T1.35's isolation probe drives one case per row and must cover
``memory_content_surfaces()`` as well as ``retrieval_channels()`` — a probe
built from the retrieval list alone returns a clean zero over the whole
operational half. T1.42d's parity audit reads ``front_doors`` for the REST/MCP
split and ``operator_wide_surfaces()`` for the scoping exemptions.

**The guard.** ``tests/test_content_surface_scoping.py`` asserts that every route
the app registers and every MCP tool it exposes is either claimed by a surface
here or listed in ``ROUTES_WITHOUT_MEMORY_CONTENT`` /
``MCP_TOOLS_WITHOUT_MEMORY_CONTENT``. Adding a front door without classifying it
fails the build. That is the mechanism the three sweeps did not have.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SurfaceKind(str, Enum):
    RETRIEVAL_CHANNEL = "retrieval_channel"
    MEMORY_CONTENT_SURFACE = "memory_content_surface"


class Scoping(str, Enum):
    SCOPED = "scoped"
    ID_ADDRESSED = "id_addressed"
    OPERATOR_WIDE = "operator_wide"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class ContentSurface:
    """One front door, what memory-derived data crosses it, and its decision."""

    key: str
    kind: SurfaceKind
    front_doors: tuple[str, ...]
    crosses: tuple[str, ...]
    scoping: Scoping
    labels: tuple[str, ...]
    decided_by: str
    reason: str


_R = SurfaceKind.RETRIEVAL_CHANNEL
_S = SurfaceKind.MEMORY_CONTENT_SURFACE


CONTENT_SURFACES: tuple[ContentSurface, ...] = (
    # -- retrieval channels ------------------------------------------------
    ContentSurface(
        key="memory_search",
        kind=_R,
        front_doors=("POST /api/v1/memories/search", "POST /api/v1/memories/search/paginated",
                     "mcp:memory_search"),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29a",
        reason="Semantic, hybrid, keyword and relational arms all render project, "
               "status and is_archived into the SQL the database executes.",
    ),
    ContentSurface(
        key="memory_reason",
        kind=_R,
        front_doors=("POST /api/v1/memories/reason", "mcp:memory_reason"),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29c",
        reason="Retrieves through the same scoped arms before the reasoning model "
               "sees anything. Its project default is every project, ratified.",
    ),
    ContentSurface(
        key="chat_retrieval",
        kind=_R,
        front_doors=("POST /api/v1/chat/completions",),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29c",
        reason="Everything retrieved here lands in the chat model's context "
               "verbatim, so an unscoped row becomes a user-visible answer.",
    ),
    ContentSurface(
        key="graph_memory_context",
        kind=_R,
        front_doors=("GET /api/v1/graph/memory-context/{memory_id}",),
        crosses=("content", "memory_id"),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29d",
        reason="Neighbour memories are excluded by project, status and archived; "
               "the relation arm deliberately keeps no status predicate so an "
               "edge whose only asserter is superseded survives.",
    ),
    ContentSurface(
        key="bulk_partition_read",
        kind=_R,
        front_doors=("GET /api/v1/vectors/projection", "GET /api/v1/graph/unified"),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29d",
        reason="get_all_vectors joins memories unconditionally, so every row is "
               "labelled even for a filters=None caller, and the scope applies "
               "before the LIMIT. Single-fingerprint by construction.",
    ),
    ContentSurface(
        key="duplicates_probe",
        kind=_R,
        front_doors=("GET /api/v1/memories/{memory_id}/duplicates", "mcp:memory_find_duplicates"),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T1.29d",
        reason="The scope is derived from the source memory rather than accepted "
               "from the caller, so neither door can widen it.",
    ),
    ContentSurface(
        key="code_search",
        kind=_R,
        front_doors=("POST /api/v1/code/search", "mcp:code_search"),
        crosses=("code_content",),
        scoping=Scoping.SCOPED,
        labels=("repo_id",),
        decided_by="T1.29c",
        reason="Code chunks are not memories: their isolation key is repo_id, "
               "pushed down on both the semantic and the symbol arm. Listed "
               "because the isolation probe must still drive it.",
    ),

    # -- id-addressed memory-content surfaces ------------------------------
    ContentSurface(
        key="memory_by_id",
        kind=_S,
        front_doors=("GET /api/v1/memories/{memory_id}", "PUT /api/v1/memories/{memory_id}",
                     "POST /api/v1/memories/{memory_id}/merge",
                     "mcp:memory_get", "mcp:memory_update"),
        crosses=("content",),
        scoping=Scoping.ID_ADDRESSED,
        labels=("project", "status"),
        decided_by="T1.29d",
        reason="A direct reference by id is not a search. Lineage inspection has "
               "to reach a superseded row, and the response already names its "
               "project and status.",
    ),
    ContentSurface(
        key="memory_write_echo",
        kind=_S,
        front_doors=("POST /api/v1/memories", "POST /api/v1/memories/batch",
                     "mcp:memory_add", "mcp:memory_batch_add"),
        crosses=("content",),
        scoping=Scoping.ID_ADDRESSED,
        labels=("project", "status"),
        decided_by="T1.29e",
        reason="The caller is reading back the rows it just wrote, including the "
               "settle re-read on wait_process.",
    ),

    # -- operational memory-content surfaces -------------------------------
    ContentSurface(
        key="reembed_backfill_queue",
        kind=_S,
        front_doors=("GET /api/v1/reembed/obsolete/memories",),
        crosses=("content_preview",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project", "status"),
        decided_by="T1.29e",
        reason="Re-embedding is a fingerprint-partition backfill, not a retrieval. "
               "Every row of every project and every lifecycle state needs a "
               "vector under the active embedder, and the write path is unscoped "
               "for the same reason — a scoped preview over an unscoped backfill "
               "would let an operator read the queue as empty while whole "
               "projects stayed unembedded. The anti-join no longer degrades to "
               "a predicate matching every row: when the active partition is "
               "absent the count stays exact and the enumeration is withheld.",
    ),
    ContentSurface(
        key="pipeline_failure_triage",
        kind=_S,
        front_doors=("GET /api/v1/pipeline-failures",),
        crosses=("content_preview",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("entity_project", "entity_status"),
        decided_by="T1.29e",
        reason="The triage queue's job is every unresolved failure in the "
               "deployment; a screen that hid another project's failures would "
               "misreport the system's health. The join is addressed by "
               "pf.entity_id, so it returns only the memory the operator is "
               "already being shown a failure for, and a lifecycle predicate "
               "would blank the preview for exactly the rows needing triage.",
    ),
    ContentSurface(
        key="dream_cycle_digest",
        kind=_S,
        front_doors=("GET /api/v1/dream-digest/cycles/{cycle_id}",),
        crosses=("summary",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T2.13",
        reason="A refine action journals the summary it replaced and the one "
               "it wrote, so the digest's before/after carries memory-derived "
               "content by construction — that is what makes the action "
               "undoable at all, and withholding it would leave a curator "
               "approving a reversal they cannot see. Operator-wide for the "
               "same reason pipeline_failure_triage is: a cycle is one "
               "night's consolidation across the deployment, and a digest "
               "that hid another project's actions would misreport what the "
               "pass did. Each action still carries its own project label. "
               "Note the journal is append-only, so a preview here outlives "
               "deletion of its memory — the retention question that spans "
               "events and chat citations is escalated and unresolved, not "
               "this surface's to settle.",
    ),
    ContentSurface(
        key="review_queue_facts",
        kind=_S,
        front_doors=("GET /api/v1/review-queue/facts",),
        crosses=("fact_content",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T2.22",
        reason="The review queue's job (doc 08 §6) is every disputed or "
               "under-sourced fact the deployment holds, ranked by consequence "
               "not arrival order; a screen that hid another project's disputes "
               "would misreport the system's truth backlog the same way "
               "pipeline_failure_triage's would misreport its health backlog. "
               "review_state='open' is the sole membership predicate — see "
               "app/services/review_queue.py for why it is never a bind "
               "parameter.",
    ),
    ContentSurface(
        key="review_queue_articles",
        kind=_S,
        front_doors=("GET /api/v1/review-queue/articles",),
        crosses=("content_preview",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T2.22",
        reason="Same triage-queue reasoning as review_queue_facts, over "
               "knowledge_articles instead of knowledge_triples. No producer "
               "writes this table yet (article_synthesis is a placeholder "
               "until T3.02), so the arm is exercised in tests against seeded "
               "rows only — the decision is about the surface's scope, not "
               "about live volume.",
    ),
    ContentSurface(
        key="knowledge_facts_browsing",
        kind=_S,
        front_doors=("GET /api/v1/knowledge/facts",),
        crosses=("fact_content",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T2.36a",
        reason="Doc 13 §5.1's Facts tab lists the vault the deployment holds, "
               "and `project` is a filter the caller applies rather than a "
               "scope the door imposes: a browsing surface that silently "
               "showed one project would make the other projects' facts look "
               "absent, which on a truth surface reads as 'we know nothing "
               "about that' rather than 'you are looking elsewhere'. Every "
               "item carries its own project. Nothing is filtered by "
               "verification status by default either — doc 08 §6's "
               "never-a-gate rule — so a candidate and a disputed fact are "
               "listed alongside a corroborated one, each labelled.",
    ),
    ContentSurface(
        key="knowledge_fact_detail",
        kind=_S,
        front_doors=("GET /api/v1/knowledge/facts/{fact_id}",),
        crosses=("fact_content",),
        scoping=Scoping.ID_ADDRESSED,
        labels=("project",),
        decided_by="T2.36a",
        reason="One fact by id, with its provenance rows grouped under the "
               "origin that wrote them so the badge's distinct-origin count "
               "can be counted back. The caller already names the row, so a "
               "project predicate would only decide whether a known id "
               "answers or 404s. It serves a belief-withdrawn row too: "
               "retained history that cannot be read answers nothing, and "
               "the belief window on the response says which it is.",
    ),
    ContentSurface(
        key="analytics_recents",
        kind=_S,
        front_doors=("GET /api/v1/analytics/overview",),
        crosses=("content",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project", "status"),
        decided_by="T1.29e",
        reason="Every other number on this dashboard is deployment-wide, and "
               "supersession is itself recent activity, so the recents list is "
               "labelled rather than narrowed. Archived rows stay excluded.",
    ),
    ContentSurface(
        key="capture_buffer_triage",
        kind=_S,
        front_doors=("GET /api/v1/memory-buffer", "POST /api/v1/memory-buffer/{buffer_id}/requeue"),
        crosses=("content_preview",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T1.29e",
        reason="Buffer rows are pre-flush captures with no memory status or "
               "is_archived yet, so project is the only scope that exists. It is "
               "an optional parameter riding the SQL and defaulting to every "
               "project, consistent with the ratified reason default, and every "
               "row already names the project it came from.",
    ),

    # -- the journal surfaces: an open retention question ------------------
    ContentSurface(
        key="event_journal",
        kind=_S,
        front_doors=("GET /api/v1/events", "GET /api/v1/events/timeline",
                     "GET /api/v1/analytics/pipeline-logs"),
        crosses=("content_preview", "summary"),
        scoping=Scoping.ESCALATED,
        labels=("project",),
        decided_by="T1.29e",
        reason="Not an isolation question — project rides the SQL and defaults to "
               "every project, as on the buffer. The open question is retention: "
               "a buffer_discarded row carries a 500-char content_preview in its "
               "payload, events is append-only by design, so deleting a memory "
               "does not remove its content from the journal. Escalated to the "
               "human; no redaction scheme may be invented here. "
               "T2.13 added `summary` to the crossing list: the consolidation "
               "stream's refine action journals the summary it replaced and the "
               "one it wrote, which is what makes the action undoable at all, "
               "and this door serves those payloads. The crossing predates "
               "T2.13 — T2.12 shipped the writer — but no probe fixture "
               "produced one until the dream digest's driver did, so it went "
               "undeclared. It falls under exactly the same escalated retention "
               "question and widens it by no new principle.",
    ),
    ContentSurface(
        key="chat_history_citations",
        kind=_S,
        front_doors=("GET /api/v1/chat/conversations/{conversation_id}",),
        crosses=("content_preview",),
        scoping=Scoping.ESCALATED,
        labels=("project", "status"),
        decided_by="T1.29e",
        reason="Retrieval was wide on the project axis when the answer was "
               "produced, so each persisted snippet names the project and "
               "lifecycle state its memory carried at citation time. The open "
               "question is retention, not scope: chat_messages.context keeps a "
               "150-char snippet of every cited memory and nothing prunes it "
               "when the memory is deleted. The same retention property as the "
               "event journal, in a second store — escalated with it.",
    ),

    # -- memory identity without content -----------------------------------
    ContentSurface(
        key="entity_browser",
        kind=_S,
        front_doors=("GET /api/v1/graph/full", "GET /api/v1/graph/entities",
                     "GET /api/v1/graph/entities/{entity_id}/neighbors"),
        crosses=("memory_id",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=(),
        decided_by="T1.29e",
        reason="No memory content crosses; the memory_ids arrays do. Entities are "
               "deliberately not memory-scoped (one row per name+type, asserted "
               "by many memories), so trimming the array would break the "
               "neighbour derivation that consumes it and would make the global "
               "entity browser lie about which memories assert a fact.",
    ),
)


ROUTES_WITHOUT_MEMORY_CONTENT: frozenset[str] = frozenset({
    "GET /health",
    "GET /api/v1/analytics/stats",
    "POST /api/v1/analytics/reprocess",
    "POST /api/v1/analytics/reprocess/stream",
    "GET /api/v1/auth/audit",
    "GET /api/v1/auth/me",
    "GET /api/v1/auth/security-posture",
    "POST /api/v1/auth/change-password",
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/logout",
    "POST /api/v1/auth/refresh",
    "DELETE /api/v1/chat/conversations/{conversation_id}",
    "GET /api/v1/chat/conversations",
    "PATCH /api/v1/chat/conversations/{conversation_id}",
    "POST /api/v1/chat/conversations",
    "GET /api/v1/code/files/{repo_id}",
    "GET /api/v1/code/graph/{repo_id}",
    "GET /api/v1/code/symbols",
    "GET /api/v1/code/symbols/lookup",
    "GET /api/v1/code/symbols/{symbol_id}",
    "GET /api/v1/code/wiki/{repo_id}",
    "POST /api/v1/code/blast-radius",
    "GET /api/v1/config/repo-allowlist",
    "PUT /api/v1/config/repo-allowlist",
    "GET /api/v1/config/classification-areas",
    "GET /api/v1/config/feature-flags",
    "GET /api/v1/config/llm",
    "GET /api/v1/config/repos-path",
    "GET /api/v1/config/system-prompts",
    "GET /api/v1/config/theme",
    "POST /api/v1/config/llm",
    "PUT /api/v1/config/feature-flags",
    "PUT /api/v1/config/repos-path",
    "PUT /api/v1/config/system-prompts",
    "PUT /api/v1/config/theme",
    "GET /api/v1/events/calendar",
    "GET /api/v1/jobs",
    "POST /api/v1/jobs/{key}/trigger",
    "PUT /api/v1/jobs/{key}",
    "PUT /api/v1/jobs/{key}/config",
    "DELETE /api/v1/memories/{memory_id}",
    "POST /api/v1/memories/delete",
    "GET /api/v1/memory-buffer/stats",
    "DELETE /api/v1/memory-buffer/{buffer_id}",
    "GET /api/v1/pipeline",
    "GET /api/v1/pipeline/metrics",
    "GET /api/v1/pipeline-failures/counts",
    "GET /api/v1/pipeline-failures/{failure_id}",
    "DELETE /api/v1/pipeline-failures/{failure_id}",
    "POST /api/v1/pipeline-failures/retry-all",
    "POST /api/v1/pipeline-failures/{failure_id}/retry",
    # Aggregate counts per cycle: timestamps, action tallies and project
    # names, never a payload's before/after. The cycle detail that does carry
    # content is classified above.
    "GET /api/v1/dream-digest/cycles",
    # Reversal verbs. The response names the fields each inverse restored and
    # the state it deliberately did not, never a field's value.
    "POST /api/v1/dream-digest/actions/{event_id}/undo",
    "POST /api/v1/dream-digest/cycles/{cycle_id}/undo",
    # An adjudication verb, not a read: it withdraws belief and journals the
    # human's verdict, and returns 204, so no memory-derived row crosses it.
    "POST /api/v1/review-queue/facts/{fact_id}/reject",
    "GET /api/v1/reembed/obsolete-counts",
    "GET /api/v1/reembed/obsolete/code-chunks",
    "GET /api/v1/reembed/obsolete/entities",
    "POST /api/v1/reembed/all",
    "POST /api/v1/reembed/code-chunks",
    "POST /api/v1/reembed/entities",
    "POST /api/v1/reembed/memories",
    "POST /api/v1/reembed/prune-cache",
    "DELETE /api/v1/repos/{repo_id}",
    "DELETE /api/v1/repos/{repo_id}/tasks/{task_id}",
    "GET /api/v1/repos",
    "GET /api/v1/repos/stats",
    "GET /api/v1/repos/{repo_id}",
    "GET /api/v1/repos/{repo_id}/tasks",
    "POST /api/v1/repos",
    "POST /api/v1/repos/{repo_id}/reindex",
    "PUT /api/v1/repos/{repo_id}",
    "GET /api/v1/review-queue/counts",
    "GET /api/v1/setup/fs/list",
    "GET /api/v1/setup/fs/roots",
    "GET /api/v1/setup/status",
    "POST /api/v1/setup",
    "POST /api/v1/setup/probe-models",
    "GET /api/v1/system/fs/list",
    "GET /api/v1/system/fs/roots",
    "GET /api/v1/tags",
})


MCP_TOOLS_WITHOUT_MEMORY_CONTENT: frozenset[str] = frozenset({
    "mcp:code_blast_radius",
    "mcp:code_changes",
    "mcp:code_communities",
    "mcp:code_context",
    "mcp:code_dependencies",
    "mcp:code_file_symbols",
    "mcp:code_processes",
    "mcp:code_rename",
    "mcp:code_symbol",
    "mcp:list_repos",
    "mcp:memory_delete",
    "mcp:memory_stats",
    "mcp:memory_tags",
})


def retrieval_channels() -> tuple[ContentSurface, ...]:
    return tuple(s for s in CONTENT_SURFACES if s.kind is SurfaceKind.RETRIEVAL_CHANNEL)


def memory_content_surfaces() -> tuple[ContentSurface, ...]:
    return tuple(s for s in CONTENT_SURFACES if s.kind is SurfaceKind.MEMORY_CONTENT_SURFACE)


def operator_wide_surfaces() -> tuple[ContentSurface, ...]:
    return tuple(s for s in CONTENT_SURFACES if s.scoping is Scoping.OPERATOR_WIDE)


def escalated_surfaces() -> tuple[ContentSurface, ...]:
    return tuple(s for s in CONTENT_SURFACES if s.scoping is Scoping.ESCALATED)


def surface(key: str) -> ContentSurface:
    for s in CONTENT_SURFACES:
        if s.key == key:
            return s
    raise KeyError(key)


def declared_front_doors() -> frozenset[str]:
    return frozenset(door for s in CONTENT_SURFACES for door in s.front_doors)
