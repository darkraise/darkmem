import { test, expect } from "@playwright/test"

test("A33: in the dark theme a disabled .dr-btn has a computed opacity of 0.38", async ({ page }) => {
  await page.goto("/login")
  await expect(page.getByRole("button").first()).toBeVisible()
  const opacity = await page.evaluate(() => {
    document.documentElement.setAttribute("data-mode", "dark")
    const button = document.createElement("button")
    button.className = "dr-btn"
    button.disabled = true
    button.textContent = "Held"
    document.body.appendChild(button)
    const value = getComputedStyle(button).opacity
    button.remove()
    return value
  })
  expect(opacity).toBe("0.38")
})
