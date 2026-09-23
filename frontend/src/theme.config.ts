import type { ThemeConfig } from "darkraise-ui/theme"
import { scrubHiddenAxisStorage } from "@/lib/theme-hidden-axes"

/**
 * The only adjustable axes: light/dark and the two colours. The header's
 * popover and Settings → Appearance both offer exactly these; every other axis
 * is a fixed part of darkmem's look, pinned to the default below and scrubbed
 * from storage by `pinHiddenAxes` / `scrubHiddenAxisStorage`.
 */
export const SWITCHER_AXES = ["mode", "accentColor", "surfaceColor"] as const

export const themeConfig: ThemeConfig = {
  defaults: {
    accentColor: "green",
    surfaceColor: "neutral",
    preset: "default",
    backgroundStyle: "solid",
    backgroundIntensity: "neutral",
    gradientPattern: "blobs",
    mode: "dark",
    density: "cozy",
    elevation: "medium",
    buttonElevation: "flat",
    radius: "rounded",
    fontSize: "medium",
    surfaceIntensity: "flat",
    accentIntensity: "vivid",
    controlDepth: "recessed",
    outerGlow: "balanced",
    innerGlow: "balanced",
  },
  switcher: {
    enabled: true,
    // Everything outside `SWITCHER_AXES` is off. This one config gates both
    // surfaces the library renders from it — the popover switcher and
    // `ThemeSettingsPanel` — so an axis off here is gone from the Appearance
    // tab too, which is the intent.
    //
    // `gradientPattern` and `presetAxes` would be off regardless: a gradient
    // pattern only paints when `backgroundStyle` is `gradient`, pinned to
    // `solid`, and the pinned `default` preset declares no preset axes.
    //
    // `theme-config.test.ts` compares this key set against the library's own
    // default config, so an axis added by a future upgrade fails the build
    // instead of quietly never appearing — and it must then be decided on
    // here, not defaulted into visibility.
    //
    // Persisting them is a two-sided contract: `ThemeSettingsPayload` in
    // backend/app/api/routes/config.py forbids unknown keys, so an axis
    // enabled here must exist there or every DB save 422s.
    axes: {
      mode: true,
      accentColor: true,
      surfaceColor: true,
      preset: false,
      backgroundStyle: false,
      backgroundIntensity: false,
      gradientPattern: false,
      density: false,
      elevation: false,
      buttonElevation: false,
      radius: false,
      fontSize: false,
      surfaceIntensity: false,
      accentIntensity: false,
      controlDepth: false,
      outerGlow: false,
      innerGlow: false,
      presetAxes: false,
    },
  },
}

// Drops values persisted under the hidden axes — above all from the period when
// every axis was adjustable — so none outlives its control. Runs at import,
// which is before `AppProviders` mounts the ThemeProvider — the provider seeds
// itself from localStorage, so a stale value would otherwise paint a frame
// before anything could correct it.
// The API-side half of the same guard is in `theme-persistence`.
scrubHiddenAxisStorage(themeConfig)
