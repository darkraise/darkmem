import { describe, it, expect, vi } from "vitest"
import { pendingTimerCount, clearPendingTimers } from "../pending-timers"

// Guards the harness itself. Without it a timer armed by a library — Redux
// Toolkit's notification fallback, reached through recharts — outlives its
// file, fires after vitest has deleted the jsdom globals, and reports an
// unhandled `cancelAnimationFrame is not defined` with every test passing.
describe("pending timer tracking", () => {
  it("counts a timer that is still armed", () => {
    const before = pendingTimerCount()
    setTimeout(() => {}, 60_000)
    expect(pendingTimerCount()).toBe(before + 1)
  })

  it("forgets a timer once it has fired", async () => {
    const before = pendingTimerCount()
    await new Promise<void>((resolve) => setTimeout(resolve, 1))
    expect(pendingTimerCount()).toBe(before)
  })

  it("forgets a timer that was cleared", () => {
    const before = pendingTimerCount()
    const id = setTimeout(() => {}, 60_000)
    clearTimeout(id)
    expect(pendingTimerCount()).toBe(before)
  })

  it("still runs the callback it wrapped, with its arguments", async () => {
    const seen = await new Promise<unknown[]>((resolve) => {
      setTimeout((...args: unknown[]) => resolve(args), 1, "a", 2)
    })
    expect(seen).toEqual(["a", 2])
  })

  it("cancels everything still armed", () => {
    const ran = vi.fn()
    setTimeout(ran, 1)
    setTimeout(ran, 2)
    expect(pendingTimerCount()).toBeGreaterThanOrEqual(2)
    clearPendingTimers()
    expect(pendingTimerCount()).toBe(0)
  })

  // Fake timers install their own globals; the tracker is simply out of the
  // path until they are restored, and must not break either mode.
  describe("under fake timers", () => {
    it("still runs a faked timer", () => {
      vi.useFakeTimers()
      try {
        const ran = vi.fn()
        setTimeout(ran, 500)
        vi.advanceTimersByTime(500)
        expect(ran).toHaveBeenCalled()
      } finally {
        vi.useRealTimers()
      }
    })

    it("is tracking again once real timers are back", () => {
      vi.useFakeTimers()
      vi.useRealTimers()
      const before = pendingTimerCount()
      setTimeout(() => {}, 60_000)
      expect(pendingTimerCount()).toBe(before + 1)
    })
  })
})

// The sweep itself is asserted above rather than from an `afterAll` here:
// vitest runs `afterAll` hooks in reverse registration order, so setup.ts's —
// registered first, when the setup file loaded — is the last to run, and a hook
// in this file could only ever observe the state *before* the sweep. The 60s
// timer the first test arms is left deliberately: it is what setup.ts's hook
// has to cancel on the way out of this file.
