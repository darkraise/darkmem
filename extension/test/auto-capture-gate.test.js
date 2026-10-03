/**
 * The auto-capture gate — T3.15's third done-when, restated for T4.07.
 *
 * T3.15 promised v1 had **no** automatic capture path and pinned it over the
 * bundle, "because 'proven by review' is not objectively checkable". T4.07 is
 * the demand-gated opt-in that doc 15 §4 always deferred to this phase, so the
 * promise it makes is now narrower and has to be checked more carefully:
 *
 * > Automatic capture exists, and it is unreachable on an install that has not
 * > explicitly opted in — enforced by the browser, not by this extension's own
 * > code.
 *
 * That distinction is why the manifest arms below matter more than the source
 * scans. A stored boolean is a promise the extension makes to itself; an
 * ungranted `optional_host_permissions` entry is Chrome refusing to run the
 * script at all. This file asserts the second, and treats the first as the
 * secondary gate it is.
 *
 * The file was `no-auto-capture.test.js` until 2026-08-11. Keeping that name
 * while the property changed would have left the strongest-sounding guard in
 * the extension asserting something no longer true of it.
 */

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { Script, createContext } from "node:vm";
import { AUTO_CAPTURE_MESSAGE } from "../src/autocapture.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "src");

// The one file allowed to observe a page on its own initiative. It ships
// unregistered; the worker registers it only after the grant.
const OBSERVER = "content-autocapture.js";

const sources = readdirSync(SRC)
  .filter((f) => f.endsWith(".js"))
  .map((f) => ({ file: f, text: readFileSync(join(SRC, f), "utf8") }));

const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));

test("the registered observer executes as a classic script and sends only new turns", () => {
  const messages = [];
  const turns = ["earlier question", "earlier answer"];
  let onMutation;
  const context = createContext({
    chrome: { runtime: { sendMessage: (message) => messages.push(message) } },
    document: {
      title: "Chat",
      body: {},
      querySelectorAll: () => turns.map((innerText) => ({ innerText })),
    },
    location: { hostname: "chatgpt.com", href: "https://chatgpt.com/c/example" },
    MutationObserver: class {
      constructor(callback) {
        onMutation = callback;
      }
      observe() {}
    },
  });

  const observer = readFileSync(join(SRC, OBSERVER), "utf8");
  new Script(observer, { filename: OBSERVER }).runInContext(context);

  assert.equal(messages.length, 0);
  assert.equal(typeof onMutation, "function");
  turns.push("  ", "new answer", "next question");
  onMutation();
  onMutation();
  assert.deepEqual(JSON.parse(JSON.stringify(messages)), [{
    type: "darkmem.auto_capture.turn",
    content: "new answer",
    pageUrl: "https://chatgpt.com/c/example",
    pageTitle: "Chat",
  }, {
    type: "darkmem.auto_capture.turn",
    content: "next question",
    pageUrl: "https://chatgpt.com/c/example",
    pageTitle: "Chat",
  }]);
  assert.equal(messages[0].type, AUTO_CAPTURE_MESSAGE);
});

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
];

test("only the gated observer arms an automatic trigger", () => {
  // Narrowed from "no shipped source", not weakened: the observer is now the
  // single file where such a trigger may live, and every other source is held
  // to the original rule. A trigger reappearing in `capture.js` still fails.
  const offenders = [];
  for (const { file, text } of sources) {
    if (file === OBSERVER) continue;
    for (const trigger of AUTOMATIC_TRIGGERS) {
      if (text.includes(trigger)) offenders.push(`${file}: ${trigger}`);
    }
  }
  assert.deepEqual(
    offenders,
    [],
    "auto-capture lives in one gated file; every other path is human-triggered:\n  " +
      offenders.join("\n  "),
  );
});

test("the observer ships unregistered — the manifest lists no content script", () => {
  // This is the arm that makes the opt-in real. A `content_scripts` entry runs
  // on every matching page from install, which is the whole thing being opted
  // into.
  assert.equal(manifest.content_scripts, undefined);
});

test("the chat surfaces are optional host permissions, never granted ones", () => {
  const granted = manifest.host_permissions ?? [];
  for (const host of granted) {
    assert.ok(
      !/chatgpt|openai|claude\.ai|gemini|google/i.test(host),
      `manifest grants install-time access to an AI-chat surface: ${host}`,
    );
  }
  assert.ok((manifest.optional_host_permissions ?? []).length > 0);
});

