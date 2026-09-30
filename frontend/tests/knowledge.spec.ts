import { test, expect, type Page } from "@playwright/test"

// T2.36's Verify field names two commands; this file is the second one's
// target. Every Done-when clause but "badges verbatim" is a statement about
// the render — both axes distinct, disputed showing both sides, virtualized
// and paged, Simple/Advanced honoured — and none of them is observable from
// a hook test. The fix round's vitest suite covers the same clauses against
// the live producer with `apiFetch` mocked; this covers them in a browser,
// against the demo producer, through the one render path both share.
//
// Demo-fixture project (port 3637): the fixture is the corpus, so nothing
// here needs a backend, and the row component, the filters, the detail-level
// toggle and the virtualizer are the same code the live path renders.
//
// Two tests, not one per assertion: this project runs its specs in parallel
// against a single vite dev server, and each extra cold navigation to this
// route costs every concurrent worker a transform stall. Measured, not
// assumed — five navigations here pushed unrelated specs past their 5s
// expect timeout and the whole project from 15s to 39s.
//
// T2.86 fix round (F2): before this round no spec here ever navigated to
// `/knowledge/facts/$factId` — both tests above stop at the list. The third
// test below closes that gap for the *route wiring*: the link, the router
// param, `FactDetail`'s dispatch, the page chrome, the render path. What it
// does NOT and cannot prove: this project has no backend, so it exercises
// `DemoFactDetail` / `DemoFact`, never `LiveFactDetail` / `FactDetailResponse`
// — a drift between that live wire shape and `LiveFactDetailData` (the exact
// bug class this task exists to kill) stays provable only by
// `fact-detail.test.tsx`'s vitest suite, which mocks `apiFetch` by hand and
// never runs against a real, running backend. That gap is real and stays
// open after this round; see the fix-round report for the full accounting.

const LABEL: Record<"simple" | "advanced", string> = {
  simple: "Simple",
  advanced: "Advanced",
}

async function setDetailLevel(page: Page, level: "simple" | "advanced") {
  await page.getByRole("radio", { name: LABEL[level] }).click()
}

async function shownCount(page: Page): Promise<number> {
  const meta = await page
    .getByText(/^(\d+ facts|\d+ of \d+ loaded)$/)
    .first()
    .textContent()
  const digits = meta?.match(/\d+/g) ?? []
  return Number(digits[digits.length - 1])
}

async function pickOption(page: Page, control: string, option: string) {
  await page.getByRole("combobox", { name: control }).click()
  await page.getByRole("option", { name: option, exact: true }).click()
}

test.describe("knowledge/facts", () => {
  test("opens on every project, counts what it holds, and windows the list", async ({
    page,
  }) => {
    await page.goto("/knowledge/facts")

    const total = await shownCount(page)
    expect(total).toBeGreaterThan(10)

    // Virtualized: the DOM holds a window over the list, not the list.
    const rendered = await page.locator("[data-index]").count()
    expect(rendered).toBeGreaterThan(0)
    expect(rendered).toBeLessThan(total)

    // The filters apply with the fixture too — a demo branch that ignored
    // the query would leave this control silently inert.
    await pickOption(page, "Status filter", "disputed")
    const disputed = await shownCount(page)
    expect(disputed).toBeGreaterThan(0)
    expect(disputed).toBeLessThan(total)
  })

  test("a disputed row shows both sides and every honesty label, in both detail modes", async ({
    page,
  }) => {
    await page.goto("/knowledge/facts")
    await pickOption(page, "Status filter", "disputed")

    const claim = page.getByText(/^disputed: .* origins? assert/).first()
    const relation = page.getByText("DEFAULT_STATE").first()

    await setDetailLevel(page, "advanced")
    // The backend's disputed claim is the two-sided form. Rendered as text,
    // not as a hover-only title a keyboard reader never reaches.
    await expect(claim).toBeVisible()
    await expect(relation).toBeVisible()

    await setDetailLevel(page, "simple")
    // Simple collapses the taxonomy triple and nothing else: the claim and
    // the rung survive the toggle.
    await expect(relation).toBeHidden()
    await expect(claim).toBeVisible()
    await expect(page.getByText("disputed").first()).toBeVisible()
  })

  test("a fact row's link opens the detail route and can navigate back", async ({
    page,
  }) => {
    await page.goto("/knowledge/facts")
    await pickOption(page, "Status filter", "disputed")

    const claimPattern = /^disputed: .* origins? assert/
    const claim = page.getByText(claimPattern).first()
    await expect(claim).toBeVisible()
    const row = page
      .locator("[data-index]")
      .filter({ has: page.getByText(claimPattern) })
      .first()

    await row.getByRole("link", { name: "details →" }).click()
    await expect(page).toHaveURL(/\/knowledge\/facts\/[^/]+$/)
    // The page chrome, the same claim carried onto the detail page verbatim,
    // and the dispute section — proof the click reached `FactDetail` and
    // rendered the disputed branch, not a blank or error page.
    await expect(page.getByRole("heading", { name: "Fact detail" })).toBeVisible()
    await expect(claim).toBeVisible()
    await expect(page.getByText("Both sides", { exact: true })).toBeVisible()

    await page.getByRole("link", { name: "Back to Facts" }).click()
    await expect(page).toHaveURL(/\/knowledge\/facts$/)
  })
})
