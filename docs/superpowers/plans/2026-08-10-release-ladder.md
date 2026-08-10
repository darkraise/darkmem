# Release Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give darkmem a release ladder — cut and deploy `v0.1` from the 232
tasks already done, then let an autonomous loop drive v0.2→v0.4, stopping at
each tag.

**Architecture:** Three durable artifacts (`RELEASES.md`, `CHANGELOG.md`, a
`Version` column on `progress.md`) make "which release is this for?" answerable
from the repo alone, so an agent that lost its context rebuilds the picture by
reading. One structural change — gate dependency moves from the epic to the task
— stops measurement gates serialising code work. A small `scripts/release.sh`
performs the four steps a release actually is, because they repeat four or more
times.

**Tech Stack:** Python 3.13 + pytest (planning-doc assertions live in
`backend/tests/test_planning_docs.py`), bash, Docker Compose.

**Design spec:** `docs/superpowers/specs/2026-08-10-release-milestones-and-autonomous-loop-design.md`

## Global Constraints

- **Proportionality test:** does this artifact outlive the task? If no, do the
  simple thing inline. (spec §8)
- **`progress.md` is canonical on `master`**, never on an epic branch (runbook §6).
- **The schema freeze does NOT happen in this plan.** `v0.1` is a dev deploy
  with disposable data; the baseline stays regenerable and `gate.sh`'s
  single-revision assertion stays live. (spec §2)
- **`gold.json` is never written by this plan.**
- Conventional commits, one logical change each; body explains what and why.
- Language: English only, everywhere.
- Every task ends green on `./scripts/gate.sh` unless the task says otherwise.

---

### Task 1: The release ledger

**Files:**
- Create: `docs/planning/RELEASES.md`
- Modify: `.worktrees/master-claim/docs/planning/progress.md` (add a `Version` column)
- Modify: `docs/planning/scripts/gen_progress.py` (emit the new column)
- Test: `backend/tests/test_planning_docs.py`

**Interfaces:**
- Produces: `RELEASES.md` with one `### vN` section per version, each holding a
  markdown list of task ids as `` - `T3.17` — title ``. The test in Step 1 parses
  exactly that shape. Later tasks and the loop read it to know what is in scope.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_planning_docs.py`:

```python
RELEASES_PATH = Path(__file__).resolve().parents[2] / "docs/planning/RELEASES.md"


def _versioned_task_ids() -> dict[str, set[str]]:
    """Task ids per version, parsed from RELEASES.md's `### vN` sections."""
    versions: dict[str, set[str]] = {}
    current = None
    for line in RELEASES_PATH.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^### (v\d+\.\d+)", line)
        if heading:
            current = heading.group(1)
            versions[current] = set()
            continue
        item = re.match(r"^- `(T[A-Z]?\d+\.\d+[a-z]?)`", line)
        if item and current:
            versions[current].add(item.group(1))
    return versions


def test_every_versioned_task_exists_in_progress():
    """A version that names a task nobody tracks is a plan nobody can execute."""
    versioned = {t for ids in _versioned_task_ids().values() for t in ids}
    rows = get_task_ids_from_progress()

    assert versioned - rows == set(), (
        f"RELEASES.md names tasks with no progress.md row: {sorted(versioned - rows)}"
    )


def test_no_task_is_assigned_to_two_versions():
    """One task ships once. Two homes means the burn-down double-counts."""
    seen: dict[str, str] = {}
    duplicated = []
    for version, ids in _versioned_task_ids().items():
        for task in ids:
            if task in seen:
                duplicated.append(f"{task}: {seen[task]} and {version}")
            seen[task] = version

    assert duplicated == [], f"tasks assigned to two versions: {duplicated}"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && .venv/bin/python -m pytest tests/test_planning_docs.py -q
```

Expected: FAIL — `FileNotFoundError` on `RELEASES.md`.

- [ ] **Step 3: Write `docs/planning/RELEASES.md`**

```markdown
# Releases

The ladder. One version per shipped feature-group; a version is cut when its
tasks are `done` and `./scripts/gate.sh --full` is green. Design:
`docs/superpowers/specs/2026-08-10-release-milestones-and-autonomous-loop-design.md`.

**`v0.1` is not the schema freeze.** Dev environment, disposable data by the
owner's decision (2026-08-10). CLAUDE.md's trigger — the first deploy whose data
must survive — remains in the future.

### v0.1 — It runs

