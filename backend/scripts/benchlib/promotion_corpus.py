"""T2.108 — the G-C measurement corpus, and the preparation that flows it.

T2.40 measured G-C over the retrieval corpus and found it **structurally
incapable of promoting**: `benchlib.ingest` never sets `origin_key`, so all 62
facts folded into the reserved unknown-origin bucket, which counts once per
fact and fires no gate. This module is the corpus that can, and the shipped
path it drives.

**What is designed here is the content, not the arithmetic.** Corroboration
means independent capture sessions asserted the same thing, so the corpus
contains genuinely repeated assertions across sessions — the same operational
fact recorded twice, weeks apart, by two different agent runs; the same
dependency noted by a human-facing capture *and* asserted by the repository's
own parsed imports. A unique `origin_key` per memory would promote everything
instantly and would be a lie: it is one assertion relabelled N times, which is
an echo with N names. The corpus therefore also carries two shapes that must
**not** promote — an echo (one session, one claim, three saves) and an
under-sourced pair (two same-kind sessions inside one week against N=3) — and
their staying at `candidate` is a result, not a defect to fix.

**Driven vs stubbed, stated where the code is rather than only in the report.**

Driven — every fact, every provenance row, every ladder decision and every
`verified` event in the measured window is produced by shipping code:
`ProcessingPipeline.process_batch` (extraction + graph),
`fact_lift.run_lift` and `fact_lift.run_code_lift` (facts + `fact_sources`),
`code_deriver.assert_repo_graph` (the repository's Layer-1 assertions), and
`verification_recompute.run_recompute` → `verification_ladder.recompute_fact`
(the decision and its journal row). Nothing here writes an `events` row, a
`verification_status` or a `fact_sources` row directly.

Stubbed — two inputs, both of them *corpus*, neither of them ladder input:

1. :func:`install_repo_fixture` writes the three tables a completed index run
   would have left behind (`repositories`, `code_files`, `code_edges`). It
   stands in for cloning and indexing a repository, which needs a network and
   a working tree the gate does not have. Everything downstream of those rows
   is the shipped deriver and the shipped lift.
2. :func:`simulate_capture_time_provenance` moves each memory-kind
   `fact_sources.created_at` back to the **capture time of the memory that
   asserted it**. See that function for the full argument; it is the one place
   this module touches a row shipped code wrote, it is disclosed as simulation
   in the report, and the corpus's own declared session dates are what it
   applies.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from benchlib import bench_db  # noqa: F401  (DATABASE_URL override first)
from benchlib import run_smoke
from benchlib.caching_llm import CachingLLMOrchestrator
from benchlib.corpus import load_corpus
from benchlib.ingest import GateConfig, _parse_created_at, run_ingest

# One spelling of "run the lift until a tick reports no outstanding groups",
# including its stalled-group break and its non-convergence ceiling: a second
# copy would drift from the harvest's and the two runs would then disagree
# about what "exhausted" means.
from benchlib.harvest_l2_facts import _lift_to_exhaustion

from app.services import fact_lift
from app.services.code_deriver import assert_repo_graph
from app.services.config import get_llm_config
from app.services.fact_provenance import MEMORY_SOURCE_KIND

HERE = Path(__file__).resolve().parent
PROMOTION_DIR = HERE / "promotion"
CORPUS_PATH = PROMOTION_DIR / "corpus.json"
REPO_FIXTURE_PATH = PROMOTION_DIR / "repo_fixture.json"
CACHE_DIR = PROMOTION_DIR / "cache"

# Fixed namespace, committed with the corpus. `memory_id` is derived from the
# entry `key` rather than stored beside it: the derivation is what makes the
# corpus reproducible from its definition, and an id that is never written down
# cannot be hand-edited into a collision with another entry's.
MEMORY_ID_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "darkmem://benchlib/promotion-corpus/v1"
)

# Same derivation for the repository, so the code-side origin key -- which is
# the repo id (`fact_lift._add_code_source`) -- is stable across runs too.
REPO_ID_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "darkmem://benchlib/promotion-corpus/repo/v1"
)

MAX_CODE_LIFT_TICKS = 20

# The groups the corpus declares, and what each is for. Validated so a typo in
# a group label cannot silently produce a corpus whose design nobody can read
# back off the data.
CORPUS_GROUPS = frozenset({
    "diversity", "time_gap", "none", "echo", "under_sourced",
})

# The two groups the design expects to stay at `candidate`. Named so the
# runner can report them as an outcome rather than leaving a reader to notice
# their absence from the promoted set.
NON_PROMOTING_GROUPS = frozenset({"echo", "under_sourced"})


def memory_id_for_key(key: str) -> str:
    return str(uuid.uuid5(MEMORY_ID_NAMESPACE, key))


def repo_id_for_name(name: str) -> str:
    return str(uuid.uuid5(REPO_ID_NAMESPACE, name))


def load_promotion_corpus(path: str | Path = CORPUS_PATH) -> list[dict]:
    """Load and validate the corpus, filling each entry's derived ``memory_id``.

    Raises:
        ValueError: on a duplicate or missing ``key``, an unknown ``group``, a
            non-ISO ``created_at``, a missing ``project``, or an ``origin_key``
            that is absent, blank, or of the unattributed shape. The last one
            is the whole point of the corpus: an entry whose origin folds into
            the reserved unknown bucket cannot corroborate anything, and one
            arriving by accident would look like a fact that simply failed to
            promote.
    """
    entries = load_corpus(path)
    seen_keys: set[str] = set()
    for idx, entry in enumerate(entries):
        key = entry.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"entry {idx}: missing non-empty 'key'")
        if key in seen_keys:
            raise ValueError(f"entry {idx}: duplicate key {key!r}")
        seen_keys.add(key)

        group = entry.get("group")
        if group not in CORPUS_GROUPS:
            raise ValueError(
                f"entry {key!r}: group {group!r} is not one of {sorted(CORPUS_GROUPS)}"
            )

        project = entry.get("project")
        if not isinstance(project, str) or not project:
            raise ValueError(f"entry {key!r}: missing non-empty 'project'")

        origin_key = entry.get("origin_key")
        if not isinstance(origin_key, str) or not origin_key.strip():
            raise ValueError(
                f"entry {key!r}: missing 'origin_key'. A capture with no session "
                f"identity folds into the reserved unknown-origin bucket, which "
                f"counts once per fact and can never fire a gate -- exactly the "
                f"defect this corpus exists to correct"
            )
        normalized = origin_key.strip().lower()
        if normalized == "unknown" or normalized.startswith("unknown:"):
            raise ValueError(
                f"entry {key!r}: origin_key {origin_key!r} carries the capture "
                f"layer's unattributed marker, which fact_sources folds into the "
                f"unknown bucket"
            )

        raw_created = entry.get("created_at")
        if not isinstance(raw_created, str):
            raise ValueError(
                f"entry {key!r}: created_at must be an ISO-8601 string, "
                f"got {raw_created!r}"
            )
        try:
            datetime.fromisoformat(raw_created)
        except ValueError as exc:
            raise ValueError(
                f"entry {key!r}: created_at {raw_created!r} is not ISO-8601"
            ) from exc

        entry["memory_id"] = memory_id_for_key(key)
    return entries


def load_repo_fixture(path: str | Path = REPO_FIXTURE_PATH) -> dict:
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    repo = fixture.get("repo") or {}
    if not repo.get("name"):
        raise ValueError(f"repo fixture {path}: 'repo.name' is required")
    if not fixture.get("files"):
        raise ValueError(f"repo fixture {path}: 'files' is required and non-empty")
    return fixture


async def seed_memory_rows(session_factory, entries: list[dict]) -> list[dict]:
    """Create the base ``memories`` rows and return process_batch entries.

    The counterpart of ``retrieval_gold.seed_memory_rows`` with the one field
    that corpus lacks: **``origin_key``**. In production it is stamped at the
    door by ``resolve_origin_key``; a bench seeder that omits it hands the
    ladder a corpus of anonymous captures, which is what made T2.40's run
    unable to promote a single fact.

    ``created_at`` is written attribute-side before the commit, as both other
    seeders do, so the row carries the declared capture time rather than the
    server stamp.
    """
    from app.models.memory import Memory

    prepared: list[dict] = []
    async with session_factory() as session:
        for idx, entry in enumerate(entries):
            memory = Memory(
                id=uuid.UUID(str(entry["memory_id"])),
                content=entry["content"],
                source=entry.get("source", "bench"),
                memory_type=entry.get("memory_type"),
                importance=entry.get("importance", 0.5),
                metadata_=entry.get("metadata", {}),
                project=entry["project"],
                origin_key=entry["origin_key"],
            )
            created = _parse_created_at(entry["created_at"], idx)
            memory.created_at = created
            session.add(memory)
            prepared.append({
                "memory_id": memory.id,
                "content": memory.content,
                "source": memory.source,
                "tags": [],
                "memory_type": memory.memory_type,
                "created_at": created.isoformat(),
            })
        await session.commit()
    return prepared


_INSERT_REPO = text("""
    INSERT INTO repositories (
        id, name, url, local_path, provider, default_branch,
        last_indexed_commit, last_indexed_at, auto_sync, status
    ) VALUES (
        CAST(:id AS uuid), CAST(:name AS varchar), CAST(:url AS varchar),
        CAST(:local_path AS varchar), 'local', CAST(:branch AS varchar),
        CAST(:commit AS varchar), now(), false, 'ready'
    )
