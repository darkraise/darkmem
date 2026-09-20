import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** The literal a secret is replaced by on every read that leaves the server.
 *
 *  Sending it back on a PUT means "the value you already hold" — the server
 *  resolves it against the stored row before validating. That is what makes
 *  the form round-trippable without a private key ever crossing the wire in
 *  either direction. */
export const MASKED = "***"

export type DestinationKind = "local" | "ssh" | "s3" | "worker"

export interface SshSettings {
  host: string
  port: number
  user: string
  remote_dir: string
  /** A known_hosts line, pinned. Never trust-on-first-use. */
  host_key: string
  private_key: string
}

export interface S3Settings {
  endpoint_url: string
  bucket: string
  prefix: string
  region: string
  access_key_id: string
  secret_access_key: string
}

export interface WorkerSettings {
  url: string
  /** The receiver's bearer. Authorisation, not confidentiality: content
   *  arrives age-encrypted, so `age_recipient` is what protects the bytes. */
  token: string
}

export interface BackupDestination {
  name: string
  kind: DestinationKind
  enabled: boolean
  retention_keep: number
  attachments_retention_keep: number
  /** The age *public* key. The identity that decrypts is the operator's and
   *  never enters the database — a snapshot carrying its own decryption key
   *  is not encrypted at rest. */
  age_recipient: string | null
  ssh: SshSettings | null
  s3: S3Settings | null
  worker: WorkerSettings | null
}

export interface BackupDestinationsResponse {
  destinations: BackupDestination[]
}

// Spelled as a literal at every `queryKey:` site rather than hoisted into a
// const: `src/lib/__tests__/query-keys.test.ts` discovers domains by matching
// `queryKey: ["<literal>"`, so a hoisted key is invisible to the guard that
// exists to stop a key escaping classification. Every other hook in this
// directory does the same.
export function useBackupDestinations() {
  return useQuery<BackupDestinationsResponse>({
    queryKey: ["backupDestinations"],
    queryFn: () => apiFetch<BackupDestinationsResponse>("/config/backup-destinations"),
    // Demo mode runs with no backend; without this gate the query 401s and
    // the auth interceptor redirects the whole demo to /login.
    enabled: !DEMO,
  })
}

export function useSaveBackupDestinations() {
  const qc = useQueryClient()
  return useMutation<BackupDestinationsResponse, Error, BackupDestination[]>({
    mutationFn: (destinations) =>
      apiFetch<BackupDestinationsResponse>("/config/backup-destinations", {
        method: "PUT",
        body: JSON.stringify({ destinations }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backupDestinations"] }),
  })
}

// ── The snapshot inventory (increment 7, spec §9.6) ──────────────────

export interface InventorySnapshot {
  name: string
  size: number
  modified_at: string
}

export interface InventoryOutcome {
  event_type: "backup_shipped" | "backup_verify_failed"
  at: string
  sha256: string | null
  error: string | null
}

export interface DestinationInventory {
  name: string
  kind: DestinationKind
  enabled: boolean
  retention_keep: number
  attachments_retention_keep: number
  snapshots: InventorySnapshot[]
  attachment_snapshots: InventorySnapshot[]
  last_outcome: InventoryOutcome | null
  /** The attachment tarball's own last outcome. Separate because the two
   *  artefacts ship and fail independently. */
  last_attachment_outcome: InventoryOutcome | null
  /** Why this destination could not be listed. A field rather than a failed
   *  page: one unreachable NAS must not blank what the others hold. */
  error: string | null
}

export interface InventoryResponse {
  destinations: DestinationInventory[]
}

export function useBackupInventory() {
  return useQuery<InventoryResponse>({
    queryKey: ["backupInventory"],
    queryFn: () => apiFetch<InventoryResponse>("/backups/inventory"),
    enabled: !DEMO,
  })
}
