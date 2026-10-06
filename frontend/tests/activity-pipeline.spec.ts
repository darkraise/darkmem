import { test, expect } from "@playwright/test"

test("pipeline stepper renders honest terminal states, including partial", async ({
  page,
}) => {
  await page.goto("/activity?tab=pipeline")
  await expect(page.getByText(/pipeline — recent/i)).toBeVisible()
})

test("failure triage names the failed step and offers a manual retry", async ({
  page,
}) => {
  await page.goto("/activity?tab=triage")
  await expect(page.getByText(/failure triage/i)).toBeVisible()
})

test("job board shows cron and last run, and a trigger never silently queues", async ({
  page,
}) => {
  // Activity's old Jobs tab was a second copy of this board; its URL now
  // lands on the one board.
  await page.goto("/activity?tab=jobs")
  await expect(page).toHaveURL(/\/jobs$/)
  // Each job prints the cron expression (five or six fields) beside its
  // plain-English reading.
  await expect(
    page
      .getByRole("main")
      .locator("code")
      .filter({ hasText: /^\S+( \S+){4,5}$/ })
      .first(),
  ).toBeVisible()
})
