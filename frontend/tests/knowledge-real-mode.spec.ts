import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

// T2.90 — knowledge.spec.ts's sibling for the real backend, the same way
// code-real-mode.spec.ts sits beside code-wiki-empty.spec.ts /
// code-index-debt.spec.ts. Playwright routes by *file*, not by test block
// (playwright.config.ts's demo-fixture project pins knowledge.spec.ts to
// its own VITE_DEMO=1 dev server on :3637 via `testMatch`), so a real-mode
// leg for the same surface cannot live in that file without either losing
// the demo project's fixture data or duplicating the config's file-routing
// mechanism inside a single spec — this file is what stays outside
// `DEMO_FIXTURE_SPECS` and lands on the default "chromium" project (:3636,
// VITE_DEMO off) instead, exactly like code-real-mode.spec.ts. `npm run
// test:e2e -- knowledge` (T2.90's own Verify command) matches both files by
// substring, so both run under one invocation.
//
// knowledge.spec.ts's own header names the gap this file closes: "this
// project has no backend, so it exercises DemoFactDetail / DemoFact, never
// LiveFactDetail / FactDetailResponse — a drift between that live wire
// shape and LiveFactDetailData ... stays provable only by
// fact-detail.test.tsx's vitest suite, which mocks apiFetch by hand and
// never runs against a real, running backend." This file drives
// LiveFactDetail/LiveFactDetailData against a real, running backend instead.
//
// Requires a live, authenticated backend carrying at least one real fact —
// never soft-skips, and never degrades to demo data on a missing backend
// (invariant 14): DEMO defaults off on this project, so a stuck loading
// spinner or a fetch failure is what "no backend" looks like here, not a
// silent fixture render. The fact is seeded by
// backend/scripts/e2e/seed_facts.py through stack.py's `seed_facts=True`
// boot flag (T2.90) — the real fact_lift run over hand-seeded Layer-1 rows,
// never a hand-crafted knowledge_triples row (see that module's docstring).
// Its subject/text ride E2E_SEEDED_FACT_SUBJECT / E2E_SEEDED_FACT_TEXT,
// exported by both the automated recipe (run_playwright_e2e.py, which
// gate.sh --full's "playwright e2e" step always runs) and the manual one
// (`stack.py --keep-running --seed-facts`, sourced from .env-e2e).
const PASSWORD = process.env.E2E_ADMIN_PASSWORD
const SEEDED_SUBJECT = process.env.E2E_SEEDED_FACT_SUBJECT
const SEEDED_TEXT = process.env.E2E_SEEDED_FACT_TEXT

// Fix round 1 (F1): both assertions below used to match by case-insensitive
// substring, which the raw FactTriple ("kestrel-e2e-subject" / "USES" /
// "marigold-e2e-object", rendered by default since the detail level defaults
// to advanced) also satisfies once its parts share a whitespace text node —
// a plausible refactor of a component shared with review-queue.tsx and
// live-dispute.tsx. SEEDED_TEXT's relation word is fact_lift's lowercased
// "uses" (fact_sentence), while the triple's Badge renders the literal
// "USES" — so a case-sensitive match keeps discriminating even if the
// triple's parts are ever joined with plain whitespace. escapeRegExp guards
// the hyphens in the seeded subject/object from being read as regex syntax.
function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.describe("knowledge/facts — real mode", () => {
  test.beforeAll(() => {
    if (!PASSWORD) {
      throw new Error(
        "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
          "missing credential.",
      )
    }
    if (!SEEDED_SUBJECT || !SEEDED_TEXT) {
      throw new Error(
        "E2E_SEEDED_FACT_SUBJECT and E2E_SEEDED_FACT_TEXT must be set — " +
          "boot the backend with fact seeding on: " +
          "`python scripts/e2e/run_playwright_e2e.py` (automatic), or " +
          "`python -m scripts.e2e.stack --keep-running --seed-facts " +
          "--port 8000 --password <pw>` then `source .env-e2e` (manual). " +
          "This spec never falls back to inventing its own expectation.",
      )
    }
    // See auth.spec.ts's header for why a disposable stack (T1.64 plan
    // §2.2) must never reach seedAdminPassword()'s hardcoded darkmem
    // target: that stack already seeded itself with this exact password
    // through the real POST /api/v1/setup front door at boot.
    if (!process.env.E2E_DISPOSABLE_STACK) {
      seedAdminPassword()
    }
  })

  test("the Facts tab renders the real, seeded fact — not the demo fixture", async ({
    page,
  }) => {
    await signIn(page)
    await page.goto("/knowledge/facts")

    await expect(
      // "1 fact" is singular, and "loaded" only shows while more pages exist.
      page.getByText(/^(\d+ facts?|\d+ of \d+ loaded)$/).first(),
    ).toBeVisible()

    await page
      .getByLabel("Filter facts by subject or object")
      .fill(SEEDED_SUBJECT!)

    const row = page
      .locator("[data-index]")
      .filter({ hasText: new RegExp(escapeRegExp(SEEDED_TEXT!)) })
    await expect(row).toHaveCount(1)
  })

  test("the fact detail route renders LiveFactDetail's FactDetailResponse fields verbatim", async ({
    page,
  }) => {
    await signIn(page)
    await page.goto("/knowledge/facts")
    await page
      .getByLabel("Filter facts by subject or object")
      .fill(SEEDED_SUBJECT!)

    const row = page
      .locator("[data-index]")
      .filter({ hasText: new RegExp(escapeRegExp(SEEDED_TEXT!)) })
      .first()
    await row.getByRole("link", { name: /^Open fact: / }).click()

    await expect(page).toHaveURL(/\/knowledge\/facts\/[^/]+$/)
    await expect(page.getByRole("heading", { name: "Fact detail" })).toBeVisible()
    // The wire-shape tripwire (T2.90 clause 3): FactDetailResponse.fact ->
    // use-facts.ts's fromApiDetail (item.fact) -> LiveFactDetailData.fact_text
    // -> this paragraph, rendered unconditionally in both Simple and
    // Advanced. Rename `fact` on the backend schema without updating the
    // frontend adapter and this exact assertion goes red — driven by hand
    // while writing this spec, see the T2.90 report for the transcript.
    await expect(page.getByText(SEEDED_TEXT!, { exact: true })).toBeVisible()

    await page.getByRole("link", { name: "Back to Facts" }).click()
    await expect(page).toHaveURL(/\/knowledge\/facts$/)
  })
})
