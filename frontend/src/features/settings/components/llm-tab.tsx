import { useState } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  ArrowDownUp,
  Bot,
  Braces,
  Cloud,
  Cpu,
  FileText,
  Filter,
  ShieldCheck,
  Tag,
  Trash2,
  type LucideIcon,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Switch } from "darkraise-ui/components/switch"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { cn } from "darkraise-ui/lib"
import {
  HelpTip,
  IconSegmented,
  type IconSegmentedOption,
} from "@/components/darkmem"
import { API_KINDS, embeddingKindWarning, validateParamsJson } from "@/demo/settings"
import type { ApiKind, DemoCodeBucket, DemoLLMPurpose } from "@/features/settings/types"
import type { TierCLLMPurpose } from "../llm-tier-c-purposes"
import {
  useLLMTabBinding,
  type LLMTabBinding,
  type TierCPurposeView,
} from "../use-llm-tab-binding"

const PURPOSE_ICONS: Record<DemoLLMPurpose["purpose"], LucideIcon> = {
  embedding: Braces,
  extraction: Filter,
  classification: Tag,
  summarization: FileText,
  reranker: ArrowDownUp,
  reasoning: Bot,
  synthesis: FileText,
}

const TIER_C_PURPOSE_ICONS: Record<TierCLLMPurpose["purpose"], LucideIcon> = {
  verification: ShieldCheck,
}

type Draft = {
  model: string
  api_kind: ApiKind
  base_url: string
  api_key: string
  params: string
  dimensions: string
  reasoning: boolean
}

function toDraft(p: DemoLLMPurpose): Draft {
  return {
    model: p.model,
    api_kind: p.api_kind,
    base_url: p.base_url,
    api_key: p.api_key,
    params: p.params,
    dimensions: p.dimensions !== undefined ? String(p.dimensions) : "",
    reasoning: p.reasoning ?? false,
  }
}

function dirtyFields(p: DemoLLMPurpose, d: Draft): string[] {
  const base = toDraft(p)
  return (Object.keys(base) as (keyof Draft)[]).filter(
    (k) => base[k] !== d[k],
  )
}

function Field({
  label,
  span2,
  children,
}: {
  label: string
  span2?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={cn("flex flex-col gap-1", span2 && "col-span-2")}>
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {label}
      </span>
      {children}
    </div>
  )
}

