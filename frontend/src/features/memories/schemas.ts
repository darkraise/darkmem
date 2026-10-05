import { z } from "zod"

import { MEMORY_TYPES } from "@/lib/taxonomy"

export const createMemorySchema = z.object({
  content: z
    .string()
    // Spaces alone are not content: they stored a blank row (the Edit dialog
    // already refused them).
    .refine((value) => value.trim().length > 0, "Content required")
    .refine((value) => value.length <= 20_000, "Content too long"),
  project: z.string().default("default"),
  memory_type: z.enum(MEMORY_TYPES),
  tags: z.array(z.string().min(1)).max(20, "Up to 20 tags"),
})
export type CreateMemoryInput = z.infer<typeof createMemorySchema>

export const memoryFilterSchema = z.object({
  query: z.string().optional(),
  sources: z.array(z.string()).optional(),
  types: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  technologies: z.array(z.string()).optional(),
  offset: z.number().int().min(0).default(0),
  limit: z.number().int().min(1).max(500).default(50),
})
export type MemoryFilter = z.infer<typeof memoryFilterSchema>
