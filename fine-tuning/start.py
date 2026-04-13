"""End-to-end fine-tuning pipeline: generate data, validate, train, evaluate.

Runs all steps sequentially, stopping on failure. Each step can be skipped
if its output already exists (--resume) or run individually (--step).

Usage:
    python start.py              # full pipeline
    python start.py --resume     # skip steps whose output already exists
    python start.py --step train # run only the training step
    python start.py --cpu        # force CPU for training and evaluation
    python start.py --dry-run    # show what would run without executing
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
DATA_RAW = ROOT / "data" / "raw"
DATA_SPLITS = ROOT / "data" / "splits"
MODELS = ROOT / "models"
GLINER_MODEL = MODELS / "gliner-darkmem" / "best"
REBEL_MODEL = MODELS / "rebel-darkmem" / "best"

STEPS = ["deps", "generate", "validate", "train-gliner", "train-rebel", "evaluate"]


def run_cmd(label: str, cmd: list[str], dry_run: bool = False) -> bool:
    print(f"\n{'='*60}", flush=True)
    print(f"  {label}", flush=True)
    print(f"  > {' '.join(cmd)}", flush=True)
    print(f"{'='*60}\n", flush=True)

    if dry_run:
        print("  [dry-run] skipped\n", flush=True)
        return True

    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        print(f"\n  FAILED (exit code {result.returncode}, {elapsed:.0f}s)", flush=True)
        return False

    print(f"\n  OK ({elapsed:.0f}s)", flush=True)
    return True


def check_deps(dry_run: bool) -> bool:
    print("\n  Checking dependencies...", flush=True)
    if dry_run:
        print("  [dry-run] skipped\n", flush=True)
        return True

    missing = []
    try:
        import gliner  # noqa: F401
    except ImportError:
        missing.append("gliner")
    try:
        import gliner.training  # noqa: F401
    except ImportError:
        if "gliner" not in missing:
            missing.append("gliner (training support)")
    try:
        import transformers  # noqa: F401
    except ImportError:
        missing.append("transformers")
    try:
        import datasets  # noqa: F401
    except ImportError:
        missing.append("datasets")
    try:
        import torch  # noqa: F401
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}", flush=True)
            print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB", flush=True)
        else:
            print("  WARNING: CUDA not available, training will use CPU (much slower)", flush=True)
    except ImportError:
        missing.append("torch")

    if missing:
        print(f"\n  Missing packages: {', '.join(missing)}", flush=True)
        print(f"  Run: pip install -r requirements.txt", flush=True)
        return False

    print("  All dependencies OK", flush=True)
    return True


def has_raw_data() -> bool:
    return DATA_RAW.exists() and any(DATA_RAW.glob("*.jsonl"))


def has_splits() -> bool:
    return all(
        (DATA_SPLITS / f).exists()
        for f in ["gliner_train.jsonl", "gliner_val.jsonl", "rebel_train.jsonl", "rebel_val.jsonl"]
    )


def has_gliner_model() -> bool:
    return GLINER_MODEL.exists() and any(GLINER_MODEL.iterdir())


def has_rebel_model() -> bool:
    return REBEL_MODEL.exists() and any(REBEL_MODEL.iterdir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tuning pipeline")
    parser.add_argument("--step", choices=STEPS, help="Run only this step")
    parser.add_argument("--resume", action="store_true", help="Skip steps whose output exists")
    parser.add_argument("--cpu", action="store_true", help="Force CPU for training/eval")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without running")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for data generation")
    parser.add_argument("--gliner-epochs", type=int, default=5, help="GLiNER training epochs")
    parser.add_argument("--gliner-lr", type=float, default=1e-5, help="GLiNER learning rate")
    parser.add_argument("--gliner-batch-size", type=int, default=16, help="GLiNER batch size")
    parser.add_argument("--rebel-epochs", type=int, default=10, help="REBEL training epochs")
    parser.add_argument("--rebel-lr", type=float, default=5e-5, help="REBEL learning rate")
    parser.add_argument("--rebel-batch-size", type=int, default=16, help="REBEL batch size")
    parser.add_argument("--hf-token", type=str, default="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", help="Hugging Face API token for gated models")
    args = parser.parse_args()

    py = sys.executable
    steps_to_run = [args.step] if args.step else STEPS
    cpu_flag = ["--cpu"] if args.cpu else []
    hf_flag = ["--hf-token", args.hf_token] if args.hf_token else []
    t_total = time.perf_counter()

    # --- deps ---
    if "deps" in steps_to_run:
        if not check_deps(args.dry_run):
            return 1

    # --- generate ---
    if "generate" in steps_to_run:
        if args.resume and has_raw_data():
            print("\n  [resume] Raw data exists, skipping generation", flush=True)
        else:
            ok = run_cmd(
                "Step 1/5: Generate training data (8,000 examples)",
                [py, "-m", "scripts.generate_data", "--seed", str(args.seed)],
                dry_run=args.dry_run,
            )
            if not ok:
                return 1

    # --- validate ---
    if "validate" in steps_to_run:
        if args.resume and has_splits():
            print("\n  [resume] Splits exist, skipping validation", flush=True)
        else:
            ok = run_cmd(
                "Step 2/5: Validate and split data",
                [py, "-m", "scripts.validate_data", "--fix", "--seed", str(args.seed)],
                dry_run=args.dry_run,
            )
            if not ok:
                return 1

    # --- train-gliner ---
    if "train-gliner" in steps_to_run:
        if args.resume and has_gliner_model():
            print("\n  [resume] GLiNER model exists, skipping training", flush=True)
        else:
            ok = run_cmd(
                "Step 3/5: Fine-tune GLiNER (~25 min on GPU)",
                [
                    py, "-m", "scripts.train_gliner",
                    "--epochs", str(args.gliner_epochs),
                    "--lr", str(args.gliner_lr),
                    "--batch-size", str(args.gliner_batch_size),
                    *cpu_flag, *hf_flag,
                ],
                dry_run=args.dry_run,
            )
            if not ok:
                return 1

    # --- train-rebel ---
    if "train-rebel" in steps_to_run:
        if args.resume and has_rebel_model():
            print("\n  [resume] REBEL model exists, skipping training", flush=True)
        else:
            ok = run_cmd(
                "Step 4/5: Fine-tune REBEL (~2 hours on GPU)",
                [
                    py, "-m", "scripts.train_rebel",
                    "--epochs", str(args.rebel_epochs),
                    "--lr", str(args.rebel_lr),
                    "--batch-size", str(args.rebel_batch_size),
                    *cpu_flag, *hf_flag,
                ],
                dry_run=args.dry_run,
            )
            if not ok:
                return 1

    # --- evaluate ---
    if "evaluate" in steps_to_run:
        ok = run_cmd(
            "Step 5/5: Evaluate fine-tuned pipeline",
            [py, "-m", "scripts.evaluate", *cpu_flag],
            dry_run=args.dry_run,
        )
        if not ok:
            return 1

    elapsed = time.perf_counter() - t_total
    print(f"\n{'='*60}", flush=True)
    print(f"  Pipeline complete in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)
    print(f"{'='*60}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
