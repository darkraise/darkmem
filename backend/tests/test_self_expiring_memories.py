"""Self-expiring dated memories (doc 08 §2.3, T2.34).

A memory that states its own retention gets `memories.expires_at` populated at
capture, so T1.37's sweep spends it without the caller setting a TTL.

The tests are weighted the way the risk is. The sweep **deletes** — embeddings
cascade, provenance is withdrawn, nothing brings the row back — so the
false-positive cases below are the load-bearing ones, and each is a phrasing
that a date-proximity parser would have got wrong. The recall cases are here to
prove the feature does something at all; the refusal cases are here to prove it
cannot destroy anything.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.stated_expiry import derive_stated_expiry

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def derive(content: str, *, reference_time: datetime = NOW):
    return derive_stated_expiry(content, reference_time=reference_time)


# ───────────────────────── it detects a real one ─────────────────────────


@pytest.mark.parametrize(
    "content,expected",
    [
        ("This note is valid until 2026-12-31.",
         datetime(2027, 1, 1, tzinfo=timezone.utc)),
        ("this memory is good through 2026-06-30",
         datetime(2026, 7, 1, tzinfo=timezone.utc)),
        ("This entry expires on 2026-03-01.",
         datetime(2026, 3, 2, tzinfo=timezone.utc)),
        ("Delete this after 2026-09-15.",
         datetime(2026, 9, 16, tzinfo=timezone.utc)),
        ("Remember this until 2026-11-30",
         datetime(2026, 12, 1, tzinfo=timezone.utc)),
        ("This note remains accurate until the end of Q3 2026.",
         datetime(2026, 10, 1, tzinfo=timezone.utc)),
        ("This memory is valid until end of March 2027",
         datetime(2027, 4, 1, tzinfo=timezone.utc)),
        ("This note is valid until December 2026",
         datetime(2027, 1, 1, tzinfo=timezone.utc)),
        ("This record is valid until March 5, 2026",
         datetime(2026, 3, 6, tzinfo=timezone.utc)),
    ],
)
def test_a_stated_self_referential_expiry_is_derived(content, expected):
    assert derive(content) == expected


def test_the_stated_day_is_covered_in_full():
    """End-exclusive. "Valid until the 31st" means good *through* the 31st, so
    the instant is the end of that day. Reading it as the day's midnight start
    would delete the memory a day early — and immediately, for a same-day TTL."""
    assert derive("This note is valid until 2026-12-31.") == datetime(
        2027, 1, 1, tzinfo=timezone.utc
    )


def test_the_earliest_future_expiry_wins():
    """Two stated retentions are two promises, and only the tighter one can be
    kept."""
    content = (
        "This note is valid until 2027-01-31. "
        "Actually, delete this after 2026-06-30."
    )
    assert derive(content) == datetime(2026, 7, 1, tzinfo=timezone.utc)


# ─────────────── it refuses the ones that would destroy data ───────────────


@pytest.mark.parametrize(
    "content",
    [
        # The canonical false positive: a date about some other subject.
        "The TLS certificate is valid until 2026-12-31, so renew it before then.",
        "The licence expires on 2026-09-01 and we should budget for the renewal.",
        "Postgres 14 reaches end of life on 2026-11-12.",
        "The contract with the vendor is good through March 2027.",
        "Our AWS reserved instances expire on 2026-08-01.",
        # A bare date with no retention claim at all.
        "We shipped the migration on 2026-01-10.",
        "Deadline: 2026-12-31.",
        # An expiry word and a date in the same memory, but unconnected.
        "This note covers the outage. The incident started 2026-12-31.",
    ],
)
def test_a_date_about_something_else_is_not_the_memorys_own_ttl(content):
    """The sweep deletes, so this is the direction that must never be wrong.
    Every string here would be a false positive for a parser keyed on a date
    near an expiry word."""
    assert derive(content) is None


@pytest.mark.parametrize(
    "content",
    [
        "This note is valid until 2020-01-01.",
        "Delete this after 2026-01-14.",
        "This note is valid until December 2025",
    ],
)
def test_a_past_expiry_is_refused(content):
    """Capture must not be able to arm a sweep that deletes the memory it just
    wrote — a lapsed date in the text is a typo or a quotation, never a TTL."""
    assert derive(content, reference_time=NOW) is None


@pytest.mark.parametrize(
    "reference",
    [
        datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
    ],
)
def test_a_same_day_expiry_lives_out_the_day_it_claims(reference):
    """The boundary, from inside the stated day. "Expires on the 15th" captured
    *during* the 15th is not a lapsed date — end-exclusive, the memory is good
    until the day ends, so it is derived rather than refused. Refusing it would
    silently drop a same-day TTL, which is the one case a caller is most
    likely to mean literally."""
    assert derive("This memory expires on 2026-01-15.", reference_time=reference) == (
        datetime(2026, 1, 16, tzinfo=timezone.utc)
    )


@pytest.mark.parametrize(
    "content",
    [
        # No year: which Q3? A guess here deletes a memory.
        "This note is valid until the end of Q3.",
        "This memory is valid until next spring.",
        "Keep this for six months.",
        "This note is valid until further notice.",
    ],
)
def test_an_ambiguous_or_relative_expiry_is_refused(content):
    assert derive(content) is None


@pytest.mark.parametrize(
    "content",
    [
        "This note is valid until 2026-02-30.",  # impossible day
        "This note is valid until 2026-13-01.",  # impossible month
    ],
)
def test_an_impossible_date_is_refused_rather_than_clamped(content):
    """Clamping 2026-02-30 to the 28th would invent a retention the memory
    never stated."""
    assert derive(content) is None


def test_empty_and_non_string_content_is_refused():
    assert derive("") is None
    assert derive_stated_expiry(None, reference_time=NOW) is None  # type: ignore[arg-type]


def test_a_naive_reference_time_is_read_as_utc():
    """`created_at` arrives tz-aware from the database, but an in-process caller
    can pass a naive one; comparing naive to aware raises rather than refusing."""
    naive = NOW.replace(tzinfo=None)
    assert derive("This note is valid until 2026-12-31.", reference_time=naive) == (
        datetime(2027, 1, 1, tzinfo=timezone.utc)
    )


# ──────────────────────── the pipeline write path ────────────────────────


EXTRACTION = {
    "entities": [{"name": "ExpiryTool", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
    "summary": "",
    "emotions": [],
    "flags": [],
}


async def _expires_at(factory, memory_id):
    from sqlalchemy import text

    async with factory() as s:
        return (await s.execute(
            text("SELECT expires_at FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(memory_id)},
        )).scalar_one()


@pytest.mark.asyncio
async def test_process_batch_fills_and_respects_expires_at(setup_database, monkeypatch):
    """The real Phase 5 savepoint A, against the real database.

    Three memories in one batch: one stating its own retention, one whose date
    is about something else, and one the caller already gave a TTL. The batch
    shape is the point — the derivation is per-memory, so a bug that read the
    batch's first content for every row would pass a single-memory test.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services.pipeline import _flag_cache_reset
    from tests.conftest import test_engine
    from tests.test_pipeline_phase1 import FakeEmbedder, cleanup, make_pipeline, seed_memories

    fingerprint = "stated-expiry|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()

    contents = [
        "This note is valid until 2026-12-31.",
        "The TLS certificate is valid until 2026-12-31, so renew it.",
        "This note is valid until 2026-12-31.",
    ]
    memory_ids = await seed_memories(factory, contents)

    chosen = datetime(2099, 1, 1, tzinfo=timezone.utc)
    async with factory() as s:
        await s.execute(
            text("UPDATE memories SET expires_at = CAST(:at AS timestamptz) "
                 "WHERE id = CAST(:id AS uuid)"),
            {"at": chosen, "id": str(memory_ids[2])},
        )
        await s.commit()

    try:
        pipe = make_pipeline(factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch)
        await pipe.process_batch([
            {"memory_id": mid, "content": c, "source": "api"}
            for mid, c in zip(memory_ids, contents)
        ])

        # Stated its own retention: derived, end-exclusive.
        assert await _expires_at(factory, memory_ids[0]) == datetime(
            2027, 1, 1, tzinfo=timezone.utc
        )
        # Same date, but about a certificate: left alone, so the sweep never
        # deletes the note that recorded it.
        assert await _expires_at(factory, memory_ids[1]) is None
        # Caller's own TTL: untouched, not narrowed to the parsed one.
        assert await _expires_at(factory, memory_ids[2]) == chosen
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["ExpiryTool"])
