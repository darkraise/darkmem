/**
 * T3.15 — the site adapters and the plain fallback.
 *
 * The done-when names four surfaces, but the property that matters is the
 * fallback: T3.26's shell works on any page with no adapter at all, and this
 * file must not have taken that away. So the tests are written so that a
 * broken adapter degrades to plain capture rather than to no capture.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { PLAIN, adapterFor, packageExchange, splitTurns } from "../src/adapters.js";

test("the three named surfaces are recognised", () => {
  assert.equal(adapterFor("https://chatgpt.com/c/abc"), "chatgpt");
  assert.equal(adapterFor("https://chat.openai.com/c/abc"), "chatgpt");
  assert.equal(adapterFor("https://claude.ai/chat/abc"), "claude");
  assert.equal(adapterFor("https://gemini.google.com/app/abc"), "gemini");
});

test("an unknown site falls back to plain capture, never to a refusal", () => {
  // The property T3.26 shipped and this task must not remove: no site adapter
  // is required for the shell to work.
  assert.equal(adapterFor("https://some-blog.example/post"), PLAIN);
  assert.equal(adapterFor("not a url"), PLAIN);
  assert.equal(adapterFor(undefined), PLAIN);
});

test("a lookalike host is not adopted as the real surface", () => {
  // `includes`-style matching would call these Claude. The adapter name is a
  // claim about where the content came from, so a near-miss must not inherit
  // it.
  assert.equal(adapterFor("https://claude.ai.evil.example/x"), PLAIN);
  assert.equal(adapterFor("https://notclaude.ai/x"), PLAIN);
  assert.equal(adapterFor("https://chatgpt.com.phish.example/x"), PLAIN);
});

test("a subdomain of a known surface is still that surface", () => {
  assert.equal(adapterFor("https://www.claude.ai/chat/1"), "claude");
});

test("turns are labelled where the surface marked them", () => {
  const turns = splitTurns("You: does it fsync?\nClaude: yes, on commit.");
  assert.deepEqual(turns, [
    { role: "user", text: "does it fsync?" },
    { role: "assistant", text: "yes, on commit." },
  ]);
});

test("an unmarked opening line is `unknown`, never guessed onto a speaker", () => {
  // Mislabelling is worse than not labelling: an assistant's claim attributed
  // to the human reads as the human's own assertion, and darkmem stores it as
  // one.
  const turns = splitTurns("postgres uses MVCC\nYou: since when?");
  assert.equal(turns[0].role, "unknown");
  assert.equal(turns[1].role, "user");
});

test("continuation lines stay with their turn", () => {
  const turns = splitTurns("Claude: first line\nsecond line\nthird");
  assert.equal(turns.length, 1);
  assert.equal(turns[0].text, "first line\nsecond line\nthird");
});

test("the captured content is the human's selection, unchanged", () => {
  // The adapter adds attribution, never content. Anything it derived rides as
  // metadata, because `content` is what darkmem extracts entities from.
  const selection = "You: does it fsync?\nClaude: yes, on commit.";
  const packaged = packageExchange({
    selection,
    pageUrl: "https://claude.ai/chat/1",
    pageTitle: "A chat",
  });

  assert.equal(packaged.content, selection);
  assert.equal(packaged.metadata.capture_surface, "claude");
  assert.deepEqual(packaged.metadata.turn_roles, ["user", "assistant"]);
});

test("the turn text is not duplicated into metadata", () => {
  // It is already in `content`; a second copy doubles what a later purge has
  // to reach.
  const packaged = packageExchange({
    selection: "You: secret-token-xyz",
    pageUrl: "https://claude.ai/chat/1",
  });
  assert.ok(!JSON.stringify(packaged.metadata).includes("secret-token-xyz"));
});

test("plain capture carries no turn labels at all", () => {
  const packaged = packageExchange({
    selection: "You: this is not a chat page",
    pageUrl: "https://some-blog.example/post",
  });
  assert.equal(packaged.metadata.capture_surface, PLAIN);
  assert.deepEqual(packaged.metadata.turn_roles, []);
});
