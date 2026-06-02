import { describe, it, expect } from "vitest"

import { missingRequiredModels, type LlmDraft } from "../setupWizardStore"

function draft(over: Partial<LlmDraft> = {}): LlmDraft {
  return {
    skipped: false,
    api_kind: "openai",
    base_url: "x",
    api_key: "",
    supports_embedding: true,
    models: [],
    perPurpose: {
      embedding: { model: "", reasoning: false },
      extraction: { model: "", reasoning: false },
      classification: { model: "", reasoning: false },
      reasoning: { model: "", reasoning: false },
      summarization: { model: "", reasoning: false },
      reranker: { model: "", reasoning: false },
    },
    ...over,
  }
}

describe("missingRequiredModels", () => {
  it("lists every required purpose when all models are empty", () => {
    expect(missingRequiredModels(draft())).toEqual([
      "embedding",
      "extraction",
      "classification",
      "reasoning",
    ])
  })

  it("omits embedding when the provider has no embeddings", () => {
    expect(missingRequiredModels(draft({ supports_embedding: false }))).not.toContain(
      "embedding",
    )
  })

  it("omits a purpose once its model is filled", () => {
    const d = draft()
    d.perPurpose.extraction.model = "gpt-x"
    expect(missingRequiredModels(d)).not.toContain("extraction")
  })

  it("returns empty when the LLM step is skipped", () => {
    expect(missingRequiredModels(draft({ skipped: true }))).toEqual([])
  })
})
