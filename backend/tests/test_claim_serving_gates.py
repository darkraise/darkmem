"""Evidence records gate the label, never the code (T2.95).

This is the load-bearing task of the M1 split. Implementation is allowed to run
arbitrarily far ahead of measurement *because* no code path can serve a claim
whose evidence does not exist — if that is wrong, running ahead stops being
safe, and everything built before M1 is shipping unbacked assertions.

Two properties carry it. **Suppression must be total** — no serving path may
reach a promoted status without the record. And **suppression must be
visible** — a withheld label and a genuinely-`candidate` one must not read
alike, or a missing measurement silently becomes an apparent property of the
corpus: the reader concludes the data is unverified when the truth is that the
*verifier* is unmeasured.

**The first round of this task asserted both properties at the producer and
neither held at a door.** The 2026-08-06 review measured a raw `corroborated`
on chat and on the review queue, the withheld rung readable off the composed
row's `tier`, the suppression marker dropped by every wire schema, and a new
module emitting a promoted literal leaving the whole scan suite green. So the
tests here are organised around where each property has to hold rather than
around the module that implements it: unit on the gate, **wire** on the
marker, **doors** on the suppression, and a scan that quantifies over `app/`
instead of naming the files it already knows about.

Note which tests may take `cleared_promotion_record` and which may not: a test
about the gate that opens the gate asserts nothing. Every door drive below
runs **unfixtured**, which is the shape the review found missing.
"""

from __future__ import annotations

import ast
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

import app.services.facts_channel as facts_channel
import app.services.hybrid_search as hybrid_search
from app.api.mcp import server as mcp_server
from app.main import app as fastapi_app
from app.repositories import memory_communities as communities_repo
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import claim_gates
from app.services.chat import ChatService
from app.services.fact_badge import row_labels
from app.utils.ids import new_id

BACKEND = Path(__file__).resolve().parents[1]

PROJECT = "t295-gate"
QUERY = "pgbouncer connection pooling"
AT = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)

# The rung the review measured leaking, and the rung it is served as.
PROMOTED = "corroborated"
SUPPRESSED = "candidate"
# The verified rung that survives a closed gate: human-ratified, and never
# something G-C's automatic ladder certified.
RATIFIED = "confirmed"
SUPPRESSED_TIER = 2
PROMOTED_TIER = 3


@pytest.fixture
def cleared_record(tmp_path):
    path = tmp_path / "promotion_metrics_record.json"
    path.write_text(json.dumps({"gate_eligible": True, "promotion_rate": 0.4}))
    return path


# ── the gate itself ──────────────────────────────────────────────────


def test_no_record_closes_the_gate(tmp_path):
    gate = claim_gates.corroboration_gate(tmp_path / "absent.json")
    assert gate.open is False
    assert "verification_unmeasured" in gate.reason


def test_an_unreadable_record_fails_closed(tmp_path):
    """A parse error must not crash the read path *open*. Serving the label
    because the gate itself broke is the one failure that would make this
    module worse than useless."""
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json at all")
    assert claim_gates.corroboration_gate(corrupt).open is False


def test_an_interim_record_does_not_open_the_gate(tmp_path):
    """T2.26's own 0.8182 was branded INTERIM by its artifact and would read as
    a pass to anything checking only for presence."""
    interim = tmp_path / "interim.json"
    interim.write_text(json.dumps({"gate_eligible": False, "note": "rehearsal"}))
    assert claim_gates.corroboration_gate(interim).open is False


def test_a_cleared_record_opens_the_gate(cleared_record):
    assert claim_gates.corroboration_gate(cleared_record).open is True


@pytest.mark.parametrize("value", ["INTERIM", "false", "no", 1, 0.8182])
def test_a_truthy_non_boolean_eligibility_does_not_open_the_gate(tmp_path, value):
    """T2.95 review finding: `gate_eligible` was checked for truthiness, so a
    record branding itself `"INTERIM"` — or even the string `"false"` — opened
    the gate. Only the JSON boolean `true` may."""
    record = tmp_path / "branded.json"
    record.write_text(json.dumps({"gate_eligible": value}))
    assert claim_gates.corroboration_gate(record).open is False


def test_an_undecodable_record_fails_closed_without_crashing(tmp_path):
    """T2.95 review finding: invalid UTF-8 raises UnicodeDecodeError out of
    the file *read* rather than the JSON parse, and an uncaught one crashed
    the whole fact read path — candidate rows included — instead of treating
    the record as absent."""
    corrupt = tmp_path / "corrupt_bytes.json"
    corrupt.write_bytes(b'{"gate_eligible": true, "note": "\xff\xfe"}')
    assert claim_gates.corroboration_gate(corrupt).open is False


# ── what is gated, and what is deliberately not ──────────────────────


@pytest.mark.parametrize("status", sorted(claim_gates.PROMOTED_STATUSES))
def test_promoted_statuses_are_withheld_without_a_record(status):
    served, reason = claim_gates.served_status(status, id_kind="fact")
    assert served == SUPPRESSED
    assert reason is not None


@pytest.mark.parametrize("status", ["candidate", "disputed", None])
def test_unpromoted_statuses_pass_through_untouched(status):
    """`disputed` asserts a two-sided conflict, which is honest without a
    promotion record; gating it would withhold an honest statement."""
    served, reason = claim_gates.served_status(status, id_kind="fact")
    assert served == status
    assert reason is None


def test_a_human_ratification_is_never_suppressed():
    """`confirmed` is human-ratified: a person looked at the fact and said yes.
    G-C certifies the *automatic* ladder, so withholding a human's ratification
    because an automated ladder is unmeasured would suppress the one label that
    never depended on the ladder. This module's first version got it wrong."""
    served, reason = claim_gates.served_status("confirmed", id_kind="fact")
    assert served == "confirmed"
    assert reason is None


# ── the claim decides its own evidence (id_kind keying) ──────────────


def test_the_article_gate_is_closed_even_with_the_fact_record(monkeypatch, cleared_record):
    """Review finding, clause 2: a fact's promotion record must not light an
    article's label. Doc 08 §4.3 certifies the corroboration ladder with G-C's
    promotion audit and doc 09 §4.3 certifies an article with G-D's judge
    qualification; they are distinct records about distinct claims. Doc 09 §4.3
    also ships a grounded article as `status='corroborated'`, so an
    id_kind-blind gate would serve the article label the moment T2.40 minted
    the fact one — the wrong record releasing the wrong claim."""
    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)

    fact = row_labels(id_kind="fact", verification_status=PROMOTED)
    article = row_labels(id_kind="article", verification_status=PROMOTED)

    assert fact["verification_status"] == PROMOTED
    assert fact["label_suppressed"] is None
    assert article["verification_status"] == SUPPRESSED
    assert "groundedness_unmeasured" in article["label_suppressed"]


def test_the_article_gate_cannot_be_opened_by_any_record():
    """The judge owns the qualification record and a scan makes it the single
    door, so this module cannot ask the question that would release the label
    and refuses instead. Opening it is the judge's own door's to open when the
    article channel is built (T3.02 / T3.23)."""
    gate = claim_gates.groundedness_gate()
    assert gate.open is False
    assert "groundedness_unmeasured" in gate.reason


def test_an_unrecognised_claim_refuses_rather_than_serving():
    """A new labelled surface must fail loud, not ungated. A default `id_kind`
    would have to name one claim, and every caller that forgot to pass one
    would silently be gated against the other claim's evidence."""
    with pytest.raises(ValueError, match="no claim gate is defined"):
        claim_gates.served_status(PROMOTED, id_kind="memory")


def test_every_badge_bearing_kind_has_a_gate():
    """Doc 12's badge-bearing kinds and the gate's kinds are the same set. A
    kind that gained a badge without a gate would serve its promoted rung
    through `row_labels` with nothing checking any record."""
    from app.services.fact_badge import BADGE_BEARING_ID_KINDS

    assert set(claim_gates._GATE_BY_ID_KIND) == set(BADGE_BEARING_ID_KINDS)


# ── the producer applies it, so consumers cannot forget to ───────────


def test_the_badge_producer_withholds_the_promoted_label():
    labels = row_labels(id_kind="fact", verification_status=PROMOTED)
    assert labels["verification_status"] == SUPPRESSED
    assert labels["unverified"] is True
    assert labels["label_suppressed"] is not None


def test_a_withheld_status_carries_no_badge():
    """The badge sentence names the origin count and the absence of
    contradiction — precisely the claim under gate. Serving it beside a
    withheld status would leak the assertion the status withheld."""
    from app.services.fact_badge import Badge

    badge = Badge(
        verification_status=PROMOTED,
        origin_count=3,
        origin_kinds=("memory",),
        as_of=None,
        contradiction=False,
        human_ratified=False,
        stale=False,
        claim="asserted by 3 distinct origins of kinds [memory]",
    )
    labels = row_labels(id_kind="fact", verification_status=PROMOTED, badge=badge)
    assert labels["badge"] is None


def test_suppressed_is_distinguishable_from_genuinely_candidate():
    """The property that keeps a missing measurement from reading as a fact
    about the corpus."""
    withheld = row_labels(id_kind="fact", verification_status=PROMOTED)
    genuine = row_labels(id_kind="fact", verification_status=SUPPRESSED)
    assert withheld["verification_status"] == genuine["verification_status"]
    assert withheld["label_suppressed"] is not None
    assert genuine["label_suppressed"] is None


def test_minting_a_record_lights_the_label_with_no_code_change(monkeypatch, cleared_record):
    """The reversibility claim the M1 split rests on, proven with a fixture
    rather than asserted."""
    before = row_labels(id_kind="fact", verification_status=PROMOTED)
    assert before["verification_status"] == SUPPRESSED

    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)
    after = row_labels(id_kind="fact", verification_status=PROMOTED)

    assert after["verification_status"] == PROMOTED
    assert after["label_suppressed"] is None
    assert after["unverified"] is False


