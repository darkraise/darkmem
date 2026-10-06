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
import { keepDialogOpenOnListEscape } from "../portal-overlays"

const ITEMS = [
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
]

function Harness({ guarded, triggerId }: { guarded: boolean; triggerId?: string }) {
  const [open, setOpen] = useState(true)
  return (
    <>
      <span>{open ? "dialog open" : "dialog closed"}</span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          onEscapeKeyDown={guarded ? keepDialogOpenOnListEscape : undefined}
        >
          <DialogTitle>Add git account</DialogTitle>
          <DialogDescription>probe</DialogDescription>
          <input aria-label="typed" defaultValue="half-typed token" />
          <Select defaultValue="github">
            <SelectTrigger aria-label="provider" id={triggerId}>
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

describe("keepDialogOpenOnListEscape", () => {
  it("without it, Escape on an open Select closes the whole dialog", async () => {
    render(<Harness guarded={false} />)
    const listbox = await openSelect()
    fireEvent.keyDown(listbox, { key: "Escape" })
    expect(await screen.findByText("dialog closed")).toBeInTheDocument()
  })

  it("closes only the Select, keeping the dialog and what was typed", async () => {
    render(<Harness guarded />)
    const listbox = await openSelect()
    fireEvent.keyDown(listbox, { key: "Escape" })
    await act(async () => {})
    expect(screen.getByRole("combobox", { name: "provider" })).toHaveAttribute(
      "aria-expanded",
      "false",
    )
    expect(screen.getByText("dialog open")).toBeInTheDocument()
    expect(screen.getByLabelText("typed")).toHaveValue("half-typed token")

    // A second Escape, with nothing open, still closes the dialog.
    fireEvent.keyDown(screen.getByRole("combobox", { name: "provider" }), {
      key: "Escape",
    })
    expect(await screen.findByText("dialog closed")).toBeInTheDocument()
  })

  it("finds a trigger given its own id for a label", async () => {
    // The list's aria-labelledby keeps naming the generated id, which no
    // element carries once the trigger has its own (Add git account).
    render(<Harness guarded triggerId="git-account-provider" />)
    const listbox = await openSelect()
    fireEvent.keyDown(listbox, { key: "Escape" })
    await act(async () => {})
    expect(screen.getByText("dialog open")).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "provider" })).toHaveAttribute(
      "aria-expanded",
      "false",
    )
  })

  it("closes only an open Combobox list", async () => {
    render(<Harness guarded />)
    const input = screen.getByRole("combobox", { name: "model" })
    fireEvent.focus(input)
    fireEvent.click(input)
    expect(input).toHaveAttribute("aria-expanded", "true")
    fireEvent.keyDown(input, { key: "Escape" })
    await act(async () => {})
    expect(input).toHaveAttribute("aria-expanded", "false")
    expect(screen.getByText("dialog open")).toBeInTheDocument()
  })
})
