"""honesty/human-only-confirmed — no machine path reaches ``confirmed``.

The machine's ceiling is ``corroborated``; ``confirmed`` is the human's floor
above it (doc 08 §4.4). That is the under-claiming preference made structural
rather than declared, and it is worth a tree-wide assertion because the failure
it guards is silent: a badge reading "human-ratified" over a fact no person
ever saw looks exactly like one that earned it.

Two arms, because the property has two halves that fail independently:

- **Behavioural.** The ladder is driven to its own ceiling with an
  overwhelming pile of agreement and never crosses. Asserting this through the
  real applier is what makes it a claim about the shipped promotion path rather
  than about a constant.
- **Structural.** A closed, listed set of scopes in the tree writes
  ``verification_status`` at all, and each one's own guarantee is what makes
  the set safe: one refuses ``confirmed`` outright, one cannot execute without
  a ``human``-kind ``fact_sources`` row, one validates its rung against the
  machine-writable set. A source scan holds the "exactly these" half, because a
  writer added later would pass every behavioural test in this file — it would
  simply be a path this file never drove.

  *An entry on that list costs a behavioural pin, checked rather than argued.*
  The third writer was admitted on the sentence "it binds a module constant",
  and a review showed what that sentence is worth: mutating the constant to
  ``confirmed`` left this whole file green while the writer minted
  machine-``confirmed`` facts. Binding a constant says nothing about the
  constant's value, so the allowlist below now maps each writer to the test
  here that drives it and asserts what landed.

  *The scan asks which scopes write the column at all, rather than which
  mention the literal.* The narrower question was the first version and a Fable
  review defeated it with six of seven realistic writer shapes — most sharply,
  assignment through the exported ``CONFIRMED`` constant, which the literal
  fast-path skipped entirely. Ignoring the value cannot be dodged by disguising
  the value.
"""
from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import (
    CONFIRMED,
    HUMAN_SOURCE_KIND,
    HumanSourceRequired,
    KnowledgeTripleRepository,
)
from app.services.verification_ladder import recompute_fact

PROJECT = "honesty-human-only-confirmed"
REFERENCE = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
CORROBORATIONS = 25

_BACKEND = Path(__file__).resolve().parents[2]
_APP = _BACKEND / "app"

# The scopes permitted to write the verification axis at all, mapped to the
# test **in this file** that drives each one and asserts it cannot land the
# human's floor. The mapping is the admission rule, and it is checked below
# rather than left to review.
#
# The argument the previous version of this comment made for the third
# entry — that it "binds a module constant rather than a parameter, so the
# rung it writes cannot be anything else" — does not generalise, and a review
# demonstrated it: mutating that constant to `confirmed` left all 21 tests here
# green while the writer minted machine-`confirmed` facts. Binding a constant
# says nothing about the constant's *value*. So each writer now needs two
# things, and neither is prose:
#
#   * a guarantee in the code — `set_verification_status` refuses `confirmed`
#     outright, `ratify` cannot execute without a `human`-kind source row, and
#     `_write_born_rung` validates its rung against the machine-writable set
#     before the statement runs;
#   * a behavioural pin here, named below, that drives the writer and asserts
#     what landed. A fourth writer inherits neither and must bring both.
#
# `_write_born_rung` is doc 10 §6's parse-is-the-verification exception (T2.28)
# and is the single statement that puts a fact on that rung, whether it is
# being born there or restored to it after a lapsed dispute; `test_deriver_lift`
# pins the callers of both its doors.
_PERMITTED_WRITERS = {
    "app/repositories/knowledge_triples.py::KnowledgeTripleRepository._write_born_rung":
        "test_the_born_rung_writer_cannot_land_the_human_floor",
    "app/repositories/knowledge_triples.py::KnowledgeTripleRepository.ratify":
        "test_the_human_door_itself_refuses_without_a_human_source",
    "app/repositories/knowledge_triples.py::KnowledgeTripleRepository.set_verification_status":
        "test_the_machine_writer_refuses_the_literal",
}


async def _fact(session, *, subject: str, obj: str) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"honesty-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type="USES",
        fact=f"{subject} uses {obj}",
        reference_time=REFERENCE,
        project=PROJECT,
    )
    await session.flush()
    return row["id"]


