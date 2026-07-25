import { useEffect, useRef, useState } from "react"
import { Bookmark, ChevronRight, Copy } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"
import { useDemoSessionRuns } from "@/demo/hooks"
import type { DemoSessionRun } from "@/demo/types"
import { SurfaceStateChip } from "./module-surface"

// A checkpoint is an OPERATIONAL session digest, not verified knowledge —
// it carries NO verification badge anywhere in this tab; the vault's badge
// vocabulary would over-claim. This label is the whole of its epistemics.
const KIND_LABEL = "session digest · not verified knowledge"

function KindPill() {
  return (
    <span className="border-border bg-muted/40 text-muted-foreground rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide whitespace-nowrap">
      {KIND_LABEL}
    </span>
  )
}

function CopyResumeButton({ block }: { block: string }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  return (
    <Button
      size="sm"
      variant="outline"
      className="ml-auto"
      onClick={() => {
        void navigator.clipboard?.writeText(block).catch(() => {})
        setCopied(true)
        window.clearTimeout(timer.current)
        timer.current = window.setTimeout(() => setCopied(false), 2000)
      }}
    >
      <Copy className="mr-1.5 size-3.5" />
      {copied ? "copied" : "copy resume block"}
    </Button>
  )
}

function RunCard({
  run,
  selected,
  onSelect,
}: {
  run: DemoSessionRun
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "border-border bg-card flex w-full flex-wrap items-center gap-2.5 rounded-md border p-3 text-left",
        selected && "border-primary/45 bg-primary/5",
      )}
    >
      <Bookmark aria-hidden className="text-primary h-4 w-4 shrink-0" />
      <span className="flex min-w-0 flex-1 basis-56 flex-col gap-0.5">
        <span className="text-sm font-semibold">{run.title}</span>
        <span className="text-muted-foreground text-sm">
          <code className="font-mono">origin_key: {run.origin_key}</code> ·
          project <b className="text-foreground font-semibold">{run.project}</b>
        </span>
      </span>
      <KindPill />
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        {run.meta_label}
      </span>
    </button>
  )
}

function RunDetail({ run }: { run: DemoSessionRun }) {
  if (!run.latest) {
    return (
      <EmptyState
        icon={<Bookmark aria-hidden className="h-6 w-6" />}
        title="No checkpoints for this run yet"
        description="Run /darkmem-checkpoint (or let the session-end hook fire) to capture a resumable digest. Once one exists, a fresh session resumes from it with /darkmem-resume instead of reloading the whole context."
      />
    )
  }
  const { latest } = run

  return (
    <div className="space-y-4">
      <div className="border-primary/35 bg-primary/5 space-y-3 rounded-md border p-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <SurfaceStateChip state="populated" label="latest checkpoint" />
          <span className="text-muted-foreground font-mono text-sm">
            {latest.saved_label}
          </span>
          <CopyResumeButton block={latest.resume_block} />
        </div>
        <p className="text-sm leading-relaxed">{latest.summary}</p>
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
          <div className="space-y-1.5">
            <p className="text-muted-foreground font-mono text-[10px] uppercase tracking-wide">
              next steps
            </p>
            <ul className="space-y-1">
              {latest.next_steps.map((step) => (
                <li key={step} className="flex items-start gap-1.5 text-sm">
                  <ChevronRight
                    aria-hidden
                    className="text-primary mt-0.5 h-3.5 w-3.5 shrink-0"
                  />
                  {step}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-1.5">
            <p className="text-muted-foreground font-mono text-[10px] uppercase tracking-wide">
              key decisions
            </p>
            <ul className="space-y-1">
              {latest.key_decisions.map((decision) => (
                <li
                  key={decision}
                  className="text-muted-foreground font-mono text-sm"
                >
                  — {decision}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-1.5">
            <p className="text-muted-foreground font-mono text-[10px] uppercase tracking-wide">
              touched files
            </p>
            <ul className="space-y-1">
              {latest.touched_files.map((file) => (
                <li
                  key={file}
                  className="text-muted-foreground font-mono text-sm"
                >
                  — {file}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div>
        <p className="text-muted-foreground pb-1.5 font-mono text-[10px] uppercase tracking-wide">
          this run's checkpoint history
        </p>
        <div className="flex flex-col">
          {run.history.map((event, i) => (
            <div
              key={`${event.time_label}-${i}`}
              className="border-border flex flex-wrap items-center gap-2.5 border-t border-dashed py-2 text-sm first:border-t-0"
            >
              <span
                aria-hidden
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  event.event === "resumed" ? "bg-info" : "bg-primary",
                )}
              />
              <span className="text-muted-foreground w-12 font-mono text-sm">
                {event.time_label}
              </span>
              <span className="font-mono text-sm">{event.event}</span>
              <span className="text-muted-foreground min-w-0 flex-1 basis-52">
                {event.detail}
              </span>
              <span className="text-muted-foreground font-mono text-sm">
                {event.tokens_label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-muted-foreground pb-0.5 font-mono text-[10px] uppercase tracking-wide">
          the CLAUDE.md managed block resume writes
        </p>
        <pre className="border-border bg-muted/40 overflow-x-auto whitespace-pre-wrap rounded-md border p-3.5 font-mono text-sm leading-relaxed">
          {latest.resume_block}
        </pre>
        <p className="text-muted-foreground text-sm">
          The writer may read the whole file but only replaces the bytes
          between the two sentinel comments, strip-before-rewrite, so a human's
          own CLAUDE.md rules above or below survive every refresh and a
          re-resume never duplicates. Every write journals a resumed event, so
          the history above shows exactly when a fresh session picked the
          digest up.
        </p>
      </div>
    </div>
  )
}

export function CheckpointsTab() {
  const runs = useDemoSessionRuns()
  const [selectedId, setSelectedId] = useState(runs[0]?.id ?? null)
  const selected = runs.find((r) => r.id === selectedId)

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        A run's progress captured as a compact digest keyed on its origin_key,
        stored server-side; resume is a specialised inject that rewrites a
        marker-bounded managed block in the tool's CLAUDE.md under the inject
        token budget, so a fresh session loads a small digest instead of
        reloading a full context window. Checkpoints are operational digests,
        not vault knowledge — they carry no verification badge, and every
        save/resume is journaled to events.
      </p>
      <div className="space-y-2">
        {runs.map((run) => (
          <RunCard
            key={run.id}
            run={run}
            selected={run.id === selectedId}
            onSelect={() => setSelectedId(run.id)}
          />
        ))}
      </div>
      {selected && <RunDetail run={selected} />}
    </div>
  )
}
