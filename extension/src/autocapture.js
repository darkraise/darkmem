/**
 * Auto-capture: the opt-in that widens v1's selection-only scope (T4.07,
 * doc 15 §4).
 *
 * v1 captures only what the human selected and clicked, because "auto-scraping
 * an entire chat surface is a privacy and noise problem" and the human stays
 * the authority on what becomes a memory. This module does not overturn that;
 * it makes the widening reachable only by an explicit, per-install act.
 *
 * **Opt-in is enforced by the browser, not by a boolean here.** A stored flag
 * alone is a promise the extension makes to itself: the code that reads it is
 * the code that could stop reading it, and an install would still be shipping
 * host access to three chat surfaces from the moment it was installed. So the
 * chat hosts live in `optional_host_permissions` — ungranted until the human
 * grants them through the options page — and the observing content script is
 * *registered at runtime*, after the grant. An install that never opted in has
 * no access to those pages at all, which is a property Chrome enforces and
 * this code cannot revoke by having a bug.
 *
 * The stored flag is therefore the **second** of two gates rather than the
 * only one. Both must hold, and :func:`autoCaptureActive` is the one place
 * that says so — a caller checking either half alone is the shape that turns
 * a revoked permission into a silent no-op, or a cleared flag into an
 * extension still reading pages.
 *
 * **One origin, still.** Auto-captured turns ride the same per-install
 * `origin_key` as clicked ones. That is what keeps a chatty surface from
 * corroborating itself: `COUNT(DISTINCT origin_key)` does not care how many
 * messages arrived, only how many independent witnesses there were, and this
 * install is one either way. Auto-capture makes the volume higher, which is
 * exactly why the key must not become finer-grained to match.
 */

export const AUTO_CAPTURE_KEY = "darkmem.auto_capture";

/** The content script's id in the dynamic registry, so a revoke can find it. */
export const AUTO_CAPTURE_SCRIPT_ID = "darkmem-auto-capture";

/**
 * The chat surfaces auto-capture can observe — doc 15 §4's v1 adapter set.
 *
 * Deliberately the same three the adapters already recognise, and no wildcard:
 * `<all_urls>` here would be an opt-in to everything the human ever browses,
 * which is not the thing being opted into.
 */
export const CHAT_HOST_PATTERNS = Object.freeze([
  "https://chatgpt.com/*",
  "https://claude.ai/*",
  "https://gemini.google.com/*",
]);

/** The permission bundle the opt-in asks Chrome for. */
export function autoCaptureRequest() {
  return { permissions: ["scripting"], origins: [...CHAT_HOST_PATTERNS] };
}

/**
 * Whether auto-capture may run right now.
 *
 * Both gates, read together and never apart. `granted` is the browser's
 * answer, `enabled` the human's stored intent; a true value for one and a
 * false for the other is a real state — the human revoked the permission from
 * Chrome's own UI, or toggled the flag off while the grant lingers — and in
 * both directions the answer is no.
 */
export function autoCaptureActive({ enabled, granted }) {
  return Boolean(enabled) && Boolean(granted);
}

/**
 * Read both gates. `hasPermissions` is `chrome.permissions.contains`.
 *
 * The permission is re-read rather than cached: Chrome lets a human revoke a
 * host grant at any time from the extensions page, without telling the
 * extension, and a cached answer would keep an observer running against a
 * permission that no longer exists — or, revoked in the other direction,
 * would leave a human who re-granted it wondering why nothing resumed.
 */
export async function readAutoCaptureState(storage, hasPermissions) {
  const stored = await storage.get(AUTO_CAPTURE_KEY);
  const enabled = stored?.[AUTO_CAPTURE_KEY] === true;
  // Asking Chrome about a permission this install never requested is cheap and
  // answers false; skipping the call when `enabled` is false would make the
  // two gates read in a fixed order and hide a lingering grant from the
  // caller that wants to clean it up.
  const granted = await hasPermissions(autoCaptureRequest());
  return { enabled, granted, active: autoCaptureActive({ enabled, granted }) };
}

/**
 * The message an auto-captured turn carries to the worker.
 *
 * The content script never talks to darkmem itself, and that is a boundary
 * rather than a style choice: the token lives in the worker's storage, and a
 * script injected into a chat page is the least trustworthy place in the
 * extension to hold a credential the page's own scripts share an origin with.
 */
export const AUTO_CAPTURE_MESSAGE = "darkmem.auto_capture.turn";

/**
 * Turns the observer has not sent yet, in order.
 *
 * Keyed on the turn's own text rather than a DOM node: a chat surface
 * re-renders its list constantly, and node identity does not survive that
 * while the text does. The seen-set is the observer's, per page — the
 * *durable* guard against re-capturing is `dedupe.js` at the door, which
 * survives a reload and this does not.
 */
export function unsentTurns(seen, turns) {
  const out = [];
  for (const turn of turns ?? []) {
    const text = (turn ?? "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

/**
 * The observer's opening state: everything already on screen counts as seen,
 * and nothing is sent.
 *
 * Opting in must not retroactively capture the conversation the human had
 * *before* they opted in. That is a materially larger act than "capture what
 * happens from now on" — it is the whole history, sent at once, on a click
 * whose label promises the smaller thing.
 *
 * A function rather than two lines in the observer because the promise is on
 * the options page and needs somewhere a test can reach: the mutation that
 * deletes the seeding step is invisible in a DOM-driven file.
 */
export function firstSweep(turns) {
  const seen = new Set();
  unsentTurns(seen, turns);
  return { seen, toSend: [] };
}

/**
 * What the toolbar says while auto-capture is on.
 *
 * The done-when asks for a clear indicator, and "clear" is doing work here:
 * an extension reading a conversation without the human currently thinking
 * about it is exactly the state that must not be quiet. So the title names
 * the mode rather than the last event, and the badge is set for as long as the
 * mode is on rather than flashing per capture.
 */
export const AUTO_CAPTURE_BADGE = "REC";

export function autoCaptureIndicator(active) {
  return active
    ? {
        badge: AUTO_CAPTURE_BADGE,
        title:
          "darkmem is auto-capturing this AI chat — every new turn is sent to darkmem",
      }
    : { badge: "", title: "Capture selection to darkmem" };
}
