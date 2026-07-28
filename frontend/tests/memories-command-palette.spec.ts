import { test, expect } from "@playwright/test"

test("memories command palette opens with ⌘K", async ({ page }) => {
  await page.goto("/memories")
  await expect(page.getByRole("heading", { name: /memories/i })).toBeVisible()
  // Ctrl on non-mac, Meta on mac — try both
  await page.keyboard.press("Control+k").catch(() => {})
  await page.keyboard.press("Meta+k").catch(() => {})
  // The Command palette should be visible; one of these roles should appear
  const palette = page.getByRole("dialog").or(page.getByRole("combobox"))
  await expect(palette.first()).toBeVisible()
})
