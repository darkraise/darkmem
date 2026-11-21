/**
 * T4.07 — auto-capture is opt-in, per install, and visible while it runs.
 *
 * The three done-whens, and what each is worth as a test:
 *
 * - **Off by default and per-install opt-in.** Cheap to assert on a boolean
 *   and nearly worthless there, because the boolean is the extension's promise
 *   to itself. The load-bearing assertions are on the *manifest*: the chat
 *   hosts must be optional, so an install that never opted in has no access to
 *   those pages at all — a property Chrome enforces and a bug here cannot
 *   revoke.
 * - **The `origin_key` still collapses one install to one origin.** Auto-
 *   capture raises the volume, and volume is exactly what the distinct-origin
 *   rule is built to ignore. A per-turn or per-tab key would let one browser
 *   corroborate itself.
 * - **A clear indicator while it is active.**
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import vm from "node:vm";

import {
  AUTO_CAPTURE_BADGE,
  AUTO_CAPTURE_KEY,
  CHAT_HOST_PATTERNS,
  autoCaptureActive,
  autoCaptureIndicator,
  autoCaptureRequest,
  readAutoCaptureState,
} from "../src/autocapture.js";
import { getOriginKey } from "../src/origin.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    async get(keys) {
      const wanted = Array.isArray(keys) ? keys : [keys];
      const out = {};
      for (const key of wanted) if (key in data) out[key] = data[key];
      return out;
    },
    async set(update) {
      Object.assign(data, update);
    },
  };
}

// ── off by default, and the browser is what enforces it ──

test("the chat surfaces are optional permissions, not granted at install", () => {
  // The assertion that actually protects a human: an install that never opted
  // in cannot read chatgpt.com at all, whatever this extension's code says.
  const granted = manifest.host_permissions ?? [];
  for (const host of granted) {
    assert.ok(
      !/chatgpt|openai|claude\.ai|gemini|google/i.test(host),
      `a chat surface is granted at install time: ${host}`,
    );
  }
  const optional = manifest.optional_host_permissions ?? [];
  for (const pattern of CHAT_HOST_PATTERNS) {
    assert.ok(
      optional.includes(pattern),
      `${pattern} must be an optional host permission for the opt-in to mean anything`,
    );
  }
});

test("scripting is optional too — it is how a page is reached without a gesture", () => {
  assert.ok(!(manifest.permissions ?? []).includes("scripting"));
  assert.ok((manifest.optional_permissions ?? []).includes("scripting"));
});

test("no static content script ships — the observer is registered after the grant", () => {
  assert.equal(manifest.content_scripts, undefined);
});

test("the opt-in asks for exactly the chat hosts, never a wildcard", () => {
  // `<all_urls>` here would be an opt-in to everything the human browses,
  // which is not the thing being opted into.
  const request = autoCaptureRequest();
  assert.deepEqual(request.origins, [...CHAT_HOST_PATTERNS]);
  for (const origin of request.origins) {
    assert.ok(!origin.includes("<all_urls>"));
    assert.ok(!origin.startsWith("*://*/"));
  }
});

test("a fresh install reads as off", async () => {
  const state = await readAutoCaptureState(fakeStorage(), async () => false);

  assert.equal(state.enabled, false);
  assert.equal(state.granted, false);
  assert.equal(state.active, false);
});

test("both gates are required, in both directions", () => {
  // Each half alone is a real state: the human revoked the host grant from
  // Chrome's own UI, or cleared the flag while the grant lingers.
  assert.equal(autoCaptureActive({ enabled: true, granted: true }), true);
  assert.equal(autoCaptureActive({ enabled: true, granted: false }), false);
  assert.equal(autoCaptureActive({ enabled: false, granted: true }), false);
  assert.equal(autoCaptureActive({ enabled: false, granted: false }), false);
});

test("a revoked host grant deactivates without the flag being touched", async () => {
  const storage = fakeStorage({ [AUTO_CAPTURE_KEY]: true });

  const state = await readAutoCaptureState(storage, async () => false);

  assert.equal(state.enabled, true, "the human's stored intent is unchanged");
  assert.equal(state.active, false, "but Chrome's answer decides");
});

test("the permission is asked about even when the flag is off", async () => {
  // Short-circuiting would hide a lingering grant from the caller whose job is
  // to clean it up.
  let asked = false;
  await readAutoCaptureState(fakeStorage(), async () => {
    asked = true;
    return true;
  });

  assert.equal(asked, true);
});

