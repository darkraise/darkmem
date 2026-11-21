import { useState, type ReactNode } from "react"
import {
  BadgeCheck,
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
import { FieldDescription } from "darkraise-ui/components/field"
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
import {
  EmptyState,
  HelpTip,
  IconButton,
  NumberField,
} from "@/components/darkmem"
import { armStatus } from "@/demo/settings"
import type {
  DemoBehavioralFlag,
  DemoGraphFlag,
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
import { useDialogSave } from "../use-dialog-save"

const SETTING_NAMES: Record<string, string> = {
  confidence_rank_gamma: "Confidence",
  w_conf: "Confidence",
  w_importance: "Importance",
  w_heat: "Read frequency",
  w_recency: "Recency",
  hybrid_search_enabled: "Hybrid search",
  reranker_enabled: "LLM reranker",
  relation_rescue: "Relation rescue",
  ppr_enabled: "Graph proximity",
  dual_level_enabled: "Relation search",
  w_ppr: "Weight",
  w_dual: "Weight",
  pipeline_concurrency: "Parallel memories",
  embedding_batch_size: "Embedding batch size",
  embedding_concurrency: "Parallel embedding calls",
  entity_cache_ttl_minutes: "Entity cache lifetime",
  classification_mode: "Mode",
  n_default: "Sources needed",
  n_diverse: "Sources needed if varied",
  time_gap_days: "Days apart that count as varied",
}

function SettingName({ name }: { name: string }) {
  const label = SETTING_NAMES[name]
  return (
    // Wraps rather than nowrap: on a phone "Parallel embedding calls
    // embedding_concurrency" is wider than the card, and nowrap pushed the
    // whole page (and the corroboration dialog) past the viewport. The key
    // drops under the label instead, and may break anywhere as a last resort.
    <span className="flex min-w-0 flex-wrap items-baseline gap-x-2">
      <span className="text-sm font-semibold">{label ?? name}</span>
      {label && (
        <span className="text-muted-foreground font-mono text-xs [overflow-wrap:anywhere]">
          {name}
        </span>
      )}
    </span>
  )
}

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
      {/* `label` is a visible slot; the name belongs to assistive tech only,
          or "Saving" is drawn over the row beside it. */}
      {saving && <Spinner size="sm" aria-label="Saving" />}
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
 *  than inferring it from which fields they happen to remember touching.
 *
 *  It stays open until the write lands, and a refusal leaves it open with the
 *  edits and the server's reason in the footer. */
function SectionDialog({
  title,
  description,
  dirty,
  canSave = true,
  onOpenChange,
  onSave,
  children,
}: {
  title: string
  description: string
  /** Field names this save will write, in display order. */
  dirty: string[]
  canSave?: boolean
  onOpenChange: (open: boolean) => void
  onSave: () => Promise<unknown>
  children: ReactNode
}) {
  const save = useDialogSave(() => onOpenChange(false))
  const saving = save.pending
  return (
    <Dialog open onOpenChange={save.guard(onOpenChange)}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">{children}</div>
        {save.error && (
          <p role="alert" className="text-destructive-text text-sm">
            Not saved: {save.error}
          </p>
        )}
        <div className="border-border flex flex-wrap items-center gap-2 border-t pt-3">
          {dirty.length > 0 && (
            <span className="text-muted-foreground font-mono text-xs">
              edited: {dirty.join(", ")}
            </span>
          )}
          <span className="flex-1" />
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
            onClick={() => save.run(onSave)}
          >
            {saving ? "Saving…" : "Save"}
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
        "rounded-full border px-2 py-0.5 font-mono text-xs tracking-wide whitespace-nowrap uppercase",
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
        <span className="text-muted-foreground ml-1 text-xs font-normal">
          {unit}
        </span>
      )}
    </span>
  )
}

/** The right-hand end of a setting row: marker, value and state pill as one
 *  unit. On a narrow screen the row wraps, and these must wrap together:
 *  as separate flex items a value stayed on the first line while its pill
 *  dropped to the next, differently from row to row. */
function RowValue({ children }: { children: ReactNode }) {
  return (
    <span className="ml-auto flex shrink-0 items-center gap-2.5">
      {children}
    </span>
  )
}

