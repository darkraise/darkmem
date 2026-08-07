"""The resample sheet: turns the blind export into something a human labels
in one sitting (T2.107, LABELLING.md Layer 3).

**This module never reads the gold.** It imports nothing from
``entailment_gold`` and never opens ``gold.json``. Its only inputs are
``resample_blind.json`` (the shuffled export of ``id``/``premise``/
``hypothesis`` rows) and ``LABELLING.md``, the general labelling rulebook.
That is proven structurally by
``scripts/benchlib/tests/test_resample_sheet.py``'s AST scan, not merely
true today: an import of ``entailment_gold``, a call to
``load_entailment_gold``, or a literal naming ``gold.json`` outside this
docstring all fail that scan. The reason is stated in the module docstring
of ``resample_draw.py`` and in ``LABELLING.md``'s History section: this
resample is the first accuracy measurement the gold receives from outside
the family that labelled it, and a sheet generator that could read the
answer would defeat the one thing being measured.

**The rulebook excerpt is read verbatim from LABELLING.md, not
paraphrased -- with one narrow, mechanical redaction.** The Step-5 review
(LABELLING.md, "Step-5 rulebook fork") found that a condensed restatement
of these rules drifted from the file and caused two real labelling
escalations, so this module extracts named sections out of the live file by
heading instead of re-writing them, and fails loudly if a targeted heading
goes missing. But LABELLING.md's rule text also cites specific pair ids as
worked examples ("is `contradicted` (eg-0018)"), and those ids are real
gold pairs -- the `contradicted` stratum of this resample is a full census,
so a cited contradicted example is *guaranteed* to also be one of the 93
sheet items, printed under that same real id a few lines below. Left in,
the rulebook excerpt would hand the labeller that item's answer directly
(verified empirically during this module's own build: a first draft of the
sheet put "eg-0016" and "eg-0022" on items 6 and 7, both cited two
paragraphs above). ``rulebook_excerpt`` strips every such citation
(``_redact_example_ids``); the rule prose itself is untouched.

The completed sheet is also the return artifact: ``parse_completed`` reads
the same file's own fill-in markers back out, so the owner works from and
hands back one file rather than a sheet plus a separate answer file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ENTAILMENT_DIR = Path(__file__).resolve().parent / "entailment"
BLIND_EXPORT_PATH = ENTAILMENT_DIR / "resample_blind.json"
LABELLING_PATH = ENTAILMENT_DIR / "LABELLING.md"
DEFAULT_SHEET_PATH = ENTAILMENT_DIR / "resample_sheet.md"

# Duplicated from the gold's own three-way vocabulary deliberately -- this
# module may not import the gold module that declares it (see the module
# docstring). Keep in sync with `entailment_gold.VERDICTS` by hand; the
# scorer, which does import that module, is what actually validates a
# completed sheet's verdicts against it.
VERDICT_WORDS = ("entailed", "contradicted", "unsupported")

_RULEBOOK_HEADINGS = (
    "The three verdicts, and the binary G-D scores on",
    "General decision procedure",
    "Edge rulings — cite these by name in rationales",
)

_ITEM_RE = re.compile(r"^## Item \d+ — (?P<id>\S+)\s*$")
_VERDICT_RE = re.compile(r"^\*\*Verdict:\*\*\s*(?P<verdict>.*)$")
_RULE_RE = re.compile(r"^\*\*Rule cited:\*\*\s*(?P<rule>.*)$")


def load_blind_rows(export_path: Path | str = BLIND_EXPORT_PATH) -> list[dict]:
    """The blind export's rows, order preserved, shape checked.

    Refuses a row carrying any field beyond ``id``/``premise``/
    ``hypothesis`` -- the export's own leak-free contract
    (``resample_draw.BLIND_FIELDS``) is what makes this sheet safe to hand
    to a labeller, and a silently widened row would carry that risk here
    too.
    """
    with open(export_path, encoding="utf-8") as fh:
        rows = json.load(fh)
    for row in rows:
        if set(row) != {"id", "premise", "hypothesis"}:
            raise ValueError(
                f"blind export row {row.get('id')!r} carries unexpected "
                f"fields {sorted(row)}; expected exactly id/premise/hypothesis"
            )
    return rows


def _sections(markdown: str) -> dict[str, str]:
    """Heading text (level 1 or 2) -> its verbatim body, up to the next
    such heading. A ``## `` line never matches the level-1 check (its
    second character is ``#``, not a space), so the two levels do not
    collide."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        if line.startswith("## ") or line.startswith("# "):
            current = line.lstrip("#").strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {heading: "\n".join(lines).strip("\n") for heading, lines in sections.items()}


