import { describe, it, expect, beforeEach } from "vitest"
import { useAuthStore } from "./store"

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ isAuthenticated: false })
  })

  it("sets isAuthenticated on setAuthenticated(true)", () => {
    useAuthStore.getState().setAuthenticated(true)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })

  it("clears isAuthenticated on logout", () => {
    useAuthStore.getState().setAuthenticated(true)
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
