import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { toast } from "darkraise-ui/components/sonner"
import { KeyRound, Pencil, Plus, Star, Trash2 } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import {
  useDeleteGitAccount,
  useUpdateGitAccount,
  type GitAccount,
} from "@/hooks/api/use-git-accounts-api"
import { useGitAccountsData } from "../use-git-accounts-binding"
import { GitAccountDialog } from "./git-account-dialog"
import { SettingsCard } from "./settings-card"

function formatVerified(at: string | null): string {
  if (!at) return "never checked"
  return `checked ${new Date(at).toLocaleDateString()}`
}

export function GitAccountsTab() {
  const { data, isLoading, isError } = useGitAccountsData()
  const update = useUpdateGitAccount()
  const [editing, setEditing] = useState<GitAccount | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState<GitAccount | null>(null)
  // The default is per host, so promoting an account silently displaces the
  // host's current default; that swap is confirmed first.
  const [promoting, setPromoting] = useState<{
    account: GitAccount
    displaced: GitAccount
  } | null>(null)

  const accounts = data.accounts
  const forges = data.providers
  const forgeLabel = (provider: string) =>
    forges.find((f) => f.provider === provider)?.label ?? provider

  const setDefault = (account: GitAccount) =>
    update.mutate(
      { id: account.id, data: { is_default: true } },
      {
        onSuccess: () => toast.success(`${account.label} is now the default`),
        onError: (error) => toast.error(error.message),
      },
    )

  const requestDefault = (account: GitAccount) => {
    const displaced = accounts.find(
      (a) => a.is_default && a.host === account.host && a.id !== account.id,
    )
    if (displaced) setPromoting({ account, displaced })
    else setDefault(account)
  }

  return (
    <div className="space-y-4">
      <SettingsCard
        icon={KeyRound}
        title="Git accounts"
        actions={
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary-text"
            onClick={() => {
              setEditing(null)
              setDialogOpen(true)
            }}
          >
            <Plus aria-hidden className="mr-1 h-4 w-4" />
            Add account
          </Button>
        }
      >
        <p className="text-muted-foreground text-sm">
          Credentials for cloning private repositories.
        </p>
        {isError ? (
          // Not the empty state: "No git accounts" invites re-adding a
          // token the instance already holds.
          <p className="text-destructive-text text-sm">
            Git accounts could not be loaded.
          </p>
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-md" />
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={KeyRound}
            title="No git accounts"
            description="Add a personal access token to clone private repositories. The token is checked with the provider before it is saved."
          />
        ) : (
          <ul className="flex flex-col gap-2.5">
            {accounts.map((account) => (
              <li
                key={account.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border px-3 py-2.5"
              >
                {/* Full width under sm so the action group wraps beneath
                      the text instead of squeezing the meta line into a
                      one-word-per-line column beside it. */}
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{account.label}</span>
                    {account.is_default && (
                      <Badge variant="outline" className="gap-1">
                        <Star aria-hidden className="h-3 w-3" />
                        Default for {account.host}
                      </Badge>
                    )}
                  </div>
                  <div className="text-muted-foreground text-sm">
                    @{account.username} · {forgeLabel(account.provider)} ·{" "}
                    {account.host} · ••••{account.token_hint} ·{" "}
                    {formatVerified(account.last_verified_at)}
                    {account.repo_count > 0 &&
                      ` · ${account.repo_count} repositor${account.repo_count === 1 ? "y" : "ies"}`}
                  </div>
                </div>
                <div className="ml-auto flex max-w-full flex-wrap items-center justify-end gap-1">
                  {!account.is_default && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => requestDefault(account)}
                      disabled={update.isPending}
                    >
                      <Star aria-hidden className="mr-1 h-4 w-4" />
                      Make default for {account.host}
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Edit ${account.label}`}
                    onClick={() => {
                      setEditing(account)
                      setDialogOpen(true)
                    }}
                  >
                    <Pencil aria-hidden className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Delete ${account.label}`}
                    onClick={() => setDeleting(account)}
                  >
                    <Trash2 aria-hidden className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </SettingsCard>

      {dialogOpen && (
        <GitAccountDialog
          key={editing?.id ?? "__add__"}
          account={editing}
          open
          onOpenChange={setDialogOpen}
        />
      )}
      {promoting && (
        <Dialog open onOpenChange={(open) => !open && setPromoting(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Make {promoting.account.label} the default for{" "}
                {promoting.account.host}?
              </DialogTitle>
              <DialogDescription>
                {promoting.displaced.label} is the default for{" "}
                {promoting.account.host} now and stops being it. Repositories
                you add on that host preselect {promoting.account.label}{" "}
                instead; existing repositories keep their account.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setPromoting(null)}>
                Cancel
              </Button>
              <Button
                disabled={update.isPending}
                onClick={() => {
                  setDefault(promoting.account)
                  setPromoting(null)
                }}
              >
                Make default
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
      {deleting && (
        <DeleteAccountDialog
          account={deleting}
          others={accounts.filter((a) => a.id !== deleting.id)}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  )
}

function DeleteAccountDialog({
  account,
  others,
  onClose,
}: {
  account: GitAccount
  others: GitAccount[]
  onClose: () => void
}) {
  const remove = useDeleteGitAccount()
  // The server refuses a delete that would strand repositories, so the picker
  // is offered up front rather than after a failed attempt.
  const [reassignTo, setReassignTo] = useState<string>("")
  const inUse = account.repo_count > 0

  const confirm = () =>
    remove.mutate(
      { id: account.id, reassignTo: reassignTo || undefined },
      {
        onSuccess: () => {
          toast.success(`Deleted ${account.label}`)
          onClose()
        },
        onError: (error) => toast.error(error.message),
      },
    )

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {account.label}?</DialogTitle>
          <DialogDescription>
            {inUse
              ? `${account.repo_count} repositor${account.repo_count === 1 ? "y" : "ies"} still use this account. Choose another for them.`
              : "The stored token is removed. This cannot be undone."}
          </DialogDescription>
        </DialogHeader>
        {inUse && (
          <Select value={reassignTo} onValueChange={setReassignTo}>
            <SelectTrigger className="h-9 w-full">
              <SelectValue placeholder="Move those repositories to…" />
            </SelectTrigger>
            <SelectContent>
              {others.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.label} (@{a.username})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={confirm}
            disabled={remove.isPending || (inUse && !reassignTo)}
          >
            {remove.isPending ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
