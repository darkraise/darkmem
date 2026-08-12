"""One-off: give pre-T2.116 judge-attempt rows their pair identity.

``gold_touching_attempts`` keys on ``gold_pairs_sha256`` since T2.116's
escalation was ruled (2026-08-12). Rows written before that field existed
carry only a ``gold_sha256``, and the counter credits those through the file
key — which is correct but degrades the moment the file moves for a reason
that is not a pair change, exactly as T2.116's own content stamp did.

This walks git history for each recorded ``gold_sha256``, recovers the
`gold.json` that hashes to it, and stamps the pair hash that file actually
carried. It is **evidence recovery, never invention**: a row whose gold
state cannot be found in history is left alone rather than guessed at, and
nothing is ever overwritten.

The ledger is gitignored machine-local state, so this is run per machine and
is idempotent. Run from anywhere:

    python scripts/benchlib/backfill_attempt_pair_hashes.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import entailment_gold, ledger  # noqa: E402

ATTEMPT_KIND = "judge_qualification_attempt"
GOLD_REPO_PATH = "backend/scripts/benchlib/entailment/gold.json"


def pair_hashes_by_file_sha() -> dict[str, str]:
    """``{gold file sha: pairs hash}`` for every committed state of the gold."""
    revs = subprocess.run(
        ["git", "log", "--format=%H", "--all", "--", GOLD_REPO_PATH],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    out: dict[str, str] = {}
    for rev in revs:
        blob = subprocess.run(
            ["git", "show", f"{rev}:{GOLD_REPO_PATH}"],
            capture_output=True, cwd=REPO_ROOT,
        ).stdout
        if not blob:
            continue
        file_sha = hashlib.sha256(blob).hexdigest()
        if file_sha in out:
            continue
        try:
            doc = json.loads(blob)
        except json.JSONDecodeError:
            continue
        out[file_sha] = entailment_gold.pairs_content_hash(doc["pairs"])
    return out


def backfill(path: Path, *, dry_run: bool = False) -> tuple[int, int]:
    rows = list(ledger.read_runs(path))
    known = pair_hashes_by_file_sha()

    stamped = unresolved = 0
    for row in rows:
        if row.get("kind") != ATTEMPT_KIND or row.get("gold_pairs_sha256"):
            continue
        pairs_sha = known.get(row.get("gold_sha256", ""))
        if pairs_sha is None:
            unresolved += 1
            print(f"  unresolved: gold {row.get('gold_sha256', '?')[:8]} "
                  f"is not in git history — left as-is")
            continue
        row["gold_pairs_sha256"] = pairs_sha
        row["gold_pairs_sha256_backfilled"] = True
        stamped += 1
        print(f"  stamped: gold {row['gold_sha256'][:8]} -> pairs {pairs_sha[:8]}")

    if stamped and not dry_run:
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return stamped, unresolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger-path", default=str(ledger.DEFAULT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    stamped, unresolved = backfill(Path(args.ledger_path), dry_run=args.dry_run)
    verb = "would stamp" if args.dry_run else "stamped"
    print(f"{verb} {stamped} attempt row(s); {unresolved} unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
