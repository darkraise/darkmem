import { useState } from "react"
import { Timer } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import { HelpTip, NumberField } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { armStatus, sourceLabel } from "@/demo/settings"
import type { DemoBehavioralFlag, DemoRankArm } from "@/features/settings/types"
import { ArmPill } from "./arm-pill"
import {
  useFlagsTabBinding,
  type FlagsTabBinding,
} from "../use-flags-tab-binding"

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
 *  (T1.57 ruling 3, doc 17). */
function UnmeasuredTag() {
  return (
    <span className="border-warning/50 text-warning rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap">
      unmeasured
    </span>
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
  onCommit,
}: {
  arm: DemoRankArm
  help?: string
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
      <ArmPill value={arm.value} />
      {arm.unmeasured && <UnmeasuredTag />}
    </div>
  )
}

function GroupHead({
  name,
  doc,
  help,
}: {
  name: string
  doc: string
  help?: string
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {name}
      </span>
      <span className="text-muted-foreground/80 font-mono text-[10px]">
        {doc}
      </span>
      {help && <HelpTip label={`About ${name}`}>{help}</HelpTip>}
    </div>
  )
}

function BehavioralFlagRow({
  flag,
  onToggle,
}: {
  flag: DemoBehavioralFlag
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
      <Switch
        checked={flag.enabled}
        onCheckedChange={onToggle}
        aria-label={flag.key}
      />
      {flag.unmeasured && <UnmeasuredTag />}
    </div>
  )
}

/** Mirrors `CodeBucketsUnavailable` in llm-tab.tsx: no backend row exists
 *  for this yet, in either mode, so the honest move is a staged note rather
 *  than fetching against a guessed contract (the T1.61 buffer-monitor
 *  precedent) or silently omitting the section (invariant 23). */
function NotYetImplemented({
  label,
  note,
}: {
  label: string
  note: string
}) {
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
  const dirty =
    patterns.join("\n") !== binding.allowlistPatterns.join("\n")

  return (
    <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
      <GroupHead
        name="repo auto-provision allowlist"
        doc="doc 18 §6 · config row repo_allowlist"
        help="Repo hints arrive over the unauthenticated MCP door; an empty allowlist refuses every hint (auto-provision inert). Patterns are host, *.host, or host/path-prefix — validated with the exact parse the SSRF gate itself runs a pattern through, so this editor and the gate can never disagree on 'allowed'."
      />
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
            disabled={!dirty}
            onClick={() => {
              binding.saveAllowlist(patterns)
              setSaved(true)
            }}
          >
            Save allowlist
          </Button>
          {saved && (
            <span className="text-success font-mono text-sm">saved</span>
          )}
        </div>
      </div>
    </div>
  )
}

