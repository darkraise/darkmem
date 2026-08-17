"""Build claim/span gold pairs mechanically from the harvest manifest.

**Why this exists.** An anchor carries a `char_span` that indexes into one
harvested block's text and a `text_sha256` that byte-binds it. Both are derived
facts about the manifest, so both must be *computed*, never typed: a hand-typed
offset can silently disagree with the text it claims to cite, and the failure
surfaces as a wrong premise put to a judge rather than as an error. This module
is the only sanctioned way to turn "cite this text, in this block" into an
anchor.

**It authors nothing.** It takes a hypothesis, a verdict and a slice that a
*caller* decided and assembles the pair around them. It makes no labelling
judgement, and it cannot: `SPAN_LABELLING.md`'s rules are decision procedures for
a human or a blind-dispatched author, not predicates this module could evaluate.
What it does is make an authored decision impossible to record incorrectly.

Two guards it enforces, both of which turn a silent defect into a loud one:

- the cited text must actually occur in the named block (a typo'd quote, or a
  quote from the wrong block, fails here rather than resolving to a wrong span);
- the resolved span must round-trip — slicing the block's text at the computed
  offsets must return exactly the requested text.

Usage as a library::

    from benchlib.span_pair_builder import PairBuilder
    b = PairBuilder.from_manifest("scripts/benchlib/entailment/span_harvest.json")
    pair = b.pair(
        pair_id="sg-0001",
        answer_id="ans-001",
        hypothesis="...",
        verdict="entailed",
        slice_tags=["verbatim"],
        rationale="general procedure 3: rewording preserves entailment",
        spans=[("readme.md", "b12", "the exact text to cite")],
    )

`--list-blocks` prints candidate blocks so an author can choose without opening
the manifest by hand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parents[1]
for _path in (str(BACKEND), str(SCRIPTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import faithfulness_gate as fg  # noqa: E402


@dataclass(frozen=True)
class PairBuilder:
    manifest: dict

    @classmethod
    def from_manifest(cls, path: str | Path) -> "PairBuilder":
        return cls(manifest=fg.load_span_manifest(path))

    def block(self, document_uri: str, block_key: str) -> dict:
        block = self.manifest["blocks"].get((document_uri, block_key))
        if block is None:
            raise KeyError(
                f"{document_uri}#{block_key} is not in the manifest. Run "
                "span_harvest.py --list to see what is, or check the uri spelling"
            )
        return block

    def anchor(self, document_uri: str, block_key: str, cited_text: str) -> dict:
        """One anchor, with its offsets and hash computed from the manifest.

        `cited_text` must occur in the block exactly once. A quote occurring
        **more than once** is refused rather than silently anchored to its first
        occurrence: which occurrence was meant is an authoring decision, and
        guessing it would put a premise the author did not choose in front of the
        judge. Widen the quote to disambiguate.
        """
        block = self.block(document_uri, block_key)
        text = block["text"]
        occurrences = text.count(cited_text)
        if occurrences == 0:
            raise ValueError(
                f"{document_uri}#{block_key} does not contain {cited_text!r}.\n"
                f"  block text: {text!r}"
            )
        if occurrences > 1:
            raise ValueError(
                f"{cited_text!r} occurs {occurrences} times in "
                f"{document_uri}#{block_key}; widen the quote so the span is "
                "unambiguous rather than anchored to whichever came first"
            )
        start = text.index(cited_text)
        anchor = {
            "document_uri": document_uri,
            "block_key": block_key,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "char_span": [start, start + len(cited_text)],
            "text": cited_text,
        }
        # Round-trip through the real loader, not through this module's own
        # arithmetic: the check is worthless if it re-derives the span the same
        # way it was built.
        resolved = fg.resolve_anchor_text(fg._anchor_from_dict(anchor), self.manifest)
        if resolved != cited_text:
            raise AssertionError(
                f"anchor round-trip failed for {document_uri}#{block_key}: "
                f"resolved {resolved!r}, wanted {cited_text!r}"
            )
        return anchor

    def pair(
        self,
        *,
        pair_id: str,
        answer_id: str,
        hypothesis: str,
        verdict: str,
        slice_tags: list[str],
        rationale: str,
        spans: list[tuple[str, str, str]],
        provenance: str = "document-span",
    ) -> dict:
        """Assemble one pair and validate it through the real loader's checks."""
        pair = {
            "id": pair_id,
            "answer_id": answer_id,
            "hypothesis": hypothesis,
            "verdict": verdict,
            "provenance": provenance,
            "slice_tags": list(slice_tags),
            "rationale": rationale,
            "premise_spans": [self.anchor(*s) for s in spans],
        }
        fg.validate_pair_shape(pair)
        # Build the premise too, so a multi-span pair's concatenation is proven
        # resolvable at authoring time rather than at scoring time.
        fg.build_premise(pair, self.manifest)
        return pair


def _list_blocks(manifest: dict, *, min_chars: int, document: str | None,
                 block_type: str | None, limit: int) -> None:
    shown = 0
    for (uri, key), block in sorted(manifest["blocks"].items()):
        if document and uri != document:
            continue
        if block_type and block["type"] != block_type:
            continue
        if block.get("text_length", 0) < min_chars:
            continue
        text = block["text"].replace("\n", "\\n")
        print(f"{uri}#{key} [{block['type']}] len={block['text_length']}: {text[:120]}")
        shown += 1
        if shown >= limit:
            print(f"... (stopped at --limit {limit})")
            return
    if shown == 0:
        print("no blocks matched", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=str(fg.entailment_gold.ENTAILMENT_DIR / "span_harvest.json"),
    )
    parser.add_argument("--list-blocks", action="store_true")
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--document", default=None)
    parser.add_argument("--type", dest="block_type", default=None)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    try:
        manifest = fg.load_span_manifest(args.manifest)
    except fg.SpanManifestAbsent as exc:
        print(f"no harvest manifest at {exc.path}", file=sys.stderr)
        return 2

    if args.list_blocks:
        _list_blocks(
            manifest, min_chars=args.min_chars, document=args.document,
            block_type=args.block_type, limit=args.limit,
        )
        return 0

    doc = manifest["manifest"]
    print(
        f"manifest: {doc.get('document_count')} documents, "
        f"{doc.get('block_count')} blocks. Pass --list-blocks to browse."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
