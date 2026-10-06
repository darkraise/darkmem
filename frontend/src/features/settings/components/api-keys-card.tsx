import { useState } from "react"
import { ChevronRight, KeyRound, Plus, Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "darkraise-ui/components/collapsible"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"
import { EmptyState, Timestamp } from "@/components/darkmem"
import {
  useApiKeys,
  useRevokeApiKey,
  type ApiKeySummary,
} from "@/hooks/api"
import { ApiKeyDialog, SCOPE_LABELS } from "./api-key-dialog"

/** Keys are stored and sent with the scope literals; only the display
 *  changes. An unknown literal falls back to itself rather than vanishing —
 *  a scope this build does not recognise is exactly the thing an operator
 *  must still see. */
const SCOPES = SCOPE_LABELS

const EXPIRES_SOON_MS = 7 * 24 * 60 * 60 * 1000

type KeyState = "active" | "expiring" | "expired"

function keyState(key: ApiKeySummary, now: number): KeyState {
  if (!key.expires_at) return "active"
  const left = new Date(key.expires_at).getTime() - now
  if (left <= 0) return "expired"
  return left < EXPIRES_SOON_MS ? "expiring" : "active"
}

const STATE_PILL: Record<KeyState, { label: string; className: string }> = {
  active: {
    label: "Active",
    className: "border-success/50 bg-success/10 text-success-text",
  },
  expiring: {
    label: "Expires soon",
    className: "border-warning/55 bg-warning/10 text-warning-text",
  },
  expired: {
    label: "Expired",
    className: "border-destructive/50 bg-destructive/8 text-destructive",
  },
}

function Pill({ className, children }: { className: string; children: string }) {
  return (
    <span
      className={cn(
        "shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium",
        className,
      )}
    >
      {children}
    </span>
  )
}

function ScopeChips({ scopes }: { scopes: string[] }) {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex flex-wrap gap-1.5">
        {scopes.map((scope) => {
          const words = SCOPES[scope]
          return (
            <Tooltip key={scope}>
              <TooltipTrigger asChild>
                <span
                  tabIndex={0}
                  className="bg-muted text-foreground rounded-md px-2 py-0.5 text-xs font-medium"
                >
                  {words?.short ?? scope}
                </span>
              </TooltipTrigger>
              <TooltipContent>{words?.full ?? scope}</TooltipContent>
            </Tooltip>
          )
        })}
      </div>
    </TooltipProvider>
  )
}

function KeyTile({
  apiKey,
  now,
  onRevoke,
}: {
  apiKey: ApiKeySummary
  now: number
  onRevoke?: (key: ApiKeySummary) => void
}) {
  const revoked = apiKey.revoked_at !== null
  const state = keyState(apiKey, now)
  const pill = revoked
    ? { label: "Revoked", className: "border-border text-muted-foreground" }
    : STATE_PILL[state]

  return (
    <article
      aria-label={apiKey.name}
      className={cn(
        "bg-card flex flex-col gap-3 rounded-lg border p-3.5",
        revoked && "bg-muted/30",
      )}
    >
      <div className="flex items-start gap-2.5">
        <span
          className={cn(
            "grid size-8 shrink-0 place-items-center rounded-md",
            revoked
              ? "bg-muted text-muted-foreground"
              : "bg-primary/10 text-primary-text",
          )}
        >
          <KeyRound aria-hidden className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p
            className={cn(
              "truncate text-sm font-semibold",
              revoked && "text-muted-foreground",
            )}
            title={apiKey.name}
          >
            {apiKey.name}
          </p>
          <p className="text-muted-foreground truncate font-mono text-xs">
            {apiKey.key_id}
          </p>
        </div>
        <Pill className={pill.className}>{pill.label}</Pill>
      </div>

      <ScopeChips scopes={apiKey.scopes} />

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Created</dt>
        <dd>
          <Timestamp iso={apiKey.created_at} />
        </dd>
        <dt className="text-muted-foreground">Last used</dt>
        <dd>
          {apiKey.last_used_at ? (
            <Timestamp iso={apiKey.last_used_at} />
          ) : (
            <span className="text-muted-foreground">Never</span>
          )}
        </dd>
        {apiKey.expires_at && (
          <>
            <dt className="text-muted-foreground">Expires</dt>
            <dd>{new Date(apiKey.expires_at).toLocaleDateString()}</dd>
          </>
        )}
        {revoked && (
          <>
            <dt className="text-muted-foreground">Revoked</dt>
            <dd>
              <Timestamp iso={apiKey.revoked_at} />
            </dd>
          </>
        )}
      </dl>

      {onRevoke && (
        <div className="border-border mt-auto flex justify-end border-t pt-2.5">
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={() => onRevoke(apiKey)}
          >
            <Trash2 aria-hidden className="mr-1.5 size-3.5" />
            Revoke
          </Button>
        </div>
      )}
    </article>
  )
}

