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
module that reads a block row. There is no route from a block to a fact at
all: the on-demand lift and the block-to-fact bridge are both retired, so the
forbidden set is the complement with no exception.

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


def test_no_service_module_imports_the_relatedness_surfaces():
    """Spec §3.6: these read block vectors and rank memories by them. That is
    permitted on a per-document panel outside the composition and nowhere
    else, so the pin is structural -- a test asserting today's results hold
    no block cannot pin "cannot"."""
    surfaces = ("app.services.document_related", "app.services.document_connections")
    offenders = []
    for path in app_sources(BACKEND):
        try:
            dotted = str(path.relative_to(BACKEND / "app/services").with_suffix(""))
        except ValueError:
            continue
        dotted = f"app.services.{dotted.replace('/', '.')}"
        if path.name in {"document_related.py", "document_connections.py"}:
            continue
        closure = import_closure(BACKEND, dotted)
        for surface in surfaces:
            if surface in closure:
                offenders.append((path.name, surface))
    assert offenders == [], f"a service reached a relatedness surface: {offenders}"


# ── never lifted unasked: the same firewall's vault side ────────────
#
# The scan above is doc 16's retrieval half — a block may not be fused into a
# ranked memory result. This is its other half: a block may not become a
# verified fact at all — the on-demand lift and the block-to-fact bridge that
# would have been that route are both retired. That half was honoured
# behaviourally and untested structurally, which is how a citation to "the
# structural test" came to overstate what it checks.
#
# The seeds are the minting, ladder-moving and vault-synthesising modules,
# not "everything that touches knowledge_triples", and the difference is not
# tidiness: `document_door` reads blocks by construction, and its
# withdraw-then-expire pass — which used to remove evidence a delete had just
# withdrawn — went with the bridge; it withdraws nothing today.
# The firewall is about a block *becoming* a verified fact, so a
# module that reads blocks but never mints or promotes anything is not one of
# its subjects, and a seed list that swept it in would assert something false
# about this door.
# That "never mints or promotes" is not left as a reading of today's
# code: `test_no_block_channel_module_can_promote_a_fact`, at the bottom of
# this file, pins it at the method level.

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
    # Increment 8's write half. Classified in the same task that creates
    # them: an unclassified module is a hole in the scan, which is this
    # codebase's named characteristic defect.
    "app.services.block_verbs",
    "app.services.block_serializer",
    # Reads block rows (via its own child-table probes) to resolve the
    # fingerprint a relatedness read compares under; classified here per
    # the same rule.
    "app.services.document_similarity",
    # The relatedness surfaces (spec §3.6). They read block rows and block
    # vectors, so they are classified here in the change that gives them that
    # reach -- an unclassified module is a hole in the scan.
    "app.services.document_related",
    "app.services.document_connections",
    # The page door reads block rows to serve a page's tree, so it is
    # classified in the change that gives it that reach.
    "app.services.page_door",
    # Reads page block text to find which attachments are still referenced.
    "app.services.page_attachment_cleanup",
    # Writes blocks through page_door._insert_page.
    "app.services.page_import",
})

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
    is directional: a block channel module may hold the vault repository to
    read from it (see `BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT` below — reads
    only, since the withdrawal capability retired with the bridge), but no
    vault writer may reach the blocks at all — there is no route from a
    block to a fact left in this tree. Walked transitively, since a helper
    two hops down that imported the block channel would defeat a
    direct-import check while making the reach entirely real.
    """
    paths = _closure_paths(writer)
    assert len(paths) >= 3, (
        f"{writer}'s closure resolved to only {len(paths)} files — either it "
        "moved, in which case re-point this scan, or the scan is vacuous"
    )
    offenders = find_forbidden_reach(paths, BACKEND, _VAULT_RULES)
    assert not offenders, (
        f"{writer} can now reach the block channel:\n" + "\n".join(offenders) +
        "\nNo route from a block to a fact exists; a vault writer that can "
        "read blocks itself is a Tier-3 firewall breach."
    )


def test_the_vault_scan_covers_every_module_that_writes_the_vault():
    """The staleness guard the hand-written seed list needs.

    A new module that writes `knowledge_triples` and is in no scanned closure
    would be scanned by nothing, and the list would go quietly stale — this
    epic's own characteristic defect. The derivation is SQL text, so it sees a
    writer that issues its own statement; a writer that goes through
    `KnowledgeTripleRepository` is usually covered anyway, the repository
    being a seed and every closure that reaches it therefore scanned. A module
    that does neither is outside what a static derivation here can see. There
    is no withdrawal-only writer left to carve out that exception for: the
    block channel may read the vault repository but never write it in any
    direction, withdrawal included (`BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT`
    below), so this guard says "reachable by some scan", never "is a minting
    module".
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


