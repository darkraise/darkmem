import type { Page } from "@playwright/test"

/** Seed auth state so /_authenticated routes don't redirect to /login. */
export async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "darkmem-auth",
      JSON.stringify({ state: { isAuthenticated: true }, version: 0 }),
    )
  })
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
  )
  await page.route("**/api/v1/auth/status", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ initialized: true }),
    }),
  )
}
