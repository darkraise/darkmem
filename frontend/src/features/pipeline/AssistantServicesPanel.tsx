import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
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
      <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
        <CardTitle className="text-lg uppercase tracking-wide">
          Assistant services
        </CardTitle>
        <CardDescription>
          LLM purposes used by chat, code enrichment, wiki generation, and
          reranking.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 pt-4">
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
