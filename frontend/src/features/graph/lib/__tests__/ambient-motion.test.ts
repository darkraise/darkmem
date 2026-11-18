import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  motionAllowed,
  startAmbientMotion,
  MOTION_FPS,
  MOTION_NODE_LIMIT,
} from "../ambient-motion"

let reduce = false
let mediaListener: ((e: { matches: boolean }) => void) | null = null
let visibility: DocumentVisibilityState = "visible"

beforeEach(() => {
  reduce = false
  mediaListener = null
  visibility = "visible"
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"],
  })
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: query.includes("reduce") ? reduce : false,
        media: query,
        onchange: null,
        addEventListener: (_: string, fn: (e: { matches: boolean }) => void) => {
          mediaListener = fn
        },
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as unknown as MediaQueryList,
  )
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => visibility })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe("motionAllowed", () => {
  it.each([
    [{ reducedMotion: false, nodeCount: 10, hidden: false }, true],
    [{ reducedMotion: true, nodeCount: 10, hidden: false }, false],
    [{ reducedMotion: false, nodeCount: 2000, hidden: false }, false],
    [{ reducedMotion: false, nodeCount: 1999, hidden: false }, true],
    [{ reducedMotion: false, nodeCount: 10, hidden: true }, false],
  ])("%o → %s", (env, expected) => {
    expect(motionAllowed(env)).toBe(expected)
  })

  it("caps at 2,000 nodes and 30 frames a second", () => {
    expect(MOTION_NODE_LIMIT).toBe(2000)
    expect(MOTION_FPS).toBe(30)
  })
})

describe("startAmbientMotion", () => {
  it("emits frames at no more than MOTION_FPS and stops when told", () => {
    const onFrame = vi.fn()
    const stop = startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBeGreaterThan(0)
    expect(onFrame.mock.calls.length).toBeLessThanOrEqual(MOTION_FPS)
    stop()
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("never starts under reduced motion", () => {
    reduce = true
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame).not.toHaveBeenCalled()
  })

  it("never starts at MOTION_NODE_LIMIT nodes", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: MOTION_NODE_LIMIT, onFrame })
    vi.advanceTimersByTime(1000)
    expect(onFrame).not.toHaveBeenCalled()
  })

  it("stops when the tab is hidden", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(200)
    visibility = "hidden"
    document.dispatchEvent(new Event("visibilitychange"))
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("stops when reduced motion turns on mid-run", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(200)
    reduce = true
    mediaListener?.({ matches: true })
    const n = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(n)
  })

  it("hands each frame the time alone, so a frame cannot move a node", () => {
    const onFrame = vi.fn()
    startAmbientMotion({ nodeCount: 100, onFrame })
    vi.advanceTimersByTime(500)
    expect(onFrame.mock.calls.length).toBeGreaterThan(0)
    for (const call of onFrame.mock.calls) {
      expect(call).toHaveLength(1)
      expect(typeof call[0]).toBe("number")
    }
    const times = onFrame.mock.calls.map((c) => c[0] as number)
    expect(times).toEqual([...times].sort((a, b) => a - b))
  })
})

