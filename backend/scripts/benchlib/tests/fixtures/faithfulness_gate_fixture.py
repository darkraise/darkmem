"""A **fixture**, not a gold set — TH1.17's own words. This module exercises
``benchlib.faithfulness_gate``'s scoring path; it is not the claim/span
entailment gold, has none of that gold's authoring discipline (no blind
labelling passes, no LABELLING.md, no append-only history), and must never
be read as one. The real gold does not exist yet (TH1.01 §5) and authoring
it is a different task's job.

**Anchors resolve in the runtime's coordinate system** (owner ruling
2026-08-17). A pair cites a block in the committed harvest manifest
(``faithfulness_gate/manifest.json``, produced by ``span_harvest.py`` running
the sources through the shipping parser) and indexes into **that block's own
text, from 0** — which is exactly what ``app.services.faithfulness_gate._entails``
slices when it puts a premise to the judge (``block.text[start:end]``).

This module used to compute ``content.index(span_text)`` against the *document
file* and record a ``fixture_path`` anchor, a second and incompatible basis. It
appeared to work because both ``.txt`` fixtures parse to a **single** block whose
text is the whole document, so document offsets and block offsets coincided.
``doc_pipeline.md`` exists to stop that coincidence covering the divergence: it
parses to six blocks, and its ``b1`` sits at source offsets ``[20, 89]`` while
its own text runs ``0..69``. A pair anchored the old way into that block would
slice the wrong region or nothing at all.

Spans are still *located* rather than typed by hand — ``block_text.index(...)``
inside the anchored block — so an offset can never silently disagree with the
text it claims to cite.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "faithfulness_gate"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _block(uri: str, block_key: str) -> dict:
    for document in _manifest()["documents"]:
        if document["uri"] != uri:
            continue
        for block in document["blocks"]:
            if block["block_key"] == block_key:
                return block
    raise AssertionError(f"fixture manifest has no {uri}#{block_key}")


def _anchor(uri: str, block_key: str, span_text: str) -> dict:
    """An anchor into one harvested block, with the span located in its text.

    Fails loudly when ``span_text`` is not in that block: a fixture that cites
    text the parser did not put in the block it names is a broken fixture, and
    finding out at scoring time would look like a scoring bug.
    """
    block = _block(uri, block_key)
    text = block["text"]
    start = text.find(span_text)
    if start < 0:
        raise AssertionError(
            f"{uri}#{block_key} does not contain {span_text!r}; its text is {text!r}"
        )
    return {
        "document_uri": uri,
        "block_key": block_key,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "char_span": [start, start + len(span_text)],
        # Recorded for the tests that assert reconstruction. Not read by the
        # loader — it resolves from the manifest, so a stale `text` here cannot
        # make a wrong premise pass.
        "text": span_text,
    }


def build_fixture_pairs() -> list[dict]:
    mvcc_first = _anchor(
        "doc_mvcc.txt", "b0", "Postgres uses MVCC for concurrency control."
    )
    mvcc_second = _anchor(
        "doc_mvcc.txt", "b0",
        "It was designed to avoid locking readers against writers.",
    )
    mvcc_isolation = _anchor(
        "doc_mvcc.txt", "b0", "The default isolation level is READ COMMITTED."
    )
    reranker_first = _anchor(
        "doc_reranker.txt", "b0",
        "The reranker scores the top forty RRF-ranked rows on a scale from "
        "zero to ten.",
    )
    reranker_second = _anchor(
        "doc_reranker.txt", "b0",
        "This stage runs only when reranker_enabled is set in the config "
        "table.",
    )
    # A deliberately truncated span: cites only "designed to avoid locking"
    # with no subject, the span-truncation slice TH1.01 §5 names.
    mvcc_truncated = _anchor("doc_mvcc.txt", "b0", "designed to avoid locking")

    # Two spans in two DIFFERENT blocks of the markdown document. This is the
    # case the retired document-coordinate basis could not express: `b2` starts
    # at source offset 91, so its own text indexes from 0 and the two systems
    # disagree by 91 characters.
    pipeline_ack = _anchor(
        "doc_pipeline.md", "b1",
        "Every capture door enqueues a buffer row and returns 202 with an ack.",
    )
    pipeline_claim = _anchor(
        "doc_pipeline.md", "b2",
        "The flush worker claims rows with FOR UPDATE SKIP LOCKED.",
    )
    pipeline_list = _anchor(
        "doc_pipeline.md", "b4",
        "Content embed runs first and registers the fingerprint.",
    )

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
        # ── the cross-block pairs, on real parser output ──────────────────
        {
            "id": "fx-9",
            "answer_id": "ans-pipeline",
            "premise_spans": [pipeline_ack, pipeline_claim],
            "hypothesis": (
                "A capture door acks with 202 and a flush worker later claims "
                "the row with FOR UPDATE SKIP LOCKED."
            ),
            "verdict": "entailed",
            "slice_tags": ["multi-span-composition"],
            "provenance": "document-span",
            "rationale": (
                "entailed only by the conjunction of two spans in two different "
                "blocks; neither block alone carries both halves"
            ),
        },
        {
            "id": "fx-10",
            "answer_id": "ans-pipeline",
            "premise_spans": [pipeline_list],
            "hypothesis": "Entity dedup runs before the content embed.",
            "verdict": "not-entailed",
            "slice_tags": ["structure-fragment"],
            "provenance": "document-span",
            "rationale": (
                "the cited list item says content embed runs first; the claim "
                "reverses the order the span asserts"
            ),
        },
    ]
