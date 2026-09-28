## A1 — Task 1
Reason: argpartition on -block allocates a negated copy, breaking the 12-byte-per-cell scratch bound the spec and the code comment state.
Cost if wrong: about 45 MB extra peak per chunk at 20,000 nodes; Task 8's RSS budget would still catch it.
### Old
````text
        top = np.argpartition(-block, k_eff - 1, axis=1)[:, :k_eff]
````
### New
````text
        top = np.argpartition(block, -k_eff, axis=1)[:, -k_eff:]
````

## A2 — Task 7
Reason: Commit subject is 53 characters; the Global Constraints cap subjects at 50.
Cost if wrong: one non-conforming commit subject in the history.
### Old
````text
git commit -m "fix(graph): scope the entity overlay to plotted nodes
````
### New
````text
git commit -m "fix(graph): scope the overlay to plotted nodes
````

## A3 — Task 14
Reason: The spec requires a frontend unit test for hull-group memoisation; a memo inside the renderer's closure cannot be tested under jsdom.
Cost if wrong: one extra exported helper and two unit tests.
### Old
````text
- [ ] **Step 4: Use cached hulls in the renderer**

In `frontend/src/features/graph/components/graph-2d-renderer.tsx`:

1. In the `@/features/graph/lib/graph-geometry` import, replace `drawHullForSigma,` with `drawFramedHull,` and `framedHullVertices,`, and add `type Point,` to that import.

2. Below `const LABEL_ZOOM_RATIO = 0.72` add:

```ts
/** While the layout runs, hull shapes refresh at most this often; camera
 *  moves never recompute them. */
const HULL_REFRESH_MS = 250
```

3. Directly before `function drawHulls() {` add:

```ts
    // Hull groups change only with the data or the mode, and hull shapes only
    // while the layout moves. Recomputing both on every frame is what made a
    // large graph stutter on pan.
    let hullGroupsFor: { memories: UnifiedMemory[]; mode: HullMode } | null = null
    let hullGroups = new Map<string, string[]>()
    const framedHulls = new Map<string, Point[]>()
    let framedHullsAt = -Infinity
    let framedHullsStale = true
```

4. Inside `drawHulls`, replace

```ts
      const hullGroups = computeHullGroups(
        filteredMemoriesRef.current,
        hullModeRef.current,
      )
```

with

```ts
      const memories = filteredMemoriesRef.current
      const mode = hullModeRef.current
      if (
        !hullGroupsFor ||
        hullGroupsFor.memories !== memories ||
        hullGroupsFor.mode !== mode
      ) {
        hullGroups = computeHullGroups(memories, mode)
        hullGroupsFor = { memories, mode }
        framedHullsStale = true
      }
      const now = performance.now()
      const layoutRunning = fa2Ref.current?.isRunning() ?? false
      if (
        framedHullsStale ||
        (layoutRunning && now - framedHullsAt >= HULL_REFRESH_MS)
      ) {
        framedHulls.clear()
        for (const [groupKey, members] of hullGroups) {
          framedHulls.set(groupKey, framedHullVertices(sigmaRef.current, members))
        }
        framedHullsAt = now
        framedHullsStale = false
      }
```

5. In the same loop replace

```ts
        const hull = drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.06,
          0.28,
        )
```

with

```ts
        const hull = drawFramedHull(
          hullCtx,
          sigmaRef.current,
          framedHulls.get(groupKey) ?? [],
          color,
          0.06,
          0.28,
        )
```

(the chip below keeps `members.length` as its count).

6. Replace the FA2 stop timer body so the final positions refresh the hulls:

```ts
    fa2StopTimerRef.current = setTimeout(() => {
      fa2StopTimerRef.current = null
      if (fa2Ref.current) fa2Ref.current.stop()
      framedHullsStale = true
      sigmaRef.current?.refresh()
    }, scale.layoutMs)
```
````
### New
````text
- [ ] **Step 4: Cache hull groups and shapes, then use the cache in the renderer**

The memo lives in `graph-geometry.ts` as a pure helper so jsdom can test it; the renderer's closure only holds an instance.

