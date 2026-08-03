"""The G-B isolation probe: fixtures, app wiring, and one driver per surface.

The channel inventory is ``app.services.content_surfaces.CONTENT_SURFACES``
(T1.29e's registry with its build-failing completeness guard), never a design
doc's list — every doc-derived enumeration of this subsystem has been
incomplete, three sweeps in a row. ``run_probe`` refuses to run unless the
driver table and the registry agree exactly in both directions, so a surface
added to the registry without a driver stops the gate number from being
produced at all rather than silently narrowing it.

Deterministic and free by construction: the orchestrator is an in-process
stub whose vectors are content hashes and whose completions are canned. It
overrides every network-touching method, so a probe run makes zero model
calls and two runs over the same code produce the same violation set.

Fixtures are the hostile cases, not the passing ones: a superseded row with a
live successor, an entity asserted by memories in two projects, archived
rows, rows embedded only under an inactive fingerprint, rows missing from the
active partition (the backfill-queue state), a ghost fingerprint whose
partition does not exist (the degraded-anti-join state), content persisted
into append-only stores past its memory's deletion, a candidate-duplicate pair
in each project, a fact whose provenance points at a memory in the other one,
and rows long enough that a declared preview and the whole content can be told
apart on the wire. Every memory content
string leads with a per-fixture sentinel so an 80-char preview still carries
it, and every raw response body is sentinel-scanned after row enumeration —
a crossing through a field no driver modelled is a forced V1, not a pass.

The metric itself lives in ``benchlib.isolation_rules``; this module only
observes and reports.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from benchlib import bench_db  # noqa: F401  (DATABASE_URL override must run first)
from benchlib.isolation_rules import (
    ProbeReport,
    Sighting,
    scan_sentinels,
    sentinel,
)

DIMS = 8
ACTIVE_MODEL = "probe-embedder"
OLD_MODEL = "probe-embedder-old"
GHOST_MODEL = "probe-ghost"

OBSERVER = "iso-alpha"
FOREIGN = "iso-beta"

ALPHA_REPO = "repo-alpha"
BETA_REPO = "repo-beta"

ACTIVE_STATUSES = ("active",)


def _code_key(repo_name: str) -> str:
    return "code_" + repo_name.replace("-", "_")


def _hash_vector(text_: str) -> list[float]:
    digest = hashlib.sha256(text_.encode("utf-8")).digest()
    vals = [
        int.from_bytes(digest[i * 4:(i + 1) * 4], "big") / 2**32 - 0.5
        for i in range(DIMS)
    ]
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]


DUP_VECTOR = _hash_vector("dup-cluster")


@dataclass(frozen=True)
class MemoryFixture:
    key: str
    project: str
    status: str = "active"
    archived: bool = False
    embed: str = "active"  # "active" | "old" | "none"
    dup: bool = False
    superseded_by: str | None = None
    confidence: float = 0.75
    ttl_days: int | None = None
    long: bool = False

    @property
    def tail_marker(self) -> str:
        """The part of ``content`` that lies past a 200-char preview boundary.

        Same role as ``ArticleFixture.tail_marker``: the sentinel deliberately
        leads the content, so it crosses whether or not a preview truncated,
        and ``scan_sentinels`` therefore cannot tell the two apart. This
        marker is the only thing that can, and the drivers over surfaces
        declaring ``content_preview`` force a V1 when it reaches the wire.
        """
        return f"-TAIL-{self.key}"

    @property
    def content(self) -> str:
        body = (
            f"{sentinel(self.key)} postgres tuning note about "
            f"{self.key.replace('_', ' ')}"
        )
        if not self.long:
            return body
        padding = "x" * max(0, 260 - len(body))
        return f"{body} {padding}{self.tail_marker}"

    @property
    def expires_at(self) -> datetime | None:
        if self.ttl_days is None:
            return None
        return datetime.now(timezone.utc) + timedelta(days=self.ttl_days)


# Insertion order satisfies the superseded_by FK: successors first.
#
# `confidence`, `ttl_days` and `long` exist for the hygiene queue's three
# memory arms: its membership predicates are `confidence < threshold`,
# `expires_at` approaching and `status = 'superseded'`, and a fixture set with
# no low-confidence row and no TTL would leave two of the three arms served an
# empty page — a driver that observed nothing while reporting a clean zero.
# `long` puts the rows those arms return past the LEFT(content, 200) boundary
# the surface declares it crosses.
MEMORY_FIXTURES: tuple[MemoryFixture, ...] = (
    MemoryFixture("a_succ", OBSERVER),
    MemoryFixture("b_succ", FOREIGN, ttl_days=3, long=True),
    MemoryFixture("a_active", OBSERVER, dup=True, confidence=0.2, long=True),
    MemoryFixture("a_twin", OBSERVER, dup=True, ttl_days=3, long=True),
    MemoryFixture("a_super", OBSERVER, status="superseded", superseded_by="a_succ", dup=True,
                  long=True),
    MemoryFixture("a_arch", OBSERVER, archived=True, dup=True),
    MemoryFixture("a_depr", OBSERVER, status="deprecated"),
    MemoryFixture("b_active", FOREIGN, dup=True, confidence=0.2, long=True),
    MemoryFixture("b_super", FOREIGN, status="superseded", superseded_by="b_succ", long=True),
    MemoryFixture("a_oldfp", OBSERVER, embed="old"),
    MemoryFixture("a_super_nofp", OBSERVER, status="superseded", superseded_by="a_succ",
                  embed="none", long=True),
    MemoryFixture("b_nofp", FOREIGN, embed="none"),
    # Created, journaled, cited — then deleted: the retention fixture.
    MemoryFixture("a_del", OBSERVER, embed="none"),
)

FIXTURES_BY_KEY = {f.key: f for f in MEMORY_FIXTURES}

# Rows the probe itself writes through the echo surface mid-run. They are not
# seeded fixtures, but later drivers (the buffer queue, the dashboard recents)
# legitimately serve them, so their true scope must be known to the
# classification or the raw-body net misfiles them as unmodelled crossings.
ECHO_FIXTURES: dict[str, MemoryFixture] = {
    key: MemoryFixture(key, project, embed="none")
    for key, project in (
        ("echo_buffered", OBSERVER),
        ("echo_settled", OBSERVER),
        ("echo_batch_a", OBSERVER),
        ("echo_batch_b", FOREIGN),
        ("echo_mcp", OBSERVER),
        ("echo_mcp_batch", OBSERVER),
    )
}

BUFFER_KEYS: dict[str, str] = {
    "buf_alpha": OBSERVER,
    "buf_beta": FOREIGN,
    **{key: fx.project for key, fx in ECHO_FIXTURES.items()},
}


@dataclass(frozen=True)
class FactFixture:
    key: str
    project: str

    @property
    def fact_text(self) -> str:
        return f"{sentinel(self.key)} disputed fact about {self.key.replace('_', ' ')}"


# One per project, review_state='open' on both — the review queue is
# operator-wide by ratified decision (doc 08 §6), so the probe's job is to
# confirm the foreign-project row still crosses labelled, not to confirm it
# is excluded.
FACT_FIXTURES: tuple[FactFixture, ...] = (
    FactFixture("fact_a_open", OBSERVER),
    FactFixture("fact_b_open", FOREIGN),
)
FACT_FIXTURES_BY_KEY = {f.key: f for f in FACT_FIXTURES}

# `(fact key, memory key)` — the provenance rows the fact detail door groups by
# origin. The middle row is the hostile one: an observer-project fact whose
# second origin is a memory in the foreign project, so the detail door reveals
# a foreign memory id to a caller who addressed a local fact. That is id-only
# exposure by the rules module's reading, and it is what makes the door's
# provenance block something the probe has observed rather than assumed.
FACT_PROVENANCE: tuple[tuple[str, str], ...] = (
    ("fact_a_open", "a_active"),
    ("fact_a_open", "b_active"),
    ("fact_b_open", "b_active"),
)

# `(source key, target key, project)` — candidate-duplicate pairs for the
# hygiene queue's duplicates arm. Both endpoints of each pair must be `active`
# or `build_duplicates_query` excludes the pair by design, and the pair's
# `project` is the newer endpoint's, which is what `memory_dream`'s associate
# arm writes. One pair per project: the foreign one is what a deployment-wide
# queue must still serve, and what the caller's project filter must exclude.
DUPLICATE_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("a_active", "a_twin", OBSERVER),
    ("b_active", "b_succ", FOREIGN),
)


@dataclass(frozen=True)
class ArticleFixture:
    key: str
    project: str

    @property
    def tail_marker(self) -> str:
        """The part of ``content_text`` that lies past the preview boundary.

        The driver forces a V1 when this reaches the wire, which is what
        makes the over-length fixture load-bearing rather than decorative.
        The sentinel deliberately sits *inside* the first 200 characters --
        it must cross, since the preview is a declared content field -- so
        `scan_sentinels` can never distinguish a truncated preview from an
        untruncated one. This marker is the only thing that can.
        """
        return f"-TAIL-{self.key}"

    @property
    def content_text(self) -> str:
        # Deliberately past review_queue.py's LEFT(content, 200) boundary,
        # with a distinct tail past it: a fixture short enough that preview
        # and full content coincide would leave the probe's article driver
        # blind to the exact truncation regression
        # tests/test_review_queue.py's own over-length fixture exists to
        # catch (M2) -- this keeps the two closures in sync rather than
        # only unit-testing the field the classification is about.
        body = f"{sentinel(self.key)} ungrounded article about {self.key.replace('_', ' ')}"
        padding = "x" * (260 - len(body))
        return f"{body} {padding}{self.tail_marker}"


ARTICLE_FIXTURES: tuple[ArticleFixture, ...] = (
    ArticleFixture("article_a_open", OBSERVER),
    ArticleFixture("article_b_open", FOREIGN),
)
ARTICLE_FIXTURES_BY_KEY = {f.key: f for f in ARTICLE_FIXTURES}


def _all_content_fixtures() -> dict[str, MemoryFixture]:
    return {**FIXTURES_BY_KEY, **ECHO_FIXTURES}


@dataclass
class ProbeContext:
    client: object
    headers: dict[str, str]
    app: object
    pipeline: object
    stub: object
    ghost: object
    memory_ids: dict[str, uuid.UUID]
    repo_ids: dict[str, uuid.UUID]
    redis_entity_id: str
    failure_id: str
    fact_ids: dict[str, uuid.UUID]
    article_ids: dict[str, uuid.UUID]
    retention_conversation_id: str
    scoped_conversation_id: str | None = None
    wide_conversation_id: str | None = None
    notes: list[str] = field(default_factory=list)


class StubOrchestrator:
    """Deterministic, network-free stand-in for the LLM orchestrator.

    Duck-types the ``LLMOrchestrator`` surface the retrieval and content
    channels reach: embed / embed_batch / embed_batch_chunked resolve to
    content-hash vectors under a fixed fingerprint, chat completions return
    canned strings, and there is no HTTP client to leak or to pay. The probe
    is gate-adjacent, so it must stay free and reproducible (Ruling 3).
    """

    def __init__(self, model: str = ACTIVE_MODEL):
        from app.config import LLMPurposeConfig

        self.model = model
        self.config = {
            purpose: LLMPurposeConfig(model=model, dimensions=DIMS, api_kind="openai")
            for purpose in (
                "embedding", "extraction", "classification",
                "reasoning", "summarization", "reranker",
            )
        }
        self.chat_calls: list[tuple[str, list]] = []

    def llm_fingerprint(self) -> str:
        return f"{self.model}|{DIMS}"

    async def embed(self, text: str) -> tuple[list[float], str]:
        return _hash_vector(text), self.llm_fingerprint()

    async def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], str]:
        return [_hash_vector(t) for t in texts], self.llm_fingerprint()

    async def embed_batch_chunked(
        self, texts: list[str], batch_size: int = 20, concurrency: int = 1,
    ) -> tuple[list[list[float]], str]:
        return await self.embed_batch(texts)

    async def chat_completion(self, purpose: str, messages: list, **kwargs) -> str:
        self.chat_calls.append((purpose, messages))
        if purpose == "extraction":
            return json.dumps({
                "entities": [], "relationships": [], "memory_type": "fact",
                "importance": 0.5, "summary": "probe", "emotions": [], "flags": [],
            })
        return "probe answer"

    async def chat_completion_stream(self, purpose: str, messages: list, **kwargs):
        self.chat_calls.append((purpose, messages))
        yield "probe answer"


def _mem(
    surface: str,
    door: str,
    case: str,
    fx: MemoryFixture,
    *,
    kind: str = "content",
    req_p: str | None = None,
    req_s: tuple[str, ...] | None = None,
    lp: bool = False,
    ls: bool = False,
    retention: bool = False,
    forced: str | None = None,
) -> Sighting:
    return Sighting(
        surface=surface, door=door, case=case, row=fx.key, kind=kind,
        true_project=fx.project, true_status=fx.status, archived=fx.archived,
        requested_project=req_p, requested_statuses=req_s,
        label_project=lp, label_status=ls, retention=retention,
        forced_v1_reason=forced,
    )


def _account_body(
    surface: str,
    door: str,
    case: str,
    body: str,
    accounted: set[str],
) -> list[Sighting]:
    """Sentinels present in the raw body but absent from every enumerated row.

    Ruling 4's preview leaks crossed through fields nobody enumerated; this
    is the net under the drivers. Always a forced V1 — either a real leak or
    a driver that failed to model a field, and both must fail loud.
    """
    out: list[Sighting] = []
    for key in sorted(scan_sentinels(body) - accounted):
        fx = _all_content_fixtures().get(key)
        out.append(Sighting(
            surface=surface, door=door, case=f"{case} [raw body]", row=key,
            true_project=fx.project if fx else None,
            true_status=fx.status if fx else None,
            forced_v1_reason="sentinel outside every enumerated row",
        ))
    return out


# ── seeding ──────────────────────────────────────────────────────────────


async def _seed(session_factory, stub: StubOrchestrator, old: StubOrchestrator) -> dict:
    from sqlalchemy import text

    from app.api.auth import hash_password
    from app.config import FEATURE_FLAGS_DEFAULTS
    from app.models.config import Config
    from app.models.memory import Memory
    from app.repositories.fact_sources import FactSourceRepository
    from app.repositories.memory_relations import upsert_edge
    from app.services.dream_journal import NEAR_DUPLICATE_PASS
    from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
    from app.services.events import record_event
    from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
    from app.services.feature_flags import FEATURE_FLAGS_KEY
    from app.services.memory_buffer import enqueue
    from app.services.memory_dream import near_duplicate_block
    from app.services.pipeline_failures import PipelineFailureService

    active_fp = stub.llm_fingerprint()
    old_fp = old.llm_fingerprint()
    memory_ids: dict[str, uuid.UUID] = {}
    repo_ids: dict[str, uuid.UUID] = {}

    async with session_factory() as session:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=dict(FEATURE_FLAGS_DEFAULTS)))
        session.add(Config(
            key="admin_password_hash", value={"hash": hash_password("probe-password")},
        ))
        await session.flush()

        for fingerprint, model in ((active_fp, ACTIVE_MODEL), (old_fp, OLD_MODEL)):
            await embedder_registry.register(session, EmbedderInfo(
                fingerprint=fingerprint, model_id=model, dims=DIMS, source="llm",
            ))

        for fx in MEMORY_FIXTURES:
            memory = Memory(
                id=uuid.uuid4(), content=fx.content, source="probe",
                memory_type="fact", importance=0.5, metadata_={},
                project=fx.project, status=fx.status,
                superseded_by=memory_ids[fx.superseded_by] if fx.superseded_by else None,
                is_archived=fx.archived, expires_at=fx.expires_at,
                confidence=fx.confidence,
            )
            session.add(memory)
            memory_ids[fx.key] = memory.id
        await session.flush()

        mem_table = child_table("memory_embeddings", active_fp)
        old_table = child_table("memory_embeddings", old_fp)
        for fx in MEMORY_FIXTURES:
            if fx.embed == "none":
                continue
            table = mem_table if fx.embed == "active" else old_table
            fingerprint = active_fp if fx.embed == "active" else old_fp
            vector = DUP_VECTOR if fx.dup else _hash_vector(fx.content)
            await session.execute(
                text(
                    f"INSERT INTO {table} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (CAST(:mid AS uuid), :fp, CAST(:vec AS vector), "
                    "CAST(:payload AS jsonb))"
                ),
                {
                    "mid": str(memory_ids[fx.key]), "fp": fingerprint,
                    "vec": str(vector),
                    "payload": json.dumps({
                        "content": fx.content, "source": "probe", "tags": [],
                        "memory_type": "fact", "created_at": "2026-07-28T00:00:00+00:00",
                    }),
                },
            )

        redis_entity_id = str(uuid.uuid4())
        alpha_cache_id = str(uuid.uuid4())
        beta_db_id = str(uuid.uuid4())
        entity_rows = (
            (redis_entity_id, "redis", "tool",
             [memory_ids["a_active"], memory_ids["b_active"], memory_ids["a_super"]]),
            (alpha_cache_id, "alpha cache", "concept", [memory_ids["a_super"]]),
            (beta_db_id, "beta db", "tool", [memory_ids["b_active"]]),
        )
        for eid, name, etype, mids in entity_rows:
            await session.execute(
                text(
                    "INSERT INTO entities (id, name, entity_type, properties, memory_ids) "
                    "VALUES (CAST(:id AS uuid), :name, :etype, CAST(:props AS jsonb), "
                    "CAST(:mids AS uuid[]))"
                ),
                {"id": eid, "name": name, "etype": etype, "props": json.dumps({}),
                 "mids": [str(m) for m in mids]},
            )
        relation_rows = (
            (redis_entity_id, alpha_cache_id, "USES", [memory_ids["a_super"]]),
            (redis_entity_id, beta_db_id, "USES", [memory_ids["b_active"]]),
        )
        for src, tgt, rel, mids in relation_rows:
            await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(id, source_entity_id, target_entity_id, rel_type, weight, memory_ids) "
                    "VALUES (gen_random_uuid(), CAST(:src AS uuid), CAST(:tgt AS uuid), "
                    ":rel, 1.0, CAST(:mids AS uuid[]))"
                ),
                {"src": src, "tgt": tgt, "rel": rel, "mids": [str(m) for m in mids]},
            )

        await session.execute(
            text(
                "INSERT INTO memory_crossrefs (memory_id, related_memory_id, score) "
                "VALUES (CAST(:a AS uuid), CAST(:b AS uuid), 0.9)"
            ),
            {"a": str(memory_ids["a_super"]), "b": str(memory_ids["b_active"])},
        )

        for source_key, target_key, project in DUPLICATE_PAIRS:
            await upsert_edge(
                session,
                source_memory_id=memory_ids[source_key],
                target_memory_id=memory_ids[target_key],
                rel_type="RELATES_TO",
                project=project,
                pass_key=NEAR_DUPLICATE_PASS,
                block=near_duplicate_block(
                    score=0.93, verdict="duplicate", existing=None,
                    detected_at="2026-07-28T00:00:00+00:00",
                ),
            )

        for repo_name in (ALPHA_REPO, BETA_REPO):
            rid = uuid.uuid4()
            repo_ids[repo_name] = rid
            await session.execute(
                text(
                    "INSERT INTO repositories "
                    "(id, name, provider, default_branch, status, auto_sync) "
                    "VALUES (CAST(:id AS uuid), :name, 'local', 'main', 'ready', FALSE)"
                ),
                {"id": str(rid), "name": repo_name},
            )
            file_id = str(uuid.uuid4())
            await session.execute(
                text(
                    "INSERT INTO code_files (id, repo_id, file_path, language) "
                    "VALUES (CAST(:id AS uuid), CAST(:rid AS uuid), :path, 'python')"
                ),
                {"id": file_id, "rid": str(rid), "path": f"{repo_name}/widget.py"},
            )
            await session.execute(
                text(
                    "INSERT INTO code_symbols "
                    "(id, file_id, name, kind, line_start, line_end, source_code) "
                    "VALUES (gen_random_uuid(), CAST(:fid AS uuid), :name, 'function', "
                    "1, 5, :src)"
                ),
                {
                    "fid": file_id, "name": f"widgetparse_{repo_name.replace('-', '_')}",
                    "src": f"def widgetparse():\n    return '{sentinel(_code_key(repo_name))}'",
                },
            )
            chunk_table = child_table("code_chunk_embeddings", active_fp)
            await session.execute(
                text(
                    f"INSERT INTO {chunk_table} "
                    "(fingerprint, repo_id, file_path, language, symbol_name, "
                    "chunk_content, line_start, line_end, embedding) "
                    "VALUES (:fp, CAST(:rid AS uuid), :path, 'python', :sym, :content, "
                    "1, 5, CAST(:vec AS vector))"
                ),
                {
                    "fp": active_fp, "rid": str(rid), "path": f"{repo_name}/widget.py",
                    "sym": f"widgetparse_{repo_name.replace('-', '_')}",
                    "content": f"widgetparse {sentinel(_code_key(repo_name))}",
                    "vec": str(_hash_vector(f"code {repo_name}")),
                },
            )
        old_chunk_table = child_table("code_chunk_embeddings", old_fp)
        await session.execute(
            text(
                f"INSERT INTO {old_chunk_table} "
                "(fingerprint, repo_id, file_path, language, symbol_name, "
                "chunk_content, line_start, line_end, embedding) "
                "VALUES (:fp, CAST(:rid AS uuid), :path, 'python', 'widgetparse_old', "
                ":content, 1, 5, CAST(:vec AS vector))"
            ),
            {
                "fp": old_fp, "rid": str(repo_ids[ALPHA_REPO]),
                "path": f"{ALPHA_REPO}/old.py",
                "content": f"widgetparse {sentinel('code_oldfp')}",
                "vec": str(_hash_vector("code oldfp")),
            },
        )

        await enqueue(session, content=f"{sentinel('buf_alpha')} buffered capture",
                      project=OBSERVER, source="probe")
        await enqueue(session, content=f"{sentinel('buf_beta')} buffered capture",
                      project=FOREIGN, source="probe")

        failure_service = PipelineFailureService(session)
        for key in ("a_active", "b_active", "a_super"):
            await failure_service.record(
                entity_type="memory", entity_id=memory_ids[key],
                pipeline_name="memory_processing", failed_step="extract",
                error_message="probe failure",
            )
        failure_id = (await session.execute(
            text("SELECT id FROM pipeline_failures LIMIT 1")
        )).scalar_one()

        from app.repositories.knowledge_triples import KnowledgeTripleRepository

        fact_ids: dict[str, uuid.UUID] = {}
        kt_repo = KnowledgeTripleRepository(session)
        for fx in FACT_FIXTURES:
            row = await kt_repo.insert_open(
                triple_key=f"probe-{fx.key}",
                subject_name=f"probe-subject-{fx.key}",
                object_name=f"probe-object-{fx.key}",
                rel_type="RELATED_TO",
                fact=fx.fact_text,
                reference_time=datetime.now(timezone.utc),
                project=fx.project,
                review_state="open",
            )
            fact_ids[fx.key] = uuid.UUID(row["id"])

        source_repo = FactSourceRepository(session)
        for fact_key, memory_key in FACT_PROVENANCE:
            await source_repo.add_source(
                fact_id=fact_ids[fact_key],
                source_kind=MEMORY_SOURCE_KIND,
                source_ref=memory_source_ref(memory_ids[memory_key]),
                origin_key=f"probe-origin-{memory_key}",
            )

        article_ids: dict[str, uuid.UUID] = {}
        for fx in ARTICLE_FIXTURES:
            article_id = uuid.uuid4()
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_articles (
                        id, subject_key, project, content, status, review_state
                    )
                    VALUES (
                        CAST(:id AS uuid), :subject_key, :project, :content,
                        'candidate', 'open'
                    )
                    """
                ),
                {
                    "id": str(article_id), "subject_key": f"probe-{fx.key}",
                    "project": fx.project, "content": fx.content_text,
                },
            )
            article_ids[fx.key] = article_id

        for key in ("a_active", "b_active"):
            await record_event(
                session, event_type="memory.created", object_type="memory",
                object_id=memory_ids[key], project=FIXTURES_BY_KEY[key].project,
                source="probe", payload={},
            )
        await record_event(
            session, event_type="pipeline", object_type="memory",
            object_id=memory_ids["b_active"], project=FOREIGN, source="probe",
            payload={"embed": "completed"},
        )
        await record_event(
            session, event_type="buffer_discarded", object_type="memory",
            object_id=memory_ids["a_del"], project=OBSERVER, source="probe",
            payload={"content_preview": FIXTURES_BY_KEY["a_del"].content[:500]},
        )

        retention_conversation_id = str(uuid.uuid4())
        await session.execute(
            text(
                "INSERT INTO conversations (id, title) "
                "VALUES (CAST(:id AS uuid), 'retention probe')"
            ),
            {"id": retention_conversation_id},
        )
        await session.execute(
            text(
                "INSERT INTO messages (id, conversation_id, role, content, context) "
                "VALUES (gen_random_uuid(), CAST(:cid AS uuid), 'assistant', "
                "'probe answer', CAST(:ctx AS jsonb))"
            ),
            {
                "cid": retention_conversation_id,
                "ctx": json.dumps({"memories": [{
                    "id": str(memory_ids["a_del"]),
                    "content": FIXTURES_BY_KEY["a_del"].content[:150],
                    "score": 0.9, "source": "probe", "tags": [], "created_at": "",
                }]}),
            },
        )
        await session.execute(
            text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(memory_ids["a_del"])},
        )

        await session.commit()

    return {
        "memory_ids": memory_ids,
        "repo_ids": repo_ids,
        "redis_entity_id": redis_entity_id,
        "failure_id": str(failure_id),
        "fact_ids": fact_ids,
        "article_ids": article_ids,
        "retention_conversation_id": retention_conversation_id,
    }


