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

export type DestinationKind = "local" | "ssh" | "s3"

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

export interface BackupDestination {
  name: string
  kind: DestinationKind
  enabled: boolean
  retention_keep: number
  /** The age *public* key. The identity that decrypts is the operator's and
   *  never enters the database — a snapshot carrying its own decryption key
   *  is not encrypted at rest. */
  age_recipient: string | null
  ssh: SshSettings | null
  s3: S3Settings | null
}

export interface BackupDestinationsResponse {
  destinations: BackupDestination[]
}

export const BACKUP_DESTINATIONS_KEY = ["backupDestinations"] as const

export function useBackupDestinations() {
  return useQuery<BackupDestinationsResponse>({
    queryKey: BACKUP_DESTINATIONS_KEY,
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
    onSuccess: () => qc.invalidateQueries({ queryKey: BACKUP_DESTINATIONS_KEY }),
  })
}
