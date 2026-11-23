import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { createMutationQueue, QueuedWriteDiscarded } from "../lib/mutation-queue"

const noReread = async () => "unused"

describe("the mutation queue", () => {
  it("feeds each mutation the hash the previous one returned", async () => {
    const queue = createMutationQueue("hash-0", noReread)
    const seen: string[] = []
    const run = (next: string) =>
      queue.enqueue(async (hash) => {
        seen.push(hash)
        return { result: null, content_hash: next }
      })

    // Fired synchronously, exactly as the editor fires a commit and an insert.
    await Promise.all([run("hash-1"), run("hash-2")])

    expect(seen).toEqual(["hash-0", "hash-1"])
  })

  it("runs one mutation at a time", async () => {
    const queue = createMutationQueue("hash-0", noReread)
    let live = 0
    let peak = 0
    const run = () =>
      queue.enqueue(async (hash) => {
        live += 1
        peak = Math.max(peak, live)
        await new Promise((r) => setTimeout(r, 5))
        live -= 1
        return { result: null, content_hash: hash }
      })

    await Promise.all([run(), run(), run()])

    expect(peak).toBe(1)
  })

  it("re-reads the hash after a mutation that returns none", async () => {
    // DELETE answers 204 with no body, so it yields no hash.
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const seen: string[] = []
    await queue.enqueue(async () => ({ result: null, content_hash: null }))
    await queue.enqueue(async (hash) => {
      seen.push(hash)
      return { result: null, content_hash: hash }
    })
    expect(seen).toEqual(["hash-fresh"])
  })

  it("no queued write follows a refusal", async () => {
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const sent: string[] = []
    const refused = queue.enqueue(async () => {
      sent.push("first")
      throw Object.assign(new Error("stale"), { status: 409, code: "hash_conflict" })
    })
    const second = queue.enqueue(async (hash) => {
      sent.push("second")
      return { result: null, content_hash: hash }
    })
    const third = queue.enqueue(async (hash) => {
      sent.push("third")
      return { result: null, content_hash: hash }
    })
    void second
    void third
    await expect(refused).rejects.toThrow("stale")
    await new Promise((r) => setTimeout(r, 20))
    expect(sent).toEqual(["first"])
    expect(queue.paused).toBe(true)
  })

  it("discardAll drops the refused write and every write queued behind it", async () => {
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const sent: string[] = []
    const write = (name: string) =>
      queue.enqueue(async (hash) => {
        sent.push(`${name}@${hash}`)
        if (name === "first") {
          throw Object.assign(new Error("stale"), { status: 409, code: "hash_conflict" })
        }
        return { result: name, content_hash: hash }
      })
    const refused = write("first")
    const queued = [write("second"), write("third")]
    await expect(refused).rejects.toThrow("stale")

    queue.discardAll()

    for (const promise of queued) {
      await expect(promise).rejects.toBeInstanceOf(QueuedWriteDiscarded)
    }
    expect(queue.paused).toBe(false)
    await expect(write("later")).resolves.toBe("later")
    expect(sent).toEqual(["first@hash-0", "later@hash-fresh"])
  })

  it("the queue resumes when the operator acts", async () => {
    const refusal = () =>
      Object.assign(new Error("stale"), { status: 409, code: "hash_conflict" })

    for (const action of ["retry", "discard"] as const) {
      let reads = 0
      const queue = createMutationQueue("hash-0", async () => `read-${++reads}`)
      const seen: string[] = []
      let refuse = true
      const write = (name: string, answer: string) =>
        queue.enqueue(async (hash) => {
          seen.push(`${name}@${hash}`)
          if (name === "first" && refuse) {
            refuse = false
            throw refusal()
          }
          return { result: name, content_hash: answer }
        })
      const first = write("first", "hash-1")
      const second = write("second", "hash-2")
      const third = write("third", "hash-3")
      await expect(first).rejects.toThrow("stale")

      if (action === "retry") {
        await expect(queue.retry()).resolves.toBe("first")
      } else {
        queue.discard()
      }
      await expect(second).resolves.toBe("second")
      await expect(third).resolves.toBe("third")
      expect(queue.paused).toBe(false)
      expect(seen).toEqual(
        action === "retry"
          ? ["first@hash-0", "first@read-1", "second@hash-1", "third@hash-2"]
          : ["first@hash-0", "second@read-1", "third@hash-2"],
      )
    }
  })

  it("a retry may carry the operator's edited write", async () => {
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    await expect(
      queue.enqueue(async () => {
        throw Object.assign(new Error("stale"), { status: 409, code: "hash_conflict" })
      }),
    ).rejects.toThrow("stale")
    const seen: string[] = []
    await queue.retry(async (hash) => {
      seen.push(`edited@${hash}`)
      return { result: null, content_hash: "hash-1" }
    })
    expect(seen).toEqual(["edited@hash-fresh"])
  })

  it("a failed retry keeps the queue paused", async () => {
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const failing = async () => {
      throw new Error("offline")
    }
    await expect(queue.enqueue(failing)).rejects.toThrow("offline")
    const sent: string[] = []
    const next = queue.enqueue(async (hash) => {
      sent.push(hash)
      return { result: null, content_hash: hash }
    })
    await expect(queue.retry()).rejects.toThrow("offline")
    expect(queue.paused).toBe(true)
    expect(sent).toEqual([])
    queue.discard()
    await next
    expect(sent).toEqual(["hash-fresh"])
  })

  it("a write that failed without a refusal is retried under its own hash", async () => {
    // It may have landed unseen; the old hash makes the server refuse a
    // second copy instead of applying it twice.
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const seen: string[] = []
    let fail = true
    const write = async (hash: string) => {
      seen.push(hash)
      if (fail) {
        fail = false
        throw new Error("network")
      }
      return { result: null, content_hash: "hash-1" }
    }
    await expect(queue.enqueue(write)).rejects.toThrow("network")
    await queue.retry()
    expect(seen).toEqual(["hash-0", "hash-0"])
  })
})

describe("one hash-precondition helper", () => {
  it("both editors use one hash-precondition helper", () => {
    const read = (file: string) =>
      readFileSync(path.resolve(__dirname, "../../..", file), "utf8")
    const local = /(function|const)\s+(nextExpectedHash|isHashConflict|expectedHashParam|precondition)\b/
    const users: Record<string, string[]> = {
      "features/documents/lib/mutation-queue.ts": ["nextExpectedHash", "isHashConflict"],
      "features/notes/lib/page-sync.ts": ["isHashConflict"],
      "features/notes/lib/page-transport.ts": ["nextExpectedHash", "expectedHashParam"],
      "hooks/api/use-blocks-api.ts": ["expectedHashParam"],
    }
    for (const [file, names] of Object.entries(users)) {
      const source = read(file)
      const imported = /import \{([^}]*)\} from "@\/lib\/hash-precondition"/.exec(source)
      expect(imported, file).not.toBeNull()
      for (const name of names) expect(imported![1], `${file} ${name}`).toContain(name)
      expect(local.test(source), file).toBe(false)
      expect(source, file).not.toMatch(/status === 409/)
    }
  })
})