/** A quiet marker on a value the operator changed; a default carries none. */
function SourceTag({ source }: { source: DemoRankArm["source"] }) {
  if (source === "default") return null
  return (
    <span className="text-primary-text font-mono text-xs whitespace-nowrap">
      (override)
    </span>
  )
}

/** Rendered only for a clamped threshold: a clamped value looks exactly like a
 *  saved one unless the difference is shown. */
function ClampedPill({ param }: { param: DemoLadderParam }) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label="About the clamped state"
          className="border-warning-edge/60 bg-warning-solid/10 text-warning-text inline-flex cursor-help items-center rounded-full border px-2.5 py-0.5 font-mono text-xs tracking-wide whitespace-nowrap uppercase"
        >
          clamped
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          {param.note ??
            `The saved value is not in effect; ${param.effective} is used.`}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/** A dialog's number field. Every keystroke is the draft, so Save enables
 *  without a blur. The field is given no bounds: the library clamps to its
 *  `min`/`max` on blur, which would change the number silently, so the row
 *  shows its own range error instead. NaN (text the field cannot parse) is
 *  kept as the draft and refused by that error, never written as zero. */
function DraftNumber({
  name,
  step,
  value,
  onChange,
  error,
  className,
}: {
  name: string
  step: number
  value: number
  onChange: (value: number) => void
  error: string | null
  className?: string
}) {
  return (
    <NumberField
      step={step}
      value={value}
      aria-label={name}
      aria-invalid={error ? true : undefined}
      aria-describedby={error ? rangeErrorId(name) : undefined}
      onValueChange={onChange}
      className={cn("w-24", className)}
    />
  )
}

/** Why a draft number would be refused, or null. The bounds are the server's
 *  (`numeric_bounds`, `FeatureFlagsUpdate`'s own), so this refuses exactly
 *  what the PUT would answer 422 to. */
function rangeError(value: number, min?: number, max?: number): string | null {
  const bounded = min !== undefined && max !== undefined
  if (!Number.isFinite(value))
    return bounded ? `Enter a value from ${min} to ${max}.` : "Enter a number."
  if (bounded && (value < min || value > max))
    return `Enter a value from ${min} to ${max}.`
  return null
}

function armRangeError(arm: DemoRankArm, value: number): string | null {
  return rangeError(value, arm.min, arm.max)
}

/** The allowed range under a field being edited, turning into the error when
 *  the draft leaves it. */
const rangeErrorId = (name: string) => `range-error-${name}`

function RangeHint({
  name,
  min,
  max,
  error,
}: {
  name: string
  min?: number
  max?: number
  error: string | null
}) {
  if (error)
    return (
      <p id={rangeErrorId(name)} role="alert" className="text-destructive-text basis-full text-sm">
        {error}
      </p>
    )
  if (min === undefined || max === undefined) return null
  return (
    <p className="text-muted-foreground basis-full text-right text-xs">
      {min} to {max}
    </p>
  )
}

/** One ranking arm.
 *
 *  The same row renders at rest and under edit, so the two cannot disagree
 *  about what an arm is — which help text it carries, which badges apply.
 *  Only the value slot changes: a number, or the input that edits it. */
