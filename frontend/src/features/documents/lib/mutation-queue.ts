import { isHashConflict, nextExpectedHash } from "@/lib/hash-precondition"

type Mutation<T> = (
  hash: string,
) => Promise<{ result: T; content_hash: string | null }>

/** Serialises a document's block mutations and carries the hash between them.
 *
 *  The editor fires a commit and an insert synchronously; run concurrently
 *  they both carry the hash read before either started, and the second is
 *  refused against the first's write. Chaining them makes each mutation see
 *  the hash its predecessor produced.
 *
 *  A failed mutation pauses the queue: the writes behind it were made against
 *  the view the failure just proved wrong, so none is sent until the operator
 *  retries the failed one or discards it.
 */
export function createMutationQueue(
  initialHash: string | null,
  reread: () => Promise<string>,
) {
  let hash = initialHash
  let tail: Promise<unknown> = Promise.resolve()
  let held: { fn: Mutation<unknown>; resume: () => void } | null = null
  let retrying: Promise<unknown> | null = null

  async function attempt<T>(fn: Mutation<T>): Promise<T> {
    // Null after a delete (204, no body), a hash conflict or a discard.
    if (hash === null) hash = await reread()
    try {
      const answer = await fn(hash)
      hash = nextExpectedHash(answer)
      return answer.result
    } catch (error) {
      // Only a conflict says the document moved. Any other failure may have
      // landed unseen, and retrying under the old hash makes the server
      // refuse a second copy instead of applying it twice.
      if (isHashConflict(error)) hash = null
      throw error
    }
  }

  function enqueue<T>(fn: Mutation<T>): Promise<T> {
    const run = tail.then(() => attempt(fn))
    tail = run.then(
      () => undefined,
      () =>
        new Promise<void>((resume) => {
          held = { fn: fn as Mutation<unknown>, resume }
        }),
    )
    return run
  }

  /** Resends the failed mutation, or `replacement` in its place (the
   *  operator's edit of it), and releases the queue once it lands. */
  function retry<T>(replacement?: Mutation<T>): Promise<T> {
    if (retrying) return retrying as Promise<T>
    const current = held
    if (!current) return Promise.reject(new Error("nothing to retry"))
    if (replacement) current.fn = replacement as Mutation<unknown>
    const run = attempt(current.fn as Mutation<T>).then((result) => {
      held = null
      current.resume()
      return result
    })
    retrying = run
    const clear = () => {
      retrying = null
    }
    run.then(clear, clear)
    return run
  }

  /** Drops the failed mutation and releases the queue. The next write
   *  re-reads the hash, since the dropped one may have landed. */
  function discard() {
    const current = held
    if (!current || retrying) return
    held = null
    hash = null
    current.resume()
  }

  return {
    enqueue,
    retry,
    discard,
    get paused() {
      return held !== null
    },
  }
}
