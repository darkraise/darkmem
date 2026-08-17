"""``resample_sheet.py`` (T2.107): the sheet generator that must never reach
the labelled gold.

Every fixture pair here is synthetic (``syn-N`` ids, made-up premises and
hypotheses) -- the resample sheet is the first accuracy measurement this
gold set will ever receive from outside the family that labelled it, and a
test asserting against real gold verdicts would be exactly the leak the
whole instrument exists to avoid. The one exception is
``rulebook_excerpt()`` read against the real, committed ``LABELLING.md``:
that file states general labelling rules, not any pair's verdict, so
reading it carries no such risk and proves the extraction still matches
the live file's headings.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from benchlib import resample_sheet

RESAMPLE_SHEET_SOURCE_PATH = Path(resample_sheet.__file__)

_SYNTHETIC_ROWS = [
    {"id": "syn-001", "premise": "The cache TTL is 300 seconds.",
     "hypothesis": "The cache TTL is set to five minutes."},
    {"id": "syn-002", "premise": "Service A replaced service B in March.",
     "hypothesis": "Service B replaced service A in March."},
    {"id": "syn-003", "premise": "The router forwards traffic to node X.",
     "hypothesis": "The router runs a firmware update nightly."},
]

_SYNTHETIC_RULEBOOK = "## Fixture Rule\n\nA fixture rule body, for round-trip tests only."


# ── structural proof: the generator never reaches the gold ──────────────


_DOCSTRING_HOLDERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_HOLDERS):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _parsed_sheet_module() -> ast.Module:
    return ast.parse(
        RESAMPLE_SHEET_SOURCE_PATH.read_text(encoding="utf-8"),
        filename=str(RESAMPLE_SHEET_SOURCE_PATH),
    )


def test_the_sheet_generator_never_imports_the_gold_module():
    """An ``import benchlib.entailment_gold`` in any spelling -- plain,
    ``from``, aliased, or wrapped across lines by a formatter -- fails
    here, because it is an AST node match, not a text search."""
    tree = _parsed_sheet_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "entailment_gold" not in alias.name, (
                    f"resample_sheet.py imports {alias.name!r} at line "
                    f"{node.lineno} -- the sheet generator must never reach "
                    "the labelled gold"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert "entailment_gold" not in module, (
                f"resample_sheet.py does `from {module} import ...` at "
                f"line {node.lineno}"
            )
            for alias in node.names:
                assert alias.name != "entailment_gold"


def test_the_sheet_generator_never_calls_the_gold_loader():
    tree = _parsed_sheet_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "load_entailment_gold":
            pytest.fail(f"resample_sheet.py references .load_entailment_gold at line {node.lineno}")
        if isinstance(node, ast.Name) and node.id == "load_entailment_gold":
            pytest.fail(f"resample_sheet.py references load_entailment_gold at line {node.lineno}")


def test_the_sheet_generator_never_names_gold_json_outside_a_docstring():
    """The recorded trap: a text search for ``gold.json`` also fires on
    this very docstring explaining the discipline. Walk the parsed tree and
    exempt only nodes structurally identified as a docstring -- never by
    matching their text -- so the exemption cannot be tricked and a real
    literal reference cannot hide inside a non-docstring string either."""
    tree = _parsed_sheet_module()
    docstrings = _docstring_node_ids(tree)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        if "gold.json" in node.value:
            offenders.append((node.lineno, node.value))
    assert offenders == [], (
        f"resample_sheet.py names gold.json outside a docstring: {offenders}"
    )


def test_the_scan_actually_catches_a_violation():
    """Mutation-proof the scan above: a source string that clearly reaches
    the gold module must fail the same checks this file runs against the
    real module -- otherwise the guard is decorative."""
    bad_source = textwrap.dedent(
        """
        from benchlib import entailment_gold

        def peek():
            return entailment_gold.load_entailment_gold()
        """
    )
    tree = ast.parse(bad_source)
    found_import = any(
        isinstance(node, ast.ImportFrom)
        and any("entailment_gold" in alias.name for alias in node.names)
        for node in ast.walk(tree)
    )
    found_call = any(
        isinstance(node, ast.Attribute) and node.attr == "load_entailment_gold"
        for node in ast.walk(tree)
    )
    assert found_import and found_call, "the scan's own matchers do not fire on an obvious violation"


# ── rulebook excerpt: verbatim, not paraphrased ──────────────────────────


def test_rulebook_excerpt_pulls_real_content_from_the_live_file():
    excerpt = resample_sheet.rulebook_excerpt()
    # Spot-check phrasing unique to each targeted section, proving the
    # extraction reached real rule text and not an empty or truncated body.
    assert "a competent reader who accepts the premise as true" in excerpt
    assert "Score the whole hypothesis" in excerpt
    assert "Exclusive-slot rule" in excerpt
    assert "Reversal rule" in excerpt


def test_rulebook_excerpt_names_no_example_pair_id():
    """The load-bearing leak check. `contradicted` is a full census, so any
    contradicted-slice example LABELLING.md cites by id is guaranteed to
    also be one of the 93 drawn items, printed under that same real id --
    a cited id directly answers that item. This was caught empirically
    (see resample_sheet.py's docstring): items 6 and 7 of a first
    generation carried exactly the ids ("eg-0022", "eg-0016") the rulebook
    excerpt cited two paragraphs above them."""
    excerpt = resample_sheet.rulebook_excerpt()
    import re
    found = re.findall(r"eg-\d{4}", excerpt)
    assert found == [], f"rulebook excerpt still names pair ids: {found}"


def test_redact_example_ids_strips_every_cited_shape():
    source = (
        "is `entailed` (eg-0016); a present-tense claim is `contradicted` (eg-0018).\n"
        "unsupported by this premise (eg-0030, eg-0038, eg-0039): a judge\n"
        "contain a negation (eg-0033..0037). This mirrors\n"
        "from/to (eg-0022, eg-0024) — or when the premise negates it (eg-0026).\n"
    )
    redacted = resample_sheet._redact_example_ids(source)
    assert "eg-" not in redacted
    # The rule prose survives untouched around each redaction.
    assert "is `entailed`; a present-tense claim is `contradicted`." in redacted
    assert "unsupported by this premise: a judge" in redacted


def test_rendered_sheet_names_no_drawn_items_id_inside_the_rulebook_block():
    """End-to-end: a rulebook block that happened to still cite one of the
    93 drawn ids would leak that item's verdict onto the page it sits on.
    Build a rulebook excerpt carrying a real-shaped citation and a row set
    sharing that same id, and prove the rendered sheet never lets the two
    coexist once `rulebook_excerpt`'s redaction has run -- render_sheet
    itself does not redact, so this exercises the two functions together
    the way `write()` actually composes them."""
    leaky_rulebook_source = "## Some Rule\n\nis `contradicted` (eg-0022).\n"
    excerpt = resample_sheet._redact_example_ids(leaky_rulebook_source)
    rows = [{"id": "eg-0022", "premise": "p", "hypothesis": "h"}]
    text = resample_sheet.render_sheet(rows, excerpt)
    # The item itself is legitimately on the page, exactly once -- as its
    # own item heading. The redacted rulebook block above it no longer
    # repeats that id next to a verdict word.
    assert text.count("eg-0022") == 1
    assert "## Item 1 — eg-0022" in text


def test_rulebook_excerpt_raises_when_a_heading_goes_missing():
    restructured = "# Something else\n\nNo targeted headings here.\n"
    tmp_path_text = restructured
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(tmp_path_text)
        path = fh.name
    with pytest.raises(ValueError, match="no longer carries the heading"):
        resample_sheet.rulebook_excerpt(path)


# ── sheet rendering: leak-free, order-preserving ─────────────────────────


def test_load_blind_rows_refuses_a_row_with_extra_fields(tmp_path):
    import json
    bad = [{"id": "x", "premise": "p", "hypothesis": "h", "verdict": "entailed"}]
    path = tmp_path / "blind.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected fields"):
        resample_sheet.load_blind_rows(path)


def test_render_sheet_preserves_the_export_order():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS, _SYNTHETIC_RULEBOOK)
    positions = [text.index(row["id"]) for row in _SYNTHETIC_ROWS]
    assert positions == sorted(positions), "the sheet reordered the export's rows"


def test_render_sheet_carries_every_premise_and_hypothesis():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS, _SYNTHETIC_RULEBOOK)
    for row in _SYNTHETIC_ROWS:
        assert row["premise"] in text
        assert row["hypothesis"] in text


def test_render_sheet_leaks_no_stratum_or_count_summary():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS, _SYNTHETIC_RULEBOOK)
    for leaky_word in ("stratum", "strata", "census", "quota", "verdict_count",
                       "per_verdict", "class boundary"):
        assert leaky_word not in text.lower()


def test_render_sheet_has_a_verdict_and_rule_slot_per_item():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS, _SYNTHETIC_RULEBOOK)
    assert text.count("**Verdict:**") == len(_SYNTHETIC_ROWS)
    assert text.count("**Rule cited:**") == len(_SYNTHETIC_ROWS)


# ── parse_completed: round-trips what render_sheet produces ─────────────


def _fill(text: str, answers: dict[str, tuple[str, str]]) -> str:
    """Fill a rendered sheet's blank slots for testing, the same way an
    owner would type into the file: locate each item by its own heading,
    then fill only that item's next Verdict/Rule lines."""
    import re

    out_lines = []
    current_id = None
    for line in text.splitlines():
        match = re.match(r"^## Item \d+ — (\S+)\s*$", line)
        if match:
            current_id = match.group(1)
            out_lines.append(line)
            continue
        if current_id in answers and line == "**Verdict:** ":
            out_lines.append(f"**Verdict:** {answers[current_id][0]}")
            continue
        if current_id in answers and line == "**Rule cited:** ":
            out_lines.append(f"**Rule cited:** {answers[current_id][1]}")
            continue
        out_lines.append(line)
    return "\n".join(out_lines) + "\n"


def test_parse_completed_round_trips_a_filled_in_sheet():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS, _SYNTHETIC_RULEBOOK)
    filled = _fill(text, {
        "syn-001": ("contradicted", "exclusive-slot rule"),
        "syn-002": ("contradicted", "reversal rule"),
        "syn-003": ("unsupported", "unrelated"),
    })
    parsed = resample_sheet.parse_completed(filled)
    assert parsed == {
        "syn-001": {"verdict": "contradicted", "rule": "exclusive-slot rule"},
        "syn-002": {"verdict": "contradicted", "rule": "reversal rule"},
        "syn-003": {"verdict": "unsupported", "rule": "unrelated"},
    }


