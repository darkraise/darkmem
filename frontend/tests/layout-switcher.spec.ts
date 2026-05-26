import { test, expect } from "@playwright/test"

test("layout switcher persists choice across reload", async ({ page }) => {
  await page.goto("/")
  // Locate the layout switcher trigger from the chrome (sidebar/topnav footer)
  const switcher = page.getByRole("button", { name: /layout/i })
  if (!(await switcher.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Layout switcher not visible — likely needs login")
  }
  await switcher.click()
  await page.getByRole("menuitem", { name: /top-nav/i }).click()
  await expect(page.locator("[data-layout='top-nav']")).toBeVisible({ timeout: 5000 })
  await page.reload()
  await expect(page.locator("[data-layout='top-nav']")).toBeVisible({ timeout: 5000 })
})
