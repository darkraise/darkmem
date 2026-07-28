import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ThemeSettings } from "darkraise-ui/theme"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
// The API adapter is tested directly: the default `themePersistence` export
// resolves to the demo no-op only when VITE_DEMO is explicitly "1" (real
// mode is the default since T1.58; unset, as under vitest, now means real).
import { apiThemePersistence as themePersistence } from "@/lib/theme-persistence"
import { themeConfig } from "@/theme.config"

const apiFetchMock = vi.mocked(apiFetch)

const storedSettings: ThemeSettings = {
  accentColor: "rose",
  surfaceColor: "teal",
  preset: "glass",
  backgroundStyle: "gradient",
  backgroundIntensity: "vivid",
  gradientPattern: "aurora",
  mode: "light",
  density: "compact",
  elevation: "high",
  buttonElevation: "high",
  radius: "pill",
}

describe("themePersistence.load", () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it("returns null when nothing is persisted", async () => {
    apiFetchMock.mockResolvedValue({ settings: null })
    await expect(themePersistence.load()).resolves.toBeNull()
    expect(apiFetchMock).toHaveBeenCalledWith("/config/theme")
  })

  it("keeps stored values for visible axes", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      accentColor: "rose",
      surfaceColor: "teal",
      backgroundStyle: "gradient",
      backgroundIntensity: "vivid",
      gradientPattern: "aurora",
      mode: "light",
    })
  })

  it("pins locked axes to defaults regardless of stored values", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      preset: themeConfig.defaults.preset,
      density: themeConfig.defaults.density,
      elevation: themeConfig.defaults.elevation,
      buttonElevation: themeConfig.defaults.buttonElevation,
      radius: themeConfig.defaults.radius,
    })
  })

  it("falls back per-field when a crash-capable value is unknown", async () => {
    apiFetchMock.mockResolvedValue({
      settings: {
        ...storedSettings,
        accentColor: "not-a-color",
        mode: "sepia",
      },
    })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      accentColor: themeConfig.defaults.accentColor,
      mode: themeConfig.defaults.mode,
      surfaceColor: "teal",
    })
  })

  it("fills missing fields from defaults", async () => {
    apiFetchMock.mockResolvedValue({
      settings: { accentColor: "emerald" },
    })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      accentColor: "emerald",
      surfaceColor: themeConfig.defaults.surfaceColor,
      backgroundStyle: themeConfig.defaults.backgroundStyle,
      mode: themeConfig.defaults.mode,
    })
  })
})

describe("themePersistence.save", () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
  })

  it("PUTs the settings wrapped in a settings envelope", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    await themePersistence.save(storedSettings)
    expect(apiFetchMock).toHaveBeenCalledWith("/config/theme", {
      method: "PUT",
      body: JSON.stringify({ settings: storedSettings }),
    })
  })
})
