import { z } from "zod"

// NB: no sync_cron here — repo sync scheduling is governed by the unified
// JobRegistry (the repo_sync job on the Jobs page), not the repo update path.
export const editRepoSchema = z.object({
  name: z.string().min(1, "Name required"),
  path: z.string().min(1, "Path required"),
  branch: z.string().default("main"),
  auto_sync: z.boolean().default(true),
  // An account id, or the NO_ACCOUNT / CUSTOM_TOKEN sentinels the picker uses.
  account: z.string().default("__none__"),
  // Only read when `account` is the custom-token sentinel.
  auth_token: z.string().default(""),
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
