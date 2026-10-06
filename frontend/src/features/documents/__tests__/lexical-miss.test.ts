import { describe, expect, it } from "vitest"

import { noHitMentionsQuery, queryWords } from "../lexical-miss"

const hit = (text: string, heading_path: string[] = []) => ({
  text,
  heading_path,
})

describe("noHitMentionsQuery", () => {
  it("calls a nonsense query a miss even though it returned hits", () => {
    // The before-shot: "zzqqxxyy" answered twenty architecture sections.
    expect(
      noHitMentionsQuery("zzqqxxyy", [
        hit("Darkmem is a centralized memory system for AI agents."),
        hit("Capture", ["Architecture"]),
      ]),
    ).toBe(true)
  })

  it("is not a miss when any hit contains any query word, in any case", () => {
    expect(
      noHitMentionsQuery("zzqq Retrieval", [
        hit("nothing here"),
        hit("Hybrid retrieval fuses two arms."),
      ]),
    ).toBe(false)
  })

  it("counts a word that appears only in a hit's heading path", () => {
    expect(
      noHitMentionsQuery("jobs", [hit("buffer_flush | every 5s", ["Jobs"])]),
    ).toBe(false)
  })

  it("matches a plural query against a singular mention", () => {
    expect(noHitMentionsQuery("searches", [hit("one search arm")])).toBe(false)
    expect(noHitMentionsQuery("jobs", [hit("a job runs")])).toBe(false)
  })

  it("takes -es off only after a sibilant", () => {
    // "notes" stemmed to "not" would find "not" in nearly every section.
    expect(queryWords("notes boxes classes process")).toEqual([
      "note",
      "box",
      "class",
      "process",
    ])
  })

  it("does not let a stopword or a short word count as a mention", () => {
    expect(
      noHitMentionsQuery("the zzqqxxyy of", [hit("the thing of it")]),
    ).toBe(true)
  })

  it("never calls it a miss with no hits or nothing to test", () => {
    expect(noHitMentionsQuery("zzqqxxyy", [])).toBe(false)
    expect(noHitMentionsQuery("the a of", [hit("anything")])).toBe(false)
    expect(noHitMentionsQuery("", [hit("anything")])).toBe(false)
  })
})

describe("queryWords", () => {
  it("lowercases, dedupes and stems", () => {
    expect(queryWords("Jobs JOBS jobs schedule")).toEqual(["job", "schedule"])
  })
})
