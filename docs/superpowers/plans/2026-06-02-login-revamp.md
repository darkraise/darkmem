# Login / Guest Auth Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain darkmem login (and share it with the setup wizard) with a frosted-glass auth card over an interactive, mouse-reactive particle "knowledge-graph" backdrop and a smooth aurora mesh gradient.

**Architecture:** Promote the existing `ParticleBackground` out of `features/setup` into a shared, extended `src/components/particle-background.tsx` that renders both the aurora mesh (CSS) and the interactive particle canvas. A thin `GlassPanel` (wrapping darkraise-ui `Card`) is the shared frosted surface for the login card and the wizard. The guest route shell hosts one backdrop for both screens. Sign-in behavior is unchanged (password-only).

**Tech Stack:** React 19 + TypeScript, TanStack Router (file-based), Tailwind v4, darkraise-ui, TanStack Query/Form, Vitest + React Testing Library (jsdom).

**Spec:** `docs/superpowers/specs/2026-06-02-login-revamp-design.md`

---

## File Structure

| File | Responsibility |
| --- | --- |
| `src/test/setup.ts` | **new** — global test stubs (`matchMedia`, canvas `getContext`, `requestAnimationFrame`) so any test rendering the backdrop runs in jsdom |
| `vitest.config.ts` | **modify** — register `setupFiles` |
| `src/styles/globals.css` | **modify** — aurora mesh classes + drift keyframes + button-glow keyframe + reduced-motion block |
| `src/components/particle-background.tsx` | **moved from** `features/setup/components/ParticleBackground.tsx`, then **rewritten** — mesh + interactive particle canvas + lifecycle |
| `src/features/setup/components/ParticleBackground.tsx` | **deleted** (relocated) |
| `src/components/glass-panel.tsx` | **new** — thin frosted wrapper over darkraise-ui `Card` |
| `src/features/auth/components/login-card.tsx` | **new** — brand block + `LoginForm`, in a `GlassPanel` (testable seam) |
| `src/routes/_guest.tsx` | **modify** — render `ParticleBackground` + centered `Outlet` |
| `src/routes/_guest/login.tsx` | **modify** — render `LoginCard`; drop `PageHeader`; keep router wiring |
| `src/features/auth/components/login-form.tsx` | **modify** — restyle submit button + password field (no behavior change) |
| `src/features/setup/components/SetupWizard.tsx` | **modify** — remove own `ParticleBackground`; `Card` → `GlassPanel` |
| `src/components/__tests__/particle-background.test.tsx` | **new** — lifecycle tests |
| `src/components/__tests__/glass-panel.test.tsx` | **new** — render test |
| `src/features/auth/components/__tests__/login-card.test.tsx` | **new** — render test |
| `src/features/setup/components/__tests__/setup-wizard-no-canvas.test.tsx` | **new** — regression: wizard renders no canvas |

---

## Task 1: Shared test setup (matchMedia + canvas + rAF stubs)

**Files:**
- Create: `frontend/src/test/setup.ts`
- Modify: `frontend/vitest.config.ts`

- [ ] **Step 1: Create the setup file**

`frontend/src/test/setup.ts`:

```ts
// Registers jest-dom matchers (toBeInTheDocument, etc.) used by later tasks'
// tests. The package is installed but was never wired into a shared setup.
import "@testing-library/jest-dom/vitest"
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
```

- [ ] **Step 2: Register it in vitest config**

In `frontend/vitest.config.ts`, add `setupFiles` to the `test` block:

```ts
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["**/node_modules/**", "**/dist/**", "tests/**"],
  },
```

- [ ] **Step 3: Verify the existing suite still passes**

Run: `npm run test`
Expected: all existing tests pass (currently 48). `clearAllMocks` clears call history but **preserves mock implementations** (it is `mockClear`, not `mockReset`/`mockRestore`), so the stubs above survive across tests and the `job-config-form` module mocks still resolve. **Do not** switch this `afterEach` to `resetAllMocks`/`restoreAllMocks` — that would detach the canvas/matchMedia/rAF stubs and break every backdrop test.

- [ ] **Step 4: Commit**

```bash
git add src/test/setup.ts vitest.config.ts
git commit -m "test: add jsdom setup stubs for canvas/matchMedia/rAF"
```

---

## Task 2: Relocate ParticleBackground to src/components

