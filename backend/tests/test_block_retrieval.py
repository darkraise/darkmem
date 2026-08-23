"""The block channel — semantic-only, scoped in SQL, never fused (TH1.06).

Three properties carry this task and each is tested for the reason it exists,
not for coverage.

**"Never fused" is a structural claim, so it gets a structural test.** A
behavioural test could only show that today's composition happens not to
contain a block row; it could not show that none *can*. So the fusion modules'
own imports are walked, and the composition's channel and id-kind registries
are read — the two places a block would have to appear before it could be
fused. Doc 16's firewall runs both ways, so the vault half is walked too: no
module that mints a fact, moves one on the verification ladder, or synthesises
an article from the vault may reach — through its own import closure — a
module that reads a block row, leaving doc 16 §5's on-demand lift as the only
route from a block to a fact.

**"Pushed into SQL" is proven by making the Python-side alternative fail.** A
test that filtered correctly would pass either way. Here the other project
holds enough higher-ranking blocks to fill the probe's whole over-fetch, so a
filter applied after the LIMIT returns nothing and the scoped block is only
retrievable if the predicate reached the database.

**One arm means a failure raises**, and that is asserted rather than assumed:
with no second channel to degrade onto, an empty list would be
indistinguishable from "your corpus has no match" (invariant 14).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services import block_embeddings as be_mod
from app.services.block_query import BlockQueryService
from app.services.document_ingest import BlockDraft, file_document

from ._reachability_scan import (
    ReachabilityRules, app_sources, find_forbidden_reach, import_closure,
    module_path,
)

BACKEND = Path(__file__).resolve().parent.parent

FINGERPRINT = "th106-probe|4"
OTHER_FINGERPRINT = "th106-probe-other|4"

PROJECT = "th106-blocks"
OTHER_PROJECT = "th106-other-project"

# Four orthogonal directions so ranking is decidable rather than incidental:
# an all-equal vector is parallel to every other one and a zero vector has no
# defined cosine at all, which is how a ranking test accidentally asserts
# nothing.
DIRECTIONS = {
    "alpha": [1.0, 0.0, 0.0, 0.0],
    "beta": [0.0, 1.0, 0.0, 0.0],
    "gamma": [0.0, 0.0, 1.0, 0.0],
}
FALLBACK = [0.0, 0.0, 0.0, 1.0]


def _direction(value: str) -> list[float]:
    head = value.split()[0].lower() if value.split() else ""
    return DIRECTIONS.get(head, FALLBACK)


class DirectionalEmbedder:
    """Maps a text's first word to a fixed direction, under one fingerprint."""

    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([_direction(t) for t in texts], self.fingerprint)

    async def embed(self, value: str):
        return _direction(value), self.fingerprint


class BrokenEmbedder(DirectionalEmbedder):
    async def embed(self, value: str):
        raise RuntimeError("embedder unreachable")


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    from app.services.embedder_registry import embedder_registry

    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)
    yield
    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)


async def _file_blocks(session, project: str, *texts: str) -> list[str]:
    # Spans are computed from the joined source rather than left null, so the
    # seeded document is one a parser could have produced: a helper whose
    # stored spans did not agree with its own content would make the
    # slice-the-source-back-out assertion below meaningless.
    drafts: list[BlockDraft] = []
    cursor = 0
    for value in texts:
        drafts.append(
            BlockDraft(text=value, type="paragraph", char_span=(cursor, cursor + len(value)))
        )
        cursor += len(value) + 2  # the "\n\n" the join inserts
    ingest = await file_document(
        session,
        project=project,
        content="\n\n".join(texts),
        parse=lambda: drafts,
        title="probe",
        source_type="note",
    )
    await session.flush()
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(ingest.document_id)},
    )).scalars().all()
    return [str(r) for r in rows]


async def _seed(session, project: str, *texts: str, embedder=None) -> list[str]:
    block_ids = await _file_blocks(session, project, *texts)
    await be_mod.embed_blocks(session, embedder or DirectionalEmbedder(), block_ids=block_ids)
    return block_ids


# ── the channel answers, independently ────────────────────────────────


@pytest.mark.asyncio
async def test_the_channel_ranks_its_own_corpus(session):
    await _seed(session, PROJECT, "alpha one", "beta two", "gamma three")

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "beta", project=PROJECT, limit=3,
    )

    assert [hit.text for hit in hits][0] == "beta two"
    assert hits[0].score > hits[-1].score, "a ranked channel must actually rank"
    assert hits[0].project == PROJECT


@pytest.mark.asyncio
async def test_a_hit_carries_the_span_that_slices_its_source_back_out(session):
    source = "alpha one\n\nbeta two"
    await _seed(session, PROJECT, "alpha one", "beta two")

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "beta", project=PROJECT, limit=1,
    )

    assert hits[0].char_span is not None
    start, end = hits[0].char_span
    assert source[start:end] == "beta two"
    assert hits[0].document_id and hits[0].block_id


