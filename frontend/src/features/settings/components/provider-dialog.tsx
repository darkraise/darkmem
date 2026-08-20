import { useState, type ReactNode } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { cn } from "darkraise-ui/lib"
import { API_KIND_OPTIONS } from "@/features/setup/api-kinds"
import type { ApiKind } from "@/features/settings/types"
import {
  MASKED_PROVIDER_KEY,
  useCreateLlmProvider,
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

function ApiKindSelect({
  value,
  onChange,
  disabled,
  ariaLabel,
}: {
  value: ApiKind
  onChange: (v: ApiKind) => void
  disabled?: boolean
  ariaLabel: string
}) {
  return (
    <Select
      value={value}
      disabled={disabled}
      onValueChange={(v) => onChange(v as ApiKind)}
    >
      <SelectTrigger aria-label={ariaLabel} disabled={disabled} className="font-mono">
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
  )
}

interface ProviderDraft {
  name: string
  api_kind: ApiKind
  base_url: string
  api_key: string
  keyCleared: boolean
}

function editDraft(p: LlmProvider): ProviderDraft {
  return {
    name: p.name,
    api_kind: p.api_kind,
    base_url: p.base_url,
    api_key: p.api_key ?? "",
    keyCleared: false,
  }
}

const CREATE_DRAFT: ProviderDraft = {
  name: "",
  api_kind: "openai",
  base_url: "",
  api_key: "",
  keyCleared: false,
}

/**
 * One dialog for adding and for editing, because the two collect the same
 * fields — a second form would be a second place for the wire contract to
 * drift out of agreement with the route.
 *
 * `provider === null` is the add case. The panel mounts this only while the
 * dialog is open and keys it on the target, so the draft seeds fresh on every
 * open — no reset effect, and no cascading render from one.
 *
 * Editing a `serves_verification`
 * provider disables `base_url` and `api_kind`: those two are the judge's
 * qualification identity and the backend 409s on either. `api_key` stays
 * enabled on purpose — that credential is owed rotation, and a dialog that
 * greyed out the whole form would make the rotation impossible through the
 * product.
 */
export function ProviderDialog({
  provider,
  open,
  onOpenChange,
}: {
  provider: LlmProvider | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const isEdit = provider !== null
  const [draft, setDraft] = useState<ProviderDraft>(() =>
    provider ? editDraft(provider) : CREATE_DRAFT,
  )
  const create = useCreateLlmProvider()
  const update = useUpdateLlmProvider()

  const frozen = provider?.serves_verification ?? false
  const patch = (p: Partial<ProviderDraft>) => setDraft((d) => ({ ...d, ...p }))
  const pending = create.isPending || update.isPending
  const error = create.error ?? update.error

  const submit = () => {
    if (isEdit) {
      const keyChanged = draft.api_key !== (provider.api_key ?? "")
      // PUT is a full replace: `api_kind` and `base_url` are required, so a
      // body omitting an unchanged field is a 422 rather than a partial
      // update. The two identity fields come from the server row when frozen,
      // so a draft left stale by a refetch cannot turn a key rotation into a
      // frozen-field 409. The mask sentinel is how "key untouched" is spelled,
      // since the server never sends the real secret back to resend.
      update.mutate(
        {
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
        },
        { onSuccess: () => onOpenChange(false) },
      )
      return
    }
    create.mutate(
      {
        name: draft.name,
        api_kind: draft.api_kind,
        base_url: draft.base_url,
        api_key: draft.api_key || null,
      },
      { onSuccess: () => onOpenChange(false) },
    )
  }

  const canSubmit = isEdit
    ? !pending
    : Boolean(draft.name) && Boolean(draft.base_url) && !pending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-lg flex-col gap-3">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `${provider.name} — connection` : "Add provider"}
          </DialogTitle>
          <DialogDescription>
            {frozen
              ? "This provider serves the verification judge. base_url and api_kind are its qualification identity and cannot be changed here; the key is still rotatable."
              : "One vendor connection several purposes can point at."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          {!isEdit && (
            <Field label="name" span2>
              <Input
                value={draft.name}
                aria-label="new provider name"
                onChange={(e) => patch({ name: e.target.value })}
                className="font-mono"
              />
            </Field>
          )}
          <Field label="api_kind">
            <ApiKindSelect
              value={draft.api_kind}
              disabled={frozen}
              ariaLabel={
                isEdit ? `${provider.name} api_kind` : "new provider api_kind"
              }
              onChange={(v) => patch({ api_kind: v })}
            />
          </Field>
          <Field label="base_url">
            <Input
              value={draft.base_url}
              disabled={frozen}
              aria-label={
                isEdit ? `${provider.name} base_url` : "new provider base_url"
              }
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
                  draft.keyCleared
                    ? "cleared on save"
                    : isEdit
                      ? "not set"
                      : "optional"
                }
                aria-label={
                  isEdit ? `${provider.name} api_key` : "new provider api_key"
                }
                onChange={(e) =>
                  patch({ api_key: e.target.value, keyCleared: false })
                }
                className="font-mono"
              />
              {isEdit &&
                !draft.keyCleared &&
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
              {isEdit && draft.keyCleared && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setDraft(editDraft(provider))}
                >
                  Undo
                </Button>
              )}
            </div>
          </Field>
        </div>

        {error && <p className="text-destructive text-sm">{error.message}</p>}
        {update.data && update.data.no_embedding_purposes.length > 0 && (
          <p className="text-warning text-sm">
            {update.data.no_embedding_purposes.join(", ")} lost their embeddings
            endpoint with this api_kind change.
          </p>
        )}

        <div className="flex items-center justify-end gap-2 pt-1">
          <Button size="sm" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={!canSubmit}
            onClick={submit}
          >
            {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
