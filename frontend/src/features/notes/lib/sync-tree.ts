import {
  canHold,
  invalidProperties,
  mergeProperties,
  propertiesEqual,
  type Properties,
} from "./block-properties"

/** One block in the form both sync trees use. A tree is an array in
 *  pre-order: a block's children follow it, in sibling order. */
export interface SyncBlock {
  id: string
  parentId: string | null
  type: string
  text: string
  properties: Properties
}

export type SyncTree = readonly SyncBlock[]

export interface NewBlock {
  block_id: string
  type: string
  text: string
  properties: Properties
  parent_id: string | null
  after_block_id: string | null
}

export type SyncOp =
  | { kind: "insert"; blocks: NewBlock[] }
  | { kind: "move"; id: string; parentId: string | null; afterId: string | null }
  | { kind: "update"; id: string; type: string; text: string; properties: Properties }
  | { kind: "delete"; id: string }

/** Why a tree cannot take an op, in the server's words; null when it can. */
export type Refusal = { status: 404 | 409 | 422; message: string }

function childrenOf(tree: SyncTree): Map<string | null, SyncBlock[]> {
  const map = new Map<string | null, SyncBlock[]>()
  for (const block of tree) {
    const list = map.get(block.parentId)
    if (list) list.push(block)
    else map.set(block.parentId, [block])
  }
  return map
}

function preOrder(byParent: Map<string | null, SyncBlock[]>): SyncBlock[] {
  const out: SyncBlock[] = []
  const walk = (parent: string | null) => {
    for (const child of byParent.get(parent) ?? []) {
      out.push(child)
      walk(child.id)
    }
  }
  walk(null)
  return out
}

function subtreeIds(tree: SyncTree, root: string): Set<string> {
  const byParent = childrenOf(tree)
  const out = new Set<string>()
  const stack = [root]
  while (stack.length) {
    const id = stack.pop()!
    out.add(id)
    for (const child of byParent.get(id) ?? []) stack.push(child.id)
  }
  return out
}

function placeIn(
  byParent: Map<string | null, SyncBlock[]>,
  block: SyncBlock,
  afterId: string | null,
) {
  const siblings = byParent.get(block.parentId) ?? []
  const index = afterId === null ? 0 : siblings.findIndex((b) => b.id === afterId) + 1
  siblings.splice(index, 0, block)
  byParent.set(block.parentId, siblings)
}

/** The refusal the server would answer `op` with against `tree`, mirroring
 *  `block_verbs.py`'s checks and their route statuses; null when it would
 *  accept it. */
export function refusalOf(tree: SyncTree, op: SyncOp, placedType?: string): Refusal | null {
  const byId = new Map(tree.map((b) => [b.id, b]))
  const byParent = childrenOf(tree)
  const placement = (
    parentId: string | null,
    afterId: string | null,
    type: string,
    self: string | null,
  ): Refusal | null => {
    const parent = parentId === null ? null : byId.get(parentId)
    if (parentId !== null && !parent) return { status: 404, message: `no parent block ${parentId}` }
    if (afterId !== null && !(byParent.get(parentId) ?? []).some((b) => b.id === afterId && b.id !== self)) {
      return { status: 404, message: `after_block_id ${afterId} is not a child of the target parent` }
    }
    if (!canHold(parent?.type ?? null, type)) {
      return { status: 422, message: `a ${parent!.type} block cannot hold a ${type} block on a page` }
    }
    return null
  }
  switch (op.kind) {
    case "insert": {
      if (op.blocks.length === 0) return { status: 422, message: "a batch insert needs at least one block" }
      const ids = new Set<string>()
      for (const item of op.blocks) {
        if (ids.has(item.block_id)) {
          return { status: 422, message: `block id ${item.block_id} appears more than once in this batch` }
        }
        ids.add(item.block_id)
      }
      let current: SyncTree = tree
      for (const item of op.blocks) {
        if (current.some((b) => b.id === item.block_id)) {
          return { status: 409, message: `block id ${item.block_id} already exists` }
        }
        const refused =
          refusalOf(current, { kind: "move", id: "", parentId: item.parent_id, afterId: item.after_block_id }, item.type) ??
          invalidOf(item.type, item.properties)
        if (refused) return refused
        current = applyOp(current, { kind: "insert", blocks: [item] })
      }
      return null
    }
    case "move": {
      // An insert is checked as the placement of a block not yet in the tree.
      if (placedType !== undefined) return placement(op.parentId, op.afterId, placedType, null)
      const block = byId.get(op.id)
      if (!block) return { status: 404, message: `block ${op.id} is not in this page` }
      if (op.parentId !== null && subtreeIds(tree, op.id).has(op.parentId)) {
        return { status: 422, message: "a block cannot be moved inside its own subtree" }
      }
      return placement(op.parentId, op.afterId, block.type, op.id)
    }
    case "update": {
      const block = byId.get(op.id)
      if (!block) return { status: 404, message: `block ${op.id} is not in this page` }
      const merged = mergeProperties(block.properties, op.properties, block.type, op.type)
      const invalid = invalidOf(op.type, merged)
      if (invalid) return invalid
      if (op.type !== block.type) {
        const parent = block.parentId === null ? null : byId.get(block.parentId)!
        if (!canHold(parent?.type ?? null, op.type)) {
          return { status: 422, message: `a ${parent!.type} block cannot hold a ${op.type} block on a page` }
        }
        const child = (byParent.get(op.id) ?? []).find((c) => !canHold(op.type, c.type))
        if (child) return { status: 422, message: `a ${op.type} block cannot hold a ${child.type} block on a page` }
      }
      return null
    }
    case "delete":
      return byId.has(op.id) ? null : { status: 404, message: `block ${op.id} is not in this page` }
  }

}

