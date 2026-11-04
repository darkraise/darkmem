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
  version: 7,
  accentColor: "rose",
  surfaceColor: "stone",
  tintWithAccent: "on",
  style: "glass",
  preset: "mica-desk",
  backgroundStyle: "gradient",
  backgroundIntensity: "vivid",
  gradientPattern: "aurora",
  mode: "light",
  density: "compact",
  elevation: "high",
  radius: "pill",
  fontSize: "large",
  contrast: "high",
  darkAccentChroma: "calm",
  font: "geist",
  outerGlow: "vivid",
  innerGlow: "subtle",
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

  it("keeps stored values for the adjustable axes", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      accentColor: "rose",
      surfaceColor: "stone",
      tintWithAccent: "on",
      mode: "light",
    })
  })

  // A row written while an axis was still adjustable must not outvote the
  // config that now hides it — there is no control left to correct it with.
  it("pins every hidden axis back to the default", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    const loaded = await themePersistence.load()
    for (const [axis, enabled] of Object.entries(
      themeConfig.switcher.axes ?? {},
    )) {
      if (enabled) continue
      expect(
        (loaded as unknown as Record<string, unknown>)[axis],
        `hidden axis ${axis} kept its stored value`,
      ).toBe((themeConfig.defaults as Record<string, unknown>)[axis])
    }
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
      surfaceColor: "stone",
    })
  })

  // 6.x offered accents as surfaces; 7.0 draws them as a neutral with the
  // accent's tint, which is what the library's own migration produces.
  it("turns a 6.x tinted surface into zinc with the tint on", async () => {
    apiFetchMock.mockResolvedValue({
      settings: { accentColor: "purple", surfaceColor: "indigo", mode: "dark" },
    })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      accentColor: "purple",
      surfaceColor: "zinc",
      tintWithAccent: "on",
    })
  })

  it("leaves a versioned row's surface to the per-field fallback", async () => {
    apiFetchMock.mockResolvedValue({
      settings: { version: 7, surfaceColor: "indigo" },
    })
    const loaded = await themePersistence.load()
    expect(loaded).toMatchObject({
      surfaceColor: themeConfig.defaults.surfaceColor,
      tintWithAccent: themeConfig.defaults.tintWithAccent,
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
      signal: undefined,
    })
  })

  // The provider abandons a save after 15 seconds; the signal lets the
  // abandoned request stop rather than land after a newer one.
  it("hands the provider's abort signal to the request", async () => {
    apiFetchMock.mockResolvedValue({ settings: storedSettings })
    const { signal } = new AbortController()
    await themePersistence.save(storedSettings, { signal })
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/config/theme",
      expect.objectContaining({ signal }),
    )
  })
})
