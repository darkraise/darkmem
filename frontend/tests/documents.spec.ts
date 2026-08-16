import { test, expect } from "@playwright/test"

/**
 * TH1.16's surface, end to end (doc 16 §6).
 *
 * Deliberately narrow. The unit suite drives every Q&A outcome against mocked
 * payloads; what only a real run can show is that the page mounts against the
 * live door, that the horizon label is on it, and that an empty corpus reads
 * as empty rather than as a failure — the three things a mocked test cannot
 * distinguish from a page that never rendered.
 */

test("the documents surface is labelled horizon", async ({ page }) => {
  await page.goto("/documents")
  await expect(page.getByText("horizon").first()).toBeVisible()
  await expect(page.getByText(/ships behind its own eval gate/i)).toBeVisible()
})

test("an empty corpus reads as empty rather than as a failure", async ({
  page,
}) => {
  await page.goto("/documents")
  // Either state is honest; what must never appear is the failed-read copy on
  // a healthy install.
  await expect(
    page.getByText(/the document list could not be read/i),
  ).toHaveCount(0)
  await expect(page.getByText(/Documents/i).first()).toBeVisible()
})

test("the grounded-answer control refuses an empty question", async ({
  page,
}) => {
  await page.goto("/documents")
  await expect(page.getByRole("button", { name: /^Ask$/ })).toBeDisabled()
})
