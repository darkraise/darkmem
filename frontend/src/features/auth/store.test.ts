import { describe, it, expect, beforeEach } from "vitest"
import { useAuthStore } from "./store"

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, isAuthenticated: false })
  })

  it("sets token + isAuthenticated on login", () => {
    useAuthStore.getState().login("test-token")
    expect(useAuthStore.getState().token).toBe("test-token")
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })

  it("clears token + isAuthenticated on logout", () => {
    useAuthStore.getState().login("t")
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
