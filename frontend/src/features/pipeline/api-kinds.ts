// Authoritative list of api_kind values exposed in the UI dropdowns.
// Mirrors LLMApiKind in backend/app/config.py — keep in sync. Today every
// kind except "ollama" dispatches through the OpenAI-compatible path; the
// vendor-specific entries are placeholders for future native adapters in
// LLMOrchestrator. The "note" string is shown to the user so they know
// the difference between native and compat-routed kinds.

export type LlmApiKind =
  | "openai"
  | "ollama"
  | "anthropic"
  | "google"
  | "deepseek"
  | "zai"

export interface ApiKindOption {
  value: LlmApiKind
  label: string
  note?: string
}

export const API_KIND_OPTIONS: ApiKindOption[] = [
  { value: "openai", label: "OpenAI-compatible (/v1)" },
  { value: "ollama", label: "Ollama native (/api)" },
  { value: "anthropic", label: "Anthropic", note: "via OpenAI compat" },
  { value: "google", label: "Google Gemini", note: "via OpenAI compat" },
  { value: "deepseek", label: "DeepSeek", note: "via OpenAI compat" },
  { value: "zai", label: "z.ai (Zhipu / GLM)", note: "via OpenAI compat" },
]

export function findApiKind(kind: string | undefined): ApiKindOption | undefined {
  return API_KIND_OPTIONS.find((o) => o.value === kind)
}

export function apiKindLabel(kind: string | undefined): string {
  return findApiKind(kind)?.label ?? kind ?? ""
}

// Mirrors ``supports_embedding`` in backend/app/services/llm_quirks.py. These
// two vendors expose chat completions only, so an embed call 404s on every
// request. Derived from api_kind directly: the provider table that used to
// carry a supports_embedding flag is gone, and the backend's runtime
// assertion is keyed the same way.
const NO_EMBEDDING_KINDS: readonly string[] = ["anthropic", "deepseek"]

export function apiKindSupportsEmbedding(kind: string | undefined): boolean {
  return !NO_EMBEDDING_KINDS.includes(kind ?? "")
}

export function embeddingKindWarning(kind: string | undefined): string | null {
  if (apiKindSupportsEmbedding(kind)) return null
  return `${apiKindLabel(kind)} exposes no embeddings endpoint — an embed call against it fails on every request.`
}