# ── no vault write from the block channel, pinned ────────────────────
#
# No block-channel module holds a `KnowledgeTripleRepository` today, not even
# to withdraw: the block-to-fact bridge that gave `document_door` a
# withdraw-then-expire pass is retired, and nothing replaced it, so `expire`
# has no more a caller here than `insert_open` does. This pin is prospective
# rather than descriptive of a live caller: neither scan above would notice a
# block channel module that started calling `insert_open` or
# `set_verification_status`, because the coverage guard derives writers from
# raw `knowledge_triples` SQL text, which a call through the repository does
# not produce, and the reach scan is rooted at the minting modules, which no
# block channel module is one of by name.
#
# So the exclusion is pinned here directly, at the method level, fail-closed
# against a future block-channel module that does hold the repository.

# Everything a block-channel module may call on the vault repository. The
# forbidden set is derived as the complement, never listed: a method added to
# `KnowledgeTripleRepository` is forbidden to this channel until someone
# classifies it here, which is the fail-closed direction. All of these are
# reads — the withdrawal method (`expire`) has no caller left to permit since
# the bridge that called it is retired, so it is not classified here either.
BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT = frozenset({
    "as_of", "get", "get_live", "list_live",
})


def _promoting_vault_methods() -> frozenset[str]:
    from app.repositories.knowledge_triples import KnowledgeTripleRepository

    public = {name for name in dir(KnowledgeTripleRepository) if not name.startswith("_")}
    assert BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT <= public, (
        "BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT names methods the repository no "
        "longer has — re-derive it rather than leaving it to rot: "
        f"{sorted(BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT - public)}"
    )
    return frozenset(public - BLOCK_CHANNEL_MAY_CALL_ON_THE_VAULT)


def _attributes_named(source: str) -> set[str]:
    return {
        node.attr for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute)
    }


@pytest.mark.parametrize("module_name", sorted(BLOCK_CHANNEL_MODULES))
def test_no_block_channel_module_can_promote_a_fact(module_name):
    """A block-channel module may only read the vault; it may never put a
    fact in one, move one up the ladder, or withdraw evidence from one.

    Named methods rather than import reach, because a future block channel
    module holding the repository would still be bound by the verbs it
    calls, not by whether it holds the import. There is no route from a
    block to a fact at all — the on-demand lift and the block-to-fact bridge
    that would have carried one are both retired.
    """
    path = module_path(module_name, BACKEND)
    assert path is not None, f"{module_name} moved — re-point this scan"
    offenders = _attributes_named(path.read_text()) & _promoting_vault_methods()
    assert not offenders, (
        f"{module_name} names {sorted(offenders)} on the vault repository. A "
        "block channel module may only read it; minting a fact, moving one "
        "up the ladder, or withdrawing one from here would open a route "
        "from a block to a verified fact where none exists today."
    )


def test_the_promoting_method_scan_catches_a_promotion():
    """The negative control. A scan whose method names stopped matching the
    repository's would pass silently and become a comment."""
    promoting = _promoting_vault_methods()
    assert "insert_open" in promoting and "set_verification_status" in promoting
    assert "expire" in promoting

    breach = "triples = KnowledgeTripleRepository(session)\nawait triples.insert_open(row)\n"
    assert _attributes_named(breach) & promoting == {"insert_open"}
