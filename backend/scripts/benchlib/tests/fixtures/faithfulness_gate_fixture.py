"""A **fixture**, not a gold set — TH1.17's own words. This module exercises
``benchlib.faithfulness_gate``'s scoring path; it is not the claim/span
entailment gold, has none of that gold's authoring discipline (no blind
labelling passes, no LABELLING.md, no append-only history), and must never
be read as one. The real gold does not exist yet (TH1.01 §5) and authoring
it is a different task's job.

Pairs are built from the two committed documents next to this file
(``faithfulness_gate/doc_mvcc.txt``, ``faithfulness_gate/doc_reranker.txt``)
by locating the cited substring with ``str.index`` and hashing the actual
file bytes, so a span offset or hash typed by hand can never silently
disagree with the file it claims to anchor.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "faithfulness_gate"


def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _anchor(fixture_path: str, block_id: str, span_text: str) -> dict:
    path = FIXTURE_DIR / fixture_path
    content = path.read_text(encoding="utf-8")
    start = content.index(span_text)
    return {
        "fixture_path": fixture_path,
        "content_hash": _content_hash(path),
        "block_id": block_id,
        "char_span": [start, start + len(span_text)],
        "text": span_text,
    }


def build_fixture_pairs() -> list[dict]:
    mvcc_first = _anchor(
        "doc_mvcc.txt", "b1", "Postgres uses MVCC for concurrency control."
    )
    mvcc_second = _anchor(
        "doc_mvcc.txt", "b2",
        "It was designed to avoid locking readers against writers.",
    )
    mvcc_isolation = _anchor(
        "doc_mvcc.txt", "b3",
        "The default isolation level is READ COMMITTED.",
    )
    reranker_first = _anchor(
        "doc_reranker.txt", "b1",
        "The reranker scores the top forty RRF-ranked rows on a scale from "
        "zero to ten.",
    )
    reranker_second = _anchor(
        "doc_reranker.txt", "b2",
        "This stage runs only when reranker_enabled is set in the config "
        "table.",
    )
    # A deliberately truncated span: cites only "designed to avoid locking"
    # with no subject, the span-truncation slice TH1.01 §5 names.
    mvcc_truncated = _anchor("doc_mvcc.txt", "b2", "designed to avoid locking")

    return [
        {
            "id": "fx-1",
            "answer_id": "ans-mvcc",
            "premise_spans": [mvcc_first],
            "hypothesis": "Postgres uses MVCC for concurrency control.",
            "verdict": "entailed",
            "slice_tags": ["verbatim"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "verbatim restatement of the cited span",
        },
        {
            "id": "fx-2",
            "answer_id": "ans-mvcc",
            "premise_spans": [mvcc_second],
            "hypothesis": "It avoids locking readers against writers.",
            "verdict": "entailed",
            "slice_tags": ["paraphrase"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "paraphrase of the cited span, same claim",
        },
        {
            "id": "fx-3",
            "answer_id": "ans-mvcc",
            "premise_spans": [mvcc_isolation],
            "hypothesis": "The default isolation level is SERIALIZABLE.",
            "verdict": "not-entailed",
            "slice_tags": ["value-swap-style"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "swaps the isolation level the span actually names",
        },
        {
            "id": "fx-4",
            "answer_id": "ans-mvcc",
            "premise_spans": [mvcc_truncated],
            "hypothesis": "MVCC was designed to avoid locking readers against writers.",
            "verdict": "not-entailed",
            "slice_tags": ["span-truncation"],
            "provenance": "hand-authored-fixture-span",
            "rationale": (
                "the cited span cuts off before the subject and object; the "
                "surrounding sentence supports the claim, the citation does not"
            ),
        },
        {
            "id": "fx-5",
            "answer_id": "ans-reranker",
            "premise_spans": [reranker_first, reranker_second],
            "hypothesis": (
                "The reranker scores the top forty rows on a zero-to-ten "
                "scale, but only runs when reranker_enabled is set."
            ),
            "verdict": "entailed",
            "slice_tags": ["multi-span-composition"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "entailed only by the conjunction of both cited spans",
        },
        {
            "id": "fx-6",
            "answer_id": "ans-reranker",
            "premise_spans": [reranker_first],
            "hypothesis": "The system uses a genetic algorithm to rank code search results.",
            "verdict": "not-entailed",
            "slice_tags": ["unrelated"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "the cited span asserts nothing about this claim",
        },
        # A third synthetic answer where every sentence is genuinely
        # entailed, so a perfect judge grounds it at coverage 1.0 -- the
        # positive case score_answer_coverage's other two answer groups
        # (each carrying one unsupported sentence on purpose) cannot cover.
        {
            "id": "fx-7",
            "answer_id": "ans-allgood",
            "premise_spans": [reranker_second],
            "hypothesis": "This stage runs only when reranker_enabled is set in the config table.",
            "verdict": "entailed",
            "slice_tags": ["verbatim"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "verbatim restatement of the cited span",
        },
        {
            "id": "fx-8",
            "answer_id": "ans-allgood",
            "premise_spans": [mvcc_isolation],
            "hypothesis": "The default isolation level is READ COMMITTED.",
            "verdict": "entailed",
            "slice_tags": ["verbatim"],
            "provenance": "hand-authored-fixture-span",
            "rationale": "verbatim restatement of the cited span",
        },
    ]
