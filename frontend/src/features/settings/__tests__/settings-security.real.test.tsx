import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), ApiError }
})

import { apiFetch } from "@/lib/api"
import { SecurityTab } from "../components/security-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// The exposed posture, and therefore coherent rather than merely convenient:
// with trust_proxy_headers on the backend collapses the tri-state, so
// cookie_secure=false alongside it is a state no server can report (T4.03).
const POSTURE_FIXTURE = {
  trust_proxy_headers: true,
  cookie_secure: true,
  cookie_secure_explicit: true,
  cookie_secure_clamped: true,
  environment: "development",
  mcp_allowed_hosts: ["192.168.0.195:8000"],
  rate_limit_max_failures: 5,
  rate_limit_window_seconds: 300,
  rate_limit_lockout_seconds: 300,
}

function mockHappy() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/setup/status") return Promise.resolve({ initialized: true })
    if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
    if (path === "/auth/security-posture") return Promise.resolve(POSTURE_FIXTURE)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

describe("SecurityTab (real) — reflects the real posture, never a hardcoded assumption", () => {
  afterEach(() => vi.clearAllMocks())

  it("renders the live trust_proxy_headers / cookie_secure / mcp_allowed_hosts / rate-limit posture from GET /auth/security-posture", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/security-posture"))

    await waitFor(() =>
      expect(
        screen.getByText(/X-Real-IP header \(trusted proxy\)/),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText("192.168.0.195:8000")).toBeInTheDocument()
    expect(screen.getByText(/5 failed attempts/)).toBeInTheDocument()
    expect(screen.getByText("5 minutes")).toBeInTheDocument()
    expect(
      screen.getByText(/on — forced on because the instance trusts proxy headers/),
    ).toBeInTheDocument()
  })

  it("mutation proof: flipping trust_proxy_headers in the response flips the rendered IP strategy", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/security-posture") {
        // The whole LAN triple moves together: with the proxy untrusted the
        // backend honours the explicit false and nothing is clamped.
        return Promise.resolve({
          ...POSTURE_FIXTURE,
          trust_proxy_headers: false,
          cookie_secure: false,
          cookie_secure_clamped: false,
        })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/direct connection address/)).toBeInTheDocument(),
    )
    expect(
      screen.queryByText(/X-Real-IP header \(trusted proxy\)/),
    ).not.toBeInTheDocument()
  })

  it("the LAN posture still renders the honoured explicit false, never the clamp copy", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/security-posture") {
        return Promise.resolve({
          ...POSTURE_FIXTURE,
          trust_proxy_headers: false,
          cookie_secure: false,
          cookie_secure_clamped: false,
        })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/off — set explicitly/)).toBeInTheDocument(),
    )
    expect(
      screen.queryByText(/forced on because/),
    ).not.toBeInTheDocument()
  })

  it("mcp_allowed_hosts renders the localhost-only default honestly when the list is empty, never fabricating a chip", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/security-posture") {
        return Promise.resolve({ ...POSTURE_FIXTURE, mcp_allowed_hosts: [] })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText("localhost only")).toBeInTheDocument(),
    )
    expect(screen.queryByText("192.168.0.195:8000")).not.toBeInTheDocument()
  })

  it("offers the password change in place rather than pointing at the user menu", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    fireEvent.click(
      await screen.findByRole("button", { name: /Change password/ }),
    )
    expect(await screen.findByRole("dialog")).toBeInTheDocument()
    expect(screen.queryByText(/user menu/)).toBeNull()
  })

  it("session renders the real sub from GET /auth/me", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/signed in as admin/)).toBeInTheDocument(),
    )
  })


})

describe("SecurityTab (real) — the three defects found in review", () => {
  afterEach(() => vi.clearAllMocks())



  // NOTE: this one passes with the fix reverted, and must not be read as
  // proving it. The suite mocks `apiFetch` wholesale, so the real 401 branch —
  // the thing that redirects and discards the message — never runs here. It
  // proves the rendering path: given the error, the card shows it. Its sibling
  // above is what pins the fix, by asserting the option that reaches the real
  // `apiFetch`; that one is verified red with `on401` removed.



  it("renders each subject as its own card", async () => {
    mockHappy()
    const { container } = render(<SecurityTab />, { wrapper })
    await screen.findByText(/signed in as admin/)
    // Sign-in, Session, MCP access — distinct subjects that read as one long
    // panel while they were divs inside a single surface.
    expect(container.querySelectorAll(".dr-card").length).toBe(3)
    for (const header of container.querySelectorAll(".dr-card-header")) {
      expect(header.className).toContain("flex-row")
    }
  })
})
