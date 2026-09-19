import { useState, type ReactNode } from "react"
import {
  BadgeCheck,
  Crosshair,
  Flag,
  FolderGit2,
  Gauge,
  Network,
  Pencil,
  SlidersHorizontal,
  Tags,
  type LucideIcon,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { Checkbox } from "darkraise-ui/components/checkbox"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Spinner } from "darkraise-ui/components/spinner"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"
import { HelpTip, IconButton, NumberField } from "@/components/darkmem"
import { SurfaceStateChip } from "@/features/activity/components/module-surface"
import { armStatus, sourceLabel } from "@/demo/settings"
import type {
  DemoBehavioralFlag,
  DemoLadderParam,
  DemoRankArm,
  DemoTunable,
} from "@/features/settings/types"
import { ArmPill } from "./arm-pill"
import {
  SECTIONS,
  useFlagsTabBinding,
  type FlagsTabBinding,
} from "../use-flags-tab-binding"

/** In flight against the API.
 *
 *  Every write on this tab is a round-trip, and until it lands the control is
 *  showing a value the server has not confirmed. Silence there is what made
 *  the classification-mode toggle read as broken: it sat at its old value with
 *  nothing to say a save was happening. The slot is fixed-width so a row does
 *  not reflow when the spinner appears and disappears. */
function SavingMark({ saving }: { saving: boolean }) {
  return (
    <span
      className="inline-flex w-4 shrink-0 items-center justify-center"
      aria-hidden={!saving}
    >
      {saving && <Spinner size="sm" label="Saving" />}
    </span>
  )
}

/** The shell every section editor shares.
 *
 *  Mounted only while a section is being edited and keyed on the section, so
 *  the draft seeds fresh from the server's values on every open rather than
 *  needing a reset effect — the same discipline `PurposeDialog` follows.
 *
 *  The footer names what a save will write. That list is the point of editing
 *  in a dialog at all: the whole section leaves in one request, so the
 *  operator should be able to see the extent of it before committing rather
 *  than inferring it from which fields they happen to remember touching. */
function SectionDialog({
  title,
  description,
  dirty,
  saving,
  canSave = true,
  onOpenChange,
  onSave,
  children,
}: {
  title: string
  description: string
  /** Field names this save will write, in display order. */
  dirty: string[]
  saving: boolean
  canSave?: boolean
  onOpenChange: (open: boolean) => void
  onSave: () => void
  children: ReactNode
}) {
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">{children}</div>
        <div className="border-border flex flex-wrap items-center gap-2 border-t pt-3">
          {dirty.length > 0 ? (
            <span className="text-muted-foreground font-mono text-[10px]">
              one request will write: {dirty.join(", ")}
            </span>
          ) : (
            <span className="text-muted-foreground font-mono text-[10px] italic">
              nothing edited
            </span>
          )}
          <span className="flex-1" />
          <SavingMark saving={saving} />
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            className="border-primary/60"
            variant="outline"
            disabled={dirty.length === 0 || !canSave || saving}
            onClick={onSave}
          >
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** A boolean at rest. A disabled Switch would read as "you may not change
 *  this", which is the wrong sentence — the Edit button is where it changes. */
function BoolTag({ on }: { on: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase",
        on
          ? "border-primary/55 bg-primary/10 text-primary-text"
          : "border-border text-muted-foreground bg-muted/40 border-dashed",
      )}
    >
      {on ? "on" : "off"}
    </span>
  )
}

/** A number at rest, in the same slot its input occupies while editing. */
function ValueTag({ value, unit }: { value: number; unit?: string }) {
  return (
    <span className="text-foreground font-mono text-sm font-semibold whitespace-nowrap tabular-nums">
      {value}
      {unit && (
        <span className="text-muted-foreground ml-1 text-[10px] font-normal">
          {unit}
        </span>
      )}
    </span>
  )
}

function SourceTag({ source }: { source: DemoRankArm["source"] }) {
  return (
    <span
      className={cn(
        "font-mono text-[10px] whitespace-nowrap",
        source === "default"
          ? "text-muted-foreground italic"
          : "text-primary-text/80",
      )}
    >
      ({sourceLabel(source)})
    </span>
  )
}

/** No entry in the gate-ledger's "Arm activation log" — flipping this arm
 *  is possible, but visibly unmeasured rather than quietly assumed good
 *  (T1.57 ruling 3, doc 17).
 *
 *  The badge carries its own explanation because the word alone reads as a
 *  warning about the control rather than about the evidence: nothing here is
 *  broken or disabled, and the operator is allowed to flip it. */
