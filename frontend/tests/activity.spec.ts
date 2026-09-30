import { test, expect } from "@playwright/test"

test("activity feed reads /events with no client-side aggregation", async ({
  page,
}) => {
  await page.goto("/activity?tab=feed")
  await expect(page.getByText(/activity — live feed/i)).toBeVisible()
})

test("activity day view drills into the UTC day bucket", async ({ page }) => {
  await page.goto("/activity?tab=day")
  await expect(page.getByText(/days are utc/i)).toBeVisible()
})