1. In `frontend/src/features/graph/lib/graph-geometry.ts`, directly after `drawFramedHull`, add:

```ts
/**
 * Hull groups and their framed-space shapes, recomputed only when they can
 * have changed.
 *
 * Groups depend on the memories and the mode, so they are rebuilt only when
 * either identity moves. Shapes depend on node positions, which move only
 * while the layout runs: they refresh at most every `refreshMs` then, and
 * once more after `invalidate`.
 */
export function createHullShapeCache<M>(
  computeGroups: (memories: M[], mode: HullMode) => Map<string, string[]>,
  refreshMs: number,
) {
  let groupsFor: { memories: M[]; mode: HullMode } | null = null
  let groups = new Map<string, string[]>()
  const shapes = new Map<string, Point[]>()
  let shapesAt = -Infinity
  let stale = true
  return {
    update(
      memories: M[],
      mode: HullMode,
      sigma: Sigma,
      layoutRunning: boolean,
      now: number,
    ): Map<string, string[]> {
      if (
        !groupsFor ||
        groupsFor.memories !== memories ||
        groupsFor.mode !== mode
      ) {
        groups = computeGroups(memories, mode)
        groupsFor = { memories, mode }
        stale = true
      }
      if (stale || (layoutRunning && now - shapesAt >= refreshMs)) {
        shapes.clear()
        for (const [groupKey, members] of groups) {
          shapes.set(groupKey, framedHullVertices(sigma, members))
        }
        shapesAt = now
        stale = false
      }
      return groups
    },
    shape(groupKey: string): Point[] {
      return shapes.get(groupKey) ?? []
    },
    invalidate(): void {
      stale = true
    },
  }
}
```

2. In `frontend/src/features/graph/lib/__tests__/framed-hull.test.ts`, change the `../graph-geometry` import to `import { createHullShapeCache, drawFramedHull, framedHullVertices, type HullMode } from "../graph-geometry"` and append:

```ts
describe("createHullShapeCache", () => {
  const GROUPS = new Map([["0", ["a", "b", "c", "d", "inner"]]])
  const groupsOf = (_memories: { id: string }[], _mode: HullMode) => GROUPS

  it("regroups only when the memories or the mode change", () => {
    const { sigma } = fakeSigma()
    const compute = vi.fn(groupsOf)
    const cache = createHullShapeCache(compute, 250)
    const memories = [{ id: "a" }]
    cache.update(memories, "cluster", sigma, false, 0)
    cache.update(memories, "cluster", sigma, true, 1000)
    expect(compute).toHaveBeenCalledTimes(1)
    const next = [...memories]
    cache.update(next, "cluster", sigma, false, 2000)
    expect(compute).toHaveBeenCalledTimes(2)
    cache.update(next, "tag", sigma, false, 3000)
    expect(compute).toHaveBeenCalledTimes(3)
  })

  it("reshapes at most every refreshMs while the layout runs, and once after invalidate", () => {
    const { sigma } = fakeSigma()
    const reads = vi.spyOn(sigma, "getNodeDisplayData")
    const cache = createHullShapeCache(groupsOf, 250)
    const memories = [{ id: "a" }]
    cache.update(memories, "cluster", sigma, true, 0)
    expect(reads).toHaveBeenCalledTimes(5)
    cache.update(memories, "cluster", sigma, true, 100)
    expect(reads).toHaveBeenCalledTimes(5)
    cache.update(memories, "cluster", sigma, true, 300)
    expect(reads).toHaveBeenCalledTimes(10)
    cache.update(memories, "cluster", sigma, false, 1000)
    expect(reads).toHaveBeenCalledTimes(10)
    cache.invalidate()
    cache.update(memories, "cluster", sigma, false, 1001)
    expect(reads).toHaveBeenCalledTimes(15)
    expect(cache.shape("0")).toHaveLength(4)
    expect(cache.shape("missing")).toEqual([])
  })
})
```

Run: `cd frontend && timeout 300 npx vitest run src/features/graph/lib/__tests__/framed-hull.test.ts`
Expected: PASS.

