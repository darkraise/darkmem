import { test, expect, type Page } from "@playwright/test"

/** The header switcher is the one project scope; its rows are named
 *  "<project><N> items". */
async function selectProject(page: Page, name: string) {
  await page.getByRole("button", { name: "Project scope" }).click()
  await page
    .getByRole("button", { name: new RegExp(`^${name}\\s*\\d+ items?$`) })
    .click()
}

// honesty/exclusions-on-empty (docs/planning/e2e-test-plan.md, "The honesty
// suite"; owned by T1.44). Asserts: exclusion counts render even when the
// result list is empty — the exact case a silent drop hides best, because
// an empty result area reads as "nothing here" whether or not anything was
// filtered out along the way (invariant 14).
//
// Sibling to honesty/no-silent-drop (T1.33), which proves a *mixed* batch —
// one excluded row, one surviving row — never drops the excluded one
// uncounted. This spec proves the harder edge: when EVERY match is
// excluded and zero rows survive, the exclusion strip must still render,
// not disappear alongside the (now-empty) result list.
//
// Exercised against the demo store (`searchDemoMemories` in
// src/demo/memories.ts), matching the fixture tier and the wiring
// no-silent-drop already established — fast, stable, and independent of
// T1.44's real-backend wiring for the same reason: the rule under test is a
// UI rendering rule, not a backend behavior. The fixture is deterministic:
// every curated memory lives in project "darkmem" (src/demo/data/
// memories-curated.ts) and the generated bulk fixture is entirely project
// "default" (src/demo/data/memories.json). ID_COOKIE_LAN and ID_TRUST_PROXY
// are the only two rows anywhere in the fixture whose technologies include
// the token "cookie-secure", and both live in project "darkmem" — so
// scoping the same search to project "default" excludes both of them by
// project, leaving zero results with a nonzero, named exclusion count.
test.describe("honesty/exclusions-on-empty", () => {
  test("exclusion counts render even when every match was excluded and zero rows remain", async ({
    page,
  }) => {
    await page.goto("/memories")

    await expect(page.getByText(/^\d+ of \d+ shown$/)).toBeVisible()

    await page.getByLabel("Search memories").fill("cookie-secure")
    await selectProject(page, "default")

    // Zero rows survive: both matches for this token live in project
    // "darkmem", so scoping to "default" excludes all of them — the demo
    // fixture's own totalMatches counts only post-filter survivors, so it
    // reads 0 here too. That is exactly why the exclusion strip, not the
    // shown/matched counter, is the signal this spec exists to protect.
    const shownLine = page.getByText(/^\d+ of \d+ shown$/)
    await expect(shownLine).toBeVisible()
    await expect(shownLine).toHaveText("0 of 0 shown")

    // The rule under test: the exclusion strip renders with its count even
    // though the result list right below it is empty — an empty result
    // area is never allowed to read as "there was nothing to exclude."
    const exclusionCount = page.getByText(/^\d+ memories excluded$/)
    await expect(exclusionCount).toBeVisible()
    await expect(exclusionCount).toHaveText("2 memories excluded")

    // The empty state renders too — the strip is not the only thing on
    // screen, and the two coexist rather than one masking the other.
    await expect(page.getByText(/no matches/i)).toBeVisible()
  })
})