async def _assert_origin(session, fact_id: str, origin_key: str) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref=f"memory:{origin_key}",
        origin_key=origin_key,
    )
    await session.flush()


async def _status(session, fact_id: str) -> str:
    result = await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return result.scalar_one()


# ─────────────────────────── the behavioural arm ───────────────────────────


@pytest.mark.asyncio
async def test_the_ladder_stops_at_corroborated_however_much_agrees(session):
    """Twenty-five independent origins, diverse enough to fire the loose gate,
    nothing contradicting: the strongest case the machine can build. It reaches
    corroborated and stops."""
    fact_id = await _fact(session, subject="darkmem", obj="pgvector")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    await recompute_fact(session, fact_id)
    await session.flush()

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_repeated_recomputes_never_drift_upward(session):
    """A ceiling that holds once but creeps on re-entry is the same defect
    arriving later — the recompute runs every two minutes in production."""
    fact_id = await _fact(session, subject="darkmem", obj="asyncpg")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    for _ in range(3):
        await recompute_fact(session, fact_id)
        await session.flush()
        assert await _status(session, fact_id) != CONFIRMED

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_the_machine_writer_refuses_the_literal(session):
    fact_id = await _fact(session, subject="darkmem", obj="fastapi")
    with pytest.raises(ValueError, match="only a human may ratify"):
        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, CONFIRMED
        )
    assert await _status(session, fact_id) == "candidate"


@pytest.mark.asyncio
async def test_the_human_door_itself_refuses_without_a_human_source(session):
    """The one permitted writer is not a bypass: it is refused too when the
    provenance that entitles the fact to be confirmed does not exist. Nothing
    in the tree can reach the literal on machine evidence alone."""
    fact_id = await _fact(session, subject="darkmem", obj="alembic")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")
    await recompute_fact(session, fact_id)
    await session.flush()
    assert await _status(session, fact_id) == "corroborated"

    with pytest.raises(HumanSourceRequired):
        await KnowledgeTripleRepository(session).ratify(fact_id)

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_the_born_rung_writer_cannot_land_the_human_floor(session):
    """The third writer's own pin, and the one this file was missing.

    The scan below sees *that* this writer touches the axis, never which value
    it writes; the writer re-reads what landed, but against the same constant,
    so it cannot catch that constant drifting. Both routes onto the rung are
    driven here and the landed status is compared against ``CONFIRMED`` —
    a different constant, which is what makes the comparison able to fail.
    """
    repo = KnowledgeTripleRepository(session)
    born = await repo.open_born_corroborated(
        triple_key=f"honesty-{uuid4()}",
        subject_name="darkmem",
        object_name="httpx",
        rel_type="DEPENDS_ON",
        fact="darkmem depends on httpx",
        reference_time=REFERENCE,
        project=PROJECT,
    )
    await session.flush()
    assert born["verification_status"] != CONFIRMED
    assert await _status(session, born["id"]) != CONFIRMED

    demoted = await _fact(session, subject="darkmem", obj="uvicorn")
    assert await repo.restore_born_corroborated(demoted) is True
    await session.flush()
    assert await _status(session, demoted) != CONFIRMED


@pytest.mark.asyncio
async def test_a_human_source_written_by_hand_is_not_a_machine_path(session):
    """Stated rather than left implicit: any code that writes a ``human`` row
    can then confirm the fact. That is not a hole in the guard — it is what
    "the ratification IS the source row" means, and the row's identity is what
    the audit reads. The guard's job is that no path reaches ``confirmed``
    *without leaving that record*, and this asserts the record is required and
    attributable, not that impersonation is impossible."""
    fact_id = await _fact(session, subject="darkmem", obj="pydantic")
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=HUMAN_SOURCE_KIND,
        source_ref="human:admin",
        origin_key="human:admin",
        detail={"ratified_by": "admin"},
    )
    await session.flush()

    await KnowledgeTripleRepository(session).ratify(fact_id)
    await session.flush()

    assert await _status(session, fact_id) == CONFIRMED
    rows = (await session.execute(
        text(
            "SELECT detail FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
            "AND source_kind = CAST(:kind AS text)"
        ),
        {"id": str(fact_id), "kind": HUMAN_SOURCE_KIND},
    )).scalars().all()
    assert rows and rows[0]["ratified_by"] == "admin"


