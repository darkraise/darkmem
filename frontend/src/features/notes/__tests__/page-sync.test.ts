import { describe, expect, it } from "vitest"
import { FakeServer } from "./fake-page-server"
import { PageSync, SyncTransportError, type PageTransport, type SyncStatus } from "../lib/page-sync"
import type { SyncBlock, SyncOp } from "../lib/sync-tree"

const para = (id: string, text = id): SyncBlock => ({ id, parentId: null, type: "paragraph", text, properties: null })

/** The fake server behind a transport, with a content hash that moves on
 *  every accepted write and failures injected per call. */
function harness(start: SyncBlock[]) {
  const server = new FakeServer(start)
  let version = 0
  const hash = () => `h${version}`
  const sent: { op: SyncOp; expected: string }[] = []
  const faults: ((op: SyncOp) => "drop-response" | "drop-request" | number | null)[] = []
  const transport: PageTransport = {
    async read() {
      return { tree: server.tree(), hash: hash() }
    },
    async send(op, expected) {
      sent.push({ op, expected })
      const fault = faults.shift()?.(op) ?? null
      if (fault === "drop-request") throw new SyncTransportError("network")
      if (typeof fault === "number") throw new SyncTransportError(`status ${fault}`, fault)
      if (expected !== hash()) throw new SyncTransportError("stale hash", 409)
      server.apply(op)
      version++
      if (fault === "drop-response") throw new SyncTransportError("network")
      return hash()
    },
  }
  const sleeps: number[] = []
  const sync = new PageSync(start, "h0", transport, async (ms) => {
    sleeps.push(ms)
  })
  const statuses: SyncStatus["kind"][] = []
  sync.subscribe((s) => statuses.push(s.kind))
  return { server, sync, sent, faults, sleeps, statuses, bump: () => version++ }
}

describe("PageSync", () => {
  it("drains to the server, chaining each write on the hash the last one answered", async () => {
    const h = harness([para("a")])
    h.sync.setDesired([para("a", "edited"), para("b")])
    await h.sync.flush()
    expect(h.server.tree()).toEqual([para("a", "edited"), para("b")])
    expect(h.sent.map((s) => s.expected)).toEqual(["h0", "h1"])
    expect(h.sync.status).toEqual({ kind: "saved" })
    expect(h.sync.pending).toBe(false)
  })

  it("treats a lost response whose write landed as done, without resending", async () => {
    const h = harness([para("a")])
    h.faults.push(() => "drop-response")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sent).toHaveLength(1)
    expect(h.sleeps).toEqual([])
    expect(h.server.tree()).toEqual([para("a", "x")])
  })

  it("resends a write that never arrived, backing off 1s, 2s, 4s", async () => {
    const h = harness([para("a")])
    h.faults.push(() => "drop-request", () => 503, () => "drop-request")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sleeps).toEqual([1000, 2000, 4000])
    expect(h.statuses).toContain("retrying")
    expect(h.server.tree()).toEqual([para("a", "x")])
  })

  it("caps the backoff at 30s", async () => {
    const h = harness([para("a")])
    for (let i = 0; i < 8; i++) h.faults.push(() => "drop-request")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sleeps).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000])
  })

  it("stops on a change made elsewhere", async () => {
    const h = harness([para("a")])
    h.faults.push(() => {
      h.server.apply({ kind: "update", id: "a", type: "paragraph", text: "theirs", properties: null })
      h.bump()
      return null
    })
    h.sync.setDesired([para("a", "mine")])
    await h.sync.flush()
    expect(h.sync.status).toMatchObject({ kind: "stopped", reason: "conflict" })
    expect(h.server.tree()).toEqual([para("a", "theirs")])
  })

  it("stops after a second 409 with nothing changed behind it", async () => {
    const h = harness([para("a")])
    h.faults.push(() => 409, () => 409)
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sync.status).toMatchObject({ kind: "stopped", reason: "conflict" })
    expect(h.sent).toHaveLength(2)
  })

  it("stops on 404 and on 422, keeping the server's message for a refusal", async () => {
    const gone = harness([para("a")])
    gone.faults.push(() => 404)
    gone.sync.setDesired([para("a", "x")])
    await gone.sync.flush()
    expect(gone.sync.status).toMatchObject({ kind: "stopped", reason: "gone" })

    const refused = harness([para("a")])
    refused.faults.push(() => 422)
    refused.sync.setDesired([para("a", "x")])
    await refused.sync.flush()
    expect(refused.sync.status).toEqual({ kind: "stopped", reason: "refused", message: "status 422" })
    expect(refused.sync.pending).toBe(true)
    expect(refused.sync.desired).toEqual([para("a", "x")])
  })

  it("joins a flush already running and sends an edit made mid-write", async () => {
    const h = harness([para("a")])
    h.faults.push(() => {
      h.sync.setDesired([para("a", "one"), para("b")])
      return null
    })
    h.sync.setDesired([para("a", "one")])
    const first = h.sync.flush()
    const second = h.sync.flush()
    expect(second).toBe(first)
    await first
    expect(h.server.tree()).toEqual([para("a", "one"), para("b")])
  })

  it("tells settled listeners once the drain is over and nothing is pending", async () => {
    const h = harness([para("a")])
    const seen: boolean[] = []
    h.sync.onSettled(() => seen.push(h.sync.pending))
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(seen).toEqual([false])
  })

  it("writes nothing once stopped", async () => {
    const h = harness([para("a")])
    h.faults.push(() => 422)
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    h.sync.setDesired([para("a", "y")])
    await h.sync.flush()
    expect(h.sent).toHaveLength(1)
  })
})
