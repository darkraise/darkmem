import { test, expect } from "@playwright/test"

test("the code graph canvas is one keyboard stop, and node choice goes through the explorer", async ({ page }) => {
  await page.goto("/code/graph")
  const canvas = page.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })
  await expect(canvas).toBeVisible()
  await expect(canvas.getByRole("button")).toHaveCount(0)

  await canvas.focus()
  await expect(canvas).toBeFocused()
  await page.keyboard.press("Tab")
  await expect(canvas).not.toBeFocused()

  // The demo explorer opens with every folder collapsed (code-explorer.tsx
  // starts `expanded` empty); open folders and files by keyboard until a
  // symbol row (a titled button with no aria-expanded) appears. Opening a
  // file docks it in the inspector, which folds the explorer to a strip, so
  // expand it again whenever that happens. Two frames let React commit and
  // run that folding effect before the next look.
  const settle = () =>
    page.evaluate(
      () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))),
    )
  const expand = page.getByRole("button", { name: "Expand explorer" })
  const explorer = page.getByRole("tabpanel", { name: "Explorer" })
  const symbols = explorer.locator("button[title]:not([aria-expanded])")
  for (let i = 0; i < 12; i++) {
    await settle()
    if (await expand.isVisible()) {
      await expand.focus()
      await page.keyboard.press("Enter")
      continue
    }
    if ((await symbols.count()) > 0) break
    await explorer.locator('button[aria-expanded="false"]').first().focus()
    await page.keyboard.press("Enter")
  }
  const symbol = symbols.first()
  const name = (await symbol.getAttribute("title"))!
  await symbol.focus()
  await page.keyboard.press("Enter")
  const panel = page.getByText("Selected symbol", { exact: true }).locator("xpath=../..")
  // The name shares its <p> with the kind and file, so match by containment.
  await expect(panel).toContainText(name)

  await canvas.focus()
  await page.keyboard.press("+")
  await page.keyboard.press("ArrowLeft")
  await page.keyboard.press("0")
  await page.keyboard.press("Escape")
  await expect(panel).not.toContainText(name)
})
