import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { DemoContextPanel } from "../components/demo-context-panel"
import { DemoMessagePane } from "../components/demo-message-pane"
import { DemoThreadList } from "../components/demo-thread-list"
import { CURATED_CHAT_THREADS } from "@/demo/data-exports"

const rankingThread = CURATED_CHAT_THREADS.find(
  (t) => t.id === "thread-ranking",
)
const degradedThread = CURATED_CHAT_THREADS.find(
  (t) => t.id === "thread-cookie",
)
if (!rankingThread || !degradedThread) throw new Error("chat fixture missing")

const rankingContext = rankingThread.messages.find((m) => m.id === "m4")
  ?.context
const degradedContext = degradedThread.messages.find((m) => m.id === "m2")
  ?.context

describe("DemoContextPanel", () => {
  it("renders labelled rows with the shared honesty vocabulary", () => {
    render(<DemoContextPanel context={rankingContext} />)
    expect(screen.getByText("Context used for this turn")).toBeInTheDocument()
    expect(screen.getAllByText("L2 · fact").length).toBe(2)
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
    expect(screen.getByText("corroborated")).toBeInTheDocument()
    expect(screen.getByText("confirmed")).toBeInTheDocument()
    // exclusions are surfaced, never silently dropped
    expect(screen.getByText("1 row excluded")).toBeInTheDocument()
  })

  it("degraded turn keeps every surviving row plus the caution banner", () => {
    render(<DemoContextPanel context={degradedContext} />)
    expect(
      screen.getByText(
        "showing keyword-only results — semantic search unavailable",
      ),
    ).toBeInTheDocument()
    expect(screen.getAllByText(/channel: keyword/).length).toBe(2)
  })

  it("empty register says why: no turn has run", () => {
    render(<DemoContextPanel context={undefined} />)
    expect(screen.getByText("No context yet")).toBeInTheDocument()
  })
})

describe("DemoMessagePane", () => {
  it("new-conversation register offers starter chips", () => {
    const onSend = vi.fn()
    render(
      <DemoMessagePane
        thread={undefined}
        selectedTurnId={null}
        onSelectTurn={vi.fn()}
        onSend={onSend}
      />,
    )
    expect(
      screen.getByText("Ask about your memory, facts, or code"),
    ).toBeInTheDocument()
    screen
      .getByRole("button", { name: "Is the reranker on by default?" })
      .click()
    expect(onSend).toHaveBeenCalledWith("Is the reranker on by default?")
  })

  it("renders messages and the sources turn-meta line", () => {
    render(
      <DemoMessagePane
        thread={rankingThread}
        selectedTurnId="m4"
        onSelectTurn={vi.fn()}
        onSend={vi.fn()}
      />,
    )
    expect(
      screen.getByText("What does the supersession window default to?"),
    ).toBeInTheDocument()
    expect(
      screen.getByText("3 sources used this turn — see context panel"),
    ).toBeInTheDocument()
    expect(screen.queryByText("project: darkmem")).toBeNull()
  })
})

describe("DemoThreadList", () => {
  it("lists threads and reports message counts", () => {
    render(
      <DemoThreadList
        threads={CURATED_CHAT_THREADS}
        activeId="thread-ranking"
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    expect(
      screen.getByText("Retrieval & ranking questions"),
    ).toBeInTheDocument()
    expect(screen.getByText("4 msgs")).toBeInTheDocument()
  })

  it("lets its header wrap rather than clip the New button", () => {
    render(
      <DemoThreadList
        threads={CURATED_CHAT_THREADS}
        activeId="thread-ranking"
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: /new/i }).parentElement).toHaveClass("flex-wrap")
  })
})
