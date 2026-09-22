import { useNavigate } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { CardContent } from "darkraise-ui/components/card"
import { GlassPanel } from "@/components/glass-panel"
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
    if (!llm.skipped && llm.providers.length > 0) {
      const purposes: SetupLLM["purposes"] = {}
      for (const p of PURPOSES) {
        const draft = llm.perPurpose[p]
        if (!draft.provider_name.trim() || !draft.model.trim()) continue
        purposes[p] = {
          provider_name: draft.provider_name,
          model: draft.model.trim(),
          reasoning: draft.reasoning,
          dimensions: draft.dimensions ?? null,
        }
      }
      body.llm = {
        providers: llm.providers.map((p) => ({
          name: p.name,
          api_kind: p.api_kind,
          base_url: p.base_url,
          api_key: p.api_key || null,
        })),
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
    <GlassPanel className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden">
      <CardContent className="flex min-h-0 flex-col gap-5 overflow-hidden p-4 sm:p-8">
        <div className="shrink-0 space-y-1 text-center">
          <h1 className="font-mono text-2xl font-bold tracking-tight">
            darkmem
          </h1>
          <p className="text-muted-foreground text-sm">Initial Setup</p>
        </div>

        <ol className="flex shrink-0 flex-wrap justify-center gap-2 text-sm">
          {[1, 2, 3, 4].map((s) => (
            <li
              key={s}
              aria-current={s === step ? "step" : undefined}
              className={`${s === step ? "block" : "hidden sm:block"} rounded-md border px-3 py-1 transition-colors ${
                s === step
                  ? "border-primary bg-primary/10 text-primary-text"
                  : s < step
                    ? "border-muted bg-muted/30 text-muted-foreground"
                    : "border-muted/50 text-muted-foreground"
              }`}
            >
              <span className="sm:hidden">Step {s} of 4 · </span>
              <span className="hidden sm:inline">{s}. </span>
              {STEP_TITLES[s as 1 | 2 | 3 | 4]}
            </li>
          ))}
        </ol>

        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          {step === 1 && <StepPassword />}
          {step === 2 && <StepLLM />}
          {step === 3 && <StepRepoPath />}
          {step === 4 && <StepFinish />}
        </div>

        <div className="border-border/60 flex shrink-0 flex-wrap justify-between gap-2 border-t pt-4">
          <Button
            variant="ghost"
            onClick={goBack}
            disabled={step === 1 || finalize.isPending}
          >
            Back
          </Button>
          <div className="flex flex-wrap items-center gap-2">
            {step === 2 && !llm.skipped && missingModels.length > 0 && (
              <span className="text-muted-foreground text-sm">
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
    </GlassPanel>
  )
}
