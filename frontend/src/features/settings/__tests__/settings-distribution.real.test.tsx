import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

// T3.19 — the Distribution tab's **live** half. Its own file rather than an
// addition to `settings-tabs.test.tsx`, which is frozen at `DEMO: true` to pin
// the fixture-backed rendering; the same split the security and maintenance
// tabs already use. A live assertion in that file could not run at all.
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
      refresh: "session_start",
    },
    {
      tool: "test-tool-beta",
      context_file: ".beta/rules/darkmem.mdc",
      mcp_config: ".beta/mcp.json",
      refresh: "session_start",
    },
  ],
  policy: { token_budget: 2000, curbed: false },
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

  it("claims no connect status, inject log or watermark it does not have", async () => {
    // The fixture panel rendered on every install, not only in demo: four
    // clients reporting "handshake ok", an inject log of deliveries that never
    // happened, and watermark rows for a writer that does not exist — beside
    // the live half, with nothing on screen telling them apart.
    vi.mocked(apiFetch).mockResolvedValue(STATE)

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()

    expect(screen.getByText(/nothing has completed the handshake/)).toBeInTheDocument()
    expect(screen.getByText(/no inject has happened/)).toBeInTheDocument()
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
    expect(screen.getByText(/1 configured target refused/)).toBeInTheDocument()
  })

  it("offers one control that stops every target, and posts it", async () => {
    const calls: Array<[string, RequestInit | undefined]> = []
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      calls.push([url, init])
      if (url === "/distribution/policy") return JSON.parse((init?.body as string) ?? "{}")
      return STATE
    })

    render(withQuery(<DistributionTab />))
    fireEvent.click(await screen.findByLabelText("Allow push"))

    await waitFor(() =>
      expect(calls.some(([url]) => url === "/distribution/policy")).toBe(true),
    )
    const [, init] = calls.find(([url]) => url === "/distribution/policy")!
    expect(JSON.parse((init?.body as string) ?? "{}").curbed).toBe(true)
  })

  it("states plainly when the policy could not be read", async () => {
    // A screen that showed "push is live" because the read failed would assert
    // the opposite of what it knows — and this is the control a human reaches
    // for when they want push to stop.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))

    render(withQuery(<DistributionTab />))

    expect(await screen.findByText(/could not be read/)).toBeInTheDocument()
    expect(screen.queryByText("Push is live")).not.toBeInTheDocument()
  })

  it("edits the content policy", async () => {
    const calls: Array<[string, RequestInit | undefined]> = []
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      calls.push([url, init])
      if (url === "/distribution/policy") return JSON.parse((init?.body as string) ?? "{}")
      return STATE
    })

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()
    // change-then-blur, because the field is controlled: a blur carrying a
    // `target` mutates the DOM node behind React's back, which is how the
    // uncontrolled version let an unparseable entry through.
    const field = await screen.findByLabelText("Token budget")
    fireEvent.change(field, { target: { value: "500" } })
    fireEvent.blur(field)

    await waitFor(() =>
      expect(calls.some(([url]) => url === "/distribution/policy")).toBe(true),
    )
    const [, init] = calls.find(([url]) => url === "/distribution/policy")!
    expect(JSON.parse((init?.body as string) ?? "{}").token_budget).toBe(500)
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

  it("does not write a budget of zero for text it could not parse", async () => {
    // `<input type="number">` reports "" for an unparseable entry and
    // `Number("")` is 0 — finite, so the guard passed and the server was told
    // the budget was zero while the field kept showing the typo.
    const calls: string[] = []
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      calls.push(url)
      if (url === "/distribution/policy") return JSON.parse((init?.body as string) ?? "{}")
      return STATE
    })

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()
    const field = (await screen.findByLabelText("Token budget")) as HTMLInputElement
    fireEvent.change(field, { target: { value: "" } })
    fireEvent.blur(field)

    // The field snaps back to what is in force, and nothing was written.
    await waitFor(() => expect(field.value).toBe("2000"))
    expect(calls).not.toContain("/distribution/policy")
  })

  it("says so when the curb could not be saved", async () => {
    // The switch snaps back to server truth, so a silent failure leaves a
    // human believing they stopped push when they did not.
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url === "/distribution/policy") throw new Error("boom")
      return STATE
    })

    render(withQuery(<DistributionTab />))
    await liveHalfRendered()
    fireEvent.click(screen.getByLabelText("Allow push"))

    expect(await screen.findByText(/was not saved/)).toBeInTheDocument()
  })
})

describe("the Distribution tab is one a human can return to", () => {
  it("is registered, so a reload does not fall back to flags", async () => {
    // It was routed and rendered but absent from the known list, so
    // `resolveStoredTab` sent every reload back to "flags" — the one tab you
    // could open and never get back to.
    const { resolveStoredTab } = await import("@/lib/settings-tab")
    expect(resolveStoredTab("distribution")).toBe("distribution")
  })
})
