"""T2.04 — the contradiction veto is absolute.

Organised by the Done-when clause each group discharges, because every clause is
a property rather than a feature and the property is what a later reader has to
re-check:

* D1  one contradiction beats any number of corroborations
* D2  echoes — the same origin restating itself — are not contradictions
* D3  validity-window overlap is required
* D4  no ``config`` knob can soften the veto
* R   recovery out of ``disputed``, and what stops a detector-less machine
      firing it
* Inv-15  the deterministic scan is Tier-C only

Several tests exist specifically to kill a mutant the obvious test would let
through; each says which one, because a test whose purpose is invisible is a
test the next person deletes.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.models.config import Config
from app.repositories.fact_sources import (
    FactSourceRepository,
    OriginObservation,
    OriginProfile,
)
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import contradiction_veto as veto_module
from app.services.contradiction_veto import (
    CONTRADICTION_DETECTORS,
    RULE_INVERSE_REPLACEMENT,
    RULE_SINGLE_VALUED,
    SINGLE_VALUED_RELATIONS,
    ContradictionFinding,
    adjudicate_contradiction,
    adjudicate_contradiction_finding,
    detect_open_contradiction,
    windows_overlap,
)
from app.services.relations import REPLACES_FAMILY
from app.taxonomy import LEGACY_RELATION_TYPE_MAP, normalize_relation_type
from app.services.verification_ladder import (
    LADDER_CONFIG_KEY,
    LADDER_MEASUREMENTS_KEY,
    NO_DETECTOR,
    LadderConfig,
    decide,
    recompute_fact,
)

# Fixed absolute timestamps, as in T2.03's suite: nothing here derives from
# datetime.now(), so a window fixture cannot rot as the wall clock moves past it
# and cannot accidentally pass by being "recent".
T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
YEAR = timedelta(days=365)

PROJECT = "t2-04-veto"


# ─────────────────────────────── fixtures ───────────────────────────────


async def _fact(
    session,
    *,
    subject: str,
    rel: str,
    obj: str,
    project: str = PROJECT,
    valid_at: datetime | None = None,
    invalid_at: datetime | None = None,
    status: str | None = None,
    expired: bool = False,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
        valid_at=valid_at,
    )
    if invalid_at is not None:
        await repo.close_window(row["id"], invalid_at)
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    if expired:
        await repo.expire(row["id"])
    await session.commit()
    return row["id"]


async def _source(session, fact_id, origin_key, *, kind="memory", ref=None) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref or f"{kind}:{origin_key}:{uuid4()}",
        origin_key=origin_key,
    )
    await session.commit()


async def _status(session, fact_id) -> str:
    result = await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return result.scalar_one()


async def _write_config(session, key: str, value: dict) -> None:
    existing = await session.execute(select(Config).where(Config.key == key))
    row = existing.scalar_one_or_none()
    if row is None:
        session.add(Config(key=key, value=value))
    else:
        row.value = value
    await session.commit()


async def _contradicted_pair(
    session,
    *,
    corroborations: int,
    contradicting_origin: str | None,
    pair: tuple[str, str] = ("postgres", "mysql"),
):
    """A well-corroborated fact, and optionally one contradicting counterpart.

    ``inverse_replacement`` is the scan's whole reach today: "postgres replaces
    mysql" against "mysql replaces postgres", both open-ended, is mutual
    directed succession over one window. ``SINGLE_VALUED_RELATIONS`` is empty
    (see ``TestSingleValuedRelationsIsEmpty``), so no fixture here may lean on
    it.
    """
    first, second = pair
    subject = await _fact(session, subject=first, rel="REPLACES", obj=second)
    for index in range(corroborations):
        await _source(session, subject, f"sess-{index}")
    counterpart = None
    if contradicting_origin is not None:
        counterpart = await _fact(session, subject=second, rel="REPLACES", obj=first)
        await _source(session, counterpart, contradicting_origin)
    return subject, counterpart


def _profile(*keys: str, kinds: tuple[str, ...] = ("memory",)) -> OriginProfile:
    return OriginProfile(
        fact_id="f",
        origins=tuple(
            OriginObservation(
                origin_key=key,
                source_kinds=kinds,
                first_seen=T0,
                last_seen=T0,
                row_count=1,
            )
            for key in keys
        ),
    )


# ───────── D1 — one contradiction beats any number of corroborations ─────────


class TestTheVetoIsAbsolute:
    async def test_twenty_corroborations_promote_when_nothing_contradicts(self, session):
        """The control. Without it the veto tests could pass on a ladder that
        never promotes anything of this shape at all."""
        subject, _ = await _contradicted_pair(session, corroborations=20, contradicting_origin=None)

        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.origin_count == 20
        assert decision.outcome == "promote"
        assert await _status(session, subject) == "corroborated"

    async def test_one_contradiction_beats_twenty_corroborations(self, session):
        """Done-when 1, end to end through the real detector.

        The fact is promoted first, so this asserts the stronger half of doc 08
        §4.2: one contradiction does not merely block a promotion, it *demotes a
        corroborated fact to disputed*.
        """
        subject, counterpart = await _contradicted_pair(
            session, corroborations=20, contradicting_origin="contrarian"
        )
        # The counterpart is created after the promotion so the transition under
        # test is corroborated -> disputed, not candidate -> disputed.
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'corroborated' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(subject)},
        )
        await session.commit()

        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.origin_count == 20, "twenty distinct origins corroborate it"
        assert decision.contradiction_blocked is True
        assert (decision.target_status, decision.outcome) == ("disputed", "dispute")
        assert await _status(session, subject) == "disputed"

    async def test_the_veto_is_not_a_weight_at_any_level_of_support(self, session):
        """Kills a mutant that lets overwhelming support outvote one dispute.

        A "one contradiction counts as N corroborations" implementation passes
        the K=20 case only if N happens to exceed 20. Sweeping K from 0 to 40
        leaves no such threshold to hide behind.
        """
        for count in (0, 1, 3, 7, 40):
            subject, _ = await _contradicted_pair(
                session,
                corroborations=count,
                contradicting_origin="contrarian",
                pair=(f"tool-a{count}", f"tool-b{count}"),
            )
            decision = await recompute_fact(session, subject)
            await session.commit()
            assert decision.origin_count == count
            assert decision.target_status == "disputed", (
                f"the veto lost to {count} corroborating origins"
            )

    async def test_exactly_one_verified_event_per_veto(self, session):
        """``recompute_fact`` stays the sole journaller across the new branch."""
        subject, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        await recompute_fact(session, subject)
        await session.commit()

        rows = await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'verified' "
                "AND object_id = CAST(:id AS uuid) ORDER BY created_at"
            ),
            {"id": str(subject)},
        )
        events = [row[0] for row in rows.all()]
        assert len(events) == 1
        assert events[0]["before"]["verification_status"] == "candidate"
        assert events[0]["after"]["verification_status"] == "disputed"

    async def test_a_re_run_over_a_standing_dispute_journals_the_reconfirmation(
        self, session
    ):
        """T2.06 amendment (2026-07-31): a re-run over a standing dispute is
        not a status *transition* — before and after are both ``disputed`` —
        but it is the veto still firing, which is exactly the
        contradiction-blocked evidence G-C's audit needs and every other kind
        of hold is not. T2.04 originally pinned this path as silent; T2.06's
        brief requires deciding it explicitly, and the decision is to journal
        it (before == after == 'disputed', outcome == 'hold',
        contradiction_blocked == True) rather than staying quiet.
        """
        subject, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        await recompute_fact(session, subject)
        await session.commit()
        second = await recompute_fact(session, subject)
        await session.commit()

        assert (second.target_status, second.outcome) == ("disputed", "hold")
        assert second.contradiction_blocked is True
        rows = await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'verified' "
                "AND object_id = CAST(:id AS uuid) ORDER BY created_at"
            ),
            {"id": str(subject)},
        )
        events = [row[0] for row in rows.all()]
        assert len(events) == 2
        assert events[0]["outcome"] == "dispute"
        second_payload = events[1]
        assert second_payload["before"]["verification_status"] == "disputed"
        assert second_payload["after"]["verification_status"] == "disputed"
        assert second_payload["outcome"] == "hold"
        assert second_payload["contradiction_blocked"] is True

    async def test_the_belief_axis_is_untouched_by_a_veto(self, session):
        """Verification and belief stay orthogonal (doc 08 §3)."""
        subject, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        before = (
            await session.execute(
                text(
                    "SELECT valid_at, invalid_at, expired_at FROM knowledge_triples "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(subject)},
            )
        ).mappings().one()

        await recompute_fact(session, subject)
        await session.commit()

        after = (
            await session.execute(
                text(
                    "SELECT valid_at, invalid_at, expired_at FROM knowledge_triples "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(subject)},
            )
        ).mappings().one()
        assert dict(before) == dict(after)


# ───────────────────────── D2 — echoes are not evidence ─────────────────────


class TestEchoIsNotContradiction:
    async def test_one_origin_restating_a_contradiction_ten_times_does_not_veto(
        self, session
    ):
        """Done-when 2. Ten rows, one origin, zero witnesses."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        for name in ("sess-a", "sess-b", "sess-c"):
            await _source(session, subject, name)
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        for index in range(10):
            await _source(session, counterpart, "sess-a", ref=f"memory:echo-{index}")

        assert await detect_open_contradiction(session, subject) is None
        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.target_status != "disputed"
        assert decision.outcome == "promote"

    async def test_a_single_distinct_origin_on_the_same_counterpart_does_veto(
        self, session
    ):
        """The control for the test above, differing in one row's origin only.

        Without it, the echo test would also pass on a detector that never fires
        for this rule at all.
        """
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        for name in ("sess-a", "sess-b", "sess-c"):
            await _source(session, subject, name)
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        for index in range(9):
            await _source(session, counterpart, "sess-a", ref=f"memory:echo-{index}")
        await _source(session, counterpart, "sess-outsider")

        finding = await detect_open_contradiction(session, subject)
        assert finding is not None
        assert finding.witness_origin == "sess-outsider"
        assert finding.counterpart_id == str(counterpart)
        assert finding.rule == RULE_INVERSE_REPLACEMENT

    async def test_the_echo_rule_asks_the_question_of_the_challenger_only(
        self, session
    ):
        """The asymmetry, pinned rather than left to surprise the next reader.

        Subject origins {a}, counterpart origins {a, b}. The counterpart brings
        a witness the subject does not have, so the subject is disputed; scanned
        in its own turn the counterpart is not, because every origin behind the
        subject is already behind it. The question is always asked of the
        challenger. A symmetric rule would dispute both rows on one witness's
        say-so, which is a vote, and the veto is not a vote.
        """
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        await _source(session, counterpart, "sess-a", ref="memory:shared")
        await _source(session, counterpart, "sess-b", ref="memory:extra")

        assert await detect_open_contradiction(session, subject) is not None
        assert await detect_open_contradiction(session, counterpart) is None

    async def test_a_counterpart_with_no_sources_at_all_does_not_veto(self, session):
        """No witness, no testimony. A fact nobody asserts cannot contradict."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        await _fact(session, subject="promtail", rel="REPLACES", obj="alloy")

        assert await detect_open_contradiction(session, subject) is None

    async def test_the_anonymous_bucket_is_never_the_witness(self, session):
        """T2.02's doctrine carried onto the veto's side.

        Unknown origin identity folds to one bucket that counts toward K but
        names no session, so it can supply neither a promotion gate nor the
        distinct witness a non-echo contradiction requires. Without this, two
        unattributed captures could manufacture a dispute exactly as they could
        once have manufactured a promotion.
        """
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        await _source(session, counterpart, None, ref="memory:anon-1")
        await _source(session, counterpart, "unknown:mcp:default", ref="memory:anon-2")
        await _source(session, counterpart, "   ", ref="memory:anon-3")

        assert await detect_open_contradiction(session, subject) is None

    async def test_the_echo_test_normalises_origins_the_way_the_repository_does(
        self, session
    ):
        """Case and padding are the same origin, so they are still an echo.

        Kills a mutant comparing raw ``fact_sources.origin_key`` strings: the
        profile hands back lowercased, trimmed keys, so a raw comparison would
        read ``  Sess-A `` as a distinct witness and veto on an echo.
        """
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        await _source(session, counterpart, "  Sess-A  ", ref="memory:cased")

        assert await detect_open_contradiction(session, subject) is None


# ─────────────────── D3 — validity-window overlap is required ───────────────


class TestWindowOverlapIsRequired:
    """Doc 08 §4.2's own example, rendered as the REPLACES-family inverse pair.

    "postgres replaces mysql" believed through 2024 and "mysql replaces
    postgres" believed from 2025 are a **succession the belief axis already
    models**, not a contradiction. The same pair over one window is a genuine
    one.
    """

    async def _replacement_pair(self, session, *, first_window, second_window):
        subject = await _fact(
            session,
            subject="postgres",
            rel="REPLACES",
            obj="mysql",
            valid_at=first_window[0],
            invalid_at=first_window[1],
        )
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session,
            subject="mysql",
            rel="REPLACES",
            obj="postgres",
            valid_at=second_window[0],
            invalid_at=second_window[1],
        )
        await _source(session, counterpart, "sess-b")
        return subject, counterpart

    async def test_disjoint_windows_are_succession_not_contradiction(self, session):
        subject, _ = await self._replacement_pair(
            session,
            first_window=(T0, T0 + YEAR),
            second_window=(T0 + YEAR, T0 + 2 * YEAR),
        )
        assert await detect_open_contradiction(session, subject) is None

    async def test_overlapping_windows_are_a_contradiction(self, session):
        """The control: the same two claims, windows overlapping."""
        subject, counterpart = await self._replacement_pair(
            session,
            first_window=(T0, T0 + 2 * YEAR),
            second_window=(T0 + YEAR, T0 + 3 * YEAR),
        )
        finding = await detect_open_contradiction(session, subject)
        assert finding is not None
        assert finding.rule == RULE_INVERSE_REPLACEMENT
        assert finding.counterpart_id == str(counterpart)

    async def test_two_open_ended_beliefs_overlap(self, session):
        """The stated open-ended semantics, asserted rather than assumed.

        NULL ``valid_at`` is unbounded-past and NULL ``invalid_at`` open-ended
        (doc 08 §3.1), so two rows with neither bound are two simultaneous live
        beliefs and genuinely conflict.
        """
        subject, _ = await self._replacement_pair(
            session, first_window=(None, None), second_window=(None, None)
        )
        assert await detect_open_contradiction(session, subject) is not None

    async def test_a_closed_historical_window_does_not_dispute_a_later_belief(
        self, session
    ):
        """The hazard the overlap rule exists to prevent.

        Getting this backwards turns every retained historical row into a
        standing dispute against whatever replaced it.
        """
        subject, _ = await self._replacement_pair(
            session,
            first_window=(T0 + 2 * YEAR, None),
            second_window=(T0, T0 + YEAR),
        )
        assert await detect_open_contradiction(session, subject) is None

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            # Both unbounded on both sides.
            ((None, None), (None, None), True),
            # One unbounded either way against a bounded window.
            ((None, None), (T0, T0 + YEAR), True),
            ((None, T0), (T0 + YEAR, None), False),
            ((T0 + YEAR, None), (None, T0), False),
            # Bounded, disjoint.
            ((T0, T0 + YEAR), (T0 + 2 * YEAR, T0 + 3 * YEAR), False),
            # Bounded, adjacent: one closes exactly where the next opens. The
            # half-open reading makes these disjoint, which is what the
            # disjoint-window pass produces and must not read as a conflict.
            ((T0, T0 + YEAR), (T0 + YEAR, T0 + 2 * YEAR), False),
            # Bounded, overlapping by an instant on either side.
            ((T0, T0 + YEAR), (T0 + YEAR - timedelta(seconds=1), T0 + 2 * YEAR), True),
            # Fully contained.
            ((T0, T0 + 3 * YEAR), (T0 + YEAR, T0 + 2 * YEAR), True),
        ],
    )
    def test_overlap_vectors(self, a, b, expected):
        assert windows_overlap(a[0], a[1], b[0], b[1]) is expected

    def test_overlap_is_symmetric(self):
        """A contradiction cannot depend on which fact the scan started from."""
        windows = [
            (None, None),
            (T0, None),
            (None, T0 + YEAR),
            (T0, T0 + YEAR),
            (T0 + YEAR, T0 + 2 * YEAR),
        ]
        for first in windows:
            for second in windows:
                assert windows_overlap(*first, *second) == windows_overlap(*second, *first)


# ────────────────── D4 — no config knob can soften the veto ─────────────────


# Every spelling by which a threshold, weight or flag could reach this path.
# Kept as data so the negative control below can exercise the real predicate.
_CONFIG_TOKENS = (
    "Config",
    "LadderConfig",
    "LADDER_FLOORS",
    "LADDER_CONFIG_KEY",
    "LADDER_MEASUREMENTS_KEY",
    "get_ladder_config",
    "get_ladder_measurements",
    "feature_flags",
    "FEATURE_FLAGS",
    "get_settings",
    "config_schema",
    "FROM config",
    "threshold",
    "enabled",
)


def _executable_source(source: str) -> str:
    """``source`` with every docstring and comment removed.

    Scanning raw text would flag the prose *explaining* that no threshold
    exists, which is the fastest way to get a guard deleted as noise.
    ``ast.unparse`` drops comments for free; the docstrings have to be popped.
    String literals survive, so a config read hidden in SQL is still caught.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)
    return ast.unparse(tree)


