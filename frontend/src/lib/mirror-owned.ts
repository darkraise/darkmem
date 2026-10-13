/** The uri prefixes of registers and plans, which the dr-forge mirror owns
 *  through content puts. The server refuses block edits on them, so the SPA
 *  offers no edit mode there (spec 2026-10-13 §2.5). */
export const MIRROR_OWNED_PREFIXES = [
  "superpowers/registers/",
  "superpowers/plans/",
]

export function isMirrorOwned(uri: string | null | undefined): boolean {
  return (
    Boolean(uri) &&
    MIRROR_OWNED_PREFIXES.some((prefix) => uri!.startsWith(prefix))
  )
}
