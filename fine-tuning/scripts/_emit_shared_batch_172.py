"""One-off emitter for shared-base batch-172 — technical domain (OAuth 2.x, OIDC, auth flows, JWT/JOSE, passkeys, SAML, Keycloak, Auth0, step-up auth).

Writes 50 rows to data/v2/shared/batch_172.tmp.jsonl with ids shared-08551..08600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_172.tmp.jsonl"
ID_OFFSET = 8550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the SPA login from implicit flow to authorization code with PKCE; the browser no longer sees access tokens in the URL fragment and the client_secret stays off the wire.", "decision", "technical", False,
     [("implicit flow", "method"), ("authorization code", "method"), ("PKCE", "method"), ("SPA", "concept")],
     [("authorization code", "implicit flow", "REPLACES"), ("PKCE", "authorization code", "EXTENDS")],
     "which OAuth flow replaced implicit for the single-page app and what did it stop leaking via the URL",
     "authorization code pkce spa implicit fragment token replace browser"),
    # --- 2 ---
    ("Keycloak 24 handles user federation against the corporate LDAP and issues OIDC ID tokens to the React front-end; the legacy SAML bridge was retired after the last tenant cut over.", "architecture", "technical", False,
     [("Keycloak", "service"), ("LDAP", "protocol"), ("OIDC", "protocol"), ("React", "framework"), ("SAML", "protocol")],
     [("Keycloak", "LDAP", "DEPENDS_ON"), ("Keycloak", "OIDC", "IMPLEMENTS"), ("OIDC", "SAML", "REPLACES")],
     "how does the identity stack federate to LDAP and which protocol swap finished the SAML bridge retirement",
     "keycloak ldap oidc react saml bridge federation tenant cutover"),
    # --- 3 ---
    ("The device code flow drives the smart-TV sign-in: the display shows a short user_code, the phone completes the consent on the authorization server, and the TV polls the token endpoint.", "architecture", "technical", False,
     [("device code flow", "method"), ("user_code", "concept"), ("authorization server", "service"), ("token endpoint", "api")],
     [("device code flow", "token endpoint", "USES")],
     "which OAuth flow did the TV app pick for cross-device consent and how does it retrieve the token",
     "device code flow smart tv user code token endpoint poll consent"),
    # --- 4 ---
    ("Refresh token rotation landed this sprint: every refresh exchange returns a fresh refresh_token and invalidates the prior one, so a leaked token burns itself on first misuse.", "milestone", "technical", False,
     [("Refresh token rotation", "method"), ("refresh_token", "concept")],
     [("Refresh token rotation", "refresh_token", "APPLIES_TO")],
     "what refresh-token hardening shipped this sprint and how does it neutralise a stolen credential",
     "refresh token rotation exchange invalidate leak replay sprint"),
    # --- 5 ---
    ("ID tokens issued by the OP carry iss, sub, aud, exp, nbf, and iat; the relying party rejects any token where aud does not match its client_id or exp is in the past.", "reference", "technical", False,
     [("ID tokens", "concept"), ("iss", "concept"), ("sub", "concept"), ("aud", "concept"), ("exp", "concept"), ("nbf", "concept"), ("iat", "concept"), ("OP", "service")],
     [("OP", "ID tokens", "PRODUCES")],
     "which standard claims sit inside an OIDC ID token and which two does the relying party always validate",
     "id token iss sub aud exp nbf iat relying party client id"),
    # --- 6 ---
    ("Auth0 is the primary IdP for the consumer tenant while ORY Hydra runs the internal service-to-service OAuth server; the split keeps B2C quotas off the internal control-plane issuer.", "architecture", "technical", False,
     [("Auth0", "service"), ("ORY Hydra", "service"), ("IdP", "concept"), ("OAuth", "protocol")],
     [("Auth0", "IdP", "IS_A"), ("ORY Hydra", "OAuth", "IMPLEMENTS")],
     "how did the team split consumer and service-to-service issuers and which vendor covers each side",
     "auth0 ory hydra idp oauth consumer service tenant split quota"),
    # --- 7 ---
    ("Chose DPoP over mTLS for sender-constrained access tokens on the public API; the front-end could not ship client certificates and DPoP proofs work from a browser with a generated keypair.", "decision", "technical", False,
     [("DPoP", "protocol"), ("mTLS", "protocol"), ("access tokens", "concept"), ("public API", "api")],
     [("DPoP", "mTLS", "PREFERS"), ("DPoP", "access tokens", "APPLIES_TO")],
     "which sender-constrained token scheme won for the public API and why was mTLS dropped",
     "dpop mtls sender constrain access token public api browser key"),
    # --- 8 ---
    ("Token exchange per RFC 8693 bridges the gateway's inbound JWT to a downstream actor token; the downstream service sees the original subject in sub while act carries the gateway identity.", "architecture", "technical", False,
     [("RFC 8693", "publication"), ("Token exchange", "method"), ("JWT", "concept"), ("sub", "concept"), ("act", "concept")],
     [("Token exchange", "RFC 8693", "IMPLEMENTS")],
     "how does the gateway preserve the original subject while attaching its own identity on downstream calls",
     "rfc 8693 token exchange jwt act sub gateway downstream subject"),
    # --- 9 ---
    ("Okta powers workforce SSO and OIDC drives the admin console; SAML 2.0 still handles two vendor apps that will not budge from the old assertion bridge before their 2027 renewal.", "fact", "technical", False,
     [("Okta", "service"), ("OIDC", "protocol"), ("SAML 2.0", "protocol"), ("admin console", "project")],
     [("Okta", "OIDC", "SUPPORTS"), ("Okta", "SAML 2.0", "SUPPORTS")],
     "which SSO vendor handles workforce sign-on and which protocol still covers legacy vendor apps",
     "okta workforce sso oidc saml 2 0 admin console vendor renewal"),
    # --- 10. noise ---
    ("The office coffee grinder jammed on a rogue espresso bean this morning and the queue for the spare kettle stretched past the copier.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("WebAuthn passkeys replaced the TOTP second factor for the admin console; FIDO2 authenticators bound to the RP ID mean phishing sites cannot harvest a challenge that applies anywhere else.", "milestone", "technical", False,
     [("WebAuthn", "protocol"), ("passkeys", "concept"), ("TOTP", "method"), ("FIDO2", "protocol"), ("RP ID", "concept")],
     [("passkeys", "TOTP", "REPLACES"), ("WebAuthn", "FIDO2", "IMPLEMENTS")],
     "which second-factor swap shipped for admins and which binding makes the credentials phishing-resistant",
     "webauthn passkey totp fido2 rp id admin phishing bind challenge"),
    # --- 12 ---
    ("JWS signatures on service-to-service JWTs use ES256 against a rotating key set published on the JWKS endpoint; HS256 is banned because any verifier holding the secret could also mint tokens.", "decision", "technical", False,
     [("JWS", "protocol"), ("JWT", "concept"), ("ES256", "algorithm"), ("HS256", "algorithm"), ("JWKS", "api")],
     [("ES256", "HS256", "PREFERS"), ("JWS", "JWKS", "DEPENDS_ON")],
     "which signing algorithm won for service JWTs and which symmetric option got banned outright",
     "jws jwt es256 hs256 jwks rotating key service sign verifier mint"),
    # --- 13 ---
    ("Dynamic client registration is gated behind an initial_access_token minted by the platform console; unauthenticated POSTs to the register endpoint return 401 rather than a generated client record.", "architecture", "technical", False,
     [("Dynamic client registration", "method"), ("initial_access_token", "concept"), ("register endpoint", "api")],
     [("Dynamic client registration", "initial_access_token", "DEPENDS_ON")],
     "how is dynamic client registration gated so random POSTs can't enrol as a client on their own",
     "dynamic client registration initial access token register endpoint"),
    # --- 14 ---
    ("Token introspection at the resource server is backed by a 30-second local cache keyed on the jti; the previous no-cache setup hammered the authorization server once per request and tripped rate limits.", "problem", "technical", False,
     [("Token introspection", "method"), ("resource server", "service"), ("jti", "concept"), ("authorization server", "service")],
     [("Token introspection", "authorization server", "COMMUNICATES_WITH")],
     "what caching layer fixed the introspection-induced rate-limit storm at the resource server",
     "token introspection cache jti resource server rate limit authorization"),
    # --- 15 ---
    ("Supabase Auth sits in front of the Postgres row-level security rules; the JWT's sub becomes auth.uid() inside the database and policy predicates use it to scope rows to the signed-in user.", "architecture", "technical", False,
     [("Supabase Auth", "service"), ("Postgres", "database"), ("JWT", "concept"), ("row-level security", "pattern"), ("sub", "concept")],
     [("Supabase Auth", "Postgres", "COMMUNICATES_WITH"), ("JWT", "row-level security", "APPLIES_TO")],
     "how does Supabase Auth thread the signed-in user identity into Postgres row filters",
     "supabase auth postgres row level security jwt sub auth uid policy"),
    # --- 16 ---
    ("Clerk handles the sign-up and MFA enrolment surface for the new SaaS tenant; we picked it over Stytch because the drop-in React components shaved two weeks off the UI build.", "decision", "technical", False,
     [("Clerk", "service"), ("Stytch", "service"), ("MFA", "method"), ("React", "framework"), ("SaaS", "concept")],
     [("Clerk", "Stytch", "PREFERS")],
     "which identity vendor won for the SaaS sign-up surface and which competitor was the runner-up",
     "clerk stytch mfa react saas signup drop in component ui build"),
    # --- 17 ---
    ("OIDC discovery document lives at /.well-known/openid-configuration and pins the issuer, authorization_endpoint, token_endpoint, jwks_uri, and userinfo_endpoint that relying parties consume at boot.", "reference", "technical", False,
     [("OIDC discovery", "method"), ("/.well-known/openid-configuration", "api"), ("issuer", "concept"), ("authorization_endpoint", "api"), ("token_endpoint", "api"), ("jwks_uri", "api"), ("userinfo_endpoint", "api")],
     [("OIDC discovery", "jwks_uri", "HAS_PART")],
     "which well-known URL do relying parties fetch at boot and which endpoints does it advertise",
     "oidc discovery well known openid configuration issuer endpoint jwks"),
    # --- 18 ---
    ("Step-up auth on the wire-transfer endpoint requires an acr of urn:mace:incommon:iap:silver; a cookie-session user gets redirected through a fresh WebAuthn prompt before the POST succeeds.", "architecture", "technical", False,
     [("Step-up auth", "method"), ("acr", "concept"), ("WebAuthn", "protocol"), ("wire-transfer endpoint", "api")],
     [("Step-up auth", "WebAuthn", "USES")],
     "how does the wire-transfer endpoint force a fresh strong-auth before accepting a sensitive POST",
     "step up auth acr webauthn wire transfer endpoint cookie prompt"),
    # --- 19 ---
    ("The userinfo endpoint returns a slim payload with sub, email, and email_verified; extra attributes live behind a profile scope that the RP only requests for the account-settings page.", "architecture", "technical", False,
     [("userinfo endpoint", "api"), ("sub", "concept"), ("email", "concept"), ("email_verified", "concept"), ("profile scope", "concept")],
     [("userinfo endpoint", "profile scope", "DEPENDS_ON")],
     "which attributes ship in the default userinfo payload and how does the RP unlock the extended set",
     "userinfo endpoint sub email verified profile scope rp settings"),
    # --- 20 ---
    ("JWE-encrypted assertions wrap the inner JWT for the partner exchange; the outer A256GCM envelope hides scope and sub from intermediaries while the inner JWS stays verifiable by the partner.", "architecture", "technical", False,
     [("JWE", "protocol"), ("JWT", "concept"), ("A256GCM", "algorithm"), ("JWS", "protocol"), ("scope", "concept")],
     [("JWE", "JWS", "HAS_PART"), ("JWE", "A256GCM", "USES")],
     "which JOSE envelope hides claim content from intermediaries while keeping partner signatures verifiable",
     "jwe jwt a256gcm jws scope partner envelope hide intermediary claim"),
    # --- 21 ---
    ("FusionAuth runs on the isolated ops cluster as the IdP for the admin portal; the main customer-facing Auth0 tenant never sees operator credentials or emergency break-glass accounts.", "decision", "technical", False,
     [("FusionAuth", "service"), ("Auth0", "service"), ("IdP", "concept"), ("admin portal", "project")],
     [("FusionAuth", "IdP", "IS_A"), ("FusionAuth", "Auth0", "REPLACES")],
     "why does the ops cluster run its own IdP instead of riding the customer Auth0 tenant for admins",
     "fusionauth auth0 idp admin portal ops isolate break glass operator"),
    # --- 22 ---
    ("Revocation for refresh tokens writes to a Redis denylist keyed on the token's jti with a TTL matching the original exp; the access-token path stays stateless and only introspects on sensitive calls.", "architecture", "technical", False,
     [("Revocation", "method"), ("refresh tokens", "concept"), ("Redis", "database"), ("jti", "concept"), ("exp", "concept")],
     [("Revocation", "Redis", "USES")],
     "how is refresh-token revocation implemented without dragging every access-token check into a database round-trip",
     "revocation refresh token redis denylist jti exp ttl access stateless"),
    # --- 23 ---
    ("Client credentials flow drives the backend cron jobs talking to the billing API; each job has its own client_id and scope so an over-scoped leak gets spotted in the audit log quickly.", "architecture", "technical", False,
     [("Client credentials flow", "method"), ("backend cron", "service"), ("billing API", "api"), ("client_id", "concept"), ("scope", "concept")],
     [("Client credentials flow", "billing API", "USES")],
     "which OAuth flow backs the backend cron jobs and how is scope leakage surfaced in audit",
     "client credentials flow cron billing api client id scope audit"),
    # --- 24 ---
    ("PAR pushes the authorization request ahead of the redirect so sensitive parameters never traverse the browser; the resulting request_uri is opaque and expires after sixty seconds in our config.", "architecture", "technical", False,
     [("PAR", "method"), ("authorization request", "method"), ("request_uri", "concept"), ("browser", "concept")],
     [("PAR", "authorization request", "IMPROVES_ON")],
     "how does PAR keep sensitive authorization-request parameters out of the browser redirect chain",
     "par pushed authorization request redirect request uri browser sixty"),
    # --- 25 ---
    ("ORY Kratos owns the self-service registration and recovery flows while ORY Hydra owns the OAuth issuer side; the two share a Postgres and coordinate via the session cookie on the login UI.", "architecture", "technical", False,
     [("ORY Kratos", "service"), ("ORY Hydra", "service"), ("OAuth", "protocol"), ("Postgres", "database"), ("session cookie", "concept")],
     [("ORY Kratos", "Postgres", "DEPENDS_ON"), ("ORY Hydra", "OAuth", "IMPLEMENTS"), ("ORY Kratos", "ORY Hydra", "COMMUNICATES_WITH")],
     "how do Kratos and Hydra split the identity and issuer roles and what do they share at runtime",
     "ory kratos hydra oauth postgres session cookie login self service"),
    # --- 26 ---
    ("Prefer ES256 over RS256 for new JWT signing keys; the shorter signatures shave kilobytes off bearer headers and our HSM vendor benched ES256 faster for the same per-second budget.", "preference", "technical", False,
     [("ES256", "algorithm"), ("RS256", "algorithm"), ("JWT", "concept"), ("HSM", "infrastructure")],
     [("ES256", "RS256", "PREFERS")],
     "which signing algorithm should new JWT keys default to and what two wins drove the preference",
     "es256 rs256 jwt hsm bearer header signature size throughput"),
    # --- 27 ---
    ("Chose WebAuthn-only passkeys for passwordless sign-in rather than magic links; magic links keep email carriers in the critical path and the deliverability incidents were costing us a daily bug report.", "decision", "technical", False,
     [("WebAuthn", "protocol"), ("passkeys", "concept"), ("magic links", "method"), ("email", "concept")],
     [("passkeys", "magic links", "PREFERS")],
     "which passwordless approach won over magic links and what operational headache did we retire",
     "webauthn passkey magic link passwordless email deliverability bug"),
    # --- 28 ---
    ("Session fixation on the login flow got closed by rotating the session id on every privilege change; the pre-login cookie never survives into the authenticated context after the recent patch.", "problem", "technical", False,
     [("Session fixation", "concept"), ("session id", "concept"), ("login flow", "method"), ("cookie", "concept")],
     [("session id", "Session fixation", "FIXES")],
     "how did we close the session-fixation hole on login and which cookie gets invalidated on privilege change",
     "session fixation id rotate login privilege cookie invalidate patch"),
    # --- 29 ---
    ("mTLS client authentication binds the API client to a certificate issued by the internal CA; the token endpoint pulls the tls_client_auth_subject_dn off the TLS layer and stamps it into the access_token.", "architecture", "technical", False,
     [("mTLS", "protocol"), ("internal CA", "service"), ("token endpoint", "api"), ("tls_client_auth_subject_dn", "concept"), ("access_token", "concept")],
     [("mTLS", "token endpoint", "APPLIES_TO")],
     "how does mTLS client auth bind an API client and which claim lands on the minted access token",
     "mtls client auth internal ca token endpoint subject dn access"),
    # --- 30 ---
    ("The authorization code flow now uses a short sixty-second code lifetime plus single-use enforcement; the prior ten-minute window accepted replayed codes during an incident and widened the blast radius.", "problem", "technical", False,
     [("authorization code flow", "method"), ("code lifetime", "config"), ("single-use enforcement", "method")],
     [("single-use enforcement", "authorization code flow", "APPLIES_TO")],
     "which two hardening moves on the authorization-code lifetime came out of the replay incident",
     "authorization code flow sixty second single use replay incident"),
    # --- 31 ---
    ("Prefer Keycloak's built-in user storage SPI over writing a custom authenticator when the backing system speaks LDAP or JDBC; the SPI handles paging, caching, and password hashing for free.", "preference", "technical", False,
     [("Keycloak", "service"), ("user storage SPI", "api"), ("custom authenticator", "concept"), ("LDAP", "protocol"), ("JDBC", "api")],
     [("user storage SPI", "custom authenticator", "PREFERS")],
     "when extending Keycloak to a new backing store which extension point beats hand-rolling an authenticator",
     "keycloak user storage spi custom authenticator ldap jdbc cache hash"),
    # --- 32 ---
    ("SAML 2.0 SSO against the state-government tenant uses HTTP-POST binding with signed assertions; the ACS URL validates the InResponseTo id to block unsolicited assertions that showed up in the log.", "fact", "technical", False,
     [("SAML 2.0", "protocol"), ("HTTP-POST binding", "method"), ("ACS URL", "api"), ("InResponseTo", "concept")],
     [("SAML 2.0", "HTTP-POST binding", "USES")],
     "which SAML binding serves the state tenant and which id check blocks unsolicited assertions",
     "saml 2 0 http post binding acs in response to unsolicited state"),
    # --- 33 ---
    ("Auth0 Action for post-login adds a groups claim by fetching the user's role list from the profile metadata; the claim lands inside the ID token and downstream RBAC reads it directly.", "architecture", "technical", False,
     [("Auth0 Action", "service"), ("groups claim", "concept"), ("ID token", "concept"), ("RBAC", "concept")],
     [("Auth0 Action", "ID token", "PRODUCES"), ("RBAC", "groups claim", "USES")],
     "how does Auth0 get role membership into the ID token and which layer downstream consumes it",
     "auth0 action post login groups claim id token rbac role profile"),
    # --- 34 ---
    ("Shipped adaptive MFA: risk signal from the device fingerprint plus impossible-travel check triggers step-up to a WebAuthn prompt, otherwise the user rides the silent session renew path.", "milestone", "technical", False,
     [("adaptive MFA", "method"), ("device fingerprint", "concept"), ("impossible-travel", "concept"), ("WebAuthn", "protocol"), ("session renew", "method")],
     [("adaptive MFA", "WebAuthn", "USES")],
     "which two risk signals drive the adaptive MFA prompt and what is the quiet path for trusted sessions",
     "adaptive mfa device fingerprint impossible travel webauthn renew step"),
    # --- 35 ---
    ("OIDC back-channel logout posts a logout_token to each relying party's back_channel_logout_uri; the RP invalidates its local session by sid without needing a front-channel iframe ping.", "reference", "technical", False,
     [("OIDC back-channel logout", "method"), ("logout_token", "concept"), ("back_channel_logout_uri", "api"), ("sid", "concept")],
     [("OIDC back-channel logout", "logout_token", "USES")],
     "how does OIDC back-channel logout tear down RP sessions without relying on front-channel iframes",
     "oidc back channel logout token uri sid iframe invalidate session"),
    # --- 36 ---
    ("Cognito got dropped in favour of Keycloak for the new region; per-tenant realms and the Admin REST API gave us CI-backed onboarding that Cognito user pools could not script as cleanly.", "decision", "technical", False,
     [("Cognito", "service"), ("Keycloak", "service"), ("Admin REST API", "api"), ("realms", "concept")],
     [("Keycloak", "Cognito", "REPLACES"), ("Keycloak", "realms", "HAS_PART")],
     "why did the new region pick Keycloak over Cognito and what capability sealed it",
     "cognito keycloak admin rest api realm tenant onboarding ci region"),
    # --- 37 ---
    ("The audit log ingests token_issued, token_refreshed, token_revoked, and mfa_challenged events into ClickHouse; the security team runs a Grafana dashboard with per-tenant anomaly bands on each counter.", "architecture", "technical", False,
     [("audit log", "concept"), ("token_issued", "event"), ("token_refreshed", "event"), ("token_revoked", "event"), ("mfa_challenged", "event"), ("ClickHouse", "database"), ("Grafana", "tool")],
     [("audit log", "ClickHouse", "USES"), ("Grafana", "ClickHouse", "DEPENDS_ON")],
     "which auth events land in the audit pipeline and which dashboard stack surfaces anomalies",
     "audit log token issued refreshed revoked mfa clickhouse grafana"),
    # --- 38 ---
    ("Bound the refresh_token to the device using a DPoP key thumbprint in the cnf claim; a stolen token lifted without the private key fails the proof-of-possession check at the token endpoint.", "architecture", "technical", False,
     [("refresh_token", "concept"), ("DPoP", "protocol"), ("cnf claim", "concept"), ("token endpoint", "api"), ("proof-of-possession", "concept")],
     [("DPoP", "refresh_token", "APPLIES_TO")],
     "how is the refresh_token bound to the client device so that a lifted token without the key fails",
     "refresh token dpop cnf thumbprint proof possession endpoint device"),
    # --- 39 ---
    ("PKCE with S256 is mandatory for every public client in the new config; plain was disabled after a code-interception PoC surfaced on the mobile deep-link during pen-test week.", "decision", "technical", False,
     [("PKCE", "method"), ("S256", "algorithm"), ("plain", "algorithm"), ("public client", "concept"), ("mobile deep-link", "concept")],
     [("S256", "plain", "PREFERS"), ("PKCE", "public client", "APPLIES_TO")],
     "which PKCE transform became mandatory and what incident pushed plain off the allow-list",
     "pkce s256 plain public client mobile deep link pen test intercept"),
    # --- 40 ---
    ("Migration milestone: every internal service now validates JWTs locally against the cached JWKS and only introspects for high-value scopes; latency on the auth check dropped by around 35 ms on average.", "milestone", "technical", False,
     [("JWT", "concept"), ("JWKS", "api"), ("scopes", "concept")],
     [("JWT", "JWKS", "USES")],
     "which validation topology change shaved latency off every auth check for internal services",
     "jwt jwks introspection scope internal service latency cache migrate"),
    # --- 41 ---
    ("Token exchange now downgrades a broad user JWT to a narrow act-as token for the reporting microservice; the downstream sees only the metrics scope even though the caller had admin privileges.", "architecture", "technical", False,
     [("Token exchange", "method"), ("act-as token", "concept"), ("reporting microservice", "service"), ("metrics scope", "concept")],
     [("Token exchange", "act-as token", "PRODUCES")],
     "how does token exchange narrow an admin caller down to a metrics-only identity for reporting",
     "token exchange act as reporting microservice metrics scope narrow"),
    # --- 42 ---
    ("Stytch handles the magic-link fallback for users who refuse to enrol a passkey; Clerk stays primary and hands off to Stytch only when the user hits the no-passkey escape hatch in the UI.", "architecture", "technical", False,
     [("Stytch", "service"), ("Clerk", "service"), ("magic-link", "method"), ("passkey", "concept")],
     [("Clerk", "Stytch", "COMMUNICATES_WITH"), ("Stytch", "magic-link", "IMPLEMENTS")],
     "how is the magic-link fallback wired up and which vendor takes over when a user refuses passkeys",
     "stytch clerk magic link passkey fallback primary escape hatch"),
    # --- 43. noise ---
    ("The building's mail-room cat curled up on the accessibility-keyboard shipment again and refused to be moved until the afternoon deliveries finished.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The mobile app stores refresh_tokens in the Keychain with access group scoping; the Android peer uses EncryptedSharedPreferences backed by the hardware-backed keystore on Pixel and Samsung devices.", "architecture", "technical", False,
     [("refresh_tokens", "concept"), ("Keychain", "platform"), ("EncryptedSharedPreferences", "api"), ("Android", "platform"), ("Pixel", "platform")],
     [("refresh_tokens", "Keychain", "LOCATED_IN"), ("EncryptedSharedPreferences", "Android", "DEPLOYED_ON")],
     "where does each mobile platform stash refresh_tokens so that lifting them off disk is not trivial",
     "refresh token keychain encrypted shared preferences android pixel keystore"),
    # --- 45 ---
    ("JOSE header typ is pinned to at+jwt for access tokens and logout+jwt for logout_tokens; verifiers reject unknown typ values so a confused-deputy swap between the two token kinds fails cleanly.", "reference", "technical", False,
     [("JOSE", "protocol"), ("at+jwt", "concept"), ("logout+jwt", "concept"), ("logout_tokens", "concept"), ("access tokens", "concept")],
     [("JOSE", "at+jwt", "HAS_PART"), ("JOSE", "logout+jwt", "HAS_PART")],
     "which JOSE header values distinguish access tokens from logout tokens and block deputy swaps",
     "jose typ at jwt logout access verifier confused deputy swap"),
    # --- 46 ---
    ("Keycloak realm export is pinned in git and Terraform applies it on every deploy; the earlier click-ops process drifted between environments and a staging-only policy leaked into production once.", "problem", "technical", False,
     [("Keycloak", "service"), ("realm export", "concept"), ("Terraform", "tool"), ("staging", "concept"), ("production", "concept")],
     [("Terraform", "realm export", "CONFIGURES")],
     "how did the team kill the click-ops drift on Keycloak realms and what process replaced it",
     "keycloak realm export terraform git click ops drift staging production"),
    # --- 47 ---
    ("Prefer opaque access tokens at the edge and swap to JWT only inside the service mesh; opaque tokens never leak claim content to a misbehaving client script and the mesh still gets low-latency local validation.", "preference", "technical", False,
     [("opaque access tokens", "concept"), ("JWT", "concept"), ("service mesh", "infrastructure"), ("edge", "concept")],
     [("opaque access tokens", "JWT", "PREFERS"), ("JWT", "service mesh", "APPLIES_TO")],
     "why pick opaque tokens at the edge and JWT inside the mesh and what risk does each choice contain",
     "opaque access token jwt service mesh edge claim leak latency"),
    # --- 48 ---
    ("RFC 7662 introspection payload carries active, scope, client_id, username, token_type, exp, and iat; unauthenticated introspection requests are rejected with a 401 at the ingress layer.", "reference", "technical", False,
     [("RFC 7662", "publication"), ("active", "concept"), ("scope", "concept"), ("client_id", "concept"), ("username", "concept"), ("token_type", "concept"), ("exp", "concept"), ("iat", "concept")],
     [("RFC 7662", "active", "HAS_PART")],
     "which introspection response fields come out of the standard and what happens to an unauthenticated call",
     "rfc 7662 introspection active scope client id token type exp iat"),
    # --- 49 ---
    ("Keycloak clustered on three nodes with Infinispan replication behind HAProxy serves the peak sign-in storm at 8 AM; the earlier single-node setup queued at the login endpoint during the Monday rush.", "milestone", "technical", False,
     [("Keycloak", "service"), ("Infinispan", "library"), ("HAProxy", "service"), ("login endpoint", "api")],
     [("Keycloak", "Infinispan", "DEPENDS_ON"), ("HAProxy", "Keycloak", "COMMUNICATES_WITH")],
     "which clustering change let Keycloak absorb the Monday sign-in storm without queueing at the endpoint",
     "keycloak infinispan haproxy cluster login endpoint peak sign in monday"),
    # --- 50 ---
    ("User opted to keep TOTP as a backup factor alongside the primary passkey; the admin UI exposes a single toggle per user and the audit trail logs every factor addition with who approved it.", "preference", "technical", False,
     [("TOTP", "method"), ("passkey", "concept"), ("admin UI", "project"), ("audit trail", "concept")],
     [("TOTP", "passkey", "RELATED_TO")],
     "which backup factor does the user keep alongside a passkey and how is every factor change audited",
     "totp passkey backup factor admin ui audit trail approve toggle"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
