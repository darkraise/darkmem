/** The content-hash precondition both block editors carry on their writes:
 *  each write names the hash it was made against, and the server refuses it
 *  with 409 when the document or page has moved since. */

/** The `expected_hash` a write sends. An empty hash means none is known (the
 *  demo's re-read answers ""), and the write goes unpreconditioned. */
export function expectedHashParam(hash: string): string | undefined {
  return hash === "" ? undefined : hash
}

/** The hash the next write is made against: the one this write answered, or
 *  null when it answered none (a 204 delete) and the caller must re-read. */
export function nextExpectedHash(
  answer: { content_hash?: string | null } | null | undefined | void,
): string | null {
  const hash = answer?.content_hash
  return typeof hash === "string" && hash !== "" ? hash : null
}

/** A write refused because its hash was stale. An error carrying no code
 *  (the notes transport keeps only the status) counts by its 409 alone. */
export function isHashConflict(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false
  const { status, code } = error as { status?: unknown; code?: unknown }
  return status === 409 && (code === undefined || code === "hash_conflict")
}
