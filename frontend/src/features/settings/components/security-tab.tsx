import { useState } from "react"
import { Globe, KeyRound, Lock, ShieldCheck } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
} from "darkraise-ui/components/card"
import { cn } from "darkraise-ui/lib"
import { ApiKeyDialog } from "./api-key-dialog"
import { EmptyState, HelpTip } from "@/components/darkmem"
import { useApiKeys, useRevokeApiKey } from "@/hooks/api"
import {
  useSecurityTabBinding,
  type SecurityTabBinding,
} from "../use-security-tab-binding"

/** The scope literals as a reader should see them in a key's row. Keys are
 *  stored and sent with the literals; only the display changes. An unknown
 *  literal falls back to itself rather than vanishing — a scope this build
 *  does not recognise is exactly the thing an operator must still see. */
const SCOPE_WORDS: Record<string, string> = {
  capture: "Save new memories",
  read: "Search and read memories",
  admin: "Receive push updates, reindex repositories, delete document subtrees",
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline gap-2 text-sm">
      <span className="text-muted-foreground w-32 shrink-0 font-mono text-sm">
        {k}
      </span>
      <span className="min-w-0 flex-1">{children}</span>
    </div>
  )
}

/** One card of security facts or controls.
 *
 *  Mirrors the Flags tab's `Section`: a library `Card` with a one-row header
 *  carrying the title and its help tip, and the body below the divider. */
