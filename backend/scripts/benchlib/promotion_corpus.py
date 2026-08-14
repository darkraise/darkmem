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

**T2.129 — the census grew and the audit's machine arm is armed.** The
2026-08-13 evidence run was the first powered G-C measurement and did not
clear, because the false-promotion audit's zero was *inoperability* rather
than measured precision: not one of the numerator's producers could fire on
this corpus. Both halves of the repair live here, and neither works alone.

*The census.* The audit's bar is ``rate < 0.01``, strict, and one genuine
false promotion in a window of N corroborations is ``1/N`` — over 1 % for
every N below 100. Across the whole decidable band of 20–99 a corpus is
therefore either vacuous or failing, so the corpus, not the bar, is what had
to move. The claim counts grew to carry more than 100 corroborations on the
**unsimulated** pass too, where the ``time_gap`` bucket empties; the 2026-08-13
run cleared its decidability floor there by exactly one corroboration.
Nothing about the corroboration structure was relaxed to reach the count: the
growth is more claims of the shapes already designed, and the two designed
refusals are untouched.

*The arm.* ``inverse_replacement`` needs a REPLACES-family edge asserted in
both directions between one pair of names, which no earlier version of this
corpus contained. The ``armed_subject`` / ``armed_counterpart`` groups supply
one, in a project nothing else uses, and they arm the **deterministic**
detector — so the audit's machine arm takes no dependency on G-D's judge
qualification.

**Which is why the corpus has waves, and this is the finding that shaped
them.** ``verification_ladder.decide`` checks the veto *before* the count and
before the already-corroborated hold, and the demotion hysteresis is
interposed only on the ``demote`` outcome — so a later-arriving counterpart
flips an already-corroborated fact to ``disputed`` immediately, with no grace.
That is what the audit's numerator counts, and it is only reachable in that
order: a counterpart present from the first recompute sends the fact
``candidate -> disputed`` with no corroboration in between, leaving the
numerator at zero with the arm fully armed — the same vacuum one layer down.
So wave 1 is the corpus, recomputed to convergence; wave 2 is the rollback
that contradicts it, plus one independent re-assertion of the original claim,
which is what puts the already-corroborated fact back in front of the
recompute's fast arm (that arm recomputes exactly the facts named by a
``sources_changed`` payload, and the counterpart's own event names only the
counterpart). The re-assertion's origin is deliberately not the rollback's:
the veto's echo test asks whether the *counterpart* brings a witness the
subject does not already have.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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

from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
)
from app.services import fact_lift
from app.services.code_deriver import assert_repo_graph
from app.services.config import get_llm_config
from app.services.fact_provenance import MEMORY_SOURCE_KIND
from app.services.verification_recompute import run_recompute

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
MAX_RECOMPUTE_TICKS = 20

# The recompute's fast arm refuses events younger than its commit-skew margin
# (`verification_recompute._COMMIT_SKEW_MARGIN`, 5s), so a tick fired straight
# after a lift drains nothing. One second over it, the same wait the runner
# makes before its own ticks.
RECOMPUTE_SKEW_WAIT_SECONDS = 6

ARMING_SUBJECT_GROUP = "armed_subject"
ARMING_COUNTERPART_GROUP = "armed_counterpart"
ARMING_GROUPS = frozenset({ARMING_SUBJECT_GROUP, ARMING_COUNTERPART_GROUP})

# The groups the corpus declares, and what each is for. Validated so a typo in
# a group label cannot silently produce a corpus whose design nobody can read
# back off the data.
CORPUS_GROUPS = frozenset({
    "diversity", "time_gap", "none", "echo", "under_sourced",
    ARMING_SUBJECT_GROUP, ARMING_COUNTERPART_GROUP,
})

# The groups the design expects to stay at `candidate`. The first two are the
# designed refusals, named so the runner can report them as an outcome rather
# than leaving a reader to notice their absence from the promoted set. The
# counterpart is here for a different reason and is not a control: it carries
# one origin against N=3, so it can never corroborate, and counting it as a
# promotable claim would overstate what the corpus can put in the audit's
# denominator.
NON_PROMOTING_GROUPS = frozenset({
    "echo", "under_sourced", ARMING_COUNTERPART_GROUP,
})

# Which ingestion pass an entry belongs to. Wave 2 exists so a fact can be
# corroborated *and then* disputed -- see the module docstring; a corpus with
# one wave can arm the detector and still leave the audit's numerator at zero.
CORPUS_WAVES = (1, 2)
DEFAULT_WAVE = 1


