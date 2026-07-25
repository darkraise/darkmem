import io
import os
import re

EPICS = [
    ("E0", "Baseline & harness", "tasks/E0-baseline-and-harness.md", "G-A open"),
    ("E1", "Engine core", "tasks/E1-engine-core.md", "G-B open"),
    ("E2", "Truth core", "tasks/E2-truth-core.md", "G-C, G-D open"),
    ("E3", "Synthesis & reach", "tasks/E3-synthesis-and-reach.md", "G-E open"),
    ("E4", "Hardening & scale", "tasks/E4-hardening-and-scale.md", "demand-gated"),
    ("EH1", "Documents / PKM", "tasks/EH1-documents-pkm.md", "G-F open"),
]

HEAD = re.compile(r"^#### (T(?:H1|[0-4])\.\d{2}[a-z]?) — (.+)$")
META = re.compile(r"`Model: ([^`]+?)`")
SIZE = re.compile(r"`Size: ([SML])`")

out = []
out.append("# Progress tracker\n")
out.append(
    "**Regenerated from the epic files** by\n"
    "`scripts/gen_progress.py` — task ids, titles, and model tiers are derived, never\n"
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
    "| `done` | Every definition-of-done item in runbook §3 holds, verification output\n"
    "recorded, commit landed, and any required review passed. |\n"
)
out.append(
    "**A task is never `done` with a failing check.** If the suite is red it is `blocked`\n"
    "and the Note says so. That rule is the whole point of this file.\n"
)
out.append("## Claiming and concurrency\n")
out.append(
    "- **This file is canonical on `main`**, not on an epic branch — otherwise it forks per\n"
    "  branch and no copy is true. Update it with a single commit touching only your row.\n"
    "- **Claiming is one commit** setting Owner and moving the row to `wip`. If two agents\n"
    "  race, the later commit loses and that agent picks another task — cheap, because the\n"
    "  loser has done no work yet.\n"
    "- **Review is tracked in the Review column**, not as separate rows. Every Opus-tier\n"
    "  task and every task feeding a gate claim needs one before it can reach `done`.\n"
    "- Regenerate the derived columns and the rollup with `python scripts/gen_progress.py`\n"
    "  after any task is added, split, or retitled.\n"
)

tables = []
totals = 0
rollup = []

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
        for j in range(i + 1, min(i + 5, len(lines))):
            mm = META.search(lines[j])
            if mm:
                model = mm.group(1).replace(" 5", "").replace(" 4.5", "")
                sm = SIZE.search(lines[j])
                if sm:
                    size = sm.group(1)
                break
        title = title.replace("|", "\\|")
        rows.append((tid, title, model, size))
    totals += len(rows)
    rollup.append((code, name, len(rows), gate))
    t = ["## %s — %s (%d tasks)\n" % (code, name, len(rows))]
    t.append("| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |")
    t.append("|---|---|---|---|---|---|---|---|---|")
    for tid, title, model, size in rows:
        t.append("| %s | %s | %s | %s | | todo | | | |" % (tid, title, size, model))
    tables.append("\n".join(t) + "\n")

out.append("## Rollup\n")
r = ["| Epic | Tasks | todo | wip | blocked | review | done | Gate |", "|---|---|---|---|---|---|---|---|"]
for code, name, n, gate in rollup:
    r.append("| %s — %s | %d | %d | 0 | 0 | 0 | 0 | %s |" % (code, name, n, n, gate))
r.append("| EH2 — .NET migration | outline | — | — | — | — | — | G-G closed |")
r.append("| **Total** | **%d** | **%d** | **0** | **0** | **0** | **0** | |" % (totals, totals))
out.append("\n".join(r) + "\n")
out.append("---\n")
out.extend(tables)

io.open("progress.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("total tasks:", totals)
for code, name, n, gate in rollup:
    print("  %-4s %d" % (code, n))