# ─────────────────────────── the structural arm ───────────────────────────


_COLUMN = "verification_status"

# The column bound by a single `=`, with the value deliberately unexamined.
# Whitespace is normalised first so a statement split across lines reads as one.
_SQL_BINDING = re.compile(rf"{_COLUMN}\s*=\s*(?!=)", re.IGNORECASE)


def _sql_assigns_column(text: str) -> bool:
    """Whether a SQL fragment *writes* the column, as opposed to filtering on it.

    SQL spells equality with a single `=`, so `WHERE verification_status =
    'confirmed'` and `SET verification_status = 'confirmed'` are one character
    apart and mean opposite things. The clause the binding sits in decides.

    The fragment is often not a whole statement: the shipped writer builds its
    SET list separately (`"verification_status = CAST(:status AS text)"`) and
    interpolates it into the `UPDATE ... SET {…}` later, so a rule that
    *required* a visible `SET` would miss the one real writer in the tree. A
    bare binding with no clause keyword at all therefore counts as a write —
    error direction chosen so an unrecognised shape lands on the allowlist for
    a human to look at, rather than passing silently.
    """
    normalised = " ".join(text.split())
    for match in _SQL_BINDING.finditer(normalised):
        prefix = f" {normalised[:match.start()].lower()} "
        if prefix.rfind(" where ") > prefix.rfind(" set "):
            continue  # a filter, not an assignment
        return True
    return False


def _confirmed_writers(root: Path) -> list[str]:
    """Every scope under ``root`` that writes ``verification_status`` **at all**.

    *(Rewritten after the Fable review, which defeated the previous version
    with six of seven realistic second-writer shapes.)*

    The old scan looked for the literal ``'confirmed'`` on the same line as the
    column, and was evaded by: a multi-line SQL statement (the literal lands on
    the line after the ``=``), assignment through the exported ``CONFIRMED``
    constant, a bound parameter named anything other than ``:confirmed``,
    ``setattr``, module-level code, and an f-string. The first of those is the
    worst, because ``knowledge_triples`` *exports* ``CONFIRMED`` — so the most
    idiomatic future writer was precisely the invisible one, and the self-test
    that proved the guard "could fail" planted the single shape inside its own
    blind spot.

    So the predicate no longer reasons about the *value*. It answers a
    stronger, simpler question — **which scopes write this column at all** —
    which cannot be dodged by disguising the value, and which is the property
    actually worth holding: two functions may write the axis, one of them
    refuses ``confirmed`` outright and the other demands a human source row.

    Three write shapes are recognised, all AST-based:

    * a string constant (including f-strings and implicit concatenation) whose
      normalised text assigns the column — the raw-SQL path;
    * an attribute assignment ``obj.verification_status = ...`` — the ORM path;
    * ``setattr(obj, "verification_status", ...)`` — the dynamic path.

    Scope is the enclosing function's qualname, ``Class.<class>`` for a class
    body, or ``<module>`` for top-level code — the last two both being holes
    found after this rewrite began.

    **What this still cannot see, stated rather than implied.** Ignoring the
    value closes value-disguise, but the guard can still be dodged by
    disguising the *column reference*: a name built at runtime
    (``f"{col} = :v"``, the house dynamic-builder shape), ``.format()`` or
    ``%``-interpolation of the column name, ``+``-concatenation split across
    the column name itself (which also defeats the file fast-path),
    ``object.__setattr__``, or ``row.__dict__[...]``. No static scan closes
    that class. The behavioural arm above is what covers it: whatever route a
    writer takes, it still has to get past a database that only two statements
    in this tree address, and past ``set_verification_status``'s refusal.
    """
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        # No fast-path on the literal: the whole point is that a writer need
        # never mention it. Only the column name can be relied on.
        if _COLUMN not in source:
            continue
        try:
            rel = path.relative_to(_BACKEND).as_posix()
        except ValueError:
            # The self-tests below drive this scan over a tmp_path tree, which
            # is not under the backend root.
            rel = path.name
        tree = ast.parse(source, filename=str(path))
        for scope, qualname in _scopes(tree):
            if _writes_column(scope):
                offenders.append(f"{rel}::{qualname}")
    return sorted(set(offenders))


