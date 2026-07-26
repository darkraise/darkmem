"""Append-only JSONL run ledger.

One JSON object per line, one line per eval run. `record()` only ever opens
the file in append mode, so prior lines are never rewritten -- a regression
is always diffable against the run that preceded it. The ledger is a generic
store: it round-trips whatever keys the caller passes (run id, timestamp,
corpus id, fingerprint, git sha, metric payload, ...) without enforcing a
schema. Values must be JSON-native -- anything else raises ``TypeError``
from ``record()`` rather than being coerced into a lookalike that reads
back as a different type. The caller stamps the timestamp, not this
module, so the recorded value always reflects when the run itself happened
rather than when it happened to reach disk.
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent / "runs" / "ledger.jsonl"


def record(run: dict, path: str | os.PathLike = DEFAULT_PATH) -> None:
    # Serialized before the file is opened, so a value JSON cannot represent
    # raises here and leaves the ledger untouched. No ``default=`` coercion:
    # a Decimal must fail loudly at record time rather than read back as a
    # string that compares lexicographically against a later run's float.
    payload = (json.dumps(run, ensure_ascii=False) + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as fh:
        if _ends_mid_line(fh):
            fh.write(b"\n")
        fh.write(payload)


def _ends_mid_line(fh) -> bool:
    """True when the file ends in a newline-less fragment.

    A killed run leaves exactly that. Appending straight onto it would glue
    the next -- healthy -- run's JSON into one unreadable line, so the kill
    would destroy the record that followed it, not just its own.
    """
    fh.seek(0, os.SEEK_END)
    if fh.tell() == 0:
        return False
    fh.seek(-1, os.SEEK_END)
    return fh.read(1) != b"\n"


def read_runs(path: str | os.PathLike = DEFAULT_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    runs = []
    # Read bytes, decode per line. In text mode a kill that split a multibyte
    # sequence raises UnicodeDecodeError from the file iterator itself --
    # outside any per-line try -- so one damaged byte would make every record
    # in the file unreadable forever.
    with open(path, "rb") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning(
                    "skipping malformed ledger line %d in %s (likely a killed run)",
                    lineno, path,
                )
    return runs
