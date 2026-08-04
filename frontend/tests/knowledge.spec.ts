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
  test("opens on every project, counts what it holds, and windows the list", async ({
    page,
  }) => {
    await page.goto("/knowledge/facts")
    // The scope is the route's all-projects capability, not a hardcoded
    // project name — a vault whose facts live under another project would
    // otherwise open empty and read as a cold start.
    await expect(page.getByText("Facts — project: all projects")).toBeVisible()

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
    // Simple collapses the taxonomy triple and nothing else: the claim, the
    // rung and the layer label all survive the toggle (T1.48, invariant 14).
    await expect(relation).toBeHidden()
    await expect(claim).toBeVisible()
    await expect(page.getByText("disputed").first()).toBeVisible()
    await expect(page.getByText("L2 · fact").first()).toBeVisible()
  })
})
