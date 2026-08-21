import { beforeEach, describe, expect, it, vi } from "vitest"
import { themeConfig as libraryDefaults } from "darkraise-ui/theme"

async function importFresh() {
  vi.resetModules()
  return import("@/theme.config")
}

/** The three axes that stay adjustable. Everything else is pinned. */
const VISIBLE_AXES = ["mode", "accentColor", "surfaceColor"]

describe("theme.config", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("offers only the three adjustable axes in the switcher", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.switcher.enabled).toBe(true)
    const visible = Object.entries(themeConfig.switcher.axes)
      .filter(([, enabled]) => enabled)
      .map(([axis]) => axis)
    expect(visible.sort()).toEqual([...VISIBLE_AXES].sort())
  })

  // Drift guard: an axis added by a library upgrade would otherwise stay
  // absent from the config with nothing failing, and would then be neither
  // deliberately shown nor deliberately pinned.
  it("covers the library's axis set exactly", async () => {
    const { themeConfig } = await importFresh()
    expect(Object.keys(themeConfig.switcher.axes).sort()).toEqual(
      Object.keys(libraryDefaults.switcher.axes).sort(),
    )
    expect(Object.keys(themeConfig.defaults).sort()).toEqual(
      Object.keys(libraryDefaults.defaults).sort(),
    )
  })

  it("keeps darkmem's own default look", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.defaults).toMatchObject({
      preset: "default",
      backgroundStyle: "solid",
      backgroundIntensity: "neutral",
      accentColor: "green",
      surfaceColor: "indigo",
      density: "cozy",
      fontSize: "medium",
      accentIntensity: "vivid",
      elevation: "medium",
      buttonElevation: "flat",
      surfaceIntensity: "flat",
      outerGlow: "balanced",
      innerGlow: "balanced",
      radius: "rounded",
    })
  })

  // A value persisted while an axis was still adjustable would otherwise keep
  // applying with no control left to change it.
  it("scrubs persisted values for hidden axes on import", async () => {
    window.localStorage.setItem("theme-preset", "glass")
    window.localStorage.setItem("theme-density", "compact")
    window.localStorage.setItem("theme-outer-glow", "vivid")
    window.localStorage.setItem("theme-accent-vibrancy", "calm")

    await importFresh()

    expect(window.localStorage.getItem("theme-preset")).toBeNull()
    expect(window.localStorage.getItem("theme-density")).toBeNull()
    expect(window.localStorage.getItem("theme-outer-glow")).toBeNull()
    // The pre-rename spelling too: the library migrates it forward, so
    // leaving it would let it be re-applied over the pin.
    expect(window.localStorage.getItem("theme-accent-vibrancy")).toBeNull()
  })

  it("leaves persisted values for the adjustable axes alone", async () => {
    window.localStorage.setItem("mode", "light")
    window.localStorage.setItem("theme-accent", "rose")
    window.localStorage.setItem("theme-surface-color", "teal")

    await importFresh()

    expect(window.localStorage.getItem("mode")).toBe("light")
    expect(window.localStorage.getItem("theme-accent")).toBe("rose")
    expect(window.localStorage.getItem("theme-surface-color")).toBe("teal")
  })
})
