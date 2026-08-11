"""T3.04 — `article_citations`, the one hard FK (doc 09 §4.3).

Doc 09 makes this the deliberate inverse of the fact table's own endpoints:
`knowledge_triples.subject_id` / `object_id` are **soft** refs because the graph
deletes entities aggressively, while a citation's `fact_id` is a **hard** FK —
"safe *because* facts are invalidate-not-delete … so a citation can never
dangle, and it buys referential integrity at the one place a dangling citation
would be a truth catastrophe: a dead citation under a corroborated badge."

So the property under test is a conjunction, and both halves have to hold at
once: the FK is enforced *and* nothing in the tree ever hard-deletes a fact. A
suite that checked only the first would pass on a system that deletes facts and
takes their citations with them.

The third clause — "and the article marked stale" — was blocked on a doc 09
§4.4 contradiction and is covered here since the ruling landed (2026-08-11):
§4.4 named `invalidated` as a staleness trigger while its own hash predicate
carried `expired_at` alone, and invalidation sets `invalid_at` only. The
enumeration won, so the L3 supporting set is the verified *and still believed*
one.
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories.knowledge_triples import OPEN_BELIEF_PREDICATE
from app.services import article_eligibility, article_synthesis, articles_channel
from app.services.article_eligibility import SUPPORTING_BELIEF_PREDICATE

pytestmark = pytest.mark.asyncio

PROJECT = "t3-04-citations"
BACKEND = Path(__file__).resolve().parents[1]


async def _fact(session, *, project: str = PROJECT) -> str:
    fact_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_triples "
            "(id, subject_name, object_name, rel_type, reference_time, fact, "
            " triple_key, project, verification_status) "
            "VALUES (CAST(:id AS uuid), 's', 'o', 'RELATED_TO', now(), 'a fact', "
            "CAST(:id AS text), CAST(:p AS text), 'corroborated')"
        ),
        {"id": fact_id, "p": project},
    )
    await session.flush()
    return fact_id


async def _article(session, *, project: str = PROJECT) -> str:
    article_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_articles "
            "(id, subject_key, project, content, status, review_state) "
            "VALUES (CAST(:id AS uuid), CAST(:k AS text), CAST(:p AS text), "
            "'body', 'candidate', 'open')"
        ),
        {"id": article_id, "k": f"s{uuid4().hex[:6]}::concept", "p": project},
    )
    await session.flush()
    return article_id


async def _cite(session, article_id: str, fact_id: str) -> str:
    citation_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO article_citations (id, article_id, fact_id, claim_span) "
            "VALUES (CAST(:id AS uuid), CAST(:a AS uuid), CAST(:f AS uuid), "
            "int4range(0, 10))"
        ),
        {"id": citation_id, "a": article_id, "f": fact_id},
    )
    await session.flush()
    return citation_id


# ─────────────── the FK is enforced ───────────────


class TestTheHardFK:
    async def test_a_citation_cannot_name_a_fact_that_does_not_exist(self, session):
        """The property the hard FK buys, stated as the thing it refuses."""
        article_id = await _article(session)

        with pytest.raises(IntegrityError):
            await _cite(session, article_id, str(uuid4()))

    async def test_a_cited_fact_cannot_be_hard_deleted(self, session):
        """No `ON DELETE` clause, so the FK restricts. This is what makes "a
        dead citation under a corroborated badge" unreachable — the database
        refuses before any application code has to remember not to."""
        article_id = await _article(session)
        fact_id = await _fact(session)
        await _cite(session, article_id, fact_id)

        with pytest.raises(IntegrityError):
            await session.execute(
                text("DELETE FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
                {"id": fact_id},
            )

    async def test_deleting_the_article_takes_its_citations(self, session):
        """`article_id` cascades while `fact_id` restricts, and the asymmetry
        is the design: a citation belongs to its article and only *points* at
        its fact."""
        article_id = await _article(session)
        fact_id = await _fact(session)
        await _cite(session, article_id, fact_id)

        await session.execute(
            text("DELETE FROM knowledge_articles WHERE id = CAST(:id AS uuid)"),
            {"id": article_id},
        )
        await session.flush()

        remaining = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM article_citations "
                    "WHERE article_id = CAST(:a AS uuid)"
                ),
                {"a": article_id},
            )
        ).scalar_one()
        assert remaining == 0
        # …and the fact it pointed at is untouched.
        assert (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM knowledge_triples WHERE id = CAST(:f AS uuid)"
                ),
                {"f": fact_id},
            )
        ).scalar_one() == 1


# ─────────────── invalidate-not-delete, which is what makes it safe ────────


class TestInvalidateNotDelete:
    async def test_an_invalidated_fact_leaves_its_citation_intact(self, session):
        """Doc 09's premise, asserted rather than assumed: the hard FK is safe
        *because* a fact is never deleted, only window-closed."""
        article_id = await _article(session)
        fact_id = await _fact(session)
        citation_id = await _cite(session, article_id, fact_id)

        await session.execute(
            text(
                "UPDATE knowledge_triples SET invalid_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        row = (
            await session.execute(
                text(
                    "SELECT c.fact_id, t.invalid_at FROM article_citations c "
                    "JOIN knowledge_triples t ON t.id = c.fact_id "
                    "WHERE c.id = CAST(:id AS uuid)"
                ),
                {"id": citation_id},
            )
        ).mappings().one()
        assert str(row["fact_id"]) == fact_id
        assert row["invalid_at"] is not None

    async def test_an_expired_fact_also_keeps_its_citation(self, session):
        """The other half of the belief window. `expired_at` is the T2.101 fold's
        spelling and `invalid_at` the window-close; neither deletes a row."""
        article_id = await _article(session)
        fact_id = await _fact(session)
        await _cite(session, article_id, fact_id)

        await session.execute(
            text(
                "UPDATE knowledge_triples SET expired_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        assert (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM article_citations "
                    "WHERE fact_id = CAST(:f AS uuid)"
                ),
                {"f": fact_id},
            )
        ).scalar_one() == 1


# ─────────────── …and the article marked stale (doc 09 §4.4, as ruled) ─────


async def _subject_hash(session, *, subject: str = "s", project: str = PROJECT) -> str:
    return article_synthesis.fact_set_hash(
        await article_synthesis.all_verified_fact_ids(
            session, subject=subject, project=project
        )
    )


class TestStalenessOnInvalidation:
    async def test_invalidating_a_cited_fact_moves_the_subjects_hash(self, session):
        """T3.04's third clause, and the whole reason the ruling was needed.

        Under §4.4's pre-amendment predicate this assertion failed: invalidation
        touches neither `verification_status` nor `expired_at`, so the hash sat
        still and the article was never labelled stale — a trigger the doc
        enumerated that its own predicate could not fire.
        """
        article_id = await _article(session)
        fact_id = await _fact(session)
        await _cite(session, article_id, fact_id)
        before = await _subject_hash(session)

        await session.execute(
            text(
                "UPDATE knowledge_triples SET invalid_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        assert await _subject_hash(session) != before
        # The conjunction, not two separate properties: the article goes stale
        # *while* the citation survives. A design that deleted the fact would
        # also move the hash, and would be the failure this FK exists to refuse.
        assert (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM article_citations "
                    "WHERE fact_id = CAST(:f AS uuid)"
                ),
                {"f": fact_id},
            )
        ).scalar_one() == 1

    async def test_the_write_and_read_bases_are_one_predicate(self):
        """Two spellings would make every article read stale from birth.

        The statuses half is already pinned in `test_article_synthesis`; this is
        the belief half, and it is the one that just moved.
        """
        sql = [
            str(article_synthesis._ALL_VERIFIED_IDS_SQL),
            str(articles_channel._LIVE_HASHES_SQL),
            str(article_synthesis._FACTS_SQL),
            str(article_eligibility._CANDIDATES_SQL),
        ]
        assert all(SUPPORTING_BELIEF_PREDICATE in q for q in sql)

    async def test_no_L3_query_keeps_the_old_narrower_basis(self):
        """The four were found by reading; a fifth would be found by this.

        Scanned line-wise rather than by parsing SQL: the failure mode of the
        old basis is not an error but a hash that sits still, which no runtime
        check can see.
        """
        offenders: list[str] = []
        for mod in (article_eligibility, article_synthesis, articles_channel):
            path = Path(mod.__file__)
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if "expired_at IS NULL" in line and "invalid_at IS NULL" not in line:
                    offenders.append(f"{path.name}:{lineno}")

        assert offenders == [], (
            "an L3 query carries the belief window's expiry half alone. Doc 09 "
            "§4.4 as amended makes the supporting set verified *and believed*, "
            f"and a half-applied basis goes stale on nothing: {offenders}"
        )

    async def test_the_basis_is_the_repos_canonical_belief_window(self):
        """Derived by hand rather than by string surgery, so a new column on the
        canonical predicate fails here instead of quietly leaving L3 behind."""
        canonical = {c.strip() for c in OPEN_BELIEF_PREDICATE.split(" AND ")}
        mine = {
            c.strip().removeprefix("t.")
            for c in SUPPORTING_BELIEF_PREDICATE.split(" AND ")
        }
        assert mine == canonical


# ─────────────── a hard delete is impossible, in the tree as well ──────────


async def test_no_module_under_app_hard_deletes_a_fact():
    """The FK restricts, but a restriction only fires when something tries.

    Doc 09's safety argument is that facts are invalidate-not-delete, and that
    is a property of the *code* as much as of the constraint: a delete path
    would turn every citation into an `IntegrityError` at runtime rather than a
    caught design error. So the tree is scanned, not just the schema.

    The scan is textual and deliberately broad — it would flag a commented-out
    delete too — because the alternative (an AST walk over SQL strings) reads
    fewer shapes, and a false positive here costs one line of triage while a
    false negative costs the invariant.
    """
    offenders: list[str] = []
    for path in sorted((BACKEND / "app").rglob("*.py")):
        rel = str(path.relative_to(BACKEND)).replace("\\", "/")
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = " ".join(line.split()).lower()
            if "delete from knowledge_triples" in stripped:
                offenders.append(f"{rel}:{lineno}")

    assert offenders == [], (
        "facts are invalidate-not-delete, and `article_citations.fact_id` takes "
        "a hard FK on that premise — a delete path here makes a dangling "
        "citation reachable, which doc 09 calls a truth catastrophe: a dead "
        f"citation under a corroborated badge. Offenders: {offenders}"
    )


async def test_the_repository_exposes_no_delete_method():
    """The scan above reads SQL; this reads the API.

    `KnowledgeTripleRepository` is the one writer, so a `delete`/`remove`
    method on it would be the sanctioned route a future caller reaches for
    even if it spells its SQL differently.
    """
    source = (BACKEND / "app/repositories/knowledge_triples.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    repo = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "KnowledgeTripleRepository"
    )
    names = {
        n.name
        for n in repo.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    forbidden = {n for n in names if "delete" in n or "purge" in n or "remove" in n}
    assert forbidden == set(), (
        f"the fact repository exposes a delete-shaped method: {sorted(forbidden)}. "
        "Facts are window-closed (`close_window`) or expired, never deleted."
    )
