import { render } from "@testing-library/react"
import type { ComponentType } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

// Audit O11: the open conversation lived in component state only, so a reload
// dropped it and Back/Forward never moved it. It now lives in ?id=.

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
const routerMocks = vi.hoisted(() => ({
  useSearch: vi.fn((): { id?: string } => ({})),
  navigate: vi.fn(),
}))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
    useSearch: () => routerMocks.useSearch(),
    useNavigate: () => routerMocks.navigate,
  }
})
const page = vi.hoisted(() => ({
  props: null as null | {
    conversationId: string | null
    onSelect: (id: string | null, options?: { replace?: boolean }) => void
  },
}))
vi.mock("@/features/chat/components/real-chat-page", () => ({
  RealChatPage: (props: NonNullable<typeof page.props>) => {
    page.props = props
    return null
  },
}))

import { Route } from "../chat"

function renderRoute(search: { id?: string } = {}) {
  const Component = (Route.options ?? Route).component as ComponentType
  routerMocks.useSearch.mockReturnValue(search)
  render(<Component />)
  return page.props!
}

afterEach(() => {
  vi.clearAllMocks()
  page.props = null
})

describe("chat route", () => {
  it("opens the conversation named in ?id=, and a draft without one", () => {
    expect(renderRoute({ id: "c7" }).conversationId).toBe("c7")
    expect(renderRoute({}).conversationId).toBeNull()
  })

  it("moves the selection through the URL, pushing unless told to replace", () => {
    const { onSelect } = renderRoute({ id: "c7" })

    onSelect("c8")
    onSelect(null)
    onSelect("created", { replace: true })

    expect(routerMocks.navigate.mock.calls).toEqual([
      [{ to: "/chat", search: { id: "c8" }, replace: undefined }],
      [{ to: "/chat", search: { id: undefined }, replace: undefined }],
      [{ to: "/chat", search: { id: "created" }, replace: true }],
    ])
  })

  it("keeps only an id-shaped ?id=", () => {
    const validate = (Route.options ?? Route).validateSearch as (
      s: Record<string, unknown>,
    ) => { id?: string }
    const uuid = "0b9a4f6e-3c55-4a2e-9a63-8f3b8c1d2e10"
    expect(validate({ id: uuid })).toEqual({ id: uuid })
    // The demo store's own ids are slugs.
    expect(validate({ id: "thread-new-3" })).toEqual({ id: "thread-new-3" })
    expect(validate({ id: "" })).toEqual({ id: undefined })
    expect(validate({ id: "../memories" })).toEqual({ id: undefined })
    expect(validate({ id: 7 })).toEqual({ id: undefined })
    expect(validate({})).toEqual({ id: undefined })
  })
})
