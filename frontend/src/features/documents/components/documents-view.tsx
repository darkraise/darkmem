import { useState } from "react"
import { Sparkles, FileText } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { EmptyState } from "@/components/darkmem"
import { Input } from "darkraise-ui/components/input"
import { Skeleton } from "darkraise-ui/components/skeleton"

import {
  useDocumentConnections,
  useDocumentSummary,
  useDocuments,
  useGroundedQa,
  type QaResponse,
} from "@/hooks/api"

/**
 * The EH1 horizon's one surface (TH1.16, doc 16 §6, doc 13).
 *
 * Three rules it exists to keep visible rather than merely satisfy:
 *
 * 1. **A withheld answer says so plainly.** It is not a greyed-out answer or a
 *    caveat under prose — there is no prose. The door sends no sentences for a
 *    withheld outcome, and this renders the reason instead.
 * 2. **A summary is visibly unbadged.** No verification chip, and the copy says
 *    it is a report over one document rather than a verified claim.
 * 3. **The surface is labelled horizon**, on the page and on the data.
 */
export function DocumentsView({ project = "default" }: { project?: string }) {
  const documents = useDocuments(project)
  const [selected, setSelected] = useState<string | null>(null)
  const [question, setQuestion] = useState("")
  const qa = useGroundedQa()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" size="sm" className="border-dashed font-mono">
          horizon
        </Badge>
        <span className="text-muted-foreground text-sm">
          Documents and grounded answers over them. This lane ships behind its
          own eval gate and is labelled horizon everywhere it appears.
        </span>
      </div>

      <Card elevation="low">
        <CardHeader className="pb-3">
          <p className="text-sm font-semibold">Documents</p>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <Skeleton className="h-20 w-full rounded-md" />
          ) : documents.isError ? (
            <p className="text-muted-foreground text-sm">
              the document list could not be read — a failed read, not an empty
              corpus
            </p>
          ) : (documents.data?.items ?? []).length === 0 ? (
            <EmptyState
              kind="empty"
              icon={FileText}
              title="No documents filed"
              description="Filing a document parses it into blocks; nothing is lifted or summarised until you ask."
            />
          ) : (
            <div className="flex flex-col gap-1.5">
              {(documents.data?.items ?? []).map((document) => (
                <button
                  key={document.id}
                  type="button"
                  onClick={() => setSelected(document.id)}
                  className="border-border hover:text-primary flex flex-wrap items-center gap-2 border-t border-dashed pt-1.5 text-left text-sm transition-colors first:border-t-0 first:pt-0"
                >
                  <span className="font-medium">
                    {document.title ?? "untitled document"}
                  </span>
                  <span className="text-muted-foreground font-mono text-sm">
                    {document.block_count} blocks
                  </span>
                  {document.uri && (
                    <span className="text-muted-foreground truncate font-mono text-sm">
                      {document.uri}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selected && <DocumentDetail documentId={selected} />}

      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="text-sm font-semibold">Grounded answer</p>
          <p className="text-muted-foreground text-sm">
            Every sentence is cited to a block span, and an answer that cannot
            be grounded is withheld rather than served.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Input
              aria-label="Question"
              placeholder="Ask a question over your documents"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="min-w-52 flex-1"
            />
            <Button
              variant="outline"
              disabled={!question.trim() || qa.isPending}
              onClick={() =>
                qa.mutate({
                  question: question.trim(),
                  project,
                  document_id: selected,
                })
              }
            >
              <Sparkles className="mr-1.5 size-3.5" />
              {qa.isPending ? "Asking…" : "Ask"}
            </Button>
          </div>
          {qa.isError && (
            <p className="text-destructive text-sm">
              the question could not be answered — {qa.error.message}
            </p>
          )}
          {qa.data && <QaAnswer answer={qa.data} />}
        </CardContent>
      </Card>
    </div>
  )
}

function QaAnswer({ answer }: { answer: QaResponse }) {
  if (answer.outcome === "withheld") {
    return (
      <div className="border-border bg-muted/20 space-y-1 rounded-md border border-dashed p-2.5">
        <p className="text-sm font-semibold">Answer withheld — not grounded</p>
        <p className="text-muted-foreground text-sm">
          {answer.reason ??
            "this answer could not be grounded in the documents, so it is not served"}
        </p>
        <p className="text-muted-foreground text-sm">
          {answer.judged
            ? `${answer.entailed} of ${answer.total} sentences were supported`
            : "the faithfulness judge is not qualified for this check, so nothing was graded"}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {answer.outcome === "labelled" && (
        <p className="text-sm font-semibold">
          Could not fully ground this answer — {answer.entailed} of{" "}
          {answer.total} sentences are supported by their cited span
        </p>
      )}
      {answer.sentences.map((sentence, index) => (
        <div
          key={index}
          className="border-border flex flex-wrap items-start gap-2 border-t border-dashed py-2 first:border-t-0 first:pt-0"
        >
          <p className="min-w-52 flex-1 text-sm">{sentence.text}</p>
          {sentence.citation ? (
            <Badge variant="outline" size="sm" className="font-mono">
              block {sentence.citation.block_id.slice(0, 8)} ·{" "}
              {sentence.citation.span_start}–{sentence.citation.span_end}
            </Badge>
          ) : (
            <span className="text-muted-foreground text-sm italic">
              no citation — this sentence is not grounded
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

function DocumentDetail({ documentId }: { documentId: string }) {
  const summary = useDocumentSummary(documentId)
  const connections = useDocumentConnections(documentId)

  return (
    <div className="grid gap-3.5 sm:grid-cols-2">
      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="text-sm font-semibold">Summary</p>
          <p className="text-muted-foreground text-sm">
            A report over this document — not a verified claim, and never
            badged.
          </p>
        </CardHeader>
        <CardContent>
          {summary.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : summary.data ? (
            <p className="text-sm">{summary.data.text}</p>
          ) : (
            <p className="text-muted-foreground text-sm italic">
              no summary has been generated — generating one is an explicit act
            </p>
          )}
        </CardContent>
      </Card>

      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="text-sm font-semibold">Connections</p>
          <p className="text-muted-foreground text-sm">
            Emergent from shared entities after lifting — not a synthesis.
          </p>
        </CardHeader>
        <CardContent>
          {connections.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : (connections.data?.items ?? []).length === 0 ? (
            <p className="text-muted-foreground text-sm italic">
              no shared entities with another document
            </p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {(connections.data?.items ?? []).map((connection) => (
                <div key={connection.document_id} className="text-sm">
                  <span className="font-medium">
                    {connection.title ?? "untitled document"}
                  </span>
                  <span className="text-muted-foreground ml-2 font-mono text-sm">
                    {connection.shared_entities.join(" · ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
