import { useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { usePipeline, useSystemPrompts } from "@/hooks/api"
import { LLMPanel } from "@/features/pipeline/LLMPanel"
import { AssistantServicesPanel } from "@/features/pipeline/AssistantServicesPanel"
import { checkPromptExhaustiveness } from "@/features/pipeline/prompt-map"

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
        <PageHeader
          title="Pipeline"
          description="Failed to load pipeline state."
        />
        <div
          role="alert"
          className="bg-destructive/10 border-destructive/30 mt-4 rounded-lg border p-4"
        >
          <p className="text-destructive text-sm">
            {(error as Error)?.message ?? "Unknown error"}
          </p>
          <button className="mt-2 text-xs underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-6">
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
    <div className="space-y-4 p-6">
      <Skeleton className="h-10 w-40 rounded" />
      <Skeleton className="h-96 rounded" />
    </div>
  )
}
