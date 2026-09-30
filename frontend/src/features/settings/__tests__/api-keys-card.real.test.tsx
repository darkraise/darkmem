import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { ApiKeysCard } from "../components/api-keys-card"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const DAY = 24 * 60 * 60 * 1000
const inDays = (n: number) => new Date(Date.now() + n * DAY).toISOString()

const LIVE = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "push-webhook",
  key_id: "abc123",
  scopes: ["capture", "admin"],
  created_at: "2026-08-01T00:00:00Z",
  last_used_at: null,
  expires_at: null,
  revoked_at: null,
}

// Listed on purpose: `GET /api-keys` does not filter, because revocation
// keeps the row so the calls the key already made keep a resolvable label.
const REVOKED = {
  id: "33333333-3333-3333-3333-333333333333",
  name: "retired-laptop",
  key_id: "def456",
  scopes: ["read"],
  created_at: "2026-07-01T00:00:00Z",
  last_used_at: "2026-07-20T00:00:00Z",
  expires_at: null,
  revoked_at: "2026-08-02T00:00:00Z",
}

function mockKeys(keys: unknown[]) {
  vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
    if (path.startsWith("/api-keys/") && init?.method === "DELETE")
      return Promise.resolve(undefined)
    if (path === "/api-keys") return Promise.resolve(keys)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

describe("ApiKeysCard (real)", () => {
  afterEach(() => vi.clearAllMocks())

  it("shows live keys as tiles and folds revoked ones away", async () => {
    mockKeys([LIVE, REVOKED])
    render(<ApiKeysCard />, { wrapper })

    const tile = await screen.findByRole("article", { name: "push-webhook" })
    expect(within(tile).getByText("Active")).toBeInTheDocument()
    expect(within(tile).getByText("Save")).toBeInTheDocument()
    expect(within(tile).getByText("Admin")).toBeInTheDocument()
    expect(within(tile).getByText("Never")).toBeInTheDocument()
    expect(screen.getByText(/1 active · 1 revoked/)).toBeInTheDocument()

    expect(screen.queryByRole("article", { name: "retired-laptop" })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: /Revoked keys \(1\)/ }))
    const revoked = await screen.findByRole("article", { name: "retired-laptop" })
    expect(within(revoked).getAllByText("Revoked").length).toBeGreaterThan(0)
    expect(
      within(revoked).queryByRole("button", { name: /Revoke/ }),
    ).toBeNull()
  })

  it("revokes only after confirmation, through the DELETE door", async () => {
    mockKeys([LIVE])
    render(<ApiKeysCard />, { wrapper })
    const tile = await screen.findByRole("article", { name: "push-webhook" })

    fireEvent.click(within(tile).getByRole("button", { name: /Revoke/ }))
    const dialog = await screen.findByRole("alertdialog")
    expect(within(dialog).getByText(/Revoke push-webhook\?/)).toBeInTheDocument()
    expect(apiFetch).not.toHaveBeenCalledWith(
      `/api-keys/${LIVE.id}`,
      expect.anything(),
    )

    fireEvent.click(within(dialog).getByRole("button", { name: "Revoke key" }))
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(`/api-keys/${LIVE.id}`, {
        method: "DELETE",
      }),
    )
  })

  it("cancelling the confirmation revokes nothing", async () => {
    mockKeys([LIVE])
    render(<ApiKeysCard />, { wrapper })
    const tile = await screen.findByRole("article", { name: "push-webhook" })

    fireEvent.click(within(tile).getByRole("button", { name: /Revoke/ }))
    const dialog = await screen.findByRole("alertdialog")
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }))

    // Closed, not unmounted: jsdom never finishes the exit animation.
    await waitFor(() => expect(dialog).toHaveAttribute("data-state", "closed"))
    expect(apiFetch).not.toHaveBeenCalledWith(
      `/api-keys/${LIVE.id}`,
      expect.anything(),
    )
  })

  it("marks keys that expire within a week or already have", async () => {
    mockKeys([
      { ...LIVE, id: "a", name: "soon", expires_at: inDays(3) },
      { ...LIVE, id: "b", name: "gone", expires_at: inDays(-1) },
      { ...LIVE, id: "c", name: "later", expires_at: inDays(60) },
    ])
    render(<ApiKeysCard />, { wrapper })

    const soon = await screen.findByRole("article", { name: "soon" })
    expect(within(soon).getByText("Expires soon")).toBeInTheDocument()
    const gone = screen.getByRole("article", { name: "gone" })
    expect(within(gone).getByText("Expired")).toBeInTheDocument()
    const later = screen.getByRole("article", { name: "later" })
    expect(within(later).getByText("Active")).toBeInTheDocument()
    expect(within(later).getByText("Expires")).toBeInTheDocument()
  })

  it("offers creation from an empty list and never shows a secret it was not handed", async () => {
    mockKeys([])
    render(<ApiKeysCard />, { wrapper })

    expect(await screen.findByText("No keys yet")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /New key/ })).not.toBeDisabled()
    expect(screen.queryByText(/^dmk_/)).toBeNull()
  })

  it("drops the one-time plaintext when its dialog closes", async () => {
    const created = {
      ...LIVE,
      id: "44444444-4444-4444-4444-444444444444",
      name: "review-probe",
      key_id: "zzz999",
      scopes: ["read"],
      token: "dmk_zzz999_plaintext",
    }
    let keys: unknown[] = []
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/api-keys" && init?.method === "POST") {
        keys = [created]
        return Promise.resolve(created)
      }
      if (path === "/api-keys") return Promise.resolve(keys)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<ApiKeysCard />, { wrapper })

    fireEvent.click(await screen.findByRole("button", { name: /New key/ }))
    const create = await screen.findByRole("button", { name: /Create key/ })
    expect(create).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/What is this key for/), {
      target: { value: "review-probe" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Create key/ }))
    expect(await screen.findByText("dmk_zzz999_plaintext")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /I have copied it/ }))
    await waitFor(() =>
      expect(screen.queryByText("dmk_zzz999_plaintext")).toBeNull(),
    )
    expect(
      await screen.findByRole("article", { name: "review-probe" }),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /New key/ }))
    expect(screen.queryByText("dmk_zzz999_plaintext")).toBeNull()
  })
})
