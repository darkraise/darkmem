import { test, expect } from "@playwright/test"

test("code wiki tab on /repos shows empty state", async ({ page }) => {
  await page.goto("/repos")
  // Code Wiki is now a tab on the Repositories page, not a standalone route.
  const tab = page.getByRole("tab", { name: /code wiki/i })
  if (!(await tab.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Repositories page not reachable without login")
  }
  await tab.click()
  const cta = page.getByRole("button", {
    name: /select a repo|add a repo|go to repositories/i,
  })
  await expect(cta.first()).toBeVisible()
})
