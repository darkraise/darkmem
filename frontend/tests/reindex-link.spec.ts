import { test, expect } from "@playwright/test"
import { seedAuth } from "./helpers/auth"

const AGGREGATOR_STUB = {
  relation_rescue: true,
  llm: {
    embedding: { provider: "ollama", base_url: "", model: "old-embed", api_key: null, dimensions: 768, reasoning: false, api_kind: "openai", params: {} },
    extraction: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, api_kind: "openai", params: {} },
    classification: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, api_kind: "openai", params: {} },
    reasoning: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, api_kind: "openai", params: {} },
    summarization: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, api_kind: "openai", params: {} },
    reranker: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, api_kind: "openai", params: {} },
  },
  prompts: {
    extraction: { default: "d", override: "", effective: "d" },
    classification: { default: "d", override: "", effective: "d" },
    reasoning: { default: "d", override: "", effective: "d" },
    summarization: { default: "d", override: "", effective: "d" },
  },
}

test("Re-embed dialog on /pipeline navigates to /reindex", async ({ page }) => {
  await seedAuth(page)
  await page.route("**/api/v1/pipeline", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(AGGREGATOR_STUB),
    }),
  )
  await page.route("**/api/v1/config/system-prompts", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ defaults: {}, overrides: {}, effective: {} }),
    }),
  )
  // Force the obsolete-counts dialog to open by returning non-zero counts
  // from POST /config/llm.
  await page.route("**/api/v1/config/llm", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...AGGREGATOR_STUB.llm,
        obsolete_after_change: { memories: 12, code_chunks: 0, entities: 4 },
      }),
    }),
  )
  // useReembedAll() posts to /reembed/all.
  await page.route("**/api/v1/reembed/all", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        accepted: true,
        batch_id: "test-batch",
        totals: { memories: 12, entities: 4, code_chunks: 0 },
      }),
    }),
  )

  await page.goto("/pipeline")
  // Embedding card is collapsed by default (only extraction starts open).
  await page.getByRole("button", { name: /embedding/i }).first().click()
  // Labels and inputs are sibling-only (no htmlFor), so target by current value.
  await page.locator('input[value="old-embed"]').fill("new-embed-model")
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Embedding model changed")).toBeVisible()
  await page.getByRole("button", { name: "Re-embed now" }).click()
  await expect(page).toHaveURL(/\/reindex$/)
})
