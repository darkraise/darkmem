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

const STATE = {
  targets: [
    {
      tool: "claude-code",
      context_file: "CLAUDE.md",
      mcp_config: ".mcp.json",
      refresh: "session_start",
    },
    {
      tool: "cursor",
      context_file: ".cursor/rules/darkmem.mdc",
      mcp_config: ".cursor/mcp.json",
      refresh: "session_start",
    },
  ],
  policy: { token_budget: 2000, curbed: false },
}

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

    expect(await screen.findByText("claude-code")).toBeInTheDocument()
    expect(screen.getByText("CLAUDE.md")).toBeInTheDocument()
    expect(screen.getByText(".cursor/rules/darkmem.mdc")).toBeInTheDocument()
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
    const field = await screen.findByLabelText("Token budget")
    fireEvent.blur(field, { target: { value: "500" } })

    await waitFor(() =>
      expect(calls.some(([url]) => url === "/distribution/policy")).toBe(true),
    )
    const [, init] = calls.find(([url]) => url === "/distribution/policy")!
    expect(JSON.parse((init?.body as string) ?? "{}").token_budget).toBe(500)
  })

  it("honours Simple/Advanced on the per-target detail", async () => {
    vi.mocked(apiFetch).mockResolvedValue(STATE)

    const simple = render(withQuery(<DistributionTab />))
    expect(await screen.findByText("claude-code")).toBeInTheDocument()
    expect(screen.queryByText(/mcp: \.mcp\.json/)).not.toBeInTheDocument()
    simple.unmount()

    useDetailLevel.setState({ level: "advanced" })
    render(withQuery(<DistributionTab />))
    expect(await screen.findByText(/mcp: \.mcp\.json/)).toBeInTheDocument()
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
