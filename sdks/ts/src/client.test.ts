// T3.14 — the three verbs' behaviour on the wire (doc 15 §6).
//
// `fetch` is stubbed globally rather than injected: an injectable-transport
// option is client-platform surface, and doc 15 §6's stance is that this SDK is
// not one. The Python suite (`sdks/python/tests/`) asserts the same properties
// against the same generator, so a template edit that breaks one language
// without the other is caught rather than averaged.
//
// What no mock transport can tell you is whether the door on the other end
// honours any of this — see `backend/tests/test_sdk_contract_conformance.py`,
// which drives the real app with the shape emitted here. A review found this
// client declaring a context to doors that discarded it, with every test in
// this file green.
//
// Not typechecked by `make build`, deliberately: that target compiles the
// generated client alone, and pulling a test file in would need vitest's types
// resolvable from a package that installs no node_modules of its own.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Darkmem } from "./client";

const CAPTURE_PATH = "/api/v1/memories";
const SEARCH_PATH = "/api/v1/memories/search/paginated";
const CONTEXT_HEADER = "X-Darkmem-Context";

type Recorded = { url: string; body: Record<string, unknown>; headers: Record<string, string> };

let recorded: Recorded[];
const realFetch = globalThis.fetch;

function respond(payload: unknown = {}, status = 200, text = "") {
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
      text: async () => text,
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
    respond({ schema_version: 1, id: "abc", status: "accepted" });

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

  it("treats an empty project as a value, not an omission", async () => {
    // Nullish, not falsy — the Python client uses `is not None` for the same
    // reason, and a generated pair must not diverge here (review finding M-2).
    respond();

    await new Darkmem({ project: "darkmem" }).capture("one", { project: "" });

    expect(recorded[0].body.project).toBe("");
  });

  it("omits an argument the caller never passed rather than sending null", async () => {
    respond();

    await new Darkmem().capture("content only");

    expect(Object.keys(recorded[0].body)).toEqual(["content"]);
  });
});

describe("search", () => {
  it("posts the query to the bound read", async () => {
    respond({ items: [], total: 0, limit: 20, offset: 0, envelope: { context: null } });

    const result = await new Darkmem().search("what replaced redis");

    expect(recorded[0].url.endsWith(SEARCH_PATH)).toBe(true);
    expect(recorded[0].body).toEqual({ query: "what replaced redis", with_trace: true });
    expect(result.envelope?.context).toBeNull();
  });

  it("always asks for the trace, with no argument to turn it off", async () => {
    // Not a preference. The door resolves a declared context only on the
    // traced branch — an untraced search answers 200 with a null envelope and
    // discards the declaration on both ranks — so an option to turn the trace
    // off would be an option to silently drop the declaration, which is the
    // defect this binding exists to close.
    respond();
    const client = new Darkmem();
    client.declareContext({ env: "prod" });

    await client.search("q");

    expect(recorded[0].body.with_trace).toBe(true);
    expect(recorded[0].headers[CONTEXT_HEADER]).toBeDefined();
  });

  it("carries the limit in the body", async () => {
    respond();

    await new Darkmem().search("q", { limit: 5 });

    expect(recorded[0].body.limit).toBe(5);
  });
});

describe("declareContext", () => {
  it("sends no header when nothing is declared", async () => {
    respond();

    await new Darkmem().search("undeclared");

    expect(recorded[0].headers[CONTEXT_HEADER]).toBeUndefined();
  });

  it("treats an empty declaration as no declaration", async () => {
    // `{}` resolves to undeclared server-side, so a header carrying it says
    // nothing. `{}` is truthy in JavaScript and falsy in Python, which is
    // exactly how the two clients came to disagree (review finding M-1).
    respond();

    await new Darkmem({ context: {} }).search("q");

    expect(recorded[0].headers[CONTEXT_HEADER]).toBeUndefined();
  });

  it("rides the search door once declared", async () => {
    respond();
    const client = new Darkmem();

    client.declareContext({ env: "prod" });
    await client.search("q");

    expect(JSON.parse(recorded[0].headers[CONTEXT_HEADER])).toEqual({ env: "prod" });
  });

  it("never rides the capture door", async () => {
    // The capture door serves no context on either rank, so sending one would
    // be a value discarded in silence — the defect this task exists to close.
    respond();
    const client = new Darkmem({ context: { env: "prod" } });

    await client.capture("one");

    expect(recorded[0].headers[CONTEXT_HEADER]).toBeUndefined();
    expect(recorded[0].body.context).toBeUndefined();
  });

  it("puts a per-call context in the body at rank 1 and keeps the declaration at rank 2", async () => {
    respond();
    const client = new Darkmem({ context: { env: "dev" } });

    await client.search("q", { context: { env: "prod" } });

    expect(recorded[0].body.context).toEqual({ env: "prod" });
    expect(JSON.parse(recorded[0].headers[CONTEXT_HEADER])).toEqual({ env: "dev" });
  });

  it("can be withdrawn", async () => {
    respond();
    const client = new Darkmem({ context: { env: "prod" } });

    client.declareContext(null);
    await client.search("undeclared again");

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

  it("puts the door's own response in the failure", async () => {
    // A 422 names the field it rejected. Throwing the status alone leaves the
    // caller guessing at the most likely failure a minimal client has.
    respond({}, 422, '{"detail":[{"loc":["body","limit"],"msg":"too large"}]}');

    await expect(new Darkmem().search("q", { limit: 9999 })).rejects.toThrow("too large");
  });
});

describe("the surface, at run time", () => {
  // The escape hatch that would make ratification expressible is a reachable
  // transport. Two probes, because either alone has a blind spot a review drill
  // walked through: `private` is erased by the compiler and leaves the method
  // on the prototype, while a public class field (`send = async (...) => {}`)
  // is an *instance* property and never appears on the prototype at all.
  it("exposes exactly three methods on the prototype", () => {
    expect(Object.getOwnPropertyNames(Darkmem.prototype).sort()).toEqual([
      "capture",
      "constructor",
      "declareContext",
      "search",
    ]);
  });

  it("puts nothing at all on the instance", () => {
    // Every field is `#private`, so an instance has no own properties. Any
    // class-field method — the shape that defeated the source scan — shows up
    // here as one.
    expect(Object.getOwnPropertyNames(new Darkmem({}))).toEqual([]);
  });

  it("hangs nothing off the constructor", () => {
    // The third home a member can have, and the one that defeated both probes
    // above: a `static` method lives on the constructor, so it is neither a
    // prototype method nor an instance property. A review drove one to a real
    // ratify call with every suite green.
    expect(Object.getOwnPropertyNames(Darkmem).sort()).toEqual([
      "length",
      "name",
      "prototype",
    ]);
  });

  it("exports only the client and its types", async () => {
    // A module-level `export function send(...)` reaches any door and belongs
    // to no class, so neither probe above sees it. Types erase at run time, so
    // what remains is the value exports.
    const module = await import("./client");
    expect(Object.keys(module).sort()).toEqual(["Darkmem"]);
  });
});
