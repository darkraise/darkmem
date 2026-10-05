import { act, fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { Pencil } from "lucide-react"
import { IconButton } from "../icon-button"

/** Open, as opposed to absent or playing its exit (`data-state="closed"`). */
function shown(): boolean {
  return screen.queryByRole("tooltip")?.getAttribute("data-state") === "open"
}

describe("IconButton", () => {
  it("closes its tooltip on click and keeps it closed while the pointer stays", async () => {
    const onClick = vi.fn()
    render(<IconButton icon={Pencil} label="Edit" onClick={onClick} />)
    const button = screen.getByRole("button", { name: "Edit" })
    // Keyboard focus opens it (the trigger needs `:focus-visible`).
    await userEvent.setup().tab()
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Edit")

    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(shown()).toBe(false)

    // A pointerenter while still over the button (what a button gets when it
    // re-enables after its action) must not reopen it.
    fireEvent.pointerEnter(button, { pointerType: "mouse" })
    await act(() => new Promise((resolve) => setTimeout(resolve, 300)))
    expect(shown()).toBe(false)
  })
})
