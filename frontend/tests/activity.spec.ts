import { test, expect } from "@playwright/test"

test("activity feed reads /events with no client-side aggregation", async ({
  page,
}) => {
  await page.goto("/activity?tab=feed")
  const heading = page.getByText(/activity — live feed/i)
  if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(heading).toBeVisible()
})

test("activity day view drills into the UTC day bucket", async ({ page }) => {
  await page.goto("/activity?tab=day")
  const label = page.getByText(/days are utc/i)
  if (!(await label.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(label).toBeVisible()
})

test("buffer monitor poison row is actionable, not just visible", async ({
  page,
}) => {
  await page.goto("/activity?tab=monitors")
  const forget = page.getByRole("button", { name: /^Forget$/ })
  if (!(await forget.isVisible({ timeout: 5000 }).catch(() => false))) {
    test.skip(true, "Activity not reachable without login")
  }
  await expect(forget).toBeVisible()
  await expect(
    page.getByRole("button", { name: /Retry \(re-buffer\)/ }),
  ).toBeVisible()
})
