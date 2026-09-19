import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * TH1.16's surface, end to end (doc 16 §6).
 *
 * Deliberately narrow. The unit suite drives every Q&A outcome against mocked
 * payloads; what only a real run can show is that the page mounts against the
 * live door, that the Ask mode states its grounding rule, and that an empty
 * corpus reads as empty rather than as a failure — the three things a mocked test cannot
 * distinguish from a page that never rendered.
 *
 * **These tests never signed in until 2026-08-17, and every one of them
 * failed for it.** `/documents` sits under the `_authenticated` route branch,
 * so an unauthenticated `page.goto` bounces to `/login` and every locator
 * reports "element(s) not found" — which reads exactly like the page mounting
 * empty, the state test 2 exists to distinguish. The three assertions were
 * therefore vacuous in the worst direction: they could not have passed on a
 * healthy install either, so the spec proved nothing about the surface while
 * looking like it did. It went unnoticed because it only runs under
 * `gate.sh --full`, and `--full` is run at phase boundaries rather than per
 * merge.
 *
 * The sign-in is the sibling real-mode specs' own, copied deliberately rather
 * than shared: `knowledge-real-mode.spec.ts` and `code-real-mode.spec.ts`
 * each carry it, and a fourth copy is cheaper than a helper that would have
 * to encode the disposable-stack rule below for every caller.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

/**
 * Since the global-scope change, a fresh browser context opens on ALL_PROJECTS
 * and `/documents` then renders the project chooser rather than the workspace,
 * so the Ask surface never mounts. Picking through the header switcher rather
 * than through the chooser is deliberate: the chooser lists only projects that
 * already hold documents, and the disposable stack seeds a memory-only project,
 * while the workspace itself renders for any project and states its own empty
 * corpus. The scope this sets is the same global one the chooser writes, so
 * `ProjectScopeReconciler` has nothing to widen — the name comes from the
 * server's own list.
 */
async function chooseAnyProject(page: Page) {
  await page.getByRole("button", { name: "Project scope" }).click()
  // "All projects" carries the hint "every scope at once"; every real project
  // row carries an item count, which is what this matches.
  const rows = page.getByRole("button", { name: /\d+ items?$/ })
  const count = await rows.count()
  if (count === 0) {
    throw new Error(
      "No project exists on this stack, so the documents workspace cannot be " +
        "reached — this spec never soft-skips: a stack with no project is a " +
        "broken fixture, not a passing run.",
    )
  }
  await rows.first().click()
}

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error(
      "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
        "missing credential. A skip here is what let it read green while " +
        "asserting nothing.",
    )
  }
  // See auth.spec.ts's header: a disposable stack (T1.64 plan §2.2) must
  // never reach seedAdminPassword()'s hardcoded darkmem target — that stack
  // already seeded itself with this exact password through the real
  // POST /api/v1/setup front door at boot.
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

test("the Ask mode states its grounding rule before anything is asked", async ({
  page,
}) => {
  await signIn(page)
  await page.goto("/documents")
  await chooseAnyProject(page)
  await page.getByRole("radio", { name: "Ask" }).click()
  await expect(
    page.getByText(/an answer that cannot be grounded is withheld/i),
  ).toBeVisible()
})

test("an empty corpus reads as empty rather than as a failure", async ({
  page,
}) => {
  await signIn(page)
  await page.goto("/documents")
  // Either state is honest; what must never appear is the failed-read copy on
  // a healthy install.
  await expect(page.getByText(/could not be loaded/i)).toHaveCount(0)
  await expect(page.getByText(/Documents/i).first()).toBeVisible()
})

test("the grounded-answer control refuses an empty question", async ({
  page,
}) => {
  await signIn(page)
  await page.goto("/documents")
  await chooseAnyProject(page)
  await page.getByRole("radio", { name: "Ask" }).click()
  await expect(page.getByRole("button", { name: /^Ask$/i })).toBeDisabled()
})

test("an unauthenticated visit bounces to /login rather than rendering", async ({
  page,
}) => {
  // The drill for the defect above: without it, a spec that silently stopped
  // signing in would go back to asserting nothing, and the three tests would
  // fail with the same "element(s) not found" that reads as a broken page.
  await page.goto("/documents")
  await expect(page).toHaveURL(/\/login/)
})