// ── one install, one origin ──

test("auto-captured turns ride the install's own origin key", async () => {
  // Volume is what the distinct-origin rule ignores; a per-turn or per-tab key
  // would let one browser corroborate a claim with itself.
  const storage = fakeStorage();
  let n = 0;
  const mint = () => `id-${(n += 1)}`;

  const first = await getOriginKey(storage, mint);
  const laterTurns = await Promise.all([
    getOriginKey(storage, mint),
    getOriginKey(storage, mint),
    getOriginKey(storage, mint),
  ]);

  assert.deepEqual(new Set([first, ...laterTurns]), new Set([first]));
});

test("nothing in the auto-capture module mints an origin of its own", () => {
  // About the mechanism, not the word: the module names `origin_key` in prose
  // precisely because the rule matters to it. What it must not do is mint or
  // store one — `origin.js` owns that, and a second minter is how an install
  // grows a second identity.
  const source = readFileSync(join(ROOT, "src/autocapture.js"), "utf8");

  assert.ok(!source.includes("randomUUID"), "no minting here");
  assert.ok(!source.includes("ORIGIN_STORAGE_KEY"), "no writing the key here");
});

// ── the indicator ──

test("the indicator names the mode while it is on", () => {
  const on = autoCaptureIndicator(true);

  assert.equal(on.badge, AUTO_CAPTURE_BADGE);
  assert.match(on.title, /auto-captur/i);
});

test("the indicator clears when it is off, leaving the ordinary title", () => {
  const off = autoCaptureIndicator(false);

  assert.equal(off.badge, "");
  assert.match(off.title, /Capture selection/);
});

test("registration status handles failure, recovery and overlapping syncs", async () => {
  const listeners = {};
  const badges = [];
  const titles = [];
  const registrations = [];
  let finishBadge;
  let badgeUpdated = new Promise((resolve) => { finishBadge = resolve; });
  let registrationFails = true;
  let registrationBlock;
  let registrationStarted;
  const storage = fakeStorage({ [AUTO_CAPTURE_KEY]: true });
  globalThis.chrome = {
    storage: { local: storage },
    permissions: {
      contains: async () => true,
      onAdded: { addListener: (listener) => { listeners.permissionAdded = listener; } },
      onRemoved: { addListener: () => {} },
    },
    scripting: {
      unregisterContentScripts: async () => {},
      registerContentScripts: async (scripts) => {
        registrations.push(scripts);
        if (registrationBlock) {
          registrationStarted();
          await registrationBlock;
        }
        if (registrationFails) throw new Error("registration refused");
      },
    },
    action: {
      setTitle: async ({ title }) => { titles.push(title); },
      setBadgeText: async ({ text }) => { badges.push(text); finishBadge(); },
    },
    runtime: {
      onInstalled: { addListener: () => {} },
      onMessage: { addListener: (listener) => { listeners.message = listener; } },
    },
    contextMenus: { onClicked: { addListener: () => {} } },
  };

  try {
    await import("../src/background.js?registration-test");
    listeners.permissionAdded();
    await badgeUpdated;
    assert.equal(badges.at(-1), "");
    assert.match(titles.at(-1), /auto-capture.*(?:failed|unavailable|not running)/i);

    const failedStatus = new Promise((resolve) => {
      const keepAlive = listeners.message(
        { type: "darkmem.auto_capture.sync" }, {}, resolve,
      );
      assert.equal(keepAlive, true);
    });
    assert.equal((await failedStatus).active, false);

    registrationFails = false;
    badgeUpdated = new Promise((resolve) => { finishBadge = resolve; });
    const recoveredStatus = new Promise((resolve) => {
      const keepAlive = listeners.message(
        { type: "darkmem.auto_capture.sync" }, {}, resolve,
      );
      assert.equal(keepAlive, true);
    });
    assert.equal((await recoveredStatus).active, true);
    await badgeUpdated;
    assert.equal(badges.at(-1), "REC");
    assert.match(titles.at(-1), /auto-captur/i);
    assert.deepEqual(registrations.at(-1)[0].js, ["src/content-autocapture.js"]);

    let releaseRegistration;
    registrationBlock = new Promise((resolve) => { releaseRegistration = resolve; });
    const started = new Promise((resolve) => { registrationStarted = resolve; });
    const firstSync = new Promise((resolve) => {
      listeners.message({ type: "darkmem.auto_capture.sync" }, {}, resolve);
    });
    await started;
    storage.data[AUTO_CAPTURE_KEY] = false;
    const secondSync = new Promise((resolve) => {
      listeners.message({ type: "darkmem.auto_capture.sync" }, {}, resolve);
    });
    await new Promise((resolve) => setImmediate(resolve));
    releaseRegistration();
    await Promise.all([firstSync, secondSync]);
    assert.equal(badges.at(-1), "");
    assert.match(titles.at(-1), /Capture selection/);
  } finally {
    delete globalThis.chrome;
  }
});

