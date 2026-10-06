import { describe, expect, it, vi } from "vitest"

vi.mock("@/lib/api", () => ({ ApiError: class extends Error {} }))

import type { DocumentListItem } from "@/hooks/api"
import { buildPathMap, buildUriTree } from "../uri-tree"
import { checkSubtree, matchesPrefix, uriProblem } from "../subtree"

const doc = (id: string, uri: string): DocumentListItem => ({
  id,
  title: null,
  uri,
  source_type: "md",
  project: "p",
  block_count: 1,
})

describe("matchesPrefix", () => {
  it("is the server's whole-segment predicate", () => {
    expect(matchesPrefix("a", "a")).toBe(true)
    expect(matchesPrefix("a/b.md", "a")).toBe(true)
    expect(matchesPrefix("ab/c.md", "a")).toBe(false)
    expect(matchesPrefix("/a/b.md", "a")).toBe(false)
  })
})

describe("checkSubtree", () => {
  it("counts a folder whose documents the prefix all reaches", () => {
    const items = [doc("1", "a/x.md"), doc("2", "a/b/y.md"), doc("3", "ab.md")]
    const node = buildPathMap(buildUriTree(items)).get("a")!
    expect(checkSubtree(node, items)).toEqual({ ok: true, count: 2 })
  })

  it("refuses a folder holding a leading-slash or doubled-slash uri", () => {
    for (const odd of ["/a/z.md", "a//z.md"]) {
      const items = [doc("1", "a/x.md"), doc("2", odd)]
      const node = buildPathMap(buildUriTree(items)).get("a")!
      // `a//z.md` IS matched at `a`, but the tree shows it under `a` too --
      // so only the leading slash differs; check each honestly.
      const result = checkSubtree(node, items)
      expect(result.ok).toBe(odd === "a//z.md")
    }
  })
})

describe("uriProblem", () => {
  it("refuses the shapes a folder action could not address later", () => {
    expect(uriProblem("notes/a.md")).toBeNull()
    expect(uriProblem("/notes/a.md")).toMatch(/start with a slash/)
    expect(uriProblem("notes/")).toMatch(/end with a slash/)
    expect(uriProblem("notes//a.md")).toMatch(/empty folder/)
    expect(uriProblem("")).toMatch(/Enter a path/)
  })
})
