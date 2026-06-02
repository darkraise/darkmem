import { useEffect, useRef } from "react"

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  color: string
  accent: boolean
}

export interface ParticleBackgroundProps {
  className?: string
  /** Render the built-in aurora mesh gradient behind the particles. */
  gradient?: boolean
  /** Cursor links + repulsion. */
  interactive?: boolean
  /** Particles per px² (clamped 70–170). */
  density?: number
  /** Drift speed in px/frame. */
  speed?: number
  colors?: {
    nodes?: string[]
    accents?: string[]
    accentRatio?: number
    /** rgb triple for node links, e.g. "129,140,248". */
    link?: string
    /** rgb triple for cursor links, e.g. "103,232,249". */
    mouseLink?: string
  }
}

const DEFAULT_NODES = ["#818cf8", "#6366f1", "#a5b4fc"]
const DEFAULT_ACCENTS = ["#22d3ee", "#67e8f9"]
const LINK = 128
const MOUSE_LINK = 180
const REPEL = 110

function MeshGradient() {
  return (
    <div className="dm-mesh" aria-hidden="true">
      <div className="dm-blob dm-b1" />
      <div className="dm-blob dm-b2" />
      <div className="dm-blob dm-b3" />
      <div className="dm-blob dm-b4" />
      <div className="dm-blob dm-b5" />
      <div className="dm-veil" />
    </div>
  )
}

