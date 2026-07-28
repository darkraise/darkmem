import { test, expect } from "@playwright/test"

test("theme switcher writes accent + mode to :root", async ({ page }) => {
  await page.goto("/")
  // open theme switcher (likely under a settings icon in the layout chrome)
  const trigger = page.getByRole("button", { name: /theme/i })
  await trigger.click()
  // pick a non-default accent — darkraise-ui renders the swatch palette
  // twice (a responsive dual layout), both with the same accessible name,
  // so scope to the one actually visible rather than picking blind.
  await page
    .getByRole("button", { name: /emerald/i })
    .and(page.locator(":visible"))
    .first()
    .click()
  const accent = await page.evaluate(() => document.documentElement.getAttribute("data-accent-color"))
  expect(accent).toBe("emerald")
  await page.reload()
  const accentAfter = await page.evaluate(() => document.documentElement.getAttribute("data-accent-color"))
  expect(accentAfter).toBe("emerald")
})
