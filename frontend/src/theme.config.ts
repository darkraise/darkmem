import type { ThemeConfig } from "darkraise-ui/theme"
import { scrubHiddenAxisStorage } from "@/lib/theme-hidden-axes"

/**
 * The only adjustable axes: light/dark, the two colours and whether the
 * surface takes the accent's tint. The header's
 * popover and Settings → Appearance both offer exactly these; every other axis
 * is a fixed part of darkmem's look, pinned to the default below and scrubbed
 * from storage by `pinHiddenAxes` / `scrubHiddenAxisStorage`.
 */
export const SWITCHER_AXES = [
  "mode",
  "accentColor",
  "surfaceColor",
  "tintWithAccent",
] as const

export const themeConfig: ThemeConfig = {
  defaults: {
    accentColor: "green",
    surfaceColor: "neutral",
    tintWithAccent: "off",
    signalColor: "none",
    // Quiet draws the app as a ledger: tint steps and 1px rules, no shadows.
    // Flat reads as tool panels, Tactile's bevels and full-width bar are
    // heavy for dense lists, and Glass's veiled top bar overlaps page
    // headers while its blur taxes the graph views.
    style: "quiet",
    preset: "base",
    backgroundStyle: "solid",
    backgroundIntensity: "neutral",
    gradientPattern: "blobs",
    glassTransparency: "medium",
    glassBlur: "medium",
    // Geist holds up best at the 11-12px of tags and labels and sits closest
    // to the JetBrains Mono that carries shas and timestamps.
    font: "geist",
    headingFont: "body",
    mode: "dark",
    density: "cozy",
    elevation: "standard",
    radius: "rounded",
    fontSize: "medium",
    contrast: "low",
    darkAccentChroma: "vivid",
    outerGlow: "balanced",
    innerGlow: "balanced",
    sidebarSelection: "auto",
  },
  switcher: {
    enabled: true,
    // Everything outside `SWITCHER_AXES` is off. This one config gates both
    // surfaces the library renders from it — the popover switcher and
    // `ThemeSettingsPanel` — so an axis off here is gone from the Appearance
    // tab too, which is the intent.
    //
    // `gradientPattern` and the two glass axes would be off regardless: a
    // gradient pattern only paints when `backgroundStyle` is `gradient`,
    // pinned to `solid`, and only the `glass` style reads the glass axes.
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
      tintWithAccent: true,
      signalColor: false,
      style: false,
      preset: false,
      backgroundStyle: false,
      backgroundIntensity: false,
      gradientPattern: false,
      glassTransparency: false,
      glassBlur: false,
      font: false,
      headingFont: false,
      density: false,
      elevation: false,
      radius: false,
      fontSize: false,
      contrast: false,
      darkAccentChroma: false,
      outerGlow: false,
      innerGlow: false,
      sidebarSelection: false,
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
