import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { useDemoStore } from "@/demo/store"
import { formatWhen } from "@/lib/format"
import type { DemoRepo, ReindexOptions } from "@/demo/types"

const TOGGLES: {
  key: keyof ReindexOptions
  label: string
  description: string
}[] = [
  {
    key: "full",
    label: "full",
    description:
      "Rebuild the entire repo graph from scratch, ignoring last_indexed_commit. Off runs the incremental diff (changed files only since the last indexed HEAD).",
  },
  {
    key: "enrich_symbols",
    label: "enrich_symbols",
    description:
      "Drain the pending-symbol LLM-summary backlog inline during this run, bounded and scoped to this repo. Off leaves symbols draining lazily via the code_enrichment background job.",
  },
  {
    key: "generate_wiki",
    label: "generate_wiki",
    description:
      "Generate the LLM wiki over the graph after this run completes. GET /code/wiki is read-only and never triggers generation on its own — this toggle is the only way a wiki gets built.",
  },
]

// POST /repos/{id}/reindex accepts exactly {full, enrich_symbols,
// generate_wiki}, all default false — the toggles only gate the two
// LLM-cost phases (13, 14) and the full-vs-incremental diff.
export function ReindexDialog({
  repo,
  open,
  onOpenChange,
  emphasizeWiki = false,
}: {
  repo: DemoRepo
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Opened from the Wiki empty state: pre-enable + highlight generate_wiki. */
  emphasizeWiki?: boolean
}) {
  const triggerReindex = useDemoStore((s) => s.triggerReindex)
  const [opts, setOpts] = useState<ReindexOptions>({
    full: false,
    enrich_symbols: false,
    generate_wiki: emphasizeWiki,
  })

  useEffect(() => {
    if (open) {
      setOpts({
        full: false,
        enrich_symbols: false,
        generate_wiki: emphasizeWiki,
      })
    }
  }, [open, emphasizeWiki])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reindex — {repo.name}</DialogTitle>
          <p className="text-muted-foreground font-mono text-sm">
            {repo.head ? `current HEAD ${repo.head}` : "never indexed"}
            {repo.last_indexed_at
              ? ` · last indexed ${formatWhen(repo.last_indexed_at)}`
              : ""}
          </p>
        </DialogHeader>
        <div className="space-y-1">
          {TOGGLES.map((toggle) => (
            <label
              key={toggle.key}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-md px-2 py-2.5",
                emphasizeWiki &&
                  toggle.key === "generate_wiki" &&
                  "border-primary/45 bg-primary/8 border border-dashed",
              )}
            >
              <span className="min-w-0 flex-1 space-y-0.5">
                <span className="block font-mono text-sm font-semibold">
                  {toggle.label}
                </span>
                <span className="text-muted-foreground block text-sm">
                  {emphasizeWiki && toggle.key === "generate_wiki"
                    ? "the one toggle that will populate the Wiki tab"
                    : toggle.description}
                </span>
              </span>
              <Switch
                checked={opts[toggle.key]}
                onCheckedChange={(checked) =>
                  setOpts((prev) => ({ ...prev, [toggle.key]: checked }))
                }
                aria-label={toggle.label}
                className="mt-0.5"
              />
            </label>
          ))}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            onClick={() => {
              triggerReindex(repo.id, opts)
              onOpenChange(false)
            }}
          >
            Run reindex
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
