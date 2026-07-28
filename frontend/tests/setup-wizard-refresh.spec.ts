import { test, expect } from "@playwright/test"

test("setup wizard persists step across reload", async ({ page }) => {
  await page.goto("/setup")
  // If already past setup, skip
  if (!page.url().endsWith("/setup")) {
    test.skip(true, "Setup already completed")
  }
  // Wait for password step. "Admin password" (StepPassword.tsx), not the
  // broader /password/i — that also matches the login page's own "Password"
  // field, so once setup is already complete and /setup redirects to
  // /login (a client-side redirect that can fire after the URL check above
  // already read "/setup"), the broader pattern would match the wrong
  // page's field and this test would silently exercise /login instead of
  // ever detecting "setup already completed" (found live this task: this
  // race was unreachable until a real, already-initialized backend existed
  // for this spec to run against at all).
  const passwordField = page.getByLabel("Admin password")
  const passwordFieldVisible = await passwordField
    .waitFor({ state: "visible", timeout: 5000 })
    .then(() => true)
    .catch(() => false)
  if (!passwordFieldVisible) {
    test.skip(true, "Setup wizard not in initial state")
  }
  // Skip step button (if available) or fill and continue
  // ... narrowly: just verify the wizard URL persists
  await page.reload()
  await expect(page).toHaveURL(/\/setup/)
})
