import { useEffect, useState } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
import { toast } from "darkraise-ui/components/sonner"

import { EmptyState, HelpTip, NumberField } from "@/components/darkmem"
import { Search } from "lucide-react"
import { SettingsCard } from "./settings-card"
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
  // Its own mutation, so a refused arm is not reported as a refused budget.
  const arm = useUpdateAutoResearch()
  const runs = useResearchRuns()
  const rerun = useRerunResearchRun()
  // Numbers, not strings: the old text inputs sent Number("") = 0 for an
  // unread config and NaN for "abc". NumberField reports NaN for text it
  // cannot parse, and that is refused below rather than written.
  const [findings, setFindings] = useState<number>(NaN)
  const [chars, setChars] = useState<number>(NaN)

  useEffect(() => {
    if (config.data) {
      setFindings(config.data.max_findings_per_run)
      setChars(config.data.max_content_chars)
    }
  }, [config.data])

  // `config.data?.enabled ?? false` would render "disarmed" before the read
  // returns — a surface asserting a posture it has not read yet. The loop
  // being off is the shipped default, but *this install's* state is unknown
  // until the row answers, and those are different claims.
  const known = config.data !== undefined
  const enabled = config.data?.enabled ?? false
  // The server's own ceilings, so the range shown is the range it enforces;
  // the fallbacks are its values for a payload that predates the fields.
  const findingsMax = config.data?.max_findings_per_run_ceiling ?? 100
  const charsMax = config.data?.max_content_chars_ceiling ?? 100_000
  const findingsError = known ? budgetError(findings, findingsMax) : null
  const charsError = known ? budgetError(chars, charsMax) : null
  const budgetsValid = findingsError === null && charsError === null

  if (config.isError && !known) {
    return (
      <SettingsCard icon={Search} title="Auto research">
        <EmptyState
          kind="failed"
          title="The research settings could not be loaded"
          description={config.error.message}
          action={<Button onClick={() => void config.refetch()}>Retry</Button>}
        />
      </SettingsCard>
    )
  }

  return (
    <SettingsCard icon={Search} title="Auto research">
      <div className="space-y-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            size="sm"
            className={enabled ? "font-mono" : "border-dashed font-mono"}
          >
            {!known ? "reading…" : enabled ? "armed" : "disarmed"}
          </Badge>
          <Button
            variant="outline"
            disabled={!known || arm.isPending}
            onClick={() =>
              arm.mutate(
                { enabled: !enabled },
                {
                  // The button and badge read the stored row, so a refusal
                  // leaves them where they were; the toast says why.
                  onError: (error) =>
                    toast.error(
                      enabled ? "Not disarmed" : "Not armed",
                      { description: error.message },
                    ),
                },
              )
            }
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
            <Label className="text-muted-foreground text-sm">
              Max findings per run
            </Label>
            <NumberField
              aria-label="Max findings per run"
              value={findings}
              // No `max`: the field would clamp an over-range entry on blur,
              // the same silent change of number this form exists to refuse.
              min={1}
              step={1}
              disabled={!known}
              onValueChange={setFindings}
            />
            <BudgetHint error={findingsError} max={findingsMax} />
          </div>
          <div className="flex min-w-40 flex-1 flex-col gap-1">
            <Label className="text-muted-foreground text-sm">
              Max content characters
            </Label>
            <NumberField
              aria-label="Max content characters"
              value={chars}
              min={1}
              step={100}
              disabled={!known}
              onValueChange={setChars}
            />
            <BudgetHint error={charsError} max={charsMax} />
          </div>
        </div>

        <Button
          variant="outline"
          className="w-fit"
          // Gated on `known` too: before the read answers there is nothing
          // in the fields, and a save would write zeros over the budget.
          disabled={!known || !budgetsValid || update.isPending}
          onClick={() =>
            update.mutate(
              {
                max_findings_per_run: findings,
                max_content_chars: chars,
              },
              {
                onSuccess: (saved) =>
                  toast.success(
                    `Budgets saved: ${saved.max_findings_per_run.toLocaleString()} findings, ${saved.max_content_chars.toLocaleString()} characters`,
                  ),
              },
            )
          }
        >
          {update.isPending ? "Saving…" : "Save budgets"}
        </Button>

        {update.isError && (
          <p className="text-destructive-text text-sm">
            not saved — {update.error.message}
          </p>
        )}

        <div className="space-y-2 border-t pt-3.5">
          <div className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-sm">
            <span>Filed runs</span>
            <HelpTip label="About re-running">
              Re-derive reprocesses a run&apos;s memories. Nothing is fetched
              again.
            </HelpTip>
          </div>

          {runs.isError && (
            <EmptyState
              kind="failed"
              title="The run list could not be read"
              description={runs.error.message}
              action={
                <Button onClick={() => void runs.refetch()}>Retry</Button>
              }
            />
          )}
          {runs.data && runs.data.items.length === 0 && (
            <p className="text-muted-foreground text-sm">
              No research runs yet.
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
            <p className="text-destructive-text text-sm">
              not re-derived — {rerun.error.message}
            </p>
          )}
          {rerun.isSuccess && (
            <p className="text-muted-foreground text-sm">
              re-derived {rerun.data.reprocessed} of {rerun.data.filed} filed
              {rerun.data.missing - rerun.data.pending > 0 &&
                ` · ${rerun.data.missing - rerun.data.pending} no longer exist`}
              {rerun.data.pending > 0 &&
                ` · ${rerun.data.pending} still in the capture buffer`}
              {rerun.data.errors > 0 && ` · ${rerun.data.errors} failed`}
            </p>
          )}
        </div>
      </div>
    </SettingsCard>
  )
}

function budgetError(value: number, max: number): string | null {
  if (!Number.isInteger(value)) return "Enter a whole number."
  if (value < 1 || value > max)
    return `Enter a number from 1 to ${max.toLocaleString()}.`
  return null
}

// The allowed range is always visible; it turns into the error when the
// value leaves it, so the field never needs a second line for both.
function BudgetHint({ error, max }: { error: string | null; max: number }) {
  return error ? (
    <span className="text-destructive-text text-sm">{error}</span>
  ) : (
    <span className="text-muted-foreground text-xs">
      1 to {max.toLocaleString()}
    </span>
  )
}
