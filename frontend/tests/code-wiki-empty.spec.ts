import { test, expect } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

// T1.59 rewrite: this spec used to target the legacy /repos page's demo-mode
// Code Wiki tab, in DEMO_FIXTURE_SPECS. That page is deleted (T1.59 Step 6)
// and its replacement, /code/wiki, needs the real backend — RealWikiView is
// gated in behind DEMO?WikiTab:RealWikiView, so this spec moved to the real
// chromium project and now authenticates the same way code-real-mode.spec.ts
// and auth.spec.ts do. The old isVisible({ timeout }).catch(() => false))
// soft-skip idiom is gone on purpose: that idiom is deprecated in the
// installed Playwright version (the timeout it passes is silently ignored,
// so the guard never actually waited) and reusing it here — in a spec this
// very revision is rewriting to fix a different instance of the same
// silent-skip failure class — would hand T1.64 a fresh instance of the
// defect it exists to retire. Every assertion below runs against a
// deterministically-reachable element once login succeeds.
const PASSWORD = process.env.E2E_ADMIN_PASSWORD

test.describe("code wiki — empty state", () => {
  test.beforeAll(() => {
    if (!PASSWORD) {
      throw new Error(
        "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
          "missing credential.",
      )
    }
    // See auth.spec.ts's header for why a disposable stack (T1.64 plan §2.2)
    // must never reach seedAdminPassword()'s hardcoded darkmem target. This
    // file was not in T1.64's original file list — found during execution,
    // the same B1 defect class, fixed the same way.
    if (!process.env.E2E_DISPOSABLE_STACK) {
      seedAdminPassword()
    }
  })

  test("/code/wiki shows the honest empty state, never implicitly generating", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
    await page.getByRole("button", { name: /sign in/i }).click()
    await expect(page).toHaveURL("/")

    await page.goto("/code/wiki")

    // Matched against real-wiki-view.tsx's own rendered copy: with no repos
    // configured, "No repositories indexed yet"; with a repo but no
    // generated wiki, "No wiki generated yet for this repository" plus the
    // reindex-dialog CTA — never a fabricated "select a repo" placeholder.
    await expect(
      page.getByText(/No repositories indexed yet|No wiki generated yet for this repository/),
    ).toBeVisible()
  })
})