_NESTING = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _scopes(tree: ast.Module):
    """Every function, every class body, and the module's own top level.

    Each scope is yielded with its *nested* scopes removed, so a statement is
    attributed to exactly one place and none is scanned twice.

    Class bodies are a scope in their own right, and their omission was a real
    hole: the first version of this walk collected only functions out of a
    ``ClassDef``, so ``class Q: SQL = "UPDATE ... SET verification_status =
    'confirmed'"`` — the naive single-line literal, no disguise at all — was
    attributed nowhere and passed. Class-level SQL template constants are one
    step from the module-level ones this tree already keeps.

    A nested ``def`` or ``class`` is removed from its parent's body, **but its
    signature is not**. Decorators, argument defaults and annotations are
    written inside the nested definition and *evaluated in the enclosing
    scope*, so dropping the whole node left them in no scope at all — a
    zero-disguise literal as a default argument or in a decorator call passed
    the scan. That was a regression introduced while fixing double-attribution:
    the earlier walk yielded whole ``FunctionDef`` nodes and caught them by
    accident. ``_shell`` puts them back where they execute.
    """
    def shell(node: ast.AST) -> list:
        """The parts of a nested definition that run in the enclosing scope."""
        parts: list = list(node.decorator_list)
        if isinstance(node, ast.ClassDef):
            parts += list(node.bases) + [kw.value for kw in node.keywords]
            return parts
        args = node.args
        parts += [d for d in args.defaults if d is not None]
        parts += [d for d in args.kw_defaults if d is not None]
        if node.returns is not None:
            parts.append(node.returns)
        every = (
            list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            + [a for a in (args.vararg, args.kwarg) if a is not None]
        )
        parts += [a.annotation for a in every if a.annotation is not None]
        return parts

    def body_only(body: list) -> list:
        own = [n for n in body if not isinstance(n, _NESTING)]
        for nested in (n for n in body if isinstance(n, _NESTING)):
            own.extend(shell(nested))
        return own

    def walk(node: ast.AST, prefix: str):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield body_only(child.body), f"{prefix}{child.name}"
                yield from walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.ClassDef):
                yield body_only(child.body), f"{prefix}{child.name}.<class>"
                yield from walk(child, f"{prefix}{child.name}.")

    yield from walk(tree, "")
    yield body_only(tree.body), "<module>"


def _writes_column(scope: list) -> bool:
    nodes = [n for root in scope for n in ast.walk(root)]
    # A bare string *statement* is a docstring or a stray literal, never a
    # statement anything executes. Both `facts_read` and `review_queue`
    # describe the column in their module docstrings, and reading prose as SQL
    # is how a guard earns a reputation for crying wolf.
    prose = {
        id(node.value)
        for node in nodes
        if isinstance(node, ast.Expr)
        and isinstance(node.value, (ast.Constant, ast.JoinedStr))
    }
    for node in nodes:
        # Raw SQL, in any string form.
        if isinstance(node, (ast.Constant, ast.JoinedStr)) and id(node) not in prose:
            text = _static_text(node)
            if text and _sql_assigns_column(text):
                return True
        # ORM attribute assignment.
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == _COLUMN:
                    return True
        # Dynamic assignment.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "setattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == _COLUMN
        ):
            return True
        # SQLAlchemy expression language: `update(...).values(column=...)` or
        # `.values({"column": ...})`. This is live idiom in the tree
        # (`relational.py`, `config.py`), so it was the most idiomatic future
        # writer the first version of this scan could not see — the same
        # criticism that produced this rewrite, recurring at smaller radius.
        #
        # Matched only inside a `.values(...)` call, never on a bare keyword:
        # roughly ten DTO constructions pass `verification_status=` as a
        # constructor kwarg (`layer_composition`, `facts_read`, `fact_badge`),
        # and flagging those would make the guard useless within a week.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "values"
        ):
            if any(kw.arg == _COLUMN for kw in node.keywords):
                return True
            # A literal dict, passed positionally or splatted with `**`. The
            # splat is purely syntactic so it costs three lines; a dict built
            # by a name, a comprehension or `dict(...)` needs data flow and is
            # named in the honest-limits paragraph instead.
            dicts = [a for a in node.args if isinstance(a, ast.Dict)]
            dicts += [
                kw.value for kw in node.keywords
                if kw.arg is None and isinstance(kw.value, ast.Dict)
            ]
            for literal in dicts:
                if any(
                    isinstance(key, ast.Constant) and key.value == _COLUMN
                    for key in literal.keys
                ):
                    return True
    return False


