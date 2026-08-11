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
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

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
