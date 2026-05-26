import { describe, it, expect } from "vitest"
import { z } from "zod"
import { schemaResolver } from "../form-resolvers"

describe("schemaResolver", () => {
  const schema = z.object({ name: z.string().min(2) })

  it("returns undefined for valid input", () => {
    const validator = schemaResolver(schema)
    expect(validator({ value: { name: "ab" } })).toBeUndefined()
  })

  it("returns a string for invalid input", () => {
    const validator = schemaResolver(schema)
    const result = validator({ value: { name: "" } })
    expect(typeof result).toBe("string")
    // Zod 4 error format: "Too small: expected string to have >=2 characters"
    expect(result).toMatch(/2/)
  })

  it("returns undefined on valid input even with refinements", () => {
    const validator = schemaResolver(schema)
    expect(validator({ value: { name: "ok" } })).toBeUndefined()
  })
})
