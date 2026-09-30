import { Link } from "@tanstack/react-router"
import { Database, ExternalLink, RefreshCw, Trash2, Zap } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import { ConfirmGate } from "./confirm-gate"
import { JobHistoryRetention } from "./job-history-retention"
import { useMaintenanceTabBinding } from "../use-maintenance-tab-binding"

/** One card of maintenance operations.
 *
 *  Matches the Flags and Security tabs: a library `Card` with a one-row header
 *  carrying an icon and the title. This tab was the last one still building
 *  its cards out of bare divs, which left three different card treatments
 *  across one Settings page. */
function OpCard({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof RefreshCw
  title: string
  children: React.ReactNode
}) {
  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        <Icon aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="min-w-0 truncate text-sm font-semibold">{title}</h3>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5 p-4">
        {children}
      </CardContent>
    </Card>
  )
}

function Op({
  name,
  meta,
  help,
  children,
  last,
}: {
  name: string
  meta?: string
  help?: React.ReactNode
  children?: React.ReactNode
  last?: boolean
}) {
  return (
    <div
      className={cn(
        "border-border flex flex-col gap-1.5 border-b border-dashed pb-2.5",
        last && "border-b-0 pb-0",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm font-semibold">{name}</span>
        {help && <HelpTip label={`About ${name}`}>{help}</HelpTip>}
        {meta && (
          <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
            {meta}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}

export function MaintenanceTab() {
  const m = useMaintenanceTabBinding()

  const expiredMeta =
    m.cleanup.expired === null
      ? undefined
      : m.cleanup.expired > 0
        ? `${m.cleanup.expired} expired`
        : "0 pending"
  const expiredHeadline =
    m.cleanup.expired === null
      ? "Delete expired memories now?"
      : `Delete ${m.cleanup.expired} expired memories now?`
  const expiredDesc =
    m.cleanup.expired === null || !m.cleanup.expiredDependents
      ? "Permanent. Memories they replaced are marked deprecated first."
      : `Permanent. ${m.cleanup.expiredDependents} memories they replaced are marked deprecated first.`

  return (
    <div className="space-y-4">
      {m.lastOpNote && (
        <div className="border-success/50 bg-success/8 rounded-md border p-3 text-sm">
          <b className="font-semibold">Last operation:</b> {m.lastOpNote}
        </div>
      )}

      {/* A stack, not a 3-up grid. The four cards ran 192-414px tall, so the
          grid left a ragged bottom edge and a hole where the fourth wrapped;
          and the other two Settings tabs are stacks, so this was the last
          column layout on the page. */}
      <div className="flex flex-col gap-6">
        <OpCard icon={RefreshCw} title="Re-embed">
          <Op
            name="Memories"
            meta={
              m.reembed.memories > 0
                ? `${m.reembed.memories} missing a vector`
                : "0 missing"
            }
            help="Embeds memories that have no vector for the current embedding model. Runs in the background."
          >
            <ConfirmGate
              tone="primary"
              disabled={m.reembed.memories === 0}
              trigger={
                <Button
                  variant="outline"
                  className="border-primary/60 text-primary-text"
                  disabled={m.reembed.memories === 0}
                  tabIndex={-1}
                >
                  <Zap className="mr-1.5 size-3.5" />
                  Re-embed memories
                </Button>
              }
              headline={`Re-embed ${m.reembed.memories} memories now?`}
              desc="Calls the embedding model for each one. Nothing is deleted, but it cannot be cancelled once started."
              confirmLabel="Confirm — start re-embed"
              onConfirm={() => m.run("reembed_memories")}
            />
          </Op>
          <Op
            name="Entities"
            meta={
              m.reembed.entities > 0
                ? `${m.reembed.entities} missing`
                : "0 missing"
            }
            last
          >
            <ConfirmGate
              tone="primary"
              disabled={m.reembed.entities === 0}
              trigger={
                <Button
                  variant="outline"
                  disabled={m.reembed.entities === 0}
                  tabIndex={-1}
                >
                  Re-embed entities
                </Button>
              }
              headline={`Re-embed ${m.reembed.entities} entities now?`}
              desc="Calls the embedding model for each one. Nothing is deleted, but it cannot be cancelled once started."
              confirmLabel="Confirm — start re-embed"
              onConfirm={() => m.run("reembed_entities")}
            />
          </Op>
        </OpCard>

        <JobHistoryRetention />

        <OpCard icon={Trash2} title="Cleanup">
          <Op
            name="Expired memories"
            meta={expiredMeta}
            help="Deletes memories past their expiry date. Also runs hourly."
          >
            <ConfirmGate
              tone="danger"
              disabled={m.cleanup.expired === 0}
              trigger={
                <Button
                  variant="outline"
                  className="border-destructive/60 text-destructive"
                  disabled={m.cleanup.expired === 0}
                  tabIndex={-1}
                >
                  <Trash2 className="mr-1.5 size-3.5" />
                  Run sweep now
                </Button>
              }
              headline={expiredHeadline}
              desc={expiredDesc}
              confirmLabel="Confirm — delete now"
              onConfirm={() => m.run("expired_memory_cleanup")}
            />
          </Op>
          <Op
            name="Orphaned entities"
            meta="on schedule"
            help="Deletes entities no memory or relation refers to any more."
          >
            <ConfirmGate
              tone="danger"
              trigger={
                <Button
                  variant="outline"
                  className="border-warning/60 text-warning-text"
                  tabIndex={-1}
                >
                  Run now
                </Button>
              }
              headline="Delete orphaned entities now?"
              desc="Deletes entities no memory or relation refers to any more."
              confirmLabel="Confirm — run now"
              onConfirm={() => m.run("graph_orphan_cleanup")}
            />
          </Op>
          <Op
            name="Unused tags"
            meta="on schedule"
            help="Deletes tags no memory carries any more."
          >
            <ConfirmGate
              tone="danger"
              trigger={
                <Button
                  variant="outline"
                  className="border-warning/60 text-warning-text"
                  tabIndex={-1}
                >
                  Run now
                </Button>
              }
              headline="Delete unused tags now?"
              desc="Deletes tags no memory carries any more."
              confirmLabel="Confirm — run now"
              onConfirm={() => m.run("tag_orphan_cleanup")}
            />
          </Op>
          <Op
            name="Unresolved pipeline failures"
            meta={`${m.cleanup.failuresMemoryIngest} memory · ${m.cleanup.failuresCodeRepo} code`}
            last
          >
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" asChild>
                <Link to="/activity" search={{ tab: "triage", day: undefined }}>
                  <ExternalLink className="mr-1.5 size-3.5" />
                  View in Activity
                </Link>
              </Button>
            </div>
          </Op>
        </OpCard>

        <OpCard icon={Database} title="Embedding caches">
          <Op
            name="Prune unused caches"
            meta={
              m.dbops.retiredFingerprints === null
                ? undefined
                : m.dbops.retiredFingerprints.length > 0
                  ? `${m.dbops.retiredFingerprints.length} unused`
                  : "none unused"
            }
            help={
              m.dbops.retiredFingerprints !== null &&
              m.dbops.retiredFingerprints.length > 0
                ? `Drops the caches of embedding models no longer in use: ${m.dbops.retiredFingerprints.join(", ")}.`
                : "Drops the caches of embedding models no longer in use."
            }
            last
          >
            <ConfirmGate
              tone="danger"
              disabled={m.dbops.retiredFingerprints?.length === 0}
              trigger={
                <Button
                  variant="outline"
                  className="border-destructive/60 text-destructive"
                  disabled={m.dbops.retiredFingerprints?.length === 0}
                  tabIndex={-1}
                >
                  <Trash2 className="mr-1.5 size-3.5" />
                  Prune caches
                </Button>
              }
              headline={
                m.dbops.retiredFingerprints === null
                  ? "Prune unused embedding caches now?"
                  : `Drop ${m.dbops.retiredFingerprints.length} unused caches now?`
              }
              desc="Irreversible. A cache rebuilds if its model is used again."
              confirmLabel="Confirm — drop tables"
              onConfirm={() => m.run("prune_caches")}
            />
          </Op>
        </OpCard>
      </div>
    </div>
  )
}
