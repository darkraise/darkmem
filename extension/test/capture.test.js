/**
 * T3.26 — the capture call, and the done-when that it needs no site adapter.
 *
 * The shell's whole claim is that a human selecting text on *any* page can
 * file it. So the tests below never describe a site: the input is a string
 * and a URL, which is all the shell is allowed to require.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  CAPTURE_PATH,
  CaptureRefused,
  MAX_SELECTION_CHARS,
  SOURCE,
  buildCapture,
  postCapture,
} from "../src/capture.js";

const BASE = "http://localhost:8000";

function ok(status = 202, body = { id: "mem-1", status: "accepted" }) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return { status, json: async () => body };
  };
  return { calls, fetchImpl };
}

test("a plain selection from an unknown site captures with no adapter", async () => {
  const { calls, fetchImpl } = ok();
  const body = buildCapture({
    selection: "  postgres uses MVCC  ",
    pageUrl: "https://some-site-nobody-wrote-an-adapter-for.example/post",
    pageTitle: "A post",
    originKey: "ext:abc",
    project: "notes",
  });

  await postCapture(fetchImpl, BASE, body, { token: "t" });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${BASE}${CAPTURE_PATH}`);
  const sent = JSON.parse(calls[0].init.body);
  assert.equal(sent.content, "postgres uses MVCC");
  assert.equal(sent.project, "notes");
});

test("it posts to the ordinary capture door, not an extension-only one", async () => {
  // A second capture path would have to be kept in step with buffering,
  // source resolution and the ack contract forever. This pins the door.
  assert.equal(CAPTURE_PATH, "/api/v1/memories");
});

test("the page's chrome rides as metadata, never folded into the content", async () => {
  // `content` is what darkmem extracts entities from, so prepending the site
  // title would mint entities for the page's navigation furniture.
  const body = buildCapture({
    selection: "the claim",
    pageUrl: "https://example.test/a",
    pageTitle: "Example — Home | Sign in",
    originKey: "ext:abc",
  });

  assert.equal(body.content, "the claim");
  assert.equal(body.metadata.page_title, "Example — Home | Sign in");
  assert.equal(body.metadata.page_url, "https://example.test/a");
});

test("the origin key rides on the capture", async () => {
  const body = buildCapture({
    selection: "x",
    originKey: "ext:install-1",
  });
  assert.equal(body.origin_key, "ext:install-1");
  assert.equal(body.source, SOURCE);
});

test("an empty or whitespace-only selection is refused before any request", async () => {
  const { calls, fetchImpl } = ok();

  for (const selection of ["", "   ", "\n\t ", undefined]) {
    assert.throws(() => buildCapture({ selection, originKey: "ext:a" }), CaptureRefused);
  }

  assert.equal(calls.length, 0, "nothing may reach the door");
  void fetchImpl;
});

test("an oversized selection is refused with its size named", () => {
  assert.throws(
    () =>
      buildCapture({
        selection: "x".repeat(MAX_SELECTION_CHARS + 1),
        originKey: "ext:a",
      }),
    (error) =>
      error instanceof CaptureRefused && error.message.includes(String(MAX_SELECTION_CHARS)),
  );
});

test("202 is success — the capture doors buffer and ack", async () => {
  const { fetchImpl } = ok(202, { id: "pre-minted" });
  const ack = await postCapture(fetchImpl, BASE, buildCapture({
    selection: "x", originKey: "ext:a",
  }));
  assert.equal(ack.id, "pre-minted");
});

test("a non-2xx answer is a refusal, not a silent success", async () => {
  // The failure this forbids: reporting "captured" for a selection the server
  // never filed. The human has navigated away by the time anything else could
  // tell them.
  const { fetchImpl } = ok(500, {});
  await assert.rejects(
    () => postCapture(fetchImpl, BASE, buildCapture({ selection: "x", originKey: "ext:a" })),
    CaptureRefused,
  );
});

test("the client names itself to the server's source resolution", async () => {
  const { calls, fetchImpl } = ok();
  await postCapture(fetchImpl, BASE, buildCapture({ selection: "x", originKey: "ext:a" }));

  assert.equal(calls[0].init.headers["X-Darkmem-Client"], SOURCE);
});

test("no Authorization header is sent when no token is configured", async () => {
  // An empty Bearer is not the same as absent: it is a credential the server
  // must parse and reject, and it would make an unconfigured install look
  // like a failed login in the auth audit.
  const { calls, fetchImpl } = ok();
  await postCapture(fetchImpl, BASE, buildCapture({ selection: "x", originKey: "ext:a" }));

  assert.equal("Authorization" in calls[0].init.headers, false);
});