Everything already `done`: capture, retrieval, the code graph, 21 jobs, MCP, the
SPA, both SDKs, the browser extension. No new tasks. Cut by demonstration, not
by assertion.

### v0.2 — Resume and checkpoints

- `T3.17` — Resume as a specialised inject
- `T3.18` — Checkpoints are operational, not vault knowledge
- `T3.21` — Session checkpoints / resume view

### v0.3 — Auto-context into agent tools

- `T3.10` — Truth-first content fill under a token budget
- `T3.20` — Inject records in timeline and calendar
- `T4.06` — Inject `watch` mode
- `T4.07` — Auto-scrape opt-in
- `T4.08` — Watch + curb surfaces on the Distribution tab

### v0.4 — Synthesised articles, unlabelled

- `T3.02` — `article_synthesis` productive runs
- `T3.03` — Claim-level entailment pass + coverage routing
- `T3.04` — `article_citations` — the one hard FK
- `T3.05` — Staleness gate + debounced re-synthesis
- `T3.06` — Articles tab
- `T3.23` — Articles retrieval channel + `article_embeddings` writer

## Gate track

Not parked and not a version: these produce gates, which unlock labels.
Clearing G-C and G-D ships as its own version whose headline is "badges go live".

`T2.114`, `T2.116`, `T3.22`, `T3.24`, `TH1.10`, `TH1.17`

## Parked — kept, not dropped, no version assigned

EH1 documents/PKM (15 tasks), the research agent (`T3.07`, `T3.08`), API keys
and webhooks (`T4.01`–`T4.05`), the two audit records (`T4.09`, `T4.10`), and
`T1.54`.
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && .venv/bin/python -m pytest tests/test_planning_docs.py -q
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Add the `Version` column to `progress.md` on master**

Run from the repo root. The column goes immediately after `Effort`, so the five
hand-edited state columns stay contiguous at the end:

```bash
cd /root/repositories/darkmem/.worktrees/master-claim
../../backend/.venv/bin/python - <<'PY'
import re, pathlib
V = {"T3.17": "v0.2", "T3.18": "v0.2", "T3.21": "v0.2",
     "T3.10": "v0.3", "T3.20": "v0.3", "T4.06": "v0.3", "T4.07": "v0.3", "T4.08": "v0.3",
     "T3.02": "v0.4", "T3.03": "v0.4", "T3.04": "v0.4", "T3.05": "v0.4", "T3.06": "v0.4",
     "T3.23": "v0.4",
     "T2.114": "gate", "T2.116": "gate", "T3.22": "gate", "T3.24": "gate",
     "TH1.10": "gate", "TH1.17": "gate"}
p = pathlib.Path("docs/planning/progress.md"); out = []
for line in p.read_text(encoding="utf-8").split("\n"):
    if re.match(r"^\| Task \| Title \|", line):
        line = line.replace("| Effort |", "| Effort | Version |", 1)
    elif re.match(r"^\|---\|---\|", line) and line.count("|") >= 10:
        line = line.replace("|---|", "|---|", 1)[:-1] + "---|"
    elif re.match(r"^\|\s*T[A-Z]?\d", line):
        cells = line.split(" | ")
        task = cells[0].lstrip("| ").strip()
        cells.insert(5, V.get(task, "—"))
        line = " | ".join(cells)
    out.append(line)
p.write_text("\n".join(out), encoding="utf-8")
print("Version column inserted")
PY
```

Then verify every row still has a consistent column count:

```bash
../../backend/.venv/bin/python - <<'PY'
import re, pathlib
CELL = re.compile(r"(?<!\\)\|")
bad = [l.split("|")[1].strip() for l in
       pathlib.Path("docs/planning/progress.md").read_text().split("\n")
       if re.match(r"^\|\s*T[A-Z]?\d", l) and len(CELL.split(l)) != 13]
print("malformed rows:", bad or "none")
PY
```

Expected: `malformed rows: none`.

- [ ] **Step 6: Teach the generator the new column**

In `docs/planning/scripts/gen_progress.py`, the header and separator literals and
the `prior` carry-forward window both need the extra column. Find the row-render
and header strings and add `Version` after `Effort`; widen the state window from
`cells[-6:-1]` to keep capturing exactly the five state columns (it is
end-anchored, so it already does — verify rather than change it).

Verify the generator round-trips **on a scratch copy, never in place**:

