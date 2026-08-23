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
})
