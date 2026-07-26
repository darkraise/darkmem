"""Append-only JSONL run ledger.

One JSON object per line, one line per eval run. `record()` only ever opens
the file in append mode, so prior lines are never rewritten -- a regression
is always diffable against the run that preceded it. The ledger is a generic
store: it round-trips whatever keys the caller passes (run id, timestamp,
corpus id, fingerprint, git sha, metric payload, ...) without enforcing a
schema. The caller stamps the timestamp, not this module, so the recorded
value always reflects when the run itself happened rather than when it
happened to reach disk.
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent / "runs" / "ledger.jsonl"


def record(run: dict, path: str | os.PathLike = DEFAULT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(run, ensure_ascii=False, default=str) + "\n")


def read_runs(path: str | os.PathLike = DEFAULT_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    runs = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(
                    "skipping malformed ledger line %d in %s (likely a killed run)",
                    lineno, path,
                )
    return runs
