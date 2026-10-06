import { describe, it, expect, vi } from "vitest"
import { pendingTimerCount, clearPendingTimers } from "../pending-timers"

// Guards the harness itself. Without it a timer armed by a library — Redux
// Toolkit's notification fallback, reached through recharts — outlives its
// file, fires after vitest has deleted the DOM globals, and reports an
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

  // An interval is strictly worse than a leaked timeout left untracked: it
  // survives a sweep aimed only at timeouts and fires forever into the gap
  // between files instead of once.
  describe("interval tracking", () => {
    it("counts an interval that is still armed", () => {
      const before = pendingTimerCount()
      setInterval(() => {}, 60_000)
      expect(pendingTimerCount()).toBe(before + 1)
    })

    it("keeps counting an interval across multiple firings", async () => {
      const before = pendingTimerCount()
      let calls = 0
      const id = setInterval(() => {
        calls += 1
      }, 1)
      await new Promise<void>((resolve) => setTimeout(resolve, 10))
      clearInterval(id)
      expect(calls).toBeGreaterThan(1)
      expect(pendingTimerCount()).toBe(before)
    })

    it("forgets an interval that was cleared", () => {
      const before = pendingTimerCount()
      const id = setInterval(() => {}, 60_000)
      clearInterval(id)
      expect(pendingTimerCount()).toBe(before)
    })

    it("still runs the interval callback it wrapped, with its arguments", async () => {
      const seen = await new Promise<unknown[]>((resolve) => {
        const id = setInterval(
          (...args: unknown[]) => {
            clearInterval(id)
            resolve(args)
          },
          1,
          "a",
          2,
        )
      })
      expect(seen).toEqual(["a", 2])
    })

    it("cancels an interval still armed", () => {
      const ran = vi.fn()
      setInterval(ran, 1)
      expect(pendingTimerCount()).toBeGreaterThanOrEqual(1)
      clearPendingTimers()
      expect(pendingTimerCount()).toBe(0)
    })

    describe("under fake timers", () => {
      it("still runs a faked interval", () => {
        vi.useFakeTimers()
        try {
          const ran = vi.fn()
          const id = setInterval(ran, 500)
          vi.advanceTimersByTime(1500)
          expect(ran).toHaveBeenCalledTimes(3)
          clearInterval(id)
        } finally {
          vi.useRealTimers()
        }
      })

      // Deliberately left armed, uncleared, with nothing after it in the
      // file to sweep it: it is what setup.ts's afterAll hook has to cancel
      // on the way out, the interval counterpart to the timeout the timeout
      // suite's own last test above leaves (both survive only up to
      // "cancels an interval still armed", which sweeps whatever is pending
      // at that point -- this test runs after it, so nothing does).
      it("is tracking intervals again once real timers are back", () => {
        vi.useFakeTimers()
        vi.useRealTimers()
        const before = pendingTimerCount()
        setInterval(() => {}, 60_000)
        expect(pendingTimerCount()).toBe(before + 1)
      })
    })
  })
})

// The sweep itself is asserted above rather than from an `afterAll` here:
// vitest runs `afterAll` hooks in reverse registration order, so setup.ts's —
// registered first, when the setup file loaded — is the last to run, and a hook
// in this file could only ever observe the state *before* the sweep. The 60s
// interval the final test arms is left deliberately, with nothing left in the
// file to sweep it: it is what setup.ts's hook has to cancel on the way out.
