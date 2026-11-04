import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const css = readFileSync(join(process.cwd(), "src/styles/globals.css"), "utf8")
const shell = readFileSync(
  join(process.cwd(), "src/routes/_authenticated.tsx"),
  "utf8",
)

function rule(selectorStart: string): string {
  const at = css.indexOf(selectorStart)
  expect(at, `no rule starting ${selectorStart}`).toBeGreaterThan(-1)
  return css.slice(at, css.indexOf("}", at))
}

describe("sidebar styling", () => {
  it("tints the active item and leaves the library's ring and rail alone", () => {
    const active = rule(
      ".dr-sidebar-nav\n  .dr-sidebar-nav-item:is(.dr-sidebar-nav-current",
    )
    expect(active).not.toContain("box-shadow")
    expect(active).toContain("background-color: hsl(var(--primary) / 0.1)")
    expect(active).toContain("color: var(--primary-text)")
  })

  it("pins the active indicator to the pill", () => {
    expect(shell).toMatch(/selection="pill"/)
  })

  it("gives the search box the ordinary border until it has focus", () => {
    const search = rule(".dr-sidebar-layout-search .dr-search-command-trigger:not(:focus-visible)")
    expect(search).toContain("border-color: hsl(var(--border))")
  })
})