# ── app wiring ───────────────────────────────────────────────────────────


async def _wire_app(stub: StubOrchestrator):
    from app.api.mcp import server as mcp_server
    from app.database import async_session_factory
    from app.main import app
    from app.services.job_registry import Job, JobRegistry
    from app.services.pipeline import ProcessingPipeline, _flag_cache_reset

    pipeline = ProcessingPipeline(stub, async_session_factory)
    app.state.llm = stub
    app.state.pipeline = pipeline
    app.state.llm_config_lock = asyncio.Lock()

    registry = JobRegistry(async_session_factory)

    async def _noop():
        return None

    registry.register(Job(
        key="repo_sync", display_name="Repository Sync", description="(probe stub)",
        default_cron="*/5 * * * *", min_interval_seconds=30, runner=_noop,
    ))
    app.state.job_registry = registry
    app.state.repo_sync_wakeup = registry.get("repo_sync").wakeup

    mcp_server.set_pipeline(pipeline)
    _flag_cache_reset()
    return app, pipeline


async def _call_mcp(name: str, arguments: dict) -> str:
    from app.api.mcp.server import mcp

    result = await mcp.call_tool(name, arguments)
    if isinstance(result, dict):
        return json.dumps(result)
    if isinstance(result, tuple):
        result = result[0]
    for block in result:
        text_value = getattr(block, "text", None)
        if text_value is not None:
            return text_value
    return ""