```bash
cd /root/repositories/darkmem
rm -rf /tmp/genchk && mkdir -p /tmp/genchk
cp -r .worktrees/master-claim/docs/planning/{tasks,scripts,progress.md} /tmp/genchk/
cd /tmp/genchk && ../../backend/.venv/bin/python scripts/gen_progress.py >/dev/null
diff <(grep -c '^| T' /tmp/genchk/progress.md) \
     <(grep -c '^| T' /root/repositories/darkmem/.worktrees/master-claim/docs/planning/progress.md) \
  && echo "row count preserved"
```

Expected: `row count preserved`.

- [ ] **Step 7: Commit**

```bash
cd /root/repositories/darkmem
git add docs/planning/RELEASES.md backend/tests/test_planning_docs.py
git commit -m "docs(releases): add the release ledger and pin it to progress

RELEASES.md is the ladder: one version per shipped feature-group, with the
gate track and the parked work separated so the burn-down counts only what
is actually queued. Two tests pin it to the tracker — a version naming a
task nobody tracks is a plan nobody can execute, and a task in two
versions double-counts."

cd .worktrees/master-claim
git add docs/planning/progress.md docs/planning/scripts/gen_progress.py
git commit -m "docs(progress): add the Version column

Every row now answers which release it is for. Generator updated and
round-tripped on a scratch copy first, since it destroys state when run
against a file it cannot fully reproduce."
```

---

### Task 2: Per-task gate marking

> **RESOLVED 2026-08-10 — owner ratified `(produces)`; this task then executed.**
> The stop and its reasoning are kept below because the escalation is the record
> worth having: the binary vocabulary was owner-approved hours earlier and still
> could not describe the corpus it was written for.
>
> **As executed:** three qualifiers, scope open-only (35 fields, not 236),
> `(produces)` on the six gate-track rows and bound by test to `Version: gate`,
> `(label)` on the other 29, and `(blocking)` **empty** — no open task's text
> claims a gate dependency. `T3.01`'s legacy `(entry)` is left alone as a done
> task, out of scope. Amendment row in `tasks/E3-synthesis-and-reach.md`.
>
> ---
>
> **The original stop — Tier-3 amendment, spec §6 condition 2.** Fable-tier
> ruling, with both load-bearing claims verified against the tree:
>
> - Spec §4 defines `(label)` and `(blocking)` only, but §3's own gate track —
>   `T2.114`, `T2.116`, `T3.22`, `T3.24`, `TH1.10`, `TH1.17`, all open —
>   **produces** gates rather than waiting on them. Neither qualifier is true of
>   a producer, and these six are the most-read qualifiers in the corpus because
>   they are the next gate attempts the loop schedules.
> - §4's sole `(blocking)` exemplar is wrong. `T2.41` is titled *"G-D evidence
>   run"* and is `done` — it **mints** the qualification record rather than
>   waiting on it, so the one deliberate use of the binary is a completed
>   producer marked as blocked by its own gate. Today's true `(blocking)` set
>   appears to be empty.
> - A third qualifier is **already in the corpus**: `Gate: G-D (entry)` on
>   `T3.01` (`tasks/E3-synthesis-and-reach.md:38`), encoding the epic-level entry
>   gate that §4 says per-task marking replaces. The plan's regex cannot see it
>   and its script would not rewrite it, so Task 2 touches the vocabulary
>   question however it is executed.
>
> **The question for the owner:** ratify a third qualifier `(produces)` — *this
> task's output is the gate's evidence; startable; stop conditions 1 and 3 govern
> it, not the qualifier* — assigned to the rows `progress.md` already stamps
> `Version: gate`. Or rule otherwise.
>
> **Two Tier-1 corrections to apply when it unblocks**, independent of the
> ruling. **Scope is open-only**: 181 of the 236 gate fields sit on `done` tasks
> in E0/E1/E2, where the qualifier has no consumer — the loop only ever asks
> whether an *open* task is startable — and stamping them would write a false
> claim into the historical record. The plan's own Files list already says E3,
> E4, M1, EH1; only its `glob("*.md")` disagrees. **And the test's regex has a
> silent-skip hole**: `` `Gate: (G-[A-F])(?: \((label|blocking)\))?` `` followed
> by a mandatory backtick fails to match an *unrecognised* qualifier entirely, so
> `(lable)` would pass forever. Capture any parenthesised token and reject
> unknown values.

