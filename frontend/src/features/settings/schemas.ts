import { z } from "zod"

export const generalSettingsSchema = z.object({
  default_project: z.string().min(1),
  hybrid_search_enabled: z.boolean(),
  semantic_weight: z.number().min(0).max(1),
})

export const pipelineSettingsSchema = z.object({
  pipeline_concurrency: z.number().int().min(1).max(64),
  llm_enrichment_enabled: z.boolean(),
  relation_rescue: z.boolean(),
  confidence_rank_gamma: z.number().min(0).max(1),
})

export const settingsSchema = z.discriminatedUnion("tab", [
  z.object({ tab: z.literal("general"), values: generalSettingsSchema }),
  z.object({ tab: z.literal("pipeline"), values: pipelineSettingsSchema }),
])
export type SettingsInput = z.infer<typeof settingsSchema>
