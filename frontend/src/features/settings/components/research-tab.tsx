import { useEffect, useState } from "react"
import { FlaskConical } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"

import { HelpTip } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import {
  useAutoResearch,
  useRerunResearchRun,
  useResearchRuns,
  useUpdateAutoResearch,
} from "@/hooks/api"

/**
 * The `auto_research` operator surface (T3.28, doc 09 §6).
 *
 * **Disarmed is a state, not an error.** A never-configured install refuses
 * every research run, and this renders that plainly rather than as a warning:
 * the loop being off is the shipped default and the correct posture until
 * someone decides otherwise.
 *
 * **Arming is an explicit act**, so the switch is a deliberate two-value
 * control rather than a toggle that fires on focus, and the copy says what
 * turning it on means.
 *
 * **The trigger is a re-derivation, not a re-run of the gathering.** The
 * owner ruled (2026-08-16) that the surface re-runs the subject of a
 * previously filed run — the one shape needing no gatherer in the tree.
 * Building it showed that re-*filing* is either impossible (a deleted
 * memory's evidence is gone; the journal keeps no finding text) or inert (a
 * surviving one re-files under its own origin, and corroboration counts
 * distinct origins). So the button re-derives: the run's surviving memories
 * go back through the pipeline, and the subject is recomputed under the
 * current taxonomy and extractor. Nothing is gathered, filed or counted
 * again, which is also why this may sit on REST at all.
 */
export function ResearchTab() {
  const config = useAutoResearch()
  const update = useUpdateAutoResearch()
  const runs = useResearchRuns()
  const rerun = useRerunResearchRun()
  const [findings, setFindings] = useState("")
  const [chars, setChars] = useState("")

  useEffect(() => {
    if (config.data) {
      setFindings(String(config.data.max_findings_per_run))
      setChars(String(config.data.max_content_chars))
    }
  }, [config.data])

  // `config.data?.enabled ?? false` would render "disarmed" before the read
  // returns — a surface asserting a posture it has not read yet. The loop
  // being off is the shipped default, but *this install's* state is unknown
  // until the row answers, and those are different claims.
  const known = config.data !== undefined
  const enabled = config.data?.enabled ?? false

  return (
    <ModuleSurface
      title="Auto research"
      state={config.isLoading ? "empty" : "populated"}
      meta={!known ? "reading…" : enabled ? "armed" : "disarmed"}
    >
      <div className="space-y-3.5">
        <div className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-sm">
          <FlaskConical aria-hidden className="h-4 w-4" />
          <span>
            The research loop files evidence an MCP agent gathered. It refuses
            every run while disarmed, which is the shipped default.
          </span>
          <HelpTip label="About auto research">
            Building the door is not arming the loop. The loop has no in-tree
            gatherer by design — a model without web access would invent
            sources — so the caller supplies the evidence through the
            `research_run` MCP tool. Arming this switch lets that tool run; it
            does not start anything on its own, and there is no schedule.
          </HelpTip>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            size="sm"
            className={enabled ? "font-mono" : "border-dashed font-mono"}
          >
            {config.isError
              ? "unreadable"
              : !known
                ? "reading…"
                : enabled
                  ? "armed"
                  : "disarmed"}
          </Badge>
          <Button
            size="sm"
            variant="outline"
            disabled={!known || update.isPending}
            onClick={() => update.mutate({ enabled: !enabled })}
          >
            {!known
              ? "Reading the current state…"
              : enabled
                ? "Disarm"
                : "Arm the research loop"}
          </Button>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <div className="flex min-w-40 flex-1 flex-col gap-1">
            <Label htmlFor="research-findings" className="text-muted-foreground text-sm">
              Max findings per run
            </Label>
            <Input
              id="research-findings"
              value={findings}
              onChange={(e) => setFindings(e.target.value)}
            />
          </div>
          <div className="flex min-w-40 flex-1 flex-col gap-1">
            <Label htmlFor="research-chars" className="text-muted-foreground text-sm">
              Max content characters
            </Label>
            <Input
              id="research-chars"
              value={chars}
              onChange={(e) => setChars(e.target.value)}
            />
          </div>
        </div>

        <Button
          size="sm"
          variant="outline"
          className="w-fit"
          disabled={update.isPending}
          onClick={() =>
            update.mutate({
              max_findings_per_run: Number(findings),
              max_content_chars: Number(chars),
            })
          }
        >
          {update.isPending ? "Saving…" : "Save budgets"}
        </Button>

        {update.isError && (
          <p className="text-destructive text-sm">
            not saved — {update.error.message}
          </p>
        )}
        {config.isError && (
          <p className="text-muted-foreground text-sm">
            the research config could not be read — a failed read, not a
            disarmed loop
          </p>
        )}

        <div className="space-y-2 border-t pt-3.5">
          <div className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-sm">
            <span>Filed runs</span>
            <HelpTip label="About re-running">
              Re-running re-derives, it does not re-gather. The run&apos;s
              memories go back through the pipeline, so entities, relations and
              facts are recomputed under the current taxonomy. No evidence is
              fetched, no row is filed and no origin is created, so
              corroboration counts are untouched. A run whose memories were
              deleted cannot be re-derived — the journal records what it filed,
              never the finding text.
            </HelpTip>
          </div>

          {runs.isError && (
            <p className="text-muted-foreground text-sm">
              the run list could not be read
            </p>
          )}
          {runs.data && runs.data.items.length === 0 && (
            <p className="text-muted-foreground text-sm">
              no research run has been filed on this install
            </p>
          )}

          {runs.data?.items.map((run) => (
            <div
              key={run.event_id}
              className="flex flex-wrap items-center justify-between gap-2 text-sm"
            >
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-medium">{run.subject}</span>
                <span className="text-muted-foreground font-mono text-xs">
                  {run.project} · {run.live}/{run.filed} live ·{" "}
                  {new Date(run.occurred_at).toLocaleDateString()}
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                // Nothing left to re-derive is a refusal, not a no-op run: the
                // button says why rather than posting a request the door will
                // decline.
                disabled={run.live === 0 || rerun.isPending}
                onClick={() =>
                  rerun.mutate({
                    eventId: run.event_id,
                    occurredAt: run.occurred_at,
                  })
                }
              >
                {run.live === 0 ? "Nothing to re-derive" : "Re-derive"}
              </Button>
            </div>
          ))}

          {rerun.isError && (
            <p className="text-destructive text-sm">
              not re-derived — {rerun.error.message}
            </p>
          )}
          {rerun.isSuccess && (
            <p className="text-muted-foreground text-sm">
              re-derived {rerun.data.reprocessed} of {rerun.data.filed} filed
              {rerun.data.missing > 0 && ` · ${rerun.data.missing} no longer exist`}
              {rerun.data.errors > 0 && ` · ${rerun.data.errors} failed`}
            </p>
          )}
        </div>
      </div>
    </ModuleSurface>
  )
}
