import "@testing-library/jest-dom/vitest"
import { vi, beforeAll, afterEach } from "vitest"

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
})

afterEach(() => {
  vi.clearAllMocks()
})
