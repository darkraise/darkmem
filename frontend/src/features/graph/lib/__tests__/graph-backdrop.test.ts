import { describe, it, expect, vi, afterEach } from "vitest"
import {
  attachBackdrop,
  coreOnScreen,
  nebulaGeometry,
  NEBULA_MIN_PX,
  NEBULA_SCALE,
} from "../graph-backdrop"

afterEach(() => vi.restoreAllMocks())

function fakeCtx() {
  const gradient = { addColorStop: vi.fn() }
  const fills: string[] = []
  const ctx = {
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    createRadialGradient: vi.fn(() => gradient),
    set fillStyle(v: string | object) {
      if (typeof v === "string") fills.push(v)
    },
  }
  return { ctx, gradient, fills }
}

function fakeHost() {
  const container = document.createElement("div")
  const sigmaLayer = document.createElement("canvas")
  container.appendChild(sigmaLayer)
  const handlers = new Set<() => void>()
  const camera = {
    on: vi.fn((_: "updated", fn: () => void) => handlers.add(fn)),
    off: vi.fn((_: "updated", fn: () => void) => handlers.delete(fn)),
  }
  return {
    container,
    sigmaLayer,
    handlers,
    camera,
    host: {
      getContainer: () => container,
      getCamera: () => camera,
      getDimensions: () => ({ width: 400, height: 300 }),
    },
  }
}

describe("nebulaGeometry", () => {
  it("centres on the core and spans NEBULA_SCALE times its on-screen radius", () => {
    expect(NEBULA_SCALE).toBe(2.2)
    expect(nebulaGeometry({ x: 120, y: 80 }, 100)).toEqual({ x: 120, y: 80, r: 220 })
  })

  it("keeps a visible glow when the core is tiny or absent", () => {
    expect(nebulaGeometry({ x: 0, y: 0 }, 0).r).toBe(NEBULA_MIN_PX)
  })
})

describe("coreOnScreen", () => {
  it("measures the core from the graph origin, where the runner centres it", () => {
    const host = {
      graphToViewport: (p: { x: number; y: number }) => ({ x: 200 + 2 * p.x, y: 150 - 2 * p.y }),
    }
    expect(coreOnScreen(host, 30)).toEqual({ centre: { x: 200, y: 150 }, radiusPx: 60 })
  })
})

describe("attachBackdrop", () => {
  it("puts one canvas beneath sigma's layers and paints the canvas colour, then the nebula", () => {
    const { ctx, gradient, fills } = fakeCtx()
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as never)
    const { container, sigmaLayer, host } = fakeHost()
    attachBackdrop(host, () => ({ centre: { x: 200, y: 150 }, radiusPx: 100 }), {
      canvas: "#0a0810",
      nebula: "#6a2bd1",
      isDark: true,
    })
    expect(container.firstElementChild).not.toBe(sigmaLayer)
    expect(container.querySelectorAll("canvas")).toHaveLength(2)
    expect(fills[0]).toBe("#0a0810")
    expect(ctx.createRadialGradient).toHaveBeenCalledWith(200, 150, 0, 200, 150, 220)
    expect(gradient.addColorStop).toHaveBeenCalled()
  })

  it("repaints when the camera moves and cleans up on detach", () => {
    const { ctx } = fakeCtx()
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as never)
    const { container, handlers, camera, host } = fakeHost()
    let r = 100
    const detach = attachBackdrop(host, () => ({ centre: { x: 0, y: 0 }, radiusPx: r }), {
      canvas: "#ffffff",
      nebula: "#ccbbff",
      isDark: false,
    })
    r = 200
    for (const fn of handlers) fn()
    expect(ctx.createRadialGradient).toHaveBeenLastCalledWith(0, 0, 0, 0, 0, 440)
    detach()
    expect(camera.off).toHaveBeenCalled()
    expect(container.querySelectorAll("canvas")).toHaveLength(1)
  })

  it("repaints at the new size when the container resizes", () => {
    const { ctx } = fakeCtx()
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as never)
    const { host } = fakeHost()
    let dims = { width: 300, height: 200 }
    let onResize: (() => void) | undefined
    const resizing = {
      ...host,
      getDimensions: () => dims,
      on: (_: "resize", fn: () => void) => (onResize = fn),
    }
    attachBackdrop(resizing, () => ({ centre: { x: 0, y: 0 }, radiusPx: 10 }), {
      canvas: "#000000",
      nebula: "#5533aa",
      isDark: true,
    })
    const canvas = host.getContainer().querySelector("canvas[aria-hidden]") as HTMLCanvasElement
    dims = { width: 640, height: 480 }
    onResize!()
    expect(canvas.style.width).toBe("640px")
    expect(canvas.style.height).toBe("480px")
  })

  it("does nothing harmful where 2D canvas is unavailable", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null)
    const { host } = fakeHost()
    expect(() =>
      attachBackdrop(host, () => ({ centre: { x: 0, y: 0 }, radiusPx: 0 }), {
        canvas: "#000000",
        nebula: "#000000",
        isDark: true,
      })(),
    ).not.toThrow()
  })
})

