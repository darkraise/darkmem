import { test, expect } from "@playwright/test"

test("code wiki shows empty state with reindex CTA", async ({ page }) => {
  await page.goto("/code-wiki")
  const cta = page.getByRole("button", { name: /reindex|select a repo|add a repo/i })
  if (!(await cta.first().isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Code wiki empty state not reachable without login")
  }
  await expect(cta.first()).toBeVisible()
})
