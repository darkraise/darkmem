import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

// T3.19 — the Distribution tab's **live** half. Its own file rather than an
// addition to `settings-tabs.test.tsx`, which is frozen at `DEMO: true` to pin
// the fixture-backed rendering; the same split the security and maintenance
// tabs already use. A live assertion in that file could not run at all.
// Keys have their own suite (api-keys-card.real.test.tsx); stubbing the card
// keeps these mocks answering only the distribution routes.
vi.mock("../components/api-keys-card", () => ({ ApiKeysCard: () => null }))
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import { DistributionTab } from "../components/distribution-tab"

function withQuery(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
}

// **Fixture values that cannot collide with `CURATED_DISTRIBUTION`.** They used
// to be byte-identical to the demo store's (`claude-code`/`CLAUDE.md`/
// `.cursor/rules/darkmem.mdc`), and the demo panel rendered on every install —
// so every assertion here resolved against a fixture on the first tick, before
// the live query settled. A review proved it by replacing the entire live
// target list with a placeholder: the test still passed. Distinct strings mean
// a match can only have come from the live half.
const STATE = {
  targets: [
    {
      tool: "test-tool-alpha",
      context_file: "ALPHA_CONTEXT.md",
      mcp_config: ".alpha/mcp.json",
    },
    {
      tool: "test-tool-beta",
      context_file: ".beta/rules/darkmem.mdc",
      mcp_config: ".beta/mcp.json",
    },
  ],
  rejected: [],
}

/** Wait for a marker only the live half can produce.
 *
 *  The second half of the same defect: `findByText` resolving on the first
 *  tick made every later `getByText`/`queryByText` a statement about a screen
 *  that had not rendered yet — so a *deleted* detail gate passed while only an
 *  *inverted* one failed. Gating on this heading makes the negative assertions
 *  mean what they say.
 */
const liveHalfRendered = () => screen.findByText("Managed block per target")

describe("Distribution tab — live", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "simple" })
  })

  it("shows each target's block path, read from the adapter registry", async () => {
    // The screen must show what the inject writer would actually use. A list
    // of its own would agree with itself and not with the system.
    vi.mocked(apiFetch).mockResolvedValue(STATE)

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(screen.getByText("test-tool-alpha")).toBeInTheDocument()
    expect(screen.getByText("ALPHA_CONTEXT.md")).toBeInTheDocument()
    expect(screen.getByText(".beta/rules/darkmem.mdc")).toBeInTheDocument()
  })

  it("claims no connect status or inject log it does not have", async () => {
    // The fixture panel rendered on every install, not only in demo: four
    // clients reporting "handshake ok" and an inject log of deliveries that
    // never happened, beside the live half, with nothing on screen telling
    // them apart.
    vi.mocked(apiFetch).mockResolvedValue(STATE)

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    // The inject log reads the journal, so its empty state is a measured
    // absence rather than a placeholder, and it is awaited rather than read
    // synchronously.
    expect(await screen.findByText(/No context has been pushed yet/)).toBeInTheDocument()
    expect(screen.queryByText(/handshake ok/)).not.toBeInTheDocument()
    expect(screen.queryByText(/last inject/)).not.toBeInTheDocument()
  })

  it("names a configured target the registry refused", async () => {
    // The reason used to reach the server log only, so an operator editing
    // `inject_adapters` watched their row vanish with no explanation on screen.
    vi.mocked(apiFetch).mockResolvedValue({
      ...STATE,
      rejected: [{ tool: "test-tool-gamma", reason: "not a project-relative path" }],
    })

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(screen.getByText("test-tool-gamma")).toBeInTheDocument()
    expect(screen.getByText(/not a project-relative path/)).toBeInTheDocument()
    expect(screen.getByText(/1 configured entry did not take effect/)).toBeInTheDocument()
  })

  it("states plainly when the targets could not be read", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))

    render(withQuery(<DistributionTab />))

    expect(
      await screen.findByText(/distribution settings could not be loaded/),
    ).toBeInTheDocument()
  })

  it("carries no token budget, watch switch or curb", async () => {
    // Nothing ever read the policy those three controls wrote, so the tab
    // keeps only what the registry answers.
    const calls: string[] = []
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      calls.push(url)
      if (url.includes("event_type=")) return { items: [], total: 0 } as never
      return STATE as never
    })

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(screen.getByText("test-tool-alpha")).toBeInTheDocument()
    expect(screen.queryByLabelText("Token budget")).not.toBeInTheDocument()
    expect(screen.queryByText(/token budget/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Watch mode")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Allow push")).not.toBeInTheDocument()

    for (const control of screen.queryAllByRole("switch")) fireEvent.click(control)
    for (const field of screen.queryAllByRole("spinbutton")) {
      fireEvent.change(field, { target: { value: "500" } })
      fireEvent.blur(field)
    }
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(calls.filter((url) => url.includes("/distribution/policy"))).toEqual([])
  })

  it("honours Simple/Advanced on the per-target detail", async () => {
    vi.mocked(apiFetch).mockResolvedValue(STATE)

    const simple = render(withQuery(<DistributionTab />))
    // Gated on the live half, not on a string the demo panel also had: the
    // negative assertion below was vacuously true against a screen showing
    // "loading…", so *deleting* the detail gate left all six tests green while
    // only inverting it failed. Deletion is the likelier regression.
    await liveHalfRendered()
    expect(screen.getByText("test-tool-alpha")).toBeInTheDocument()
    expect(screen.queryByText(/mcp: \.alpha\/mcp\.json/)).not.toBeInTheDocument()
    simple.unmount()

    useDetailLevel.setState({ level: "advanced" })
    render(withQuery(<DistributionTab />))
    expect(await screen.findByText(/mcp: \.alpha\/mcp\.json/)).toBeInTheDocument()
  })

})

