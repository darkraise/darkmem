import { describe, it, expect } from "vitest"
import { parseCommandPaletteQuery } from "../components/memory-command-palette"

describe("parseCommandPaletteQuery", () => {
  it("plain string → query, no facets", () => {
    expect(parseCommandPaletteQuery("postgres tuning")).toEqual({
      query: "postgres tuning",
      sources: [],
      types: [],
      tags: [],
      technologies: [],
    })
  })

  it("recognises source:X prefixes", () => {
    expect(parseCommandPaletteQuery("source:claude-code postgres")).toEqual({
      query: "postgres",
      sources: ["claude-code"],
      types: [],
      tags: [],
      technologies: [],
    })
  })

  it("recognises tag:X and tech:Y together", () => {
    expect(parseCommandPaletteQuery("tag:python tech:fastapi auth")).toEqual({
      query: "auth",
      sources: [],
      types: [],
      tags: ["python"],
      technologies: ["fastapi"],
    })
  })

  it("recognises type:decision", () => {
    expect(parseCommandPaletteQuery("type:decision")).toEqual({
      query: "",
      sources: [],
      types: ["decision"],
      tags: [],
      technologies: [],
    })
  })
})
