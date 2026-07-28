import { test, expect } from "@playwright/test"

test("dashboard contribution calendar renders from the events substrate", async ({
  page,
}) => {
  await page.goto("/")
  await expect(page.getByText(/contribution calendar/i)).toBeVisible()
})

test("cell click navigates to /memories?date=YYYY-MM-DD", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByText(/contribution calendar/i)).toBeVisible()

  const cells = page.getByRole("button", { name: /—/ })
  // A second, previously uninventoried soft-skip: `.count()` does not wait,
  // so on a slow render it can read 0 before the grid has finished
  // rendering, the click loop never runs, and the skip below fires on a
  // race rather than a real "no active day" state. Wait for at least one
  // cell to exist first.
  await expect(cells.first()).toBeVisible()
  const total = await cells.count()
  let clicked = false
  for (let i = total - 1; i >= 0 && !clicked; i--) {
    const label = await cells.nth(i).getAttribute("aria-label")
    if (label && !/— 0 memor/.test(label)) {
      await cells.nth(i).click()
      clicked = true
    }
  }
  test.skip(!clicked, "No day with activity in the current window")

  await expect(page).toHaveURL(/\/memories\?date=\d{4}-\d{2}-\d{2}/)
})