// ─────────────── T4.08: the inject log ───────────────

describe("Distribution tab — the inject log (T4.08)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "simple" })
  })

  /** Routes by path so the targets read and the inject log never answer for
   *  each other — a single `mockResolvedValue` makes the log render the
   *  distribution state, which is a passing test about nothing. */
  function route(state: unknown, injects: unknown[] = [], curbs: unknown[] = []) {
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.includes("event_type=inject_curbed")) {
        return { items: curbs, total: curbs.length } as never
      }
      if (path.includes("event_type=inject")) {
        return { items: injects, total: injects.length } as never
      }
      return state as never
    })
  }

  function injectEvent(over: Record<string, unknown> = {}) {
    return {
      id: 41,
      created_at: "2026-08-11T11:20:00Z",
      event_type: "inject",
      object_type: "system",
      object_id: null,
      project: "darkmem",
      actor: null,
      api_key_id: null,
      source: null,
      payload: {
        tool: "test-tool-alpha",
        context_file: "ALPHA_CONTEXT.md",
        fact_ids: ["a", "b"],
        article_ids: [],
        memory_ids: ["c"],
        budget_tokens: 1200,
        tokens_used: 640,
      },
      ...over,
    }
  }

  it("lists recent injects inline with their items and budget", async () => {
    route(STATE, [injectEvent()])
    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(await screen.findByText(/3 items · 640 \/ 1,200 tokens/)).toBeInTheDocument()
  })

  it("names what shifted on a watch re-inject", async () => {
    route(STATE, [
      injectEvent({ payload: { ...injectEvent().payload, trigger: "project_changed" } }),
    ])
    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(
      await screen.findByText(/re-injected: project_changed changed/),
    ).toBeInTheDocument()
  })

  it("merges curbs into the log as curbs, not as pushes of nothing", async () => {
    route(STATE, [], [
      injectEvent({ id: 42, event_type: "inject_curbed", payload: { tool: "test-tool-alpha" } }),
    ])
    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(
      await screen.findByText(/push curbed — nothing was pushed/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/0 items/)).not.toBeInTheDocument()
  })

  it("an unreadable log says so rather than reading as no push", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.includes("event_type=")) throw new Error("journal down")
      return STATE as never
    })
    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(
      await screen.findByText(/The inject log could not be loaded/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/No context has been pushed yet/)).not.toBeInTheDocument()
  })
})