function invalidOf(type: string, props: Properties): Refusal | null {
  const message = invalidProperties(type, props)
  return message === null ? null : { status: 422, message }
}

/** `tree` after the server accepted `op`, by the server's own rules. */
export function applyOp(tree: SyncTree, op: SyncOp): SyncBlock[] {
  const byParent = childrenOf(tree.map((b) => ({ ...b })))
  switch (op.kind) {
    case "insert":
      for (const item of op.blocks) {
        placeIn(
          byParent,
          { id: item.block_id, parentId: item.parent_id, type: item.type, text: item.text, properties: item.properties },
          item.after_block_id,
        )
      }
      break
    case "move": {
      const all = [...byParent.values()].flat()
      const block = all.find((b) => b.id === op.id)!
      const from = byParent.get(block.parentId)!
      from.splice(from.indexOf(block), 1)
      placeIn(byParent, { ...block, parentId: op.parentId }, op.afterId)
      break
    }
    case "update":
      for (const siblings of byParent.values()) {
        const i = siblings.findIndex((b) => b.id === op.id)
        const block = siblings[i]
        if (!block) continue
        siblings[i] = {
          ...block,
          type: op.type,
          text: op.text,
          properties: mergeProperties(block.properties, op.properties, block.type, op.type),
        }
      }
      break
    case "delete": {
      const doomed = subtreeIds(tree, op.id)
      for (const [parent, siblings] of byParent) {
        byParent.set(parent, siblings.filter((b) => !doomed.has(b.id)))
      }
      break
    }
  }
  return preOrder(byParent)
}

export function treesEqual(a: SyncTree, b: SyncTree): boolean {
  if (a.length !== b.length) return false
  return a.every((x, i) => {
    const y = b[i]!
    return (
      x.id === y.id &&
      x.parentId === y.parentId &&
      x.type === y.type &&
      x.text === y.text &&
      propertiesEqual(x.properties, y.properties)
    )
  })
}

/** Indices of a longest strictly increasing subsequence of `values`. */
function lisIndices(values: readonly number[]): Set<number> {
  const at = (i: number) => values[i]!
  const tails: number[] = []
  const prev: number[] = new Array<number>(values.length).fill(-1)
  for (let i = 0; i < values.length; i++) {
    let lo = 0
    let hi = tails.length
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (at(tails[mid]!) < at(i)) lo = mid + 1
      else hi = mid
    }
    if (lo > 0) prev[i] = tails[lo - 1]!
    tails[lo] = i
  }
  const out = new Set<number>()
  let k = tails.length ? tails[tails.length - 1]! : -1
  while (k !== -1) {
    out.add(k)
    k = prev[k]!
  }
  return out
}