// The three dormant rank arms. Each flips only on a measured retrieval win
// recorded in the gate ledger, which the row says rather than implying a
// switch an operator should simply turn.
const DORMANT_RANK_ARMS = new Set(["w_importance", "w_heat", "w_recency"])
const DORMANT_ARM_NOTE = "Turned on only after a measured retrieval win"

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
  const error = editing ? armRangeError(arm, draft) : null
  return (
    <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <SettingName name={arm.key} />
      <HelpTip label={`About ${arm.key}`}>{help ?? arm.desc}</HelpTip>
      <RowValue>
        <SourceTag source={arm.source} />
        {editing ? (
          <DraftNumber
            name={arm.key}
            step={arm.step ?? 1}
            value={draft}
            onChange={onChange}
            error={error}
          />
        ) : (
          <ValueTag value={arm.value} />
        )}
        {/* No ACTIVE pill for a value the server will refuse: it would claim
            an effect the save cannot have. */}
        {!error && <ArmPill value={shown} />}
      </RowValue>
      {editing && <RangeHint name={arm.key} min={arm.min} max={arm.max} error={error} />}
      {DORMANT_RANK_ARMS.has(arm.key) && (
        <FieldDescription className="basis-full">
          {DORMANT_ARM_NOTE}
        </FieldDescription>
      )}
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
          finding the meta in the same place on every card. From sm up the
          title truncates instead. Below sm the meta drops under the title and
          the title wraps on spaces: at phone width truncation left titles
          three characters long ("GRA…"), identifiable only by their icon. */}
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
        <div className="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-row sm:items-center sm:gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <h3 className="text-foreground min-w-0 font-mono text-xs font-semibold tracking-[0.14em] uppercase sm:truncate">
              {name}
            </h3>
            {help && (
              <span className="shrink-0">
                <HelpTip label={`About ${name}`}>{help}</HelpTip>
              </span>
            )}
          </div>
          <span className="hidden flex-1 sm:block" />
          {meta && (
            <span className="text-muted-foreground shrink-0 font-mono text-xs whitespace-nowrap">
              {meta}
            </span>
          )}
        </div>
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
      <SettingName name={flag.key} />
      <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
      <RowValue>
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
      </RowValue>
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
      <SettingName name={tunable.key} />
      <HelpTip label={`About ${tunable.key}`}>
        {tunable.desc}. Range {tunable.min}–{tunable.max}; default{" "}
        {tunable.coded_default}.
      </HelpTip>
      <RowValue>
        <SourceTag source={tunable.source} />
        {editing ? (
          <span className="flex items-center gap-2">
            <DraftNumber
              name={tunable.key}
              step={1}
              value={draft}
              onChange={onChange}
              error={tunableRangeError(tunable, draft)}
            />
            {tunable.unit && (
              <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">
                {tunable.unit}
              </span>
            )}
          </span>
        ) : (
          <ValueTag value={tunable.value} unit={tunable.unit} />
        )}
      </RowValue>
      {editing && (
        <RangeHint
          name={tunable.key}
          min={tunable.min}
          max={tunable.max}
          error={tunableRangeError(tunable, draft)}
        />
      )}
    </div>
  )
}

function tunableRangeError(tunable: DemoTunable, value: number) {
  return rangeError(value, tunable.min, tunable.max)
}

/** A source of this tab whose read failed, in the app's one failed state. */
function LoadFailed({
  title,
  error,
  retry,
}: {
  title: string
  error: Error
  retry: () => void
}) {
  return (
    <EmptyState
      kind="failed"
      title={title}
      description={error.message}
      action={<Button onClick={retry}>Retry</Button>}
    />
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
        help="Repositories an agent may register automatically. Patterns are host, *.host or host/path-prefix. An empty list refuses every request."
        meta={
          patterns.length === 0
            ? "empty"
            : `${patterns.length} pattern${patterns.length === 1 ? "" : "s"}`
        }
        onEdit={binding.allowlistError ? undefined : () => setEditing(true)}
        saving={saving}
      >
        {binding.allowlistError ? (
          <LoadFailed
            title="Could not load the allowlist"
            error={binding.allowlistError}
            retry={binding.retryAllowlist}
          />
        ) : patterns.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No patterns — every repo hint is refused until at least one is
            saved.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {patterns.map((pattern) => (
              <code
                key={pattern}
                className="border-inset bg-muted/40 rounded-md border px-2 py-0.5 font-mono text-xs"
              >
                {pattern}
              </code>
            ))}
          </div>
        )}
      </Section>
      {editing && <AllowlistDialog binding={binding} onOpenChange={setEditing} />}
    </>
  )
}

function AllowlistDialog({
  binding,
  onOpenChange,
}: {
  binding: FlagsTabBinding
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
      description="One pattern per line: host, *.host or host/path-prefix."
      dirty={dirty}
      onOpenChange={onOpenChange}
      onSave={() => binding.saveAllowlist(patterns)}
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
        <code className="font-mono">*.forge.internal.example</code>. An empty
        list refuses every request.
      </p>
    </SectionDialog>
  )
}

