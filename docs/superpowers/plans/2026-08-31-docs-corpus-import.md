# Docs Corpus Import Implementation Plan (Increment 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** File the repo's `docs/` corpus into project `darkmem` through the document door (uri = repo-relative path), spot-checking block counts and oversized warnings on the way in, and write the agent-facing conventions doc the spec's increments 1, 3 and 5 all lean on. Re-runnable by construction: the `(project, uri)` upsert updates in place and the content-hash gate short-circuits unchanged files.

**Architecture:** A one-shot host-side script speaking REST at the running instance — through the real door, against the real deployed artifact, with the session cookie `POST /api/v1/auth/login` sets (`backend/app/api/auth.py:99-106` accepts cookie or bearer). Not in-process: an in-process import would need `DATABASE_URL` plumbing and would bypass the transport increment 0 just proved out. The conventions doc lands in `docs/` and is therefore itself imported by the run that follows it.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §6 (increment 5), §1 (conventions), §3 (checkpoint discipline).
**Review:** cleared with the M2 caveat (project invisible to the index) — carried below. Corpus measured 2026-08-31: `docs/` holds 714 files — **447 `.md` + 18 `.txt` = 465 parseable**; the rest (148 json, 41 html, 25 py, …) have no parser and are skipped by suffix, not errored. The spec's "446 files" is a point-in-time count; the script derives its own and hardcodes nothing.

## Prerequisites

1. **The parser-fixes plan is deployed** (`docs/superpowers/plans/2026-08-31-document-parser-fixes.md`, Task 6). Importing first re-creates the measured defect: `docs/planning/progress.md` parses to a 235,716-char single block under the commonmark preset. Verify before running:
   ```bash
   curl -s http://127.0.0.1:8000/openapi.json | grep -c oversized_blocks   # non-zero
   ```
2. **Increment 0 is not required for the import itself** (the script is REST + admin login), but the conventions doc's MCP guidance assumes it is done — see `2026-08-31-watchable-progress.md`, "Prerequisite — Increment 0".


**Added 2026-08-31 after the spec revision.** Increment 3 (the `documents.content`
column, spec §5 as revised) must ALSO land before this import runs. The spec cut the
`properties["$content"]` bridge and took the column instead, explicitly on the
argument that a baseline regeneration is cheapest while nothing is stored. Importing
~465 documents first would spend that argument and force a re-import to populate
`content`. Order is: increment 2 deployed → increment 3 deployed → this plan.

## Review findings this plan carries

- **M2 — the imported project is invisible to the project index.** `GET /api/v1/projects` derives from `memories` only (`backend/app/api/routes/projects.py:28-49`; docstring: "derived, never a registry"); document filing never registers a project. Unless memory rows already exist under project `darkmem` on the instance, the imported corpus produces a project the workspace's entry-point cards will not show. That is increment 4's backend fix (spec amendment required per the review); this plan **verifies and records** the behaviour rather than working around it.
- **m1 — the list route clamps at 200.** `GET /api/v1/documents` caps `limit` at 200 (`backend/app/api/routes/documents.py:279`) and its response carries no `total`, so no single page can show the ~465-file corpus and a client cannot even see that it was truncated. Any tree UI over one page silently drops half the corpus — increment 4's problem, noted here because this import is what makes it manifest. Verification below counts in SQL, not through the list route.
- **m3 — a byte-identical re-push never gains later increments' property writes.** The `UNCHANGED` gate returns before any row write (`backend/app/services/document_ingest.py:215-216`). When increment 3's `$content` bridge eventually lands, this corpus will **not** acquire `$content` by being re-imported unchanged — the import ordering must not assume otherwise. The forward path is increment 3's own backfill decision (review m3); this plan only refrains from claiming the re-run covers it.
- **Cost of a re-run, stated:** every `unchanged` re-push spends one real embed call, unconditionally (`document_door.py`, the unchanged-branch comment: "this door pays it once per request"). A full re-run therefore makes ~465 embed calls against the LAN Ollama box before filing anything. Cheap, not free; do not loop the script on a timer.

## Global Constraints

