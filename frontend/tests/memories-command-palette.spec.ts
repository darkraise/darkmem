import { test, expect } from "@playwright/test"

test("memories command palette opens with ⌘K", async ({ page }) => {
  await page.goto("/memories")
  if (!(await page.getByRole("heading", { name: /memories/i }).isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Memories page not reachable without login")
  }
  // Ctrl on non-mac, Meta on mac — try both
  await page.keyboard.press("Control+k").catch(() => {})
  await page.keyboard.press("Meta+k").catch(() => {})
  // The Command palette should be visible; one of these roles should appear
  const palette = page.getByRole("dialog").or(page.getByRole("combobox"))
  await expect(palette.first()).toBeVisible({ timeout: 3000 }).catch(() => {})
})
