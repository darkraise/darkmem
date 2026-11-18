export const MOTION_NODE_LIMIT = 2000
export const MOTION_FPS = 30

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"

export function motionAllowed(env: {
  reducedMotion: boolean
  nodeCount: number
  hidden: boolean
}): boolean {
  return !env.reducedMotion && env.nodeCount < MOTION_NODE_LIMIT && !env.hidden
}

export function startAmbientMotion(opts: {
  nodeCount: number
  onFrame: (timeSec: number) => void
}): () => void {
  const { nodeCount, onFrame } = opts
  const media = window.matchMedia(REDUCED_MOTION_QUERY)
  let reducedMotion = media.matches
  const hidden = () => document.visibilityState === "hidden"
  if (!motionAllowed({ reducedMotion, nodeCount, hidden: hidden() })) return () => {}

  const interval = 1000 / MOTION_FPS
  const start = performance.now()
  let last = -Infinity
  let frame: number | null = null

  const tick = () => {
    frame = requestAnimationFrame(tick)
    const now = performance.now()
    if (now - last < interval) return
    last = now
    onFrame((now - start) / 1000)
  }
  const sync = () => {
    const allowed = motionAllowed({ reducedMotion, nodeCount, hidden: hidden() })
    if (allowed && frame === null) frame = requestAnimationFrame(tick)
    if (!allowed && frame !== null) {
      cancelAnimationFrame(frame)
      frame = null
    }
  }
  const onMediaChange = (e: { matches: boolean }) => {
    reducedMotion = e.matches
    sync()
  }

  media.addEventListener("change", onMediaChange)
  document.addEventListener("visibilitychange", sync)
  sync()

  return () => {
    if (frame !== null) cancelAnimationFrame(frame)
    frame = null
    media.removeEventListener("change", onMediaChange)
    document.removeEventListener("visibilitychange", sync)
  }
}
