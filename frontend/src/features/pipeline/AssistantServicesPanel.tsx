import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { type PipelineState } from "@/hooks/api"
import { LLMPurposeCard } from "./LLMPurposeCard"
import type { LLMPurpose } from "./prompt-map"

const ORDER: LLMPurpose[] = ["reasoning", "summarization", "reranker"]

interface Props {
  state: PipelineState
}

export function AssistantServicesPanel({ state }: Props) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Assistant services</CardTitle>
        <p className="text-muted-foreground text-xs">
          LLM purposes used by chat, code enrichment, wiki generation, and reranking.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {ORDER.map((p) => (
          <LLMPurposeCard
            key={p}
            purpose={p}
            config={state.llm[p]}
            prompts={state.prompts}
          />
        ))}
      </CardContent>
    </Card>
  )
}
