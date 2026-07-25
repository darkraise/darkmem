import { useState } from "react"
import {
  Check,
  Flag,
  Globe,
  KeyRound,
  Lock,
  ShieldCheck,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import {
  ModuleSurface,
  SurfaceStateChip,
} from "@/features/activity/components/module-surface"
import { useDemoSecurity } from "@/demo/hooks"
import { ConfirmGate } from "./confirm-gate"

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

function CardShell({
  icon: Icon,
  title,
  tag,
  chip,
  help,
  dormant,
  className,
  children,
}: {
  icon: typeof Lock
  title: string
  tag?: string
  chip?: React.ReactNode
  help?: React.ReactNode
  dormant?: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={cn(
        "border-border bg-card flex flex-col gap-2.5 rounded-lg border p-3.5",
        dormant && "bg-muted/10 border-dashed",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Icon aria-hidden className="text-muted-foreground h-4 w-4" />
        <span
          className={cn(
            "text-sm font-semibold",
            dormant && "text-muted-foreground",
          )}
        >
          {title}
        </span>
        {help && <HelpTip label={`About ${title}`}>{help}</HelpTip>}
        {chip}
        {tag && (
          <span className="text-muted-foreground border-muted-foreground/60 ml-auto rounded-full border border-dashed px-2.5 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap">
            {tag}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}

function PillFlow({ steps }: { steps: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {steps.map((step, i) => (
        <span key={step} className="flex items-center gap-1.5">
          <span
            className={cn(
              "border-border bg-muted/40 rounded-full border px-2.5 py-0.5 font-mono text-sm whitespace-nowrap",
              i === 0 && "border-primary/55 text-primary bg-primary/8",
            )}
          >
            {step}
          </span>
          {i < steps.length - 1 && (
            <span className="text-muted-foreground">→</span>
          )}
        </span>
      ))}
    </div>
  )
}

function AuthCard() {
  const sec = useDemoSecurity()
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const [changed, setChanged] = useState(false)
  const filled = current !== "" && next.length >= 8 && next === confirm

  return (
    <CardShell icon={ShieldCheck} title="Auth">
      <Row k="session">
        signed in — {sec.session.issued_label},{" "}
        <code className="font-mono">jti {sec.session.jti}</code>
      </Row>
      <div className="flex flex-wrap gap-2.5">
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="sec-pw-current" className="text-sm">
            Current password
          </Label>
          <Input
            id="sec-pw-current"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="sec-pw-new" className="text-sm">
            New password
          </Label>
          <Input
            id="sec-pw-new"
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="sec-pw-confirm" className="text-sm">
            Confirm new password
          </Label>
          <Input
            id="sec-pw-confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
      </div>
      {/* The revocation consequence stays visible next to the trigger — a
          destructive side effect is never demoted to a hover. */}
      <p className="text-warning text-sm">
        <b className="font-semibold">
          Changing your password revokes every token minted before this moment
        </b>{" "}
        — the iat check treats them as dead on arrival.
      </p>
      <ConfirmGate
        tone="danger"
        disabled={!filled}
        trigger={
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={!filled}
            tabIndex={-1}
          >
            <Check className="mr-1.5 size-3.5" />
            Change password
          </Button>
        }
        headline="Change the admin password now?"
        desc="Every token minted before this moment is revoked — the iat check treats them as dead on arrival, so any other signed-in session is signed out immediately. This is the box's only credential."
        confirmLabel="Confirm — change password"
        onConfirm={() => {
          setChanged(true)
          setCurrent("")
          setNext("")
          setConfirm("")
        }}
      />
      {changed && (
        <p className="text-success text-sm">
          Password changed (demo) — all pre-change tokens are now dead by iat.
        </p>
      )}
      <div className="border-border flex flex-col gap-1.5 border-t border-dashed pt-2">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
            login rate limiting — per-ip with lockout
          </span>
          <HelpTip label="About login rate limiting">
            {sec.rate_limit.ip_source}
          </HelpTip>
        </div>
        <Row k="attempt threshold">
          {sec.rate_limit.attempt_threshold} failed attempts
        </Row>
        <Row k="lockout window">{sec.rate_limit.lockout_window}</Row>
        <Row k="journaled">{sec.rate_limit.journaled}</Row>
      </div>
    </CardShell>
  )
}

function TokensCard() {
  const sec = useDemoSecurity()
  return (
    <CardShell
      icon={Lock}
      title="Tokens"
      help="Revocation must outlive the token, never the reverse — a blocklisted jti is checked on every authenticated request until its own exp passes."
    >
      <Row k="blocklist">
        {sec.blocklisted} rows — swept by token_blocklist_cleanup, hourly, only
        after natural expiry
      </Row>
      <PillFlow steps={["active", "blocklisted (rotation)", "swept"]} />
      <PillFlow
        steps={["active", "dead by iat (password change — ALL pre-change tokens)"]}
      />
      <PillFlow steps={["active", "expired (exp elapses)"]} />
      <div className="border-border flex flex-col gap-1.5 border-t border-dashed pt-2">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
            cookie_secure — tri-state
          </span>
          <HelpTip label="About cookie_secure">
            {sec.cookie_secure.note}
          </HelpTip>
        </div>
        <Row k="value">{sec.cookie_secure.value}</Row>
      </div>
    </CardShell>
  )
}

function TofuCard() {
  const sec = useDemoSecurity()
  return (
    <CardShell
      icon={Flag}
      title="Setup — trust-on-first-use"
      chip={<SurfaceStateChip state="populated" label="claimed" />}
      help="There is no SETUP_SECRET and none will be reintroduced — on a single-human LAN box the secret-distribution problem is strictly worse than the TOFU race it would close, and the race window is bounded by the LAN boundary plus the minutes between first boot and the wizard."
      className="sm:col-span-2"
    >
      <Row k="claimed">{sec.tofu.claimed_label}</Row>
      <Row k="gate">
        <code className="font-mono">require_uninitialized</code> 403s every
        request to <code className="font-mono">/api/v1/setup/*</code> now that{" "}
        <code className="font-mono">admin_password_hash</code> exists
      </Row>
      <Row k="journaled">
        <code className="font-mono">{sec.tofu.journaled}</code>
      </Row>
    </CardShell>
  )
}

function LanTrustCard() {
  const sec = useDemoSecurity()
  return (
    <CardShell
      icon={Globe}
      title="LAN trust model"
      tag="v1 committed posture"
      help="darkmem trusts its LAN, authenticates its human, and attributes — but does not authenticate — its agents. Three postures, one service layer underneath all of them."
      className="sm:col-span-2"
    >
      <div className="border-border bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold">/mcp</span>
          <HelpTip label="About the /mcp door">
            Unauthenticated by design. A foreign Host header gets 421, fixed
            by extending the allowlist — never by disabling the check.
          </HelpTip>
          <span className="text-muted-foreground ml-auto font-mono text-[10px]">
            Host allowlist only, no credential
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {sec.mcp_hosts.map((h) => (
            <span
              key={h.host}
              className={cn(
                "border-border bg-background rounded-full border px-2 py-0.5 font-mono text-sm",
                h.wild && "text-warning border-warning/55 border-dashed",
              )}
            >
              {h.host}
            </span>
          ))}
        </div>
      </div>
      <div className="border-border bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold">/api/v1 + /ws</span>
          <HelpTip label="About the /api/v1 and /ws door">
            The one authenticated door on this box; /ws rejects a
            missing/invalid/revoked token with close code 1008 before joining
            the broadcast set.
          </HelpTip>
          <span className="text-muted-foreground ml-auto font-mono text-[10px]">
            cookie JWT — the human door
          </span>
        </div>
      </div>
      <div className="border-border bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold">/setup</span>
          <HelpTip label="About the /setup door">
            See the Setup card above — closes itself permanently the moment
            the first wizard run completes.
          </HelpTip>
          <span className="text-muted-foreground ml-auto font-mono text-[10px]">
            trust-on-first-use, open only until claimed
          </span>
        </div>
      </div>
    </CardShell>
  )
}

// The load-bearing honesty surface of this board (invariant 23): the
// api_keys table is dormant and unwired — every control renders disabled,
// and this card must never read as "on" in any state.
function DormantApiKeyCard() {
  const sec = useDemoSecurity()
  return (
    <CardShell
      icon={KeyRound}
      title="Programmatic ApiKey bearer"
      tag="Phase-4 · designed, not wired"
      help="This card previews the fixed design so no interim feature invents a second credential shape. It activates on the first genuine off-LAN need — an exposed deployment or the repo push-webhook receiver, whichever comes first. The Host allowlist stays on even after activation; a bearer key is defense in addition to it, never instead of it."
      dormant
      className="sm:col-span-2"
    >
      {/* The dormant state stays visible in full — never tooltip-only. */}
      <p className="text-muted-foreground text-sm">
        The <code className="font-mono">api_keys</code> table exists in the
        schema but is dormant — every write on this box today still passes{" "}
        <code className="font-mono">api_key_id=None</code>. It is{" "}
        <b className="font-semibold">not available in this deployment</b> and
        every control below is disabled.
      </p>
      <div className="flex flex-wrap gap-2.5">
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="apikey-label" className="text-muted-foreground text-sm">
            Key label
          </Label>
          <Input
            id="apikey-label"
            placeholder="unavailable until activation"
            disabled
            className="border-dashed"
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="apikey-scope" className="text-muted-foreground text-sm">
            Scope
          </Label>
          <Input
            id="apikey-scope"
            placeholder="capture / read / admin"
            disabled
            className="border-dashed"
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="apikey-expiry" className="text-muted-foreground text-sm">
            Expiry
          </Label>
          <Input
            id="apikey-expiry"
            placeholder="optional"
            disabled
            className="border-dashed"
          />
        </div>
      </div>
      <Button size="sm" variant="outline" disabled className="w-fit">
        <KeyRound className="mr-1.5 size-3.5" />
        Create key — unavailable until activation
      </Button>
      <div className="flex flex-wrap gap-1.5">
        {sec.api_key_scopes.map((scope) => (
          <span
            key={scope.label}
            className={cn(
              "text-muted-foreground border-muted-foreground/50 rounded-full border border-dashed px-2 py-0.5 font-mono text-sm",
              scope.never && "border-destructive/50 text-destructive",
            )}
          >
            {scope.label}
          </span>
        ))}
      </div>
    </CardShell>
  )
}

export function SecurityTab() {
  const sec = useDemoSecurity()
  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Auth, tokens, the trust-on-first-use claim, the LAN trust model, and
          the dormant Phase-4 ApiKey path.
        </span>
        <HelpTip label="About the Security tab">
          Auth (the admin password-change form and the session&apos;s
          cookie-JWT state), tokens (rotation, blocklist, the
          mass-revocation-by-iat rule a password change triggers), the
          trust-on-first-use claim, the LAN trust model, and the dormant
          ApiKey bearer path — kept visibly Phase-4 so nothing here overclaims
          a credential path that does not exist yet.
        </HelpTip>
      </div>
      <ModuleSurface
        title="Security"
        state="populated"
        meta={`${sec.blocklisted} blocklisted · ${sec.lockouts_30d} lockouts / 30d`}
      >
        <div className="grid gap-3.5 sm:grid-cols-2">
          <AuthCard />
          <TokensCard />
          <TofuCard />
          <LanTrustCard />
          <DormantApiKeyCard />
        </div>
      </ModuleSurface>
    </div>
  )
}
