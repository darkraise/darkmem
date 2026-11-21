import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

function chatPage() {
  const messages = [];
  const timers = new Map();
  let now = 0;
  let id = 1;
  let onMutation = null;
  const sent = [];
  const sandbox = {
    location: { hostname: "chatgpt.com", href: "https://chatgpt.com/c/1" },
    document: { title: "Chat", body: {}, querySelectorAll: () => [...messages] },
    MutationObserver: class {
      constructor(cb) {
        onMutation = cb;
      }
      observe() {}
      disconnect() {}
    },
    chrome: { runtime: { sendMessage: (m) => sent.push(m) } },
    window: { addEventListener() {} },
    setTimeout: (fn, ms) => {
      const t = id++;
      timers.set(t, { at: now + ms, fn });
      return t;
    },
    clearTimeout: (t) => timers.delete(t),
  };
  vm.runInNewContext(readFileSync(join(ROOT, "src/content-autocapture.js"), "utf8"), sandbox);
  return {
    sent,
    add(text) {
      const m = { innerText: text };
      messages.push(m);
      onMutation?.([]);
      return m;
    },
    set(m, text) {
      m.innerText = text;
      onMutation?.([]);
    },
    advance(ms) {
      const until = now + ms;
      for (;;) {
        const due = [...timers.entries()].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        timers.delete(due[0]);
        now = due[1].at;
        due[1].fn();
      }
      now = until;
    },
  };
}

test("A5: a reply that changes 30 times before settling produces one capture request", () => {
  const page = chatPage();
  const reply = page.add("w0");
  for (let i = 1; i <= 30; i++) {
    page.advance(500);
    page.set(reply, "w0" + " w".repeat(i));
  }
  assert.equal(page.sent.length, 0, "nothing is sent while the text keeps changing");
  page.advance(3000);
  assert.equal(page.sent.length, 1);
  assert.equal(page.sent[0].content, "w0" + " w".repeat(30));
  page.advance(60000);
  assert.equal(page.sent.length, 1, "once per message");
});
