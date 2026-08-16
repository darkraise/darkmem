import { useEffect, useState } from "react"
import { FlaskConical } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"

import { HelpTip } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { useAutoResearch, useUpdateAutoResearch } from "@/hooks/api"

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
 * The trigger half of T3.28 is deliberately absent: a UI button cannot gather
 * evidence, and `research_run` is an MCP tool precisely because the caller
 * must be the gatherer. Adding a server-side gatherer to make a button work
 * is the shape doc 09 §6 refuses, so the shape of a UI trigger is an owner
 * decision this surface does not pre-empt.
 */
export function ResearchTab() {
  const config = useAutoResearch()
  const update = useUpdateAutoResearch()
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
      </div>
    </ModuleSurface>
  )
}