function UnmeasuredTag() {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label="About the unmeasured badge"
          className="border-warning/50 text-warning-text cursor-help rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase"
        >
          unmeasured
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          No entry in the gate ledger's "Arm activation log" — nobody has
          measured whether turning this on helps retrieval, and at what latency
          and token cost. It is not broken and not locked: you can flip it. The
          badge exists so that turning it on is a deliberate experiment rather
          than something quietly assumed proven. It clears on its own once a
          measurement lands in the `flag_measurements` config row, which is read
          from the backend rather than hardcoded here.
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/** What the ladder is actually running at, versus what was asked for. The
 *  state word is the point: a clamped threshold looks exactly like a saved one
 *  unless the difference is rendered. */
function LadderStatePill({ param }: { param: DemoLadderParam }) {
  const help: Record<DemoLadderParam["state"], string> = {
    default: `Nothing is committed for this threshold, so the ladder runs at its shipped floor of ${param.floor}.`,
    honoured: `The committed value of ${param.committed} is what the ladder runs at. Tightening a threshold — asking for more evidence — never needs permission.`,
    clamped:
      param.note ??
      `The committed value is not what the ladder runs at; it is running at ${param.effective}.`,
  }
  const clamped = param.state === "clamped"
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label={`About the ${param.state} state`}
          className={cn(
            "inline-flex cursor-help items-center rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase",
            clamped
              ? "border-warning/60 bg-warning/10 text-warning-text"
              : param.state === "honoured"
                ? "border-primary/55 bg-primary/10 text-primary-text"
                : "border-border text-muted-foreground bg-muted/40 border-dashed",
          )}
        >
          {param.state}
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          {help[param.state]}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function ActivationNote({ taskId }: { taskId?: string }) {
  if (!taskId) return null
  return (
    <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
      activated by <span className="font-semibold">{taskId}</span>
    </span>
  )
}

/** Blur/Enter-commit numeric field — a keystroke is not yet an edit. */
function ArmInput({
  arm,
  value,
  onChange,
  className,
}: {
  arm: DemoRankArm
  value: number
  onChange: (value: number) => void
  className?: string
}) {
  const [draft, setDraft] = useState(value)
  // Follow the value when it changes from outside this field — a dialog
  // reopening on fresh server data, a sibling control. Without it the draft is
  // initial-value-only and the next blur writes the stale number back.
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    setSeen(value)
    setDraft(value)
  }
  const commit = () => {
    // NaN is what the field reports for text it cannot parse, and is the case
    // a raw number input used to collapse into a committed zero.
    if (Number.isFinite(draft) && draft !== value) onChange(draft)
    else setDraft(value)
  }
  return (
    <NumberField
      step={arm.step ?? 1}
      value={draft}
      aria-label={arm.key}
      onValueChange={setDraft}
      onBlur={commit}
      onKeyDown={(e) => e.key === "Enter" && commit()}
      className={cn("w-24", className)}
    />
  )
}

/** One ranking arm.
 *
 *  The same row renders at rest and under edit, so the two cannot disagree
 *  about what an arm is — which help text it carries, which badges apply.
 *  Only the value slot changes: a number, or the input that edits it. */
function ArmRow({
  arm,
  help,
  draft,
  onChange,
}: {
  arm: DemoRankArm
  help?: string
  /** Present only inside a dialog. Absent means read-only. */
  draft?: number
  onChange?: (value: number) => void
}) {
  const editing = draft !== undefined && onChange !== undefined
  const shown = editing ? draft : arm.value
  return (
    <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <span className="font-mono text-sm font-semibold whitespace-nowrap">
        {arm.key}
      </span>
      {arm.alias && (
        <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
          {arm.alias}
        </span>
      )}
      <HelpTip label={`About ${arm.key}`}>{help ?? arm.desc}</HelpTip>
      <span className="flex-1" />
      <ActivationNote taskId={arm.activatesWith} />
      <SourceTag source={arm.source} />
      {editing ? (
        <ArmInput arm={arm} value={draft} onChange={onChange} />
      ) : (
        <ValueTag value={arm.value} />
      )}
      <ArmPill value={shown} />
      {arm.unmeasured && <UnmeasuredTag />}
    </div>
  )
}

/** One card of controls.
 *
 *  Each section is its own card rather than a band inside one long surface.
 *  Eight bands in a single card read as one list however they are ruled: the
 *  separator has to compete with the row borders inside every band, and it
 *  loses. A card boundary does not compete — it is the same affordance the
 *  rest of the app already uses to say "this is a distinct thing".
 *
 *  `meta` is the section's own one-line summary, right-aligned so each card
 *  carries a second anchor for scanning. */
function Section({
  icon: Icon,
  name,
  help,
  meta,
  onEdit,
  saving,
  children,
}: {
  icon: LucideIcon
  name: string
  help?: string
  meta?: ReactNode
  /** Omitted for a section with nothing to edit. */
  onEdit?: () => void
  saving?: boolean
  children: ReactNode
}) {
  return (
    <Card className="gap-0 py-0">
      {/* One row, always. Wrapping put the summary under the title on the
          longer names, which cost the header its scan line — the eye stops
          finding the meta in the same place on every card. The title truncates
          instead; nothing here is so long that its tail carries meaning the
          help tip does not. */}
      {/* `flex-row space-y-0` are not redundant: the library's `.dr-card-header`
          is `flex flex-col space-y-1`, so setting only `flex-nowrap` left the
          children stacked in a column — a header three lines tall that still
          reported `display: flex` and `flex-wrap: nowrap`. */}
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        {/* `text-primary-text`, not `text-accent`: in this theme `--accent` is the
            near-white hover surface (210 40% 96%) and `--primary` is the brand
            colour the library's own comment calls the accent source. An icon
            on `text-accent` would be all but invisible on the header. */}
        <Icon aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 truncate font-mono text-[11px] font-semibold tracking-[0.14em] uppercase">
          {name}
        </h3>
        {help && (
          <span className="shrink-0">
            <HelpTip label={`About ${name}`}>{help}</HelpTip>
          </span>
        )}
        <span className="flex-1" />
        {meta && (
          <span className="text-muted-foreground shrink-0 font-mono text-[10px] whitespace-nowrap">
            {meta}
          </span>
        )}
        {onEdit && (
          <>
            <SavingMark saving={saving ?? false} />
            <IconButton
              icon={Pencil}
              label={`Edit ${name}`}
              variant="outline"
              className="shrink-0"
              disabled={saving}
              onClick={onEdit}
            />
          </>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2 p-4">{children}</CardContent>
    </Card>
  )
}

function BehavioralFlagRow({
  flag,
  draft,
  onChange,
}: {
  flag: DemoBehavioralFlag
  draft?: boolean
  onChange?: (enabled: boolean) => void
}) {
  const editing = draft !== undefined && onChange !== undefined
  return (
    <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <span className="font-mono text-sm font-semibold whitespace-nowrap">
        {flag.key}
      </span>
      <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
      <span className="flex-1" />
      <SourceTag source={flag.source} />
      {editing ? (
        <Switch
          checked={draft}
          onCheckedChange={onChange}
          aria-label={flag.key}
        />
      ) : (
        <BoolTag on={flag.enabled} />
      )}
      {flag.unmeasured && <UnmeasuredTag />}
    </div>
  )
}

/** A bounded integer knob. Separate from `ArmRow` because it carries no
 *  active/inactive state — 0 is out of range rather than a no-op, so an
 *  `ArmPill` here would label a throughput setting as a dormant ranking
 *  signal. */
function TunableRow({
  tunable,
  draft,
  onChange,
}: {
  tunable: DemoTunable
  draft?: number
  onChange?: (value: number) => void
}) {
  const editing = draft !== undefined && onChange !== undefined
  return (
    <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <span className="font-mono text-sm font-semibold whitespace-nowrap">
        {tunable.key}
      </span>
      <HelpTip label={`About ${tunable.key}`}>
        {tunable.desc}. Accepted range {tunable.min}–{tunable.max}; the coded
        default is {tunable.coded_default}.
      </HelpTip>
      <span className="flex-1" />
      <SourceTag source={tunable.source} />
      {editing ? (
        <TunableInput tunable={tunable} value={draft} onChange={onChange} />
      ) : (
        <ValueTag value={tunable.value} unit={tunable.unit} />
      )}
    </div>
  )
}

function TunableInput({
  tunable,
  value,
  onChange,
}: {
  tunable: DemoTunable
  value: number
  onChange: (value: number) => void
}) {
  const [draft, setDraft] = useState(value)
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    setSeen(value)
    setDraft(value)
  }
  const commit = () => {
    // Clamped to the API's own bound so the field refuses locally exactly what
    // the request would 422 on — and so one out-of-range field cannot fail the
    // whole section's single write.
    const clamped = Math.min(Math.max(draft, tunable.min), tunable.max)
    if (Number.isFinite(draft) && clamped !== value) onChange(clamped)
    else setDraft(value)
  }
  return (
    <div className="flex items-center gap-2">
      <NumberField
        step={1}
        min={tunable.min}
        max={tunable.max}
        value={draft}
        aria-label={tunable.key}
        onValueChange={setDraft}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
        className="w-24"
      />
      {tunable.unit && (
        <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
          {tunable.unit}
        </span>
      )}
    </div>
  )
}

/** Mirrors `CodeBucketsUnavailable` in llm-tab.tsx: no backend row exists
 *  for this yet, in either mode, so the honest move is a staged note rather
 *  than fetching against a guessed contract (the T1.61 buffer-monitor
 *  precedent) or silently omitting the section (invariant 23). */
function NotYetImplemented({ label, note }: { label: string; note: string }) {
  return (
    <div className="border-inset text-muted-foreground flex flex-col gap-1 rounded-md border border-dashed px-3 py-2.5 text-sm">
      <span className="font-mono text-[10px] tracking-wide uppercase">
        {label}
      </span>
      <span>{note}</span>
    </div>
  )
}

function RepoAllowlistSection({ binding }: { binding: FlagsTabBinding }) {
  const [editing, setEditing] = useState(false)
  const saving = binding.isSaving(SECTIONS.allowlist)
  const patterns = binding.allowlistPatterns

  return (
    <>
      <Section
        icon={FolderGit2}
        name="repo auto-provision allowlist"
        help="Repo hints arrive over the unauthenticated MCP door; an empty allowlist refuses every hint (auto-provision inert). Patterns are host, *.host, or host/path-prefix — validated with the exact parse the SSRF gate itself runs a pattern through, so this editor and the gate can never disagree on 'allowed'."
        meta={
          patterns.length === 0
            ? "empty — every hint refused"
            : `${patterns.length} pattern${patterns.length === 1 ? "" : "s"}`
        }
        onEdit={() => setEditing(true)}
        saving={saving}
      >
        {patterns.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Empty today — every repo hint is refused until at least one pattern
            is saved.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {patterns.map((pattern) => (
              <code
                key={pattern}
                className="border-inset bg-muted/40 rounded-md border px-2 py-0.5 font-mono text-[11px]"
              >
                {pattern}
              </code>
            ))}
          </div>
        )}
      </Section>
      {editing && (
        <AllowlistDialog
          binding={binding}
          saving={saving}
          onOpenChange={setEditing}
        />
      )}
    </>
  )
}

function AllowlistDialog({
  binding,
  saving,
  onOpenChange,
}: {
  binding: FlagsTabBinding
  saving: boolean
  onOpenChange: (open: boolean) => void
}) {
  const committed = binding.allowlistPatterns
  const [draft, setDraft] = useState(committed.join("\n"))
  const patterns = draft
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean)
  const dirty = patterns.join("\n") !== committed.join("\n") ? ["patterns"] : []

  return (
    <SectionDialog
      title="repo_allowlist"
      description="One pattern per line. Host, *.host, or host/path-prefix — each validated with the same parse the SSRF gate runs, so this editor and the gate cannot disagree on 'allowed'."
      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveAllowlist(patterns)
        onOpenChange(false)
      }}
    >
      <Textarea
        value={draft}
        aria-label="repo_allowlist patterns"
        onChange={(e) => setDraft(e.target.value)}
        rows={6}
        className="font-mono text-sm"
      />
      <p className="text-muted-foreground text-sm">
        e.g. <code className="font-mono">github.com/darkraise/*</code> or{" "}
        <code className="font-mono">*.forge.internal.example</code>. Saving an
        empty list leaves auto-provision inert — every hint refused.
      </p>
    </SectionDialog>
  )
}

const LADDER_PARAM_HELP: Record<string, string> = {
  n_default:
    "How many DISTINCT origin_keys a fact needs before it climbs candidate → corroborated in the ordinary case, with no diversity gate fired. Counting is over distinct origins, never over rows: one memory asserting a claim twice is one origin.",
  n_diverse:
    "The lowered bar when the diversity gate fires — two attributable origins that differ in source-kind, or that lie at least the time-gap apart. It must never exceed the default bar, or firing a gate would make promotion harder.",
  time_gap_days:
    "How far apart two same-kind attributable origins must lie for the diversity gate to fire on time rather than on source-kind. Below this spacing, two origins of one kind stay at the default bar.",
}

/** The promotion gate at rest: what each threshold is committed to and what
 *  the ladder is actually running at, which are not always the same number. */
