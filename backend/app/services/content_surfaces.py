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
               "verbatim, so an unscoped row becomes a user-visible answer. "
               "Since T2.58 it retrieves through `LayerCompositionService."
               "search`, which pushes the same project and status scope down "
               "into every channel it asks; the project axis stays wide by "
               "ratified default and each row still names its own project and "
               "status, and a wide request does not ask the facts channel, "
               "which has no wide arm.",
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
        key="document_related_memories",
        kind=_R,
        front_doors=("GET /api/v1/documents/{document_id}/related-memories",),
        crosses=("content",),
        scoping=Scoping.SCOPED,
        # `status` rides the row because a related memory may be superseded or
        # deprecated, and a maintenance surface that hid that would invite an
        # edit to a row the pipeline has already retired. `project` rides it
        # because this declaration is only worth something if the label is on
        # the wire -- `RelatedMemoryItem` served no `project` until 2026-09-05,
        # so the guard was passing on the declaration alone.
        labels=("project", "status"),
        decided_by="spec 2026-09-05 §3",
        reason="The sibling documents reads sit in ROUTES_WITHOUT_MEMORY_CONTENT "
               "because no `memories` row crosses them. This one is different "
               "and is classified on what it actually returns: `m.content` for "
               "every related memory. The ranking is cosine over the vectors "
               "both sides already carry, not an entity walk, and the scope is "
               "still derived from the document rather than accepted from the "
               "caller -- `document_similarity.resolve_shared_fingerprint` "
               "picks the one partition both sides are embedded in, and the "
               "project predicate inside `_related_sql` binds the document's "
               "own project -- so the door has no wide mode and a caller "
               "cannot widen it. Single-door on REST; an MCP twin would hand "
               "an agent an L1-keyed memory list, which is "
               "graph.candidate_read's own block.",
    ),
    ContentSurface(
        key="memory_overview",
        kind=_R,
        front_doors=("GET /api/v1/knowledge/overview", "mcp:memory_overview"),
        crosses=("community_report", "topic_label"),
        scoping=Scoping.SCOPED,
        labels=("project",),
        decided_by="T2.21",
        reason="A community's report_string is prose the summarization purpose "
               "wrote about that community's member memories, so memory-derived "
               "content crosses here even though no memories row does. The door "
               "has no wide mode at all: `project` is a single bind parameter on "
               "`list_with_members`, so both doors read one project's "
               "memory_communities and there is no request that spans two. Every "
               "topic still names its project, and the reduce sees only the "
               "reports of the project asked for — a foreign community's report "
               "reaching the prompt would put another project's content into "
               "this project's overview text, where no label could recover it. "
               "No status axis exists: a community is not a memory and carries "
               "no lifecycle.",
    ),
    ContentSurface(
        key="knowledge_composed_search",
        kind=_R,
        front_doors=("POST /api/v1/knowledge/search", "mcp:knowledge_search"),
        crosses=("content", "fact_content"),
        scoping=Scoping.SCOPED,
        labels=("project", "status"),
        decided_by="T2.72 (MCP), T2.80 (REST)",
        reason="Doc 12 §3's composed four-layer read. `project` is a required "
               "keyword on `LayerCompositionService.search` and is pushed down "
               "by both channels it fans out to — `MemoryFilter(project=…)` on "
               "the memory hybrid and the facts channel's own bind parameter — "
               "so there is no wide mode to request and no arm that could "
               "answer one. T2.58 widened the *service* parameter to accept a "
               "`None` project for the chat door's ratified wide default, and "
               "that changed nothing here: this door binds a required string "
               "with its own default, and a `None` project does not ask the "
               "facts channel at all rather than asking it wide. It is a "
               "retrieval channel rather than an "
               "operational surface for the ordinary reason: the caller names "
               "a query, not rows, so which rows come back is the answer. Each "
               "memory row keeps the hybrid's `status` label and each fact its "
               "project, and a fact's supporting memories arrive nested inside "
               "it carrying their own labels rather than flattened into the "
               "parent's. T2.80 added the REST twin doc 12 §2 assigns; it "
               "spends the same composition call with the same required "
               "`project`, so the scope is one pushdown and not two.",
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
        front_doors=("GET /api/v1/knowledge/facts/{fact_id}", "mcp:fact_get"),
        crosses=("fact_content",),
        scoping=Scoping.ID_ADDRESSED,
        labels=("project",),
        decided_by="T2.36a, T2.72",
        reason="One fact by id, with its provenance rows grouped under the "
               "origin that wrote them so the badge's distinct-origin count "
               "can be counted back. The caller already names the row, so a "
               "project predicate would only decide whether a known id "
               "answers or 404s. It serves a belief-withdrawn row too: "
               "retained history that cannot be read answers nothing, and "
               "the belief window on the response says which it is.",
    ),
    ContentSurface(
        key="knowledge_articles_browsing",
        kind=_S,
        front_doors=("GET /api/v1/knowledge/articles",),
        crosses=("article_content",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T3.06",
        reason="Doc 13 §5.2's Articles tab, and the same reasoning its Facts "
               "sibling carries: `project` is a filter the caller applies "
               "rather than a scope the door imposes, because a browsing "
               "surface that silently showed one project makes the others "
               "read as absent. It crosses an excerpt of the synthesised "
               "prose — which is derived from verified facts and never from "
               "a raw memory or a document block (the doc-16 firewall), so "
               "the content it exposes is the vault's own settled claims. "
               "Nothing is filtered by verification status: a stale or "
               "candidate article is listed and labelled, never withheld.",
    ),
    ContentSurface(
        key="knowledge_article_detail",
        kind=_S,
        front_doors=(
            "GET /api/v1/knowledge/articles/{article_id}",
            "mcp:article_get",
        ),
        crosses=("article_content", "fact_content"),
        scoping=Scoping.ID_ADDRESSED,
        labels=("project",),
        decided_by="T3.06",
        reason="One article by id: the grounded prose plus the fact text "
               "behind each citation, so a claim's support is readable "
               "without a second fetch per citation. The caller already names "
               "the row, so a project predicate would only decide whether a "
               "known id answers or 404s. It serves a superseded article too "
               "— lineage that cannot be read is not lineage — and a citation "
               "whose fact is no longer believed, flagged rather than hidden, "
               "because hiding it would leave an uncited claim on the page.",
    ),
    ContentSurface(
        key="hygiene_queue_duplicates",
        kind=_S,
        front_doors=("GET /api/v1/hygiene-queue/duplicates",),
        crosses=("memory_ids", "content_preview"),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project",),
        decided_by="T2.23, T2.87",
        reason="The hygiene queue's job (doc 08 §6) is every open "
               "candidate-duplicate pair the deployment holds; hiding "
               "another project's would misreport the housekeeping backlog "
               "the same way review_queue_facts' scoping argument does. "
               "T2.23 shipped only the two endpoint ids, score and verdict — "
               "no content crossed. T2.87 added each endpoint's own "
               "content_preview and created_at, truncated at the same 200 "
               "chars hygiene_queue_memories declares: a supersede direction "
               "cannot be told from ids and a score alone, and building a "
               "direction picker without them would be the UI inventing an "
               "adjudication. The endpoint ids stay id-only exposure; the "
               "previews are the new content crossing.",
    ),
    ContentSurface(
        key="hygiene_queue_memories",
        kind=_S,
        front_doors=(
            "GET /api/v1/hygiene-queue/low-confidence",
            "GET /api/v1/hygiene-queue/expiring-soon",
            "GET /api/v1/hygiene-queue/superseded",
        ),
        crosses=("content_preview",),
        scoping=Scoping.OPERATOR_WIDE,
        labels=("project", "status"),
        decided_by="T2.23",
        reason="Same triage-queue reasoning as review_queue_facts/articles, "
               "over memories instead of knowledge_triples/knowledge_articles "
               "— low-confidence, expiring-soon and superseded-lineage "
               "housekeeping, each an operator-wide backlog a project filter "
               "would misreport the same way pipeline_failure_triage's would.",
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

    ContentSurface(
        key="knowledge_topics_browsing",
        kind=_S,
        front_doors=("GET /api/v1/knowledge/topics", "GET /api/v1/knowledge/topics/{label}"),
        crosses=("community_report", "topic_label"),
        scoping=Scoping.SCOPED,
        labels=("project",),
        decided_by="T2.39a",
        reason="browse_topics/get_topic (T2.20) read straight off memory_communities, "
               "scoped by a required `project` bind parameter with no wide mode -- the "
               "same shape memory_overview (T2.21) already carries for the same "
               "underlying rows. A community's report_string is prose the "
               "summarization purpose wrote about that community's member memories, "
               "so memory-derived content crosses even though no memories row does. "
               "get_topic resolves by (project, label), so a cross-project read for a "
               "label seeded in another project answers 404, never that project's "
               "topic.",
    ),
    ContentSurface(
        key="knowledge_pin_suggestions",
        kind=_S,
        front_doors=("GET /api/v1/knowledge/topics/pin-suggestions",),
        crosses=("community_report", "topic_label"),
        scoping=Scoping.SCOPED,
        labels=("project",),
        decided_by="T2.39a",
        reason="diff_topics/compute_pin_suggestions (T2.20) read the same "
               "project-scoped memory_communities rows as topic browsing, plus "
               "knowledge_triples/knowledge_articles gates keyed on the same project. "
               "Accept and dismiss (POST .../accept, .../dismiss) return no "
               "memory-derived content -- 204, listed in "
               "ROUTES_WITHOUT_MEMORY_CONTENT, the same shape T2.05's ratify/reject "
               "doors use.",
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
    # The EH1 documents surface (TH1.16). **Document** content crosses these —
    # block spans, a summary, entity names — but no `memories` row does, and
    # this registry's claim is about memory content, exactly as it is for the
    # code browser's own routes below. Classified here rather than as a
    # content surface because a content-surface entry obliges an isolation
    # probe driver over the memory fixture corpus, and driving these doors
    # against memory fixtures would produce zero sightings and a permanently
    # vacuous "clean" result — a worse answer than a stated classification.
    #
    # The scoping question is still answered, just not by this registry: the
    # block channel joins `documents` and filters `project` in SQL
    # (`tests/test_block_retrieval.py` proves a foreign project's blocks
    # cannot consume the probe's limit), and the connections query scopes the
    # same way (`tests/test_document_connections.py`).
    # The auto_research config row (T3.28): an arm switch and two budgets.
    # No memory content crosses — it configures whether the research loop may
    # run at all, and the rows a run files are the capture doors' surface.
    "GET /api/v1/config/auto-research",
    "PUT /api/v1/config/auto-research",
    # The backup destinations row (increment 6). Hosts, buckets, retention
    # counts and masked credentials -- the snapshots themselves carry every
    # memory in the database, but they leave as opaque bytes down a wire this
    # door only names, and no `memories` row is read to serve either verb.
    "GET /api/v1/config/backup-destinations",
    "PUT /api/v1/config/backup-destinations",
    # The snapshot inventory (increment 7). Filenames, sizes, timestamps and
    # a per-destination verification badge -- the snapshots themselves carry
    # every memory in the database, but this door names them rather than
    # opening them, and reads no `memories` row to serve the page.
    "GET /api/v1/backups/inventory",
    # The run listing and re-derivation (T3.28's trigger half). No memory
    # content crosses either: the listing serves a run's subject, its
    # journalled counts and how many of its rows are still live, and the
    # re-derivation serves counts alone. Neither reads a memory's `content`
    # -- re-extraction hands the rows to the pipeline in-process and returns
    # a tally, so the content never reaches the response.
    "GET /api/v1/config/auto-research/runs",
    "POST /api/v1/config/auto-research/runs/{event_id}/rerun",
    "GET /api/v1/documents",
    # The sync manifest: uri, hash and time per document, no content at all.
    "GET /api/v1/documents/manifest",
    # A document's revisions: the contents its filings wrote, with hash, actor
    # and time. Document content crosses, never a `memories` row.
    "GET /api/v1/documents/{document_id}/revisions",
    "GET /api/v1/documents/{document_id}/revisions/{revision_id}",
    "GET /api/v1/documents/{document_id}/summary",
    # The summarize trigger. Same classification as its GET twin: the prose
    # is generated from this document's own blocks, so document content
    # crosses and no `memories` row does. It spends a model call, which is a
    # cost question rather than a scoping one -- `refuse_when_read_only` on
    # the route is what answers that.
    "POST /api/v1/documents/{document_id}/summary",
    "GET /api/v1/documents/{document_id}/connections",
    "POST /api/v1/documents/qa",
    # The write door: filing and deleting a document. Same classification as
    # the reads above and for the same reason -- never a `memories` row, so
    # there is no memory content for an isolation probe to drive against.
    # The tables these touch are wider than `documents` alone, but not by
    # much any more: a delete removes the document row and cascades its
    # blocks and their vectors. It withdraws no provenance, expires no fact
    # and journals nothing -- there is no route from a block to a fact for it
    # to withdraw, and no delete event type for it to write. None of that
    # reads or returns memory content, which is the claim this bucket makes;
    # it is named here so the next reader does not take the narrower sentence
    # as the inventory.
    "POST /api/v1/documents",
    "DELETE /api/v1/documents/{document_id}",
    "DELETE /api/v1/documents/by-uri",
    # Increment 8's block verbs. Same classification and same reason as the
    # write door above: they edit a document's own blocks and answer counts
    # and a content hash. No memory content is read or returned -- a document
    # block is not a memory, and the block channel is firewalled from memory
    # composition (doc 16 §5, tests/test_block_retrieval.py).
    "POST /api/v1/documents/{document_id}/blocks",
    "PATCH /api/v1/documents/{document_id}/blocks/{block_id}",
    "POST /api/v1/documents/{document_id}/blocks/{block_id}/move",
    "DELETE /api/v1/documents/{document_id}/blocks/{block_id}",
    # The search door: ranks blocks and resolves each hit's heading path.
    # Same classification and same reason as the write door immediately
    # above -- it crosses `blocks`/`documents`, never a `memories` row, so
    # there is nothing here for a memory-content isolation probe to drive
    # against.
    "POST /api/v1/documents/search",
    # The outline and fetch doors: a document's heading tree, and its blocks
    # (all of them, or only the ids named). Same classification as the write
    # and search doors immediately above for the same underlying reason --
    # never a `memories` row. Each answers at two paths: a `{document_id}`
    # form, and a `by-uri` form taking `?project=` and `?uri=`. Both forms
    # resolve through `document_door.resolve_document_target` -- a read of
    # `documents` that confirms the row exists (404 otherwise), then an
    # id-keyed read of `blocks`, with no join between the two. So a `project`
    # predicate does exist here, on the by-uri resolution only, and it
    # identifies a document rather than filtering a result set; the block
    # read that follows is id-keyed either way.
    "GET /api/v1/documents/{document_id}/outline",
    "GET /api/v1/documents/{document_id}",
    "GET /api/v1/documents/by-uri/outline",
    "GET /api/v1/documents/by-uri",
    # The metadata verb and the subtree rename. Same classification and same
    # reason as the write door above -- they rewrite a document's own title,
    # uri, pin and tag set, and answer an id or a count. `tags` is the shared
    # table the memory side also writes, but nothing here reads or returns a
    # `memories` row, so there is no memory content for an isolation probe to
    # drive against.
    "PATCH /api/v1/documents/{document_id}",
    "POST /api/v1/documents/rename",
    # The subtree delete (increment 2). Same classification and reason as the
    # write door above -- it removes documents and answers a count, and no
    # `memories` row crosses it.
    "POST /api/v1/documents/delete",
    # The pages epic (increment A, plus B1's trash listing and batch
    # insert). **Page** content crosses these -- a
    # page's title, its block tree and their text -- but no `memories` row
    # does: pages are a human authoring surface, not derived from or lifted
    # into the memory graph, and REST-only (`docs/two-door-parity.md`'s
    # `pages.reads` / `pages.write` rows). Same reasoning as the documents
    # entries above, on the pages table and its own `blocks` rows instead.
    "GET /api/v1/pages",
    "GET /api/v1/pages/{page_id}",
    "GET /api/v1/pages/trash",
    "POST /api/v1/pages",
    "PATCH /api/v1/pages/{page_id}",
    "DELETE /api/v1/pages/{page_id}",
    "POST /api/v1/pages/{page_id}/restore",
    "POST /api/v1/pages/trash/empty",
    "POST /api/v1/pages/{page_id}/blocks",
    "POST /api/v1/pages/{page_id}/blocks/batch",
    "PATCH /api/v1/pages/{page_id}/blocks/{block_id}",
    "POST /api/v1/pages/{page_id}/blocks/{block_id}/move",
    "DELETE /api/v1/pages/{page_id}/blocks/{block_id}",
    # Page attachments: a page's file bytes and their metadata. No
    # `memories` row crosses; REST-only for the pages.attachments row.
    "POST /api/v1/pages/{page_id}/attachments",
    "GET /api/v1/pages/attachments/{attachment_id}",
    # The Notion import writes pages and their blocks, so it is a content
    # surface on the same footing as the page write routes above.
    "POST /api/v1/pages/import/notion",
    # Distribution config (T3.19): adapter paths and a token budget. No
    # memory content crosses -- it configures what *would* be injected, and
    # the injected rows themselves are T3.10's surface.
    "GET /api/v1/distribution",
    "PUT /api/v1/distribution/policy",
    # The work-log lane (spec 2026-09-23). No memory content crosses: a
    # workstream and its entries are a client's own notes about its work,
    # never derived from a `memories` row, and every read is scoped by the
    # project or the workstream id the caller names.
    "POST /api/v1/worklog/entries",
    "GET /api/v1/worklog/resume",
    "GET /api/v1/worklog/workstreams",
    "GET /api/v1/worklog/workstreams/{workstream_id}/entries",
    "POST /api/v1/worklog/search",
    "PATCH /api/v1/worklog/workstreams/{workstream_id}",
    "DELETE /api/v1/worklog/workstreams/{workstream_id}",
    # Key management (T4.01). No memory content crosses: these read and write
    # `api_keys` and nothing else. The scoping question does not arise -- a
    # credential is box-level, not project-scoped, which is also why its
    # lifecycle journals under `object_type='system'`.
    "POST /api/v1/api-keys",
    "GET /api/v1/api-keys",
    "DELETE /api/v1/api-keys/{key_id}",
    # Token and cost telemetry (the usage surface). No memory content crosses:
    # `llm_usage` stores what a call cost, never what it said. The prompt and
    # the completion are not recorded at all -- only their token counts -- and
    # `usage_raw` holds the vendor's own envelope, which is counts too. What
    # does cross is a memory *id*, as `subject_id`, and the same reasoning the
    # entity browser records applies: an id is not content, and the surface is
    # operator-wide because a cost review that hid another project's spend
    # would report a fraction of the bill as the bill.
    "GET /api/v1/usage/overview",
    "GET /api/v1/usage/series",
    "GET /api/v1/usage/by-subject/{subject_type}/{subject_id}",
    "GET /api/v1/usage/top",
    "POST /api/v1/usage/subject-totals",
    "GET /api/v1/usage/by-job",
    # The price table is pure configuration -- dollars per million tokens.
    "GET /api/v1/usage/prices",
    "PUT /api/v1/usage/prices",
    # The MCP call log. No memory content crosses: arguments are minimised at
    # write time (content arguments become sizes) and results become ids and a
    # count. A search query is stored only when the operator turns on
    # `log_query_text`, and it is the caller's own words, not a memory's. Ids
    # are not content (the usage surface's reasoning), and the surface is
    # operator-wide because an audit of what agents asked for that hid a
    # project would report a fraction of the traffic as the traffic.
    "GET /api/v1/mcp-calls",
    "GET /api/v1/mcp-calls/summary",
    # The progress board (spec 2026-10-13). Register and plan text crosses
    # these -- a document's own rows and task headings, plus ledger entry
    # properties -- but no `memories` row does: the board reads `documents`
    # and the work log, both walled off from the memory side, and is
    # REST-only (`board.reads` / `board.write` on docs/two-door-parity.md).
    # Views are layout definitions and carry no content at all.
    "GET /api/v1/board/records",
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
    "GET /api/v1/config/verification-ladder",
    "GET /api/v1/config/llm",
    # Git forge credentials. Nothing here reads or returns memory content --
    # a row is a label, a forge username and a four-character token hint --
    # and the token itself never leaves the process.
    "GET /api/v1/git-accounts",
    "POST /api/v1/git-accounts",
    "POST /api/v1/git-accounts/verify",
    "PUT /api/v1/git-accounts/{account_id}",
    "DELETE /api/v1/git-accounts/{account_id}",
    "GET /api/v1/config/llm-providers",
    "POST /api/v1/config/llm-providers",
    "PUT /api/v1/config/llm-providers/{name}",
    "DELETE /api/v1/config/llm-providers/{name}",
    "POST /api/v1/config/llm-providers/probe-models",
    "POST /api/v1/config/llm-providers/{name}/probe-models",
    "GET /api/v1/config/repos-path",
    "GET /api/v1/config/notifications",
    "PUT /api/v1/config/notifications",
    "POST /api/v1/config/notifications/test",
    "GET /api/v1/config/system-prompts",
    "GET /api/v1/config/theme",
    "POST /api/v1/config/llm",
    "PUT /api/v1/config/feature-flags",
    "PUT /api/v1/config/verification-ladder",
    "PUT /api/v1/config/repos-path",
    "PUT /api/v1/config/system-prompts",
    "PUT /api/v1/config/theme",
    "GET /api/v1/events/calendar",
    "GET /api/v1/jobs",
    "GET /api/v1/jobs/{key}/runs",
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
    # T2.112. 204 and no memory-derived content: the dismissal carries an
    # optional operator note in and returns nothing, the same shape the
    # reject door above already has.
    "POST /api/v1/review-queue/facts/{fact_id}/dismiss-suspicion",
    # Reject's counterpart, and 204 for the same reason (T2.05). An earlier
    # draft answered the ratified fact so the human could see the claim their
    # own act produced; it was withdrawn because a verb that serves content
    # inherits the whole scoping question, and the isolation probe drives every
    # *declared door* of a content surface — driving a mutating door inside a
    # read-isolation probe would change the state its later drivers observe and
    # cost the probe its determinism. The caller re-reads the fact instead,
    # which is one request and the shape reject already established.
    "POST /api/v1/knowledge/facts/{fact_id}/ratify",
    # Accept/dismiss a pin suggestion: 204, same adjudication-verb shape as
    # ratify/reject. The body carries a subject_key and an optional label
    # the caller already had; the response echoes neither, so no
    # memory-derived row crosses either door.
    "POST /api/v1/knowledge/topics/pin-suggestions/accept",
    "POST /api/v1/knowledge/topics/pin-suggestions/dismiss",
    # Aggregate totals across the four hygiene arms, never a row.
    "GET /api/v1/hygiene-queue/counts",
    # Bulk-action doors. The response names each item's id, whether it
    # applied, its event id and its refusal reason — never a memory field's
    # value (the same shape review-queue's reject door carries).
    "POST /api/v1/hygiene-queue/bulk/supersede",
    "POST /api/v1/hygiene-queue/bulk/prune",
    "POST /api/v1/hygiene-queue/bulk/confirm-dedup",
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
    "POST /api/v1/repos/{repo_id}/reindex-files",
    "POST /api/v1/repos/{repo_id}/webhook",
    "PUT /api/v1/repos/{repo_id}",
    "GET /api/v1/review-queue/counts",
    "GET /api/v1/setup/fs/list",
    "GET /api/v1/setup/fs/roots",
    "GET /api/v1/setup/status",
    "POST /api/v1/setup",
    "POST /api/v1/setup/probe-models",
    "GET /api/v1/system/fs/list",
    "GET /api/v1/system/fs/roots",
    # The project catalog (the scope switcher's list). Sibling of the tags
    # histogram directly below: it aggregates over `memories` and serves a
    # distinct `project` value plus a row count. No `content`, no summary, no
    # memory id -- the scoping question this registry answers cannot arise on
    # a door whose whole response is the set of scopes.
    "GET /api/v1/projects",
    "GET /api/v1/tags",
})


MCP_TOOLS_WITHOUT_MEMORY_CONTENT: frozenset[str] = frozenset({
    # The work-log tools: a client's note about its own work is not memory content.
    "mcp:worklog_append",
    "mcp:worklog_resume",
    "mcp:worklog_workstreams",
    "mcp:worklog_entries",
    "mcp:worklog_search",
    "mcp:worklog_update",
    "mcp:worklog_purge",
    "mcp:code_blast_radius",
    "mcp:code_changes",
    "mcp:code_communities",
    "mcp:code_context",
    "mcp:code_dependencies",
    "mcp:code_file_symbols",
    "mcp:code_processes",
    # spec section 6.1. Its REST twin, POST .../reindex-files, is already
    # above for the same reason: the response is a repo id, a commit sha and
    # a file count, none of it a `memories` row.
    "mcp:code_reindex",
    "mcp:code_rename",
    "mcp:code_symbol",
    "mcp:list_repos",
    "mcp:memory_delete",
    "mcp:memory_stats",
    "mcp:memory_tags",
    # T3.27. A write door whose response is counts and ids only: the content
    # crossing it came *from* the caller, so nothing memory-derived crosses
    # back. Unlike `memory_add` it has no wait_process settle re-read, so
    # there is no shape in which it echoes a stored row.
    "mcp:research_run",
    # The document door's MCP half (spec 2026-08-23), for the reason its REST
    # twins carry above: document content crosses these -- block text, a
    # heading tree, a filed document's own counts -- and no `memories` row
    # does, so there is nothing here for a memory-content isolation probe to
    # drive against.
    "mcp:block_update",
    "mcp:block_insert",
    "mcp:block_move",
    "mcp:block_delete",
    "mcp:document_put",
    "mcp:document_search",
    "mcp:document_outline",
    "mcp:document_get",
    "mcp:document_revisions",
    "mcp:document_delete",
    # The subtree delete's MCP half. Same reason as its REST twin: it removes
    # documents and answers a count, and no `memories` row crosses it.
    "mcp:document_delete_subtree",
    # The metadata verb's MCP half, both modes. Same reason as its REST twins
    # above -- it rewrites a document's own title, uri, pin and tag set and
    # answers an id or a count, and no `memories` row crosses it.
    "mcp:document_update",
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