// ── the observer captures a reply once it has settled ──

/**
 * Runs the content script in a sandbox: a fake chat page whose message
 * elements the test edits, the observer the script registers, and a clock
 * the test moves. `sent` holds every turn the script posted to the worker.
 */
function observedPage(initial = []) {
  const messages = initial.map((text) => ({ innerText: text }));
  const timers = new Map();
  let now = 0;
  let nextTimer = 1;
  let onMutation = null;
  const sent = [];
  const sandbox = {
    location: { hostname: "chatgpt.com", href: "https://chatgpt.com/c/1" },
    document: {
      title: "Chat",
      body: {},
      querySelectorAll: () => [...messages],
    },
    MutationObserver: class {
      constructor(callback) {
        onMutation = callback;
      }
      observe() {}
      disconnect() {
        onMutation = null;
      }
    },
    chrome: { runtime: { sendMessage: (message) => sent.push(message) } },
    window: { addEventListener() {} },
    setTimeout: (fn, ms) => {
      const id = nextTimer++;
      timers.set(id, { at: now + ms, fn });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
  };
  vm.runInNewContext(readFileSync(join(ROOT, "src/content-autocapture.js"), "utf8"), sandbox);
  const page = {
    sent,
    messages,
    add(text) {
      const message = { innerText: text };
      messages.push(message);
      page.mutate();
      return message;
    },
    set(message, text) {
      message.innerText = text;
      page.mutate();
    },
    mutate() {
      onMutation?.([]);
    },
    advance(ms) {
      const until = now + ms;
      for (;;) {
        const due = [...timers.entries()]
          .filter(([, timer]) => timer.at <= until)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        timers.delete(due[0]);
        now = due[1].at;
        due[1].fn();
      }
      now = until;
    },
    texts: () => sent.map((message) => message.content),
  };
  return page;
}

test("a reply that changes 30 times before settling is captured once", () => {
  const page = observedPage(["an earlier turn"]);
  const reply = page.add("t");
  let text = "t";
  for (let i = 0; i < 30; i++) {
    page.advance(100);
    text += ` token${i}`;
    page.set(reply, text);
  }
  assert.deepEqual(page.texts(), []);
  page.advance(2999);
  assert.deepEqual(page.texts(), []);
  page.advance(1);
  assert.deepEqual(page.texts(), [text]);
});

test("a settled message is not captured again", () => {
  const page = observedPage();
  page.add("a whole reply");
  page.advance(3000);
  page.mutate();
  page.add("");
  page.advance(10_000);
  assert.deepEqual(page.texts(), ["a whole reply"]);
});

test("an edited message is captured again after it settles", () => {
  const page = observedPage();
  const reply = page.add("first wording");
  page.advance(3000);
  page.set(reply, "second wording");
  page.advance(2999);
  assert.deepEqual(page.texts(), ["first wording"]);
  page.advance(1);
  assert.deepEqual(page.texts(), ["first wording", "second wording"]);
  page.advance(10_000);
  assert.equal(page.sent.length, 2);
});

test("a reply over the size limit is skipped whole", () => {
  const page = observedPage();
  const reply = page.add("x".repeat(5000));
  for (const size of [10_000, 15_000, 20_001]) {
    page.advance(500);
    page.set(reply, "x".repeat(size));
  }
  page.advance(10_000);
  assert.deepEqual(page.sent, []);
});

test("two messages settle independently", () => {
  const page = observedPage();
  const first = page.add("message A");
  page.advance(2000);
  const second = page.add("message B starts");
  page.advance(1000);
  assert.deepEqual(page.texts(), ["message A"]);
  page.set(second, "message B, longer");
  page.advance(2999);
  assert.deepEqual(page.texts(), ["message A"]);
  page.advance(1);
  assert.deepEqual(page.texts(), ["message A", "message B, longer"]);
  assert.equal(first.innerText, "message A");
});
