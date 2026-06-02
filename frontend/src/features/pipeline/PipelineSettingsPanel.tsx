import { useEffect } from "react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { usePipeline, useSystemPrompts } from "@/hooks/api"
import { LLMPanel } from "./LLMPanel"
import { AssistantServicesPanel } from "./AssistantServicesPanel"
import { checkPromptExhaustiveness } from "./prompt-map"

export function PipelineSettingsPanel() {
  const { data: state, isLoading, error, refetch } = usePipeline()
  const { data: systemPrompts } = useSystemPrompts()

  useEffect(() => {
    if (systemPrompts) {
      checkPromptExhaustiveness(Object.keys(systemPrompts.defaults))
    }
  }, [systemPrompts])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-40 rounded" />
        <Skeleton className="h-96 rounded" />
      </div>
    )
  }

  if (error || !state) {
    return (
      <div
        role="alert"
        className="bg-destructive/10 border-destructive/30 rounded-lg border p-4"
      >
        <p className="text-destructive text-base">
          {(error as Error)?.message ?? "Unknown error"}
        </p>
        <Button
          variant="link"
          className="mt-2 text-base underline"
          onClick={() => refetch()}
        >
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <LLMPanel state={state} />
      <AssistantServicesPanel state={state} />
    </div>
  )
}
