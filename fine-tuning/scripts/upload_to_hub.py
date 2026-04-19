"""Upload the five darkmem production heads to HuggingFace Hub.

For each model a repo is created (if missing), a README.md is generated from
the known metadata, and the model folder is uploaded. Defaults to private
repos so the models don't leak until you flip visibility yourself.

Usage::

    # Private repos under your user:
    python -m scripts.upload_to_hub --hf-user darkraise --token $HF_TOKEN

    # Dry-run (print what would happen):
    python -m scripts.upload_to_hub --hf-user darkraise --dry-run

    # Subset of heads:
    python -m scripts.upload_to_hub --hf-user darkraise --only span retriever

Requires ``huggingface_hub`` (already a transformers dependency).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


@dataclass(frozen=True)
class HeadSpec:
    """One production head and everything needed to describe it on the Hub."""

    key: str
    repo_suffix: str
    folder: Path
    base_model: str
    library: str  # "gliner" | "transformers" | "sentence-transformers"
    pipeline_tag: str
    summary: str
    metric_line: str
    tags: tuple[str, ...]


SPECS: list[HeadSpec] = [
    HeadSpec(
        key="classifier",
        repo_suffix="darkmem-classifier-v1",
        folder=MODELS_DIR / "darkmem-classifier-v1" / "best",
        base_model="answerdotai/ModernBERT-base",
        library="transformers",
        pipeline_tag="text-classification",
        summary=(
            "Seven-class memory-type classifier for darkmem. Labels: fact, decision, "
            "preference, problem, reference, architecture, milestone."
        ),
        metric_line="accuracy 0.975 / macro F1 0.975 on 1,000-row gold (`gold_v3.jsonl`).",
        tags=("text-classification", "memory", "darkmem", "modernbert"),
    ),
    HeadSpec(
        key="retriever",
        repo_suffix="darkmem-retriever-v1",
        folder=MODELS_DIR / "darkmem-retriever-v1",
        base_model="BAAI/bge-base-en-v1.5",
        library="sentence-transformers",
        pipeline_tag="sentence-similarity",
        summary=(
            "Contrastively fine-tuned bge-base encoder for darkmem semantic search. "
            'Query prefix: "Represent this sentence for searching relevant passages: ".'
        ),
        metric_line="MRR@10 0.884 / R@1 0.872 / R@5 0.904 / R@10 0.910 on 500-pair test.",
        tags=("sentence-similarity", "memory", "darkmem", "bge", "feature-extraction"),
    ),
    HeadSpec(
        key="span",
        repo_suffix="darkmem-span-v1",
        folder=MODELS_DIR / "darkmem-span-v1" / "best",
        base_model="urchade/gliner_small-v2.1",
        library="gliner",
        pipeline_tag="token-classification",
        summary=(
            "Stage-1 entity span detector (single-label `entity`). Types are assigned "
            "by `darkmem-typer-v1` in stage 2."
        ),
        metric_line="name recall 0.972 on 90-gold, 0.800 on coding10 test.",
        tags=("token-classification", "gliner", "ner", "darkmem"),
    ),
    HeadSpec(
        key="typer",
        repo_suffix="darkmem-typer-v1",
        folder=MODELS_DIR / "darkmem-typer-v1" / "best",
        base_model="answerdotai/ModernBERT-base",
        library="transformers",
        pipeline_tag="text-classification",
        summary=(
            "Stage-2 entity typer. Consumes text with `[ENT]...[/ENT]` markers around "
            "the candidate span and classifies into the 10-type coding taxonomy "
            "(tool, service, database, language, protocol, project, algorithm, "
            "artifact, concept, entity)."
        ),
        metric_line="accuracy 0.692 / macro F1 0.678; two-stage type acc 0.83 on 90-gold.",
        tags=("text-classification", "memory", "darkmem", "modernbert", "ner"),
    ),
    HeadSpec(
        key="relation",
        repo_suffix="darkmem-relation-base-v1",
        folder=MODELS_DIR / "darkmem-relation-base-v1" / "best",
        base_model="Babelscape/rebel-base",
        library="transformers",
        pipeline_tag="text2text-generation",
        summary=(
            "Seq2seq relation extractor (rebel-base, 139M params). Output format: "
            "`<triplet> source <subj> target <obj> type`. Emits the native REBEL 30-type "
            "set; collapse to 10 at inference via REL_MAP, then to the 5-type schema-v2 "
            "set via REL_MAP_5. See `backend/app/services/extraction.clean_extraction`."
        ),
        metric_line="F1 0.602 (10-type) / 0.618 (5-type rescored); 606 MB peak VRAM, 426 ms/row.",
        tags=("text2text-generation", "relation-extraction", "rebel", "darkmem"),
    ),
]


def _render_readme(spec: HeadSpec, repo_id: str) -> str:
    """Generate a minimal but useful model card."""
    usage_block = _usage_block(spec, repo_id)
    tags_yaml = "\n".join(f"- {t}" for t in spec.tags)
    return f"""---