function CorroborationSection({ binding }: { binding: FlagsTabBinding }) {
  const [editing, setEditing] = useState(false)
  const saving = binding.isSaving(SECTIONS.ladder)
  const corr = binding.corroboration
  const clamped = corr.params.filter((p) => p.state === "clamped")

  return (
    <>
      <Section
        icon={BadgeCheck}
        name="corroboration promotion gate"
        meta={
          clamped.length > 0
            ? `${clamped.length} clamped`
            : corr.rowPresent
              ? "tuned"
              : "all at shipped floors"
        }
        help={`The candidate → corroborated rung of the verification ladder. ${corr.gate_note} These three numbers are FLOORS, not settings: tightening one (asking for more evidence) is always honoured, while loosening one below its shipped default is honoured only for a parameter named by a recorded ${corr.measurementTask} measurement — otherwise it is clamped back and the row says so. The contradiction veto is absolute and reads none of this: one non-echo contradiction beats any count.`}
        onEdit={
          binding.corroborationAvailable ? () => setEditing(true) : undefined
        }
        saving={saving}
      >
        {binding.corroborationAvailable ? (
          <>
            {corr.params.map((param) => (
              <div
                key={param.name}
                className="border-inset bg-card flex flex-col gap-2 rounded-md border px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-mono text-sm font-semibold whitespace-nowrap">
                    {param.name}
                  </span>
                  <HelpTip label={`About ${param.name}`}>
                    {LADDER_PARAM_HELP[param.name] ?? param.name}
                    {" The shipped floor is "}
                    {param.floor}
                    {param.measured
                      ? `, and a recorded ${corr.measurementTask} measurement licenses this parameter below it.`
                      : `, and no ${corr.measurementTask} measurement licenses going below it.`}
                  </HelpTip>
                  <span className="flex-1" />
                  {param.committed !== null &&
                    param.committed !== param.effective && (
                      <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
                        asked for {param.committed}
                      </span>
                    )}
                  <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
                    running at
                  </span>
                  <ValueTag value={param.effective} />
                  <LadderStatePill param={param} />
                </div>
                {param.state === "clamped" && param.note && (
                  <p className="text-warning-text pl-0.5 text-sm">{param.note}</p>
                )}
              </div>
            ))}
            {clamped.length === 0 && !corr.rowPresent && (
              <p className="text-muted-foreground pl-0.5 text-sm italic">
                No config row — every threshold is at its shipped floor.
              </p>
            )}
          </>
        ) : (
          <NotYetImplemented
            label="n_default · n_diverse · time_gap_days"
            note="Could not read /config/verification-ladder — the thresholds are still enforced at whatever the config row resolves to; only this editor is unavailable."
          />
        )}
      </Section>
      {editing && (
        <LadderDialog
          binding={binding}
          saving={saving}
          onOpenChange={setEditing}
        />
      )}
    </>
  )
}

