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
