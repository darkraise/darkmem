"""T2.52 -- the contradiction-shortlist miss-rate runner's measurement core.

Measures the **recall** of doc 08 SS5.3's combined candidate generator --
same-endpoint facts (an index lookup on shared subject/object names) UNION a
`pg_trgm`-on-`fact` top-K shortlist -- against the contradiction-pair gold's
two positive slices (`same-endpoint`, `lexically-disjoint`). Neither arm is
production code yet (`contradiction_scan` is still a `PlaceholderJobRunner`,
T2.11's), so this module *is* the generator under test: it materialises the
**whole live gold** (all 50 pairs, both labels) into ONE bench-database
project and runs the same SQL doc 08 SS5.3 describes.

**Why one shared project, not one per pair.** Every side in the gold file
carries `project: "default"` -- the file was authored to be measured as one
corpus. Isolating each contradiction pair into its own project was tried
first and produces a vacuous 0% miss rate on every slice: with only the
pair's own two rows in scope, `ORDER BY similarity DESC LIMIT top_k` always
returns the lone other row regardless of how low its score is, because
nothing else competes for the K slots. `contradiction_candidate_top_k`
bounding "candidates per fact" is meaningless without other candidates to be
bounded against. Loading the full 50-pair gold into one project gives every
probed fact ~98 real competitors drawn from the gold's own vocabulary (the
`similar-unrelated` and `compatible-same-endpoint` negatives especially,
which exist precisely to look lexically close to something they are not) --
the same shape of crowding the trigram shortlist faces in a real project,
without inventing any fixture data beyond what T2.57 already authored.

**Fact identity is deduplicated by `triple_key`, matching production.**
Two different gold pairs legitimately reuse one side as an anchor against
different counterparts (e.g. `cg-0002.a` and `cg-0012.a` are the identical
triple); `ux_knowledge_triples_open` forbids two open rows sharing one
`triple_key`, and correctly so -- production never has two rows for one
fact either. The loader below inserts each distinct `triple_key` once and
resolves every pair's side to that one row.

**A pair counts as caught if EITHER side's own scan finds the other.**
`contradiction_scan` drains facts needing a check off `sources_changed`/newly-
lifted, and a genuine contradiction's two sides are independently sourced
(disjoint origins, by the gold's own structural precondition) -- so each side
gets its own lift event and its own turn as the scanned "subject" over the
corpus's lifetime. Only one direction has to surface the other for the veto
to eventually fire. This also matches the granularity the brief states: one
hit/miss decision per pair, not per direction -- 12 lexically-disjoint pairs
give a miss rate resolvable only to 1/12, and reporting anything finer would
claim precision the gold cannot support.

**No LLM, no model call.** The candidate generator is cheap deterministic SQL
(doc 08 SS5.3: "no embedding"); this module never calls out and needs no API
key. `contradiction_candidate_top_k` (10) is the same default the placeholder
job's `config_schema` carries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.contradiction_veto import windows_overlap
from app.services.triple_key import compute_triple_key
from app.utils.ids import new_id

from benchlib.contradiction_gold import (
    CONTRADICTION_SLICES,
    GOLD_PATH,
    LABEL_CONTRADICTION,
    load_contradiction_gold,
)

DEFAULT_TOP_K = 10
CORPUS_PROJECT = "t252-missrate-corpus"

# doc 17 SS5.2 / doc 08 SS5.3: "writer justified at miss rate > 20% on the
# disjoint slice" -- stated here, once, so the runner and its tests read one
# value rather than two copies drifting apart.
WRITER_TRIGGER_BAR = 0.20
BAR_SLICE = "lexically-disjoint"


def _parse_bound(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


async def _get_or_insert(
    session: AsyncSession, *, project: str, side: dict, reference_time: datetime,
    cache: dict[str, UUID],
) -> UUID:
    """Insert one materialised fact row, or reuse the one already inserted
    for this `triple_key` -- two gold pairs sharing an anchor side must
    resolve to the SAME row, exactly as production's partial-unique index
    on `(triple_key) WHERE expired_at IS NULL AND invalid_at IS NULL` would
    force for any two callers asserting the identical open triple."""
    triple_key = compute_triple_key(
        project, side["subject_name"], side["rel_type"], side["object_name"],
    )
    cached = cache.get(triple_key)
    if cached is not None:
        return cached

    fact_id = new_id()
    await session.execute(
        text("""
            INSERT INTO knowledge_triples (
                id, subject_name, object_name, rel_type, valid_at, invalid_at,
                reference_time, fact, project, triple_key
            ) VALUES (
                CAST(:id AS uuid), CAST(:subject_name AS text),
                CAST(:object_name AS text), CAST(:rel_type AS text),
                CAST(:valid_at AS timestamptz), CAST(:invalid_at AS timestamptz),
                CAST(:reference_time AS timestamptz), CAST(:fact AS text),
                CAST(:project AS text), CAST(:triple_key AS text)
            )
        """),
        {
            "id": str(fact_id),
            "subject_name": side["subject_name"],
            "object_name": side["object_name"],
            "rel_type": side["rel_type"],
            "valid_at": _parse_bound(side["valid_at"]),
            "invalid_at": _parse_bound(side["invalid_at"]),
            "reference_time": reference_time,
            "fact": side["fact"],
            "project": project,
            "triple_key": triple_key,
        },
    )
    cache[triple_key] = fact_id
    return fact_id


_SAME_ENDPOINT_SQL = """
    SELECT id, valid_at, invalid_at
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND id <> CAST(:fact_id AS uuid)
      AND (
        subject_name = CAST(:subject_name AS text)
        OR object_name = CAST(:object_name AS text)
        OR subject_name = CAST(:object_name AS text)
        OR object_name = CAST(:subject_name AS text)
      )
