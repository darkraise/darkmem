/**
 * T3.15's third done-when: **no automatic capture path exists in v1** —
 * "asserted by a test over the built bundle, not by review ('proven by review'
 * is not objectively checkable)".
 *
 * So this file does not read the code for intent. It scans every shipped
 * source and the manifest for the mechanisms by which a capture could fire
 * without a human, and it pins the inverse too: every path that *does* reach
 * the capture door starts at a user gesture. Auto-scrape is T4.07 — demand-
 * gated and opt-in — and the promise that v1 has none is only worth what a
 * machine can check.
 */

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "src");

const sources = readdirSync(SRC)
  .filter((f) => f.endsWith(".js"))
  .map((f) => ({ file: f, text: readFileSync(join(SRC, f), "utf8") }));

/**
 * Mechanisms that fire without a human. Each one is a way a page or a timer
 * could reach the capture door on its own.
 */
const AUTOMATIC_TRIGGERS = [
  "setInterval",
  "setTimeout",
  "requestIdleCallback",
  "requestAnimationFrame",
  "MutationObserver",
  "IntersectionObserver",
  "chrome.tabs.onUpdated",
  "chrome.webNavigation",
  "chrome.alarms",
  "onDOMContentLoaded",
  "DOMContentLoaded",
  "chrome.scripting.executeScript",
];

test("no shipped source arms an automatic trigger", () => {
  const offenders = [];
  for (const { file, text } of sources) {
    for (const trigger of AUTOMATIC_TRIGGERS) {
      if (text.includes(trigger)) offenders.push(`${file}: ${trigger}`);
    }
  }
  assert.deepEqual(
    offenders,
    [],
    "v1 capture is human-triggered only; auto-scrape is T4.07, demand-gated " +
      `and opt-in:\n  ${offenders.join("\n  ")}`,
  );
});

test("the manifest grants only the two permissions capture needs", () => {
  // An allowlist, because the denylist above is alias-defeatable and this is
  // not: a capture that runs without a human needs a capability, and the
  // manifest is where capabilities are granted. Found by the 2026-08-09 task
  // review, which noted this arm called itself "the sharpest bundle-level
  // check available" while never reading `permissions` -- where the unused
  // `scripting` and `activeTab` grants sat.
  const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));

  assert.deepEqual(
    [...(manifest.permissions ?? [])].sort(),
    ["contextMenus", "storage"],
    "v1 needs the context menu and local storage; `scripting`, `activeTab` " +
      "and `tabs` are how a capture reaches a page without a gesture",
  );
});

test("no capture is reachable from an extension lifecycle event", () => {
  // The mutation that defeated the denylist: `chrome.runtime.onInstalled`
  // posting content no human selected passed all 36 tests, because
  // `onInstalled` is not a timer and `postCapture` is allowed in
  // background.js. So the assertion is about *which listener* the capture
  // sits in, not about which APIs are absent.
  const background = readFileSync(join(SRC, "background.js"), "utf8");

  const lifecycle = ["onInstalled", "onStartup", "onConnect", "onMessage"];
  for (const event of lifecycle) {
    const index = background.indexOf(event);
    if (index === -1) continue;
    // The listener body runs until the next top-level `chrome.` registration.
    const rest = background.slice(index);
    const body = rest.slice(0, rest.indexOf("\nchrome.") + 1 || rest.length);
    assert.ok(
      !body.includes("postCapture"),
      `capture reachable from ${event}, which fires without a human`,
    );
  }
});

test("no shipped source reaches an API through a computed name", () => {
  // `globalThis["set" + "Interval"]` passes a substring denylist. Computed
  // access to a global is the general shape, and v1 needs none of it.
  const computed = /(globalThis|window|self|chrome)\s*\[/;
  for (const { file, text } of sources) {
    assert.ok(!computed.test(text), `${file} reaches a global by computed name`);
  }
});

test("the manifest requests no host access to the AI-chat surfaces", () => {
  // The sharpest bundle-level check available: a content script injected into
  // chatgpt.com or claude.ai is the shape auto-scrape would take, and the
  // manifest is what grants it. v1 reads the selection the browser hands the
  // context menu, so it needs neither.
  const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));

  assert.equal(manifest.content_scripts, undefined);
  const hosts = manifest.host_permissions ?? [];
  for (const host of hosts) {
    assert.ok(
      !/chatgpt|openai|claude\.ai|gemini|google/i.test(host),
      `manifest grants access to an AI-chat surface: ${host}`,
    );
  }
});

test("every capture path begins at a user gesture", () => {
  // The inverse of the scan above: it is not enough that no timer exists —
  // the paths that DO capture must be reachable only from a human action.
  const background = sources.find((s) => s.file === "background.js").text;
  const gestures = ["contextMenus.onClicked", "action.onClicked"];

  assert.ok(
    gestures.some((g) => background.includes(g)),
    "capture must be entered from a user gesture",
  );

  // `postCapture` is the only door call, and it must not appear in a module
  // that a page could drive on its own.
  for (const { file, text } of sources) {
    if (!text.includes("postCapture(")) continue;
    assert.ok(
      file === "background.js" || file === "capture.js",
      `postCapture reached from ${file}, which is not the gesture-entered path`,
    );
  }
});

test("the adapters are pure — they take a selection, they do not read the page", () => {
  // An adapter that queried the DOM could gather what the human did not
  // select, which is auto-scrape by another name even when a human clicked.
  const adapters = sources.find((s) => s.file === "adapters.js").text;
  for (const dom of ["document.", "window.", "querySelector", "innerText", "innerHTML"]) {
    assert.ok(!adapters.includes(dom), `adapters.js touches the DOM: ${dom}`);
  }
});
