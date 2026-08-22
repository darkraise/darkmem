import type { ReactNode } from "react"
import { Monitor, Moon, Palette, Sun } from "lucide-react"
import {
  ACCENT_COLORS,
  MODES,
  SURFACE_COLORS,
  accentColors,
  useTheme,
} from "darkraise-ui/theme"
import type { AccentColor, SurfaceColor } from "darkraise-ui/theme"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
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

/** The library's own section shell, so this reads as the built-in popover. */
function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="dr-theme-switcher-row">
      <Label className="dr-theme-switcher-section-label">{label}</Label>
      {children}
    </div>
  )
}

function SwatchGrid<T extends string>({
  values,
  active,
  onPick,
  previewHsl,
}: {
  values: readonly T[]
  active: T
  onPick: (value: T) => void
  previewHsl: (value: T) => string
}) {
  return (
    <div className="dr-theme-switcher-swatch-grid">
      {values.map((value) => (
        <button
          key={value}
          type="button"
          title={value}
          aria-label={value}
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
    activePreset,
  } = useTheme()

  // Mirrors the library's own `mode` gate: a preset supporting a single mode
  // has already been switched to it, so the control offers no real choice.
  const modeLocked = activePreset.supportedModes?.length === 1

  // Keyed by axis so `SWITCHER_AXES` drives what renders rather than merely
  // describing it — an axis moved out of that list leaves here with it.
  const sections: Record<(typeof SWITCHER_AXES)[number], ReactNode> = {
    mode: modeLocked ? null : (
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
          previewHsl={(color) => accentColors[color][500]}
        />
      </Row>
    ),
    surfaceColor: (
      <Row label={labels.theme.axisLabels.surfaceColor}>
        <SwatchGrid
          values={SURFACE_COLORS}
          active={surfaceColor}
          onPick={setSurfaceColor}
          // `slate` is the one surface with no accent scale behind it; the
          // library hardcodes this preview grey for it.
          previewHsl={(color) =>
            color === "slate"
              ? "215 16% 47%"
              : accentColors[color as AccentColor & SurfaceColor][500]
          }
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
