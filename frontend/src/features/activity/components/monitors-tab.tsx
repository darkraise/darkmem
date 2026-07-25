import {
  ArrowRight,
  Check,
  CircleCheck,
  CircleDashed,
  Clock,
  CornerDownRight,
  Info,
  Play,
  RefreshCw,
  TriangleAlert,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import {
  useDemoBufferMonitor,
  useDemoDreamMonitor,
} from "@/demo/hooks"
import type { DemoDreamChainJob } from "@/demo/types"
import { ModuleSurface } from "./module-surface"

function StagedCard({
  phase,
  headline,
  reason,
}: {
  phase: string
  headline: string
  reason: string
}) {
  return (
    <div className="border-warning/40 bg-warning/5 flex gap-3 rounded-md border border-dashed p-4">
      <Clock aria-hidden className="text-warning h-5 w-5 shrink-0" />
      <div className="flex flex-col gap-1.5">
        <span className="text-warning font-mono text-sm">{phase}</span>
        <span className="text-sm font-semibold">{headline}</span>
        <span className="text-muted-foreground max-w-3xl text-sm">{reason}</span>
      </div>
    </div>
  )
}

function FlowNode({
  label,
  caption,
  state,
}: {
  label: string
  caption: string
  state: "ok" | "active" | "pending"
}) {
  return (
    <div className="flex w-28 flex-none flex-col items-center gap-1.5 text-center">
      <span
        className={cn(
          "bg-card flex h-7 w-7 items-center justify-center rounded-full border-2",
          state === "ok" && "border-success text-success",
          state === "active" && "border-info bg-info/10 text-info",
          state === "pending" &&
            "border-border text-muted-foreground/70 border-dashed",
        )}
      >
        {state === "ok" && (
          <CircleCheck aria-hidden className="h-3.5 w-3.5" />
        )}
        {state === "active" && (
          <RefreshCw aria-hidden className="h-3.5 w-3.5" />
        )}
        {state === "pending" && (
          <CircleDashed aria-hidden className="h-3.5 w-3.5" />
        )}
      </span>
      <span
        className={cn(
          "font-mono text-sm font-semibold leading-tight",
          state === "active" ? "text-info" : "text-foreground",
        )}
      >
        {label}
      </span>
      <span className="text-muted-foreground text-[10px] leading-snug">
        {caption}
      </span>
    </div>
  )
}

function FlowConnector({ done }: { done: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "mt-3.5 h-0.5 min-w-3 flex-1",
        done ? "bg-success" : "bg-border",
      )}
    />
  )
}