def _config_references(source: str) -> list[str]:
    """Lines of executable ``source`` that reach for configuration.

    The one predicate. A control that re-typed this inline would prove only
    that the copy works; the real scan could go blind with its tokens
    misspelled and still report success.
    """
    hits: list[str] = []
    for lineno, line in enumerate(_executable_source(source).splitlines(), 1):
        for token in _CONFIG_TOKENS:
            if token in line:
                hits.append(f"{lineno}: {line.strip()}")
                break
    return hits


class TestNoConfigKnobCanSoftenTheVeto:
    def test_the_detector_module_reads_no_configuration(self):
        source = Path(inspect.getfile(veto_module)).read_text()
        hits = _config_references(source)
        assert not hits, (
            "the contradiction scan reached for configuration:\n"
            + "\n".join(hits)
            + "\nThe veto is absolute (doc 08 §4.2): not a weight, not a score, "
              "not tunable. A threshold here would be a knob that softens it."
        )

    def test_the_scan_rejects_a_synthesised_knob(self):
        """In-suite negative control — the guard's teeth, proven every run."""
        knobbed = (
            "async def detect(session, fact_id):\n"
            '    """No knob here at all, honest."""\n'
            "    row = await session.execute('SELECT value FROM config')\n"
            "    if not row['enabled']:\n"
            "        return None\n"
        )
        hits = _config_references(knobbed)
        assert hits, (
            "the real predicate failed to flag a synthesised config read; the "
            "module scan above would be reporting success while blind"
        )

    def test_the_detector_signature_carries_no_tunable(self):
        """Structural: there is no parameter a caller could turn down."""
        for func in (detect_open_contradiction, adjudicate_contradiction):
            params = list(inspect.signature(func).parameters)
            assert params == ["session", "fact_id"], (
                f"{func.__name__} grew a parameter beyond the session and the "
                "fact it adjudicates"
            )

    @pytest.mark.parametrize(
        "config",
        [
            LadderConfig(),
            LadderConfig(n_default=99, n_diverse=99, time_gap_days=9999),
            LadderConfig(n_default=1, n_diverse=1, time_gap_days=0),
        ],
    )
    @pytest.mark.parametrize("origin_count", [0, 1, 3, 40])
    @pytest.mark.parametrize("status", ["candidate", "corroborated"])
    def test_no_threshold_grid_position_changes_the_veto(
        self, config, origin_count, status
    ):
        """The behavioural half, swept rather than sampled.

        A veto expressed as *any* arithmetic against the ladder's numbers would
        flip somewhere on this grid. None of these 24 positions may differ.
        """
        prof = _profile(*(f"o{i}" for i in range(origin_count)))
        decision = decide("f", status, prof, config, open_contradiction=True)
        assert (decision.target_status, decision.outcome) == ("disputed", "dispute")
        assert decision.contradiction_blocked is True

    async def test_no_written_config_row_softens_a_real_veto(self, session):
        """End to end, against every row an operator could plausibly reach for.

        Includes a fabricated ``contradiction_veto`` row with an off switch,
        because the failure this guards is a *future* knob, not a present one.
        """
        await _write_config(
            session,
            LADDER_CONFIG_KEY,
            {"n_default": 99, "n_diverse": 99, "time_gap_days": 9999},
        )
        await _write_config(
            session,
            LADDER_MEASUREMENTS_KEY,
            {"measured": ["n_default", "n_diverse", "time_gap_days"]},
        )
        await _write_config(
            session,
            "feature_flags",
            {"contradiction_veto_enabled": False, "hybrid_search_enabled": True},
        )
        await _write_config(
            session,
            "contradiction_veto",
            {"enabled": False, "threshold": 99, "min_contradictions": 5, "weight": 0.0},
        )

        subject, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.target_status == "disputed"
        assert await _status(session, subject) == "disputed"


