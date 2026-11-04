import type { ReactNode } from "react"
import { Monitor, Moon, Palette, Sun } from "lucide-react"
import {
  ACCENT_COLORS,
  MODES,
  SURFACE_COLORS,
  accentColors,
  useTheme,
} from "darkraise-ui/theme"
import type { SurfaceColor } from "darkraise-ui/theme"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "darkraise-ui/components/popover"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { useUiLabels } from "darkraise-ui/labels"
import { SWITCHER_AXES } from "@/theme.config"

const MODE_ICONS = { light: Sun, dark: Moon, system: Monitor } as const

/**
 * The 500 stop of every surface that has no accent scale behind it.
 *
 * LIBRARY GAP (darkraise-ui 6.6.0, still open in 7.0.0): the library holds
 * these scales in its own
 * `surfaceColors` map but exports only `accentColors`, so a swatch preview for
 * the neutral surfaces has no supported source. 6.4.0 shipped `slate` as the
 * only such surface and this was a single inline constant; 6.6.0 added eleven
 * more, which is what turned the missing export into a crash rather than a
 * one-line special case.
 *
 * Retire this the moment `surfaceColors` is exported from `darkraise-ui/theme`.
 * These values are previews only — nothing renders from them but the swatch —
 * so a library retune drifts the dot, never the theme.
 */
const NEUTRAL_SURFACE_PREVIEW: Record<string, string> = {
  slate: "215 16% 47%",
  gray: "220 9% 46%",
  cool: "210 9% 47%",
  zinc: "240 4% 46%",
  neutral: "0 0% 45%",
  iron: "22 4% 46%",
  mauve: "284 3% 46%",
  graphite: "210 3% 40%",
  stone: "25 5% 45%",
  sand: "36 8% 44%",
  olive: "70 5% 44%",
  sepia: "26 12% 42%",
}

/** Total over `SURFACE_COLORS`: anything the library adds later falls back
 *  to a visible grey instead of throwing on an undefined scale. */
function surfacePreviewHsl(color: SurfaceColor): string {
  return NEUTRAL_SURFACE_PREVIEW[color] ?? "0 0% 50%"
}

/** The library's own section shell, so this reads as the built-in popover. */
function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="dr-theme-switcher-row">
      <Label className="dr-theme-switcher-section-label">{label}</Label>
      {children}
    </div>
  )
}

/** "cool" -> "Cool": a swatch's only name is its title/aria-label. */
function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function SwatchGrid<T extends string>({
  values,
  active,
  onPick,
  previewHsl,
  columns,
  label,
}: {
  values: readonly T[]
  active: T
  onPick: (value: T) => void
  previewHsl: (value: T) => string
  /** Fixed column count, chosen so the grid fills whole rows. The library's
   *  `auto-fill` packs 9 a row, which leaves ragged last rows. */
  columns?: number
  label?: string
}) {
  return (
    <div
      className="dr-theme-switcher-swatch-grid"
      role="group"
      aria-label={label}
      style={
        columns
          ? { gridTemplateColumns: `repeat(${columns}, 1.5rem)` }
          : undefined
      }
    >
      {values.map((value) => (
        <button
          key={value}
          type="button"
          title={titleCase(value)}
          aria-label={titleCase(value)}
          aria-pressed={active === value}
          className="dr-theme-switcher-swatch"
          data-active={active === value ? "true" : undefined}
          style={{ backgroundColor: `hsl(${previewHsl(value)})` }}
          onClick={() => onPick(value)}
        />
      ))}
    </div>
  )
}

/**
 * The header's theme popover, narrowed to the axes in `SWITCHER_AXES`.
 *
 * LIBRARY GAP (darkraise-ui 6.4.0): the library's own `ThemeSwitcher` and
 * `ThemeSettingsPanel` both derive their sections from
 * `config.switcher.axes`, with no per-instance override — neither takes an
 * `axes` prop, and `ThemeContext` is not exported, so a scoped provider would
 * fork the theme state rather than narrow the view of it. darkmem needs two
 * views of one theme: this short popover in the header, and the full panel in
 * Settings → Appearance. The full panel is what requires every axis enabled in
 * the config, so the narrowing has to happen here.
 *
 * Retire this the moment the library accepts an axis list per instance —
 * `SWITCHER_AXES` is exactly the list to hand it.
 */
export function MinimalThemeSwitcher() {
  const labels = useUiLabels()
  const {
    mode,
    accentColor,
    surfaceColor,
    setMode,
    setAccentColor,
    setSurfaceColor,
    tintWithAccent,
    setTintWithAccent,
  } = useTheme()

  // Keyed by axis so `SWITCHER_AXES` drives what renders rather than merely
  // describing it — an axis moved out of that list leaves here with it.
  const sections: Record<(typeof SWITCHER_AXES)[number], ReactNode> = {
    mode: (
      <Row label={labels.theme.axisLabels.mode}>
        <ToggleGroup
          type="single"
          value={mode}
          onValueChange={(value) => {
            if (value) setMode(value as (typeof MODES)[number])
          }}
          variant="outline"
          size="sm"
          aria-label={labels.theme.axisLabels.mode}
          className="dr-theme-switcher-toggle-group"
          data-cols={MODES.length}
        >
          {MODES.map((value) => {
            const Icon = MODE_ICONS[value]
            return (
              <ToggleGroupItem key={value} value={value}>
                <Icon className="dr-theme-switcher-row-icon" />
                {labels.theme.modes[value]}
              </ToggleGroupItem>
            )
          })}
        </ToggleGroup>
      </Row>
    ),
    accentColor: (
      <Row label={labels.theme.axisLabels.accentColor}>
        <SwatchGrid
          values={ACCENT_COLORS}
          active={accentColor}
          onPick={setAccentColor}
          // The neutral accent has no scale of its own: it reads the surface.
          previewHsl={(color) =>
            color === "neutral"
              ? surfacePreviewHsl(surfaceColor)
              : accentColors[color][500]
          }
        />
      </Row>
    ),
    surfaceColor: (
      <Row label={labels.theme.axisLabels.surfaceColor}>
        <SwatchGrid
          label={labels.theme.axisLabels.surfaceColor}
          values={SURFACE_COLORS}
          active={surfaceColor}
          onPick={setSurfaceColor}
          previewHsl={surfacePreviewHsl}
          columns={6}
        />
      </Row>
    ),
    // 6.x offered the accents as tinted surfaces; 7.0 tints any neutral with
    // the accent instead, and the library skips the tint under the neutral
    // accent.
    tintWithAccent: (
      <Row label={labels.theme.axisLabels.tintWithAccent}>
        <Switch
          checked={tintWithAccent === "on"}
          disabled={accentColor === "neutral"}
          onCheckedChange={(on) => setTintWithAccent(on ? "on" : "off")}
          aria-label={labels.theme.axisLabels.tintWithAccent}
        />
      </Row>
    ),
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon">
          <Palette className="size-[var(--icon-size)]" />
          <span className="sr-only">{labels.theme.triggerLabel}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        role="dialog"
        aria-label={labels.theme.title}
        className="dr-theme-settings w-[34rem] max-w-[calc(100vw-2rem)] space-y-2"
        data-layout="compact"
      >
        {SWITCHER_AXES.map((axis) => (
          <div key={axis}>{sections[axis]}</div>
        ))}
      </PopoverContent>
    </Popover>
  )
}
