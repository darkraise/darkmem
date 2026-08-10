import io
import os
import re
import sys

EPICS = [
    ("E0", "Baseline & harness", "tasks/E0-baseline-and-harness.md", "**G-A CLEARED 2026-07-27**"),
    ("E1", "Engine core", "tasks/E1-engine-core.md", "**G-B CLEARED 2026-07-28**"),
    ("E2", "Truth core", "tasks/E2-truth-core.md", "G-C, G-D open"),
    ("E3", "Synthesis & reach", "tasks/E3-synthesis-and-reach.md", "G-E open"),
    ("E4", "Hardening & scale", "tasks/E4-hardening-and-scale.md", "demand-gated"),
    ("EH1", "Documents / PKM", "tasks/EH1-documents-pkm.md", "G-F open"),
    # M1 holds every evidence run and the gold they consume (created
    # 2026-08-06). Its ids keep their original epic prefix — T2.54 stays
    # T2.54 — because the whole tree already cites them, so the row regex
    # must not assume a task id matches its epic key.
    ("M1", "Measurement phase", "tasks/M1-measurement.md", "consumes implementation; gates nothing"),
]

HEAD = re.compile(r"^#### (T(?:H1|[0-4])\.\d{2,3}[a-z]?) — (.+)$")
META = re.compile(r"`Model: ([^`]+?)`")
SIZE = re.compile(r"`Size: ([SML])`")
EFFORT = re.compile(r"`Effort: ([a-z]+)`")
ROW = re.compile(r"^\| (T(?:H1|[0-4])\.\d{2,3}[a-z]?) \|")
CELL = re.compile(r"(?<!\\)\|")

STATUSES = ["todo", "wip", "blocked", "review", "done", "dropped"]
FRESH = ("", "todo", "", "", "")

# ------------------------------------------------ carry hand-edited state forward
# Regenerating rebuilds the derived columns from the epic files. The five state
# columns belong to whoever is executing and must survive that: runbook §5 tells
# every agent to regenerate after logging an amendment, so a generator that reset
# them would wipe every claim, status, commit sha and review verdict in the
# tracker the first time an amendment landed after work began.
prior = {}
if os.path.exists("progress.md"):
    for line in io.open("progress.md", encoding="utf-8").read().split("\n"):
        if not ROW.match(line):
            continue
        cells = [c.strip() for c in CELL.split(line)]
        # The Effort column was inserted after Model, widening the row by one.
        # Read the state block from the end rather than a fixed offset so a
        # pre-Effort progress.md still round-trips its claims on the first
        # regeneration after the change.
        if len(cells) >= 11:
            prior[cells[1]] = tuple(cells[-6:-1])


def render(cells):
    # An empty cell renders as "| " so a fully-fresh table is byte-identical to
    # what this script produced before state was carried.
    return "".join("| " + (c + " " if c else "") for c in cells) + "|"


out = []
out.append("# Progress tracker\n")
out.append(
    "**Regenerated from the epic files** by\n"
    "`scripts/gen_progress.py` — task ids, titles, model tiers, and effort are derived, never\n"
    "hand-copied, so the two cannot drift. Only the state columns (Owner, Status, Commit,\n"
    "Review, Note) are edited by hand.\n"
)
out.append(
    "The epic files in [`tasks/`](tasks/) are the source of truth for *scope*; this file\n"
    "tracks *state*. If they disagree about what a task is, the epic file wins — and the\n"
    "disagreement is an amendment to log.\n"
)
out.append("## Status vocabulary\n")
out.append(
    "| Status | Means |\n|---|---|\n"
    "| `todo` | Not started. Check the epic's entry gate before claiming — an open gate\n"
    "blocks the whole epic regardless of `Depends`. |\n"
    "| `wip` | Claimed. The **Owner** column names who; one owner at a time. |\n"
    "| `blocked` | Started and stopped. The **Note** column must say what blocks it. |\n"
    "| `review` | Code complete, awaiting the Fable-tier review that Opus-tier and\n"
    "gate-feeding tasks require. The **Review** column carries the reviewer's verdict. |\n"
    "| `done` | Every definition-of-done item in runbook §4 holds, verification output\n"
    "recorded, commit landed, and any required review passed. |\n"
    "| `dropped` | The task's premise no longer holds, so it is resolved without being\n"
    "executed. The **Note** must say who decided and why. A drop is not a deferral —\n"
    "a deferred task is still `todo`. |\n"
)
out.append(
    "**A task is never `done` with a failing check.** If the suite is red it is `blocked`\n"
    "and the Note says so. That rule is the whole point of this file.\n"
)
out.append("## Claiming and concurrency\n")
CLAIMING = (
    "- **This file is canonical on `master`**, not on an epic branch — otherwise it forks per\n"
    "  branch and no copy is true. Update it with a single commit touching only your row.\n"
    "- **Claiming is one commit** setting Owner and moving the row to `wip`. If two agents\n"
    "  race, the later commit loses and that agent picks another task — cheap, because the\n"
    "  loser has done no work yet.\n"
    "- **Review is tracked in the Review column**, not as separate rows. Every Opus-tier\n"
    "  task and every task feeding a gate claim needs one before it can reach `done`.\n"
    "- Regenerate the derived columns and the rollup with `python scripts/gen_progress.py`\n"
    "  after any task is added, split, or retitled. It carries the five state columns\n"
    "  through unchanged, so regenerating mid-execution is safe and never resets a claim.\n"
)
out.append(CLAIMING)