# LABELLING.md cites illustrative pair ids inline, e.g. "is `contradicted`
# (eg-0018)". Those ids are real gold pairs, and the `contradicted` stratum
# of this resample is a FULL CENSUS -- every live contradicted pair is drawn
# -- so any contradicted-slice example cited here is *guaranteed* to also be
# one of the 93 sheet items, printed under its own real id. Leaving the
# citation in would tell the labeller that item's verdict directly out of
# the rulebook text sitting above it (verified empirically: a first
# generation of this sheet put "eg-0016" and "eg-0022" -- both cited as
# examples two paragraphs above -- on items 6 and 7). Every parenthetical
# naming an example id is stripped; the rule text itself is untouched.
_EXAMPLE_ID_RE = re.compile(r"\s*\([^()]*\beg-\d{4}\b[^()]*\)")


def _redact_example_ids(text: str) -> str:
    return _EXAMPLE_ID_RE.sub("", text)


def rulebook_excerpt(labelling_path: Path | str = LABELLING_PATH) -> str:
    """The rule text of the sections a labeller needs, pulled out of the
    current ``LABELLING.md`` and left otherwise verbatim -- reworded
    nowhere, because a paraphrase is exactly what the Step-5 rulebook fork
    (see module docstring) drifted from the file and caused real
    escalations. The one intentional change is mechanical, not editorial:
    every parenthetical citing an example pair id is stripped (see
    ``_redact_example_ids``), because those ids are real gold pairs this
    sheet also carries.

    Raises:
        ValueError: A targeted heading is missing -- the file was
            restructured and this extraction needs updating rather than
            silently shipping a shorter rulebook.
    """
    with open(labelling_path, encoding="utf-8") as fh:
        text = fh.read()
    sections = _sections(text)
    missing = [h for h in _RULEBOOK_HEADINGS if h not in sections]
    if missing:
        raise ValueError(
            f"LABELLING.md no longer carries the heading(s) {missing!r} this "
            "excerpt targets -- update _RULEBOOK_HEADINGS to match the "
            "restructured file"
        )
    blocks = [
        f"## {heading}\n\n{_redact_example_ids(sections[heading])}"
        for heading in _RULEBOOK_HEADINGS
    ]
    return "\n\n".join(blocks)


def render_sheet(rows: list[dict], rulebook: str) -> str:
    """The sheet text: the rulebook excerpt once, then one block per row in
    the export's own order -- never resorted, never regrouped, so no
    stratum boundary or verdict-class clustering is introduced beyond
    whatever the (already shuffled) export order carries."""
    lines = [
        "# Entailment gold — Layer 3 resample sheet",
        "",
        f"{len(rows)} premise/hypothesis pairs, in the blind export's own "
        "shuffled order. Decide one verdict per item "
        f"({' / '.join(VERDICT_WORDS)}) against the rules below -- verbatim "
        "excerpts of the labelling rulebook, current as of this sheet's "
        "generation -- and name the rule you used. Use only the printed "
        "premise: no lookup of any recorded answer, no prior labelling "
        "run, no corpus or world knowledge outside this text. Fill in the "
        "Verdict and `Rule cited` line under each item, in place, and "
        "return this same file.",
        "",
        "---",
        "",
        rulebook,
        "",
        "---",
        "",
    ]
    for n, row in enumerate(rows, start=1):
        lines.extend([
            f"## Item {n} — {row['id']}",
            "",
            f"**Premise:** {row['premise']}",
            "",
            f"**Hypothesis:** {row['hypothesis']}",
            "",
            "**Verdict:** ",
            "",
            "**Rule cited:** ",
            "",
            "---",
            "",
        ])
    return "\n".join(lines) + "\n"


def parse_completed(text: str) -> dict[str, dict]:
    """The filled-in sheet's own verdicts and rule citations, keyed by id.

    Reads only the sheet's markup -- no file access at all, let alone the
    gold. A blank or malformed field is passed through as an empty string;
    validating it against the closed verdict vocabulary and checking
    coverage against the drawn sample is the scorer's job
    (``resample_score.score``), which is where the gold enters and where
    that validation belongs.
    """
    result: dict[str, dict] = {}
    current_id: str | None = None
    verdict = ""
    rule = ""
    for line in text.splitlines():
        match = _ITEM_RE.match(line)
        if match:
            if current_id is not None:
                result[current_id] = {"verdict": verdict.strip(), "rule": rule.strip()}
            current_id = match.group("id")
            verdict = ""
            rule = ""
            continue
        match = _VERDICT_RE.match(line)
        if match:
            verdict = match.group("verdict")
            continue
        match = _RULE_RE.match(line)
        if match:
            rule = match.group("rule")
            continue
    if current_id is not None:
        result[current_id] = {"verdict": verdict.strip(), "rule": rule.strip()}
    return result


def write(
    sheet_path: Path | str = DEFAULT_SHEET_PATH,
    export_path: Path | str = BLIND_EXPORT_PATH,
    labelling_path: Path | str = LABELLING_PATH,
) -> Path:
    rows = load_blind_rows(export_path)
    text = render_sheet(rows, rulebook_excerpt(labelling_path))
    sheet_path = Path(sheet_path)
    sheet_path.write_text(text, encoding="utf-8")
    return sheet_path


if __name__ == "__main__":  # pragma: no cover
    written = write()
    print(f"wrote {written}")
