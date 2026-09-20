import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The Notion import end to end: what only a real browser against a real server
 * shows is that the zip leaves the dialog, reaches the streaming route, and
 * that a page block's attachment comes back through the attachment route as a
 * rendered image.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error("E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a missing credential.")
  }
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

async function personalProject(page: Page): Promise<string> {
  const response = await page.request.get("/api/v1/projects")
  expect(response.ok()).toBe(true)
  const projects = (await response.json()) as { name: string; kind: string }[]
  const personal = projects.find((p) => p.kind === "personal")
  expect(personal, "the boot seeds a personal project").toBeTruthy()
  return personal!.name
}

test("imports a Notion export and shows the tree and a rendered image", async ({ page }) => {
  await signIn(page)
  await page.goto("/notes")
  await page.getByRole("button", { name: "Page tree actions" }).click()
  await page.getByRole("menuitem", { name: /import from notion/i }).click()

  await page.setInputFiles('input[type="file"]', "tests/fixtures/notion-export.zip")
  await page.getByRole("button", { name: /^import$/i }).click()

  const goTo = page.getByRole("button", { name: /go to imported pages/i })
  await expect(goTo).toBeVisible({ timeout: 60_000 })
  await goTo.click()

  await expect(page.getByText(/Notion import — /).first()).toBeVisible()

  const project = await personalProject(page)
  const listed = await page.request.get(`/api/v1/pages?project=${encodeURIComponent(project)}`)
  expect(listed.ok()).toBe(true)
  const pages = (await listed.json()) as {
    id: string
    parent_id: string | null
    title: string | null
  }[]
  const notes = pages.find((p) => p.title === "Notes")
  expect(notes, "the export's Notes page was imported").toBeTruthy()

  // The tree is derived, not read: the fixture is flat, and Notes is a child
  // of Home only because Home links to it on a line of its own. Walking the
  // ancestry is what shows the derivation reached the database, where the
  // page merely existing would pass on a flat import too.
  const byId = new Map(pages.map((p) => [p.id, p]))
  const ancestry: (string | null)[] = []
  for (let node = notes!; node.parent_id !== null; ) {
    const parent = byId.get(node.parent_id)
    expect(parent, `page ${node.id} names a parent outside the project`).toBeTruthy()
    node = parent!
    ancestry.push(node.title)
  }
  expect(ancestry.length, "Notes is at the root, so nothing derived it").toBeGreaterThan(0)
  expect(ancestry[0]).toBe("Home")
  expect(ancestry[ancestry.length - 1]).toMatch(/^Notion import — /)

  // The tree's expansion state is not what this leg proves; a direct link
  // opens the page whose one block is the export's image.
  await page.goto(`/notes?page=${notes!.id}`)
  const image = page.locator('img[src*="/api/v1/pages/attachments/"]').first()
  await expect(image).toBeVisible({ timeout: 30_000 })
  await expect
    .poll(() => image.evaluate((el) => (el as HTMLImageElement).naturalWidth), { timeout: 30_000 })
    .toBeGreaterThan(0)
})
