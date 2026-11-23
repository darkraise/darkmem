// T3.14 — the two verbs' behaviour on the wire (doc 15 §6).
//
// `fetch` is stubbed globally rather than injected: an injectable-transport
// option is client-platform surface, and doc 15 §6's stance is that this SDK is
// not one. The Python suite (`sdks/python/tests/`) asserts the same properties
// against the same generator, so a template edit that breaks one language
// without the other is caught rather than averaged.
//
// What no mock transport can tell you is whether the door on the other end
// honours any of this — see `backend/tests/test_sdk_contract_conformance.py`,
// which drives the real app with the shape emitted here.
//
// Not typechecked by `make build`, deliberately: that target compiles the
// generated client alone, and pulling a test file in would need vitest's types
// resolvable from a package that installs no node_modules of its own.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Darkmem } from "./client";

const CAPTURE_PATH = "/api/v1/memories";
const SEARCH_PATH = "/api/v1/memories/search/paginated";

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
    respond({ items: [], total: 0, limit: 20, offset: 0, envelope: { channels: {} } });

    const result = await new Darkmem().search("what replaced redis");

    expect(recorded[0].url.endsWith(SEARCH_PATH)).toBe(true);
    expect(recorded[0].body).toEqual({ query: "what replaced redis", with_trace: true });
    expect(result.envelope).toEqual({ channels: {} });
  });

  it("always asks for the trace, with no argument to turn it off", async () => {
    // Doc 15 §6 defines the verb as returning the labelled results with their
    // trace.
    respond();

    await new Darkmem().search("q");

    expect(recorded[0].body.with_trace).toBe(true);
  });

  it("carries the limit in the body", async () => {
    respond();

    await new Darkmem().search("q", { limit: 5 });

    expect(recorded[0].body.limit).toBe(5);
  });
});

describe("no declared context", () => {
  it("sends neither the old header nor a context body key", async () => {
    // Declared context is gone from both doors, so neither verb sends it.
    respond();
    const client = new Darkmem();

    await client.search("q");
    await client.capture("one");

    for (const request of recorded) {
      expect(Object.keys(request.headers).map((h) => h.toLowerCase())).not.toContain(
        "x-darkmem-context",
      );
      expect(request.body.context).toBeUndefined();
    }
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
  // transport, and a member has three homes and two key kinds. Each
  // combination has hidden a drilled fourth verb at least once:
  //
  //   prototype   — `private post()`; the modifier is erased at compile time
  //   instance    — `send = async (...) => {}`, a class field, never on the prototype
  //   constructor — `static async send(...)`, on neither of the two above
  //   symbol key  — `[Symbol.for("send")]()`, which `Object.getOwnPropertyNames`
  //                 enumerates in *none* of the three, so one construct was
  //                 invisible to all three probes at once
  //
  // `Reflect.ownKeys` is names and symbols together, which is why every probe
  // below reads it rather than `getOwnPropertyNames`.
  const ownKeys = (target: object) =>
    Reflect.ownKeys(target)
      .map((key) => (typeof key === "symbol" ? key.toString() : key))
      .sort();

  it("exposes exactly two methods on the prototype", () => {
    expect(ownKeys(Darkmem.prototype)).toEqual([
      "capture",
      "constructor",
      "search",
    ]);
  });

  it("puts nothing at all on the instance", () => {
    // Every field is `#private`, so an instance has no own keys of any kind.
    //
    // NOT total, and reading it as total is what let escape 8 through on the
    // fourth reopening of this finding (2026-08-10): this constructs one
    // client, with default options, so a member attached only when
    // `options.baseUrl` is set — i.e. in every real deployment — has no own
    // key *here* and a working transport everywhere else. The total check is
    // a source walk over assignment targets that mention `this`, in
    // backend/tests/test_sdk_generator.py::TestNoMemberCanBeAttachedConditionally.
    expect(ownKeys(new Darkmem({}))).toEqual([]);
  });

  it("hangs nothing off the constructor", () => {
    expect(ownKeys(Darkmem)).toEqual(["length", "name", "prototype"]);
  });

  it("exports only the client and its types", async () => {
    // A module-level `export function send(...)` reaches any door and belongs
    // to no class, so neither probe above sees it. Types erase at run time, so
    // what remains is the value exports.
    const module = await import("./client");
    expect(Object.keys(module).sort()).toEqual(["Darkmem"]);
  });
});