# The corroboration parameters the design is written against. Imported from
# the repository that owns them rather than re-typed: a corpus validated
# against a stale copy of N or of the gap would claim a structure the ladder
# no longer reads, and it would claim it silently.
_GAP = timedelta(days=CORROBORATION_TIME_GAP_DAYS)

# What each group's claims must look like for the group to mean what its name
# says. `(min_origins, max_origins, gap)` where `gap` is 'ge' (the time gate
# must fire), 'lt' (it must not) or None (not constrained).
_DESIGN: dict[str, tuple[int, int | None, str | None]] = {
    # One memory origin is enough: the indexed repository supplies the second
    # origin AND the second kind, which is the diversity gate at N=2.
    "diversity": (1, None, None),
    # Two sessions, far enough apart that the time gate fires at N=2.
    "time_gap": (CORROBORATION_N_DIVERSE, None, "ge"),
    # Three sessions inside one week: no gate fires, so the default N applies
    # and is met exactly.
    "none": (CORROBORATION_N_DEFAULT, None, "lt"),
    # One session saying the same thing repeatedly. Must stay one origin.
    "echo": (1, 1, None),
    # Two same-kind sessions inside one week: k=2 against N=3.
    "under_sourced": (CORROBORATION_N_DIVERSE, CORROBORATION_N_DIVERSE, "lt"),
    # The claim the veto is armed against. Its wave-1 sessions alone must meet
    # the default N -- `validate_arming_design` is what checks that, because
    # this table cannot see waves -- and the wave-2 re-assertion then adds an
    # origin, which is why no gap rule applies here: whether that fourth origin
    # lands inside or outside the seven days changes which gate *would* have
    # fired, and the fact is already corroborated by then either way.
    ARMING_SUBJECT_GROUP: (CORROBORATION_N_DEFAULT, None, None),
    # One session records the rollback. One origin is the design, not a
    # shortfall: the counterpart's job is to contradict, and a counterpart that
    # corroborated would put a second fact in the audit's numerator.
    ARMING_COUNTERPART_GROUP: (1, 1, None),
}


def memory_id_for_key(key: str) -> str:
    return str(uuid.uuid5(MEMORY_ID_NAMESPACE, key))


def claim_key(key: str) -> str:
    """Which claim an entry asserts, read off its ``key``.

    The corpus's corroboration structure is a property of *claims*, not of
    entries, so the design check needs to know which entries are re-assertions
    of one claim. The rule is the key's own convention: a trailing single-
    character segment is the variant marker (``at-k8s-a`` / ``at-k8s-b``,
    ``ld-postgres-1``..``-3``), everything else is the claim. A key with no
    variant marker is its own claim.

    Deliberately derived rather than stored beside each entry: a declared
    claim label can disagree with the content, and a wrong label would make
    the design check validate a structure the corpus does not have.

    **The convention is guard-by-convention, so it is guarded.** On its own
    this rule reads a key like ``pg-c`` as a variant of claim ``pg`` —
    a grouping nobody wrote down, which the design check would then happily
    validate. :func:`validate_claim_key_convention` runs in the loader and
    refuses that shape, so the only single-character tails the corpus can
    contain are ones with a sibling.
    """
    head, _, tail = key.rpartition("-")
    return head if head and len(tail) == 1 else key


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

        wave = entry.get("wave", DEFAULT_WAVE)
        if wave not in CORPUS_WAVES:
            raise ValueError(
                f"entry {key!r}: wave {wave!r} is not one of {list(CORPUS_WAVES)}"
            )
        if wave != DEFAULT_WAVE and group not in ARMING_GROUPS:
            raise ValueError(
                f"entry {key!r} in group {group!r} is in wave {wave}. Only the "
                f"arming groups {sorted(ARMING_GROUPS)} have a second wave; a "
                f"measured claim held back to wave 2 is recomputed once fewer "
                f"than the corpus it is measured beside"
            )
        entry["wave"] = wave

        entry["memory_id"] = memory_id_for_key(key)
    validate_claim_key_convention(entries)
    validate_corroboration_design(entries)
    validate_arming_design(entries)
    return entries


def entries_for_wave(entries: list[dict], wave: int) -> list[dict]:
    return [entry for entry in entries if entry.get("wave", DEFAULT_WAVE) == wave]


