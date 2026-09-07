type Mutation<T> = (
  hash: string,
) => Promise<{ result: T; content_hash: string | null }>

/** Serialises a document's block mutations and carries the hash between them.
 *
 *  The editor fires a commit and an insert synchronously; run concurrently
 *  they both carry the hash read before either started, and the second is
 *  refused against the first's write. Chaining them makes each mutation see
 *  the hash its predecessor produced.
 */
export function createMutationQueue(
  initialHash: string | null,
  reread: () => Promise<string>,
) {
  let hash = initialHash
  let tail: Promise<unknown> = Promise.resolve()

  function enqueue<T>(fn: Mutation<T>): Promise<T> {
    const run = tail.then(async () => {
      // Null after a delete (204, no body) or after a rejection dropped it.
      if (hash === null) hash = await reread()
      try {
        const { result, content_hash } = await fn(hash)
        hash = content_hash
        return result
      } catch (error) {
        // Drop the hash rather than keep a stale one: a refusal means the
        // document moved, and every later mutation would carry the losing
        // hash forever.
        hash = null
        throw error
      }
    })
    // Keep the chain alive after a rejection, or one failure wedges the rest.
    tail = run.catch(() => undefined)
    return run as Promise<T>
  }

  return { enqueue }
}
