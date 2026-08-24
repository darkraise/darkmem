import { useEffect, useRef, useState } from "react"
import { Bookmark, ChevronRight, Copy } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState, listItemClass, useDetailLevel } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import {
  useCheckpointDigest,
  useCheckpointRuns,
  type CheckpointDigestData,
  type CheckpointRunData,
} from "../use-checkpoint-runs"
import { ModuleSurface, SurfaceStateChip } from "./module-surface"

// A checkpoint is an OPERATIONAL session digest, not verified knowledge —
// it carries NO verification badge anywhere in this tab; the vault's badge
// vocabulary would over-claim. This label is the whole of its epistemics,
// which is why it renders at BOTH detail levels: `simple` collapses
// technical detail and never hides an honesty signal.
const KIND_LABEL = "session digest · not verified knowledge"

function KindPill() {
  return (
    <span className="border-border bg-muted/40 text-muted-foreground rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase">
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
  advanced,
  onSelect,
}: {
  run: CheckpointRunData
  selected: boolean
  advanced: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={listItemClass({
        interactive: true,
        className: cn(
          "bg-card flex w-full flex-wrap items-center gap-2.5 p-3 text-left",
          selected && "border-primary/45 bg-primary/5",
        ),
      })}
    >
      <Bookmark aria-hidden className="text-primary h-4 w-4 shrink-0" />
      <span className="flex min-w-0 flex-1 basis-56 flex-col gap-0.5">
        <span className="text-sm font-semibold">{run.title}</span>
        <span className="text-muted-foreground text-sm">
          {advanced ? (
            <>
              <code className="font-mono">origin_key: {run.originKey}</code>{" "}
              ·{" "}
            </>
          ) : null}
          project <b className="text-foreground font-semibold">{run.project}</b>
        </span>
      </span>
      <KindPill />
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        {run.metaLabel}
      </span>
    </button>
  )
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-1.5">
      <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {title}
      </p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="text-muted-foreground font-mono text-sm">
            — {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

function RunDetail({
  run,
  digest,
  isLoading,
}: {
  run: CheckpointRunData
  digest: CheckpointDigestData | null
  isLoading: boolean
}) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"

  if (isLoading) {
    return (
      <p className="text-muted-foreground text-sm">
        Loading this run's digest…
      </p>
    )
  }
  if (!digest) {
    return (
      <EmptyState
        kind="empty"
        icon={Bookmark}
        title="No checkpoints for this run yet"
        description="Run /darkmem-checkpoint (or let the session-end hook fire) to capture a resumable digest. Once one exists, a fresh session resumes from it with /darkmem-resume instead of reloading the whole context."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="border-primary/35 bg-primary/5 space-y-3 rounded-md border p-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <SurfaceStateChip state="populated" label="latest checkpoint" />
          <span className="text-muted-foreground font-mono text-sm">
            {digest.savedLabel}
          </span>
          {advanced && digest.tokenEstimate !== null ? (
            <span className="text-muted-foreground font-mono text-sm">
              ~{digest.tokenEstimate.toLocaleString()} tokens of the inject
              budget
            </span>
          ) : null}
          {/* The affordance itself is not technical detail, so it survives
              `simple`; only the raw block below is collapsed. */}
          <CopyResumeButton block={digest.resumeLine} />
        </div>
        <p className="text-sm leading-relaxed">{digest.summary}</p>
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
          <div className="space-y-1.5">
            <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
              next steps
            </p>
            <ul className="space-y-1">
              {digest.nextSteps.map((step) => (
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
          <DetailList title="key decisions" items={digest.keyDecisions} />
          <DetailList title="touched files" items={digest.touchedFiles} />
        </div>
      </div>

      <div>
        <p className="text-muted-foreground pb-1.5 font-mono text-[10px] tracking-wide uppercase">
          this run's checkpoint history
        </p>
        {run.history.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={Bookmark}
            title="Nothing journalled for this run"
            description="Checkpoints appear as the session saves them."
          />
        ) : (
          <div className="flex flex-col">
            {run.history.map((event) => (
              <div
                key={event.id}
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
                  {event.timeLabel}
                </span>
                <span className="font-mono text-sm">{event.event}</span>
                <span className="text-muted-foreground min-w-0 flex-1 basis-52">
                  {event.detail}
                </span>
                {advanced && event.tokensLabel ? (
                  <span className="text-muted-foreground font-mono text-sm">
                    {event.tokensLabel}
                  </span>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {advanced ? (
        <div className="space-y-2">
          <p className="text-muted-foreground pb-0.5 font-mono text-[10px] tracking-wide uppercase">
            what resume writes into the managed block
          </p>
          <pre className="border-border bg-muted/40 overflow-x-auto rounded-md border p-3.5 font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {digest.resumeLine}
          </pre>
          <p className="text-muted-foreground text-sm">
            This is the digest served by the resume path itself, not a rendering
            of it — the copy button hands you these exact bytes. The writer may
            read the whole file but only replaces what lies between the two
            sentinel comments, strip-before-rewrite, so a human's own CLAUDE.md
            rules above or below survive every refresh and a re-resume never
            duplicates. The rest of the block is whatever the vault fills under
            the same token budget at resume time. Every write journals a resumed
            event, so the history above shows exactly when a fresh session
            picked the digest up.
          </p>
        </div>
      ) : null}
    </div>
  )
}

export function CheckpointsTab() {
  const { runs, isLoading, isError } = useCheckpointRuns()
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = runs.find((r) => r.id === selectedId) ?? runs[0] ?? null
  const { digest, isLoading: digestLoading } = useCheckpointDigest(selected)

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
      <ModuleSurface
        title="Checkpointed runs"
        state={isLoading ? "empty" : runs.length > 0 ? "populated" : "empty"}
        meta={`${runs.length} ${runs.length === 1 ? "run" : "runs"}`}
      >
        {isError ? (
          <p className="text-destructive text-sm">
            The checkpoint journal could not be read.
          </p>
        ) : isLoading ? (
          <p className="text-muted-foreground text-sm">Loading runs…</p>
        ) : runs.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={Bookmark}
            title="No runs have checkpointed yet"
            description="A run appears here the moment it saves its first digest — over REST or over MCP. Nothing else creates one, so an empty list means no agent has checkpointed against this instance."
          />
        ) : (
          runs.map((run) => (
            <RunCard
              key={run.id}
              run={run}
              advanced={advanced}
              selected={run.id === selected?.id}
              onSelect={() => setSelectedId(run.id)}
            />
          ))
        )}
      </ModuleSurface>
      {!isError && !isLoading && selected && (
        <ModuleSurface
          title="Run digest"
          state={digestLoading ? "empty" : digest ? "populated" : "empty"}
          meta={selected.id}
        >
          <RunDetail run={selected} digest={digest} isLoading={digestLoading} />
        </ModuleSurface>
      )}
    </div>
  )
}