# ------------------------------------------------------------ carry standing notes
# `progress.md` holds hand-written prose in two places this script cannot
# reproduce — before `## Rollup`, and between the rollup table and the `---`
# above the epic tables — and regenerating without carrying them is a silent
# delete. Together they held 62 lines on 2026-08-10: a standing open-flake
# record, and the account of three recount defects that says why the counts are
# derived. The runbook tells every agent to regenerate after logging an
# amendment, so the loss was one routine command away. Both regions are anchored
# on generated text, so a preamble edit degrades to carrying nothing rather than
# to duplicating a section.
_old = io.open("progress.md", encoding="utf-8").read() if os.path.exists("progress.md") else ""


def standing_notes(after, before):
    """Prose between two generated anchors in the previous progress.md."""
    start, end = _old.find(after), _old.find(before)
    if start == -1 or end <= start:
        return ""
    return _old[start + len(after):end].strip("\n")


preamble_notes = standing_notes(CLAIMING, "## Rollup")
if preamble_notes:
    out.append(preamble_notes + "\n")

tables = []
totals = 0
rollup = []
bad = []

for code, name, path, gate in EPICS:
    body = io.open(path, encoding="utf-8").read()
    lines = body.split("\n")
    rows = []
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if not m:
            continue
        tid, title = m.group(1), m.group(2)
        model = ""
        size = ""
        effort = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            mm = META.search(lines[j])
            if mm:
                model = mm.group(1).replace(" 5", "").replace(" 4.5", "")
                sm = SIZE.search(lines[j])
                if sm:
                    size = sm.group(1)
                em = EFFORT.search(lines[j])
                if em:
                    effort = em.group(1)
                break
        title = title.replace("|", "\\|")
        rows.append((tid, title, model, size, effort))
    totals += len(rows)
    counts = dict.fromkeys(STATUSES, 0)
    t = ["## %s — %s (%d tasks)\n" % (code, name, len(rows))]
    t.append("| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |")
    t.append("|---|---|---|---|---|---|---|---|---|---|")
    for tid, title, model, size, effort in rows:
        state = prior.pop(tid, FRESH)
        if state[1] not in counts:
            bad.append("%s has status %r, which is not in the vocabulary" % (tid, state[1]))
            continue
        counts[state[1]] += 1
        t.append(render([tid, title, size, model, effort] + list(state)))
    rollup.append((code, name, len(rows), counts, gate))
    tables.append("\n".join(t) + "\n")

# State left over belongs to a task the epic files no longer define. Dropping it
# silently is how a claim or a completed row disappears without anyone noticing.
for tid, state in sorted(prior.items()):
    if state != FRESH:
        bad.append("%s carries state %r but no epic file defines it any more" % (tid, state))

if bad:
    for msg in bad:
        print("FAIL", msg)
    print("\nprogress.md NOT written — %d problem(s)" % len(bad))
    sys.exit(1)

out.append("## Rollup\n")
r = ["| Epic | Tasks | " + " | ".join(STATUSES) + " | Gate |",
     "|---" * (len(STATUSES) + 3) + "|"]
tot = dict.fromkeys(STATUSES, 0)
for code, name, n, counts, gate in rollup:
    for s in STATUSES:
        tot[s] += counts[s]
    r.append("| %s — %s | %d | %s | %s |" % (
        code, name, n, " | ".join(str(counts[s]) for s in STATUSES), gate))
r.append("| EH2 — .NET migration | outline |" + " — |" * len(STATUSES) + " G-G closed |")
r.append("| **Total** | **%d** | %s | |" % (
    totals, " | ".join("**%d**" % tot[s] for s in STATUSES)))
out.append("\n".join(r) + "\n")

# The second standing-notes region: prose under the rollup table, above the
# `---`. It holds the account of why these counts are derived, written by the
# agents who found them drifted three times.
rollup_block = standing_notes("## Rollup", "\n---\n")
rollup_lines = rollup_block.split("\n")
_last_row = max((k for k, line in enumerate(rollup_lines) if line.startswith("|")), default=-1)
rollup_notes = "\n".join(rollup_lines[_last_row + 1:]).strip("\n")
if rollup_notes:
    out.append(rollup_notes + "\n")

out.append("---\n")
out.extend(tables)

# `progress.md` is canonical on `master` only (runbook §6), and every branch
# carries a frozen copy whose banner says so. Regenerating outside `master`
# rewrites that copy from the branch's own task files and **deletes the banner
# in the process** — so the file stops announcing that it is stale at exactly
# the moment it becomes misleading, and the state columns reset to whatever the
# branch's stale copy carried. That banner exists because three agents in one
# session reported the stale copy as a bug; losing it undoes their fix. The
# refusal is here rather than in a caller because the caller is usually an
# agent following a runbook line, not a person who read this file.
_branch = os.popen("git rev-parse --abbrev-ref HEAD 2>/dev/null").read().strip()
if _branch and _branch != "master" and not os.environ.get("GEN_PROGRESS_ALLOW_BRANCH"):
    sys.exit(
        "refusing to regenerate progress.md on branch %r: it is canonical on master "
        "only, and rewriting a branch copy silently drops the stale-copy banner. "
        "Run this in the master worktree (.worktrees/master-claim), or set "
        "GEN_PROGRESS_ALLOW_BRANCH=1 if you genuinely mean to rewrite this copy."
        % _branch
    )

io.open("progress.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("total tasks:", totals)
for code, name, n, counts, gate in rollup:
    live = " ".join("%s=%d" % (s, counts[s]) for s in STATUSES if counts[s])
    print("  %-4s %d   %s" % (code, n, live))
