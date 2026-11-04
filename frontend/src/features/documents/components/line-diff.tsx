import { useMemo } from "react"
import { diffLines } from "diff"
import { cn } from "darkraise-ui/lib"

// darkraise-ui ships no diff component (checked 2026-09-28 against its
// dist/components). This renderer exists only for that gap; a library diff
// view retires it.

// Bounds the main-thread work: a document may hold 1,000,000 characters, and
// the diff is O(N·D) in its edit distance. `diffLines` answers undefined past
// either bound.
const MAX_EDITS = 2_000
const DIFF_TIMEOUT_MS = 1_000

function splitLines(value: string): string[] {
  const lines = value.split("\n")
  if (lines[lines.length - 1] === "") lines.pop()
  return lines
}

export function LineDiff({ before, after }: { before: string; after: string }) {
  const parts = useMemo(
    () => diffLines(before, after, { maxEditLength: MAX_EDITS, timeout: DIFF_TIMEOUT_MS }),
    [before, after],
  )

  if (parts === undefined) {
    return (
      <p className="text-muted-foreground text-sm">
        These revisions differ in too many lines to compare here.
      </p>
    )
  }
  if (!parts.some((part) => part.added || part.removed)) {
    return (
      <p className="text-muted-foreground text-sm">The two revisions are identical.</p>
    )
  }

  return (
    <div
      role="group"
      aria-label="line diff"
      className="border-border overflow-x-auto rounded-md border py-1 font-mono text-xs leading-relaxed"
    >
      {parts.flatMap((part, partIndex) => {
        const change = part.added ? "added" : part.removed ? "removed" : "same"
        const mark = part.added ? "+" : part.removed ? "-" : " "
        return splitLines(part.value).map((line, lineIndex) => (
          <div
            key={`${partIndex}:${lineIndex}`}
            data-change={change}
            className={cn(
              "flex px-2 whitespace-pre-wrap",
              part.added && "bg-success-solid/15 text-success-text",
              part.removed && "bg-destructive-solid/15 text-destructive-text",
            )}
          >
            <span aria-hidden className="text-muted-foreground w-4 shrink-0 select-none">
              {mark}
            </span>
            <span data-line className="min-w-0 flex-1">
              {line}
            </span>
          </div>
        ))
      })}
    </div>
  )
}
