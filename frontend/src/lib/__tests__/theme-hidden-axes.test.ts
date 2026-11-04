import { beforeEach, describe, expect, it } from "vitest"
import type { ThemeConfig, ThemeSettings } from "darkraise-ui/theme"
import {
  hiddenAxes,
  pinHiddenAxes,
  scrubHiddenAxisStorage,
} from "@/lib/theme-hidden-axes"
import { SWITCHER_AXES, themeConfig } from "@/theme.config"

/** darkmem's config with every axis on except `axes`, so each test controls
 *  exactly which axes are hidden rather than inheriting the live pin set. */
function withHidden(...axes: string[]): ThemeConfig {
  const next = structuredClone(themeConfig) as ThemeConfig
  const table = next.switcher.axes as Record<string, boolean>
  for (const axis of Object.keys(table)) table[axis] = true
  for (const axis of axes) table[axis] = false
  return next
}

describe("theme-hidden-axes", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("hides everything but the switcher axes in darkmem's own config", () => {
    const hidden = new Set(hiddenAxes(themeConfig))
    for (const axis of SWITCHER_AXES) expect(hidden.has(axis)).toBe(false)
    expect(hidden.has("preset")).toBe(true)
    expect(hidden.has("outerGlow")).toBe(true)
  })

  it("pins a hidden axis back to the configured default", () => {
    const config = withHidden("density", "contrast")
    const stored: ThemeSettings = {
      ...themeConfig.defaults,
      density: "compact",
      contrast: "high",
      accentColor: "rose",
    }

    const pinned = pinHiddenAxes(stored, config) as unknown as Record<
      string,
      unknown
    >

    expect(pinned.density).toBe(themeConfig.defaults.density)
    expect(pinned.contrast).toBe(themeConfig.defaults.contrast)
    // An adjustable axis is untouched — the pin is scoped, not a reset.
    expect(pinned.accentColor).toBe("rose")
  })

  it("scrubs persisted storage for a hidden axis and only that axis", () => {
    window.localStorage.setItem("theme-density", "compact")
    window.localStorage.setItem("theme-accent", "rose")

    scrubHiddenAxisStorage(withHidden("density"))

    expect(window.localStorage.getItem("theme-density")).toBeNull()
    expect(window.localStorage.getItem("theme-accent")).toBe("rose")
  })

  it("scrubs the 6.x spellings the library migrates into a hidden axis", () => {
    // The scrub runs before the library's migration, so leaving a 6.x key
    // would let its value be migrated in over the pin.
    window.localStorage.setItem("theme-dark-accent-chroma", "calm")
    window.localStorage.setItem("theme-accent-intensity", "calm")
    window.localStorage.setItem("theme-accent-vibrancy", "calm")

    scrubHiddenAxisStorage(withHidden("darkAccentChroma"))

    expect(window.localStorage.getItem("theme-dark-accent-chroma")).toBeNull()
    expect(window.localStorage.getItem("theme-accent-intensity")).toBeNull()
    expect(window.localStorage.getItem("theme-accent-vibrancy")).toBeNull()
  })

  it("pins every axis back to the defaults when all are hidden", () => {
    const config = withHidden(...Object.keys(themeConfig.switcher.axes ?? {}))
    const drifted = Object.fromEntries(
      Object.keys(themeConfig.defaults).map((axis) => [axis, "drifted"]),
    ) as unknown as ThemeSettings

    const pinned = pinHiddenAxes(drifted, config)

    expect(pinned).toEqual(themeConfig.defaults)
  })
})
