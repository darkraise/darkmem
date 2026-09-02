import { useEffect, useState } from "react"
import { HardDriveDownload, ShieldAlert, ShieldCheck } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "darkraise-ui/components/dialog"

import { EmptyState, HelpTip } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { MASKED, type BackupDestination } from "@/hooks/api/use-backups-api"
import {
  useBackupsTabBinding,
  type BackupOutcome,
} from "@/features/settings/use-backups-tab-binding"

/**
 * The `backup_destinations` operator surface (increment 6, spec §9.3).
 *
 * **This is the second producer, not the only one.** The host's systemd timer
 * keeps its own local dumps whether or not the app is up, and the copy says so
 * on the surface rather than in a runbook: an operator who reads this tab as
 * "the backup system" would treat a red destination as no backup at all.
 *
 * **A secret is never rendered and never re-sent.** The server masks it on
 * read; an untouched field goes back as the mask, which the server reads as
 * "the value you already hold". Typing into the field is the only way to
 * replace it.
 *
 * **The encrypt-before-egress rule is the server's**, not this form's. A
 * non-local destination without an age recipient is refused at save with a
 * 422, and the message is rendered here — one place decides, one place
 * explains. A client-side copy of the rule would be a second decider that
 * drifts.
 */
export function BackupsTab() {
  const {
    destinations,
    recentOutcomes,
    save,
    runNow,
    isLoading,
    isSaving,
    isRunning,
  } = useBackupsTabBinding()

  const [editing, setEditing] = useState<BackupDestination | null>(null)
  // Two error slots, not one: a refusal belongs beside the control that
  // caused it. One shared slot renders the dialog's 422 behind the dialog as
  // well, which reads as two separate failures.
  const [formError, setFormError] = useState<string | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)
  const [runMessage, setRunMessage] = useState<string | null>(null)

  async function commit(next: BackupDestination) {
    setFormError(null)
    const merged = destinations.map((d) => (d.name === next.name ? next : d))
    try {
      await save(merged)
      setEditing(null)
    } catch (exc) {
      setFormError(exc instanceof Error ? exc.message : String(exc))
    }
  }

  async function toggle(destination: BackupDestination, enabled: boolean) {
    setRowError(null)
    try {
      await save(
        destinations.map((d) =>
          d.name === destination.name ? { ...d, enabled } : d,
        ),
      )
    } catch (exc) {
      setRowError(exc instanceof Error ? exc.message : String(exc))
    }
  }

  return (
    <ModuleSurface
      title="Backups"
      state={isLoading ? "empty" : "populated"}
      meta={`${destinations.length} destination${destinations.length === 1 ? "" : "s"}`}
    >
      <div className="space-y-3.5">
        <div className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-sm">
          <HardDriveDownload aria-hidden className="h-4 w-4" />
          <span>
            The host's systemd timer keeps its own local dumps independently of
            this job; the two never share a directory or a retention set.
          </span>
          <HelpTip label="About off-host backups">
            This job dumps the database with the image's own pg_dump, encrypts
            with each destination's age recipient, ships, reads every upload
            back to verify it, and prunes per destination. The age identity
            that decrypts is yours and never enters this database — a snapshot
            carrying its own decryption key would not be encrypted at rest.
          </HelpTip>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" disabled={isRunning} onClick={async () => {
            const result = await runNow()
            setRunMessage(
              result.ok ? "Backup run started." : (result.message ?? "Refused."),
            )
          }}>
            {isRunning ? "Running…" : "Run now"}
          </Button>
          {runMessage ? (
            <span className="text-muted-foreground text-sm">{runMessage}</span>
          ) : null}
        </div>

        {rowError ? (
          <p role="alert" className="text-destructive text-sm">
            {rowError}
          </p>
        ) : null}

        {destinations.length === 0 && !isLoading ? (
          <EmptyState
            kind="empty"
            icon={HardDriveDownload}
            title="No destinations configured"
            description="Nothing is shipped off this host until a destination exists. The systemd timer's local dumps are unaffected either way."
          />
        ) : (
          <ul className="space-y-2.5">
            {destinations.map((destination) => (
              <DestinationRow
                key={destination.name}
                destination={destination}
                outcome={recentOutcomes.get(destination.name) ?? null}
                busy={isSaving}
                onToggle={(enabled) => toggle(destination, enabled)}
                onEdit={() => {
                  setFormError(null)
                  setEditing(destination)
                }}
              />
            ))}
          </ul>
        )}
      </div>

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogTitle>Edit destination</DialogTitle>
          <DialogDescription>
            An untouched secret stays as it is. Typing into a masked field is
            the only way to replace it.
          </DialogDescription>
          {editing ? (
            <DestinationForm
              destination={editing}
              busy={isSaving}
              error={formError}
              onCancel={() => setEditing(null)}
              onSave={commit}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </ModuleSurface>
  )
}

