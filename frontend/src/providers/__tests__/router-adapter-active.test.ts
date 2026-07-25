import { describe, it, expect } from "vitest"
import { isNavHrefActive, splitNavHref } from "../router-adapter"

describe("splitNavHref", () => {
  it("passes through a plain path", () => {
    expect(splitNavHref("/memories")).toEqual({ to: "/memories" })
  })

  it("splits a query string into a search record", () => {
    expect(splitNavHref("/code?tab=graph")).toEqual({
      to: "/code",
      search: { tab: "graph" },
    })
  })

  it("keeps multiple params", () => {
    expect(splitNavHref("/code?tab=graph&repo=abc")).toEqual({
      to: "/code",
      search: { tab: "graph", repo: "abc" },
    })
  })
})

describe("isNavHrefActive", () => {
  it("matches '/' only exactly", () => {
    expect(isNavHrefActive("/", "/", {})).toBe(true)
    expect(isNavHrefActive("/", "/memories", {})).toBe(false)
  })

  it("matches a nav item on its own path", () => {
    expect(isNavHrefActive("/memories", "/memories", {})).toBe(true)
  })

  it("keeps the parent item active on a detail view", () => {
    expect(isNavHrefActive("/memories", "/memories/abc-123", {})).toBe(true)
    expect(
      isNavHrefActive("/knowledge/facts", "/knowledge/facts/f1", {}),
    ).toBe(true)
    expect(
      isNavHrefActive("/knowledge/articles", "/knowledge/articles/a1", {}),
    ).toBe(true)
  })

  it("keeps sibling dedicated pages independent", () => {
    expect(
      isNavHrefActive("/knowledge/facts", "/knowledge/articles/a1", {}),
    ).toBe(false)
    expect(isNavHrefActive("/code/graph", "/code/repositories", {})).toBe(false)
    expect(isNavHrefActive("/code/graph", "/code/graph", {})).toBe(true)
  })

  it("never matches a sibling path that shares a prefix", () => {
    expect(isNavHrefActive("/memories", "/memories-old", {})).toBe(false)
    expect(isNavHrefActive("/code/graph", "/code-graph", {})).toBe(false)
  })

  it("requires href query params to equal the current search", () => {
    expect(isNavHrefActive("/code?tab=graph", "/code", { tab: "graph" })).toBe(
      true,
    )
    expect(
      isNavHrefActive("/code?tab=graph", "/code", { tab: "repositories" }),
    ).toBe(false)
    expect(isNavHrefActive("/code?tab=graph", "/code", {})).toBe(false)
  })

  it("ignores extra current-search params the href does not name", () => {
    expect(
      isNavHrefActive("/code?tab=graph", "/code", {
        tab: "graph",
        repo: "abc",
      }),
    ).toBe(true)
  })
})