library_name: {spec.library}
pipeline_tag: {spec.pipeline_tag}
base_model: {spec.base_model}
language:
- en
tags:
{tags_yaml}
---

# {spec.repo_suffix}

{spec.summary}

## Metrics

{spec.metric_line}

## Base model

[{spec.base_model}](https://huggingface.co/{spec.base_model})

## Usage

{usage_block}

## License

Inherits the license of the base model. Fine-tuned weights published under the
same terms unless noted otherwise in the repo.

## Provenance

Fine-tuned as part of [darkmem](https://github.com/) — a centralized memory
system for AI agents. Training recipe and evaluation scripts are in the
`fine-tuning/` subtree of the darkmem repository.
"""


def _usage_block(spec: HeadSpec, repo_id: str) -> str:
    if spec.library == "gliner":
        return f"""```python
from gliner import GLiNER

model = GLiNER.from_pretrained("{repo_id}")
spans = model.predict_entities("your text here", ["entity"], threshold=0.4)
```"""
    if spec.library == "sentence-transformers":
        return f"""```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("{repo_id}")
emb = model.encode(
    "Represent this sentence for searching relevant passages: " + "your query",
    normalize_embeddings=True,
)
```"""
    if spec.pipeline_tag == "text2text-generation":
        return f"""```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("{repo_id}")
model = AutoModelForSeq2SeqLM.from_pretrained("{repo_id}")
inp = tok("your text | Entities: ...", return_tensors="pt", truncation=True)
out = model.generate(**inp, num_beams=4, max_length=128)
print(tok.decode(out[0], skip_special_tokens=False))
```"""
    return f"""```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

tok = AutoTokenizer.from_pretrained("{repo_id}", trust_remote_code=True)
model = AutoModelForSequenceClassification.from_pretrained("{repo_id}", trust_remote_code=True)
```"""


def upload_one(spec: HeadSpec, hf_user: str, private: bool, token: str | None, dry_run: bool) -> None:
    repo_id = f"{hf_user}/{spec.repo_suffix}"
    if not spec.folder.exists():
        print(f"[skip]   {repo_id} — local folder missing: {spec.folder}")
        return
    if not any(spec.folder.iterdir()):
        print(f"[skip]   {repo_id} — local folder is empty: {spec.folder}")
        return

    readme_path = spec.folder / "README.md"
    readme_body = _render_readme(spec, repo_id)

    if dry_run:
        total_bytes = sum(p.stat().st_size for p in spec.folder.rglob("*") if p.is_file())
        print(
            f"[dryrun] {repo_id} — would upload {spec.folder} ({total_bytes/1_000_000:.1f} MB), "
            f"private={private}, write README ({len(readme_body)} chars)"
        )
        return

    from huggingface_hub import HfApi  # noqa: PLC0415
    api = HfApi(token=token)
    print(f"[create] {repo_id} (private={private})")
    api.create_repo(repo_id=repo_id, repo_type="model", private=private, exist_ok=True, token=token)

    print(f"[write]  {repo_id}/README.md")
    readme_path.write_text(readme_body, encoding="utf-8")

    print(f"[upload] {repo_id} <- {spec.folder}")
    api.upload_folder(
        folder_path=str(spec.folder),
        repo_id=repo_id,
        repo_type="model",
        token=token,
        commit_message=f"Upload {spec.repo_suffix} from darkmem fine-tuning pipeline",
    )
    print(f"[done]   https://huggingface.co/{repo_id}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--hf-user", required=True, help="Your HuggingFace username or org.")
    p.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="private",
        help="Repo visibility (default: private).",
    )
    p.add_argument("--dry-run", action="store_true", help="Print what would happen, do nothing.")
    p.add_argument(
        "--only",
        nargs="+",
        metavar="HEAD",
        help="Upload only these heads (keys: classifier, retriever, span, typer, relation).",
    )
    p.add_argument(
        "--token",
        default=os.getenv("HF_TOKEN"),
        help="HuggingFace auth token (env HF_TOKEN otherwise).",
    )
    args = p.parse_args()

    if not args.dry_run and not args.token:
        print("error: --token or $HF_TOKEN is required for real uploads", file=sys.stderr)
        return 2

    specs = SPECS if not args.only else [s for s in SPECS if s.key in args.only]
    if args.only and len(specs) != len(args.only):
        unknown = set(args.only) - {s.key for s in SPECS}
        print(f"error: unknown head keys: {sorted(unknown)}", file=sys.stderr)
        return 2

    private = args.visibility == "private"
    for spec in specs:
        upload_one(spec, args.hf_user, private=private, token=args.token, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
