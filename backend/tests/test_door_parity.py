"""Two-door parity: invariant 17 made enforceable instead of aspirational.

Doc 12 section 1 fixes the rule -- an MCP tool and its REST twin call the same
service, and **every capability lands on both doors or is explicitly
single-door with a stated reason**. The failure mode is not a crash: a
capability that reaches one door and stops is invisible until a consumer of
the other door needs it and finds nothing.

``PARITY_TABLE`` below is the audit. It is the single source of truth for
``docs/two-door-parity.md``, which this module renders and asserts against, so
the committed human-readable table can never drift from the enforced one.

The enumeration is driven off ``app.routes`` and the live FastMCP tool
registry, never off a literal list of names: a new REST route or a new tool
that nobody classified fails this file, which is the whole point. A
hand-maintained inventory somebody must remember to extend is the exact
failure this task exists to prevent.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import func, select

from app.api.mcp import server as mcp_server
from app.api.mcp.server import mcp
from app.main import app
from app.models.memory import Memory

REPO_ROOT = Path(__file__).resolve().parents[2]
PARITY_DOC = REPO_ROOT / "docs" / "two-door-parity.md"
EPIC_FILE = REPO_ROOT / "docs" / "planning" / "tasks" / "E1-engine-core.md"

TWO_DOOR = "two-door"
REST_ONLY = "rest-single-door"
MCP_ONLY = "mcp-single-door"
DIVERGENT = "divergent"

SINGLE_DOOR = (REST_ONLY, MCP_ONLY)


@dataclass(frozen=True)
class Surface:
    name: str
    status: str
    rest: tuple[tuple[str, str], ...] = ()
    mcp: tuple[str, ...] = ()
    reason: str = ""
    owner: str = ""
    note: str = ""


V1 = "/api/v1"


# One text over both document rows rather than two copies of it: they were
# flipped by one ruling, and a second copy is what lets the halves of one
# decision drift into disagreeing about what was decided.
_DOCUMENTS_RULING = (
    "Owner ruling 2026-08-23. G-F gates the faithfulness judge, which "
    "governs documents.grounded_qa -- an answer that is generated, "
    "labelled and served. These verbs generate nothing and label "
    "nothing: they file a document and return its own text with a "
    "cosine score, as code.search returns source. The doc 16 firewall "
    "is against block rows reaching the verified vault unlifted, and "
    "tests/test_block_retrieval.py bars that structurally: no module "
    "that mints a fact, moves one on the verification ladder or "
    "synthesises an article from the vault can reach, through its own "
    "import closure, a module that reads a block row -- doc 16 section "
    "5's on-demand lift is the only route from a block to a fact, and "
    "it reads no block itself. This does not clear G-F and no bar "
    "moved."
)

# The wire differences, recorded rather than left to be discovered, and one
# per row because the two rows serve different shapes: doc 12 §3 allows a tool
# and its route to differ in shape and nowhere else, and the `memory.search`
# row below already settles the array-versus-envelope half.
_RETRIEVAL_WIRE_SHAPE = (
    "Stated wire asymmetries, none of them a capability. The three tools "
    "answer bare JSON arrays where the routes answer an envelope carrying "
    "`horizon` and, on the two keyed reads, the resolved `document_id` -- the "
    "same difference the memory.search row records. A section hit still says "
    "what it is on both doors, since `id_kind` and `layer` ride the row "
    "rather than the envelope, while an outline node and a block row carry no "
    "label of their own and so reach a tool caller unlabelled. Search carries "
    "two more, the pair knowledge.composed_search already records: the tool "
    "clamps an out-of-range limit to the shared cap while the route 422s on "
    "it, and unavailability is a 503 from the route's llm dependency against "
    "a tool payload carrying the MCP envelope's schema_version -- which is "
    "also the one shape in which document_search answers an object rather "
    "than an array. Neither reaches the keyed reads, which take no llm "
    "dependency on either door. What one service call does produce is the "
    "ranking, the scope and the document-resolution refusals: all three verbs "
    "resolve a supplied `document_id` through "
    "`document_door.resolve_document_target`, which is also what lets the two "
    "keyed reads take a (project, uri) pair instead."
)

_WRITE_WIRE_SHAPE = (
    "Stated wire asymmetry, and it runs both ways here. The filing route "
    "answers 201 with `horizon` on the body; the tool answers the same five "
    "fields without it, `title_applied` included, because `PutResult` "
    "produces them once for both doors. The delete route answers 204 with no "
    "body while `document_delete` answers `{document_id, deleted}` -- the "
    "tool carries more, a bare 204 being nothing for an agent to read. Both "
    "doors call `put_document` and `delete_document`, so the provenance "
    "withdrawal a delete owes has one implementation, and both resolve the "
    "document to delete through `document_door.resolve_document_target`, by "
    "id or by (project, uri)."
)


PARITY_TABLE: tuple[Surface, ...] = (
    # ── Both doors ──────────────────────────────────────────────────
    Surface(
        name="distribution.config",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/distribution"), ("PUT", f"{V1}/distribution/policy")),
        mcp=(),
        reason=(
            "Configures what agents are *told*, and the curb stops push "
            "entirely. Exposing 'stop telling agents things' to an agent "
            "inverts the control it exists to give a human, so this is "
            "single-door on purpose rather than by omission."
        ),
    ),
    Surface(
        name="config.auto_research",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/config/auto-research"),
            ("PUT", f"{V1}/config/auto-research"),
        ),
        mcp=(),
        reason=(
            "Arming the research loop is an operator act, and the loop's own "
            "door is an MCP tool — so an MCP twin here would let the caller "
            "that runs the loop also switch it on, which is the control this "
            "row exists to keep with the human. Same shape as the "
            "distribution config above and for the same reason."
        ),
    ),
    Surface(
        name="config.research_runs",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/config/auto-research/runs"),
            ("POST", f"{V1}/config/auto-research/runs/{{event_id}}/rerun"),
        ),
        mcp=(),
        reason=(
            "The operator's view of what the loop has already filed, and a "
            "re-derivation of one run's evidence. Single-door for the sibling "
            "reason to the config rows above: the MCP caller is the one that "
            "runs the loop, and handing it the surface that inspects and "
            "re-derives its own past runs is the review step folded back into "
            "the reviewed. Re-derivation also files nothing and gathers "
            "nothing, so doc 09 §6's gatherer argument -- which is what keeps "
            "`research_run` itself off REST -- does not reach it."
        ),
    ),
    Surface(
        name="documents.reads",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/documents"),
            ("GET", f"{V1}/documents/{{document_id}}/summary"),
            ("GET", f"{V1}/documents/{{document_id}}/connections"),
        ),
        mcp=(),
        reason=(
            "Three browsing reads with a reason each, and the 'single-door "
            "until G-F clears' clause that stood here is superseded by the "
            "owner ruling of 2026-08-23 -- documents.grounded_qa below is the "
            "row G-F still governs. The list is the list/detail split "
            "knowledge.articles_list already carries: a page of documents in "
            "filing order carrying titles, uris and block counts and no text "
            "is a browsing surface, and the agent's list-shaped read of this "
            "corpus is the ranked document_search on documents.retrieval "
            "below. The summary is on-demand unbadged prose -- "
            "`DocumentSummary` declares no verification field at all, the "
            "response says `badged: false`, no caller in `backend/app` "
            "generates one, and the route 404s until a human asks -- so a "
            "tool would advertise a report that does not exist for every "
            "document in the corpus. Connections serves L1 entity names read "
            "off `entities.memory_ids`, which is what graph.candidate_read is "
            "single-door for: doc 12 section 4 fixes L1 as never directly "
            "served on a retrieval surface, and this is the same rows reached "
            "by a different key."
        ),
    ),
    Surface(
        name="documents.grounded_qa",
        status=REST_ONLY,
        rest=(("POST", f"{V1}/documents/qa"),),
        mcp=(),
        reason=(
            "The one row an eval gate governs, and it states its own gate "
            "rather than pointing at a neighbour's: the answer is served, "
            "labelled or withheld by the faithfulness gate, and an agent twin "
            "would be a second consumer of a judge role that has no "
            "qualification record yet. Every answer is withheld today; "
            "publishing that to agents as a tool would advertise a capability "
            "the gate does not license. This used to open by borrowing the "
            "reads' firewall clause, which the owner ruling of 2026-08-23 "
            "removed from that row -- doc 16 section 1's firewall is real and "
            "is about block rows reaching the verified vault unlifted, which "
            "is not what keeps this surface single-door."
        ),
    ),
    Surface(
        name="documents.write",
        status=TWO_DOOR,
        rest=(
            ("POST", f"{V1}/documents"),
            ("DELETE", f"{V1}/documents/{{document_id}}"),
            ("DELETE", f"{V1}/documents/by-uri"),
        ),
        mcp=("document_put", "document_delete"),
        note=f"{_DOCUMENTS_RULING} {_WRITE_WIRE_SHAPE}",
    ),
    Surface(
        name="documents.retrieval",
        status=TWO_DOOR,
        rest=(
            ("POST", f"{V1}/documents/search"),
            ("GET", f"{V1}/documents/{{document_id}}/outline"),
            ("GET", f"{V1}/documents/{{document_id}}"),
            ("GET", f"{V1}/documents/by-uri/outline"),
            ("GET", f"{V1}/documents/by-uri"),
        ),
        mcp=("document_search", "document_outline", "document_get"),
        note=f"{_DOCUMENTS_RULING} {_RETRIEVAL_WIRE_SHAPE}",
    ),
    Surface(
        name="checkpoint.save",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/checkpoints"),),
        mcp=("checkpoint_save",),
    ),
    Surface(
        name="checkpoint.latest",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/checkpoints/latest"),),
        mcp=("checkpoint_latest",),
    ),
    Surface(
        name="memory.capture",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/memories"),),
        mcp=("memory_add",),
    ),
    Surface(
        name="memory.capture_batch",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/memories/batch"),),
        mcp=("memory_batch_add",),
        note=(
            "Both doors resolve identity on the raw entry dicts before "
            "MemoryCreate validation, and both mirror the 1-100 cap."
        ),
    ),
    Surface(
        name="memory.search",
        status=TWO_DOOR,
        rest=(
            ("POST", f"{V1}/memories/search"),
            ("POST", f"{V1}/memories/search/paginated"),
        ),
        mcp=("memory_search",),
        note=(
            "Stated wire asymmetry, settled by T1.42a and T1.42c: the tool "
            "answers a bare JSON array, which has nowhere to carry the "
            "envelope's ContextEcho or excluded counts. Giving it one is a "
            "breaking change that doc 12 section 3 says ships as a new tool "
            "name, never as a silent mutation of this one. The ranking, the "
            "filters and the SQL pushdown are the same service call."
        ),
    ),
    Surface(
        name="memory.read",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/memories/{{memory_id}}"),),
        mcp=("memory_get",),
    ),
    Surface(
        name="memory.update",
        status=TWO_DOOR,
        rest=(("PUT", f"{V1}/memories/{{memory_id}}"),),
        mcp=("memory_update",),
    ),
    Surface(
        name="memory.delete",
        status=TWO_DOOR,
        rest=(("DELETE", f"{V1}/memories/{{memory_id}}"),),
        mcp=("memory_delete",),
    ),
    Surface(
        name="memory.reason",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/memories/reason"),),
        mcp=("memory_reason",),
    ),
    Surface(
        name="memory.duplicates",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/memories/{{memory_id}}/duplicates"),),
        mcp=("memory_find_duplicates",),
    ),
    Surface(
        name="tag.histogram",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/tags"),),
        mcp=("memory_tags",),
    ),
    Surface(
        name="project.catalog",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/projects"),),
        mcp=(),
        reason=(
            "The scope picker's list, for a human choosing which project the "
            "UI is looking at. An MCP caller never browses for its scope: it "
            "passes `project` explicitly on every capture and recall tool, "
            "because the agent is the thing that decides which project its "
            "work belongs to. Its sibling tag.histogram above is two-door for "
            "the opposite reason -- tags are a retrieval filter an agent picks "
            "from, so it has to be able to see which ones exist. Revisit this "
            "if an agent ever needs to recall across a corpus whose projects "
            "it did not author."
        ),
    ),
    Surface(
        name="repo.list",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/repos"),),
        mcp=("list_repos",),
    ),
    Surface(
        name="code.search",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/code/search"),),
        mcp=("code_search",),
        note=(
            "Both doors fuse through CodeQueryService.search_code and publish "
            "the same rrf_score under the same score key (T1.42c). With no "
            "embedder configured the doors answer differently on purpose: the "
            "tool returns doc 12 section 3's typed degradation envelope, the "
            "route degrades to the keyword arm."
        ),
    ),
    Surface(
        name="code.blast_radius",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/code/blast-radius"),),
        mcp=("code_blast_radius",),
        note=(
            "Only the name-to-id resolution is the tool's; the recursive "
            "traversal is the service's (T1.42c)."
        ),
    ),
    Surface(
        name="code.symbols",
        status=TWO_DOOR,
        rest=(
            ("GET", f"{V1}/code/symbols"),
            ("GET", f"{V1}/code/symbols/lookup"),
            ("GET", f"{V1}/code/symbols/{{symbol_id}}"),
        ),
        mcp=("code_symbol", "code_file_symbols"),
        note=(
            "Two doors, two implementations: both tools build their own "
            "SQLAlchemy query instead of spending "
            "CodeQueryService.list_symbols. Not yet observably divergent -- "
            "the tools emit a subset of the service's keys and no row differs "
            "-- but it is the same latent drift T1.42c found already realised "
            "on code_search and code_blast_radius. Delegating is not a "
            "no-behaviour-change edit (the service caps at limit=50 and the "
            "tools are uncapped), so it needs an owner, not a one-liner."
        ),
    ),
    Surface(
        name="knowledge.overview",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/knowledge/overview"),),
        mcp=("memory_overview",),
        note=(
            "Doc 12 section 3's tool table pairs the tool with this route, and "
            "both doors call memory_overview.get_overview -- the map "
            "selection, the single summarization reduce, the community-set "
            "cache and the declared drops are the service's, so neither door "
            "can answer a partial overview the other reports as complete. The "
            "REST door is auth-gated and the tool is not, the same posture "
            "every two-door read on this table carries."
        ),
    ),
    Surface(
        name="knowledge.fact_detail",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/knowledge/facts/{{fact_id}}"),),
        mcp=("fact_get",),
        note=(
            "Doc 12 section 2's route table assigns fact_get a REST twin at "
            "exactly this path and section 3 puts the agent-facing single-"
            "object vault read on the tool, so T2.72 built the tool rather "
            "than leaving the route filed single-door on a posture argument. "
            "Both doors call facts_read.get_fact and both serialise through "
            "FactDetailResponse -- the tool does not reshape the dict, so a "
            "field the model does not declare is dropped on both doors and "
            "the badge's claim sentence crosses byte for byte "
            "(test_fact_detail_doors_serve_the_same_row). The REST door is "
            "auth-gated and the tool is not, the same posture every two-door "
            "read on this table carries."
        ),
    ),
    Surface(
        name="knowledge.article_detail",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/knowledge/articles/{{article_id}}"),),
        mcp=("article_get",),
        note=(
            "Doc 12 section 2's route table assigns article_get a REST twin at "
            "exactly this path, and section 3 puts the single-object vault "
            "reads on tools. Built as its sibling was rather than filed "
            "single-door: both doors call articles_read.get_article and both "
            "serialise through ArticleDetailResponse, so the coverage number, "
            "the citations and the stale label cross byte for byte. The REST "
            "door is auth-gated and the tool is not, the same posture every "
            "two-door read here carries."
        ),
    ),
    Surface(
        name="knowledge.articles_list",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/knowledge/articles"),),
        reason=(
            "The same reason knowledge.facts_list is REST-only, and it is the "
            "list/detail split rather than a posture argument: doc 12 section 3 "
            "assigns the agent one list-shaped vault read and it is "
            "knowledge_search -- a composed, ranked, badged answer to a query. "
            "A project-scoped page of articles in synthesis order is a browsing "
            "surface doc 13 section 5.2 needs and an agent does not; the detail "
            "half of this surface is knowledge.article_detail, two-door with "
            "article_get."
        ),
    ),
    Surface(
        name="knowledge.composed_search",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/knowledge/search"),),
        mcp=("knowledge_search",),
        note=(
            "Doc 12 section 3's composed four-layer read: one ranked list "
            "drawn from L0 memories and L2 facts at once, every row labelled "
            "and every fact badged, the memories that source a fact nested "
            "under it, and an envelope naming which channels ran and how many "
            "rows a context conflict excluded. T2.72 shipped the tool and "
            "filed the surface MCP-single-door as an agent-shaped projection, "
            "recording rather than resolving the fact that doc 12 section 2 "
            "assigns the twin; T2.80 built it. The filing was honest and it "
            "was wrong: memory.search and code.search are both two-door, so a "
            "cross-layer ranked answer is a capability by this table's own "
            "precedent, and this was the only ranked retrieval in the system "
            "with one door. Both ends call LayerCompositionService.search and "
            "both serialise through knowledge_search_response, the function "
            "T2.72 placed outside the tool for exactly this; the degraded "
            "payload has one producer too "
            "(knowledge_search_unavailable). Ranking parity is asserted on "
            "the order and not the shape "
            "(tests/test_knowledge_search.py), because a row-shape test stays "
            "green while two doors order one corpus differently. Two stated "
            "wire asymmetries, neither of them a capability: the tool clamps "
            "an out-of-range limit to the shared cap while the route 422s on "
            "it, and unavailability is a 503 whose body is the shared model "
            "against a tool payload that adds the MCP envelope's "
            "schema_version. The route is auth-gated and the tool is not, the "
            "same posture every two-door read on this table carries."
        ),
    ),
    Surface(
        name="memory.stats",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/analytics/stats"),),
        mcp=("memory_stats",),
        note=(
            "T1.42f closed the audit's one recorded divergence: neither door "
            "called a service before, so the shared counts (plus the entities "
            "and relationships pair from PostgresGraphRepository.get_stats(), "
            "with its SQLAlchemyError rollback guard intact) were lifted into "
            "AnalyticsService.get_stats() and both doors now call it."
        ),
    ),
    # ── REST single door, each with its reason ──────────────────────
    Surface(
        name="auth.session",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/auth/login"),
            ("POST", f"{V1}/auth/logout"),
            ("POST", f"{V1}/auth/refresh"),
            ("POST", f"{V1}/auth/change-password"),
            ("GET", f"{V1}/auth/me"),
        ),
        reason=(
            "The MCP door is unauthenticated by design (invariant 20, doc 12 "
            "section 6), so a session surface on it is a contradiction in "
            "terms: there is no session to establish, and a change-password "
            "twin would let any LAN peer seize the admin account."
        ),
    ),
    Surface(
        name="auth.audit",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/auth/audit"),),
        reason=(
            "A human security-review read of the doc 12 section 7 "
            "observability class: it enumerates login attempts and token "
            "events, which is precisely the material an unauthenticated "
            "caller must not be able to page through."
        ),
    ),
    Surface(
        name="security.posture",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/auth/security-posture"),),
        reason=(
            "Human observability of the box's own security configuration -- "
            "the same doc 12 section 7 class as the review queue and "
            "auth.audit above: an operator's read of which IP-trust and "
            "cookie strategy is live, not a capability an agent retrieves. "
            "The response enumerates named fields rather than serialising "
            "settings, so it can never leak a credential, but it stays an "
            "authenticated door read: an unauthenticated caller has nothing "
            "to gain from seeing another human's transport-trust posture."
        ),
    ),
    Surface(
        name="setup.tofu",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/setup"),
            ("GET", f"{V1}/setup/status"),
            ("GET", f"{V1}/setup/fs/list"),
            ("GET", f"{V1}/setup/fs/roots"),
            ("POST", f"{V1}/setup/probe-models"),
        ),
        reason=(
            "Trust-on-first-use admin provisioning (invariant 21). It writes "
            "the admin password hash and the provider credentials and browses "
            "the host filesystem to choose a repo root; a twin would make the "
            "TOFU window seizable by any LAN peer, which is the one thing the "
            "no-pre-shared-secret design depends on not happening."
        ),
    ),
    Surface(
        name="system.fs_browse",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/system/fs/list"),
            ("GET", f"{V1}/system/fs/roots"),
        ),
        reason=(
            "Authenticated host-filesystem browse behind the repo-path "
            "picker. Directory listing over an unauthenticated door is a "
            "disclosure primitive with no offsetting agent benefit "
            "(invariant 20)."
        ),
    ),
    Surface(
        name="config.runtime",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/config/classification-areas"),
            ("GET", f"{V1}/config/feature-flags"),
            ("PUT", f"{V1}/config/feature-flags"),
            ("GET", f"{V1}/config/llm"),
            ("POST", f"{V1}/config/llm"),
            ("GET", f"{V1}/config/repo-allowlist"),
            ("PUT", f"{V1}/config/repo-allowlist"),
            ("GET", f"{V1}/config/repos-path"),
            ("PUT", f"{V1}/config/repos-path"),
            ("GET", f"{V1}/config/system-prompts"),
            ("PUT", f"{V1}/config/system-prompts"),
            ("GET", f"{V1}/config/notifications"),
            ("PUT", f"{V1}/config/notifications"),
            ("POST", f"{V1}/config/notifications/test"),
            ("GET", f"{V1}/config/theme"),
            ("PUT", f"{V1}/config/theme"),
            ("GET", f"{V1}/config/verification-ladder"),
            ("PUT", f"{V1}/config/verification-ladder"),
        ),
        reason=(
            "Operator configuration -- provider credentials, feature flags, "
            "the repo allowlist, the repos path, the system prompts. Doc 12 "
            "section 3's confirmed-power rule generalises: the unauthenticated "
            "LAN door must never carry a power the REST door reserves for an "
            "authenticated human, and the read half alone would hand out the "
            "provider API key."
        ),
    ),
    Surface(
        name="config.llm_providers",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/config/llm-providers"),
            ("POST", f"{V1}/config/llm-providers"),
            ("PUT", f"{V1}/config/llm-providers/{{name}}"),
            ("DELETE", f"{V1}/config/llm-providers/{{name}}"),
            ("POST", f"{V1}/config/llm-providers/probe-models"),
            ("POST", f"{V1}/config/llm-providers/{{name}}/probe-models"),
        ),
        reason=(
            "Provider management is operator configuration, not an agent "
            "capability -- the same posture as config.runtime, split into its "
            "own surface because it is a distinct resource. An agent has no "
            "business rotating the operator's vendor credentials, and /mcp is "
            "unauthenticated on a local-network trust model, so putting "
            "credential writes there would be a genuine security regression."
        ),
    ),
    Surface(
        name="analytics.observability",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/analytics/overview"),
            ("GET", f"{V1}/analytics/pipeline-logs"),
        ),
        reason=(
            "Human-observability reads behind the dashboard (doc 12 section "
            "7's sanctioned class): aggregate activity over a date window and "
            "the raw ingest log, which is a view of how the box is running "
            "rather than knowledge an agent retrieves."
        ),
    ),
    Surface(
        name="analytics.reprocess",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/analytics/reprocess"),
            ("POST", f"{V1}/analytics/reprocess/stream"),
        ),
        reason=(
            "A whole-corpus reprocess is unbounded operator maintenance that "
            "spends the configured provider budget and rewrites every "
            "memory's graph. The reasoning that keeps ratification off the "
            "MCP door (doc 12 section 3) keeps this off it: an "
            "unauthenticated caller must not be able to spend the operator's "
            "money or churn the whole corpus."
        ),
    ),
    Surface(
        name="events.read",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/events"),
            ("GET", f"{V1}/events/calendar"),
            ("GET", f"{V1}/events/timeline"),
        ),
        reason=(
            "Stated in doc 12 section 7 verbatim, and the canonical example "
            "of the sanctioned exception: an observability and curation "
            "surface a human consumes to reconstruct history, not an agent "
            "capability, and the raw stream would leak cross-project "
            "operational detail with no isolation benefit."
        ),
    ),
    Surface(
        name="graph.candidate_read",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/graph/full"),
            ("GET", f"{V1}/graph/unified"),
            ("GET", f"{V1}/graph/entities"),
            ("GET", f"{V1}/graph/entities/{{entity_id}}/neighbors"),
            ("GET", f"{V1}/graph/memory-context/{{memory_id}}"),
        ),
        reason=(
            "The L1 candidate graph, served as node-and-edge payloads the UI "
            "canvas lays out client-side. Doc 12 section 4 fixes L1 as never "
            "directly served on a retrieval surface; the agent-facing path to "
            "the same knowledge is memory_search at L0 and, target-new, the "
            "vault family at L2/L3."
        ),
    ),
    Surface(
        name="jobs.control",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/jobs"),
            ("PUT", f"{V1}/jobs/{{key}}"),
            ("PUT", f"{V1}/jobs/{{key}}/config"),
            ("POST", f"{V1}/jobs/{{key}}/trigger"),
            ("GET", f"{V1}/jobs/{{key}}/runs"),
        ),
        reason=(
            "Scheduler control. Triggering or reconfiguring a job is remote "
            "control of the box's background work -- expired_memory_cleanup "
            "deletes rows and graph_orphan_cleanup prunes the graph -- so it "
            "stays behind the authenticated door."
        ),
    ),
    Surface(
        name="pipeline.observability",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/pipeline"),
            ("GET", f"{V1}/pipeline/metrics"),
        ),
        reason=(
            "Human-observability read behind the pipeline dashboard: "
            "configuration echo and per-phase metrics, an operator's view of "
            "the box's health rather than knowledge an agent retrieves."
        ),
    ),
    Surface(
        name="pipeline_failures.triage",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/pipeline-failures"),
            ("GET", f"{V1}/pipeline-failures/counts"),
            ("GET", f"{V1}/pipeline-failures/{{failure_id}}"),
            ("DELETE", f"{V1}/pipeline-failures/{{failure_id}}"),
            ("POST", f"{V1}/pipeline-failures/{{failure_id}}/retry"),
            ("POST", f"{V1}/pipeline-failures/retry-all"),
        ),
        reason=(
            "Operator triage and remediation: the retry doors re-run "
            "extraction and spend the provider budget, and the listing is a "
            "health view for the human. An agent learns its own capture's "
            "fate from the pipeline websocket and its ack, not from another "
            "caller's failure queue."
        ),
    ),
    Surface(
        name="dream_digest.undo",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/dream-digest/cycles"),
            ("GET", f"{V1}/dream-digest/cycles/{{cycle_id}}"),
            ("POST", f"{V1}/dream-digest/actions/{{event_id}}/undo"),
            ("POST", f"{V1}/dream-digest/cycles/{{cycle_id}}/undo"),
        ),
        reason=(
            "Curation, not an agent capability, and the same "
            "conflict-of-interest reasoning doc 12 section 1 applies to the "
            "review queue applies here more sharply. Doc 08 section 7 makes "
            "undo an authenticated human act over what consolidation did "
            "overnight; an agent reversing the consolidation of its own "
            "memories is the agent editing the record it is measured "
            "against. The read half is the same human-observability shape as "
            "pipeline_failures.triage -- a digest a person reviews -- and an "
            "agent has no use for another actor's nightly cycle report. "
            "Invariant 15 is the second, independent reason: the dream job "
            "family may not be reachable from capture or retrieval, and an "
            "MCP twin would put a door onto that stream inside the agent "
            "surface."
        ),
    ),
    Surface(
        name="review_queue.triage",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/review-queue/facts"),
            ("GET", f"{V1}/review-queue/articles"),
            ("GET", f"{V1}/review-queue/counts"),
            ("POST", f"{V1}/review-queue/facts/{{fact_id}}/reject"),
            ("POST", f"{V1}/review-queue/facts/{{fact_id}}/dismiss-suspicion"),
        ),
        reason=(
            "Doc 12 section 1 names the review queue as one of the reshape's "
            "two deliberate single-door kinds -- a human-observability read, "
            "not a confirmed-power write -- and section 3 assigns the "
            "agent-facing capability to a separate tool family, "
            "dispute_inspect (both-sides detail on one disputed fact or "
            "article), never to this backlog view: 'the review-queue read is "
            "a curation surface, not an agent capability ... an agent "
            "triaging its own truth backlog is a conflict of interest the "
            "design declines.' This surface is the pipeline_failures.triage "
            "shape (doc 08 section 6) over facts and articles. review_state "
            "still has no writer here (T2.62 owns its sole derived one). "
            "T2.63 added the one action door: reject withdraws belief and "
            "journals a human_verdict event so doc 17 section 5.1's "
            "false-promotion audit has a human-rejected half at all. It stays "
            "REST-only for the same conflict-of-interest reason the reads do, "
            "and more sharply -- an agent rejecting the facts it is measured "
            "against is the adjudication analogue of grading its own work."
        ),
    ),
    Surface(
        name="knowledge.facts_list",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/knowledge/facts"),),
        reason=(
            "Doc 12 section 3 assigns the agent one list-shaped vault read "
            "and it is knowledge_search, not a fact list: a composed, ranked, "
            "badged answer to a query, with the memories that source each "
            "fact nested under it and an envelope naming what was excluded. "
            "This route answers a different question -- doc 13 section 5.1's "
            "Facts tab, the vault's own bookkeeping in arrival order: the "
            "bi-temporal belief window including window-closed rows that are "
            "retained history, and exact-match filters on subject, relation, "
            "object and verification_status. There is no query for an agent "
            "to aim at it, and an agent that paged the vault would be reading "
            "the corpus rather than retrieving from it. T2.72 replaced the "
            "trust-posture argument this row used to carry, which was weak "
            "for the reason its reviewer gave: every two-door read on this "
            "table already pairs an unauthenticated tool with an "
            "authenticated route, so posture does not decide door count. The "
            "detail half of this surface is no longer here -- it is "
            "knowledge.fact_detail, two-door with fact_get."
        ),
    ),
    Surface(
        name="knowledge.ratify",
        status=REST_ONLY,
        rest=(("POST", f"{V1}/knowledge/facts/{{fact_id}}/ratify"),),
        reason=(
            "The confirmed-power write, and doc 12 section 3 names it as the "
            "first of the reshape's two sanctioned single-door kinds in so "
            "many words: 'the unauthenticated LAN MCP surface must never carry "
            "confirmed power'. Unlike knowledge.facts_list, this row's reason "
            "IS the trust posture and the posture argument holds here where it "
            "did not there -- the two-door reads pair an unauthenticated tool "
            "with an authenticated route because reading the vault is a "
            "capability an agent should have, whereas confirmed is by "
            "construction the one rung the machine cannot reach on its own "
            "(doc 08 section 4.4). A twin would let any LAN peer forge the "
            "human's imprimatur, which is the forged-ratification threat doc "
            "18 section 2 tables. Recorded here so nobody completes the "
            "symmetry later."
        ),
    ),
    Surface(
        name="api_keys.manage",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/api-keys"),
            ("GET", f"{V1}/api-keys"),
            ("DELETE", f"{V1}/api-keys/{{key_id}}"),
        ),
        reason=(
            "The second of doc 12 section 3's sanctioned single-door kinds, "
            "and doc 18 section 5 fixes it in the same words it uses for "
            "ratification: 'a credential mint is confirmed-grade power'. The "
            "posture argument is the one that holds for knowledge.ratify and "
            "not for the vault reads -- a twin on the unauthenticated LAN MCP "
            "door would let any peer on the network mint itself a credential, "
            "which is strictly worse than the surface it would be minting "
            "access to. It is also why 'admin' is not the scope of this "
            "surface: a key holding admin still cannot reach it, so a stolen "
            "key cannot mint its own successor and outlive its revocation "
            "(T4.01). Recorded here so nobody completes the symmetry later."
        ),
    ),
    Surface(
        name="knowledge.topics",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/knowledge/topics"),
            ("GET", f"{V1}/knowledge/topics/{{label}}"),
            ("GET", f"{V1}/knowledge/topics/pin-suggestions"),
            ("POST", f"{V1}/knowledge/topics/pin-suggestions/accept"),
            ("POST", f"{V1}/knowledge/topics/pin-suggestions/dismiss"),
        ),
        reason=(
            "T2.39a's door onto T2.20's topic_browsing.py / pin_suggestions.py, "
            "both shipped with zero callers anywhere in app/ until this task. "
            "Doc 12 section 3's tool table names exactly one MCP-exposed topic "
            "capability -- memory_overview, the project-wide map-reduce "
            "(already two-door, knowledge.overview above) -- and assigns no "
            "tool to per-topic browsing or to the pin-suggestion diff/accept/"
            "dismiss flow doc 09 section 3.4 describes. Accept/dismiss are "
            "also a human curation decision about what feeds article "
            "synthesis, the same review-a-suggestion shape "
            "hygiene_queue.triage and review_queue.reject keep off the "
            "unauthenticated MCP surface rather than a query an agent has a "
            "reason to aim at. If a later doc revision names an agent-facing "
            "tool here the way T2.72 added fact_get for knowledge.facts_list, "
            "this row moves to two-door then, not before."
        ),
    ),
    Surface(
        name="hygiene_queue.triage",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/hygiene-queue/duplicates"),
            ("GET", f"{V1}/hygiene-queue/low-confidence"),
            ("GET", f"{V1}/hygiene-queue/expiring-soon"),
            ("GET", f"{V1}/hygiene-queue/superseded"),
            ("GET", f"{V1}/hygiene-queue/counts"),
            ("POST", f"{V1}/hygiene-queue/bulk/supersede"),
            ("POST", f"{V1}/hygiene-queue/bulk/prune"),
            ("POST", f"{V1}/hygiene-queue/bulk/confirm-dedup"),
        ),
        reason=(
            "The same review_queue.triage shape (doc 08 section 6) over "
            "memories/memory_relations instead of facts/articles: a human "
            "curation surface for housekeeping, not an agent capability. The "
            "bulk actions are a human deciding what to retire or triage in "
            "its own store, the same conflict-of-interest review_queue's "
            "reject door declines to hand an agent; there is no dispute_inspect-"
            "shaped agent need for a housekeeping backlog either."
        ),
    ),
    Surface(
        name="buffer.triage",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/memory-buffer"),
            ("GET", f"{V1}/memory-buffer/stats"),
            ("DELETE", f"{V1}/memory-buffer/{{buffer_id}}"),
            ("POST", f"{V1}/memory-buffer/{{buffer_id}}/requeue"),
        ),
        reason=(
            "The operator's view of the Tier-A capture buffer plus poison-row "
            "remediation. An agent already learns its own capture's fate from "
            "memory_add's ack (doc 05 section 2); another caller's buffered "
            "rows, and the power to drop or requeue them, are not its "
            "business."
        ),
    ),
    Surface(
        name="reembed.maintenance",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/reembed/all"),
            ("POST", f"{V1}/reembed/memories"),
            ("POST", f"{V1}/reembed/entities"),
            ("POST", f"{V1}/reembed/code-chunks"),
            ("POST", f"{V1}/reembed/prune-cache"),
            ("GET", f"{V1}/reembed/obsolete-counts"),
            ("GET", f"{V1}/reembed/obsolete/memories"),
            ("GET", f"{V1}/reembed/obsolete/entities"),
            ("GET", f"{V1}/reembed/obsolete/code-chunks"),
        ),
        reason=(
            "Expensive, destructive maintenance around an embedder rotation: "
            "it re-embeds the whole corpus into a new fingerprint partition "
            "and prunes the entity cache. Operator power, authenticated door "
            "only; the obsolete-listings exist to let the human decide "
            "whether to pay for it."
        ),
    ),
    Surface(
        name="vectors.projection",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/vectors/projection"),),
        reason=(
            "A 2-D projection computed purely for the UI's scatter plot. It "
            "is a rendering aid over embeddings an agent already reaches as "
            "ranked results through memory_search, so a twin would ship "
            "coordinates no agent has a use for."
        ),
    ),
    Surface(
        name="chat.console",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/chat/completions"),
            ("GET", f"{V1}/chat/conversations"),
            ("POST", f"{V1}/chat/conversations"),
            ("GET", f"{V1}/chat/conversations/{{conversation_id}}"),
            ("PATCH", f"{V1}/chat/conversations/{{conversation_id}}"),
            ("DELETE", f"{V1}/chat/conversations/{{conversation_id}}"),
        ),
        reason=(
            "The UI's chat console runs on the box's own configured LLM. An "
            "MCP client brings its own model, and a twin would turn the "
            "unauthenticated door into an open proxy spending the operator's "
            "provider credit."
        ),
    ),
    Surface(
        name="memory.bulk_delete",
        status=REST_ONLY,
        rest=(("POST", f"{V1}/memories/delete"),),
        reason=(
            "The UI's multi-select delete. An agent removes the rows it knows "
            "by id through memory_delete; a mass-erasure primitive on an "
            "unauthenticated door is exactly the power doc 12 section 3 keeps "
            "behind authentication."
        ),
    ),
    Surface(
        name="memory.merge",
        status=REST_ONLY,
        rest=(("POST", f"{V1}/memories/{{memory_id}}/merge"),),
        reason=(
            "A human curation decision that collapses two memories and "
            "discards content -- the same conflict of interest doc 12 section "
            "3 declines for the review queue. The agent gets the read "
            "(memory_find_duplicates) and the human makes the call."
        ),
    ),
    Surface(
        name="repo.manage",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/repos"),
            ("GET", f"{V1}/repos/stats"),
            ("GET", f"{V1}/repos/{{repo_id}}"),
            ("PUT", f"{V1}/repos/{{repo_id}}"),
            ("DELETE", f"{V1}/repos/{{repo_id}}"),
            ("POST", f"{V1}/repos/{{repo_id}}/reindex"),
            ("POST", f"{V1}/repos/{{repo_id}}/webhook"),
            ("GET", f"{V1}/repos/{{repo_id}}/tasks"),
            ("DELETE", f"{V1}/repos/{{repo_id}}/tasks/{{task_id}}"),
        ),
        reason=(
            "Registration and indexing control: creating a repo makes the box "
            "clone and index an arbitrary URL or path under the operator's "
            "allowlist, and reindex spends the provider budget. The reads "
            "carry indexing-operations detail -- index debt, the task queue, "
            "the HEAD sha -- that belongs to the operator dashboard, while "
            "list_repos already gives an agent the id, name and counts it "
            "needs to scope a code query. The push webhook (T4.05, doc 10 "
            "§5) is the same reindex control surfaced for an external CI "
            "system rather than the UI's Reindex button -- an externally "
            "reachable receiver, gated on the same `admin` scope, calling "
            "the identical `CodePipeline.run` polling and the Reindex "
            "button both call; it earns no MCP twin for the same reason "
            "reindex doesn't."
        ),
    ),
    Surface(
        name="code.files",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/code/files/{{repo_id}}"),),
        reason=(
            "A file-tree browse for the code explorer. The agent-facing "
            "equivalent is code_file_symbols, which answers 'what is in this "
            "file' directly, so a twin would add a browse round-trip and no "
            "capability."
        ),
    ),
    Surface(
        name="code.repo_graph",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/code/graph/{{repo_id}}"),),
        reason=(
            "The whole-repo node-and-edge dump the UI canvas lays out "
            "client-side. The agent-facing projections of the very same rows "
            "are the six code_* graph tools below, which answer a question "
            "instead of shipping a graph; a tool twin would hand an agent a "
            "repo-sized payload to traverse itself."
        ),
    ),
    Surface(
        name="code.wiki",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/code/wiki/{{repo_id}}"),),
        reason=(
            "Generated repo prose rendered by the UI. It is strictly "
            "read-only -- generation is an explicit POST "
            "/repos/{id}/reindex?generate_wiki=true, never a GET side effect "
            "-- and an agent reads the code graph and the symbols themselves "
            "rather than a summary written for a human."
        ),
    ),
    Surface(
        name="health.liveness",
        status=REST_ONLY,
        rest=(("GET", "/health"),),
        reason=(
            "An unauthenticated liveness probe for the container runtime. A "
            "tool twin is meaningless by construction: reaching the tool "
            "already proves the server is up."
        ),
    ),
    # ── MCP single door, each with its reason ───────────────────────
    Surface(
        name="code.context",
        status=MCP_ONLY,
        mcp=("code_context",),
        reason=(
            "An agent-shaped projection -- callers, callees, heritage, "
            "community, processes for one symbol -- of rows the REST door "
            "serves whole through GET /code/graph/{repo_id}. No knowledge is "
            "REST-unreachable; what is single-door is the filtered query, "
            "because the UI's consumer is a canvas that wants the graph and "
            "the agent's consumer is a prompt that wants the answer."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. No route answers this query; the claim is "
            "true of the underlying rows, not of the query. Escalated by "
            "T1.42d, not resolved."
        ),
    ),
    Surface(
        name="code.dependencies",
        status=MCP_ONLY,
        mcp=("code_dependencies",),
        reason=(
            "The imports edges for one repo or one file, filtered server-side "
            "out of the same code_edges rows GET /code/graph/{repo_id} ships "
            "whole to the canvas. Single-door in shape, not in capability."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. No route answers this query; the claim is "
            "true of the underlying rows, not of the query. Escalated by "
            "T1.42d, not resolved."
        ),
    ),
    Surface(
        name="code.communities",
        status=MCP_ONLY,
        mcp=("code_communities",),
        reason=(
            "The Leiden community nodes for one repo, filtered out of the "
            "same code_graph_nodes rows GET /code/graph/{repo_id} ships "
            "whole. The UI renders communities as clusters on the canvas; the "
            "agent wants them as a list."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. No route answers this query; the claim is "
            "true of the underlying rows, not of the query. Escalated by "
            "T1.42d, not resolved."
        ),
    ),
    Surface(
        name="code.processes",
        status=MCP_ONLY,
        mcp=("code_processes",),
        reason=(
            "The traced execution flows for one repo with their ordered "
            "steps, filtered out of the same code_graph_nodes and code_edges "
            "rows GET /code/graph/{repo_id} ships whole. Single-door in "
            "shape, not in capability."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. No route answers this query; the claim is "
            "true of the underlying rows, not of the query. Escalated by "
            "T1.42d, not resolved."
        ),
    ),
    Surface(
        name="code.rename",
        status=MCP_ONLY,
        mcp=("code_rename",),
        reason=(
            "A cross-file reference sweep with a per-reference confidence, "
            "assembled from the definition rows and the call, heritage and "
            "import edges the REST door serves whole. It exists to drive an "
            "agent's edit; the UI has no rename view for a twin to feed."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. No route answers this query; the claim is "
            "true of the underlying rows, not of the query. Escalated by "
            "T1.42d, not resolved."
        ),
    ),
    Surface(
        name="research.run",
        status=MCP_ONLY,
        mcp=("research_run",),
        reason=(
            "The door files evidence its caller gathered, and darkmem has no "
            "evidence gatherer by design -- a model without web access would "
            "invent its sources. So the caller has to be the gatherer, which "
            "an MCP agent is and neither REST caller is: the SPA and the "
            "generated three-verb SDK cannot search the web, so the honest "
            "REST shape of 'research subject S into project P' is a route "
            "that gathers server-side, i.e. the in-tree gatherer the design "
            "refuses. A second door would also be the second ingestion path "
            "T3.07 was built to avoid."
        ),
        note=(
            "Not a capture twin either: the tool takes no source, no "
            "origin_key and no ctx, so a caller cannot file through it while "
            "looking like ordinary capture, and it refuses until the owner "
            "enables the research config row (T3.27, doc 09 section 6)."
        ),
    ),
    Surface(
        name="code.changes",
        status=MCP_ONLY,
        mcp=("code_changes",),
        reason=(
            "The only genuinely single-door capability in the code family: it "
            "shells out to git in the repo working directory and reports the "
            "uncommitted diff against the indexed symbols. Every REST read "
            "and the whole indexed graph are commit-based, so no route "
            "carries this state and the UI has no working-tree view. It "
            "serves the agent editing the tree right now."
        ),
        note=(
            "Doc 12 section 3 lists this tool as having a REST twin under "
            "/code or /repos today. It has none, and unlike its five "
            "siblings the underlying state is not REST-reachable either. "
            "Escalated by T1.42d, not resolved."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Enumeration -- off the router and the tool registry, never off a literal
# ---------------------------------------------------------------------------


def _iter_api_routes():
    """Flatten FastAPI's lazily-included router tree into APIRoute leaves.

    Recent FastAPI wraps ``include_router`` targets in ``_IncludedRouter``
    rather than eagerly flattening ``app.routes``, so a plain iteration sees
    wrapper objects instead of the leaf routes.
    """
    def walk(routes):
        for r in routes:
            original = getattr(r, "original_router", None)
            if original is not None:
                yield from walk(original.routes)
            elif isinstance(r, APIRoute):
                yield r

    yield from walk(app.routes)


def live_rest_surface() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in _iter_api_routes()
        for method in route.methods - {"HEAD"}
    }


async def live_mcp_surface() -> set[str]:
    return {tool.name for tool in await mcp.list_tools()}


def _table_rest() -> list[tuple[tuple[str, str], Surface]]:
    return [(entry, surface) for surface in PARITY_TABLE for entry in surface.rest]


def _table_mcp() -> list[tuple[str, Surface]]:
    return [(tool, surface) for surface in PARITY_TABLE for tool in surface.mcp]


# ---------------------------------------------------------------------------
# The audit is exhaustive over both doors
# ---------------------------------------------------------------------------


def test_every_rest_route_is_classified():
    """A new REST route with no MCP twin and no recorded exemption fails here.

    This is the guard the whole task exists for: parity cannot be a list
    somebody remembers to extend, so the left-hand side is the live router.
    """
    classified = {entry for entry, _ in _table_rest()}
    live = live_rest_surface()

    unclassified = live - classified
    assert not unclassified, (
        "these REST routes have no row in PARITY_TABLE -- give each one an "
        "MCP twin, or a row stating why it is single-door: "
        f"{sorted(unclassified)}"
    )

    stale = classified - live
    assert not stale, (
        f"PARITY_TABLE names REST routes that no longer exist: {sorted(stale)}"
    )


async def test_every_mcp_tool_is_classified():
    classified = {tool for tool, _ in _table_mcp()}
    live = await live_mcp_surface()

    unclassified = live - classified
    assert not unclassified, (
        "these MCP tools have no row in PARITY_TABLE -- give each one a REST "
        f"twin, or a row stating why it is single-door: {sorted(unclassified)}"
    )

    stale = classified - live
    assert not stale, (
        f"PARITY_TABLE names MCP tools that no longer exist: {sorted(stale)}"
    )


def test_no_surface_is_claimed_twice():
    rest_owners: dict[tuple[str, str], list[str]] = {}
    for entry, surface in _table_rest():
        rest_owners.setdefault(entry, []).append(surface.name)
    duplicated = {k: v for k, v in rest_owners.items() if len(v) > 1}
    assert not duplicated, f"REST routes claimed by more than one row: {duplicated}"

    mcp_owners: dict[str, list[str]] = {}
    for tool, surface in _table_mcp():
        mcp_owners.setdefault(tool, []).append(surface.name)
    duplicated_tools = {k: v for k, v in mcp_owners.items() if len(v) > 1}
    assert not duplicated_tools, (
        f"MCP tools claimed by more than one row: {duplicated_tools}"
    )

    names = [s.name for s in PARITY_TABLE]
    assert len(names) == len(set(names)), "duplicate surface names in PARITY_TABLE"


# ---------------------------------------------------------------------------
# Every status means what it says
# ---------------------------------------------------------------------------


# "Not yet built" is not a reason (T1.42d ruling 1). A row whose justification
# is that nobody has got to it yet is the sequencing invariant 17 forbids,
# wearing an exemption's clothes.
_NON_REASONS = (
    "not yet built",
    "not built",
    "not implemented",
    "not yet implemented",
    "planned",
    "future",
    "todo",
    "tbd",
    "coming soon",
    "no reason",
    "n/a",
    # The two spellings that got a schedule past this list once (Task 5 fix
    # round 1). A reason naming what a row does not have yet is the same
    # sentence as "not yet built" with the tense moved.
    "no mcp twin yet",
    "twin yet",
)

_MIN_REASON_CHARS = 80


def test_statuses_match_the_doors_the_row_actually_names():
    for surface in PARITY_TABLE:
        if surface.status == TWO_DOOR:
            assert surface.rest and surface.mcp, (
                f"{surface.name} is marked two-door but names "
                f"rest={surface.rest} mcp={surface.mcp}"
            )
        elif surface.status == REST_ONLY:
            assert surface.rest and not surface.mcp, (
                f"{surface.name} is marked rest-single-door but names "
                f"mcp={surface.mcp}"
            )
        elif surface.status == MCP_ONLY:
            assert surface.mcp and not surface.rest, (
                f"{surface.name} is marked mcp-single-door but names "
                f"rest={surface.rest}"
            )
        elif surface.status == DIVERGENT:
            assert surface.rest and surface.mcp, (
                f"{surface.name} is marked divergent but is not on both doors"
            )
        else:
            pytest.fail(f"{surface.name} carries unknown status {surface.status!r}")


def test_every_single_door_surface_states_a_real_reason():
    for surface in PARITY_TABLE:
        if surface.status not in SINGLE_DOOR:
            continue
        reason = surface.reason.strip()
        assert len(reason) >= _MIN_REASON_CHARS, (
            f"{surface.name} is single-door with no stated reason (or too "
            f"thin a one): {reason!r}"
        )
        lowered = reason.lower()
        for placeholder in _NON_REASONS:
            assert placeholder not in lowered, (
                f"{surface.name}'s reason leans on {placeholder!r}, which is "
                "a schedule, not a reason -- invariant 17 forbids sequencing "
                "one door behind the other"
            )


def test_a_two_door_surface_states_no_exemption():
    for surface in PARITY_TABLE:
        if surface.status != TWO_DOOR:
            continue
        assert not surface.reason, (
            f"{surface.name} is on both doors and carries an exemption "
            "reason; an exemption that exempts nothing hides the next real one"
        )


def test_every_divergence_carries_a_named_owner_that_exists():
    """A divergence is worse than a stated exemption and must not be filed as
    one: it needs a task id, and that task id has to be a real row.

    T1.42f closed the last recorded divergence (memory.stats), so this can
    legitimately find an empty list -- the loop below is then vacuously true
    rather than skipped, and the "0 divergent" the doc's generated headline
    now states (test_the_committed_table_reports_its_own_counts) is the
    place this closure is said, per this test's own former warning not to
    just delete the check.
    """
    epic = EPIC_FILE.read_text(encoding="utf-8")
    divergences = [s for s in PARITY_TABLE if s.status == DIVERGENT]
    for surface in divergences:
        assert re.fullmatch(r"T\d+\.\d+[a-z]?", surface.owner), (
            f"{surface.name} is divergent but names no owning task "
            f"(got {surface.owner!r})"
        )
        assert len(surface.reason.strip()) >= _MIN_REASON_CHARS, (
            f"{surface.name} is divergent with no description of the drift"
        )
        assert f"#### {surface.owner} " in epic, (
            f"{surface.name} names owner {surface.owner}, which has no task "
            f"in {EPIC_FILE.name}"
        )


# ---------------------------------------------------------------------------
# memory.stats: the former divergence, now converged onto AnalyticsService
# ---------------------------------------------------------------------------


def _stats_fake_ctx(session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    return _fake_ctx


async def test_stats_doors_agree_on_graph_counts(client, auth_headers, session, monkeypatch):
    """Both doors must answer the same question identically -- values, not
    just key presence. StatsResponse defaults entities/relationships to
    None, so a door that stopped computing them would still pass a
    key-presence check; only asserting the numbers themselves catches that
    (this is exactly the hole T1.42d found in its own guard)."""
    from app.repositories.graph import PostgresGraphRepository

    monkeypatch.setattr(mcp_server, "async_session_factory", _stats_fake_ctx(session))

    graph_repo = PostgresGraphRepository(session)
    m1 = uuid.uuid4()
    session.add(Memory(id=m1, content="stats-parity", source="test"))
    await session.flush()
    await graph_repo.create_entity(name="stats-parity-a", entity_type="concept", properties={}, memory_id=m1)
    await graph_repo.create_entity(name="stats-parity-b", entity_type="concept", properties={}, memory_id=m1)
    await graph_repo.create_relationship(
        source_name="stats-parity-a", target_name="stats-parity-b",
        rel_type="RELATED_TO", properties={}, weight=1.0, memory_id=m1,
    )
    await session.flush()

    rest = (await client.get(f"{V1}/analytics/stats", headers=auth_headers)).json()
    tool = json.loads(await mcp_server.memory_stats())

    for key in ("memories", "tags", "sources", "entities", "relationships"):
        assert key in rest, f"REST stats is missing {key!r}"
        assert key in tool, f"memory_stats tool is missing {key!r}"

    assert rest["entities"] is not None and rest["relationships"] is not None
    assert tool["entities"] is not None and tool["relationships"] is not None
    assert rest["entities"] == tool["entities"] >= 2
    assert rest["relationships"] == tool["relationships"] >= 1
    assert rest["memories"] == tool["memories"]
    assert rest["tags"] == tool["tags"]
    assert set(rest["sources"]) == set(tool["sources"])


async def test_rest_stats_calls_the_shared_analytics_service(client, auth_headers, monkeypatch):
    """Guards ruling 1: the route must reach AnalyticsService.get_stats(),
    not recompute the counts inline. Fails if someone re-inlines the route."""
    from app.services.analytics import AnalyticsService

    calls = []
    original = AnalyticsService.get_stats

    async def spy(self):
        calls.append(self)
        return await original(self)

    monkeypatch.setattr(AnalyticsService, "get_stats", spy)

    response = await client.get(f"{V1}/analytics/stats", headers=auth_headers)
    assert response.status_code == 200
    assert len(calls) == 1, "GET /analytics/stats did not call AnalyticsService.get_stats()"


async def test_mcp_stats_calls_the_shared_analytics_service(session, monkeypatch):
    """Guards ruling 1 on the MCP side: fails if memory_stats grows its own
    hand-rolled counts again instead of calling the shared service."""
    from app.services.analytics import AnalyticsService

    monkeypatch.setattr(mcp_server, "async_session_factory", _stats_fake_ctx(session))

    calls = []
    original = AnalyticsService.get_stats

    async def spy(self):
        calls.append(self)
        return await original(self)

    monkeypatch.setattr(AnalyticsService, "get_stats", spy)

    result = json.loads(await mcp_server.memory_stats())
    assert "memories" in result
    assert len(calls) == 1, "memory_stats did not call AnalyticsService.get_stats()"


async def test_get_stats_survives_a_failing_graph_count(session):
    """Ruling 2: the SQLAlchemyError rollback guard must survive the move
    off the route intact. A failing graph COUNT must not poison the session
    or 500 the whole surface -- it must degrade honestly (null graph counts,
    the memory/tag/source counts still present).

    The failure must be a real aborted statement, not a Python-raised
    stand-in: a synthetic `raise SQLAlchemyError(...)` never actually touches
    Postgres, so the session was never poisoned and a test built on it cannot
    tell a present rollback from a deleted one. Querying a table that does
    not exist gets a real ProgrammingError from asyncpg and leaves the
    session's transaction genuinely aborted until something rolls it back.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.analytics import AnalyticsService

    class _ExplodingGraphRepo:
        def __init__(self, session: AsyncSession):
            self.session = session

        async def get_stats(self):
            await self.session.execute(text("SELECT 1 FROM this_table_does_not_exist"))
            return {"entity_count": 0, "relationship_count": 0}

    service = AnalyticsService(session, graph_repo=_ExplodingGraphRepo(session))
    stats = await service.get_stats()

    assert stats["entities"] is None
    assert stats["relationships"] is None
    assert stats["memories"] is not None
    assert stats["tags"] is not None

    # The session must still be usable after the rollback -- a poisoned
    # session raises InFailedSqlTransactionError (wrapped in
    # PendingRollbackError by SQLAlchemy) on the next query instead.
    still_usable = (await session.execute(select(func.count()).select_from(Memory))).scalar()
    assert still_usable is not None


