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

/**
 * Turn markers these surfaces render.
 *
 * **Colon only.** A dash separator was accepted in the first version and it
 * misfired on ordinary prose: "AI-assisted coding is..." matched the
 * assistant pattern and shipped a fabricated turn role. A speaker label is
 * `Name:`; anything looser reads English as markup.
 */
const TURN_PATTERNS = [
  { role: "user", pattern: /^(you|user|me):\s+/i },
  { role: "assistant", pattern: /^(chatgpt|claude|gemini|assistant):\s+/i },
];

/**
 * Split a selection into labelled turns where the surface marked them.
 *
 * Conservative on purpose, and the rule is narrower than an earlier version of
 * this comment claimed (corrected 2026-08-09 after review). An unmarked line
 * **before any marker** is kept as an `unknown` turn. An unmarked line *after*
 * one is a continuation and joins the turn above it, which is what a wrapped
 * paragraph is — treating each wrapped line as its own `unknown` turn would
 * shred every multi-line message. So: openers are never guessed; continuations
 * are attributed, because a line following "Claude:" with no new marker is
 * still Claude speaking.
 *
 * Mislabelling who said something is worse than not labelling it — an
 * assistant's claim attributed to the human reads as the human's own
 * assertion, and darkmem stores it as one.
 */
export function splitTurns(selection) {
  const text = selection ?? "";

  // **A selection with no line breaks yields no roles at all**, and that is
  // the case that matters rather than an edge: Chromium collapses newlines in
  // `info.selectionText`, so a two-turn exchange can arrive as one line. The
  // first version then labelled the whole thing with the first speaker it saw
  // and shipped `["user"]` over text containing the assistant's reply --
  // precisely the misattribution this module calls worse than no label. With
  // no separator there is no evidence of where a turn ends, so it says
  // nothing instead of guessing.
  if (!/\r?\n/.test(text.trim())) return [];

  const lines = text.split(/\r?\n/);
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