@pytest.mark.asyncio
async def test_document_id_narrows_within_a_project(session):
    await _seed(session, PROJECT, "alpha first document")
    second = await _seed(session, PROJECT, "alpha second document")
    document_id = (await session.execute(
        text("SELECT CAST(document_id AS text) FROM blocks WHERE id = CAST(:b AS uuid)"),
        {"b": second[0]},
    )).scalar_one()

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "alpha", project=PROJECT, limit=10, document_id=document_id,
    )

    assert [hit.text for hit in hits] == ["alpha second document"]


# ── the scope predicate is in the SQL, and that is what is proven ─────


@pytest.mark.asyncio
async def test_another_projects_blocks_cannot_consume_the_probes_limit(session):
    """The decisive pushdown test.

    `OTHER_PROJECT` holds six blocks that match the query *exactly*, more than
    the probe's whole over-fetch for `limit=1`. `PROJECT` holds one weaker
    match. A predicate applied in Python after the LIMIT sees only the six and
    returns nothing; only a predicate that reached the database can return the
    one.
    """
    await _seed(session, OTHER_PROJECT, *["alpha decoy"] * 6)
    await _seed(session, PROJECT, "gamma scoped")

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "alpha", project=PROJECT, limit=1,
    )

    assert [hit.text for hit in hits] == ["gamma scoped"]
    assert all(hit.project == PROJECT for hit in hits)


@pytest.mark.asyncio
async def test_the_probe_never_reads_another_fingerprints_partition(session):
    await _seed(session, PROJECT, "alpha under the first embedder")
    await _seed(
        session, PROJECT, "alpha under the second embedder",
        embedder=DirectionalEmbedder(OTHER_FINGERPRINT),
    )

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "alpha", project=PROJECT, limit=10,
    )

    assert [hit.text for hit in hits] == ["alpha under the first embedder"]


# ── one arm, so a failure raises ─────────────────────────────────────


@pytest.mark.asyncio
async def test_an_embedder_failure_raises_rather_than_reading_as_no_match(session):
    await _seed(session, PROJECT, "alpha one")

    with pytest.raises(RuntimeError):
        await BlockQueryService(session, BrokenEmbedder()).search(
            "alpha", project=PROJECT,
        )


@pytest.mark.asyncio
async def test_a_genuine_no_match_is_an_empty_list_not_an_error(session):
    await _seed(session, OTHER_PROJECT, "alpha elsewhere")

    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "alpha", project=PROJECT,
    )

    assert hits == []


@pytest.mark.asyncio
async def test_an_install_that_never_embedded_a_block_gets_no_results_not_a_fault(session):
    """The partition does not exist until something is embedded into it, and an
    empty corpus must read as empty rather than as a 500. Checked explicitly
    rather than by catching the error, so a query that fails against a table
    that *does* exist still raises."""
    hits = await BlockQueryService(session, DirectionalEmbedder()).search(
        "alpha", project=PROJECT,
    )
    assert hits == []


# ── never fused: structural, because behaviour cannot prove "cannot" ──

FUSION_MODULES = (
    "rank_fusion.py",
    "layer_composition.py",
    "hybrid_search.py",
    "chat.py",
)
BLOCK_MODULES = ("block_query", "block_embeddings")


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            names.update(f"{node.module}.{a.name}" for a in node.names if node.module)
    return names


@pytest.mark.parametrize("module_name", FUSION_MODULES)
def test_no_fusion_module_imports_the_block_channel(module_name):
    path = BACKEND / "app" / "services" / module_name
    assert path.exists(), f"{module_name} moved — re-point this scan, do not delete it"
    imported = _imported_names(path)
    for block_module in BLOCK_MODULES:
        offenders = [name for name in imported if block_module in name]
        assert not offenders, (
            f"{module_name} imports {offenders} — the block channel is separate "
            "by design (doc 16 §4); fusing it makes the core read path depend on "
            "the EH1 horizon, which is a Tier-3 firewall breach, not a feature"
        )


def test_the_composition_knows_no_block_channel_and_no_block_id_kind():
    from app.services.layer_composition import CHANNEL_LIST_WEIGHTS, LAYER_BY_ID_KIND

    assert "block" not in CHANNEL_LIST_WEIGHTS
    assert "block" not in LAYER_BY_ID_KIND
    assert "document" not in set(LAYER_BY_ID_KIND.values())


def test_the_composition_refuses_a_block_candidate_outright():
    """Not merely absent from the registries — unrepresentable through them.

    If a later change gave `block` a layer, the two assertions above would
    fail; this one covers the other order, where a caller hand-builds a
    candidate and expects the composition to carry it anyway.
    """
    from app.services.layer_composition import LAYER_BY_ID_KIND

    with pytest.raises(KeyError):
        _ = LAYER_BY_ID_KIND["block"]


# ── never lifted unasked: the same firewall's vault side ────────────
#
# The scan above is doc 16's retrieval half — a block may not be fused into a
# ranked memory result. This is its other half: a block may not become a
# verified fact except through the on-demand lift doc 16 §5 owns. That half
# was honoured behaviourally and untested structurally, which is how a
# citation to "the structural test" came to overstate what it checks.
#
# The seeds are the minting, ladder-moving and vault-synthesising modules,
# not "everything that touches knowledge_triples", and the difference is not
# tidiness: `document_door` writes the vault too — it expires a fact whose
# last source its delete just withdrew — and reads blocks by construction.
# That is the withdrawal direction, which removes evidence and can only
# demote. The firewall is about a block *becoming* a verified fact, so a
# module that only ever takes evidence away is not one of its subjects, and a
# seed list that swept it in would assert something false about this door.

