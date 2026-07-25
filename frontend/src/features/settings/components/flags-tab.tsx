import { useState } from "react"
import { Timer } from "lucide-react"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { activeArmCount, sourceLabel } from "@/demo/settings"
import { useDemoFlags, useDemoJobs } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoRankArm } from "@/demo/types"
import { ArmPill } from "./arm-pill"

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
  const [draft, setDraft] = useState(String(arm.value))
  const commit = () => {
    const num = Number(draft)
    if (Number.isFinite(num) && num !== arm.value) onCommit(num)
    else setDraft(String(arm.value))
  }
  return (
    <Input
      type="number"
      step={arm.step ?? 1}
      value={draft}
      aria-label={arm.key}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => e.key === "Enter" && commit()}
      className={cn("w-24 text-right font-mono", className)}
    />
  )
}

function ArmRow({ arm }: { arm: DemoRankArm }) {
  const saveArm = useDemoStore((s) => s.saveArm)
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
      <span className="text-muted-foreground min-w-40 flex-1 text-sm">
        {arm.desc}
      </span>
      <SourceTag source={arm.source} />
      <ArmInput arm={arm} onCommit={(v) => saveArm(arm.key, v)} />
      <ArmPill value={arm.value} />
    </div>
  )
}

function GroupHead({ name, doc }: { name: string; doc: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-2">
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {name}
      </span>
      <span className="text-muted-foreground/80 font-mono text-[10px]">
        {doc}
      </span>
    </div>
  )
}

export function FlagsTab() {
  const flags = useDemoFlags()
  const jobs = useDemoJobs()
  const saveArm = useDemoStore((s) => s.saveArm)
  const setGraphFlag = useDemoStore((s) => s.setGraphFlag)
  const saveCorroboration = useDemoStore((s) => s.saveCorroboration)

  const active = activeArmCount(flags)
  const flagsOn = flags.graph_flags.filter((f) => f.enabled).length
  const corr = flags.corroboration

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        The tunables tab: the seven <code className="font-mono">w_*</code>{" "}
        ranking-arm weights, the three graph-augmentation flags, the
        corroboration promotion gate, and a job-cadence summary. Every value is
        a config row read through the merge-over-coded-defaults; nothing here
        is computed, only read and written. An arm at 0 renders as
        built-but-unspent, never omitted, and raising it is a deliberate,
        measured activation.
      </p>
      <ModuleSurface
        title="Flags"
        state="populated"
        meta={`${active} of 7 arms active · ${flagsOn} of 3 graph flags on · ${flags.overrides_written} overrides written`}
      >
        <div className="flex flex-col gap-2">
          <GroupHead name="rank_fusion_factor arms" doc="doc 04 §9 · doc 07 §3" />
          {flags.fusion_arms.map((arm) => (
            <ArmRow key={arm.key} arm={arm} />
          ))}
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead
            name="graph augmentation — RRF list weights + *_enabled flags"
            doc="doc 07 §4 / §11"
          />
          {flags.graph_flags.map((flag) => {
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
                <span className="text-muted-foreground min-w-40 flex-1 text-sm">
                  {flag.desc}
                </span>
                <SourceTag source={flag.source} />
                <Switch
                  checked={flag.enabled}
                  onCheckedChange={(on) => setGraphFlag(flag.key, on)}
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
                  <ArmInput
                    arm={paired}
                    onCommit={(v) => saveArm(paired.key, v)}
                    className="w-20"
                  />
                  <ArmPill value={paired.value} />
                </div>
              ) : (
                <p className="text-muted-foreground pl-0.5 text-sm italic">
                  {flag.no_weight_note}
                </p>
              )}
            </div>
            )
          })}
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="context match boost" doc="doc 07 §6" />
          <ArmRow arm={flags.context_boost} />
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="corroboration promotion gate" doc="doc 08 §4.1" />
          <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
            <span className="font-mono text-sm font-semibold">
              corroboration_n_base
            </span>
            <span className="text-muted-foreground min-w-40 flex-1 text-sm">
              distinct origin_keys required to promote candidate → corroborated,
              default case
            </span>
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
              onCommit={(v) => saveCorroboration(v, corr.n_diverse)}
              className="w-16"
            />
          </div>
          <div className="border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2">
            <span className="font-mono text-sm font-semibold">
              corroboration_n_diverse
            </span>
            <span className="text-muted-foreground min-w-40 flex-1 text-sm">
              lowered N when the diversity/time gate below is met
            </span>
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
              onCommit={(v) => saveCorroboration(corr.n_base, v)}
              className="w-16"
            />
          </div>
          <div className="border-border bg-muted/15 text-muted-foreground rounded-md border border-dashed px-3 py-2.5 text-sm">
            <b className="text-foreground font-semibold">Diversity/time gate:</b>{" "}
            {corr.gate_note}
          </div>
        </div>

        <div className="border-border flex flex-col gap-2 border-t border-dashed pt-3">
          <GroupHead name="job cadences" doc="doc 02 §5.3 · JobRegistry" />
          {jobs.map((job) => (
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
            Cron only, read-mostly summary — each job&apos;s{" "}
            <code className="font-mono">min_interval_seconds</code> floor,{" "}
            <code className="font-mono">max_run_seconds</code> ceiling, enabled
            switch, and <code className="font-mono">config_schema</code> fields
            are edited in the dedicated Settings → Jobs tab, not duplicated
            here.
          </p>
        </div>
      </ModuleSurface>
    </div>
  )
}