function LadderDialog({
  binding,
  saving,
  onOpenChange,
}: {
  binding: FlagsTabBinding
  saving: boolean
  onOpenChange: (open: boolean) => void
}) {
  const corr = binding.corroboration
  // The box holds what was *asked for*, so an operator sees and corrects their
  // own edit; a clamped threshold's effective value is rendered beside it
  // rather than overwriting it.
  const committed = Object.fromEntries(
    corr.params.map((p) => [p.name, p.committed]),
  ) as Record<string, number | null>
  const [draft, setDraft] = useState<Record<string, number | null>>(committed)

  const dirty = corr.params
    .filter((p) => draft[p.name] !== committed[p.name])
    .map((p) => p.name)

  return (
    <SectionDialog
      title="corroboration promotion gate"
      description={`Floors, not settings. Tightening is always honoured; loosening below a floor is honoured only for a parameter named by a recorded ${corr.measurementTask} measurement, and is otherwise clamped back — the row will say so after saving.`}
      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveLadder(
          Object.fromEntries(dirty.map((name) => [name, draft[name] ?? null])),
        )
        onOpenChange(false)
      }}
    >
      {corr.params.map((param) => (
        <div
          key={param.name}
          className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2"
        >
          <span className="font-mono text-sm font-semibold whitespace-nowrap">
            {param.name}
          </span>
          <HelpTip label={`About ${param.name}`}>
            {LADDER_PARAM_HELP[param.name] ?? param.name}
            {" The shipped floor is "}
            {param.floor}.
          </HelpTip>
          <span className="flex-1" />
          <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
            floor {param.floor}
          </span>
          <ArmInput
            arm={{
              key: param.name,
              desc: "",
              value: draft[param.name] ?? param.floor,
              coded_default: param.floor,
              source: draft[param.name] === null ? "default" : "override",
              step: 1,
            }}
            value={draft[param.name] ?? param.floor}
            onChange={(v) => setDraft((d) => ({ ...d, [param.name]: v }))}
            className="w-20"
          />
          <Button
            variant="ghost"
            className="text-muted-foreground font-mono text-[10px]"
            disabled={draft[param.name] === null}
            onClick={() => setDraft((d) => ({ ...d, [param.name]: null }))}
          >
            reset to floor
          </Button>
        </div>
      ))}
    </SectionDialog>
  )
}