# ---------------------------------------------------------------------------
# knowledge.fact_detail: the vault's detail read, on both doors (T2.72)
# ---------------------------------------------------------------------------


async def _seed_badged_fact(session) -> str:
    """One corroborated fact with two distinct origins and a verified event.

    Two origins rather than one because the badge's ``origin_count`` is a
    ``DISTINCT origin_key`` count: a single-origin fixture agrees with a row
    count and would pass against a door that published either number.
    """
    from datetime import datetime, timezone

    from sqlalchemy import text

    from app.repositories.fact_sources import FactSourceRepository
    from app.repositories.knowledge_triples import KnowledgeTripleRepository

    project = "t272-parity"
    at = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"t272-{uuid.uuid4()}",
        subject_name="darkmem",
        object_name="postgres",
        rel_type="USES",
        fact="darkmem USES postgres",
        reference_time=at,
        project=project,
        valid_at=at,
    )
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'corroborated' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": row["id"]},
    )
    sources = FactSourceRepository(session)
    for origin in ("origin-a", "origin-b"):
        await sources.add_source(
            fact_id=row["id"],
            source_kind="memory",
            source_ref=str(uuid.uuid4()),
            origin_key=origin,
        )
    await session.execute(
        text("SELECT events_ensure_partition(CAST(:at AS timestamptz)::date)"),
        {"at": at},
    )
    await session.execute(
        text(
            "INSERT INTO events (created_at, event_type, object_type, object_id, "
            "project, payload) VALUES (CAST(:at AS timestamptz), 'verified', "
            "'fact', CAST(:fid AS uuid), CAST(:project AS text), "
            "CAST(:payload AS jsonb))"
        ),
        {
            "at": at,
            "fid": str(row["id"]),
            "project": project,
            "payload": json.dumps(
                {
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                }
            ),
        },
    )
    await session.flush()
    return str(row["id"])