3. In `frontend/src/features/graph/components/graph-2d-renderer.tsx`, in the `@/features/graph/lib/graph-geometry` import, replace `drawHullForSigma,` with `createHullShapeCache,` and `drawFramedHull,` (`computeHullGroups` stays imported: the cache calls it).

4. Below `const LABEL_ZOOM_RATIO = 0.72` add:

```ts
/** While the layout runs, hull shapes refresh at most this often; camera
 *  moves never recompute them. */
const HULL_REFRESH_MS = 250
```

5. Directly before `function drawHulls() {` add:

```ts
    // Hull groups change only with the data or the mode, and hull shapes only
    // while the layout moves. Recomputing both on every frame is what made a
    // large graph stutter on pan.
    const hullCache = createHullShapeCache(computeHullGroups, HULL_REFRESH_MS)
```

6. Inside `drawHulls`, replace

```ts
      const hullGroups = computeHullGroups(
        filteredMemoriesRef.current,
        hullModeRef.current,
      )
```

with

```ts
      const hullGroups = hullCache.update(
        filteredMemoriesRef.current,
        hullModeRef.current,
        sigmaRef.current,
        fa2Ref.current?.isRunning() ?? false,
        performance.now(),
      )
```

7. In the same loop replace

```ts
        const hull = drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.06,
          0.28,
        )
```

with

```ts
        const hull = drawFramedHull(
          hullCtx,
          sigmaRef.current,
          hullCache.shape(groupKey),
          color,
          0.06,
          0.28,
        )
```

(the chip below keeps `members.length` as its count).

8. Replace the FA2 stop timer body so the final positions refresh the hulls:

```ts
    fa2StopTimerRef.current = setTimeout(() => {
      fa2StopTimerRef.current = null
      if (fa2Ref.current) fa2Ref.current.stop()
      hullCache.invalidate()
      sigmaRef.current?.refresh()
    }, scale.layoutMs)
```
````

## A4 — Task 16
Reason: The spec's measurement dataset has 100,000 edges; five draws per node yield about 93,000 at 20,000 nodes.
Cost if wrong: a slightly denser 2k story; no test depends on the harness's edge count.
### Old
````text
  const graph = useMemo(() => syntheticMemoryGraph(nodes, 60, 5), [nodes])
````
### New
````text
  // Six draws per node give about 110,000 distinct edges at 20,000 nodes,
  // above the 100,000 the scale measurement is specified at.
  const graph = useMemo(() => syntheticMemoryGraph(nodes, 60, 6), [nodes])
````

## A5 — Header
Reason: Since A3, hull memoisation is unit-tested on `createHullShapeCache`; the header still says only Task 17 can cover it.
Cost if wrong: Task 14's implementer skips or doubts the new cache tests in step 2.
### Old
````text
- The spec's hull-group memoisation test is covered by the Task 17 measurement only: the memo lives in the renderer's closure, which jsdom cannot run (no WebGL).
````
### New
````text
- The spec's hull-group memoisation test runs against `createHullShapeCache` in `graph-geometry.ts` (Task 14, `framed-hull.test.ts`), a WebGL-free helper the renderer's closure holds one instance of; the renderer itself cannot run under jsdom (no WebGL), so Task 17's pan and zoom measurement covers the wiring.
````

## A6 — Task 17
Reason: The Playwright MCP server's Chromium refuses to launch as root without `--no-sandbox`, and its launch flags cannot be set from the session; the repo's own Playwright library passes `--no-sandbox` by default and has the matching revision 1223 installed.
Cost if wrong: the fps figure comes from a headless shell rather than the MCP's browser; it is already reported as a lower bound under software WebGL, and a GPU check is still owed.
### Old
````text
- [ ] **Step 3: Measure each story in the Playwright MCP browser**

For the `Scale2k` id and then the `Scale20k` id:

1. `browser_navigate` to `http://localhost:6006/iframe.html?id=<id>&viewMode=story`.
````
### New
````text
- [ ] **Step 3: Measure each story in a scripted Playwright browser**