@pytest.mark.parametrize("rung", [PROMOTED, SUPPRESSED, "confirmed", "disputed"])
def test_the_filter_vocabulary_is_served_status_inverted(rung, tmp_path, cleared_record):
    """`raw_statuses_for_served` is the preimage of `served_status`, so a
    surface filtering on a served rung and a surface labelling with one cannot
    give two answers about the same row. Asserted as the round trip at both
    gate states rather than as a table, because a table is a second
    implementation."""
    for gate in (
        claim_gates.corroboration_gate(tmp_path / "absent.json"),
        claim_gates.corroboration_gate(cleared_record),
    ):
        preimage = claim_gates.raw_statuses_for_served(
            rung, id_kind=claim_gates.FACT_ID_KIND, gate=gate
        )
        for raw in preimage:
            served, _ = claim_gates.served_status(
                raw, id_kind=claim_gates.FACT_ID_KIND, gate=gate
            )
            assert served == rung
        for other in (PROMOTED, SUPPRESSED, "confirmed", "disputed"):
            served, _ = claim_gates.served_status(
                other, id_kind=claim_gates.FACT_ID_KIND, gate=gate
            )
            assert (other in preimage) is (served == rung)


def test_the_closed_gate_leaves_the_promoted_rung_unfilterable(tmp_path):
    """The empty set is the honest answer, not a missing filter: with the gate
    closed nothing is *served* as corroborated, so a filter on that rung must
    match no row rather than the rows whose label was withheld."""
    closed = claim_gates.corroboration_gate(tmp_path / "absent.json")
    assert (
        claim_gates.raw_statuses_for_served(
            PROMOTED, id_kind=claim_gates.FACT_ID_KIND, gate=closed
        )
        == frozenset()
    )
    assert claim_gates.raw_statuses_for_served(
        SUPPRESSED, id_kind=claim_gates.FACT_ID_KIND, gate=closed
    ) == frozenset({SUPPRESSED, PROMOTED})


# ── structural: no serving path may bypass the producer ──────────────
#
# The first round's scan named two filenames and matched one node shape, and
# the review measured what that buys: a third file was invisible to it, and
# the two bypasses that existed at the time — `chat.py` and `review_queue.py`
# — were not in its list. What follows quantifies over every `.py` under
# `app/`, routes and MCP included, and classifies each emission by where its
# value came from rather than by which file it is in.

CLAIM_LABEL_KEY = "verification_status"

# The gate's own two modules: `fact_badge` is doc 12's single producer of the
# label and `claim_gates` is the gate it applies. Naming these two is the
# property being asserted — everything else under `app/` is a consumer — which
# is why the set is pinned below rather than left to grow into a list of
# exceptions.
PRODUCER_RELPATHS = frozenset(
    {"app/services/fact_badge.py", "app/services/claim_gates.py"}
)

GROUNDED_LABEL = "grounded"

# The producer's and the gate's own entry points. A ``verification_status=``
# keyword handed to one of these is the raw rung going *into* the gate, which
# is the correct direction and the opposite of an emission — every serving path
# has to do it. Naming them is not the enumeration this scan exists to replace:
# they are the API the property is stated in terms of. The declarations are read
# off the gate module rather than spelled here, so the two cannot drift into
# different vocabularies (T2.100).
GATE_ENTRY_POINTS = frozenset(
    {"row_labels", "served_status"} | claim_gates.STATUS_DECLARATIONS
)

UNSERVED = claim_gates.unserved_status.__name__
JOURNALLED = claim_gates.journalled_status.__name__


def _calls(node: ast.AST, name: str) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == name
    return isinstance(func, ast.Attribute) and func.attr == name


def _labels_bindings(tree: ast.AST) -> set[str]:
    """Names this module binds directly from a ``row_labels(...)`` call."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _calls(node.value, "row_labels"):
            bound |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return bound


def _reads_a_labels_mapping(node: ast.AST, bound: set[str]) -> bool:
    """``<labels>["verification_status"]`` / ``<labels>.get(...)``.

    The key is not that the expression *mentions* the label — the two leaks
    the review measured both did — but that the mapping it reads out of is one
    the producer built.
    """
    if isinstance(node, ast.Subscript):
        if not (
            isinstance(node.slice, ast.Constant) and node.slice.value == CLAIM_LABEL_KEY
        ):
            return False
        source = node.value
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
    ):
        if not (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == CLAIM_LABEL_KEY
        ):
            return False
        source = node.func.value
    else:
        return False

    if _calls(source, "row_labels"):
        return True
    if isinstance(source, ast.Name):
        return source.id in bound or source.id.endswith("labels")
    if isinstance(source, ast.Attribute):
        return source.attr.endswith("labels")
    return False


def _emissions(tree: ast.AST):
    """Every place a mapping or a model gains a ``verification_status`` entry.

    The first round matched ``ast.Dict`` with constant values only; the second
    added ``dict()`` keywords and subscript assignment. The re-review then ran
    fifteen shapes through it and the widest miss was the ordinary one: a
    **pydantic response model built by keyword** — ``SomeResponse(
    verification_status=row[...])`` — which is how a new route is written and
    which only ``dict(...)`` calls were checked for. So the keyword rule now
    quantifies over every call, not one callee, with the gate's own entry
    points admitted because a keyword handed to those goes into the gate rather
    than past it.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == CLAIM_LABEL_KEY:
                    yield node.lineno, value
        elif isinstance(node, ast.Call):
            if not any(_calls(node, entry) for entry in GATE_ENTRY_POINTS):
                for keyword in node.keywords:
                    if keyword.arg == CLAIM_LABEL_KEY:
                        yield node.lineno, keyword.value
            # ``payload.setdefault("verification_status", rung)`` writes the
            # entry positionally, so neither the keyword rule nor the literal
            # one sees it.
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "setdefault"
                and len(node.args) == 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == CLAIM_LABEL_KEY
            ):
                yield node.lineno, node.args[1]
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value == CLAIM_LABEL_KEY
                ):
                    yield node.lineno, node.value


def _known_key_bindings(tree: ast.AST) -> set[str]:
    """Names bound in this module to a mapping whose keys this module writes.

    A mapping built here from a literal, a comprehension or an empty
    constructor cannot acquire a ``verification_status`` without one of the
    emission shapes above firing on it, so copying it is safe. Anything else —
    a parameter, a loop variable over a database result, an attribute — is a
    mapping whose keys this module never enumerated.
    """
    known: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        built_here = (
            isinstance(value, ast.DictComp)
            or (isinstance(value, ast.Dict) and all(k is not None for k in value.keys))
            or (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in ("dict", "defaultdict", "Counter", "OrderedDict")
                and not value.args
            )
        )
        if built_here:
            known |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return known


def _copy_source_is_accounted_for(node: ast.AST, known: set[str]) -> bool:
    if isinstance(node, (ast.Dict, ast.DictComp)):
        return True
    if isinstance(node, ast.Name):
        return node.id in known
    if isinstance(node, ast.Attribute):
        return node.attr.endswith("labels")
    if isinstance(node, ast.Call):
        if _calls(node, "ungated_mapping"):
            return True
        # ``dict(x)`` is the copy, not a source: look through it. Any other
        # call is a value some function built, and that function's own
        # emissions are scanned by the same walk.
        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            return not node.args or _copy_source_is_accounted_for(node.args[0], known)
        return True
    return False


def _wholesale_copies(tree: ast.AST, known: set[str]):
    """Copies that emit every key of a mapping without naming one.

    ``dict(row)``, ``{**row}`` and ``{k: row[k] for k in COLUMNS}`` put a
    ``verification_status`` on the wire while mentioning no such string, so
    every rule above is blind to them by construction. This one asks the same
    question the others do — where did the value come from — of the mapping
    rather than of the entry.
    """
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "dict"
            and node.args
        ):
            if not _copy_source_is_accounted_for(node.args[0], known):
                yield node.lineno, node.args[0]
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is None and not _copy_source_is_accounted_for(value, known):
                    yield node.lineno, value
        elif isinstance(node, ast.DictComp):
            generator = node.generators[0]
            if (
                isinstance(generator.target, ast.Name)
                and isinstance(node.key, ast.Name)
                and node.key.id == generator.target.id
                and isinstance(node.value, ast.Subscript)
                and isinstance(node.value.slice, ast.Name)
                and node.value.slice.id == generator.target.id
                and not _copy_source_is_accounted_for(node.value.value, known)
            ):
                yield node.lineno, node.value.value


def ungated_label_emissions(sources) -> list[str]:
    """Emissions whose value came from neither the producer nor a declaration.

    Two questions, not one. Every module is asked where a named
    ``verification_status`` entry got its value. A module that **serves the
    claim** — one that calls the producer — is also asked where a wholesale
    mapping copy got its keys, because that is how the label reaches a reader
    without anyone writing its name. Restricting the second question to
    serving modules is what keeps it a property rather than a marker sprayed
    over every ``dict(row)`` in the tree; its reach and its blind spot are both
    stated in the fix round 2 report.
    """
    offenders = []
    for relpath, source in sources:
        tree = ast.parse(source)
        bound = _labels_bindings(tree)
        for lineno, value in _emissions(tree):
            if _reads_a_labels_mapping(value, bound):
                continue
            if any(_calls(value, marker) for marker in claim_gates.STATUS_DECLARATIONS):
                continue
            # A literal `None` is the absence of a status, not a status. The
            # memory candidate says so explicitly because a memory's lifecycle
            # `status` is a different vocabulary entirely.
            if isinstance(value, ast.Constant) and value.value is None:
                continue
            offenders.append(f"{relpath}:{lineno}: {ast.unparse(value)}")
        if "row_labels" not in source:
            continue
        known = _known_key_bindings(tree)
        for lineno, value in _wholesale_copies(tree, known):
            offenders.append(f"{relpath}:{lineno}: copy of {ast.unparse(value)}")
    return offenders


def _code_strings(tree: ast.AST):
    """String constants that are code, not prose.

    Docstrings are excluded by node identity rather than by position in the
    text, because the trap this scan inherited went the other way:
    ``test_verification_judge``'s scan matches its module name as *text* and
    fires on any comment that mentions it.
    """
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            yield node.lineno, node.value


def _app_sources() -> list[tuple[str, str]]:
    """Every module under ``app/`` except the producer and the gate."""
    return [
        (relpath, path.read_text())
        for path in sorted((BACKEND / "app").rglob("*.py"))
        for relpath in [path.relative_to(BACKEND).as_posix()]
        if relpath not in PRODUCER_RELPATHS
    ]


