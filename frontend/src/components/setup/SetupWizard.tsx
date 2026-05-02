import { useNavigate } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent } from "darkraise-ui/components/card"
import { toast } from "sonner"
import { useSetupWizardStore, PURPOSES } from "@/features/setup/setupWizardStore"
import { useFinalizeSetup, type SetupRequest, type SetupLLM } from "@/hooks/api/use-setup-api"
import { StepPassword, isStepPasswordValid } from "./StepPassword"
import { StepLLM, isStepLLMValid } from "./StepLLM"
import { StepRepoPath, isStepRepoPathValid } from "./StepRepoPath"
import { StepFinish } from "./StepFinish"

const STEP_TITLES: Record<1 | 2 | 3 | 4, string> = {
  1: "Admin password",
  2: "Default LLM provider",
  3: "Default code repo path",
  4: "Finish setup",
}

export function SetupWizard() {
  const navigate = useNavigate()
  const step = useSetupWizardStore((s) => s.step)
  const setStep = useSetupWizardStore((s) => s.setStep)
  const setLlmSkipped = useSetupWizardStore((s) => s.setLlmSkipped)
  const setReposSkipped = useSetupWizardStore((s) => s.setReposSkipped)
  const password = useSetupWizardStore((s) => s.password)
  const llm = useSetupWizardStore((s) => s.llm)
  const repos = useSetupWizardStore((s) => s.repos)
  const reset = useSetupWizardStore((s) => s.reset)
  const finalize = useFinalizeSetup()

  const stepValid =
    step === 1
      ? isStepPasswordValid(password)
      : step === 2
        ? isStepLLMValid(llm)
        : step === 3
          ? isStepRepoPathValid(repos)
          : true

  const goNext = () => {
    if (step === 1 && !isStepPasswordValid(password)) return
    if (step === 2) setLlmSkipped(false)
    if (step === 3) setReposSkipped(false)
    if (step < 4) setStep((step + 1) as 1 | 2 | 3 | 4)
  }
  const goBack = () => {
    if (step > 1) setStep((step - 1) as 1 | 2 | 3 | 4)
  }
  const skip = () => {
    if (step === 2) {
      setLlmSkipped(true)
      setStep(3)
    } else if (step === 3) {
      setReposSkipped(true)
      setStep(4)
    }
  }

  const buildRequest = (): SetupRequest => {
    const body: SetupRequest = { password: password.value }
    if (!llm.skipped && llm.provider_name) {
      const purposes: SetupLLM["purposes"] = {}
      for (const p of PURPOSES) {
        if (p === "embedding" && !llm.supports_embedding) continue
        const draft = llm.perPurpose[p]
        if (!draft.model.trim()) continue
        purposes[p] = {
          model: draft.model.trim(),
          reasoning: draft.reasoning,
          dimensions: draft.dimensions ?? null,
        }
      }
      body.llm = {
        provider_name: llm.provider_name.trim(),
        api_kind: llm.api_kind,
        base_url: llm.base_url.trim(),
        api_key: llm.api_key || null,
        supports_embedding: llm.supports_embedding,
        purposes,
      }
    }
    if (!repos.skipped && repos.basePath) {
      body.repos = {
        base_path: repos.basePath,
        repos: repos.detected
          .filter((r) => r.selected)
          .map((r) => ({ name: r.name.trim(), sub_path: r.subPath })),
      }
    }
    return body
  }

  const handleFinish = async () => {
    try {
      const result = await finalize.mutateAsync(buildRequest())
      if (!result.llm.ok && result.llm.message) {
        toast.warning(`LLM setup partial: ${result.llm.message}`)
      }
      for (const f of result.repos_failed) {
        toast.warning(`Repo "${f.name}" not added: ${f.error}`)
      }
      reset()
      navigate({ to: "/" })
    } catch (e) {
      toast.error(`Setup failed: ${(e as Error).message}`)
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-4">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold font-mono">darkmem</h1>
        <p className="text-sm text-muted-foreground">{STEP_TITLES[step]}</p>
      </div>
      <ol className="flex justify-center gap-2 text-xs">
        {[1, 2, 3, 4].map((s) => (
          <li
            key={s}
            className={`px-3 py-1 rounded-md border ${
              s === step
                ? "border-primary text-primary"
                : s < step
                  ? "border-muted text-muted-foreground line-through"
                  : "border-muted text-muted-foreground"
            }`}
          >
            {s}. {STEP_TITLES[s as 1 | 2 | 3 | 4]}
          </li>
        ))}
      </ol>

      <Card>
        <CardContent className="pt-6">
          {step === 1 && <StepPassword />}
          {step === 2 && <StepLLM />}
          {step === 3 && <StepRepoPath />}
          {step === 4 && <StepFinish />}
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button variant="ghost" onClick={goBack} disabled={step === 1 || finalize.isPending}>
          Back
        </Button>
        <div className="flex gap-2">
          {(step === 2 || step === 3) && (
            <Button variant="outline" onClick={skip}>
              Skip
            </Button>
          )}
          {step < 4 ? (
            <Button onClick={goNext} disabled={!stepValid}>
              Next
            </Button>
          ) : (
            <Button onClick={handleFinish} disabled={finalize.isPending}>
              {finalize.isPending ? "Finishing..." : "Finish"}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
