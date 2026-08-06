"""Plan linter — every structural claim the corpus makes, asserted mechanically.

Run from docs/planning/:   python scripts/check_plan.py
Exit 0 = green. Any failure prints the offending item and exits 1.

Written after a review found that a claim of the form "X is named in Y" had been
recorded as done without being true. Anything this corpus asserts about itself
should fail loudly here rather than be taken on trust.
"""

import glob
import io
import os
import re
import sys

TID = r"T(?:H1|[0-4])\.\d{2,3}[a-z]?"
HEAD = re.compile(r"^#### (%s) — (.+)$" % TID, re.M)
FIELD = re.compile(
    r"^`Model: ([^`]+)` · `Effort: ([a-z]+)` · `Size: ([SML])` · "
    r"`(Depends|Trigger): ([^`]*)`.*$", re.M)
EFFORTS = ("low", "medium", "high", "xhigh", "max")

EPIC_FILES = sorted(glob.glob("tasks/*.md"))
FAILS = []


def fail(cat, msg):
    FAILS.append((cat, msg))


def read(p):
    return io.open(p, encoding="utf-8").read()


# --------------------------------------------------------------- load tasks
tasks = {}       # tid -> dict
order = []
for f in EPIC_FILES:
    if "EH2" in f:
        continue
    src = read(f)
    lines = src.split("\n")
    idx = [i for i, l in enumerate(lines) if HEAD.match(l + "\n")]
    # A block ends at the next heading of ANY level, not just the next task.
    # Without this the final task in a file absorbs the amendment log, and every
    # task another row happens to mention becomes a phantom prerequisite of it.
    stops = sorted(i for i, l in enumerate(lines) if l.startswith("#"))
    for k, i in enumerate(idx):
        nxt = [s for s in stops if s > i]
        end = nxt[0] if nxt else len(lines)
        block = "\n".join(lines[i:end])
        m = HEAD.match(lines[i] + "\n")
        tid, title = m.group(1), m.group(2)
        fm = FIELD.search(block)
        if not fm:
            fail("fields", "%s (%s) has no parseable meta line" % (tid, f))
            continue
        if fm.group(2) not in EFFORTS:
            fail("effort", "%s (%s) has effort %r, not one of %s"
                 % (tid, f, fm.group(2), ", ".join(EFFORTS)))
        deps = re.findall(TID, fm.group(5)) if fm.group(4) == "Depends" else []
        tasks[tid] = dict(
            file=f, title=title, block=block, model=fm.group(1),
            effort=fm.group(2), size=fm.group(3), kind=fm.group(4), deps=deps,
        )
        order.append(tid)

if len(tasks) != len(order):
    fail("dup", "duplicate task ids detected")

# --------------------------------------------------------- 1. reference sanity
for tid, t in tasks.items():
    for d in t["deps"]:
        if d not in tasks:
            fail("deps", "%s depends on undefined %s" % (tid, d))

allrefs = set()
for f in EPIC_FILES + glob.glob("*.md"):
    if f.endswith("plan-review.md"):
        continue
    allrefs |= set(re.findall(TID, read(f)))
for r in sorted(allrefs - set(tasks)):
    # `T1.24` is a legitimate way to name the T1.24a-f family in prose. Only an
    # id that names neither a task nor a family of them is a broken reference.
    if sum(1 for t in tasks if t.startswith(r)) >= 2:
        continue
    fail("refs", "reference to undefined task %s" % r)

# ------------------------------------------------------------- 2. no cycles
color = {k: 0 for k in tasks}


def dfs(n, st):
    color[n] = 1
    st.append(n)
    for m in tasks[n]["deps"]:
        if m not in tasks:
            continue
        if color[m] == 1:
            fail("cycle", " -> ".join(st[st.index(m):] + [m]))
        elif color[m] == 0:
            dfs(m, st)
    st.pop()
    color[n] = 2


for n in list(tasks):
    if color[n] == 0:
        dfs(n, [])

# ------------------------------------------- 3. epic entry tasks carry the gate
# Each epic's first-startable tasks must transitively require the prior gate,
# unless the task text explicitly claims an exemption.
GATE_OF = {"E1": "T0.17", "E2": "T1.50", "E3": "T2.41"}
EPIC_OF = {"E0": "T0.", "E1": "T1.", "E2": "T2.", "E3": "T3.", "E4": "T4.", "EH1": "TH1."}


def reaches(src, target, seen=None):
    seen = seen or set()
    if src in seen:
        return False
    seen.add(src)
    for d in tasks.get(src, {}).get("deps", []):
        if d == target or reaches(d, target, seen):
            return True
    return False


for epic, gate in GATE_OF.items():
    prefix = EPIC_OF[epic]
    for tid, t in tasks.items():
        if not tid.startswith(prefix):
            continue
        if reaches(tid, gate):
            continue
        if "gate-exempt" in t["block"]:
            continue
        fail("gate", "%s cannot reach its epic entry gate %s and claims no exemption" % (tid, gate))