The Playwright MCP server's Chromium refuses to launch as root without `--no-sandbox`, and its launch flags are outside the session. Drive the same measurement from a scratch script, `measure-graph.cjs` in the session scratchpad directory (never in the repo), using the frontend's own Playwright library:

- `const { chromium } = require("/root/repositories/darkmem/frontend/node_modules/playwright")`
- `const browser = await chromium.launch()` (the library adds `--no-sandbox` unless `chromiumSandbox: true` is passed; do not pass it)
- `const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })`
- wrap both stories in `try { … } finally { await browser.close() }`

Each numbered action below maps one to one: `browser_navigate` → `await page.goto(url)`; `browser_evaluate` → `await page.evaluate(<the same function>)`; `browser_wait_for` 25 seconds → `await page.waitForTimeout(25000)`; `browser_run_code_unsafe` → `await (<the same async (page) => {…} function>)(page)`; `browser_take_screenshot` → `await page.screenshot({ path: "<scratchpad>/scale-20k.png" })`; Step 4's `browser_close` → the `finally`. Print, per story, the renderer string and the returned object as one JSON line.

Run: `timeout 600 node <scratchpad>/measure-graph.cjs`. If launch fails with "Executable doesn't exist", run `cd frontend && timeout 600 npx playwright install chromium-headless-shell chromium` once and retry; on any other launch failure, stop and report the error verbatim. Still never run `npx playwright test`.

In both Step 5 register notes, append `; driver: scripted Playwright 1.60 headless (MCP browser cannot launch as root)`.

For the `Scale2k` id and then the `Scale20k` id:

1. `browser_navigate` to `http://localhost:6006/iframe.html?id=<id>&viewMode=story`.
````

## A7 — Task 18
Reason: Task 18 required master before its own completion, but the executing-plans flow merges only after every task completes; split it into pre-merge gate steps and post-merge deploy steps.
Cost if wrong: the post-merge deploy is forgotten and the host serves the old image until someone acts on the owed ledger line.
### Old
````text
This task runs after dr-superpowers:finishing-a-development-branch has merged the branch into master: CLAUDE.md redeploys this host after every change that lands, and production must not run unmerged code.

- [ ] **Step 1: Check the precondition**

Run: `git branch --show-current && git log --oneline master | head -30`
Expected: the current branch is `master` and its log contains the commits of Tasks 1–17. If not, stop and report: the branch has not been merged yet.

- [ ] **Step 2: Run the merge gate**

Run: `timeout 3600 ./scripts/gate.sh`
Expected: exit 0. Exit 2 (`GATE BLOCKED`) names a missing toolchain, not a red gate. Exit 143 is an earlyoom kill: check `free -h`, re-run the named leg alone, and report both results rather than treating the kill as a failure.

- [ ] **Step 3: Build without pushing and check the built commit**
````
### New
````text
This task has two halves. Steps 1–2 run now, on `feat/memory-graph-scale`, inside the task loop, and they alone decide this task's `complete` ledger line. That line records the gated commit and must end `remaining: post-merge deploy (Task 18 Steps 3–6) owed after finishing-a-development-branch merges`. Steps 3–6 deploy production, and production must not run unmerged code, so they run only after the Final Review is clean and dr-superpowers:finishing-a-development-branch has merged the branch into master. The session that performs that merge runs them next, on master. Steps 3–6 push nothing. If the session ends before they run, its hand-off names Steps 3–6 as owed.

- [ ] **Step 1: Check the precondition**

Run: `git branch --show-current && git status --porcelain && git log --oneline master..HEAD | head -40`
Expected: the current branch is `feat/memory-graph-scale`, `git status --porcelain` prints nothing, and the log lists the commits of Tasks 1–17. If not, stop and report what differs.

- [ ] **Step 2: Run the merge gate on the branch**

Run: `timeout 3600 ./scripts/gate.sh && git rev-parse --short HEAD`
Expected: exit 0, then the gated commit's short sha, which goes into this task's ledger line. Exit 2 (`GATE BLOCKED`) names a missing toolchain, not a red gate. Exit 143 is an earlyoom kill: check `free -h`, re-run the named leg alone, and report both results rather than treating the kill as a failure.

