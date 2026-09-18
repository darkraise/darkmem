import type { SyncBlock, SyncOp, SyncTree } from "../lib/sync-tree"

export type Props = Record<string, unknown> | null

interface Row {
  id: string
  parent: string | null
  type: string
  text: string
  props: Props
}

const DEFINED: Record<string, readonly string[]> = {
  paragraph: [],
  heading: ["level"],
  list: ["ordered", "marker", "number"],
  code: ["language"],
  quote: [],
  table: ["header", "alignments"],
  table_row: ["cells"],
  divider: [],
  html: [],
  todo: ["checked"],
  toggle: [],
  callout: ["variant"],
}

export const CONTAINERS: readonly string[] = ["list", "todo", "toggle"]

export class Refused extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

/** A port of `backend/app/services/block_verbs.py`'s page verbs, written
 *  from the Python rather than from the module under test, so a mistake in
 *  the client's mirror of those rules cannot hide behind the same mistake
 *  here. Rows sit in one flat list; a sibling run is the list order. */
export class FakeServer {
  rows: Row[]

  constructor(tree: SyncTree) {
    this.rows = tree.map((b) => ({ id: b.id, parent: b.parentId, type: b.type, text: b.text, props: b.properties }))
  }

  kids(parent: string | null): Row[] {
    return this.rows.filter((r) => r.parent === parent)
  }

  get(id: string): Row | undefined {
    return this.rows.find((r) => r.id === id)
  }

  subtree(id: string): Set<string> {
    const out = new Set([id])
    let grew = true
    while (grew) {
      grew = false
      for (const r of this.rows) {
        if (r.parent !== null && out.has(r.parent) && !out.has(r.id)) {
          out.add(r.id)
          grew = true
        }
      }
    }
    return out
  }

  private nest(parent: Row | undefined, childType: string) {
    if (!parent || CONTAINERS.includes(parent.type)) return
    if (parent.type === "table" && childType === "table_row") return
    throw new Refused(422, `a ${parent.type} block cannot hold a ${childType} block on a page`)
  }

  private validate(type: string, props: Props) {
    const p = props ?? {}
    if (type === "todo" && typeof p.checked !== "boolean") throw new Refused(422, "todo needs checked")
    if (type === "callout" && !["error", "info", "success", "warning"].includes(p.variant as string)) {
      throw new Refused(422, "callout needs variant")
    }
  }

  private place(row: Row, after: string | null) {
    const siblings = this.kids(row.parent)
    let at: number
    if (after === null) {
      const first = siblings[0]
      at = first ? this.rows.indexOf(first) : this.rows.length
    } else {
      const anchor = siblings.find((s) => s.id === after)
      if (!anchor) throw new Refused(404, `after_block_id ${after} is not a child of the target parent`)
      at = this.rows.indexOf(anchor) + 1
    }
    this.rows.splice(at, 0, row)
  }

  /** Applies `op` or throws `Refused` with the route's status, leaving the
   *  rows untouched on a refusal as the savepoint does. */
  apply(op: SyncOp) {
    const before = this.rows.map((r) => ({ ...r }))
    try {
      this.applyUnchecked(op)
    } catch (error) {
      this.rows = before
      throw error
    }
  }

  private applyUnchecked(op: SyncOp) {
    switch (op.kind) {
      case "insert":
        for (const item of op.blocks) {
          if (this.get(item.block_id)) throw new Refused(409, `block id ${item.block_id} already exists`)
          const parent = item.parent_id === null ? undefined : this.get(item.parent_id)
          if (item.parent_id !== null && !parent) throw new Refused(404, `no parent block ${item.parent_id}`)
          this.nest(parent, item.type)
          this.validate(item.type, item.properties)
          this.place(
            { id: item.block_id, parent: item.parent_id, type: item.type, text: item.text, props: item.properties },
            item.after_block_id,
          )
        }
        return
      case "move": {
        const row = this.get(op.id)
        if (!row) throw new Refused(404, `block ${op.id} is not in this page`)
        if (op.parentId !== null && this.subtree(op.id).has(op.parentId)) {
          throw new Refused(422, "a block cannot be moved inside its own subtree")
        }
        const parent = op.parentId === null ? undefined : this.get(op.parentId)
        if (op.parentId !== null && !parent) throw new Refused(404, `no parent block ${op.parentId}`)
        this.nest(parent, row.type)
        if (op.afterId !== null && !this.kids(op.parentId).some((s) => s.id === op.afterId && s.id !== op.id)) {
          throw new Refused(404, `after_block_id ${op.afterId} is not a child of the target parent`)
        }
        this.rows.splice(this.rows.indexOf(row), 1)
        this.place({ ...row, parent: op.parentId }, op.afterId)
        return
      }
      case "update": {
        const row = this.get(op.id)
        if (!row) throw new Refused(404, `block ${op.id} is not in this page`)
        let merged: Props = { ...(row.props ?? {}), ...(op.properties ?? {}) }
        if (Object.keys(merged).length === 0) merged = null
        if (merged !== null && row.type !== op.type) {
          const defined = DEFINED[op.type] ?? []
          const kept = Object.fromEntries(Object.entries(merged).filter(([k]) => defined.includes(k)))
          merged = Object.keys(kept).length ? kept : null
        }
        this.validate(op.type, merged)
        if (row.type !== op.type) {
          this.nest(row.parent === null ? undefined : this.get(row.parent), op.type)
          for (const child of this.kids(row.id)) this.nest({ ...row, type: op.type }, child.type)
        }
        Object.assign(row, { type: op.type, text: op.text, props: merged })
        return
      }
      case "delete": {
        if (!this.get(op.id)) throw new Refused(404, `block ${op.id} is not in this page`)
        const doomed = this.subtree(op.id)
        this.rows = this.rows.filter((r) => !doomed.has(r.id))
      }
    }
  }

  /** The rows in pre-order, the order a page read serves them in. */
  tree(): SyncBlock[] {
    const out: SyncBlock[] = []
    const walk = (parent: string | null) => {
      for (const r of this.kids(parent)) {
        out.push({ id: r.id, parentId: r.parent, type: r.type, text: r.text, properties: r.props })
        walk(r.id)
      }
    }
    walk(null)
    return out
  }
}