/** One label the classifier may emit, with its description on hover. */
function LabelChip({
  label,
  muted = false,
}: {
  label: { name: string; description?: string }
  muted?: boolean
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label={`About the ${label.name} label`}
          className={cn(
            "cursor-help rounded-full border px-2 py-0.5 font-mono text-[11px] whitespace-nowrap",
            muted
              ? "border-border/60 text-muted-foreground border-dashed"
              : "border-border bg-muted/40 text-foreground/90",
          )}
        >
          {label.name}
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          {label.description ??
            "Served with its description once this area is enabled."}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/** Mode, areas and the resulting label space, rendered as the one chain they
 *  actually are: the mode decides whether the areas are read, and each area is
 *  what puts particular labels in the list. Read-only here; the Edit dialog
 *  carries the same rows with their controls live, and saves mode and areas in
 *  one request. */
function ClassificationSection({ binding }: { binding: FlagsTabBinding }) {
  const [editing, setEditing] = useState(false)
  const saving = binding.isSaving(SECTIONS.classification)
  const simple = binding.classificationMode === "simple"
  const selected = new Set(binding.classificationAreas)

  const unowned = binding.classificationLabels.filter((l) => l.area === null)
  const byArea = new Map<string, typeof binding.classificationLabels>()
  for (const label of binding.classificationLabels) {
    if (label.area === null) continue
    byArea.set(label.area, [...(byArea.get(label.area) ?? []), label])
  }

  return (
    <>
      <Section
        icon={Tags}
        name="classification"
        help="Classification always runs — there is no on/off flag, only which model-backed classifier serves the purpose (set on the LLM tab via classifier_kind). What these controls decide is the label space: the exact set of values the classifier may write to a memory's classified_type. Anything the model emits outside that set is normalised back into it."
        meta={`${binding.classificationMode} · ${binding.classificationLabels.length} labels`}
        onEdit={() => setEditing(true)}
        saving={saving}
      >
        <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
          <span className="font-mono text-sm font-semibold whitespace-nowrap">
            classification_mode
          </span>
          <HelpTip label="About classification_mode">
            `simple` keeps the seven-type vocabulary extraction already emits,
            which lets the pipeline fold classification into the single
            extraction call instead of a second LLM round-trip. `expanded` opens
            the per-area label space and forces two concurrent calls. The mode
            also changes the extraction prompt, so re-extracting the same
            content under a different mode is not bit-identical.
          </HelpTip>
          <span className="flex-1" />
          <span className="border-primary/55 bg-primary/10 text-primary-text rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase">
            {binding.classificationMode}
          </span>
        </div>

        <p className="text-muted-foreground pl-0.5 text-sm">
          {simple ? (
            <>
              In <span className="font-mono">simple</span> mode the label space
              is <b className="text-foreground font-semibold">fixed</b>: the
              classification areas are{" "}
              <b className="text-warning-text font-semibold">not read at all</b>, so
              they are hidden here rather than shown as settings that do
              nothing. Edit and switch to{" "}
              <span className="font-mono">expanded</span> to configure them.
            </>
          ) : (
            <>
              In <span className="font-mono">expanded</span> mode the label
              space is <span className="font-mono">fact</span> plus the union of
              every enabled area below. Each area contributes the labels shown
              on its row.
            </>
          )}
        </p>

        <div className="border-inset bg-card flex flex-col gap-2.5 rounded-md border px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-sm font-semibold whitespace-nowrap">
              label space
            </span>
            <HelpTip label="About the label space">
              Exactly the values the classifier may write to a memory's
              `classified_type`, resolved by the backend's own merge function
              rather than re-derived here. Note nothing downstream filters or
              ranks on this column today — it is served on the memory detail
              view.
            </HelpTip>
            <span className="flex-1" />
            <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
              {binding.classificationLabels.length} label
              {binding.classificationLabels.length === 1 ? "" : "s"}
              {!simple && (
                <>
                  {" · "}
                  {binding.classificationAreas.length} of{" "}
                  {binding.availableAreas.length} areas enabled
                </>
              )}
            </span>
          </div>

          {unowned.length > 0 && (
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-muted-foreground w-32 shrink-0 font-mono text-[10px] tracking-wide uppercase">
                {simple ? "fixed vocabulary" : "always"}
              </span>
              <div className="flex flex-1 flex-wrap gap-1.5">
                {unowned.map((label) => (
                  <LabelChip key={label.name} label={label} />
                ))}
              </div>
            </div>
          )}

          {!simple &&
            binding.availableAreas
              .filter((area) => selected.has(area.key))
              .map((area) => {
                const contributed = byArea.get(area.key) ?? []
                return (
                  <div
                    key={area.key}
                    className="border-border/50 flex flex-wrap items-baseline gap-2 border-t border-dashed pt-2"
                  >
                    <span className="w-32 shrink-0 truncate text-sm">
                      {area.display_name}
                    </span>
                    <div className="flex flex-1 flex-wrap items-baseline gap-1.5">
                      {contributed.length > 0 ? (
                        contributed.map((label) => (
                          <LabelChip key={label.name} label={label} />
                        ))
                      ) : (
                        <span className="text-muted-foreground text-sm italic">
                          contributes nothing — every name it defines is already
                          owned by another enabled area
                        </span>
                      )}
                    </div>
                    <span className="text-muted-foreground w-10 shrink-0 text-right font-mono text-[10px]">
                      +{contributed.length}
                    </span>
                  </div>
                )
              })}
        </div>
      </Section>
      {editing && (
        <ClassificationDialog
          binding={binding}
          saving={saving}
          onOpenChange={setEditing}
        />
      )}
    </>
  )
}

function ClassificationDialog({
  binding,
  saving,
  onOpenChange,
}: {
  binding: FlagsTabBinding
  saving: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [mode, setMode] = useState(binding.classificationMode)
  const [areas, setAreas] = useState<string[]>(binding.classificationAreas)
  const simple = mode === "simple"
  const selected = new Set(areas)

  const dirty: string[] = []
  if (mode !== binding.classificationMode) dirty.push("classification_mode")
  if (
    [...areas].sort().join(",") !==
    [...binding.classificationAreas].sort().join(",")
  ) {
    dirty.push("classification_areas")
  }

  const toggle = (key: string, on: boolean) =>
    setAreas((current) =>
      on ? [...current, key] : current.filter((a) => a !== key),
    )

  return (
    <SectionDialog
      title="classification"
      description="The mode decides whether the areas are read at all; the enabled areas decide the label space in expanded mode. Both leave in one request."
      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        const patch: Record<string, unknown> = {}
        if (dirty.includes("classification_mode")) {
          patch.classification_mode = mode
        }
        if (dirty.includes("classification_areas")) {
          patch.classification_areas = areas
        }
        binding.saveFlags(SECTIONS.classification, patch)
        onOpenChange(false)
      }}
    >
      <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
        <span className="font-mono text-sm font-semibold whitespace-nowrap">
          classification_mode
        </span>
        <span className="flex-1" />
        <SegmentGroup
          value={mode}
          onValueChange={(v: string) => setMode(v as "simple" | "expanded")}
          aria-label="classification_mode"
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="simple">simple</SegmentGroupItem>
          <SegmentGroupItem value="expanded">expanded</SegmentGroupItem>
        </SegmentGroup>
      </div>

      {/* The area list follows the mode being *drafted*, not the mode that is
          saved: picking `simple` here is picking a fixed vocabulary, so the
          controls that shape a per-area one have nothing to say and go away
          with it. Keeping them visible-but-inert inside an editor was the
          same mistake the read-only card already stopped making. */}
      <p className="text-muted-foreground text-sm">
        {simple ? (
          <>
            <span className="font-mono">simple</span> uses a{" "}
            <b className="text-foreground font-semibold">fixed</b> nine-label
            vocabulary and{" "}
            <b className="text-warning-text font-semibold">does not read</b> the
            classification areas, so there is nothing to choose here. Pick{" "}
            <span className="font-mono">expanded</span> to bring them back —
            whatever was enabled before is preserved and will be saved with the
            mode.
          </>
        ) : (
          <>
            The label space will be <span className="font-mono">fact</span> plus
            the union of the areas ticked below.
          </>
        )}
      </p>

      {!simple && (
        <div className="grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
          {binding.availableAreas.map((area) => {
            const locked = area.key === "general"
            return (
              <label
                key={area.key}
                className="flex items-center gap-2 text-sm"
                htmlFor={`edit-area-${area.key}`}
              >
                <Checkbox
                  id={`edit-area-${area.key}`}
                  checked={selected.has(area.key)}
                  disabled={locked}
                  aria-label={area.key}
                  onCheckedChange={(c) => toggle(area.key, c === true)}
                />
                <span className={cn(locked && "text-muted-foreground")}>
                  {area.display_name}
                </span>
                <HelpTip label={`About the ${area.display_name} area`}>
                  {locked && "Always on — the base area. "}
                  Adds: {area.types.join(", ")}.
                </HelpTip>
              </label>
            )
          })}
        </div>
      )}
    </SectionDialog>
  )
}

/** The four `feature_flags` sections whose editors are a list of like rows.
 *
 *  One dialog component rather than four: the sections differ in which rows
 *  they carry, not in how an edit works, and four near-identical dialogs is
 *  four places for the dirty-tracking and the one-request save to drift. */
function FlagsSectionDialog({
  title,
  description,
  section,
  binding,
  arms,
  flags,
  tunables,
  onOpenChange,
}: {
  title: string
  description: string
  section: (typeof SECTIONS)[keyof typeof SECTIONS]
  binding: FlagsTabBinding
  arms?: DemoRankArm[]
  flags?: DemoBehavioralFlag[]
  tunables?: DemoTunable[]
  onOpenChange: (open: boolean) => void
}) {
  const committed: Record<string, number | boolean> = {}
  for (const arm of arms ?? []) committed[arm.key] = arm.value
  for (const flag of flags ?? []) committed[flag.key] = flag.enabled
  for (const tunable of tunables ?? []) committed[tunable.key] = tunable.value

  const [draft, setDraft] =
    useState<Record<string, number | boolean>>(committed)
  const dirty = Object.keys(committed).filter((k) => draft[k] !== committed[k])
  const set = (key: string, value: number | boolean) =>
    setDraft((d) => ({ ...d, [key]: value }))

  return (
    <SectionDialog
      title={title}
      description={description}
      dirty={dirty}
      saving={binding.isSaving(section)}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveFlags(
          section,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
        onOpenChange(false)
      }}
    >
      {(arms ?? []).map((arm) => (
        <ArmRow
          key={arm.key}
          arm={arm}
          draft={draft[arm.key] as number}
          onChange={(v) => set(arm.key, v)}
        />
      ))}
      {(flags ?? []).map((flag) => (
        <BehavioralFlagRow
          key={flag.key}
          flag={flag}
          draft={draft[flag.key] as boolean}
          onChange={(v) => set(flag.key, v)}
        />
      ))}
      {(tunables ?? []).map((tunable) => (
        <TunableRow
          key={tunable.key}
          tunable={tunable}
          draft={draft[tunable.key] as number}
          onChange={(v) => set(tunable.key, v)}
        />
      ))}
    </SectionDialog>
  )
}