""")

_INSERT_FILE = text("""
    INSERT INTO code_files (id, repo_id, file_path, language, last_commit_sha)
    VALUES (
        CAST(:id AS uuid), CAST(:repo_id AS uuid), CAST(:file_path AS varchar),
        CAST(:language AS varchar), CAST(:commit AS varchar)
    )
""")

_INSERT_EDGE = text("""
    INSERT INTO code_edges (
        repo_id, source_kind, source_key, target_kind, target_key, edge_type
    ) VALUES (
        CAST(:repo_id AS uuid), 'file', CAST(:source_key AS varchar),
        'module', CAST(:target_key AS varchar), 'imports'
    )
""")


async def install_repo_fixture(session_factory, fixture: dict) -> str:
    """Write the rows a completed index run would have left, and return the id.

    **This is corpus, not ladder input.** It stubs the indexer — cloning a
    repository and parsing it needs a network and a working tree a gate run
    does not have — and it stubs nothing else: ``assert_repo_graph`` reads
    these three tables and mints the Layer-1 assertions, ``run_code_lift``
    turns those into facts and ``code``-kind provenance, and the ladder decides
    from the provenance. The stand-in stops at the boundary where the truth
    core begins.
    """
    repo = fixture["repo"]
    repo_id = repo_id_for_name(repo["name"])
    commit = repo.get("last_indexed_commit")
    async with session_factory() as session:
        await session.execute(_INSERT_REPO, {
            "id": repo_id,
            "name": repo["name"],
            "url": repo.get("url"),
            "local_path": repo.get("local_path"),
            "branch": repo.get("default_branch", "main"),
            "commit": commit,
        })
        for entry in fixture["files"]:
            await session.execute(_INSERT_FILE, {
                "id": str(uuid.uuid5(REPO_ID_NAMESPACE, f"{repo_id}:{entry['file_path']}")),
                "repo_id": repo_id,
                "file_path": entry["file_path"],
                "language": entry.get("language"),
                "commit": commit,
            })
        for edge in fixture.get("imports", ()):
            await session.execute(_INSERT_EDGE, {
                "repo_id": repo_id,
                "source_key": edge["source_key"],
                "target_key": edge["target_key"],
            })
        await session.commit()
    return repo_id


# The memory whose id a `memory`-kind provenance row names. Joined on the text
# spelling rather than by casting the ref to uuid: `source_ref` holds every
# kind's spelling, and a planner free to hoist a `CAST(source_ref AS uuid)`
# above the kind filter would abort on the first non-uuid ref -- the identical
# reasoning `fact_sources.memory_sources_for_fact` records.
_STAMP_CAPTURE_TIME = text("""
    UPDATE fact_sources fs
    SET created_at = m.created_at
    FROM memories m
    WHERE fs.source_kind = CAST(:kind AS text)
      AND CAST(m.id AS text) = fs.source_ref
      AND fs.created_at IS DISTINCT FROM m.created_at
    RETURNING fs.id
