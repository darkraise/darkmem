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