**Post-merge steps (3–6), run only after finishing-a-development-branch has merged into master.** First run `git branch --show-current && git diff --quiet <gated commit> HEAD && echo "tree matches the gated commit"`. Expected: the branch is `master` and the line prints. If the branch is not `master`, stop and report that the merge has not happened. If the line does not print, master moved after the gate: re-run Step 2's gate on master, and a red gate there stops the deploy.

- [ ] **Step 3: Build without pushing and check the built commit**
````

## A8 — Task 8
Reason: Noise at scale 1.2 puts same-cluster cosine near 0.41, below the 0.5 threshold, so the bench measured an almost edgeless graph (510 edges at 20,000 nodes) and never timed the route's JSON encoding.
Cost if wrong: the dense run may exceed the cold budget, which turns a false PASS into an owner decision on register item 5.
### Old
````text
Resets darkmem_bench, seeds N memories with clustered synthetic vectors under
one fingerprint, then times GraphService.get_unified_graph(all_memories=True)
cold and warm and reports the process's peak RSS. Exits 1 when cold exceeds
10 s, warm exceeds 1 s, or peak RSS exceeds 1,500 MB.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import resource
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
# Standalone execution only puts this file's directory on sys.path; both
# `benchlib` and `app` must resolve before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import bench_db  # noqa: E402  (overrides DATABASE_URL first)

import numpy as np  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.repositories.vector import PostgresVectorRepository  # noqa: E402
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry  # noqa: E402
from app.services.graph import GraphService, reset_graph_caches  # noqa: E402

COLD_BUDGET_S = 10.0
WARM_BUDGET_S = 1.0
PEAK_RSS_BUDGET_MB = 1500
BATCH = 1000


def _peak_rss_mb() -> float:
    # ru_maxrss is kilobytes on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class _BenchLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        self.calls = 0

    def llm_fingerprint(self) -> str:
        return self.fingerprint

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        return "bench cluster"


def _vectors(nodes: int, dims: int, clusters: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    centers = rng.normal(size=(clusters, dims)).astype(np.float32)
    x = centers[rng.integers(0, clusters, nodes)] + rng.normal(scale=1.2, size=(nodes, dims)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


async def _seed(nodes: int, dims: int, clusters: int, fingerprint: str) -> None:
    vectors = _vectors(nodes, dims, clusters)
    async with bench_db.session_factory() as session:
        await embedder_registry.register(
            session, EmbedderInfo(fingerprint=fingerprint, model_id="bench-graph-scale", dims=dims, source="llm"),
        )
        await session.commit()
        child = child_table("memory_embeddings", fingerprint)
        for start in range(0, nodes, BATCH):
            ids = [uuid.uuid4() for _ in range(min(BATCH, nodes - start))]
            await session.execute(
                text(
                    "INSERT INTO memories (id, content, source, importance, metadata, project, "
                    "status, memory_type, is_archived) "
                    "VALUES (:id, :content, 'bench', 0.5, '{}'::jsonb, 'bench', 'active', 'fact', FALSE)"
                ),
                [{"id": mid, "content": f"bench memory {start + i}"} for i, mid in enumerate(ids)],
            )
            await session.execute(
                text(
                    f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
                ),
                [
                    {
                        "mid": mid,
                        "fp": fingerprint,
                        "vec": "[" + ",".join(f"{v:.5f}" for v in vectors[start + i]) + "]",
                        "payload": json.dumps({"content": f"bench memory {start + i}", "source": "bench", "tags": [f"topic-{(start + i) % clusters}"]}),
                    }
                    for i, mid in enumerate(ids)
                ],
            )
            await session.commit()


async def _time_graph(fingerprint: str) -> tuple[float, float, dict, int]:
    llm = _BenchLLM(fingerprint)
    reset_graph_caches()
    async with bench_db.session_factory() as session:
        svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=llm)
        t0 = time.perf_counter()
        cold = await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t1 = time.perf_counter()
        await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t2 = time.perf_counter()
    return t1 - t0, t2 - t1, cold, llm.calls


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=20_000)
    parser.add_argument("--dims", type=int, default=1024)
    parser.add_argument("--clusters", type=int, default=60)
    args = parser.parse_args()
    fingerprint = f"bench-graph-scale|{args.dims}"

    await bench_db.reset_bench_db()
    t_seed = time.perf_counter()
    await _seed(args.nodes, args.dims, args.clusters, fingerprint)
    print(f"seeded {args.nodes} memories in {time.perf_counter() - t_seed:.1f}s")

    rss_before = _peak_rss_mb()
    cold_s, warm_s, result, llm_calls = await _time_graph(fingerprint)
    rss_after = _peak_rss_mb()
    print(
        f"nodes={len(result['memories'])} total={result['total_memories']} "
        f"edges={len(result['similarity_edges'])} clusters={len(result['clusters'])} "
        f"llm_calls={llm_calls} cold={cold_s:.2f}s warm={warm_s:.3f}s "
        f"peak_rss={rss_after:.0f}MB (after seeding {rss_before:.0f}MB)"
    )
    await bench_db.engine.dispose()
    ok = (
        cold_s <= COLD_BUDGET_S
        and warm_s <= WARM_BUDGET_S
        and rss_after <= PEAK_RSS_BUDGET_MB
        and len(result["memories"]) == args.nodes
    )
    print(
        "PASS" if ok else
        f"FAIL (budgets: cold <= {COLD_BUDGET_S}s, warm <= {WARM_BUDGET_S}s, "
        f"peak RSS <= {PEAK_RSS_BUDGET_MB}MB)"
    )
    return 0 if ok else 1
