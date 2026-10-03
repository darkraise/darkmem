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
import {
  AUTO_CAPTURE_MESSAGE,
  AUTO_CAPTURE_SCRIPT_ID,
  AUTO_CAPTURE_SYNC_MESSAGE,
  CHAT_HOST_PATTERNS,
  autoCaptureIndicator,
  autoCaptureRequest,
  readAutoCaptureState,
} from "./autocapture.js";

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
  syncAutoCapture();
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

/**
 * Bring the registered observer in line with the two gates (T4.07).
 *
 * Called on every wakeup and after every opt-in change rather than only when
 * the human toggles: a host grant can be revoked from Chrome's own extensions
 * page without this extension being told, and a registration that outlived its
 * permission is the state the opt-in exists to make impossible.
 */
let lastAutoCaptureSync = Promise.resolve();

function syncAutoCapture() {
  const result = lastAutoCaptureSync.then(reconcileAutoCapture);
  lastAutoCaptureSync = result.catch(() => {});
  return result;
}

async function reconcileAutoCapture() {
  const state = await readAutoCaptureState(
    chrome.storage.local,
    (request) => chrome.permissions.contains(request),
  );

  let registered = false;
  try {
    if (state.active) {
      // Idempotent by removing first: `registerContentScripts` throws on a
      // duplicate id, and a worker that woke twice would otherwise leave
      // auto-capture off with an error nobody sees.
      await chrome.scripting.unregisterContentScripts({
        ids: [AUTO_CAPTURE_SCRIPT_ID],
      }).catch(() => {});
      await chrome.scripting.registerContentScripts([
        {
          id: AUTO_CAPTURE_SCRIPT_ID,
          js: ["src/content-autocapture.js"],
          matches: [...CHAT_HOST_PATTERNS],
          runAt: "document_idle",
        },
      ]);
      registered = true;
    } else {
      await chrome.scripting.unregisterContentScripts({
        ids: [AUTO_CAPTURE_SCRIPT_ID],
      }).catch(() => {});
    }
  } catch {}

  const indicator = state.active && !registered
    ? { badge: "", title: "Auto-capture unavailable — observer registration failed" }
    : autoCaptureIndicator(registered);
  await notify(indicator.title);
  try {
    await chrome.action.setBadgeText({ text: indicator.badge });
  } catch {
    // The badge is a courtesy; the title already carries the mode.
  }
  return { ...state, active: registered };
}

/**
 * One auto-captured turn, filed through the ordinary capture door.
 *
 * Same door, same `origin_key`, same dedupe as a clicked capture — doc 15 §4's
 * whole stance is that browser capture is a new *source*, not a new pipeline,
 * and auto-capture must not become a second one inside the extension either.
 *
 * The gates are re-read here rather than trusted from the fact that a message
 * arrived. A content script registered a moment ago can outlive a revoked
 * permission by one message, and the door is the last place to stop it.
 */
async function captureTurn({ content, pageUrl, pageTitle }) {
  const state = await readAutoCaptureState(
    chrome.storage.local,
    (request) => chrome.permissions.contains(request),
  );
  if (!state.active) return;

  const { baseUrl, token, project } = await settings();
  const originKey = await getOriginKey(chrome.storage.local);
  const packaged = packageExchange({ selection: content, pageUrl, pageTitle });
  const body = buildCapture({
    selection: packaged.content,
    pageUrl,
    pageTitle,
    originKey,
    project,
  });
  body.metadata = { ...body.metadata, ...packaged.metadata, auto_captured: true };

  const digest = await fingerprint(body.content);
  if (await alreadyCaptured(chrome.storage.local, originKey, digest)) return;

  await postCapture(fetch, baseUrl, body, { token });
  await remember(chrome.storage.local, originKey, digest);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === AUTO_CAPTURE_SYNC_MESSAGE) {
    syncAutoCapture().then(sendResponse, () => sendResponse(null));
    return true;
  }
  if (message?.type !== AUTO_CAPTURE_MESSAGE) return;
  // Failures are swallowed here rather than surfaced per turn: auto-capture
  // runs unattended by definition, and a toolbar that reported every transient
  // failure would train the human to ignore the one indicator that matters.
  // The mode's own state stays on the badge.
  captureTurn(message).catch(() => {});
});

chrome.permissions.onAdded.addListener(() => {
  syncAutoCapture();
});
chrome.permissions.onRemoved.addListener(() => {
  syncAutoCapture();
});

async function notify(message) {
  try {
    await chrome.action.setTitle({ title: message });
  } catch {
    // The badge is a courtesy; losing it must not turn a successful capture
    // into a reported failure.
  }
}
