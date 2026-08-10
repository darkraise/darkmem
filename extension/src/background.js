/**
 * The MV3 service worker: a context-menu entry that captures the selection.
 *
 * Thin on purpose. Everything decidable lives in `origin.js` and `capture.js`
 * so it can be tested without a browser; this file is the wiring that a test
 * environment cannot exercise anyway, and keeping logic out of it is what
 * makes `npm test` meaningful rather than decorative.
 */

import { getOriginKey } from "./origin.js";
import {
  CaptureRefused,
  buildCapture,
  permissionHint,
  postCapture,
} from "./capture.js";
import { packageExchange } from "./adapters.js";
import { alreadyCaptured, fingerprint, remember } from "./dedupe.js";

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
    const packaged = packageExchange({
      selection: info.selectionText,
      pageUrl: info.pageUrl ?? tab?.url,
      pageTitle: tab?.title,
    });
    const body = buildCapture({
      selection: packaged.content,
      pageUrl: info.pageUrl ?? tab?.url,
      pageTitle: tab?.title,
      originKey,
      project,
    });
    // The adapter's attribution rides alongside the shell's page metadata
    // rather than replacing it: the shell's two fields are what a plain
    // capture carries, and an adapter only ever adds.
    body.metadata = { ...body.metadata, ...packaged.metadata };

    const digest = await fingerprint(body.content);
    if (await alreadyCaptured(chrome.storage.local, originKey, digest)) {
      // Reported, not silent. A human who selects the same passage twice
      // deserves to know why the second click did nothing -- otherwise the
      // feature looks broken exactly when it is working.
      await notify("Already captured — this passage is in darkmem");
      return;
    }

    await postCapture(fetch, baseUrl, body, { token });
    // Recorded only after the door accepted: remembering first would let a
    // failed post suppress the retry.
    await remember(chrome.storage.local, originKey, digest);
    await notify("Captured to darkmem");
  } catch (error) {
    // Surfaced, never swallowed: a capture that silently did not happen is
    // the failure the human cannot detect, and they have already navigated
    // away by the time anything else could tell them.
    // A transport failure is where the manifest's narrow `host_permissions`
    // shows up, and it shows up as a bare "Failed to fetch" that reads like
    // darkmem being down. `CaptureRefused` is ours and needs no hint.
    const hint =
      error instanceof CaptureRefused
        ? ""
        : permissionHint(baseUrl, chrome.runtime.getManifest().host_permissions);
    await notify(
      error instanceof CaptureRefused
        ? `Not captured — ${error.message}`
        : `Not captured — ${error?.message ?? "the request did not complete"}${hint}`,
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
