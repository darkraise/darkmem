import { describe, expect, it, vi } from "vitest"
import { act, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router"

import { DocumentLeaveGuard, type HeldWrites } from "../components/document-leave-guard"

function renderGuard(held: HeldWrites, { withEditBox = true } = {}) {
  const onDiscard = vi.fn()
  const restoreFocus = vi.fn(() => {
    const target = withEditBox
      ? screen.getByRole("textbox", { name: "held edit" })
      : screen.getByRole("button", { name: "held block" })
    target.focus()
  })
  const root = createRootRoute({
    component: () => (
      <>
        {withEditBox ? (
          <textarea aria-label="held edit" defaultValue="unsaved words" />
        ) : (
          <button type="button">held block</button>
        )}
        <DocumentLeaveGuard held={held} restoreFocus={restoreFocus} onDiscard={onDiscard} />
        <Outlet />
      </>
    ),
  })
  const routeTree = root.addChildren([
    createRoute({ getParentRoute: () => root, path: "/", component: () => <p>document page</p> }),
    createRoute({ getParentRoute: () => root, path: "/other", component: () => <p>other page</p> }),
  ])
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: ["/"] }),
  })
  render(<RouterProvider router={router} />)
  const navigate = () =>
    act(async () => {
      void router.navigate({ to: "/other" } as never)
    })
  return { router, navigate, onDiscard, restoreFocus }
}

const path = (router: ReturnType<typeof renderGuard>["router"]) =>
  router.state.location.pathname

describe("DocumentLeaveGuard", () => {
  it("a refused write asks before in-app navigation", async () => {
    const { router, navigate, onDiscard } = renderGuard("refused")
    await screen.findByText("document page")

    await navigate()
    const dialog = await screen.findByRole("alertdialog")
    expect(within(dialog).getByText("Leave without saving?")).toBeInTheDocument()
    expect(within(dialog).getByText("This block's edit has not been saved.")).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: "Stay" })).toBeInTheDocument()

    await userEvent.click(within(dialog).getByRole("button", { name: "Stay" }))
    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: "held edit" })).toHaveFocus(),
    )
    expect(screen.getByRole("textbox", { name: "held edit" })).toHaveValue("unsaved words")
    expect(path(router)).toBe("/")
    expect(onDiscard).not.toHaveBeenCalled()

    await navigate()
    await userEvent.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Leave and discard",
      }),
    )
    expect(await screen.findByText("other page")).toBeInTheDocument()
    expect(path(router)).toBe("/other")
    expect(onDiscard).toHaveBeenCalledTimes(1)
  })

  it("Escape stays, and focus returns to the block when the write has no edit box", async () => {
    const { router, navigate } = renderGuard("refused", { withEditBox: false })
    await screen.findByText("document page")

    await navigate()
    await screen.findByRole("alertdialog")
    await userEvent.keyboard("{Escape}")
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "held block" })).toHaveFocus(),
    )
    expect(path(router)).toBe("/")
  })

  it.each(["saving", "none"] as const)(
    "with held=%s the navigation completes with no dialog",
    async (held) => {
      const { router, navigate } = renderGuard(held)
      await screen.findByText("document page")

      await navigate()
      expect(await screen.findByText("other page")).toBeInTheDocument()
      expect(path(router)).toBe("/other")
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    },
  )
})
