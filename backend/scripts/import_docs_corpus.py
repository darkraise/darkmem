#!/usr/bin/env python
"""One-shot corpus import (increment 5): file docs/ into project `darkmem`.

Re-runnable: the door's (project, uri) upsert updates in place and the
content-hash gate short-circuits unchanged files. Note the door's stated
cost -- every unchanged re-push still spends one embed call -- so a full
re-run makes one embed call per file before filing anything. Do not loop
this on a timer.

Everything goes through the REST door on purpose: the run doubles as an
end-to-end exercise of the deployed artifact, and the door owns the bounds,
the journal and the embed. Failures are per-file results, never aborts --
the same isolation posture as `ingest_documents`.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

import httpx

# Mirrors block_pipeline.URI_SUFFIX_SOURCE_TYPES minus PDF, which the str-only
# door cannot carry (a designed 422, not an unimplemented case).
PARSEABLE_SUFFIXES = {".md", ".markdown", ".txt", ".text"}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--project", default="darkmem")
    ap.add_argument("--root", default=str(repo_root / "docs"))
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be filed; no login, no writes")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    parseable = [p for p in files if p.suffix.lower() in PARSEABLE_SUFFIXES]
    skipped_suffix = len(files) - len(parseable)

    if args.dry_run:
        for p in parseable:
            print(p.relative_to(repo_root).as_posix())
        print(f"\n{len(parseable)} parseable, {skipped_suffix} skipped by suffix")
        return 0

    password = os.environ.get("DARKMEM_ADMIN_PASSWORD") or getpass.getpass(
        "admin password: "
    )

    outcomes: dict[str, int] = {}
    failures: list[tuple[str, str]] = []
    warned: list[tuple[str, int, int]] = []       # (uri, oversized, largest)
    biggest: list[tuple[int, str]] = []           # (blocks_filed, uri)
    skipped_empty = 0

    # Generous per-request timeout: the door parses AND embeds synchronously,
    # and the largest file dissolves into thousands of row blocks.
    timeout = httpx.Timeout(600.0, connect=10.0)
    with httpx.Client(base_url=args.base_url, timeout=timeout) as client:
        resp = client.post("/api/v1/auth/login", json={"password": password})
        resp.raise_for_status()  # the cookie jar now carries the session

        for path in parseable:
            uri = path.relative_to(repo_root).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                failures.append((uri, f"not utf-8: {exc}"))
                continue
            if not content:
                skipped_empty += 1     # DocumentPutRequest: min_length=1
                continue

            resp = client.post(
                "/api/v1/documents",
                json={"project": args.project, "uri": uri, "content": content},
            )
            if resp.status_code != 201:
                failures.append((uri, f"{resp.status_code}: {resp.text[:200]}"))
                continue
            data = resp.json()
            outcomes[data["outcome"]] = outcomes.get(data["outcome"], 0) + 1
            biggest.append((data["blocks_filed"], uri))
            if data.get("oversized_blocks"):
                warned.append(
                    (uri, data["oversized_blocks"], data["largest_block_chars"])
                )
            print(f"{data['outcome']:9} {data['blocks_filed']:5} blocks  {uri}")

    print(f"\n== {args.project} import report ==")
    print(f"parseable: {len(parseable)}  skipped by suffix: {skipped_suffix}"
          f"  skipped empty: {skipped_empty}")
    print(f"outcomes: {outcomes}")
    print("\nlargest trees (MAX_BLOCKS is 5000):")
    for count, uri in sorted(biggest, reverse=True)[:10]:
        print(f"  {count:5}  {uri}")
    if warned:
        print(f"\noversized-block warnings ({len(warned)} files):")
        for uri, count, largest in sorted(warned, key=lambda w: -w[2])[:10]:
            print(f"  {count:3} blocks over the floor, largest {largest:7}  {uri}")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for uri, err in failures:
            print(f"  {uri}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
