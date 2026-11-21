import { isHashConflict } from "@/lib/hash-precondition"
import { applyOp, nextOp, treesEqual, type SyncOp, type SyncTree } from "./sync-tree"

/** A failed write or read. `status` is the HTTP status, absent for a network
 *  failure. */
export class SyncTransportError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message)
    this.name = "SyncTransportError"
  }
}

export interface PageTransport {
  /** The page as the server holds it now, canonicalised by the caller. */
  read(): Promise<{ tree: SyncTree; hash: string }>
  /** Sends one write preconditioned on `expectedHash`; resolves to the
   *  page's new content hash. */
  send(op: SyncOp, expectedHash: string): Promise<string>
}

export type SyncStatus =
  | { kind: "idle" }
  | { kind: "saved" }
  | { kind: "saving" }
  | { kind: "retrying" }
  | { kind: "stopped"; reason: "conflict" | "gone" | "refused"; message: string }

const BACKOFF_START_MS = 1000
const BACKOFF_CAP_MS = 30_000
const CONFLICT_MESSAGE = "This page was changed somewhere else."
const GONE_MESSAGE = "This page is no longer available."

function isRetryable(error: unknown): error is SyncTransportError {
  return (
    error instanceof SyncTransportError &&
    (error.status === undefined || error.status >= 500 || isHashConflict(error))
  )
}

/** One page's save queue. It holds the last tree the server acknowledged
 *  and the tree the editor asks for, and drains the difference one write at
 *  a time. Pure of React and of the editor: the caller feeds it trees. */
export class PageSync {
  private snapshotTree: SyncTree
  private desiredTree: SyncTree
  private hash: string
  private running: Promise<void> | null = null
  private current: SyncStatus = { kind: "idle" }
  private readonly listeners = new Set<(status: SyncStatus) => void>()
  private readonly settledListeners = new Set<() => void>()

  constructor(
    snapshot: SyncTree,
    hash: string,
    private readonly transport: PageTransport,
    private readonly sleep: (ms: number) => Promise<void> = (ms) =>
      new Promise((resolve) => setTimeout(resolve, ms)),
  ) {
    this.snapshotTree = snapshot
    this.desiredTree = snapshot
    this.hash = hash
  }

  get snapshot(): SyncTree {
    return this.snapshotTree
  }

  get desired(): SyncTree {
    return this.desiredTree
  }

  get status(): SyncStatus {
    return this.current
  }

  get stopped(): boolean {
    return this.current.kind === "stopped"
  }

  /** Work not yet on the server: a write in flight, or a difference left. */
  get pending(): boolean {
    if (this.running !== null) return true
    try {
      return nextOp(this.snapshotTree, this.desiredTree) !== null
    } catch {
      return true
    }
  }

  subscribe(listener: (status: SyncStatus) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** Called each time a drain has finished and `pending` reads its final
   *  value — which a status listener cannot rely on, since statuses are
   *  emitted from inside the drain. */
  onSettled(listener: () => void): () => void {
    this.settledListeners.add(listener)
    return () => this.settledListeners.delete(listener)
  }

  setDesired(tree: SyncTree) {
    this.desiredTree = tree
  }

  /** Drains until the server holds the desired tree or the queue stops. A
   *  call while a drain runs joins it; the drain re-reads the desired tree
   *  before every write, so a later edit is never left behind. */
  flush(): Promise<void> {
    if (this.stopped) return Promise.resolve()
    this.running ??= this.drain().finally(() => {
      this.running = null
      for (const listener of this.settledListeners) listener()
    })
    return this.running
  }

  private emit(status: SyncStatus) {
    this.current = status
    for (const listener of this.listeners) listener(status)
  }

  private stop(reason: "conflict" | "gone" | "refused", message: string) {
    this.emit({ kind: "stopped", reason, message })
  }

  private async drain() {
    let backoff = BACKOFF_START_MS
    let unexplained409 = 0
    for (;;) {
      let op: SyncOp | null
      try {
        op = nextOp(this.snapshotTree, this.desiredTree)
      } catch (error) {
        this.stop("refused", (error as Error).message)
        return
      }
      if (op === null) {
        this.emit({ kind: "saved" })
        return
      }
      if (this.current.kind !== "retrying") this.emit({ kind: "saving" })
      try {
        this.hash = await this.transport.send(op, this.hash)
        this.snapshotTree = applyOp(this.snapshotTree, op)
        backoff = BACKOFF_START_MS
        unexplained409 = 0
        this.emit({ kind: "saving" })
        continue
      } catch (error) {
        if (error instanceof SyncTransportError && error.status === 404) {
          this.stop("gone", GONE_MESSAGE)
          return
        }
        if (!isRetryable(error)) {
          this.stop("refused", (error as Error).message)
          return
        }
        const outcome = await this.landed(op)
        if (outcome === "landed") {
          backoff = BACKOFF_START_MS
          unexplained409 = 0
          continue
        }
        if (outcome === "stopped") return
        // Not landed and nothing else changed. A 409 with no change behind it
        // has no benign cause (the hash covers only the content), so a second
        // one in a row stops rather than looping.
        if (outcome === "unchanged" && isHashConflict(error) && ++unexplained409 >= 2) {
          this.stop("conflict", CONFLICT_MESSAGE)
          return
        }
        this.emit({ kind: "retrying" })
        await this.sleep(backoff)
        backoff = Math.min(backoff * 2, BACKOFF_CAP_MS)
      }
    }
  }

  /** Whether `op` reached the server, judged by one comparison of the
   *  re-read tree: the snapshot with the op applied, the snapshot unchanged,
   *  or anything else (someone else wrote). */
  private async landed(op: SyncOp): Promise<"landed" | "unchanged" | "unreadable" | "stopped"> {
    let read: { tree: SyncTree; hash: string }
    try {
      read = await this.transport.read()
    } catch (error) {
      if (error instanceof SyncTransportError && error.status === 404) {
        this.stop("gone", GONE_MESSAGE)
        return "stopped"
      }
      return "unreadable"
    }
    const applied = applyOp(this.snapshotTree, op)
    if (treesEqual(read.tree, applied)) {
      this.snapshotTree = applied
      this.hash = read.hash
      return "landed"
    }
    if (treesEqual(read.tree, this.snapshotTree)) {
      this.hash = read.hash
      return "unchanged"
    }
    this.stop("conflict", CONFLICT_MESSAGE)
    return "stopped"
  }
}