def test_parse_completed_reads_blank_slots_as_empty_strings():
    text = resample_sheet.render_sheet(_SYNTHETIC_ROWS[:1], _SYNTHETIC_RULEBOOK)
    parsed = resample_sheet.parse_completed(text)
    assert parsed == {"syn-001": {"verdict": "", "rule": ""}}


def test_parse_completed_ignores_prose_that_is_not_a_fill_in_line():
    text = (
        "Some preamble mentioning **Verdict:** in passing but not as a "
        "field line.\n\n"
        "## Item 1 — syn-001\n\n"
        "**Verdict:** entailed\n\n"
        "**Rule cited:** paraphrase\n"
    )
    parsed = resample_sheet.parse_completed(text)
    assert parsed == {"syn-001": {"verdict": "entailed", "rule": "paraphrase"}}


def test_redact_example_ids_strips_a_bare_id_in_prose():
    """The shape that actually leaked, in the shape it leaked in.

    On 2026-08-17 five ids reached the excerpt because every rule citation
    written that day named its example mid-sentence rather than in a trailing
    parenthetical. One of them sat beside its own verdict distribution -- "the
    repetition study on eg-0650 (3 `entailed` / 2 `unsupported`...)" -- and
    eg-0650 is live and in the sampled entailed stratum, so the excerpt would
    have handed the sitting model that item's answer.
    """
    source = (
        "the repetition study on eg-0650 (3 `entailed` / 2 `unsupported`)\n"
        "eg-0465 (\"idx-03 hosts one\") and eg-0475 are equivalent\n"
        "which is how eg-0512 survived the round that retired eg-0699.\n"
    )
    redacted = resample_sheet._redact_example_ids(source)
    assert "eg-" not in redacted, redacted
    # Replaced, not deleted: the sentence must still read as a rule.
    assert "a cited example" in redacted
