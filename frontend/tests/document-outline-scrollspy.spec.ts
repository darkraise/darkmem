import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The outline rail's two moving parts, neither of which a unit test can
 * assert: happy-dom performs no layout, so `getBoundingClientRect` is all zeroes
 * and both the scrollspy and the rail's self-centring are pure geometry.
 * `project-workspace.test.tsx` can only check that whatever the reader
 * reports is what the rail marks; what the reader reports is measured here.
 *
 * Sign-in is copied from the sibling real-mode specs rather than shared, for
 * the reason documents.spec.ts's header gives.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD
const PROJECT = "default"
const URI = "e2e-outline-scrollspy.md"

/** Enough sections that the rail overflows its own box and the document
 *  scrolls several screens — both are preconditions, not decoration. */
const CONTENT = [
  "# Scrollspy fixture",
  "",
  ...Array.from(
    { length: 24 },
    (_, i) =>
      `## Section ${i + 1}\n\n${"A paragraph of body text. ".repeat(20)}\n\n### Sub ${i + 1}.1\n\n${"More prose. ".repeat(20)}\n`,
  ),
].join("\n")

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

async function openFixture(page: Page) {
  // 1600px wide: the rail is `xl:flex`, so a narrower viewport hides it and
  // every assertion below would resolve to nothing.
  await page.setViewportSize({ width: 1600, height: 900 })
  const response = await page.request.post("/api/v1/documents", {
    data: { project: PROJECT, uri: URI, title: "Scrollspy fixture", content: CONTENT },
  })
  if (!response.ok()) {
    throw new Error(
      `filing the fixture failed with ${response.status()}: ${await response.text()}. ` +
        "Filing embeds the document's blocks in the same request, so an " +
        "unreachable embedder fails here — check the seeded Ollama endpoint " +
        "before reading this as a UI regression.",
    )
  }
  await page.goto(`/projects/${PROJECT}`)
  await page.getByText(URI, { exact: true }).click()
  await expect(page.getByLabel("document outline")).toBeVisible()
}

/** The heading the rail currently marks. */
function markedHeading(page: Page) {
  return page.locator(
    '[aria-label="document outline"] .dr-timeline-item:has(.dr-timeline-indicator[data-status="current"]) button',
  )
}

function readerViewport(page: Page) {
  return page.locator(
    '[data-panel-id="reader"] [data-darkraise-scroll-viewport]',
  )
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

test("the rail marks the section the reader is in, and follows the scroll", async ({
  page,
}) => {
  await signIn(page)
  await openFixture(page)

  // At the top the first heading is the current one.
  await expect(markedHeading(page)).toHaveText("Scrollspy fixture")

  await readerViewport(page).evaluate((el) => {
    el.scrollTop = el.scrollHeight / 2
  })

  // Something further down is marked now. Not pinned to a specific heading:
  // that would encode the fixture's own line heights, and the claim is that
  // the marker MOVED WITH the scroll, not where it landed.
  await expect(markedHeading(page)).not.toHaveText("Scrollspy fixture")
  const midway = await markedHeading(page).textContent()

  await readerViewport(page).evaluate((el) => {
    el.scrollTop = el.scrollHeight
  })
  await expect(markedHeading(page)).not.toHaveText(midway!)
})

test("the rail scrolls itself to keep the marked heading in view", async ({
  page,
}) => {
  await signIn(page)
  await openFixture(page)

  const rail = page.locator(
    '[aria-label="document outline"] .overflow-y-auto',
  )
  // Precondition: the rail must actually overflow, or "it scrolls itself" is
  // vacuously true and this test proves nothing.
  //
  // Polled rather than read once: the rail's height cap is measured from the
  // reader's viewport by a ResizeObserver, so it lands a frame after the
  // first paint and a single read here can catch the uncapped box.
  await expect
    .poll(
      async () => rail.evaluate((el) => el.scrollHeight - el.clientHeight),
      { timeout: 5000 },
    )
    .toBeGreaterThan(40)
  expect(await rail.evaluate((el) => el.scrollTop)).toBe(0)

  await readerViewport(page).evaluate((el) => {
    el.scrollTop = el.scrollHeight
  })

  // The rail moved on its own — nobody dragged it and nothing was clicked.
  await expect
    .poll(async () => rail.evaluate((el) => el.scrollTop), { timeout: 5000 })
    .toBeGreaterThan(0)

  // And the marked row is inside the rail's box rather than scrolled past it.
  const visible = await markedHeading(page).evaluate((row) => {
    const scroller = row.closest(".overflow-y-auto")!
    const rowBox = row.getBoundingClientRect()
    const box = scroller.getBoundingClientRect()
    return rowBox.top >= box.top - 1 && rowBox.bottom <= box.bottom + 1
  })
  expect(visible).toBe(true)
})

test("tracking the document never scrolls the document", async ({ page }) => {
  // The rail centres itself by setting its own `scrollTop`. `scrollIntoView`
  // would walk every scrollable ancestor — and the nearest one is the
  // reader's own viewport, so following the document's scroll would scroll
  // the document, which is a feedback loop.
  await signIn(page)
  await openFixture(page)

  const viewport = readerViewport(page)
  await viewport.evaluate((el) => {
    el.scrollTop = el.scrollHeight / 2
  })
  const settled = await viewport.evaluate((el) => el.scrollTop)

  await expect(markedHeading(page)).not.toHaveText("Scrollspy fixture")
  // Give the rail's smooth scroll time to finish and any feedback loop time
  // to show itself.
  await page.waitForTimeout(1200)
  expect(await viewport.evaluate((el) => el.scrollTop)).toBe(settled)
})