/** Graph augmentation pairs a channel flag with its RRF list weight, so its
 *  editor carries both in one draft and one request — a flag turned on with
 *  its weight left at 0 produces candidates that fuse at zero weight, and
 *  saving the two separately is what made that easy to do by accident. */
function GraphDialog({
  binding,
  onOpenChange,
}: {
  binding: FlagsTabBinding
  onOpenChange: (open: boolean) => void
}) {
  const committed: Record<string, number | boolean> = {}
  for (const flag of binding.graphFlags) {
    committed[flag.key] = flag.enabled
    if (flag.paired_arm) committed[flag.paired_arm.key] = flag.paired_arm.value
  }
  const [draft, setDraft] =
    useState<Record<string, number | boolean>>(committed)
  const dirty = Object.keys(committed).filter((k) => draft[k] !== committed[k])
  const set = (key: string, value: number | boolean) =>
    setDraft((d) => ({ ...d, [key]: value }))

  return (
    <SectionDialog
      title="graph augmentation"
      description="Each channel flag turns on a producer of ranked candidates; its paired w_* is that list's weight in the fusion. Both go out in one request."
      dirty={dirty}
      saving={binding.isSaving(SECTIONS.graph)}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveFlags(
          SECTIONS.graph,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
        onOpenChange(false)
      }}
    >
      {binding.graphFlags.map((flag) => (
        <div
          key={flag.key}
          className="border-inset bg-card flex flex-col gap-2 rounded-md border px-3 py-2.5"
        >
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-sm font-semibold">{flag.key}</span>
            <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
            <span className="flex-1" />
            <ActivationNote taskId={flag.activatesWith} />
            <Switch
              checked={draft[flag.key] as boolean}
              onCheckedChange={(on) => set(flag.key, on)}
              aria-label={flag.key}
            />
            {flag.unmeasured && <UnmeasuredTag />}
          </div>
          {flag.paired_arm ? (
            <div className="flex flex-wrap items-center gap-2 pl-0.5">
              <span className="text-muted-foreground font-mono text-sm">
                paired weight{" "}
                <b className="text-foreground font-sans font-semibold">
                  {flag.paired_arm.key}
                </b>
              </span>
              <HelpTip label={`About ${flag.paired_arm.key}`}>
                {flag.paired_arm.desc}
              </HelpTip>
              <span className="flex-1" />
              <ArmInput
                arm={flag.paired_arm}
                value={draft[flag.paired_arm.key] as number}
                onChange={(v) => set(flag.paired_arm!.key, v)}
              />
              <ArmPill value={draft[flag.paired_arm.key] as number} />
            </div>
          ) : (
            <p className="text-muted-foreground pl-0.5 text-sm italic">
              {flag.no_weight_note}
            </p>
          )}
        </div>
      ))}
    </SectionDialog>
  )
}

