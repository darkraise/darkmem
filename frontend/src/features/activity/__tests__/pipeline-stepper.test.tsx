import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useDemoStore } from "@/demo/store"
import { PipelineStepper } from "../components/pipeline-stepper"

describe("PipelineStepper", () => {
  it("is an ordered list that runs vertically below md and horizontally from md", () => {
    const run = useDemoStore.getState().pipelineRuns[0]!
    render(<PipelineStepper run={run} />)
    const list = screen.getByRole("list", { name: "Pipeline steps" })
    expect(list).toHaveClass("flex-col", "md:flex-row")
    expect(screen.getAllByRole("listitem")).toHaveLength(run.steps.length)
  })
})
