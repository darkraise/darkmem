import { test, expect } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

// Gives the task's own Verify command (`npm run test:e2e -- code`) real
// teeth (T1.59 plan §5, Finding 2). code-index-debt.spec.ts and
// code-wiki-empty.spec.ts both live in DEMO_FIXTURE_SPECS on purpose — they
// prove the demo fixture renders correctly, and the real-mode binding is
// otherwise only proven by mocked-apiFetch vitest suites. This spec is the
// only one that mounts the real components against a real, authenticated
// session and a real (even if empty) backend.
//
// MUST NEVER move into playwright.config.ts's DEMO_FIXTURE_SPECS array —
// doing so would silently restore the exact green-but-empty failure this
// spec exists to close, with the Verify command still reporting green.
// Authenticates the same way auth.spec.ts does (seedAdminPassword() +
// the real login form), never seedAuth() — seedAuth only mocks
// window.localStorage plus two routes and would leave every other real
// REST call in this file 401ing. Requires E2E_ADMIN_PASSWORD and a live,
// already-initialized dev stack, matching auth.spec.ts's own documented
// precondition — this spec never soft-skips for a missing credential, and
// never uses the deprecated isVisible({ timeout }) idiom: every assertion
// after a successful login is a real pass/fail signal, not a guess about
// reachability.
const PASSWORD = process.env.E2E_ADMIN_PASSWORD

// The demo fixture's own repo names (src/demo/data/code-curated.ts) — none
// of these may ever appear on the real, unauthenticated-by-default project.
const DEMO_REPO_NAMES = [
  "darkmem/backend",
  "darkmem/frontend",
  "acme-storefront-api",
  "legacy-billing-service",
  "payments-service",
  "internal-tools-cli",
]

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.describe("code section — real mode", () => {
  test.beforeAll(() => {
    if (!PASSWORD) {
      throw new Error(
        "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
          "missing credential.",
      )
    }
    seedAdminPassword()
  })

  test("/code/repositories renders RealRepositoriesView, not the demo fixture", async ({
    page,
  }) => {
    await signIn(page)
    await page.goto("/code/repositories")

    await expect(
      page.getByRole("button", { name: /Add repository/ }),
    ).toBeVisible()

    for (const name of DEMO_REPO_NAMES) {
      await expect(page.getByText(name, { exact: true })).toHaveCount(0)
    }
  })

  test("/code/graph renders RealCodeGraphView, not the demo fixture, with an honest empty state", async ({
    page,
  }) => {
    await signIn(page)
    await page.goto("/code/graph")

    // No repos configured for this real, freshly-seeded project — the
    // honest empty state, not a fabricated graph.
    await expect(
      page.getByText(/No repositories indexed yet|No graph yet/),
    ).toBeVisible()

    for (const name of DEMO_REPO_NAMES) {
      await expect(page.getByText(name, { exact: true })).toHaveCount(0)
    }
  })

  test("/code/wiki renders RealWikiView, not the demo fixture, and never issues a non-GET /code/wiki request", async ({
    page,
  }) => {
    const violations: string[] = []
    page.on("request", (req) => {
      if (req.url().includes("/code/wiki") && req.method() !== "GET") {
        violations.push(`${req.method()} ${req.url()}`)
      }
    })

    await signIn(page)
    await page.goto("/code/wiki")

    await expect(
      page.getByText(/No repositories indexed yet|No wiki generated yet/),
    ).toBeVisible()

    for (const name of DEMO_REPO_NAMES) {
      await expect(page.getByText(name, { exact: true })).toHaveCount(0)
    }

    expect(violations).toEqual([])
  })
})