def test_the_walk_reaches_every_serving_layer():
    """The first round's grounded scan globbed one directory, non-recursively,
    so a new *route* serving the label left the suite green (measured). The
    coverage of the walk is therefore asserted rather than assumed."""
    scanned = {relpath for relpath, _ in _app_sources()}
    for layer in ("app/api/routes/", "app/api/mcp/", "app/services/", "app/repositories/"):
        assert any(relpath.startswith(layer) for relpath in scanned), layer
    assert len(scanned) > 150, "the walk stopped short of the tree"
    assert PRODUCER_RELPATHS <= {
        path.relative_to(BACKEND).as_posix() for path in (BACKEND / "app").rglob("*.py")
    }


def test_no_path_under_app_emits_a_label_the_producer_did_not_build():
    """A gate applied at each consumer is a convention; applied at the one
    producer it is a property. This is what keeps it one."""
    offenders = ungated_label_emissions(_app_sources())
    assert not offenders, (
        "a path emits a verification_status the producer did not build. Serve "
        "`fact_badge.row_labels`'s value, or declare the site with "
        "`claim_gates.ungated_status` if no reader is served it: "
        + "; ".join(offenders)
    )


@pytest.mark.parametrize(
    "snippet",
    [
        'item = {"verification_status": "corroborated"}',
        'item = {"verification_status": row["verification_status"]}',
        'item = {"verification_status": row.verification_status}',
        "item = dict(verification_status=row.verification_status)",
        'item["verification_status"] = candidate.verification_status',
        'item = {"verification_status": rung}',
        'item = {"verification_status": badge.as_dict()["verification_status"]}',
    ],
)
def test_the_scan_fires_on_a_path_that_bypassed_the_producer(snippet):
    """The guard's own failure mode, exercised. A scan nobody watched fail is
    a scan nobody has tested — the first round's passed its unit test and
    missed both live bypasses."""
    assert ungated_label_emissions([("app/services/new_surface.py", snippet)])


@pytest.mark.parametrize(
    "snippet",
    [
        'item = {"verification_status": row_labels(id_kind="fact")["verification_status"]}',
        'labels = row_labels(id_kind="fact")\n'
        'item = {"verification_status": labels["verification_status"]}',
        'item = {"verification_status": row.labels.get("verification_status")}',
        f'item = {{"verification_status": {UNSERVED}(row["verification_status"])}}',
        f'item = {{"verification_status": {JOURNALLED}(row["verification_status"])}}',
    ],
)
def test_the_scan_admits_the_producer_and_declared_derivations(snippet):
    assert ungated_label_emissions([("app/services/new_surface.py", snippet)]) == []


# A module that serves the claim calls the producer, and the wholesale-copy
# half of the scan keys on exactly that. Snippets below that exercise it carry
# the call so they are the kind of module the rule is about.
SERVING = 'labels = row_labels(id_kind="fact")\n'

# **The scan's reach, written down.** The fix round 1 re-review ran fifteen
# emission shapes through the guard and it caught three; a scan whose reach is
# unstated is one nobody can rely on, so the reach is a table with an expected
# outcome per shape rather than a paragraph. `False` rows are knowingly
# uncovered, each for a reason given in the fix round 2 report — they are
# author-adversarial shapes, not ones an ordinary route writes by accident.
EMISSION_SHAPES = [
    ("dict literal", 'item = {"verification_status": "corroborated"}', True),
    ("dict() keyword", "item = dict(verification_status=rung)", True),
    ("subscript assignment", 'item["verification_status"] = rung', True),
    (
        "pydantic constructor keyword",
        'item = FactListItem(id=fid, verification_status=row["verification_status"])',
        True,
    ),
    ("function call keyword", "serialize(row, verification_status=rung)", True),
    ("dict.update keyword", "payload.update(verification_status=rung)", True),
    ("dict.update literal", 'payload.update({"verification_status": rung})', True),
    ("dict.setdefault", 'payload.setdefault("verification_status", rung)', True),
    ("wholesale dict(row)", SERVING + "item = dict(row)", True),
    ("wholesale {**row}", SERVING + 'item = {**row, "id": fid}', True),
    (
        "column-loop comprehension",
        SERVING + "item = {column: row[column] for column in COLUMNS}",
        True,
    ),
    (
        "name laundering",
        'fact_labels = row\nitem = {"verification_status": fact_labels["verification_status"]}',
        False,
    ),
    ("dict(zip(...))", SERVING + "item = dict(zip(COLUMNS, values))", False),
    (
        "aliased key variable",
        'KEY = "verification_status"\nitem[KEY] = rung',
        False,
    ),
    (
        "JSON string assembly",
        'body = \'{"verification_status": "\' + rung + \'"}\'',
        False,
    ),
    (
        "false unserved_status declaration",
        f'return {{"verification_status": {UNSERVED}(row["verification_status"])}}',
        False,
    ),
    ("wholesale copy outside a serving module", "item = dict(row)", False),
]


@pytest.mark.parametrize(
    "shape,snippet,fires", EMISSION_SHAPES, ids=[s[0] for s in EMISSION_SHAPES]
)
def test_the_scans_reach_is_the_one_it_claims(shape, snippet, fires):
    """Both directions of every shape the re-review ran, so widening or
    narrowing the guard shows up here as a changed expectation rather than as
    silence. The shape that mattered is `pydantic constructor keyword`: it is
    how a new route builds its response, it is what T2.28's serving surface
    will be, and it passed the previous guard."""
    assert bool(ungated_label_emissions([("app/services/new_surface.py", snippet)])) is fires


# ── which declaration a site carries, and whether it is the true one ──
#
# T2.100. The single ``ungated_status`` marker defined wrapping as a claim that
# the value reaches no reader, and the ladder's journal sites wrapped it while
# ``GET /api/v1/events`` served the payload verbatim to an authenticated
# reader. The exposure is ruled acceptable — G-C's own false-promotion audit
# reads that journal — but the declaration was false at exactly the sites where
# it was load-bearing, and a false declaration is worse than an undeclared one:
# the scan trusts it and so does the next person to read it.
#
# So the marker is two markers, and this section asks the question that
# separates them. The static half is directional: a value bound for the journal
# may not declare that it reaches nobody. The behavioural half is at the doors,
# below — the "false declaration" row in EMISSION_SHAPES is `False` because no
# static scan can see that a wrapped value is served, which is why the promise
# is checked by driving the door instead.

# ``record_event`` is the sole journal writer and ``record_human_verdict`` is
# its one wrapper; the prefix is the convention both follow. Matching the
# prefix rather than the two names is what keeps a third wrapper from being
# invisible to this rule the day it is written.
JOURNAL_WRITER_PREFIX = "record_"

# The declarations that may not appear on a value flowing into the journal.
# ``ungated_mapping`` is here for the reason its docstring gives: it is
# deliberately unsplit, and that stays honest only while no site carrying it
# lands in a payload ``/events`` serves.
UNJOURNALLED_DECLARATIONS = frozenset({UNSERVED, "ungated_mapping"})


def _declaration_sites(tree: ast.AST) -> list[tuple[str, str]]:
    """``(marker, enclosing qualname)`` for every status declaration in a module.

    Attributed to the innermost enclosing definition so re-classifying a site
    is a visible edit rather than a line-number shuffle.
    """
    found: list[tuple[str, str]] = []

    def walk(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            for marker in claim_gates.STATUS_DECLARATIONS:
                if _calls(child, marker):
                    found.append((marker, scope))
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                walk(child, f"{scope}.{child.name}" if scope else child.name)
            else:
                walk(child, scope)

    walk(tree, "")
    return found


def declaration_inventory(sources) -> dict[str, dict[str, dict[str, int]]]:
    """``relpath -> marker -> qualname -> how many sites``."""
    inventory: dict[str, dict[str, dict[str, int]]] = {}
    for relpath, source in sources:
        for marker, qualname in _declaration_sites(ast.parse(source)):
            scope = inventory.setdefault(relpath, {}).setdefault(marker, {})
            scope[qualname or "<module>"] = scope.get(qualname or "<module>", 0) + 1
    return inventory


# **The classification, pinned.** Every site below was decided one at a time
# and its reason is in `docs/planning/reviews/2026-08-06-t2.100-report.md`. In
# one sentence each: the four `journalled` scopes hand their value to
# `record_event`, directly or through `record_human_verdict`, and `/events`
# serves it; the four `unserved` scopes hand theirs to the ranking, to the
# badge producer, or to a caller the door discards.
#
# Pinned rather than merely scanned so that adding a declared site is an
# argument someone makes here, not a wrap someone reaches for to quiet the
# emission scan.
DECLARATION_INVENTORY = {
    "app/repositories/knowledge_triples.py": {
        JOURNALLED: {
            "KnowledgeTripleRepository.set_verification_status": 2,
            "KnowledgeTripleRepository.ratify": 2,
        },
    },
    "app/services/human_adjudication.py": {
        JOURNALLED: {
            "record_human_verdict": 1,
            "reject_fact": 1,
            "ratify_fact": 1,
        },
        UNSERVED: {"reject_fact": 1},
    },
    "app/services/facts_channel.py": {
        UNSERVED: {"_row_to_candidate": 1},
    },
    "app/services/layer_composition.py": {
        UNSERVED: {
            "fact_candidate": 1,
            "article_candidate": 1,
            "compose": 1,
        },
    },
}


def test_every_declaration_site_is_the_one_that_was_classified():
    """A site's marker is its claim about where the value goes, and a claim
    nobody re-reads decays. This is the whole classification in one place, so a
    re-classification is a diff and a new declared site is an argument."""
    assert declaration_inventory(_app_sources()) == DECLARATION_INVENTORY


def _names_written_by(node: ast.stmt) -> set[str]:
    """The names a simple statement mutates: targets, subscript bases, receivers."""
    written: set[str] = set()
    targets: list[ast.AST] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        # ``payload.update(...)`` / ``payload.setdefault(...)``: the mapping is
        # the receiver, and nothing is bound to a name at all.
        func = node.value.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            written.add(func.value.id)
    # Unpacking targets are walked into, subscript *slices* deliberately are
    # not: ``payload, extra = {...}, None`` writes both names, while
    # ``payload[key] = ...`` writes `payload` and merely reads `key`.
    def _from_target(target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            written.add(target.id)
        elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            written.add(target.value.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                _from_target(element)
        elif isinstance(target, ast.Starred):
            _from_target(target.value)

    for target in targets:
        _from_target(target)
    return written


def journal_bound_denials(sources) -> list[str]:
    """Values flowing into the journal under a declaration that denies a reader.

    ``/events`` serves ``payload`` verbatim under the same ``require_auth`` as
    the facts door, so anything reaching a ``record_*`` writer reaches a reader.
    Both the inline payload and the one bound to a name a statement earlier are
    followed, the second because that is how the human-verdict writer builds it.

    **The binding is not always an ``ast.Assign``**, and assuming it was is how
    the first version of this guard passed its own self-test while missing the
    live site: ``payload: dict = {...}`` is an ``AnnAssign``, and a payload just
    as often gains its entry through ``payload[...] = ...`` or
    ``payload.update(...)`` a few lines below its construction. So a statement
    is read for a denial anywhere in its subtree, and every name it writes
    through — target, subscript base, or method receiver — carries the taint.

    **Taint moves through a second name.** ``inner = {…denial…}`` then
    ``payload = {"wrapped": inner}`` used to be blind — one ordinary refactor
    away from the live before/after payload style, and undisclosed. A statement
    that reads a tainted name now taints what it writes, iterated to a fixpoint
    because a module's statements are not walked in source order.

    **Reach, stated.** One hop *out of the module*: a value handed to an
    ordinary function that itself journals is invisible here. What covers that
    is **not** the events door drive, which the first report claimed — a door
    drive asserts the presence of a rung on a known transition and can never
    catch a falsely-`unserved` value inside a payload. The backstop is
    ``DECLARATION_INVENTORY``: every declared site in the tree is pinned, so a
    site reached through any number of hops is an argument someone makes there
    before this guard is ever consulted.
    """
    offenders: list[str] = []
    for relpath, source in sources:
        tree = ast.parse(source)
        # Simple statements only. A compound one (`if`, `for`, a whole `def`)
        # contains every statement under it, so reading its subtree would taint
        # every name the block writes — including the row a journal call
        # legitimately reads from two statements away.
        statements = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr))
        ]
        tainted: set[str] = set()
        while True:
            grown = set(tainted)
            for node in statements:
                carries = any(
                    _calls(inner, marker)
                    for inner in ast.walk(node)
                    for marker in UNJOURNALLED_DECLARATIONS
                ) or any(
                    isinstance(inner, ast.Name) and inner.id in tainted
                    for inner in ast.walk(getattr(node, "value", node) or node)
                )
                if carries:
                    grown |= _names_written_by(node)
            if grown == tainted:
                break
            tainted = grown
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if not name.startswith(JOURNAL_WRITER_PREFIX):
                continue
            for inner in ast.walk(node):
                denies = any(
                    _calls(inner, marker) for marker in UNJOURNALLED_DECLARATIONS
                )
                launders = isinstance(inner, ast.Name) and inner.id in tainted
                if denies or launders:
                    offenders.append(f"{relpath}:{node.lineno}: {name}")
                    break
    return offenders


