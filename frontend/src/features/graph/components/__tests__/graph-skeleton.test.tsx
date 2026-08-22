import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { GraphSkeleton } from "../graph-skeleton"

const source = () => {
  const here = path.dirname(fileURLToPath(import.meta.url))
  return readFileSync(path.resolve(here, "../graph-skeleton.tsx"), "utf8")
}

describe("GraphSkeleton", () => {
  it("names what is loading", () => {
    render(<GraphSkeleton />)
    expect(screen.getByRole("status")).toHaveTextContent("Loading graph")
  })

  it("takes a caller's label", () => {
    render(<GraphSkeleton label="Loading entities" />)
    expect(screen.getByRole("status")).toHaveTextContent("Loading entities")
  })

  // The regression: the previous version carried five hardcoded RGB triples
  // (168,85,247 / 63,185,80 / 88,166,255 / 255,166,87 / 6,182,212) matching
  // neither the theme tokens nor buildMemoryPalette, so it read as a
  // different product every time it appeared.
  it("carries no colour of its own", () => {
    const src = source()
    expect(src).not.toMatch(/rgba?\(/)
    expect(src).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    expect(src).not.toMatch(/\b\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\b/)
  })

  it("draws both node shapes the graph draws", () => {
    const { container } = render(<GraphSkeleton />)
    const nodes = Array.from(container.querySelectorAll<HTMLElement>(".dr-skeleton"))
    // Entities are diamonds and memories are discs; a placeholder showing only
    // circles promises a graph the page does not render.
    expect(nodes.some((n) => n.className.includes("rounded-full"))).toBe(true)
    expect(nodes.some((n) => n.style.transform.includes("rotate(45deg)"))).toBe(true)
  })

  it("uses the shared Skeleton primitive rather than a private one", () => {
    expect(source()).toMatch(/from "darkraise-ui\/components\/skeleton"/)
    const { container } = render(<GraphSkeleton />)
    expect(container.querySelectorAll(".dr-skeleton").length).toBeGreaterThan(10)
  })
})
