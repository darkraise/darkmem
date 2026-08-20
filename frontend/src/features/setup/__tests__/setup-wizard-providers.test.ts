import { beforeEach, describe, expect, it } from "vitest"
import { useSetupWizardStore, type WizardProvider } from "../setupWizardStore"

const provider: WizardProvider = {
  name: "user-openai",
  api_kind: "openai",
  base_url: "https://api.openai.com/v1",
  api_key: "sk-x",
}

beforeEach(() => {
  useSetupWizardStore.getState().reset()
})

describe("setupWizardStore provider actions", () => {
  it("adds a provider to the list", () => {
    useSetupWizardStore.getState().addLlmProvider(provider)
    expect(useSetupWizardStore.getState().llm.providers).toEqual([provider])
  })

  it("updates a provider's fields without touching its name", () => {
    useSetupWizardStore.getState().addLlmProvider(provider)
    useSetupWizardStore.getState().updateLlmProvider("user-openai", { api_key: "sk-new" })
    const stored = useSetupWizardStore.getState().llm.providers[0]!
    expect(stored.name).toBe("user-openai")
    expect(stored.api_key).toBe("sk-new")
  })

  it("removing a provider clears any purpose still pointing at it", () => {
    const { addLlmProvider, setLlmPurpose, removeLlmProvider } = useSetupWizardStore.getState()
    addLlmProvider(provider)
    setLlmPurpose("extraction", { provider_name: "user-openai", model: "gpt-4o-mini" })
    expect(
      useSetupWizardStore.getState().llm.perPurpose.extraction.provider_name,
    ).toBe("user-openai")

    removeLlmProvider("user-openai")

    const state = useSetupWizardStore.getState()
    expect(state.llm.providers).toEqual([])
    // A dangling provider_name would pass SetupWizard's buildRequest filter
    // (non-empty provider_name + non-empty model) unchanged and reach the
    // backend naming a provider row that no longer exists — a foreign-key
    // failure at finalize time, well after the wizard looked complete.
    expect(state.llm.perPurpose.extraction.provider_name).toBe("")
    // Only the dangling reference is cleared; the typed model stays put so
    // the user doesn't lose their work if they pick a new provider.
    expect(state.llm.perPurpose.extraction.model).toBe("gpt-4o-mini")
  })

  it("removing one provider leaves another purpose's assignment untouched", () => {
    const other: WizardProvider = { ...provider, name: "user-deepseek", api_kind: "deepseek" }
    const { addLlmProvider, setLlmPurpose, removeLlmProvider } = useSetupWizardStore.getState()
    addLlmProvider(provider)
    addLlmProvider(other)
    setLlmPurpose("extraction", { provider_name: "user-openai", model: "gpt-4o-mini" })
    setLlmPurpose("classification", { provider_name: "user-deepseek", model: "deepseek-chat" })

    removeLlmProvider("user-openai")

    const state = useSetupWizardStore.getState()
    expect(state.llm.perPurpose.extraction.provider_name).toBe("")
    expect(state.llm.perPurpose.classification.provider_name).toBe("user-deepseek")
  })
})
