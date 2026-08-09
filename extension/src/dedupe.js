/**
 * Capture dedup by content fingerprint (T3.15, doc 15 §4).
 *
 * The failure this exists to prevent is mundane and constant: a human selects
 * the same passage twice, or re-captures after a page reload, and darkmem
 * stores two memories asserting one thing. That is not merely untidy — facts
 * count `COUNT(DISTINCT origin_key)` and this install is **one** origin, so a
 * duplicate cannot manufacture corroboration; what it does instead is inflate
 * the corpus and hand retrieval two rows where the vault holds one claim.
 *
 * **Fingerprint, not text.** The seen-set stores hashes, never content: it
 * lives in `chrome.storage.local` unencrypted, and a local cache of everything
 * a human ever clipped is a liability the feature does not need to create.
 *
 * **Scoped to the install's own key.** The set is per `origin_key`, so two
 * profiles on one machine do not suppress each other's captures — and, more
 * importantly, so clearing an install's identity clears its dedup history with
 * it rather than leaving a set that silently refuses new captures.
 *
 * **Bounded, and it forgets the oldest first.** An unbounded set grows for the
 * life of the install; a bounded one that dropped a *random* entry would make
 * duplicate suppression non-deterministic. Oldest-first keeps the recent
 * window — which is where accidental re-capture actually happens.
 */

export const SEEN_STORAGE_PREFIX = "darkmem.seen.";
export const SEEN_LIMIT = 500;

/**
 * A stable fingerprint of what will be stored.
 *
 * Normalised before hashing — trimmed, inner whitespace collapsed — because
 * re-selecting a passage rarely reproduces the same leading spaces or line
 * wrapping, and a fingerprint that changed with the selection's edges would
 * suppress nothing. Deliberately NOT lowercased: case is content here, and two
 * passages differing only in case are two passages.
 */
export async function fingerprint(content) {
  const normalised = (content ?? "").trim().replace(/\s+/g, " ");
  const bytes = new TextEncoder().encode(normalised);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

const keyFor = (originKey) => `${SEEN_STORAGE_PREFIX}${originKey}`;

/** Whether this install has already captured this content. */
export async function alreadyCaptured(storage, originKey, digest) {
  const stored = await storage.get(keyFor(originKey));
  const seen = stored?.[keyFor(originKey)] ?? [];
  return seen.includes(digest);
}

/**
 * Record a capture's fingerprint, evicting oldest-first past the bound.
 *
 * Called only **after** the door accepted the capture. Recording before would
 * mean a failed post suppressed the retry — the human clicks again, nothing
 * happens, and nothing explains why.
 */
export async function remember(storage, originKey, digest) {
  const key = keyFor(originKey);
  const stored = await storage.get(key);
  const seen = stored?.[key] ?? [];
  if (seen.includes(digest)) return seen;

  const next = [...seen, digest].slice(-SEEN_LIMIT);
  await storage.set({ [key]: next });
  return next;
}
