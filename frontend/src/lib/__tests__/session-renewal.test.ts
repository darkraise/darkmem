import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import { createElement, type ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { apiFetch } from "../api"
import {
  RENEWED_AT_KEY,
  recordRenewal,
  resetSessionRenewal,
  sessionExpiresAt,
  startSessionRenewal,
} from "../session-renewal"
import type { PageView } from "@/hooks/api"
import type { PageTransport } from "@/features/notes/lib/page-sync"
import { resetPageSyncEngines, usePageSync } from "@/features/notes/use-page-sync"
import { deferred, json, minutesAhead, routeFetch } from "./session-test-kit"

const signIn = vi.fn()
const settle = () => act(async () => {
  await vi.advanceTimersByTimeAsync(0)
})

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
  resetSessionRenewal()
})

afterEach(() => {
  resetSessionRenewal()
  resetPageSyncEngines()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe("session renewal", () => {
  it.each([60, 59])("renews a session with an hour or less to spare (%i minutes)", async (minutes) => {
    const answer = deferred<Response>()
    const net = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(minutes) })],
      "/auth/refresh": [answer.promise],
    })
    startSessionRenewal(signIn)
    await settle()

    expect(net.count("/auth/refresh")).toBe(1)
    expect(localStorage.getItem(RENEWED_AT_KEY)).toBeNull()

    const renewed = minutesAhead(24 * 60)
    answer.resolve(json({ ok: true, expires_at: renewed }))
    await settle()
    expect(localStorage.getItem(RENEWED_AT_KEY)).not.toBeNull()
    expect(sessionExpiresAt()).toBe(Date.parse(renewed))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })
    expect(net.count("/auth/refresh")).toBe(1)
    expect(signIn).not.toHaveBeenCalled()
  })

  it("leaves a session with more than an hour alone until the check finds an hour", async () => {
    const net = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(61) })],
      "/auth/refresh": [json({ ok: true, expires_at: minutesAhead(24 * 60) })],
    })
    startSessionRenewal(signIn)
    await settle()
    expect(net.count("/auth/refresh")).toBe(0)

    // Back from a hidden tab two minutes later, before the minute timer.
    vi.setSystemTime(Date.now() + 2 * 60_000)
    document.dispatchEvent(new Event("visibilitychange"))
    await settle()
    expect(net.count("/auth/refresh")).toBe(1)
  })

  it("a failed first expiry read is read again by the next check", async () => {
    const net = routeFetch({
      "/auth/me": [
        json({ detail: "unavailable" }, 503),
        json({ detail: "unavailable" }, 503),
        json({ authenticated: true, expires_at: minutesAhead(30) }),
      ],
      "/auth/refresh": [json({ ok: true, expires_at: minutesAhead(24 * 60) })],
    })
    startSessionRenewal(signIn)
    await settle()
    expect(sessionExpiresAt()).toBeNull()
    expect(net.count("/auth/refresh")).toBe(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })
    expect(net.count("/auth/me")).toBe(3)
    expect(net.count("/auth/refresh")).toBe(1)
  })

  it("a second tab adopts the renewal", async () => {
    const net = routeFetch({
      "/auth/me": [
        json({ authenticated: true, expires_at: minutesAhead(90) }),
        json({ authenticated: true, expires_at: minutesAhead(24 * 60) }),
      ],
      "/auth/refresh": [json({ ok: true, expires_at: minutesAhead(24 * 60) })],
    })
    startSessionRenewal(signIn)
    await settle()

    window.dispatchEvent(
      new StorageEvent("storage", { key: RENEWED_AT_KEY, newValue: String(Date.now()) }),
    )
    await settle()
    expect(net.count("/auth/me")).toBe(2)

    vi.setSystemTime(Date.now() + 40 * 60_000)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })
    expect(net.count("/auth/refresh")).toBe(0)
  })

  it("a refused renewal ends the session once", async () => {
    const before = window.location.href
    const net = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(59) })],
      "/auth/refresh": [json({ detail: "Token has been revoked" }, 401)],
    })
    startSessionRenewal(signIn)
    await settle()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60_000)
    })

    expect(net.count("/auth/refresh")).toBe(1)
    expect(signIn).toHaveBeenCalledTimes(1)
    expect(window.location.href).toBe(before)
  })

  it("a tab that slept past expiry goes to sign-in by client navigation", async () => {
    const page: PageView = {
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: "Plans",
      content_hash: "h0",
      blocks: [
        { block_id: "a", type: "paragraph", text: "a", order_index: 0, char_span: null, parent_id: null, properties: null, source: "a" },
      ],
    }
    const stuck: PageTransport = {
      read: async () => ({ tree: [], hash: "x" }),
      send: () => new Promise(() => {}),
    }
    const qc = new QueryClient()
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)
    const draft = renderHook(() => usePageSync(page, 0, () => stuck), { wrapper })
    act(() => {
      draft.result.current.onDocumentChange([
        { id: "a", type: "paragraph", props: {}, content: [{ type: "text", text: "a draft", styles: {} }], children: [] },
      ])
      draft.result.current.flushNow()
    })
    draft.unmount()

    const net = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(90) })],
    })
    startSessionRenewal(signIn)
    await settle()
    vi.setSystemTime(Date.now() + 2 * 60 * 60_000)
    document.dispatchEvent(new Event("visibilitychange"))
    await settle()

    expect(signIn).toHaveBeenCalledTimes(1)
    expect(net.count("/auth/refresh")).toBe(0)
    const reopened = renderHook(() => usePageSync(page, 0, () => stuck), { wrapper })
    expect(JSON.stringify(reopened.result.current.initialBlocks)).toContain("a draft")
    reopened.unmount()
  })

  it("a 401 within ten seconds of a renewal is retried once", async () => {
    const net = routeFetch({
      "/auth/me": [json({ authenticated: true, expires_at: minutesAhead(24 * 60) })],
      "/thing": [json({ detail: "Token has been revoked" }, 401), json({ value: 1 })],
    })
    startSessionRenewal(signIn)
    await settle()
    recordRenewal()

    vi.setSystemTime(Date.now() + 3_000)
    await expect(apiFetch("/thing")).resolves.toEqual({ value: 1 })
    expect(net.count("/thing")).toBe(2)
    expect(signIn).not.toHaveBeenCalled()

    vi.setSystemTime(Date.now() + 8_000)
    net.fetchMock.mockImplementation(async () => json({ detail: "Token has been revoked" }, 401))
    await expect(apiFetch("/thing")).rejects.toMatchObject({ status: 401 })
    expect(signIn).toHaveBeenCalledTimes(1)
  })
})
