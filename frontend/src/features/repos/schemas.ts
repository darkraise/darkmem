import { z } from "zod"

export const cronExpressionSchema = z
  .string()
  .refine((s) => /^(\S+\s+){4,5}\S+$/.test(s.trim()), {
    message: "Cron must have 5 or 6 space-separated fields",
  })

export const editRepoSchema = z.object({
  name: z.string().min(1, "Name required"),
  path: z.string().min(1, "Path required"),
  branch: z.string().default("main"),
  sync_cron: cronExpressionSchema,
  auto_sync: z.boolean().default(true),
  enrich_symbols: z.boolean().default(true),
  generate_wiki: z.boolean().default(true),
})
export type EditRepoInput = z.infer<typeof editRepoSchema>

export const reindexSchema = z
  .object({
    full: z.boolean().default(false),
    enrich_symbols: z.boolean().default(false),
    generate_wiki: z.boolean().default(false),
  })
  .refine((d) => d.full || d.enrich_symbols || d.generate_wiki, {
    message: "Pick at least one reindex action",
  })
export type ReindexInput = z.infer<typeof reindexSchema>