test("the manifest grants only the two permissions capture needs", () => {
  // Unchanged from T3.15, and `scripting` is exactly why it stays: the review
  // that added this arm called `scripting` "how a capture reaches a page
  // without a gesture". T4.07 needs it — so it is *optional*, requested with
  // the hosts at opt-in time and handed back when the human switches off.
  assert.deepEqual(
    [...(manifest.permissions ?? [])].sort(),
    ["contextMenus", "storage"],
    "`scripting`, `activeTab` and `tabs` are how a capture reaches a page " +
      "without a gesture; auto-capture asks for `scripting` at opt-in instead",
  );
  assert.deepEqual([...(manifest.optional_permissions ?? [])].sort(), ["scripting"]);
});

test("no capture is reachable from an extension lifecycle event", () => {
  // Unchanged in intent. `onInstalled` now calls `syncAutoCapture`, which
  // *registers* rather than captures — so the assertion stays on `postCapture`
  // and on the auto path's own entry point, neither of which may sit in a
  // listener that fires without a human.
  const background = readFileSync(join(SRC, "background.js"), "utf8");

  const lifecycle = ["onInstalled", "onStartup", "onConnect"];
  for (const event of lifecycle) {
    const index = background.indexOf(event);
    if (index === -1) continue;
    const rest = background.slice(index);
    const body = rest.slice(0, rest.indexOf("\nchrome.") + 1 || rest.length);
    for (const door of ["postCapture", "captureTurn"]) {
      assert.ok(
        !body.includes(door),
        `capture reachable from ${event}, which fires without a human`,
      );
    }
  }
});

test("the auto path re-reads both gates before it reaches the door", () => {
  // A content script registered a moment ago can outlive a revoked permission
  // by one message. Trusting the arrival of the message is the shape that
  // turns a revoked grant into a capture nobody authorised.
  const background = readFileSync(join(SRC, "background.js"), "utf8");
  const start = background.indexOf("async function captureTurn");
  assert.ok(start !== -1, "the auto path must be its own named function");

  const body = background.slice(start, background.indexOf("\nchrome.", start));
  const gate = body.indexOf("readAutoCaptureState");
  const door = body.indexOf("postCapture");

  assert.ok(gate !== -1, "captureTurn must read the gates");
  assert.ok(body.includes("if (!state.active) return"), "and must refuse on either");
  assert.ok(gate < door, "and must do so before reaching the door");
});

/** Source with comments removed, so a scan reads the mechanism and not the
 *  prose explaining it. The observer's own docstring says why it must not hold
 *  the token, which a raw substring scan for "token" reads as it holding one. */
function code(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

test("the observer holds no credential and posts to no server", () => {
  // It shares an origin with the chat page's own scripts, which makes it the
  // last place in the extension that should hold the token.
  const observer = code(readFileSync(join(SRC, OBSERVER), "utf8"));

  for (const f of ["fetch(", "token", "postCapture", "XMLHttpRequest"]) {
    assert.ok(!observer.includes(f), `the observer reaches the network: ${f}`);
  }
});

test("no shipped source reaches an API through a computed name", () => {
  // `globalThis["set" + "Interval"]` passes a substring denylist. Computed
  // access to a global is the general shape, and nothing here needs it.
  const computed = /(globalThis|window|self|chrome)\s*\[/;
  for (const { file, text } of sources) {
    assert.ok(!computed.test(text), `${file} reaches a global by computed name`);
  }
});

test("every capture path begins at a user gesture or behind the gate", () => {
  const background = sources.find((s) => s.file === "background.js").text;
  const gestures = ["contextMenus.onClicked", "action.onClicked"];

  assert.ok(
    gestures.some((g) => background.includes(g)),
    "the selection capture must be entered from a user gesture",
  );

  // `postCapture` is still the only door call, and it must not appear in a
  // module a page could drive on its own.
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
  // select. That is still true with auto-capture shipped: the DOM knowledge
  // lives in the observer, which is gated, and not in a module the clicked
  // path also uses.
  const adapters = sources.find((s) => s.file === "adapters.js").text;
  for (const dom of ["document.", "window.", "querySelector", "innerText", "innerHTML"]) {
    assert.ok(!adapters.includes(dom), `adapters.js touches the DOM: ${dom}`);
  }
});

test("the observer seeds from the existing conversation rather than sending it", () => {
  // Source-level because the alternative is invisible: deleting the seeding
  // step leaves a file that still parses, still observes, and quietly sends
  // the whole conversation on the first mutation.
  const observer = code(readFileSync(join(SRC, OBSERVER), "utf8"));

  assert.ok(observer.includes("firstSweep("), "the opening sweep must be the shared one");
  assert.ok(
    observer.indexOf("firstSweep(") < observer.indexOf("new MutationObserver"),
    "and must run before anything is observed",
  );
});
