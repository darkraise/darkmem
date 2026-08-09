/**
 * The capture call (T3.26, doc 15 §4).
 *
 * **The ordinary capture door, and nothing else.** This posts to
 * `POST /api/v1/memories` — the same door the REST clients and the MCP tools
 * reach. An extension-specific endpoint would be a second capture path to keep
 * in step with buffering, `source` resolution and the 202 ack contract, and
 * the repo has already paid for that shape twice (the two RRF constants, the
 * duplicated MCP code-search implementations).
 *
 * **No site adapter, by design.** The done-when is that the shell works with
 * none: the payload is whatever the human selected, plus where they selected
 * it. Per-site extraction is T3.15's, and building a hook for it here would be
 * scaffolding for a caller that does not exist.
 */

export const CAPTURE_PATH = "/api/v1/memories";
export const SOURCE = "browser-extension";
export const MAX_SELECTION_CHARS = 20000;

export class CaptureRefused extends Error {}

/**
 * Build the capture body for a human-selected passage.
 *
 * The page URL and title ride as context rather than being prepended to the
 * content: darkmem extracts entities from `content`, so folding the chrome of
 * the page into it would mint entities for the site's navigation furniture.
 */
export function buildCapture({ selection, pageUrl, pageTitle, originKey, project }) {
  const text = (selection ?? "").trim();
  if (!text) {
    // A selection-less capture would file an empty memory that no human
    // intended and no reader can act on. Refusing is the honest answer, and
    // it is refused here rather than at the server so the user hears about
    // it while the page is still in front of them.
    throw new CaptureRefused("nothing selected");
  }
  if (text.length > MAX_SELECTION_CHARS) {
    throw new CaptureRefused(
      `selection is ${text.length} characters; the capture bound is ${MAX_SELECTION_CHARS}`,
    );
  }

  return {
    content: text,
    source: SOURCE,
    origin_key: originKey,
    project: project || "default",
    metadata: { page_url: pageUrl ?? null, page_title: pageTitle ?? null },
  };
}

/**
 * POST one capture. Returns the door's 202 ack.
 *
 * 202 is the expected success, not an edge case: every capture door buffers
 * and answers with a `CaptureAck` carrying the pre-minted memory id. Treating
 * only 201 as success would report every ordinary capture as a failure.
 */
export async function postCapture(fetchImpl, baseUrl, body, { token } = {}) {
  const response = await fetchImpl(`${baseUrl}${CAPTURE_PATH}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Names this client to the server's source resolution, which prefers an
      // explicit header over the User-Agent product map.
      "X-Darkmem-Client": SOURCE,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (response.status !== 202 && response.status !== 201) {
    throw new CaptureRefused(
      `capture door answered ${response.status}; the selection was not filed`,
    );
  }
  return response.json();
}
