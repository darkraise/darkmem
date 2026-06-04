// Pipeline purposes recognised by the rest of the system. Profile names
// usually contain one of these as a hyphen-separated segment (e.g.
// "openai-extraction", "zai-flash-extraction"). Anything that doesn't
// match falls into the "other" bucket.
export const KNOWN_PURPOSES = [
  "embedding",
  "extraction",
  "classification",
  "reasoning",
  "summarization",
  "reranker",
] as const
export type KnownPurpose = (typeof KNOWN_PURPOSES)[number]
const KNOWN_PURPOSE_SET = new Set<string>(KNOWN_PURPOSES)

// Legacy-null hint only: parse the profile name for a purpose keyword.
// Walk segments right-to-left so a name like "openai-embedding-large"
// routes to "embedding" (the keyword), not the trailing variant tag.
function inferPurpose(profileName: string): KnownPurpose | "other" {
  const segments = profileName.toLowerCase().split("-")
  for (let i = segments.length - 1; i >= 0; i--) {
    const segment = segments[i]
    if (segment && KNOWN_PURPOSE_SET.has(segment)) {
      return segment as KnownPurpose
    }
  }
  return "other"
}

/**
 * The purpose bucket a profile really belongs to — mirrors how the Pipeline
 * card filters its dropdown (LLMPurposeCard: stored ``purpose`` column wins;
 * a null purpose falls back to the legacy ``is_embedding`` heuristic). Keeping
 * this aligned with that filter is what makes the Profiles grouping agree with
 * the Pipeline by construction. A null purpose that isn't an embedding profile
 * maps to all non-embedding purposes in the Pipeline, so "other" is the honest
 * single bucket here; ``inferPurpose`` is only a hint for naming those rows.
 */
export function purposeOf(
  profile: { purpose?: string | null; is_embedding?: boolean },
  name: string,
): KnownPurpose | "other" {
  if (profile.purpose && KNOWN_PURPOSE_SET.has(profile.purpose)) {
    return profile.purpose as KnownPurpose
  }
  if (profile.is_embedding) return "embedding"
  return inferPurpose(name)
}
