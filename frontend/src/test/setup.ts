import "@testing-library/jest-dom/vitest"
import { vi, beforeAll, afterAll, afterEach } from "vitest"
import { trackTimers, clearPendingTimers } from "./pending-timers"

// Before any hook, so a timer armed at import time is tracked too. See
// `pending-timers.ts` for what fires into the gap between two files.
trackTimers()

// Node 25's experimental localStorage (a bare object with no Storage
// methods) shadows jsdom's implementation in the vitest environment.
// Installed at module level so import-time side effects see it too.
const localStorageStore = new Map<string, string>()
Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: {
    getItem: (key: string) => localStorageStore.get(key) ?? null,
    setItem: (key: string, value: string) => {
      localStorageStore.set(key, String(value))
    },
    removeItem: (key: string) => {
      localStorageStore.delete(key)
    },
    clear: () => localStorageStore.clear(),
    key: (index: number) => [...localStorageStore.keys()][index] ?? null,
    get length() {
      return localStorageStore.size
    },
  },
})

// jsdom provides none of these; the atmospheric backdrop needs all three.
beforeAll(() => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))

  const ctxStub = {
    setTransform: vi.fn(),
    scale: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    strokeStyle: "",
    fillStyle: "",
    lineWidth: 1,
    shadowColor: "",
    shadowBlur: 0,
  }
  HTMLCanvasElement.prototype.getContext = vi.fn(
    () => ctxStub,
  ) as unknown as typeof HTMLCanvasElement.prototype.getContext

  // Deterministic, non-recursive rAF: record the call, never invoke the
  // callback (so the draw loop schedules exactly once and never spins).
  window.requestAnimationFrame = vi.fn(() => 1)
  window.cancelAnimationFrame = vi.fn()

  // jsdom ships no ResizeObserver and lays nothing out, so every rect is
  // 0×0. @tanstack/react-virtual refuses to compute a range for a
  // zero-height scroll container, which would leave every virtualized list
  // rendering nothing at all under test. Give elements a viewport-sized box.
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver

  // jsdom ships no scrollIntoView (T1.60) — ChatMessages calls it in an
  // effect on every render, which throws under jsdom without this stub.
  Element.prototype.scrollIntoView = vi.fn()

  // react-virtual sizes its scroll container from offsetWidth/offsetHeight.
  for (const [prop, value] of [
    ["offsetWidth", 1024],
    ["offsetHeight", 768],
  ] as const) {
    Object.defineProperty(HTMLElement.prototype, prop, {
      configurable: true,
      value,
    })
  }

  Element.prototype.getBoundingClientRect = function (): DOMRect {
    return {
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 1024,
      bottom: 768,
      width: 1024,
      height: 768,
      toJSON: () => ({}),
    } as DOMRect
  }
})

afterEach(() => {
  vi.clearAllMocks()
})

// Every test in this file has finished, so nothing is waiting on whatever is
// still armed — and vitest is about to delete the globals those callbacks read.
afterAll(() => {
  clearPendingTimers()
})
