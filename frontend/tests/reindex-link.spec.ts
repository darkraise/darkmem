import { test, expect } from "@playwright/test"
import { seedAuth } from "./helpers/auth"

const AGGREGATOR_STUB = {
  mode: "llm",
  stages: { extraction: "llm", classification: "llm", retrieval: "llm" },
  shadow_mode: false,
  ml: {
    device: "auto", effective_device: null, cuda_index: 0,
    persistence: "ttl", idle_ttl_minutes: 30, eviction_check_interval_seconds: 60,
    cpu_fallback: true,
    available_devices: [{ id: "cpu", label: "CPU", kind: "cpu", index: null }],
  },
  llm: {
    embedding: { provider: "ollama", base_url: "", model: "old-embed", api_key: null, dimensions: 768, reasoning: false, tool_call_mode: "json", params: {} },
    extraction: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
    classification: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
    reasoning: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
    summarization: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
    reranker: { provider: "ollama", base_url: "", model: "x", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
  },
  prompts: {
    extraction: { default: "d", override: "", effective: "d" },
    extraction_entities: { default: "d", override: "", effective: "d" },
    extraction_relationships: { default: "d", override: "", effective: "d" },
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
  await page.route("**/api/v1/pipeline/metrics", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        cpu_percent: null, ram_used_mb: null, ram_total_mb: null,
        gpu_util_percent: null, vram_used_mb: null, vram_total_mb: null,
        groups: {
          extraction: { loaded: false, idle_seconds: null },
          classification: { loaded: false, idle_seconds: null },
          retriever: { loaded: false, idle_seconds: null },
        },
      }),
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
  // Intercept the re-embed start so we don't need a real backend.
  // useReembedAll() posts to /reembed/all (not /reembed/start as the plan draft said).
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
  // The accessible name is lowercased ("▸ embedding old-embed · 768d · ollama"),
  // so match with a case-insensitive regex.
  await page.getByRole("button", { name: /embedding/i }).first().click()
  // Labels and inputs are sibling-only (no htmlFor), so getByLabel can't
  // associate them. Target the Embedding card's Model input by its current
  // value — "old-embed" is only rendered in the embedding config stub.
  await page.locator('input[value="old-embed"]').fill("new-embed-model")
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Embedding model changed")).toBeVisible()
  await page.getByRole("button", { name: "Re-embed now" }).click()
  await expect(page).toHaveURL(/\/reindex$/)
})
