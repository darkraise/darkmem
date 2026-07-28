import { describe, it, expect } from "vitest"
import { reindexSchema, editRepoSchema } from "../schemas"

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
    const r = editRepoSchema.parse({ name: "x", path: "/p" })
    expect(r.branch).toBe("main")
  })
  it("has no sync_cron field (repo sync schedule is governed by the Jobs page)", () => {
    expect("sync_cron" in editRepoSchema.shape).toBe(false)
  })
})
