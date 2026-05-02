import { useEffect, useRef } from "react"

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
}

type Props = {
  density?: number
  linkDistance?: number
  speed?: number
}

export function ParticleBackground({
  density = 0.00012,
  linkDistance = 140,
  speed = 0.25,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const particlesRef = useRef<Particle[]>([])
  const sizeRef = useRef<{ w: number; h: number; dpr: number }>({ w: 0, h: 0, dpr: 1 })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      const w = window.innerWidth
      const h = window.innerHeight
      sizeRef.current = { w, h, dpr }
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.scale(dpr, dpr)

      const target = Math.min(220, Math.max(40, Math.floor(w * h * density)))
      const current = particlesRef.current
      if (current.length < target) {
        for (let i = current.length; i < target; i++) {
          current.push(spawn(w, h))
        }
      } else if (current.length > target) {
        current.length = target
      }
    }

    const spawn = (w: number, h: number): Particle => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * speed,
      vy: (Math.random() - 0.5) * speed,
      r: 1.0 + Math.random() * 1.5,
    })

    const step = () => {
      const { w, h } = sizeRef.current
      ctx.clearRect(0, 0, w, h)

      // Soft radial vignette so the particles fade toward the centre, keeping
      // the wizard card in focus.
      const gradient = ctx.createRadialGradient(
        w / 2, h / 2, Math.min(w, h) * 0.15,
        w / 2, h / 2, Math.max(w, h) * 0.7,
      )
      gradient.addColorStop(0, "rgba(0,0,0,0)")
      gradient.addColorStop(1, "rgba(0,0,0,0.35)")

      const particles = particlesRef.current

      // Update positions.
      for (const p of particles) {
        if (!reduceMotion) {
          p.x += p.vx
          p.y += p.vy
          if (p.x < -10) p.x = w + 10
          else if (p.x > w + 10) p.x = -10
          if (p.y < -10) p.y = h + 10
          else if (p.y > h + 10) p.y = -10
        }
      }

      // Draw connecting lines.
      ctx.lineWidth = 0.7
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i]
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const d2 = dx * dx + dy * dy
          if (d2 < linkDistance * linkDistance) {
            const alpha = 1 - Math.sqrt(d2) / linkDistance
            ctx.strokeStyle = `rgba(120, 160, 220, ${alpha * 0.18})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
      }

      // Draw particle dots.
      for (const p of particles) {
        ctx.fillStyle = "rgba(180, 200, 240, 0.7)"
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      }

      // Vignette overlay.
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, w, h)

      rafRef.current = requestAnimationFrame(step)
    }

    resize()
    window.addEventListener("resize", resize)
    rafRef.current = requestAnimationFrame(step)

    return () => {
      window.removeEventListener("resize", resize)
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [density, linkDistance, speed])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none"
      style={{
        background:
          "radial-gradient(ellipse at center, hsl(220 18% 12%) 0%, hsl(222 22% 6%) 70%, hsl(224 26% 4%) 100%)",
      }}
    />
  )
}
