import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { LlmApiKind } from "@/features/setup/api-kinds"

export type Purpose =
  | "embedding"
  | "extraction"
  | "classification"
  | "reasoning"
  | "summarization"
  | "reranker"

export const PURPOSES: Purpose[] = [
  "embedding",
  "extraction",
  "classification",
  "reasoning",
  "summarization",
  "reranker",
]

export const REQUIRED_PURPOSES_NON_EMBEDDING: Purpose[] = [
  "extraction",
  "classification",
  "reasoning",
]

export type DetectedRepo = {
  name: string
  subPath: string
  selected: boolean
}

export type WizardProvider = {
  name: string
  api_kind: LlmApiKind
  base_url: string
  api_key: string
}

export type PurposeDraft = {
  provider_name: string
  model: string
  reasoning: boolean
  dimensions?: number
}

type SetupWizardState = {
  step: 1 | 2 | 3 | 4
  maxStep: 1 | 2 | 3 | 4
  password: { value: string; confirm: string }
  llm: {
    skipped: boolean
    providers: WizardProvider[]
    perPurpose: Record<Purpose, PurposeDraft>
  }
  repos: {
    skipped: boolean
    basePath: string
    detected: DetectedRepo[]
  }
  setStep: (step: 1 | 2 | 3 | 4) => void
  setPassword: (value: string, confirm: string) => void
  addLlmProvider: (provider: WizardProvider) => void
  updateLlmProvider: (name: string, patch: Partial<Omit<WizardProvider, "name">>) => void
  removeLlmProvider: (name: string) => void
  setLlmPurpose: (purpose: Purpose, draft: Partial<PurposeDraft>) => void
  setLlmSkipped: (skipped: boolean) => void
  setReposBasePath: (path: string) => void
  setReposDetected: (detected: DetectedRepo[]) => void
  toggleRepoSelected: (subPath: string) => void
  renameDetectedRepo: (subPath: string, name: string) => void
  setReposSkipped: (skipped: boolean) => void
  reset: () => void
}

export type LlmDraft = SetupWizardState["llm"]

/** Required purposes still missing a provider or a model, so the wizard can
 * name exactly what's blocking. Embedding is never in this list: a fresh
 * install always resolves it against the seeded ollama-local default, so
 * leaving it unassigned here is a valid choice, not an incomplete one — the
 * same is true of summarization and reranker. */
export function missingRequiredModels(llm: LlmDraft): Purpose[] {
  if (llm.skipped) return []
  return REQUIRED_PURPOSES_NON_EMBEDDING.filter((p) => {
    const draft = llm.perPurpose[p]
    return !draft.provider_name.trim() || !draft.model.trim()
  })
}

const emptyPurposeDraft: PurposeDraft = { provider_name: "", model: "", reasoning: false }

const initial = () => ({
  step: 1 as const,
  maxStep: 1 as 1 | 2 | 3 | 4,
  password: { value: "", confirm: "" },
  llm: {
    skipped: false,
    providers: [] as WizardProvider[],
    perPurpose: {
      embedding: { ...emptyPurposeDraft },
      extraction: { ...emptyPurposeDraft },
      classification: { ...emptyPurposeDraft },
      reasoning: { ...emptyPurposeDraft },
      summarization: { ...emptyPurposeDraft },
      reranker: { ...emptyPurposeDraft },
    } as Record<Purpose, PurposeDraft>,
  },
  repos: { skipped: false, basePath: "", detected: [] as DetectedRepo[] },
})

export const useSetupWizardStore = create<SetupWizardState>()(
  persist(
    (set) => ({
      ...initial(),
      setStep: (step) =>
        set((s) => ({ step, maxStep: step > s.maxStep ? step : s.maxStep })),
      setPassword: (value, confirm) => set({ password: { value, confirm } }),
      addLlmProvider: (provider) =>
        set((s) => ({
          llm: { ...s.llm, providers: [...s.llm.providers, provider] },
        })),
      updateLlmProvider: (name, patch) =>
        set((s) => ({
          llm: {
            ...s.llm,
            providers: s.llm.providers.map((p) =>
              p.name === name ? { ...p, ...patch } : p,
            ),
          },
        })),
      removeLlmProvider: (name) =>
        set((s) => ({
          llm: {
            ...s.llm,
            providers: s.llm.providers.filter((p) => p.name !== name),
            // A purpose pointed at a provider that no longer exists must
            // not keep carrying its stale name into the finalize payload.
            perPurpose: Object.fromEntries(
              (Object.entries(s.llm.perPurpose) as [Purpose, PurposeDraft][]).map(
                ([purpose, draft]) => [
                  purpose,
                  draft.provider_name === name
                    ? { ...draft, provider_name: "" }
                    : draft,
                ],
              ),
            ) as Record<Purpose, PurposeDraft>,
          },
        })),
      setLlmPurpose: (purpose, draft) =>
        set((s) => ({
          llm: {
            ...s.llm,
            perPurpose: {
              ...s.llm.perPurpose,
              [purpose]: { ...s.llm.perPurpose[purpose], ...draft },
            },
          },
        })),
      setLlmSkipped: (skipped) => set((s) => ({ llm: { ...s.llm, skipped } })),
      setReposBasePath: (basePath) =>
        set((s) => ({ repos: { ...s.repos, basePath } })),
      setReposDetected: (detected) =>
        set((s) => ({ repos: { ...s.repos, detected } })),
      toggleRepoSelected: (subPath) =>
        set((s) => ({
          repos: {
            ...s.repos,
            detected: s.repos.detected.map((r) =>
              r.subPath === subPath ? { ...r, selected: !r.selected } : r,
            ),
          },
        })),
      renameDetectedRepo: (subPath, name) =>
        set((s) => ({
          repos: {
            ...s.repos,
            detected: s.repos.detected.map((r) =>
              r.subPath === subPath ? { ...r, name } : r,
            ),
          },
        })),
      setReposSkipped: (skipped) =>
        set((s) => ({ repos: { ...s.repos, skipped } })),
      reset: () => set(initial()),
    }),
    {
      name: "darkmem-setup-wizard",
      // Bumped from 1: the persisted `llm` shape changed incompatibly
      // (single api_kind/base_url/api_key -> a providers array). With no
      // `migrate` supplied, zustand discards a stored v1 blob rather than
      // hydrating it into a shape that no longer matches.
      version: 2,
      // Vendor API keys stay in memory only, like the password: a reload
      // keeps the providers and asks for their keys again.
      partialize: (s) => ({
        step: s.step,
        maxStep: s.maxStep,
        password: { value: "", confirm: "" },
        llm: {
          ...s.llm,
          providers: s.llm.providers.map((p) => ({ ...p, api_key: "" })),
        },
        repos: s.repos,
      }),
    },
  ),
)
