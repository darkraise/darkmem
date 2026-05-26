import { z } from "zod"

export const setupPasswordSchema = z
  .object({
    value: z.string().min(8, "Password must be at least 8 characters"),
    confirm: z.string(),
  })
  .refine((d) => d.value === d.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  })

export const setupLLMSchema = z.object({
  skipped: z.boolean(),
  api_kind: z.string(),
  base_url: z.string().url("Must be a valid URL"),
  api_key: z.string().min(1, "API key required when LLM is enabled"),
  supports_embedding: z.boolean(),
  models: z.array(z.string()),
})

export const setupReposSchema = z.object({
  skipped: z.boolean(),
  basePath: z.string(),
  detected: z.array(
    z.object({
      name: z.string().min(1),
      subPath: z.string(),
      selected: z.boolean(),
    }),
  ),
})

export const setupCompleteSchema = z.object({
  password: setupPasswordSchema,
  llm: setupLLMSchema,
  repos: setupReposSchema,
})
export type SetupCompleteInput = z.infer<typeof setupCompleteSchema>