# ─────────────────────── R — recovery out of `disputed` ─────────────────────


class TestRecovery:
    def test_no_detector_still_holds_a_dispute_unconditionally(self):
        """The property T2.03 protected, now protected by the third value.

        ``NO_DETECTOR`` is not ``False``: a caller that ran nothing cannot end a
        dispute by silence. This is what stops a machine with no detector behind
        it from journalling ``disputed -> corroborated``.
        """
        assert NO_DETECTOR is None
        strong = OriginProfile(
            fact_id="f",
            origins=(
                OriginObservation("a", ("memory",), T0, T0, 1),
                OriginObservation("b", ("code",), T0, T0, 1),
            ),
        )
        held = decide("f", "disputed", strong, LadderConfig())
        assert (held.target_status, held.outcome) == ("disputed", "hold")

        recovered = decide("f", "disputed", strong, LadderConfig(), open_contradiction=False)
        assert (recovered.target_status, recovered.outcome) == ("corroborated", "recover")

    def test_recovery_re_enters_the_ordinary_rule_rather_than_jumping_to_corroborated(
        self,
    ):
        """A fact that lost its origins while disputed is not re-promoted.

        The contradiction being resolved says nothing about the fact's support,
        so recovery lands where the count puts it.
        """
        thin = _profile("a")
        decision = decide("f", "disputed", thin, LadderConfig(), open_contradiction=False)
        assert (decision.target_status, decision.outcome) == ("candidate", "recover")

    async def test_a_resolved_contradiction_recovers_the_fact(self, session):
        subject, counterpart = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        await recompute_fact(session, subject)
        await session.commit()
        assert await _status(session, subject) == "disputed"

        # Belief in the counterpart is withdrawn — the deterministic resolution
        # of a same-endpoint dispute the belief axis already models.
        await KnowledgeTripleRepository(session).expire(counterpart)
        await session.commit()

        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.outcome == "recover"
        assert await _status(session, subject) == "corroborated"

    async def test_a_standing_contradiction_is_never_recovered(self, session):
        """Kills a recovery that fires on reaching the branch rather than on a
        clean verdict."""
        subject, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        for _ in range(3):
            await recompute_fact(session, subject)
            await session.commit()
        assert await _status(session, subject) == "disputed"

    async def test_recovery_journals_exactly_one_transition(self, session):
        subject, counterpart = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="contrarian"
        )
        await recompute_fact(session, subject)
        await session.commit()
        await KnowledgeTripleRepository(session).expire(counterpart)
        await session.commit()
        await recompute_fact(session, subject)
        await session.commit()

        rows = await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'verified' "
                "AND object_id = CAST(:id AS uuid) ORDER BY created_at"
            ),
            {"id": str(subject)},
        )
        events = [row[0] for row in rows.all()]
        # Asserted as a chain rather than by ordering: the fixture's savepoints
        # share one transaction timestamp, so `created_at` cannot separate two
        # rows written in the same test.
        assert len(events) == 2
        transitions = {
            (e["before"]["verification_status"], e["after"]["verification_status"])
            for e in events
        }
        assert transitions == {("candidate", "disputed"), ("disputed", "corroborated")}


