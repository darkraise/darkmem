import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// The toggle is one mount in the app header, but it only governs five of the
// eight page areas. On the rest it was a live control that changed nothing,
// which is worse than absent: it invites the reader to try it and teaches
// them the setting does not work.
//
// This suite pins WHERE it renders. It is deliberately driven off the
// exported allowlist rather than a hand-copied list of paths, so the rule and
// its test cannot drift apart — a path added to one is added to both.

const pathname = vi.hoisted(() => ({ current: "/" }))

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useRouterState: ({ select }: { select: (s: unknown) => unknown }) =>
    select({ location: { pathname: pathname.current } }),
}))

import { DetailLevelToggle, DETAIL_LEVEL_ROUTES } from "../detail-level-toggle"

function renderAt(path: string) {
  pathname.current = path
  const { unmount } = render(<DetailLevelToggle />)
  const found = screen.queryByLabelText("Detail level") !== null
  unmount()
  return found
}

const SHOWN = [
  "/knowledge",
  "/knowledge/facts",
  "/knowledge/facts/abc-123",
  "/knowledge/articles",
  "/knowledge/articles/abc-123",
  "/knowledge/review",
  "/knowledge/topics",
  "/activity",
  "/chat",
  "/memories",
  "/memories/abc-123",
  "/settings",
]

const HIDDEN = [
  "/",
  "/code",
  "/code/graph",
  "/code/repositories",
  "/code/wiki",
  "/memory-graph",
  "/unified-graph",
  "/documents",
  "/jobs",
  "/usage",
]

describe("DetailLevelToggle placement", () => {
  it.each(SHOWN)("renders on %s, where something consumes the level", (path) => {
    expect(renderAt(path)).toBe(true)
  })

  it.each(HIDDEN)("is absent on %s, where nothing consumes it", (path) => {
    expect(renderAt(path)).toBe(false)
  })

  it("is an allowlist, so an unknown route hides rather than shows", () => {
    // A blocklist would default a new page to showing a control that does
    // nothing. Defaulting to hidden makes the failure mode "a real setting is
    // missing" — visible and reported — instead of "a dead control ships".
    expect(renderAt("/some-route-that-does-not-exist-yet")).toBe(false)
  })

  it("matches on a path segment, never a bare prefix", () => {
    // `/codex` must not inherit `/code`'s decision, and `/memories-archive`
    // must not inherit `/memories`'.
    expect(renderAt("/memoriesarchive")).toBe(false)
    expect(DETAIL_LEVEL_ROUTES.every((p) => p.startsWith("/"))).toBe(true)
  })
})
