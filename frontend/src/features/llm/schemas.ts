import { z } from "zod"

const REASONING_EFFORTS = ["none", "low", "medium", "high", "xhigh"] as const
const API_KINDS = [
  "openai",
  "anthropic",
  "google",
  "deepseek",
  "zai",
  "ollama",
] as const

export const llmProfileSchema = z
  .object({
    name: z.string().min(1, "Profile name required"),
    api_kind: z.enum(API_KINDS),
    provider_ref: z.string().optional(),
    model: z.string().min(1, "Model required"),
    reasoning_effort: z.enum(REASONING_EFFORTS).optional(),
    thinking: z.object({ type: z.enum(["enabled", "disabled"]) }).optional(),
    params: z.record(z.string(), z.unknown()).default({}),
    supports_embedding: z.boolean().default(false),
  })
  .superRefine((data, ctx) => {
    if (data.api_kind === "anthropic" && data.reasoning_effort) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["reasoning_effort"],
        message: "Anthropic models do not accept reasoning_effort",
      })
    }
    if (
      data.model === "deepseek-v4-flash" &&
      data.thinking?.type !== "disabled"
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["thinking"],
        message: "deepseek-v4-flash requires thinking.type = disabled",
      })
    }
  })
export type LLMProfileInput = z.infer<typeof llmProfileSchema>