function DestinationRow({
  destination,
  outcome,
  busy,
  onToggle,
  onEdit,
}: {
  destination: BackupDestination
  outcome: BackupOutcome | null
  busy: boolean
  onToggle: (enabled: boolean) => void
  onEdit: () => void
}) {
  return (
    <li className="border-border flex flex-wrap items-center gap-2.5 rounded-md border p-3">
      <span className="font-medium">{destination.name}</span>
      <Badge variant="outline" size="sm" className="font-mono">
        {destination.kind}
      </Badge>
      <span className="text-muted-foreground text-sm">
        keeps {destination.retention_keep}
      </span>
      {destination.kind !== "local" && !destination.age_recipient ? (
        <Badge variant="outline" size="sm" className="border-dashed">
          unencrypted
        </Badge>
      ) : null}
      <OutcomeLine outcome={outcome} />
      <div className="ml-auto flex items-center gap-2">
        <Switch
          checked={destination.enabled}
          disabled={busy}
          aria-label={`Enable ${destination.name}`}
          onCheckedChange={onToggle}
        />
        <Button variant="ghost" size="sm" onClick={onEdit}>
          Edit {destination.name}
        </Button>
      </div>
    </li>
  )
}

function OutcomeLine({ outcome }: { outcome: BackupOutcome | null }) {
  if (!outcome) {
    return <span className="text-muted-foreground text-sm">no run yet</span>
  }
  if (outcome.event_type === "backup_shipped") {
    return (
      <span className="text-muted-foreground flex items-center gap-1 text-sm">
        <ShieldCheck aria-hidden className="h-3.5 w-3.5" />
        verified {new Date(outcome.at).toLocaleString()}
      </span>
    )
  }
  return (
    <span className="text-destructive flex items-center gap-1 text-sm">
      <ShieldAlert aria-hidden className="h-3.5 w-3.5" />
      {outcome.error ?? "not restorable"}
    </span>
  )
}

function DestinationForm({
  destination,
  busy,
  error,
  onCancel,
  onSave,
}: {
  destination: BackupDestination
  busy: boolean
  error: string | null
  onCancel: () => void
  onSave: (next: BackupDestination) => void
}) {
  const [draft, setDraft] = useState<BackupDestination>(destination)

  useEffect(() => setDraft(destination), [destination])

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault()
        onSave(draft)
      }}
    >
      <div className="flex flex-col gap-1">
        <Label htmlFor="backup-keep" className="text-muted-foreground text-sm">
          Snapshots to keep
        </Label>
        <Input
          id="backup-keep"
          inputMode="numeric"
          value={String(draft.retention_keep)}
          onChange={(e) =>
            setDraft({ ...draft, retention_keep: Number(e.target.value) || 0 })
          }
        />
      </div>

      {draft.kind !== "local" ? (
        <div className="flex flex-col gap-1">
          <Label htmlFor="backup-recipient" className="text-muted-foreground text-sm">
            age recipient (public key)
          </Label>
          <Input
            id="backup-recipient"
            value={draft.age_recipient ?? ""}
            onChange={(e) =>
              setDraft({ ...draft, age_recipient: e.target.value || null })
            }
          />
        </div>
      ) : null}

      {draft.ssh ? (
        <div className="flex flex-col gap-1">
          <Label htmlFor="backup-ssh-key" className="text-muted-foreground text-sm">
            ssh private key
          </Label>
          <Input
            id="backup-ssh-key"
            value={draft.ssh.private_key}
            onChange={(e) =>
              setDraft({
                ...draft,
                ssh: { ...draft.ssh!, private_key: e.target.value },
              })
            }
          />
          {draft.ssh.private_key === MASKED ? (
            <p className="text-muted-foreground text-xs">
              Stored. Saving without editing this field keeps it.
            </p>
          ) : null}
        </div>
      ) : null}

      {draft.s3 ? (
        <div className="flex flex-col gap-1">
          <Label htmlFor="backup-s3-secret" className="text-muted-foreground text-sm">
            S3 secret access key
          </Label>
          <Input
            id="backup-s3-secret"
            value={draft.s3.secret_access_key}
            onChange={(e) =>
              setDraft({
                ...draft,
                s3: { ...draft.s3!, secret_access_key: e.target.value },
              })
            }
          />
          {draft.s3.secret_access_key === MASKED ? (
            <p className="text-muted-foreground text-xs">
              Stored. Saving without editing this field keeps it.
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy}>
          Save
        </Button>
      </div>
    </form>
  )
}
