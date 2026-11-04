import {
  ACCENT_COLORS,
  BACKGROUND_STYLES,
  MODES,
  SURFACE_COLORS,
  type AccentColor,
  type SurfaceColor,
  type ThemePersistenceAdapter,
  type ThemeSettings,
} from "darkraise-ui/theme"
import { apiFetch } from "@/lib/api"
import { themeConfig } from "@/theme.config"
import { pinHiddenAxes } from "@/lib/theme-hidden-axes"
import { DEMO } from "@/lib/demo-flag"

interface ThemeSettingsResponse {
  settings: ThemeSettings | null
}

function pick<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T | undefined,
): T | undefined {
  return allowed.includes(value as T) ? (value as T) : fallback
}

// generateTokens indexes color scales by accent/surface value, so an
// out-of-range stored value must fall back per-field rather than crash the
// theme apply. The remaining axes only drive data attributes, and the
// provider validates the style and preset names itself, so they pass through
// as stored.
// A 6.x row (no `version`) may name an accent as its surface. The library
// would migrate that to zinc plus the accent tint, but the per-field fallback
// below runs first and would reset it to the default, losing the tint.
function liftTintedSurface(stored: ThemeSettings): ThemeSettings {
  const surface: unknown = stored.surfaceColor
  if (
    stored.version !== undefined ||
    SURFACE_COLORS.includes(surface as SurfaceColor) ||
    !ACCENT_COLORS.includes(surface as AccentColor)
  ) {
    return stored
  }
  return { ...stored, surfaceColor: "zinc", tintWithAccent: "on" }
}

function sanitize(raw: ThemeSettings): ThemeSettings {
  const stored = liftTintedSurface(raw)
  const defaults = themeConfig.defaults ?? {}
  // Hidden axes are pinned last, so a row written while an axis was still
  // adjustable cannot outvote the config it is now hidden by.
  return pinHiddenAxes(
    {
      ...defaults,
      ...stored,
      accentColor: pick(
        stored.accentColor,
        ACCENT_COLORS,
        defaults.accentColor,
      ),
      surfaceColor: pick(
        stored.surfaceColor,
        SURFACE_COLORS,
        defaults.surfaceColor,
      ),
      backgroundStyle: pick(
        stored.backgroundStyle,
        BACKGROUND_STYLES,
        defaults.backgroundStyle,
      ),
      mode: pick(stored.mode, MODES, defaults.mode),
    },
    themeConfig,
  )
}

export const apiThemePersistence: ThemePersistenceAdapter = {
  async load() {
    const { settings } = await apiFetch<ThemeSettingsResponse>("/config/theme")
    return settings ? sanitize(settings) : null
  },
  async save(settings: ThemeSettings, options) {
    await apiFetch<ThemeSettingsResponse>("/config/theme", {
      method: "PUT",
      body: JSON.stringify({ settings }),
      signal: options?.signal,
    })
  },
}

// Demo mode has no backend; the provider's own localStorage channel already
// persists theme state, so the DB adapter degrades to a no-op rather than
// hammering the dead proxy.
const demoPersistence: ThemePersistenceAdapter = {
  async load() {
    return null
  },
  async save() {},
}

export const themePersistence: ThemePersistenceAdapter = DEMO
  ? demoPersistence
  : apiThemePersistence
