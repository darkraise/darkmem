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
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.api.mcp import server as mcp_server
from app.api.mcp.server import mcp
from app.main import app

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


PARITY_TABLE: tuple[Surface, ...] = (
    # ── Both doors ──────────────────────────────────────────────────
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
    # ── Divergent ───────────────────────────────────────────────────
    Surface(
        name="memory.stats",
        status=DIVERGENT,
        rest=(("GET", f"{V1}/analytics/stats"),),
        mcp=("memory_stats",),
        owner="T1.42f",
        reason=(
            "Both doors hand-roll the same three counts and have already "
            "drifted in a user-visible way: the route also returns entities "
            "and relationships from PostgresGraphRepository.get_stats(), and "
            "the tool returns neither, so an agent asking how big the graph "
            "is gets nothing where the UI gets a number. Neither door calls a "
            "service -- the route computes inline -- so there is nothing to "
            "point the tool at, and closing it means lifting the computation "
            "into AnalyticsService and moving both doors onto it."
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
            ("GET", f"{V1}/config/theme"),
            ("PUT", f"{V1}/config/theme"),
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
            "needs to scope a code query."
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
    one: it needs a task id, and that task id has to be a real row."""
    epic = EPIC_FILE.read_text(encoding="utf-8")
    divergences = [s for s in PARITY_TABLE if s.status == DIVERGENT]
    assert divergences, (
        "no divergence recorded -- if the last one closed, say so in "
        "docs/two-door-parity.md rather than deleting the check"
    )
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
# The recorded divergence is real, and stays recorded until it is fixed
# ---------------------------------------------------------------------------


async def test_memory_stats_is_still_the_recorded_divergence(
    client, auth_headers, session, monkeypatch,
):
    """The audit's one divergence, asserted rather than asserted-about.

    Failing here means the drift changed. If the tool now returns the graph
    counts, T1.42f landed: move memory.stats to two-door and delete this
    guard. If the *route* stopped returning them, the doors converged by
    losing a capability, which is worse and is not what T1.42f asks for.
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())

    rest = (await client.get(f"{V1}/analytics/stats", headers=auth_headers)).json()
    tool = json.loads(await mcp_server.memory_stats())

    shared = {"memories", "tags", "sources"}
    assert shared <= set(rest)
    assert shared <= set(tool)

    assert {"entities", "relationships"} <= set(rest), (
        "GET /analytics/stats stopped returning the graph counts -- the doors "
        "must converge by giving the tool the counts, not by taking them off "
        "the route"
    )
    assert not {"entities", "relationships"} & set(tool), (
        "memory_stats now returns the graph counts. If T1.42f landed, move "
        "memory.stats to two-door in PARITY_TABLE and drop this guard"
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
