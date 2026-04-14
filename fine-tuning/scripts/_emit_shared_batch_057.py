"""One-off emitter for shared-base batch-057 — ai_coding domain (security-focused coding / secure-by-default patterns / OWASP-aligned practices in application code).

Writes 50 rows to data/v2/shared/batch_057.tmp.jsonl with ids shared-02801..02850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_057.tmp.jsonl"
ID_OFFSET = 2800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced every f-string SQL concat in the reporting service with psycopg bound parameters; the static scan now fails CI on string-built queries.", "decision", "ai_coding", False,
     [("f-string", "pattern"), ("psycopg", "library"), ("bound parameters", "pattern")],
     [("bound parameters", "f-string", "REPLACES")],
     "how did the reporting service kill SQL injection risk in its query builders",
     "parameterise query psycopg bind prevent injection static scan gate"),
    # --- 2 ---
    ("Output encoding moved from a global html.escape to context-aware encoders per sink; URL, HTML attribute, and script contexts each pick a different escaper.", "architecture", "ai_coding", False,
     [("html.escape", "method"), ("HTML attribute", "pattern"), ("script", "pattern")],
     [],
     "which XSS defence did we switch to after discovering global escape was unsafe in attribute contexts",
     "context aware output encoding sink HTML attribute URL script escape"),
    # --- 3 ---
    ("Content-Security-Policy now ships nonces generated per response instead of SHA hashes; inline scripts stay auditable but the deploy pipeline stopped gating on hash rebuilds.", "decision", "ai_coding", False,
     [("Content-Security-Policy", "config"), ("nonces", "pattern"), ("SHA hashes", "pattern")],
     [("nonces", "SHA hashes", "PREFERS")],
     "which CSP inline-script strategy replaced the hash pipeline and what did it unblock",
     "csp nonce versus hash inline script rotate per response build gate"),
    # --- 4 ---
    ("Added X-Content-Type-Options: nosniff to every response after a legacy JSON endpoint got sniffed as HTML and executed a stray <script> in an old IE emulation mode.", "problem", "ai_coding", False,
     [("X-Content-Type-Options", "config"), ("nosniff", "config")],
     [],
     "which header did we add after a MIME-sniff bug turned a JSON response into executable HTML",
     "nosniff mime sniff header JSON XSS legacy browser fix"),
    # --- 5 ---
    ("Rolled out Trusted Types policies on the admin SPA; every DOM sink now goes through a named policy and raw string assignment to innerHTML throws in production.", "milestone", "ai_coding", False,
     [("Trusted Types", "pattern"), ("innerHTML", "pattern"), ("admin SPA", "project")],
     [],
     "which browser primitive now guards DOM sinks on the admin SPA against string HTML injection",
     "trusted types policy DOM sink innerHTML enforce production throw"),
    # --- 6 ---
    ("Subresource Integrity hashes are mandatory on every third-party CDN script; the build pipeline fails if a vendor script lands without an integrity attribute.", "preference", "ai_coding", False,
     [("Subresource Integrity", "pattern"), ("CDN", "infrastructure"), ("integrity", "config")],
     [],
     "which policy stops a compromised CDN from silently shipping tampered JavaScript to users",
     "subresource integrity hash third party script CDN pipeline gate"),
    # --- 7 ---
    ("Swapped a raw loader for an explicit allowlisted deserialiser using dill's dispatch table; the ingestion worker no longer accepts arbitrary class instances from disk.", "architecture", "ai_coding", False,
     [("dill", "library"), ("ingestion worker", "service"), ("deserialiser", "pattern")],
     [("deserialiser", "dill", "USES")],
     "how did the ingestion worker stop trusting arbitrary serialised classes on disk",
     "unsafe deserialization allowlist loader dispatch table worker"),
    # --- 8 ---
    ("Every YAML load in the config service went from yaml.load to yaml.safe_load after a red-team payload smuggled a rogue constructor through a feature flag file.", "problem", "ai_coding", False,
     [("yaml.load", "method"), ("yaml.safe_load", "method"), ("config service", "service")],
     [("yaml.safe_load", "yaml.load", "REPLACES")],
     "which YAML loader swap did the config service make after a red-team deserialization exploit",
     "yaml safe load unsafe constructor python object config red team"),
    # --- 9 ---
    ("Path traversal guard on the downloads route now joins the base dir and calls pathlib resolve, then checks the resolved path is a descendant; os.path.normpath alone let .. slip through on Windows.", "fact", "ai_coding", False,
     [("pathlib", "library"), ("os.path.normpath", "method"), ("downloads", "api")],
     [("pathlib", "os.path.normpath", "IMPROVES_ON")],
     "how does the downloads route now reject path-traversal attempts across Windows and Linux",
     "path traversal resolve descendant check normpath windows bypass"),
    # --- 10. noise ---
    ("The office plant in the window crawled two more inches toward the monitor this week, somehow.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("SSRF guard on the URL fetcher allowlists https and http only, resolves the host, and rejects any IP in private, loopback, or link-local ranges before connecting.", "architecture", "ai_coding", False,
     [("SSRF", "pattern"), ("URL fetcher", "service"), ("allowlist", "pattern")],
     [],
     "how does the outbound URL fetcher block SSRF attempts to internal metadata services",
     "ssrf guard allowlist scheme private ip loopback metadata resolve"),
    # --- 12 ---
    ("Prototype pollution on the admin dashboard got shut by switching deep-merge helpers to Object.create(null) records; lodash merge's __proto__ flow is banned in the linter.", "problem", "ai_coding", False,
     [("Object.create", "method"), ("lodash", "library"), ("__proto__", "pattern"), ("admin dashboard", "project")],
     [("Object.create", "lodash", "REPLACES")],
     "which JavaScript change closed the prototype-pollution hole on the admin dashboard",
     "prototype pollution deep merge null proto lodash lint rule ban"),
    # --- 13 ---
    ("Mass-assignment on the user profile endpoint is now filtered through a Pydantic model with extra='forbid'; arbitrary role bumps via stray JSON fields are rejected with a 422.", "architecture", "ai_coding", False,
     [("Pydantic", "library"), ("user profile", "api"), ("extra='forbid'", "config")],
     [],
     "how does the user-profile endpoint stop mass-assignment attacks that try to escalate role fields",
     "mass assignment strong parameter pydantic forbid extra role escalate"),
    # --- 14 ---
    ("CSRF moved from double-submit tokens to SameSite=Lax cookies plus an Origin check; the upgrade landed on 2026-03-22 with a two-week shadow window proving parity.", "milestone", "ai_coding", False,
     [("SameSite=Lax", "config"), ("Origin", "config"), ("CSRF", "pattern"), ("2026-03-22", "date")],
     [("SameSite=Lax", "CSRF", "REPLACES")],
     "which CSRF defence replaced double-submit tokens and when did the switch land",
     "csrf samesite lax origin header replace double submit rollout"),
    # --- 15 ---
    ("The login endpoints now emit Retry-After and RateLimit headers on every failure; automated credential-stuffing sweeps visibly back off once they parse the 429.", "fact", "ai_coding", False,
     [("Retry-After", "config"), ("RateLimit", "config"), ("login", "api")],
     [],
     "which response headers did the login endpoint add to slow down credential-stuffing attacks",
     "rate limit retry after header login credential stuffing back off"),
    # --- 16 ---
    ("Secret comparisons use hmac.compare_digest everywhere; the old == check on the webhook signature path briefly leaked a character-at-a-time timing signal in benchmarks.", "architecture", "ai_coding", False,
     [("hmac.compare_digest", "method"), ("webhook", "pattern")],
     [("hmac.compare_digest", "webhook", "APPLIES_TO")],
     "which Python primitive replaced naive equality on secret comparisons to close a timing side channel",
     "constant time compare digest hmac secret timing leak webhook sig"),
    # --- 17 ---
    ("Password hashing standardised on Argon2id with m=19456 t=2 p=1; the parameters come from OWASP's 2026 cheat sheet and get re-benchmarked each quarter.", "decision", "ai_coding", False,
     [("Argon2id", "algorithm"), ("OWASP", "organization")],
     [("Argon2id", "OWASP", "RELATED_TO")],
     "which password-hashing parameters did we pick and where do the numbers come from",
     "argon2id parameter memory iteration OWASP cheat sheet benchmark"),
    # --- 18 ---
    ("Bumped the bcrypt cost factor from 10 to 12 on the auth service; the migration re-hashes passwords lazily on successful login rather than forcing a mass reset.", "milestone", "ai_coding", False,
     [("bcrypt", "algorithm"), ("auth service", "service")],
     [],
     "how did we raise the bcrypt work factor without triggering a fleet-wide password reset",
     "bcrypt cost factor raise lazy rehash login migration plan"),
    # --- 19 ---
    ("2FA shipped as TOTP plus ten single-use recovery codes downloaded once at enrolment; the recovery list is Argon2-hashed server side and never stored in plaintext.", "architecture", "ai_coding", False,
     [("TOTP", "protocol"), ("Argon2", "algorithm"), ("2FA", "pattern")],
     [],
     "which 2FA design did the auth service ship and how are recovery codes stored",
     "two factor TOTP recovery code argon2 hash enrol download once"),
    # --- 20 ---
    ("Added WebAuthn as the preferred second factor; TOTP is still supported but new accounts see a platform authenticator prompt first in the enrolment flow.", "decision", "ai_coding", False,
     [("WebAuthn", "protocol"), ("TOTP", "protocol")],
     [("WebAuthn", "TOTP", "PREFERS")],
     "which second-factor flavour did we promote to default and which one is the fallback",
     "webauthn platform authenticator prefer totp fallback enrolment"),
    # --- 21 ---
    ("The login page's errors collapsed to a single uniform message and status; the old distinction between unknown-user and wrong-password was a textbook account enumeration channel.", "problem", "ai_coding", False,
     [("login", "api"), ("account enumeration", "pattern")],
     [],
     "which login-response change closed the account-enumeration oracle the old error messages created",
     "account enumeration uniform login error message response time"),
    # --- 22 ---
    ("Every application-level control in the threat model cites its OWASP Top 10 2021 ID; the ticket template carries an A01..A10 field so auditors can grep the change log.", "reference", "ai_coding", False,
     [("OWASP Top 10 2021", "publication"), ("threat model", "concept")],
     [],
     "which threat-model taxonomy do tickets cite and why pin a specific year",
     "owasp top ten 2021 cite ticket template audit trace"),
    # --- 23 ---
    ("Password-reset flow cites NIST 800-63B memorized-secret rules: minimum 12 chars, no composition rules, and breach-list check against HaveIBeenPwned's k-anonymous range API.", "architecture", "ai_coding", False,
     [("NIST 800-63B", "publication"), ("HaveIBeenPwned", "service")],
     [("HaveIBeenPwned", "NIST 800-63B", "IMPLEMENTS")],
     "which password policy reference drives the reset flow and how do we check against breaches",
     "nist 800 63b memorized secret length breach list haveibeenpwned"),
    # --- 24 ---
    ("Added trufflehog and gitleaks to the pre-commit hook and CI; the pre-commit mode is fast while CI runs the full history scan on push to main.", "preference", "ai_coding", False,
     [("trufflehog", "tool"), ("gitleaks", "tool"), ("pre-commit", "tool")],
     [],
     "which secret-scanning tools guard commits and how is the fast-versus-deep split organised",
     "secret scan trufflehog gitleaks pre commit ci history stage"),
    # --- 25 ---
    ("Replaced npm audit with OSV-Scanner in the Node pipelines; the GitHub Advisory Database coverage and JSON output made the SARIF upload to code scanning trivial.", "decision", "ai_coding", False,
     [("npm audit", "tool"), ("OSV-Scanner", "tool"), ("SARIF", "protocol")],
     [("OSV-Scanner", "npm audit", "REPLACES")],
     "which dependency-scanner swap landed in the Node pipelines and what made the new one stick",
     "osv scanner replace npm audit sarif code scanning node pipeline"),
    # --- 26 ---
    ("SBOM generation runs Syft on every release artefact; the CycloneDX JSON gets attached to the GitHub release and signed alongside the binary.", "architecture", "ai_coding", False,
     [("Syft", "tool"), ("CycloneDX", "protocol"), ("SBOM", "concept")],
     [("Syft", "SBOM", "PRODUCES")],
     "how does the release pipeline produce an SBOM and where does it get published",
     "sbom syft cyclonedx release artefact attach sign supply chain"),
    # --- 27 ---
    ("Wrote CodeQL queries for the in-house taint sources; the GraphQL resolver arguments are now tracked end to end into every sink we care about.", "milestone", "ai_coding", False,
     [("CodeQL", "tool"), ("GraphQL", "technology")],
     [],
     "which static-analysis tool now tracks GraphQL-argument taint into sinks and who wrote the queries",
     "codeql taint source graphql resolver sink custom query in house"),
    # --- 28 ---
    ("Semgrep rules bank pulls from r2c-OWASP plus a local rules folder; the local rules enforce our no-raw-sql and must-use-compare_digest policies on top of the stock pack.", "architecture", "ai_coding", False,
     [("Semgrep", "tool"), ("r2c-OWASP", "project"), ("compare_digest", "method")],
     [("Semgrep", "r2c-OWASP", "USES")],
     "how is the Semgrep rule pack organised between community and local project rules",
     "semgrep rule owasp local custom no raw sql compare digest bank"),
    # --- 29 ---
    ("Fuzz harnesses live under tests/fuzz and are authored with Atheris for Python and cargo-fuzz for Rust; CI runs them in short smoke mode on PRs and long mode nightly.", "preference", "ai_coding", False,
     [("Atheris", "tool"), ("cargo-fuzz", "tool"), ("tests/fuzz", "file")],
     [],
     "which fuzzing tools did we standardise on per language and how are harnesses run in CI",
     "fuzz harness atheris cargo fuzz python rust smoke nightly run"),
    # --- 30 ---
    ("File uploads validate by reading the magic bytes with python-magic instead of trusting the Content-Type header; a JPEG with a .jpg extension but PDF magic now gets rejected.", "architecture", "ai_coding", False,
     [("python-magic", "library"), ("Content-Type", "config"), ("JPEG", "pattern")],
     [],
     "how does the upload endpoint decide what kind of file it really received",
     "upload file magic byte sniff python magic content type header"),
    # --- 31 ---
    ("The boto3 session in the job runner assumes a least-privilege role per tenant; the base credentials can only call sts:AssumeRole and nothing else.", "architecture", "ai_coding", False,
     [("boto3", "library"), ("sts:AssumeRole", "api"), ("job runner", "service")],
     [],
     "how does the job runner scope AWS privileges per tenant without carrying an admin key",
     "boto3 session assume role least privilege tenant scope sts"),
    # --- 32 ---
    ("Tenant-scoped queries go through a repository base class that injects a WHERE tenant_id = :tid filter; raw SQL in the repo layer is rejected by Semgrep.", "architecture", "ai_coding", False,
     [("tenant_id", "pattern"), ("Semgrep", "tool"), ("repository", "pattern")],
     [],
     "which pattern enforces tenant isolation at the ORM layer and how is it policed in code",
     "tenant scoped query repository base inject filter semgrep enforce"),
    # --- 33 ---
    ("Enabled Postgres row-level security on the shared orders table; every role connects with SET app.tenant_id and the RLS policy does the scoping for legacy call sites.", "milestone", "ai_coding", False,
     [("Postgres", "database"), ("row-level security", "pattern"), ("orders", "pattern")],
     [("row-level security", "Postgres", "USES")],
     "which database-layer belt-and-braces backs up the application tenant filter on the orders table",
     "postgres row level security policy set tenant legacy fallback"),
    # --- 34 ---
    ("The upload-then-rename path had a classic TOCTOU: we checked size via stat then opened the file, letting a symlink swap slip through; now we open first and fstat the fd.", "problem", "ai_coding", False,
     [("TOCTOU", "pattern"), ("stat", "command"), ("fstat", "command"), ("symlink", "pattern")],
     [("fstat", "stat", "REPLACES")],
     "which time-of-check versus time-of-use bug did the upload path have and how did we close it",
     "toctou stat fstat symlink swap file descriptor check order"),
    # --- 35 ---
    ("HttpOnly, Secure, and SameSite=Strict went on the session cookie; the analytics JS that used to read it was refactored to accept a server-provided visitor id instead.", "architecture", "ai_coding", False,
     [("HttpOnly", "config"), ("Secure", "config"), ("SameSite=Strict", "config"), ("session cookie", "pattern")],
     [],
     "which cookie flags does the session cookie now carry and what refactor did strict mode force",
     "httponly secure samesite strict cookie session analytics refactor"),
    # --- 36 ---
    ("JSON endpoints reject application/json requests missing a same-origin Sec-Fetch-Site; combined with SameSite cookies this stops cross-site JSON POST forgeries.", "fact", "ai_coding", False,
     [("Sec-Fetch-Site", "config"), ("SameSite", "config")],
     [],
     "which fetch-metadata header helps block cross-site JSON POST forgery on top of SameSite",
     "sec fetch site metadata cross site json post samesite guard"),
    # --- 37 ---
    ("Enforced HSTS with includeSubDomains and preload submission; the domain landed on the Chromium preload list so first-visit http downgrades can't happen any more.", "milestone", "ai_coding", False,
     [("HSTS", "protocol"), ("includeSubDomains", "config"), ("Chromium", "platform")],
     [],
     "which transport-layer policy got us onto the browser preload list and what does that buy",
     "hsts include subdomains preload chromium downgrade first visit"),
    # --- 38 ---
    ("Regex handling in the ingest worker dropped python's re in favour of re2; a malicious feed payload had been triggering catastrophic backtracking in a user-agent matcher.", "problem", "ai_coding", False,
     [("re", "library"), ("re2", "library"), ("ingest worker", "service")],
     [("re2", "re", "REPLACES")],
     "which regex engine swap killed a ReDoS bug in the ingest worker's user-agent parser",
     "redos catastrophic backtracking re2 engine swap ingest feed"),
    # --- 39 ---
    ("LDAP queries escape the user input with ldap3's escape_filter_chars; the dn path uses escape_rdn so an attacker-controlled username can't break out of the filter.", "architecture", "ai_coding", False,
     [("ldap3", "library"), ("escape_filter_chars", "method"), ("escape_rdn", "method")],
     [],
     "how does the directory-lookup layer escape user input to avoid LDAP injection",
     "ldap injection escape filter chars rdn ldap3 library user input"),
    # --- 40 ---
    ("XML parsing moved to defusedxml across the board; the old lxml default had XXE-style external-entity resolution on and one test fixture was already pulling file:///etc/hostname.", "problem", "ai_coding", False,
     [("defusedxml", "library"), ("lxml", "library"), ("XXE", "pattern")],
     [("defusedxml", "lxml", "REPLACES")],
     "which XML library swap closed an XXE hole in the document-import pipeline",
     "xxe defusedxml lxml external entity file disclosure parser swap"),
    # --- 41 ---
    ("Command execution uses subprocess with shell=False and a list argv only; a lint rule flags any shell=True call or legacy os-module shell helpers in the application packages.", "preference", "ai_coding", False,
     [("subprocess", "library"), ("shell=False", "config"), ("shell=True", "config")],
     [],
     "which subprocess convention does the codebase enforce to avoid shell-injection surprises",
     "subprocess shell false list argv shell helper ban lint rule"),
    # --- 42 ---
    ("Server-side request signing builds a canonical string with sorted headers and a sha256 body hash before HMAC; a 2025 incident traced to unsorted header concat taught us to pin the canon.", "architecture", "ai_coding", False,
     [("HMAC", "algorithm"), ("sha256", "algorithm"), ("canonical string", "pattern")],
     [],
     "why does the request signer pin a canonical string and what incident drove the rule",
     "request signing canonical header sort body hash hmac incident"),
    # --- 43 ---
    ("Template engine picked Jinja2 with autoescape=True globally; a historical report template that needed raw HTML uses a reviewed |safe filter with a lint-allowed marker.", "decision", "ai_coding", False,
     [("Jinja2", "library"), ("autoescape", "config"), ("|safe", "pattern")],
     [],
     "which template-engine default prevents XSS by construction and how do exceptions get reviewed",
     "jinja2 autoescape safe filter review marker template default"),
    # --- 44 ---
    ("Switched the JWT verifier from PyJWT to python-jose and explicitly set algorithms=['RS256']; the none-alg bypass class can't even parse on the new stack.", "architecture", "ai_coding", False,
     [("PyJWT", "library"), ("python-jose", "library"), ("RS256", "algorithm"), ("none-alg", "pattern")],
     [("python-jose", "PyJWT", "REPLACES")],
     "which JWT library move and config pin killed the classic alg=none bypass path",
     "jwt alg none bypass rs256 python jose pyjwt algorithms pin"),
    # --- 45 ---
    ("The rate limiter keys combine IP plus username hash plus route; per-IP alone let a botnet spray across the signup route until the username axis was added.", "problem", "ai_coding", False,
     [("rate limiter", "pattern"), ("signup", "api")],
     [],
     "which rate-limit keying change stopped a credential-spray botnet from slipping through the signup route",
     "rate limit key ip username route combine spray botnet signup"),
    # --- 46 ---
    ("Structured logging redacts Authorization, Cookie, Set-Cookie, and any key matching (?i)(secret|token|password) via a logfmt processor before the record leaves the process.", "architecture", "ai_coding", False,
     [("Authorization", "config"), ("Cookie", "config"), ("Set-Cookie", "config"), ("logfmt", "pattern")],
     [],
     "which logging pipeline stage strips credentials out of structured records before they hit the shipper",
     "log redact authorization cookie token password pattern processor"),
    # --- 47 ---
    ("The open redirect gap on the login-next parameter got fenced by an allowlist of relative paths and trusted hosts; any scheme or authority in the input is rejected with a 400.", "fact", "ai_coding", False,
     [("open redirect", "pattern"), ("login-next", "config"), ("allowlist", "pattern")],
     [],
     "how does the login-next parameter now avoid being weaponised as an open-redirect primitive",
     "open redirect login next allowlist relative host scheme reject"),
    # --- 48 ---
    ("The feature-flag SDK reads from a signed bundle with ed25519 verification at load; a tampered bundle fails fast instead of silently flipping an admin-only flag on.", "architecture", "ai_coding", False,
     [("ed25519", "algorithm"), ("feature-flag SDK", "library")],
     [("ed25519", "feature-flag SDK", "APPLIES_TO")],
     "how does the feature-flag SDK detect tampering in the flag bundle it loads at startup",
     "feature flag bundle ed25519 signature verify tamper detect load"),
    # --- 49. noise ---
    ("The new kettle in the break room whistles at a pitch that annoys only one specific engineer.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Error responses in production strip stack traces and keep a request id; full traces land only in the internal log pipeline with the id, so support can still join them up.", "preference", "ai_coding", False,
     [("stack traces", "pattern"), ("request id", "pattern")],
     [],
     "how do production error responses stay debuggable without leaking stack traces to callers",
     "stack trace strip production request id log pipeline correlate"),
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
