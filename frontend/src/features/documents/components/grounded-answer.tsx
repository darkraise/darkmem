import { Badge } from "darkraise-ui/components/badge"
import type { DocumentListItem, QaCitation, QaResponse } from "@/hooks/api"

function documentLabel(doc: DocumentListItem): string {
  const last = doc.uri?.split("/").filter(Boolean).pop()
  return last ?? doc.title ?? "untitled document"
}

/**
 * A grounded answer over the project's documents (TH1.16, doc 16 §6).
 *
 * A withheld answer renders its reason and no prose at all: the door sends no
 * sentences for that outcome, and a surface that rendered an answer with a
 * caveat under it would serve exactly what the gate withheld.
 */
export function GroundedAnswer({
  answer,
  documents,
  onOpenCitation,
}: {
  answer: QaResponse
  /** Resolves a citation's document for its label. A citation naming a
   *  document outside the loaded list keeps its raw block id and is inert. */
  documents: DocumentListItem[]
  onOpenCitation: (citation: QaCitation) => void
}) {
  return (
    <div className="border-border space-y-2 rounded-md border border-dashed p-3">
      <p className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        answer
      </p>
      {answer.outcome === "withheld" ? (
        <div className="space-y-1">
          <p className="text-sm font-semibold">
            Answer withheld — not grounded
          </p>
          <p className="text-muted-foreground text-sm">
            {answer.reason ??
              "this answer could not be grounded in the documents, so it is not served"}
          </p>
          <p className="text-muted-foreground text-sm">
            {answer.judged
              ? `${answer.entailed} of ${answer.total} sentences were supported`
              : "grounding could not be checked"}
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {answer.outcome === "labelled" && (
            <p className="text-sm font-semibold">
              Could not fully ground this answer — {answer.entailed} of{" "}
              {answer.total} sentences are supported
            </p>
          )}
          {answer.sentences.map((sentence, index) => (
            <div
              key={index}
              className="border-border flex flex-wrap items-start gap-2 border-t border-dashed py-2 first:border-t-0 first:pt-0"
            >
              <p className="min-w-52 flex-1 text-sm">{sentence.text}</p>
              {sentence.citation ? (
                <CitationChip
                  citation={sentence.citation}
                  document={documents.find(
                    (d) => d.id === sentence.citation?.document_id,
                  )}
                  onOpen={onOpenCitation}
                />
              ) : (
                <span className="text-muted-foreground text-sm italic">
                  no citation — this sentence is not grounded
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CitationChip({
  citation,
  document,
  onOpen,
}: {
  citation: QaCitation
  document: DocumentListItem | undefined
  onOpen: (citation: QaCitation) => void
}) {
  const span = `${citation.span_start}–${citation.span_end}`
  if (!document) {
    return (
      <Badge variant="outline" size="sm" className="font-mono">
        block {citation.block_id.slice(0, 8)} · {span}
      </Badge>
    )
  }
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      title="Open the cited passage"
      className="focus-visible:ring-primary/40 cursor-pointer rounded-md focus-visible:ring-2 focus-visible:outline-none"
    >
      <Badge
        variant="outline"
        size="sm"
        className="hover:bg-muted/40 font-mono"
      >
        {documentLabel(document)} · {span}
      </Badge>
    </button>
  )
}
