import assert from "node:assert/strict";
import { test } from "node:test";

test("options shows registration failure when both opt-in gates are open", async () => {
  const elements = Object.fromEntries(
    ["base", "token", "project", "origin", "save", "status", "autocapture", "autocapture-status"]
      .map((id) => [id, { value: "", textContent: "", checked: false, addEventListener() {} }]),
  );
  const messages = [];
  const stored = {
    "darkmem.auto_capture": true,
    "darkmem.origin_key": "ext:existing",
  };
  globalThis.document = { getElementById: (id) => elements[id] };
  globalThis.chrome = {
    storage: {
      local: {
        get: async () => stored,
        set: async (update) => { Object.assign(stored, update); },
      },
    },
    permissions: { contains: async () => true },
    runtime: {
      sendMessage: async (message) => {
        messages.push(message);
        return { enabled: true, granted: true, active: false };
      },
    },
  };

  try {
    await import("../src/options.js?registration-test");
    assert.deepEqual(messages, [{ type: "darkmem.auto_capture.sync" }]);
    assert.equal(elements.autocapture.checked, false);
    assert.match(elements["autocapture-status"].textContent, /off.*(?:failed|unavailable|not running)/i);
  } finally {
    delete globalThis.chrome;
    delete globalThis.document;
  }
});