""")


async def simulate_capture_time_provenance(session_factory) -> int:
    """Move memory-kind provenance timestamps back to their capture times.

    **This is the one simulated step in the run, and the report names it.**

    Doc 08 §4.1 defines the time-gap gate over *assertions* — "≥ 7 days apart
    across distinct sessions". The implementation reads
    ``fact_sources.created_at``, which is when the lift **wrote** the
    provenance row. In production those two are within a lift cadence of each
    other, so the stored timestamp is a faithful proxy. A corpus ingested in
    one pass destroys the proxy: every provenance row lands inside the same
    second however far apart the captures it describes actually were, so the
    time-gap gate is unreachable on **any** backfilled corpus, and a corpus
    whose declared session timeline says otherwise would be silently ignored.

    So this restores the corpus's declared timeline into the column the gate
    reads. It is the same move ``ingest._create_memory_rows`` already makes one
    layer down for ``memories.created_at``, on the same argument recorded
    there: discarding a corpus's declared dates reduces a corpus written to
    exercise the date rules to a test of something else.

    It is still a simulation and is reported as one. Two properties bound it:
    it writes a timestamp and nothing else — no status, no journal row, no
    provenance row that did not already exist — and the value it writes is read
    from the corpus definition, so re-running produces the same stamps.

    Code-kind rows are deliberately untouched: the repository really was
    indexed now.
    """
    async with session_factory() as session:
        result = await session.execute(
            _STAMP_CAPTURE_TIME, {"kind": MEMORY_SOURCE_KIND}
        )
        stamped = len(result.all())
        await session.commit()
    return stamped


async def code_lift_to_exhaustion(session_factory) -> dict:
    """Run the shipping code lift until a tick reports no candidates."""
    ticks = facts_created = sources_added = 0
    while True:
        async with session_factory() as session:
            outcome = await fact_lift.run_code_lift(
                session, batch_size=fact_lift.MAX_LIFT_BATCH
            )
            await session.commit()
        ticks += 1
        facts_created += outcome.facts_created
        sources_added += outcome.sources_added
        if outcome.candidates == 0 or outcome.sources_added == 0:
            break
        if ticks >= MAX_CODE_LIFT_TICKS:
            raise RuntimeError(
                f"code lift did not exhaust in {MAX_CODE_LIFT_TICKS} ticks"
            )
    return {
        "ticks": ticks,
        "facts_created": facts_created,
        "sources_added": sources_added,
    }


# ── the read-back, over `events` and the vault, by SQL ───────────────────

# The Done-when's "a non-zero promotion count read back from `events` by SQL,
# not by a counter your own code kept". Nothing in this module increments
# anything; this reads what the ladder journaled.
_PROMOTIONS_BY_GATE = text("""
    SELECT payload->>'gate_fired' AS gate_fired,
           COUNT(*)                        AS promote_events,
           COUNT(DISTINCT object_id)       AS promoted_facts
    FROM events
    WHERE event_type = 'verified'
      AND object_type = 'fact'
      AND payload->>'outcome' = 'promote'
    GROUP BY 1
    ORDER BY 1
