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

import { apiFetch, ApiError } from "@/lib/api"
import { SecurityTab } from "../components/security-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const POSTURE_FIXTURE = {
  trust_proxy_headers: true,
  cookie_secure: false,
  cookie_secure_explicit: true,
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

describe("SecurityTab (real) — ruling 3: reflects the real posture, never a hardcoded assumption", () => {
  afterEach(() => vi.clearAllMocks())

  it("renders the TOFU claim from GET /setup/status, not a hardcoded 'claimed'", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/setup/status"))
    await waitFor(() =>
      expect(screen.getAllByText("claimed").length).toBeGreaterThan(0),
    )
  })

  it("mutation proof: an uninitialized status renders 'not claimed', not the fixed default", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: false })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("not claimed")).toBeInTheDocument())
    expect(screen.queryByText("claimed")).not.toBeInTheDocument()
  })

  it("ruling 3: renders the live trust_proxy_headers / cookie_secure / mcp_allowed_hosts / rate-limit posture from GET /auth/security-posture", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/security-posture"))

    await waitFor(() =>
      expect(
        screen.getByText(/X-Real-IP \(trusted proxy — trust_proxy_headers on\)/),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText("192.168.0.195:8000")).toBeInTheDocument()
    expect(screen.getByText(/5 failed attempts/)).toBeInTheDocument()
    expect(screen.getByText("5 minutes")).toBeInTheDocument()
    expect(screen.getByText(/false — explicit/)).toBeInTheDocument()
  })

  it("mutation proof: flipping trust_proxy_headers in the response flips the rendered IP strategy", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/security-posture") {
        return Promise.resolve({ ...POSTURE_FIXTURE, trust_proxy_headers: false })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/raw socket peer \(trust_proxy_headers off\)/)).toBeInTheDocument(),
    )
    expect(
      screen.queryByText(/X-Real-IP \(trusted proxy — trust_proxy_headers on\)/),
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
      expect(screen.getByText(/localhost only \(mcp_allowed_hosts is empty/)).toBeInTheDocument(),
    )
    expect(screen.queryByText("192.168.0.195:8000")).not.toBeInTheDocument()
  })

  it("ruling 4: fields with genuinely no backend source still render as an honest gap, never a fabricated number", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("claimed").length).toBeGreaterThan(0))

    // The blocklist count, lockouts_30d, the session issue time/jti, and
    // the two journaled-count rows still have zero GET surface — every one
    // must render the honest-gap copy, never a guessed value. (Everything
    // /auth/security-posture now answers -- trust_proxy_headers,
    // cookie_secure, mcp_allowed_hosts, the rate-limit thresholds -- is
    // asserted as real data in the tests above, not as a gap here.)
    expect(
      screen.getAllByText(/not exposed via the API/).length,
    ).toBeGreaterThanOrEqual(3)
  })

  it("session renders the real sub from GET /auth/me, and skips the issue time/jti it does not carry", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/signed in as admin/)).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/issue time and jti are not exposed/),
    ).toBeInTheDocument()
  })

  it("change-password POSTs /auth/change-password with the real fields", async () => {
    mockHappy()
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/change-password" && init?.method === "POST") {
        return Promise.resolve({ ok: true })
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("claimed").length).toBeGreaterThan(0))

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "old-password" },
    })
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-123" },
    })
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-password-123" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Change password/ }))
    fireEvent.click(screen.getByRole("button", { name: /Confirm — change password/ }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/change-password",
        expect.objectContaining({ method: "POST" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/auth/change-password")
    expect(JSON.parse((call![1] as RequestInit).body as string)).toEqual({
      current_password: "old-password",
      new_password: "new-password-123",
    })
    await waitFor(() =>
      expect(screen.getByText(/Password changed/)).toBeInTheDocument(),
    )
  })

  it("mutation proof: a rejected change-password renders the real error, never a fake success", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/setup/status") return Promise.resolve({ initialized: true })
      if (path === "/auth/me") return Promise.resolve({ authenticated: true, sub: "admin" })
      if (path === "/auth/change-password" && init?.method === "POST") {
        return Promise.reject(new ApiError("Current password is incorrect", 401))
      }
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getAllByText("claimed").length).toBeGreaterThan(0))

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "wrong" },
    })
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-123" },
    })
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-password-123" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Change password/ }))
    fireEvent.click(screen.getByRole("button", { name: /Confirm — change password/ }))

    await waitFor(() =>
      expect(screen.getByText("Current password is incorrect")).toBeInTheDocument(),
    )
    expect(screen.queryByText(/Password changed/)).not.toBeInTheDocument()
  })
})