function CardShell({
  icon: Icon,
  title,
  help,
  className,
  children,
}: {
  icon: typeof Lock
  title: string
  help?: React.ReactNode
  className?: string
  children: React.ReactNode
}) {
  return (
    <Card className={cn("gap-0 py-0", className)}>
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        <Icon aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="min-w-0 truncate text-sm font-semibold">{title}</h3>
        {help && (
          <span className="shrink-0">
            <HelpTip label={`About ${title}`}>{help}</HelpTip>
          </span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5 p-4">
        {children}
      </CardContent>
    </Card>
  )
}

function AuthCard({ binding }: { binding: SecurityTabBinding }) {
  return (
    <CardShell icon={ShieldCheck} title="Sign-in">
      <Row k="session">
        {binding.sessionSub ? `signed in as ${binding.sessionSub}` : "signed in"}
      </Row>
      <Row k="password">
        Change it from the user menu at the top right.
      </Row>

      <div className="border-inset flex flex-col gap-1.5 border-t border-dashed pt-2">
        <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
          login rate limiting
        </span>
        {binding.rateLimitIpSource !== null && (
          <Row k="IP source">
            <span className="text-muted-foreground">
              {binding.rateLimitIpSource}
            </span>
          </Row>
        )}
        {binding.rateLimitAttemptThreshold !== null && (
          <Row k="attempt threshold">
            {binding.rateLimitAttemptThreshold} failed attempts
          </Row>
        )}
        {binding.rateLimitLockoutWindow !== null && (
          <Row k="lockout window">{binding.rateLimitLockoutWindow}</Row>
        )}
      </div>
    </CardShell>
  )
}

function SessionCard({ binding }: { binding: SecurityTabBinding }) {
  return (
    <CardShell icon={Lock} title="Session">
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
            secure cookie
          </span>
          <HelpTip label="About the secure cookie">
            When on, the session cookie is only sent over HTTPS. It is off
            only on a plain-HTTP LAN install.
          </HelpTip>
        </div>
        {binding.cookieSecureValue !== null && (
          <Row k="value">{binding.cookieSecureValue}</Row>
        )}
      </div>
      <div className="border-border flex flex-col gap-1.5 border-t border-dashed pt-2">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
            read-only mode
          </span>
          <HelpTip label="About read-only mode">
            A read-only instance serves a restored backup and refuses every
            write.
          </HelpTip>
        </div>
        {binding.readOnly !== null && (
          <Row k="value">
            {binding.readOnly
              ? "on — this instance is a read-only backup"
              : "off"}
          </Row>
        )}
        {binding.readOnlyTokenRotationDisabled && (
          <Row k="token rotation">
            off — signing out or refreshing does not revoke the old token
          </Row>
        )}
      </div>
    </CardShell>
  )
}

function McpAccessCard({ binding }: { binding: SecurityTabBinding }) {
  return (
    <CardShell
      icon={Globe}
      title="MCP access"
      help="Every MCP call needs an API key. A client on another machine also needs its host listed here, set with MCP_ALLOWED_HOSTS."
      className="sm:col-span-2"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground font-mono text-xs uppercase">
          allowed hosts
        </span>
        {binding.mcpHosts !== null && (
          <div className="flex flex-wrap gap-1.5">
            {binding.mcpHosts.map((h) => (
              <span
                key={h.host}
                className={cn(
                  "border-inset bg-background rounded-full border px-2 py-0.5 font-mono text-sm",
                  h.wild && "text-warning-text border-warning/55 border-dashed",
                )}
              >
                {h.host}
              </span>
            ))}
          </div>
        )}
      </div>
    </CardShell>
  )
}

function ApiKeyCard() {
  const { data: keys, isLoading, isError } = useApiKeys()
  const revokeKey = useRevokeApiKey()
  const [creating, setCreating] = useState(false)

  const rows = keys ?? []

  return (
    <CardShell
      icon={KeyRound}
      title="Keys for apps and agents"
      // Plain language on purpose: whoever runs this box is not necessarily
      // the person who wrote it. The precise contract - the `dmk_<id>_<secret>`
      // shape, the closed scope set, minting being behind the human door, the
      // Host allowlist standing regardless - lives in doc 18 §5 and in
      // `api_key_scopes.py`, where the next developer needs it. A settings
      // card is not the place to teach it.
      help="A key lets an app or an AI agent use darkmem without logging in. You choose what each key may do, and you can revoke it whenever you like. The key itself is shown only once, when you create it."
      className="sm:col-span-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-muted-foreground text-sm">
          {rows.length === 0
            ? "No keys yet"
            : `${rows.length} ${rows.length === 1 ? "key" : "keys"}`}
        </span>
        <Button variant="outline" onClick={() => setCreating(true)}>
          <KeyRound className="mr-1.5 size-3.5" />
          New key
        </Button>
      </div>

      <ApiKeyDialog open={creating} onOpenChange={setCreating} />

      <div className="flex flex-col gap-1.5">
        {isLoading ? (
          <span className="text-muted-foreground text-sm">loading keys…</span>
        ) : isError ? (
          <span className="text-muted-foreground text-sm">
            The list of keys could not be loaded.
          </span>
        ) : rows.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={KeyRound}
            title="No keys yet"
            description="Create one to let an app or an AI agent reach darkmem."
          />
        ) : (
          rows.map((key) => (
            <div
              key={key.id}
              className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-1.5 text-sm first:border-t-0 first:pt-0"
            >
              <span className="font-mono">{key.name}</span>
              <span className="text-muted-foreground font-mono text-sm">
                {key.key_id}
              </span>
              <span className="text-muted-foreground text-sm">
                {key.scopes.map((s) => SCOPE_WORDS[s] ?? s).join(" · ")}
              </span>
              <span className="text-muted-foreground text-sm">
                {key.last_used_at
                  ? `last used ${new Date(key.last_used_at).toLocaleString()}`
                  : "never used"}
              </span>
              {key.revoked_at ? (
                // Kept listed on purpose: the row survives revocation so the
                // calls it already made keep a resolvable label in the
                // per-object timeline.
                <span className="text-muted-foreground ml-auto text-sm">
                  revoked {new Date(key.revoked_at).toLocaleString()}
                </span>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  className="ml-auto"
                  disabled={revokeKey.isPending}
                  onClick={() => revokeKey.mutate(key.id)}
                >
                  Revoke
                </Button>
              )}
            </div>
          ))
        )}
      </div>
    </CardShell>
  )
}

export function SecurityTab() {
  const binding = useSecurityTabBinding()

  return (
    <div className="flex flex-col gap-6">
      <AuthCard binding={binding} />
      <SessionCard binding={binding} />
      <McpAccessCard binding={binding} />
      <ApiKeyCard />
    </div>
  )
}
