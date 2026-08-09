/**
 * The per-install `origin_key` (T3.26, doc 15 §4).
 *
 * `origin_key` is darkmem's corroboration-independence key: facts count
 * `COUNT(DISTINCT origin_key)` over their sources, so what this value
 * identifies decides what "two independent origins agreed" means. Two
 * properties follow, and both are the point of this module rather than
 * details of it.
 *
 * **Stable across restarts.** A key regenerated per session would let one
 * browser corroborate a claim with itself simply by being restarted — the
 * chatty-source failure the distinct-origin rule exists to prevent, reached
 * from the client side. So it is minted once and read from `storage.local`
 * forever after.
 *
 * **Per install, not per site or per tab.** The independent thing here is the
 * human at this browser, not the page they happened to be reading. Keying on
 * the site would make one person clipping five blogs look like five witnesses.
 */

export const ORIGIN_STORAGE_KEY = "darkmem.origin_key";
export const ORIGIN_PREFIX = "ext";

/**
 * Read the install's key, minting one on first use.
 *
 * Concurrency matters here despite the small surface: MV3 wakes the service
 * worker per event, so two events arriving together can both find an empty
 * store. The re-read after writing is what makes the loser of that race adopt
 * the winner's key instead of overwriting it — without it an install could
 * hold two keys and count as two origins.
 */
export async function getOriginKey(storage, mintId = () => crypto.randomUUID()) {
  const existing = await storage.get(ORIGIN_STORAGE_KEY);
  if (existing && typeof existing[ORIGIN_STORAGE_KEY] === "string") {
    return existing[ORIGIN_STORAGE_KEY];
  }

  const minted = `${ORIGIN_PREFIX}:${mintId()}`;
  await storage.set({ [ORIGIN_STORAGE_KEY]: minted });

  const settled = await storage.get(ORIGIN_STORAGE_KEY);
  return settled?.[ORIGIN_STORAGE_KEY] ?? minted;
}
