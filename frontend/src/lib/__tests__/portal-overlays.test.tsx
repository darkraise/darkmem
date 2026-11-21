import { act, fireEvent, render, screen } from "@testing-library/react"
import { useState } from "react"
import { describe, expect, it } from "vitest"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Combobox,
  ComboboxContent,
  ComboboxControl,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemText,
  ComboboxList,
} from "darkraise-ui/components/combobox"

const ITEMS = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
]

function Harness() {
  const [open, setOpen] = useState(true)
  return (
    <>
      <span>{open ? "dialog open" : "dialog closed"}</span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogTitle>Add git account</DialogTitle>
          <DialogDescription>probe</DialogDescription>
          <input aria-label="typed" defaultValue="half-typed token" />
          <Select defaultValue="github">
            <SelectTrigger aria-label="provider">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ITEMS.map((i) => (
                <SelectItem key={i.value} value={i.value}>
                  {i.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Combobox items={ITEMS} openOnClick openOnFocus>
            <ComboboxControl>
              <ComboboxInput aria-label="model" />
            </ComboboxControl>
            <ComboboxContent>
              <ComboboxList>
                {ITEMS.map((i) => (
                  <ComboboxItem key={i.value} item={i}>
                    <ComboboxItemText>{i.label}</ComboboxItemText>
                  </ComboboxItem>
                ))}
              </ComboboxList>
            </ComboboxContent>
          </Combobox>
        </DialogContent>
      </Dialog>
    </>
  )
}

async function openSelect() {
  fireEvent.click(screen.getByRole("combobox", { name: "provider" }))
  const listbox = await screen.findByRole("listbox")
  // The Select focuses its content on a microtask.
  await act(async () => {})
  return listbox
}

describe("Escape in a dialog with a list", () => {
  // darkraise-ui 6.6 closed the whole dialog here, and the app carried its own
  // Escape handler on every such dialog; 7.0 closes only the open list.
  it("the library closes only an open Select", async () => {
    render(<Harness />)
    const listbox = await openSelect()
    fireEvent.keyDown(listbox, { key: "Escape" })
    await act(async () => {})
    expect(screen.getByText("dialog open")).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "provider" })).toHaveAttribute(
      "aria-expanded",
      "false",
    )
  })

  it("the library closes only an open Combobox", async () => {
    render(<Harness />)
    const input = screen.getByRole("combobox", { name: "model" })
    fireEvent.focus(input)
    fireEvent.click(input)
    expect(input).toHaveAttribute("aria-expanded", "true")
    fireEvent.keyDown(input, { key: "Escape" })
    await act(async () => {})
    expect(input).toHaveAttribute("aria-expanded", "false")
    expect(screen.getByText("dialog open")).toBeInTheDocument()
  })

  it("a second Escape, with nothing open, closes the dialog", async () => {
    render(<Harness />)
    const listbox = await openSelect()
    fireEvent.keyDown(listbox, { key: "Escape" })
    await act(async () => {})
    expect(screen.getByLabelText("typed")).toHaveValue("half-typed token")

    fireEvent.keyDown(screen.getByRole("combobox", { name: "provider" }), {
      key: "Escape",
    })
    expect(await screen.findByText("dialog closed")).toBeInTheDocument()
  })
})
