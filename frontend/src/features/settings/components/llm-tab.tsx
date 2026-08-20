import { useEffect, useState } from "react"
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
import {
  Combobox,
  ComboboxContent,
  ComboboxControl,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemText,
  ComboboxList,
  ComboboxTrigger,
} from "darkraise-ui/components/combobox"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"
import {
  HelpTip,
  IconSegmented,
  type IconSegmentedOption,
} from "@/components/darkmem"
import { validateParamsJson } from "@/demo/settings"
import { embeddingKindWarning } from "@/features/setup/api-kinds"
import {
  useLlmProviders,
  useProbeProviderModels,
} from "@/hooks/api/use-llm-providers-api"
import type { DemoCodeBucket, DemoLLMPurpose } from "@/features/settings/types"
import type { TierCLLMPurpose } from "../llm-tier-c-purposes"
import {
  useLLMTabBinding,
  type LLMTabBinding,
  type TierCPurposeView,
} from "../use-llm-tab-binding"
import { ProvidersPanel } from "./providers-panel"

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
  provider_name: string
  model: string
  params: string
  dimensions: string
  reasoning: boolean
}

function toDraft(p: DemoLLMPurpose): Draft {
  return {
    provider_name: p.provider_name,
    model: p.model,
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
  const Icon = PURPOSE_ICONS[purpose.purpose]
  const wide = purpose.purpose === "summarization"

  const { data: providersData } = useLlmProviders()
  const providers = providersData?.providers ?? []
  const selectedProvider = providers.find((p) => p.name === draft.provider_name)
  const warning = isEmbedding ? embeddingKindWarning(selectedProvider?.api_kind) : null

  const probe = useProbeProviderModels()
  const providerName = draft.provider_name
  useEffect(() => {
    if (!providerName) return
    probe.mutate({ name: providerName })
    // react-query's `mutate` identity is not guaranteed stable across
    // renders; depending on it here would re-probe every render instead of
    // only when the selected provider actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerName])
  const modelItems = (probe.data?.models ?? []).map((m) => ({
    value: m,
    label: m,
  }))

  const patch = (p: Partial<Draft>) => setDraft((d) => ({ ...d, ...p }))

  const save = () => {
    if (!paramsCheck.ok) return
    // Only the changed fields are written — the live-reload trace names
    // exactly what the save touched.
    const changed: Partial<Omit<DemoLLMPurpose, "purpose">> = {}
    for (const key of dirty) {
      switch (key) {
        case "provider_name":
          changed.provider_name = draft.provider_name
          break
        case "model":
          changed.model = draft.model
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
          <Combobox
            items={modelItems}
            inputValue={draft.model}
            onInputValueChange={(d) => patch({ model: d.value })}
            openOnClick
            openOnFocus
          >
            <ComboboxControl>
              <ComboboxInput
                aria-label={`${purpose.purpose} model`}
                placeholder="model id"
                className="font-mono"
              />
              <ComboboxTrigger />
            </ComboboxControl>
            <ComboboxContent>
              <ComboboxList>
                {modelItems.map((it) => (
                  <ComboboxItem key={it.value} item={it}>
                    <ComboboxItemText>{it.label}</ComboboxItemText>
                  </ComboboxItem>
                ))}
                <ComboboxEmpty>No models</ComboboxEmpty>
              </ComboboxList>
            </ComboboxContent>
          </Combobox>
          {probe.data?.error && (
            <span className="text-destructive text-sm">
              {probe.data.error}
            </span>
          )}
        </Field>
        <Field label="provider_name">
          <Select
            value={draft.provider_name}
            onValueChange={(v) => patch({ provider_name: v })}
          >
            <SelectTrigger
              aria-label={`${purpose.purpose} provider_name`}
              className="font-mono"
            >
              <SelectValue placeholder="no provider selected" />
            </SelectTrigger>
            <SelectContent>
              {providers.map((p) => (
                <SelectItem key={p.name} value={p.name} className="font-mono">
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
            deliberate ruling, not an oversight: its qualification
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
        <Field label="provider_name">
          <Input value={purpose.provider_name} disabled className="font-mono" />
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
        <HelpTip label="Why the profile-ref provider and profile tabs were removed">
          darkmem is not an LLM proxy: each purpose was one row the operator
          edited directly, with the columns provider_ref, profile_ref, and
          ml_profile_ref dropped from every purpose row. A profile picker over
          a schema with no profiles table would have been scaffolding
          rendered as a feature — the honest move was deletion, not a
          greyed-out control. The dead LLMProvidersPanel / LLMProfilesPanel /
          MLProfilesPanel components themselves are gone from the source
          tree, not merely unmounted. The Providers sub-tab above this card
          is not that tab reappearing: it edits a separate `llm_providers`
          connection row a purpose can point at, not a profile indirection
          column on the purpose row itself.
        </HelpTip>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {["llm-profiles tab", "ml-profiles tab"].map(
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
    <Tabs defaultValue="purposes">
      <TabsList>
        <TabsTrigger value="providers">Providers</TabsTrigger>
        <TabsTrigger value="purposes">Purposes</TabsTrigger>
      </TabsList>
      <TabsContent value="providers" className="pt-4">
        <ProvidersPanel />
      </TabsContent>
      <TabsContent value="purposes" className="pt-4">
        <div className="space-y-4">
          <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
            <span>
              Seven purpose cards — each picking a provider from the
              Providers sub-tab plus the model and params that vary per
              purpose, including the seeded-inert `synthesis` purpose — plus
              `verification`, read-only here (it judges the verification
              ladder and its qualification is a gate's evidence).
              A save live-reloads the orchestrator; no redeploy, no LLM_* env
              vars.
            </span>
            <HelpTip label="About the LLM tab">
              Each purpose is one row naming a shared provider row, so a
              credential rotation on the Providers sub-tab reaches every
              purpose that uses it with nothing to re-apply here. Every vendor
              auth, reasoning-control, and structured-output quirk that
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
      </TabsContent>
    </Tabs>
  )
}
