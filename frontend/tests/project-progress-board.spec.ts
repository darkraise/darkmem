import { test, expect, type Page } from "@playwright/test"

/**
 * The Progress board and the explorer tree, end to end.
 *
 * These two surfaces are the reason a real browser is not optional here. The
 * unit suite runs in happy-dom, which performs NO layout: it can assert that both
 * folder icons render and that a column exists, and it would pass just as
 * happily if every row collapsed to zero height, the indent guides drew
 * nowhere, or the board's columns stacked into an unreadable ribbon. Height,
 * placement and "did the CSS actually win over the library's own" are what
 * only this file can show.
 *
 * The board is a projection of two committed markdown files, so this spec
 * files its own miniature corpus rather than depending on the repo's — the
 * disposable stack starts empty, and a board that renders nothing is exactly
 * the failure mode being tested against.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD
const PROJECT = "board-e2e"

const LEDGER = `# Progress

| Epic | Tasks | todo | wip | blocked | review | done | dropped | Gate |
|---|---|---|---|---|---|---|---|---|
| E9 — Board fixture | 3 | 1 | 0 | 1 | 0 | 1 | 0 | G-Z open |

## E9

| Task | Title | Size | Model | Effort | Version | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| T9.01 | A startable task | S | Opus | high | — | claude/lane-a | todo | | | |
| T9.02 | A blocked task | M | Sonnet | high | — | claude/lane-a | blocked | | | waiting on an owner ruling |
| T9.03 | A finished task | S | Haiku | high | — | claude/lane-a | done | abc1234 | approved | |
`

const EPIC = `# E9 — Board fixture

**Goal:** Exercise the board.

**Entry gate:** **G-Z** holds T9.02 only.

---

## Lane A — the only lane

#### T9.01 — A startable task

\`Model: Opus 5\` · \`Effort: high\` · \`Size: S\` · \`Depends: —\`

**Done when:**
- [ ] It renders

#### T9.02 — A blocked task

\`Model: Sonnet 5\` · \`Effort: high\` · \`Size: M\` · \`Depends: —\`

#### T9.03 — A finished task

\`Model: Haiku\` · \`Effort: high\` · \`Size: S\` · \`Depends: —\`
`

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

/**
 * File one fixture document.
 *
 * The disposable stack has no embedding endpoint, and this door embeds a
 * document's blocks after filing them. That embed fails here and the route
 * answers 500 -- but the filing has already committed by then (embedding runs
 * after the filing commits, never inside it), so the document and its blocks
 * exist and both surfaces under test read them without touching a vector.
 *
 * So the status is deliberately not asserted; what IS asserted is the thing
 * the tests actually depend on -- that the document is there afterwards. A
 * fixture that silently filed nothing would leave every assertion below
 * looking at an empty board, which is the failure this spec exists to catch.
 */
async function file(page: Page, uri: string, content: string) {
  await page.request.post("/api/v1/documents", {
    data: { project: PROJECT, uri, content },
  })
  const listed = await page.request.get(
    `/api/v1/documents?project=${PROJECT}&limit=100`,
  )
  expect(listed.ok(), `listing after ${uri}: ${listed.status()}`).toBe(true)
  const body = await listed.json()
  expect(
    body.items.some((d: { uri: string | null }) => d.uri === uri),
    `${uri} was not filed`,
  ).toBe(true)
}

test.beforeAll(() => {
  if (!PASSWORD) {
    // Never soft-skip for a missing credential: a skip here reads green while
    // asserting nothing, which is the defect documents.spec.ts records.
    throw new Error("E2E_ADMIN_PASSWORD must be set")
  }
})

test.describe("project workspace", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page)
    await file(page, "docs/planning/progress.md", LEDGER)
    await file(page, "docs/planning/tasks/E9-board-fixture.md", EPIC)
  })

  test("the Progress tab renders a board, not the ledger's markdown", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)

    const todo = page.getByRole("heading", { name: "todo", exact: true })
    await expect(todo).toBeVisible()
    await expect(page.getByRole("heading", { name: "blocked", exact: true })).toBeVisible()

    // The card, and the Note the eleven-column table hides.
    await expect(page.getByText("A startable task")).toBeVisible()
    await expect(page.getByText("waiting on an owner ruling")).toBeVisible()

    // Columns lay out side by side rather than stacking -- the assertion
    // happy-dom cannot make.
    const todoBox = await todo.boundingBox()
    const blockedBox = await page
      .getByRole("heading", { name: "blocked", exact: true })
      .boundingBox()
    expect(todoBox).not.toBeNull()
    expect(blockedBox).not.toBeNull()
    expect(blockedBox!.x).toBeGreaterThan(todoBox!.x)
    expect(Math.abs(blockedBox!.y - todoBox!.y)).toBeLessThan(4)
  })

  test("the startable filter honours the gate's named task", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)
    await page.getByRole("button", { name: /startable only/i }).click()

    // T9.01 is todo with no dependency and is not the task G-Z names.
    await expect(page.getByText("A startable task")).toBeVisible()
    await expect(page.getByText("A finished task")).toHaveCount(0)
  })

  test("the artifacts tree renders as a file explorer with real row heights", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}?tab=artifacts`)

    // Only ROOT folders start expanded (`rootFolderPaths`), so `planning` is
    // a collapsed folder row until it is opened -- which is what makes this a
    // test of the folder icon's two states rather than just of one row.
    const folder = page.getByText("planning", { exact: true }).first()
    await expect(folder).toBeVisible()

    // A row that collapsed to zero height passes every happy-dom assertion.
    const folderBox = await folder.boundingBox()
    expect(folderBox).not.toBeNull()
    expect(folderBox!.height).toBeGreaterThan(12)

    // The folder icon flips with its branch, and only a browser can say so:
    // both icons are always in the DOM and a `data-state` CSS variant picks
    // one, so happy-dom sees two icons in every state. Scoped to THIS row --
    // `docs` above it is already open, and an unscoped `.first()` reads that
    // row's correctly-hidden closed icon.
    const row = folder.locator("..")
    await expect(row.locator("svg.lucide-folder")).toBeVisible()
    await expect(row.locator("svg.lucide-folder-open")).toBeHidden()

    await folder.click()
    await expect(row.locator("svg.lucide-folder-open")).toBeVisible()
    await expect(row.locator("svg.lucide-folder")).toBeHidden()

    const leaf = page.getByText("progress.md", { exact: true }).first()
    await expect(leaf).toBeVisible()

    const leafBox = await leaf.boundingBox()
    expect(leafBox).not.toBeNull()
    expect(leafBox!.height).toBeGreaterThan(12)
    // Indented past its folder: the guide and padding actually applied.
    expect(leafBox!.x).toBeGreaterThan(folderBox!.x)

    // The leaf took an extension icon, not the generic fallback.
    await expect(page.locator("svg.lucide-file-text").first()).toBeVisible()
  })

  test("the header carries an icon-only back button to Projects", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}`)

    const back = page.getByRole("link", { name: "Back to Projects" })
    await expect(back).toBeVisible()
    // Icon-only: the destination lives in the accessible name and the
    // tooltip, never as text beside the arrow.
    await expect(back).toHaveText("")

    await back.click()
    await expect(page).toHaveURL(/\/projects$/)
  })
})
