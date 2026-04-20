import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { useNavigate } from "@tanstack/react-router"
import { toast } from "sonner"
import { useReembedAll, type PipelineState } from "@/hooks/api"
import { LLMPurposeCard } from "./LLMPurposeCard"
import type { LLMPurpose } from "./prompt-map"

const ORDER: LLMPurpose[] = [
  "embedding", "extraction", "classification", "reasoning", "summarization", "reranker",
]

interface Props {
  state: PipelineState
}

export function LLMPanel({ state }: Props) {
  const navigate = useNavigate()
  const reembedAll = useReembedAll()
  const [obsolete, setObsolete] = useState<
    { memories: number; code_chunks: number; entities: number } | null
  >(null)

  const llmStages = Object.values(state.stages).filter((v) => v === "llm").length
  const status = llmStages === 3 ? "active" : llmStages === 0 ? "inactive" : "mixed"

  const startReembed = () => {
    reembedAll.mutate(undefined, {
      onSuccess: () => {
        toast.info("Re-embed started — progress on /reindex")
        setObsolete(null)
        navigate({ to: "/reindex" })
      },
      onError: (err) => toast.error(`Re-embed failed: ${(err as Error).message}`),
    })
  }

  return (
    <Card className={status === "inactive" ? "opacity-60" : ""}>
      <CardHeader className="pb-2 flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-sm">LLM stack</CardTitle>
          <p className="text-muted-foreground text-xs">Per-purpose provider + model + prompts</p>
        </div>
        <Badge variant={status === "active" ? "default" : "outline"} className="text-[10px]">
          {status} · {llmStages}/3
        </Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        {ORDER.map((p) => (
          <LLMPurposeCard
            key={p}
            purpose={p}
            config={state.llm[p]}
            prompts={state.prompts}
            onObsoleteDetected={setObsolete}
          />
        ))}
      </CardContent>

      <Dialog open={obsolete !== null} onOpenChange={(v) => !v && setObsolete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Embedding model changed</DialogTitle>
          </DialogHeader>
          {obsolete && (
            <div className="text-sm space-y-3 py-2">
              <p>The embedding changed. Existing vectors are now from the old model:</p>
              <ul className="text-sm space-y-1 pl-4 list-disc">
                {obsolete.memories > 0 && <li>{obsolete.memories} memories</li>}
                {obsolete.entities > 0 && <li>{obsolete.entities} entities</li>}
                {obsolete.code_chunks > 0 && <li>{obsolete.code_chunks} code chunks</li>}
              </ul>
              <p className="text-[11px] text-muted-foreground">
                Re-embedding recomputes vectors only; extraction and classification stay as-is.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setObsolete(null)}>Later</Button>
            <Button onClick={startReembed} disabled={reembedAll.isPending}>
              {reembedAll.isPending ? "Starting…" : "Re-embed now"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
