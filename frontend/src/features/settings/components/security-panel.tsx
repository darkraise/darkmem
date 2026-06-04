import { useState } from "react"
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

export function SecurityPanel() {
  const [filterIdx, setFilterIdx] = useState(0)
  const [offset, setOffset] = useState(0)
  const action = FILTERS[filterIdx]?.action

  const { data, isLoading } = useAuditLog({ limit: PAGE_SIZE, offset, action })
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
            <div className="border-border flex w-fit flex-wrap gap-1 rounded-md border p-0.5">
              {FILTERS.map((f, i) => (
                <Button
                  key={f.label}
                  variant="ghost"
                  onClick={() => setFilter(i)}
                  className={`rounded px-3 py-1 text-base font-medium transition-colors ${
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
          {isLoading ? (
            <div className="bg-muted h-40 animate-pulse rounded" />
          ) : items.length === 0 ? (
            <p className="text-muted-foreground py-8 text-center text-base">
              No audit events recorded.
            </p>
          ) : (
            <div className="divide-border border-border divide-y rounded-md border">
              {items.map((e) => (
                <div
                  key={e.id}
                  className="flex items-center justify-between gap-3 px-3 py-2"
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={actionVariant(e.action)}
                      className="text-base"
                    >
                      {e.action.replace(/^auth_|^setup_/, "")}
                    </Badge>
                    <span className="text-muted-foreground text-base">
                      {detailText(e.details)}
                    </span>
                  </div>
                  <span className="text-muted-foreground font-mono text-base">
                    {e.timestamp ? relativeTime(e.timestamp) : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="text-muted-foreground mt-3 flex items-center justify-between text-base">
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
