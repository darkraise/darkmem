import type { ThemeConfig, ThemeSettings } from "darkraise-ui/theme"

/**
 * Hiding an axis in `switcher.axes` removes its control and nothing else.
 *
 * The library's own `hiddenCommonAxes` neutralisation is a *preset* mechanism
 * (a preset that reinterprets a surface hides and neutralises the axis it
 * supersedes) and never reads the switcher config, so a value persisted while
 * an axis was still adjustable keeps applying after it is hidden — with no
 * control left to undo it. These helpers close that: a hidden axis is pinned
 * to the configured default on both paths a value can arrive by, the API row
 * and localStorage.
 */

/**
 * Where the provider persists each axis. Mirrors the `LS_*` constants in
 * darkraise-ui's ThemeProvider, which are not exported; the spellings are not
 * mechanical (`accentColor` is `theme-accent`, `backgroundStyle` is
 * `theme-bg-style`), so this cannot be derived from the axis name.
 *
 * `accentIntensity` carries two keys because v6.3 renamed the axis and the
 * library still migrates the old spelling — scrubbing only the new one would
 * let the pre-rename value survive and be re-migrated over the pin.
 *
 * `presetAxes` is deliberately absent: its keys are `theme-<preset>-<axis>`,
 * and the pinned `default` preset declares no axes at all, so there is nothing
 * to scrub. A preset that owns axes would need its own entry here.
 */
const AXIS_STORAGE_KEYS: Partial<Record<string, readonly string[]>> = {
  accentColor: ["theme-accent"],
  surfaceColor: ["theme-surface-color"],
  preset: ["theme-preset"],
  backgroundStyle: ["theme-bg-style"],
  backgroundIntensity: ["theme-bg-intensity"],
  gradientPattern: ["theme-gradient-pattern"],
  mode: ["mode"],
  density: ["theme-density"],
  elevation: ["theme-elevation"],
  buttonElevation: ["theme-button-elevation"],
  surfaceIntensity: ["theme-surface-intensity"],
  radius: ["theme-radius"],
  fontSize: ["theme-font-size"],
  accentIntensity: ["theme-accent-intensity", "theme-accent-vibrancy"],
  outerGlow: ["theme-outer-glow"],
  innerGlow: ["theme-inner-glow"],
}

/** The axes whose switcher control is turned off, in config order. */
export function hiddenAxes(config: ThemeConfig): string[] {
  return Object.entries(config.switcher.axes)
    .filter(([, enabled]) => !enabled)
    .map(([axis]) => axis)
}

/**
 * Force every hidden axis back to its configured default.
 *
 * Applied to whatever the persistence adapter loaded, so a row written before
 * the axis was hidden cannot outvote the config.
 */
export function pinHiddenAxes(
  settings: ThemeSettings,
  config: ThemeConfig,
): ThemeSettings {
  const defaults = config.defaults as unknown as Record<string, unknown>
  const pinned: Record<string, unknown> = { ...settings }
  for (const axis of hiddenAxes(config)) {
    if (axis === "presetAxes") {
      // No default to pin to — the config carries no preset-axis values, so
      // dropping the stored ones is what hands each preset back its own.
      delete pinned.presetAxisValues
      continue
    }
    if (axis in defaults) pinned[axis] = defaults[axis]
  }
  return pinned as unknown as ThemeSettings
}

/**
 * Drop persisted localStorage values for hidden axes.
 *
 * Must run before the provider mounts: it seeds its initial state from these
 * keys, and a stale one would paint a frame — and then be written back as the
 * user's setting on the next save.
 */
export function scrubHiddenAxisStorage(config: ThemeConfig): void {
  if (typeof window === "undefined") return
  for (const axis of hiddenAxes(config)) {
    for (const key of AXIS_STORAGE_KEYS[axis] ?? []) {
      try {
        window.localStorage.removeItem(key)
      } catch {
        // A blocked or full localStorage is not a reason to fail boot; the
        // API-side pin in `pinHiddenAxes` still holds.
      }
    }
  }
}
