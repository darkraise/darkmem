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
  },
  switcher: {
    enabled: true,
    axes: {
      mode: true,
      accentColor: true,
      surfaceColor: true,
      preset: false,
      backgroundStyle: true,
      backgroundIntensity: true,
      gradientPattern: true,
      density: false,
      elevation: false,
      buttonElevation: false,
      radius: false,
      presetAxes: true,
    },
  },
}

// Axes hidden from the switcher and pinned to `defaults`, mapped to the
// ThemeProvider localStorage key each one persists under. The provider
// initializes from localStorage over `defaults` and re-applies DB-loaded
// settings over both, so a value persisted before an axis was hidden would
// stick forever with no UI to change it back — every persistence channel
// (localStorage below, DB in lib/theme-persistence.ts) must scrub these.
// Keep in sync with the axes disabled above.
export const LOCKED_AXES = {
  preset: "theme-preset",
  density: "theme-density",
  elevation: "theme-elevation",
  buttonElevation: "theme-button-elevation",
  radius: "theme-radius",
} as const

try {
  for (const key of Object.values(LOCKED_AXES)) {
    window.localStorage.removeItem(key)
  }
} catch {
  // Storage unavailable (e.g. blocked); the provider falls back to defaults.
}
