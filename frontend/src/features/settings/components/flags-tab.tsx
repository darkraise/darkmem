import { useState, type ReactNode } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
} from "darkraise-ui/components/card"
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
import { HelpTip, NumberField } from "@/components/darkmem"
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
  SAVING_ALLOWLIST,
  SAVING_CLASSIFICATION_AREAS,
  SAVING_CLASSIFICATION_MODE,
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

function SourceTag({ source }: { source: DemoRankArm["source"] }) {
  return (
    <span
      className={cn(
        "font-mono text-[10px] whitespace-nowrap",
        source === "default"
          ? "text-muted-foreground italic"
          : "text-primary/80",
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
          className="border-warning/50 text-warning cursor-help rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase"
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
            "inline-flex cursor-help items-center rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap",
            clamped
              ? "border-warning/60 bg-warning/10 text-warning"
              : param.state === "honoured"
                ? "border-primary/55 bg-primary/10 text-primary"
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

/** Blur/Enter-commit numeric field — a keystroke is not yet an override. */
function ArmInput({
  arm,
  onCommit,
  className,
}: {
  arm: DemoRankArm
  onCommit: (value: number) => void
  className?: string
}) {
  const [draft, setDraft] = useState(arm.value)
  // The draft must follow the committed value when that value changes from
  // OUTSIDE this field — a reset button, a refetch, another control's
  // response. Without this the draft is initial-value-only, and the next blur
  // commits the stale number back: measured in a browser, "reset to floor"
  // cleared the threshold and the blur that followed re-sent the old value,
  // silently undoing the reset with a 200 and no error anywhere. React's
  // documented adjust-state-during-render pattern, not an effect — an effect
  // would paint the stale draft for a frame first.
  const [lastCommitted, setLastCommitted] = useState(arm.value)
  if (arm.value !== lastCommitted) {
    setLastCommitted(arm.value)
    setDraft(arm.value)
  }
  const commit = () => {
    // NaN is what the field reports for text it cannot parse, and is the
    // case a raw number input used to collapse into a committed zero.
    if (Number.isFinite(draft) && draft !== arm.value) onCommit(draft)
    else setDraft(arm.value)
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

function ArmRow({
  arm,
  help,
  saving = false,
  onCommit,
}: {
  arm: DemoRankArm
  help?: string
  saving?: boolean
  onCommit: (value: number) => void
}) {
  return (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
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
      <ArmInput arm={arm} onCommit={onCommit} />
      <SavingMark saving={saving} />
      <ArmPill value={arm.value} />
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
  name,
  help,
  meta,
  children,
}: {
  name: string
  help?: string
  meta?: ReactNode
  children: ReactNode
}) {
  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
        <h3 className="text-foreground font-mono text-[11px] font-semibold tracking-[0.14em] uppercase">
          {name}
        </h3>
        {help && <HelpTip label={`About ${name}`}>{help}</HelpTip>}
        <span className="flex-1" />
        {meta && (
          <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
            {meta}
          </span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2 p-4">{children}</CardContent>
    </Card>
  )
}

function BehavioralFlagRow({
  flag,
  saving,
  onToggle,
}: {
  flag: DemoBehavioralFlag
  saving: boolean
  onToggle: (enabled: boolean) => void
}) {
  return (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <span className="font-mono text-sm font-semibold whitespace-nowrap">
        {flag.key}
      </span>
      <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
      <span className="flex-1" />
      <SourceTag source={flag.source} />
      <SavingMark saving={saving} />
      <Switch
        checked={flag.enabled}
        onCheckedChange={onToggle}
        aria-label={flag.key}
        // A switch acts on a single click, so a second one mid-flight sends a
        // second write racing the first. A text field is different: taking it
        // away mid-edit loses what is being typed.
        disabled={saving}
      />
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
  saving,
  onCommit,
}: {
  tunable: DemoTunable
  saving: boolean
  onCommit: (value: number) => void
}) {
  const [draft, setDraft] = useState(tunable.value)
  // Same external-change sync as ArmInput — see the comment there.
  const [lastCommitted, setLastCommitted] = useState(tunable.value)
  if (tunable.value !== lastCommitted) {
    setLastCommitted(tunable.value)
    setDraft(tunable.value)
  }
  const commit = () => {
    const clamped = Math.min(Math.max(draft, tunable.min), tunable.max)
    if (Number.isFinite(draft) && clamped !== tunable.value) onCommit(clamped)
    else setDraft(tunable.value)
  }
  return (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
      <span className="font-mono text-sm font-semibold whitespace-nowrap">
        {tunable.key}
      </span>
      <HelpTip label={`About ${tunable.key}`}>
        {tunable.desc}. Accepted range {tunable.min}–{tunable.max}; the coded
        default is {tunable.coded_default}.
      </HelpTip>
      <span className="flex-1" />
      <SourceTag source={tunable.source} />
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
      <SavingMark saving={saving} />
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
    <div className="border-border text-muted-foreground flex flex-col gap-1 rounded-md border border-dashed px-3 py-2.5 text-sm">
      <span className="font-mono text-[10px] tracking-wide uppercase">
        {label}
      </span>
      <span>{note}</span>
    </div>
  )
}

function RepoAllowlistSection({ binding }: { binding: FlagsTabBinding }) {
  const [draft, setDraft] = useState(binding.allowlistPatterns.join("\n"))
  const [saved, setSaved] = useState(false)

  const patterns = draft
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean)
  const dirty = patterns.join("\n") !== binding.allowlistPatterns.join("\n")

  return (
    <Section
      name="repo auto-provision allowlist"
      help="Repo hints arrive over the unauthenticated MCP door; an empty allowlist refuses every hint (auto-provision inert). Patterns are host, *.host, or host/path-prefix — validated with the exact parse the SSRF gate itself runs a pattern through, so this editor and the gate can never disagree on 'allowed'."
      meta={
        binding.allowlistPatterns.length === 0
          ? "empty — every hint refused"
          : `${binding.allowlistPatterns.length} pattern${binding.allowlistPatterns.length === 1 ? "" : "s"}`
      }
    >
      <div className="border-border bg-card flex flex-col gap-2 rounded-md border px-3 py-2.5">
        <span className="text-muted-foreground text-sm">
          One pattern per line — e.g.{" "}
          <code className="font-mono">github.com/darkraise/*</code> or{" "}
          <code className="font-mono">*.forge.internal.example</code>.
          {binding.allowlistPatterns.length === 0 && (
            <>
              {" "}
              Empty today — every repo hint is refused until at least one
              pattern is saved.
            </>
          )}
        </span>
        <Textarea
          value={draft}
          aria-label="repo_allowlist patterns"
          onChange={(e) => {
            setDraft(e.target.value)
            setSaved(false)
          }}
          rows={3}
          className="font-mono text-sm"
        />
        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={!dirty || binding.isSaving(SAVING_ALLOWLIST)}
            onClick={() => {
              binding.saveAllowlist(patterns)
              setSaved(true)
            }}
          >
            Save allowlist
          </Button>
          <SavingMark saving={binding.isSaving(SAVING_ALLOWLIST)} />
          {saved && (
            <span className="text-success font-mono text-sm">saved</span>
          )}
        </div>
      </div>
    </Section>
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

/** Editable, with the distance between asked-for and running rendered on every
 *  row. The thresholds are floors, so a below-floor value is clamped rather
 *  than refused — and a form that echoes the typed number back would state,
 *  falsely, that the ladder promotes at it. */
function CorroborationSection({ binding }: { binding: FlagsTabBinding }) {
  const corr = binding.corroboration
  const clamped = corr.params.filter((p) => p.state === "clamped")

  return (
    <Section
      name="corroboration promotion gate"
      meta={
        clamped.length > 0
          ? `${clamped.length} clamped`
          : corr.rowPresent
            ? "tuned"
            : "all at shipped floors"
      }
      help={`The candidate → corroborated rung of the verification ladder. ${corr.gate_note} These three numbers are FLOORS, not settings: tightening one (asking for more evidence) is always honoured, while loosening one below its shipped default is honoured only for a parameter named by a recorded ${corr.measurementTask} measurement — otherwise it is clamped back and the row says so. The contradiction veto is absolute and reads none of this: one non-echo contradiction beats any count.`}
    >
      {binding.corroborationAvailable ? (
        <>
          {corr.params.map((param) => (
            <div
              key={param.name}
              className="border-border bg-card flex flex-col gap-2 rounded-md border px-3 py-2"
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
                <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
                  running at{" "}
                  <b className="text-foreground font-sans text-sm font-semibold">
                    {param.effective}
                  </b>
                </span>
                <ArmInput
                  arm={{
                    key: param.name,
                    desc: "",
                    // The box holds what was *asked for*, so an operator can
                    // see and correct their own edit; the effective value is
                    // rendered separately rather than overwriting it.
                    value: param.committed ?? param.floor,
                    coded_default: param.floor,
                    source: param.committed === null ? "default" : "override",
                    step: 1,
                  }}
                  onCommit={(v) => binding.saveCorroboration(param.name, v)}
                  className="w-16"
                />
                <SavingMark saving={binding.isSaving(param.name)} />
                <LadderStatePill param={param} />
                {param.committed !== null && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-muted-foreground h-7 font-mono text-[10px]"
                    disabled={binding.isSaving(param.name)}
                    onClick={() => binding.saveCorroboration(param.name, null)}
                  >
                    reset to floor
                  </Button>
                )}
              </div>
              {param.state === "clamped" && param.note && (
                <p className="text-warning pl-0.5 text-sm">{param.note}</p>
              )}
            </div>
          ))}
          {clamped.length === 0 && !corr.rowPresent && (
            <p className="text-muted-foreground pl-0.5 text-sm italic">
              No config row — every threshold is at its shipped floor. Saving
              any value here creates the row.
            </p>
          )}
        </>
      ) : binding.corroborationLoading ? null : (
        <NotYetImplemented
          label="n_default · n_diverse · time_gap_days"
          note="Could not read /config/verification-ladder — the thresholds are still enforced at whatever the config row resolves to; only this editor is unavailable."
        />
      )}
    </Section>
  )
}

/** The classification tuning that rides the same `feature_flags` row as the
 *  arms without gating a pipeline phase: which label vocabularies the
 *  classifier may draw from, and how large a label space it works in. */
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
 *  actually are.
 *
 *  They were three sibling blocks: a toggle, a flat list of labels, and a grid
 *  of checkboxes. Nothing on the page said that the mode decides whether the
 *  areas are read at all, or that each area is what puts particular labels in
 *  the list — an operator could tick Security and have no way to see which
 *  three labels that added. Now the area IS the row that carries its labels,
 *  and an area that is off shows what enabling it would add, so the effect of
 *  a checkbox is visible before it is clicked rather than after.
 *
 *  Attribution comes from the backend, which replays its own merge to produce
 *  it: two areas may define the same label name and the later one wins, so
 *  intersecting client-side would credit the wrong area — and crediting the
 *  wrong area tells the operator that unticking the wrong box removes it. */
function ClassificationSection({ binding }: { binding: FlagsTabBinding }) {
  const selected = new Set(binding.classificationAreas)
  const savingMode = binding.isSaving(SAVING_CLASSIFICATION_MODE)
  const savingAreas = binding.isSaving(SAVING_CLASSIFICATION_AREAS)
  const simple = binding.classificationMode === "simple"

  const toggle = (key: string, on: boolean) => {
    const next = on
      ? [...binding.classificationAreas, key]
      : binding.classificationAreas.filter((a) => a !== key)
    binding.setClassificationAreas(next)
  }

  // Labels no area owns: the `fact` fallback, and the whole fixed vocabulary
  // in simple mode.
  const unowned = binding.classificationLabels.filter((l) => l.area === null)
  const byArea = new Map<string, typeof binding.classificationLabels>()
  for (const label of binding.classificationLabels) {
    if (label.area === null) continue
    byArea.set(label.area, [...(byArea.get(label.area) ?? []), label])
  }

  return (
    <Section
      name="classification"
      help="Classification always runs — there is no on/off flag, only which model-backed classifier serves the purpose (set on the LLM tab via classifier_kind). What these controls decide is the label space: the exact set of values the classifier may write to a memory's classified_type. Anything the model emits outside that set is normalised back into it."
      meta={`${binding.classificationMode} · ${binding.classificationLabels.length} labels`}
    >
      <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
        <span className="font-mono text-sm font-semibold whitespace-nowrap">
          classification_mode
        </span>
        <HelpTip label="About classification_mode">
          `simple` keeps the seven-type vocabulary extraction already emits,
          which lets the pipeline fold classification into the single
          extraction call instead of a second LLM round-trip. `expanded` opens
          the per-area label space and forces two concurrent calls. The mode
          also changes the extraction prompt, so re-extracting the same content
          under a different mode is not bit-identical.
        </HelpTip>
        <span className="flex-1" />
        <SavingMark saving={savingMode} />
        <SegmentGroup
          value={binding.classificationMode}
          onValueChange={(v: string) =>
            binding.setClassificationMode(v as "simple" | "expanded")
          }
          aria-label="classification_mode"
          disabled={savingMode}
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="simple">simple</SegmentGroupItem>
          <SegmentGroupItem value="expanded">expanded</SegmentGroupItem>
        </SegmentGroup>
      </div>

      {/* The one sentence that ties the three controls together. */}
      <p className="text-muted-foreground pl-0.5 text-sm">
        {simple ? (
          <>
            In <span className="font-mono">simple</span> mode the label space is{" "}
            <b className="text-foreground font-semibold">fixed</b> and the areas
            below are <b className="text-warning font-semibold">not read at
            all</b> — ticking them changes nothing until the mode is expanded.
          </>
        ) : (
          <>
            In <span className="font-mono">expanded</span> mode the label space
            is <span className="font-mono">fact</span> plus the union of every
            enabled area below. Each area contributes the labels shown on its
            row.
          </>
        )}
      </p>

      <div className="border-border bg-card flex flex-col gap-2.5 rounded-md border px-3 py-2.5">
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
          <SavingMark saving={savingAreas} />
          <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
            {binding.classificationLabels.length} label
            {binding.classificationLabels.length === 1 ? "" : "s"} ·{" "}
            {binding.classificationAreas.length} of{" "}
            {binding.availableAreas.length} areas enabled
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

        {binding.availableAreas.map((area) => {
          const locked = area.key === "general"
          const on = selected.has(area.key)
          const contributed = byArea.get(area.key) ?? []
          // An area that is off has contributed nothing, so its own type list
          // is the preview. It is what enabling it *would* add — subject to a
          // name another enabled area already owns.
          const preview = area.types.map((name) => ({ name }))
          return (
            <div
              key={area.key}
              className="border-border/50 flex flex-wrap items-baseline gap-2 border-t border-dashed pt-2"
            >
              <label
                className="flex w-32 shrink-0 items-center gap-2 text-sm"
                htmlFor={`area-${area.key}`}
              >
                <Checkbox
                  id={`area-${area.key}`}
                  checked={on}
                  // Deliberately still writable in simple mode. The value is
                  // durable and takes effect the moment the mode flips, so
                  // setting areas up first is a real workflow; disabling the
                  // box would refuse a preference it is perfectly able to
                  // store. The row says it is not read yet — that is the
                  // honest half, not taking the control away.
                  disabled={locked || savingAreas}
                  aria-label={area.key}
                  onCheckedChange={(c) => toggle(area.key, c === true)}
                />
                <span
                  className={cn(
                    "truncate",
                    (!on || simple) && "text-muted-foreground",
                  )}
                >
                  {area.display_name}
                </span>
              </label>
              <div className="flex flex-1 flex-wrap items-baseline gap-1.5">
                {simple ? (
                  <span className="text-muted-foreground text-sm italic">
                    not read in simple mode
                  </span>
                ) : on ? (
                  contributed.length > 0 ? (
                    contributed.map((label) => (
                      <LabelChip key={label.name} label={label} />
                    ))
                  ) : (
                    <span className="text-muted-foreground text-sm italic">
                      contributes nothing — every name it defines is already
                      owned by another enabled area
                    </span>
                  )
                ) : (
                  <>
                    <span className="text-muted-foreground font-mono text-[10px]">
                      would add
                    </span>
                    {preview.map((label) => (
                      <LabelChip key={label.name} label={label} muted />
                    ))}
                  </>
                )}
              </div>
              <span className="text-muted-foreground w-10 shrink-0 text-right font-mono text-[10px]">
                {simple ? "—" : on ? `+${contributed.length}` : area.types.length}
              </span>
            </div>
          )
        })}
      </div>
    </Section>
  )
}

export function FlagsTab() {
  const binding = useFlagsTabBinding()

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
          and written. Job schedules are edited on the Jobs page, not here, and
          which model serves each purpose is on the LLM tab. An arm at 0 renders
          as inactive rather than being omitted, and a flag with no recorded
          gate-ledger win renders visibly unmeasured — flipping it stays
          possible, but is never quietly assumed proven.
        </HelpTip>
      </div>
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 rounded-lg border px-4 py-2.5">
        <span className="text-sm font-semibold">Flags</span>
        <span className="text-muted-foreground font-mono text-sm">
          {`${activeArms} of ${allArms.length} arms active · ${flagsOn} of ${binding.behavioralFlags.length} feature flags on · ${binding.overridesWritten} overrides written`}
        </span>
        <span className="ml-auto">
          <SurfaceStateChip state="populated" />
        </span>
      </div>

      <div className="flex flex-col gap-4">
        <Section
          name="rank_fusion_factor arms"
          help="Per-row multipliers applied to a row's fused rrf_score after Reciprocal Rank Fusion. Each is a no-op at exactly 0 — the factor is 1, so the arm is built and wired but moves nothing. Each flips only on a measured retrieval win reported with its latency and token twin, recorded in the gate ledger's arm activation log, never by intuition."
          meta={`${activeFusionArms} of ${binding.fusionArms.length} active`}
        >
          {binding.fusionArms.map((arm) => (
            <ArmRow
              key={arm.key}
              arm={arm}
              saving={binding.isSaving(arm.key)}
              onCommit={(v) => binding.saveArm(arm.key, v)}
            />
          ))}
        </Section>

        <Section
          name="feature flags"
          help="Plain on/off switches, distinct from the weighted arms above: each gates a whole code path rather than scaling a score. relation_rescue is the only surviving ingestion-side flag; the other two govern retrieval."
          meta={`${flagsOn} of ${binding.behavioralFlags.length} on`}
        >
          {binding.behavioralFlags.map((flag) => (
            <BehavioralFlagRow
              key={flag.key}
              flag={flag}
              saving={binding.isSaving(flag.key)}
              onToggle={(enabled) =>
                binding.setBehavioralFlag(flag.key, enabled)
              }
            />
          ))}
        </Section>

        <Section
          name="context match boost"
          help="The magnitude of the applies_when context boost (doc 07 §6). Its own group because it acts on a match outcome rather than on a stored column: at 0 matching still labels every row and still counts conflicts — only the multiplier goes quiet."
        >
          <ArmRow
            arm={binding.contextBoost}
            saving={binding.isSaving(binding.contextBoost.key)}
            onCommit={(v) => binding.saveArm(binding.contextBoost.key, v)}
          />
        </Section>

        <Section
          name="graph augmentation — RRF list weights + *_enabled flags"
          help="Doc 07 §4. Each *_enabled flag turns on a producer of ranked candidates from the entity graph, and its paired w_* is that list's weight in the fusion — a LIST weight, not a per-row multiplier, so it scales how much the whole list counts rather than boosting individual rows. All three land inert so retrieval is byte-identical to the vector+FTS hybrid until one is measured. A flag on with its weight still at 0 produces candidates that fuse at zero weight, which is why the pairing is shown together."
          meta={
            binding.graphFlags.length
              ? `${channelsOn} of ${binding.graphFlags.length} channels on`
              : undefined
          }
        >
          {binding.graphAugmentationAvailable ? (
            binding.graphFlags.map((flag) => {
              const paired = flag.paired_arm
              return (
                <div
                  key={flag.key}
                  className="border-border bg-card flex flex-col gap-2 rounded-md border px-3 py-2.5"
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-mono text-sm font-semibold">
                      {flag.key}
                    </span>
                    <HelpTip label={`About ${flag.key}`}>{flag.desc}</HelpTip>
                    <span className="flex-1" />
                    <ActivationNote taskId={flag.activatesWith} />
                    <SourceTag source={flag.source} />
                    <SavingMark saving={binding.isSaving(flag.key)} />
                    <Switch
                      checked={flag.enabled}
                      onCheckedChange={(on) =>
                        binding.setGraphFlag(flag.key, on)
                      }
                      aria-label={flag.key}
                      disabled={binding.isSaving(flag.key)}
                    />
                    {flag.unmeasured && <UnmeasuredTag />}
                  </div>
                  {paired ? (
                    <div className="flex flex-wrap items-center gap-2 pl-0.5">
                      <span className="text-muted-foreground font-mono text-sm">
                        paired weight{" "}
                        <b className="text-foreground font-sans font-semibold">
                          {paired.key}
                        </b>
                      </span>
                      <HelpTip label={`About ${paired.key}`}>
                        {paired.desc}
                      </HelpTip>
                      <span className="flex-1" />
                      <SourceTag source={paired.source} />
                      <ArmInput
                        arm={paired}
                        onCommit={(v) => binding.saveArm(paired.key, v)}
                      />
                      <SavingMark saving={binding.isSaving(paired.key)} />
                      <ArmPill value={paired.value} />
                    </div>
                  ) : (
                    <p className="text-muted-foreground pl-0.5 text-sm italic">
                      {flag.no_weight_note}
                    </p>
                  )}
                </div>
              )
            })
          ) : binding.isLoading ? null : (
            <NotYetImplemented
              label="ppr_enabled · dual_level_enabled · community_injection_enabled"
              note="Could not read /config/feature-flags — the flags are still at whatever the config row holds; only this editor is unavailable."
            />
          )}
        </Section>

        <Section
          name="pipeline & embedding tunables"
          help="Throughput and cache knobs in the same feature_flags row as the arms. None of them gates a phase or changes what gets stored — they trade provider rate-limit headroom, memory and batch latency against each other. Each accepts a bounded range the API enforces; a value outside it is refused rather than clamped."
          meta={
            tunablesOverridden
              ? `${tunablesOverridden} overridden`
              : "all at coded defaults"
          }
        >
          {binding.tunables.map((tunable) => (
            <TunableRow
              key={tunable.key}
              tunable={tunable}
              saving={binding.isSaving(tunable.key)}
              onCommit={(v) => binding.saveTunable(tunable.key, v)}
            />
          ))}
        </Section>

        <ClassificationSection binding={binding} />

        <RepoAllowlistSection binding={binding} />

        <CorroborationSection binding={binding} />
      </div>
    </div>
  )
}