def validate_claim_key_convention(entries: list[dict]) -> None:
    """Refuse a variant marker that groups nothing.

    :func:`claim_key` reads any trailing single-character segment as a
    variant marker, so a future ``pg-c`` would be filed under a claim ``pg``
    that no entry declares and no reader expects — and the design check would
    validate that invented grouping rather than refusing it. Variants exist in
    sets by construction (``-a``/``-b``, ``-1``..``-3``), so a marker with no
    sibling sharing its head is a key that means something else. The fix is to
    rename it (``pg-cx``), which is what this message says.
    """
    by_head: dict[str, list[str]] = {}
    for entry in entries:
        key = entry["key"]
        head, _, tail = key.rpartition("-")
        if head and len(tail) == 1:
            by_head.setdefault(head, []).append(key)
    for head, keys in sorted(by_head.items()):
        if len(keys) == 1:
            raise ValueError(
                f"key {keys[0]!r} ends in a single-character segment, which "
                f"claim_key reads as a variant marker, but no other entry "
                f"shares the claim {head!r}. A variant with no sibling is a "
                f"key whose last segment is not a variant marker at all; give "
                f"it a final segment of two characters or more"
            )


def validate_corroboration_design(entries: list[dict]) -> None:
    """Assert that each claim really has the corroboration shape its group claims.

    The failure this exists to prevent is not a crash — it is a corpus that
    still loads, still runs and still produces numbers, while asserting a
    structure it no longer has. Two concrete edits do it: giving each of an
    echo's saves its own ``origin_key`` turns the designed refusal into a
    promotion, and moving one half of a ``time_gap`` pair to within a week of
    the other silently reclassifies its facts into the ``none`` bucket at an N
    they cannot meet. Both leave the gate reading a corpus whose design
    document is wrong, which is worse than a corpus that fails to load.
    """
    by_claim: dict[str, list[dict]] = {}
    for entry in entries:
        by_claim.setdefault(claim_key(entry["key"]), []).append(entry)

    for claim, group_entries in sorted(by_claim.items()):
        groups = {entry["group"] for entry in group_entries}
        if len(groups) > 1:
            raise ValueError(
                f"claim {claim!r} spans several groups {sorted(groups)}; a claim "
                f"belongs to exactly one design group"
            )
        group = groups.pop()
        min_origins, max_origins, gap_rule = _DESIGN[group]

        first_seen: dict[str, datetime] = {}
        for entry in group_entries:
            captured = datetime.fromisoformat(entry["created_at"])
            origin = entry["origin_key"].strip().lower()
            if origin not in first_seen or captured < first_seen[origin]:
                first_seen[origin] = captured
        origins = len(first_seen)

        if origins < min_origins:
            raise ValueError(
                f"claim {claim!r} in group {group!r} is asserted by {origins} "
                f"distinct origin(s); the design needs at least {min_origins}"
            )
        if max_origins is not None and origins > max_origins:
            raise ValueError(
                f"claim {claim!r} in group {group!r} is asserted by {origins} "
                f"distinct origin(s); the design allows at most {max_origins}. "
                f"Adding an origin here changes what the group demonstrates"
            )

        if gap_rule is None:
            continue
        times = sorted(first_seen.values())
        span = times[-1] - times[0]
        if gap_rule == "ge" and span < _GAP:
            raise ValueError(
                f"claim {claim!r} in group {group!r} spans {span} across its "
                f"origins, under the {_GAP} the time-gap gate needs; its facts "
                f"would fall into the 'none' bucket instead"
            )
        if gap_rule == "lt" and span >= _GAP:
            raise ValueError(
                f"claim {claim!r} in group {group!r} spans {span} across its "
                f"origins, at or over {_GAP}, so the time-gap gate fires and the "
                f"claim leaves the bucket its group exists to populate"
            )


def _declared_replacement(entry: dict) -> tuple[str, str]:
    declared = entry.get("replaces")
    if (
        not isinstance(declared, list)
        or len(declared) != 2
        or not all(isinstance(name, str) and name.strip() for name in declared)
    ):
        raise ValueError(
            f"arming entry {entry['key']!r} must declare "
            f"'replaces': [subject, object] -- the two names whose REPLACES "
            f"edge the veto is armed on. Left to the extractor alone, a "
            f"reworded content silently arms nothing and the run reports a "
            f"clean audit"
        )
    subject, obj = (name.strip().lower() for name in declared)
    if subject == obj:
        raise ValueError(
            f"arming entry {entry['key']!r} declares {subject!r} replacing "
            f"itself; `detect_open_contradiction` skips a self-loop, whose "
            f"inverse is itself"
        )
    text_ = entry["content"].lower()
    for name in (subject, obj):
        if not re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text_):
            raise ValueError(
                f"arming entry {entry['key']!r} declares the pair "
                f"({subject!r}, {obj!r}) but its content never names {name!r}, "
                f"so the extractor has nothing to build the edge from"
            )
    return subject, obj


