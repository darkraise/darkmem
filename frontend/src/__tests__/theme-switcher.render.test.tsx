import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"
import { ThemeProvider, ThemeSwitcher } from "darkraise-ui/theme"
import { themeConfig } from "@/theme.config"

// The switcher's own section headings, keyed by axis. Locally spelled
// because the library keeps its label table internal; a rename there turns
// into a failure here, which is the point.
const AXIS_HEADINGS: Record<string, string> = {
  mode: "Mode",
  accentColor: "Accent Color",
  surfaceColor: "Surface Color",
  preset: "Preset",
  backgroundStyle: "Background",
  backgroundIntensity: "Background Intensity",
  density: "Density",
  elevation: "Elevation",
  buttonElevation: "Button Elevation",
  surfaceIntensity: "Surface Intensity",
  radius: "Radius",
  fontSize: "Font Size",
  accentIntensity: "Accent Intensity",
  outerGlow: "Outer Glow",
  innerGlow: "Inner Glow",
}

// Conditional on another axis rather than on config, so it is asserted
// separately instead of being counted as missing.
const GRADIENT_PATTERN_HEADING = "Gradient Pattern"

async function openSwitcher() {
  const user = userEvent.setup()
  render(
    <ThemeProvider config={themeConfig}>
      <ThemeSwitcher />
    </ThemeProvider>,
  )
  await user.click(screen.getByRole("button"))
  return user
}

describe("theme switcher", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("renders a control for every configured axis", async () => {
    await openSwitcher()
    for (const [axis, heading] of Object.entries(AXIS_HEADINGS)) {
      expect(
        screen.queryByText(heading),
        `axis ${axis} has no control in the switcher`,
      ).toBeInTheDocument()
    }
  })

  it("discloses the gradient pattern once the background is a gradient", async () => {
    const user = await openSwitcher()
    expect(screen.queryByText(GRADIENT_PATTERN_HEADING)).not.toBeInTheDocument()
    await user.click(screen.getByText("Gradient"))
    expect(screen.getByText(GRADIENT_PATTERN_HEADING)).toBeInTheDocument()
  })

  // The heading table above is only a proof of coverage while it names every
  // axis the config enables; `presetAxes` is excluded because it is a master
  // toggle for per-preset controls, not an axis with a heading of its own.
  it("covers every enabled axis", async () => {
    const enabled = Object.entries(themeConfig.switcher.axes)
      .filter(([axis, on]) => on && axis !== "presetAxes")
      .map(([axis]) => axis)
    expect(enabled.sort()).toEqual(
      [...Object.keys(AXIS_HEADINGS), "gradientPattern"].sort(),
    )
  })
})