Pure move so the tree keeps building before the rewrite. The wizard keeps working (it passes no props).

**Files:**
- Move: `frontend/src/features/setup/components/ParticleBackground.tsx` → `frontend/src/components/particle-background.tsx`
- Modify: `frontend/src/features/setup/components/SetupWizard.tsx:15`

- [ ] **Step 1: Move the file (preserve history)**

```bash
git mv src/features/setup/components/ParticleBackground.tsx src/components/particle-background.tsx
```

- [ ] **Step 2: Repoint the wizard import**

In `frontend/src/features/setup/components/SetupWizard.tsx`, change line 15 from:

```tsx
import { ParticleBackground } from "./ParticleBackground"
```

to:

```tsx
import { ParticleBackground } from "@/components/particle-background"
```

- [ ] **Step 3: Verify build + types + tests**

Run: `npm run typecheck && npx vite build && npm run test`
Expected: tsc exit 0, build succeeds, tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/components/particle-background.tsx src/features/setup/components/ParticleBackground.tsx src/features/setup/components/SetupWizard.tsx
git commit -m "refactor(ui): move ParticleBackground to shared src/components"
```

---

## Task 3: Aurora mesh + keyframes in globals.css

Define the CSS the rewritten component (Task 4) and the login button (Task 7) consume.

**Files:**
- Modify: `frontend/src/styles/globals.css` (append at end of file)

- [ ] **Step 1: Append the backdrop CSS**

Add to the end of `frontend/src/styles/globals.css`:

```css
/* --- Atmospheric guest backdrop (ParticleBackground mesh) --- */
.dm-mesh {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: linear-gradient(160deg, #070a11 0%, #05070d 55%, #03050a 100%);
}
.dm-blob {
  position: absolute;
  border-radius: 9999px;
  will-change: transform;
}
.dm-b1 { width: 62vw; height: 62vw; left: -16%; top: -22%; background: #6366f1; opacity: 0.18; filter: blur(115px); animation: dm-floatA 24s ease-in-out infinite alternate; }
.dm-b2 { width: 58vw; height: 58vw; right: -18%; bottom: -26%; background: #7c3aed; opacity: 0.16; filter: blur(120px); animation: dm-floatB 28s ease-in-out infinite alternate; }
.dm-b3 { width: 46vw; height: 46vw; left: 28%; top: 22%; background: #2563eb; opacity: 0.13; filter: blur(125px); animation: dm-floatC 32s ease-in-out infinite alternate; }
.dm-b4 { width: 30vw; height: 30vw; right: 18%; top: -10%; background: #22d3ee; opacity: 0.09; filter: blur(115px); animation: dm-floatB 26s ease-in-out infinite alternate; }
.dm-b5 { width: 48vw; height: 48vw; left: -12%; bottom: 2%; background: #4338ca; opacity: 0.15; filter: blur(125px); animation: dm-floatA 30s ease-in-out infinite alternate; }
.dm-veil {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 42%, rgba(5, 7, 12, 0.22) 0%, rgba(3, 4, 9, 0.72) 100%);
}

@keyframes dm-floatA { from { transform: translate(0, 0) scale(1); } to { transform: translate(7%, 5%) scale(1.08); } }
@keyframes dm-floatB { from { transform: translate(0, 0) scale(1); } to { transform: translate(-6%, -4%) scale(1.1); } }
@keyframes dm-floatC { from { transform: translate(0, 0) scale(1.05); } to { transform: translate(4%, -6%) scale(1); } }

/* Distinct from the existing chat `pulse-glow` (which scales/fades). Box-shadow only. */
@keyframes dm-btn-glow {
  0%, 100% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.18), 0 4px 16px rgba(99, 102, 241, 0.32); }
  50% { box-shadow: 0 0 28px rgba(56, 189, 248, 0.42), 0 4px 18px rgba(99, 102, 241, 0.5); }
}
.dm-btn-pulse { animation: dm-btn-glow 2.8s ease-in-out infinite; }
/* No glow while disabled/pending (the disabled state shows a solid grey fill). */
.dm-btn-pulse:disabled { animation: none; }

/* Frosted surface base + opaque fallback. The app's "default" preset leaves
   darkraise-ui's --backdrop-filter: none, so the glass relies entirely on the
   utility classes below; without this fallback the card is illegible where
   backdrop-filter is unsupported/disabled (e.g. Firefox with the pref off,
   GPU-blocklisted contexts). Unlayered rule, so it wins over Card's bg-card. */
.dm-glass { background-color: rgb(15 18 28 / 0.55); }
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .dm-glass { background-color: rgb(13 17 28 / 0.92); }
}

@media (prefers-reduced-motion: reduce) {
  .dm-blob,
  .dm-btn-pulse {
    animation: none !important;
    will-change: auto; /* release the compositing layer when nothing animates */
  }
}
```

- [ ] **Step 2: Verify build (CSS compiles, no JS change to test yet)**

Run: `npx vite build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/styles/globals.css
git commit -m "feat(ui): add aurora mesh + glow keyframes for guest backdrop"
```

---

## Task 4: Rewrite ParticleBackground (mesh + interactive canvas + lifecycle)

**Files:**
- Modify (full rewrite): `frontend/src/components/particle-background.tsx`
- Test: `frontend/src/components/__tests__/particle-background.test.tsx`

- [ ] **Step 1: Write the failing lifecycle tests**

`frontend/src/components/__tests__/particle-background.test.tsx`:

```tsx
import { render } from "@testing-library/react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { ParticleBackground } from "../particle-background"

// NOTE: `vi` must be imported explicitly. This project does NOT register
// vitest globals as TYPES (no `types: ["vitest/globals"]` in tsconfig), so
// using `vi` without importing it fails `tsc -b` even though `globals: true`
// makes it available at runtime.

function setReducedMotion(matches: boolean) {
  ;(window.matchMedia as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  )
}

describe("ParticleBackground", () => {
  beforeEach(() => {
    setReducedMotion(false)
  })

  it("renders one canvas behind the content", () => {
    const { container } = render(<ParticleBackground />)
    expect(container.querySelectorAll("canvas")).toHaveLength(1)
  })

  it("starts the animation loop when motion is allowed", () => {
    render(<ParticleBackground />)
    expect(window.requestAnimationFrame).toHaveBeenCalled()
  })

  it("does NOT start a loop under prefers-reduced-motion", () => {
    setReducedMotion(true)
    render(<ParticleBackground />)
    expect(window.requestAnimationFrame).not.toHaveBeenCalled()
  })

  it("cancels the loop when the tab is hidden", () => {
    render(<ParticleBackground />)
    Object.defineProperty(document, "hidden", { value: true, configurable: true })
    document.dispatchEvent(new Event("visibilitychange"))
    expect(window.cancelAnimationFrame).toHaveBeenCalled()
    Object.defineProperty(document, "hidden", { value: false, configurable: true })
  })

  it("removes its listeners on unmount", () => {
    const remove = vi.spyOn(window, "removeEventListener")
    const { unmount } = render(<ParticleBackground />)
    unmount()
    expect(remove).toHaveBeenCalledWith("resize", expect.any(Function))
    remove.mockRestore() // restore the spy so it doesn't leak into other tests
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test -- particle-background`
Expected: FAIL — the current (relocated) component keeps the rAF loop under reduced-motion and has no `visibilitychange` handler.

- [ ] **Step 3: Rewrite the component**

Replace the entire contents of `frontend/src/components/particle-background.tsx`:

```tsx
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

    const pick = (arr: string[]) => arr[Math.floor(Math.random() * arr.length)] ?? arr[0]!
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
        if (p.x < 0) { p.x = 0; p.vx *= -1 } else if (p.x > w) { p.x = w; p.vx *= -1 }
        if (p.y < 0) { p.y = 0; p.vy *= -1 } else if (p.y > h) { p.y = h; p.vy *= -1 }
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm run test -- particle-background`
Expected: PASS (5 tests).

- [ ] **Step 5: Typecheck + build**

Run: `npm run typecheck && npx vite build`
Expected: tsc exit 0, build succeeds.

- [ ] **Step 6: Commit**

```bash
git add src/components/particle-background.tsx src/components/__tests__/particle-background.test.tsx
git commit -m "feat(ui): interactive aurora particle background with reduced-motion + visibility handling"
```

---

## Task 5: GlassPanel (frosted surface over darkraise-ui Card)

**Files:**
- Create: `frontend/src/components/glass-panel.tsx`
- Test: `frontend/src/components/__tests__/glass-panel.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/__tests__/glass-panel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { GlassPanel } from "../glass-panel"

describe("GlassPanel", () => {
  it("renders children and forwards className", () => {
    render(
      <GlassPanel className="max-w-sm" data-testid="panel">
        <span>hello</span>
      </GlassPanel>,
    )
    expect(screen.getByText("hello")).toBeInTheDocument()
    const panel = screen.getByTestId("panel")
    expect(panel.className).toContain("max-w-sm")
    expect(panel.className).toContain("backdrop-blur-[16px]")
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test -- glass-panel`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement GlassPanel**

`frontend/src/components/glass-panel.tsx`:

```tsx
import type { ComponentProps } from "react"
import { Card } from "darkraise-ui/components/card"

// Styling only — callers supply width/height/flex/overflow via className so
// the login card (max-w-sm) and the setup wizard (max-h-[90vh] flex-col
// overflow-hidden) each keep their own layout.
// `dm-glass` (globals.css) supplies the base fill + the @supports opaque
// fallback; do not also set a Tailwind bg utility here (it would layer-conflict).
const GLASS =
  "dm-glass rounded-[18px] border border-white/12 shadow-[0_24px_70px_rgba(0,0,0,0.62)] ring-1 ring-indigo-500/10 backdrop-blur-[16px]"

export function GlassPanel({
  className,
  ...props
}: ComponentProps<typeof Card>) {
  return <Card className={`${GLASS} ${className ?? ""}`} {...props} />
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm run test -- glass-panel`
Expected: PASS. (Verified: darkraise-ui `Card` composes className via `cn` = `twMerge(clsx)` and spreads extra props; there is no competing `backdrop-blur` utility to dedupe, and the GlassPanel utilities land in the higher-priority utilities layer over `.dr-card`'s component-layer base, so the glass classes apply.)

- [ ] **Step 5: Commit**

```bash
git add src/components/glass-panel.tsx src/components/__tests__/glass-panel.test.tsx
git commit -m "feat(ui): add GlassPanel frosted surface over Card"
```

---

## Task 6: Guest shell hosts the backdrop; wizard stops rendering its own

One commit so `/setup` always has exactly one canvas.

**Files:**
- Modify: `frontend/src/routes/_guest.tsx`
- Modify: `frontend/src/features/setup/components/SetupWizard.tsx`
- Test: `frontend/src/features/setup/components/__tests__/setup-wizard-no-canvas.test.tsx`

- [ ] **Step 1: Update the guest layout**

In `frontend/src/routes/_guest.tsx`, add the import and replace the `component`:

```tsx
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { useAuthStore } from "@/features/auth"
import { checkSetupStatus } from "@/lib/api"
import { ParticleBackground } from "@/components/particle-background"

export const Route = createFileRoute("/_guest")({
  beforeLoad: async ({ location }) => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/" })
    }
    if (location.pathname === "/setup") {
      return
    }
    const { initialized } = await checkSetupStatus()
    if (!initialized) {
      throw redirect({ to: "/setup" })
    }
  },
  component: () => (
    <div className="bg-background relative flex min-h-screen items-center justify-center px-4">
      <ParticleBackground />
      <Outlet />
    </div>
  ),
})
```

(Keep `bg-background` so the layout degrades to a solid dark page if the mesh is ever disabled — the `-z-10` backdrop paints over it.)
```

- [ ] **Step 2: Remove the wizard's own backdrop and swap Card → GlassPanel**

In `frontend/src/features/setup/components/SetupWizard.tsx`:
1. Delete line 15: `import { ParticleBackground } from "@/components/particle-background"`.
2. Change the `Card` import (line 3) to keep only `CardContent`, and add `GlassPanel`:

```tsx
import { CardContent } from "darkraise-ui/components/card"
import { GlassPanel } from "@/components/glass-panel"
```

3. Replace the opening wrapper. Change (SetupWizard.tsx:121-125):

```tsx
  return (
    <>
      <ParticleBackground />
      <Card className="border-border/60 bg-card/85 flex max-h-[90vh] w-full max-w-2xl flex-col shadow-2xl backdrop-blur-md">
        <CardContent className="flex flex-col gap-6 overflow-hidden p-8">
```

to:

```tsx
  return (
    <GlassPanel className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden">
      <CardContent className="flex flex-col gap-6 overflow-hidden p-8">
```

4. Replace the closing wrapper. Change the end of the component (SetupWizard.tsx:191-193):

```tsx
        </CardContent>
      </Card>
    </>
  )
```

to:

```tsx
      </CardContent>
    </GlassPanel>
  )
```

- [ ] **Step 3: Write the regression test**

`frontend/src/features/setup/components/__tests__/setup-wizard-no-canvas.test.tsx`:

```tsx
import { render } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))
// SetupWizard calls useNavigate() at render; stub it so the test needs no
// RouterProvider (and no console warning).
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SetupWizard } from "../SetupWizard"

describe("SetupWizard", () => {
  it("does not render its own particle canvas (backdrop is the guest shell's)", () => {
    const qc = new QueryClient()
    const { container } = render(
      <QueryClientProvider client={qc}>
        <SetupWizard />
      </QueryClientProvider>,
    )
    expect(container.querySelectorAll("canvas")).toHaveLength(0)
  })
})
```

- [ ] **Step 4: Run the test + typecheck + build**

Run: `npm run test -- setup-wizard-no-canvas && npm run typecheck && npx vite build`
Expected: test PASS, tsc exit 0, build succeeds.

Note on coverage: the spec's "exactly one canvas on /setup" is intentionally decomposed into two isolation tests — Task 4 proves `ParticleBackground` renders exactly one canvas, and this test proves the wizard adds none (so re-introducing its own backdrop fails the suite) — plus the Task 8 manual check that `/setup` shows one backdrop. A route-level test that renders the `_guest` shell is deliberately avoided: its `<Outlet />` needs a `RouterProvider` and the repo has no route-test harness, so it would add harness cost while only re-asserting 1 (ParticleBackground, already covered) + 0 (Outlet stub).

- [ ] **Step 5: Commit**

```bash
git add src/routes/_guest.tsx src/features/setup/components/SetupWizard.tsx src/features/setup/components/__tests__/setup-wizard-no-canvas.test.tsx
git commit -m "feat(ui): host guest backdrop in _guest shell; wizard uses GlassPanel"
```

---

## Task 7: Login card (brand + restyled form)

**Files:**
- Create: `frontend/src/features/auth/components/login-card.tsx`
- Modify: `frontend/src/routes/_guest/login.tsx`
- Modify: `frontend/src/features/auth/components/login-form.tsx`
- Test: `frontend/src/features/auth/components/__tests__/login-card.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/features/auth/components/__tests__/login-card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

// useLogin -> auth adapter -> apiFetch is the only external touchpoint; nothing
// in the auth feature imports sonner, so no toast mock is needed here.
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { LoginCard } from "../login-card"

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe("LoginCard", () => {
  it("renders the brand wordmark, password field, and submit", () => {
    wrap(<LoginCard onSuccess={() => {}} />)
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    // Exact "Password" — /password/i would also match the visibility toggle's
    // aria-label "Show password" and throw "multiple elements".
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test -- login-card`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create LoginCard**

`frontend/src/features/auth/components/login-card.tsx`:

```tsx
import { GlassPanel } from "@/components/glass-panel"
import { LoginForm } from "./login-form"

function BrandGlyph() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <g stroke="#67e8f9" strokeWidth="1.6" fill="none">
        <line x1="6" y1="7" x2="14" y2="5" />
        <line x1="6" y1="7" x2="9" y2="17" />
        <line x1="14" y1="5" x2="18" y2="14" />
        <line x1="9" y1="17" x2="18" y2="14" />
      </g>
      <g fill="#818cf8">
        <circle cx="6" cy="7" r="2.4" />
        <circle cx="14" cy="5" r="2.4" />
        <circle cx="18" cy="14" r="2.4" />
        <circle cx="9" cy="17" r="2.4" />
      </g>
    </svg>
  )
}

export function LoginCard({ onSuccess }: { onSuccess: () => void }) {
  return (
    <GlassPanel className="w-full max-w-sm p-8">
      <div className="mb-1 flex items-center justify-center gap-2.5">
        <BrandGlyph />
        <span className="bg-gradient-to-r from-[#c7d2fe] via-[#a5b4fc] to-[#67e8f9] bg-clip-text text-3xl font-extrabold tracking-[0.3px] text-transparent">
          darkmem
        </span>
      </div>
      <p className="text-muted-foreground mb-6 text-center text-base">
        Sign in to continue
      </p>
      <LoginForm onSuccess={onSuccess} />
    </GlassPanel>
  )
}
```

- [ ] **Step 4: Rewrite the login route to use LoginCard**

Replace `frontend/src/routes/_guest/login.tsx`:

```tsx
import { createFileRoute, useRouter } from "@tanstack/react-router"
import { LoginCard } from "@/features/auth/components/login-card"

export const Route = createFileRoute("/_guest/login")({
  component: LoginPage,
})

function LoginPage() {
  const router = useRouter()
  return <LoginCard onSuccess={() => router.navigate({ to: "/" })} />
}
```

- [ ] **Step 5: Restyle the submit button + password field in login-form.tsx (no behavior change)**

In `frontend/src/features/auth/components/login-form.tsx`:

Change the submit `Button` to add the gradient + glow classes (keep `type`, `disabled`, label logic):

```tsx
      <Button
        type="submit"
        disabled={login.isPending}
        className="dm-btn-pulse w-full bg-gradient-to-r from-[#818cf8] via-[#6366f1] to-[#38bdf8] font-semibold text-slate-950 disabled:bg-none disabled:bg-slate-700 disabled:text-slate-100 disabled:opacity-100 focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
      >
        {login.isPending ? "Signing in…" : "Sign in"}
      </Button>
```

The `disabled:*` classes are required: darkraise-ui's `.dr-btn` applies `disabled:opacity-50`, which would composite the near-black `text-slate-950` over the dimmed light gradient and drop the pending "Signing in…" label below WCAG AA. `disabled:opacity-100 disabled:bg-none disabled:bg-slate-700 disabled:text-slate-100` swaps to a solid mid-grey with light text (≥4.5:1) for the pending state.

Add `autoFocus` to the password field and glass styling to the control. Change the `PasswordInputControl` opening tag and the `PasswordInputField`:

```tsx
                <PasswordInputControl className="h-[42px] rounded-[10px] border border-white/15 bg-black/35 focus-within:ring-2 focus-within:ring-cyan-300/60">
                  <PasswordInputField
                    id={field.name}
                    autoComplete="current-password"
                    autoFocus
                    className="bg-transparent text-slate-100 placeholder:text-slate-400 focus:shadow-none focus-visible:shadow-none"
                    value={field.state.value}
                    aria-invalid={isInvalid}
                    aria-describedby={ariaDescribedBy}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                  />
```

The `className` on `PasswordInputField` is required, not optional: the inner field is darkraise-ui's `.dr-input`, which carries an opaque `bg-card`. Without `bg-transparent` the field renders as a solid dark box inside the glass control instead of showing the `bg-black/35` tint. `focus:shadow-none focus-visible:shadow-none` suppresses `.dr-input`'s built-in focus ring so only the control's cyan `focus-within` ring shows (avoids a double indicator). Leave `PasswordInputVisibilityTrigger`/`PasswordInputIndicator` as-is; verify the eye icon is visible on the dark field in the browser.

Also restyle the error message so it stays legible on the translucent card and is announced to assistive tech. Change the error block (currently `login-form.tsx:80-84`) from:

```tsx
      {login.isError && (
        <p className="text-destructive text-base">
          {(login.error as Error).message}
        </p>
      )}
```

to:

```tsx
      {login.isError && (
        <p
          role="alert"
          className="rounded-md bg-red-950/60 px-3 py-2 text-base text-red-200"
        >
          {(login.error as Error).message}
        </p>
      )}
```

The translucent chip gives the message its own legible surface independent of whatever blob/particle is behind the glass, and `role="alert"` announces a failed login to screen-reader users (the bare `<p>` was silent).

- [ ] **Step 6: Run tests to verify they pass**

Run: `npm run test -- login-card`
Expected: PASS. Then `npm run test` — full suite green.

- [ ] **Step 7: Typecheck + build**

Run: `npm run typecheck && npx vite build`
Expected: tsc exit 0, build succeeds.

- [ ] **Step 8: Commit**

```bash
git add src/features/auth/components/login-card.tsx src/routes/_guest/login.tsx src/features/auth/components/login-form.tsx src/features/auth/components/__tests__/login-card.test.tsx
git commit -m "feat(ui): branded glass login card with restyled form"
```

---

## Task 8: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Format touched files**

Run: `npx prettier --write "src/components/**/*.{ts,tsx}" "src/features/auth/**/*.tsx" "src/features/setup/components/SetupWizard.tsx" "src/routes/_guest.tsx" "src/routes/_guest/login.tsx" "src/styles/globals.css" "src/test/setup.ts"`

- [ ] **Step 2: Full gate**

Run: `npm run typecheck && npx vite build && npm run test`
Expected: tsc exit 0; build succeeds; all tests pass (48 existing + the new lifecycle/render/regression tests).

- [ ] **Step 3: Manual checks (dev server)**

Run: `npm run dev`, then verify:
- `/login`: glass card, gradient wordmark + glyph, password field shows the translucent tint (not a solid box), glowing Sign-in button; mouse moves disturb the particle graph; aurora mesh is smooth and dim.
- **Focus & keyboard**: on load, focus starts in the password field (autofocus); Tab → eye toggle → Sign in; Shift+Tab reverses; exactly one focus ring shows on the field (cyan), clearing ~3:1 on the glass. In dev (StrictMode double-mount) confirm autofocus lands once.
- **Pending button contrast**: submit and confirm the "Signing in…" label stays legible (≥4.5:1) against the solid grey disabled fill — not a dim near-black-on-faded-gradient.
- **Error on glass**: trigger a failed login; the error chip is legible over the moving backdrop and is announced by a screen reader (`role="alert"`).
- **backdrop-filter disabled**: in DevTools (Rendering → emulate unsupported) or Firefox `layout.css.backdrop-filter.enabled=false`, confirm the card + text stay legible (the `@supports` opaque fallback kicks in).
- `/login` with OS "reduce motion" on: no canvas loop (one static frame), no blob drift, no button pulse; layout intact; resizing keeps the frame painted.
- `/setup` (uninitialized DB): exactly ONE canvas backdrop; the step list still scrolls and the Back/Next/Finish row stays pinned; the wizard surface matches the login glass.
- **Performance**: DevTools → Performance, record ~5s on `/login` while moving the mouse; frames stay under ~16ms over the card region. If sustained long frames appear, lower the GlassPanel blur toward `backdrop-blur-[10px]`. (Do NOT add `contain: paint`/`isolation: isolate` to the card — that does not stop backdrop-filter resampling and can break the glass blend.)
- **Mobile** (throttled / 320px viewport): card never touches edges; backdrop animates without dropping below ~30fps; cursor interaction is auto-disabled on coarse pointers; eye toggle + submit are ≥44px touch targets.
- Resize the window and toggle to another tab and back: no errors; animation pauses/resumes.

- [ ] **Step 4: Commit any formatting**

```bash
git add src/components src/features/auth src/features/setup/components/SetupWizard.tsx src/routes/_guest.tsx src/routes/_guest/login.tsx src/styles/globals.css src/test/setup.ts
git commit -m "style: prettier pass for login revamp"
```

---

## Self-review notes (author)

- **Spec coverage:** mesh values + `.dm-glass` `@supports` fallback + reduced-motion `will-change` release (Task 3), particle params + interaction + DPR cap + visibilitychange + static reduced-motion + stable `colors` ref + low-end downgrade (Task 4), GlassPanel-over-Card with the opaque-fallback hook (Task 5), single backdrop in shell + wizard de-dup with exact JSX (Task 6), brand block + button restyle incl. disabled-state contrast + transparent field with single ring + error chip with `role="alert"` + focus rings + autofocus (Task 7), test-env stubs + regression + render tests (Tasks 1/4/5/6/7), prettier + manual a11y/perf/responsive checks (Task 8). The `@supports` fallback and disabled-button contrast are now **concrete code steps** (Tasks 3/5/7); Task 8 only verifies them. Remaining manual-only items (inherently visual/un-unit-testable): exact frame timing, mobile fps, the reduced-motion CSS drift-disable, and the "one canvas on /setup" integration (decomposed into the Task 4 + Task 6 isolation tests).
- **Placeholders:** none — every code/test/command block is concrete.
- **Type consistency:** `ParticleBackgroundProps`/`colors` shape is used consistently; `GlassPanel` uses `ComponentProps<typeof Card>`; `LoginCard`/`LoginForm` share the `onSuccess: () => void` contract.