/** Every op that would move `snapshot` toward `desired`, in the order they
 *  are preferred: new blocks first (as one batch), then moves in the desired
 *  tree's pre-order, then updates, then deletes of the topmost removed
 *  blocks. */
function candidates(snapshot: SyncTree, desired: SyncTree): SyncOp[] {
  const snapById = new Map(snapshot.map((b) => [b.id, b]))
  const desiredIds = new Set(desired.map((b) => b.id))
  const desiredByParent = childrenOf(desired)
  const snapByParent = childrenOf(snapshot)
  const out: SyncOp[] = []

  const fresh = desired.filter((b) => !snapById.has(b.id))
  const freshIds = new Set(fresh.map((b) => b.id))
  /** The nearest earlier desired sibling the server will already hold under
   *  the same parent when this block is placed: a sibling already there, or
   *  one earlier in the same batch. */
  const anchorFor = (block: SyncBlock, batch: boolean): string | null => {
    const siblings = desiredByParent.get(block.parentId) ?? []
    for (let i = siblings.findIndex((b) => b.id === block.id) - 1; i >= 0; i--) {
      const s = siblings[i]!
      if (batch && freshIds.has(s.id)) return s.id
      if (snapById.get(s.id)?.parentId === block.parentId) return s.id
    }
    return null
  }
  if (fresh.length) {
    out.push({
      kind: "insert",
      blocks: fresh.map((b) => ({
        block_id: b.id,
        type: b.type,
        text: b.text,
        properties: b.properties,
        parent_id: b.parentId,
        after_block_id: anchorFor(b, true),
      })),
    })
  }

  const moves: SyncOp[] = []
  const inPlace = new Set<string>()
  for (const [parent, desiredKids] of desiredByParent) {
    const snapKids = snapByParent.get(parent) ?? []
    const kept = desiredKids.filter((b) => snapById.get(b.id)?.parentId === parent)
    const positions = kept.map((b) => snapKids.findIndex((s) => s.id === b.id))
    const lis = lisIndices(positions)
    kept.forEach((b, i) => {
      if (lis.has(i)) inPlace.add(b.id)
    })
  }
  for (const block of desired) {
    if (!snapById.has(block.id) || inPlace.has(block.id)) continue
    moves.push({ kind: "move", id: block.id, parentId: block.parentId, afterId: anchorFor(block, false) })
  }
  out.push(...moves)

  for (const block of desired) {
    const stored = snapById.get(block.id)
    if (!stored) continue
    if (stored.type !== block.type || stored.text !== block.text || !propertiesEqual(stored.properties, block.properties)) {
      out.push({ kind: "update", id: block.id, type: block.type, text: block.text, properties: block.properties })
    }
  }

  for (const block of snapshot) {
    if (desiredIds.has(block.id)) continue
    const parentGoing = block.parentId !== null && !desiredIds.has(block.parentId)
    if (!parentGoing) out.push({ kind: "delete", id: block.id })
  }
  return out
}

/** The next write that moves the server toward `desired`: the first
 *  preferred op the server would accept, with a batch cut to its longest
 *  acceptable prefix. `null` when the trees already agree. Throws when they
 *  differ and no op is acceptable, which only a desired tree breaking the
 *  server's rules can cause. */
export function nextOp(snapshot: SyncTree, desired: SyncTree): SyncOp | null {
  const ops = candidates(snapshot, desired)
  if (ops.length === 0) return null
  for (const op of ops) {
    if (op.kind === "insert") {
      let n = op.blocks.length
      while (n > 0 && refusalOf(snapshot, { kind: "insert", blocks: op.blocks.slice(0, n) }) !== null) n--
      if (n > 0) return { kind: "insert", blocks: op.blocks.slice(0, n) }
      continue
    }
    // A delete whose subtree still holds a block the desired tree keeps would
    // take that block with it; it waits for the block to move out.
    if (op.kind === "delete") {
      const doomed = subtreeIds(snapshot, op.id)
      if (desired.some((b) => doomed.has(b.id))) continue
    }
    if (refusalOf(snapshot, op) === null) return op
  }
  throw new Error("no write the server would accept moves this page toward the editor")
}
