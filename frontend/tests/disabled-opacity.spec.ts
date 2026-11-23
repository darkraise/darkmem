import { test, expect, type Page } from "@playwright/test"

async function disabledOpacity(page: Page, mode: "dark" | "light"): Promise<string> {
  return page.evaluate((m) => {
    document.documentElement.setAttribute("data-mode", m)
    const button = document.createElement("button")
    button.className = "dr-btn"
    button.disabled = true
    button.textContent = "Held"
    document.body.appendChild(button)
    const opacity = getComputedStyle(button).opacity
    button.remove()
    return opacity
  }, mode)
}

test("a disabled button dims to 0.38 in the dark theme", async ({ page }) => {
  await page.goto("/login")
  await expect(page.getByRole("button").first()).toBeVisible()
  expect(await disabledOpacity(page, "dark")).toBe("0.38")
  expect(await disabledOpacity(page, "light")).toBe("0.5")
})