**Files:**
- Modify: `docs/planning/tasks/E3-synthesis-and-reach.md`, `E4-hardening-and-scale.md`, `M1-measurement.md`, `EH1-documents-pkm.md`
- Test: `backend/tests/test_planning_docs.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: every `Gate: G-x` in a task's metadata line is qualified as
  `Gate: G-x (label)` or `Gate: G-x (blocking)`. The loop reads the qualifier to
  decide whether a task is startable.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_planning_docs.py`:

```python
TASKS_DIR = Path(__file__).resolve().parents[2] / "docs/planning/tasks"

GATE_FIELD = re.compile(r"`Gate: (G-[A-F])(?: \((label|blocking)\))?`")


def test_every_gate_field_says_what_it_blocks():
    """An unqualified `Gate:` reads as "blocked until the gate clears", which
    is false for most tasks: gates gate labels, not code (T2.95's serving
    boundary). That ambiguity is what serialised the roadmap behind
    measurement, so the qualifier is mandatory."""
    unqualified = []
    for path in sorted(TASKS_DIR.glob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for gate, qualifier in GATE_FIELD.findall(line):
                if not qualifier:
                    unqualified.append(f"{path.name}:{number} Gate: {gate}")

    assert unqualified == [], (
        "these Gate fields do not say whether the code is blocked or only the "
        f"label waits: {unqualified}"
    )
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd backend && .venv/bin/python -m pytest tests/test_planning_docs.py::test_every_gate_field_says_what_it_blocks -q
```

Expected: FAIL, listing every unqualified `Gate:` field.

- [ ] **Step 3: Qualify each gate field**

Read each task's text before deciding. The rule:

- **`(blocking)`** only when the task *cannot be executed* until the gate
  clears — it consumes the gate's own output. Today that is `T2.41` (needs the
  qualification record) and any task whose Done-when requires a cleared gate.
- **`(label)`** for everything else — the code ships and only the badge waits.
  All of `v0.4` is `(label)`: articles are built and served unlabelled, exactly
  as `T2.95` intends.

Apply with an explicit list rather than a blanket regex, so each decision is a
read of the task:

```bash
cd /root/repositories/darkmem
backend/.venv/bin/python - <<'PY'
import pathlib, re
BLOCKING = {"T2.41"}          # extend only after reading the task
d = pathlib.Path("docs/planning/tasks")
for path in sorted(d.glob("*.md")):
    text = path.read_text(encoding="utf-8"); out = []; task = None
    for line in text.splitlines():
        h = re.match(r"^#### (T[A-Z]?\d+\.\d+[a-z]?) —", line)
        if h:
            task = h.group(1)
        if "`Gate: G-" in line and "(label)" not in line and "(blocking)" not in line:
            kind = "blocking" if task in BLOCKING else "label"
            line = re.sub(r"`Gate: (G-[A-F])`", rf"`Gate: \1 ({kind})`", line)
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
print("qualified")
PY
```

- [ ] **Step 4: Run it to verify it passes**

```bash
cd backend && .venv/bin/python -m pytest tests/test_planning_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Record the amendment**

Append one row to the amendment log at the bottom of
`docs/planning/tasks/E3-synthesis-and-reach.md`:

```markdown
| 2026-08-10 | all gated tasks | 2 | **`Gate:` is now qualified `(label)` or `(blocking)`.** An unqualified field read as "blocked until the gate clears", which is false for nearly every task: gates gate labels and `T2.95`'s serving boundary already refuses an unbacked claim. Only `T2.41` is `(blocking)` today | The ambiguity is what serialised the roadmap behind measurement — 232 tasks done, nothing released, and E3 work sitting behind an open G-D that gates only its badge. Recorded rather than silently applied because it changes which work an agent believes is startable |
```

- [ ] **Step 6: Commit**

```bash
git add docs/planning/tasks backend/tests/test_planning_docs.py
git commit -m "docs(tasks): say whether a gate blocks the code or only the label

An unqualified 'Gate: G-D' reads as blocked-until-cleared, which is false
for nearly every task carrying one — gates gate labels, and T2.95's
serving boundary already refuses an unbacked claim. That ambiguity is what
queued the roadmap behind measurement. Only T2.41 is (blocking) today; a
test fails the build on any unqualified field."
```

---

### Task 3: Version sync, CHANGELOG, and the release script

