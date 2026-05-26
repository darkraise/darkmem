import type { z } from "zod"

export function schemaResolver<T>(schema: z.ZodType<T>) {
  return ({ value }: { value: T }): string | undefined => {
    const result = schema.safeParse(value)
    if (result.success) return undefined
    const firstIssue = result.error.issues[0]
    return firstIssue ? firstIssue.message : "Invalid input"
  }
}