- **Everything goes through the door.** No direct `INSERT` into `documents`/`blocks`; the door owns the SAVEPOINT, the bounds (`MAX_CONTENT_CHARS` 1,000,000 / `MAX_BLOCKS` 5,000, `document_door.py:60-61`), the `document_filed` journal and the embed. A 422 is a per-file result to record, never a reason to bypass.
- **Suffix routing is closed and refusing** (`block_pipeline.URI_SUFFIX_SOURCE_TYPES`): the script filters to `.md`/`.markdown`/`.txt`/`.text` itself and counts what it skipped. PDFs are excluded by construction — `content` is `str` on both doors and `parse_pdf` takes bytes; a PDF through this door is a designed 422.
- **The commits carry nothing the image does:** `chore(scripts):` and `docs(agents):` — no `feat`/`fix`, so no release is cut and no redeploy is owed (the redeploy rule scopes to changes that alter the running artifact; a host-side script and a doc do not).
- **Backend tests** (for the script's small pure helper, if extracted): from `backend/`, `.venv/bin/python -m pytest -q`. The script itself is operational tooling verified by its own run report, matching the posture of `backend/scripts/e2e/`.
- Largest corpus file is 585,667 bytes (`docs/planning/progress.md`) — under `MAX_CONTENT_CHARS`; no file needs splitting.

## File Structure

```
backend/scripts/import_docs_corpus.py   # Task 1 (create)
docs/agent-conventions.md               # Task 2 (create)
```

---

### Task 1: The import script

**Files:**
- Create: `backend/scripts/import_docs_corpus.py`

**Interfaces:**
- Consumes: `POST /api/v1/auth/login` (`{"password": …}`, cookie-setting — `backend/app/api/routes/auth.py:76`); `POST /api/v1/documents` (`DocumentPutRequest`: project, uri, content — `backend/app/api/routes/documents.py:170-176`); the `oversized_blocks`/`largest_block_chars` response fields the parser-fixes plan added.
- Produces: a run report on stdout; exit 0 only when every parseable file filed.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 1 - coupling 0 - risk 1 = 2
**Approach:** inline - skip 4: REST-vs-in-process is confined to this one file and trivially reversible; REST exercises the running artifact, which is the point of importing at all.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python
"""One-shot corpus import (increment 5): file docs/ into project `darkmem`.

Re-runnable: the door's (project, uri) upsert updates in place and the
content-hash gate short-circuits unchanged files. Note the door's stated
cost — every unchanged re-push still spends one embed call — so a full
re-run makes one embed call per file before filing anything.

Everything goes through the REST door on purpose: the run doubles as an
end-to-end exercise of the deployed artifact, and the door owns the bounds,
the journal and the embed. Failures are per-file results, never aborts —
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
```

- [ ] **Step 2: Dry-run against the tree**

```bash
cd backend && .venv/bin/python scripts/import_docs_corpus.py --dry-run
```

Expected: ~465 uris, every one starting `docs/`, and a skipped-by-suffix count around 249. If the parseable count is wildly off the 465 measured on 2026-08-31, the corpus moved — fine; the script derives, the plan's number is provenance.

- [ ] **Step 3: Commit**

`chore(scripts): docs corpus import script` — no release is cut (no feat/fix), which is intended.

---

### Task 2: The agent conventions doc

**Files:**
- Create: `docs/agent-conventions.md`

**Interfaces:**
- Consumes: nothing (prose; every claim cites shipped behaviour).
- Produces: the document the import files at uri `docs/agent-conventions.md` — the conventions ship inside the store they describe.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 0 - spec 1 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the doc.** It must carry, at minimum, each of the following — every one is a stated spec decision or a shipped constraint, cited here so the writer does not re-derive them:

1. **Project naming**: `project = <repo-name>` for project artifacts, matching the `project/<repo-name>` tag convention agents already use for memories (spec §1); personal notes stay in `default`.
2. **Uri scheme**: the repo-relative path the file had (`docs/planning/progress.md`). Re-filing the same `(project, uri)` updates in place — the upsert is the identity, unlike memory capture where every door appends.
3. **Checkpoint discipline** (spec §3; the m2 limit **must be stated in the doc**):
   - Mint one `origin_key` per run at process boot and declare it on **every** `checkpoint_save` — correlation is a client-discipline property, not a system guarantee (`backend/app/services/checkpoints.py`, module docstring, final paragraph). An undeclared origin is refused, never merged.
   - Checkpoint at each meaningful step; bounds: summary ≤ 4,000 chars, ≤ 50 next-steps of ≤ 500 chars, ≤ 16,384 bytes total for next_steps.
   - **What the store serves back**: only the latest checkpoint is readable (`GET /checkpoints/latest` / `checkpoint_latest`); past summaries are unreadable from every surface, and the `checkpoint_saved` event deliberately carries no step content (write-time minimization). Checkpoints are a live watch signal, not a record — anything worth keeping goes in the ledger document at a milestone.
4. **Ledger shape**: one `planning/progress.md`-style document per project, updated at milestones via `document_put` — headings-and-prose, **never mega-tables** (the measured failure), and never per-step appends (an edit re-embeds the whole document; the door's own cost model).
5. **Index document per project** (spec D3 interim): MCP has no `document_list` by ruling (`docs/two-door-parity.md`), and the REST list pages at 200 — so each project maintains an `index.md` naming its filed uris. If this chafes, the fix is a ruling amendment by the owner, not a quiet tool addition.
6. **Optional `properties.kind` label** (`"artifact"` / `"note"`): decoration for later UI filtering; the project boundary is the separation. Note the REST/MCP put doors do not currently accept `properties` — the label is aspirational until a door serves it; say so rather than instructing agents to send a field the contract drops.
7. **Round-trip honesty**: `document_get` returns block text with markdown syntax already stripped (heading markers gone, tables flattened to cell-joined rows, `hr`/`html_block` dropped). Until increment 3's raw-content bridge lands, the store is a read-index, not a filesystem: **do not** get-edit-put a document and expect the source back; edit the source of truth and re-file.

- [ ] **Step 2: Verify the constraints hold as written** — re-read against `checkpoints.py` bounds and the spec's §1/§3 conventions; every number in the doc must match the code, not memory.

- [ ] **Step 3: Commit**

`docs(agents): artifact store and checkpoint conventions`

---

### Task 3: Run the import against the live instance and verify

**Files:** none (execution and evidence).

**Interfaces:**
- Consumes: Task 1's script, Task 2's doc (so it is in the tree when the import sweeps), the deployed parser fixes.
- Produces: the filed corpus, and a recorded verification.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 1 = 2

- [ ] **Step 1: Preconditions**

```bash
curl -s http://127.0.0.1:8000/openapi.json | grep -c oversized_blocks   # non-zero (parser fixes deployed)
./scripts/backup.sh /root/darkmem-backups                               # cheap insurance before a 465-file write
```

- [ ] **Step 2: Run**

```bash
cd backend && DARKMEM_ADMIN_PASSWORD=... .venv/bin/python scripts/import_docs_corpus.py
```

Exit 0. Record the report (outcome counts, largest trees, warning list) in the task's completion report. Expect ~27 files on the oversized-warning list (the spec's measured count of files exceeding the nomic budget) — dramatically fewer than pre-table-parsing, since the mega-tables now dissolve into rows.

- [ ] **Step 3: Verify storage, in SQL (the list route cannot show 465 files — m1)**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "SELECT count(*) FROM documents WHERE project='darkmem';"
# ≈ the script's parseable minus failures/empties

docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "SELECT b.type, count(*) FROM blocks b JOIN documents d ON d.id=b.document_id
   WHERE d.project='darkmem' GROUP BY b.type ORDER BY 2 DESC;"
# table_row present in force; no single-type anomaly

docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "SELECT d.uri, count(*) FROM blocks b JOIN documents d ON d.id=b.document_id
   WHERE d.project='darkmem' GROUP BY d.uri ORDER BY 2 DESC LIMIT 5;"
# every count under MAX_BLOCKS 5000
```

- [ ] **Step 4: Verify the door reads back**

```bash
# outline by uri
curl -s "http://127.0.0.1:8000/api/v1/documents/by-uri/outline?project=darkmem&uri=docs/design/16-documents-and-pkm.md" -b "$COOKIE_JAR" | head -c 400
# search
curl -s -X POST http://127.0.0.1:8000/api/v1/documents/search -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"query": "supersession trigger window", "project": "darkmem", "limit": 5}'
```

Outline returns headings; search returns hits with `heading_path`.

- [ ] **Step 5: Record the M2 behaviour**

```bash
curl -s http://127.0.0.1:8000/api/v1/projects -b "$COOKIE_JAR"
```

Record whether `darkmem` appears. If it does, that is memory rows under that project name, not the documents — the route groups `memories.project` only. Either way, write one line into the completion report: *"the imported project is [visible via pre-existing memories | invisible] on the project index; the index cannot reflect documents until increment 4's M2 fix"*. Do not "fix" this here; it is a spec-amendment item.

- [ ] **Step 6: Confirm nothing was left running** — the script is a foreground client and starts nothing; verify no stray processes anyway before reporting done.

## Rollback

The import is data, not code:

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem \
  -c "DELETE FROM documents WHERE project='darkmem';"
```

`blocks` cascades from `documents`, and `block_embeddings__<slug>` cascades from `blocks`, in every partition. Caveat: if any imported block has been cited as a fact source by then (none will be — the lift is on-demand and nothing here triggers it), deletion must go through `DELETE /api/v1/documents` per document instead, which withdraws provenance first (`document_door.delete_document`). The `document_filed` journal rows remain — append-only by design; deleting a document is not a content purge and the residue is the accepted T2.59 posture.

## Notes on scope

- **This plan does not make the corpus browsable.** The tree UI is increment 4, blocked on the review's M2 spec amendment; until then the corpus is reachable by search, outline and by-uri reads, and enumerable only in SQL or 200-row pages (m1).
- **This plan does not arm any recurring sync.** One shot, run by hand. A cron'd re-import would spend ~465 embed calls per tick on the unchanged path alone — and a docs/-watching loop is precisely the git-sync-back the owner ruled out (spec §7).
- **`$content` forward note (m3):** when increment 3 lands its raw-content bridge, this corpus will not gain `$content` from an unchanged re-run; increment 3 owns the backfill decision.
- Increments 3, 4, 6, 7, 8 and D1 are deliberately unplanned pending spec amendments (3, 4, 6, D1) or redesign (7, 8) per the 2026-08-31 review.