**Files:**
- Create: `CHANGELOG.md`, `scripts/release.sh`
- Modify: `backend/pyproject.toml:3`, `backend/app/main.py:647`, `frontend/package.json:4`
- Test: `backend/tests/test_planning_docs.py`

**Interfaces:**
- Produces: `scripts/release.sh <version>` — asserts a clean tree and a green
  gate, syncs the three product version fields, writes the tag, builds and
  deploys. Used at every version.

**The version reset, and why.** The three product fields say `0.2.0`. Nothing
was ever released under it and nothing manages it. The ladder starts at `v0.1`,
so the fields reset to `0.1.0`. `app/main.py`'s value is served in the OpenAPI
document, so Step 5 verifies the SDK generator is unaffected.

- [ ] **Step 1: Write the failing test**

```python
PRODUCT_VERSION = re.compile(r'version\s*=\s*"(\d+\.\d+\.\d+)"')


def test_the_product_version_is_one_number_in_three_places():
    """Backend, the OpenAPI document and the SPA ship as ONE image, so they are
    one product with one version. The SDK and extension are distributed
    separately (doc 15 §2) and keep their own — they are deliberately not
    checked here."""
    root = Path(__file__).resolve().parents[2]
    pyproject = PRODUCT_VERSION.search(
        (root / "backend/pyproject.toml").read_text(encoding="utf-8")
    ).group(1)
    fastapi = re.search(
        r'FastAPI\([^)]*version="(\d+\.\d+\.\d+)"',
        (root / "backend/app/main.py").read_text(encoding="utf-8"),
    ).group(1)
    package = json.loads(
        (root / "frontend/package.json").read_text(encoding="utf-8")
    )["version"]

    assert pyproject == fastapi == package, (
        f"product version drifted: pyproject={pyproject} "
        f"fastapi={fastapi} package.json={package}"
    )
```

Add `import json` to the test file's imports if absent.

- [ ] **Step 2: Run it — it should PASS (all three are 0.2.0)**

```bash
cd backend && .venv/bin/python -m pytest tests/test_planning_docs.py::test_the_product_version_is_one_number_in_three_places -q
```

Expected: PASS. This test's value is preventing future drift, so it is written
before the fields move rather than after.

- [ ] **Step 3: Reset the three fields to 0.1.0**

```bash
cd /root/repositories/darkmem
sed -i 's/^version = "0.2.0"/version = "0.1.0"/' backend/pyproject.toml
sed -i 's/version="0.2.0"/version="0.1.0"/' backend/app/main.py
sed -i 's/"version": "0.2.0"/"version": "0.1.0"/' frontend/package.json
grep -n '0\.1\.0' backend/pyproject.toml backend/app/main.py frontend/package.json
```

- [ ] **Step 4: Run the test again**

Expected: PASS with all three now `0.1.0`.

- [ ] **Step 5: Verify the OpenAPI change did not move the SDK contract**

```bash
cd sdks && make generate && cd .. && git diff --exit-code sdks/ && echo "SDK unchanged"
cd backend && .venv/bin/python -m pytest tests/test_sdk_generator.py -q
```

Expected: `SDK unchanged`, and the generator suite green. If the emitted clients
*do* change, stop — the contract hash covers more than the three bound routes
and that is a finding, not a merge conflict to resolve.

- [ ] **Step 6: Write `CHANGELOG.md`**

```markdown
# Changelog

What changed, per release. One user, one dev environment — this is a "what got
better" log, not release notes for strangers. The ladder is
`docs/planning/RELEASES.md`.

## v0.1 — 2026-08-10

First release. Everything below already existed and had never been tagged or
deployed.

### Added
- Buffered capture on four doors (REST + MCP, single and batch) with
  `origin_key` identity resolution.
- Hybrid retrieval — semantic + keyword under RRF, with an optional reranker.
- The entity/relationship graph, closed taxonomy, supersession, and
  fingerprint-partitioned embeddings.
- Code indexing: symbol graph, code search, blast radius, wiki.
- 21 scheduled jobs under one registry, including the Tier-C dream family.
- The verified-fact vault and its ladder — **badges serve as `candidate` until
  G-C and G-D clear**, which is deliberate, not a defect.
- Session checkpoints on both doors.
- The SPA: memories, knowledge, activity, code, settings.
- Minimal TypeScript and Python SDKs, generated from the live contract.
- A browser capture extension.

### Known limits
- Verification, groundedness and coverage labels are withheld pending G-C, G-D
  and G-E. The system ships **unlabelled** by design (`T2.95`).
- Data is disposable: the schema is not frozen and a schema change drops and
  recreates the database.
```