export function ParticleBackground({
  className,
  gradient = true,
  interactive = true,
  density = 0.00012,
  speed = 1.0,
  colors,
}: ParticleBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const particlesRef = useRef<Particle[]>([])
  const sizeRef = useRef({ w: 0, h: 0 })
  const mouseRef = useRef({ x: 0, y: 0, active: false })
  // Read palette through a ref so an inline `colors` object prop doesn't re-init
  // the whole canvas on every parent render (`colors` is NOT in the effect deps).
  const colorsRef = useRef(colors)
  colorsRef.current = colors

  useEffect(() => {
    if (typeof window === "undefined") return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const c = colorsRef.current
    const nodes = c?.nodes ?? DEFAULT_NODES
    const accents = c?.accents ?? DEFAULT_ACCENTS
    const accentRatio = c?.accentRatio ?? 0.18
    const linkRGB = c?.link ?? "129,140,248"
    const mouseRGB = c?.mouseLink ?? "103,232,249"
    const reduce =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false
    // Downgrade on touch / low-core devices: fewer particles and NO cursor
    // interaction, so finger-tracking repulsion doesn't fight typing on mobile.
    const lowEnd =
      (window.matchMedia?.("(pointer: coarse)").matches ?? false) ||
      (navigator.hardwareConcurrency ?? 8) <= 4
    const isInteractive = interactive && !lowEnd

    const pick = (arr: string[]) =>
      arr[Math.floor(Math.random() * arr.length)] ?? arr[0]!
    const spawn = (w: number, h: number): Particle => {
      const accent = Math.random() < accentRatio
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * speed,
        vy: (Math.random() - 0.5) * speed,
        r: accent ? 2.0 + Math.random() * 1.4 : 1.3 + Math.random() * 1.5,
        color: accent ? pick(accents) : pick(nodes),
        accent,
      }
    }

    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1)
      const w = window.innerWidth
      const h = window.innerHeight
      sizeRef.current = { w, h }
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const target = lowEnd
        ? Math.min(90, Math.max(40, Math.round(w * h * density)))
        : Math.min(170, Math.max(70, Math.round(w * h * density)))
      const cur = particlesRef.current
      if (cur.length < target) {
        for (let i = cur.length; i < target; i++) cur.push(spawn(w, h))
      } else if (cur.length > target) {
        cur.length = target
      }
    }

    const draw = () => {
      const { w, h } = sizeRef.current
      const ps = particlesRef.current
      const m = mouseRef.current
      ctx.clearRect(0, 0, w, h)
      ctx.lineWidth = 1
      for (let i = 0; i < ps.length; i++) {
        const a = ps[i]!
        for (let j = i + 1; j < ps.length; j++) {
          const b = ps[j]!
          const dx = a.x - b.x
          const dy = a.y - b.y
          const d = Math.hypot(dx, dy)
          if (d < LINK) {
            ctx.strokeStyle = `rgba(${linkRGB},${(1 - d / LINK) * 0.5})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
        if (isInteractive && m.active) {
          const dx = a.x - m.x
          const dy = a.y - m.y
          const d = Math.hypot(dx, dy)
          if (d < MOUSE_LINK) {
            ctx.strokeStyle = `rgba(${mouseRGB},${(1 - d / MOUSE_LINK) * 0.75})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(m.x, m.y)
            ctx.stroke()
          }
        }
      }
      for (const p of ps) {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = p.color
        ctx.shadowColor = p.accent ? p.color : "transparent"
        ctx.shadowBlur = p.accent ? 8 : 0
        ctx.fill()
      }
      ctx.shadowBlur = 0
    }

    const step = () => {
      const { w, h } = sizeRef.current
      const ps = particlesRef.current
      const m = mouseRef.current
      for (const p of ps) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) {
          p.x = 0
          p.vx *= -1
        } else if (p.x > w) {
          p.x = w
          p.vx *= -1
        }
        if (p.y < 0) {
          p.y = 0
          p.vy *= -1
        } else if (p.y > h) {
          p.y = h
          p.vy *= -1
        }
        if (isInteractive && m.active) {
          const dx = p.x - m.x
          const dy = p.y - m.y
          const d = Math.hypot(dx, dy)
          if (d < REPEL && d > 0.01) {
            const f = ((REPEL - d) / REPEL) * 2.2
            p.x += (dx / d) * f
            p.y += (dy / d) * f
          }
        }
      }
      draw()
      rafRef.current = requestAnimationFrame(step)
    }

    const onMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY, active: true }
    }
    const onMouseLeave = () => {
      mouseRef.current.active = false
    }
    const onTouchMove = (e: TouchEvent) => {
      const t = e.touches[0]
      if (t) mouseRef.current = { x: t.clientX, y: t.clientY, active: true }
    }
    const onTouchEnd = () => {
      mouseRef.current.active = false
    }
    const onVisibility = () => {
      if (document.hidden) {
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current)
          rafRef.current = null
        }
      } else if (rafRef.current === null) {
        rafRef.current = requestAnimationFrame(step)
      }
    }

    const onResize = () => {
      resize()
      if (reduce) draw() // keep the static frame painted after a resize
    }
    resize()
    window.addEventListener("resize", onResize)

    if (reduce) {
      draw() // single static frame, no loop, no interaction
    } else {
      if (isInteractive) {
        window.addEventListener("mousemove", onMouseMove, { passive: true })
        window.addEventListener("mouseout", onMouseLeave)
        window.addEventListener("touchmove", onTouchMove, { passive: true })
        window.addEventListener("touchend", onTouchEnd)
      }
      document.addEventListener("visibilitychange", onVisibility)
      rafRef.current = requestAnimationFrame(step)
    }

    return () => {
      window.removeEventListener("resize", onResize)
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseout", onMouseLeave)
      window.removeEventListener("touchmove", onTouchMove)
      window.removeEventListener("touchend", onTouchEnd)
      document.removeEventListener("visibilitychange", onVisibility)
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
      particlesRef.current = []
    }
    // Re-init only on the primitives that change canvas behavior. `colors` is
    // read through colorsRef (not referenced here, so exhaustive-deps is satisfied);
    // `gradient` only affects render.
  }, [interactive, density, speed])

  return (
    <div
      className={`pointer-events-none fixed inset-0 -z-10 overflow-hidden ${className ?? ""}`}
      aria-hidden="true"
    >
      {gradient && <MeshGradient />}
      <canvas ref={canvasRef} className="absolute inset-0" />
    </div>
  )
}