export function FlagsTab() {
  const binding = useFlagsTabBinding()

  const activeArms =
    [...binding.fusionArms, binding.contextBoost].filter(
      (a) => armStatus(a.value) === "active",
    ).length
  const totalArms = binding.fusionArms.length + 1
  const flagsOn = binding.behavioralFlags.filter((f) => f.enabled).length
  const corr = binding.corroboration

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Ranking-arm weights, behavioral feature flags, the corroboration
          promotion gate, the repo auto-provision allowlist, and job
          cadences — config rows read through merge-over-coded-defaults.
        </span>
        <HelpTip label="About the Flags tab">
          The tunables tab: the rank_fusion_factor w_* arms, the plain
          on/off feature flags, the corroboration promotion gate, the
          repo_allowlist SSRF gate input, and a job-cadence summary. Every
          value is a config row read through the merge-over-coded-defaults;
          nothing here is computed, only read and written. An arm at 0
          renders as inactive, never omitted, and a flag with no recorded
          gate-ledger win renders visibly unmeasured — flipping it is
          possible, but never quietly assumed proven.
        </HelpTip>
      </div>
      <ModuleSurface
        title="Flags"
        state="populated"
        meta={`${activeArms} of ${totalArms} arms active · ${flagsOn} of ${binding.behavioralFlags.length} feature flags on · ${binding.overridesWritten} overrides written`}
      >
        <div className="flex flex-col gap-2">
          <GroupHead name="rank_fusion_factor arms" doc="doc 04 §9 · doc 07 §3" />
          {binding.fusionArms.map((arm) => (
            <ArmRow
              key={arm.key}
              arm={arm}
              onCommit={(v) => binding.saveArm(arm.key, v)}
            />
          ))}
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="feature flags" doc="doc 07 §11 · behavioral on/off" />
          {binding.behavioralFlags.map((flag) => (
            <BehavioralFlagRow
              key={flag.key}
              flag={flag}
              onToggle={(enabled) =>
                binding.setBehavioralFlag(flag.key, enabled)
              }
            />
          ))}
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="context match boost" doc="doc 07 §6" />
          <ArmRow
            arm={binding.contextBoost}
            onCommit={(v) => binding.saveArm(binding.contextBoost.key, v)}
          />
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead
            name="graph augmentation — RRF list weights + *_enabled flags"
            doc="doc 07 §4 / §11"
          />
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
                    <SourceTag source={flag.source} />
                    <Switch
                      checked={flag.enabled}
                      onCheckedChange={(on) =>
                        binding.setGraphFlag(flag.key, on)
                      }
                      aria-label={flag.key}
                    />
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
          ) : (
            <NotYetImplemented
              label="ppr_enabled · dual_level_enabled · community_injection_enabled"
              note="not yet exposed via the API — there is no repo_allowlist-style config row for these yet, in either mode (doc 07 §4/§11 is a future epic's scope)."
            />
          )}
        </div>

        <RepoAllowlistSection binding={binding} />

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead
            name="corroboration promotion gate"
            doc="doc 08 §4.1"
            help={`Diversity/time gate: ${corr.gate_note || "candidate → corroborated, owned by T2.03 (the verification ladder)."}`}
          />
          {binding.corroborationAvailable ? (
            <>
              <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
                <span className="font-mono text-sm font-semibold">
                  corroboration_n_base
                </span>
                <HelpTip label="About corroboration_n_base">
                  distinct origin_keys required to promote candidate →
                  corroborated, default case
                </HelpTip>
                <span className="flex-1" />
                <SourceTag source={corr.source} />
                <ArmInput
                  arm={{
                    key: "corroboration_n_base",
                    desc: "",
                    value: corr.n_base,
                    coded_default: 3,
                    source: corr.source,
                    step: 1,
                  }}
                  onCommit={(v) =>
                    binding.saveCorroboration(v, corr.n_diverse)
                  }
                  className="w-16"
                />
              </div>
              <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
                <span className="font-mono text-sm font-semibold">
                  corroboration_n_diverse
                </span>
                <HelpTip label="About corroboration_n_diverse">
                  lowered N when the diversity/time gate is met — see the
                  group help icon for the full gate rule. {corr.gate_note}
                </HelpTip>
                <span className="flex-1" />
                <SourceTag source={corr.source} />
                <ArmInput
                  arm={{
                    key: "corroboration_n_diverse",
                    desc: "",
                    value: corr.n_diverse,
                    coded_default: 2,
                    source: corr.source,
                    step: 1,
                  }}
                  onCommit={(v) => binding.saveCorroboration(corr.n_base, v)}
                  className="w-16"
                />
              </div>
            </>
          ) : (
            <NotYetImplemented
              label="corroboration_n_base · corroboration_n_diverse"
              note="not yet exposed via the API — the verification ladder (candidate → corroborated) is E2/T2.03 scope; no config row exists yet, in either mode."
            />
          )}
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="job cadences" doc="doc 02 §5.3 · JobRegistry" />
          {binding.jobs.map((job) => (
            <div
              key={job.key}
              className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-1.5 text-sm"
            >
              <Timer aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
              <span className="font-mono font-semibold whitespace-nowrap">
                {job.key}
              </span>
              <code className="text-muted-foreground font-mono text-sm">
                {job.cron}
              </code>
              <span className="text-muted-foreground ml-auto text-sm whitespace-nowrap">
                {job.cron_label}
              </span>
            </div>
          ))}
          <p className="text-muted-foreground text-sm">
            Read-only summary — floors, ceilings, enabled switches, and{" "}
            <code className="font-mono">config_schema</code> fields are edited
            in the dedicated Settings → Jobs tab, not duplicated here.
          </p>
        </div>
      </ModuleSurface>
    </div>
  )
}
