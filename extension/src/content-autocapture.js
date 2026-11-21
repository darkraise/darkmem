/**
 * The auto-capture observer (T4.07, doc 15 §4).
 *
 * **This file is the only one in the extension that reads a page on its own
 * initiative, and it never ships enabled.** It is not listed in the manifest's
 * `content_scripts`; the worker registers it at runtime after the human grants
 * the optional host permission, and unregisters it when they take that back.
 * An install that never opted in has no host access to these surfaces, so this
 * script cannot run at all — Chrome enforces that, not this comment.
 *
 * **It holds no credential and talks to no server.** It posts observed turns
 * to the worker, which owns the token. A script injected into a chat page
 * shares an origin with that page's own scripts, which makes it the last place
 * in the extension that should hold a secret.
 *
 * **It reads turns, not the page.** The selectors below name the message
 * containers of the three surfaces and nothing else — no cookies, no inputs,
 * no headers. A surface that changes its markup yields nothing rather than
 * yielding the wrong thing: `unsentTurns` receives an empty list and the
 * observer goes quiet, which is the correct failure for a feature whose
 * hazard is capturing too much.
 *
 * **It sends a turn once it has settled.** A reply streams in token by
 * token, and every partial text is a different string, so sending on change
 * would file each prefix as its own memory. Each message element keeps its
 * last seen text and a timer; a change restarts the timer, and only a text
 * left unchanged for `SETTLE_MS` is sent.
 */

const AUTO_CAPTURE_MESSAGE = "darkmem.auto_capture.turn";

const SETTLE_MS = 3000;

// The worker's capture bound (`MAX_SELECTION_CHARS` in capture.js). This is a
// classic script and cannot import it; a settled turn past it is skipped
// here rather than sent to be refused.
const MAX_TURN_CHARS = 20000;

function unsentTurns(seen, turns) {
  const out = [];
  for (const turn of turns ?? []) {
    const text = (turn ?? "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function firstSweep(turns) {
  const seen = new Set();
  unsentTurns(seen, turns);
  return { seen };
}

/**
 * Where each surface keeps its message text.
 *
 * Kept here rather than in `adapters.js`, deliberately: that module is pure by
 * test — "an adapter that queried the DOM could gather what the human did not
 * select, which is auto-scrape by another name" — and the property is worth
 * more than the tidiness of one registry. This is the auto-scrape path; it is
 * the one place allowed to know about the DOM.
 */
const TURN_SELECTORS = [
  { host: /(^|\.)chatgpt\.com$/, selector: "[data-message-author-role]" },
  { host: /(^|\.)claude\.ai$/, selector: "[data-testid='chat-message']" },
  { host: /(^|\.)gemini\.google\.com$/, selector: "message-content" },
];

function selectorForHost(hostname) {
  return TURN_SELECTORS.find((entry) => entry.host.test(hostname))?.selector ?? null;
}

function readTurns(selector) {
  return [...document.querySelectorAll(selector)].map((node) => node.innerText ?? "");
}

/**
 * Per message element: the text it last showed and the timer that sends it
 * once that text has held for `SETTLE_MS`. `seen` stays the second guard, so
 * a re-rendered element showing an already-sent text sends nothing.
 */
function createSettler(seen) {
  const states = new Map();

  function settle(state) {
    state.timer = null;
    if (state.text.length > MAX_TURN_CHARS) return;
    send(unsentTurns(seen, [state.text]));
  }

  function observe(nodes, { initial = false } = {}) {
    const present = new Set(nodes);
    for (const [node, state] of states) {
      if (present.has(node)) continue;
      if (state.timer !== null) clearTimeout(state.timer);
      states.delete(node);
    }
    for (const node of nodes) {
      const text = (node.innerText ?? "").trim();
      let state = states.get(node);
      if (!state) {
        state = { text: initial ? text : "", timer: null };
        states.set(node, state);
      }
      if (text === state.text) continue;
      state.text = text;
      if (state.timer !== null) clearTimeout(state.timer);
      state.timer = text ? setTimeout(() => settle(state), SETTLE_MS) : null;
    }
  }

  function stop() {
    for (const state of states.values()) {
      if (state.timer !== null) clearTimeout(state.timer);
    }
    states.clear();
  }

  return { observe, stop };
}

function send(turns) {
  for (const content of turns) {
    // Fire and forget: the worker reports its own outcome through the toolbar,
    // and awaiting here would stall the observer behind the network on a
    // surface that produces turns faster than a round trip.
    chrome.runtime.sendMessage({
      type: AUTO_CAPTURE_MESSAGE,
      content,
      pageUrl: location.href,
      pageTitle: document.title,
    });
  }
}

function start() {
  const selector = selectorForHost(location.hostname);
  if (!selector) return;

  // Everything already on screen counts as seen rather than captured, and the
  // rule lives in `firstSweep` so a test can hold it. The per-page-view set it
  // returns is not the durable guard against re-capture — `dedupe.js` at the
  // door is, and it survives a reload; this only keeps one page-view from
  // re-sending what it already sent as the surface re-renders.
  const { seen } = firstSweep(readTurns(selector));
  const settler = createSettler(seen);
  settler.observe([...document.querySelectorAll(selector)], { initial: true });

  const observer = new MutationObserver(() => {
    settler.observe([...document.querySelectorAll(selector)]);
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  // A page leaving for good takes its pending timers with it; one kept in
  // the back/forward cache comes back still observing.
  window.addEventListener("pagehide", (event) => {
    if (event.persisted) return;
    observer.disconnect();
    settler.stop();
  });
}

start();
