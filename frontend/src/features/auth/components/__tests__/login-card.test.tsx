import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

// useLogin -> auth adapter -> apiFetch is the only external touchpoint; nothing
// in the auth feature imports sonner, so no toast mock is needed here.
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { LoginCard } from "../login-card"

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe("LoginCard", () => {
  it("renders the brand wordmark, password field, and submit", () => {
    wrap(<LoginCard onSuccess={() => {}} />)
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })
})
