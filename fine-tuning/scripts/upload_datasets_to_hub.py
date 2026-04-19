"""Upload the training + evaluation datasets for each shipping head to HuggingFace Hub.

One dataset repo per production head, mirroring the model-side layout from
``upload_to_hub.py`` so ``darkraise/darkmem-<head>-v1`` (model) pairs with
``darkraise/darkmem-<head>-dataset`` (data).

Each dataset repo ships the exact JSONL files the shipping checkpoint was
trained on plus the held-out evaluation gold used in PRODUCTION.md. The
script stages files into a temp dir, writes a README.md describing format
and row counts, then uploads the folder. Defaults to private repos.

Usage::

    python -m scripts.upload_datasets_to_hub --hf-user darkraise --token $HF_TOKEN

    python -m scripts.upload_datasets_to_hub --hf-user darkraise --dry-run

    python -m scripts.upload_datasets_to_hub --hf-user darkraise \\
        --only classifier retriever
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


@dataclass(frozen=True)
class FilePlan:
    """One file to stage into the dataset repo."""
    source: Path
    target: str  # filename inside the repo


@dataclass(frozen=True)
class DatasetSpec:
    """One production dataset and everything needed to publish it."""
    key: str                 # CLI selector: classifier, retriever, span, typer, relation
    repo_suffix: str         # HF repo suffix
    model_repo_suffix: str   # paired model repo (for cross-linking in README)
    summary: str             # one-paragraph description
    files: tuple[FilePlan, ...]
    format_notes: str        # row format description for the README


SPECS: list[DatasetSpec] = [
    DatasetSpec(
        key="classifier",
        repo_suffix="darkmem-classifier-dataset",
        model_repo_suffix="darkmem-classifier-v1",
        summary=(
            "Memory-type classification training and evaluation data for "
            "darkmem-classifier-v1. 7-class taxonomy: fact, decision, preference, "
            "problem, reference, architecture, milestone."
        ),
        files=(
            FilePlan(
                source=ROOT / "data" / "classification" / "train_v2_aug2.jsonl",
                target="train.jsonl",
            ),
            FilePlan(
                source=REPO_ROOT / "docs" / "e2e" / "scripts" / "classification_eval" / "corpus" / "gold_v3.jsonl",
                target="test.jsonl",
            ),
        ),
        format_notes=(
            "Each line is a JSON object with keys `text` (the memory content) and "
            "`type` (the 7-class label). `train.jsonl` has 11,300 rows; `test.jsonl` "
            "is the 1,000-row held-out gold used for the accuracy 0.975 figure in "
            "PRODUCTION.md."
        ),
    ),
    DatasetSpec(
        key="retriever",
        repo_suffix="darkmem-retriever-dataset",
        model_repo_suffix="darkmem-retriever-v1",
        summary=(
            "Contrastive training + evaluation data for darkmem-retriever-v1 "
            "(bge-base-en-v1.5 fine-tuned). Query/passage pairs and hard-negative "
            "triplets for MNR + triplet-margin losses."
        ),
        files=(
            FilePlan(
                source=ROOT / "runs" / "retrieval-contrastive" / "train_pairs_7k_clean.jsonl",
                target="train_pairs.jsonl",
            ),
            FilePlan(
                source=ROOT / "runs" / "retrieval-contrastive" / "train_triplets.jsonl",
                target="train_triplets.jsonl",
            ),
            FilePlan(
                source=ROOT / "runs" / "retrieval-contrastive" / "test_pairs.jsonl",
                target="test_pairs.jsonl",
            ),
        ),
        format_notes=(
            "`train_pairs.jsonl` is 7,500 positive pairs with `query` / `passage` "
            "keys. `train_triplets.jsonl` is 400 `anchor` / `positive` / `negative` "
            "triplets mined with hard-negative sampling. `test_pairs.jsonl` is the "
            "500-pair evaluation set used for MRR@10=0.884 in PRODUCTION.md; "
            "passage corpus size on the eval side is 7,000."
        ),
    ),
    DatasetSpec(
        key="span",
        repo_suffix="darkmem-span-dataset",
        model_repo_suffix="darkmem-span-v1",
        summary=(
            "Span-detection training data for darkmem-span-v1 (GLiNER small). "
            "Every entity collapsed to the single label `entity`; types are assigned "
            "by darkmem-typer-v1 in stage 2 of the two-stage NER pipeline."
        ),
        files=(
            FilePlan(source=ROOT / "data" / "splits" / "span_train.jsonl", target="train.jsonl"),
            FilePlan(source=ROOT / "data" / "splits" / "span_val.jsonl", target="val.jsonl"),
            FilePlan(source=ROOT / "data" / "splits" / "span_test.jsonl", target="test.jsonl"),
        ),
        format_notes=(
            "GLiNER format: `{tokenized_text: [...tokens], ner: [[start_token, "
            "end_token_inclusive, 'entity'], ...]}`. Inclusive-end convention — "
            "`_char_spans_to_token_spans` in the darkmem fine-tuning scripts "
            "converts from exclusive-end char offsets."
        ),
    ),
    DatasetSpec(
        key="typer",
        repo_suffix="darkmem-typer-dataset",
        model_repo_suffix="darkmem-typer-v1",
        summary=(
            "Entity-type classification training data for darkmem-typer-v1 "
            "(ModernBERT-base). 10-type coding taxonomy: tool, service, database, "
            "language, protocol, project, algorithm, artifact, concept, entity."
        ),
        files=(
            FilePlan(source=ROOT / "data" / "splits" / "typer_train.jsonl", target="train.jsonl"),
            FilePlan(source=ROOT / "data" / "splits" / "typer_val.jsonl", target="val.jsonl"),
            FilePlan(source=ROOT / "data" / "splits" / "typer_test.jsonl", target="test.jsonl"),
        ),
        format_notes=(
            "Each row is one entity mention in context with `[ENT]...[/ENT]` "
            "markers wrapping the candidate span. Keys: `text` (marker-wrapped "
            "context), `label` (one of the 10 taxonomy types). max_length 256."
        ),
    ),
    DatasetSpec(
        key="relation",
        repo_suffix="darkmem-relation-dataset",
        model_repo_suffix="darkmem-relation-base-v1",
        summary=(
            "Seq2seq relation-extraction training data for darkmem-relation-base-v1 "
            "(rebel-base, 30-type native). Two test-gold files: a 10-type gold for "
            "the v1 scoring convention and the 5-type gold introduced in schema-v2."
        ),
        files=(
            FilePlan(
                source=ROOT / "data" / "splits" / "rebel_train.jsonl",
                target="train.jsonl",
            ),
            FilePlan(
                source=ROOT / "data" / "splits" / "rebel_val.jsonl",
                target="val.jsonl",
            ),
            FilePlan(
                source=ROOT / "data" / "splits" / "rebel_coding10_test_gold.jsonl",
                target="test_gold_10type.jsonl",
            ),
            FilePlan(
                source=ROOT / "data" / "splits" / "rebel_coding5_test_gold.jsonl",
                target="test_gold_5type.jsonl",
            ),
        ),
        format_notes=(
            "`train.jsonl` / `val.jsonl`: REBEL seq2seq format `{input: <text | "
            "Entities: ...>, output: <triplet> s <subj> t <obj> TYPE}` with 30-type "
            "native labels. `test_gold_*` files carry entities + ground-truth "
            "relationships in canonical form; use `rebel_pair_rescore.py` to "
            "compute pair-wise F1 against rebel-base predictions (apply REL_MAP "
            "30->10, then REL_MAP_5 10->5 as needed)."
        ),
    ),
]


def _build_corpus_spec() -> DatasetSpec:
    """Corpus spec is assembled dynamically — the relaug survivors and noisy
    batches are open-ended directories, so glob them at build time rather
    than hand-listing every file."""
    files: list[FilePlan] = []

    # Canonical source + schema-v2 derivatives.
    canon_files = [
        ("data/v2/shared/shared_coding10_clean.jsonl", "shared/shared_coding10_clean.jsonl"),
        ("data/splits/coding10clean_train_canon.jsonl", "coding10clean/train_canon.jsonl"),
        ("data/splits/coding10clean_val_canon.jsonl", "coding10clean/val_canon.jsonl"),
        ("data/splits/coding10clean_test_canon.jsonl", "coding10clean/test_canon.jsonl"),
        ("data/splits/coding10clean_train_canon.pre-relaug.jsonl", "coding10clean/train_canon.pre-relaug.jsonl"),
        ("data/splits/coding10clean_val_canon.pre-relaug.jsonl", "coding10clean/val_canon.pre-relaug.jsonl"),
        ("data/splits/coding10clean_test_canon.pre-relaug.jsonl", "coding10clean/test_canon.pre-relaug.jsonl"),
        ("data/splits/coding5clean_train_canon.jsonl", "coding5clean/train_canon.jsonl"),
        ("data/splits/coding5clean_val_canon.jsonl", "coding5clean/val_canon.jsonl"),
        ("data/splits/coding5clean_test_canon.jsonl", "coding5clean/test_canon.jsonl"),
    ]
    for src_rel, tgt in canon_files:
        src = ROOT / src_rel
        if src.exists():
            files.append(FilePlan(source=src, target=tgt))

    # Phase-2 relaug survivors (~54 files).
    for src in sorted((ROOT / "data" / "v2" / "relaug" / "survivors").glob("*.jsonl")):
        files.append(FilePlan(source=src, target=f"relaug_survivors/{src.name}"))

    # Phase-3 noisy-batch augmentation (~10 files).
    for src in sorted((ROOT / "data" / "v2" / "noisy").glob("*.jsonl")):
        files.append(FilePlan(source=src, target=f"noisy/{src.name}"))

    return DatasetSpec(
        key="corpus",
        repo_suffix="darkmem-corpus",
        model_repo_suffix="darkmem-classifier-v1",  # arbitrary — README crosslinks all heads
        summary=(
            "Canonical training corpus for darkmem. The raw shared corpus, the "
            "10-type and 5-type canonical splits, the frozen pre-relaug val/test "
            "gold, the Phase-2 synth-relation augmentation survivors, and the "
            "Phase-3 noisy-batch augmentation. Feed this into the data-build "
            "pipeline (fine-tuning/scripts/_build_*_splits.py) to regenerate "
            "every head-specific training file."
        ),
        files=tuple(files),
        format_notes=(
            "Layout: `shared/` is the raw 14k-row clean corpus, `coding10clean/` "
            "and `coding5clean/` are the remapped canonicals, `relaug_survivors/` "
            "holds validator-accepted synth rows (per-class), `noisy/` is the "
            "noisy-batch augmentation. Every file is JSONL with the shared "
            "`{id, text, entities, relationships, memory_type, domain, source}` "
            "schema used throughout the darkmem fine-tuning pipeline. "
            "Entities use inclusive-end char offsets matching GLiNER's internal "
            "convention."
        ),
    )


SPECS.append(_build_corpus_spec())


def _render_readme(spec: DatasetSpec, repo_id: str, hf_user: str) -> str:
    file_rows = "\n".join(
        f"| `{fp.target}` | {_bytes_fmt(fp.source)} | {_line_count(fp.source)} rows |"
        for fp in spec.files
    )
    model_link = f"[{spec.model_repo_suffix}](https://huggingface.co/{hf_user}/{spec.model_repo_suffix})"
    return f"""---
