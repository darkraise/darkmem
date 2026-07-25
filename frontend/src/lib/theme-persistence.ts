import {
  ACCENT_COLORS,
  BACKGROUND_STYLES,
  MODES,
  SURFACE_COLORS,
  type ThemePersistenceAdapter,
  type ThemeSettings,
} from "darkraise-ui/theme"
import { apiFetch } from "@/lib/api"
import { themeConfig } from "@/theme.config"
import { DEMO } from "@/demo/flag"

interface ThemeSettingsResponse {
  settings: Partial<ThemeSettings> | null
}

function pick<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T,
): T {
  return allowed.includes(value as T) ? (value as T) : fallback
}

// generateTokens indexes color scales by accent/surface value, so an
// out-of-range stored value must fall back per-field rather than crash the
// theme apply. Locked axes (see LOCKED_AXES in theme.config.ts) are forced
// back to defaults so an old DB row can't resurrect a hidden control's value.
function sanitize(stored: Partial<ThemeSettings>): ThemeSettings {
  const defaults = themeConfig.defaults
  return {
    ...defaults,
    ...stored,
    accentColor: pick(stored.accentColor, ACCENT_COLORS, defaults.accentColor),
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
    preset: defaults.preset,
    density: defaults.density,
    elevation: defaults.elevation,
    buttonElevation: defaults.buttonElevation,
    radius: defaults.radius,
  }
}

export const apiThemePersistence: ThemePersistenceAdapter = {
  async load() {
    const { settings } = await apiFetch<ThemeSettingsResponse>("/config/theme")
    return settings ? sanitize(settings) : null
  },
  async save(settings: ThemeSettings) {
    await apiFetch<ThemeSettingsResponse>("/config/theme", {
      method: "PUT",
      body: JSON.stringify({ settings }),
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
