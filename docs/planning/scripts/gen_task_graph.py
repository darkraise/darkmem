"""Regenerate the Mermaid task-dependency graphs in risks-and-lanes.md.

Derived from each task's `Depends:` field, so the picture cannot drift from the
plan. Run after any task is added, split, or re-pointed:

    cd docs/planning && python scripts/gen_task_graph.py
"""

import glob
import io
import re

TID = r"T(?:H1|[0-4])\.\d{2,3}[a-z]?"
HEAD = re.compile(r"^#### (%s) — (.+)$" % TID)
LANE = re.compile(r"^## Lane ([A-Z]) — (.+)$")
DEP = re.compile(r"`Depends: ([^`]*)`")
SIZE = re.compile(r"`Size: ([SML])`")

EPICS = [
    ("E0", "Phase 0 · baseline & harness", "tasks/E0-baseline-and-harness.md"),
    ("E1", "Phase 1 · engine core", "tasks/E1-engine-core.md"),
    ("E2", "Phase 2 · truth core", "tasks/E2-truth-core.md"),
    ("E3", "Phase 3 · synthesis & reach", "tasks/E3-synthesis-and-reach.md"),
    ("E4", "Phase 4 · hardening & scale", "tasks/E4-hardening-and-scale.md"),
    ("EH1", "H1 · documents / PKM", "tasks/EH1-documents-pkm.md"),
]

# Gate tasks get a distinct shape — they are barriers, not ordinary work.
GATES = {"T0.17", "T1.50", "T2.40", "T2.41", "T3.22", "TH1.10"}

STOP = {
    "the", "a", "an", "and", "of", "for", "with", "to", "in", "on", "its",
    "+", "-", "—", "·",
}


def nid(t):
    return t.replace(".", "_")


def short(title, limit=30):
    """A label short enough to keep the graph readable."""
    title = re.sub(r"`|\*\*|\(.*?\)", "", title).strip()
    # Only drop a stopword when it is genuinely lowercase prose — FOR in
    # "FOR UPDATE SKIP LOCKED" is not the preposition "for".
    words = [w for w in title.split() if not (w.islower() and w in STOP)]
    out = " ".join(words)
    if len(out) > limit:
        out = out[: limit - 1].rstrip() + "…"
    return out.replace('"', "'")


def parse(path):
    """-> [(tid, title, lane_letter, lane_name, size, [deps])] in file order."""
    lines = io.open(path, encoding="utf-8").read().split("\n")
    rows = []
    lane = ("?", "unassigned")
    for i, l in enumerate(lines):
        lm = LANE.match(l)
        if lm:
            lane = (lm.group(1), lm.group(2))
            continue
        m = HEAD.match(l)
        if not m:
            continue
        deps, size = [], "M"
        for j in range(i + 1, min(i + 4, len(lines))):
            d = DEP.search(lines[j])
            if d:
                deps = re.findall(TID, d.group(1))
                s = SIZE.search(lines[j])
                if s:
                    size = s.group(1)
                break
            s = SIZE.search(lines[j])
            if s:
                size = s.group(1)
        rows.append((m.group(1), m.group(2), lane[0], lane[1], size, deps))
    return rows


all_rows = {}
for code, _, path in EPICS:
    all_rows[code] = parse(path)

owner = {}
for code, rows in all_rows.items():
    for r in rows:
        owner[r[0]] = code

# ---- critical path over the whole graph -----------------------------------
edges = {r[0]: r[5] for rows in all_rows.values() for r in rows}
memo, choice = {}, {}


def depth(n):
    if n in memo:
        return memo[n]
    memo[n] = 1
    best, pick = 0, None
    for m in edges.get(n, []):
        if m in edges:
            d = depth(m)
            if d > best:
                best, pick = d, m
    memo[n], choice[n] = best + 1, pick
    return memo[n]


end = max(edges, key=depth)
crit, cur = [], end
while cur:
    crit.append(cur)
    cur = choice.get(cur)
crit = set(crit)

out = []
out.append("<!-- BEGIN GENERATED TASK GRAPHS — regenerate with scripts/gen_task_graph.py -->")
out.append("")
out.append("### How to read these")
out.append("")
out.append(
    "Arrows point **prerequisite → dependent**, so work flows left to right. Boxes are\n"
    "grouped by lane. Shapes and colours carry three facts:"
)
out.append("")
out.append("- **`{{hexagon}}` = a gate task.** A barrier, not ordinary work — everything in the")
out.append("  next epic waits on it regardless of what any `Depends` field says.")
out.append("- **Thick red border = on the critical path.** %d tasks long, ending at %s." % (len(crit), end))
out.append("  Shortening the plan means shortening this chain and nothing else.")
out.append("- **Dashed border = `Size: L`.** More than a day; needs a reviewed step-level plan")
out.append("  before any code (runbook §3).")
out.append("- **Faded nodes** are prerequisites owned by another epic, drawn for context.")
out.append("")
out.append("Titles are truncated — the full task is in its epic file, the state is in")
out.append("`progress.md`.")
out.append("")

