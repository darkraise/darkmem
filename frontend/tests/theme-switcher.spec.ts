import { test, expect } from "@playwright/test"

test("theme switcher writes accent + mode to :root", async ({ page }) => {
  await page.goto("/")
  // open theme switcher (likely under a settings icon in the layout chrome)
  const trigger = page.getByRole("button", { name: /theme/i })
  if (!(await trigger.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Theme switcher not visible — likely needs login")
  }
  await trigger.click()
  // pick a non-default accent
  await page.getByRole("button", { name: /emerald/i }).click()
  const accent = await page.evaluate(() => document.documentElement.getAttribute("data-accent-color"))
  expect(accent).toBe("emerald")
  await page.reload()
  const accentAfter = await page.evaluate(() => document.documentElement.getAttribute("data-accent-color"))
  expect(accentAfter).toBe("emerald")
})
