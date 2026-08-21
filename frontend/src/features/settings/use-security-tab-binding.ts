import { useMutation, useQuery } from "@tanstack/react-query"
import { DEMO } from "@/lib/demo-flag"
import { useDemoSecurity } from "@/demo/hooks"
import { apiFetch, ApiError } from "@/lib/api"

export interface ChangePasswordInput {
  currentPassword: string
  newPassword: string
}

/**
 * `T | null` fields have no real-mode source at all — no endpoint returns
 * them. `GET /auth/security-posture` (added to close this gap) covers
 * `trustProxyHeaders`, `cookieSecureValue`, `mcpHosts` and the rate-limit
 * thresholds; the remainder (session issue time/jti, the blocklist count,
 * the auth_lockout journal count) still have no backend read surface —
 * rendered null and skipped by the component (T1.45's precedent), never
 * approximated (ruling 4).
 */
export interface SecurityTabBinding {
  isLoading: boolean
  blocklisted: number | null
  lockouts30d: number | null
  sessionSub: string | null
  sessionIssuedLabel: string | null
  sessionJti: string | null
  rateLimitIpSource: string
  rateLimitAttemptThreshold: number | null
  rateLimitLockoutWindow: string | null
  rateLimitJournaled: string | null
  cookieSecureValue: string | null
  cookieSecureNote: string
  /** null while the /setup/status probe is in flight — never defaulted to
   *  either true or false, since both are meaningfully different claims. */
  tofuClaimed: boolean | null
  tofuClaimedLabel: string | null
  tofuJournaled: string | null
  trustProxyHeaders: boolean | null
  mcpHosts: { host: string; wild?: boolean }[] | null
  changePassword: (input: ChangePasswordInput) => void
  changePasswordPending: boolean
  changePasswordError: string | null
  changePasswordSuccess: boolean
}

interface SetupStatusResponse {
  initialized: boolean
}

interface AuthMeResponse {
  authenticated: boolean
  sub: string
}

interface SecurityPostureResponse {
  trust_proxy_headers: boolean
  cookie_secure: boolean
  cookie_secure_explicit: boolean
  cookie_secure_clamped: boolean
  environment: string
  mcp_allowed_hosts: string[]
  rate_limit_max_failures: number
  rate_limit_window_seconds: number
  rate_limit_lockout_seconds: number
}

function formatSeconds(seconds: number): string {
  if (seconds % 60 === 0 && seconds > 0) return `${seconds / 60} minutes`
  return `${seconds}s`
}

export function useSecurityTabBinding(): SecurityTabBinding {
  const demoSec = useDemoSecurity()

  const statusQuery = useQuery<SetupStatusResponse>({
    queryKey: ["setupStatus"],
    queryFn: () => apiFetch<SetupStatusResponse>("/setup/status"),
    enabled: !DEMO,
  })
  const meQuery = useQuery<AuthMeResponse>({
    queryKey: ["authMe"],
    queryFn: () => apiFetch<AuthMeResponse>("/auth/me"),
    enabled: !DEMO,
  })
  const postureQuery = useQuery<SecurityPostureResponse>({
    queryKey: ["securityPosture"],
    queryFn: () => apiFetch<SecurityPostureResponse>("/auth/security-posture"),
    enabled: !DEMO,
  })
  const changePasswordMutation = useMutation<
    { ok: boolean },
    Error,
    ChangePasswordInput
  >({
    mutationFn: (input) =>
      apiFetch<{ ok: boolean }>("/auth/change-password", {
        method: "POST",
        // A 401 here means the CURRENT password was wrong, not that the
        // session died. Under the default handling it signed the operator out
        // over a typo and discarded the server's own message.
        on401: "surface",
        body: JSON.stringify({
          current_password: input.currentPassword,
          new_password: input.newPassword,
        }),
      }),
  })

  if (DEMO) {
    return {
      isLoading: false,
      blocklisted: demoSec.blocklisted,
      lockouts30d: demoSec.lockouts_30d,
      sessionSub: "admin",
      sessionIssuedLabel: demoSec.session.issued_label,
      sessionJti: demoSec.session.jti,
      rateLimitIpSource: demoSec.rate_limit.ip_source,
      rateLimitAttemptThreshold: demoSec.rate_limit.attempt_threshold,
      rateLimitLockoutWindow: demoSec.rate_limit.lockout_window,
      rateLimitJournaled: demoSec.rate_limit.journaled,
      cookieSecureValue: demoSec.cookie_secure.value,
      cookieSecureNote: demoSec.cookie_secure.note,
      tofuClaimed: true,
      tofuClaimedLabel: demoSec.tofu.claimed_label,
      tofuJournaled: demoSec.tofu.journaled,
      trustProxyHeaders: true,
      mcpHosts: demoSec.mcp_hosts,
      changePassword: () => {},
      changePasswordPending: false,
      changePasswordError: null,
      changePasswordSuccess: false,
    }
  }

  const posture = postureQuery.data

  return {
    isLoading: statusQuery.isLoading || meQuery.isLoading || postureQuery.isLoading,
    blocklisted: null,
    lockouts30d: null,
    sessionSub: meQuery.data?.sub ?? null,
    sessionIssuedLabel: null,
    sessionJti: null,
    rateLimitIpSource: posture
      ? posture.trust_proxy_headers
        ? "X-Real-IP (trust_proxy_headers is on) — the leftmost X-Forwarded-For is never trusted"
        : "the raw transport-socket peer (trust_proxy_headers is off)"
      : "X-Real-IP when trust_proxy_headers is on (an operator TLS proxy in front) — the leftmost X-Forwarded-For is never trusted",
    rateLimitAttemptThreshold: posture?.rate_limit_max_failures ?? null,
    rateLimitLockoutWindow: posture ? formatSeconds(posture.rate_limit_lockout_seconds) : null,
    rateLimitJournaled: null,
    cookieSecureValue: posture
      ? `${posture.cookie_secure} — ${
          posture.cookie_secure_clamped
            ? "enforced by the exposed posture, overriding an explicit false"
            : posture.cookie_secure_explicit
              ? "explicit"
              : `default for environment=${posture.environment}`
        }`
      : null,
    cookieSecureNote:
      "Unset means Secure-only when environment=production; explicit false permits login over plain-HTTP LAN. " +
      "With trust_proxy_headers on the tri-state collapses to enforced — an explicit false is overridden, not honoured.",
    tofuClaimed: statusQuery.data?.initialized ?? null,
    tofuClaimedLabel: statusQuery.data
      ? statusQuery.data.initialized
        ? "claimed"
        : "not yet claimed"
      : null,
    tofuJournaled: null,
    trustProxyHeaders: posture?.trust_proxy_headers ?? null,
    mcpHosts: posture
      ? posture.mcp_allowed_hosts.length > 0
        ? posture.mcp_allowed_hosts.map((host) => ({ host, wild: host === "*" }))
        : [{ host: "localhost only (mcp_allowed_hosts is empty — the default)" }]
      : null,
    changePassword: (input) => changePasswordMutation.mutate(input),
    changePasswordPending: changePasswordMutation.isPending,
    changePasswordError:
      changePasswordMutation.error instanceof ApiError
        ? changePasswordMutation.error.message
        : changePasswordMutation.error?.message ?? null,
    changePasswordSuccess: changePasswordMutation.isSuccess,
  }
}
