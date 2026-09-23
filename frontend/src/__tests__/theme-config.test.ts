import { beforeEach, describe, expect, it, vi } from "vitest"
import { themeConfig as libraryDefaults } from "darkraise-ui/theme"

async function importFresh() {
  vi.resetModules()
  return import("@/theme.config")
}

describe("theme.config", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  // Only the header's three stay adjustable. One config gates both the popover
  // and `ThemeSettingsPanel`, so an axis off here is off on Settings →
  // Appearance too — which is what pins darkmem's look.
  it("leaves exactly the switcher axes adjustable", async () => {
    const { themeConfig, SWITCHER_AXES } = await importFresh()
    expect(themeConfig.switcher.enabled).toBe(true)
    const on = Object.entries(themeConfig.switcher.axes)
      .filter(([, enabled]) => enabled)
      .map(([axis]) => axis)
    expect(on.sort()).toEqual([...SWITCHER_AXES].sort())
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

  // The header's three are a subset of the adjustable set, never a separate
  // vocabulary: a name here that no axis matches would render nothing.
  it("names header-switcher axes that exist in the config", async () => {
    const { themeConfig, SWITCHER_AXES } = await importFresh()
    for (const axis of SWITCHER_AXES) {
      expect(themeConfig.switcher.axes[axis]).toBe(true)
    }
  })

  it("keeps darkmem's own default look", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.defaults).toMatchObject({
      preset: "default",
      backgroundStyle: "solid",
      backgroundIntensity: "neutral",
      accentColor: "green",
      surfaceColor: "neutral",
      density: "cozy",
      fontSize: "medium",
      accentIntensity: "vivid",
      controlDepth: "recessed",
      elevation: "medium",
      buttonElevation: "flat",
      surfaceIntensity: "flat",
      outerGlow: "balanced",
      innerGlow: "balanced",
      radius: "rounded",
    })
  })

  // A value saved while every axis was adjustable must not keep applying
  // once its control is gone; the three adjustable axes keep theirs.
  it("scrubs persisted values for hidden axes only", async () => {
    window.localStorage.setItem("mode", "light")
    window.localStorage.setItem("theme-accent", "rose")
    window.localStorage.setItem("theme-surface-color", "teal")
    window.localStorage.setItem("theme-preset", "glass")
    window.localStorage.setItem("theme-density", "compact")
    window.localStorage.setItem("theme-control-depth", "flat")

    await importFresh()

    expect(window.localStorage.getItem("mode")).toBe("light")
    expect(window.localStorage.getItem("theme-accent")).toBe("rose")
    expect(window.localStorage.getItem("theme-surface-color")).toBe("teal")
    expect(window.localStorage.getItem("theme-preset")).toBeNull()
    expect(window.localStorage.getItem("theme-density")).toBeNull()
    expect(window.localStorage.getItem("theme-control-depth")).toBeNull()
  })
})