def validate_arming_design(entries: list[dict]) -> None:
    """Assert the corpus can actually arm ``inverse_replacement``, and in order.

    Every clause here is a way the arming silently becomes vacuous while the
    corpus still loads, still runs and still prints an audit rate of 0.0000 —
    which is the exact reading the 2026-08-13 run was unable to distinguish
    from precision, and the reason this task exists.

    - **Wave order.** The subject's wave-1 sessions alone must meet the default
      N, because the audit counts a fact corroborated and *then* disputed. Move
      the counterpart into wave 1 and the veto fires on the first recompute:
      ``candidate -> disputed``, no corroboration in between, numerator 0.
    - **The re-assertion.** A wave-2 entry on the subject claim, from an origin
      of its own, is what re-enqueues the already-corroborated fact — the fast
      arm recomputes exactly the facts a ``sources_changed`` payload names, and
      the counterpart's event names only the counterpart. Without it the
      dispute waits on the slow arm's cadence, which a run cannot depend on.
    - **The witness.** The counterpart's origin may appear nowhere in the
      subject claim. The veto's echo test asks whether the *counterpart* brings
      a witness the subject lacks; share the origin and the finding is an echo
      and the veto correctly declines.
    - **The project.** Nothing else may live in the arming project, so the
      REPLACES memories' supersession and the detector's candidate scan cannot
      reach a measured claim.
    """
    by_group: dict[str, list[dict]] = {}
    for entry in entries:
        if entry["group"] in ARMING_GROUPS:
            by_group.setdefault(entry["group"], []).append(entry)

    for group in sorted(ARMING_GROUPS):
        members = by_group.get(group, [])
        claims = {claim_key(entry["key"]) for entry in members}
        if len(claims) != 1:
            raise ValueError(
                f"group {group!r} holds {len(claims)} claim(s); the arming "
                f"design is exactly one pair, and a second pair would put a "
                f"second fact in the false-promotion audit's numerator"
            )

    subject_entries = by_group[ARMING_SUBJECT_GROUP]
    counterpart_entries = by_group[ARMING_COUNTERPART_GROUP]

    pairs = {_declared_replacement(entry) for entry in subject_entries}
    if len(pairs) != 1:
        raise ValueError(
            f"the arming subject claim declares several replacement pairs "
            f"{sorted(pairs)}; its entries must all assert one edge"
        )
    forward = pairs.pop()
    reverse = {_declared_replacement(entry) for entry in counterpart_entries}
    if reverse != {(forward[1], forward[0])}:
        raise ValueError(
            f"the arming counterpart declares {sorted(reverse)}, which is not "
            f"the inverse of the subject's {forward}. `inverse_replacement` "
            f"matches a REPLACES-family edge asserted in both directions "
            f"between the same two names and nothing else"
        )

    projects = {entry["project"] for entry in subject_entries + counterpart_entries}
    if len(projects) != 1:
        raise ValueError(
            f"the arming pair spans projects {sorted(projects)}; the detector "
            f"scopes its candidate scan by project, so a split pair contradicts "
            f"nothing"
        )
    arming_project = projects.pop()
    intruders = sorted({
        entry["key"] for entry in entries
        if entry["project"] == arming_project and entry["group"] not in ARMING_GROUPS
    })
    if intruders:
        raise ValueError(
            f"entries {intruders} share the arming project {arming_project!r}. "
            f"A REPLACES memory supersedes same-project memories and the "
            f"detector scans same-project facts, so a measured claim parked "
            f"here is measured under a side effect"
        )

    first_wave = entries_for_wave(subject_entries, 1)
    later_wave = entries_for_wave(subject_entries, 2)
    first_origins = {entry["origin_key"].strip().lower() for entry in first_wave}
    if len(first_origins) < CORROBORATION_N_DEFAULT:
        raise ValueError(
            f"the arming subject claim is asserted by {len(first_origins)} "
            f"origin(s) in wave 1; it needs {CORROBORATION_N_DEFAULT} to be "
            f"corroborated before the counterpart arrives, and a fact disputed "
            f"straight out of `candidate` never enters the audit's numerator"
        )
    captured = sorted(
        datetime.fromisoformat(entry["created_at"]) for entry in first_wave
    )
    if captured[-1] - captured[0] >= _GAP:
        raise ValueError(
            f"the arming subject claim's wave-1 sessions span "
            f"{captured[-1] - captured[0]}, at or over {_GAP}. The time-gap "
            f"gate would then carry it, and the gate is unreachable on the "
            f"unsimulated pass -- so the fact would not be corroborated there "
            f"and the dispute would land on one pass only"
        )
    if not later_wave:
        raise ValueError(
            "the arming subject claim has no wave-2 entry, so nothing "
            "re-enqueues the corroborated fact and the dispute waits on the "
            "slow arm's cadence rather than on the corpus"
        )
    later_origins = {entry["origin_key"].strip().lower() for entry in later_wave}
    if later_origins & first_origins:
        raise ValueError(
            f"the arming subject claim's wave-2 re-assertion reuses origin(s) "
            f"{sorted(later_origins & first_origins)}; an independent session "
            f"re-confirming the claim is what the corpus says it is"
        )

    if entries_for_wave(counterpart_entries, 1):
        raise ValueError(
            "the arming counterpart has a wave-1 entry, so the veto fires on "
            "the first recompute and the subject is disputed out of "
            "`candidate` with no corroboration to count against"
        )
    witness = {entry["origin_key"].strip().lower() for entry in counterpart_entries}
    subject_origins = first_origins | later_origins
    if witness & subject_origins:
        raise ValueError(
            f"the arming counterpart's origin(s) {sorted(witness & subject_origins)} "
            f"also assert the subject claim. The veto's echo test asks whether "
            f"the counterpart brings a witness the subject does not have, so a "
            f"shared origin is an echo and no contradiction is found"
        )