- [ ] **Step 7: Write `scripts/release.sh`**

```bash
#!/usr/bin/env bash
# Cut a release: assert, sync, tag, deploy. Four steps that repeat every
# version, which is why this is a script and not a checklist.
set -euo pipefail

VERSION="${1:?usage: release.sh v0.N}"
NUMERIC="${VERSION#v}.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -z "$(git status --porcelain)" ]] || { echo "tree is dirty; commit first"; exit 1; }
git rev-parse "$VERSION" >/dev/null 2>&1 && { echo "$VERSION already tagged"; exit 1; }

echo "── gate ──"
./scripts/gate.sh --full

echo "── version fields -> $NUMERIC ──"
sed -i -E "s/^version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NUMERIC\"/" backend/pyproject.toml
sed -i -E "s/version=\"[0-9]+\.[0-9]+\.[0-9]+\"/version=\"$NUMERIC\"/" backend/app/main.py
sed -i -E "s/\"version\": \"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$NUMERIC\"/" frontend/package.json
git diff --quiet || git commit -aqm "chore(release): $VERSION"

echo "── tag ──"
git tag -a "$VERSION" -m "$VERSION"

echo "── build and deploy ──"
./scripts/build-push.sh
docker compose up -d

echo "$VERSION tagged and deployed."
echo "CHANGELOG.md is written by hand before running this — verify it names $VERSION."
```

```bash
chmod +x scripts/release.sh
```

- [ ] **Step 8: Verify the script refuses a dirty tree**

```bash
cd /root/repositories/darkmem
touch /tmp/dirt && cp /tmp/dirt ./dirt-probe && ./scripts/release.sh v0.99; echo "exit=$?"
rm -f ./dirt-probe
```

Expected: `tree is dirty; commit first`, `exit=1`, and no tag created.

- [ ] **Step 9: Commit**

```bash
git add CHANGELOG.md scripts/release.sh backend/pyproject.toml backend/app/main.py \
        frontend/package.json backend/tests/test_planning_docs.py
git commit -m "feat(release): version sync, changelog, and the release script

The three product fields claimed 0.2.0 — never released, never managed —
so they reset to 0.1.0 where the ladder starts. app/main.py's value is
served in the OpenAPI document, so the SDK generator was re-run and its
output byte-compared to prove the contract did not move.

A test pins the three to one number: backend, OpenAPI and the SPA ship as
one image, so they are one product. The SDK and extension are distributed
separately and keep their own versions, deliberately unchecked.

release.sh does the four steps a release is — assert clean and green,
sync, tag, deploy — because they repeat at every version."
```

---

### Task 4: Demonstrate v0.1

**Files:**
- Create: `docs/releases/v0.1-demonstration.md`

**Interfaces:**
- Consumes: `scripts/build-push.sh`, `docker-compose.yml`.
- Produces: the evidence file `release.sh` will not check for you. A green suite
  is not a running system, and this task exists because the difference is
  exactly what "nothing visible" means.

**Fully autonomous — no human step.** Setup is plain REST (`POST /api/v1/setup`
takes `{"password": ...}` as its only required block) and it **issues the auth
cookie itself**, so there is no login form to drive and no JWT to lift out of a
browser. `_extract_token` reads the cookie before the `Authorization` header, so
a `curl` jar authenticates everything after. A browser appears exactly once, in
Step 4b, for the one claim curl cannot substantiate: that the SPA renders.

- [ ] **Step 1: Build the image and bring the stack up**

```bash
cd /root/repositories/darkmem
./scripts/build-push.sh
docker compose up -d
sleep 10 && curl -sS -o /dev/null -w "health=%{http_code}\n" http://localhost:8000/health
```

Expected: `health=200`. If the prod compose refuses for missing `.env` values,
use `docker compose -f docker-compose.dev.yml up -d` and record that the
demonstration ran against the dev stack.

- [ ] **Step 2: Finalize setup over REST — no browser needed**

`POST /api/v1/setup` takes `{"password": ...}` as its only required block and
**issues the auth cookie itself** on a successful password write, so there is no
separate login step. `_extract_token` reads the cookie before the `Authorization`
header, so a cookie jar authenticates every later call.

