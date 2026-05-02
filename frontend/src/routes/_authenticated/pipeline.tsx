import { useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { usePipeline, useSystemPrompts } from "@/hooks/api"
import { LLMPanel } from "@/components/pipeline/LLMPanel"
import { AssistantServicesPanel } from "@/components/pipeline/AssistantServicesPanel"
import { checkPromptExhaustiveness } from "@/components/pipeline/prompt-map"

export const Route = createFileRoute("/_authenticated/pipeline")({
  component: PipelinePage,
})

function PipelinePage() {
  const { data: state, isLoading, error, refetch } = usePipeline()
  const { data: systemPrompts } = useSystemPrompts()

  useEffect(() => {
    if (systemPrompts) {
      checkPromptExhaustiveness(Object.keys(systemPrompts.defaults))
    }
  }, [systemPrompts])

  if (isLoading) return <PipelineSkeleton />
  if (error || !state) {
    return (
      <div className="p-6">
        <PageHeader title="Pipeline" description="Failed to load pipeline state." />
        <div role="alert" className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mt-4">
          <p className="text-destructive text-sm">{(error as Error)?.message ?? "Unknown error"}</p>
          <button className="text-xs underline mt-2" onClick={() => refetch()}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        title="Pipeline"
        description="Configure the LLM purposes, profiles, and prompts that power memory ingestion."
      />
      <LLMPanel state={state} />
      <AssistantServicesPanel state={state} />
    </div>
  )
}

function PipelineSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <div className="h-10 w-40 bg-muted rounded animate-pulse" />
      <div className="h-96 bg-muted rounded animate-pulse" />
    </div>
  )
}
