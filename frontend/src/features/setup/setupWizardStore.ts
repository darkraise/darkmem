import { create } from "zustand"
import { persist } from "zustand/middleware"

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

export type PurposeDraft = {
  model: string
  reasoning: boolean
  dimensions?: number
}

type SetupWizardState = {
  step: 1 | 2 | 3 | 4
  password: { value: string; confirm: string }
  llm: {
    skipped: boolean
    api_kind: string
    base_url: string
    api_key: string
    supports_embedding: boolean
    models: string[]
    perPurpose: Record<Purpose, PurposeDraft>
  }
  repos: {
    skipped: boolean
    basePath: string
    detected: DetectedRepo[]
  }
  setStep: (step: 1 | 2 | 3 | 4) => void
  setPassword: (value: string, confirm: string) => void
  setLlmField: <K extends keyof SetupWizardState["llm"]>(
    key: K,
    value: SetupWizardState["llm"][K],
  ) => void
  setLlmPurpose: (purpose: Purpose, draft: Partial<PurposeDraft>) => void
  setLlmSkipped: (skipped: boolean) => void
  setReposBasePath: (path: string) => void
  setReposDetected: (detected: DetectedRepo[]) => void
  toggleRepoSelected: (subPath: string) => void
  renameDetectedRepo: (subPath: string, name: string) => void
  setReposSkipped: (skipped: boolean) => void
  reset: () => void
}

const emptyPurposeDraft: PurposeDraft = { model: "", reasoning: false }

const initial = () => ({
  step: 1 as 1,
  password: { value: "", confirm: "" },
  llm: {
    skipped: false,
    api_kind: "openai",
    base_url: "https://api.openai.com/v1",
    api_key: "",
    supports_embedding: true,
    models: [] as string[],
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
      setStep: (step) => set({ step }),
      setPassword: (value, confirm) => set({ password: { value, confirm } }),
      setLlmField: (key, value) =>
        set((s) => ({ llm: { ...s.llm, [key]: value } })),
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
      version: 1,
      partialize: (s) => ({
        step: s.step,
        password: { value: "", confirm: "" },
        llm: s.llm,
        repos: s.repos,
      }),
    },
  ),
)