def _static_text(node: ast.AST) -> str:
    """The statically-known text of a string node, f-strings included.

    An f-string's interpolations are replaced by a placeholder rather than
    dropped, so ``f"SET verification_status = {value}"`` still reads as an
    assignment.
    """
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("?")
        return "".join(parts)
    return ""


def test_exactly_the_permitted_writers_touch_the_verification_axis():
    writers = _confirmed_writers(_APP)
    assert writers == sorted(_PERMITTED_WRITERS), (
        f"expected exactly {sorted(_PERMITTED_WRITERS)} to write "
        f"{_COLUMN!r}, found {writers}. A second path to the human's floor is "
        f"the forged-ratification failure this spec exists to refuse: it would "
        f"pass every behavioural test above simply by never being driven. Each "
        f"permitted writer carries a guarantee in the code and a behavioural "
        f"pin in this file; a new writer inherits neither and must bring both."
    )


def test_every_permitted_writer_is_pinned_by_a_test_in_this_file():
    """The admission rule, executable rather than argued in the comment above.

    A writer earns its place on the allowlist by being *driven* here and having
    what it landed asserted — because the scan is value-blind by design, and an
    allowlist entry whose whole guarantee is a sentence is how a writer that
    mints ``confirmed`` sits in plain sight and passes. That is exactly what a
    review found: the third entry's guarantee was a comment, and mutating the
    constant it binds left this whole file green.

    What this cannot check is that the named test asserts the *right* thing —
    no rule can. What it does is force the pin to exist, to live beside the
    property, and to be reviewed here rather than in whatever file the writer's
    own feature tests happen to be in.
    """
    missing = {
        writer: pin
        for writer, pin in _PERMITTED_WRITERS.items()
        if pin not in globals() or not callable(globals()[pin])
    }
    assert not missing, (
        f"allowlisted writer(s) name a behavioural pin that does not exist in "
        f"this module: {missing}. The pin is the admission price."
    )


# Each of these defeated the previous line-oriented scan. They are the
# regression suite for the guard itself, not for the feature.
_EVASIONS: dict[str, str] = {
    "multiline_sql": (
        "async def promote(session):\n"
        "    await session.execute(\n"
        "        \"UPDATE knowledge_triples SET verification_status =\\n\"\n"
        "        \"        'confirmed'\"\n"
        "    )\n"
    ),
    "via_constant": (
        "from app.repositories.knowledge_triples import CONFIRMED\n"
        "async def promote(session, row):\n"
        "    row.verification_status = CONFIRMED\n"
    ),
    "renamed_bound_param": (
        "async def promote(session, value):\n"
        "    await session.execute(\n"
        "        \"UPDATE knowledge_triples SET verification_status = CAST(:v AS text)\",\n"
        "        {\"v\": value},\n"
        "    )\n"
    ),
    "setattr": (
        "def promote(row, value):\n"
        "    setattr(row, 'verification_status', value)\n"
    ),
    "module_level": (
        "import sqlalchemy\n"
        "STMT = sqlalchemy.text(\n"
        "    \"UPDATE knowledge_triples SET verification_status = 'confirmed'\"\n"
        ")\n"
    ),
    "fstring": (
        "STATUS = 'confirmed'\n"
        "def promote(session):\n"
        "    return f\"UPDATE knowledge_triples SET verification_status = '{STATUS}'\"\n"
    ),
    # ── Found by the scoped re-review of this very fix. Both are the same
    # criticism recurring at smaller radius: the guard's own self-tests again
    # contained only shapes the guard already caught.
    "class_body": (
        "class Promoter:\n"
        "    SQL = \"UPDATE knowledge_triples SET verification_status = 'confirmed'\"\n"
    ),
    "sqlalchemy_values_kwarg": (
        "from sqlalchemy import update\n"
        "def promote(session, table):\n"
        "    return update(table).values(verification_status='confirmed')\n"
    ),
    "sqlalchemy_values_dict": (
        "from sqlalchemy import update\n"
        "def promote(session, table):\n"
        "    return update(table).values({'verification_status': 'confirmed'})\n"
    ),
    # ── Found by the round-2 re-review: a regression introduced while fixing
    # double-attribution. A nested def's decorators, argument defaults and
    # annotations are written inside the definition but *evaluated in the
    # enclosing scope*, so dropping the whole node left them unscanned. Each of
    # these is a zero-disguise literal in a syntactic slot the walk had lost.
    "default_argument": (
        "def promote(sql=\"UPDATE knowledge_triples SET verification_status = 'confirmed'\"):\n"
        "    return sql\n"
    ),
    "decorator_call": (
        "import functools\n"
        "@functools.lru_cache(\"UPDATE knowledge_triples SET verification_status = 'confirmed'\")\n"
        "def promote():\n"
        "    return None\n"
    ),
    "return_annotation": (
        "def promote() -> \"UPDATE knowledge_triples SET verification_status = 'confirmed'\":\n"
        "    return None\n"
    ),
    "lambda_default": (
        "def promote(f=lambda row: setattr(row, 'verification_status', 'confirmed')):\n"
        "    return f\n"
    ),
    "values_splatted_literal": (
        "from sqlalchemy import update\n"
        "def promote(table):\n"
        "    return update(table).values(**{'verification_status': 'confirmed'})\n"
    ),
}

