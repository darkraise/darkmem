import ReactMarkdown from "react-markdown"
import { AlignLeft, Columns2, FileText } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { IconSegmented, type IconSegmentedOption } from "@/components/darkmem"

/**
 * The three ways to read a system prompt, shared by every surface that shows
 * one so the control behaves identically in each.
 *
 * A system prompt is markdown that is *delivered as plain text*, which is why
 * neither view alone is enough: rendered, the heading structure is readable
 * but the literal bytes the model receives are not; plain, the reverse. Split
 * is for editing, where both questions are live at once.
 */
export type PromptViewMode = "plain" | "markdown" | "split"

const MODE_OPTIONS: ReadonlyArray<IconSegmentedOption<PromptViewMode>> = [
  { value: "plain", label: "Plain text", icon: AlignLeft },
  { value: "markdown", label: "Rendered markdown", icon: FileText },
  { value: "split", label: "Split view", icon: Columns2 },
]

export function PromptViewToggle({
  value,
  onChange,
  className,
}: {
  value: PromptViewMode
  onChange: (value: PromptViewMode) => void
  className?: string
}) {
  return (
    <IconSegmented
      value={value}
      options={MODE_OPTIONS}
      onChange={onChange}
      label="Prompt view"
      className={className}
    />
  )
}

function PlainPane({ value }: { value: string }) {
  return (
    <pre className="border-border bg-muted/12 min-h-0 flex-1 overflow-auto rounded-md border p-3 font-mono text-sm whitespace-pre-wrap">
      {value}
    </pre>
  )
}

function MarkdownPane({ value }: { value: string }) {
  return (
    <div className="border-border bg-muted/12 min-h-0 flex-1 overflow-auto rounded-md border p-3">
      <div className="md-prose">
        <ReactMarkdown>{value}</ReactMarkdown>
      </div>
    </div>
  )
}

/**
 * The prompt itself, in whichever view is selected.
 *
 * Each pane scrolls on its own in split view: one shared scrollbar would tie
 * two renderings of different heights together, so scrolling to a passage in
 * the rendered pane would land somewhere else in the source.
 */
export function PromptPanes({
  value,
  mode,
  className,
}: {
  value: string
  mode: PromptViewMode
  className?: string
}) {
  if (mode === "split") {
    return (
      <div
        className={cn(
          "grid min-h-0 flex-1 grid-cols-1 gap-2 sm:grid-cols-2",
          className,
        )}
      >
        <PlainPane value={value} />
        <MarkdownPane value={value} />
      </div>
    )
  }
  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      {mode === "markdown" ? (
        <MarkdownPane value={value} />
      ) : (
        <PlainPane value={value} />
      )}
    </div>
  )
}