class TestDetectorComposition:
    def test_only_the_deterministic_scan_is_wired_today(self):
        """T2.11's LLM scan joins this tuple when it lands.

        Recorded as an assertion rather than a comment so the hand-off cannot
        happen silently: a detector plumbed past the registry would keep its own
        disputes open while this one's silence resolved them.
        """
        assert CONTRADICTION_DETECTORS == (detect_open_contradiction,)

    async def test_any_registered_detector_can_open_a_dispute(self, session, monkeypatch):
        """The registry is read, not decorative.

        Kills an ``adjudicate_contradiction`` that calls the deterministic scan
        directly and ignores the tuple — under which T2.11 could register and
        never be consulted.
        """
        subject = await _fact(session, subject="darkmem", rel="USES", obj="pgvector")
        await _source(session, subject, "sess-a")
        assert await adjudicate_contradiction(session, subject) is False

        async def always_finds(_session, fact_id):
            return ContradictionFinding(
                fact_id=str(fact_id),
                counterpart_id=str(uuid4()),
                rule="stub",
                witness_origin="stub-origin",
            )

        monkeypatch.setattr(
            veto_module,
            "CONTRADICTION_DETECTORS",
            (detect_open_contradiction, always_finds),
        )
        assert await adjudicate_contradiction(session, subject) is True

    async def test_a_clean_verdict_needs_every_detector_to_report_nothing(
        self, session, monkeypatch
    ):
        """Recovery is conjunctive: one dissenting detector keeps the dispute."""
        subject = await _fact(
            session, subject="darkmem", rel="USES", obj="pgvector", status="disputed"
        )
        await _source(session, subject, "sess-a")

        async def always_finds(_session, fact_id):
            return ContradictionFinding(
                fact_id=str(fact_id),
                counterpart_id=str(uuid4()),
                rule="stub",
                witness_origin="stub-origin",
            )

        monkeypatch.setattr(veto_module, "CONTRADICTION_DETECTORS", (always_finds,))
        decision = await recompute_fact(session, subject)
        await session.commit()
        assert (decision.target_status, decision.outcome) == ("disputed", "hold")
        assert await _status(session, subject) == "disputed"


