import { useMemo } from "react"
import { diffLines } from "diff"
import { cn } from "darkraise-ui/lib"

// darkraise-ui ships no diff component (checked 2026-09-28 against its
// dist/components). This renderer exists only for that gap; a library diff
// view retires it.

function splitLines(value: string): string[] {
  const lines = value.split("\n")
  if (lines[lines.length - 1] === "") lines.pop()
  return lines
}

export function LineDiff({ before, after }: { before: string; after: string }) {
  const parts = useMemo(() => diffLines(before, after), [before, after])

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
              part.added && "bg-success/15 text-success-text",
              part.removed && "bg-destructive/15 text-destructive",
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
