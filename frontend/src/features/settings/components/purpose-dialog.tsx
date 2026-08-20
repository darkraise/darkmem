import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
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
import { cn } from "darkraise-ui/lib"
import { validateParamsJson } from "@/demo/settings"
import { embeddingKindWarning } from "@/features/setup/api-kinds"
import type { DemoLLMPurpose } from "@/features/settings/types"
import {
  useLlmProviders,
  useProbeProviderModels,
} from "@/hooks/api/use-llm-providers-api"
import type { LLMTabBinding } from "../use-llm-tab-binding"
import {
  ClassifierKindRow,
  CodeBuckets,
  CodeBucketsUnavailable,
  Field,
} from "./purpose-sections"

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
  return (Object.keys(base) as (keyof Draft)[]).filter((k) => base[k] !== d[k])
}

/**
 * The purpose editor. The tab mounts it only while a row is being edited and
 * keys it on the purpose, so the draft seeds fresh from the server's values on
 * every open rather than needing a reset effect.
 *
 * The purpose editor. Every field a purpose owns lives here and nowhere else,
 * so the row and card layouts stay pure display and cannot disagree about what
 * a purpose is configurable by.
 *
 * The save payload carries only what the update schema declares —
 * `provider_name`, `model`, `params`, `dimensions`, `reasoning`. Connection
 * fields are undeclared on that schema, so a body carrying one would be
 * silently dropped and the request would still return 200: an inert write that
 * looks like a successful one.
 */
export function PurposeDialog({
  purpose,
  binding,
  open,
  onOpenChange,
}: {
  purpose: DemoLLMPurpose
  binding: LLMTabBinding
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(purpose))
  const paramsCheck = validateParamsJson(draft.params)
  const isEmbedding = purpose.purpose === "embedding"
  const isSummarization = purpose.purpose === "summarization"

  const { data: providersData } = useLlmProviders()
  const providers = providersData?.providers ?? []
  const selectedProvider = providers.find((p) => p.name === draft.provider_name)
  const warning = isEmbedding
    ? embeddingKindWarning(selectedProvider?.api_kind)
    : null

  const probe = useProbeProviderModels()
  const providerName = draft.provider_name
  useEffect(() => {
    if (!open || !providerName) return
    probe.mutate({ name: providerName })
    // react-query's `mutate` identity is not stable across renders; depending
    // on it would re-probe every render rather than only on a provider change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, providerName])
  const modelItems = (probe.data?.models ?? []).map((m) => ({
    value: m,
    label: m,
  }))

  const dirty = dirtyFields(purpose, draft)
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
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col gap-3">
        <DialogHeader>
          <DialogTitle>{purpose.purpose} — configuration</DialogTitle>
          <DialogDescription>
            {purpose.role}
            {purpose.hint && ` — ${purpose.hint.text}`}
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto">
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
              {/* A probe failure is a 200 carrying `error`, not a thrown
                  request — it reports and the field stays typeable, so a
                  vendor that is briefly down cannot make a purpose
                  unconfigurable. */}
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
                    <SelectItem
                      key={p.name}
                      value={p.name}
                      className="font-mono"
                    >
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

          {isSummarization &&
            (binding.buckets ? (
              <CodeBuckets
                buckets={binding.buckets}
                saveCodeBucket={binding.saveCodeBucket!}
              />
            ) : (
              <CodeBucketsUnavailable />
            ))}
        </div>

        <div className="flex items-center gap-2.5 pt-1">
          {dirty.length > 0 && (
            <span className="text-muted-foreground text-sm">
              edited: {dirty.join(", ")}
            </span>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={dirty.length === 0 || !paramsCheck.ok}
            onClick={save}
          >
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
