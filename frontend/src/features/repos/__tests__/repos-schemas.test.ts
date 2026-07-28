import { describe, it, expect } from "vitest"
import { cronExpressionSchema } from "../schemas"

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
