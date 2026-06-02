import { describe, it, expect } from "vitest"

import { findEntityMatches } from "../lib/entity-match"

const ents = (...names: string[]) => names.map((name, i) => ({ name, id: String(i) }))

describe("findEntityMatches", () => {
  it("does not match an entity name inside a larger word", () => {
    expect(findEntityMatches("this is the capital city", ents("api"))).toEqual([])
    expect(findEntityMatches("a category list", ents("cat"))).toEqual([])
    expect(findEntityMatches("concatenate the values", ents("cat"))).toEqual([])
  })

  it("matches an entity name on word boundaries", () => {
    const m = findEntityMatches("the api works", ents("api"))
    expect(m).toHaveLength(1)
    expect(m[0]!.start).toBe(4)
    expect(m[0]!.end).toBe(7)
  })

  it("matches at the start and end of the text", () => {
    expect(findEntityMatches("api first", ents("api"))).toHaveLength(1)
    expect(findEntityMatches("use api", ents("api"))).toHaveLength(1)
  })

  it("matches multi-word and hyphenated names", () => {
    expect(findEntityMatches("we use darkraise-ui here", ents("darkraise-ui"))).toHaveLength(1)
    expect(findEntityMatches("github actions runs it", ents("github actions"))).toHaveLength(1)
  })

  it("returns matches sorted by start and dedupes repeated names", () => {
    const m = findEntityMatches("redis then valkey", ents("valkey", "redis"))
    expect(m.map((x) => x.name)).toEqual(["redis", "valkey"])
  })
})
