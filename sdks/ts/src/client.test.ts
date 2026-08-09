// T3.14 — the three verbs' behaviour on the wire (doc 15 §6).
//
// `fetch` is stubbed globally rather than injected: an injectable-transport
// option is client-platform surface, and doc 15 §6's stance is that this SDK is
// not one. The Python suite (`sdks/python/tests/`) asserts the same properties
// against the same generator, so a template edit that breaks one language
// without the other is caught rather than averaged.
//
// Not typechecked by `make build`, deliberately: that target compiles the
// generated client alone, and pulling a test file in would need vitest's types
// resolvable from a package that installs no node_modules of its own.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Darkmem } from "./client";

const CAPTURE_PATH = "/api/v1/memories";
const SEARCH_PATH = "/api/v1/knowledge/search";
const CONTEXT_HEADER = "X-Darkmem-Context";

type Recorded = { url: string; body: Record<string, unknown>; headers: Record<string, string> };

let recorded: Recorded[];
const realFetch = globalThis.fetch;

function respond(payload: unknown = {}, status = 200) {
  globalThis.fetch = vi.fn(async (url: string, init: RequestInit) => {
    recorded.push({
      url: String(url),
      body: JSON.parse(String(init.body)),
      headers: init.headers as Record<string, string>,
    });
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => payload,
    };
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  recorded = [];
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("capture", () => {
  it("posts the content to the capture door", async () => {
    respond({ schema_version: 1, id: "abc" });

    const ack = await new Darkmem({ baseUrl: "http://darkmem.test:8000" }).capture(
      "the tab is on live data",
    );

    expect(recorded[0].url).toBe(`http://darkmem.test:8000${CAPTURE_PATH}`);
    expect(recorded[0].body.content).toBe("the tab is on live data");
    expect(ack.id).toBe("abc");
  });

  it("takes the constructor project as the default and lets the argument win", async () => {
    respond();
    const client = new Darkmem({ project: "darkmem" });

    await client.capture("one");
    await client.capture("two", { project: "other" });

    expect(recorded[0].body.project).toBe("darkmem");
    expect(recorded[1].body.project).toBe("other");
  });

  it("omits an argument the caller never passed rather than sending null", async () => {
    respond();

    await new Darkmem().capture("content only");

    expect(Object.keys(recorded[0].body)).toEqual(["content"]);
  });

  it("throws on a failure status", async () => {
    respond({ detail: "nope" }, 422);

    await expect(new Darkmem().capture("rejected")).rejects.toThrow("422");
  });
});

describe("search", () => {
  it("posts the query to the composed read", async () => {
    respond({ rows: null, sections: {}, envelope: { fused: false } });

    const result = await new Darkmem().search("what replaced redis");

    expect(recorded[0].url.endsWith(SEARCH_PATH)).toBe(true);
    expect(recorded[0].body).toEqual({ query: "what replaced redis" });
    expect(result.envelope.fused).toBe(false);
  });

  it("maps `fused` to the contract's `fuse` field", async () => {
    respond({ rows: [], sections: null, envelope: { fused: true } });

    await new Darkmem().search("q", { fused: true, limit: 5 });

    expect(recorded[0].body).toEqual({ query: "q", fuse: true, limit: 5 });
  });

  it("sends an explicit `fused: false` rather than dropping it", async () => {
    // `false` is a value, not an omission — filtering on falsiness would make
    // an explicit choice indistinguishable from silence.
    respond({ rows: null, sections: {}, envelope: { fused: false } });

    await new Darkmem().search("q", { fused: false });

    expect(recorded[0].body).toEqual({ query: "q", fuse: false });
  });
});

describe("declareContext", () => {
  it("sends no header when nothing is declared", async () => {
    respond();

    await new Darkmem().capture("undeclared");

    expect(recorded[0].headers[CONTEXT_HEADER]).toBeUndefined();
  });

  it("rides every later call once declared", async () => {
    respond();
    const client = new Darkmem();

    client.declareContext({ env: "prod" });
    await client.capture("one");
    await client.search("two");

    for (const call of recorded) {
      expect(JSON.parse(call.headers[CONTEXT_HEADER])).toEqual({ env: "prod" });
    }
  });

  it("lets a per-call context win over the declaration", async () => {
    respond();
    const client = new Darkmem({ context: { env: "dev" } });

    await client.capture("one", { context: { env: "prod" } });

    expect(JSON.parse(recorded[0].headers[CONTEXT_HEADER])).toEqual({ env: "prod" });
  });

  it("carries the context in the header and never as a body field", async () => {
    // An earlier draft of the generated client posted `applies_when`, a key no
    // request schema in the contract has, so every declaration was dropped by
    // the door with nothing said.
    respond();
    const client = new Darkmem();
    client.declareContext({ env: "prod" });

    await client.search("q");

    expect(Object.keys(recorded[0].body)).toEqual(["query"]);
    expect(recorded[0].headers[CONTEXT_HEADER]).toBeDefined();
  });

  it("can be withdrawn", async () => {
    respond();
    const client = new Darkmem({ context: { env: "prod" } });

    client.declareContext(null);
    await client.capture("undeclared again");

    expect(recorded[0].headers[CONTEXT_HEADER]).toBeUndefined();
  });
});

describe("transport", () => {
  it("turns the token into a bearer header", async () => {
    respond();

    await new Darkmem({ token: "jwt-value" }).capture("authenticated");

    expect(recorded[0].headers["Authorization"]).toBe("Bearer jwt-value");
  });

  it("does not double a trailing slash on the base url", async () => {
    respond();

    await new Darkmem({ baseUrl: "http://darkmem.test:8000/" }).capture("x");

    expect(recorded[0].url).toBe(`http://darkmem.test:8000${CAPTURE_PATH}`);
  });

  it("exposes no fourth method at run time", async () => {
    // The escape hatch that would make ratification expressible is a reachable
    // transport, and `private` does not close it: TypeScript erases the
    // modifier and leaves the method on the prototype. `#post` does not exist
    // at run time, so there is nothing to call with an arbitrary path.
    expect(Object.getOwnPropertyNames(Darkmem.prototype).sort()).toEqual([
      "capture",
      "constructor",
      "declareContext",
      "search",
    ]);
  });
});