def _row_key(row_content: str) -> str | None:
    found = scan_sentinels(row_content or "")
    return next(iter(found)) if found else None


def _parse_sse(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


# ── drivers, one per registry surface ────────────────────────────────────


async def _drive_memory_search(ctx: ProbeContext) -> list[Sighting]:
    surface = "memory_search"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    async def rest_case(door: str, body: dict, case: str, req_p, req_s):
        response = await ctx.client.post(door, json=body, headers=ctx.headers)
        response.raise_for_status()
        payload = response.json()
        rows = payload["items"] if isinstance(payload, dict) else payload
        accounted: set[str] = set()
        for row in rows:
            fx = ids_to_fx.get(str(row["id"]))
            if fx is None:
                continue
            accounted.add(fx.key)
            out.append(_mem(
                surface, door, case, fx, req_p=req_p, req_s=req_s,
                lp=row.get("project") == fx.project,
                ls=row.get("status") == fx.status,
            ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await rest_case(
        "/api/v1/memories/search",
        {"query": "postgres tuning notes", "project": OBSERVER, "limit": 50},
        "scoped project, default statuses", OBSERVER, ACTIVE_STATUSES,
    )
    await rest_case(
        "/api/v1/memories/search",
        {"query": "postgres tuning notes", "project": OBSERVER,
         "status": ["active", "superseded"], "limit": 50},
        "scoped project, superseded requested", OBSERVER, ("active", "superseded"),
    )
    await rest_case(
        "/api/v1/memories/search",
        {"query": "postgres tuning notes", "limit": 50},
        "wide project (all projects), default statuses", None, ACTIVE_STATUSES,
    )
    await rest_case(
        "/api/v1/memories/search",
        {"project": OBSERVER, "memory_type": "fact", "limit": 50},
        "relational arm (no query), scoped project", OBSERVER, ACTIVE_STATUSES,
    )
    await rest_case(
        "/api/v1/memories/search/paginated",
        {"query": "postgres tuning notes", "project": OBSERVER, "limit": 50},
        "paginated, scoped project", OBSERVER, ACTIVE_STATUSES,
    )

    door = "mcp:memory_search"
    body = await _call_mcp("memory_search", {"query": "postgres tuning notes", "limit": 50})
    rows = json.loads(body)
    accounted: set[str] = set()
    for row in rows:
        fx = ids_to_fx.get(str(row["id"]))
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(_mem(
            surface, door, "MCP door (no project parameter, default statuses)", fx,
            req_p=None, req_s=ACTIVE_STATUSES,
            lp=row.get("project") == fx.project,
            ls=row.get("status") == fx.status,
        ))
    out.extend(_account_body(surface, door, "MCP door", body, accounted))
    return out


async def _drive_memory_reason(ctx: ProbeContext) -> list[Sighting]:
    surface = "memory_reason"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    async def one_case(door: str, body_text: str, sources: list[dict], case: str, req_p):
        accounted: set[str] = set()
        for src in sources:
            fx = ids_to_fx.get(str(src.get("memory_id")))
            if fx is None:
                continue
            accounted.add(fx.key)
            out.append(_mem(
                surface, door, case, fx, kind="preview",
                req_p=req_p, req_s=ACTIVE_STATUSES,
                lp="project" in src, ls="status" in src,
            ))
        out.extend(_account_body(surface, door, case, body_text, accounted))

    for req_p, case in ((OBSERVER, "scoped project"), (None, "default (every project, ratified)")):
        body = {"question": "what do we know about postgres tuning?", "limit": 20}
        if req_p:
            body["project"] = req_p
        response = await ctx.client.post("/api/v1/memories/reason", json=body, headers=ctx.headers)
        response.raise_for_status()
        await one_case("POST /api/v1/memories/reason", response.text,
                       response.json()["sources"], case, req_p)

    for req_p, case in ((OBSERVER, "MCP scoped project"), (None, "MCP default (every project)")):
        args = {"question": "what do we know about postgres tuning?", "limit": 20}
        if req_p:
            args["project"] = req_p
        body = await _call_mcp("memory_reason", args)
        await one_case("mcp:memory_reason", body, json.loads(body)["sources"], case, req_p)
    return out


async def _drive_chat_retrieval(ctx: ProbeContext) -> list[Sighting]:
    surface = "chat_retrieval"
    door = "POST /api/v1/chat/completions"
    out: list[Sighting] = []

    async def one_case(context: dict | None, case: str, req_p):
        response = await ctx.client.post(
            "/api/v1/chat/completions",
            json={"content": "what do we know about postgres tuning?", "context": context},
            headers=ctx.headers,
        )
        response.raise_for_status()
        events = _parse_sse(response.text)
        accounted: set[str] = set()
        conversation_id = None
        for event in events:
            if event.get("type") == "sources":
                for row in event.get("memories", []):
                    key = _row_key(row.get("content", ""))
                    if key is None:
                        continue
                    fx = FIXTURES_BY_KEY[key]
                    accounted.add(key)
                    out.append(_mem(
                        surface, door, case, fx,
                        req_p=req_p, req_s=ACTIVE_STATUSES,
                        lp="project" in row, ls="status" in row,
                    ))
            if event.get("type") == "done":
                conversation_id = event.get("conversation_id")
        out.extend(_account_body(surface, door, case, response.text, accounted))
        return conversation_id

    ctx.scoped_conversation_id = await one_case(
        {"project": OBSERVER}, "scoped project context", OBSERVER,
    )
    ctx.wide_conversation_id = await one_case(
        None, "default context (no project)", None,
    )
    return out


async def _drive_graph_memory_context(ctx: ProbeContext) -> list[Sighting]:
    surface = "graph_memory_context"
    seed_id = str(ctx.memory_ids["a_active"])
    door = "GET /api/v1/graph/memory-context/{memory_id}"
    case = f"seed a_active ({OBSERVER}, active)"
    response = await ctx.client.get(
        f"/api/v1/graph/memory-context/{seed_id}", headers=ctx.headers,
    )
    response.raise_for_status()
    payload = response.json()
    out: list[Sighting] = []
    accounted: set[str] = set()
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    for neighbor in payload.get("neighbors", []):
        fx = ids_to_fx.get(str(neighbor["id"]))
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(_mem(
            surface, door, case, fx, kind="preview",
            req_p=OBSERVER, req_s=ACTIVE_STATUSES,
            lp=neighbor.get("project") == fx.project,
            ls=neighbor.get("status") == fx.status,
        ))

    for entity in payload.get("entities", []):
        for mid in entity.get("memory_ids", []):
            fx = ids_to_fx.get(str(mid))
            if fx is None or fx.key == "a_active":
                continue
            if fx.project != OBSERVER or fx.status != "active":
                out.append(_mem(
                    surface, door,
                    f"{case}: entity {entity['name']!r} memory_ids", fx, kind="id",
                ))

    beta_only = [r for r in payload.get("relations", []) if r.get("target") == "beta db"]
    for relation in beta_only:
        out.append(Sighting(
            surface=surface, door=door,
            case=f"{case}: relation asserted only by a {FOREIGN} memory",
            row=f"redis->{relation['target']}", kind="id",
            true_project=FOREIGN,
        ))
    super_only = [r for r in payload.get("relations", []) if r.get("target") == "alpha cache"]
    for relation in super_only:
        out.append(Sighting(
            surface=surface, door=door,
            case=f"{case}: relation asserted only by a superseded memory "
                 "(deliberate: no status predicate on the relation arm)",
            row=f"redis->{relation['target']}", kind="id",
            true_project=OBSERVER, true_status="superseded",
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    return out


async def _drive_bulk_partition_read(ctx: ProbeContext) -> list[Sighting]:
    surface = "bulk_partition_read"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    async def projection_case(params: str, case: str, req_p, req_s):
        door = "GET /api/v1/vectors/projection"
        response = await ctx.client.get(
            f"/api/v1/vectors/projection{params}", headers=ctx.headers,
        )
        response.raise_for_status()
        accounted: set[str] = set()
        for point in response.json()["points"]:
            fx = ids_to_fx.get(str(point["memory_id"]))
            if fx is None:
                continue
            accounted.add(fx.key)
            forced = None
            if fx.embed == "old":
                forced = "row served out of an inactive fingerprint partition"
            out.append(_mem(
                surface, door, case, fx, kind="preview",
                req_p=req_p, req_s=req_s,
                lp=point.get("project") == fx.project,
                ls=point.get("status") == fx.status,
                forced=forced,
            ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await projection_case(f"?project={OBSERVER}", "scoped project, default statuses",
                          OBSERVER, ACTIVE_STATUSES)
    await projection_case("", "wide project, default statuses", None, ACTIVE_STATUSES)
    await projection_case(
        "?status=active&status=superseded", "wide project, superseded requested",
        None, ("active", "superseded"),
    )

    async def unified_case(params: str, case: str, req_p):
        door = "GET /api/v1/graph/unified"
        response = await ctx.client.get(
            f"/api/v1/graph/unified{params}", headers=ctx.headers,
        )
        response.raise_for_status()
        payload = response.json()
        accounted: set[str] = set()
        for node in payload.get("memories", []):
            fx = ids_to_fx.get(str(node["id"]))
            if fx is None:
                continue
            accounted.add(fx.key)
            forced = None
            if fx.embed == "old":
                forced = "row served out of an inactive fingerprint partition"
            out.append(_mem(
                surface, door, case, fx,
                req_p=req_p, req_s=ACTIVE_STATUSES,
                lp=node.get("project") == fx.project,
                ls=node.get("status") == fx.status,
                forced=forced,
            ))
        for entity in payload.get("entities", []) or []:
            for mid in entity.get("memory_ids", []):
                fx = ids_to_fx.get(str(mid))
                if fx is None:
                    continue
                if fx.project != OBSERVER or fx.status != "active":
                    out.append(_mem(
                        surface, door, f"{case}: entity overlay memory_ids",
                        fx, kind="id",
                    ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await unified_case(f"?project={OBSERVER}&include_entities=true",
                       "scoped project with entity overlay", OBSERVER)
    await unified_case("", "wide project", None)
    return out


async def _drive_duplicates_probe(ctx: ProbeContext) -> list[Sighting]:
    surface = "duplicates_probe"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}
    source_id = str(ctx.memory_ids["a_active"])
    case = "seed a_active; scope derived from the source memory"

    async def account_rows(door: str, body_text: str, rows: list[dict]):
        accounted: set[str] = set()
        for row in rows:
            fx = ids_to_fx.get(str(row["memory_id"]))
            if fx is None:
                continue
            accounted.add(fx.key)
            out.append(_mem(
                surface, door, case, fx,
                req_p=OBSERVER, req_s=ACTIVE_STATUSES,
            ))
        out.extend(_account_body(surface, door, case, body_text, accounted))

    response = await ctx.client.get(
        f"/api/v1/memories/{source_id}/duplicates?threshold=0.9", headers=ctx.headers,
    )
    response.raise_for_status()
    await account_rows(
        "GET /api/v1/memories/{memory_id}/duplicates", response.text, response.json(),
    )

    body = await _call_mcp(
        "memory_find_duplicates", {"memory_id": source_id, "threshold": 0.9},
    )
    await account_rows("mcp:memory_find_duplicates", body, json.loads(body))
    return out


async def _drive_code_search(ctx: ProbeContext) -> list[Sighting]:
    surface = "code_search"
    out: list[Sighting] = []
    repo_by_id = {str(rid): name for name, rid in ctx.repo_ids.items()}
    code_keys = {_code_key(ALPHA_REPO): ALPHA_REPO, _code_key(BETA_REPO): BETA_REPO}

    def code_sighting(door, case, key, true_repo, req_repo, labelled, forced=None):
        return Sighting(
            surface=surface, door=door, case=case, row=key, kind="content",
            true_project=true_repo, true_status=None,
            requested_project=req_repo, requested_statuses=None,
            label_project=labelled, forced_v1_reason=forced,
        )

    async def account_code(door: str, case: str, body_text: str, rows: list[dict], req_repo):
        accounted: set[str] = set()
        for row in rows:
            key = _row_key(row.get("chunk_content", ""))
            if key is None:
                continue
            accounted.add(key)
            if key == "code_oldfp":
                out.append(code_sighting(
                    door, case, key, ALPHA_REPO, req_repo, True,
                    forced="chunk served out of an inactive fingerprint partition",
                ))
                continue
            true_repo = code_keys.get(key) or repo_by_id.get(str(row.get("repo_id")))
            out.append(code_sighting(
                door, case, key, true_repo, req_repo,
                labelled=str(row.get("repo_id") or "") in repo_by_id,
            ))
        out.extend(_account_body(surface, door, case, body_text, accounted))

    door = "POST /api/v1/code/search"
    response = await ctx.client.post(
        "/api/v1/code/search",
        json={"query": "widgetparse", "repo_id": str(ctx.repo_ids[ALPHA_REPO]), "limit": 20},
        headers=ctx.headers,
    )
    response.raise_for_status()
    await account_code(door, "scoped to repo-alpha", response.text, response.json(), ALPHA_REPO)

    response = await ctx.client.post(
        "/api/v1/code/search", json={"query": "widgetparse", "limit": 20},
        headers=ctx.headers,
    )
    response.raise_for_status()
    await account_code(door, "wide (every repository)", response.text, response.json(), None)

    body = await _call_mcp("code_search", {"query": "widgetparse", "repo_name": ALPHA_REPO})
    payload = json.loads(body)
    rows = payload if isinstance(payload, list) else payload.get("results", [])
    await account_code("mcp:code_search", "MCP scoped to repo-alpha", body, rows, ALPHA_REPO)
    return out


async def _drive_memory_by_id(ctx: ProbeContext) -> list[Sighting]:
    surface = "memory_by_id"
    out: list[Sighting] = []
    fx = FIXTURES_BY_KEY["a_super"]
    mid = str(ctx.memory_ids["a_super"])

    door = "GET /api/v1/memories/{memory_id}"
    case = "id-addressed read of a superseded row (lineage inspection)"
    response = await ctx.client.get(f"/api/v1/memories/{mid}", headers=ctx.headers)
    response.raise_for_status()
    row = response.json()
    out.append(_mem(
        surface, door, case, fx,
        lp=row.get("project") == fx.project, ls=row.get("status") == fx.status,
    ))
    for ref in row.get("related_memories") or []:
        ref_fx = FIXTURES_BY_KEY.get(
            next((k for k, v in ctx.memory_ids.items() if str(v) == str(ref["memory_id"])), ""),
        )
        if ref_fx is not None and (ref_fx.project != OBSERVER or ref_fx.status != "active"):
            out.append(_mem(surface, door, f"{case}: crossref ids", ref_fx, kind="id"))
    out.extend(_account_body(surface, door, case, response.text, {fx.key}))

    body = await _call_mcp("memory_get", {"memory_id": mid})
    row = json.loads(body)
    out.append(_mem(
        surface, "mcp:memory_get", case, fx,
        lp=row.get("project") == fx.project, ls=row.get("status") == fx.status,
    ))
    out.extend(_account_body(surface, "mcp:memory_get", case, body, {fx.key}))
    return out


async def _drive_memory_write_echo(ctx: ProbeContext) -> list[Sighting]:
    surface = "memory_write_echo"
    out: list[Sighting] = []

    door = "POST /api/v1/memories"
    response = await ctx.client.post(
        "/api/v1/memories",
        json={"content": f"{sentinel('echo_buffered')} probe echo", "project": OBSERVER},
        headers=ctx.headers,
    )
    if response.status_code != 202:
        ctx.notes.append(f"write echo: buffered POST returned {response.status_code}")
    out.extend(_account_body(surface, door, "buffered accept (202 ack)", response.text, set()))

    response = await ctx.client.post(
        "/api/v1/memories?wait_process=true",
        json={"content": f"{sentinel('echo_settled')} postgres tuning echo", "project": OBSERVER},
        headers=ctx.headers,
    )
    if response.status_code == 201:
        row = response.json()
        out.append(Sighting(
            surface=surface, door=door, case="wait_process settle re-read",
            row="echo_settled", true_project=row.get("project"),
            true_status=row.get("status"),
            label_project="project" in row, label_status="status" in row,
        ))
        out.extend(_account_body(
            surface, door, "wait_process settle re-read", response.text, {"echo_settled"},
        ))
    else:
        ctx.notes.append(
            "write echo: wait_process settle returned "
            f"{response.status_code}; settle re-read not observed",
        )

    response = await ctx.client.post(
        "/api/v1/memories/batch",
        json={"entries": [
            {"content": f"{sentinel('echo_batch_a')} probe echo", "project": OBSERVER},
            {"content": f"{sentinel('echo_batch_b')} probe echo", "project": FOREIGN},
        ]},
        headers=ctx.headers,
    )
    out.extend(_account_body(
        surface, "POST /api/v1/memories/batch", "buffered batch accept",
        response.text, set(),
    ))

    body = await _call_mcp("memory_add", {
        "content": f"{sentinel('echo_mcp')} probe echo", "project": OBSERVER,
    })
    out.extend(_account_body(surface, "mcp:memory_add", "buffered accept", body, set()))

    body = await _call_mcp("memory_batch_add", {"entries": [
        {"content": f"{sentinel('echo_mcp_batch')} probe echo", "project": OBSERVER},
    ]})
    out.extend(_account_body(surface, "mcp:memory_batch_add", "buffered accept", body, set()))

    mid = str(ctx.memory_ids["a_twin"])
    body = await _call_mcp("memory_update", {"memory_id": mid, "tags": ["probe/echo"]})
    row = json.loads(body)
    fx = FIXTURES_BY_KEY["a_twin"]
    out.append(_mem(
        surface, "mcp:memory_update", "update echo of the caller's own row", fx,
        lp=row.get("project") == fx.project, ls=row.get("status") == fx.status,
    ))
    out.extend(_account_body(
        surface, "mcp:memory_update", "update echo", body, {"a_twin"},
    ))
    return out


async def _drive_reembed_backfill_queue(ctx: ProbeContext) -> list[Sighting]:
    surface = "reembed_backfill_queue"
    door = "GET /api/v1/reembed/obsolete/memories"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    case = "active partition present (deployment-wide queue, ratified)"
    response = await ctx.client.get("/api/v1/reembed/obsolete/memories", headers=ctx.headers)
    response.raise_for_status()
    payload = response.json()
    accounted: set[str] = set()
    for item in payload["items"]:
        fx = ids_to_fx.get(str(item["memory_id"]))
        if fx is None:
            key = _row_key(item.get("content_preview", ""))
            fx = _all_content_fixtures().get(key or "")
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(_mem(
            surface, door, case, fx, kind="preview",
            lp="project" in item, ls="status" in item,
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    if payload.get("partition_missing"):
        ctx.notes.append("reembed queue reported partition_missing with the partition present")

    ghost_case = "active partition ABSENT (the degraded-anti-join state, Ruling 4)"
    original_llm = ctx.pipeline.llm
    ctx.pipeline.llm = ctx.ghost
    try:
        response = await ctx.client.get(
            "/api/v1/reembed/obsolete/memories", headers=ctx.headers,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("partition_missing"):
            out.append(Sighting(
                surface=surface, door=door, case=ghost_case, row="partition_missing flag",
                forced_v1_reason="absent partition not reported as partition_missing",
            ))
        for item in payload["items"]:
            fx = ids_to_fx.get(str(item["memory_id"]))
            out.append(Sighting(
                surface=surface, door=door, case=ghost_case,
                row=fx.key if fx else str(item["memory_id"]), kind="preview",
                true_project=fx.project if fx else None,
                true_status=fx.status if fx else None,
                forced_v1_reason="row enumerated while the active partition is absent "
                                 "(the anti-join degraded to TRUE)",
            ))
        out.extend(_account_body(surface, door, ghost_case, response.text, set()))
    finally:
        ctx.pipeline.llm = original_llm
    return out


async def _drive_pipeline_failure_triage(ctx: ProbeContext) -> list[Sighting]:
    surface = "pipeline_failure_triage"
    door = "GET /api/v1/pipeline-failures"
    case = "deployment-wide triage queue (ratified operator-wide)"
    response = await ctx.client.get("/api/v1/pipeline-failures", headers=ctx.headers)
    response.raise_for_status()
    payload = response.json()
    rows = payload["items"] if isinstance(payload, dict) else payload
    out: list[Sighting] = []
    accounted: set[str] = set()
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}
    for row in rows:
        fx = ids_to_fx.get(str(row.get("entity_id")))
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(_mem(
            surface, door, case, fx, kind="preview",
            lp=row.get("entity_project") == fx.project,
            ls=row.get("entity_status") == fx.status,
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    return out


async def _drive_dream_cycle_digest(ctx: ProbeContext) -> list[Sighting]:
    """The dream digest's cycle detail, driven through a real refine action.

    A refine journals the summary it replaced and the one it wrote, which is
    exactly what makes the action undoable — so memory-derived content crosses
    this surface by construction. The actions are produced by the pass's own
    applier rather than by a hand-written payload, so the probe sees the shape
    the producer really writes.

    Operator-wide by ratification: a cycle is one night's consolidation across
    the deployment, so serving both projects is correct and what is asserted is
    that each action carries its own project label. No `memories.status`-shaped
    lifecycle applies to a journal row, so `true_status` stays None — the same
    reading `review_queue_facts` gives a fact row.
    """
    from sqlalchemy import text

    from app.database import async_session_factory
    from app.services import memory_dream as dream

    surface = "dream_cycle_digest"
    door = "GET /api/v1/dream-digest/cycles/{cycle_id}"
    case = "one night's consolidation across the deployment (ratified operator-wide)"

    cycle = str(uuid.uuid4())
    refined: dict[str, MemoryFixture] = {}
    async with async_session_factory() as session:
        for key in ("a_active", "b_active"):
            fx = FIXTURES_BY_KEY.get(key)
            if fx is None:
                continue
            memory_id = ctx.memory_ids.get(key)
            if memory_id is None:
                continue
            row = (
                await session.execute(
                    text(
                        "SELECT content, summary, project FROM memories "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": str(memory_id)},
                )
            ).mappings().first()
            if row is None:
                continue
            applied = await dream.apply_refine(
                session,
                dream.RefineAction(
                    memory=dream.MemoryRow(
                        memory_id=str(memory_id), project=row["project"],
                        created_at=datetime.now(timezone.utc),
                        content=row["content"], summary=row["summary"],
                        metadata={}, tags=(),
                    ),
                    verdict=dream.RefineVerdict(
                        summary=f"{sentinel(fx.key)} refined note", tags=None
                    ),
                ),
                cycle_id=cycle,
                outcome=dream.DreamOutcome(),
            )
            if applied:
                refined[str(memory_id)] = fx
        await session.commit()

    out: list[Sighting] = []
    accounted: set[str] = set()
    if not refined:
        ctx.notes.append(
            "dream_cycle_digest: no refine action landed, so the surface was "
            "not exercised"
        )
        return out

    response = await ctx.client.get(
        f"/api/v1/dream-digest/cycles/{cycle}", headers=ctx.headers
    )
    response.raise_for_status()
    for group in response.json()["objects"]:
        fx = refined.get(str(group.get("object_id")))
        if fx is None:
            continue
        accounted.add(fx.key)
        for action in group["actions"]:
            out.append(Sighting(
                surface=surface, door=door, case=case, row=fx.key,
                kind="content", true_project=fx.project, true_status=None,
                label_project=action.get("project") == fx.project,
            ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    return out


async def _drive_review_queue_facts(ctx: ProbeContext) -> list[Sighting]:
    surface = "review_queue_facts"
    door = "GET /api/v1/review-queue/facts"
    case = "deployment-wide truth-adjudication triage (ratified operator-wide)"
    response = await ctx.client.get("/api/v1/review-queue/facts", headers=ctx.headers)
    response.raise_for_status()
    out: list[Sighting] = []
    accounted: set[str] = set()
    ids_to_fx = {str(fid): FACT_FIXTURES_BY_KEY[key] for key, fid in ctx.fact_ids.items()}
    for row in response.json()["items"]:
        fx = ids_to_fx.get(str(row.get("id")))
        if fx is None:
            continue
        accounted.add(fx.key)
        # No memories.status-shaped lifecycle applies to a fact row, so
        # true_status stays None (classify() reads that as "not breachable
        # on this axis") and only project labelling is asserted — the same
        # reading pipeline_failure_triage gives entity rows with no status
        # concept of their own.
        out.append(Sighting(
            surface=surface, door=door, case=case, row=fx.key, kind="content",
            true_project=fx.project, true_status=None,
            label_project=row.get("project") == fx.project,
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    return out


async def _drive_review_queue_articles(ctx: ProbeContext) -> list[Sighting]:
    surface = "review_queue_articles"
    door = "GET /api/v1/review-queue/articles"
    case = "deployment-wide truth-adjudication triage (ratified operator-wide)"
    response = await ctx.client.get("/api/v1/review-queue/articles", headers=ctx.headers)
    response.raise_for_status()
    out: list[Sighting] = []
    accounted: set[str] = set()
    ids_to_fx = {str(aid): ARTICLE_FIXTURES_BY_KEY[key] for key, aid in ctx.article_ids.items()}
    for row in response.json()["items"]:
        fx = ids_to_fx.get(str(row.get("id")))
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(Sighting(
            surface=surface, door=door, case=case, row=fx.key, kind="preview",
            true_project=fx.project, true_status=None,
            label_project=row.get("project") == fx.project,
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    # The declared crossing is `content_preview`, not `content`. Every fixture
    # runs past the LEFT(content, 200) boundary, so a tail marker on the wire
    # means the surface widened beyond what content_surfaces declares -- and
    # `_account_body` cannot catch it, because the sentinel sits inside the
    # first 200 characters and crosses legitimately either way.
    for fx in ARTICLE_FIXTURES:
        if fx.tail_marker in response.text:
            out.append(Sighting(
                surface=surface, door=door, case=f"{case} [past preview boundary]",
                row=fx.key, true_project=fx.project, true_status=None,
                forced_v1_reason="article content crossed past its declared preview",
            ))
    return out


def _preview_boundary(surface: str, door: str, case: str, body: str) -> list[Sighting]:
    """Long fixtures whose tail reached a surface declaring ``content_preview``.

    The same assertion ``_drive_review_queue_articles`` makes over articles,
    and it is needed for the same reason: ``_account_body`` cannot make it,
    because the sentinel sits inside the first 200 characters and crosses
    legitimately whether or not the preview truncated. Without this, a surface
    that quietly started returning whole ``content`` would keep reporting a
    clean zero.
    """
    return [
        Sighting(
            surface=surface, door=door, case=f"{case} [past preview boundary]",
            row=fx.key, true_project=fx.project, true_status=fx.status,
            forced_v1_reason="memory content crossed past its declared preview",
        )
        for fx in MEMORY_FIXTURES
        if fx.long and fx.tail_marker in body
    ]


async def _drive_knowledge_facts_browsing(ctx: ProbeContext) -> list[Sighting]:
    """Doc 13 §5.1's Facts tab — the vault the deployment holds, browsed.

    ``project`` is a filter the caller applies rather than a scope the door
    imposes, so the two cases assert different things: on the wide read, that
    the foreign-project fact still arrives naming its project; on the filtered
    read, that the project the caller named rode the SQL. No
    ``memories.status``-shaped lifecycle applies to a fact row, so
    ``true_status`` stays None — the reading ``review_queue_facts`` gives the
    same rows, and the verification axis is deliberately not a lifecycle
    (doc 08 §6's never-a-gate rule).
    """
    surface = "knowledge_facts_browsing"
    door = "GET /api/v1/knowledge/facts"
    out: list[Sighting] = []
    ids_to_fx = {str(fid): FACT_FIXTURES_BY_KEY[key] for key, fid in ctx.fact_ids.items()}

    async def one_case(params: str, case: str, req_p: str | None):
        response = await ctx.client.get(
            f"/api/v1/knowledge/facts{params}", headers=ctx.headers,
        )
        response.raise_for_status()
        accounted: set[str] = set()
        for row in response.json()["items"]:
            fx = ids_to_fx.get(str(row.get("id")))
            if fx is None:
                continue
            accounted.add(fx.key)
            out.append(Sighting(
                surface=surface, door=door, case=case, row=fx.key, kind="content",
                true_project=fx.project, true_status=None, requested_project=req_p,
                label_project=row.get("project") == fx.project,
            ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await one_case("", "the whole vault (ratified operator-wide browse)", None)
    await one_case(
        f"?project={OBSERVER}", "project filter applied by the caller", OBSERVER,
    )
    return out


async def _drive_knowledge_fact_detail(ctx: ProbeContext) -> list[Sighting]:
    """One fact by id, with the provenance groups the badge's count audits.

    Id-addressed, so no scope is requested and nothing here can be a V1 on the
    project axis: what the surface owes instead is a label, and the foreign
    fixture is what proves it pays. The provenance groups are the half of this
    response the list door does not have — they name the memories that assert
    the fact, one of them in the other project, which is id-only exposure by
    the rules module's reading and reported as such rather than counted.
    """
    surface = "knowledge_fact_detail"
    door = "GET /api/v1/knowledge/facts/{fact_id}"
    out: list[Sighting] = []
    ids_to_mem = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    for fx in FACT_FIXTURES:
        case = f"fact addressed by id, seeded in {fx.project}"
        response = await ctx.client.get(
            f"/api/v1/knowledge/facts/{ctx.fact_ids[fx.key]}", headers=ctx.headers,
        )
        response.raise_for_status()
        row = response.json()
        out.append(Sighting(
            surface=surface, door=door, case=case, row=fx.key, kind="content",
            true_project=fx.project, true_status=None,
            label_project=row.get("project") == fx.project,
        ))
        for group in row.get("sources", []):
            for source in group.get("sources", []):
                memory = ids_to_mem.get(str(source.get("source_ref")))
                if memory is not None and (
                    memory.project != OBSERVER or memory.status != "active"
                ):
                    out.append(_mem(
                        surface, door, f"{case}: provenance origin", memory, kind="id",
                    ))
        out.extend(_account_body(surface, door, case, response.text, {fx.key}))
    return out


async def _drive_hygiene_queue_duplicates(ctx: ProbeContext) -> list[Sighting]:
    """The candidate-duplicate arm, whose declared crossing is ids alone.

    ``content_surfaces`` says only the two endpoint ids, the score and the
    verdict cross here — no memory content — and that distinction is the whole
    shape of this driver. The endpoint ids are the declared payload and are
    ``I1`` by the rules module (existence across scope, without content:
    exactly what ``entity_browser``'s ``memory_ids`` arrays are), so the
    labelling of a pair is observed but not counted. What *can* fail is the
    other two:

    * a pair outside a project the caller named. ``classify`` short-circuits
      on ``kind='id'`` before it reaches the scope axis, so a scope breach on
      an id-only row is a breach the axis model cannot express — that is what
      ``forced_v1_reason`` is for.
    * any memory sentinel at all in the body. Here the raw-body net is the
      sharpest assertion rather than a backstop, because the declaration
      permits no content crossing whatsoever.
    """
    surface = "hygiene_queue_duplicates"
    door = "GET /api/v1/hygiene-queue/duplicates"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    async def one_case(params: str, case: str, req_p: str | None):
        response = await ctx.client.get(
            f"/api/v1/hygiene-queue/duplicates{params}", headers=ctx.headers,
        )
        response.raise_for_status()
        for row in response.json()["items"]:
            endpoints = [
                ids_to_fx.get(str(row.get("source_memory_id"))),
                ids_to_fx.get(str(row.get("target_memory_id"))),
            ]
            if not any(endpoints):
                continue
            # Named by fixture keys, never by the relation's id: the bench
            # database is rebuilt per run, so an id in a row or case name
            # would make two runs render differently.
            pair = "+".join(fx.key if fx else "unknown" for fx in endpoints)
            if req_p is not None and row.get("project") != req_p:
                out.append(Sighting(
                    surface=surface, door=door, case=case, row=pair, kind="id",
                    true_project=row.get("project"), true_status=None,
                    requested_project=req_p,
                    forced_v1_reason="pair outside the requested project",
                ))
            for fx in endpoints:
                if fx is not None and (fx.project != OBSERVER or fx.status != "active"):
                    out.append(_mem(
                        surface, door, f"{case}: pair {pair}", fx, kind="id",
                    ))
        out.extend(_account_body(surface, door, case, response.text, set()))

    await one_case("", "every open candidate pair (ratified operator-wide)", None)
    await one_case(
        f"?project={OBSERVER}", "project filter applied by the caller", OBSERVER,
    )
    return out


async def _drive_hygiene_queue_memories(ctx: ProbeContext) -> list[Sighting]:
    """The three memory-shaped hygiene arms, each a deployment-wide backlog.

    Unlike a fact or a journal row, every row here *is* a memory, so its
    lifecycle is the ``memories.status`` one and ``true_status`` carries it —
    which is what makes the superseded arm load-bearing: it serves superseded
    rows on a read that requested no status at all, so each one must name the
    state it came from or it is a V2.

    The declared crossing is ``content_preview``, so every fixture the three
    arms return runs past the ``[:200]`` boundary and ``_preview_boundary``
    fails the surface if a tail reaches the wire.
    """
    surface = "hygiene_queue_memories"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    async def one_case(arm: str, params: str, case: str, req_p: str | None):
        door = f"GET /api/v1/hygiene-queue/{arm}"
        response = await ctx.client.get(
            f"/api/v1/hygiene-queue/{arm}{params}", headers=ctx.headers,
        )
        response.raise_for_status()
        accounted: set[str] = set()
        for row in response.json()["items"]:
            fx = ids_to_fx.get(str(row.get("id")))
            if fx is None:
                key = _row_key(row.get("content_preview", ""))
                fx = _all_content_fixtures().get(key or "")
            if fx is None:
                continue
            accounted.add(fx.key)
            out.append(_mem(
                surface, door, case, fx, kind="preview", req_p=req_p,
                lp=row.get("project") == fx.project,
                ls=row.get("status") == fx.status,
            ))
        out.extend(_account_body(surface, door, case, response.text, accounted))
        out.extend(_preview_boundary(surface, door, case, response.text))

    for arm, backlog in (
        ("low-confidence", "low-confidence captures"),
        ("expiring-soon", "rows approaching their TTL"),
        ("superseded", "superseded lineage"),
    ):
        await one_case(
            arm, "", f"{backlog}, deployment-wide (ratified operator-wide)", None,
        )
        await one_case(
            arm, f"?project={OBSERVER}",
            f"{backlog}, project filter applied by the caller", OBSERVER,
        )
    return out


async def _drive_analytics_recents(ctx: ProbeContext) -> list[Sighting]:
    surface = "analytics_recents"
    door = "GET /api/v1/analytics/overview"
    case = "deployment-wide dashboard recents (ratified operator-wide)"
    response = await ctx.client.get("/api/v1/analytics/overview", headers=ctx.headers)
    response.raise_for_status()
    out: list[Sighting] = []
    accounted: set[str] = set()
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}
    for row in response.json()["recent_memories"]:
        fx = ids_to_fx.get(str(row["id"]))
        if fx is None:
            key = _row_key(row.get("content", ""))
            fx = _all_content_fixtures().get(key or "")
        if fx is None:
            continue
        accounted.add(fx.key)
        out.append(_mem(
            surface, door, case, fx,
            lp=row.get("project") == fx.project,
            ls=row.get("status") == fx.status,
        ))
    out.extend(_account_body(surface, door, case, response.text, accounted))
    return out


async def _drive_capture_buffer_triage(ctx: ProbeContext) -> list[Sighting]:
    surface = "capture_buffer_triage"
    out: list[Sighting] = []
    buffer_keys = BUFFER_KEYS

    async def one_case(params: str, case: str, req_p):
        door = "GET /api/v1/memory-buffer"
        response = await ctx.client.get(f"/api/v1/memory-buffer{params}", headers=ctx.headers)
        response.raise_for_status()
        accounted: set[str] = set()
        for row in response.json()["items"]:
            key = _row_key(row.get("content_preview", "") or row.get("content", ""))
            if key not in buffer_keys:
                continue
            accounted.add(key)
            out.append(Sighting(
                surface=surface, door=door, case=case, row=key, kind="preview",
                true_project=buffer_keys[key], true_status=None,
                requested_project=req_p,
                label_project=row.get("project") == buffer_keys[key],
            ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await one_case("", "wide (every project, ratified default)", None)
    await one_case(f"?project={OBSERVER}", "scoped project", OBSERVER)
    return out


async def _drive_event_journal(ctx: ProbeContext) -> list[Sighting]:
    surface = "event_journal"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    def event_sighting(door, case, row, event, req_p, retention=False):
        fx = ids_to_fx.get(str(event.get("object_id")))
        project = event.get("project")
        return Sighting(
            surface=surface, door=door, case=case, row=row,
            kind="preview",
            true_project=fx.project if fx else project,
            true_status=None,
            requested_project=req_p,
            label_project=project is not None and project == (fx.project if fx else project),
            retention=retention,
        )

    async def list_case(params: str, case: str, req_p):
        door = "GET /api/v1/events"
        response = await ctx.client.get(f"/api/v1/events{params}", headers=ctx.headers)
        response.raise_for_status()
        accounted: set[str] = set()
        for event in response.json()["items"]:
            payload = event.get("payload") or {}
            preview = payload.get("content_preview", "")
            key = _row_key(preview) if preview else None
            if key is None:
                # The consolidation stream carries memory-derived content in
                # `before`/`after` rather than in a `content_preview` field —
                # a refine journals the summary it replaced and the one it
                # wrote. Modelled here so it is enumerated against the event's
                # own project label instead of landing in the raw-body net as
                # an unmodelled crossing.
                elsewhere = scan_sentinels(json.dumps(payload, default=str))
                key = sorted(elsewhere)[0] if elsewhere else None
            fx = ids_to_fx.get(str(event.get("object_id")))
            row_name = key or (fx.key if fx else event.get("event_type", "event"))
            if key:
                accounted.add(key)
                out.append(event_sighting(
                    door, case, row_name, event, req_p,
                    retention=key == "a_del",
                ))
            elif fx is not None:
                out.append(event_sighting(door, case, row_name, event, req_p))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await list_case("", "wide (every project, ratified default)", None)
    await list_case(f"?project={OBSERVER}", "scoped project", OBSERVER)

    door = "GET /api/v1/events/timeline"
    case = "timeline of one memory"
    response = await ctx.client.get(
        f"/api/v1/events/timeline?object_type=memory&object_id={ctx.memory_ids['a_active']}",
        headers=ctx.headers,
    )
    response.raise_for_status()
    payload = response.json()
    timeline = payload["items"] if isinstance(payload, dict) else payload
    accounted = set()
    for event in timeline:
        # Every row here is this one memory's own history, so a sentinel in a
        # payload is that memory's content coming back through its journal —
        # a consolidation action's before/after summary, for instance.
        found = scan_sentinels(json.dumps(event.get("payload") or {}, default=str))
        for key in sorted(found):
            accounted.add(key)
            out.append(event_sighting(door, case, key, event, None))
    out.extend(_account_body(surface, door, case, response.text, accounted))

    door = "GET /api/v1/analytics/pipeline-logs"
    response = await ctx.client.get("/api/v1/analytics/pipeline-logs", headers=ctx.headers)
    response.raise_for_status()
    for row in response.json():
        fx = ids_to_fx.get(str(row.get("memory_id")))
        if fx is not None and (fx.project != OBSERVER or fx.status != "active"):
            out.append(_mem(
                surface, door, "pipeline log rows (id + step payload, no labels)",
                fx, kind="id",
            ))
    out.extend(_account_body(surface, door, "pipeline log rows", response.text, set()))
    return out


async def _drive_chat_history_citations(ctx: ProbeContext) -> list[Sighting]:
    surface = "chat_history_citations"
    door = "GET /api/v1/chat/conversations/{conversation_id}"
    out: list[Sighting] = []

    async def one_case(conversation_id: str | None, case: str, retention: bool):
        if conversation_id is None:
            ctx.notes.append(f"chat history: no conversation for case {case!r}")
            return
        response = await ctx.client.get(
            f"/api/v1/chat/conversations/{conversation_id}", headers=ctx.headers,
        )
        response.raise_for_status()
        accounted: set[str] = set()
        for message in response.json()["messages"]:
            context = message.get("context") or {}
            for cited in context.get("memories", []):
                key = _row_key(cited.get("content", ""))
                if key is None:
                    continue
                fx = FIXTURES_BY_KEY[key]
                accounted.add(key)
                out.append(_mem(
                    surface, door, case, fx, kind="preview",
                    lp="project" in cited, ls="status" in cited,
                    retention=retention and key == "a_del",
                ))
        out.extend(_account_body(surface, door, case, response.text, accounted))

    await one_case(ctx.scoped_conversation_id, "citations from the scoped chat", False)
    await one_case(ctx.wide_conversation_id, "citations from the default-context chat", False)
    await one_case(
        ctx.retention_conversation_id,
        "citation whose memory was deleted (escalated retention property)", True,
    )
    return out


async def _drive_entity_browser(ctx: ProbeContext) -> list[Sighting]:
    surface = "entity_browser"
    out: list[Sighting] = []
    ids_to_fx = {str(mid): FIXTURES_BY_KEY[key] for key, mid in ctx.memory_ids.items()}

    def id_sightings(door: str, case: str, entities: list[dict]):
        for entity in entities:
            for mid in entity.get("memory_ids", []):
                fx = ids_to_fx.get(str(mid))
                if fx is not None and (fx.project != OBSERVER or fx.status != "active"):
                    out.append(_mem(
                        surface, door, f"{case}: entity {entity.get('name')!r}",
                        fx, kind="id",
                    ))

    response = await ctx.client.get("/api/v1/graph/full", headers=ctx.headers)
    response.raise_for_status()
    id_sightings("GET /api/v1/graph/full", "global graph", response.json()["entities"])
    out.extend(_account_body(
        surface, "GET /api/v1/graph/full", "global graph", response.text, set(),
    ))

    response = await ctx.client.get("/api/v1/graph/entities?name=redis", headers=ctx.headers)
    response.raise_for_status()
    id_sightings("GET /api/v1/graph/entities", "entity listing", response.json())
    out.extend(_account_body(
        surface, "GET /api/v1/graph/entities", "entity listing", response.text, set(),
    ))

    response = await ctx.client.get(
        f"/api/v1/graph/entities/{ctx.redis_entity_id}/neighbors", headers=ctx.headers,
    )
    response.raise_for_status()
    payload = response.json()
    neighbor_entities = [payload.get("entity") or {}] + list(payload.get("neighbors", []))
    id_sightings(
        "GET /api/v1/graph/entities/{entity_id}/neighbors",
        "neighbours of the cross-project entity", neighbor_entities,
    )
    out.extend(_account_body(
        surface, "GET /api/v1/graph/entities/{entity_id}/neighbors",
        "neighbours of the cross-project entity", response.text, set(),
    ))
    return out


DRIVERS = {
    "dream_cycle_digest": _drive_dream_cycle_digest,
    "memory_search": _drive_memory_search,
    "memory_reason": _drive_memory_reason,
    "chat_retrieval": _drive_chat_retrieval,
    "graph_memory_context": _drive_graph_memory_context,
    "bulk_partition_read": _drive_bulk_partition_read,
    "duplicates_probe": _drive_duplicates_probe,
    "code_search": _drive_code_search,
    "memory_by_id": _drive_memory_by_id,
    "memory_write_echo": _drive_memory_write_echo,
    "reembed_backfill_queue": _drive_reembed_backfill_queue,
    "pipeline_failure_triage": _drive_pipeline_failure_triage,
    "review_queue_facts": _drive_review_queue_facts,
    "review_queue_articles": _drive_review_queue_articles,
    "knowledge_facts_browsing": _drive_knowledge_facts_browsing,
    "knowledge_fact_detail": _drive_knowledge_fact_detail,
    "hygiene_queue_duplicates": _drive_hygiene_queue_duplicates,
    "hygiene_queue_memories": _drive_hygiene_queue_memories,
    "analytics_recents": _drive_analytics_recents,
    "capture_buffer_triage": _drive_capture_buffer_triage,
    "event_journal": _drive_event_journal,
    "chat_history_citations": _drive_chat_history_citations,
    "entity_browser": _drive_entity_browser,
}


async def _sweep_content_free(ctx: ProbeContext) -> list[Sighting]:
    """Honesty check on the registry's content-free claims (Ruling 2).

    Every parameterless GET declared content-free is fetched and its raw body
    sentinel-scanned; three parameterized GETs are fetched against fixture
    ids. A sentinel crossing any of them is a wrongly classified surface —
    a leak the completeness guard would pass forever — and counts as V1.
    Non-GET doors and GETs with no addressable fixture are skipped and the
    skip is recorded, never silent.

    Code sentinels are exempt on the code and repository doors only: the
    registry's claim is about *memory* content, and code content served by
    the code browser's own routes (symbol listings carry source snippets,
    labelled by repo_id) is those doors' job. A code sentinel on any
    non-code door still counts.
    """
    from app.services.content_surfaces import ROUTES_WITHOUT_MEMORY_CONTENT

    surface = "content_free_routes"
    out: list[Sighting] = []
    swept = 0
    skipped: list[str] = []

    substitutions = {
        "GET /api/v1/pipeline-failures/{failure_id}":
            f"/api/v1/pipeline-failures/{ctx.failure_id}",
        "GET /api/v1/repos/{repo_id}": f"/api/v1/repos/{ctx.repo_ids[ALPHA_REPO]}",
        "GET /api/v1/code/wiki/{repo_id}": f"/api/v1/code/wiki/{ctx.repo_ids[ALPHA_REPO]}",
    }

    for door in sorted(ROUTES_WITHOUT_MEMORY_CONTENT):
        method, _, path = door.partition(" ")
        if method != "GET":
            continue
        if "{" in path:
            if door in substitutions:
                path = substitutions[door]
            else:
                skipped.append(door)
                continue
        response = await ctx.client.get(path, headers=ctx.headers)
        swept += 1
        accounted: set[str] = set()
        if door.startswith(("GET /api/v1/code/", "GET /api/v1/repos")):
            accounted = {key for key in scan_sentinels(response.text) if key.startswith("code_")}
        out.extend(_account_body(surface, door, f"content-free sweep ({response.status_code})",
                                 response.text, accounted))
    ctx.notes.append(
        f"content-free sweep: {swept} GET doors fetched; "
        f"skipped (no addressable fixture): {', '.join(skipped) if skipped else 'none'}; "
        "non-GET doors out of sweep scope by design"
    )
    return out


async def run_probe() -> ProbeReport:
    from httpx import ASGITransport, AsyncClient

    await bench_db.reset_bench_db()

    from app.api.auth import create_access_token
    from app.database import async_session_factory, engine as app_engine

    # The reset drops and recreates every object under new OIDs; the app
    # engine may hold pooled connections with prepared statements against the
    # old ones (see bench_db.reset_bench_db's docstring).
    await app_engine.dispose()

    stub = StubOrchestrator(ACTIVE_MODEL)
    old = StubOrchestrator(OLD_MODEL)
    ghost = StubOrchestrator(GHOST_MODEL)

    seeded = await _seed(async_session_factory, stub, old)
    app, pipeline = await _wire_app(stub)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
    report = ProbeReport(observer_project=OBSERVER)

    registry_keys = [s.key for s in _registry_surfaces()]
    missing = set(registry_keys) - set(DRIVERS)
    extra = set(DRIVERS) - set(registry_keys)
    if missing or extra:
        raise RuntimeError(
            "driver table out of step with content_surfaces registry: "
            f"missing drivers for {sorted(missing)}, drivers without surfaces {sorted(extra)}"
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://probe") as client:
        ctx = ProbeContext(
            client=client, headers=headers, app=app, pipeline=pipeline,
            stub=stub, ghost=ghost,
            memory_ids=seeded["memory_ids"], repo_ids=seeded["repo_ids"],
            redis_entity_id=seeded["redis_entity_id"],
            failure_id=seeded["failure_id"],
            fact_ids=seeded["fact_ids"], article_ids=seeded["article_ids"],
            retention_conversation_id=seeded["retention_conversation_id"],
        )
        for key in registry_keys:
            report.add(await DRIVERS[key](ctx))
            report.surfaces_driven.append(key)
        report.add(await _sweep_content_free(ctx))
        report.surfaces_driven.append("content_free_routes")
        report.notes.extend(ctx.notes)

    report.notes.append(
        "model calls: 0 by construction — the orchestrator stub has no HTTP client"
    )
    return report


def _registry_surfaces():
    from app.services.content_surfaces import CONTENT_SURFACES

    return CONTENT_SURFACES