async def test_fact_detail_doors_serve_the_same_row(
    client, auth_headers, session, monkeypatch
):
    """A row shape that diverges between the doors fails here (T2.72).

    The whole document is compared, not a field list: a key-presence check
    passes a door that dropped a value, and a field list passes a door that
    grew a key nobody enumerated. Both doors serialise through
    ``FactDetailResponse``, so the assertion below holds structurally rather
    than by agreement -- which is the point. The failure this catches is the
    realistic one: a tool that reshapes the service's dict itself, exactly as
    ``code_search`` and ``code_blast_radius`` did before T1.42c consolidated
    them.
    """
    monkeypatch.setattr(mcp_server, "async_session_factory", _stats_fake_ctx(session))
    fact_id = await _seed_badged_fact(session)

    response = await client.get(f"{V1}/knowledge/facts/{fact_id}", headers=auth_headers)
    assert response.status_code == 200
    tool_text = await mcp_server.fact_get(fact_id=fact_id)

    rest_row = json.loads(response.content)
    tool_row = json.loads(tool_text)
    assert tool_row == rest_row, (
        "GET /knowledge/facts/{fact_id} and fact_get answered different "
        "shapes for one fact; both doors must serialise through "
        "FactDetailResponse rather than reshaping the service's dict"
    )


