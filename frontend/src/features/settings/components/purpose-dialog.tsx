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
import { useDropdownPlacement } from "@/hooks/use-dropdown-placement"
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
import { NumberField } from "@/components/darkmem"
import { validateParamsJson } from "@/demo/settings"
import { embeddingKindWarning } from "@/features/setup/api-kinds"
import { describeProbeError } from "@/features/setup/probe-error"
import type { DemoLLMPurpose } from "@/features/settings/types"
import {
  useLlmProviders,
  useProbeProviderModels,
} from "@/hooks/api/use-llm-providers-api"
import type { LLMTabBinding } from "../use-llm-tab-binding"
import { useDialogSave } from "../use-dialog-save"
import { ClassifierKindRow, CodeBuckets, Field } from "./purpose-sections"

type Draft = {
  provider_name: string
  model: string
  params: string
  dimensions: number
  reasoning: boolean
}

function toDraft(p: DemoLLMPurpose): Draft {
  return {
    provider_name: p.provider_name,
    model: p.model,
    params: p.params,
    dimensions: p.dimensions ?? 0,
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
  const modelDropdown = useDropdownPlacement()
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
  const hasModels = modelItems.length > 0

  const dirty = dirtyFields(purpose, draft)
  const patch = (p: Partial<Draft>) => setDraft((d) => ({ ...d, ...p }))
  const saving = useDialogSave(() => onOpenChange(false))

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
          changed.dimensions = draft.dimensions
          break
        case "reasoning":
          changed.reasoning = draft.reasoning
          break
      }
    }
    saving.run(() => binding.savePurpose(purpose.purpose, changed))
  }

  return (
    <Dialog open={open} onOpenChange={saving.guard(onOpenChange)}>
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

          <div className="grid grid-cols-1 gap-x-3 gap-y-2 sm:grid-cols-2">
            <Field label="model">
              <div ref={modelDropdown.ref}>
                <Combobox
                  items={modelItems}
                  inputValue={draft.model}
                  onInputValueChange={(d) => patch({ model: d.value })}
                  // Only a list worth showing opens: with no probed models
                  // the popover held nothing but "No models" and sat over the
                  // params label on the dialog's first focus. The empty case
                  // is helper text under the field instead.
                  openOnClick={hasModels}
                  openOnFocus={hasModels}
                  onOpenChange={modelDropdown.onOpenChange}
                >
                  <ComboboxControl>
                    <ComboboxInput
                      aria-label={`${purpose.purpose} model`}
                      placeholder="model id"
                      className="font-mono"
                    />
                    {hasModels && <ComboboxTrigger />}
                  </ComboboxControl>
                  {hasModels && (
                    <ComboboxContent className={modelDropdown.contentClassName}>
                      <ComboboxList>
                        {modelItems.map((it) => (
                          <ComboboxItem key={it.value} item={it}>
                            <ComboboxItemText>{it.label}</ComboboxItemText>
                          </ComboboxItem>
                        ))}
                        <ComboboxEmpty>No matching models</ComboboxEmpty>
                      </ComboboxList>
                    </ComboboxContent>
                  )}
                </Combobox>
              </div>
              {probe.data && !probe.data.error && !hasModels && (
                <span className="text-muted-foreground text-sm">
                  The provider listed no models; type the model id.
                </span>
              )}
              {/* A probe failure is a 200 carrying `error`, not a thrown
                  request — it reports and the field stays typeable, so a
                  vendor that is briefly down cannot make a purpose
                  unconfigurable. */}
              {probe.data?.error && (
                <span className="text-destructive-text text-sm">
                  No model list from {draft.provider_name}:{" "}
                  {describeProbeError(probe.data.error)}
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
                <NumberField
                  value={draft.dimensions}
                  min={0}
                  step={1}
                  aria-label="embedding dimensions"
                  onValueChange={(next) => {
                    // NaN is what the field reports for text it cannot parse,
                    // and it is the reason to use this over a raw number
                    // input: the previous spelling committed `Number(v) || 0`,
                    // so a typo silently wrote zero dimensions onto the
                    // purpose row. Refusing it keeps the last good value.
                    if (Number.isFinite(next)) patch({ dimensions: next })
                  }}
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
            <Field label="params" span2>
              <Input
                value={draft.params}
                aria-label={`${purpose.purpose} params`}
                onChange={(e) => patch({ params: e.target.value })}
                className={cn(
                  "font-mono",
                  !paramsCheck.ok && "border-destructive-edge",
                )}
              />
              {!paramsCheck.ok && (
                <span className="text-destructive-text text-sm">
                  {paramsCheck.error}
                </span>
              )}
            </Field>
          </div>

          {/* Derived warnings stay visible — a 404-on-every-request footgun is
              never demoted to a hover. */}
          {warning && <p className="text-warning-text text-sm">{warning}</p>}
          {!warning && purpose.hint?.tone === "caution" && (
            <p className="text-warning-text text-sm">{purpose.hint.text}</p>
          )}

          {isSummarization && binding.buckets && (
            <CodeBuckets
              buckets={binding.buckets}
              saveCodeBucket={binding.saveCodeBucket!}
            />
          )}
        </div>

        {saving.error && (
          <p role="alert" className="text-destructive-text text-sm">
            Not saved: {saving.error}
          </p>
        )}
        <div className="flex items-center gap-2.5 pt-1">
          {dirty.length > 0 && (
            <span className="text-muted-foreground text-sm">
              edited: {dirty.join(", ")}
            </span>
          )}
          <Button
            variant="ghost"
            className="ml-auto"
            disabled={saving.pending}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            variant="outline"
            className="border-primary/60 text-primary-text"
            disabled={dirty.length === 0 || !paramsCheck.ok || saving.pending}
            onClick={save}
          >
            {saving.pending ? "Saving…" : "Save"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
