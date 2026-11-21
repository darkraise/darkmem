import type Graph from "graphology"
import FA2Layout from "graphology-layout-forceatlas2/worker"

export interface LayoutLoop {
  /** Runs ForceAtlas2 on `simulation` in a worker until the deadline. */
  start(simulation: Graph): void
  stop(): void
  kill(): void
  isRunning(): boolean
}

/**
 * The worker, the per-frame mirror and the run deadline both constellation
 * runners share: `onFrame` copies the simulation onto the drawn graph once per
 * animation frame, and `onSettle` runs once the deadline stops the worker.
 */
export function createLayoutLoop(opts: {
  layoutMs: number
  fa2Settings: Record<string, unknown>
  onFrame: () => void
  onSettle: () => void
}): LayoutLoop {
  let worker: FA2Layout | null = null
  let frame: number | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false

  const loop = () => {
    opts.onFrame()
    frame = requestAnimationFrame(loop)
  }
  const halt = () => {
    if (frame !== null) cancelAnimationFrame(frame)
    if (timer !== null) clearTimeout(timer)
    frame = null
    timer = null
    worker?.stop()
    running = false
  }

  return {
    start(simulation) {
      if (running) return
      worker?.kill()
      worker = new FA2Layout(simulation, { settings: opts.fa2Settings })
      worker.start()
      running = true
      frame = requestAnimationFrame(loop)
      timer = setTimeout(() => {
        halt()
        opts.onSettle()
      }, opts.layoutMs)
    },
    stop() {
      halt()
    },
    kill() {
      halt()
      worker?.kill()
      worker = null
    },
    isRunning() {
      return running
    },
  }
}