```bash
cd /root/repositories/darkmem
JAR=/tmp/darkmem-v01.jar; rm -f "$JAR"
PASSWORD='v0.1-demonstration-password'

curl -sS -c "$JAR" -X POST http://localhost:8000/api/v1/setup \
  -H 'Content-Type: application/json' \
  -d "{\"password\":\"$PASSWORD\"}" | head -c 300; echo
grep -q darkmem_session "$JAR" && echo "session cookie issued"
```

Expected: a `SetupResponse` with `password.ok = true`, and `session cookie issued`.

Then confirm the guard closes behind it:

```bash
curl -sS -o /dev/null -w "setup_guard=%{http_code}\n" \
  -X POST http://localhost:8000/api/v1/setup \
  -H 'Content-Type: application/json' -d "{\"password\":\"$PASSWORD\"}"
```

Expected: `setup_guard=403` — `require_uninitialized` refuses a second run, which
is the trust-on-first-use property.

- [ ] **Step 3: Capture and retrieve through a real door**

```bash
curl -sS -b "$JAR" -X POST http://localhost:8000/api/v1/memories \
  -H 'Content-Type: application/json' \
  -d '{"content":"darkmem v0.1 was demonstrated on 2026-08-10 by capturing this memory.","project":"default","wait_process":true}' \
  | head -c 400; echo

sleep 3
curl -sS -b "$JAR" -X POST http://localhost:8000/api/v1/memories/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"v0.1 demonstrated","limit":3}' | head -c 400; echo
```

Expected: a `202` ack carrying the pre-minted memory id (or `201` with the
processed memory, if `wait_process` settled inside
`buffer_wait_timeout_seconds`), then that memory coming back from search.

**If capture returns 202 and search finds nothing**, the buffer has not flushed
yet — wait for the `buffer_flush` job or re-run the search. That is the designed
Tier-A accept, not a failure.

- [ ] **Step 4: Confirm MCP answers**

```bash
curl -sS -X POST http://localhost:8000/mcp/ \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"v0.1-demo","version":"1"}}}' \
  | head -c 300; echo
```

Expected: a JSON-RPC result naming the server. A `421` means the Host allowlist
refused — fix by extending `MCP_ALLOWED_HOSTS`, **never** by disabling the check
(invariant 20).

- [ ] **Step 4b: Prove the SPA renders — the one job curl cannot do**

Everything above exercises the API. v0.1 also claims a UI, and a served
`index.html` is not a rendering app. This is the only step that needs a browser,
and it reuses the cookie rather than driving a login form.

```bash
cd /root/repositories/darkmem/frontend
node - "$JAR" <<'JS'
import { chromium } from "@playwright/test";
import { readFileSync } from "node:fs";

const base = "http://localhost:8000";
// Netscape cookie jar: the last tab-separated field is the value.
const token = readFileSync(process.argv[2], "utf8")
  .split("\n").find((l) => l.includes("darkmem_session"))
  .split("\t").pop().trim();

const browser = await chromium.launch();
const ctx = await browser.newContext();
await ctx.addCookies([{ name: "darkmem_session", value: token, url: base }]);
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));

await page.goto(`${base}/memories`, { waitUntil: "networkidle" });
const body = await page.locator("body").innerText();
const ok = /v0\.1 was demonstrated/i.test(body);

console.log(JSON.stringify({
  url: page.url(),
  rendered_the_captured_memory: ok,
  page_errors: errors,
}, null, 2));
await page.screenshot({ path: "/tmp/v0.1-spa.png", fullPage: true });
await browser.close();
JS
```

Expected: `rendered_the_captured_memory: true` and `page_errors: []`. That single
assertion walks image → SPA bundle → API → Postgres → back to the screen, which
is the whole claim v0.1 makes. Keep `/tmp/v0.1-spa.png`.

- [ ] **Step 5: Record the evidence**

Write `docs/releases/v0.1-demonstration.md` containing, for each of Steps 1–4:
the command run, its real output (trimmed), and the date. Then state plainly
anything that did **not** work and was accepted — an honest demonstration with a
recorded gap is worth more than a tidy one.

- [ ] **Step 6: Commit**

```bash
git add docs/releases/v0.1-demonstration.md
git commit -m "docs(release): demonstrate v0.1 against a running stack

A green suite is not a running system, and the gap between them is what
'nothing visible' has meant here. Health, the setup guard, capture,
retrieval and the MCP handshake, each with its real output."
```

---