async def test_the_badge_crosses_both_doors_byte_for_byte(
    client, auth_headers, session, monkeypatch, cleared_promotion_record):
    """Doc 12 §4's claim is shown verbatim or not at all, so the two doors
    must publish the same bytes and not merely the same meaning.

    Asserted against the raw payloads rather than the parsed ones: a door
    that rebuilt the sentence with different punctuation, a different origin
    count or a softened verb would still parse into a plausible dict, and
    the raw-bytes check is what makes the second producer T2.71's guard
    forbids visible here too.
    """
    monkeypatch.setattr(mcp_server, "async_session_factory", _stats_fake_ctx(session))
    fact_id = await _seed_badged_fact(session)

    response = await client.get(f"{V1}/knowledge/facts/{fact_id}", headers=auth_headers)
    assert response.status_code == 200
    tool_text = await mcp_server.fact_get(fact_id=fact_id)

    rest_badge = json.loads(response.content)["badge"]
    tool_badge = json.loads(tool_text)["badge"]
    assert rest_badge is not None, "the fixture produced no badge to compare"
    assert tool_badge == rest_badge

    claim = rest_badge["claim"]
    assert claim, "the badge carries no claim sentence"
    assert claim.encode("utf-8") in response.content
    assert claim in tool_text
    assert json.dumps(rest_badge, sort_keys=True) == json.dumps(
        tool_badge, sort_keys=True
    )