````
### New
````text
Resets darkmem_bench, seeds N memories with clustered synthetic vectors under
one fingerprint, then times GraphService.get_unified_graph(all_memories=True)
cold and warm, times the JSON encoding of its result as the route serves it,
and reports the process's peak RSS. Exits 1 when cold exceeds 10 s, warm
exceeds 1 s, peak RSS exceeds 1,500 MB, or the seeded data yields fewer than
two similarity edges per node.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import resource
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
# Standalone execution only puts this file's directory on sys.path; both
# `benchlib` and `app` must resolve before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import bench_db  # noqa: E402  (overrides DATABASE_URL first)

import numpy as np  # noqa: E402
from fastapi.encoders import jsonable_encoder  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.repositories.vector import PostgresVectorRepository  # noqa: E402
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry  # noqa: E402
from app.services.graph import GraphService, reset_graph_caches  # noqa: E402

COLD_BUDGET_S = 10.0
WARM_BUDGET_S = 1.0
PEAK_RSS_BUDGET_MB = 1500
BATCH = 1000
# Same-cluster cosine is about 1 / (1 + NOISE**2), 0.8 here, so every node's
# top-k clears the 0.5 threshold as on a real corpus. Noisier data leaves the
# kNN graph nearly empty and times nothing.
NOISE = 0.5
MIN_EDGES_PER_NODE = 2


def _peak_rss_mb() -> float:
    # ru_maxrss is kilobytes on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class _BenchLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        self.calls = 0

    def llm_fingerprint(self) -> str:
        return self.fingerprint

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        return "bench cluster"


