import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"

// Link needs a router this test never builds; render the target it was given.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    to,
    params,
    search,
  }: {
    children?: ReactNode
    to: string
    params?: Record<string, string>
    search?: Record<string, string>
  }) => {
    let href = to
    for (const [key, value] of Object.entries(params ?? {})) {
      href = href.replace(`$${key}`, value)
    }
    const query = new URLSearchParams(search ?? {}).toString()
    return <a href={query ? `${href}?${query}` : href}>{children}</a>
  },
}))

import { SourceRow } from "../components/fact-sources"

const MEMORY_ID = "01a10d58-90b9-77dc-aa27-4769fc511f3d"
const REPO_ID = "0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a1b"

function row(kind: string, ref: string) {
  return {
    origin_key: "unknown",
    kind: kind as "memory",
    ref,
    detail: "—",
    at: new Date().toISOString(),
  }
}

describe("SourceRow", () => {
  it("links a memory source to the memory it came from", () => {
    render(<SourceRow source={row("memory", MEMORY_ID)} />)
    expect(screen.getByRole("link", { name: MEMORY_ID })).toHaveAttribute(
      "href",
      `/memories/${MEMORY_ID}`,
    )
  })

  it("links a code source naming a repository to that repository's graph", () => {
    render(<SourceRow source={row("code", REPO_ID)} />)
    expect(screen.getByRole("link", { name: REPO_ID })).toHaveAttribute(
      "href",
      `/code/graph?repo=${REPO_ID}`,
    )
  })

  it("leaves a ref with no page of its own as text", () => {
    render(<SourceRow source={row("human", "reviewer-1")} />)
    expect(screen.getByText("reviewer-1")).toBeInTheDocument()
    expect(screen.queryByRole("link")).toBeNull()
  })
})
