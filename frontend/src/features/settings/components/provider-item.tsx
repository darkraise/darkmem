import { Card, CardContent } from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"
import { Pencil, Plug, ShieldCheck, Trash2 } from "lucide-react"
import { HelpTip } from "@/components/darkmem"
import { apiKindLabel } from "@/features/setup/api-kinds"
import type { LlmLayout } from "@/features/settings/use-llm-layout"
import {
  useDeleteLlmProvider,
  useProbeProviderModels,
  type LlmProvider,
} from "@/hooks/api/use-llm-providers-api"

function ProbeResult({
  result,
}: {
  result: { models: string[]; error: string | null } | undefined
}) {
  if (!result) return null
  if (result.error) {
    return <span className="text-destructive text-sm">{result.error}</span>
  }
  return (
    <span className="text-muted-foreground text-sm">
      {result.models.length} model{result.models.length === 1 ? "" : "s"}
    </span>
  )
}

/**
 * One provider, read-only, in either layout. Editing lives in the dialog the
 * `onEdit` callback opens.
 *
 * Grid and list are one component with a layout prop rather than two
 * components: they show the same fields and offer the same actions, differing
 * only in arrangement, so a split would just be two places for the frozen-field
 * badge or the delete guard to drift apart.
 */
export function ProviderItem({
  provider,
  layout,
  onEdit,
}: {
  provider: LlmProvider
  layout: LlmLayout
  onEdit: () => void
}) {
  const del = useDeleteLlmProvider()
  const probe = useProbeProviderModels()

  const frozen = provider.serves_verification
  const canDelete = provider.used_by.length === 0
  // The kind module owns this mapping; a card says "Ollama native (/api)"
  // rather than "ollama" without a second copy of the labels living here.
  const kindOption = apiKindLabel(provider.api_kind)

  const identity = (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <Plug aria-hidden className="text-primary h-4 w-4 shrink-0" />
      <span className="font-mono text-sm font-semibold">{provider.name}</span>
      {frozen && (
        <>
          <ShieldCheck
            aria-hidden
            className="text-muted-foreground h-3.5 w-3.5"
          />
          <HelpTip label={`About ${provider.name}'s frozen fields`}>
            This provider serves the verification judge. base_url and api_kind
            are the judge's qualification identity, so the backend refuses to
            change them. The key is still rotatable — that credential is owed
            rotation regardless.
          </HelpTip>
        </>
      )}
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex">
            <Badge variant="secondary" className="font-mono">
              {provider.used_by.length}
            </Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent>
          {provider.used_by.length === 0
            ? "not referenced by any purpose"
            : `used by: ${provider.used_by.join(", ")}`}
        </TooltipContent>
      </Tooltip>
    </div>
  )

  const connection = (
    <div
      className={cn(
        "text-muted-foreground min-w-0 font-mono text-xs",
        layout === "grid" ? "flex flex-col gap-0.5" : "flex flex-wrap gap-x-3",
      )}
    >
      <span>{kindOption}</span>
      <span className="truncate">{provider.base_url}</span>
      <span>{provider.api_key ? "key set" : "no key"}</span>
    </div>
  )

  const actions = (
    <div className="flex flex-wrap items-center gap-1.5">
      <Button
        variant="ghost"
        aria-label={`Test connection ${provider.name}`}
        disabled={probe.isPending}
        onClick={() => probe.mutate({ name: provider.name })}
      >
        {probe.isPending ? "Testing…" : "Test connection"}
      </Button>
      <ProbeResult result={probe.data} />
      <Button
        variant="outline"
        className="border-primary/60 text-primary ml-auto"
        aria-label={`Edit ${provider.name}`}
        onClick={onEdit}
      >
        <Pencil aria-hidden className="mr-1 h-3.5 w-3.5" />
        Edit
      </Button>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex">
            <Button
              size="icon"
              variant="ghost"
              className="text-destructive"
              aria-label={`Delete ${provider.name}`}
              disabled={!canDelete || del.isPending}
              onClick={() => del.mutate(provider.name)}
            >
              <Trash2 aria-hidden className="h-4 w-4" />
            </Button>
          </span>
        </TooltipTrigger>
        <TooltipContent>
          {canDelete
            ? "delete this provider"
            : `in use by: ${provider.used_by.join(", ")}`}
        </TooltipContent>
      </Tooltip>
    </div>
  )

  const failure = del.isError && (
    <p className="text-destructive text-sm">{del.error.message}</p>
  )

  if (layout === "list") {
    return (
      <div className="border-inset bg-card flex flex-col gap-2 rounded-lg border px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {identity}
          {connection}
        </div>
        {actions}
        {failure}
      </div>
    )
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-2.5 pt-4">
        {identity}
        {connection}
        {actions}
        {failure}
      </CardContent>
    </Card>
  )
}

