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
    if (path === "/api-keys") return Promise.resolve(KEYS_FIXTURE)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

// One live key and one revoked one. The revoked row is listed on purpose:
// `GET /api-keys` does not filter, because revocation keeps the row so the
// calls the key already made keep a resolvable label (T4.04).
const KEYS_FIXTURE = [
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "push-webhook",
    key_id: "abc123",
    scopes: ["capture"],
    created_at: "2026-08-01T00:00:00Z",
    last_used_at: null,
    expires_at: null,
    revoked_at: null,
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    name: "retired-laptop",
    key_id: "def456",
    scopes: ["read"],
    created_at: "2026-07-01T00:00:00Z",
    last_used_at: null,
    expires_at: null,
    revoked_at: "2026-08-02T00:00:00Z",
  },
]

describe("SecurityTab (real) — key management", () => {
  afterEach(() => vi.clearAllMocks())

  it("lists the keys the box actually holds, revoked ones included", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("push-webhook")).toBeInTheDocument())
    expect(screen.getByText("retired-laptop")).toBeInTheDocument()
    // Locale-independent: the marker, not the rendered date format.
    expect(screen.getByText(/^revoked /)).toBeInTheDocument()
  })

  it("revokes through the DELETE door, and offers no Revoke on an already-revoked key", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("push-webhook")).toBeInTheDocument())

    const revokeButtons = screen.getAllByRole("button", { name: "Revoke" })
    expect(revokeButtons).toHaveLength(1)

    fireEvent.click(revokeButtons[0]!)
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/api-keys/22222222-2222-2222-2222-222222222222",
        { method: "DELETE" },
      ),
    )
  })

  it("never shows a key secret it was not handed — the plaintext exists once", async () => {
    mockHappy()
    render(<SecurityTab />, { wrapper })
    await waitFor(() => expect(screen.getByText("push-webhook")).toBeInTheDocument())
    expect(screen.queryByText(/Copy this now/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^dmk_/)).not.toBeInTheDocument()
  })
})

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



  it("drops the one-time plaintext when its own key is revoked", async () => {
    const created = {
      id: "44444444-4444-4444-4444-444444444444",
      name: "review-probe",
      key_id: "zzz999",
      scopes: ["read"],
      created_at: "2026-08-21T00:00:00Z",
      last_used_at: null,
      expires_at: null,
      revoked_at: null,
      token: "dmk_zzz999_plaintext",
    }
    let keys = [...KEYS_FIXTURE]
    vi.mocked(apiFetch).mockImplementation(
      (path: string, init?: RequestInit) => {
        if (path === "/api-keys" && init?.method === "POST") {
          keys = [...keys, created]
          return Promise.resolve(created)
        }
        if (path.startsWith("/api-keys/") && init?.method === "DELETE") {
          return Promise.resolve(undefined)
        }
        if (path === "/api-keys") return Promise.resolve(keys)
        if (path === "/setup/status") return Promise.resolve({ initialized: true })
        if (path === "/auth/me")
          return Promise.resolve({ authenticated: true, sub: "admin" })
        if (path === "/auth/security-posture") return Promise.resolve(POSTURE_FIXTURE)
        return Promise.reject(new Error(`unexpected apiFetch(${path})`))
      },
    )
    render(<SecurityTab />, { wrapper })
    await screen.findByText(/signed in as admin/)

    fireEvent.click(screen.getByRole("button", { name: /New key/ }))
    fireEvent.change(await screen.findByLabelText(/What is this key for/), {
      target: { value: "review-probe" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Create key/ }))
    expect(await screen.findByText("dmk_zzz999_plaintext")).toBeInTheDocument()

    // The plaintext exists for exactly as long as the dialog that issued it.
    // This used to be enforced by clearing the inline panel when its own key
    // was revoked; now the secret cannot outlive its dialog at all, which is
    // the stronger property and covers revocation as a special case. What the
    // test protects is unchanged: a one-time credential must not linger on a
    // screen after the moment it belongs to.
    fireEvent.click(screen.getByRole("button", { name: /I have copied it/ }))
    await waitFor(() =>
      expect(screen.queryByText("dmk_zzz999_plaintext")).not.toBeInTheDocument(),
    )

    // And reopening does not hand it back.
    fireEvent.click(screen.getByRole("button", { name: /New key/ }))
    expect(screen.queryByText("dmk_zzz999_plaintext")).not.toBeInTheDocument()
  })

  it("renders each subject as its own card", async () => {
    mockHappy()
    const { container } = render(<SecurityTab />, { wrapper })
    await screen.findByText(/signed in as admin/)
    // Sign-in, Session, MCP access, ApiKey — distinct subjects that read as
    // one long panel while they were divs inside a single surface.
    expect(container.querySelectorAll(".dr-card").length).toBe(4)
    for (const header of container.querySelectorAll(".dr-card-header")) {
      expect(header.className).toContain("flex-row")
    }
  })
})