const GRID = "grid gap-3 sm:grid-cols-2 xl:grid-cols-3"

export function ApiKeysCard() {
  const { data, isLoading, isError } = useApiKeys()
  const revokeKey = useRevokeApiKey()
  const [creating, setCreating] = useState(false)
  const [revoking, setRevoking] = useState<ApiKeySummary | null>(null)

  const keys = data ?? []
  const live = keys.filter((k) => k.revoked_at === null)
  const revoked = keys.filter((k) => k.revoked_at !== null)
  const now = Date.now()

  function confirmRevoke() {
    if (!revoking) return
    const target = revoking
    revokeKey.mutate(target.id, {
      onSuccess: () => {
        toast.success(`Revoked ${target.name}`)
        setRevoking(null)
      },
      onError: (error) => toast.error(`Could not revoke: ${error.message}`),
    })
  }

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 border-b px-4 py-2.5">
        <KeyRound aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 truncate font-mono text-xs font-semibold tracking-[0.14em] uppercase">
          Keys for apps and agents
        </h3>
        {!isLoading && !isError && keys.length > 0 && (
          <span className="text-muted-foreground hidden truncate text-sm sm:inline">
            {live.length} active
            {revoked.length > 0 && ` · ${revoked.length} revoked`}
          </span>
        )}
        <Button
          size="sm"
          className="ml-auto shrink-0"
          aria-label="New key"
          onClick={() => setCreating(true)}
        >
          <Plus aria-hidden className="size-3.5 sm:mr-1" />
          <span className="hidden sm:inline">New key</span>
        </Button>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 p-4">
        <p className="text-muted-foreground text-sm">
          A key lets an app or an AI agent use darkmem without signing in. It
          is shown once, when you create it.
        </p>

        {isLoading ? (
          <div className={GRID} aria-label="Loading keys">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-44 rounded-lg" />
            ))}
          </div>
        ) : isError ? (
          <p className="text-destructive text-sm">
            The list of keys could not be loaded.
          </p>
        ) : live.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={KeyRound}
            title={revoked.length > 0 ? "No active keys" : "No keys yet"}
            description="Create one to let an app or an AI agent reach darkmem."
          />
        ) : (
          <div className={GRID}>
            {live.map((key) => (
              <KeyTile
                key={key.id}
                apiKey={key}
                now={now}
                onRevoke={setRevoking}
              />
            ))}
          </div>
        )}

        {revoked.length > 0 && (
          // Revoked keys stay listed: the calls a key already made keep a
          // resolvable label in the per-memory timeline.
          <Collapsible>
            <CollapsibleTrigger className="group text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm">
              <ChevronRight
                aria-hidden
                className="size-4 transition-transform group-data-[state=open]:rotate-90"
              />
              Revoked keys ({revoked.length})
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className={cn(GRID, "pt-3")}>
                {revoked.map((key) => (
                  <KeyTile key={key.id} apiKey={key} now={now} />
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>

      <ApiKeyDialog open={creating} onOpenChange={setCreating} />

      <AlertDialog
        open={revoking !== null}
        onOpenChange={(open) => !open && setRevoking(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke {revoking?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Apps and agents using this key stop working immediately. This
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              data-variant="destructive"
              disabled={revokeKey.isPending}
              onClick={(e) => {
                e.preventDefault()
                confirmRevoke()
              }}
            >
              {revokeKey.isPending ? "Revoking…" : "Revoke key"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
