"""The resample scorer: turns the owner's completed sheet into the
``resample`` block ``judge_qualification``'s eligibility lock requires
(T2.107, LABELLING.md Layer 3).

Unlike ``resample_sheet.py``, this module's whole job is to touch the gold:
it reads the current ``gold.json``, compares the owner's verdicts against
its recorded ones, and writes the comparison's result back. What it never
does is *decide* a verdict -- every verdict compared here was typed by the
owner into the sheet, not produced by this module or by any agent.

Three refusals carry the discipline, all load-bearing:

- **Stale-gold refusal.** The draw (``resample_draw.py``) pinned its sample
  to one ``gold.json`` version by hash. If the file has moved since, the
  drawn ids may no longer name the same pairs the labeller saw, or worse,
  may silently name different ones -- scoring against a changed gold
  certifies nothing about the gold being certified, so this refuses before
  comparing anything.
- **Coverage refusal.** The verdicts must cover exactly the drawn sample --
  a missing id understates ``n``, and a surplus id was never drawn and
  proves nothing about the sample that was.
- **Re-run refusal.** Once a gold carries a ``resample`` block, a second
  ``write_resample`` call without ``force=True`` raises. LABELLING.md's
  Layer 3 already states the alternative on a failure -- reclassify, fix
  the rule if needed, draw a fresh seeded sample against a new gold SHA --
  never relabel the same draw until the number looks better. ``force`` is
  the one sanctioned exception, for a genuine correction to how the
  comparison itself was computed (not to the verdicts), and it keeps the
  superseded block inside the new one so the correction is visible in the
  record rather than silently overwriting it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from benchlib import entailment_gold, resample_sheet
from benchlib.judge_qualification import RESAMPLE_MAX_DISAGREEMENTS

ENTAILMENT_DIR = entailment_gold.ENTAILMENT_DIR
MANIFEST_PATH = ENTAILMENT_DIR / "resample_manifest.json"
BLIND_EXPORT_PATH = ENTAILMENT_DIR / "resample_blind.json"
DEFAULT_DISAGREEMENTS_PATH = ENTAILMENT_DIR / "resample_disagreements.json"


def load_manifest(manifest_path: Path | str = MANIFEST_PATH) -> dict:
    with open(manifest_path, encoding="utf-8") as fh:
        return json.load(fh)


def load_blind_ids(export_path: Path | str = BLIND_EXPORT_PATH) -> set[str]:
    with open(export_path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {row["id"] for row in rows}


def score(
    verdicts: dict[str, dict],
    *,
    gold_bytes: bytes,
    gold_pairs: list[dict],
    manifest: dict,
    blind_ids: set[str],
    performed_by: str,
    date: str,
) -> tuple[dict, list[dict]]:
    """Compare ``verdicts`` (``{id: {"verdict", "rule"}}``, as
    ``resample_sheet.parse_completed`` returns) against the recorded gold.

    Returns ``(resample_block, disagreements)``: the block is exactly the
    shape ``judge_qualification._resample_reasons`` requires, and
    ``disagreements`` names every mismatched id with both verdicts -- the
    scorer's most useful output, per LABELLING.md's "classify each
    disagreement" step.

    Raises:
        ValueError: The gold has moved since the draw was pinned, or
            ``verdicts`` does not cover exactly the drawn sample, or a
            verdict is not one of the three lawful words.
    """
    actual_sha256 = hashlib.sha256(gold_bytes).hexdigest()
    if actual_sha256 != manifest["gold_sha256"]:
        raise ValueError(
            "gold.json has changed since this resample was drawn: the "
            f"manifest pins gold_sha256={manifest['gold_sha256']!r}, the "
            f"current gold hashes to {actual_sha256!r}. The draw is pinned "
            "to one gold version; scoring a stale draw certifies nothing "
            "-- re-draw (resample_draw.py) against the new gold first."
        )

    missing = blind_ids - set(verdicts)
    surplus = set(verdicts) - blind_ids
    if missing or surplus:
        raise ValueError(
            "verdicts do not cover exactly the drawn sample: "
            f"missing={sorted(missing)} surplus={sorted(surplus)}"
        )

    for pid, entry in verdicts.items():
        verdict = entry.get("verdict")
        if verdict not in entailment_gold.VERDICTS:
            raise ValueError(
                f"pair {pid!r}: verdict {verdict!r} is not one of "
                f"{sorted(entailment_gold.VERDICTS)} -- the sheet is "
                "incomplete or was edited outside its own fill-in markers"
            )

    gold_verdict_by_id = {pair["id"]: pair["verdict"] for pair in gold_pairs}
    disagreements = []
    for pid in sorted(verdicts):
        recorded = gold_verdict_by_id[pid]
        given = verdicts[pid]["verdict"]
        if given != recorded:
            disagreements.append({
                "id": pid,
                "gold_verdict": recorded,
                "resample_verdict": given,
                "rule_cited": verdicts[pid].get("rule", ""),
            })

    resample_block = {
        "n": len(verdicts),
        "disagreements": len(disagreements),
        # From the manifest, never re-derived: the seed is the draw's own
        # identity, and recomputing it here would silently accept a
        # different draw as if it were the one pinned to this gold_sha256.
        "seed": manifest["seed"],
        "performed_by": performed_by,
        "date": date,
        # The content basis (T2.116). Stamped here rather than at write
        # time because *here* is where the pairs are provably the certified
        # ones: the gold_sha256 refusal above has already established that
        # `gold_pairs` is the file the draw was pinned to. Computing it in
        # `write_resample` would hash whatever is on disk at persist time,
        # which is the very substitution this field exists to detect.
        "pairs_sha256": entailment_gold.pairs_content_hash(gold_pairs),
        "pair_digests": entailment_gold.pair_digests(gold_pairs),
    }
    return resample_block, disagreements


def write_resample(
    gold_path: Path | str,
    resample_block: dict,
    *,
    force: bool = False,
) -> dict:
    """Persist ``resample_block`` into ``gold_path``'s top level.

    Never touches ``pairs``, any pair's verdict, or ``resample_blind.json``
    -- only the top-level ``resample`` key.
    """
    gold_path = Path(gold_path)
    with open(gold_path, encoding="utf-8") as fh:
        doc = json.load(fh)

    existing = doc.get("resample")
    if existing is not None:
        if not force:
            raise ValueError(
                "gold.json already carries a resample block (recorded "
                f"{existing.get('date')!r} by {existing.get('performed_by')!r}, "
                f"{existing.get('disagreements')!r} disagreement(s) of "
                f"{existing.get('n')!r}). One sitting is recorded once per "
                "draw; a re-run cannot improve the number. Pass force=True "
                "for a genuine correction -- the prior block is kept under "
                "'supersedes', never dropped."
            )
        prior_chain = existing.get("supersedes", [])
        prior_own = {k: v for k, v in existing.items() if k != "supersedes"}
        resample_block = {**resample_block, "supersedes": [*prior_chain, prior_own]}

    doc["resample"] = resample_block
    gold_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    return doc


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", default=str(resample_sheet.DEFAULT_SHEET_PATH),
                         metavar="PATH", help="the completed sheet (resample_sheet.py's output, filled in)")
    parser.add_argument("--gold", default=str(entailment_gold.GOLD_PATH), metavar="PATH")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), metavar="PATH")
    parser.add_argument("--blind-export", default=str(BLIND_EXPORT_PATH), metavar="PATH")
    parser.add_argument("--disagreements-out", default=str(DEFAULT_DISAGREEMENTS_PATH), metavar="PATH")
    parser.add_argument("--performed-by", required=True, metavar="NAME")
    parser.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                         help="defaults to today (UTC)")
    parser.add_argument("--force", action="store_true", help=(
        "overwrite a previously recorded resample block; the prior block "
        "is kept visibly under 'supersedes', never silently dropped"
    ))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    date = args.date or datetime.now(timezone.utc).date().isoformat()

    manifest = load_manifest(args.manifest)
    blind_ids = load_blind_ids(args.blind_export)

    gold_path = Path(args.gold)
    gold_bytes = gold_path.read_bytes()
    gold_doc = json.loads(gold_bytes)

    sheet_text = Path(args.sheet).read_text(encoding="utf-8")
    verdicts = resample_sheet.parse_completed(sheet_text)

    resample_block, disagreements = score(
        verdicts,
        gold_bytes=gold_bytes,
        gold_pairs=gold_doc["pairs"],
        manifest=manifest,
        blind_ids=blind_ids,
        performed_by=args.performed_by,
        date=date,
    )

    Path(args.disagreements_out).write_text(
        json.dumps(disagreements, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    write_resample(gold_path, resample_block, force=args.force)

    print(json.dumps(resample_block, indent=2))
    bar_word = "within" if resample_block["disagreements"] <= RESAMPLE_MAX_DISAGREEMENTS else "OVER"
    print(
        f"{resample_block['disagreements']} disagreement(s) of "
        f"{resample_block['n']} -- {bar_word} the ratified bar of "
        f"<= {RESAMPLE_MAX_DISAGREEMENTS}"
    )
    for entry in disagreements:
        print(
            f"  {entry['id']}: gold={entry['gold_verdict']!r} "
            f"resample={entry['resample_verdict']!r} rule={entry['rule_cited']!r}"
        )
    if disagreements:
        print(f"disagreement detail written to {args.disagreements_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
