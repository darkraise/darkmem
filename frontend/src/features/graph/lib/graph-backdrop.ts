import type { Point } from "./constellation-layout"
import { hexToRgba } from "./graph-colors"

export const NEBULA_SCALE = 2.2
export const NEBULA_MIN_PX = 120
export const WEBGL_UNAVAILABLE_MESSAGE =
  "The graph needs WebGL, which this browser has turned off."

export interface BackdropHost {
  getContainer(): HTMLElement
  getCamera(): {
    on(event: "updated", fn: () => void): unknown
    off(event: "updated", fn: () => void): unknown
  }
  getDimensions(): { width: number; height: number }
}

export function nebulaGeometry(
  centre: Point,
  radiusPx: number,
): { x: number; y: number; r: number } {
  const r = Math.round(NEBULA_SCALE * radiusPx * 1000) / 1000
  return { x: centre.x, y: centre.y, r: Math.max(NEBULA_MIN_PX, r) }
}

export function coreOnScreen(
  host: { graphToViewport(p: Point): Point },
  R: number,
): { centre: Point; radiusPx: number } {
  const centre = host.graphToViewport({ x: 0, y: 0 })
  const edge = host.graphToViewport({ x: R, y: 0 })
  return { centre, radiusPx: Math.hypot(edge.x - centre.x, edge.y - centre.y) }
}

export function attachBackdrop(
  host: BackdropHost,
  getCore: () => { centre: Point; radiusPx: number },
  colors: { canvas: string; nebula: string; isDark: boolean },
): () => void {
  const container = host.getContainer()
  const canvas = document.createElement("canvas")
  canvas.setAttribute("aria-hidden", "true")
  Object.assign(canvas.style, {
    position: "absolute",
    inset: "0",
    pointerEvents: "none",
  })
  container.insertBefore(canvas, container.firstChild)
  const ctx = canvas.getContext("2d")
  const peak = colors.isDark ? 0.55 : 0.35

  const paint = () => {
    if (!ctx) return
    const { width, height } = host.getDimensions()
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = colors.canvas
    ctx.fillRect(0, 0, width, height)
    const core = getCore()
    const g = nebulaGeometry(core.centre, core.radiusPx)
    const gradient = ctx.createRadialGradient(g.x, g.y, 0, g.x, g.y, g.r)
    gradient.addColorStop(0, hexToRgba(colors.nebula, peak))
    gradient.addColorStop(0.5, hexToRgba(colors.nebula, peak / 3))
    gradient.addColorStop(1, hexToRgba(colors.nebula, 0))
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, width, height)
  }

  const camera = host.getCamera()
  camera.on("updated", paint)
  paint()

  return () => {
    camera.off("updated", paint)
    canvas.remove()
  }
}
