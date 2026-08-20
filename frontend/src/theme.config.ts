import type { ThemeConfig } from "darkraise-ui/theme"

export const themeConfig: ThemeConfig = {
  defaults: {
    accentColor: "indigo",
    surfaceColor: "slate",
    preset: "default",
    backgroundStyle: "solid",
    backgroundIntensity: "balanced",
    gradientPattern: "blobs",
    mode: "dark",
    density: "cozy",
    elevation: "medium",
    buttonElevation: "flat",
    radius: "rounded",
    fontSize: "medium",
    // v6.3 renamed `accentVibrancy` to `accentIntensity` (same value set) and
    // added the surface-intensity and glow axes. All three sit at the
    // library's own defaults, so the upgrade changes nothing visually; the
    // presets that own a glow raise it themselves via `commonAxisDefaults`.
    surfaceIntensity: "balanced",
    accentIntensity: "balanced",
    outerGlow: "none",
    innerGlow: "none",
  },
  switcher: {
    enabled: true,
    // Every axis the library ships is user-adjustable. `theme-config.test.ts`
    // compares this key set against the library's own default config, so an
    // axis added by a future upgrade fails the build instead of quietly
    // never appearing in the switcher.
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
      outerGlow: true,
      innerGlow: true,
      presetAxes: true,
    },
  },
}