function PurposeCard({
  purpose,
  binding,
}: {
  purpose: DemoLLMPurpose
  binding: LLMTabBinding
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(purpose))
  const dirty = dirtyFields(purpose, draft)
  const paramsCheck = validateParamsJson(draft.params)
  const isEmbedding = purpose.purpose === "embedding"
  const warning = isEmbedding ? embeddingKindWarning(draft.api_kind) : null
  const Icon = PURPOSE_ICONS[purpose.purpose]
  const wide = purpose.purpose === "summarization"

  const patch = (p: Partial<Draft>) => setDraft((d) => ({ ...d, ...p }))

  const save = () => {
    if (!paramsCheck.ok) return
    // Only the changed fields are written — the live-reload trace names
    // exactly what the save touched.
    const changed: Partial<Omit<DemoLLMPurpose, "purpose">> = {}
    for (const key of dirty) {
      switch (key) {
        case "model":
          changed.model = draft.model
          break
        case "api_kind":
          changed.api_kind = draft.api_kind
          break
        case "base_url":
          changed.base_url = draft.base_url
          break
        case "api_key":
          changed.api_key = draft.api_key
          break
        case "params":
          changed.params = draft.params
          break
        case "dimensions":
          changed.dimensions = Number(draft.dimensions) || 0
          break
        case "reasoning":
          changed.reasoning = draft.reasoning
          break
      }
    }
    binding.savePurpose(purpose.purpose, changed)
  }

  return (
    <div
      className={cn(
        "border-border bg-card flex flex-col gap-2.5 rounded-lg border p-4",
        wide && "sm:col-span-2",
        dirty.length > 0 && "border-warning/50 bg-warning/4",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Icon aria-hidden className="text-primary h-4 w-4" />
        <span className="font-mono text-sm font-semibold">
          {purpose.purpose}
        </span>
        <HelpTip label={`About the ${purpose.purpose} purpose`}>
          {purpose.role}
          {purpose.hint && ` — ${purpose.hint.text}`}
        </HelpTip>
        <span className="border-border bg-muted text-muted-foreground ml-auto rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap">
          {purpose.tier}
        </span>
      </div>

      {purpose.purpose === "classification" && (
        <ClassifierKindRow binding={binding} />
      )}

      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        <Field label="model">
          <Input
            value={draft.model}
            aria-label={`${purpose.purpose} model`}
            onChange={(e) => patch({ model: e.target.value })}
            className="font-mono"
          />
        </Field>
        <Field label="api_kind">
          <Select
            value={draft.api_kind}
            onValueChange={(v) => patch({ api_kind: v as ApiKind })}
          >
            <SelectTrigger
              aria-label={`${purpose.purpose} api_kind`}
              className="font-mono"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {API_KINDS.map((kind) => (
                <SelectItem key={kind} value={kind} className="font-mono">
                  {kind}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="base_url" span2>
          <Input
            value={draft.base_url}
            aria-label={`${purpose.purpose} base_url`}
            onChange={(e) => patch({ base_url: e.target.value })}
            className="font-mono"
          />
        </Field>
        <Field label="api_key">
          <Input
            type="password"
            value={draft.api_key}
            placeholder={
              draft.api_kind === "ollama" ? "not required for ollama" : ""
            }
            aria-label={`${purpose.purpose} api_key`}
            onChange={(e) => patch({ api_key: e.target.value })}
            className="font-mono"
          />
        </Field>
        {isEmbedding ? (
          <Field label="dimensions">
            <Input
              type="number"
              value={draft.dimensions}
              aria-label="embedding dimensions"
              onChange={(e) => patch({ dimensions: e.target.value })}
              className="font-mono"
            />
          </Field>
        ) : (
          <Field label="reasoning">
            {/* The control is shorter than the inputs beside it, so it centres
                inside the same row height rather than sitting on the baseline
                the taller segmented pair used to fill. */}
            <div className="flex h-9 items-center">
              <Switch
                checked={draft.reasoning}
                onCheckedChange={(next) => patch({ reasoning: next })}
                aria-label={`${purpose.purpose} reasoning`}
              />
            </div>
          </Field>
        )}
        <Field label="params (jsonb)" span2>
          <Input
            value={draft.params}
            aria-label={`${purpose.purpose} params`}
            onChange={(e) => patch({ params: e.target.value })}
            className={cn(
              "font-mono",
              !paramsCheck.ok && "border-destructive",
            )}
          />
          {!paramsCheck.ok && (
            <span className="text-destructive text-sm">
              {paramsCheck.error}
            </span>
          )}
        </Field>
      </div>

      {/* Derived warnings stay visible — a 404-on-every-request footgun is
          never demoted to a hover. */}
      {warning && <p className="text-warning text-sm">{warning}</p>}
      {!warning && purpose.hint?.tone === "caution" && (
        <p className="text-warning text-sm">{purpose.hint.text}</p>
      )}

      {wide &&
        (binding.buckets ? (
          <CodeBuckets
            buckets={binding.buckets}
            saveCodeBucket={binding.saveCodeBucket!}
          />
        ) : (
          <CodeBucketsUnavailable />
        ))}

      <div className="flex items-center gap-2.5 pt-1">
        <Button
          size="sm"
          variant="outline"
          className="border-primary/60 text-primary"
          disabled={dirty.length === 0 || !paramsCheck.ok}
          onClick={save}
        >
          Save
        </Button>
        {dirty.length > 0 && (
          <span className="text-muted-foreground ml-auto text-sm">
            edited: {dirty.join(", ")} — unsaved
          </span>
        )}
      </div>
    </div>
  )
}

function TierCPurposeCard({ purpose }: { purpose: TierCPurposeView }) {
  const Icon = TIER_C_PURPOSE_ICONS[purpose.purpose]
  const live = purpose.activatesWith === null
  return (
    <div className="border-border bg-card/60 flex flex-col gap-2.5 rounded-lg border border-dashed p-4 opacity-90">
      <div className="flex flex-wrap items-center gap-2">
        <Icon aria-hidden className="text-muted-foreground h-4 w-4" />
        <span className="font-mono text-sm font-semibold">
          {purpose.purpose}
        </span>
        <HelpTip label={`About the ${purpose.purpose} purpose`}>
          {purpose.role}
        </HelpTip>
        <span className="border-border bg-muted text-muted-foreground ml-auto rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap">
          {live ? "tier c · live" : "tier c · inert"}
        </span>
      </div>
      <p className="text-muted-foreground text-sm">
        {live ? (
          <>
            Seeded row, resolvable, and dispatched — this connection judges
            fact verification-ladder promotions today. Read-only by
            deliberate ruling (T2.106), not an oversight: its qualification
            record is G-D's gate evidence, pinned to this exact model
            identity, and a settings-form repoint is a real capability with
            a real failure mode. The judge already refuses to serve on a
            mismatched identity, but the write-time guard that would make
            editing this row safe means touching the verification ladder's
            enforcement path — out of scope here.
          </>
        ) : (
          <>
            Seeded row, resolvable, no consumer yet — activates with{" "}
            <span className="font-mono">{purpose.activatesWith}</span>.
            Rendered rather than omitted: a hidden inert purpose reads as
            "not configured", the same misreading a dormant w_* arm at zero
            would cause if it were left off the Flags tab.
          </>
        )}
      </p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        <Field label="model">
          <Input value={purpose.model} disabled className="font-mono" />
        </Field>
        <Field label="api_kind">
          <Input value={purpose.api_kind} disabled className="font-mono" />
        </Field>
      </div>
    </div>
  )
}

const CLASSIFIER_KIND_OPTIONS: ReadonlyArray<IconSegmentedOption<"llm" | "local">> = [
  { value: "llm", label: "LLM-backed classifier", icon: Cloud },
  { value: "local", label: "In-process classifier", icon: Cpu },
]

function ClassifierKindRow({ binding }: { binding: LLMTabBinding }) {
  return (
    <div className="border-primary/40 bg-primary/5 flex flex-wrap items-center gap-2.5 rounded-md border border-dashed px-2.5 py-2">
      <span className="font-mono text-sm">classifier_kind</span>
      <IconSegmented
        value={binding.classifierKind}
        options={CLASSIFIER_KIND_OPTIONS}
        onChange={binding.setClassifierKind}
        label="classifier_kind"
      />
      <HelpTip label="About classifier_kind">
        re-homes the dropped ml_profile_ref indirection inline — a two-value
        field on this row, not a picker over a deleted table.
      </HelpTip>
    </div>
  )
}

function CodeBuckets({
  buckets,
  saveCodeBucket,
}: {
  buckets: DemoCodeBucket[]
  saveCodeBucket: NonNullable<LLMTabBinding["saveCodeBucket"]>
}) {
  return (
    <div className="border-border flex flex-col gap-2 border-t border-dashed pt-2.5">
      <div className="flex items-center gap-1.5">
        <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
          code-summarization buckets
        </span>
        <HelpTip label="About code-summarization buckets">
          each bucket carries its own model + prompt over the one
          summarization connection.
        </HelpTip>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-3">
        {buckets.map((bucket) => (
          <div
            key={bucket.key}
            className="border-border bg-background flex flex-col gap-1.5 rounded-md border px-2.5 py-2"
          >
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-sm font-semibold">
                {bucket.key}
              </span>
              <HelpTip label={`About the ${bucket.key} bucket`}>
                {bucket.note}
              </HelpTip>
            </div>
            <Input
              value={bucket.model}
              aria-label={`${bucket.key} bucket model`}
              onChange={(e) => saveCodeBucket(bucket.key, e.target.value)}
              className="font-mono"
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function CodeBucketsUnavailable() {
  return (
    <div className="border-border text-muted-foreground flex flex-col gap-1 border-t border-dashed pt-2.5 text-sm">
      <span className="font-mono text-[10px] tracking-wide uppercase">
        code-summarization buckets
      </span>
      <span>
        not yet exposed via the API — there is no backend row for these,
        in either mode.
      </span>
    </div>
  )
}

function RemovedChrome() {
  return (
    <div className="border-border bg-muted/12 flex flex-col gap-2 rounded-lg border border-dashed p-4">
      <div className="text-muted-foreground flex items-center gap-2 font-mono text-[10px] tracking-wide uppercase">
        <Trash2 aria-hidden className="h-3.5 w-3.5" />
        removed with the flattening — not rendered, not disabled, deleted
        <HelpTip label="Why the provider and profile tabs were removed">
          darkmem is not an LLM proxy: each purpose is one row the operator
          edits directly, with the columns provider_ref, profile_ref, and
          ml_profile_ref dropped from every purpose row. A profile picker over
          a schema with no profiles table would be scaffolding rendered as a
          feature — the honest move is deletion, not a greyed-out control.
          The dead LLMProvidersPanel / LLMProfilesPanel / MLProfilesPanel
          components themselves are gone from the source tree, not merely
          unmounted.
        </HelpTip>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {["llm-providers tab", "llm-profiles tab", "ml-profiles tab"].map(
          (label) => (
            <span
              key={label}
              className="border-border text-muted-foreground rounded-full border border-dashed px-2.5 py-0.5 font-mono text-sm line-through opacity-75"
            >
              {label}
            </span>
          ),
        )}
        {["provider_ref", "profile_ref", "ml_profile_ref"].map((col) => (
          <span
            key={col}
            className="text-muted-foreground font-mono text-sm line-through opacity-75"
          >
            {col}
          </span>
        ))}
      </div>
    </div>
  )
}

export function LLMTab() {
  const binding = useLLMTabBinding()

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Seven inline purpose cards — each a self-contained connection
          binding, including the seeded-inert `synthesis` purpose — plus
          `verification`, read-only here (T2.106: it judges the
          verification ladder and its qualification is a gate's evidence).
          A save live-reloads the orchestrator; no redeploy, no LLM_* env
          vars.
        </span>
        <HelpTip label="About the LLM tab">
          Each purpose is one row with no provider/profile indirection. Every
          vendor auth, reasoning-control, and structured-output quirk that
          api_kind selects is resolved by the backend orchestrator, never
          re-implemented here. A save rebuilds the orchestrator and takes
          effect without a redeploy.
        </HelpTip>
      </div>
      {/* Cards seed an editable draft from their `purpose` prop on mount and
          own it thereafter, which is right for an editor — a refetch must not
          overwrite what the reader is typing. The cost is that mounting one
          before the config arrives freezes the empty placeholder the binding
          builds from `query.data?.[p]`, which is why the fields used to stay
          blank until the tab was unmounted and remounted. Waiting for the
          first load is what makes the seed real; `isLoading` is false on
          every later refetch, so this does not flash between saves. */}
      {binding.isLoading ? (
        <div className="grid gap-3.5 sm:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-md" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2">
          {binding.purposes.map((purpose) => (
            <PurposeCard key={purpose.purpose} purpose={purpose} binding={binding} />
          ))}
          {binding.tierCPurposes.map((purpose) => (
            <TierCPurposeCard key={purpose.purpose} purpose={purpose} />
          ))}
        </div>
      )}
      <RemovedChrome />
    </div>
  )
}
