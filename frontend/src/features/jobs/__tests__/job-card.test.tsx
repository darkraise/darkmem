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
  it("expands a clamped description from a visible more/less control", async () => {
    // jsdom does no layout: report the clamped description as overflowing.
    const spy = vi
      .spyOn(HTMLElement.prototype, "scrollHeight", "get")
      .mockReturnValue(100)
    const job = renderCard("pipeline_failure_cleanup")
    const description = screen.getByRole("button", {
      name: new RegExp(job.description.slice(0, 20)),
    })
    expect(description).toHaveAttribute("aria-expanded", "false")
    expect(description).toHaveClass("cursor-pointer")
    expect(description).toHaveTextContent(/more$/)
    expect(screen.getByText(job.description)).toHaveClass("line-clamp-2")
    await userEvent.click(description)
    expect(description).toHaveAttribute("aria-expanded", "true")
    expect(description).toHaveTextContent(/less$/)
    expect(screen.getByText(job.description)).not.toHaveClass("line-clamp-2")
    spy.mockRestore()
  })

  it("leaves a description that fits as plain text", () => {
    const job = renderCard("pipeline_failure_cleanup")
    expect(screen.getByText(job.description).closest("button")).toBeNull()
  })

  it("marks a disabled job in words, not only by its switch", () => {
    const job = useDemoStore.getState().jobs.find((j) => j.key === "repo_sync")!
    render(
      <JobGridCard
        job={{ ...job, enabled: false }}
        onTrigger={vi.fn()}
        onConfigure={vi.fn()}
        onHistory={vi.fn()}
        onToggleEnabled={vi.fn()}
      />,
    )
    expect(screen.getByText("disabled")).toBeInTheDocument()
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
