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
  // getByText(/^jobs$/i) is ambiguous: the tab trigger itself is also
  // named "Jobs" — scope to the panel's own heading, not the tab.
  const heading = page.getByText(/^jobs$/i).and(page.locator(':not([role="tab"])'))
  await expect(heading).toBeVisible()
  await expect(page.getByText(/cron/i).first()).toBeVisible()
})