### Task 5: Cut and deploy v0.1

**Files:** none created; produces the `v0.1` tag and a running deployment.

- [ ] **Step 1: Confirm the changelog names v0.1**

```bash
grep -n "^## v0.1" CHANGELOG.md
```

Expected: one match.

- [ ] **Step 2: Cut the release**

```bash
cd /root/repositories/darkmem
DEEPSEEK_API_KEY=<key from CLAUDE.md> ./scripts/release.sh v0.1
```

Expected: the gate runs green, the three version fields move to `0.1.0`, the tag
is written, the image builds, the stack comes up, and the script prints
`v0.1 tagged and deployed.`

- [ ] **Step 3: Verify the tag and the deployment**

```bash
git tag
curl -sS http://localhost:8000/health
docker compose ps --format '{{.Name}} {{.State}}'
```

Expected: `v0.1` present, health responding, containers `running`.

- [ ] **Step 4: Record it on master**

```bash
cd .worktrees/master-claim
# add to the E3/rollup preamble: v0.1 tagged and deployed 2026-08-10
git commit -aqm "docs(progress): v0.1 tagged and deployed"
```

---

### Task 6: The loop's operating contract

**Files:**
- Create: `docs/planning/autonomous-loop.md`

**Interfaces:**
- Produces: the document a fresh session reads to run the ladder unattended. The
  startup prompt names this file and nothing else, so the contract lives in the
  repo rather than in a prompt someone has to keep.

- [ ] **Step 1: Write `docs/planning/autonomous-loop.md`**

It must contain, and nothing more:

1. **The state machine.** `progress.md` on `master` for task state,
   `RELEASES.md` for scope, `gate-ledger.md` for evidence, `CHANGELOG.md` for
   what shipped. The loop rebuilds its picture from these every iteration and
   never relies on conversation context surviving compaction.
2. **The iteration**, verbatim from spec §5: read state → take the next
   unclaimed task in the current version → claim in one commit → execute under
   the runbook (owning design doc, TDD, mutation-drill every guard, real Verify
   output) → `./scripts/gate.sh` → commit with reasoning → update `progress.md`
   on `master` → check stops.
3. **The version boundary:** `--full` → Fable review of the whole version → tag
   → CHANGELOG → `release.sh` → **stop and report**.
4. **Fable is the escalation target.** Where Opus or Sonnet cannot decide, ask
   Fable rather than guessing; Fable's answer is the decision. Reach the owner
   only when Fable says a call is owner-only, or a stop fires.
5. **The eight stops**, copied verbatim from spec §6 including the two drawn
   from 2026-08-10 — a ruling can be invalid because of *who* made it, and a
   pre-positioned fallback is the tell that the loop is rationalising past a
   stop.
6. **Proportionality:** does this artifact outlive the task? If no, inline it.
7. **What the loop may never do:** write `gold.json`, spend a measurement
   attempt, freeze the schema, move a bar, run two pytest sessions at once, or
   mark a task `done` with a failing check.

- [ ] **Step 2: Commit**

```bash
git add docs/planning/autonomous-loop.md
git commit -m "docs(planning): the autonomous loop's operating contract

The document a fresh session reads to run the ladder unattended. It lives
in the repo rather than in a prompt, because the loop's whole defence
against context loss is that the repository is the state machine."
```

---

## Self-review

**Spec coverage.** §2 version scheme → Task 3. §3 ladder → Task 1. §4 gate
marking → Task 2. §5 loop → Task 6. §6 stops → Task 6 Step 1.5. §7 state and the
runbook amendment → Task 6 Step 1.1 and Task 2 Step 5. §8 proportionality →
Global Constraints and Task 6 Step 1.6. §9 success criteria → Tasks 4 and 5.
§10 out of scope → nothing implements it, correctly.

**Deliberately not in this plan:** the v0.2–v0.4 tasks themselves. Each already
carries its own What / Done-when / Verify in its epic file, and restating them
here would duplicate the source of truth and rot against it. The loop executes
them from there; this plan builds the machinery the loop needs and cuts v0.1.

**Type consistency.** `_versioned_task_ids()` (Task 1) is used only by Task 1.
`GATE_FIELD` (Task 2) and `PRODUCT_VERSION` (Task 3) are local to their tests.
`release.sh` takes `v0.N` and derives `0.N.0` — the tag and the field format
differ deliberately, and Task 5 Step 2 shows the exact invocation.