def test_no_journal_payload_declares_that_it_reaches_no_reader():
    """The defect T2.100 exists for, as a property rather than a review note."""
    offenders = journal_bound_denials(_app_sources())
    assert not offenders, (
        "a value declared as reaching no reader is written to the journal, "
        f"which `GET /api/v1/events` serves verbatim: {offenders}. Declare it "
        f"`claim_gates.{JOURNALLED}` — the exposure is ruled acceptable and "
        "the declaration is what has to be true."
    )


DENIAL_SHAPES = [
    (
        "inline payload",
        f'record_event(session, payload={{"verification_status": {UNSERVED}(rung)}})',
        True,
    ),
    (
        "payload bound a statement earlier",
        f'payload = {{"verification_status": {UNSERVED}(rung)}}\n'
        "record_event(session, payload=payload)",
        True,
    ),
    # The shape the live code uses, and the one that defeated this guard's
    # first version: an annotated binding is an `AnnAssign`, not an `Assign`,
    # so the guard passed its own self-test above while the real journal site
    # went unseen. Planting the shape the tree actually contains is the
    # difference between a tested guard and a guard nobody watched fail.
    (
        "annotated payload binding",
        f'payload: dict = {{"verification_status": {UNSERVED}(rung)}}\n'
        "record_event(session, payload=payload)",
        True,
    ),
    (
        "payload gaining the entry after construction",
        f'payload = {{}}\npayload["verification_status"] = {UNSERVED}(rung)\n'
        "record_event(session, payload=payload)",
        True,
    ),
    (
        "payload updated in place",
        f"payload = {{}}\npayload.update(verification_status={UNSERVED}(rung))\n"
        "record_event(session, payload=payload)",
        True,
    ),
    # Both of these were measured blind in review. The first sits inside the
    # docstring's own claimed reach ("every name it writes through"), and the
    # second is one refactor away from the live before/after payload style.
    (
        "payload bound through a tuple target",
        f'payload, extra = {{"verification_status": {UNSERVED}(rung)}}, None\n'
        "record_event(session, payload=payload)",
        True,
    ),
    (
        "the denial laundered through a second name",
        f'inner = {{"verification_status": {UNSERVED}(rung)}}\n'
        'payload = {"wrapped": inner}\n'
        "record_event(session, payload=payload)",
        True,
    ),
    (
        "a second name that was never tainted",
        'inner = {"origin_count": 2}\npayload = {"wrapped": inner}\n'
        "record_event(session, payload=payload)",
        False,
    ),
    (
        "keyword into a journal wrapper",
        f"record_human_verdict(session, verification_status={UNSERVED}(rung))",
        True,
    ),
    (
        "a wholesale copy into a payload",
        "record_event(session, payload=dict(ungated_mapping(row)))",
        True,
    ),
    (
        "the journal declaration, which is the point",
        f'record_event(session, payload={{"verification_status": {JOURNALLED}(rung)}})',
        False,
    ),
    (
        "an unserved declaration nowhere near the journal",
        f'return {{"verification_status": {UNSERVED}(rung)}}',
        False,
    ),
    (
        "a journal call carrying no status at all",
        'record_event(session, payload={"outcome": outcome})',
        False,
    ),
]


@pytest.mark.parametrize(
    "shape,snippet,fires", DENIAL_SHAPES, ids=[s[0] for s in DENIAL_SHAPES]
)
def test_the_journal_direction_guard_fires_on_what_it_claims(shape, snippet, fires):
    """Both directions, including the shape the live code actually uses: the
    human-verdict payload is bound to a name before ``record_event`` sees it,
    so a guard that only walked the call would have missed the site the review
    found."""
    assert bool(journal_bound_denials([("app/services/new_surface.py", snippet)])) is fires


# ── who reads a journal payload, and who gates it ────────────────────
#
# T2.100 fix round. The declaration guard above asks where a *written* value
# goes; this asks the mirror question, which is the one the review answered by
# measurement: which modules **read** the journal back, because a payload
# embedded in a claim surface is that surface's own output. The ruling that
# accepts the raw rung is about the events door, so it does not travel with
# the bytes into a body whose purpose is to state a fact's status.

JOURNAL_PAYLOAD_READERS = frozenset(
    {"list_events", "object_timeline", "calendar_counts", "latest_verified_evidence"}
)

EMBEDDING_GATE = claim_gates.gated_journal_payload.__name__


def journal_payload_reach(sources) -> dict[str, dict[str, bool]]:
    """``relpath -> reader -> whether the module also gates what it reads``."""
    reach: dict[str, dict[str, bool]] = {}
    for relpath, source in sources:
        tree = ast.parse(source)
        gated = any(_calls(node, EMBEDDING_GATE) for node in ast.walk(tree))
        for node in ast.walk(tree):
            for reader in JOURNAL_PAYLOAD_READERS:
                if _calls(node, reader):
                    reach.setdefault(relpath, {})[reader] = gated
    return reach


# **The reader set, pinned, with its disposition.** The review measured this
# set at three doors when every statement of it named one, which is this
# task's own defect class: a stated reach narrower than the measured readers.
#
# - `api/routes/events.py` is the audit substrate's own door. It serves the
#   payload verbatim to an authenticated reader and that is the ruling; the
#   drives below assert both the rung and the authentication.
# - `facts_read.py` (`ladder`) and `review_queue.py` (`evidence`) embed the
#   payload in a claim surface, so both gate it.
# - `fact_badge.py` and `layer_composition.py` read the same journal and serve
#   **no** payload from it: the badge takes `as_of` and a contradiction
#   boolean, and `dispute_label` copies named counterpart fields. Neither
#   carries a rung, which is why neither gates — and a third of these is a
#   diff here before it is a leak.
JOURNAL_PAYLOAD_REACH = {
    "app/api/routes/events.py": {
        "list_events": False,
        "object_timeline": False,
        "calendar_counts": False,
    },
    "app/services/fact_badge.py": {"latest_verified_evidence": False},
    "app/services/facts_read.py": {
        "object_timeline": True,
        "latest_verified_evidence": True,
    },
    "app/services/layer_composition.py": {"latest_verified_evidence": False},
    "app/services/review_queue.py": {"latest_verified_evidence": True},
    # `research_rerun` (T3.28) reads the `research_run` payload for a
    # subject, a filed count and the memory ids to re-derive. It carries no
    # rung and serves no payload content onward -- the ids go to the
    # pipeline in-process and what comes back is a tally -- so it does not
    # gate, for the same reason `fact_badge` and `layer_composition` do not.
    "app/services/research_rerun.py": {"list_events": False},
}


def test_every_reader_of_a_journal_payload_is_the_one_that_was_classified():
    """A new reader of the journal is an argument someone makes here.

    Scanned over the whole tree including the producer and the gate, because
    the question is who reads the substrate rather than who serves a label —
    `fact_badge` is a reader and is exempt from the emission scan.
    """
    sources = _app_sources() + [
        (path.relative_to(BACKEND).as_posix(), path.read_text())
        for path in sorted((BACKEND / "app").rglob("*.py"))
        if path.relative_to(BACKEND).as_posix() in PRODUCER_RELPATHS
    ]
    assert journal_payload_reach(sources) == JOURNAL_PAYLOAD_REACH


