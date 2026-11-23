import { test, expect, type Page } from "@playwright/test"

/** The header switcher is the one project scope; its rows are named
 *  "<project><N> items". */
async function selectProject(page: Page, name: string) {
  await page.getByRole("button", { name: "Project scope" }).click()
  await page
    .getByRole("button", { name: new RegExp(`^${name}\\s*\\d+ items?$`) })
    .click()
}

// honesty/no-silent-drop (docs/planning/e2e-test-plan.md, "The honesty
// suite"; owned by T1.33). Asserts: a filtered channel reports its count,
// and no row that matched the query disappears from the response without
// that count naming it.
//
// This is the mirror of the seven isolation leaks closed earlier in E1
// (memory_reason, ChatService, the graph walk, get_memory_context, the
// projection endpoint, memory_find_duplicates, the neighbour fetch) — every
// one of those silently *included* a row it should have scoped out. The
// failure mode here is the opposite: silently *excluding* a row, which looks
// identical to "nothing matched" unless the exclusion is counted and shown.
//
// Exercised against the demo store (`searchDemoMemories` in
// src/demo/memories.ts), which already implements this rule for the
// `/memories` page — fast and stable per the e2e-test-plan's fixture tiers,
// and it does not depend on T1.44's real-backend wiring to be meaningful.
// The fixture is deterministic: every curated memory lives in project
// "darkmem" (src/demo/data/memories-curated.ts) and the generated bulk
// fixture is entirely project "default" (src/demo/data/memories.json).
// "pgvector" matches exactly one row, a curated one, and "fastapi" matches
// only bulk rows, so the two-token search scoped to "darkmem" keeps one row
// and must count the out-of-project matches: a mixed batch, not the
// all-excluded edge case `honesty/exclusions-on-empty` (T1.44) owns.
test.describe("honesty/no-silent-drop", () => {
  test("an out-of-scope match is excluded with a rendered, non-zero count — not silently dropped", async ({
    page,
  }) => {
    await page.goto("/memories")

    await expect(page.getByText(/^\d+ of \d+ shown$/)).toBeVisible()

    await page.getByLabel("Search memories").fill("pgvector fastapi")
    await selectProject(page, "darkmem")

    // The surviving row must still render — this proves the query itself
    // matched, so the exclusion strip cannot be explained away as "there
    // was nothing to find in the first place".
    const shownLine = page.getByText(/^\d+ of \d+ shown$/)
    await expect(shownLine).toHaveText("1 of 1 shown")

    // The rule under test: the excluded rows must be named with a count,
    // not merely missing from the list above.
    const exclusionCount = page.getByText(/^\d+ memor(y|ies) excluded$/)
    await expect(exclusionCount).toBeVisible()
    const count = Number(((await exclusionCount.textContent()) ?? "").split(" ")[0])
    expect(count).toBeGreaterThan(0)
    await expect(
      page.getByText(/outside the current project scope \(darkmem\)/),
    ).toBeVisible()
  })
})