function BufferTargetBoard() {
  const monitor = useDemoBufferMonitor()
  const { pending, claimed, done, error, poison, wait_process_note } =
    monitor.target
  const total = pending + claimed + done + error

  const tiles = [
    { key: "pending", value: pending, desc: "capture acked, awaiting claim", dot: "bg-muted-foreground/50", caution: false },
    { key: "claimed", value: claimed, desc: "in flight to the five-phase pipeline", dot: "bg-info", caution: false },
    { key: "done", value: done, desc: "flushed; retained briefly, then swept", dot: "bg-success", caution: false },
    { key: "error", value: error, desc: "attempts exceeded — poison", dot: "bg-warning", caution: true },
  ]

  return (
    <ModuleSurface
      title="Ingest buffer — memory_buffer"
      state="populated"
      meta="target design · not yet live"
    >
      <div className="flex items-start overflow-x-auto pb-1">
        <FlowNode label="pending" caption="capture acked, 202" state="ok" />
        <FlowConnector done />
        <FlowNode label="claimed" caption="SKIP LOCKED, in flight" state="ok" />
        <FlowConnector done />
        <FlowNode label="done" caption="flushed, swept on a delay" state="ok" />
      </div>
      <p className="text-warning flex items-center gap-1.5 text-sm">
        <CornerDownRight aria-hidden className="h-3.5 w-3.5 shrink-0" />
        <span>
          <code className="font-mono">claimed → error</code> when attempts
          exceeds the retry threshold — poison, surfaced below and in triage
        </span>
      </p>
      <div className="border-border flex h-2.5 overflow-hidden rounded-full border">
        {tiles.map((t) => (
          <div
            key={t.key}
            className={cn("h-full", t.dot)}
            style={{ flexGrow: Math.max(t.value, 1) }}
            title={`${t.key}: ${t.value} of ${total}`}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2.5 md:grid-cols-4">
        {tiles.map((t) => (
          <div
            key={t.key}
            className="border-border flex flex-col gap-1 rounded-md border p-2.5"
          >
            <span className="flex items-center gap-1.5">
              <span aria-hidden className={cn("h-2 w-2 rounded-full", t.dot)} />
              <span
                className={cn(
                  "font-mono text-[10px] uppercase tracking-wide",
                  t.caution ? "text-warning" : "text-muted-foreground",
                )}
              >
                {t.key}
              </span>
            </span>
            <span
              className={cn(
                "text-xl font-semibold",
                t.caution && "text-warning",
              )}
            >
              {t.value}
            </span>
            <span className="text-muted-foreground text-[10px] leading-snug">
              {t.desc}
            </span>
          </div>
        ))}
      </div>
      {poison && (
        <div className="border-warning/55 bg-warning/5 flex gap-2.5 rounded-md border border-dashed p-3">
          <TriangleAlert aria-hidden className="text-warning h-4 w-4 shrink-0" />
          <div className="flex flex-col gap-1">
            <span className="text-sm font-semibold">{poison.headline}</span>
            <span className="text-muted-foreground font-mono text-sm">
              {poison.detail}
            </span>
          </div>
        </div>
      )}
      <p className="text-muted-foreground border-border flex items-start gap-2 rounded-md border border-dashed px-2.5 py-2 text-sm">
        <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        {wait_process_note}
      </p>
    </ModuleSurface>
  )
}

function DreamTargetBoard({ onOpenDigest }: { onOpenDigest: () => void }) {
  const monitor = useDemoDreamMonitor()
  const { last_cycle_label, chain, narrative, lock_note } = monitor.target

  const connectorDone = (node: DemoDreamChainJob | undefined) =>
    node?.state === "ok"

  return (
    <ModuleSurface
      title="Consolidation cycle — dream-run monitor"
      state="populated"
      meta="target design · not yet live"
    >
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" variant="outline" disabled title="target design — not live">
          <Play className="mr-1.5 size-3.5" />
          Dream now
        </Button>
        <span className="text-muted-foreground text-[10px] italic">
          disabled — ships with the consolidation job family; nothing here can
          honestly trigger a cycle yet
        </span>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {last_cycle_label}
        </span>
      </div>
      <div className="flex items-start overflow-x-auto pb-1">
        {chain.map((node, i) => (
          <div key={node.key} className="flex flex-1 items-start">
            {i > 0 && <FlowConnector done={connectorDone(chain[i - 1])} />}
            <FlowNode
              label={node.key}
              caption={node.caption}
              state={node.state}
            />
          </div>
        ))}
      </div>
      <p className="text-sm">{narrative}</p>
      <p className="text-muted-foreground border-border flex items-start gap-2 rounded-md border border-dashed px-2.5 py-2 text-sm">
        <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        {lock_note}
      </p>
      <Button
        size="sm"
        variant="link"
        className="w-fit px-0"
        onClick={onOpenDigest}
      >
        Open in Dream digest
        <ArrowRight className="ml-1.5 size-3.5" />
      </Button>
    </ModuleSurface>
  )
}

export function MonitorsTab({ onOpenDigest }: { onOpenDigest: () => void }) {
  const buffer = useDemoBufferMonitor()
  const dream = useDemoDreamMonitor()

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        Two Activity modules staged behind backends that do not exist yet: the
        buffer-depth monitor (needs memory_buffer) and the dream-run monitor
        (needs the consolidation job family). A live-looking panel bound to a
        table that never writes would read as broken or as a shipped-capability
        claim, so each stays labelled staged — and each is followed by its
        fully populated target design so the whole surface is reviewable
        without any panel claiming it ships.
      </p>

      <ModuleSurface
        title="Ingest buffer — memory_buffer"
        state="staged"
        meta="Activity · staged module"
      >
        <StagedCard
          phase={buffer.staged_phase}
          headline="Buffer-depth monitor is staged"
          reason={buffer.staged_reason}
        />
      </ModuleSurface>
      <BufferTargetBoard />

      <ModuleSurface
        title="Consolidation cycle — dream-run monitor"
        state="staged"
        meta="Activity · staged module"
      >
        <StagedCard
          phase={dream.staged_phase}
          headline="Dream-run monitor is staged"
          reason={dream.staged_reason}
        />
      </ModuleSurface>
      <DreamTargetBoard onOpenDigest={onOpenDigest} />

      <p className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <Check aria-hidden className="h-3.5 w-3.5 shrink-0" />
        The other Activity modules — stepper, feed, triage, jobs — read live
        substrates and carry no staged label.
      </p>
    </div>
  )
}
