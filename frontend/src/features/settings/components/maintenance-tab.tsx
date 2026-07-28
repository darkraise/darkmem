import { Link } from "@tanstack/react-router"
import { Database, ExternalLink, RefreshCw, Trash2, Zap } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import { ConfirmGate } from "./confirm-gate"
import { useMaintenanceTabBinding } from "../use-maintenance-tab-binding"

function OpCard({
  icon: Icon,
  title,
  count,
  children,
}: {
  icon: typeof RefreshCw
  title: string
  count?: string
  children: React.ReactNode
}) {
  return (
    <div className="border-border bg-card flex flex-col gap-2.5 rounded-lg border p-3.5">
      <div className="border-border flex items-center gap-2 border-b border-dashed pb-2">
        <Icon aria-hidden className="text-muted-foreground h-4 w-4" />
        <span className="text-sm font-semibold">{title}</span>
        {count && (
          <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
            {count}
          </span>
        )}
      </div>
      {children}
    </div>
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
  meta: string
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
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {meta}
        </span>
      </div>
      {children}
    </div>
  )
}

function IllustrativeTag({ label }: { label: string }) {
  return (
    <span className="border-border text-muted-foreground inline-flex items-center rounded-full border border-dashed px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
      {label}
    </span>
  )
}

export function MaintenanceTab() {
  const m = useMaintenanceTabBinding()

  const expiredMeta =
    m.cleanup.expired === null
      ? "count not exposed via the API"
      : m.cleanup.expired > 0
        ? `${m.cleanup.expired} past expires_at`
        : "0 pending"
  const expiredHelp =
    m.cleanup.expired === null
      ? "GET /pipeline-failures/counts and /reembed/obsolete-counts have no equivalent for expires_at — the trigger runs the sweep regardless of what it finds."
      : m.cleanup.expired > 0
        ? `Deletes memories past their TTL. ${m.cleanup.expiredDependents} have dependents pointing at them via superseded_by — those are demoted to deprecated first, per chk_superseded_has_pointer.`
        : "Nothing past its TTL right now; the hourly schedule keeps running."
  const expiredHeadline =
    m.cleanup.expired === null
      ? "Run the expired-memory sweep now?"
      : `Delete ${m.cleanup.expired} expired memories now?`
  const expiredDesc =
    m.cleanup.expired === null
      ? "Deletes every memory past its TTL; dependents pointing at a deleted row via superseded_by are demoted to deprecated first, per chk_superseded_has_pointer. This is the same job the hourly schedule already runs — this button just runs it now."
      : `Permanent. ${m.cleanup.expiredDependents} dependents are demoted to deprecated (superseded_by cleared) before their target is deleted. This is the same job the hourly schedule already runs — this button just runs it now.`

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Re-embed backfills, cleanup triggers, and DB ops — every trigger
          confirms inline before it runs.
        </span>
        <HelpTip label="About the Maintenance tab">
          Re-embed backfills rows missing a vector under the active embedder
          fingerprint; cleanup ops are one-click triggers for the same
          JobRegistry jobs the hourly schedule runs. Re-embed&apos;s
          confirmation states cost and duration (it only backfills, it deletes
          nothing); cleanup&apos;s and DB ops&apos; confirm data loss.
        </HelpTip>
      </div>
      {!m.eventsJournaled && (
        // Kept always-visible, never tooltip-only (matches the dormant
        // ApiKey card's own rule) — a journaling gap is exactly the kind
        // of silent degradation this corpus exists to surface.
        <div className="border-warning/50 bg-warning/8 text-warning rounded-md border p-3 text-sm">
          None of these triggers are journaled to the events timeline today
          — an operator watching Activity → Timeline will not see them
          recorded there. Backend gap, tracked separately from this surface.
        </div>
      )}
      {m.lastOpNote && (
        <div className="border-success/50 bg-success/8 rounded-md border p-3 text-sm">
          <b className="font-semibold">Last operation:</b> {m.lastOpNote}
        </div>
      )}
      <div className="grid items-start gap-3.5 lg:grid-cols-3">
        <OpCard icon={RefreshCw} title="Re-embed" count={`fp: ${m.fingerprint}`}>
          <Op
            name="memories"
            meta={
              m.reembed.memories > 0
                ? `${m.reembed.memories} missing a vector`
                : "0 missing — nothing to backfill"
            }
            help="Backfills memories with no row under the active fingerprint. Runs in the background; POST returns 202 immediately."
          >
            <ConfirmGate
              tone="primary"
              disabled={m.reembed.memories === 0}
              trigger={
                <Button
                  size="sm"
                  variant="outline"
                  className="border-primary/60 text-primary"
                  disabled={m.reembed.memories === 0}
                  tabIndex={-1}
                >
                  <Zap className="mr-1.5 size-3.5" />
                  Re-embed memories
                </Button>
              }
              headline={`Re-embed ${m.reembed.memories} memories now?`}
              desc="Dispatches embedding calls to the live embedding-purpose LLM. Not destructive — existing vectors under other fingerprints are left alone — but it cannot be cancelled once started, only blocked from a second concurrent run on this category (409 already_running)."
              confirmLabel="Confirm — start re-embed"
              onConfirm={() => m.run("reembed_memories")}
            />
          </Op>
          <Op
            name="entities"
            meta={
              m.reembed.entities > 0
                ? `${m.reembed.entities} missing`
                : "0 missing"
            }
          >
            <ConfirmGate
              tone="primary"
              disabled={m.reembed.entities === 0}
              trigger={
                <Button
                  size="sm"
                  variant="outline"
                  disabled={m.reembed.entities === 0}
                  tabIndex={-1}
                >
                  Re-embed entities
                </Button>
              }
              headline={`Re-embed ${m.reembed.entities} entities now?`}
              desc="Dispatches embedding calls to the live embedding-purpose LLM. Not destructive, but it cannot be cancelled once started."
              confirmLabel="Confirm — start re-embed"
              onConfirm={() => m.run("reembed_entities")}
            />
          </Op>
          {m.codeChunksReembedAvailable ? (
            <Op
              name="code_chunks"
              meta={
                m.reembed.codeChunks > 0
                  ? `${m.reembed.codeChunks} missing`
                  : "0 missing"
              }
              help="Backfills code chunks with no row under the active fingerprint. Runs in the background; POST returns 202 immediately."
              last
            >
              <ConfirmGate
                tone="primary"
                disabled={m.reembed.codeChunks === 0}
                trigger={
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={m.reembed.codeChunks === 0}
                    tabIndex={-1}
                  >
                    Re-embed code chunks
                  </Button>
                }
                headline={`Re-embed ${m.reembed.codeChunks} code chunks now?`}
                desc="Dispatches embedding calls to the live embedding-purpose LLM. Not destructive, but it cannot be cancelled once started."
                confirmLabel="Confirm — start re-embed"
                onConfirm={() => m.run("reembed_code_chunks")}
              />
            </Op>
          ) : (
            <Op
              name="code_chunks"
              meta={`${m.reembed.codeChunks} missing`}
              help="Cross-fingerprint code-chunk backfill is not implemented server-side — POST /reembed/code-chunks returns 202 but ReembedService.reembed_code_chunks never embeds anything and reports every row as an error. The button is disabled and points at a full repository reindex instead, rather than wiring a trigger that structurally cannot succeed."
              last
            >
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" disabled>
                  Re-embed code chunks
                </Button>
                <IllustrativeTag label="use Repositories → Reindex" />
              </div>
            </Op>
          )}
        </OpCard>

        <OpCard
          icon={Trash2}
          title="Cleanup ops"
          count={`${m.cleanup.failuresMemoryIngest + m.cleanup.failuresCodeRepo} unresolved failures`}
        >
          <Op name="expired_memory_cleanup" meta={expiredMeta} help={expiredHelp}>
            <ConfirmGate
              tone="danger"
              disabled={m.cleanup.expired === 0}
              trigger={
                <Button
                  size="sm"
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
            name="graph_orphan_cleanup"
            meta="on schedule"
            help="Deletes entities no live memory asserts and no surviving relation references (FK-cascade-safe)."
          >
            <ConfirmGate
              tone="danger"
              trigger={
                <Button
                  size="sm"
                  variant="outline"
                  className="border-warning/60 text-warning"
                  tabIndex={-1}
                >
                  Run now
                </Button>
              }
              headline="Run graph_orphan_cleanup now?"
              desc="Deletes entities no live memory asserts and no surviving relation references — the FK cascades, so a referenced entity is never touched. Same job the hourly schedule already runs."
              confirmLabel="Confirm — run now"
              onConfirm={() => m.run("graph_orphan_cleanup")}
            />
          </Op>
          <Op
            name="tag_orphan_cleanup"
            meta="on schedule"
            help="Deletes tags no live memory carries any more."
          >
            <ConfirmGate
              tone="danger"
              trigger={
                <Button
                  size="sm"
                  variant="outline"
                  className="border-warning/60 text-warning"
                  tabIndex={-1}
                >
                  Run now
                </Button>
              }
              headline="Run tag_orphan_cleanup now?"
              desc="Deletes tags no live memory carries any more. Same job the hourly schedule already runs — this button just runs it now."
              confirmLabel="Confirm — run now"
              onConfirm={() => m.run("tag_orphan_cleanup")}
            />
          </Op>
          <Op
            name="unresolved pipeline failures"
            meta={`${m.cleanup.failuresMemoryIngest} memory_ingest · ${m.cleanup.failuresCodeRepo} code_repo`}
            help="The full retry worklist lives at Activity → Triage; this is a count and a shortcut, not a second copy of that list."
            last
          >
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" asChild>
                <Link to="/activity" search={{ tab: "triage", day: undefined }}>
                  <ExternalLink className="mr-1.5 size-3.5" />
                  View in Activity
                </Link>
              </Button>
            </div>
          </Op>
        </OpCard>

        <OpCard icon={Database} title="DB ops">
          <Op
            name="prune obsolete caches"
            meta={
              m.dbops.retiredFingerprints === null
                ? "not enumerated ahead of time"
                : m.dbops.retiredFingerprints.length > 0
                  ? `${m.dbops.retiredFingerprints.length} retired fingerprints`
                  : "none retired"
            }
            help={
              m.dbops.retiredFingerprints === null
                ? "Drops entity_embedding_cache child tables for every fingerprint except the active one. POST /reembed/prune-cache does not enumerate which fingerprints are retired ahead of a run — it drops whatever it finds and reports the count afterward."
                : m.dbops.retiredFingerprints.length > 0
                  ? `Drops entity_embedding_cache child tables for every fingerprint except the active one: ${m.dbops.retiredFingerprints.join(", ")}.`
                  : "No retired embedder caches to prune."
            }
          >
            <ConfirmGate
              tone="danger"
              disabled={m.dbops.retiredFingerprints?.length === 0}
              trigger={
                <Button
                  size="sm"
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
                  ? "Prune retired embedder caches now?"
                  : `Drop ${m.dbops.retiredFingerprints.length} retired cache tables now?`
              }
              desc="DROP TABLE, irreversible. Each cache rebuilds lazily the next time its embedder is used, but any current hit-rate savings on those fingerprints are lost immediately."
              confirmLabel="Confirm — drop tables"
              onConfirm={() => m.run("prune_caches")}
            />
          </Op>
          <Op
            name="VACUUM ANALYZE"
            meta={m.dbops.vacuumTarget}
            help={m.dbops.vacuumNote}
          >
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" disabled>
                Run now
              </Button>
              <IllustrativeTag label="no dedicated endpoint yet" />
            </div>
          </Op>
          <Op
            name="REINDEX"
            meta={m.dbops.reindexTarget}
            help={m.dbops.reindexNote}
            last
          >
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" disabled>
                Run now
              </Button>
              <IllustrativeTag label="no dedicated endpoint yet" />
            </div>
          </Op>
        </OpCard>
      </div>
    </div>
  )
}