const LADDER_PARAM_HELP: Record<string, string> = {
  n_default:
    "How many independent sources a fact needs before it is marked corroborated. One source repeating a claim counts once.",
  n_diverse:
    "The lower count used when the sources differ in kind (for example a memory and code) or lie at least time_gap_days apart. Must not exceed n_default.",
  time_gap_days:
    "How many days apart two sources of the same kind must be to count as diverse.",
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
        meta={clamped.length > 0 ? `${clamped.length} clamped` : undefined}
        help="How many independent sources a fact needs before it is marked corroborated. These are minimums: raising one always applies, while lowering one below its default is clamped back unless a recorded measurement allows it."
        onEdit={
          binding.corroborationAvailable ? () => setEditing(true) : undefined
        }
        saving={saving}
      >
        {binding.corroborationAvailable ? (
          corr.params.map((param) => (
            <div
              key={param.name}
              className="border-inset bg-card flex flex-col gap-2 rounded-md border px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2.5">
                <SettingName name={param.name} />
                <HelpTip label={`About ${param.name}`}>
                  {LADDER_PARAM_HELP[param.name] ?? param.name}
                  {" Default "}
                  {param.floor}.
                </HelpTip>
                <RowValue>
                  {param.committed !== null &&
                    param.committed !== param.effective && (
                      <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">
                        asked for {param.committed}
                      </span>
                    )}
                  <ValueTag value={param.effective} />
                  {param.state === "clamped" && <ClampedPill param={param} />}
                </RowValue>
              </div>
              {param.state === "clamped" && param.note && (
                <p className="text-warning-text pl-0.5 text-sm">{param.note}</p>
              )}
            </div>
          ))
        ) : binding.ladderError ? (
          <LoadFailed
            title="Could not load the corroboration thresholds"
            error={binding.ladderError}
            retry={binding.retryLadder}
          />
        ) : null}
      </Section>
      {editing && <LadderDialog binding={binding} onOpenChange={setEditing} />}
    </>
  )
}

function LadderDialog({
  binding,
  onOpenChange,
}: {
  binding: FlagsTabBinding
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
  const errorOf = (name: string) => {
    const value = draft[name]
    return value === null || value === undefined ? null : rangeError(value)
  }

  return (
    <SectionDialog
      title="corroboration promotion gate"
      description="Minimum source counts. Lowering one below its floor may be clamped back; the card shows it if so."
      dirty={dirty}
      canSave={corr.params.every((p) => errorOf(p.name) === null)}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveLadder(
          Object.fromEntries(dirty.map((name) => [name, draft[name] ?? null])),
        )
      }
    >
      {corr.params.map((param) => (
        // Two columns (name | fixed-width control group) so floor, input and
        // reset line up across rows whatever the name's length; under sm the
        // control group drops onto its own line instead of overflowing.
        <div
          key={param.name}
          className="border-inset bg-card grid grid-cols-1 items-center gap-2 rounded-md border px-3 py-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-2.5"
        >
          <div className="flex min-w-0 items-center gap-2.5">
            <SettingName name={param.name} />
            <HelpTip label={`About ${param.name}`}>
              {LADDER_PARAM_HELP[param.name] ?? param.name}
            </HelpTip>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="text-muted-foreground w-14 font-mono text-xs whitespace-nowrap sm:text-right">
              floor {param.floor}
            </span>
            <DraftNumber
              name={param.name}
              step={1}
              value={draft[param.name] ?? param.floor}
              onChange={(v) => setDraft((d) => ({ ...d, [param.name]: v }))}
              error={errorOf(param.name)}
              className="w-20"
            />
            <Button
              variant="ghost"
              className="text-muted-foreground font-mono text-xs"
              disabled={draft[param.name] === null}
              onClick={() => setDraft((d) => ({ ...d, [param.name]: null }))}
            >
              reset to floor
            </Button>
          </div>
          <RangeHint name={param.name} error={errorOf(param.name)} />
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
  if (!label.description) {
    return (
      <span
        className={cn(
          "rounded-full border px-2 py-0.5 font-mono text-xs whitespace-nowrap",
          muted
            ? "border-border/60 text-muted-foreground border-dashed"
            : "border-border bg-muted/40 text-foreground/90",
        )}
      >
        {label.name}
      </span>
    )
  }
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label={`About the ${label.name} label`}
          className={cn(
            "cursor-help rounded-full border px-2 py-0.5 font-mono text-xs whitespace-nowrap",
            muted
              ? "border-border/60 text-muted-foreground border-dashed"
              : "border-border bg-muted/40 text-foreground/90",
          )}
        >
          {label.name}
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          {label.description}
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
        help="Which labels the classifier may assign to a memory. The classifier model itself is set on the LLM tab."
        meta={`${binding.classificationLabels.length} labels`}
        onEdit={() => setEditing(true)}
        saving={saving}
      >
        <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
          <SettingName name="classification_mode" />
          <HelpTip label="About classification_mode">
            `simple` uses a fixed set of labels and classifies in the same LLM
            call as extraction. `expanded` lets you choose label areas and costs
            a second LLM call per memory.
          </HelpTip>
          <span className="flex-1" />
          <span className="border-primary/55 bg-primary/10 text-primary-text rounded-full border px-2 py-0.5 font-mono text-xs tracking-wide uppercase">
            {binding.classificationMode}
          </span>
        </div>

        <div className="border-inset bg-card flex flex-col gap-2.5 rounded-md border px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-sm font-semibold whitespace-nowrap">
              label space
            </span>
            <HelpTip label="About the label space">
              The labels the classifier may assign to a memory.
            </HelpTip>
            <span className="flex-1" />
            {!simple && (
              <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">
                {binding.classificationAreas.length} of{" "}
                {binding.availableAreas.length} areas enabled
              </span>
            )}
          </div>

          {unowned.length > 0 && (
            <div className="flex flex-wrap items-baseline gap-2">
              {!simple && (
                <span className="text-muted-foreground w-32 shrink-0 font-mono text-xs tracking-wide uppercase">
                  always
                </span>
              )}
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
                          no additional labels
                        </span>
                      )}
                    </div>
                    <span className="text-muted-foreground w-10 shrink-0 text-right font-mono text-xs">
                      +{contributed.length}
                    </span>
                  </div>
                )
              })}
        </div>
      </Section>
      {editing && (
        <ClassificationDialog binding={binding} onOpenChange={setEditing} />
      )}
    </>
  )
}

