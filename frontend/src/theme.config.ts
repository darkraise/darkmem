import type { ThemeConfig } from "darkraise-ui/theme"
import { scrubHiddenAxisStorage } from "@/lib/theme-hidden-axes"

export const themeConfig: ThemeConfig = {
  defaults: {
    accentColor: "green",
    surfaceColor: "indigo",
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
    outerGlow: "balanced",
    innerGlow: "balanced",
  },
  switcher: {
    enabled: true,
    // Three axes stay adjustable — light/dark and the two colour choices.
    // Everything else is a fixed part of darkmem's look and is pinned to the
    // default above rather than offered as a control.
    //
    // `gradientPattern` and `presetAxes` are hidden as consequences rather
    // than as choices of their own: a gradient pattern only paints when
    // `backgroundStyle` is `gradient`, which is pinned to `solid`, and the
    // pinned `default` preset declares no preset axes, so both controls would
    // render with nothing behind them.
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
      outerGlow: false,
      innerGlow: false,
      presetAxes: false,
    },
  },
}

// Runs at import, which is before `AppProviders` mounts the ThemeProvider:
// the provider seeds itself from localStorage, so a value persisted while an
// axis was still adjustable would otherwise keep applying with no control left
// to change it. The API-side half of the same pin is in `theme-persistence`.
scrubHiddenAxisStorage(themeConfig)
