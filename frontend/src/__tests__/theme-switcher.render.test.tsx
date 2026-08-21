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
  gradientPattern: "Gradient Pattern",
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

  it("renders a control for every enabled axis", async () => {
    await openSwitcher()
    for (const [axis, on] of Object.entries(themeConfig.switcher.axes)) {
      const heading = AXIS_HEADINGS[axis]
      if (!on || axis === "presetAxes" || !heading) continue
      expect(
        screen.queryByText(heading),
        `axis ${axis} has no control in the switcher`,
      ).toBeInTheDocument()
    }
  })

  // The other half of the same claim, and the one that actually protects the
  // pin: a hidden axis whose control still rendered would let someone set a
  // value the persistence layer then scrubs, which reads as a broken control
  // rather than an absent one.
  it("renders no control for a hidden axis", async () => {
    await openSwitcher()
    for (const [axis, on] of Object.entries(themeConfig.switcher.axes)) {
      const heading = AXIS_HEADINGS[axis]
      if (on || axis === "presetAxes" || !heading) continue
      expect(
        screen.queryByText(heading),
        `hidden axis ${axis} still has a control in the switcher`,
      ).not.toBeInTheDocument()
    }
  })

  // The heading table above is only a proof of coverage while it names every
  // axis the config knows about; `presetAxes` is excluded because it is a
  // master toggle for per-preset controls, not an axis with a heading.
  it("covers every configured axis", async () => {
    const configured = Object.keys(themeConfig.switcher.axes).filter(
      (axis) => axis !== "presetAxes",
    )
    expect(configured.sort()).toEqual(Object.keys(AXIS_HEADINGS).sort())
  })
})
