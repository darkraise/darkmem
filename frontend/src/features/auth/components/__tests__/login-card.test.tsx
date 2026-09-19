import { readFileSync } from "node:fs"
import { join } from "node:path"
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
  it("renders the brand wordmark, a visible password label, and submit", () => {
    wrap(<LoginCard onSuccess={() => {}} />)
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByText("Password")).not.toHaveClass("sr-only")
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })

  it("uses the app's brand mark and the library button colours", () => {
    const { container } = wrap(<LoginCard onSuccess={() => {}} />)
    expect(container.querySelector(".dm-brand-mark")).not.toBeNull()
    const submit = screen.getByRole("button", { name: /sign in/i })
    expect(submit.className).not.toMatch(/gradient|slate|#/)
  })

  it("carries no hard-coded colour in its source", () => {
    const dir = join(process.cwd(), "src/features/auth/components")
    for (const file of ["login-card.tsx", "login-form.tsx"]) {
      const source = readFileSync(join(dir, file), "utf8")
      expect(source, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\b(slate|cyan|indigo|white|black)[-/]/)
    }
  })
})
