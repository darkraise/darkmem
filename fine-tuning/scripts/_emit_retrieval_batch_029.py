"""One-off emitter for retrieval top-up batch-029 — hard-negative kind, target shared rows at line offsets 2800..2899.

Writes 100 rows to data/v2/retrieval/batch_029.tmp.jsonl with ids ret-02801..02900.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_029.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 2800
SHARED_OFFSET = 2800
QUERY_KIND = "hard-negative"

# One (query, negative_line_offset) per target row, in target-row order.
# `query` is about the TARGET row; `negative_line_offset` points to a different shared row
# whose text is topically close but does not answer the query.
ENTRIES: list[tuple[str, int]] = [
    # 2800 shared-02802 context-aware output encoding per sink
    ("Which XSS defence replaced global html.escape with per-sink context-aware encoders?", 2841),
    # 2801 shared-02803 CSP nonces per response replace SHA hashes
    ("Which CSP inline-script strategy replaced the hash pipeline and unblocked deploys?", 2800),
    # 2802 shared-02804 X-Content-Type-Options nosniff after IE sniff
    ("Why did we add X-Content-Type-Options: nosniff to every response?", 2835),
    # 2803 shared-02805 Trusted Types on admin SPA
    ("How did Trusted Types policies change raw innerHTML assignment on the admin SPA?", 2800),
    # 2804 shared-02806 SRI mandatory on third-party CDN scripts
    ("Why does the build fail when a vendor script lands without an integrity attribute?", 2801),
    # 2805 shared-02807 allowlisted dispatch deserialiser for the ingestion worker
    ("How did we stop the ingestion worker accepting arbitrary class instances from disk?", 2807),
    # 2806 shared-02808 yaml.load to yaml.safe_load after red-team feature-flag payload
    ("Why did every YAML load in the config service move to yaml.safe_load?", 2805),
    # 2807 shared-02809 path traversal guard via pathlib resolve + descendant check
    ("How does the downloads route guard against path traversal via .. now?", 2828),
    # 2808 shared-02810 NOISE office plant crawling toward monitor
    ("What offhand remark did I make about the office plant this week?", 2847),
    # 2809 shared-02811 SSRF guard allowlists http/https, rejects private IPs
    ("How does the URL fetcher's SSRF guard reject private-IP targets?", 2840),
    # 2810 shared-02812 prototype pollution fixed via Object.create(null)
    ("How did we shut down prototype pollution on the admin dashboard deep-merge path?", 2811),
    # 2811 shared-02813 mass assignment blocked via Pydantic extra='forbid'
    ("How are stray JSON fields bumping user roles rejected on the profile endpoint?", 2810),
    # 2812 shared-02814 CSRF moved to SameSite=Lax plus Origin check on 2026-03-22
    ("When did CSRF protection move from double-submit tokens to SameSite cookies?", 2834),
    # 2813 shared-02815 Retry-After and RateLimit headers on login failures
    ("What headers do the login endpoints now emit on every failure?", 2843),
    # 2814 shared-02816 hmac.compare_digest for secret comparisons
    ("Why do we use hmac.compare_digest for the webhook signature comparison now?", 2816),
    # 2815 shared-02817 Argon2id m=19456 t=2 p=1 per OWASP 2026
    ("Which Argon2id parameters did we standardise password hashing on?", 2817),
    # 2816 shared-02818 bcrypt cost 10 to 12, lazy rehash on login
    ("How did we migrate bcrypt cost from 10 to 12 without a mass reset?", 2815),
    # 2817 shared-02819 2FA recovery codes Argon2-hashed server side
    ("How are the 2FA single-use recovery codes stored server-side?", 2819),
    # 2818 shared-02820 WebAuthn preferred second factor, platform authenticator prompt first
    ("Which second factor does the enrolment flow prompt for first now?", 2817),
    # 2819 shared-02821 uniform login error kills account enumeration
    ("How did we close the account-enumeration channel on the login page?", 2814),
    # 2820 shared-02822 OWASP Top 10 2021 A01..A10 tag in ticket template
    ("Why does every threat-model ticket carry an A01..A10 field?", 2822),
    # 2821 shared-02823 NIST 800-63B password rules + HIBP k-anon
    ("Which NIST rules govern the password-reset flow and the HIBP breach check?", 2815),
    # 2822 shared-02824 trufflehog + gitleaks in pre-commit and CI
    ("Which secret-scanning tools run in pre-commit and full CI history?", 2824),
    # 2823 shared-02825 OSV-Scanner replaces npm audit, SARIF upload
    ("Why did we replace npm audit with OSV-Scanner in the Node pipelines?", 2825),
    # 2824 shared-02826 Syft SBOM CycloneDX attached and signed per release
    ("Which tool generates the CycloneDX SBOM attached to every release?", 2823),
    # 2825 shared-02827 CodeQL queries track GraphQL resolver args
    ("How are GraphQL resolver arguments now tracked as taint sources?", 2827),
    # 2826 shared-02828 Semgrep r2c-OWASP plus local rules
    ("What local Semgrep rules sit on top of the r2c-OWASP pack?", 2814),
    # 2827 shared-02829 fuzz harnesses Atheris + cargo-fuzz
    ("Which fuzzers power the tests/fuzz harnesses across Python and Rust?", 2826),
    # 2828 shared-02830 python-magic magic-byte check on uploads
    ("How do file uploads validate real file type beyond the Content-Type header?", 2807),
    # 2829 shared-02831 least-privilege boto3 per-tenant role
    ("How is the job runner's boto3 session scoped per tenant?", 2830),
    # 2830 shared-02832 repository base class injects WHERE tenant_id
    ("How is tenant scoping injected into queries in the repository layer?", 2829),
    # 2831 shared-02833 Postgres RLS on shared orders; app.tenant_id via SET
    ("How did we enable tenant scoping on the shared orders table for legacy call sites?", 2830),
    # 2832 shared-02834 TOCTOU upload-then-rename fixed by fstat on opened fd
    ("How did the upload-then-rename TOCTOU race get closed?", 2804),
    # 2833 shared-02835 session cookie HttpOnly, Secure, SameSite=Strict
    ("Which flags went on the session cookie and how did analytics adapt?", 2812),
    # 2834 shared-02836 Sec-Fetch-Site same-origin check stops cross-site JSON POST
    ("How do JSON endpoints reject cross-site POST requests using fetch metadata?", 2812),
    # 2835 shared-02837 HSTS includeSubDomains plus preload submission
    ("What HSTS setting landed us on the Chromium preload list?", 2802),
    # 2836 shared-02838 ingest worker moved re to re2 after ReDoS
    ("Why did the ingest worker drop Python's re for re2 on user-agent parsing?", 2838),
    # 2837 shared-02839 LDAP ldap3 escape_filter_chars and escape_rdn
    ("How are LDAP filter and DN values escaped against injection?", 2836),
    # 2838 shared-02840 defusedxml across the board
    ("Why did we move XML parsing to defusedxml across the codebase?", 2837),
    # 2839 shared-02841 subprocess shell=False, list argv only
    ("What lint rule enforces shell=False and list argv for command execution?", 2807),
    # 2840 shared-02842 canonical string sorted headers + sha256 body hash before HMAC
    ("How did a 2025 signing incident teach us to sort headers in the canonical string?", 2814),
    # 2841 shared-02843 Jinja2 autoescape=True globally
    ("Why is Jinja2 autoescape set to True globally and how is raw HTML handled?", 2800),
    # 2842 shared-02844 JWT verifier moved to python-jose with algorithms=['RS256']
    ("How did we kill the JWT none-alg bypass class entirely?", 2814),
    # 2843 shared-02845 rate limiter combines IP + username hash + route
    ("Why did the rate limiter add a username axis on top of per-IP keys?", 2813),
    # 2844 shared-02846 structured logging redacts Authorization/Cookie and regex-matched keys
    ("How does the structured logging pipeline redact secrets before records leave the process?", 2848),
    # 2845 shared-02847 open redirect gap fenced by relative-path and trusted-host allowlist
    ("How did we fence the open-redirect gap on the login-next parameter?", 2809),
    # 2846 shared-02848 feature-flag SDK verifies signed bundle with ed25519 at load
    ("How does the feature-flag SDK fail fast on a tampered bundle at load?", 2804),
    # 2847 shared-02849 NOISE kettle whistles at a pitch annoying one engineer
    ("What quick aside did I make about the break-room kettle?", 2808),
    # 2848 shared-02850 prod error responses strip traces, keep request id
    ("How do production error responses let support still pull the full stack trace?", 2844),
    # 2849 shared-02851 Adopted Mochi, tortoiseshell kitten, from Cats Protection Bridgwater 2026-02-14
    ("When and where did we adopt Mochi the tortoiseshell kitten?", 2889),
    # 2850 shared-02852 Hugo's annual booster at Cedar Lane on 2026-05-09
    ("When is Hugo's annual booster at Cedar Lane and which vaccines this round?", 2880),
    # 2851 shared-02853 Mochi switched Royal Canin Kitten to Orijen on 2026-03-22
    ("Why did Mochi move from Royal Canin Kitten to Orijen Cat & Kitten on 2026-03-22?", 2865),
    # 2852 shared-02854 long-line at Westover Common, short flexi at Heath Path
    ("Why does Hugo wear the long-line at Westover Common but the short flexi at Heath Path?", 2891),
    # 2853 shared-02855 Hugo harness moved to Ruffwear Front Range 2026-01-18
    ("Why did Hugo's harness switch to the Ruffwear Front Range on 2026-01-18?", 2850),
    # 2854 shared-02856 Tofu basks 38 C hot / 25 C cool; UVB six months
    ("What are Tofu's hot and cool basking temperatures and UVB replacement cadence?", 2871),
    # 2855 shared-02857 Greenfields refused Hugo, moved to Pawhaven
    ("Why did we move Hugo's August boarding from Greenfields to Pawhaven?", 2890),
    # 2856 shared-02858 Mochi litter: two IKEA Vargon trays, World's Best corn
    ("How is Mochi's litter setup arranged across trays and rooms?", 2881),
    # 2857 shared-02859 Koi pond pH 8.1 on 2026-04-03; peat bag plan
    ("What triggered the planned partial water change and peat-bag addition on the koi pond?", 2867),
    # 2858 shared-02860 NOISE cat at the door again
    ("What brief aside happened about the cat at the door?", 2883),
    # 2859 shared-02861 Hugo moved clicker to verbal-marker on 2026-02-09
    ("Why did Hugo's training switch from clicker to verbal-marker on 2026-02-09?", 2860),
    # 2860 shared-02862 Hugo hand-strip at Wagtails 2026-03-15
    ("Why is Hugo's Wagtails appointment a hand-strip rather than a clip?", 2891),
    # 2861 shared-02863 Hugo recall from 10 m to 3 m: 4/10 to 9/10
    ("How did shortening Hugo's recall distance change his return rate?", 2859),
    # 2862 shared-02864 WTA Spring Open at Stoneleigh 2026-05-23
    ("When is the Welsh Terrier Spring Open at Stoneleigh and when do entries close?", 2878),
    # 2863 shared-02865 Mochi prefers cardboard scratcher under bay window
    ("Which scratcher does Mochi actually use and which gets ignored?", 2872),
    # 2864 shared-02866 Biscuit end-of-life at home on 2026-01-07 with Dr Patel
    ("How was Biscuit's end-of-life appointment on 2026-01-07 handled at home?", 2894),
    # 2865 shared-02867 Pip's seed mix moved Trill to Versele-Laga Prestige 2026-03-01
    ("Why did Pip's seed mix move from Trill to Versele-Laga Prestige?", 2851),
    # 2866 shared-02868 Hugo microchip at Petlog; address updated 2026-04-02
    ("Where is Hugo's microchip registered and when was the address updated?", 2895),
    # 2867 shared-02869 Koi UV clarifier replaced with Oase Bitron 36C on 2026-02-20
    ("Why did the koi pond UV clarifier get replaced with the Oase Bitron 36C?", 2886),
    # 2868 shared-02870 Sureflap chip-only cat-flap; neighbour's tabby locked out
    ("Why is the back-door cat-flap set to Sureflap chip-only with Mochi whitelisted?", 2876),
    # 2869 shared-02871 06:40 morning ritual
    ("What is the 06:40 morning ritual before breakfast?", 2886),
    # 2870 shared-02872 Pip cotton cover 21:00 to 07:00 halved chatter
    ("How did Pip's cotton cover change the early-morning chatter?", 2889),
    # 2871 shared-02873 Tofu eats dubia roaches 3x week, never spinach
    ("What is Tofu's feeding schedule and which greens are off limits?", 2854),
    # 2872 shared-02874 slow-feeder bowl stretches Hugo's meal
    ("Why did Hugo move from a standard bowl to a slow-feeder?", 2886),
    # 2873 shared-02875 wildlife camera caught hedgehog 23:14 on 2026-04-08
    ("What did the wildlife camera catch at 23:14 on 2026-04-08 and what did we do?", 2899),
    # 2874 shared-02876 Hugo insurance Petplan to Bought By Many 2026-01-02
    ("Why did Hugo's pet insurance move from Petplan to Bought By Many on 2026-01-02?", 2852),
    # 2875 shared-02877 Sasha walks Hugo Tue/Thu 11:30, GBP 15, riverbank loop
    ("What is Sasha's walking arrangement for Hugo and what does it cost?", 2893),
    # 2876 shared-02878 Mochi Bravecto Plus monthly, alternating Stronghold
    ("Which flea treatment does Mochi rotate and what did the Bravecto clear?", 2852),
    # 2877 shared-02879 reactive-dog class at Pawsitive Steps 2026-03-12
    ("What did the reactive-dog class at Pawsitive Steps cover for Hugo?", 2861),
    # 2878 shared-02880 Adaptil collar over diffuser for fireworks weekends
    ("Why do we prefer the Adaptil collar over the diffuser on fireworks weekends?", 2850),
    # 2879 shared-02881 koi feeding every two days below 10 C
    ("Why does koi feeding drop to once every two days below 10 C?", 2887),
    # 2880 shared-02882 Tofu retained shed 2026-03-18; warm soak nightly
    ("How are we treating Tofu's retained shed on the left back toe?", 2854),
    # 2881 shared-02883 kitten-proof front room list
    ("What kitten-proofing items got ticked off in the front room?", 2868),
    # 2882 shared-02884 NOISE dog wants out
    ("What quick aside did I make about the dog wanting out?", 2858),
    # 2883 shared-02885 joined Cornish Rex breed forum 2026-02-11
    ("Why did I join the Cornish Rex breed forum on 2026-02-11?", 2884),
    # 2884 shared-02886 Acme 211.5 recall whistle on black lanyard
    ("Which recall whistle is Hugo's and where is it kept?", 2887),
    # 2885 shared-02887 koi pellets Tetra Pond to Saki-Hikari Growth 2026-04-01
    ("Why did the koi pond pellet brand move to Saki-Hikari Growth on 2026-04-01?", 2888),
    # 2886 shared-02888 PetSafe Treat Pouch Sport on right hip
    ("How is the dog-training treat pouch positioned against the other gear?", 2884),
    # 2887 shared-02889 koi pond 1500 L holds 8 adult fish
    ("What is the koi pond stocking limit and the rule of thumb behind it?", 2879),
    # 2888 shared-02890 Pip free-flight in conservatory 2026-03-29
    ("How did we set up Pip's free-flight session in the conservatory on 2026-03-29?", 2870),
    # 2889 shared-02891 Mochi carrier acceptance from 30 s to 20 min
    ("How did Mochi's carrier tolerance go from 30 seconds to 20 minutes?", 2849),
    # 2890 shared-02892 home boarding with Sasha over kennels for September
    ("Why pick home boarding with Sasha over kennels for the September trip?", 2855),
    # 2891 shared-02893 grooming: hand-strip 12 wks, ear pluck monthly, Dremel nails
    ("What is Hugo's grooming schedule across strip, ears, and nails?", 2860),
    # 2892 shared-02894 pet-sitter agreement with Sasha: one A4 page in drawer
    ("What is on the one-page pet-sitter agreement with Sasha in the kitchen drawer?", 2875),
    # 2893 shared-02895 Mochi stuck behind dishwasher 2026-03-08; 50 mm offcut
    ("How did we fix the gap behind the dishwasher after Mochi got stuck?", 2881),
    # 2894 shared-02896 paw-print mould of Biscuit at Cedar Lane 2026-01-07
    ("Where was Biscuit's paw-print mould done and where does it sit now?", 2864),
    # 2895 shared-02897 household no more pets until 2028
    ("What did the household agree about new pets after Mochi and Hugo?", 2897),
    # 2896 shared-02898 Mochi hairball weekly to monthly via Whiskas malt
    ("How did we cut Mochi's hairball frequency from weekly to monthly?", 2851),
    # 2897 shared-02899 Dogs Trust rehoming evening 2026-05-02
    ("Why am I attending the Dogs Trust rehoming evening on 2026-05-02?", 2895),
    # 2898 shared-02900 2026 garden tweaks: hedgehog highway, stumpery, no slug pellets
    ("What wildlife-friendly garden tweaks are planned for 2026?", 2873),
    # 2899 shared-02901 Thursday pub crew at The Anvil
    ("What rhythm did the Thursday pub crew at The Anvil settle into for food orders?", 2869),
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    targets = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(ENTRIES) == 100
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, ((query, neg_off), tgt) in enumerate(zip(ENTRIES, targets), start=1):
            neg_row = json.loads(lines[neg_off])
            if neg_row["id"] == tgt["id"]:
                raise ValueError(f"negative row must differ from target at index {i}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": tgt["id"],
                "query": query,
                "negative": neg_row["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
