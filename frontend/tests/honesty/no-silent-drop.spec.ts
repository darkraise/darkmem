import { test, expect } from "@playwright/test"

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
// "darkmem" (src/demo/data/memories-curated.ts), and exactly two of them —
// ID_COOKIE_LAN (applies_when: "env=dev") and ID_TRUST_PROXY (no declared
// context) — match the token "cookie-secure". Declaring session context
// "env=prod" must exclude the first and keep the second: a mixed batch,
// not the all-excluded edge case `honesty/exclusions-on-empty` (T1.44) owns.
test.describe("honesty/no-silent-drop", () => {
  test("a context-conflicting match is excluded with a rendered, non-zero count — not silently dropped", async ({
    page,
  }) => {
    await page.goto("/memories")

    await expect(page.getByText(/^\d+ of \d+ shown$/)).toBeVisible()

    // The page's own context filter (a Select combobox), distinct from the
    // app-chrome ContextChip ("Session context").
    const contextTrigger = page.getByRole("combobox", {
      name: "Filter by context",
    })
    await expect(contextTrigger).toBeVisible()

    await page.getByLabel("Search memories").fill("cookie-secure")
    await contextTrigger.click()
    await page.getByRole("option", { name: "env=prod" }).click()

    // The surviving row (ID_TRUST_PROXY) must still render — this proves
    // the query itself matched, so an empty exclusion strip cannot be
    // explained away as "there was nothing to find in the first place".
    const shownLine = page.getByText(/^\d+ of \d+ shown$/)
    await expect(shownLine).toBeVisible()
    const shownText = (await shownLine.textContent()) ?? ""
    const match = shownText.match(/^(\d+) of (\d+) shown$/)
    expect(match).not.toBeNull()
    const [, shown, matched] = match!
    expect(Number(shown)).toBe(1)
    expect(Number(matched)).toBe(1)

    // The rule under test: the excluded row (ID_COOKIE_LAN) must be named
    // with a count, not merely missing from the list above.
    const exclusionCount = page.getByText(/^\d+ memory excluded$/)
    await expect(exclusionCount).toBeVisible()
    await expect(exclusionCount).toHaveText("1 memory excluded")

    await expect(page.getByText(/env=dev-only row/i)).toBeVisible()
  })
})