def validate_diversity_group_against_fixture(
    entries: list[dict], fixture: dict
) -> dict[str, str]:
    """Tie each ``diversity`` claim to the repository import that seconds it.

    The diversity group's design spans two committed files, and the dependency
    between them was unguarded: a ``diversity`` claim naming a package the
    fixture does not import still loads, still validates and still runs, and
    then quietly yields a one-origin ``candidate`` — the bucket shrinks with
    no error and no symptom, which is the same genus of silent-wrongness
    :func:`validate_corroboration_design` exists to refuse one file down.
    ``_DESIGN`` cannot catch it: it grants ``diversity`` a single memory origin
    precisely because the second origin is supposed to come from the parse.

    Refuses three shapes and returns the claim → dependency map it proved:

    - a claim naming none of the fixture's dependencies (the import was never
      added, or was renamed out from under the claim);
    - a claim naming several (the grouping is ambiguous, so which fact the
      claim lands on is not readable off the corpus);
    - two claims naming the same dependency (they converge on one fact, so the
      bucket carries fewer claims than the corpus appears to declare).

    The other direction is deliberately allowed: an import no memory notes is
    a code-only fact born on the rung, counted by the completeness probe's
    carve-out rather than lost.
    """
    from app.services.code_deriver import dependency_name

    dependencies: set[str] = set()
    for edge in fixture.get("imports", ()):
        name = dependency_name(edge["target_key"])
        if name is None:
            raise ValueError(
                f"repo fixture import {edge['target_key']!r} is not a "
                f"dependency the deriver will assert, so it seconds nothing"
            )
        dependencies.add(name.lower())

    by_claim: dict[str, list[dict]] = {}
    for entry in entries:
        if entry["group"] != "diversity":
            continue
        by_claim.setdefault(claim_key(entry["key"]), []).append(entry)

    resolved: dict[str, str] = {}
    for claim, group_entries in sorted(by_claim.items()):
        text_ = " ".join(entry["content"] for entry in group_entries).lower()
        named = sorted(
            dep for dep in dependencies
            if re.search(rf"(?<![\w-]){re.escape(dep)}(?![\w-])", text_)
        )
        if not named:
            raise ValueError(
                f"diversity claim {claim!r} names none of the repository's "
                f"imported dependencies {sorted(dependencies)}; without the "
                f"import there is no second origin, so the claim silently "
                f"holds at one origin and leaves the diversity bucket"
            )
        if len(named) > 1:
            raise ValueError(
                f"diversity claim {claim!r} names several imported "
                f"dependencies {named}; which fact it corroborates is then "
                f"not readable off the corpus"
            )
        dependency = named[0]
        if dependency in resolved.values():
            twin = next(k for k, v in resolved.items() if v == dependency)
            raise ValueError(
                f"diversity claims {twin!r} and {claim!r} both name "
                f"{dependency!r}; they converge on one fact, so the bucket "
                f"holds fewer claims than the corpus appears to declare"
            )
        resolved[claim] = dependency
    return resolved


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