""")

# The census that makes the non-promoting groups visible as an outcome rather
# than as an absence. `origins` is COUNT(DISTINCT normalised origin_key) --
# the same quantity the ladder counts -- so an echo shows up as one origin
# behind several provenance rows.
_FACT_CENSUS = text("""
    WITH per_fact AS (
        SELECT kt.id,
               kt.project,
               kt.verification_status,
               COUNT(DISTINCT lower(btrim(fs.origin_key))) AS origins,
               COUNT(DISTINCT fs.source_kind)              AS kinds,
               COUNT(fs.id)                                AS provenance_rows
        FROM knowledge_triples kt
        LEFT JOIN fact_sources fs ON fs.fact_id = kt.id
        GROUP BY kt.id, kt.project, kt.verification_status
    )
    SELECT project, verification_status, origins, kinds, provenance_rows,
           COUNT(*) AS facts
    FROM per_fact
    GROUP BY 1, 2, 3, 4, 5
    ORDER BY 1, 2, 3, 4, 5
""")

# The two designed refusals, by name. Reported explicitly because "the corpus
# also contains claims that must not promote" is only a claim until the rows
# are shown holding at `candidate` with the origin count that explains why.
_CONTROL_FACTS = text("""
    SELECT kt.project, kt.subject_name, kt.rel_type, kt.object_name,
           kt.verification_status,
           COUNT(DISTINCT lower(btrim(fs.origin_key))) AS origins,
           COUNT(fs.id)                                AS provenance_rows
    FROM knowledge_triples kt
    LEFT JOIN fact_sources fs ON fs.fact_id = kt.id
    WHERE kt.object_name = ANY(CAST(:names AS text[]))
    GROUP BY kt.id, kt.project, kt.subject_name, kt.rel_type, kt.object_name,
             kt.verification_status
    ORDER BY kt.object_name
