import { useNavigate } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent } from "darkraise-ui/components/card"
import { toast } from "darkraise-ui/components/sonner"
import {
  useSetupWizardStore,
  PURPOSES,
  missingRequiredModels,
} from "@/features/setup/setupWizardStore"
import {
  useFinalizeSetup,
  type SetupRequest,
  type SetupLLM,
} from "@/hooks/api/use-setup-api"
import { ParticleBackground } from "@/components/particle-background"
import { StepPassword, isStepPasswordValid } from "./StepPassword"
import { StepLLM, isStepLLMValid } from "./StepLLM"
import { StepRepoPath, isStepRepoPathValid } from "./StepRepoPath"
import { StepFinish } from "./StepFinish"

const STEP_TITLES: Record<1 | 2 | 3 | 4, string> = {
  1: "Admin password",
  2: "Default LLM provider",
  3: "Default code repo path",
  4: "Review & finish",
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

  // Names of the required purposes still missing a model, so the disabled Next
  // button can say exactly what's blocking instead of just greying out.
  const missingModels = missingRequiredModels(llm)

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
    if (!llm.skipped && llm.api_kind) {
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
        api_kind: llm.api_kind,
        base_url: llm.base_url.trim() || null,
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
    <>
      <ParticleBackground />
      <Card className="border-border/60 bg-card/85 flex max-h-[90vh] w-full max-w-2xl flex-col shadow-2xl backdrop-blur-md">
        <CardContent className="flex flex-col gap-6 overflow-hidden p-8">
          <div className="shrink-0 space-y-1 text-center">
            <h1 className="font-mono text-2xl font-bold tracking-tight">
              darkmem
            </h1>
            <p className="text-muted-foreground text-base">Initial Setup</p>
          </div>

          <ol className="flex shrink-0 flex-wrap justify-center gap-2 text-base">
            {[1, 2, 3, 4].map((s) => (
              <li
                key={s}
                className={`rounded-md border px-3 py-1 transition-colors ${
                  s === step
                    ? "border-primary bg-primary/10 text-primary"
                    : s < step
                      ? "border-muted bg-muted/30 text-muted-foreground"
                      : "border-muted/50 text-muted-foreground"
                }`}
              >
                {s}. {STEP_TITLES[s as 1 | 2 | 3 | 4]}
              </li>
            ))}
          </ol>

          <div className="flex-1 overflow-y-auto pr-1">
            {step === 1 && <StepPassword />}
            {step === 2 && <StepLLM />}
            {step === 3 && <StepRepoPath />}
            {step === 4 && <StepFinish />}
          </div>

          <div className="border-border/60 flex shrink-0 justify-between border-t pt-4">
            <Button
              variant="ghost"
              onClick={goBack}
              disabled={step === 1 || finalize.isPending}
            >
              Back
            </Button>
            <div className="flex items-center gap-3">
              {step === 2 && !llm.skipped && missingModels.length > 0 && (
                <span className="text-muted-foreground text-base">
                  Add a model for: {missingModels.join(", ")}
                </span>
              )}
              {(step === 2 || step === 3) && (
                <Button
                  variant="outline"
                  onClick={skip}
                  disabled={finalize.isPending}
                >
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
        </CardContent>
      </Card>
    </>
  )
}
