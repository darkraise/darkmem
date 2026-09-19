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

  // Every axis is adjustable, because this one config gates both surfaces the
  // library renders from it — the popover switcher and `ThemeSettingsPanel` —
  // and turning an axis off here would remove it from Settings → Appearance
  // too. The header's narrowing lives in `MinimalThemeSwitcher`.
  it("leaves every library axis adjustable", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.switcher.enabled).toBe(true)
    const off = Object.entries(themeConfig.switcher.axes)
      .filter(([, enabled]) => !enabled)
      .map(([axis]) => axis)
    expect(off).toEqual([])
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

  // The scrub is inert while nothing is hidden, and stays wired so that
  // hiding an axis again cannot leave a value applying with no control.
  it("leaves persisted values alone while every axis is adjustable", async () => {
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
    expect(window.localStorage.getItem("theme-preset")).toBe("glass")
    expect(window.localStorage.getItem("theme-density")).toBe("compact")
    expect(window.localStorage.getItem("theme-control-depth")).toBe("flat")
  })
})