function ClassificationDialog({
  binding,
  onOpenChange,
}: {
  binding: FlagsTabBinding
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
      description="Choose the label mode and, in expanded mode, the label areas."
      dirty={dirty}
      onOpenChange={onOpenChange}
      onSave={() => {
        const patch: Record<string, unknown> = {}
        if (dirty.includes("classification_mode")) {
          patch.classification_mode = mode
        }
        if (dirty.includes("classification_areas")) {
          patch.classification_areas = areas
        }
        return binding.saveFlags(SECTIONS.classification, patch)
      }}
    >
      <div className="border-inset bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
        <SettingName name="classification_mode" />
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
      {simple && (
        <p className="text-muted-foreground text-sm">
          Simple mode uses a fixed set of labels. Switch to expanded to choose
          label areas.
        </p>
      )}

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
  const inRange =
    (arms ?? []).every(
      (arm) => armRangeError(arm, draft[arm.key] as number) === null,
    ) &&
    (tunables ?? []).every(
      (t) => tunableRangeError(t, draft[t.key] as number) === null,
    )

  return (
    <SectionDialog
      title={title}
      description={description}
      dirty={dirty}
      canSave={inRange}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveFlags(
          section,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
      }
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
  const weightError = (flag: DemoGraphFlag) =>
    flag.paired_arm
      ? armRangeError(flag.paired_arm, draft[flag.paired_arm.key] as number)
      : null
  const weightsInRange = binding.graphFlags.every((f) => !weightError(f))

  return (
    <SectionDialog
      title="graph augmentation"
      canSave={weightsInRange}
      description="Each channel adds results from the entity graph; its weight sets how much they count in the ranking."
      dirty={dirty}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveFlags(
          SECTIONS.graph,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
      }
    >
      {binding.graphFlags.map((flag) => (
        <div
          key={flag.key}
          className="border-inset bg-card flex flex-col gap-2 rounded-md border px-3 py-2.5"
        >
          <div className="flex flex-wrap items-center gap-2.5">
            <SettingName name={flag.key} />
            <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
            <span className="flex-1" />
            <Switch
              checked={draft[flag.key] as boolean}
              onCheckedChange={(on) => set(flag.key, on)}
              aria-label={flag.key}
            />
          </div>
          {flag.paired_arm && (
            <div className="flex flex-wrap items-center gap-2 pl-0.5">
              <SettingName name={flag.paired_arm.key} />
              <HelpTip label={`About ${flag.paired_arm.key}`}>
                {flag.paired_arm.desc}
              </HelpTip>
              <RowValue>
                <DraftNumber
                  name={flag.paired_arm.key}
                  step={flag.paired_arm.step ?? 1}
                  value={draft[flag.paired_arm.key] as number}
                  onChange={(v) => set(flag.paired_arm!.key, v)}
                  error={weightError(flag)}
                />
                {!weightError(flag) && (
                  <ArmPill value={draft[flag.paired_arm.key] as number} />
                )}
              </RowValue>
              <RangeHint
                name={flag.paired_arm.key}
                min={flag.paired_arm.min}
                max={flag.paired_arm.max}
                error={weightError(flag)}
              />
            </div>
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

  const activeFusionArms = binding.fusionArms.filter(
    (a) => armStatus(a.value) === "active",
  ).length
  const flagsOn = binding.behavioralFlags.filter((f) => f.enabled).length
  const channelsOn = binding.graphFlags.filter((f) => f.enabled).length
  const tunablesOverridden = binding.tunables.filter(
    (t) => t.source === "override",
  ).length

  if (binding.error) {
    return (
      <LoadFailed
        title="Could not load the feature flags"
        error={binding.error}
        retry={binding.retry}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-6">
        <Section
          icon={SlidersHorizontal}
          name="ranking arms"
          help="Multipliers applied to each search result's score. An arm at 0 has no effect."
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
          help="On/off switches for whole search and ingestion features."
          meta={`${flagsOn} of ${binding.behavioralFlags.length} on`}
          onEdit={() => setEditing(SECTIONS.flags)}
          saving={binding.isSaving(SECTIONS.flags)}
        >
          {binding.behavioralFlags.map((flag) => (
            <BehavioralFlagRow key={flag.key} flag={flag} />
          ))}
        </Section>

        <Section
          icon={Network}
          name="graph augmentation"
          help="Each channel adds results from the entity graph. Its paired weight sets how much that list counts in the ranking; a channel that is on with weight 0 has no effect."
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
                  <SettingName name={flag.key} />
                  <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
                  <RowValue>
                    <SourceTag source={flag.source} />
                    <BoolTag on={flag.enabled} />
                  </RowValue>
                </div>
                {flag.paired_arm && (
                  <div className="flex flex-wrap items-center gap-2 pl-0.5">
                    <SettingName name={flag.paired_arm.key} />
                    <HelpTip label={`About ${flag.paired_arm.key}`}>
                      {flag.paired_arm.desc}
                    </HelpTip>
                    <RowValue>
                      <SourceTag source={flag.paired_arm.source} />
                      <ValueTag value={flag.paired_arm.value} />
                      <ArmPill value={flag.paired_arm.value} />
                    </RowValue>
                  </div>
                )}
              </div>
            ))
          ) : null}
        </Section>

        <Section
          icon={Gauge}
          name="pipeline & embedding tunables"
          help="Throughput and cache settings. They trade provider rate limits, memory and batch latency; none changes what is stored."
          meta={
            tunablesOverridden ? `${tunablesOverridden} overridden` : undefined
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
          title="ranking arms"
          description="Multipliers on each search result's score. 0 has no effect."
          section={SECTIONS.arms}
          binding={binding}
          arms={binding.fusionArms}
          onOpenChange={close}
        />
      )}
      {editing === SECTIONS.flags && (
        <FlagsSectionDialog
          title="feature flags"
          description="On/off switches for whole search and ingestion features."
          section={SECTIONS.flags}
          binding={binding}
          flags={binding.behavioralFlags}
          onOpenChange={close}
        />
      )}
      {editing === SECTIONS.graph && (
        <GraphDialog binding={binding} onOpenChange={close} />
      )}
      {editing === SECTIONS.tunables && (
        <FlagsSectionDialog
          title="pipeline & embedding tunables"
          description="Each value must lie in its field's range."
          section={SECTIONS.tunables}
          binding={binding}
          tunables={binding.tunables}
          onOpenChange={close}
        />
      )}
    </div>
  )
}