def test_no_path_under_app_serves_a_grounded_label_today():
    """The article channel is not built (T3.02/T3.23). This pins that nothing
    serves the label *before* the channel exists, so the gate lands with the
    channel rather than after it. The non-literal half of the same question —
    a path reading the status off a row, which is how every real serving path
    works — is answered by the emission scan above plus the article gate."""
    offenders = [
        f"{relpath}:{lineno}"
        for relpath, source in _app_sources()
        for lineno, value in _code_strings(ast.parse(source))
        if value == GROUNDED_LABEL
    ]
    assert not offenders, f"a path emits a grounded label ungated: {offenders}"


def test_the_grounded_scan_reads_code_and_not_prose():
    """Both directions of the text-matching trap. It must fire on a route that
    serves the literal — the case the old glob could not see outside
    `services/` — and must not fire on a docstring that discusses groundedness
    or on a longer identifier that contains the word."""
    serving = '{"verification_status": "grounded"}'
    prose = '"""Whether an article is grounded is doc 09 §4.3\'s question."""'
    adjacent = 'BAR = "groundedness_gate_precision_bar"'

    def _hits(source: str) -> bool:
        return any(
            value == GROUNDED_LABEL for _, value in _code_strings(ast.parse(source))
        )

    assert _hits(serving)
    assert not _hits(prose)
    assert not _hits(adjacent)


def test_this_module_never_reaches_the_judge():
    """The groundedness question belongs to `verification_judge`, which owns the
    record and is scan-enforced as the only door. Re-asking it here would put
    two modules in the business of deciding whether the judge is qualified —
    the drift that scan exists to prevent, and it caught this module's first
    version doing exactly that."""
    source = (BACKEND / "app" / "services" / "claim_gates.py").read_text()
    assert "from app.services.verification_judge import" not in source
    assert "import verification_judge" not in source


# ── the doors, driven with the gate closed and no fixture ────────────
#
# The review's clause-1 verdict turned on this section not existing. Every
# door-level test in the suite that met a promoted status took
# `cleared_promotion_record`, so suppression was tested at zero doors — and
# the fixture is precisely what masked the chat leak from the parity test.
# Nothing below may take it.

FACTS_ROUTE = "/api/v1/knowledge/facts"
SEARCH_ROUTE = "/api/v1/knowledge/search"
QUEUE_ROUTE = "/api/v1/review-queue/facts"
TOPICS_ROUTE = "/api/v1/knowledge/topics/pin-suggestions"


class _FakeLLM:
    async def embed(self, query: str):
        return [1.0, 0.0, 0.0, 0.0], "t295|4"


@pytest.fixture
def doors(session, monkeypatch):
    """Both doors pointed at the test's own session."""

    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", None)
    monkeypatch.setattr(fastapi_app.state, "llm", _FakeLLM(), raising=False)


async def _promoted_fact(session, *, review_state: str | None = None) -> str:
    """A fact promoted **the way production promotes one**, with no evidence
    record.

    It used to reach the rung by direct UPDATE, and that quietly made the
    whole-body door drive below assert a property of the fixture rather than
    of the doors: a fact that never transitioned has no ``verified`` journal
    row, so no door could have embedded one, so "the rung appears nowhere"
    held without any door doing anything. Driving the ladder's own applier
    journals the transition, which is what every real corroborated fact
    carries — and what the fact detail and the review queue then embed.
    """
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"t295-{uuid.uuid4()}",
        subject_name="pgbouncer",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer DEPLOYED_ON homelab",
        reference_time=AT,
        project=PROJECT,
        valid_at=AT,
        review_state=review_state,
    )
    await KnowledgeTripleRepository(session).set_verification_status(
        row["id"], PROMOTED, outcome="promote", origin_count=2, required_n=2
    )
    await FactSourceRepository(session).add_source(
        fact_id=row["id"],
        source_kind="memory",
        source_ref=str(uuid.uuid4()),
        origin_key="origin-a",
    )
    await session.flush()
    return str(row["id"])


def _fact_channel_row(fact_id: str) -> dict:
    return {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "pgbouncer DEPLOYED_ON homelab",
        "subject_name": "pgbouncer",
        "rel_type": "DEPLOYED_ON",
        "object_name": "homelab",
        "project": PROJECT,
        "verification_status": PROMOTED,
        "review_state": None,
        "rrf_score": 0.5,
    }


def _stub_channels(monkeypatch, fact_id: str) -> None:
    async def _memories(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[])

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[_fact_channel_row(fact_id)])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memories)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)


def _assert_withheld(payload: dict, where: str) -> None:
    assert payload["verification_status"] == SUPPRESSED, where
    assert payload["label_suppressed"], f"{where}: the marker never reached the wire"
    assert "verification_unmeasured" in payload["label_suppressed"], where


async def test_the_rest_facts_list_serves_the_withheld_rung_and_says_so(
    client, auth_headers, session, doors
):
    await _promoted_fact(session)

    body = (
        await client.get(f"{FACTS_ROUTE}?project={PROJECT}", headers=auth_headers)
    ).json()

    assert body["total"] == 1
    item = body["items"][0]
    _assert_withheld(item, "REST facts list")
    assert item["badge"] is None
    assert item["unverified"] is True


async def test_the_rest_fact_detail_serves_the_withheld_rung_and_says_so(
    client, auth_headers, session, doors
):
    fact_id = await _promoted_fact(session)

    response = await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)

    assert response.status_code == 200, response.text
    _assert_withheld(response.json(), "REST fact detail")


async def test_the_mcp_fact_get_serves_the_withheld_rung_and_says_so(session, doors):
    fact_id = await _promoted_fact(session)

    body = json.loads(await mcp_server.fact_get(fact_id=fact_id))

    _assert_withheld(body, "MCP fact_get")


async def test_the_review_queue_serves_the_withheld_rung_and_says_so(
    client, auth_headers, session, doors
):
    """The door the review measured serving a raw `corroborated`. A triager is
    a reader, and this is the one screen whose whole purpose is judging how
    well-supported a fact is."""
    fact_id = await _promoted_fact(session, review_state="open")
    await session.execute(
        text(
            "UPDATE knowledge_triples SET demotion_pending_since = NOW(), "
            "demotion_pending_cycles = 1 WHERE id = CAST(:id AS uuid)"
        ),
        {"id": fact_id},
    )
    await session.flush()

    body = (
        await client.get(f"{QUEUE_ROUTE}?project={PROJECT}", headers=auth_headers)
    ).json()

    assert body["total"] == 1
    item = body["items"][0]
    _assert_withheld(item, "REST review queue")
    # The reason is derived from the raw rung and is unaffected: it answers why
    # the row is queued, which is not a claim about how verified it is.
    assert item["reason"] == "under-sourced"


async def test_both_knowledge_doors_serve_the_withheld_rung_and_its_tier(
    client, auth_headers, session, monkeypatch, doors
):
    """The composed read on both doors, including `tier` — the field that
    served the withheld rung numerically while the label beside it read
    `candidate`."""
    fact_id = await _promoted_fact(session)
    _stub_channels(monkeypatch, fact_id)

    rest = await client.post(
        SEARCH_ROUTE,
        json={"query": QUERY, "project": PROJECT, "limit": 20, "fuse": True},
        headers=auth_headers,
    )
    assert rest.status_code == 200, rest.text
    tool = json.loads(
        await mcp_server.knowledge_search(
            query=QUERY, project=PROJECT, limit=20, fuse=True
        )
    )

    for door, body in (("REST knowledge search", rest.json()), ("MCP knowledge_search", tool)):
        row = next(r for r in body["rows"] if r["id_kind"] == "fact")
        _assert_withheld(row["labels"], door)
        assert row["labels"]["badge"] is None, door
        assert row["tier"] == SUPPRESSED_TIER, (
            f"{door}: the served tier is the promoted rung in numeric form"
        )


async def test_the_chat_context_serves_the_withheld_rung_and_says_so(
    session, monkeypatch, doors
):
    """The leak the review measured, at its own door. The payload is persisted
    into `messages.context` and rendered by the chat context panel, so a raw
    rung here outlives the request that served it."""
    fact_id = await _promoted_fact(session)
    _stub_channels(monkeypatch, fact_id)

    service = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await service._retrieve(QUERY, {"project": PROJECT})

    served = retrieval["facts"]
    assert [row["id"] for row in served] == [fact_id]
    _assert_withheld(served[0], "chat context")
    assert served[0]["badge"] is None


async def test_the_composed_row_still_ranks_on_the_rung_it_does_not_serve(
    session, monkeypatch, doors
):
    """Derivation may use the true status; the wire may not reveal it. The
    module's doctrine permits ranking to consume promoted rungs, so the row's
    own tier stays the promoted one — only the served copy moves."""
    from app.services.layer_composition import LayerCompositionService

    fact_id = await _promoted_fact(session)
    _stub_channels(monkeypatch, fact_id)

    composed = await LayerCompositionService(_FakeLLM(), session).search(
        QUERY, project=PROJECT, limit=20
    )

    row = next(r for r in composed.rows if r.id_kind == "fact")
    assert row.verification_status == PROMOTED
    assert row.tier == PROMOTED_TIER
    assert row.labels["verification_status"] == SUPPRESSED


async def test_a_composition_without_badges_serves_the_withheld_rung_too(session):
    """`compose(badges=None)` is a supported call and on that path `_labels` is
    the served label dict — the badge overlay that gates it never runs. The raw
    attribute spelled there put a promoted rung on the wire for every caller
    that took it."""
    from app.services.layer_composition import compose, fact_candidate

    candidate = fact_candidate(_fact_channel_row(str(uuid.uuid4())), channel_rank=1)
    result = compose([candidate])

    labels = result.rows[0].labels
    assert labels["verification_status"] == SUPPRESSED
    assert labels["label_suppressed"]


async def _candidate_fact(session) -> str:
    """A fact genuinely sitting at `candidate` — nothing was withheld from it."""
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"t295-cand-{uuid.uuid4()}",
        subject_name="pgbouncer",
        object_name="staging",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer DEPLOYED_ON staging",
        reference_time=AT,
        project=PROJECT,
        valid_at=AT,
    )
    await session.flush()
    return str(row["id"])


