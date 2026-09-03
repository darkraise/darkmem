import { ShieldCheck } from "lucide-react"
import { useState } from "react"
import { EmptyState } from "@/components/darkmem"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { useAuditLog, type AuditEntry } from "@/hooks/api"
import { relativeTime } from "@/lib/format"

const PAGE_SIZE = 50

const FILTERS: { label: string; action?: string }[] = [
  { label: "All" },
  { label: "Failed logins", action: "auth_login_failed" },
  { label: "Logins", action: "auth_login_success" },
  { label: "Password changes", action: "auth_password_change" },
]

function actionVariant(
  action: string,
): "default" | "destructive" | "secondary" {
  if (action === "auth_login_failed") return "destructive"
  if (action === "auth_login_success") return "default"
  return "secondary"
}

function detailText(details: Record<string, unknown>): string {
  if (typeof details.ip === "string") return `IP ${details.ip}`
  if (typeof details.sub === "string") return `as ${details.sub}`
  return ""
}

/** UNREACHABLE as of 2026-09-03: nothing imports this module or its export,
 *  the settings barrel re-exports only `./schemas`, there is no dynamic
 *  import, and neither of its strings appears in any built chunk. The live
 *  Security surface is `security-tab.tsx`.
 *
 *  The `isError` guard below is therefore defensive, not a shipped repair —
 *  it is kept so this cannot be wired up fail-open, since an audit surface
 *  that renders "no events" on a failed read understates what it holds. The
 *  real resolution is to delete this file; that is the owner's call. */
export function SecurityPanel() {
  const [filterIdx, setFilterIdx] = useState(0)
  const [offset, setOffset] = useState(0)
  const action = FILTERS[filterIdx]?.action

  const { data, isLoading, isError } = useAuditLog({ limit: PAGE_SIZE, offset, action })
  const items: AuditEntry[] = data?.items ?? []
  const total = data?.total ?? 0

  const setFilter = (idx: number) => {
    setFilterIdx(idx)
    setOffset(0)
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-lg uppercase tracking-wide">
              Audit log
            </CardTitle>
            <div className="border-inset flex w-fit flex-wrap gap-1 rounded-md border p-0.5">
              {FILTERS.map((f, i) => (
                <Button
                  key={f.label}
                  variant="ghost"
                  onClick={() => setFilter(i)}
                  className={`rounded px-3 py-1 font-medium transition-colors ${
                    filterIdx === i
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {f.label}
                </Button>
              ))}
            </div>
          </div>
          <CardDescription>
            Authentication and account-security events, most recent first.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          {isError ? (
            // Not the empty state: an audit surface that renders "no events"
            // on a failed read is the one screen that must never understate
            // what it holds.
            <p className="text-destructive text-sm">
              The audit log could not be loaded — a failed read, not an empty
              journal.
            </p>
          ) : isLoading ? (
            <div className="bg-muted h-40 animate-pulse rounded" />
          ) : items.length === 0 ? (
            <EmptyState
              kind="empty"
              icon={ShieldCheck}
              title="No audit events yet"
              description="Sign-ins, lockouts and setup steps are journalled here as they happen."
            />
          ) : (
            <div className="divide-border border-inset divide-y rounded-md border">
              {items.map((e) => (
                <div
                  key={e.id}
                  className="flex items-center justify-between gap-3 px-3 py-2"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={actionVariant(e.action)}>
                      {e.action.replace(/^auth_|^setup_/, "")}
                    </Badge>
                    <span className="text-muted-foreground text-sm">
                      {detailText(e.details)}
                    </span>
                  </div>
                  <span className="text-muted-foreground font-mono text-sm">
                    {e.timestamp ? relativeTime(e.timestamp) : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="text-muted-foreground mt-3 flex items-center justify-between text-sm">
            <span>
              {total > 0
                ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} of ${total}`
                : "0 events"}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                disabled={offset === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
