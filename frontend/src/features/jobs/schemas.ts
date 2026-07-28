import { z } from "zod"

export const cronExpressionSchema = z
  .string()
  .refine((s) => /^(\S+\s+){4,5}\S+$/.test(s.trim()), {
    message: "Cron must have 5 or 6 space-separated fields",
  })

export const jobUpdateSchema = z.object({
  key: z.string().min(1),
  cron: cronExpressionSchema,
  min_interval_seconds: z.number().int().min(0),
})
export type JobUpdate = z.infer<typeof jobUpdateSchema>
