import { describe, expect, it } from "vitest"
import { createMutationQueue } from "../lib/mutation-queue"

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

  it("re-reads the hash after a rejection instead of wedging", async () => {
    const queue = createMutationQueue("hash-0", async () => "hash-fresh")
    const seen: string[] = []
    await expect(
      queue.enqueue(async () => {
        throw new Error("409")
      }),
    ).rejects.toThrow("409")
    await queue.enqueue(async (hash) => {
      seen.push(hash)
      return { result: null, content_hash: hash }
    })
    expect(seen).toEqual(["hash-fresh"])
  })
})