async def _filtered_ids(client, auth_headers, rung: str) -> list[str]:
    body = (
        await client.get(
            f"{FACTS_ROUTE}?project={PROJECT}&verification_status={rung}",
            headers=auth_headers,
        )
    ).json()
    assert body["total"] == len(body["items"]), "the count and the page disagree"
    return [item["id"] for item in body["items"]]


async def test_the_status_filter_cannot_invert_the_gate(
    client, auth_headers, session, doors
):
    """The filter was an oracle for the rung the label withholds, measured at
    this door: `?verification_status=corroborated` returned exactly the
    suppressed fact and `?verification_status=candidate` returned it not at
    all, so two requests recovered per fact what the label refuses to say. The
    label never appeared in a body and the reader had it anyway — which is why
    the filter now keys on the served rung, the same value the field carries."""
    withheld = await _promoted_fact(session)
    genuine = await _candidate_fact(session)

    assert await _filtered_ids(client, auth_headers, PROMOTED) == []
    assert set(await _filtered_ids(client, auth_headers, SUPPRESSED)) == {
        withheld,
        genuine,
    }

    body = (
        await client.get(f"{FACTS_ROUTE}?project={PROJECT}", headers=auth_headers)
    ).json()
    served = {item["id"]: item for item in body["items"]}
    _assert_withheld(served[withheld], "the suppressed fact")
    assert served[genuine]["verification_status"] == SUPPRESSED
    assert served[genuine]["label_suppressed"] is None


async def test_the_status_filter_follows_the_record_the_label_follows(
    client, auth_headers, session, monkeypatch, cleared_record, doors
):
    """The other direction: once the record exists the two rungs are served
    apart again, and the filter separates them the same way. A filter that
    stayed collapsed would hide the promoted rows the gate had just released."""
    withheld = await _promoted_fact(session)
    genuine = await _candidate_fact(session)
    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)

    assert await _filtered_ids(client, auth_headers, PROMOTED) == [withheld]
    assert await _filtered_ids(client, auth_headers, SUPPRESSED) == [genuine]


async def test_minting_the_record_lights_every_door_with_no_code_change(
    client, auth_headers, session, monkeypatch, cleared_record, doors
):
    """Clause 4 at a door rather than at the producer. This one *may* open the
    gate: it is the reversibility claim, and the assertion is that the doors
    move with the record."""
    fact_id = await _promoted_fact(session)

    before = (await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)).json()
    assert before["verification_status"] == SUPPRESSED

    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)
    after = (await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)).json()

    assert after["verification_status"] == PROMOTED
    assert after["label_suppressed"] is None
    assert after["badge"]["claim"]


# ── each declaration, checked against the door it names ──────────────
#
# T2.100. A marker is a claim about where a value goes, and no static scan can
# check it: the "false declaration" row in EMISSION_SHAPES is `False` precisely
# because a serving path that wraps itself is invisible to the parsed tree.
# What is not invisible is the response body. So both halves of the split are
# driven — the journalled sites at the door that serves them, the unserved
# sites at every door they feed — and a site that declared the wrong one fails
# here rather than in a review six weeks later.

EVENTS_ROUTE = "/api/v1/events"
REJECT_ROUTE = "/api/v1/review-queue/facts/{fact_id}/reject"


async def _events(client, auth_headers, **params) -> list[dict]:
    response = await client.get(EVENTS_ROUTE, params=params, headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_the_events_door_serves_the_journalled_rung_verbatim(
    client, auth_headers, session, doors
):
    """The declaration `journalled_status` makes, proven true at the door.

    A ladder transition journals the rung it moved off and the rung it moved
    to, and `GET /events` hands that payload to an authenticated reader under
    the same `require_auth` as the facts door — so for any fact that has ever
    transitioned the withheld rung is directly readable, with none of the
    subtraction the two closed oracles needed.

    **This is ruled acceptable and is asserted, not merely tolerated** (T2.100
    amendment log): G-C's own false-promotion audit reads this journal, so
    narrowing the substrate to protect the gate would degrade the evidence the
    gate is measured with. What the ruling forbids is a site claiming the
    opposite. Anyone who "fixes" this exposure by gating the events door has to
    delete this test to do it, which is the review the change deserves.
    """
    fact_id = await _candidate_fact(session)

    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id, PROMOTED, outcome="promote", origin_count=2, required_n=2
    )
    await session.flush()

    rows = await _events(
        client, auth_headers, object_type="fact", event_type="verified"
    )
    journalled = next(row for row in rows if row["object_id"] == fact_id)

    assert journalled["payload"]["before"]["verification_status"] == SUPPRESSED
    assert journalled["payload"]["after"]["verification_status"] == PROMOTED


async def test_the_rejection_journals_the_rung_and_returns_none_of_it(
    client, auth_headers, session, doors
):
    """Both halves of the split on one value, in one call.

    `reject_fact` reads the rung once and uses it twice: the copy handed to
    `record_human_verdict` is `journalled_status` and the copy in the returned
    dict is `unserved_status`. The door proves each. The verdict payload
    carries `corroborated` to an authenticated reader; the response carries no
    body at all, because 204 is what the route answers and the return value is
    for an in-process caller's bookkeeping.
    """
    fact_id = await _promoted_fact(session, review_state="open")

    response = await client.post(
        REJECT_ROUTE.format(fact_id=fact_id), headers=auth_headers
    )

    assert response.status_code == 204, response.text
    assert response.content == b"", "the unserved return reached the wire"

    verdicts = await _events(
        client, auth_headers, object_type="fact", event_type="human_verdict"
    )
    verdict = next(row for row in verdicts if row["object_id"] == fact_id)
    assert verdict["payload"]["verification_status"] == PROMOTED
    assert verdict["payload"]["verdict"] == "rejected"


async def test_an_events_read_requires_an_authenticated_reader(client, session):
    """The ruling's own qualifier, asserted.

    What was accepted is that *an authenticated operator* can read the ladder's
    transitions off the audit substrate. The events door drive above sends auth
    headers and would stay green if the dependency were dropped, so it cannot
    tell "an authenticated operator can read them" from "anyone can" — and the
    difference is the whole scope of what was ruled. All three readers of the
    table are driven, because the payload is served verbatim by each.
    """
    await _promoted_fact(session)

    for route in (EVENTS_ROUTE, f"{EVENTS_ROUTE}/timeline", f"{EVENTS_ROUTE}/calendar"):
        response = await client.get(route)
        assert response.status_code == 401, (
            f"{route} served the journal to an unauthenticated reader; the "
            "exposure ruled acceptable was to an authenticated operator"
        )


async def _ladder(client, auth_headers, fact_id: str) -> list[dict]:
    response = await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()["ladder"]


async def _queue_evidence(client, auth_headers, fact_id: str) -> dict:
    body = (
        await client.get(f"{QUEUE_ROUTE}?project={PROJECT}", headers=auth_headers)
    ).json()
    return next(item for item in body["items"] if item["id"] == fact_id)["evidence"]


async def test_the_fact_detail_ladder_serves_the_journal_through_the_gate(
    client, auth_headers, session, doors
):
    """An accepted residue is scoped to the surface it was accepted on.

    `/events` may serve the rung raw because a reader of that door is reading a
    computation log by construction of the door they opened — an argument about
    the door, not about the bytes. Embedded in a body whose purpose is to state
    this fact's status, the same payload is the claim surface's own output: a
    detail response that suppresses the rung in `verification_status` and hands
    it back two keys later in `ladder` has not gated anything, it has moved the
    answer.

    Driven end to end with a production-shaped transition, which is the part
    that matters — a fact promoted by direct UPDATE has no journal row, and a
    fixture like that is why this was measured in review rather than by a test.
    """
    fact_id = await _promoted_fact(session)

    response = await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)
    body = response.json()

    assert PROMOTED not in response.text, "the ladder handed back the withheld rung"
    _assert_withheld(body, "REST fact detail")
    transition = next(
        entry for entry in body["ladder"] if entry["event_type"] == "verified"
    )
    payload = transition["payload"]
    # The rung is served, not dropped: a trace that silently rewrote the
    # transition would record a movement to `candidate` the ladder never made.
    assert payload["after"][CLAIM_LABEL_KEY] == SUPPRESSED
    assert "verification_unmeasured" in payload["after"]["label_suppressed"]
    # And the transition's own starting rung was genuinely `candidate`, so the
    # marker is what tells the two apart inside one payload.
    assert payload["before"][CLAIM_LABEL_KEY] == SUPPRESSED
    assert "label_suppressed" not in payload["before"]


async def test_the_review_queue_evidence_serves_the_journal_through_the_gate(
    client, auth_headers, session, doors
):
    """The second embedding, and the surface where it reads worst: the queue
    exists to show a triager how well-supported a fact is, and it was handing
    back the withheld rung in the evidence block beside the suppressed label."""
    fact_id = await _promoted_fact(session, review_state="open")

    response = await client.get(f"{QUEUE_ROUTE}?project={PROJECT}", headers=auth_headers)
    item = next(row for row in response.json()["items"] if row["id"] == fact_id)

    assert PROMOTED not in response.text, "the evidence handed back the withheld rung"
    _assert_withheld(item, "REST review queue")
    payload = item["evidence"]["payload"]
    assert payload["after"][CLAIM_LABEL_KEY] == SUPPRESSED
    assert "verification_unmeasured" in payload["after"]["label_suppressed"]


async def test_minting_the_record_returns_the_rung_to_both_embeddings(
    client, auth_headers, session, monkeypatch, cleared_record, doors
):
    """Reversibility, at the two surfaces this round closed. The gate withholds
    the rung; it does not edit the journal, and the record is what puts the
    transition back on both bodies with no code change."""
    fact_id = await _promoted_fact(session, review_state="open")

    assert PROMOTED not in json.dumps(await _ladder(client, auth_headers, fact_id))
    assert PROMOTED not in json.dumps(
        await _queue_evidence(client, auth_headers, fact_id), default=str
    )

    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)

    ladder = await _ladder(client, auth_headers, fact_id)
    transition = next(entry for entry in ladder if entry["event_type"] == "verified")
    assert transition["payload"]["after"][CLAIM_LABEL_KEY] == PROMOTED
    assert "label_suppressed" not in transition["payload"]["after"]

    evidence = await _queue_evidence(client, auth_headers, fact_id)
    assert evidence["payload"]["after"][CLAIM_LABEL_KEY] == PROMOTED


