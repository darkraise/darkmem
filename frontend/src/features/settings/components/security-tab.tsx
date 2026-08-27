import { useState } from "react"
import {
  Flag,
  Globe,
  KeyRound,
  Lock,
  ShieldCheck,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardHeader,
} from "darkraise-ui/components/card"
import { cn } from "darkraise-ui/lib"
import { ApiKeyDialog } from "./api-key-dialog"
import { EmptyState, HelpTip } from "@/components/darkmem"
import {
  SurfaceStateChip,
} from "@/features/activity/components/module-surface"
import { useApiKeys, useRevokeApiKey } from "@/hooks/api"
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
  // demand-gated rather than taken because the word fits. The routes each one
  // covers: capture -> POST /memories and /memories/batch; read -> POST
  // /memories/search/paginated; admin -> the push webhook.
  { label: "Save new memories" },
  { label: "Search and read memories" },
  { label: "Receive push updates" },
  { label: "Confirming a fact is never allowed — only you can do that", never: true },
]

/** The scope literals as a reader should see them in a key's row. Keys are
 *  stored and sent with the literals; only the display changes. An unknown
 *  literal falls back to itself rather than vanishing — a scope this build
 *  does not recognise is exactly the thing an operator must still see. */
const SCOPE_WORDS: Record<string, string> = {
  capture: "Save new memories",
  read: "Search and read memories",
  admin: "Receive push updates",
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

/** One card of security facts or controls.
 *
 *  Mirrors the Flags tab's `Section`: a library `Card` with a one-row header
 *  carrying the title, its help tip and a status tag, and the body below the
 *  divider. These were `div`s nested inside one outer surface, which made five
 *  distinct subjects — auth, tokens, the TOFU claim, the LAN posture, the key
 *  credential — read as one long panel.
 *
 *  `dormant` keeps its dashed treatment for a card describing something not
 *  wired; the border is already the inset step, so a dormant card reads softer
 *  still rather than louder. */
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
    <Card className={cn("gap-0 py-0", dormant && "border-dashed", className)}>
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 overflow-hidden border-b px-4 py-2.5">
        <Icon aria-hidden className="text-primary h-4 w-4 shrink-0" />
        <h3
          className={cn(
            "min-w-0 truncate text-sm font-semibold",
            dormant && "text-muted-foreground",
          )}
        >
          {title}
        </h3>
        {help && (
          <span className="shrink-0">
            <HelpTip label={`About ${title}`}>{help}</HelpTip>
          </span>
        )}
        {chip}
        <span className="flex-1" />
        {tag && (
          <span className="text-muted-foreground border-muted-foreground/60 shrink-0 rounded-full border border-dashed px-2.5 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap">
            {tag}
          </span>
        )}
      </CardHeader>
      <CardContent
        className={cn(
          "flex flex-col gap-2.5 p-4",
          dormant && "bg-muted/10",
        )}
      >
        {children}
      </CardContent>
    </Card>
  )
}

function PillFlow({ steps }: { steps: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {steps.map((step, i) => (
        <span key={step} className="flex items-center gap-1.5">
          <span
            className={cn(
              "border-inset bg-muted/40 rounded-full border px-2.5 py-0.5 font-mono text-sm whitespace-nowrap",
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
  return (
    <CardShell icon={ShieldCheck} title="Auth">
      <Row k="session">
        {binding.sessionSub ? `signed in as ${binding.sessionSub}` : "signed in"}
        {binding.sessionIssuedLabel && `, ${binding.sessionIssuedLabel}`}
        {binding.sessionJti && (
          <>
            {" · "}
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
      {/* The form moved to the user menu (Change password). A pointer rather
          than a second copy: two password forms against one credential is two
          places for the validation and the revocation warning to drift. */}
      <Row k="password">
        changed from the{" "}
        <b className="text-foreground font-semibold">user menu</b> — the avatar
        at the top right, <b className="text-foreground font-semibold">Change
        password</b>. It is an account action rather than a posture setting, and
        it is reachable from every page.
      </Row>

      <div className="border-inset flex flex-col gap-1.5 border-t border-dashed pt-2">
        <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
          login rate limiting — per-IP with lockout
        </span>
        <Row k="IP source">
          <span className="text-muted-foreground">
            {binding.rateLimitIpSource}
          </span>
        </Row>
        {binding.rateLimitAttemptThreshold !== null ? (
          <Row k="attempt threshold">
            {binding.rateLimitAttemptThreshold} failed attempts
          </Row>
        ) : (
          <UnavailableRow
            k="attempt threshold"
            note="not exposed via the API"
          />
        )}
        {binding.rateLimitLockoutWindow !== null ? (
          <Row k="lockout window">{binding.rateLimitLockoutWindow}</Row>
        ) : (
          <UnavailableRow k="lockout window" note="not exposed via the API" />
        )}
        {binding.rateLimitJournaled !== null ? (
          <Row k="journaled">{binding.rateLimitJournaled}</Row>
        ) : (
          <UnavailableRow
            k="journaled"
            note="not exposed via the API — no read endpoint aggregates auth_lockout events into a count"
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
      help="darkmem trusts its LAN, authenticates its human by session, and authenticates its agents by a per-tool-scoped bearer key — a credential, not a session. Three postures, one service layer underneath all of them."
      className="sm:col-span-2"
    >
      <div className="border-inset bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm font-semibold">/mcp</span>
          <HelpTip label="About the /mcp door">
            Every call requires Authorization: Bearer dmk_…, with scopes
            enforced per tool. The Host allowlist is a second, independent
            guard: an unkeyed request gets 401 regardless of Host, and only a
            keyed request that also fails the Host check gets 421, fixed by
            extending the allowlist — never by disabling either guard.
          </HelpTip>
          <span className="text-muted-foreground ml-auto font-mono text-[10px]">
            Bearer key required — scoped per tool
          </span>
        </div>
        {binding.mcpHosts !== null ? (
          <div className="flex flex-wrap gap-1.5">
            {binding.mcpHosts.map((h) => (
              <span
                key={h.host}
                className={cn(
                  "border-inset bg-background rounded-full border px-2 py-0.5 font-mono text-sm",
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
      <div className="border-inset bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
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
      <div className="border-inset bg-muted/12 flex flex-col gap-1.5 rounded-md border px-3 py-2">
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
  const revokeKey = useRevokeApiKey()
  const [creating, setCreating] = useState(false)

  const rows = keys ?? []

  return (
    <CardShell
      icon={KeyRound}
      title="Keys for apps and agents"
      tag="live"
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
            The list of keys could not be loaded. This is a failed read, not an
            empty list — your keys are still there.
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

      <div className="flex flex-wrap gap-1.5">
        {API_KEY_SCOPES.map((scope) => (
          <span
            key={scope.label}
            className={cn(
              "text-muted-foreground border-muted-foreground/50 rounded-full border border-dashed px-2 py-0.5 text-sm",
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
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 rounded-lg border px-4 py-2.5">
        <span className="text-sm font-semibold">Security</span>
        {(blocklistedMeta + lockoutsMeta) && (
          <span className="text-muted-foreground font-mono text-sm">
            {blocklistedMeta + lockoutsMeta}
          </span>
        )}
        <span className="ml-auto">
          <SurfaceStateChip state={binding.isLoading ? "empty" : "populated"} />
        </span>
      </div>

      <div className="flex flex-col gap-6">
        <AuthCard binding={binding} />
        <TokensCard binding={binding} />
        <TofuCard binding={binding} />
        <LanTrustCard binding={binding} />
        <ApiKeyCard />
      </div>
    </div>
  )
}
