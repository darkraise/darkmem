import { describe, it, expect } from "vitest"

import { missingRequiredModels, type LlmDraft, type WizardProvider } from "../setupWizardStore"

const provider: WizardProvider = {
  name: "user-openai",
  api_kind: "openai",
  base_url: "https://api.openai.com/v1",
  api_key: "sk-x",
}

function draft(over: Partial<LlmDraft> = {}): LlmDraft {
  return {
    skipped: false,
    providers: [provider],
    perPurpose: {
      embedding: { provider_name: "", model: "", reasoning: false },
      extraction: { provider_name: "", model: "", reasoning: false },
      classification: { provider_name: "", model: "", reasoning: false },
      reasoning: { provider_name: "", model: "", reasoning: false },
      summarization: { provider_name: "", model: "", reasoning: false },
      reranker: { provider_name: "", model: "", reasoning: false },
    },
    ...over,
  }
}

describe("missingRequiredModels", () => {
  it("lists every required purpose when none has a provider or model", () => {
    expect(missingRequiredModels(draft())).toEqual([
      "extraction",
      "classification",
      "reasoning",
    ])
  })

  it("never lists embedding — it always falls back to the seeded default", () => {
    expect(missingRequiredModels(draft())).not.toContain("embedding")
    const d = draft()
    d.perPurpose.embedding.provider_name = "user-openai"
    expect(missingRequiredModels(d)).not.toContain("embedding")
  })

  it("keeps a purpose missing when a provider is picked but no model is", () => {
    const d = draft()
    d.perPurpose.extraction.provider_name = "user-openai"
    expect(missingRequiredModels(d)).toContain("extraction")
  })

  it("keeps a purpose missing when a model is typed but no provider is picked", () => {
    const d = draft()
    d.perPurpose.extraction.model = "gpt-4o-mini"
    expect(missingRequiredModels(d)).toContain("extraction")
  })

  it("omits a purpose once both its provider and model are filled", () => {
    const d = draft()
    d.perPurpose.extraction.provider_name = "user-openai"
    d.perPurpose.extraction.model = "gpt-4o-mini"
    expect(missingRequiredModels(d)).not.toContain("extraction")
  })

  it("returns empty when the LLM step is skipped", () => {
    expect(missingRequiredModels(draft({ skipped: true }))).toEqual([])
  })
})
