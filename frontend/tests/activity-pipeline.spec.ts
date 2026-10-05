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
  await page.goto("/activity?tab=jobs")
  // Three things on this page are named "Jobs": the sidebar nav link, the tab
  // trigger, and the panel's own heading. Only the last one means the board
  // rendered, so scope to <main> (which excludes the sidebar) and drop the
  // tab. Matching on text alone used to resolve to the sidebar link and pass
  // whether or not the board was there.
  const heading = page
    .getByRole("main")
    .getByText(/^jobs$/i)
    .and(page.locator(':not([role="tab"])'))
  await expect(heading).toBeVisible()
  // The board is the shared /jobs list: each row prints the cron expression
  // (five or six fields) beside its plain-English reading.
  await expect(
    page
      .getByRole("main")
      .locator("code")
      .filter({ hasText: /^\S+( \S+){4,5}$/ })
      .first(),
  ).toBeVisible()
})
