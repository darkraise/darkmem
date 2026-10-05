import { useId, useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Label } from "darkraise-ui/components/label"
import { useGitAccountsData } from "@/features/settings/use-git-accounts-binding"
import { GitAccountDialog } from "@/features/settings/components/git-account-dialog"

// Sentinels for the two rows that are actions rather than accounts. Select
// values must be non-empty strings, so "no auth" gets one too.
export const NO_ACCOUNT = "__none__"
export const CUSTOM_TOKEN = "__custom__"
const ADD_ACCOUNT = "__add__"

interface Props {
  /** An account id, NO_ACCOUNT, or CUSTOM_TOKEN. */
  value: string
  onChange: (value: string) => void
  /** Filters the list, since a GitLab repo cannot use a GitHub credential. */
  provider: string
  /** Hidden for a provider that carries no credential at all (local repos). */
  allowCustomToken?: boolean
  label?: string
}

export function GitAccountSelect({
  value,
  onChange,
  provider,
  allowCustomToken = true,
  label = "Account",
}: Props) {
  const { data } = useGitAccountsData()
  const [addOpen, setAddOpen] = useState(false)
  const triggerId = useId()

  const accounts = data.accounts.filter((a) => a.provider === provider)

  return (
    <div>
      <Label
        id={`${triggerId}-label`}
        htmlFor={triggerId}
        className="text-muted-foreground"
      >
        {label}
      </Label>
      <Select
        value={value}
        onValueChange={(next) => {
          if (next === ADD_ACCOUNT) {
            setAddOpen(true)
            return
          }
          onChange(next)
        }}
      >
        <SelectTrigger
          id={triggerId}
          aria-labelledby={`${triggerId}-label`}
          className="h-9 w-full"
        >
          <SelectValue placeholder="Select an account" />
        </SelectTrigger>
        <SelectContent>
          {accounts.map((account) => (
            <SelectItem key={account.id} value={account.id}>
              {account.label} · @{account.username}
              {account.is_default ? " (default)" : ""}
            </SelectItem>
          ))}
          {accounts.length > 0 && <SelectSeparator />}
          <SelectItem value={NO_ACCOUNT}>No authentication (public)</SelectItem>
          {allowCustomToken && (
            <SelectItem value={CUSTOM_TOKEN}>
              Custom token for this repo…
            </SelectItem>
          )}
          <SelectItem value={ADD_ACCOUNT}>+ Add account…</SelectItem>
        </SelectContent>
      </Select>
      {addOpen && (
        <GitAccountDialog
          account={null}
          open
          onOpenChange={setAddOpen}
          defaultProvider={provider}
          // Selecting it straight away is the whole point of adding one here.
          onCreated={(created) => onChange(created.id)}
        />
      )}
    </div>
  )
}
