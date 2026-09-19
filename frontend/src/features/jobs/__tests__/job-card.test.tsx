import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { JobGridCard } from "../components/job-grid-card"

function renderCard(key: string) {
  const job = useDemoStore.getState().jobs.find((j) => j.key === key)!
  render(
    <JobGridCard
      job={job}
      onTrigger={vi.fn()}
      onConfigure={vi.fn()}
      onHistory={vi.fn()}
      onToggleEnabled={vi.fn()}
    />,
  )
  return job
}

describe("JobGridCard", () => {
  it("expands its description on click", async () => {
    const job = renderCard("pipeline_failure_cleanup")
    const description = screen.getByRole("button", { name: job.description })
    expect(description).toHaveAttribute("aria-expanded", "false")
    expect(description).toHaveClass("line-clamp-2")
    await userEvent.click(description)
    expect(description).toHaveAttribute("aria-expanded", "true")
    expect(description).not.toHaveClass("line-clamp-2")
  })

  it("offers Run as an outline button", () => {
    renderCard("token_blocklist_cleanup")
    expect(screen.getByRole("button", { name: "Trigger now" })).toHaveAttribute(
      "data-variant",
      "outline",
    )
  })

  it("says failed in words beside a failed run's icon", () => {
    renderCard("expired_memory_cleanup")
    expect(screen.getByText("failed")).toBeInTheDocument()
  })
})
