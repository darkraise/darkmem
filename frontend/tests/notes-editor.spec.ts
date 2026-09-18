import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The /notes page editor end to end: what only a real browser against a real
 * server can show is that an edit leaves the editor, reaches the page block
 * verbs and comes back on a reload. The unit suite drives the save engine
 * against a fake server; this drives the real one.
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

async function createPage(page: Page, title: string, content?: string): Promise<string> {
  const project = await personalProject(page)
  const response = await page.request.post("/api/v1/pages", { data: { project, title, content: content ?? null } })
  expect(response.status()).toBe(201)
  return ((await response.json()) as { id: string }).id
}

async function openPage(page: Page, id: string) {
  await page.goto(`/notes?page=${id}`)
  await expect(page.locator(".bn-editor")).toBeVisible()
}

async function saved(page: Page) {
  // A blur inside the editor on mount can flush a no-op save (nothing was
  // pending yet) and flash "Saved" before the action under test ever runs;
  // waiting past the engine's text-edit debounce (TEXT_IDLE_MS, 800ms)
  // before checking makes this always observe that action's own save
  // rather than a stale one.
  await page.waitForTimeout(1000)
  await expect(page.getByText("Saved", { exact: true })).toBeVisible()
}

async function pageBlocks(page: Page, id: string) {
  const response = await page.request.get(`/api/v1/pages/${id}`)
  return ((await response.json()) as { blocks: { type: string; text: string; properties: Record<string, unknown> | null }[] })
    .blocks
}

test("typing persists across a reload", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Typing")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.keyboard.type("Hello from the editor")
  await saved(page)
  await page.reload()
  await expect(page.locator(".bn-editor")).toContainText("Hello from the editor")
})

test("a to-do, a toggle and a callout save with their properties", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Blocks")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.keyboard.type("[] ship it")
  await page.locator('.bn-editor input[type="checkbox"]').first().check()
  // Checking the box moves focus onto the checkbox itself; clicking the
  // item's text puts the cursor back in the editable content before the
  // keyboard is used again.
  await page.locator(".bn-editor").getByText("ship it").click()
  await page.keyboard.press("End")
  await page.keyboard.press("Enter")
  await page.keyboard.press("Enter")
  await page.keyboard.type("/toggle")
  await page.getByText("Toggle List", { exact: true }).click()
  await page.keyboard.type("folded")
  await page.keyboard.press("Enter")
  await page.keyboard.press("Enter")
  await page.keyboard.type("/callout")
  await page.getByText("Callout: warning", { exact: true }).click()
  await page.keyboard.type("careful")
  await saved(page)

  const blocks = await pageBlocks(page, id)
  expect(blocks.find((b) => b.type === "todo")).toMatchObject({ text: "ship it", properties: { checked: true } })
  expect(blocks.find((b) => b.type === "toggle")).toMatchObject({ text: "folded" })
  expect(blocks.find((b) => b.type === "callout")).toMatchObject({ text: "careful", properties: { variant: "warning" } })

  await page.reload()
  await expect(page.locator('.bn-editor input[type="checkbox"]').first()).toBeChecked()
  // Two elements carry data-variant="warning": BlockNote's own node view
  // wrapper and the callout's own styled div inside it.
  await expect(page.locator('.bn-editor [data-variant="warning"]').first()).toContainText("careful")

  const toggle = page.locator(".bn-toggle-wrapper").first()
  const shown = await toggle.getAttribute("data-show-children")
  await toggle.locator(".bn-toggle-button").click()
  await expect(toggle).not.toHaveAttribute("data-show-children", shown ?? "")
})

test("a pasted multi-block snippet arrives as blocks", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Paste")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.evaluate(() => {
    const data = new DataTransfer()
    data.setData("text/plain", "- one\n- two\n\n> quoted")
    document
      .querySelector(".bn-editor")!
      .dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }))
  })
  await saved(page)
  const blocks = await pageBlocks(page, id)
  expect(blocks.filter((b) => b.type === "list").map((b) => b.text)).toEqual(["one", "two"])
  expect(blocks.some((b) => b.type === "quote" && b.text === "quoted")).toBe(true)
})

test("inline HTML survives an edit to the words beside it", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Atoms", "Press <kbd>K</kbd> now")
  await openPage(page, id)
  await page.locator(".bn-editor").getByText("now").click()
  await page.keyboard.press("End")
  await page.keyboard.type(" please")
  await saved(page)
  const [first] = await pageBlocks(page, id)
  expect(first!.text).toBe("Press <kbd>K</kbd> now please")
})

test("a page moves in the tree, goes to the trash and comes back", async ({ page }) => {
  await signIn(page)
  const first = await createPage(page, "Tree first")
  const second = await createPage(page, "Tree second")
  await page.goto(`/notes?page=${first}`)
  const source = page.getByText("Tree second", { exact: true }).first()
  const target = page.getByText("Tree first", { exact: true }).first()
  const box = (await target.boundingBox())!
  await source.hover()
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2, box.y + 2, { steps: 12 })
  await page.mouse.up()
  await expect
    .poll(async () => {
      const list = await page.request.get(`/api/v1/pages?project=${encodeURIComponent(await personalProject(page))}`)
      const rows = (await list.json()) as { id: string; order_index: number; parent_id: string | null }[]
      const a = rows.find((r) => r.id === first)!
      const b = rows.find((r) => r.id === second)!
      return a.parent_id === b.parent_id && b.order_index < a.order_index
    })
    .toBe(true)

  const deleted = await page.request.delete(`/api/v1/pages/${second}`)
  expect(deleted.status()).toBe(204)
  await page.goto("/notes")
  await page.getByRole("button", { name: "Trash" }).click()
  await page.getByRole("button", { name: "Restore Tree second" }).click()
  await expect(page.getByText("Tree second", { exact: true }).first()).toBeVisible()
})
