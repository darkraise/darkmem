import { useState, type ReactNode } from "react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"
import { Plug, Plus, ShieldCheck, Trash2, X } from "lucide-react"
import { EmptyState, HelpTip } from "@/components/darkmem"
import { API_KIND_OPTIONS } from "@/features/setup/api-kinds"
import type { ApiKind } from "@/features/settings/types"
import {
  MASKED_PROVIDER_KEY,
  useCreateLlmProvider,
  useDeleteLlmProvider,
  useLlmProviders,
  useProbeProviderModels,
  useUpdateLlmProvider,
  type LlmProvider,
} from "@/hooks/api/use-llm-providers-api"

function Field({
  label,
  span2,
  children,
}: {
  label: string
  span2?: boolean
  children: ReactNode
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

function ProbeResult({
  result,
}: {
  result: { models: string[]; error: string | null } | undefined
}) {
  if (!result) return null
  if (result.error) {
    return <span className="text-destructive text-sm">{result.error}</span>
  }
  return (
    <span className="text-muted-foreground text-sm">
      {result.models.length} model{result.models.length === 1 ? "" : "s"}
    </span>
  )
}

interface ProviderDraft {
  api_kind: ApiKind
  base_url: string
  api_key: string
  keyCleared: boolean
}

function toDraft(p: LlmProvider): ProviderDraft {
  return {
    api_kind: p.api_kind,
    base_url: p.base_url,
    api_key: p.api_key ?? "",
    keyCleared: false,
  }
}

// A `serves_verification` provider carries the judge's qualification
// identity on `base_url`/`api_kind` — the backend 409s on either, so those
// two render disabled here. `api_key` is deliberately left enabled: the
// owner has ruled that credential is owed rotation, and greying out the
// whole card would make rotation impossible through the product.
function ProviderCard({ provider }: { provider: LlmProvider }) {
  const [draft, setDraft] = useState<ProviderDraft>(() => toDraft(provider))
  const update = useUpdateLlmProvider()
  const del = useDeleteLlmProvider()
  const probe = useProbeProviderModels()

  const frozen = provider.serves_verification
  const patch = (p: Partial<ProviderDraft>) => setDraft((d) => ({ ...d, ...p }))

  const dirty =
    (!frozen &&
      (draft.api_kind !== provider.api_kind ||
        draft.base_url !== provider.base_url)) ||
    draft.keyCleared ||
    draft.api_key !== (provider.api_key ?? "")

  // PUT is a full replace: `api_kind` and `base_url` are required, so a body
  // omitting an unchanged field is a 422 rather than a partial update. A
  // frozen provider is no exception — the guard compares incoming values
  // against stored ones, and resending the two identity fields verbatim is
  // what makes a key-only rotation possible at all. Those two come from the
  // server row rather than the draft when frozen, so a draft left stale by a
  // refetch cannot turn a rotation into a frozen-field 409. The mask sentinel
  // is how "key untouched" is spelled, since the server never sends the real
  // secret back for this form to resend.
  const save = () => {
    const keyChanged = draft.api_key !== (provider.api_key ?? "")
    update.mutate({
      name: provider.name,
      data: {
        api_kind: frozen ? provider.api_kind : draft.api_kind,
        base_url: frozen ? provider.base_url : draft.base_url,
        api_key: draft.keyCleared
          ? null
          : keyChanged
            ? draft.api_key
            : MASKED_PROVIDER_KEY,
      },
    })
  }

  const canDelete = provider.used_by.length === 0

  return (
    <Card>
      <CardContent className="flex flex-col gap-2.5 pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <Plug aria-hidden className="text-primary h-4 w-4" />
          <span className="font-mono text-sm font-semibold">
            {provider.name}
          </span>
          {frozen && (
            <>
              <ShieldCheck
                aria-hidden
                className="text-muted-foreground h-3.5 w-3.5"
              />
              <HelpTip label={`About ${provider.name}'s frozen fields`}>
                This provider serves the verification judge. base_url and
                api_kind are the judge's qualification identity, so the
                backend refuses to change them here. The key is still
                rotatable — that credential is owed rotation regardless.
              </HelpTip>
            </>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="ml-auto inline-flex">
                <Badge variant="secondary" className="font-mono">
                  {provider.used_by.length}
                </Badge>
              </span>
            </TooltipTrigger>
            <TooltipContent>
              {provider.used_by.length === 0
                ? "not referenced by any purpose"
                : `used by: ${provider.used_by.join(", ")}`}
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          <Field label="api_kind">
            <Select
              value={draft.api_kind}
              disabled={frozen}
              onValueChange={(v) => patch({ api_kind: v as ApiKind })}
            >
              <SelectTrigger
                aria-label={`${provider.name} api_kind`}
                disabled={frozen}
                className="font-mono"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {API_KIND_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                    {opt.note && (
                      <span className="text-muted-foreground ml-1 text-xs">
                        ({opt.note})
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="base_url">
            <Input
              value={draft.base_url}
              disabled={frozen}
              aria-label={`${provider.name} base_url`}
              onChange={(e) => patch({ base_url: e.target.value })}
              className="font-mono"
            />
          </Field>
          <Field label="api_key" span2>
            <div className="flex items-center gap-1.5">
              <Input
                type="password"
                value={draft.keyCleared ? "" : draft.api_key}
                disabled={draft.keyCleared}
                placeholder={
                  draft.keyCleared ? "cleared on save" : "not set"
                }
                aria-label={`${provider.name} api_key`}
                onChange={(e) =>
                  patch({ api_key: e.target.value, keyCleared: false })
                }
                className="font-mono"
              />
              {!draft.keyCleared &&
                (provider.api_key !== null || draft.api_key !== "") && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => patch({ api_key: "", keyCleared: true })}
                  >
                    Clear
                  </Button>
                )}
              {draft.keyCleared && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setDraft(toDraft(provider))}
                >
                  Undo
                </Button>
              )}
            </div>
          </Field>
        </div>

        {update.isError && (
          <p className="text-destructive text-sm">{update.error.message}</p>
        )}
        {update.data && update.data.no_embedding_purposes.length > 0 && (
          <p className="text-warning text-sm">
            {update.data.no_embedding_purposes.join(", ")} lost their
            embeddings endpoint with this api_kind change.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={!dirty || update.isPending}
            onClick={save}
          >
            Save
          </Button>
          <Button
            size="sm"
            variant="ghost"
            aria-label={`Test connection ${provider.name}`}
            disabled={probe.isPending}
            onClick={() => probe.mutate({ name: provider.name })}
          >
            {probe.isPending ? "Testing…" : "Test connection"}
          </Button>
          <ProbeResult result={probe.data} />
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="ml-auto inline-flex">
                <Button
                  size="icon"
                  variant="ghost"
                  className="text-destructive"
                  aria-label={`Delete ${provider.name}`}
                  disabled={!canDelete || del.isPending}
                  onClick={() => del.mutate(provider.name)}
                >
                  <Trash2 aria-hidden className="h-4 w-4" />
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>
              {canDelete
                ? "delete this provider"
                : `in use by: ${provider.used_by.join(", ")}`}
            </TooltipContent>
          </Tooltip>
        </div>
        {del.isError && (
          <p className="text-destructive text-sm">{del.error.message}</p>
        )}
      </CardContent>
    </Card>
  )
}

function NewProviderCard() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [apiKind, setApiKind] = useState<ApiKind>("openai")
  const [baseUrl, setBaseUrl] = useState("")
  const [apiKey, setApiKey] = useState("")
  const create = useCreateLlmProvider()
  const probe = useProbeProviderModels()

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="border-border text-muted-foreground hover:text-foreground hover:border-primary/50 flex min-h-[10rem] flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-4 text-sm transition-colors"
      >
        <Plus aria-hidden className="h-5 w-5" />
        Add provider
      </button>
    )
  }

  const submit = () => {
    create.mutate(
      { name, api_kind: apiKind, base_url: baseUrl, api_key: apiKey || null },
      {
        onSuccess: () => {
          setOpen(false)
          setName("")
          setBaseUrl("")
          setApiKey("")
        },
      },
    )
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-2.5 pt-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold">
            New provider
          </span>
          <Button
            size="icon"
            variant="ghost"
            className="ml-auto"
            aria-label="Cancel new provider"
            onClick={() => setOpen(false)}
          >
            <X aria-hidden className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          <Field label="name" span2>
            <Input
              value={name}
              aria-label="new provider name"
              onChange={(e) => setName(e.target.value)}
              className="font-mono"
            />
          </Field>
          <Field label="api_kind">
            <Select
              value={apiKind}
              onValueChange={(v) => setApiKind(v as ApiKind)}
            >
              <SelectTrigger
                aria-label="new provider api_kind"
                className="font-mono"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {API_KIND_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                    {opt.note && (
                      <span className="text-muted-foreground ml-1 text-xs">
                        ({opt.note})
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="base_url">
            <Input
              value={baseUrl}
              aria-label="new provider base_url"
              onChange={(e) => setBaseUrl(e.target.value)}
              className="font-mono"
            />
          </Field>
          <Field label="api_key" span2>
            <Input
              type="password"
              value={apiKey}
              placeholder="optional"
              aria-label="new provider api_key"
              onChange={(e) => setApiKey(e.target.value)}
              className="font-mono"
            />
          </Field>
        </div>
        {create.isError && (
          <p className="text-destructive text-sm">{create.error.message}</p>
        )}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button
            size="sm"
            variant="ghost"
            aria-label="Test connection new provider"
            disabled={probe.isPending || !baseUrl}
            onClick={() =>
              probe.mutate({
                draft: { api_kind: apiKind, base_url: baseUrl, api_key: apiKey || null },
              })
            }
          >
            {probe.isPending ? "Testing…" : "Test connection"}
          </Button>
          <ProbeResult result={probe.data} />
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary ml-auto"
            disabled={!name || !baseUrl || create.isPending}
            onClick={submit}
          >
            Create
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function ProvidersPanel() {
  const { data, isLoading } = useLlmProviders()
  const providers = data?.providers ?? []

  if (isLoading) {
    return (
      <div className="grid gap-3.5 sm:grid-cols-2">
        {Array.from({ length: 2 }, (_, i) => (
          <Skeleton key={i} className="h-48 w-full rounded-md" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {providers.length === 0 && (
        <EmptyState
          kind="empty"
          icon={Plug}
          title="No providers configured"
          description="A provider is one vendor connection an operator can point several purposes at instead of configuring each one separately."
        />
      )}
      <div className="grid gap-3.5 sm:grid-cols-2">
        {providers.map((p) => (
          <ProviderCard key={p.name} provider={p} />
        ))}
        <NewProviderCard />
      </div>
    </div>
  )
}