# Where each shape must be attributed. The previous suite asserted only that
# *something* was flagged, so misattributing every class body to `<module>`
# passed all sixteen tests — and scope-coverage bugs are this guard's recurring
# failure mode (both the class-body hole and the dropped-signature regression
# were exactly that).
_EVASION_SCOPES: dict[str, str] = {
    "multiline_sql": "::promote",
    "via_constant": "::promote",
    "renamed_bound_param": "::promote",
    "setattr": "::promote",
    "module_level": "::<module>",
    "fstring": "::promote",
    "class_body": "::Promoter.<class>",
    "sqlalchemy_values_kwarg": "::promote",
    "sqlalchemy_values_dict": "::promote",
    "default_argument": "::<module>",
    "decorator_call": "::<module>",
    "return_annotation": "::<module>",
    "lambda_default": "::<module>",
    "values_splatted_literal": "::promote",
}


@pytest.mark.parametrize("shape", sorted(_EVASIONS))
def test_the_scan_catches_every_shape_that_defeated_it(tmp_path, shape):
    """A guard that cannot fail is not a guard — and the previous version's
    self-test planted the one shape inside its own blind spot, so it read as
    proof while five realistic writers walked past. Each of these was verified
    to evade the old scan."""
    offender = tmp_path / f"{shape}.py"
    offender.write_text(_EVASIONS[shape], encoding="utf-8")
    found = _confirmed_writers(tmp_path)
    assert found, f"{shape} evaded the scan"
    expected = _EVASION_SCOPES[shape]
    assert any(name.endswith(expected) for name in found), (
        f"{shape} was caught, but attributed to {found} rather than a scope "
        f"ending {expected!r}. Catching a writer in the wrong scope is how a "
        f"coverage hole hides: the count stays right while a whole syntactic "
        f"region goes unscanned."
    )


def test_the_scan_ignores_reads_of_the_literal(tmp_path):
    """The tree is full of legitimate mentions — the ladder holds a confirmed
    fact, the recompute excludes it from its slice. A scan that flagged those
    would be turned off within a week."""
    reader = tmp_path / "reads.py"
    reader.write_text(
        "def hold(row):\n"
        "    if row.verification_status == 'confirmed':\n"
        "        return 'hold'\n"
        "    if row.verification_status != 'confirmed':\n"
        "        return 'move'\n"
        "    return None\n"
        "\n"
        "READABLE = ('candidate', 'corroborated', 'confirmed')\n"
        "SELECT = 'SELECT verification_status FROM knowledge_triples'\n"
        "WHERE = \"SELECT 1 FROM knowledge_triples WHERE verification_status = 'confirmed'\"\n",
        encoding="utf-8",
    )
    assert _confirmed_writers(tmp_path) == []
