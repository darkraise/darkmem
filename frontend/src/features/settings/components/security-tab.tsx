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
import {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  type ApiKeyCreated,
} from "@/hooks/api"
import { ConfirmGate } from "./confirm-gate"
import {
  useSecurityTabBinding,
  type SecurityTabBinding,
} from "../use-security-tab-binding"

// The closed scope set itself, which is design rather than per-instance data
// and so stays a constant. `ratify` is listed precisely because it is *not* a
// scope: a reader must be able to see that the omission is deliberate.
const API_KEY_SCOPES: { label: string; inert?: boolean; never?: boolean }[] = [
  // Each scope names the surface it actually reaches (T4.21). The boundary is
  // the surface the minimal client speaks; widening `read` to the vault or the
  // code graph is a decision about what a leaked key can exfiltrate, and it is
  // demand-gated rather than taken because the word fits.
  { label: "capture — write memories (POST /memories, /memories/batch)" },
  { label: "read — search memories (POST /memories/search/paginated)" },
  { label: "admin — the push webhook" },
  { label: "ratify — never a scope, human cookie session only", never: true },
]

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

/** A field the backend has no read surface for at all today — never
 *  approximated (ruling 4), rendered as a labelled gap instead of a
 *  fabricated value or a silently omitted row. */
function UnavailableRow({ k, note }: { k: string; note: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-2 text-sm">
      <span className="text-muted-foreground w-32 shrink-0 font-mono text-sm">
        {k}
      </span>
      <span className="text-muted-foreground min-w-0 flex-1 italic">
        not exposed via the API — {note}
      </span>
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

function AuthCard({ binding }: { binding: SecurityTabBinding }) {
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const filled = current !== "" && next.length >= 8 && next === confirm

  return (
    <CardShell icon={ShieldCheck} title="Auth">
      <Row k="session">
        {binding.sessionSub ? `signed in as ${binding.sessionSub}` : "signed in"}
        {binding.sessionIssuedLabel && `, ${binding.sessionIssuedLabel}`}
        {binding.sessionJti && (
          <>
            {" "}
            <code className="font-mono">jti {binding.sessionJti}</code>
          </>
        )}
      </Row>
      {binding.sessionIssuedLabel === null && (
        <span className="text-muted-foreground -mt-1 text-sm italic">
          issue time and jti are not exposed via GET /auth/me (it returns
          only {"{authenticated, sub}"})
        </span>
      )}
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
        disabled={!filled || binding.changePasswordPending}
        trigger={
          <Button
            size="sm"
            variant="outline"
            className="border-primary/60 text-primary"
            disabled={!filled || binding.changePasswordPending}
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
          binding.changePassword({ currentPassword: current, newPassword: next })
          setCurrent("")
          setNext("")
          setConfirm("")
        }}
      />
      {binding.changePasswordError && (
        <p className="text-destructive text-sm">
          {binding.changePasswordError}
        </p>
      )}
      {binding.changePasswordSuccess && (
        <p className="text-success text-sm">
          Password changed — all pre-change tokens are now dead by iat.
        </p>
      )}
      <div className="border-border flex flex-col gap-1.5 border-t border-dashed pt-2">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
            login rate limiting — per-ip with lockout
          </span>
          <HelpTip label="About login rate limiting">
            {binding.rateLimitIpSource}
          </HelpTip>
        </div>
        {binding.rateLimitAttemptThreshold !== null ? (
          <Row k="attempt threshold">
            {binding.rateLimitAttemptThreshold} failed attempts
          </Row>
        ) : (
          <UnavailableRow
            k="attempt threshold"
            note="the login rate limiter's max_failures is an in-process constant with no config row or GET surface"
          />
        )}
        {binding.rateLimitLockoutWindow !== null ? (
          <Row k="lockout window">{binding.rateLimitLockoutWindow}</Row>
        ) : (
          <UnavailableRow k="lockout window" note="same constant as above" />
        )}
        {binding.rateLimitJournaled !== null ? (
          <Row k="journaled">{binding.rateLimitJournaled}</Row>
        ) : (
          <UnavailableRow
            k="journaled"
            note="no read endpoint aggregates auth_lockout events into a count"
          />
        )}
      </div>
    </CardShell>
  )
}

function TokensCard({ binding }: { binding: SecurityTabBinding }) {
  return (
    <CardShell
      icon={Lock}
      title="Tokens"
      help="Revocation must outlive the token, never the reverse — a blocklisted jti is checked on every authenticated request until its own exp passes."
    >
      {binding.blocklisted !== null ? (
        <Row k="blocklist">
          {binding.blocklisted} rows — swept by token_blocklist_cleanup, hourly,
          only after natural expiry
        </Row>
      ) : (
        <UnavailableRow
          k="blocklist"
          note="no endpoint reads the token_blocklist table's row count"
        />
      )}
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
            {binding.cookieSecureNote}
          </HelpTip>
        </div>
        {binding.cookieSecureValue !== null ? (
          <Row k="value">{binding.cookieSecureValue}</Row>
        ) : (
          <UnavailableRow
            k="value"
            note="app/config.py's cookie_secure setting has no GET surface"
          />
        )}
      </div>
    </CardShell>
  )
}

function TofuCard({ binding }: { binding: SecurityTabBinding }) {
  return (
    <CardShell
      icon={Flag}
      title="Setup — trust-on-first-use"
      chip={
        binding.tofuClaimed !== null ? (
          <SurfaceStateChip
            state="populated"
            label={binding.tofuClaimed ? "claimed" : "not claimed"}
          />
        ) : undefined
      }
      help="There is no SETUP_SECRET and none will be reintroduced — on a single-human LAN box the secret-distribution problem is strictly worse than the TOFU race it would close, and the race window is bounded by the LAN boundary plus the minutes between first boot and the wizard."
      className="sm:col-span-2"
    >
      <Row k="claimed at">
        {binding.tofuClaimedLabel ?? "loading — GET /api/v1/setup/status"}
      </Row>
      <Row k="gate">
        <code className="font-mono">require_uninitialized</code> 403s every
        request to <code className="font-mono">/api/v1/setup/*</code> now that{" "}
        <code className="font-mono">admin_password_hash</code> exists
      </Row>
      {binding.tofuJournaled !== null ? (
        <Row k="journaled">
          <code className="font-mono">{binding.tofuJournaled}</code>
        </Row>
      ) : (
        <UnavailableRow
          k="journaled"
          note="GET /setup/status returns only {initialized}, not the setup_completed event's payload"
        />
      )}
    </CardShell>
  )
}

function LanTrustCard({ binding }: { binding: SecurityTabBinding }) {
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
        {binding.mcpHosts !== null ? (
          <div className="flex flex-wrap gap-1.5">
            {binding.mcpHosts.map((h) => (
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
        ) : (
          <span className="text-muted-foreground text-sm italic">
            not exposed via the API — mcp_allowed_hosts is an env-var-backed
            setting with no GET surface
          </span>
        )}
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
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            active IP strategy
          </span>
          {binding.trustProxyHeaders !== null ? (
            <span className="font-mono text-sm">
              {binding.trustProxyHeaders
                ? "X-Real-IP (trusted proxy — trust_proxy_headers on)"
                : "raw socket peer (trust_proxy_headers off)"}
            </span>
          ) : (
            <span className="text-muted-foreground text-sm italic">
              not exposed via the API — trust_proxy_headers has no GET
              surface
            </span>
          )}
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

// The load-bearing honesty surface of this board (invariant 23), and its
// direction reversed by T4.04: this card declared the api_keys table dormant
// and every write `api_key_id=None`, which stopped being true when T4.01 wired
// the credential and T4.02 stamped the columns. A stale dormancy claim is the
// same defect as a premature shipped claim — it tells an operator a live
// credential path does not exist.
function ApiKeyCard() {
  const { data: keys, isLoading, isError } = useApiKeys()
  const createKey = useCreateApiKey()
  const revokeKey = useRevokeApiKey()
  const [label, setLabel] = useState("")
  const [scopes, setScopes] = useState("read")
  // The plaintext exists exactly once, on the create response. Holding it in
  // component state is what "shown once" means here: a reload loses it, and
  // there is no read surface that could hand it back.
  const [issued, setIssued] = useState<ApiKeyCreated | null>(null)

  const parsedScopes = scopes
    .split(/[,\s]+/)
    .map((scope) => scope.trim())
    .filter(Boolean)

  return (
    <CardShell
      icon={KeyRound}
      title="Programmatic ApiKey bearer"
      tag="live"
      help="A key is `dmk_<key_id>_<secret>` presented as `Authorization: Bearer`. Scopes are a closed set — capture, read, admin — and `ratify` is deliberately not among them: confirming a fact stays a human cookie session. Minting and revoking are behind the human door, so a key can never mint, list or revoke a key, including one holding admin. The MCP Host allowlist stays on regardless; a bearer is defence in addition to it, never instead of it."
      className="sm:col-span-2"
    >
      <div className="flex flex-wrap gap-2.5">
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="apikey-label" className="text-muted-foreground text-sm">
            Key label
          </Label>
          <Input
            id="apikey-label"
            placeholder="e.g. push-webhook"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1">
          <Label htmlFor="apikey-scope" className="text-muted-foreground text-sm">
            Scope
          </Label>
          <Input
            id="apikey-scope"
            placeholder="capture / read / admin"
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
          />
        </div>
      </div>
      <Button
        size="sm"
        variant="outline"
        className="w-fit"
        disabled={!label.trim() || parsedScopes.length === 0 || createKey.isPending}
        onClick={() =>
          createKey.mutate(
            { name: label.trim(), scopes: parsedScopes },
            {
              onSuccess: (created) => {
                setIssued(created)
                setLabel("")
              },
            },
          )
        }
      >
        <KeyRound className="mr-1.5 size-3.5" />
        {createKey.isPending ? "Creating key…" : "Create key"}
      </Button>
      {createKey.isError && (
        <p className="text-destructive text-sm">
          key not created — {createKey.error.message}
        </p>
      )}
      {issued && (
        <div className="border-border bg-muted/20 flex flex-col gap-1 rounded-md border border-dashed p-2.5">
          <span className="text-sm font-semibold">
            Copy this now — it is never shown again
          </span>
          <code className="font-mono text-sm break-all">{issued.token}</code>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        {isLoading ? (
          <span className="text-muted-foreground text-sm">loading keys…</span>
        ) : isError ? (
          <span className="text-muted-foreground text-sm">
            the key list could not be read — a failed read, not an empty list
          </span>
        ) : (keys ?? []).length === 0 ? (
          <span className="text-muted-foreground text-sm italic">
            no keys issued
          </span>
        ) : (
          (keys ?? []).map((key) => (
            <div
              key={key.id}
              className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-1.5 text-sm first:border-t-0 first:pt-0"
            >
              <span className="font-mono">{key.name}</span>
              <span className="text-muted-foreground font-mono text-sm">
                {key.key_id}
              </span>
              <span className="text-muted-foreground font-mono text-sm">
                {key.scopes.join(" · ")}
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

      <div className="flex flex-wrap gap-1.5">
        {API_KEY_SCOPES.map((scope) => (
          <span
            key={scope.label}
            className={cn(
              "text-muted-foreground border-muted-foreground/50 rounded-full border border-dashed px-2 py-0.5 font-mono text-sm",
              scope.inert && "opacity-60",
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
  const binding = useSecurityTabBinding()
  const blocklistedMeta =
    binding.blocklisted !== null ? `${binding.blocklisted} blocklisted · ` : ""
  const lockoutsMeta =
    binding.lockouts30d !== null ? `${binding.lockouts30d} lockouts / 30d` : ""

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Auth, tokens, the trust-on-first-use claim, the LAN trust model, and
          the programmatic ApiKey bearer.
        </span>
        <HelpTip label="About the Security tab">
          Auth (the admin password-change form and the session&apos;s
          cookie-JWT state), tokens (rotation, blocklist, the
          mass-revocation-by-iat rule a password change triggers), the
          trust-on-first-use claim, the LAN trust model, and the ApiKey
          bearer path, live since the credential was wired. Fields with no
          backend read surface (the blocklist count, the lockout count, the
          session's issue time and jti) render as an honest gap, never a
          guessed number; the posture fields — cookie_secure,
          trust_proxy_headers, mcp_allowed_hosts, the rate limiter's
          thresholds — are live reads.
        </HelpTip>
      </div>
      <ModuleSurface
        title="Security"
        state={binding.isLoading ? "empty" : "populated"}
        meta={blocklistedMeta + lockoutsMeta || undefined}
      >
        <div className="grid gap-3.5 sm:grid-cols-2">
          <AuthCard binding={binding} />
          <TokensCard binding={binding} />
          <TofuCard binding={binding} />
          <LanTrustCard binding={binding} />
          <ApiKeyCard />
        </div>
      </ModuleSurface>
    </div>
  )
}
