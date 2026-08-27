/**
 * Which LLM purposes have a system prompt, and what it is keyed by in
 * `backend/app/services/prompt.py`.
 *
 * The two vocabularies overlap without being the same: `PROMPTS` also holds
 * keys that are not LLM purposes at all (`chat`, `cluster_naming`,
 * `agent_instructions`), and four purposes — `embedding`, `reranker`,
 * `verification`, `synthesis` — have no *editable* prompt here.
 *
 * The reason differs per purpose, and the earlier wording ("no dispatching
 * consumer that sends one") was false for three of the four by 2026-08-27:
 * embedding genuinely takes no instructions, but `reranker`,
 * `verification` and `synthesis` all send a prompt today — they are absent
 * because their prompts are deliberately NOT editable. Each is held inline
 * beside the parser that enforces its output shape (`reranker.py`,
 * `article_synthesis.py`), and `verification_judge.py`'s folds into the
 * judge identity hash, so a UI edit there would silently invalidate a
 * minted qualification record. A purpose absent from this map gets no
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
