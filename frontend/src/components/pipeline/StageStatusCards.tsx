import { Badge } from "darkraise-ui/components/badge"
import {
  useMLMetrics,
  useMLModelsHealth,
  type MLHeadSource,
  type PipelineState,
} from "@/hooks/api"

interface Props {
  stages: PipelineState["stages"]
  active: boolean
}

type StageKey = keyof PipelineState["stages"]

// Each pipeline stage maps to one representative ML head whose source is
// shown on the card. Extraction uses three heads internally (span, typer,
// relation); `span` stands in for the group since it's the first to load.
const STAGE_TO_HEAD: Record<StageKey, "span" | "classifier" | "retriever"> = {
  extraction: "span",
  classification: "classifier",
  retrieval: "retriever",
}

const STAGE_TO_GROUP: Record<StageKey, "extraction" | "classification" | "retriever"> = {
  extraction: "extraction",
  classification: "classification",
  retrieval: "retriever",
}

const STAGE_LABELS: Record<StageKey, string> = {
  extraction: "Extraction",
  classification: "Classification",
  retrieval: "Retrieval",
}

export function StageStatusCards({ stages, active }: Props) {
  const { data: metrics } = useMLMetrics(active)
  const { data: health } = useMLModelsHealth(active)

  return (
    <div className="border-t border-border pt-3 mt-2 space-y-2">
      <div className="text-[10px] text-muted-foreground">Pipeline stages</div>
      <div className="grid grid-cols-1 gap-2">
        {(Object.keys(STAGE_LABELS) as StageKey[]).map((stage) => {
          const routedToMl = stages[stage] === "ml"
          const group = STAGE_TO_GROUP[stage]
          const loaded = metrics?.groups?.[group]?.loaded ?? false
          const source = health?.sources?.[STAGE_TO_HEAD[stage]]
          return (
            <StageCard
              key={stage}
              label={STAGE_LABELS[stage]}
              routedToMl={routedToMl}
              loaded={loaded}
              source={source}
            />
          )
        })}
      </div>
    </div>
  )
}

function StageCard({
  label, routedToMl, loaded, source,
}: {
  label: string
  routedToMl: boolean
  loaded: boolean
  source: MLHeadSource | undefined
}) {
  const modelLabel = sourceLabel(source, routedToMl, loaded)
  return (
    <div className="bg-background rounded-md px-3 py-2 flex items-center justify-between">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${routedToMl ? (loaded ? "bg-emerald-500" : "bg-amber-500") : "bg-muted-foreground/40"}`} />
        <div className="min-w-0">
          <div className="text-xs font-medium truncate">{label}</div>
          <div className="text-[10px] text-muted-foreground font-mono truncate">{modelLabel}</div>
        </div>
      </div>
      <Badge variant={routedToMl ? "default" : "outline"} className="text-[9px] shrink-0">
        {routedToMl ? (loaded ? "loaded" : "on demand") : "overridden by LLM"}
      </Badge>
    </div>
  )
}

function sourceLabel(
  source: MLHeadSource | undefined,
  routedToMl: boolean,
  loaded: boolean,
): string {
  if (!routedToMl) return "LLM handles this stage"
  if (!source || !source.location) return loaded ? "—" : "lazy-load on first request"
  const basename = source.location.split(/[\\/]/).pop() || source.location
  const rev = source.revision && source.revision !== "local" ? `@${source.revision.slice(0, 7)}` : ""
  return `${basename}${rev}`
}
