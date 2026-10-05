import { useEffect, useId, useRef, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { toast } from "darkraise-ui/components/sonner"
import { Plus } from "lucide-react"
import { useCreateRepo } from "@/hooks/api"
import type { RepoCreateParams } from "@/hooks/api"
import { useGitAccountsData } from "@/features/settings/use-git-accounts-binding"
import {
  CUSTOM_TOKEN,
  GitAccountSelect,
  NO_ACCOUNT,
} from "./git-account-select"
import {
  IndexingModesFields,
  type IndexingModes,
} from "./indexing-modes-fields"

const INDEXING_MODES_DEFAULTS: IndexingModes = {
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
}

// Providers that carry no credential: a local checkout has nothing to
// authenticate against, so the picker is hidden rather than shown empty.
const CREDENTIAL_FREE = new Set(["local"])

// Ported from routes/_authenticated/repos.tsx's AddRepoDialog (T1.59) — same
// POST /repos shape, adapted to the Code section's own trigger/dialog chrome.
export function AddRepoDialog() {
  // Every Label is tied to its control: a bare <Label> beside an <Input>
  // announces an unlabelled field and does not focus it when clicked.
  const fieldId = useId()
  const ids = {
    name: `${fieldId}-name`,
    url: `${fieldId}-url`,
    provider: `${fieldId}-provider`,
    branch: `${fieldId}-branch`,
    token: `${fieldId}-token`,
  }
  const [open, setOpen] = useState(false)
  const createRepo = useCreateRepo()
  const { data: accountData, isLoading: accountsLoading } = useGitAccountsData()
  const [form, setForm] = useState<RepoCreateParams>({
    name: "",
    url: "",
    provider: "github",
    default_branch: "main",
    auth_token: "",
    ...INDEXING_MODES_DEFAULTS,
  })
  const [accountChoice, setAccountChoice] = useState<string>(NO_ACCOUNT)

  const provider = form.provider ?? "github"
  const credentialFree = CREDENTIAL_FREE.has(provider)

  // Which provider the preselect below has already run for. Without it the
  // effect would re-apply the default on renders the operator's own choice
  // caused, silently reverting every selection they make.
  const preselectedFor = useRef<string | null>(null)

  // Preselect the provider's default so the common case needs no interaction.
  // Runs once per provider, and only once the accounts have actually arrived
  // — preselecting off an empty loading response would land on NO_ACCOUNT and
  // then never correct itself.
  useEffect(() => {
    if (credentialFree || accountsLoading) return
    if (preselectedFor.current === provider) return
    preselectedFor.current = provider
    const fallback = accountData.accounts.find(
      (a) => a.provider === provider && a.is_default,
    )
    setAccountChoice(fallback?.id ?? NO_ACCOUNT)
  }, [accountData, provider, credentialFree, accountsLoading])

  const set = <K extends keyof RepoCreateParams>(
    field: K,
    value: RepoCreateParams[K],
  ) => setForm((prev) => ({ ...prev, [field]: value }))

  const reset = () => {
    setForm({
      name: "",
      url: "",
      provider: "github",
      default_branch: "main",
      auth_token: "",
      ...INDEXING_MODES_DEFAULTS,
    })
    setAccountChoice(NO_ACCOUNT)
    // The next open is a fresh form, so it gets the preselect again.
    preselectedFor.current = null
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return

    const params: RepoCreateParams = { name: form.name.trim() }
    if (form.url) params.url = form.url
    if (form.provider) params.provider = form.provider
    if (form.default_branch) params.default_branch = form.default_branch
    params.fetch_enabled = form.fetch_enabled
    params.fetch_interval_seconds = form.fetch_interval_seconds
    params.index_on_commit_enabled = form.index_on_commit_enabled
    params.commit_poll_seconds = form.commit_poll_seconds
    params.index_uncommitted = form.index_uncommitted

    if (credentialFree) {
      // Send the field explicitly so the server does not stamp a default.
      params.git_account_id = null
    } else if (accountChoice === CUSTOM_TOKEN) {
      if (form.auth_token) params.auth_token = form.auth_token
      params.git_account_id = null
    } else {
      params.git_account_id =
        accountChoice === NO_ACCOUNT ? null : accountChoice
    }

    createRepo.mutate(params, {
      onSuccess: () => {
        toast.success("Repository added")
        setOpen(false)
        reset()
      },
      onError: () => toast.error("Failed to add repository"),
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden className="mr-1 h-4 w-4" />
          Add repository
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add repository</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label htmlFor={ids.name} className="text-muted-foreground">
              Name *
            </Label>
            <Input
              id={ids.name}
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor={ids.url} className="text-muted-foreground">
              URL
            </Label>
            <Input
              id={ids.url}
              value={form.url ?? ""}
              onChange={(e) => set("url", e.target.value)}
              placeholder="https://github.com/org/repo"
            />
          </div>
          <div>
            <Label
              id={`${ids.provider}-label`}
              htmlFor={ids.provider}
              className="text-muted-foreground"
            >
              Provider
            </Label>
            <Select value={provider} onValueChange={(v) => set("provider", v)}>
              <SelectTrigger
                id={ids.provider}
                aria-labelledby={`${ids.provider}-label`}
                className="h-9 w-full"
              >
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="github">GitHub</SelectItem>
                <SelectItem value="gitlab">GitLab</SelectItem>
                <SelectItem value="local">Local</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor={ids.branch} className="text-muted-foreground">
              Default branch
            </Label>
            <Input
              id={ids.branch}
              value={form.default_branch ?? "main"}
              onChange={(e) => set("default_branch", e.target.value)}
            />
          </div>
          {!credentialFree && (
            <GitAccountSelect
              value={accountChoice}
              onChange={setAccountChoice}
              provider={provider}
            />
          )}
          {!credentialFree && accountChoice === CUSTOM_TOKEN && (
            <div>
              <Label htmlFor={ids.token} className="text-muted-foreground">
                Auth token
              </Label>
              <Input
                id={ids.token}
                type="password"
                value={form.auth_token ?? ""}
                onChange={(e) => set("auth_token", e.target.value)}
                placeholder="Used by this repository only"
              />
            </div>
          )}
          <IndexingModesFields
            value={{
              fetch_enabled: form.fetch_enabled ?? false,
              fetch_interval_seconds: form.fetch_interval_seconds ?? 300,
              index_on_commit_enabled: form.index_on_commit_enabled ?? false,
              commit_poll_seconds: form.commit_poll_seconds ?? 60,
              index_uncommitted: form.index_uncommitted ?? false,
            }}
            onChange={(next) => setForm((prev) => ({ ...prev, ...next }))}
          />
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={createRepo.isPending}>
              {createRepo.isPending ? "Adding..." : "Add Repository"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