# ---- top-level gate graph -------------------------------------------------
out.append("### The whole plan, at gate level")
out.append("")
out.append("```mermaid")
out.append("flowchart LR")
out.append('    E0["E0 · Phase 0<br/>baseline & harness<br/>%d tasks"]' % len(all_rows["E0"]))
out.append('    E1["E1 · Phase 1<br/>engine core<br/>%d tasks"]' % len(all_rows["E1"]))
out.append('    E2["E2 · Phase 2<br/>truth core<br/>%d tasks"]' % len(all_rows["E2"]))
out.append('    E3["E3 · Phase 3<br/>synthesis & reach<br/>%d tasks"]' % len(all_rows["E3"]))
out.append('    E4["E4 · Phase 4<br/>hardening<br/>%d tasks"]' % len(all_rows["E4"]))
out.append('    EH1["EH1 · H1<br/>documents / PKM<br/>%d tasks"]' % len(all_rows["EH1"]))
out.append('    EH2["EH2 · H2<br/>.NET migration<br/>outline only"]')
out.append('    GA{{"G-A<br/>harness green on the<br/>recorded baseline"}}')
out.append('    GB{{"G-B<br/>F1 parity · eval with twin<br/>isolation probe = 0"}}')
out.append('    GC{{"G-C<br/>promotion rate +<br/>false-promotion audit"}}')
out.append('    GD{{"G-D<br/>judge precision/recall<br/>on labelled gold"}}')
out.append('    GE{{"G-E<br/>coverage distribution<br/>holding in production"}}')
out.append('    GF{{"G-F<br/>core eval stable<br/>+ appetite"}}')
out.append('    GG{{"G-G<br/>target shipped +<br/>harness ported first"}}')
out.append('    DER["code deriver<br/>T2.27-T2.28"]')
out.append('    F7["F7 auto-research<br/>T3.07-T3.08"]')
out.append("    E0 --> GA --> E1 --> GB --> E2")
out.append("    E2 --> GC --> DER")
out.append("    E2 --> GD --> E3")
out.append("    E3 --> GE --> F7")
out.append("    E3 -.->|appetite| E4")
out.append("    E3 -.-> GF -.-> EH1")
out.append("    E3 -.-> GG -.-> EH2")
out.append("    classDef gate fill:#2d1b3d,stroke:#a855f7,stroke-width:2px,color:#e9d5ff")
out.append("    classDef horizon stroke-dasharray:5 3,opacity:0.65")
out.append("    class GA,GB,GC,GD,GE,GF,GG gate")
out.append("    class EH1,EH2,GF,GG horizon")
out.append("```")
out.append("")
out.append(
    "Solid edges are the committed path; dashed edges are appetite-gated. Every gate is a\n"
    "measured number in [`gate-ledger.md`](gate-ledger.md), never a judgement call."
)
out.append("")

# ---- per-epic graphs ------------------------------------------------------
for code, title, _ in EPICS:
    rows = all_rows[code]
    out.append("### %s — %s (%d tasks)" % (code, title, len(rows)))
    out.append("")
    out.append("```mermaid")
    out.append("flowchart LR")
    lanes = []
    for r in rows:
        key = (r[2], r[3])
        if key not in lanes:
            lanes.append(key)
    internal = {r[0] for r in rows}
    for letter, name in lanes:
        members = [r for r in rows if r[2] == letter and r[3] == name]
        out.append('    subgraph L%s%s["Lane %s — %s"]' % (code, letter, letter, short(name, 34)))
        out.append("    direction TB")
        for tid, ttitle, _, _, size, _ in members:
            label = "%s<br/>%s" % (tid, short(ttitle))
            if tid in GATES:
                out.append('        %s{{"%s"}}' % (nid(tid), label))
            else:
                out.append('        %s["%s"]' % (nid(tid), label))
        out.append("    end")
    # external prerequisites
    ext = []
    for r in rows:
        for d in r[5]:
            if d not in internal and d in owner and d not in ext:
                ext.append(d)
    for d in ext:
        out.append('    %s["%s<br/><i>%s</i>"]' % (nid(d), d, owner[d]))
    for r in rows:
        for d in r[5]:
            if d in internal or d in owner:
                out.append("    %s --> %s" % (nid(d), nid(r[0])))
    out.append("    classDef crit stroke:#ef4444,stroke-width:3px")
    out.append("    classDef large stroke-dasharray:6 3")
    out.append("    classDef ext fill:#1f2937,stroke:#4b5563,color:#9ca3af,opacity:0.7")
    c = [nid(r[0]) for r in rows if r[0] in crit]
    lg = [nid(r[0]) for r in rows if r[4] == "L"]
    if c:
        out.append("    class %s crit" % ",".join(c))
    if lg:
        out.append("    class %s large" % ",".join(lg))
    if ext:
        out.append("    class %s ext" % ",".join(nid(d) for d in ext))
    out.append("```")
    out.append("")

out.append("<!-- END GENERATED TASK GRAPHS -->")

block = "\n".join(out)

p = "risks-and-lanes.md"
s = io.open(p, encoding="utf-8").read()
BEGIN = "<!-- BEGIN GENERATED TASK GRAPHS"
END = "<!-- END GENERATED TASK GRAPHS -->"
section = "## Part 2 — The task graph\n\n" + block + "\n\n---\n\n"
if BEGIN in s:
    pre = s[: s.index(BEGIN)]
    post = s[s.index(END) + len(END):]
    s = pre + block + post
else:
    anchor = "---\n\n## Part 2 — Risk register"
    assert anchor in s, "risk-register anchor not found"
    s = s.replace(anchor, "---\n\n" + section + "## Part 3 — Risk register", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)

print("critical path (%d): %s" % (len(crit), " -> ".join(reversed([t for t in
      sorted(crit, key=lambda x: -memo[x])]))[:400]))
print("graphs written for:", ", ".join(c for c, _, _ in EPICS))
