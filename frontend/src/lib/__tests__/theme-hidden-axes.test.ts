import { beforeEach, describe, expect, it } from "vitest"
import type { ThemeConfig, ThemeSettings } from "darkraise-ui/theme"
import {
  hiddenAxes,
  pinHiddenAxes,
  scrubHiddenAxisStorage,
} from "@/lib/theme-hidden-axes"
import { themeConfig } from "@/theme.config"

/**
 * darkmem hides no axis today — every one is reachable from Settings →
 * Appearance — so these assert the guard against a config that does, which is
 * the state it exists for. Deleting it because it is currently inert would
 * mean re-deriving the localStorage key table the next time an axis is pinned.
 */
function withHidden(...axes: string[]): ThemeConfig {
  const next = structuredClone(themeConfig) as ThemeConfig
  const table = next.switcher.axes as unknown as Record<string, boolean>
  for (const axis of axes) table[axis] = false
  return next
}

describe("theme-hidden-axes", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("reports nothing hidden for darkmem's own config", () => {
    expect(hiddenAxes(themeConfig)).toEqual([])
  })

  it("pins a hidden axis back to the configured default", () => {
    const config = withHidden("density", "controlDepth")
    const stored = {
      ...themeConfig.defaults,
      density: "compact",
      controlDepth: "flat",
      accentColor: "rose",
    } as unknown as ThemeSettings

    const pinned = pinHiddenAxes(stored, config) as unknown as Record<
      string,
      unknown
    >

    expect(pinned.density).toBe(themeConfig.defaults.density)
    expect(pinned.controlDepth).toBe(themeConfig.defaults.controlDepth)
    // An adjustable axis is untouched — the pin is scoped, not a reset.
    expect(pinned.accentColor).toBe("rose")
  })

  it("scrubs persisted storage for a hidden axis and only that axis", () => {
    window.localStorage.setItem("theme-control-depth", "flat")
    window.localStorage.setItem("theme-accent", "rose")

    scrubHiddenAxisStorage(withHidden("controlDepth"))

    expect(window.localStorage.getItem("theme-control-depth")).toBeNull()
    expect(window.localStorage.getItem("theme-accent")).toBe("rose")
  })

  it("scrubs the pre-rename accent-intensity spelling too", () => {
    // The library migrates `theme-accent-vibrancy` forward, so leaving it
    // would let the pre-rename value be re-applied over the pin.
    window.localStorage.setItem("theme-accent-vibrancy", "calm")
    window.localStorage.setItem("theme-accent-intensity", "calm")

    scrubHiddenAxisStorage(withHidden("accentIntensity"))

    expect(window.localStorage.getItem("theme-accent-vibrancy")).toBeNull()
    expect(window.localStorage.getItem("theme-accent-intensity")).toBeNull()
  })

  it("pins every axis back to the defaults when all are hidden", () => {
    const config = withHidden(...Object.keys(themeConfig.switcher.axes))
    const drifted = Object.fromEntries(
      Object.keys(themeConfig.defaults).map((axis) => [axis, "drifted"]),
    ) as unknown as ThemeSettings

    const pinned = pinHiddenAxes(drifted, config)

    expect(pinned).toEqual(themeConfig.defaults)
  })
})
