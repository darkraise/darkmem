/**
 * T3.15 — dedup by content fingerprint and per-install `origin_key`.
 *
 * What a duplicate actually costs is worth stating, because it shapes the
 * tests: this install is **one** origin, so a duplicate capture can never
 * manufacture corroboration. What it does is inflate the corpus and hand
 * retrieval two rows where the vault holds one claim. So these tests care
 * about suppression being *reliable* and *scoped*, not about it being a
 * safety property it is not.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  SEEN_LIMIT,
  SEEN_STORAGE_PREFIX,
  alreadyCaptured,
  fingerprint,
  remember,
} from "../src/dedupe.js";

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    async get(key) {
      return key in data ? { [key]: data[key] } : {};
    },
    async set(update) {
      Object.assign(data, update);
    },
  };
}

test("the same passage fingerprints the same across selections", async () => {
  // Re-selecting rarely reproduces the same edges or wrapping, so a
  // fingerprint sensitive to them would suppress nothing.
  const a = await fingerprint("postgres uses MVCC");
  const b = await fingerprint("  postgres   uses\nMVCC  ");
  assert.equal(a, b);
});

test("case is content — two passages differing only in case are two", async () => {
  const a = await fingerprint("Postgres uses MVCC");
  const b = await fingerprint("postgres uses mvcc");
  assert.notEqual(a, b);
});

test("a second capture of the same content is recognised", async () => {
  const storage = fakeStorage();
  const digest = await fingerprint("the same passage");

  assert.equal(await alreadyCaptured(storage, "ext:1", digest), false);
  await remember(storage, "ext:1", digest);
  assert.equal(await alreadyCaptured(storage, "ext:1", digest), true);
});

test("the set is scoped per install key", async () => {
  // Two profiles on one machine must not suppress each other's captures, and
  // clearing an install's identity clears its history with it rather than
  // leaving a set that silently refuses new captures.
  const storage = fakeStorage();
  const digest = await fingerprint("shared text");

  await remember(storage, "ext:1", digest);

  assert.equal(await alreadyCaptured(storage, "ext:2", digest), false);
  assert.ok(Object.keys(storage.data).every((k) => k.startsWith(SEEN_STORAGE_PREFIX)));
});

test("the set stores hashes, never the captured text", async () => {
  // It lives unencrypted in storage.local; a local cache of everything the
  // human ever clipped is a liability the feature does not need to create.
  const storage = fakeStorage();
  await remember(storage, "ext:1", await fingerprint("secret-token-xyz"));

  assert.ok(!JSON.stringify(storage.data).includes("secret-token-xyz"));
});

test("the set is bounded and forgets the oldest first", async () => {
  // A random eviction would make suppression non-deterministic; oldest-first
  // keeps the recent window, which is where accidental re-capture happens.
  const storage = fakeStorage();
  const digests = [];
  for (let i = 0; i < SEEN_LIMIT + 10; i += 1) {
    const d = await fingerprint(`passage ${i}`);
    digests.push(d);
    await remember(storage, "ext:1", d);
  }

  assert.equal(await alreadyCaptured(storage, "ext:1", digests[0]), false);
  assert.equal(await alreadyCaptured(storage, "ext:1", digests.at(-1)), true);
  assert.equal(storage.data[`${SEEN_STORAGE_PREFIX}ext:1`].length, SEEN_LIMIT);
});

test("two concurrent captures both survive", async () => {
  // MV3 wakes the worker per event, so a plain read-modify-write drops one.
  // `origin.js` already settles this way; this is the same idiom.
  const storage = fakeStorage();
  const [a, b] = [await fingerprint("first"), await fingerprint("second")];

  await Promise.all([remember(storage, "ext:1", a), remember(storage, "ext:1", b)]);

  assert.equal(await alreadyCaptured(storage, "ext:1", a), true);
  assert.equal(await alreadyCaptured(storage, "ext:1", b), true);
});

test("remembering the same digest twice does not grow the set", async () => {
  const storage = fakeStorage();
  const digest = await fingerprint("once");

  await remember(storage, "ext:1", digest);
  const after = await remember(storage, "ext:1", digest);

  assert.equal(after.length, 1);
});
