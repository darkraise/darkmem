/**
 * Site adapters for AI-chat pages (T3.15, doc 15 §4).
 *
 * **The human selects; the adapter only packages.** v1 is human-triggered
 * capture, never auto-scrape (that is T4.07, demand-gated and opt-in), so an
 * adapter never reads the page on its own initiative and never runs without a
 * selection in hand. Every function here is pure: selection text in, capture
 * payload out. There is no DOM traversal, no polling, and nothing that could
 * fire without a user gesture — which is also what makes the "no automatic
 * capture path" done-when checkable over the bundle rather than by review.
 *
 * **What an adapter adds is attribution, not content.** On a chat page the
 * selected text usually spans both sides of an exchange, and who said what is
 * the part a plain capture loses. So an adapter's whole job is to label the
 * turns it can recognise and to name the surface the exchange came from. It
 * never rewrites, summarises or drops the human's selection: the captured
 * content is what was on screen.
 *
 * **The fallback is the contract, not a degradation.** T3.26's shell works on
 * any page with no adapter at all, and that property must survive this file:
 * an unknown host uses `PLAIN`, which passes the selection through unchanged.
 * A site that changes its markup therefore degrades to plain capture rather
 * than breaking capture.
 */

/** Turn markers these surfaces render, in the order they are tried. */
const TURN_PATTERNS = [
  { role: "user", pattern: /^(you|user|me)\s*[:—-]\s*/i },
  { role: "assistant", pattern: /^(chatgpt|claude|gemini|assistant|ai)\s*[:—-]\s*/i },
];

/**
 * Split a selection into labelled turns where the surface marked them.
 *
 * Conservative on purpose: a line that carries no recognised marker is kept
 * verbatim as an `unknown` turn rather than being guessed onto the previous
 * speaker. Mislabelling who said something is worse than not labelling it —
 * an assistant's claim attributed to the human reads as the human's own
 * assertion, and darkmem stores it as one.
 */
export function splitTurns(selection) {
  const lines = (selection ?? "").split(/\r?\n/);
  const turns = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const match = TURN_PATTERNS.find((t) => t.pattern.test(trimmed));
    if (match) {
      turns.push({ role: match.role, text: trimmed.replace(match.pattern, "") });
    } else if (turns.length > 0) {
      turns[turns.length - 1].text += `\n${trimmed}`;
    } else {
      turns.push({ role: "unknown", text: trimmed });
    }
  }
  return turns;
}

/** The adapter registry, keyed by hostname suffix. */
const ADAPTERS = [
  { name: "chatgpt", hosts: ["chatgpt.com", "chat.openai.com"] },
  { name: "claude", hosts: ["claude.ai"] },
  { name: "gemini", hosts: ["gemini.google.com"] },
];

export const PLAIN = "plain";

/**
 * The adapter name for a page URL, or `PLAIN`.
 *
 * Matched on the registrable suffix with a leading dot, never `includes`: a
 * substring match would adopt `claude.ai.evil.example` as Claude, and an
 * adapter is a statement about which surface the content came from.
 */
export function adapterFor(pageUrl) {
  let host;
  try {
    host = new URL(pageUrl ?? "").hostname.toLowerCase();
  } catch {
    return PLAIN;
  }
  const hit = ADAPTERS.find((a) =>
    a.hosts.some((h) => host === h || host.endsWith(`.${h}`)),
  );
  return hit ? hit.name : PLAIN;
}

/**
 * Package a human-selected exchange for the ordinary capture door.
 *
 * The content is the selection, unchanged. Everything the adapter derived —
 * the surface it came from and the turn labels — rides as metadata, for the
 * same reason T3.26 keeps the page title out of `content`: darkmem extracts
 * entities from `content`, and a label the human never wrote is not theirs.
 */
export function packageExchange({ selection, pageUrl, pageTitle }) {
  const surface = adapterFor(pageUrl);
  const turns = surface === PLAIN ? [] : splitTurns(selection);
  return {
    content: (selection ?? "").trim(),
    metadata: {
      page_url: pageUrl ?? null,
      page_title: pageTitle ?? null,
      capture_surface: surface,
      // Roles only. The text stays in `content`; duplicating it here would
      // put the same prose in the row twice and double what a later purge
      // has to reach.
      turn_roles: turns.map((t) => t.role),
    },
  };
}
