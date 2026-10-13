import { test, expect, type Page } from "@playwright/test"

/**
 * The progress board and the explorer tree, end to end.
 *
 * Happy-dom performs no layout and dnd-kit's pointer pipeline does not run
 * there, so dragging a card between state columns -- and the register file
 * changing because of it -- is only provable in a real browser. The spec files
 * its own register: the disposable stack starts empty.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD
const PROJECT = "board-e2e"
const URI = "superpowers/registers/e2e.md"

const REGISTER = `# Register — board fixture

**Covers:** docs/superpowers/specs/e2e.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | Drag me to planned | - | - | open | - |
| 2 | Stay where you are | - | - | doing | - |
`

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

/**
 * File the fixture register. The disposable stack has no embedder, so the
 * filing route may answer 500 after the filing committed (it embeds after the
 * commit); the status is not asserted, the document's presence is.
 */
async function fileRegister(page: Page): Promise<string> {
  await page.request.post("/api/v1/documents", {
    data: { project: PROJECT, uri: URI, content: REGISTER },
  })
  const listed = await page.request.get(
    `/api/v1/documents?project=${PROJECT}&limit=100`,
  )
  expect(listed.ok(), `listing: ${listed.status()}`).toBe(true)
  const body = await listed.json()
  const doc = body.items.find((d: { uri: string | null }) => d.uri === URI)
  expect(doc, `${URI} was not filed`).toBeTruthy()
  return doc.id as string
}

test.beforeAll(() => {
  if (!PASSWORD) {
    // Never soft-skip for a missing credential: a skip reads green while
    // asserting nothing.
    throw new Error("E2E_ADMIN_PASSWORD must be set")
  }
})

test.describe("project workspace", () => {
  let documentId = ""

  test.beforeEach(async ({ page }) => {
    await signIn(page)
    documentId = await fileRegister(page)
  })

  test("dragging a register card files the new state into the register", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)

    const lane = page.getByRole("region", { name: "Register rows" })
    const open = lane.getByRole("region", { name: "column open" })
    const planned = lane.getByRole("region", { name: "column planned" })
    const card = open.getByRole("group", { name: /#1 Drag me to planned/ })
    await expect(card).toBeVisible()

    // Columns lay out side by side -- the assertion happy-dom cannot make.
    const openBox = await open.boundingBox()
    const plannedBox = await planned.boundingBox()
    expect(plannedBox!.x).toBeGreaterThan(openBox!.x)

    // dnd-kit's mouse sensor needs a 6px move before a drag starts.
    const from = await card.boundingBox()
    await page.mouse.move(from!.x + 20, from!.y + 10)
    await page.mouse.down()
    await page.mouse.move(from!.x + 40, from!.y + 30, { steps: 5 })
    await page.mouse.move(
      plannedBox!.x + plannedBox!.width / 2,
      plannedBox!.y + 60,
      {
        steps: 15,
      },
    )
    await page.mouse.up()

    await expect(
      planned.getByRole("group", { name: /#1 Drag me to planned/ }),
    ).toBeVisible()
    const read = await page.request.get(
      `/api/v1/documents/${documentId}?include_content=true`,
    )
    expect(read.ok()).toBe(true)
    expect((await read.json()).content).toContain(
      "| 1 | Drag me to planned | - | - | planned | - |",
    )
  })

  test("a row the drag did not touch stays in its column", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)
    const doing = page
      .getByRole("region", { name: "Register rows" })
      .getByRole("region", { name: "column doing" })
    await expect(
      doing.getByRole("group", { name: /#2 Stay where you are/ }),
    ).toBeVisible()
  })

  test("the artifacts tree renders as a file explorer with real row heights", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=artifacts`)

    // Only root folders start expanded, so `registers` is a collapsed folder
    // row until opened -- a test of the folder icon's two states.
    const folder = page.getByText("registers", { exact: true }).first()
    await expect(folder).toBeVisible()
    const folderBox = await folder.boundingBox()
    expect(folderBox!.height).toBeGreaterThan(12)

    const row = folder.locator("..")
    await expect(row.locator("svg.lucide-folder")).toBeVisible()
    await expect(row.locator("svg.lucide-folder-open")).toBeHidden()
    await folder.click()
    await expect(row.locator("svg.lucide-folder-open")).toBeVisible()

    const leaf = page.getByText("e2e.md", { exact: true }).first()
    await expect(leaf).toBeVisible()
    const leafBox = await leaf.boundingBox()
    expect(leafBox!.height).toBeGreaterThan(12)
    expect(leafBox!.x).toBeGreaterThan(folderBox!.x)
  })

  test("a register offers no edit mode", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}?tab=artifacts`)
    await page.getByText("registers", { exact: true }).first().click()
    await page.getByText("e2e.md", { exact: true }).first().click()
    await expect(page.getByRole("button", { name: "Details" })).toBeVisible()
    await expect(page.getByRole("button", { name: /^edit$/i })).toHaveCount(0)
  })

  test("the header carries an icon-only back button to Projects", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}`)
    const back = page.getByRole("link", { name: "Back to Projects" })
    await expect(back).toBeVisible()
    await expect(back).toHaveText("")
    await back.click()
    await expect(page).toHaveURL(/\/projects$/)
  })
})
