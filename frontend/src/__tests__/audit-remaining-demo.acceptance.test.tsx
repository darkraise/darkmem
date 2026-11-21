import { describe, it, expect, vi, afterEach } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(() => Promise.reject(new Error("no request in demo mode"))),
}))

import { apiFetch } from "@/lib/api"
import { LLMTab } from "@/features/settings/components/llm-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.localStorage.clear()
})

describe("A43: demo mode", () => {
  it("A43: Settings LLM makes no request and writes no vendor API key to localStorage", async () => {
    const fetchSpy = vi.fn(() => Promise.reject(new Error("network in demo")))
    vi.stubGlobal("fetch", fetchSpy)
    const setItem = vi.spyOn(Storage.prototype, "setItem")
    const SECRET = "sk-demo-secret-0123456789"

    const user = userEvent.setup()
    render(<LLMTab />, { wrapper })
    await user.click(screen.getByRole("tab", { name: "Providers" }))
    await user.click(screen.getByRole("button", { name: /add provider/i }))
    await user.type(screen.getByLabelText("new provider name"), "demo-vendor")
    await user.type(screen.getByLabelText("new provider api_key"), SECRET)
    await user.click(screen.getByRole("button", { name: "Create" }))

    // let any effect or query settle
    await new Promise((r) => setTimeout(r, 50))
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    for (const call of setItem.mock.calls) {
      expect(String(call[0]) + String(call[1])).not.toContain(SECRET)
    }
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i)!
      expect(k + (window.localStorage.getItem(k) ?? "")).not.toContain(SECRET)
    }
    void fireEvent
    void it
  })
})
