import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { Cloud, Cpu } from "lucide-react"
import { IconSegmented, type IconSegmentedOption } from "../icon-segmented"

const OPTIONS: ReadonlyArray<IconSegmentedOption<"llm" | "local">> = [
  { value: "llm", label: "LLM-backed classifier", icon: Cloud },
  { value: "local", label: "In-process classifier", icon: Cpu },
]

function renderControl(value: "llm" | "local" = "local") {
  return render(
    <IconSegmented
      value={value}
      options={OPTIONS}
      onChange={vi.fn()}
      label="classifier_kind"
    />,
  )
}

describe("IconSegmented", () => {
  it("names every segment, since an icon carries no text of its own", () => {
    renderControl()
    for (const option of OPTIONS) {
      expect(screen.getByRole("radio", { name: option.label })).toBeInTheDocument()
    }
  })

  // `toBeChecked()` alone passed for weeks while nothing looked selected: the
  // tooltip trigger's own `data-state` (open/closed) was landing on the
  // segment and overwriting checked/unchecked, so the library's
  // `[data-state="checked"]` colour rule never matched. Accessible state and
  // painted state are different claims, so this asserts both.
  it("marks the checked segment in the attribute the styling keys on", () => {
    renderControl("local")
    const checked = screen.getByRole("radio", { name: "In-process classifier" })
    const other = screen.getByRole("radio", { name: "LLM-backed classifier" })

    expect(checked).toBeChecked()
    expect(checked).toHaveAttribute("data-state", "checked")
    expect(other).not.toBeChecked()
    expect(other.getAttribute("data-state")).not.toBe("checked")
  })

  it("renders the indicator pill that paints the selection", () => {
    const { container } = renderControl()
    expect(
      container.querySelector(".dr-segment-group-indicator"),
      "without the indicator the checked segment has no visible fill",
    ).not.toBeNull()
  })
})
