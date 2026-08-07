import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// L3 has no live channel: article synthesis ships behind G-D, which is open.
// The demo store seeds CURATED_ARTICLES unconditionally, and those fixtures
// carry `confirmed`/`corroborated` statuses, claim sentences and invented
// coverage ratios. Rendering them outside DEMO puts fabricated verified claims
// in front of a real reader, under page chrome promising that every claim
// links to a verified fact — while the backend's own defences (no article
// channel, a closed groundedness gate, a scan forbidding `grounded` literals
// under app/) all sit on the other side of the wire and never see this screen.
//
// So this is a guard, not a render test: it fails the build if the demo
// fixture becomes reachable in real mode again.
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))

import { ArticlesTab } from "../components/articles-tab"

describe("ArticlesTab outside DEMO", () => {
  it("serves no article and says why", () => {
    render(<ArticlesTab />)

    expect(screen.getByText("No articles yet")).toBeInTheDocument()
    expect(
      screen.getByText(/synthesis is not shipped yet/i),
    ).toBeInTheDocument()
  })

  it("renders no verification badge of any rung", () => {
    render(<ArticlesTab />)

    for (const rung of ["candidate", "corroborated", "confirmed", "disputed"]) {
      expect(screen.queryByText(rung)).not.toBeInTheDocument()
    }
  })

  it("renders no claim-support coverage figure", () => {
    render(<ArticlesTab />)

    expect(screen.queryByText(/claim-support coverage/i)).not.toBeInTheDocument()
  })
})
