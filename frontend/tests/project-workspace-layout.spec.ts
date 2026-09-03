import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The one claim about the artifacts workspace that no unit test can make.
 *
 * jsdom performs no layout, so every vitest assertion about the tree and
 * reader panes passes whether they fill the viewport or collapse to zero
 * height. The height chain this pins runs route root -> Tabs -> TabsContent
 * -> ResizablePanelGroup, and a break anywhere along it is invisible to the
 * unit suite and obvious to a human — which is exactly the gap that left the
 * layout resting on a manual look rather than on evidence.
 *
 * Sign-in is copied from the sibling real-mode specs rather than shared, for
 * the reason documents.spec.ts's header gives.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error(
      "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
        "missing credential, for the reason documents.spec.ts records.",
    )
  }
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

test("the tree and reader panes fill the viewport on a wide window", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await signIn(page)
  await page.goto("/projects/default")

  const tree = page.locator('[data-panel-id="tree"]')
  const reader = page.locator('[data-panel-id="reader"]')
  await expect(tree).toBeVisible()
  await expect(reader).toBeVisible()

  const treeBox = await tree.boundingBox()
  const readerBox = await reader.boundingBox()
  expect(treeBox).not.toBeNull()
  expect(readerBox).not.toBeNull()

  // The collapse this guards against is a zero or near-zero height, which is
  // what a broken chain produces. A generous floor: the assertion is "the
  // panes got real height from the chain", not a pixel-perfect layout lock
  // that would fail on any future spacing change.
  expect(treeBox!.height).toBeGreaterThan(400)
  expect(readerBox!.height).toBeGreaterThan(400)

  // Side by side, not stacked.
  expect(readerBox!.x).toBeGreaterThan(treeBox!.x + treeBox!.width - 1)

  // Neither pane may drive the page into a horizontal scroll.
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(overflows).toBe(false)
})

test("each pane scrolls independently rather than the page scrolling as one", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await signIn(page)
  await page.goto("/projects/default")

  // The scroll viewport the panes carry is what makes them independent: if
  // the chain collapses, the content spills into the document scroller
  // instead and these resolve to nothing.
  const viewports = page.locator(
    '[data-panel-id="tree"] [data-darkraise-scroll-viewport]',
  )
  await expect(viewports.first()).toBeVisible()

  const scrollable = await viewports.first().evaluate((el) => {
    const style = getComputedStyle(el as HTMLElement)
    return style.overflowY === "auto" || style.overflowY === "scroll"
  })
  expect(scrollable).toBe(true)
})
