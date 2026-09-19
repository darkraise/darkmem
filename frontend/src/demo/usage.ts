import type { UsageOverview, UsageSeries } from "@/hooks/api"

const row = (
  key: string,
  cost_micros: number,
  calls: number,
  prompt_tokens: number,
  completion_tokens: number,
) => ({
  key,
  cost_micros,
  calls,
  prompt_tokens,
  cached_tokens: Math.round(prompt_tokens * 0.3),
  completion_tokens,
  unmeasured_calls: 0,
  unpriced_calls: 0,
})

export const DEMO_USAGE_OVERVIEW: UsageOverview = {
  window_start: "2026-06-25T00:00:00Z",
  window_end: "2026-07-25T00:00:00Z",
  total_cost_micros: 4_182_000,
  total_calls: 1_864,
  prompt_tokens: 2_410_000,
  cached_tokens: 723_000,
  completion_tokens: 318_000,
  reasoning_tokens: 0,
  unmeasured_calls: 12,
  unpriced_calls: 0,
  unpriced_models: [],
  merged_classification_present: true,
  cache_hit_ratio: 0.3,
  failed_calls: 9,
  failed_cost_micros: 21_000,
  by_purpose: [
    row("extraction", 2_310_000, 820, 1_420_000, 190_000),
    row("reasoning", 1_080_000, 214, 540_000, 88_000),
    row("reranker", 512_000, 610, 360_000, 24_000),
    row("summarization", 280_000, 220, 90_000, 16_000),
  ],
  by_model: [
    row("deepseek-v4-flash", 3_390_000, 1_030, 1_960_000, 278_000),
    row("qwen3-embedding:0.6b", 0, 610, 360_000, 0),
    row("gpt-5.5", 792_000, 224, 90_000, 40_000),
  ],
  by_subject_type: [
    row("memory", 2_600_000, 1_100, 1_500_000, 200_000),
    row("chat", 1_080_000, 214, 540_000, 88_000),
    row("job", 502_000, 550, 370_000, 30_000),
  ],
}

const DAY_MS = 86_400_000
const SERIES_END = Date.UTC(2026, 6, 25)

export const DEMO_USAGE_SERIES: UsageSeries = {
  bucket: "day",
  buckets: Array.from({ length: 30 }, (_, i) => {
    const calls = 40 + ((i * 17) % 45)
    return {
      bucket_start: new Date(SERIES_END - (29 - i) * DAY_MS).toISOString(),
      cost_micros: calls * 2_200,
      calls,
      prompt_tokens: calls * 1_300,
      completion_tokens: calls * 170,
      unmeasured_calls: i % 9 === 0 ? 1 : 0,
    }
  }),
}
