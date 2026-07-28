import { test, expect } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

// Runs against the real dev backend, never seedAuth() — that helper exists
// specifically to bypass this flow for every other spec. Requires
// E2E_ADMIN_PASSWORD and a live, already-initialized dev stack; the seed
// step overwrites the shared stack's real admin password on purpose
// (T1.58 Ruling 4) so this spec can log in with a password it knows.
const PASSWORD = process.env.E2E_ADMIN_PASSWORD

test.describe("auth", () => {
  test.beforeAll(() => {
    if (!PASSWORD) {
      throw new Error(
        "E2E_ADMIN_PASSWORD must be set to run auth.spec.ts against the " +
          "live, seeded dev stack — it never soft-skips for a missing " +
          "credential.",
      )
    }
    seedAdminPassword()
  })

  test("a fresh, unauthenticated session lands on /login, not /", async ({
    page,
  }) => {
    await page.goto("/")
    await expect(page).toHaveURL(/\/login$/)
  })

  // The rate limiter is in-memory, per-IP, 5 failures / 300s window / 300s
  // lockout (LoginRateLimiter, backend/app/services/login_rate_limit.py) —
  // shared across every request this vite-proxied test issues. Exactly one
  // wrong-password attempt per run leaves 4 of headroom for accidental
  // re-runs within the window; a lockout reads as "rate-limited," never as
  // a false "wrong-password assertion failed" (restart the backend to
  // clear the in-memory bucket immediately if this fires).
  test("the wrong password shows an inline error and never navigates off /login", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByRole("textbox", { name: "Password" }).fill(`${PASSWORD}-wrong`)
    await page.getByRole("button", { name: /sign in/i }).click()

    const alert = page.getByRole("alert")
    await expect(alert).toBeVisible()
    const message = (await alert.textContent()) ?? ""
    test.skip(
      /too many|retry in/i.test(message),
      `login is rate-limited ("${message}") — not this test's failure; ` +
        "restart the backend to clear the in-memory bucket and re-run",
    )
    await expect(page).toHaveURL(/\/login$/)
  })

  test("the right password signs in and the authenticated shell renders", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
    await page.getByRole("button", { name: /sign in/i }).click()

    await expect(page).toHaveURL("/")
    // Dashboard (T1.43, done) is bound to real data and always renders
    // once authenticated, in demo mode and real mode alike.
    await expect(page.getByText(/contribution calendar/i)).toBeVisible({
      timeout: 10_000,
    })
  })

  test("a reload of / stays authenticated — no bounce to /login", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
    await page.getByRole("button", { name: /sign in/i }).click()
    await expect(page).toHaveURL("/")

    await page.reload()
    await expect(page).toHaveURL("/")
    await expect(page.getByText(/contribution calendar/i)).toBeVisible({
      timeout: 10_000,
    })
  })

  test("logout returns to /login, and a direct navigation to / bounces back", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
    await page.getByRole("button", { name: /sign in/i }).click()
    await expect(page).toHaveURL("/")

    // darkraise-ui's UserMenu trigger carries no accessible name (an
    // avatar-initials icon button) — the stable handle is its own class.
    await page.locator(".dr-user-menu-trigger").click()
    await page.getByRole("menuitem", { name: /log out/i }).click()

    await expect(page).toHaveURL(/\/login$/)

    await page.goto("/")
    await expect(page).toHaveURL(/\/login$/)
  })
})