async def test_no_unserved_declaration_reaches_a_reader_at_any_door(
    client, auth_headers, session, monkeypatch, doors
):
    """The other half: the promoted rung appears **nowhere** in what these
    doors serve, for a fact promoted the way production promotes one.

    Stronger than the field assertions above on purpose. Those read one key
    and pass while the same value rides a second one — which is how `tier`
    served the withheld rung as a number for as long as it did. This searches
    the whole body for the string, so a ranking input that leaked into any key
    of any row fails it.

    The doors are the ones the four `unserved_status` sites feed:
    `facts_channel._row_to_candidate` and `layer_composition`'s two candidate
    constructors and `ComposedRow` all reach the composed read, which REST,
    MCP and chat share.

    **The fixture is the assertion here**, and it was the defect. This claim
    was measured false at its own fact-detail door for any journalled fact,
    and it passed only because `_promoted_fact` reached the rung by direct
    UPDATE — so the blanket string search was a property of a fact with no
    ladder rather than of the doors. `_promoted_fact` now drives the ladder's
    applier, so the detail body carries a real `verified` transition and the
    claim holds because the door gates that payload (T2.100 fix round I-1),
    not because there was nothing to leak.
    """
    fact_id = await _promoted_fact(session)
    _stub_channels(monkeypatch, fact_id)

    bodies = {
        "REST facts list": (
            await client.get(f"{FACTS_ROUTE}?project={PROJECT}", headers=auth_headers)
        ).text,
        "REST fact detail": (
            await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)
        ).text,
        "MCP fact_get": await mcp_server.fact_get(fact_id=fact_id),
        "REST knowledge search": (
            await client.post(
                SEARCH_ROUTE,
                json={"query": QUERY, "project": PROJECT, "limit": 20, "fuse": True},
                headers=auth_headers,
            )
        ).text,
        "MCP knowledge_search": await mcp_server.knowledge_search(
            query=QUERY, project=PROJECT, limit=20, fuse=True
        ),
    }

    service = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    bodies["chat context"] = json.dumps(
        await service._retrieve(QUERY, {"project": PROJECT}), default=str
    )

    for door, body in bodies.items():
        assert PROMOTED not in body, (
            f"{door} serves the promoted rung somewhere in its body; a site "
            f"declaring `claim_gates.{UNSERVED}` says no reader receives it"
        )


# ── no served aggregate counts the rung the label withholds ──────────
#
# T2.99. The label is not the only way a number can name the rung. The topics
# door served `verified_fact_count` over the raw column, so a reader could
# list the subject's facts — where `confirmed` is served openly and
# `corroborated` is not — subtract, and recover per subject how many of its
# facts were withheld. The same number gates whether the suggestion is served
# at all, so the leak had two exits and both are driven here.


async def _subject_fact(session, subject: str, status: str) -> None:
    """A fact at an exact rung, written straight to the column — this suite
    asserts what a *door* serves over stored rows, so the rung is a fixture
    input rather than something the ladder is asked to produce."""
    fact_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO knowledge_triples (id, subject_name, object_name, "
            "rel_type, reference_time, fact, project, triple_key, "
            "verification_status) VALUES (CAST(:id AS uuid), :subject, 'homelab', "
            "'DEPLOYED_ON', now(), :fact, CAST(:project AS text), :key, :status)"
        ),
        {
            "id": str(fact_id),
            "subject": subject,
            "fact": f"{subject} DEPLOYED_ON homelab",
            "project": PROJECT,
            "key": f"t299:{subject}:{fact_id}",
            "status": status,
        },
    )


async def _seed_topics(session, plan: dict[str, list[str]]) -> None:
    """`subject -> the rungs of its facts`, plus one community per subject."""
    memory_ids = []
    for subject, statuses in plan.items():
        for status in statuses:
            await _subject_fact(session, subject, status)
        memory_id = new_id()
        await session.execute(
            text(
                "INSERT INTO memories (id, content, source, project, status) VALUES "
                "(CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')"
            ),
            {"id": str(memory_id), "content": f"{subject} notes", "project": PROJECT},
        )
        memory_ids.append((subject, memory_id))
    await communities_repo.replace_project_communities(
        session,
        PROJECT,
        [
            communities_repo.CommunityDraft(
                label=f"{subject}, topic",
                memory_ids=(memory_id,),
                properties={
                    "size": 1,
                    "dominant_entities": [
                        {"name": subject, "type": "tool", "display_name": subject}
                    ],
                },
            )
            for subject, memory_id in memory_ids
        ],
    )
    await session.flush()


async def _pin_suggestions(client, auth_headers) -> dict:
    response = await client.get(
        f"{TOPICS_ROUTE}?project={PROJECT}", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {s["dominant_name"]: s for s in body["suggestions"]}


async def test_the_topics_count_cannot_be_subtracted_back_to_the_rung(
    client, auth_headers, session, doors
):
    """Two subjects that differ only in the rung of their second fact. The
    withheld one's second fact sits at the promoted rung and the genuine
    one's at the suppressed rung; both serve `confirmed` on the first. If the
    count is taken over the column the two report 2 and 1, and the difference
    is exactly the number of facts whose label was withheld."""
    await _seed_topics(
        session,
        {
            "withheld-sub": ["confirmed", PROMOTED],
            "genuine-sub": ["confirmed", SUPPRESSED],
        },
    )

    served = await _pin_suggestions(client, auth_headers)

    assert set(served) == {"withheld-sub", "genuine-sub"}
    assert served["withheld-sub"]["verified_fact_count"] == 1
    assert (
        served["withheld-sub"]["verified_fact_count"]
        == served["genuine-sub"]["verified_fact_count"]
    ), "the served count separates a withheld rung from a genuine candidate"


async def test_the_topics_membership_cannot_be_read_back_to_the_rung(
    client, auth_headers, session, doors
):
    """The second exit. The count also gates whether a suggestion is served,
    so a subject supported only by withheld facts appearing at all asserts
    the floor was met by facts the reader is not shown — the same oracle with
    one bit in place of a number. Both subjects here must be absent from the
    suggestions while both remain in the diff, which is the honest shape:
    the topic exists, the claim about its support does not."""
    await _seed_topics(
        session,
        {"withheld-only": [PROMOTED], "genuine-only": [SUPPRESSED]},
    )

    response = await client.get(
        f"{TOPICS_ROUTE}?project={PROJECT}", headers=auth_headers
    )
    body = response.json()

    assert body["suggestions"] == []
    assert {entry["dominant_name"] for entry in body["diff"]} == {
        "withheld-only",
        "genuine-only",
    }


async def test_minting_the_record_restores_the_topics_count_and_membership(
    client, auth_headers, session, monkeypatch, cleared_record, doors
):
    """Clause 2 at this door. Both exits reopen on the record alone, with no
    code change — the promoted rung starts counting again and the subject it
    is the only support for is nominated again."""
    await _seed_topics(
        session,
        {"withheld-sub": ["confirmed", PROMOTED], "withheld-only": [PROMOTED]},
    )

    before = await _pin_suggestions(client, auth_headers)
    assert before["withheld-sub"]["verified_fact_count"] == 1
    assert "withheld-only" not in before

    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)
    after = await _pin_suggestions(client, auth_headers)

    assert after["withheld-sub"]["verified_fact_count"] == 2
    assert after["withheld-only"]["verified_fact_count"] == 1


# ── the sweep, pinned: one aggregate over the rung, and it is gated ───


_SQL_AGGREGATE = re.compile(
    r"\b(count|sum|avg|min|max|bool_or|bool_and|array_agg|jsonb_agg|string_agg)\s*\(",
    re.IGNORECASE,
)
_SQL_STATEMENT = re.compile(r"\bfrom\b", re.IGNORECASE)

# Every SQL string under `app/` that aggregates while naming the verification
# column. Over-inclusive on purpose — naming the column near an aggregate is
# cheap to detect and each hit is cheap to account for, whereas deciding in a
# regex whether the aggregate is *keyed* on the column is neither. The error
# direction is the honesty guard's: an unrecognised shape lands here for a
# human to look at rather than passing silently.
#
# - `pin_suggestions` counts facts per subject and serves the number.
#   Gated: it binds the counted rungs through
#   `claim_gates.raw_statuses_for_served`, so what it counts is what the
#   reader was already shown (T2.99).
# - `review_ranking` aggregates over the review queue's membership
#   (`review_state = 'open'`), never over the rung; its one rung predicate
#   selects `disputed`, which is ungated and its own preimage, so no
#   aggregate downstream of it can separate a withheld rung from a candidate.
#
# **Reach, stated rather than implied.** This reads one string *expression* at
# a time: a plain constant, or an f-string rejoined across its interpolations
# (widened 2026-08-11, after a shared predicate turned `article_eligibility`'s
# counting CTE into two fragments neither of which carried both signals — the
# scan lost a site it had been reporting, and lost it silently). Fragments
# assembled by concatenation or `.format` and joined later are still invisible
# — `KnowledgeTripleRepository.list_live` builds its `COUNT(*)` exactly that
# way, and that count is gated only because `facts_read` hands it a
# served-inverted set. Neither this scan nor the label scan sees that shape.
# What covers it is a door drive with the gate closed.
# - `article_eligibility` counts a subject's verified facts to decide whether
#   it clears doc 09 §4.1's synthesis floor. **Ungated on purpose, and the
#   reason is that it serves nobody**: the module has no route, no door and no
#   caller outside the synthesis selection path, and its consumer (T3.02) is
#   held shut by G-D. It counts the stored rungs because the question it asks
#   is what the vault holds, not what it may currently say out loud — see its
#   module docstring. **The obligation this entry records:** the returned
#   `verified_fact_count` is a stored-vocabulary number, so the first surface
#   that renders it owes the same `raw_statuses_for_served` inversion
#   `pin_suggestions` does, or it becomes the oracle that gates against.
# - `article_eligibility` also aggregates fact ids per subject
#   (`live_fact_ids`), the one basis of the stored `fact_set_hash` and of the
#   articles channel's live one that labels a returned article stale.
#   **Ungated, and here the stored vocabulary is not merely acceptable but
#   required**: the article's
#   own stored hash was computed from stored rungs (T3.02), so comparing it
#   against a served-inverted set would mark every article stale the moment a
#   gate closed — a label flip driven by the gate rather than by knowledge
#   changing. No rung reaches a reader from this path; the aggregate's only
#   output is an opaque digest.
AGGREGATES_NAMING_THE_RUNG = {
    "app/services/pin_suggestions.py",
    "app/services/review_ranking.py",
    "app/services/article_eligibility.py",
}


