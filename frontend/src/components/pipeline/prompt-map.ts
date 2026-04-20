export type LLMPurpose =
  | "embedding"
  | "extraction"
  | "classification"
  | "reasoning"
  | "summarization"
  | "reranker"

/** Which stage-bound prompts belong to each LLM purpose card. */
export const PROMPT_PURPOSE_MAP: Record<LLMPurpose, string[]> = {
  embedding: [],
  extraction: ["extraction", "extraction_entities", "extraction_relationships"],
  classification: ["classification"],
  reasoning: ["reasoning"],
  summarization: ["summarization"],
  reranker: [],
}

/** Prompts not owned by a single purpose; rendered on Settings -> Assistant Prompts. */
export const ORPHAN_PROMPTS = ["chat", "cluster_naming", "agent_instructions"] as const

export const EXPECTED_PROMPT_KEYS = new Set<string>([
  ...Object.values(PROMPT_PURPOSE_MAP).flat(),
  ...ORPHAN_PROMPTS,
])

/** Log a warning if `serverKeys` doesn't match `EXPECTED_PROMPT_KEYS`. */
export function checkPromptExhaustiveness(serverKeys: Iterable<string>): void {
  const server = new Set(serverKeys)
  const missing = [...EXPECTED_PROMPT_KEYS].filter((k) => !server.has(k))
  const extra = [...server].filter((k) => !EXPECTED_PROMPT_KEYS.has(k))
  if (missing.length || extra.length) {
    // eslint-disable-next-line no-console
    console.warn(
      "[prompt-map] mismatch with server system-prompts:",
      { missing, extra },
    )
  }
}
