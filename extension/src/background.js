/**
 * The MV3 service worker: a context-menu entry that captures the selection.
 *
 * Thin on purpose. Everything decidable lives in `origin.js` and `capture.js`
 * so it can be tested without a browser; this file is the wiring that a test
 * environment cannot exercise anyway, and keeping logic out of it is what
 * makes `npm test` meaningful rather than decorative.
 */

import { getOriginKey } from "./origin.js";
import { CaptureRefused, buildCapture, postCapture } from "./capture.js";

const MENU_ID = "darkmem-capture-selection";
const SETTINGS_KEYS = ["darkmem.base_url", "darkmem.token", "darkmem.project"];

async function settings() {
  const stored = await chrome.storage.local.get(SETTINGS_KEYS);
  return {
    baseUrl: stored["darkmem.base_url"] || "http://localhost:8000",
    token: stored["darkmem.token"] || "",
    project: stored["darkmem.project"] || "default",
  };
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Capture selection to darkmem",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID) return;

  const { baseUrl, token, project } = await settings();
  try {
    const originKey = await getOriginKey(chrome.storage.local);
    const body = buildCapture({
      selection: info.selectionText,
      pageUrl: info.pageUrl ?? tab?.url,
      pageTitle: tab?.title,
      originKey,
      project,
    });
    await postCapture(fetch, baseUrl, body, { token });
    await notify("Captured to darkmem");
  } catch (error) {
    // Surfaced, never swallowed: a capture that silently did not happen is
    // the failure the human cannot detect, and they have already navigated
    // away by the time anything else could tell them.
    await notify(
      error instanceof CaptureRefused
        ? `Not captured — ${error.message}`
        : `Not captured — ${error?.message ?? "the request did not complete"}`,
    );
  }
});

async function notify(message) {
  try {
    await chrome.action.setTitle({ title: message });
  } catch {
    // The badge is a courtesy; losing it must not turn a successful capture
    // into a reported failure.
  }
}
