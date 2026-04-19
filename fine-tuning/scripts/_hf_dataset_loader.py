"""Resolve a training-data path from either a local filesystem arg or an HF dataset repo.

The darkmem trainers (`train_classifier`, `train_gliner`, `train_typer`,
`train_rebel`, `contrastive_finetune`) all accept `--train-path` / `--val-path`
CLI flags pointing at local JSONL files. After the per-head dataset repos
landed on HuggingFace (`darkraise/darkmem-*-dataset`), we also want the
trainers to pull the same files directly from the Hub so a fresh machine
can reproduce the shipping heads without holding the local corpus on disk.

The design is deliberately minimal: trainers keep accepting a local
`Path` argument. If the caller also supplies `--hf-dataset-repo` and
`--hf-dataset-file`, the loader downloads the file into the HF cache and
returns the cached path — the trainer reads from that path exactly as if
it were local. No changes inside the trainer's read loop.

Usage inside a trainer::

    from scripts._hf_dataset_loader import add_hf_args, resolve_dataset_path

    ap = argparse.ArgumentParser()
    ap.add_argument("--train-path", type=Path)
    add_hf_args(ap, purpose="train")
    args = ap.parse_args()

    train_path = resolve_dataset_path(
        local=args.train_path,
        repo=args.hf_train_repo,
        filename=args.hf_train_file,
        token=os.environ.get("HF_TOKEN"),
    )

The helper is dependency-free except for ``huggingface_hub`` (already a
transformers install-time dep).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def add_hf_args(
    parser: argparse.ArgumentParser,
    *,
    purpose: str = "train",
) -> None:
    """Register ``--hf-{purpose}-repo`` / ``--hf-{purpose}-file`` flags.

    ``purpose`` is a slug like ``train`` or ``val`` so a single trainer can
    expose both sets of flags without collision. Filenames default to
    ``train.jsonl`` / ``val.jsonl`` / ``test.jsonl`` matching the layout
    under ``darkraise/darkmem-*-dataset``.
    """
    default_file = {
        "train": "train.jsonl",
        "val": "val.jsonl",
        "test": "test.jsonl",
    }.get(purpose, f"{purpose}.jsonl")

    parser.add_argument(
        f"--hf-{purpose}-repo",
        default=None,
        help=(
            f"HuggingFace dataset repo id to pull the {purpose} split from "
            f"(e.g. darkraise/darkmem-classifier-dataset). Overrides the "
            f"local --{purpose}-path only when set."
        ),
    )
    parser.add_argument(
        f"--hf-{purpose}-file",
        default=default_file,
        help=(
            f"Filename inside the HF dataset repo (default: {default_file})."
        ),
    )


def resolve_dataset_path(
    *,
    local: Path | None,
    repo: str | None,
    filename: str | None,
    token: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Return a concrete path for a trainer to read.

    Precedence: explicit local path wins. If no local path is given and
    ``repo`` is set, download from the Hub and return the cached path.
    Raises ``ValueError`` if neither is available.
    """
    if local is not None:
        if not local.exists():
            raise FileNotFoundError(f"Dataset path not found: {local}")
        return local
    if not repo:
        raise ValueError(
            "No dataset source provided: pass a local path or --hf-*-repo."
        )
    if not filename:
        raise ValueError("--hf-*-file must be set when --hf-*-repo is used.")

    from huggingface_hub import hf_hub_download  # noqa: PLC0415

    kwargs: dict = {"repo_id": repo, "filename": filename, "repo_type": "dataset"}
    if token or os.environ.get("HF_TOKEN"):
        kwargs["token"] = token or os.environ.get("HF_TOKEN")
    if cache_dir is not None:
        kwargs["cache_dir"] = str(cache_dir)
    cached = hf_hub_download(**kwargs)
    return Path(cached)