def _vectors(nodes: int, dims: int, clusters: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    centers = rng.normal(size=(clusters, dims)).astype(np.float32)
    x = centers[rng.integers(0, clusters, nodes)] + rng.normal(scale=NOISE, size=(nodes, dims)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


async def _seed(nodes: int, dims: int, clusters: int, fingerprint: str) -> None:
    vectors = _vectors(nodes, dims, clusters)
    async with bench_db.session_factory() as session:
        await embedder_registry.register(
            session, EmbedderInfo(fingerprint=fingerprint, model_id="bench-graph-scale", dims=dims, source="llm"),
        )
        await session.commit()
        child = child_table("memory_embeddings", fingerprint)
        for start in range(0, nodes, BATCH):
            ids = [uuid.uuid4() for _ in range(min(BATCH, nodes - start))]
            await session.execute(
                text(
                    "INSERT INTO memories (id, content, source, importance, metadata, project, "
                    "status, memory_type, is_archived) "
                    "VALUES (:id, :content, 'bench', 0.5, '{}'::jsonb, 'bench', 'active', 'fact', FALSE)"
                ),
                [{"id": mid, "content": f"bench memory {start + i}"} for i, mid in enumerate(ids)],
            )
            await session.execute(
                text(
                    f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
                ),
                [
                    {
                        "mid": mid,
                        "fp": fingerprint,
                        "vec": "[" + ",".join(f"{v:.5f}" for v in vectors[start + i]) + "]",
                        "payload": json.dumps({"content": f"bench memory {start + i}", "source": "bench", "tags": [f"topic-{(start + i) % clusters}"]}),
                    }
                    for i, mid in enumerate(ids)
                ],
            )
            await session.commit()


async def _time_graph(fingerprint: str) -> tuple[float, float, dict, int]:
    llm = _BenchLLM(fingerprint)
    reset_graph_caches()
    async with bench_db.session_factory() as session:
        svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=llm)
        t0 = time.perf_counter()
        cold = await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t1 = time.perf_counter()
        await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t2 = time.perf_counter()
    return t1 - t0, t2 - t1, cold, llm.calls


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=20_000)
    parser.add_argument("--dims", type=int, default=1024)
    parser.add_argument("--clusters", type=int, default=60)
    args = parser.parse_args()
    fingerprint = f"bench-graph-scale|{args.dims}"

    await bench_db.reset_bench_db()
    t_seed = time.perf_counter()
    await _seed(args.nodes, args.dims, args.clusters, fingerprint)
    print(f"seeded {args.nodes} memories in {time.perf_counter() - t_seed:.1f}s")

    rss_before = _peak_rss_mb()
    cold_s, warm_s, result, llm_calls = await _time_graph(fingerprint)
    # The route declares no response model, so every response, cache hits
    # included, pays this encoding on the event loop.
    t_encode = time.perf_counter()
    body = json.dumps(jsonable_encoder(result), ensure_ascii=False, separators=(",", ":"))
    encode_s = time.perf_counter() - t_encode
    rss_after = _peak_rss_mb()
    edges = len(result["similarity_edges"])
    print(
        f"nodes={len(result['memories'])} total={result['total_memories']} "
        f"edges={edges} clusters={len(result['clusters'])} "
        f"llm_calls={llm_calls} cold={cold_s:.2f}s warm={warm_s:.3f}s "
        f"encode={encode_s:.2f}s body={len(body) / 1_000_000:.1f}MB "
        f"peak_rss={rss_after:.0f}MB (after seeding {rss_before:.0f}MB)"
    )
    await bench_db.engine.dispose()
    ok = (
        cold_s <= COLD_BUDGET_S
        and warm_s <= WARM_BUDGET_S
        and rss_after <= PEAK_RSS_BUDGET_MB
        and len(result["memories"]) == args.nodes
        and edges >= MIN_EDGES_PER_NODE * args.nodes
    )
    print(
        "PASS" if ok else
        f"FAIL (budgets: cold <= {COLD_BUDGET_S}s, warm <= {WARM_BUDGET_S}s, "
        f"peak RSS <= {PEAK_RSS_BUDGET_MB}MB, edges >= {MIN_EDGES_PER_NODE} x nodes)"
    )
    return 0 if ok else 1
````

## Final-review changes outside the plan text

- The kNN pass (`PostgresVectorRepository.get_louvain_clustered_vectors`, Task 3)
  runs on a single-thread executor (`_KNN_EXECUTOR` in
  `backend/app/repositories/vector.py`) rather than directly on the event
  loop as Task 3's code block specified: invariant 13 pins one server
  process, and a multi-second pass on the loop would stall every capture,
  MCP call, websocket and scheduled job for its duration. Commit
  `perf(graph): run the kNN pass off the event loop`.
