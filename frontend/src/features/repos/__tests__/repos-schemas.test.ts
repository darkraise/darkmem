import { describe, it, expect } from "vitest"
import { cronExpressionSchema, reindexSchema, editRepoSchema } from "../schemas"

describe("cronExpressionSchema", () => {
  it("accepts 5-field expressions", () => {
    expect(cronExpressionSchema.safeParse("0 */6 * * *").success).toBe(true)
  })
  it("accepts 6-field (Quartz-style) expressions", () => {
    expect(cronExpressionSchema.safeParse("0 0 */6 * * *").success).toBe(true)
  })
  it("rejects bare strings", () => {
    expect(cronExpressionSchema.safeParse("every 6 hours").success).toBe(false)
  })
})

describe("reindexSchema", () => {
  it("requires at least one action", () => {
    const r = reindexSchema.safeParse({
      full: false,
      enrich_symbols: false,
      generate_wiki: false,
    })
    expect(r.success).toBe(false)
  })
  it("accepts a single action", () => {
    expect(
      reindexSchema.safeParse({
        full: false,
        enrich_symbols: true,
        generate_wiki: false,
      }).success,
    ).toBe(true)
  })
})

describe("editRepoSchema", () => {
  it("defaults branch to main", () => {
    const r = editRepoSchema.parse({
      name: "x",
      path: "/p",
      sync_cron: "0 0 * * *",
    })
    expect(r.branch).toBe("main")
  })
})
