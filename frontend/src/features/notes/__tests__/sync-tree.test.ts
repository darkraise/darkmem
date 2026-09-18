import { describe, expect, it } from "vitest"
import { applyOp, nextOp, treesEqual, type SyncBlock, type SyncTree } from "../lib/sync-tree"
import { CONTAINERS, FakeServer, Refused, type Props } from "./fake-page-server"
import { pick, rng } from "./seeded"

const TYPES = ["paragraph", "heading", "list", "todo", "toggle", "quote", "code", "callout", "divider"]

function propsFor(type: string, r: () => number): Props {
  switch (type) {
    case "heading":
      return { level: 1 + Math.floor(r() * 6) }
    case "list":
      return { ordered: r() < 0.5, marker: r() < 0.5 ? "-" : "1." }
    case "todo":
      return { checked: r() < 0.5 }
    case "callout":
      return { variant: pick(["info", "warning", "error", "success"], r) }
    case "code":
      return { language: r() < 0.5 ? "text" : "py" }
    default:
      return null
  }
}

let counter = 0
const freshId = () => `b${++counter}`

function randomInsert(server: FakeServer, r: () => number) {
  const containers = server.rows.filter((x) => CONTAINERS.includes(x.type))
  const parent = r() < 0.4 && containers.length ? pick(containers, r).id : null
  const siblings = server.kids(parent)
  const after = r() < 0.3 || !siblings.length ? null : pick(siblings, r).id
  const type = pick(TYPES, r)
  server.apply({
    kind: "insert",
    blocks: [{ block_id: freshId(), type, text: `t${Math.floor(r() * 5)}`, properties: propsFor(type, r), parent_id: parent, after_block_id: after }],
  })
}

/** A random tree obeying the page rules, built through the fake server. */
function genTree(r: () => number, n: number): SyncBlock[] {
  const server = new FakeServer([])
  for (let i = 0; i < n; i++) randomInsert(server, r)
  return server.tree()
}

/** Random edits of the kinds the editor makes. An edit the rules refuse is
 *  skipped, so every desired tree is one the editor could hold. */
function edit(tree: SyncTree, r: () => number, k: number): SyncBlock[] {
  const server = new FakeServer(tree)
  for (let i = 0; i < k; i++) {
    const kind = r()
    try {
      if (kind < 0.3 || server.rows.length === 0) {
        randomInsert(server, r)
      } else if (kind < 0.45) {
        server.apply({ kind: "delete", id: pick(server.rows, r).id })
      } else if (kind < 0.7) {
        const row = pick(server.rows, r)
        const inside = server.subtree(row.id)
        const containers = server.rows.filter((x) => CONTAINERS.includes(x.type) && !inside.has(x.id))
        const parent = r() < 0.5 && containers.length ? pick(containers, r).id : null
        const siblings = server.kids(parent).filter((s) => s.id !== row.id)
        const after = r() < 0.3 || !siblings.length ? null : pick(siblings, r).id
        server.apply({ kind: "move", id: row.id, parentId: parent, afterId: after })
      } else if (kind < 0.85) {
        const row = pick(server.rows, r)
        const type = pick(TYPES, r)
        server.apply({ kind: "update", id: row.id, type, text: row.text, properties: propsFor(type, r) })
      } else {
        const row = pick(server.rows, r)
        server.apply({ kind: "update", id: row.id, type: row.type, text: `${row.text}!`, properties: row.props })
      }
    } catch (error) {
      if (!(error instanceof Refused)) throw error
    }
  }
  return server.tree()
}

/** Runs the sync loop against the fake server and returns how many writes
 *  it took, failing on any refusal, any drift between the snapshot and the
 *  server, a runaway loop, or stopping short. */
function converge(start: SyncTree, desired: SyncTree, label: string): number {
  const server = new FakeServer(start)
  let snapshot: SyncTree = start
  let writes = 0
  for (let op = nextOp(snapshot, desired); op !== null; op = nextOp(snapshot, desired)) {
    let refusal: Error | null = null
    try {
      server.apply(op)
    } catch (error) {
      refusal = error as Error
    }
    if (refusal) throw new Error(`${label}: server refused ${JSON.stringify(op)}: ${refusal.message}`)
    snapshot = applyOp(snapshot, op)
    if (!treesEqual(snapshot, server.tree())) {
      throw new Error(`${label}: snapshot drifted from the server after ${JSON.stringify(op)}`)
    }
    if (++writes > 4 * (start.length + desired.length) + 10) throw new Error(`${label}: did not converge`)
  }
  if (!treesEqual(snapshot, desired)) throw new Error(`${label}: stopped short of the desired tree`)
  return writes
}

const block = (id: string, parentId: string | null, type: string, properties: Props = null): SyncBlock => ({
  id,
  parentId,
  type,
  text: id,
  properties,
})
const BULLET = { ordered: false, marker: "-" }

describe("sync tree", () => {
  it("converges on any legal edit sequence, and the server accepts every write", () => {
    for (let seed = 0; seed < 1500; seed++) {
      const r = rng(seed)
      const start = genTree(r, Math.floor(r() * 12))
      const desired = edit(start, r, 1 + Math.floor(r() * 8))
      converge(start, desired, `seed ${seed}`)
    }
  })

  it("sends every new block as one batch and moves nothing else", () => {
    const start = [block("a", null, "paragraph"), block("b", null, "paragraph"), block("c", null, "paragraph")]
    const desired = [
      block("x", null, "paragraph"),
      start[0]!,
      block("y", null, "list", BULLET),
      block("y1", "y", "paragraph"),
      start[1]!,
      start[2]!,
    ]
    expect(nextOp(start, desired)).toEqual({
      kind: "insert",
      blocks: [
        { block_id: "x", type: "paragraph", text: "x", properties: null, parent_id: null, after_block_id: null },
        { block_id: "y", type: "list", text: "y", properties: BULLET, parent_id: null, after_block_id: "a" },
        { block_id: "y1", type: "paragraph", text: "y1", properties: null, parent_id: "y", after_block_id: null },
      ],
    })
    expect(converge(start, desired, "batch")).toBe(1)
  })

  it("never anchors on a sibling that only a later move brings under the parent", () => {
    const list = block("L", null, "list", BULLET)
    const x = block("X", null, "paragraph")
    const desired = [list, { ...x, parentId: "L" }, block("N", "L", "paragraph")]
    expect(converge([list, x], desired, "anchor")).toBe(2)
  })

  it("swaps an ancestor and its descendant without asking for a cycle", () => {
    const a = block("A", null, "list", BULLET)
    const b = block("B", "A", "list", BULLET)
    expect(converge([a, b], [{ ...b, parentId: null }, { ...a, parentId: "B" }], "swap")).toBe(2)
  })

  it("moves a child out before deleting its old parent", () => {
    const a = block("A", null, "toggle")
    const c = block("C", "A", "paragraph")
    expect(converge([a, c], [{ ...c, parentId: null }], "rescue")).toBe(2)
  })

  it("retypes a paragraph into a list before inserting its first child", () => {
    const p = block("P", null, "paragraph")
    expect(converge([p], [{ ...p, type: "list", properties: BULLET }, block("K", "P", "paragraph")], "retype")).toBe(2)
  })

  it("deletes only the topmost block of a removed subtree", () => {
    const a = block("A", null, "toggle")
    expect(nextOp([a, block("C", "A", "paragraph")], [])).toEqual({ kind: "delete", id: "A" })
  })

  it("writes nothing when the trees agree", () => {
    const tree = genTree(rng(3), 10)
    expect(nextOp(tree, tree)).toBeNull()
  })
})
