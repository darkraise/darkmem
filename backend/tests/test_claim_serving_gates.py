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
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import claim_gates
from app.services.chat import ChatService
from app.services.fact_badge import row_labels

BACKEND = Path(__file__).resolve().parents[1]

PROJECT = "t295-gate"
QUERY = "pgbouncer connection pooling"
AT = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)

# The rung the review measured leaking, and the rung it is served as.
PROMOTED = "corroborated"
SUPPRESSED = "candidate"
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
# has to do it. Naming three functions is not the enumeration this scan exists
# to replace: they are the API the property is stated in terms of.
GATE_ENTRY_POINTS = frozenset({"row_labels", "served_status", "ungated_status"})


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
            if _calls(value, "ungated_status"):
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
        'item = {"verification_status": ungated_status(row["verification_status"])}',
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
        "false ungated_status declaration",
        'return {"verification_status": ungated_status(row["verification_status"])}',
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
    """A fact sitting at the promoted rung on disk, with no evidence record."""
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
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'corroborated' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": row["id"]},
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
    result = compose([candidate], declared_context={})

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
