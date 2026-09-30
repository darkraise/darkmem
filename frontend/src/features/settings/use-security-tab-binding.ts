import { useQuery } from "@tanstack/react-query"
import { DEMO } from "@/lib/demo-flag"
import { useDemoSecurity } from "@/demo/hooks"
import { apiFetch } from "@/lib/api"

/**
 * Every `T | null` field is null until `GET /auth/security-posture` (or
 * `/auth/me`) answers; the component skips a null row rather than
 * approximating it.
 */
export interface SecurityTabBinding {
  sessionSub: string | null
  rateLimitIpSource: string | null
  rateLimitAttemptThreshold: number | null
  rateLimitLockoutWindow: string | null
  cookieSecureValue: string | null
  mcpHosts: { host: string; wild?: boolean }[] | null
  readOnly: boolean | null
  readOnlyTokenRotationDisabled: boolean | null
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
  read_only: boolean
  read_only_token_rotation_disabled: boolean
}

function formatSeconds(seconds: number): string {
  if (seconds % 60 === 0 && seconds > 0) return `${seconds / 60} minutes`
  return `${seconds}s`
}

function ipSource(trustProxyHeaders: boolean): string {
  return trustProxyHeaders
    ? "X-Real-IP header (trusted proxy)"
    : "direct connection address"
}

export function useSecurityTabBinding(): SecurityTabBinding {
  const demoSec = useDemoSecurity()

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

  if (DEMO) {
    return {
      sessionSub: "admin",
      rateLimitIpSource: ipSource(true),
      rateLimitAttemptThreshold: demoSec.rate_limit.attempt_threshold,
      rateLimitLockoutWindow: demoSec.rate_limit.lockout_window,
      cookieSecureValue: demoSec.cookie_secure.value,
      mcpHosts: demoSec.mcp_hosts,
      // The demo is a production-shaped instance, not a worker.
      readOnly: false,
      readOnlyTokenRotationDisabled: false,
    }
  }

  const posture = postureQuery.data

  return {
    sessionSub: meQuery.data?.sub ?? null,
    rateLimitIpSource: posture ? ipSource(posture.trust_proxy_headers) : null,
    rateLimitAttemptThreshold: posture?.rate_limit_max_failures ?? null,
    rateLimitLockoutWindow: posture ? formatSeconds(posture.rate_limit_lockout_seconds) : null,
    cookieSecureValue: posture
      ? `${posture.cookie_secure ? "on" : "off"} — ${
          posture.cookie_secure_clamped
            ? "forced on because the instance trusts proxy headers"
            : posture.cookie_secure_explicit
              ? "set explicitly"
              : `default for the ${posture.environment} environment`
        }`
      : null,
    mcpHosts: posture
      ? posture.mcp_allowed_hosts.length > 0
        ? posture.mcp_allowed_hosts.map((host) => ({ host, wild: host === "*" }))
        : [{ host: "localhost only" }]
      : null,
    readOnly: posture?.read_only ?? null,
    readOnlyTokenRotationDisabled:
      posture?.read_only_token_rotation_disabled ?? null,
  }
}
