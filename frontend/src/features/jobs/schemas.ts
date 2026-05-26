import { z } from "zod"
import { cronExpressionSchema } from "@/features/repos/schemas"

export const jobUpdateSchema = z.object({
  key: z.string().min(1),
  cron: cronExpressionSchema,
  min_interval_seconds: z.number().int().min(0),
})
export type JobUpdate = z.infer<typeof jobUpdateSchema>

export { cronExpressionSchema }
