import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { Accordion } from "darkraise-ui/components/accordion"
import { HelpTip } from "../help-tip"
import { DetailSection } from "@/features/knowledge/components/detail-section"

describe("HelpTip", () => {
  it("keeps the explanation off the page until the icon is focused", async () => {
    render(<HelpTip label="About w_conf">confidence weighting rule</HelpTip>)
    expect(
      screen.queryByText("confidence weighting rule"),
    ).not.toBeInTheDocument()
    fireEvent.focus(screen.getByRole("button", { name: "About w_conf" }))
    // The tooltip opens after its 150ms hover/focus delay.
    expect(
      await screen.findByText("confidence weighting rule"),
    ).toBeInTheDocument()
  })
})

describe("DetailSection", () => {
  it("collapses by default and discloses on demand; meta stays visible", () => {
    render(
      <Accordion type="multiple" defaultValue={["open-one"]}>
        <DetailSection value="open-one" title="Sources" meta="3 distinct origins">
          <span>source rows</span>
        </DetailSection>
        <DetailSection value="closed-one" title="Verification ladder" meta="4 events">
          <span>ladder rows</span>
        </DetailSection>
      </Accordion>,
    )
    // The default-open section is disclosed; the other is not.
    expect(screen.getByText("source rows")).toBeInTheDocument()
    expect(screen.queryByText("ladder rows")).not.toBeInTheDocument()
    // Collapsed rows still show their honest summary meta.
    expect(screen.getByText("4 events")).toBeInTheDocument()
    fireEvent.click(
      screen.getByRole("button", { name: /Verification ladder/ }),
    )
    expect(screen.getByText("ladder rows")).toBeInTheDocument()
  })
})
