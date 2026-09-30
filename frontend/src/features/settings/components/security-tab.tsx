import { Globe, Lock, ShieldCheck } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
} from "darkraise-ui/components/card"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import {
  useSecurityTabBinding,
  type SecurityTabBinding,
} from "../use-security-tab-binding"

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

export function SecurityTab() {
  const binding = useSecurityTabBinding()

  return (
    <div className="flex flex-col gap-6">
      <AuthCard binding={binding} />
      <SessionCard binding={binding} />
      <McpAccessCard binding={binding} />
    </div>
  )
}
