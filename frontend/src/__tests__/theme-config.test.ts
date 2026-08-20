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

  it("exposes every axis the library ships", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.switcher.enabled).toBe(true)
    for (const [axis, enabled] of Object.entries(themeConfig.switcher.axes)) {
      expect(enabled, `axis ${axis} is hidden`).toBe(true)
    }
  })

  // Drift guard: an axis added by a library upgrade would otherwise stay
  // absent from the switcher with nothing failing.
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
      accentColor: "indigo",
      surfaceColor: "slate",
      preset: "default",
      mode: "dark",
      density: "cozy",
      radius: "rounded",
    })
  })

  // Every axis is user-adjustable now, so importing the config must not
  // wipe persisted choices the way the locked-axis scrub used to.
  it("leaves persisted axis values alone on import", async () => {
    window.localStorage.setItem("theme-preset", "glass")
    window.localStorage.setItem("theme-density", "compact")
    window.localStorage.setItem("theme-outer-glow", "vivid")

    await importFresh()

    expect(window.localStorage.getItem("theme-preset")).toBe("glass")
    expect(window.localStorage.getItem("theme-density")).toBe("compact")
    expect(window.localStorage.getItem("theme-outer-glow")).toBe("vivid")
  })
})