# ---------------------------------------------------------------------------
# The committed table is this table
# ---------------------------------------------------------------------------

_DOC_BEGIN = "<!-- BEGIN GENERATED PARITY TABLE -->"
_DOC_END = "<!-- END GENERATED PARITY TABLE -->"

_STATUS_LABEL = {
    TWO_DOOR: "two-door",
    REST_ONLY: "REST single-door",
    MCP_ONLY: "MCP single-door",
    DIVERGENT: "**divergent**",
}


def _cell(text: str) -> str:
    return text.replace("|", "\\|") if text else "—"


def render_markdown() -> str:
    lines = [
        "| Surface | REST | MCP | Status | Reason / note |",
        "|---|---|---|---|---|",
    ]
    for surface in PARITY_TABLE:
        rest = "<br>".join(f"`{m} {p}`" for m, p in surface.rest) or "—"
        tools = "<br>".join(f"`{t}`" for t in surface.mcp) or "—"
        prose = " ".join(part for part in (surface.reason, surface.note) if part)
        if surface.status == DIVERGENT:
            prose = f"**Owner: {surface.owner}.** {prose}"
        lines.append(
            f"| `{surface.name}` | {rest} | {tools} | "
            f"{_STATUS_LABEL[surface.status]} | {_cell(prose)} |"
        )
    return "\n".join(lines)


