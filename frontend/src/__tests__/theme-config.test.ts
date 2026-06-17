import { beforeEach, describe, expect, it, vi } from "vitest"

const HIDDEN_KEYS = [
  "theme-preset",
  "theme-density",
  "theme-elevation",
  "theme-button-elevation",
  "theme-radius",
]

async function importFresh() {
  vi.resetModules()
  return import("@/theme.config")
}

describe("theme.config", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("hides the locked axes from the switcher", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.switcher.axes.preset).toBe(false)
    expect(themeConfig.switcher.axes.density).toBe(false)
    expect(themeConfig.switcher.axes.elevation).toBe(false)
    expect(themeConfig.switcher.axes.buttonElevation).toBe(false)
    expect(themeConfig.switcher.axes.radius).toBe(false)
  })

  it("pins the locked axes to the agreed defaults", async () => {
    const { themeConfig } = await importFresh()
    expect(themeConfig.defaults.preset).toBe("default")
    expect(themeConfig.defaults.density).toBe("cozy")
    expect(themeConfig.defaults.elevation).toBe("medium")
    expect(themeConfig.defaults.buttonElevation).toBe("flat")
    expect(themeConfig.defaults.radius).toBe("rounded")
  })

  it("clears persisted values for hidden axes on import", async () => {
    for (const key of HIDDEN_KEYS) {
      window.localStorage.setItem(key, "stale")
    }
    window.localStorage.setItem("theme-accent", "rose")

    await importFresh()

    for (const key of HIDDEN_KEYS) {
      expect(window.localStorage.getItem(key)).toBeNull()
    }
    expect(window.localStorage.getItem("theme-accent")).toBe("rose")
  })
})
