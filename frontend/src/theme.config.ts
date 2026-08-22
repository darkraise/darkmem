import type { ThemeConfig } from "darkraise-ui/theme"
import { scrubHiddenAxisStorage } from "@/lib/theme-hidden-axes"

/**
 * The axes the header's popover switcher offers. Everything else is reachable
 * only from Settings → Appearance, which renders the library's full panel.
 *
 * This is a *presentation* split, not a pin: every axis below is genuinely
 * adjustable and persisted, so nothing here may be fed to `pinHiddenAxes` or
 * `scrubHiddenAxisStorage` — those exist for axes with no control anywhere.
 * `MinimalThemeSwitcher` is the only consumer.
 */
export const SWITCHER_AXES = ["mode", "accentColor", "surfaceColor"] as const

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
    controlDepth: "recessed",
    outerGlow: "balanced",
    innerGlow: "balanced",
  },
  switcher: {
    enabled: true,
    // Every axis is on, because this config gates BOTH surfaces the library
    // renders from it — the popover switcher and `ThemeSettingsPanel` — and
    // there is no per-instance override (no `axes` prop on either component,
    // and `ThemeContext` is not exported, so a scoped provider would fork the
    // theme state rather than narrow the view of it). Turning an axis off here
    // would remove it from the Appearance tab too.
    //
    // The header stays minimal instead through `MinimalThemeSwitcher`, which
    // renders only `SWITCHER_AXES` above; the shell's own switcher is turned
    // off in `routes/_authenticated.tsx`.
    //
    // `theme-config.test.ts` compares this key set against the library's own
    // default config, so an axis added by a future upgrade fails the build
    // instead of quietly never appearing.
    //
    // Persisting them is a two-sided contract: `ThemeSettingsPayload` in
    // backend/app/api/routes/config.py forbids unknown keys, so an axis
    // enabled here must exist there or every DB save 422s.
    axes: {
      mode: true,
      accentColor: true,
      surfaceColor: true,
      preset: true,
      backgroundStyle: true,
      backgroundIntensity: true,
      gradientPattern: true,
      density: true,
      elevation: true,
      buttonElevation: true,
      radius: true,
      fontSize: true,
      surfaceIntensity: true,
      accentIntensity: true,
      controlDepth: true,
      outerGlow: true,
      innerGlow: true,
      presetAxes: true,
    },
  },
}

// Inert while every axis is enabled, and deliberately kept armed: it is what
// stops a value persisted under an axis from outliving that axis's control if
// one is ever turned off again. Runs at import, which is before `AppProviders`
// mounts the ThemeProvider — the provider seeds itself from localStorage, so a
// stale value would otherwise paint a frame before anything could correct it.
// The API-side half of the same guard is in `theme-persistence`.
scrubHiddenAxisStorage(themeConfig)
