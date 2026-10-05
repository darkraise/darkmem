import { useState } from "react"
import { Globe, KeyRound, Lock, ShieldCheck } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"
import { ChangePasswordDialog } from "./change-password-dialog"
import { SettingsCard } from "./settings-card"
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
    <SettingsCard icon={Icon} title={title} help={help} className={className}>
      {children}
    </SettingsCard>
  )
}

function AuthCard({ binding }: { binding: SecurityTabBinding }) {
  // The control itself, not a pointer to the user menu: on a phone "top
  // right" is a single avatar glyph. Mounted only while open, and never in
  // demo, where the shell does not wire the dialog either (there is no
  // server to take the change).
  const [changingPassword, setChangingPassword] = useState(false)
  return (
    <CardShell icon={ShieldCheck} title="Sign-in">
      <Row k="session">
        {binding.sessionSub
          ? `signed in as ${binding.sessionSub}`
          : "signed in"}
      </Row>
      <Row k="password">
        {DEMO ? (
          <span className="text-muted-foreground">
            Not changeable in the demo.
          </span>
        ) : (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setChangingPassword(true)}
          >
            <KeyRound aria-hidden className="mr-1.5 size-3.5" />
            Change password
          </Button>
        )}
      </Row>
      {changingPassword && (
        <ChangePasswordDialog open onOpenChange={setChangingPassword} />
      )}

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
            When on, the session cookie is only sent over HTTPS. It is off only
            on a plain-HTTP LAN install.
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
          <div className="flex flex-wrap items-center gap-1.5">
            {binding.mcpHosts.map((h) => (
              <span
                key={h.host}
                title={h.wild ? "* disables the Host allowlist" : undefined}
                className={cn(
                  "border-inset bg-background rounded-full border px-2 py-0.5 font-mono text-sm",
                  h.wild && "text-warning-text border-warning/55 border-dashed",
                )}
              >
                {h.host}
              </span>
            ))}
            {binding.mcpHosts.some((h) => h.wild) && (
              <HelpTip label="About the * host">
                The * entry turns the Host allowlist off: a keyed request is
                accepted whatever host it names. Every call still needs an API
                key.
              </HelpTip>
            )}
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