# Every dispute the ladder journaled, with the one thing that decides whether
# it reaches the false-promotion audit's numerator: whether the same fact was
# journaled `corroborated` first. A dispute out of `candidate` is a real
# dispute and still leaves the audit reading zero, so the two are reported
# apart rather than as one "disputes" count.
#
# The counterpart triple is joined off the payload rather than replayed from
# it, on `detect_scanned_contradiction`'s own reasoning: a journal row is
# append-only and can outlive the rows it describes.
_ARMED_DISPUTES = text("""
    WITH disputes AS (
        SELECT DISTINCT ON (e.object_id)
               e.object_id, e.created_at, e.id, e.payload
        FROM events e
        WHERE e.event_type = 'verified'
          AND e.object_type = 'fact'
          AND e.payload->>'outcome' = 'dispute'
        ORDER BY e.object_id, e.created_at, e.id
    )
    SELECT kt.project,
           kt.subject_name, kt.rel_type, kt.object_name,
           kt.verification_status,
           d.payload->'contradiction'->>'rule'           AS rule,
           d.payload->'contradiction'->>'witness_origin' AS witness_origin,
           ck.subject_name AS counterpart_subject,
           ck.rel_type     AS counterpart_rel_type,
           ck.object_name  AS counterpart_object,
           EXISTS (
               SELECT 1 FROM events p
               WHERE p.event_type = 'verified'
                 AND p.object_type = 'fact'
                 AND p.object_id = d.object_id
                 AND p.payload->'after'->>'verification_status' = 'corroborated'
                 AND (p.created_at, p.id) < (d.created_at, d.id)
           ) AS corroborated_first
    FROM disputes d
    JOIN knowledge_triples kt ON kt.id = d.object_id
    LEFT JOIN knowledge_triples ck
           ON CAST(ck.id AS text) = d.payload->'contradiction'->>'counterpart_id'
    ORDER BY kt.project, kt.subject_name, kt.object_name
""")


@dataclass(frozen=True)
class ReadBack:
    promotions_by_gate: tuple[dict, ...]
    census: tuple[dict, ...]
    controls: tuple[dict, ...]
    disputes: tuple[dict, ...] = ()

    @property
    def promoted_facts(self) -> int:
        return sum(row["promoted_facts"] for row in self.promotions_by_gate)

    @property
    def disputes_after_corroboration(self) -> int:
        return sum(1 for row in self.disputes if row["corroborated_first"])


