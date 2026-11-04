import type { AxisKey, ThemeConfig, ThemeSettings } from "darkraise-ui/theme"

/**
 * Hiding an axis in `switcher.axes` removes its control and nothing else, so a
 * value persisted while an axis was still adjustable keeps applying after it
 * is hidden — with no control left to undo it. These helpers close that: a hidden axis is pinned
 * to the configured default on both paths a value can arrive by, the API row
 * and localStorage.
 */

/**
 * Where the provider persists each axis. Mirrors each axis's `storageKey` in
 * darkraise-ui's axis registry, which the public entries do not export; the
 * spellings are not mechanical (`accentColor` is `theme-accent`,
 * `glassTransparency` is `theme-glass-opacity`), so this cannot be derived
 * from the axis name.
 *
 * Trailing keys are 6.x spellings the library migrates into the axis on first
 * load. The scrub runs before that migration, so scrubbing only the 7.0 key
 * would let the old value be migrated in over the pin. `preset` needs no
 * legacy entry: 6.x stored the style under `theme-preset`, which is scrubbed
 * as the preset's own key.
 */
const AXIS_STORAGE_KEYS: Partial<Record<AxisKey, readonly string[]>> = {
  mode: ["mode"],
  accentColor: ["theme-accent"],
  surfaceColor: ["theme-surface-color"],
  tintWithAccent: ["theme-tint-with-accent"],
  signalColor: ["theme-signal-color"],
  style: ["theme-style"],
  preset: ["theme-preset"],
  backgroundStyle: ["theme-bg-style"],
  backgroundIntensity: ["theme-bg-intensity", "theme-canvas-tint"],
  gradientPattern: ["theme-gradient-pattern"],
  glassTransparency: ["theme-glass-opacity", "theme-glassmorphism-opacity"],
  glassBlur: ["theme-glass-blur", "theme-glassmorphism-blur"],
  font: ["theme-font"],
  headingFont: ["theme-heading-font"],
  density: ["theme-density"],
  elevation: ["theme-elevation"],
  radius: ["theme-radius"],
  fontSize: ["theme-font-size"],
  contrast: ["theme-contrast", "theme-surface-intensity"],
  darkAccentChroma: [
    "theme-dark-accent-chroma",
    "theme-accent-intensity",
    "theme-accent-vibrancy",
  ],
  outerGlow: ["theme-outer-glow", "theme-glass-halo"],
  innerGlow: ["theme-inner-glow"],
  sidebarSelection: ["theme-sidebar-selection", "theme-sidebar-active-bar"],
}

/** The axes whose switcher control is turned off, in config order. */
export function hiddenAxes(config: ThemeConfig): AxisKey[] {
  return Object.entries(config.switcher.axes ?? {})
    .filter(([, enabled]) => !enabled)
    .map(([axis]) => axis as AxisKey)
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
  const defaults: Record<string, unknown> = config.defaults ?? {}
  const pinned: Record<string, unknown> = { ...settings }
  for (const axis of hiddenAxes(config)) {
    if (axis in defaults) pinned[axis] = defaults[axis]
  }
  return pinned as ThemeSettings
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