export function FlagsTab() {
  const binding = useFlagsTabBinding()
  const [editing, setEditing] = useState<string | null>(null)
  const close = () => setEditing(null)

  const graphWeights = binding.graphFlags.flatMap((f) =>
    f.paired_arm ? [f.paired_arm] : [],
  )
  const allArms = [...binding.fusionArms, binding.contextBoost, ...graphWeights]
  const activeArms = allArms.filter(
    (a) => armStatus(a.value) === "active",
  ).length
  const activeFusionArms = binding.fusionArms.filter(
    (a) => armStatus(a.value) === "active",
  ).length
  const flagsOn = binding.behavioralFlags.filter((f) => f.enabled).length
  const channelsOn = binding.graphFlags.filter((f) => f.enabled).length
  const tunablesOverridden = binding.tunables.filter(
    (t) => t.source === "override",
  ).length

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Ranking-arm weights, behavioral feature flags, graph augmentation, the
          pipeline and embedding tunables, classification, the corroboration
          promotion gate, and the repo auto-provision allowlist — config rows
          read through merge-over-coded-defaults.
        </span>
        <HelpTip label="About the Flags tab">
          The tunables tab. Every value here is a row in the `feature_flags`,
          `verification_ladder` or `repo_allowlist` config row, read through
          merge-over-coded-defaults; nothing on this tab is computed, only read
          and written. Each card is read-only until you press Edit, and each
          card's edits are written in a single request. Job schedules are edited
          on the Jobs page, and which model serves each purpose is on the LLM
          tab. An arm at 0 renders as inactive rather than being omitted, and a
          flag with no recorded gate-ledger win renders visibly unmeasured —
          flipping it stays possible, but is never quietly assumed proven.
        </HelpTip>
      </div>
      <div className="border-inset bg-muted/30 flex flex-wrap items-center gap-2.5 rounded-lg border px-4 py-2.5">
        <span className="text-sm font-semibold">Flags</span>
        <span className="text-muted-foreground font-mono text-sm">
          {`${activeArms} of ${allArms.length} arms active · ${flagsOn} of ${binding.behavioralFlags.length} feature flags on · ${binding.overridesWritten} overrides written`}
        </span>
        <span className="ml-auto">
          <SurfaceStateChip state="populated" />
        </span>
      </div>

      <div className="flex flex-col gap-6">
        <Section
          icon={SlidersHorizontal}
          name="rank_fusion_factor arms"
          help="Per-row multipliers applied to a row's fused rrf_score after Reciprocal Rank Fusion. Each is a no-op at exactly 0 — the factor is 1, so the arm is built and wired but moves nothing. Each flips only on a measured retrieval win reported with its latency and token twin, recorded in the gate ledger's arm activation log, never by intuition."
          meta={`${activeFusionArms} of ${binding.fusionArms.length} active`}
          onEdit={() => setEditing(SECTIONS.arms)}
          saving={binding.isSaving(SECTIONS.arms)}
        >
          {binding.fusionArms.map((arm) => (
            <ArmRow key={arm.key} arm={arm} />
          ))}
        </Section>

        <Section
          icon={Flag}
          name="feature flags"
          help="Plain on/off switches, distinct from the weighted arms above: each gates a whole code path rather than scaling a score. relation_rescue is the only surviving ingestion-side flag; the other two govern retrieval."
          meta={`${flagsOn} of ${binding.behavioralFlags.length} on`}
          onEdit={() => setEditing(SECTIONS.flags)}
          saving={binding.isSaving(SECTIONS.flags)}
        >
          {binding.behavioralFlags.map((flag) => (
            <BehavioralFlagRow key={flag.key} flag={flag} />
          ))}
        </Section>

        <Section
          icon={Crosshair}
          name="context match boost"
          help="The magnitude of the applies_when context boost (doc 07 §6). Its own group because it acts on a match outcome rather than on a stored column: at 0 matching still labels every row and still counts conflicts — only the multiplier goes quiet."
          onEdit={() => setEditing(SECTIONS.contextBoost)}
          saving={binding.isSaving(SECTIONS.contextBoost)}
        >
          <ArmRow arm={binding.contextBoost} />
        </Section>

        <Section
          icon={Network}
          name="graph augmentation"
          help="Doc 07 §4. Each *_enabled flag turns on a producer of ranked candidates from the entity graph, and its paired w_* is that list's weight in the fusion — a LIST weight, not a per-row multiplier, so it scales how much the whole list counts rather than boosting individual rows. All three land inert so retrieval is byte-identical to the vector+FTS hybrid until one is measured. A flag on with its weight still at 0 produces candidates that fuse at zero weight, which is why the pairing is shown together."
          meta={
            binding.graphFlags.length
              ? `${channelsOn} of ${binding.graphFlags.length} channels on`
              : undefined
          }
          onEdit={
            binding.graphAugmentationAvailable
              ? () => setEditing(SECTIONS.graph)
              : undefined
          }
          saving={binding.isSaving(SECTIONS.graph)}
        >
          {binding.graphAugmentationAvailable ? (
            binding.graphFlags.map((flag) => (
              <div
                key={flag.key}
                className="border-inset bg-card flex flex-col gap-2 rounded-md border px-3 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-mono text-sm font-semibold">
                    {flag.key}
                  </span>
                  <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
                  <span className="flex-1" />
                  <ActivationNote taskId={flag.activatesWith} />
                  <SourceTag source={flag.source} />
                  <BoolTag on={flag.enabled} />
                  {flag.unmeasured && <UnmeasuredTag />}
                </div>
                {flag.paired_arm ? (
                  <div className="flex flex-wrap items-center gap-2 pl-0.5">
                    <span className="text-muted-foreground font-mono text-sm">
                      paired weight{" "}
                      <b className="text-foreground font-sans font-semibold">
                        {flag.paired_arm.key}
                      </b>
                    </span>
                    <HelpTip label={`About ${flag.paired_arm.key}`}>
                      {flag.paired_arm.desc}
                    </HelpTip>
                    <span className="flex-1" />
                    <SourceTag source={flag.paired_arm.source} />
                    <ValueTag value={flag.paired_arm.value} />
                    <ArmPill value={flag.paired_arm.value} />
                  </div>
                ) : (
                  <p className="text-muted-foreground pl-0.5 text-sm italic">
                    {flag.no_weight_note}
                  </p>
                )}
              </div>
            ))
          ) : binding.isLoading ? null : (
            <NotYetImplemented
              label="ppr_enabled · dual_level_enabled · community_injection_enabled"
              note="Could not read /config/feature-flags — the flags are still at whatever the config row holds; only this editor is unavailable."
            />
          )}
        </Section>

        <Section
          icon={Gauge}
          name="pipeline & embedding tunables"
          help="Throughput and cache knobs in the same feature_flags row as the arms. None of them gates a phase or changes what gets stored — they trade provider rate-limit headroom, memory and batch latency against each other. Each accepts a bounded range the API enforces; a value outside it is refused rather than clamped."
          meta={
            tunablesOverridden
              ? `${tunablesOverridden} overridden`
              : "all at coded defaults"
          }
          onEdit={() => setEditing(SECTIONS.tunables)}
          saving={binding.isSaving(SECTIONS.tunables)}
        >
          {binding.tunables.map((tunable) => (
            <TunableRow key={tunable.key} tunable={tunable} />
          ))}
        </Section>

        <ClassificationSection binding={binding} />

        <RepoAllowlistSection binding={binding} />

        <CorroborationSection binding={binding} />
      </div>

      {editing === SECTIONS.arms && (
        <FlagsSectionDialog
          title="rank_fusion_factor arms"
          description="Per-row multipliers on a row's fused rrf_score. Each is a no-op at exactly 0. All four save in one request."
          section={SECTIONS.arms}
          binding={binding}
          arms={binding.fusionArms}
          onOpenChange={close}
        />
      )}
      {editing === SECTIONS.flags && (
        <FlagsSectionDialog
          title="feature flags"
          description="On/off switches, each gating a whole code path rather than scaling a score. All three save in one request."
          section={SECTIONS.flags}
          binding={binding}
          flags={binding.behavioralFlags}
          onOpenChange={close}
        />
      )}
      {editing === SECTIONS.contextBoost && (
        <FlagsSectionDialog
          title="context match boost"
          description="The magnitude of the applies_when context boost. At 0, matching still labels every row and still counts conflicts — only the multiplier goes quiet."
          section={SECTIONS.contextBoost}
          binding={binding}
          arms={[binding.contextBoost]}
          onOpenChange={close}
        />
      )}
      {editing === SECTIONS.graph && (
        <GraphDialog binding={binding} onOpenChange={close} />
      )}
      {editing === SECTIONS.tunables && (
        <FlagsSectionDialog
          title="pipeline & embedding tunables"
          description="Throughput and cache knobs. Each accepts a bounded range the API enforces; the fields clamp locally so one out-of-range value cannot fail the whole save."
          section={SECTIONS.tunables}
          binding={binding}
          tunables={binding.tunables}
          onOpenChange={close}
        />
      )}
    </div>
  )
}
