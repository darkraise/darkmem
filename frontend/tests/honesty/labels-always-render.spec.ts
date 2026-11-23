import { test, expect, type Page } from "@playwright/test"

/** The header switcher is the one project scope; its rows are named
 *  "<project><N> items". */
async function selectProject(page: Page, name: string) {
  await page.getByRole("button", { name: "Project scope" }).click()
  await page
    .getByRole("button", { name: new RegExp(`^${name}\\s*\\d+ items?$`) })
    .click()
}

// honesty/labels-always-render (T1.48). Simple/Advanced ships with the
// first advanced surface, and simple never hides an honesty signal
// (invariant 14): verification badges, layer labels, superseded/stale
// labels, and exclusion counts must render in BOTH detail modes. Only the
// technical breakdown (per-modality/fused scores, arm breakdown,
// fingerprints, raw config keys) collapses in simple mode — proven
// separately by src/components/darkmem/__tests__/darkmem-components.test.tsx
// and src/features/memories/__tests__/real-memories-view.test.tsx.
//
// Exercised against the demo store (DEMO defaults on until T1.58), which
// shares the exact components (MemoryRow, VerificationBadge, LayerChip,
// StaleBadge) the real surfaces bind to — the same honesty guard applies
// whichever data source populated the row.

const LABEL: Record<"simple" | "advanced", string> = {
  simple: "Simple",
  advanced: "Advanced",
}

async function setDetailLevel(page: Page, level: "simple" | "advanced") {
  const toggle = page.getByRole("radio", { name: LABEL[level] })
  await toggle.click()
}

test.describe("honesty/labels-always-render", () => {
  test("memory list: exclusion count renders in both modes", async ({
    page,
  }) => {
    await page.goto("/memories")

    await expect(page.getByText(/^\d+ of \d+ shown$/)).toBeVisible()

    await selectProject(page, "default")

    // Both "cookie-secure" rows live in project "darkmem", so scoping to
    // "default" excludes them by project.
    await page.getByLabel("Search memories").fill("cookie-secure")

    for (const level of ["simple", "advanced"] as const) {
      await setDetailLevel(page, level)

      await expect(page.getByText("2 memories excluded")).toBeVisible()
      await expect(
        page.getByText(/outside the current project scope \(default\)/),
      ).toBeVisible()
    }
  })

  test("memory list: superseded badge renders in both modes, never filtered out", async ({
    page,
  }) => {
    await page.goto("/memories")

    await expect(page.getByText(/^\d+ of \d+ shown$/)).toBeVisible()

    await selectProject(page, "darkmem")
    // "introduced" appears in exactly one curated memory — the superseded
    // reranker row — so this isolates it without relying on ranking order.
    await page.getByLabel("Search memories").fill("introduced")

    for (const level of ["simple", "advanced"] as const) {
      await setDetailLevel(page, level)
      // Exact: the status filter's "Superseded" toggle also matches loosely.
      await expect(page.getByText("superseded", { exact: true })).toBeVisible()
    }
  })

  test("article detail: verification badge and stale label render in both modes", async ({
    page,
  }) => {
    // ARTICLE_IDS.degradedChannel — corroborated but stale (a new
    // corroborated fact changed its fact_set_hash since synthesis). The
    // hero badge is not the only "corroborated" text on the page — the
    // open-by-default Citations section cites two corroborated facts too
    // — so every match here is scoped with .first(), the hero's DOM
    // position (it renders before the Citations accordion).
    await page.goto("/knowledge/articles/a7d3b0f2")

    await expect(page.getByText("corroborated").first()).toBeVisible()

    for (const level of ["simple", "advanced"] as const) {
      await setDetailLevel(page, level)
      await expect(page.getByText("corroborated").first()).toBeVisible()
      await expect(page.getByText("stale", { exact: true })).toBeVisible()
      await expect(
        page.getByText(/synthesised before the latest verified change/),
      ).toBeVisible()
    }
  })

  test("article detail: superseded badge and successor link render in both modes", async ({
    page,
  }) => {
    // ARTICLE_IDS.retrievalFusionV1 — superseded_by ARTICLE_IDS.retrievalFusion.
    // "superseded" also matches inside the successor link's text, so the
    // badge check is scoped with .first() (the badge renders before the
    // successor link in the hero).
    await page.goto("/knowledge/articles/af0b3d9a")

    await expect(page.getByText("superseded").first()).toBeVisible()

    for (const level of ["simple", "advanced"] as const) {
      await setDetailLevel(page, level)
      await expect(page.getByText("superseded").first()).toBeVisible()
      await expect(
        page.getByText(/superseded by a newer version/),
      ).toBeVisible()
    }
  })
})
