import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import type { ModelPriceRow } from "@/hooks/api"
import { ModelPricesPanel } from "../components/model-prices-panel"

const ROWS: ModelPriceRow[] = [
  {
    model: "deepseek-v4-flash",
    input_micros_per_mtok: 270_000,
    cached_micros_per_mtok: 14_000,
    output_micros_per_mtok: 1_100_000,
    overridden: false,
  },
]

describe("ModelPricesPanel", () => {
  it("renders rates in dollars per million tokens", () => {
    render(<ModelPricesPanel models={ROWS} onSave={vi.fn()} />)
    expect(screen.getByLabelText(/Input rate/i)).toHaveValue("0.27")
  })

  it("sends micro-USD integers, not the dollars it displays", () => {
    // Money is an integer end to end; a float reaching the wire is the bug
    // this asserts against.
    const onSave = vi.fn()
    render(<ModelPricesPanel models={ROWS} onSave={onSave} />)
    fireEvent.change(screen.getByLabelText(/Input rate/i), {
      target: { value: "0.55" },
    })
    fireEvent.click(screen.getByRole("button", { name: /save prices/i }))
    expect(onSave).toHaveBeenCalledWith({
      "deepseek-v4-flash": {
        input_micros_per_mtok: 550_000,
        cached_micros_per_mtok: 14_000,
        output_micros_per_mtok: 1_100_000,
      },
    })
  })

  it("marks a model whose rate the operator has changed", () => {
    render(
      <ModelPricesPanel models={[{ ...ROWS[0]!, overridden: true }]} onSave={vi.fn()} />,
    )
    expect(screen.getByText(/overridden/i)).toBeInTheDocument()
  })

  it("offers the unpriced models as rows and sends only the ones filled in", () => {
    // The overview says "add a rate under Prices" for these; the table had no
    // row for them and no way to add one.
    const onSave = vi.fn()
    render(
      <ModelPricesPanel
        models={ROWS}
        unpricedModels={["qwen2.5:3b", "qwen3:4b"]}
        onSave={onSave}
      />,
    )
    for (const [label, value] of [
      ["qwen2.5:3b Input rate", "0.1"],
      ["qwen2.5:3b Cached rate", "0"],
      ["qwen2.5:3b Output rate", "0.2"],
    ] as const) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole("button", { name: /save prices/i }))
    const sent = onSave.mock.calls[0]![0]
    expect(sent["qwen2.5:3b"]).toEqual({
      input_micros_per_mtok: 100_000,
      cached_micros_per_mtok: 0,
      output_micros_per_mtok: 200_000,
    })
    // Untouched, so not priced at zero.
    expect(sent["qwen3:4b"]).toBeUndefined()
  })

  it("sends existing overrides and edits, never an untouched shipped default", () => {
    // The PUT replaces the override layer: an untouched default sent along
    // would be stored as an override and stop following the shipped rate.
    const onSave = vi.fn()
    const kept = { ...ROWS[0]!, model: "gpt-5.5", overridden: true }
    const untouched = { ...ROWS[0]!, model: "nomic-embed-text:latest" }
    render(
      <ModelPricesPanel
        models={[...ROWS, kept, untouched]}
        unpricedModels={["qwen2.5:3b"]}
        onSave={onSave}
      />,
    )
    fireEvent.change(screen.getByLabelText("qwen2.5:3b Input rate"), {
      target: { value: "0.1" },
    })
    fireEvent.change(screen.getByLabelText("qwen2.5:3b Cached rate"), {
      target: { value: "0" },
    })
    fireEvent.change(screen.getByLabelText("qwen2.5:3b Output rate"), {
      target: { value: "0.2" },
    })
    // Retyping the shipped rate is no edit.
    fireEvent.change(screen.getByLabelText("deepseek-v4-flash Input rate"), {
      target: { value: "0.270" },
    })
    fireEvent.click(screen.getByRole("button", { name: /save prices/i }))
    expect(Object.keys(onSave.mock.calls[0]![0]).sort()).toEqual([
      "gpt-5.5",
      "qwen2.5:3b",
    ])
  })

  it("shows an unpriced model's rates as empty, not as zero", () => {
    render(
      <ModelPricesPanel models={ROWS} unpricedModels={["qwen3:4b"]} onSave={vi.fn()} />,
    )
    expect(screen.getByLabelText("qwen3:4b Input rate")).toHaveValue("")
    expect(screen.getByLabelText("qwen3:4b Input rate")).toHaveAttribute(
      "placeholder",
      "not priced",
    )
    // Untouched, so it does not block the save.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("adds any model by name", () => {
    render(<ModelPricesPanel models={ROWS} onSave={vi.fn()} />)
    fireEvent.change(screen.getByLabelText("Model to price"), {
      target: { value: "my-local-model" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Add model" }))
    expect(screen.getByLabelText("my-local-model Input rate")).toBeInTheDocument()
  })

  it("refuses a rate that is not a number before it reaches the server", () => {
    const onSave = vi.fn()
    render(<ModelPricesPanel models={ROWS} onSave={onSave} />)
    fireEvent.change(screen.getByLabelText(/Input rate/i), {
      target: { value: "abc" },
    })
    expect(screen.getByRole("alert")).toHaveTextContent(/must be a number/)
    expect(screen.getByRole("button", { name: /save prices/i })).toBeDisabled()
  })
})
