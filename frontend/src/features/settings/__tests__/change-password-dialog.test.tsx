import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

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
import { ChangePasswordDialog } from "../components/change-password-dialog"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const renderDialog = () =>
  render(<ChangePasswordDialog open onOpenChange={() => {}} />, { wrapper })

const fill = (current: string, next: string, confirm: string) => {
  fireEvent.change(screen.getByLabelText("Current password"), {
    target: { value: current },
  })
  fireEvent.change(screen.getByLabelText("New password"), {
    target: { value: next },
  })
  fireEvent.change(screen.getByLabelText("Confirm new password"), {
    target: { value: confirm },
  })
}

const submit = async () => {
  fireEvent.click(screen.getByRole("button", { name: /Change password/ }))
  fireEvent.click(
    await screen.findByRole("button", { name: /Confirm — change password/ }),
  )
}

describe("ChangePasswordDialog", () => {
  afterEach(() => vi.clearAllMocks())

  it("POSTs /auth/change-password with the real fields", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ ok: true })
    renderDialog()
    fill("old-password", "a-new-password", "a-new-password")
    await submit()

    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find(([path]) => path === "/auth/change-password")
      expect(call).toBeTruthy()
      expect(JSON.parse((call![1] as RequestInit).body as string)).toEqual({
        current_password: "old-password",
        new_password: "a-new-password",
      })
    })
  })

  it("sends on401 surface, so a wrong current password cannot sign the operator out", async () => {
    // `apiFetch` treats every 401 as a dead session — it redirects to /login
    // and discards the server's message. This endpoint returns 401 for a wrong
    // CURRENT password, with the session perfectly valid. Measured in a browser
    // before the fix: a typo bounced the operator to /login and the real
    // "Current password is incorrect" never reached the screen.
    vi.mocked(apiFetch).mockResolvedValue({ ok: true })
    renderDialog()
    fill("whatever", "a-new-password", "a-new-password")
    await submit()

    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find(([path]) => path === "/auth/change-password")
      expect((call![1] as { on401?: string }).on401).toBe("surface")
    })
  })

  // NOTE: this passes with the fix reverted and must not be read as proving
  // it. The suite mocks `apiFetch` wholesale, so the real 401 branch — the one
  // that redirects and discards the message — never runs here. It proves the
  // rendering path: given the error, the dialog shows it. Its sibling above is
  // what pins the fix, and that one is verified red with `on401` removed.
  it("shows the server's own reason for a rejected current password", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError("Current password is incorrect", 401),
    )
    renderDialog()
    fill("wrong-one", "a-new-password", "a-new-password")
    await submit()

    expect(
      await screen.findByText("Current password is incorrect"),
    ).toBeInTheDocument()
  })

  it("says why the button will not submit instead of greying out in silence", () => {
    renderDialog()
    fill("", "short", "mismatch")
    expect(
      screen.getByRole("button", { name: /Change password/ }),
    ).toBeDisabled()
    expect(screen.getByText(/at least 8 characters/)).toBeInTheDocument()
    expect(screen.getByText(/confirmation does not match/)).toBeInTheDocument()
  })

  it("does not scold an untouched form", () => {
    renderDialog()
    expect(screen.queryByText(/Not ready —/)).not.toBeInTheDocument()
  })

  it("states the sign-out consequence without a hover", () => {
    renderDialog()
    expect(
      screen.getByText(/signs out every other session/),
    ).toBeInTheDocument()
  })
})