def _docstrings(tree: ast.AST) -> set[int]:
    seen: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                seen.add(first.value.lineno)
    return seen


def _module_string_constants(tree: ast.AST) -> dict[str, str]:
    """Module-level ``NAME = "literal"``, for resolving f-string SQL."""
    out: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                out[target.id] = value.value
    return out


def _sql_strings(tree: ast.AST, prose: set[int]) -> list[str]:
    """Every string an SQL query could be spelled as, joined where f-strung.

    A query interpolating a shared predicate is one `JoinedStr` whose pieces
    are separate `Constant` nodes, so reading constants alone splits the query
    at the interpolation point and loses any signal that does not survive in
    one fragment — which is how `article_eligibility`'s counting CTE dropped
    out of this scan the day its predicate became shared. Interpolated
    module-level literals are substituted; anything else becomes a space, so
    the join can only widen what is seen, never fabricate it.
    """
    constants = _module_string_constants(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for piece in node.values:
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    parts.append(piece.value)
                elif isinstance(piece, ast.FormattedValue):
                    name = piece.value
                    parts.append(
                        constants.get(name.id, " ")
                        if isinstance(name, ast.Name)
                        else " "
                    )
            out.append("".join(parts))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.lineno not in prose:
                out.append(node.value)
    return out


def sql_aggregates_over_the_rung(sources) -> set[str]:
    found: set[str] = set()
    for relpath, source in sources:
        tree = ast.parse(source)
        prose = _docstrings(tree)
        for raw in _sql_strings(tree, prose):
            text_ = " ".join(raw.split())
            if (
                CLAIM_LABEL_KEY in text_
                and _SQL_AGGREGATE.search(text_)
                and _SQL_STATEMENT.search(text_)
            ):
                found.add(relpath)
    return found


def test_only_the_swept_aggregates_name_the_rung():
    """A number is a claim about the rung as surely as a word is.

    The label scan above asks where a served ``verification_status`` came
    from, and a ``COUNT(*)`` keyed on that column answers it without ever
    emitting one — which is how the topics door served a raw-rung aggregate
    for as long as it did. This pins the swept result so a third site has to
    be argued for rather than merely written."""
    assert sql_aggregates_over_the_rung(_app_sources()) == AGGREGATES_NAMING_THE_RUNG


def test_the_one_swept_aggregate_binds_the_rungs_the_gate_allows():
    """Pinning the site is half of it: the site also has to be gated. This
    asserts the binding rather than the literal, so renaming the helper does
    not quietly evade it."""
    from app.services import pin_suggestions

    closed = claim_gates.ClaimGate(False, "no record")
    assert pin_suggestions.served_verified_statuses(closed) == [RATIFIED]
    assert pin_suggestions.served_verified_statuses(
        claim_gates.ClaimGate(True)
    ) == sorted(pin_suggestions.VERIFIED_SERVED_STATUSES)

    source = (BACKEND / "app/services/pin_suggestions.py").read_text(encoding="utf-8")
    assert "raw_statuses_for_served" in source, (
        "the counted set no longer inverts the gate; the count and the label "
        "have to answer the same question about the same fact"
    )


@pytest.mark.parametrize(
    "snippet, fires",
    [
        (
            'Q = text("SELECT COUNT(*) FROM knowledge_triples WHERE '
            'verification_status = ANY(CAST(:s AS text[]))")',
            True,
        ),
        (
            'Q = text("SELECT count(id) FROM knowledge_triples GROUP BY '
            'verification_status")',
            True,
        ),
        # A read of the column with no aggregate is the ordinary serving
        # shape, and the label scan owns it.
        ('Q = text("SELECT verification_status FROM knowledge_triples")', False),
        # Prose describing a count is not a count.
        ('"""COUNT(*) over verification_status, from the ladder."""', False),
        # The shape that went dark: the two signals land on opposite sides of
        # an interpolation, so neither fragment carries both.
        (
            'P = "t.expired_at IS NULL"\n'
            'Q = text(f"SELECT verification_status FROM knowledge_triples '
            'WHERE {P} GROUP BY count(id)")',
            True,
        ),
        # …and the join may not invent one: an f-string with no aggregate
        # anywhere still does not fire.
        (
            'P = "t.expired_at IS NULL"\n'
            'Q = text(f"SELECT verification_status FROM knowledge_triples '
            'WHERE {P}")',
            False,
        ),
    ],
)
def test_the_aggregate_sweep_fires_on_what_it_claims(tmp_path, snippet, fires):
    path = tmp_path / "planted.py"
    path.write_text(snippet, encoding="utf-8")
    found = sql_aggregates_over_the_rung([("planted.py", path.read_text())])
    assert bool(found) is fires


# ── the marker survives serialization, per schema ────────────────────


@pytest.mark.parametrize(
    "model_path",
    [
        "app.schemas.facts:FactListItem",
        "app.schemas.facts:FactDetailResponse",
        "app.schemas.knowledge:ComposedRowLabels",
        "app.schemas.review_queue:ReviewQueueFactItem",
    ],
)
def test_every_labelled_wire_model_declares_the_suppression_marker(model_path):
    """Pydantic's default `extra='ignore'` drops what a model does not name, so
    a producer-level test passes while the marker dies at the boundary —
    exactly how three schemas lost it at once. This is the third field this
    surface has dropped that way; `unverified` was the second."""
    import importlib

    module_name, _, attribute = model_path.partition(":")
    model = getattr(importlib.import_module(module_name), attribute)
    assert "label_suppressed" in model.model_fields, model_path


# ─────────────── T3.02: the article gate is wired to the judge's record ──────


async def test_minting_a_qualification_record_lights_an_article_with_no_code_change(
    session, tmp_path
):
    """The article analogue of the fact gate's own reversibility test.

    Before T3.02 the article gate was closed *unconditionally* and opening it
    needed an edit — which is a code-gated label wearing a gate's name, and the
    inverse of T2.95's principle that an evidence record gates the label, never
    the code. The gate now comes from the judge's single door, so minting a
    cleared record opens it with no edit anywhere.
    """
    import json as _json

    from app.services.verification_judge import article_claim_gate

    absent = tmp_path / "missing.json"
    closed = await article_claim_gate(session, {}, absent)
    assert closed.open is False
    assert closed.reason

    # A record that clears every bar the judge checks would open it. This
    # asserts the *wiring* — that the answer tracks the record rather than a
    # constant — which is the property the code change bought.
    record = tmp_path / "record.json"
    record.write_text(_json.dumps({"gate_eligible": False}))
    still_closed = await article_claim_gate(session, {}, record)
    assert still_closed.open is False
    assert "gate_eligible" in (still_closed.reason or "")


async def test_an_unwired_caller_still_fails_closed(session):
    """`row_labels` without a gate falls through to the module default, which
    is `groundedness_gate()` — closed. So a path that forgets to pass one
    cannot serve a promoted article status by omission."""
    labels = row_labels(id_kind="article", verification_status=PROMOTED)

    assert labels["verification_status"] == SUPPRESSED
    assert "groundedness_unmeasured" in labels["label_suppressed"]


async def test_a_minted_fact_record_still_does_not_light_an_article(
    session, cleared_record, monkeypatch
):
    """T2.95 seam 3, now that the article path is reachable.

    A fact's rung is certified by G-C's promotion audit and an article's by
    G-D's judge qualification. Gating both against one record would let the
    fact record light an article's label — which is the whole reason `id_kind`
    rides through the producer.
    """
    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)

    fact = row_labels(id_kind="fact", verification_status=PROMOTED)
    article = row_labels(id_kind="article", verification_status=PROMOTED)

    assert fact["verification_status"] == PROMOTED, "the fact record lights facts"
    assert article["verification_status"] == SUPPRESSED, (
        "and must not light articles"
    )


async def test_an_open_gate_passed_in_is_actually_read():
    """The forwarding's own proof, and it needs an *open* gate to exist.

    With no qualification record the judge's gate and the module's default are
    both closed, so forwarding or not forwarding produces the same answer — a
    mutation that dropped the parameter passed every other test in this file.
    An unproven wiring is not a wiring; this is the assertion that fails when
    `row_labels` stops reading what it is handed.
    """
    from app.services.claim_gates import ClaimGate

    withheld = row_labels(id_kind="article", verification_status=PROMOTED)
    served = row_labels(
        id_kind="article", verification_status=PROMOTED, gate=ClaimGate(True, None)
    )

    assert withheld["verification_status"] == SUPPRESSED
    assert served["verification_status"] == PROMOTED
    assert served["label_suppressed"] is None


def test_the_shipped_record_if_present_is_one_the_gate_can_read():
    """The artifact's own guard, which no other test can carry any more.

    Every test in the suite now runs with `PROMOTION_RECORD_PATH` pinned at an
    absent path (`_corroboration_gate_closed_by_default`), so nothing else looks
    at the file the repository actually ships. That is right for the gate's
    behaviour and wrong for the artifact: a minted record with a trailing comma,
    a `"gate_eligible": "true"` string, or bad UTF-8 fails **closed** and
    silently — the label simply stays withheld and reads exactly like a gate
    nobody has cleared yet, which is the one confusion T2.95 exists to prevent.

    Absent is a legitimate state and passes here: it means G-C has not cleared.
    Present-but-unreadable is not, and neither is present-but-not-eligible,
    because minting is a deliberate act and a half-minted record records
    nothing.
    """
    path = BACKEND / "app" / "services" / "promotion_metrics_record.json"
    if not path.exists():
        pytest.skip("no record minted; the gate is closed, which is a valid state")

    record = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(record, dict), "a record the loader cannot treat as a dict"
    assert record.get("gate_eligible") is True, (
        "a minted record must say `true`, not a truthy string: the gate compares "
        "with `is True` precisely so an INTERIM branding cannot read as a pass"
    )
    assert claim_gates.corroboration_gate(path).open is True