# ──────────────────────── the deterministic scan itself ─────────────────────


class TestTheDeterministicScan:
    async def test_a_multi_valued_relation_is_never_scanned(self, session):
        """"darkmem uses postgres" and "darkmem uses fastapi" are both true.

        Telling an additional truth from a replacement needs the model T2.11
        wires; a deterministic scan that guessed would manufacture disputes over
        every polyvalent relation in the corpus.
        """
        subject = await _fact(session, subject="darkmem", rel="USES", obj="postgres")
        await _source(session, subject, "sess-a")
        other = await _fact(session, subject="darkmem", rel="USES", obj="fastapi")
        await _source(session, other, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    def test_the_inverse_rule_uses_the_shared_replaces_family(self):
        """One spelling of the family, imported rather than re-typed."""
        assert REPLACES_FAMILY == frozenset({"REPLACES", "IMPROVES_ON", "BUILDS_ON"})

    async def test_the_inverse_rule_spans_the_whole_family(self, session):
        """``REPLACES`` against ``IMPROVES_ON`` is still mutual succession."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="promtail", rel="IMPROVES_ON", obj="alloy"
        )
        await _source(session, counterpart, "sess-b")

        finding = await detect_open_contradiction(session, subject)
        assert finding is not None
        assert finding.rule == RULE_INVERSE_REPLACEMENT

    async def test_the_same_claim_restated_is_agreement_not_contradiction(self, session):
        """Same endpoints, same direction — two witnesses agreeing."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        agreeing = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, agreeing, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_a_counterpart_in_another_project_never_contradicts(self, session):
        """Project is the isolation boundary here as everywhere else."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        elsewhere = await _fact(
            session,
            subject="promtail",
            rel="REPLACES",
            obj="alloy",
            project="some-other-project",
        )
        await _source(session, elsewhere, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_an_expired_counterpart_never_contradicts(self, session):
        """Belief has been withdrawn from it; it is history, not a claim."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        withdrawn = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy", expired=True
        )
        await _source(session, withdrawn, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_an_expired_subject_is_not_adjudicated(self, session):
        subject = await _fact(
            session, subject="alloy", rel="REPLACES", obj="promtail", expired=True
        )
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="promtail", rel="REPLACES", obj="alloy"
        )
        await _source(session, counterpart, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_a_fact_never_contradicts_itself(self, session):
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="promtail")
        await _source(session, subject, "sess-a")
        assert await detect_open_contradiction(session, subject) is None

    async def test_a_replacement_self_loop_is_not_its_own_inverse(self, session):
        """Kills the arm that matches ``subject_name = object_name`` against
        itself and disputes every self-loop on that name."""
        subject = await _fact(session, subject="alloy", rel="REPLACES", obj="alloy")
        await _source(session, subject, "sess-a")
        other = await _fact(session, subject="alloy", rel="REPLACES", obj="alloy")
        await _source(session, other, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_a_missing_fact_adjudicates_to_nothing(self, session):
        assert await detect_open_contradiction(session, uuid4()) is None
        assert await adjudicate_contradiction(session, uuid4()) is False


# ───── The single-valued rule, and why its set is empty (fix round) ─────


class TestSingleValuedRelationsIsEmpty:
    """`HAPPENED_ON` was admitted and had to be withdrawn. This is the guard.

    `normalize_relation_type` folds three unrelated senses into that one stored
    value with no discriminator: a point occurrence, a span occurrence, and --
    through `LEGACY_RELATION_TYPE_MAP`'s `VISITED` and `LIVES_IN` -- a *location*.
    A relation is single-valued only when every sense it stores is, so admitting
    it manufactured disputes out of claims that are all true at once.
    """

    def test_the_set_is_empty_and_stated(self):
        assert SINGLE_VALUED_RELATIONS == frozenset(), (
            "no relation in the closed vocabulary is single-valued across every "
            "sense it stores; widening this needs a taxonomy change, not an edit"
        )

    def test_no_member_may_be_a_target_of_the_legacy_map(self):
        """The general guard, not an enumeration of today's mistake.

        A legacy alias folding a different sense into a relation is *the*
        mechanism that made `HAPPENED_ON` polyvalent, and it re-reads the live
        map, so a future alias pointing at a future member fails here too.
        """
        folded = frozenset(LEGACY_RELATION_TYPE_MAP.values())
        offenders = SINGLE_VALUED_RELATIONS & folded
        assert not offenders, (
            f"{sorted(offenders)} carry legacy aliases "
            f"({sorted(k for k, v in LEGACY_RELATION_TYPE_MAP.items() if v in offenders)}) "
            "that fold a different sense into the same stored rel_type, so the "
            "relation is not single-valued and the scan would manufacture "
            "disputes out of simultaneously-true claims"
        )

    def test_the_legacy_map_really_does_fold_locations_into_happened_on(self):
        """The premise of the guard above, asserted rather than assumed.

        If the taxonomy ever separates these senses this test fails, which is
        the signal that re-admitting `HAPPENED_ON` may be re-examined.
        """
        assert normalize_relation_type("VISITED") == "HAPPENED_ON"
        assert normalize_relation_type("LIVES_IN") == "HAPPENED_ON"

    async def test_two_places_a_person_has_been_are_not_a_contradiction(self, session):
        """The regression. `alice VISITED paris` and `alice LIVES_IN tokyo` both
        normalise to `HAPPENED_ON` and are both true."""
        subject = await _fact(
            session, subject="alice", rel=normalize_relation_type("VISITED"), obj="paris"
        )
        await _source(session, subject, "sess-a")
        other = await _fact(
            session, subject="alice", rel=normalize_relation_type("LIVES_IN"), obj="tokyo"
        )
        await _source(session, other, "sess-b")

        assert await detect_open_contradiction(session, subject) is None
        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.target_status != "disputed"

    async def test_a_multi_day_event_asserted_per_day_is_not_a_contradiction(
        self, session
    ):
        """The instance no date parse can close: both objects *are* dates.

        This is why the honest fix was emptying the set rather than gating the
        object side on date-shape.
        """
        subject = await _fact(
            session, subject="the conference", rel="HAPPENED_ON", obj="2024-03-01"
        )
        await _source(session, subject, "sess-a")
        second_day = await _fact(
            session, subject="the conference", rel="HAPPENED_ON", obj="2024-03-02"
        )
        await _source(session, second_day, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_two_spellings_of_one_date_are_not_a_contradiction(self, session):
        """`object_name` is a string, so the same date in two formats is two
        distinct values and two origins stating it would dispute each other."""
        subject = await _fact(
            session, subject="the launch", rel="HAPPENED_ON", obj="2024-03-01"
        )
        await _source(session, subject, "sess-a")
        restated = await _fact(
            session, subject="the launch", rel="HAPPENED_ON", obj="march 1, 2024"
        )
        await _source(session, restated, "sess-b")

        assert await detect_open_contradiction(session, subject) is None

    async def test_the_single_valued_arm_still_works_when_a_relation_qualifies(
        self, session, monkeypatch
    ):
        """The rule is dark for want of a qualifying relation, not broken.

        `DEPLOYED_ON` stands in purely to exercise the arm -- nothing here claims
        it is single-valued, and the guards above are what keep the real set
        empty. Without this test the arm would be untested code that a later
        taxonomy change silently depends on.
        """
        monkeypatch.setattr(
            veto_module, "SINGLE_VALUED_RELATIONS", frozenset({"DEPLOYED_ON"})
        )
        subject = await _fact(
            session, subject="darkmem", rel="DEPLOYED_ON", obj="homelab"
        )
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="darkmem", rel="DEPLOYED_ON", obj="fly-io"
        )
        await _source(session, counterpart, "sess-b")

        finding = await detect_open_contradiction(session, subject)
        assert finding is not None
        assert finding.rule == RULE_SINGLE_VALUED
        assert finding.counterpart_id == str(counterpart)
        assert finding.witness_origin == "sess-b"

    async def test_the_arm_is_dark_with_the_real_set(self, session):
        """The control for the test above: same rows, no monkeypatch, no finding."""
        subject = await _fact(
            session, subject="darkmem", rel="DEPLOYED_ON", obj="homelab"
        )
        await _source(session, subject, "sess-a")
        counterpart = await _fact(
            session, subject="darkmem", rel="DEPLOYED_ON", obj="fly-io"
        )
        await _source(session, counterpart, "sess-b")

        assert await detect_open_contradiction(session, subject) is None


# ───────── T2.64 — the finding names the claim, not only the row ─────────


class TestTheFindingCarriesTheCounterpartsClaim:
    """Doc 08 §6 serves a disputed fact labelled with both sides, and §4.2's
    finding is the only thing that ever knows the other one.

    An id alone would satisfy "names the counterpart" while failing the clause
    it exists for: the human adjudicating, and every surface serving them,
    would still have to fetch ``knowledge_triples`` to learn what the other
    side actually claims — and the surfaces that would have to do the fetching
    are exactly the ones forbidden from reaching this scan.
    """

    async def test_the_finding_carries_the_counterparts_own_triple(self, session):
        subject, counterpart = await _contradicted_pair(
            session, corroborations=2, contradicting_origin="sess-dissent"
        )

        finding = await detect_open_contradiction(session, subject)

        assert finding is not None
        assert finding.counterpart_id == counterpart
        # Reversed, not echoed. The subject asserts "postgres REPLACES mysql";
        # a finding that read its own row back would produce that triple and
        # look plausible, so the assertion pins the counterpart's direction.
        assert (
            finding.counterpart_subject,
            finding.counterpart_rel_type,
            finding.counterpart_object,
        ) == ("mysql", "REPLACES", "postgres")
        assert finding.rule == RULE_INVERSE_REPLACEMENT
        assert finding.witness_origin == "sess-dissent"

    async def test_the_claim_is_readable_without_reading_the_counterpart_row(
        self, session
    ):
        """The whole point of carrying the triple: delete the counterpart and
        the finding still states what it claimed.

        Not a hypothetical — ``events`` is append-only and its payloads outlive
        deletion of their subject, so a journalled finding routinely outlives
        the row it names.
        """
        subject, counterpart = await _contradicted_pair(
            session, corroborations=1, contradicting_origin="sess-dissent"
        )
        finding = await detect_open_contradiction(session, subject)
        assert finding is not None

        await session.execute(
            text("DELETE FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
            {"id": counterpart},
        )
        await session.commit()

        assert finding.counterpart_object == "postgres"
        assert await detect_open_contradiction(session, subject) is None

    async def test_the_widened_projection_changed_no_verdict(self, session):
        """The three name columns are projection, never predicate: the same
        pair that contradicted before still does, and the same non-pair still
        does not."""
        disputed, _ = await _contradicted_pair(
            session, corroborations=3, contradicting_origin="sess-dissent"
        )
        clean, _ = await _contradicted_pair(
            session,
            corroborations=3,
            contradicting_origin=None,
            pair=("redis", "memcached"),
        )

        assert await adjudicate_contradiction(session, disputed) is True
        assert await adjudicate_contradiction(session, clean) is False

    async def test_the_finding_variant_reads_the_registry_not_the_scan(
        self, session, monkeypatch
    ):
        """Kills an ``adjudicate_contradiction_finding`` that calls the
        deterministic scan directly — under which T2.11 could register a
        detector, open disputes through the boolean predicate, and have its
        finding silently dropped from every journalled payload.
        """
        subject = await _fact(session, subject="darkmem", rel="USES", obj="pgvector")
        await _source(session, subject, "sess-a")
        assert await adjudicate_contradiction_finding(session, subject) is None

        stub = ContradictionFinding(
            fact_id=str(subject),
            counterpart_id=str(uuid4()),
            rule="stub",
            witness_origin="stub-origin",
        )

        async def always_finds(_session, _fact_id):
            return stub

        monkeypatch.setattr(
            veto_module,
            "CONTRADICTION_DETECTORS",
            (detect_open_contradiction, always_finds),
        )
        assert await adjudicate_contradiction_finding(session, subject) is stub

    async def test_the_two_adjudication_forms_never_disagree(self, session, monkeypatch):
        """The boolean predicate is the finding variant's own answer, reduced.

        Two independent walks of ``CONTRADICTION_DETECTORS`` could disagree
        about what a clean verdict means, and only one of them is the one that
        ends a dispute.
        """
        subject, _ = await _contradicted_pair(
            session, corroborations=2, contradicting_origin="sess-dissent"
        )
        clean, _ = await _contradicted_pair(
            session,
            corroborations=2,
            contradicting_origin=None,
            pair=("redis", "memcached"),
        )

        for fact_id in (subject, clean):
            verdict = await adjudicate_contradiction(session, fact_id)
            finding = await adjudicate_contradiction_finding(session, fact_id)
            assert verdict is (finding is not None)

        monkeypatch.setattr(veto_module, "CONTRADICTION_DETECTORS", ())
        assert await adjudicate_contradiction(session, subject) is False
        assert await adjudicate_contradiction_finding(session, subject) is None


# ───────── Invariant 15 — the deterministic scan is Tier-C only ─────────

BACKEND = Path(__file__).resolve().parent.parent

# The ladder is the scan's only legitimate consumer: the veto is an input to the
# verification decision and nothing else. T2.11 registers its detector inside the
# scan's own module, so it does not join this list.
_ALLOWED_VETO_FILES: set[str] = {"app/services/verification_ladder.py"}


def _forbidden_veto_references(paths: list[Path], root: Path = BACKEND) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(root))
        if rel == "app/services/contradiction_veto.py" or rel in _ALLOWED_VETO_FILES:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if (
                "app.services.contradiction_veto" in line
                or "from app.services import contradiction_veto" in line
                or "detect_open_contradiction" in line
                or "adjudicate_contradiction" in line
            ):
                offenders.append(f"{rel}:{lineno}: {stripped}")
    return offenders


def test_no_app_code_outside_the_ladder_reaches_the_scan():
    paths = [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scan below would pass "
        "vacuously; check BACKEND / the glob path"
    )
    offenders = _forbidden_veto_references(paths)
    assert not offenders, (
        "app code outside the verification ladder reached the contradiction "
        "scan:\n" + "\n".join(offenders) + "\nThe veto is Tier-C (invariant 15): "
        "adjudication stays off capture and retrieval, and a fact write that "
        "disputed inline would put a model-free verdict on the hot path."
    )


def test_the_veto_guard_rejects_a_forbidden_reference(tmp_path):
    """In-suite negative control — proven every run, not once by hand."""
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True)
    violation = fake / "eager_dispute.py"
    violation.write_text(
        "from app.services.contradiction_veto import detect_open_contradiction\n"
        "async def on_write(session, fact_id):\n"
        "    await detect_open_contradiction(session, fact_id)\n"
    )
    offenders = _forbidden_veto_references([violation], root=tmp_path)
    assert offenders, (
        "the real guard failed to flag a synthesised violation; the tree-wide "
        "scan above would be reporting success while blind"
    )
