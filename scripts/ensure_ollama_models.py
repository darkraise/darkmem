"""Ensure every LLM model the darkmem pipeline configures is present on Ollama.

Ollama hosts decoder-only LLMs; the darkmem fine-tuned heads (GLiNER,
ModernBERT, REBEL, bge) are NOT served by Ollama. For those, push weights
to HuggingFace Hub via ``fine-tuning/scripts/upload_to_hub.py``. This
script handles the Ollama side only: it inspects either the running
backend's DB config or the default settings and ensures the Ollama daemon
has each referenced model pulled.

Behaviour per model:
  * If the model tag is already present locally, skip.
  * Otherwise run ``ollama pull <tag>``.
  * ``--dry-run`` reports the plan without pulling.

Usage::

    # Use defaults from backend/app/config.py:
    python scripts/ensure_ollama_models.py

    # Use the live DB config (reads /api/v1/config/llm via the running backend):
    python scripts/ensure_ollama_models.py --from-backend --api http://localhost:8000

    # Dry run:
    python scripts/ensure_ollama_models.py --dry-run

    # Override the Ollama host (default uses OLLAMA_HOST env var or http://localhost:11434):
    python scripts/ensure_ollama_models.py --ollama-host http://192.168.0.197:11434

    # Force re-pull (useful for catching remote tag updates):
    python scripts/ensure_ollama_models.py --force
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]


def _default_ollama_host() -> str:
    env = os.environ.get("OLLAMA_HOST")
    if env:
        return env if env.startswith("http") else f"http://{env}"
    return "http://localhost:11434"


def _installed_models(host: str) -> set[str]:
    """Query ``/api/tags`` for the list of locally pulled models."""
    try:
        req = Request(f"{host.rstrip('/')}/api/tags")
        with urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"warning: could not reach Ollama at {host}: {exc}", file=sys.stderr)
        return set()
    return {entry["name"] for entry in data.get("models", [])}


def _models_from_settings() -> list[tuple[str, str]]:
    """Read the env-driven defaults in ``backend/app/config.Settings``.

    Returns a list of (purpose, model_tag) pairs, filtered to Ollama purposes.
    """
    backend_path = REPO_ROOT / "backend"
    sys.path.insert(0, str(backend_path))
    try:
        from app.config import settings  # type: ignore
    finally:
        sys.path.pop(0)

    purposes = {
        "embedding": settings.llm_embedding,
        "extraction": settings.llm_extraction,
        "classification": getattr(settings, "llm_classification", None),
        "reasoning": settings.llm_reasoning,
        "summarization": settings.llm_summarization,
        "reranker": settings.llm_reranker,
    }
    out: list[tuple[str, str]] = []
    for purpose, cfg in purposes.items():
        if cfg is None:
            continue
        if cfg.provider != "ollama":
            continue
        if not cfg.model:
            continue
        out.append((purpose, cfg.model))
    return out


def _models_from_backend(api_url: str, token: str | None) -> list[tuple[str, str]]:
    """GET ``/api/v1/config/llm`` from the live backend and extract Ollama tags."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{api_url.rstrip('/')}/api/v1/config/llm", headers=headers)
    with urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    out: list[tuple[str, str]] = []
    for purpose, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("provider") != "ollama":
            continue
        tag = cfg.get("model")
        if tag:
            out.append((purpose, tag))
    return out


def _dedup_by_tag(items: list[tuple[str, str]]) -> list[tuple[list[str], str]]:
    """Merge entries so each tag is pulled once even if multiple purposes share it."""
    grouped: dict[str, list[str]] = {}
    for purpose, tag in items:
        grouped.setdefault(tag, []).append(purpose)
    return [(purposes, tag) for tag, purposes in grouped.items()]


def _pull(tag: str, host: str, dry_run: bool) -> bool:
    """Run ``ollama pull`` against the host. Returns True on success or dry-run."""
    env = os.environ.copy()
    env["OLLAMA_HOST"] = host
    cmd = ["ollama", "pull", tag]
    if dry_run:
        print(f"  [dry-run] would run: OLLAMA_HOST={host} {' '.join(cmd)}")
        return True
    print(f"  pulling {tag} from {host} ...")
    try:
        result = subprocess.run(cmd, env=env, check=False)
    except FileNotFoundError:
        print(
            "error: `ollama` CLI not on PATH. Install from https://ollama.com/download "
            "or run against the HTTP API directly.",
            file=sys.stderr,
        )
        return False
    if result.returncode != 0:
        print(f"  pull failed with exit {result.returncode}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--from-backend",
        action="store_true",
        help="Read LLM config from the running backend instead of app.config defaults.",
    )
    ap.add_argument(
        "--api",
        default=os.environ.get("DARKMEM_API", "http://localhost:8000"),
        help="darkmem backend base URL (used with --from-backend).",
    )
    ap.add_argument(
        "--token",
        default=os.environ.get("DARKMEM_ADMIN_TOKEN"),
        help="Admin JWT for the backend (required when --from-backend hits an auth-enforced instance).",
    )
    ap.add_argument(
        "--ollama-host",
        default=_default_ollama_host(),
        help="Ollama HTTP host (default: $OLLAMA_HOST or http://localhost:11434).",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Pull even if the tag is already installed (refreshes remote tags).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without pulling.",
    )
    args = ap.parse_args()

    if args.from_backend:
        try:
            pairs = _models_from_backend(args.api, args.token)
        except Exception as exc:
            print(f"error: could not read config from {args.api}: {exc}", file=sys.stderr)
            return 1
        source_label = f"backend {args.api}"
    else:
        pairs = _models_from_settings()
        source_label = "backend/app/config.py defaults"

    if not pairs:
        print("No Ollama-provider LLMs configured. Nothing to do.")
        return 0

    grouped = _dedup_by_tag(pairs)
    print(f"LLM tags from {source_label} (deduped):")
    for purposes, tag in grouped:
        print(f"  {tag}  <-  {', '.join(sorted(purposes))}")

    installed = _installed_models(args.ollama_host)
    print(f"Ollama at {args.ollama_host} currently has {len(installed)} model(s).")

    to_pull: list[str] = []
    for _, tag in grouped:
        if not args.force and tag in installed:
            print(f"  present: {tag} -> skip")
            continue
        to_pull.append(tag)

    if not to_pull:
        print("All required models are already present.")
        return 0

    print(f"\nPlan: pull {len(to_pull)} model(s).")
    failures: list[str] = []
    for tag in to_pull:
        ok = _pull(tag, args.ollama_host, args.dry_run)
        if not ok:
            failures.append(tag)

    if failures:
        print(f"\n{len(failures)} pull(s) failed: {', '.join(failures)}", file=sys.stderr)
        return 2
    print("\nAll required Ollama models are available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
