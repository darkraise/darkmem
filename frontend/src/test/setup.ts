import { vi, beforeAll, afterEach } from "vitest"

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