VAULT_WRITERS = (
    "app.repositories.knowledge_triples",
    "app.services.fact_lift",
    "app.services.verification_recompute",
    "app.services.verification_ladder",
    "app.services.contradiction_scan",
    "app.services.citation_reverify",
    "app.services.human_adjudication",
    "app.services.entity_merge",
    "app.services.article_synthesis",
)

BLOCK_CHANNEL_MODULES = frozenset({
    "app.services.block_query",
    "app.services.block_embeddings",
    "app.services.block_pipeline",
    "app.services.document_ingest",
    "app.services.document_parsers",
    "app.services.document_door",
})

# `block_fact_sources` is deliberately absent from that set: it *is* doc 16
# §5's lift, so forbidding it would forbid the sanctioned crossing rather than
# the unsanctioned one. Leaving it out is safe for a reason the test below
# checks rather than assumes — it reads no block row itself, taking block ids
# from whoever calls it.
SANCTIONED_LIFT = "app.services.block_fact_sources"

_VAULT_RULES = ReachabilityRules(
    forbidden_modules=BLOCK_CHANNEL_MODULES,
    forbidden_attrs=frozenset({
        "BlockQueryService", "ingest_document", "file_document", "put_document",
    }),
)


def _closure_paths(*seeds: str) -> list[Path]:
    return [
        path
        for path in (module_path(m, BACKEND) for m in sorted(import_closure(BACKEND, *seeds)))
        if path
    ]


@pytest.mark.parametrize("writer", VAULT_WRITERS)
def test_no_vault_writers_import_closure_reaches_the_block_channel(writer):
    """A module that mints or promotes a fact must not be able to read a block.

    Rooted at the writers rather than at the block channel because the claim
    is directional: the lift may reach the vault, the vault may not reach the
    blocks. Walked transitively, since a helper two hops down that imported
    the block channel would defeat a direct-import check while making the
    reach entirely real.
    """
    paths = _closure_paths(writer)
    assert len(paths) >= 3, (
        f"{writer}'s closure resolved to only {len(paths)} files — either it "
        "moved, in which case re-point this scan, or the scan is vacuous"
    )
    offenders = find_forbidden_reach(paths, BACKEND, _VAULT_RULES)
    assert not offenders, (
        f"{writer} can now reach the block channel:\n" + "\n".join(offenders) +
        "\nA block becomes a fact only through doc 16 §5's on-demand lift; a "
        "vault writer that can read blocks itself is a Tier-3 firewall breach."
    )


def test_the_sanctioned_lift_cannot_read_a_block_row_either():
    """Why `block_fact_sources` is safe to leave out of the forbidden set: it
    records and withdraws provenance for block ids it is handed, and reaches
    no module that can go and fetch the rows behind them."""
    reachable = import_closure(BACKEND, SANCTIONED_LIFT)
    assert reachable & BLOCK_CHANNEL_MODULES == set()


def test_the_vault_scan_covers_every_module_that_writes_the_vault():
    """The staleness guard the hand-written seed list needs.

    A new module that writes `knowledge_triples` and is in no scanned closure
    would be scanned by nothing, and the list would go quietly stale — this
    epic's own characteristic defect. The derivation is SQL text, so it sees a
    writer that issues its own statement; a writer that goes through
    `KnowledgeTripleRepository` is usually covered anyway, the repository
    being a seed and every closure that reaches it therefore scanned. A module
    that does neither is outside what a static derivation here can see, and a
    withdrawal-only writer that legitimately reads blocks (the comment above
    `VAULT_WRITERS`) belongs outside the seeds rather than inside them — so
    this guard says "reachable by some scan", never "is a minting module".
    """
    covered: set[str] = set()
    for writer in VAULT_WRITERS:
        covered |= import_closure(BACKEND, writer)

    statements = ("INSERT INTO knowledge_triples", "UPDATE knowledge_triples",
                  "DELETE FROM knowledge_triples")
    uncovered: list[str] = []
    for path in app_sources(BACKEND):
        text_ = path.read_text()
        if not any(statement in text_ for statement in statements):
            continue
        dotted = str(path.relative_to(BACKEND).with_suffix("")).replace("/", ".")
        if dotted not in covered:
            uncovered.append(dotted)
    assert not uncovered, (
        f"these modules write knowledge_triples but no vault-side scan reaches "
        f"them: {uncovered} — add them to VAULT_WRITERS"
    )


def test_the_vault_scan_reports_a_module_that_does_reach_the_block_channel():
    """The negative control. A scan whose rules stopped matching — a renamed
    block module, a moved service — passes silently and becomes a comment."""
    paths = _closure_paths("app.services.document_door")
    assert find_forbidden_reach(paths, BACKEND, _VAULT_RULES)
