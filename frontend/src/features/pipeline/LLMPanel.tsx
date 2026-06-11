import { useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { toast } from "darkraise-ui/components/sonner"
import { useReembedAll, type PipelineState } from "@/hooks/api"
import { LLMPurposeCard } from "./LLMPurposeCard"
import type { LLMPurpose } from "./prompt-map"

// Purposes wired into the ingestion pipeline. reasoning/summarization/reranker
// live on the separate Assistant Services panel.
const ORDER: LLMPurpose[] = ["embedding", "extraction", "classification"]

interface Props {
  state: PipelineState
}

export function LLMPanel({ state }: Props) {
  const reembedAll = useReembedAll()
  const [obsolete, setObsolete] = useState<{
    memories: number
    code_chunks: number
    entities: number
  } | null>(null)

  const startReembed = () => {
    reembedAll.mutate(undefined, {
      onSuccess: () => {
        toast.info("Re-embed started — track progress in the Maintenance tab")
        setObsolete(null)
      },
      onError: (err) =>
        toast.error(`Re-embed failed: ${(err as Error).message}`),
    })
  }

  return (
    <Card>
      <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
        <CardTitle className="text-lg uppercase tracking-wide">
          LLM pipeline
        </CardTitle>
        <CardDescription>
          Embedding, extraction, and classification settings used during memory
          ingestion.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="space-y-2 p-6 pt-4">
          {ORDER.map((p) => (
            <LLMPurposeCard
              key={p}
              purpose={p}
              config={state.llm[p]}
              prompts={state.prompts}
              onObsoleteDetected={setObsolete}
            />
          ))}
        </div>
      </CardContent>

      <Dialog
        open={obsolete !== null}
        onOpenChange={(v) => !v && setObsolete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Embedding model changed</DialogTitle>
          </DialogHeader>
          {obsolete && (
            <div className="space-y-3 py-2 text-sm">
              <p>
                The embedding changed. Existing vectors are now from the old
                model:
              </p>
              <ul className="list-disc space-y-1 pl-4 text-sm">
                {obsolete.memories > 0 && <li>{obsolete.memories} memories</li>}
                {obsolete.entities > 0 && <li>{obsolete.entities} entities</li>}
                {obsolete.code_chunks > 0 && (
                  <li>{obsolete.code_chunks} code chunks</li>
                )}
              </ul>
              <p className="text-muted-foreground text-sm">
                Re-embedding recomputes vectors only; extraction and
                classification stay as-is.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setObsolete(null)}>
              Later
            </Button>
            <Button onClick={startReembed} disabled={reembedAll.isPending}>
              {reembedAll.isPending ? "Starting…" : "Re-embed now"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
