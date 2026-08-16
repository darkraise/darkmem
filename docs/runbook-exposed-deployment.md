# Runbook — exposing darkmem beyond the LAN

**Who this is for.** An operator putting darkmem behind a TLS proxy so it is
reachable from outside the trusted LAN. Everything here is additive: every LAN
rule below still holds underneath (doc 18 §9).

**darkmem does not terminate TLS and never will.** It has no certificate
handling, no ACME client and no HTTP→HTTPS redirect. The certificate, the
renewal, and the redirect are the operator's proxy's job. If you have not put a
TLS proxy in front, you are not in this posture — stay on the LAN defaults.

## 1. The one switch, and everything it moves

`TRUST_PROXY_HEADERS=true` is the exposed-deployment switch. It is not only a
rate-limiter setting:

| | LAN default (off) | Exposed (on) |
|---|---|---|
| Login rate-limit bucket | the transport peer | `X-Real-IP`, else the **rightmost** `X-Forwarded-For` hop |
| `cookie_secure` | tri-state: unset ⇒ Secure only when `ENVIRONMENT=production` | **enforced** — an explicit `COOKIE_SECURE=false` is overridden |

The leftmost `X-Forwarded-For` is read in **neither** posture. It is
client-supplied, so a limiter keyed on it would let an attacker rotate the
value per guess and never lock out.

Setting `COOKIE_SECURE=false` alongside `TRUST_PROXY_HEADERS=true` is not an
error and does not stop the app — the value is clamped to `true`, a warning is
logged at startup, and `GET /api/v1/auth/security-posture` reports
`cookie_secure_clamped: true`. If you genuinely serve plain HTTP, leave
`TRUST_PROXY_HEADERS` off; the two settings describe the same fact and must
agree.

## 2. What your proxy must do

- **Terminate TLS**, and redirect plain HTTP to it.
- **Set `X-Real-IP` to its own view of the peer**, overwriting whatever the
  client sent. If the client can supply this header through your proxy, the
  lockout is defeated and turning the switch on has made things worse than
  leaving it off.
- **Append to `X-Forwarded-For`, never replace it** — the app reads the
  rightmost hop, which must be the one your proxy added.
- **Do not route `/mcp` from the public side.** `/mcp` is unauthenticated by
  design (local-network trust model); its only network defence is the
  DNS-rebinding Host allowlist, and the bearer-required option for that door is
  designed but **not shipped** (doc 18 §5). Publishing `/mcp` publishes every
  MCP tool to anyone who can reach it. Restrict it at the proxy.

## 3. Credentials for programmatic callers

Non-human callers use an API key — `Authorization: Bearer dmk_<key_id>_<secret>`
— minted from the settings UI, with a closed scope set (`capture`, `read`,
`admin`). The plaintext is shown once at issue. `ratify` is not a scope and
never becomes one: confirming a fact stays a human cookie session on the REST
door.

**Only `admin` reaches anything today, and only one route.** The push-webhook
receiver (`POST /repos/{id}/webhook`) is the single scope-gated route in the
tree. `capture` and `read` can be granted and are refused everywhere, so a key
holding them is inert — that is a gap in the activation, not a restriction you
have configured, and it means an exposed deployment cannot yet serve a
programmatic capture or read client. Grant `admin` for the webhook; do not plan
around the other two until they gate something.

Revoke a key from the same surface. Revocation sets `revoked_at` and keeps the
row rather than deleting it, so calls the key already made keep a resolvable
name instead of pointing at an id nothing explains.

**Detecting a key you did not expect to be in use.** Every keyed delivery
journals a `repo_webhook_received` event carrying the key id and its label —
including deliveries that are refused as conflicts or that name a repository
that does not exist, which is what a probing credential mostly produces. The
settings card's last-used column is the quick signal; the events journal is the
record. A key whose last-used time moves when you are not deploying is the
signal to revoke.

Note the scope of that: the webhook is currently the **only** route a key
reaches, so key activity appears in the events journal and not on a memory's
own timeline — no keyed call can write a memory today.

## 4. Verify the posture you think you have

With an authenticated session, read the live posture rather than assuming it:

```
GET /api/v1/auth/security-posture
```

Expect, in this posture:

- `trust_proxy_headers: true`
- `cookie_secure: true` (and `cookie_secure_clamped: true` if you also set
  `COOKIE_SECURE=false`)
- `mcp_allowed_hosts` listing exactly the hosts you intend

Then confirm the limiter is really keyed on the proxied address: make
`rate_limit_max_failures` failed logins from one client, confirm the next
attempt returns `429`, and confirm a request from a different source address
still returns `401`. If the `429` never arrives, your proxy is not setting
`X-Real-IP` the way §2 requires.

## 5. What does not change

The MCP Host allowlist (a foreign Host is `421`, fixed by extending the
allowlist — never by setting `*`), trust-on-first-use setup then `403`,
single-door ratification, and the single-worker invariant. Exposure layers on
top of these; it replaces none of them.
