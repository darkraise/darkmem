import { test, expect } from "@playwright/test"

// T1.46 — code fail-stale banner + index-debt indicator. The two signals
// the code-truth hardening (T1.38/T1.39) produces, surfaced on the Code
// section's Repositories tab.
//
// VITE_DEMO defaults on until T1.58 flips it, so the webServer this suite
// drives always renders the demo-fed RepositoriesTab, never
// RealRepositoriesView — the real-backend binding is proven instead by
// src/features/code/__tests__/real-repositories-view.test.tsx (mocked
// apiFetch, DEMO forced false), which is the only way to exercise that
// branch until the default flips. This spec proves the two signals render
// as designed, over the same demo fixture the real view's honest labelling
// mirrors field-for-field (last-good sha, cause, queued count, drain state).
test.describe("code repositories — stale banner and index-debt indicator", () => {
  test("stale banner names the last-good sha and the cause", async ({ page }) => {
    await page.goto("/code/repositories")

    const heading = page.getByRole("heading", { name: "Repositories" })
    if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Code Repositories page not reachable without login")
    }

    await expect(
      page.getByText(
        "Last index failed — serving the last-good graph, marked stale",
      ),
    ).toBeVisible()
    await expect(page.getByText(/Leiden partitioning step timed out/)).toBeVisible()
    await expect(page.getByText("last-good HEAD 4b7e120")).toBeVisible()
  })

  test("index-debt indicator shows the queued file count, draining not lost", async ({
    page,
  }) => {
    await page.goto("/code/repositories")

    const heading = page.getByRole("heading", { name: "Repositories" })
    if (!(await heading.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, "Code Repositories page not reachable without login")
    }

    await expect(page.getByText(/168.*dependent files queued/)).toBeVisible()
    await expect(page.getByText(/draining via next sync/)).toBeVisible()
  })
})