async def read_back(session) -> ReadBack:
    """What the journal and the vault say after the recompute has converged."""
    gates = (await session.execute(_PROMOTIONS_BY_GATE)).mappings().all()
    census = (await session.execute(_FACT_CENSUS)).mappings().all()
    controls = (
        await session.execute(_CONTROL_FACTS, {"names": list(CONTROL_OBJECT_NAMES)})
    ).mappings().all()
    disputes = (await session.execute(_ARMED_DISPUTES)).mappings().all()
    return ReadBack(
        promotions_by_gate=tuple(dict(row) for row in gates),
        census=tuple(dict(row) for row in census),
        controls=tuple(dict(row) for row in controls),
        disputes=tuple(dict(row) for row in disputes),
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

    lines.append("")
    lines.append("== the armed veto: disputes the detector actually produced ==")
    if not result.disputes:
        lines.append(
            "  NONE -- the arm did not fire. The false-promotion audit's zero "
            "is inoperability, not precision, and says nothing about the ladder"
        )
    for row in result.disputes:
        counterpart = (
            f"{row['counterpart_subject']} {row['counterpart_rel_type']} "
            f"{row['counterpart_object']}"
            if row["counterpart_subject"] else "(counterpart row is gone)"
        )
        lines.append(
            f"  {row['project']}: {row['subject_name']} {row['rel_type']} "
            f"{row['object_name']} -> {row['verification_status']} "
            f"by rule={row['rule']} against [{counterpart}], "
            f"witness={row['witness_origin']}, "
            f"corroborated_first={row['corroborated_first']}"
        )
    lines.append(
        f"  disputes after a journaled corroboration (the audit's numerator): "
        f"{result.disputes_after_corroboration}"
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
    wave_two_entries: int = 0
    wave_two_lift: dict = field(default_factory=dict)
    first_recompute: dict = field(default_factory=dict)


_COUNT_FACTS = text("SELECT COUNT(*) FROM knowledge_triples")


async def recompute_to_convergence(session_factory) -> dict:
    """Run the shipping recompute until a tick drains no events.

    The same loop the runner makes after this returns, spelled once here
    because wave 1 has to converge *before* wave 2 lands: the corpus's whole
    arming design is a fact corroborated on one pass and disputed on the next,
    and a single pass over both waves collapses that into one decision.
    """
    import asyncio

    await asyncio.sleep(RECOMPUTE_SKEW_WAIT_SECONDS)
    ticks = recomputed = transitions = 0
    while ticks < MAX_RECOMPUTE_TICKS:
        async with session_factory() as session:
            outcome = await run_recompute(session)
            await session.commit()
        ticks += 1
        recomputed += outcome.drain.facts_recomputed
        transitions += outcome.drain.transitions
        if outcome.drain.events_scanned == 0:
            break
    return {"ticks": ticks, "recomputed": recomputed, "transitions": transitions}


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

    **Two waves, with a full recompute between them** (T2.129). Wave 1 is the
    measured corpus and everything above; it is then recomputed to convergence,
    which is where the promotions the audit's denominator counts are journaled.
    Wave 2 is the arming pair's later half — the rollback that contradicts an
    already-corroborated fact, and the independent re-assertion that puts that
    fact back in front of the fast arm. Folding wave 2 into wave 1 does not
    merely reorder the run: the veto is checked ahead of the count, so the fact
    would go ``candidate -> disputed`` and the audit's numerator would stay 0
    with the arm armed. The runner's own recompute ticks are what then apply
    wave 2, so this returns with the dispute still owed.
    """
    import hashlib

    corpus_bytes = Path(corpus_path).read_bytes()
    entries = load_promotion_corpus(corpus_path)
    fixture = load_repo_fixture(fixture_path)
    validate_diversity_group_against_fixture(entries, fixture)
    first_wave = entries_for_wave(entries, 1)
    second_wave = entries_for_wave(entries, 2)

    await reset()
    await run_smoke.seed_llm_purpose_configs(session_factory, api_key)

    async with session_factory() as session:
        llm_config = await get_llm_config(session)

    prepared_entries = await seed_memory_rows(session_factory, first_wave)
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

    first_recompute = await recompute_to_convergence(session_factory)

    prepared_second = await seed_memory_rows(session_factory, second_wave)
    second_ingest = await run_ingest(
        llm, prepared_second, GateConfig(), session_factory
    )
    wave_two_lift = await _lift_to_exhaustion(session_factory)
    if simulate_capture_time:
        stamped += await simulate_capture_time_provenance(session_factory)

    async with session_factory() as session:
        n_facts = int((await session.execute(_COUNT_FACTS)).scalar_one())

    notes: list[str] = []
    if not simulate_capture_time:
        notes.append(
            "capture-time provenance simulation disabled: every fact_sources "
            "row carries its write time, so the time_gap gate cannot fire"
        )
    notes.append(
        f"wave 1 ({len(first_wave)} captures) was recomputed to convergence "
        f"before wave 2 ({len(second_wave)} captures) was ingested; the "
        f"dispute wave 2 arms is owed to the ticks that follow"
    )
    return PreparedCorpus(
        corpus_entries=len(entries),
        corpus_sha256=hashlib.sha256(corpus_bytes).hexdigest(),
        gate_config=ingest_result.gate_config,
        fingerprint=ingest_result.fingerprint,
        live_calls=ingest_result.live_calls + second_ingest.live_calls,
        lift=lift,
        code_lift=code_lift,
        capture_time_stamped=stamped,
        repo_assertions=repo_assertions,
        n_facts=n_facts,
        notes=tuple(notes),
        wave_two_entries=len(second_wave),
        wave_two_lift=wave_two_lift,
        first_recompute=first_recompute,
    )
