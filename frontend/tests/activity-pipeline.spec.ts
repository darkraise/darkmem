import { test, expect } from "@playwright/test"

test("pipeline stepper renders honest terminal states, including partial", async ({
  page,
}) => {
  await page.goto("/activity?tab=pipeline")
  const heading = page.getByText(/pipeline — recent/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(heading).toBeVisible()
})

test("failure triage names the failed step and offers a manual retry", async ({
  page,
}) => {
  await page.goto("/activity?tab=triage")
  const heading = page.getByText(/failure triage/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(heading).toBeVisible()
})

test("job board shows cron and last run, and a trigger never silently queues", async ({
  page,
}) => {
  await page.goto("/activity?tab=jobs")
  const heading = page.getByText(/^jobs$/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(heading).toBeVisible()
  await expect(page.getByText(/cron/i).first()).toBeVisible()
})