tags:
  - darkmem
  - {spec.key}
language:
  - en
size_categories:
  - 1K<n<100K
---

# {spec.repo_suffix}

{spec.summary}

## Files

| file | size | rows |
|---|---|---|
{file_rows}

## Format

{spec.format_notes}

## Provenance

These are the exact files the shipping checkpoint {model_link} was trained and
evaluated on, pulled from the `fine-tuning/` tree of the darkmem repository
(private). Row counts and schemas match the descriptions in the
darkmem `PRODUCTION.md` model manifest.

## License

Dataset weights and contents are released under the same terms as the
darkmem project (internal / private). Do not redistribute without the
original license grant.
"""


def _bytes_fmt(p: Path) -> str:
    n = p.stat().st_size
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _line_count(p: Path) -> str:
    try:
        with p.open("r", encoding="utf-8") as fh:
            return f"{sum(1 for _ in fh):,}"
    except Exception:
        return "?"


def upload_one(
    spec: DatasetSpec,
    hf_user: str,
    private: bool,
    token: str | None,
    dry_run: bool,
) -> None:
    from huggingface_hub import HfApi  # noqa: PLC0415

    repo_id = f"{hf_user}/{spec.repo_suffix}"
    missing = [fp for fp in spec.files if not fp.source.exists()]
    if missing:
        print(
            f"[skip] {repo_id}: missing source files: "
            + ", ".join(str(fp.source) for fp in missing),
            file=sys.stderr,
        )
        return

    total_bytes = sum(fp.source.stat().st_size for fp in spec.files)
    size_mb = total_bytes / (1024 * 1024)

    if dry_run:
        readme = _render_readme(spec, repo_id, hf_user)
        print(
            f"[dryrun] {repo_id} -> would upload {len(spec.files)} file(s) "
            f"({size_mb:.1f} MB), private={private}, write README ({len(readme)} chars)"
        )
        for fp in spec.files:
            print(f"  {fp.source.name} -> {fp.target}  ({_bytes_fmt(fp.source)})")
        return

    api = HfApi(token=token)
    print(f"[create] {repo_id} (private={private})")
    api.create_repo(repo_id, repo_type="dataset", private=private, exist_ok=True)

    with tempfile.TemporaryDirectory() as staging:
        staging_path = Path(staging)
        for fp in spec.files:
            dst = staging_path / fp.target
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp.source, dst)
        (staging_path / "README.md").write_text(
            _render_readme(spec, repo_id, hf_user), encoding="utf-8"
        )

        print(f"[upload] {repo_id} <- {len(spec.files)} file(s) + README ({size_mb:.1f} MB)")
        api.upload_folder(
            repo_id=repo_id,
            repo_type="dataset",
            folder_path=str(staging_path),
            commit_message=f"Upload {spec.repo_suffix} from darkmem fine-tuning corpus",
        )
    print(f"[done]   https://huggingface.co/datasets/{repo_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf-user", required=True, help="HuggingFace username or org.")
    ap.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="private",
        help="Repo visibility (default: private).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print the plan; do nothing.")
    ap.add_argument(
        "--only",
        nargs="+",
        metavar="KEY",
        help=f"Upload only these keys: {', '.join(s.key for s in SPECS)}",
    )
    ap.add_argument(
        "--token",
        default=os.environ.get("HF_TOKEN"),
        help="HF write token (env HF_TOKEN otherwise).",
    )
    args = ap.parse_args()

    if not args.dry_run and not args.token:
        print("error: HF_TOKEN env or --token required for real uploads", file=sys.stderr)
        return 2

    specs = SPECS if not args.only else [s for s in SPECS if s.key in args.only]
    if args.only:
        unknown = set(args.only) - {s.key for s in SPECS}
        if unknown:
            print(f"error: unknown keys: {sorted(unknown)}", file=sys.stderr)
            return 2

    private = args.visibility == "private"
    for spec in specs:
        upload_one(spec, args.hf_user, private, args.token, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
