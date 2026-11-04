import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"
import { ThemeProvider, ThemeSettingsPanel } from "darkraise-ui/theme"
import { MinimalThemeSwitcher } from "@/components/app-chrome/minimal-theme-switcher"
import { SWITCHER_AXES, themeConfig } from "@/theme.config"

// The switcher's own section headings, keyed by axis. Locally spelled
// because the library keeps its label table internal; a rename there turns
// into a failure here, which is the point.
const AXIS_HEADINGS: Record<string, string> = {
  mode: "Mode",
  accentColor: "Accent Color",
  surfaceColor: "Surface Color",
  tintWithAccent: "Tint With Accent",
  signalColor: "Signal Color",
  style: "Style",
  preset: "Preset",
  backgroundStyle: "Background",
  backgroundIntensity: "Background Intensity",
  gradientPattern: "Gradient Pattern",
  glassTransparency: "Transparency",
  glassBlur: "Backdrop Blur",
  font: "Font",
  headingFont: "Heading Font",
  density: "Density",
  elevation: "Elevation",
  radius: "Radius",
  fontSize: "Font Size",
  contrast: "Contrast",
  darkAccentChroma: "Dark Accent Chroma",
  outerGlow: "Outer Glow",
  innerGlow: "Inner Glow",
  sidebarSelection: "Sidebar Selection",
}

/** Fails loudly rather than silently asserting `undefined` is absent. */
function headingFor(axis: string): string {
  const heading = AXIS_HEADINGS[axis]
  if (!heading) throw new Error(`no heading spelled for axis ${axis}`)
  return heading
}

async function openSwitcher() {
  const user = userEvent.setup()
  render(
    <ThemeProvider config={themeConfig}>
      <MinimalThemeSwitcher />
    </ThemeProvider>,
  )
  await user.click(screen.getByRole("button"))
  return user
}

describe("header theme switcher", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("renders a control for each of its axes", async () => {
    await openSwitcher()
    for (const axis of SWITCHER_AXES) {
      expect(
        screen.queryByText(headingFor(axis)),
        `axis ${axis} has no control in the header switcher`,
      ).toBeInTheDocument()
    }
  })

  // The other half of the claim: this component's own section list, not only
  // the config, keeps the popover to its own axes.
  it("renders no control for any other axis", async () => {
    await openSwitcher()
    const headerAxes = new Set<string>(SWITCHER_AXES)
    for (const axis of Object.keys(AXIS_HEADINGS)) {
      if (headerAxes.has(axis)) continue
      expect(
        screen.queryByText(headingFor(axis)),
        `axis ${axis} leaked into the header switcher`,
      ).not.toBeInTheDocument()
    }
  })

  // The heading table above is only a proof of coverage while it names every
  // axis the config knows about.
  it("covers every configured axis", () => {
    const configured = Object.keys(themeConfig.switcher.axes ?? {})
    expect(configured.sort()).toEqual(Object.keys(AXIS_HEADINGS).sort())
  })
})

describe("appearance panel", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  function renderPanel() {
    render(
      <ThemeProvider config={themeConfig}>
        <ThemeSettingsPanel layout="page" />
      </ThemeProvider>,
    )
  }

  it("renders a control for each switcher axis", () => {
    renderPanel()
    for (const axis of SWITCHER_AXES) {
      expect(
        screen.queryAllByText(headingFor(axis)).length,
        `axis ${axis} has no control in the appearance panel`,
      ).toBeGreaterThan(0)
    }
  })

  // The pinned axes are gone from the tab, not merely from the header.
  it("renders no control for a pinned axis", () => {
    renderPanel()
    const adjustable = new Set<string>(SWITCHER_AXES)
    for (const axis of Object.keys(AXIS_HEADINGS)) {
      if (adjustable.has(axis)) continue
      expect(
        screen.queryByText(headingFor(axis)),
        `pinned axis ${axis} still has a control in the appearance panel`,
      ).not.toBeInTheDocument()
    }
  })
})
