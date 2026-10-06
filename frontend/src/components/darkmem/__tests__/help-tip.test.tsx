import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
    // Real keyboard focus, not a synthetic focus event: since darkraise-ui
    // v6.3 the trigger opens on focus only while `:focus-visible` matches,
    // which needs the element to actually hold focus.
    await userEvent.setup().tab()
    expect(screen.getByRole("button", { name: "About w_conf" })).toHaveFocus()
    // The tooltip opens after its 150ms hover/focus delay.
    expect(
      await screen.findByText("confidence weighting rule"),
    ).toBeInTheDocument()
  })
})

describe("HelpTip on touch", () => {
  // jsdom has no PointerEvent; a MouseEvent carrying pointerType is what the
  // tooltip's handlers read.
  const tap = (target: Element) => {
    const event = new MouseEvent("pointerdown", {
      bubbles: true,
      cancelable: true,
    })
    Object.defineProperty(event, "pointerType", { value: "touch" })
    act(() => {
      target.dispatchEvent(event)
    })
  }

  it("opens on a tap and closes on a second tap or a tap elsewhere", async () => {
    render(
      <>
        <HelpTip label="About w_conf">confidence weighting rule</HelpTip>
        <p>elsewhere</p>
      </>,
    )
    const trigger = screen.getByRole("button", { name: "About w_conf" })

    tap(trigger)
    expect(
      await screen.findByText("confidence weighting rule"),
    ).toBeInTheDocument()

    tap(trigger)
    // Closed is the trigger's state; the content lingers for its exit
    // animation, which jsdom never finishes.
    await waitFor(() => expect(trigger).toHaveAttribute("data-state", "closed"))

    tap(trigger)
    await waitFor(() => expect(trigger).toHaveAttribute("data-state", "open"))
    tap(screen.getByText("elsewhere"))
    // Closed is the trigger's state; the content lingers for its exit
    // animation, which jsdom never finishes.
    await waitFor(() => expect(trigger).toHaveAttribute("data-state", "closed"))
  })
})

describe("DetailSection", () => {
  it("collapses by default and discloses on demand; meta stays visible", () => {
    render(
      <Accordion type="multiple" defaultValue={["open-one"]}>
        <DetailSection
          value="open-one"
          title="Sources"
          meta="3 distinct origins"
        >
          <span>source rows</span>
        </DetailSection>
        <DetailSection
          value="closed-one"
          title="Verification ladder"
          meta="4 events"
        >
          <span>ladder rows</span>
        </DetailSection>
      </Accordion>,
    )
    // The default-open section is disclosed; the other is not.
    expect(screen.getByText("source rows")).toBeInTheDocument()
    expect(screen.queryByText("ladder rows")).not.toBeInTheDocument()
    // Collapsed rows still show their honest summary meta.
    expect(screen.getByText("4 events")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Verification ladder/ }))
    expect(screen.getByText("ladder rows")).toBeInTheDocument()
  })
})
