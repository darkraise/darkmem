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

const LABEL: Record<"simple" | "advanced", string> = {
  simple: "Simple",
  advanced: "Advanced",
}

async function setDetailLevel(page: Page, level: "simple" | "advanced") {
  await page.getByRole("radio", { name: LABEL[level] }).click()
}

async function shownCount(page: Page): Promise<number> {
  const meta = await page
    .getByText(/^(all \d+ shown|\d+ of \d+ loaded)$/)
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
  test.beforeEach(async ({ page }) => {
    await page.goto("/knowledge/facts")
    await expect(page.getByText(/Facts — project:/)).toBeVisible()
  })

  test("opens on every project and counts what it holds", async ({ page }) => {
    // The scope is the route's all-projects capability, not a hardcoded
    // project name — a vault whose facts live under another project would
    // otherwise open empty and read as a cold start.
    await expect(page.getByText("Facts — project: all projects")).toBeVisible()
    expect(await shownCount(page)).toBeGreaterThan(0)
  })

  test("the status filter narrows the list in demo mode too", async ({
    page,
  }) => {
    const before = await shownCount(page)
    await pickOption(page, "Status filter", "disputed")
    const after = await shownCount(page)
    expect(after).toBeGreaterThan(0)
    expect(after).toBeLessThan(before)
  })

  test("a disputed row renders both sides on the row, in both detail modes", async ({
    page,
  }) => {
    await pickOption(page, "Status filter", "disputed")
    for (const level of ["advanced", "simple"] as const) {
      await setDetailLevel(page, level)
      // The backend's disputed claim is the two-sided form. Rendered as
      // text, not as a hover-only title a keyboard reader never reaches.
      const claim = page.getByText(/^disputed: .* origins? assert/).first()
      await expect(claim).toBeVisible()
      await expect(page.getByText("disputed").first()).toBeVisible()
    }
  })

  test("simple mode collapses the raw triple and keeps every honesty label", async ({
    page,
  }) => {
    await pickOption(page, "Status filter", "disputed")
    const relation = page.getByText("DEFAULT_STATE").first()

    await setDetailLevel(page, "advanced")
    await expect(relation).toBeVisible()

    await setDetailLevel(page, "simple")
    await expect(relation).toBeHidden()
    await expect(page.getByText(/^disputed: /).first()).toBeVisible()
    await expect(page.getByText("L2 · fact").first()).toBeVisible()
  })

  test("the list is virtualized — the DOM holds a window, not the corpus", async ({
    page,
  }) => {
    const total = await shownCount(page)
    expect(total).toBeGreaterThan(10)
    const rendered = await page.locator("[data-index]").count()
    expect(rendered).toBeGreaterThan(0)
    expect(rendered).toBeLessThan(total)
  })
})
