import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { TAB_VALUES } from "../settings"

describe("Settings tab registry", () => {
  // A trigger whose value is missing here renders, but the route drops both
  // the click and ?tab=<value>, so the tab can never be opened.
  it("registers every tab the page renders", () => {
    const source = readFileSync(
      join(process.cwd(), "src/routes/_authenticated/settings.tsx"),
      "utf8",
    )
    const rendered = [...source.matchAll(/<TabsTrigger[^>]*value="([^"]+)"/g)]
      .map((m) => m[1])
      .sort()
    expect([...TAB_VALUES].sort()).toEqual(rendered)
    expect(TAB_VALUES).toHaveLength(10)
  })
})
