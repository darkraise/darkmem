/**
 * Name of the first DIRTY row that fails `isInvalid`, or null.
 *
 * The LLM Providers/Profiles panels submit the full merged map (the PUT
 * replaces it), but validation must only gate on rows the user actually
 * edited. Validating every row let a pre-existing invalid row the user never
 * touched block saving an unrelated edit, with an error naming a row they
 * weren't looking at.
 */
export function firstInvalidDirty<T>(
  merged: Record<string, T | undefined>,
  dirtyNames: Set<string>,
  isInvalid: (row: T) => boolean,
): string | null {
  for (const name of Object.keys(merged)) {
    const row = merged[name]
    if (!row) continue
    if (dirtyNames.has(name) && isInvalid(row)) return name
  }
  return null
}
