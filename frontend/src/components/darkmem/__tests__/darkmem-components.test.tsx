import { render, screen } from "@testing-library/react"
import { describe, it, expect, beforeEach } from "vitest"
import { VerificationBadge } from "../verification-badge"
import { LayerChip } from "../layer-chip"
import { ExclusionStrip } from "../exclusion-strip"
import { WhyRetrievedTrace } from "../why-retrieved-trace"
import { useDetailLevel } from "../use-detail-level"

const TRACE = {
  channels: [
    { name: "semantic", fraction: 0.82 },
    { name: "keyword", fraction: 0.55 },
    { name: "ppr", fraction: null },
    { name: "rerank", fraction: 0.74, display: "7.4" },
  ],
  rrfScore: 0.0412,
  summary: "strong wording and keyword match.",
}

describe("VerificationBadge", () => {
  it("renders the ladder status verbatim", () => {
    render(<VerificationBadge status="corroborated" />)
    expect(screen.getByText("corroborated")).toBeInTheDocument()
  })
})

describe("LayerChip", () => {
  it("renders the layer with its name", () => {
    render(<LayerChip layer={2} />)
    expect(screen.getByText("L2 · fact")).toBeInTheDocument()
  })
})

describe("ExclusionStrip", () => {
  it("surfaces the exclusion count and reason", () => {
    render(
      <ExclusionStrip
        items={[
          {
            count: 3,
            unit: "facts",
            reason: "ranked below the context limit",
            tag: "by_result_limit",
          },
        ]}
      />,
    )
    expect(screen.getByText("3 facts excluded")).toBeInTheDocument()
    expect(screen.getByText(/ranked below the context limit/)).toBeInTheDocument()
  })

  it("renders nothing when there are no exclusions", () => {
    const { container } = render(<ExclusionStrip items={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe("WhyRetrievedTrace", () => {
  beforeEach(() => {
    useDetailLevel.setState({ level: "advanced" })
  })

  it("defaults to advanced and shows the score breakdown", () => {
    expect(useDetailLevel.getState().level).toBe("advanced")
    render(<WhyRetrievedTrace {...TRACE} />)
    expect(screen.getByText("semantic")).toBeInTheDocument()
    expect(screen.getByText("off")).toBeInTheDocument()
    expect(screen.getByText("rrf_score")).toBeInTheDocument()
    expect(screen.getByText("0.0412")).toBeInTheDocument()
  })

  it("collapses to the plain-language line in simple mode", () => {
    useDetailLevel.setState({ level: "simple" })
    render(<WhyRetrievedTrace {...TRACE} />)
    expect(screen.getByText("Why it ranked:")).toBeInTheDocument()
    expect(screen.queryByText("rrf_score")).not.toBeInTheDocument()
  })
})
