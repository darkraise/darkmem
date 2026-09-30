import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  PasswordInput,
  PasswordInputControl,
  PasswordInputField,
  PasswordInputIndicator,
  PasswordInputVisibilityTrigger,
} from "darkraise-ui/components/password-input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Switch } from "darkraise-ui/components/switch"
import { toast } from "darkraise-ui/components/sonner"
import { CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react"
import {
  useCreateGitAccount,
  useUpdateGitAccount,
  useVerifyGitToken,
  type GitAccount,
} from "@/hooks/api/use-git-accounts-api"
import { useGitAccountsData } from "../use-git-accounts-binding"

interface Props {
  /** null opens the add case; an account opens the edit case. */
  account: GitAccount | null
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Preselects the forge when opened from a repo dialog that already knows it. */
  defaultProvider?: string
  /** Called with the created account, so a caller can select it immediately. */
  onCreated?: (account: GitAccount) => void
}

export function GitAccountDialog({
  account,
  open,
  onOpenChange,
  defaultProvider,
  onCreated,
}: Props) {
  const isEdit = account != null
  const { data } = useGitAccountsData()
  const forges = data.providers

  const [label, setLabel] = useState(account?.label ?? "")
  const [provider, setProvider] = useState(
    account?.provider ?? defaultProvider ?? "github",
  )
  const [host, setHost] = useState(account?.host ?? "")
  const [token, setToken] = useState("")
  const [isDefault, setIsDefault] = useState(account?.is_default ?? false)

  const create = useCreateGitAccount()
  const update = useUpdateGitAccount()
  const verify = useVerifyGitToken()

  const forge = forges.find((f) => f.provider === provider)
  const effectiveHost = host.trim() || forge?.default_host || ""
  const pending = create.isPending || update.isPending

  const handleVerify = () => {
    if (!token.trim()) return
    verify.mutate(
      { token: token.trim(), provider, host: host.trim() || null },
      {
        onSuccess: (result) => {
          if (!label.trim()) setLabel(result.username)
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isEdit) {
      const patch: Parameters<typeof update.mutate>[0]["data"] = {}
      if (label.trim() && label.trim() !== account.label) patch.label = label.trim()
      // An empty token field means "leave the stored one alone" — the server
      // only re-verifies when the value actually changes.
      if (token.trim()) patch.token = token.trim()
      if (isDefault !== account.is_default) patch.is_default = isDefault
      if (Object.keys(patch).length === 0) {
        onOpenChange(false)
        return
      }
      update.mutate(
        { id: account.id, data: patch },
        {
          onSuccess: () => {
            toast.success("Account updated")
            onOpenChange(false)
          },
          onError: (error) => toast.error(error.message),
        },
      )
      return
    }

    if (!label.trim() || !token.trim()) return
    create.mutate(
      {
        label: label.trim(),
        token: token.trim(),
        provider,
        host: host.trim() || null,
        is_default: isDefault,
      },
      {
        onSuccess: (created) => {
          toast.success(`Added ${created.label} (@${created.username})`)
          onCreated?.(created)
          onOpenChange(false)
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit account" : "Add git account"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Leave the token blank to keep the stored one. Changing it re-checks the account with the provider."
              : "The token is checked with the provider before it is saved."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          {!isEdit && (
            <>
              <div>
                <Label className="text-muted-foreground">Provider</Label>
                <Select value={provider} onValueChange={setProvider}>
                  <SelectTrigger className="h-9 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {forges.map((f) => (
                      <SelectItem key={f.provider} value={f.provider}>
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground">Host</Label>
                <Input
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder={forge?.default_host ?? "github.com"}
                />
                <p className="text-muted-foreground mt-1 text-sm">
                  Leave blank for {forge?.default_host ?? "the provider default"}.
                  Set it for a self-hosted install.
                </p>
              </div>
            </>
          )}
          <div>
            <Label className="text-muted-foreground">
              {isEdit ? "New token" : "Access token *"}
            </Label>
            <div className="flex gap-2">
              <PasswordInput className="flex-1">
                <PasswordInputControl>
                  <PasswordInputField
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder={
                      isEdit ? `Keeps ••••${account.token_hint}` : "ghp_… or github_pat_…"
                    }
                    autoComplete="off"
                  />
                  <PasswordInputVisibilityTrigger>
                    <PasswordInputIndicator
                      visible={<EyeOff aria-hidden className="h-4 w-4" />}
                      hidden={<Eye aria-hidden className="h-4 w-4" />}
                    />
                  </PasswordInputVisibilityTrigger>
                </PasswordInputControl>
              </PasswordInput>
              <Button
                type="button"
                variant="outline"
                onClick={handleVerify}
                disabled={!token.trim() || verify.isPending}
              >
                {verify.isPending ? (
                  <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                ) : (
                  "Check"
                )}
              </Button>
            </div>
            {verify.data && (
              <p className="text-muted-foreground mt-1 flex items-center gap-1 text-sm">
                <CheckCircle2 aria-hidden className="h-4 w-4 text-emerald-500" />
                {verify.data.username} on {verify.data.host}
                {verify.data.scopes ? ` — ${verify.data.scopes}` : ""}
              </p>
            )}
          </div>
          <div>
            <Label className="text-muted-foreground">Name *</Label>
            <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Personal, Work, CI bot…"
              required
            />
          </div>
          <div className="flex items-start gap-2 rounded-md border px-3 py-2">
            <Switch
              className="mt-0.5"
              checked={isDefault}
              onCheckedChange={setIsDefault}
            />
            <div className="text-sm">
              <div>Default for {forge?.label ?? provider}</div>
              <div className="text-muted-foreground text-sm">
                Preselected when you add a repository on {effectiveHost}. Only one
                account per host can hold this.
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={pending || (!isEdit && (!label.trim() || !token.trim()))}
            >
              {pending ? "Saving..." : isEdit ? "Save" : "Add account"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
