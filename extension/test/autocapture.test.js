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

import {
  AUTO_CAPTURE_BADGE,
  AUTO_CAPTURE_KEY,
  CHAT_HOST_PATTERNS,
  autoCaptureActive,
  autoCaptureIndicator,
  autoCaptureRequest,
  firstSweep,
  readAutoCaptureState,
  unsentTurns,
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

// ── what gets sent ──

test("a turn already sent this page-view is not sent again", () => {
  const seen = new Set();

  assert.deepEqual(unsentTurns(seen, ["one", "two"]), ["one", "two"]);
  assert.deepEqual(unsentTurns(seen, ["one", "two", "three"]), ["three"]);
});

test("blank turns are dropped rather than captured as empty memories", () => {
  assert.deepEqual(unsentTurns(new Set(), ["", "   ", "real"]), ["real"]);
});

test("turns keep their order — a conversation captured out of order is a different one", () => {
  assert.deepEqual(unsentTurns(new Set(), ["a", "b", "c"]), ["a", "b", "c"]);
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

// ── opting in does not back-fill ──

test("the first sweep sends nothing — opting in is not a request for the history", () => {
  // The options page promises this in words. Sending the existing conversation
  // is a materially larger act than "capture what happens from now on", on a
  // click whose label promises the smaller one.
  const sweep = firstSweep(["an earlier question", "an earlier answer"]);

  assert.deepEqual(sweep.toSend, []);
});

test("what was already on screen is never sent later either", () => {
  const { seen } = firstSweep(["already here"]);

  assert.deepEqual(unsentTurns(seen, ["already here", "brand new"]), ["brand new"]);
});