""")

# The object names the corpus's `echo` and `under_sourced` groups assert.
CONTROL_OBJECT_NAMES = ("cassandra", "avro")


@dataclass(frozen=True)
class ReadBack:
    promotions_by_gate: tuple[dict, ...]
    census: tuple[dict, ...]
    controls: tuple[dict, ...]

    @property
    def promoted_facts(self) -> int:
        return sum(row["promoted_facts"] for row in self.promotions_by_gate)


async def read_back(session) -> ReadBack:
    """What the journal and the vault say after the recompute has converged."""
    gates = (await session.execute(_PROMOTIONS_BY_GATE)).mappings().all()
    census = (await session.execute(_FACT_CENSUS)).mappings().all()
    controls = (
        await session.execute(_CONTROL_FACTS, {"names": list(CONTROL_OBJECT_NAMES)})
    ).mappings().all()
    return ReadBack(
        promotions_by_gate=tuple(dict(row) for row in gates),
        census=tuple(dict(row) for row in census),
        controls=tuple(dict(row) for row in controls),
    )


def render_read_back(result: ReadBack) -> str:
    lines = ["== promotions journaled, read back from `events` by SQL =="]
    if not result.promotions_by_gate:
        lines.append("  (no `promote` outcome journaled)")
    for row in result.promotions_by_gate:
        lines.append(
            f"  gate_fired={row['gate_fired']}: {row['promote_events']} promote "
            f"events over {row['promoted_facts']} distinct facts"
        )
    lines.append(f"  total distinct facts promoted: {result.promoted_facts}")

    lines.append("")
    lines.append("== fact census (project, status, distinct origins, kinds) ==")
    for row in result.census:
        lines.append(
            f"  {row['project']:<9} {row['verification_status']:<13} "
            f"origins={row['origins']} kinds={row['kinds']} "
            f"provenance_rows={row['provenance_rows']} -> {row['facts']} facts"
        )

    lines.append("")
    lines.append("== the designed refusals (echo, under-sourced) ==")
    if not result.controls:
        lines.append("  (no control fact was lifted -- extraction did not produce it)")
    for row in result.controls:
        lines.append(
            f"  {row['project']}: {row['subject_name']} {row['rel_type']} "
            f"{row['object_name']} -> {row['verification_status']} "
            f"(origins={row['origins']}, provenance_rows={row['provenance_rows']})"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class PreparedCorpus:
    """What the preparation did, for the runner's header and the ledger."""

    corpus_entries: int
    corpus_sha256: str
    gate_config: dict
    fingerprint: str
    live_calls: int
    lift: dict
    code_lift: dict
    capture_time_stamped: int
    repo_assertions: dict
    n_facts: int
    notes: tuple[str, ...] = field(default_factory=tuple)


_COUNT_FACTS = text("SELECT COUNT(*) FROM knowledge_triples")


async def prepare(
    *,
    api_key: str,
    session_factory,
    cache_dir: str | Path = CACHE_DIR,
    corpus_path: str | Path = CORPUS_PATH,
    fixture_path: str | Path = REPO_FIXTURE_PATH,
    reset,
    simulate_capture_time: bool = True,
) -> PreparedCorpus:
    """Reset, seed, ingest, lift — the whole corpus, through shipping code.

    Ordering is load-bearing in one place: the **memory** lift runs before the
    code lift. That is the order a real vault sees (notes accumulate, then a
    repository is indexed) and it is the order that produces the diversity
    gate's population — ``fact_lift._lift_one_code`` mints a fact born
    ``corroborated`` only when it opens the row itself, so a triple the memory
    side already lifted receives the repository as an ordinary second origin of
    a second kind and climbs by the count, journaling as it goes. Reversed, the
    same facts would be born on the rung with no journal row at all and would
    be invisible to every G-C promotion metric.
    """
    import hashlib

    corpus_bytes = Path(corpus_path).read_bytes()
    entries = load_promotion_corpus(corpus_path)
    fixture = load_repo_fixture(fixture_path)

    await reset()
    await run_smoke.seed_llm_purpose_configs(session_factory, api_key)

    async with session_factory() as session:
        llm_config = await get_llm_config(session)

    prepared_entries = await seed_memory_rows(session_factory, entries)
    llm = CachingLLMOrchestrator(llm_config, cache_dir=str(cache_dir))
    ingest_result = await run_ingest(llm, prepared_entries, GateConfig(), session_factory)

    lift = await _lift_to_exhaustion(session_factory)

    stamped = 0
    if simulate_capture_time:
        stamped = await simulate_capture_time_provenance(session_factory)

    repo_id = await install_repo_fixture(session_factory, fixture)
    async with session_factory() as session:
        repo_assertions = await assert_repo_graph(session, repo_id)
        await session.commit()
    code_lift = await code_lift_to_exhaustion(session_factory)

    async with session_factory() as session:
        n_facts = int((await session.execute(_COUNT_FACTS)).scalar_one())

    notes: list[str] = []
    if not simulate_capture_time:
        notes.append(
            "capture-time provenance simulation disabled: every fact_sources "
            "row carries its write time, so the time_gap gate cannot fire"
        )
    return PreparedCorpus(
        corpus_entries=len(entries),
        corpus_sha256=hashlib.sha256(corpus_bytes).hexdigest(),
        gate_config=ingest_result.gate_config,
        fingerprint=ingest_result.fingerprint,
        live_calls=ingest_result.live_calls,
        lift=lift,
        code_lift=code_lift,
        capture_time_stamped=stamped,
        repo_assertions=repo_assertions,
        n_facts=n_facts,
        notes=tuple(notes),
    )
