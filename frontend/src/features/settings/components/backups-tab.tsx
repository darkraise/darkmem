import { useEffect, useState } from "react"
import {
  Eye,
  EyeOff,
  HardDriveDownload,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Clipboard,
  ClipboardIndicator,
  ClipboardTrigger,
} from "darkraise-ui/components/clipboard"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  PasswordInput,
  PasswordInputControl,
  PasswordInputField,
  PasswordInputIndicator,
  PasswordInputVisibilityTrigger,
} from "darkraise-ui/components/password-input"
import { Textarea } from "darkraise-ui/components/textarea"
import { Switch } from "darkraise-ui/components/switch"
import { toast } from "darkraise-ui/components/sonner"
import { cn } from "darkraise-ui/lib"
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
  DialogTitle,
} from "darkraise-ui/components/dialog"

import { EmptyState } from "@/components/darkmem"
import { SettingsCard } from "./settings-card"
import {
  MASKED,
  type BackupDestination,
  type DestinationInventory,
  type DestinationKind,
  type InventoryOutcome,
} from "@/hooks/api/use-backups-api"
import {
  outcomeKey,
  useBackupsTabBinding,
  type BackupOutcome,
} from "@/features/settings/use-backups-tab-binding"

/**
 * The `backup_destinations` operator surface (increment 6, spec §9.3).
 *
 * **This is the second producer, not the only one.** The host's systemd timer
 * keeps its own local dumps whether or not the app is up.
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
function RetryButton({
  retrying,
  onRetry,
}: {
  retrying: boolean
  onRetry: () => void
}) {
  return (
    <Button disabled={retrying} onClick={onRetry}>
      {retrying ? "Retrying…" : "Retry"}
    </Button>
  )
}

export function BackupsTab() {
  const {
    destinations,
    inventory,
    recentOutcomes,
    save,
    runNow,
    isLoading,
    isError,
    isSaving,
    isRunning,
    destinationsError,
    retryDestinations,
    inventoryError,
    retryInventory,
    outcomesError,
    outcomesLoading,
    retryOutcomes,
    retrying,
  } = useBackupsTabBinding()

  const [editing, setEditing] = useState<BackupDestination | null>(null)
  // A new destination is the same form over a blank draft; it differs only
  // in what Save does (append rather than replace) and in naming the kind.
  const [adding, setAdding] = useState(false)
  // The dialog's 422 stays in the dialog; a refused switch is a toast, as for
  // every Settings control that saves at once.
  const [formError, setFormError] = useState<string | null>(null)
  const [runMessage, setRunMessage] = useState<string | null>(null)

  async function commit(next: BackupDestination) {
    setFormError(null)
    const merged = adding
      ? [...destinations, next]
      : destinations.map((d) => (d.name === next.name ? next : d))
    try {
      await save(merged)
      setEditing(null)
      setAdding(false)
    } catch (exc) {
      setFormError(exc instanceof Error ? exc.message : String(exc))
    }
  }

  function openAdd() {
    setFormError(null)
    setEditing(newDestination("local"))
    setAdding(true)
  }

  function closeForm() {
    setEditing(null)
    setAdding(false)
  }

  async function toggle(destination: BackupDestination, enabled: boolean) {
    try {
      await save(
        destinations.map((d) =>
          d.name === destination.name ? { ...d, enabled } : d,
        ),
      )
    } catch (exc) {
      toast.error(
        `${destination.name} not ${enabled ? "enabled" : "disabled"}`,
        { description: exc instanceof Error ? exc.message : String(exc) },
      )
    }
  }

  // Nothing to ship to: the empty state below says so, and a Run now that
  // stays live above it only earns a refusal. Unknown (loading or a failed
  // read) is not "none", so the button stays usable then.
  const noDestinations = !isLoading && !isError && destinations.length === 0

  return (
    <SettingsCard icon={HardDriveDownload} title="Backups">
      <div className="space-y-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            disabled={isRunning || noDestinations}
            aria-describedby={noDestinations ? "backups-run-hint" : undefined}
            onClick={async () => {
              const result = await runNow()
              setRunMessage(
                result.ok
                  ? "Backup run started."
                  : (result.message ?? "Refused."),
              )
            }}
          >
            {isRunning ? "Running…" : "Run now"}
          </Button>
          {noDestinations ? (
            <span
              id="backups-run-hint"
              className="text-muted-foreground text-sm"
            >
              Add a destination to run a backup.
            </span>
          ) : runMessage ? (
            <span className="text-muted-foreground text-sm">{runMessage}</span>
          ) : null}
          {/* Saving an added destination writes the whole list, so it waits
              for a list it can append to. */}
          <Button
            variant="outline"
            className="ml-auto"
            disabled={isLoading || isError}
            onClick={openAdd}
          >
            Add destination
          </Button>
        </div>

        {isError ? (
          // Not the empty state: "No destinations configured" tells an
          // operator their backups are not set up, which on a failed read is
          // both false and the most alarming thing this tab can say.
          <EmptyState
            kind="failed"
            title="Backup destinations could not be loaded"
            description={destinationsError?.message}
            action={
              <RetryButton
                retrying={retrying.destinations}
                onRetry={retryDestinations}
              />
            }
          />
        ) : destinations.length === 0 && !isLoading ? (
          <EmptyState
            kind="empty"
            icon={HardDriveDownload}
            title="No destinations configured"
            description="Nothing is shipped off this host until a destination exists."
            action={<Button onClick={openAdd}>Add destination</Button>}
          />
        ) : (
          <ul className="space-y-2.5">
            {destinations.map((destination) => (
              <DestinationRow
                key={destination.name}
                destination={destination}
                outcome={
                  recentOutcomes.get(outcomeKey(destination.name, "dump")) ??
                  null
                }
                attachmentOutcome={
                  recentOutcomes.get(
                    outcomeKey(destination.name, "attachments"),
                  ) ?? null
                }
                outcomesKnown={!outcomesError && !outcomesLoading}
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
        {outcomesError ? (
          <EmptyState
            kind="failed"
            title="Recent backup outcomes could not be loaded"
            description={outcomesError.message}
            action={
              <RetryButton retrying={retrying.outcomes} onRetry={retryOutcomes} />
            }
          />
        ) : null}
        {inventoryError ? (
          <EmptyState
            kind="failed"
            title="What each destination holds could not be loaded"
            description={inventoryError.message}
            action={
              <RetryButton
                retrying={retrying.inventory}
                onRetry={retryInventory}
              />
            }
          />
        ) : (
          <InventorySection inventory={inventory} />
        )}
      </div>

      <Dialog
        open={editing !== null}
        onOpenChange={(open) => !open && closeForm()}
      >
        <DialogContent
          className="max-h-[90vh] overflow-y-auto"
        >
          <DialogTitle>
            {adding ? "Add destination" : "Edit destination"}
          </DialogTitle>
          <DialogDescription>
            {adding
              ? "A destination off this host is shipped age-encrypted, so it needs the recipient's public key."
              : "An untouched secret stays as it is. Typing into a masked field is the only way to replace it."}
          </DialogDescription>
          {editing ? (
            <DestinationForm
              destination={editing}
              isNew={adding}
              busy={isSaving}
              error={formError}
              onCancel={closeForm}
              onSave={commit}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </SettingsCard>
  )
}

const KIND_LABELS: Record<DestinationKind, string> = {
  local: "local — this host's dump directory",
  ssh: "ssh — a directory on another machine",
  s3: "s3 — an S3-compatible bucket",
  worker: "worker — a darkmem backup worker",
}

/** A blank destination of one kind, with the server's own defaults. */
function newDestination(kind: DestinationKind, name = ""): BackupDestination {
  return {
    name,
    kind,
    enabled: true,
    retention_keep: 14,
    attachments_retention_keep: 3,
    age_recipient: null,
    ssh:
      kind === "ssh"
        ? {
            host: "",
            port: 22,
            user: "",
            remote_dir: "",
            host_key: "",
            private_key: "",
          }
        : null,
    s3:
      kind === "s3"
        ? {
            endpoint_url: "",
            bucket: "",
            prefix: "",
            region: "auto",
            access_key_id: "",
            secret_access_key: "",
          }
        : null,
    worker: kind === "worker" ? { url: "", token: "" } : null,
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ["KB", "MB", "GB", "TB"]
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(1)} ${units[unit]}`
}

/** What each destination is actually holding, and the command to restore it.
 *
 *  There is deliberately no restore button. Restoring replaces the live
 *  database, and section 9.6 makes it a shell command so the act stays with a
 *  human at a console who has read what is here first. This section's job is
 *  to make that decision informed, not to make it one click away. */
function InventorySection({
  inventory,
}: {
  inventory: DestinationInventory[]
}) {
  if (inventory.length === 0) return null
  return (
    <div className="border-border flex flex-col gap-2.5 border-t border-dashed pt-3">
      <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        what each destination holds
      </span>
      {inventory.map((row) => (
        <div key={row.name} className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{row.name}</span>
            <Badge variant="outline" size="sm" className="font-mono">
              {row.kind}
            </Badge>
            <OutcomeBadge outcome={row.last_outcome} label="database" />
            <OutcomeBadge
              outcome={row.last_attachment_outcome}
              label="attachments"
            />
          </div>
          {row.error ? (
            <p className="text-destructive-text text-sm">{row.error}</p>
          ) : row.snapshots.length === 0 ? (
            <p className="text-muted-foreground text-sm">no snapshots yet</p>
          ) : (
            <ul className="text-muted-foreground space-y-0.5 text-sm">
              {[...row.snapshots]
                .sort((a, b) => b.name.localeCompare(a.name))
                .map((snapshot) => (
                  <li key={snapshot.name} className="flex flex-wrap gap-2">
                    <span className="font-mono">{snapshot.name}</span>
                    <span>{formatBytes(snapshot.size)}</span>
                    <span>
                      {new Date(snapshot.modified_at).toLocaleString()}
                    </span>
                  </li>
                ))}
            </ul>
          )}
          {row.error ? null : row.attachment_snapshots.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              no attachment tarballs yet
            </p>
          ) : (
            <ul className="text-muted-foreground space-y-0.5 text-sm">
              {[...row.attachment_snapshots]
                .sort((a, b) => b.name.localeCompare(a.name))
                .map((snapshot) => (
                  <li key={snapshot.name} className="flex flex-wrap gap-2">
                    <span className="font-mono">{snapshot.name}</span>
                    <span>{formatBytes(snapshot.size)}</span>
                    <span>
                      {new Date(snapshot.modified_at).toLocaleString()}
                    </span>
                  </li>
                ))}
            </ul>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <code className="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">
              {`./scripts/restore.sh --from ${row.name} --latest`}
            </code>
            <Clipboard
              value={`./scripts/restore.sh --from ${row.name} --latest`}
              toast
            >
              <ClipboardTrigger>
                <ClipboardIndicator copied="Copied" fallback="Copy" />
              </ClipboardTrigger>
            </Clipboard>
          </div>
        </div>
      ))}
      <p className="text-muted-foreground text-sm">
        Restoring replaces the live database.
      </p>
    </div>
  )
}

/** One family's verdict. Two badges rather than one, because the dump and the
 *  attachment tarball ship and fail independently and an operator choosing a
 *  snapshot needs both answers. */
function OutcomeBadge({
  outcome,
  label,
}: {
  outcome: InventoryOutcome | null
  label: string
}) {
  if (!outcome) return null
  const verified = outcome.event_type === "backup_shipped"
  return (
    <Badge
      variant="outline"
      size="sm"
      className={verified ? "" : "border-dashed"}
    >
      {label}: {verified ? "verified" : "not restorable"}
    </Badge>
  )
}

function DestinationRow({
  destination,
  outcome,
  attachmentOutcome,
  outcomesKnown,
  busy,
  onToggle,
  onEdit,
}: {
  destination: BackupDestination
  outcome: BackupOutcome | null
  attachmentOutcome: BackupOutcome | null
  /** False while the outcomes read has failed: a missing outcome is then
   *  unknown, not "no run yet". */
  outcomesKnown: boolean
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
      {outcomesKnown ? (
        <>
          <OutcomeLine outcome={outcome} label="database" />
          <OutcomeLine outcome={attachmentOutcome} label="attachments" />
        </>
      ) : null}
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

function OutcomeLine({
  outcome,
  label,
}: {
  outcome: BackupOutcome | null
  label: string
}) {
  if (!outcome) {
    return (
      <span className="text-muted-foreground text-sm">{label}: no run yet</span>
    )
  }
  if (outcome.event_type === "backup_shipped") {
    return (
      <span className="text-muted-foreground flex items-center gap-1 text-sm">
        <ShieldCheck aria-hidden className="h-3.5 w-3.5" />
        {label}: verified {new Date(outcome.at).toLocaleString()}
      </span>
    )
  }
  return (
    <span className="text-destructive-text flex items-center gap-1 text-sm">
      <ShieldAlert aria-hidden className="h-3.5 w-3.5" />
      {label}: {outcome.error ?? "not restorable"}
    </span>
  )
}

function DestinationForm({
  destination,
  isNew = false,
  busy,
  error,
  onCancel,
  onSave,
}: {
  destination: BackupDestination
  /** Name and kind are identity: set once on create, fixed after. */
  isNew?: boolean
  busy: boolean
  error: string | null
  onCancel: () => void
  onSave: (next: BackupDestination) => void
}) {
  const [draft, setDraft] = useState<BackupDestination>(destination)

  useEffect(() => setDraft(destination), [destination])

  const setSsh = (patch: Partial<NonNullable<BackupDestination["ssh"]>>) =>
    setDraft((d) => ({ ...d, ssh: { ...d.ssh!, ...patch } }))
  const setS3 = (patch: Partial<NonNullable<BackupDestination["s3"]>>) =>
    setDraft((d) => ({ ...d, s3: { ...d.s3!, ...patch } }))

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault()
        onSave(draft)
      }}
    >
      {isNew ? (
        <>
          <div className="flex flex-col gap-1">
            <Label
              htmlFor="backup-name"
              className="text-muted-foreground text-sm"
            >
              Name
            </Label>
            <Input
              id="backup-name"
              autoComplete="off"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-muted-foreground text-sm">Kind</Label>
            <Select
              value={draft.kind}
              onValueChange={(v) => {
                const kind = v as DestinationKind
                // Swap the connection block, keep what the operator typed
                // into the fields every kind shares.
                const blank = newDestination(kind, draft.name)
                setDraft({
                  ...blank,
                  retention_keep: draft.retention_keep,
                  attachments_retention_keep: draft.attachments_retention_keep,
                  age_recipient: kind === "local" ? null : draft.age_recipient,
                })
              }}
            >
              <SelectTrigger aria-label="Destination kind">
                <SelectValue>{KIND_LABELS[draft.kind]}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(KIND_LABELS) as DestinationKind[]).map((k) => (
                  <SelectItem key={k} value={k}>
                    {KIND_LABELS[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      ) : null}

      {draft.ssh ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_6rem]">
          <TextField
            id="backup-ssh-host"
            label="ssh host"
            value={draft.ssh.host}
            onChange={(host) => setSsh({ host })}
          />
          <TextField
            id="backup-ssh-port"
            label="Port"
            inputMode="numeric"
            value={String(draft.ssh.port)}
            onChange={(port) => setSsh({ port: Number(port) || 0 })}
          />
          <TextField
            id="backup-ssh-user"
            label="User"
            value={draft.ssh.user}
            onChange={(user) => setSsh({ user })}
          />
          <TextField
            id="backup-ssh-dir"
            label="Remote directory"
            value={draft.ssh.remote_dir}
            onChange={(remote_dir) => setSsh({ remote_dir })}
            className="sm:col-span-2"
          />
          <div className="flex flex-col gap-1 sm:col-span-2">
            <Label
              htmlFor="backup-ssh-host-key"
              className="text-muted-foreground text-sm"
            >
              Host key (a known_hosts line, pinned)
            </Label>
            <Input
              id="backup-ssh-host-key"
              spellCheck={false}
              className="font-mono text-xs"
              value={draft.ssh.host_key}
              onChange={(e) => setSsh({ host_key: e.target.value })}
            />
          </div>
        </div>
      ) : null}

      {draft.s3 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <TextField
            id="backup-s3-endpoint"
            label="Endpoint URL"
            value={draft.s3.endpoint_url}
            onChange={(endpoint_url) => setS3({ endpoint_url })}
            className="sm:col-span-2"
          />
          <TextField
            id="backup-s3-bucket"
            label="Bucket"
            value={draft.s3.bucket}
            onChange={(bucket) => setS3({ bucket })}
          />
          <TextField
            id="backup-s3-prefix"
            label="Prefix"
            value={draft.s3.prefix}
            onChange={(prefix) => setS3({ prefix })}
          />
          <TextField
            id="backup-s3-region"
            label="Region"
            value={draft.s3.region}
            onChange={(region) => setS3({ region })}
          />
          <TextField
            id="backup-s3-access-key"
            label="Access key id"
            value={draft.s3.access_key_id}
            onChange={(access_key_id) => setS3({ access_key_id })}
          />
        </div>
      ) : null}
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

      <div className="flex flex-col gap-1">
        <Label
          htmlFor="backup-attachment-keep"
          className="text-muted-foreground text-sm"
        >
          Attachment tarballs to keep
        </Label>
        <Input
          id="backup-attachment-keep"
          inputMode="numeric"
          value={String(draft.attachments_retention_keep)}
          onChange={(e) =>
            setDraft({
              ...draft,
              attachments_retention_keep: Number(e.target.value) || 0,
            })
          }
        />
      </div>

      {draft.kind !== "local" ? (
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="backup-recipient"
            className="text-muted-foreground text-sm"
          >
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
          <Label
            htmlFor="backup-ssh-key"
            className="text-muted-foreground text-sm"
          >
            ssh private key
          </Label>
          {/* A textarea: a PEM key is multi-line, and a single-line input
              flattened it on paste. */}
          <Textarea
            id="backup-ssh-key"
            rows={4}
            spellCheck={false}
            autoComplete="off"
            className="font-mono text-xs"
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

      {draft.worker ? (
        <>
          <div className="flex flex-col gap-1">
            <Label
              htmlFor="backup-worker-url"
              className="text-muted-foreground text-sm"
            >
              Receiver URL
            </Label>
            <Input
              id="backup-worker-url"
              value={draft.worker.url}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  worker: { ...draft.worker!, url: e.target.value },
                })
              }
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label
              htmlFor="backup-worker-token"
              className="text-muted-foreground text-sm"
            >
              Receiver token
            </Label>
            <SecretField
              id="backup-worker-token"
              value={draft.worker.token}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  worker: { ...draft.worker!, token: value },
                })
              }
            />
            {draft.worker.token === MASKED ? (
              <p className="text-muted-foreground text-xs">
                Stored. Saving without editing this field keeps it.
              </p>
            ) : null}
          </div>
        </>
      ) : null}

      {draft.s3 ? (
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="backup-s3-secret"
            className="text-muted-foreground text-sm"
          >
            S3 secret access key
          </Label>
          <SecretField
            id="backup-s3-secret"
            value={draft.s3.secret_access_key}
            onChange={(value) =>
              setDraft({
                ...draft,
                s3: { ...draft.s3!, secret_access_key: value },
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
        <p role="alert" className="text-destructive-text text-sm">
          {error}
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={busy || !draft.name.trim()}>
          {isNew ? "Add" : "Save"}
        </Button>
      </div>
    </form>
  )
}

function TextField({
  id,
  label,
  value,
  onChange,
  inputMode,
  className,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  inputMode?: "numeric"
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <Label htmlFor={id} className="text-muted-foreground text-sm">
        {label}
      </Label>
      <Input
        id={id}
        autoComplete="off"
        inputMode={inputMode}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

/** A credential field: masked by default with a reveal toggle, so a token or
 *  secret is not left on screen in clear text while the form is open. */
function SecretField({
  id,
  value,
  onChange,
}: {
  id: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <PasswordInput>
      <PasswordInputControl>
        <PasswordInputField
          id={id}
          value={value}
          autoComplete="off"
          onChange={(e) => onChange(e.target.value)}
        />
        <PasswordInputVisibilityTrigger>
          <PasswordInputIndicator
            visible={<EyeOff aria-hidden className="h-4 w-4" />}
            hidden={<Eye aria-hidden className="h-4 w-4" />}
          />
        </PasswordInputVisibilityTrigger>
      </PasswordInputControl>
    </PasswordInput>
  )
}
