/**
 * T3.26 — the per-install origin key.
 *
 * `origin_key` is darkmem's corroboration-independence key: facts count
 * DISTINCT origins, never rows. So "stable across restarts" is not a comfort
 * property, it is the thing that stops one browser from corroborating a claim
 * with itself. These tests are written against that consequence rather than
 * against the storage call.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { ORIGIN_PREFIX, ORIGIN_STORAGE_KEY, getOriginKey } from "../src/origin.js";

/** The two `chrome.storage.local` methods this module uses, in memory. */
function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    writes: 0,
    async get(key) {
      return key in data ? { [key]: data[key] } : {};
    },
    async set(update) {
      this.writes += 1;
      Object.assign(data, update);
    },
  };
}

test("a key is minted on first use and carries the install prefix", async () => {
  const storage = fakeStorage();

  const key = await getOriginKey(storage, () => "fixed-id");

  assert.equal(key, `${ORIGIN_PREFIX}:fixed-id`);
  assert.equal(storage.data[ORIGIN_STORAGE_KEY], `${ORIGIN_PREFIX}:fixed-id`);
});

test("the key survives a restart — the same store yields the same key", async () => {
  const storage = fakeStorage();
  const first = await getOriginKey(storage, () => "one");

  // A restart is a fresh service worker over the same `storage.local`, so a
  // second call with a *different* minter must still return the stored key.
  // Passing a different minter is what makes this fail if the module ever
  // re-mints: an identical minter would return the same string either way.
  const second = await getOriginKey(storage, () => "two");

  assert.equal(second, first);
  assert.equal(storage.writes, 1);
});

test("a hundred reads mint exactly one key", async () => {
  const storage = fakeStorage();
  let minted = 0;

  for (let index = 0; index < 100; index += 1) {
    await getOriginKey(storage, () => `id-${(minted += 1)}`);
  }

  assert.equal(minted, 1);
  assert.equal(storage.writes, 1);
});

test("two concurrent wakeups settle on one key, not two", async () => {
  // MV3 wakes the service worker per event, so two events arriving together
  // can both find an empty store. Whichever writes second must adopt the
  // stored value rather than keep its own -- an install holding two keys
  // would count as two origins, which is the exact failure distinct-origin
  // counting exists to prevent.
  const storage = fakeStorage();
  let next = 0;
  const minter = () => `id-${(next += 1)}`;

  const [a, b] = await Promise.all([
    getOriginKey(storage, minter),
    getOriginKey(storage, minter),
  ]);

  assert.equal(a, b);
  assert.equal(storage.data[ORIGIN_STORAGE_KEY], a);
});

test("a stored key is returned verbatim, never re-prefixed", async () => {
  const storage = fakeStorage({ [ORIGIN_STORAGE_KEY]: "ext:already-minted" });

  assert.equal(await getOriginKey(storage), "ext:already-minted");
});
