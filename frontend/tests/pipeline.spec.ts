import { test, expect } from "@playwright/test"
import { seedAuth } from "./helpers/auth"

test.beforeEach(async ({ page }) => {
  await seedAuth(page)

  let aggregatorStages: "llm" | "ml" = "llm"
  const aggregator = () => ({
    mode: aggregatorStages,
    stages: {
      extraction: aggregatorStages,
      classification: aggregatorStages,
      retrieval: aggregatorStages,
    },
    shadow_mode: false,
    ml: {
      device: "auto",
      effective_device: null,
      cuda_index: 0,
      persistence: "ttl",
      idle_ttl_minutes: 30,
      eviction_check_interval_seconds: 60,
      cpu_fallback: true,
      available_devices: [
        { id: "cpu", label: "CPU", kind: "cpu", index: null },
      ],
    },
    llm: {
      embedding: { provider: "ollama", base_url: "", model: "qwen3-embedding:0.6b", api_key: null, dimensions: 1024, reasoning: false, tool_call_mode: "json", params: {} },
      extraction: { provider: "ollama", base_url: "", model: "qwen2.5:3b", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
      classification: { provider: "ollama", base_url: "", model: "qwen2.5:3b", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
      reasoning: { provider: "ollama", base_url: "", model: "qwen2.5:3b", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
      summarization: { provider: "ollama", base_url: "", model: "qwen2.5:3b", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
      reranker: { provider: "ollama", base_url: "", model: "qwen2.5:3b", api_key: null, dimensions: null, reasoning: false, tool_call_mode: "json", params: {} },
    },
    prompts: {
      extraction: { default: "d", override: "", effective: "d" },
      extraction_entities: { default: "d", override: "", effective: "d" },
      extraction_relationships: { default: "d", override: "", effective: "d" },
      classification: { default: "d", override: "", effective: "d" },
      reasoning: { default: "d", override: "", effective: "d" },
      summarization: { default: "d", override: "", effective: "d" },
    },
  })

  await page.route("**/api/v1/pipeline", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(aggregator()),
    }),
  )
  await page.route("**/api/v1/pipeline/metrics", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        cpu_percent: 12,
        ram_used_mb: 1024,
        ram_total_mb: 16384,
        gpu_util_percent: null,
        vram_used_mb: null,
        vram_total_mb: null,
        groups: {
          extraction: { loaded: false, idle_seconds: null },
          classification: { loaded: false, idle_seconds: null },
          retriever: { loaded: false, idle_seconds: null },
        },
      }),
    }),
  )
  await page.route("**/api/v1/pipeline/mode", async (route, req) => {
    const body = JSON.parse(req.postData() || "{}")
    aggregatorStages = body.mode === "ml" ? "ml" : "llm"
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mode: aggregatorStages,
        stages: {
          extraction: aggregatorStages,
          classification: aggregatorStages,
          retrieval: aggregatorStages,
        },
      }),
    })
  })
  await page.route("**/api/v1/config/system-prompts", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ defaults: {}, overrides: {}, effective: {} }),
    }),
  )
})

test("pipeline page flips mode and exposes advanced switches", async ({ page }) => {
  await page.goto("/pipeline")
  await expect(page.getByRole("heading", { name: "Pipeline" })).toBeVisible()

  await page.getByRole("radio", { name: "Darkmem ML stack" }).click()

  await page.getByRole("button", { name: /Advanced/ }).first().click()

  for (const stage of ["extraction", "classification", "retrieval"] as const) {
    const row = page.locator("div.flex.items-center.justify-between", {
      has: page.locator(`label:has-text("${stage}")`),
    })
    await expect(row.getByRole("switch")).toHaveAttribute("data-state", "checked")
  }
})

test("unload all shows confirmation dialog", async ({ page }) => {
  await page.goto("/pipeline")
  await page.getByRole("button", { name: "Unload all models" }).click()
  await expect(page.getByText("Unload all ML models?")).toBeVisible()
  await page.getByRole("button", { name: "Cancel" }).click()
  await expect(page.getByText("Unload all ML models?")).toBeHidden()
})