# ------------------------------- 4. honesty specs named in their owning tasks
e2e = read("e2e-test-plan.md")
spec_rows = re.findall(r"^\| `(honesty/[\w-]+)` \| .+ \| (%s) \|$" % TID, e2e, re.M)
if not spec_rows:
    fail("honesty", "no honesty-suite rows parsed from e2e-test-plan.md")
for spec, owner in spec_rows:
    if owner not in tasks:
        fail("honesty", "spec %s names unknown owner %s" % (spec, owner))
    elif spec not in tasks[owner]["block"]:
        fail("honesty", "spec %s is NOT named in %s's task text (the e2e plan claims it is)" % (spec, owner))

# --------------------------------------------- 5. inert objects have writers
risks = read("risks-and-lanes.md")
for obj, writer in re.findall(r"`([\w\[\]\.]+)` → (%s)" % TID, risks):
    if writer not in tasks:
        fail("inert", "inert object %s names unknown writer %s" % (obj, writer))

# ------------------------------- 6. tasks other tasks call prerequisites exist
# A task whose text says another task builds something for it must depend on it.
for tid, t in tasks.items():
    for other in re.findall(r"\b(%s)\b (?:builds|lands|owns)\b" % TID, t["block"]):
        if other != tid and other in tasks and not reaches(tid, other):
            fail("wiring", "%s says %s builds something for it but does not depend on it" % (tid, other))

# ----------------------------------------------- 7. no dead-leaf infrastructure
depended = set()
for t in tasks.values():
    depended |= set(t["deps"])
for tid, t in tasks.items():
    if tid in depended:
        continue
    blk = t["block"]
    if re.search(r"first writer|primitive|channel|runner|scaffold|registry", blk, re.I):
        if "terminal-by-design" not in blk:
            fail("deadleaf", "%s looks like infrastructure but nothing depends on it" % tid)

# --------------------------------------------- 8. runbook section refs resolve
rb = read("agent-runbook.md")
sections = set(re.findall(r"^## (\d+)\. ", rb, re.M))
for f in EPIC_FILES + glob.glob("*.md") + glob.glob("scripts/*.py"):
    for ref in re.findall(r"runbook §(\d+)", read(f)):
        if ref not in sections:
            fail("runbook", "%s cites runbook §%s which does not exist" % (f, ref))
for ref in re.findall(r"(?<!runbook )§(\d+)['’]?s? (?:claim|definition|bootstrapping)", rb):
    if ref not in sections:
        fail("runbook", "agent-runbook self-reference §%s does not exist" % ref)

# --------------------------------------------------- 9. counts are consistent
n = len(tasks)
for f in ["README.md", "progress.md", "risks-and-lanes.md", "plan-review.md"]:
    src = read(f)
    # Only corpus-wide totals — per-epic and per-lane counts are legitimately
    # different numbers, so match the shapes that claim to speak for the whole plan.
    totals = re.findall(r"\*\*(\d+) tasks\b", src) + re.findall(r"\b(\d+) tasks across\b", src) + \
        re.findall(r"\b(\d+) tasks written in advance\b", src)
    for stale in totals:
        if stale != str(n):
            fail("counts", "%s says '%s tasks'; the corpus has %d" % (f, stale, n))

# ------------------------------------------- 10. ledger reconciles with itself
led = read("plan-review.md")
m = re.search(r"\*\*(\d+) findings\.\*\*", led)
ids = set(re.findall(r"^\| ([ABC]-[\w\d]+) \|", led, re.M))
if m and len(ids) != int(m.group(1)):
    fail("ledger", "plan-review claims %s findings but has %d dispositioned rows" % (m.group(1), len(ids)))

# ---------------------------------------------- 11. paths referenced are real
REPO = "../.."
for f in EPIC_FILES + glob.glob("*.md"):
    for p in re.findall(r"`((?:backend|frontend|docs|scripts)/[\w./-]+)`", read(f)):
        if any(ch in p for ch in "<>*"):
            continue
        if p.endswith("/"):
            p = p[:-1]
        full = os.path.join(REPO, p)
        if os.path.exists(full):
            continue
        # only assert paths that claim to exist today
        if "spikes" in p or p.startswith("docs/design"):
            fail("paths", "%s references %s which does not exist" % (f, p))

# --------------------------------------------------------------- report
if FAILS:
    by = {}
    for cat, msg in FAILS:
        by.setdefault(cat, []).append(msg)
    for cat in sorted(by):
        print("FAIL [%s] (%d)" % (cat, len(by[cat])))
        for msg in by[cat][:20]:
            print("   ", msg)
        if len(by[cat]) > 20:
            print("    ... and %d more" % (len(by[cat]) - 20))
    print("\n%d checks failed across %d tasks" % (len(FAILS), len(tasks)))
    sys.exit(1)

print("PLAN GREEN — %d tasks, all structural claims verified" % len(tasks))
