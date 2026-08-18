import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ProcessPanel } from "../process-panel"
import type { CodeProcess } from "../../lib/code-processes"

const PROCESSES: CodeProcess[] = [
  {
    id: "process:main::app.py",
    label: "main",
    entryNodeId: "main::app.py",
    entryKind: "function",
    entryFile: "app.py",
    steps: [
      { index: 1, nodeId: "main::app.py", label: "main", kind: "function", file: "app.py" },
      { index: 2, nodeId: "save::db.py", label: "save", kind: "method", file: "db.py" },
      { index: 3, nodeId: "render::ui.py", label: "render", kind: "function", file: "ui.py" },
    ],
    nodeIds: ["main::app.py", "save::db.py", "render::ui.py"],
    stepCount: 3,
  },
  {
    id: "process:boot::cli.py",
    label: "boot",
    entryNodeId: "boot::cli.py",
    entryKind: "function",
    entryFile: "cli.py",
    steps: [
      { index: 1, nodeId: "boot::cli.py", label: "boot", kind: "function", file: "cli.py" },
    ],
    nodeIds: ["boot::cli.py"],
    stepCount: 1,
  },
]

function renderPanel(
  overrides: Partial<Parameters<typeof ProcessPanel>[0]> = {},
) {
  const onSelect = vi.fn()
  render(
    <ProcessPanel
      processes={PROCESSES}
      selectedProcessId={null}
      onSelect={onSelect}
      {...overrides}
    />,
  )
  return { onSelect }
}

describe("ProcessPanel", () => {
  it("renders a row per process with its label, step count, and entry meta", () => {
    renderPanel()
    expect(screen.getByText("main")).toBeInTheDocument()
    expect(screen.getByText("boot")).toBeInTheDocument()
    expect(screen.getByText("3 steps")).toBeInTheDocument()
    // Singular form for a one-step process.
    expect(screen.getByText("1 step")).toBeInTheDocument()
    // Entry kind/file shown muted; "function" appears for both rows.
    expect(screen.getAllByText("function").length).toBeGreaterThanOrEqual(1)
    // The file path sits in the same span as the kind/separator, so match on a
    // normalized substring rather than the exact text node.
    expect(
      screen.getByText((_, el) => el?.textContent === "function · app.py"),
    ).toBeInTheDocument()
  })

  it("fires onSelect with the clicked process", async () => {
    const user = userEvent.setup()
    const { onSelect } = renderPanel()

    await user.click(screen.getByText("main"))

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(PROCESSES[0])
  })

  it("shows the empty state when no processes are detected", () => {
    renderPanel({ processes: [] })
    expect(screen.getByText("No execution flows")).toBeInTheDocument()
  })
})
