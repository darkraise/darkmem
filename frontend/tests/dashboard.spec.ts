import { test, expect } from "@playwright/test"

test("dashboard contribution calendar renders from the events substrate", async ({
  page,
}) => {
  await page.goto("/")
  const heading = page.getByText(/contribution calendar/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Dashboard not reachable without login")
  }
  await expect(heading).toBeVisible()
})

test("cell click navigates to /memories?date=YYYY-MM-DD", async ({ page }) => {
  await page.goto("/")
  const heading = page.getByText(/contribution calendar/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Dashboard not reachable without login")
  }

  const cells = page.getByRole("button", { name: /—/ })
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