"""

# similarity() rather than the `%` operator: `%` reads its threshold off
# pg_trgm.similarity_threshold (session GUC, default 0.3), a hidden knob this
# query must not depend on silently. ORDER BY similarity DESC caps the
# shortlist at contradiction_candidate_top_k, doc 08 SS5.3's per-fact bound.
_TRIGRAM_SQL = """
    SELECT id, valid_at, invalid_at, similarity(fact, CAST(:fact_text AS text)) AS sim
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND id <> CAST(:fact_id AS uuid)
    ORDER BY sim DESC
    LIMIT CAST(:top_k AS integer)
"""


async def same_endpoint_candidates(
    session: AsyncSession, *, project: str, fact_id: UUID, subject_name: str, object_name: str,
) -> dict[str, dict]:
    rows = await session.execute(
        text(_SAME_ENDPOINT_SQL),
        {
            "project": project, "fact_id": str(fact_id),
            "subject_name": subject_name, "object_name": object_name,
        },
    )
    return {str(r["id"]): dict(r) for r in rows.mappings().all()}


async def trigram_candidates(
    session: AsyncSession, *, project: str, fact_id: UUID, fact_text: str, top_k: int,
) -> dict[str, dict]:
    rows = await session.execute(
        text(_TRIGRAM_SQL),
        {"project": project, "fact_id": str(fact_id), "fact_text": fact_text, "top_k": top_k},
    )
    return {str(r["id"]): dict(r) for r in rows.mappings().all()}


async def combined_candidates(
    session: AsyncSession, *, project: str, fact_id: UUID,
    subject_name: str, object_name: str, fact_text: str, top_k: int = DEFAULT_TOP_K,
) -> dict[str, dict]:
    """same-endpoint UNION pg_trgm top-K, doc 08 SS5.3's whole generator.

    Keyed by candidate id so the union dedups naturally; a row present in
    both arms keeps whichever dict is written last (both carry the same
    valid_at/invalid_at, so this never affects the overlap filter below).
    """
    same_endpoint = await same_endpoint_candidates(
        session, project=project, fact_id=fact_id,
        subject_name=subject_name, object_name=object_name,
    )
    trigram = await trigram_candidates(
        session, project=project, fact_id=fact_id, fact_text=fact_text, top_k=top_k,
    )
    return {**same_endpoint, **trigram}


def _overlapping(
    candidates: dict[str, dict], subject_valid_at, subject_invalid_at,
) -> set[str]:
    return {
        cid for cid, row in candidates.items()
        if windows_overlap(
            subject_valid_at, subject_invalid_at, row["valid_at"], row["invalid_at"],
        )
    }


@dataclass(frozen=True)
class PairProbe:
    pair_id: str
    slice_tag: str
    hit: bool
    caught_via: str  # "a", "b", "both", or "miss"


@dataclass
class SliceResult:
    slice_tag: str
    total: int = 0
    misses: list[str] = field(default_factory=list)

    @property
    def miss_count(self) -> int:
        return len(self.misses)

    @property
    def miss_rate(self) -> float:
        return self.miss_count / self.total if self.total else 0.0

    @property
    def granularity(self) -> float:
        return 1 / self.total if self.total else 0.0


async def probe_pair(
    session: AsyncSession, pair: dict, ids: dict[str, UUID], *,
    project: str = CORPUS_PROJECT, top_k: int = DEFAULT_TOP_K,
) -> PairProbe:
    sides = {"a": pair["a"], "b": pair["b"]}
    hit_sides = []
    for side_key, other_key in (("a", "b"), ("b", "a")):
        side = sides[side_key]
        counterpart_id = str(ids[other_key])
        if ids[side_key] == ids[other_key]:
            # A pair whose two sides collapsed onto one materialised row
            # (identical triple_key) cannot be adjudicated by a generator
            # that excludes `id <> :fact_id` -- but the gold loader already
            # refuses same-triple_key pairs (contradiction_gold.py), so this
            # never fires against the live gold; it is a defensive guard
            # against a future gold file relaxing that rule silently.
            continue
        candidates = await combined_candidates(
            session, project=project, fact_id=ids[side_key],
            subject_name=side["subject_name"], object_name=side["object_name"],
            fact_text=side["fact"], top_k=top_k,
        )
        surviving = _overlapping(
            candidates, _parse_bound(side["valid_at"]), _parse_bound(side["invalid_at"]),
        )
        if counterpart_id in surviving:
            hit_sides.append(side_key)

    if not hit_sides:
        caught_via = "miss"
    elif len(hit_sides) == 2:
        caught_via = "both"
    else:
        caught_via = hit_sides[0]

    return PairProbe(
        pair_id=pair["id"], slice_tag=pair["slice_tags"][0],
        hit=bool(hit_sides), caught_via=caught_via,
    )


@dataclass
class MissRateReport:
    gold_path: Path
    top_k: int
    corpus_size: int
    slices: dict[str, SliceResult]
    probes: list[PairProbe]

    def slice_result(self, tag: str) -> SliceResult:
        return self.slices[tag]

    def bar_breached(self, bar: float = WRITER_TRIGGER_BAR, slice_tag: str = BAR_SLICE) -> bool:
        return self.slice_result(slice_tag).miss_rate > bar

    def render(self, bar: float = WRITER_TRIGGER_BAR, slice_tag: str = BAR_SLICE) -> str:
        lines = [
            "# T2.52 -- contradiction candidate-generator miss rate",
            "",
            f"Gold: `{self.gold_path}` -- combined generator "
            f"(same-endpoint UNION pg_trgm top-{self.top_k}), measured against "
            f"the whole live gold materialised as one {self.corpus_size}-fact "
            "project (doc 08 SS5.3's real competitive shape for the trigram "
            "shortlist).",
            "",
            f"**Bar (stated beforehand): writer justified at miss rate > "
            f"{bar:.0%} on the `{slice_tag}` slice** (doc 08 SS5.3 / doc 17 SS5.2).",
            "",
            "| Slice | Pairs | Misses | Miss rate | Granularity |",
            "|---|---|---|---|---|",
        ]
        for tag in sorted(self.slices):
            r = self.slices[tag]
            lines.append(
                f"| {tag} | {r.total} | {r.miss_count} | {r.miss_rate:.1%} | "
                f"1/{r.total} ({r.granularity:.1%}) |"
            )
        lines.append("")
        bar_result = self.slice_result(slice_tag)
        breached = self.bar_breached(bar, slice_tag)
        lines.append(
            f"**`{slice_tag}` measured miss rate: {bar_result.miss_rate:.1%} "
            f"({bar_result.miss_count}/{bar_result.total}), granularity "
            f"1/{bar_result.total} ~= {bar_result.granularity:.1%}.**"
        )
        lines.append(
            f"Verdict: {'JUSTIFIES' if breached else 'does NOT justify'} "
            f"T2.33 (the `triple_embeddings` writer) -- "
            f"{'above' if breached else 'at or below'} the {bar:.0%} bar."
        )
        if bar_result.misses:
            lines.append("")
            lines.append(f"Missed pairs on `{slice_tag}`: {', '.join(bar_result.misses)}")
        return "\n".join(lines) + "\n"


async def run_missrate(
    session: AsyncSession, *, gold_path=None, top_k: int = DEFAULT_TOP_K,
    project: str = CORPUS_PROJECT,
) -> MissRateReport:
    # Bench-only: pg_trgm is not part of the baseline schema (0001_baseline.py
    # ships only the `vector` extension), and this runner never touches
    # production. The real writer, when T2.33 lands, is the baseline owner's
    # call on whether to move this into the migration.
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    kwargs = {} if gold_path is None else {"path": gold_path}
    gold = load_contradiction_gold(**kwargs)
    live_pairs = [p for p in gold["pairs"] if not p.get("retired")]

    reference_time = datetime.now(timezone.utc)
    cache: dict[str, UUID] = {}
    pair_ids: dict[str, dict[str, UUID]] = {}
    for pair in live_pairs:
        pair_ids[pair["id"]] = {
            side_key: await _get_or_insert(
                session, project=project, side=pair[side_key],
                reference_time=reference_time, cache=cache,
            )
            for side_key in ("a", "b")
        }

    slices = {tag: SliceResult(slice_tag=tag) for tag in CONTRADICTION_SLICES}
    probes: list[PairProbe] = []
    for pair in live_pairs:
        if pair["label"] != LABEL_CONTRADICTION:
            continue
        probe = await probe_pair(
            session, pair, pair_ids[pair["id"]], project=project, top_k=top_k,
        )
        probes.append(probe)
        result = slices[probe.slice_tag]
        result.total += 1
        if not probe.hit:
            result.misses.append(probe.pair_id)

    gold_path_resolved = Path(gold_path) if gold_path is not None else GOLD_PATH
    return MissRateReport(
        gold_path=gold_path_resolved, top_k=top_k, corpus_size=len(cache),
        slices=slices, probes=probes,
    )