def test_the_committed_table_is_the_enforced_table():
    """One source of truth. Regenerate the doc with:

        cd backend && .venv/bin/python -c \
          "from tests.test_door_parity import render_markdown; print(render_markdown())"
    """
    doc = PARITY_DOC.read_text(encoding="utf-8")
    assert _DOC_BEGIN in doc and _DOC_END in doc, (
        f"{PARITY_DOC.name} has lost its generated-table markers"
    )
    committed = doc.split(_DOC_BEGIN, 1)[1].split(_DOC_END, 1)[0].strip()
    assert committed == render_markdown(), (
        f"{PARITY_DOC.name} has drifted from PARITY_TABLE -- regenerate it "
        "(see this test's docstring) rather than editing the markdown by hand"
    )


def test_the_committed_table_reports_its_own_counts():
    """The doc's headline counts are derived, so they cannot go stale."""
    doc = PARITY_DOC.read_text(encoding="utf-8")
    counts = {
        status: sum(1 for s in PARITY_TABLE if s.status == status)
        for status in (TWO_DOOR, REST_ONLY, MCP_ONLY, DIVERGENT)
    }
    single = counts[REST_ONLY] + counts[MCP_ONLY]
    headline = (
        f"{len(PARITY_TABLE)} surfaces: {counts[TWO_DOOR]} two-door, "
        f"{single} single-door with a stated reason "
        f"({counts[REST_ONLY]} REST-only, {counts[MCP_ONLY]} MCP-only), "
        f"{counts[DIVERGENT]} divergent"
    )
    assert headline in doc, (
        f"docs/two-door-parity.md must state its own counts verbatim: {headline!r}"
    )
