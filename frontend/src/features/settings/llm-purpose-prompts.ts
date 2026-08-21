/**
 * Which LLM purposes have a system prompt, and what it is keyed by in
 * `backend/app/services/prompt.py`.
 *
 * The two vocabularies overlap without being the same: `PROMPTS` also holds
 * keys that are not LLM purposes at all (`chat`, `cluster_naming`,
 * `agent_instructions`), and four purposes — `embedding`, `reranker`,
 * `verification`, `synthesis` — have no prompt for the same reason each is
 * unusual: embedding takes no instructions, and the other three have no
 * dispatching consumer that sends one. A purpose absent from this map gets no
 * prompt affordance rather than a button that opens an empty editor.
 *
 * The names happen to match today, so this reads as an identity map. It is
 * written out anyway: the mapping is a fact about two independently-owned
 * vocabularies, and deriving it from the purpose name would silently invent a
 * key the backend does not serve the first time either side is renamed.
 */
export const PURPOSE_PROMPT_KEYS: Readonly<Record<string, string>> = {
  extraction: "extraction",
  classification: "classification",
  reasoning: "reasoning",
  summarization: "summarization",
}

export function promptKeyForPurpose(purpose: string): string | undefined {
  return PURPOSE_PROMPT_KEYS[purpose]
}
