"""One-off emitter for shared-base batch-197 — technical domain (DNS servers, DNSSEC, certificate automation, ACME).

Writes 50 rows to data/v2/shared/batch_197.tmp.jsonl with ids shared-09801..09850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_197.tmp.jsonl"
ID_OFFSET = 9800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Moved the authoritative zone for the main domain from BIND 9 to Knot DNS; zone-transfer throughput on the catalog-zone reload dropped from twelve seconds to under a second on the same VM.", "decision", "technical", False,
     [("BIND 9", "library"), ("Knot DNS", "library"), ("catalog-zone", "pattern")],
     [("Knot DNS", "BIND 9", "REPLACES")],
     "which authoritative DNS server replaced BIND 9 for the primary zone and what throughput win did the migration unlock",
     "knot dns bind 9 authoritative zone transfer catalog reload throughput"),
    # --- 2. architecture ---
    ("Recursive resolver tier runs Unbound fronted by dnsdist for ACL and rate-limiting; NSD handles the authoritative tier for public zones and the two never share a process or a cache.", "architecture", "technical", False,
     [("Unbound", "library"), ("dnsdist", "tool"), ("NSD", "library"), ("ACL", "concept")],
     [("dnsdist", "Unbound", "APPLIES_TO"), ("NSD", "Unbound", "COMMUNICATES_WITH")],
     "how is the resolver tier split from the authoritative tier and which component handles ACL in front of Unbound",
     "unbound nsd dnsdist recursive authoritative acl rate limit split"),
    # --- 3. decision ---
    ("Chose PowerDNS Authoritative over BIND 9 for the customer DNS product; the MySQL backend and HTTP API matched the existing provisioning stack without writing a zone-file generator.", "decision", "technical", False,
     [("PowerDNS", "library"), ("BIND 9", "library"), ("MySQL", "database"), ("HTTP API", "protocol")],
     [("PowerDNS", "BIND 9", "PREFERS"), ("PowerDNS", "MySQL", "USES")],
     "which authoritative DNS stack did we pick for the customer product and which backend integration drove the choice",
     "powerdns bind mysql backend http api provision customer product"),
    # --- 4. fact ---
    ("CoreDNS is the cluster DNS in the Kubernetes fleet; the kubernetes plugin resolves service names from the API server and the forward plugin chains upstream to the node resolver.", "fact", "technical", False,
     [("CoreDNS", "library"), ("Kubernetes", "platform"), ("kubernetes plugin", "library"), ("forward plugin", "library")],
     [("CoreDNS", "Kubernetes", "APPLIES_TO")],
     "which DNS server and plugins resolve service names inside the Kubernetes fleet and how does it chain upstream",
     "coredns kubernetes plugin forward service name upstream cluster"),
    # --- 5. architecture ---
    ("DNSSEC signing lives on the hidden primary running Knot DNS with automatic KSK and ZSK rollover; the public NSD replicas serve the signed zone and never hold key material.", "architecture", "technical", False,
     [("DNSSEC", "protocol"), ("Knot DNS", "library"), ("NSD", "library"), ("KSK", "concept"), ("ZSK", "concept"), ("hidden primary", "pattern")],
     [("Knot DNS", "DNSSEC", "USES"), ("NSD", "Knot DNS", "COMMUNICATES_WITH")],
     "how is DNSSEC key material isolated from the public-facing nameservers and which server handles rollover",
     "dnssec ksk zsk knot nsd hidden primary rollover key isolate"),
    # --- 6. milestone ---
    ("Finished the DS-record handoff at the registrar for the root zone cut; the chain of trust validates end-to-end on Cloudflare's public resolver and on 1.1.1.1 dig +dnssec checks.", "milestone", "technical", False,
     [("DS-record", "concept"), ("registrar", "service"), ("Cloudflare", "service"), ("chain of trust", "concept"), ("dig", "tool")],
     [("DS-record", "chain of trust", "SUPPORTS")],
     "which registrar handoff closed the DNSSEC chain of trust and which public resolver confirmed the validation",
     "ds record registrar chain trust cloudflare 1.1.1.1 dig dnssec validate"),
    # --- 7. problem ---
    ("DNSSEC validation broke for a week after we rotated the ZSK without pre-publishing it; resolvers with stale cached RRSIGs served SERVFAIL until the pre-publish window in the rollover policy got fixed.", "problem", "technical", False,
     [("ZSK", "concept"), ("RRSIG", "concept"), ("SERVFAIL", "concept"), ("pre-publish", "pattern"), ("rollover policy", "pattern")],
     [("pre-publish", "SERVFAIL", "FIXES")],
     "which DNSSEC rollover step did we skip that caused a week of SERVFAIL responses and how was it fixed",
     "zsk rotation pre publish rrsig servfail rollover policy cache"),
    # --- 8. decision ---
    ("Local network DNS runs AdGuard Home instead of Pi-hole; the built-in DoH upstream and per-client filtering profiles made it easier to split the kids' devices from the work laptops.", "decision", "technical", False,
     [("AdGuard Home", "tool"), ("Pi-hole", "tool"), ("DoH", "protocol"), ("per-client filtering", "pattern")],
     [("AdGuard Home", "Pi-hole", "PREFERS"), ("AdGuard Home", "DoH", "USES")],
     "which home DNS filter replaced Pi-hole and which two features drove the swap",
     "adguard home pi hole doh per client filter upstream home network"),
    # --- 9. fact ---
    ("dnsmasq serves the guest VLAN's DHCP and DNS on the edge router; its small footprint and single config file beat running a separate ISC DHCP daemon alongside Unbound on the same box.", "fact", "technical", False,
     [("dnsmasq", "library"), ("DHCP", "protocol"), ("ISC DHCP", "library"), ("Unbound", "library"), ("VLAN", "concept")],
     [("dnsmasq", "ISC DHCP", "REPLACES")],
     "which combined DHCP and DNS daemon runs on the edge router and what did it replace",
     "dnsmasq dhcp dns guest vlan edge router isc unbound footprint"),
    # --- 10. noise ---
    ("The office espresso machine's grinder started making a metallic ticking sound about twelve days ago and nobody has admitted ownership of opening the hopper.", "fact", "noise", True, [], [], None, None),
    # --- 11. architecture ---
    ("Split-horizon DNS is served by two Unbound views: an internal view resolves RFC1918 names from local zones, an external view forwards to 1.1.1.1 over DoT and never sees the internal records.", "architecture", "technical", False,
     [("Split-horizon DNS", "pattern"), ("Unbound", "library"), ("RFC1918", "concept"), ("DoT", "protocol"), ("1.1.1.1", "service")],
     [("Unbound", "DoT", "USES")],
     "how does split-horizon DNS separate internal and external views in Unbound and which upstream transport is used",
     "split horizon unbound view internal external rfc1918 dot 1.1.1.1"),
    # --- 12. reference ---
    ("RFC 8555 defines the ACME protocol; the identifier authorisation flow, challenge types, and order lifecycle are the bits every issuer client has to implement in lockstep.", "reference", "technical", False,
     [("RFC 8555", "publication"), ("ACME", "protocol"), ("challenge", "concept"), ("order", "concept")],
     [("RFC 8555", "ACME", "USES")],
     "which RFC defines the ACME protocol and which three flow pieces must a client implement to interoperate",
     "rfc 8555 acme protocol challenge order authorisation identifier client"),
    # --- 13. decision ---
    ("Switched the wildcard certificate pipeline from certbot to acme.sh; the native dns_cf hook for Cloudflare avoided the Python dependency drag that certbot's dns plugins pulled in on Alpine.", "decision", "technical", False,
     [("certbot", "tool"), ("acme.sh", "tool"), ("dns_cf", "library"), ("Cloudflare", "service"), ("Alpine", "platform")],
     [("acme.sh", "certbot", "REPLACES"), ("acme.sh", "dns_cf", "USES")],
     "which ACME client replaced certbot for wildcard issuance and why did it win on Alpine",
     "acme.sh certbot wildcard dns_cf cloudflare alpine python dependency"),
    # --- 14. decision ---
    ("Kubernetes certificate issuance uses cert-manager with a Let's Encrypt ACME ClusterIssuer; the DNS-01 solver delegates to Route53 via IRSA so pods never hold long-lived cloud credentials.", "decision", "technical", False,
     [("cert-manager", "tool"), ("Let's Encrypt", "service"), ("ClusterIssuer", "concept"), ("DNS-01", "protocol"), ("Route53", "service"), ("IRSA", "pattern")],
     [("cert-manager", "Let's Encrypt", "USES"), ("DNS-01", "Route53", "APPLIES_TO")],
     "which Kubernetes tool issues Let's Encrypt certs and how does the DNS-01 solver authenticate to Route53 without stored keys",
     "cert manager letsencrypt cluster issuer dns 01 route53 irsa kubernetes"),
    # --- 15. architecture ---
    ("Internal PKI uses step-ca from smallstep as the private ACME issuer; workloads request short-lived certs via the ACME HTTP-01 flow against a cluster-local DNS name and renew every twenty-four hours.", "architecture", "technical", False,
     [("step-ca", "tool"), ("smallstep", "service"), ("ACME", "protocol"), ("HTTP-01", "protocol"), ("short-lived certs", "pattern")],
     [("step-ca", "ACME", "USES"), ("HTTP-01", "step-ca", "APPLIES_TO")],
     "which internal CA issues short-lived workload certificates and which ACME challenge type does it use",
     "step ca smallstep acme http 01 private pki short lived internal"),
    # --- 16. fact ---
    ("TLS-ALPN-01 handles issuance for the load balancer that terminates on port 443 only; HTTP-01 was off the table because port 80 is blocked at the perimeter and the ALB can't redirect before handshake.", "fact", "technical", False,
     [("TLS-ALPN-01", "protocol"), ("HTTP-01", "protocol"), ("load balancer", "service"), ("ALB", "service")],
     [("TLS-ALPN-01", "HTTP-01", "REPLACES")],
     "which ACME challenge type works when only port 443 is reachable and why is HTTP-01 unusable here",
     "tls alpn 01 http 01 port 443 alb load balancer perimeter block"),
    # --- 17. preference ---
    ("Prefer the Let's Encrypt staging directory for CI tests; one runaway CI loop re-issued the same SAN set twenty times in an hour against production, and pointing tests at staging plus a local cert cache now prevents that blast-radius.", "preference", "technical", False,
     [("Let's Encrypt", "service"), ("staging directory", "pattern"), ("SAN", "concept"), ("cert cache", "pattern"), ("CI loop", "concept")],
     [("staging directory", "Let's Encrypt", "APPLIES_TO"), ("cert cache", "CI loop", "IMPROVES_ON")],
     "which Let's Encrypt directory does CI prefer and which two mechanisms prevent a runaway re-issue storm",
     "letsencrypt staging directory san cert cache ci loop prefer production"),
    # --- 18. decision ---
    ("Picked lego over acme.sh for the Go services; a single static binary with DNS-provider packages baked in was simpler to ship in our scratch containers than a shell script with curl dependencies.", "decision", "technical", False,
     [("lego", "tool"), ("acme.sh", "tool"), ("scratch container", "pattern"), ("DNS-provider", "library")],
     [("lego", "acme.sh", "PREFERS")],
     "which ACME client did the Go services pick and which deployment constraint ruled against acme.sh",
     "lego acme.sh go service scratch container static binary dns provider"),
    # --- 19. milestone ---
    ("Completed CAA coverage across every owned apex zone, pinning issuance to Let's Encrypt and Sectigo only; the wildcard CAA plus the iodef mailto now means a rogue issuance attempt bounces and we get an email from any well-behaved CA.", "milestone", "technical", False,
     [("CAA", "concept"), ("Let's Encrypt", "service"), ("Sectigo", "service"), ("iodef", "concept")],
     [("CAA", "Let's Encrypt", "APPLIES_TO")],
     "how do CAA records at the apex restrict who can issue certificates and which field gets us notified on a bounce",
     "caa record letsencrypt sectigo iodef mailto issuance pin apex"),
    # --- 20. reference ---
    ("Certificate Transparency logs are queried via crt.sh for monitoring; a weekly cron pulls certs for our domains and alerts on any issuance that wasn't triggered by our own ACME clients.", "reference", "technical", False,
     [("Certificate Transparency", "concept"), ("crt.sh", "tool"), ("ACME", "protocol")],
     [("crt.sh", "Certificate Transparency", "USES")],
     "which Certificate Transparency tool does the weekly monitoring job query and what does it alert on",
     "certificate transparency ct log crt.sh monitor weekly cron alert"),
    # --- 21. decision ---
    ("Authoritative DNS for the new SaaS product runs on NS1; the data-feed API for traffic-steering records lets the ops plane swap pool members without editing zone files by hand.", "decision", "technical", False,
     [("NS1", "service"), ("data-feed API", "api"), ("traffic-steering", "pattern")],
     [("NS1", "data-feed API", "USES")],
     "which managed DNS vendor runs the new SaaS product's zones and which API drives traffic-steering without zone edits",
     "ns1 managed dns data feed api traffic steering pool saas ops"),
    # --- 22. fact ---
    ("Route53 hosts the public zone for the billing domain; ALIAS records point at the CloudFront distribution so the apex A record can front a CDN without CNAME-at-apex heartburn.", "fact", "technical", False,
     [("Route53", "service"), ("ALIAS record", "concept"), ("CloudFront", "service"), ("apex A record", "concept")],
     [("Route53", "CloudFront", "COMMUNICATES_WITH")],
     "how does Route53 let the apex A record front CloudFront without violating the CNAME-at-apex rule",
     "route53 alias cloudfront apex a record cname heartburn billing"),
    # --- 23. architecture ---
    ("Multi-cloud DNS is Google Cloud DNS as the primary with Cloudflare DNS as the hot secondary; zone changes propagate via AXFR from the GCP source and a health-check failover flips the NS set within five minutes.", "architecture", "technical", False,
     [("Google Cloud DNS", "service"), ("Cloudflare DNS", "service"), ("AXFR", "protocol"), ("health-check failover", "pattern"), ("NS set", "concept")],
     [("Cloudflare DNS", "Google Cloud DNS", "COMMUNICATES_WITH"), ("AXFR", "Cloudflare DNS", "APPLIES_TO")],
     "which two managed DNS vendors form the primary-secondary pair and how do zones propagate between them",
     "google cloud dns cloudflare axfr primary secondary failover ns multi"),
    # --- 24. preference ---
    ("Prefer DNS-01 over HTTP-01 for every production cert; wildcard support alone is enough, and DNS-01 works identically whether the host is public, internal, or behind a strict perimeter.", "preference", "technical", False,
     [("DNS-01", "protocol"), ("HTTP-01", "protocol"), ("wildcard", "concept"), ("perimeter", "concept")],
     [("DNS-01", "HTTP-01", "PREFERS")],
     "why does the team standardise on DNS-01 instead of HTTP-01 for production certificates",
     "dns 01 http 01 wildcard perimeter production prefer standard"),
    # --- 25. problem ---
    ("DNS-01 validation failed intermittently because our TTL-60 _acme-challenge TXT updates raced negative caching on the validating resolver; dropped propagation wait to poll the authoritative servers directly and the flake vanished.", "problem", "technical", False,
     [("DNS-01", "protocol"), ("_acme-challenge", "concept"), ("TXT", "concept"), ("negative caching", "concept")],
     [],
     "which caching behaviour caused DNS-01 validation flakes and what polling change eliminated them",
     "dns 01 acme challenge txt negative cache ttl poll authoritative flake"),
    # --- 26. milestone ---
    ("Cut over the internal service mesh to DoT between every node and the local stub resolver; dnsdist on each node now speaks DoT upstream to the central Unbound pair, leaving plain UDP only inside the node namespace.", "milestone", "technical", False,
     [("DoT", "protocol"), ("dnsdist", "tool"), ("Unbound", "library"), ("stub resolver", "pattern")],
     [("dnsdist", "DoT", "USES"), ("dnsdist", "Unbound", "COMMUNICATES_WITH")],
     "which cutover completed DoT coverage across the service mesh and where does plain UDP still live",
     "dot dnsdist unbound stub resolver service mesh node namespace udp"),
    # --- 27. fact ---
    ("ODoH support was added to the client-side resolver library for privacy-critical paths; the relay is separate from the target resolver so neither side sees both the client IP and the query together.", "fact", "technical", False,
     [("ODoH", "protocol"), ("resolver library", "library"), ("relay", "concept"), ("target resolver", "concept")],
     [],
     "which DNS privacy protocol splits client IP from query content and how does the relay-target split achieve it",
     "odoh oblivious dns https relay target client ip query privacy"),
    # --- 28. reference ---
    ("DoQ is defined in RFC 9250 and layers DNS over QUIC; it gets us connection migration across networks and zero-RTT resume, which matters for mobile clients roaming between Wi-Fi and LTE.", "reference", "technical", False,
     [("DoQ", "protocol"), ("RFC 9250", "publication"), ("QUIC", "protocol"), ("zero-RTT", "concept")],
     [("DoQ", "QUIC", "USES")],
     "which RFC specifies DoQ and which two QUIC features make it valuable for roaming mobile clients",
     "doq rfc 9250 quic zero rtt connection migration mobile roam"),
    # --- 29. decision ---
    ("Local developer machines use encrypted DNS via NextDNS with DoH profiles; the native /etc/hosts file is reserved for pinned staging overrides that intentionally shadow the resolver output.", "decision", "technical", False,
     [("NextDNS", "service"), ("DoH", "protocol"), ("/etc/hosts", "file"), ("staging override", "pattern")],
     [("NextDNS", "DoH", "USES")],
     "which encrypted DNS provider do developer machines use and what role does the hostsfile still play",
     "nextdns doh developer hosts file staging override encrypted dns"),
    # --- 30. architecture ---
    ("Gandi LiveDNS hosts the public zones that webhook-driven acme.sh clients update with DNS-01 TXT records; the scoped API key is per-zone and rotated from Vault on a thirty-day schedule.", "architecture", "technical", False,
     [("Gandi LiveDNS", "service"), ("acme.sh", "tool"), ("DNS-01", "protocol"), ("API key", "concept"), ("Vault", "tool")],
     [("acme.sh", "Gandi LiveDNS", "USES"), ("Vault", "API key", "APPLIES_TO")],
     "which DNS provider hosts the zones that acme.sh updates for DNS-01 and where do the scoped API keys rotate",
     "gandi livedns acme.sh dns 01 txt api key vault scope rotate"),
    # --- 31. decision ---
    ("Decided to standardise on SHA-256 DS digests rather than SHA-384 for registrar handoffs; the EPP endpoints at two of our three registrars still reject SHA-384, and downgrading kept our KSK rollover schedule unblocked.", "decision", "technical", False,
     [("SHA-256", "algorithm"), ("SHA-384", "algorithm"), ("DS digest", "concept"), ("EPP", "protocol"), ("KSK", "concept")],
     [("SHA-256", "SHA-384", "PREFERS")],
     "which DS digest algorithm did the team standardise on for registrar handoffs and what registrar limitation forced the choice",
     "sha 256 sha 384 ds digest epp registrar ksk rollover standard"),
    # --- 32. fact ---
    ("NSEC3 with opt-out is used on the large delegation-heavy TLD-style zone; plain NSEC was leaking the entire name list via zone walking in a single afternoon of dnsrecon runs.", "fact", "technical", False,
     [("NSEC3", "concept"), ("NSEC", "concept"), ("opt-out", "pattern"), ("dnsrecon", "tool"), ("zone walking", "concept")],
     [("NSEC3", "NSEC", "REPLACES")],
     "which authenticated denial scheme replaced NSEC on the delegation-heavy zone and what attack motivated it",
     "nsec3 nsec opt out zone walk dnsrecon delegation tld denial"),
    # --- 33. milestone ---
    ("Finished moving all zone provisioning to a git-ops flow: zone files live in a repo, a CI job runs named-checkzone and knotc zone-check, and a merge kicks a signed push to the hidden primary.", "milestone", "technical", False,
     [("git-ops", "pattern"), ("named-checkzone", "tool"), ("knotc", "tool"), ("hidden primary", "pattern"), ("CI job", "concept")],
     [],
     "which git-ops flow validates and deploys zone files and which two check tools run in CI before merge",
     "git ops zone file named checkzone knotc ci merge hidden primary"),
    # --- 34. decision ---
    ("Kept Pi-hole instead of CoreDNS for the homelab's blocklist use case; the query-log UI and gravity updates were a better fit than writing custom CoreDNS plugins in Go.", "decision", "technical", False,
     [("Pi-hole", "tool"), ("CoreDNS", "library"), ("gravity", "pattern"), ("query-log UI", "api"), ("Go", "language")],
     [("Pi-hole", "CoreDNS", "PREFERS")],
     "why did the homelab stick with Pi-hole instead of switching to CoreDNS for blocklists",
     "pi hole coredns homelab blocklist gravity query log go plugin"),
    # --- 35. milestone ---
    ("All public hostnames migrated off manual OpenSSL issuance to Let's Encrypt via cert-manager; the last long-lived year-long cert expired on the staging load balancer without a single outage.", "milestone", "technical", False,
     [("OpenSSL", "tool"), ("Let's Encrypt", "service"), ("cert-manager", "tool"), ("load balancer", "service")],
     [("cert-manager", "OpenSSL", "REPLACES")],
     "which certificate issuance migration retired the last long-lived manual OpenSSL cert and what tool handled the automation",
     "openssl letsencrypt cert manager migrate long lived expire load balancer"),
    # --- 36. architecture ---
    ("Revocation is handled by short lifetimes, not CRL or OCSP; certs issued by step-ca are ninety-minute leaves and the MUST-STAPLE flag is set on anything that does cross a trust boundary.", "architecture", "technical", False,
     [("short lifetimes", "pattern"), ("CRL", "concept"), ("OCSP", "protocol"), ("step-ca", "tool"), ("MUST-STAPLE", "concept")],
     [("short lifetimes", "OCSP", "REPLACES")],
     "which revocation strategy replaces CRL and OCSP in the internal PKI and which flag protects boundary-crossing certs",
     "short lifetime crl ocsp step ca must staple revoke boundary"),
    # --- 37. preference ---
    ("Prefer a weekly throwaway-cert canary for every cert-manager issuer rather than waiting for renewal to silently fail; after an IAM policy refactor once stripped a DNS-01 solver's Route53 TXT write permission without warning, the canary became non-negotiable.", "preference", "technical", False,
     [("cert-manager", "tool"), ("DNS-01", "protocol"), ("Route53", "service"), ("IAM policy", "concept"), ("throwaway-cert canary", "pattern")],
     [("throwaway-cert canary", "cert-manager", "APPLIES_TO")],
     "why does the team prefer a weekly throwaway-cert canary per cert-manager issuer and which near-miss made it mandatory",
     "throwaway cert canary cert manager issuer weekly dns 01 route53 iam"),
    # --- 38. fact ---
    ("The hostsfile on the jump host pins _ns.internal to a /32 inside the bastion VPC; this deliberately shadows the resolver so bootstrapping the ACME client on a fresh node doesn't depend on cluster DNS being up.", "fact", "technical", False,
     [("hostsfile", "file"), ("jump host", "service"), ("bastion VPC", "service"), ("ACME client", "tool"), ("cluster DNS", "service")],
     [],
     "why does the jump host pin ns.internal in the hostsfile and what cluster bootstrap problem does it solve",
     "hosts file jump host bastion ns internal acme bootstrap shadow"),
    # --- 39. decision ---
    ("EdDSA with Ed25519 is the default for new DNSSEC zones; RSA-2048 survives only on legacy zones where the registrar still doesn't accept DS records for algorithm 15.", "decision", "technical", False,
     [("EdDSA", "algorithm"), ("Ed25519", "algorithm"), ("RSA-2048", "algorithm"), ("algorithm 15", "concept"), ("DS record", "concept")],
     [("Ed25519", "RSA-2048", "PREFERS")],
     "which DNSSEC signing algorithm is the new default and what forces the legacy RSA-2048 holdouts to stay",
     "eddsa ed25519 rsa 2048 algorithm 15 ds record legacy registrar"),
    # --- 40. architecture ---
    ("A stub resolver on each node writes a tiny resolv.conf that points at 127.0.0.53 where systemd-resolved runs; the upstream DNS is managed through NetworkManager and resolvectl status is the source of truth.", "architecture", "technical", False,
     [("stub resolver", "pattern"), ("resolv.conf", "file"), ("systemd-resolved", "tool"), ("NetworkManager", "tool"), ("resolvectl", "tool")],
     [("systemd-resolved", "NetworkManager", "COMMUNICATES_WITH")],
     "how does each Linux node wire resolv.conf to systemd-resolved and which command is authoritative for the current upstream",
     "systemd resolved resolv.conf network manager resolvectl stub node linux"),
    # --- 41. preference ---
    ("Prefer cert-manager's Certificate CRD with a duration of forty-eight hours and a renewBefore of twenty-four for cluster-internal certs; the short window is cheap and it surfaces issuer breakage within a day.", "preference", "technical", False,
     [("cert-manager", "tool"), ("Certificate CRD", "concept"), ("renewBefore", "config"), ("issuer", "concept")],
     [],
     "which cert-manager lifetimes does the team prefer for cluster-internal certs and what monitoring benefit does the short window provide",
     "cert manager certificate crd duration renew before short internal"),
    # --- 42. problem ---
    ("Cloudflare DNS propagation delayed a DNS-01 challenge because the universal-SSL proxy layer was still cached for the zone; flushed the challenge via the cache.purge API and the validation completed on retry.", "problem", "technical", False,
     [("Cloudflare DNS", "service"), ("DNS-01", "protocol"), ("universal-SSL", "service"), ("cache.purge API", "api")],
     [("cache.purge API", "DNS-01", "FIXES")],
     "which Cloudflare caching layer delayed DNS-01 validation and which API call unstuck it",
     "cloudflare dns 01 universal ssl cache purge api propagation delay"),
    # --- 43. noise ---
    ("The backup generator test at 03:00 tripped the motion-detector flood light again and three neighbours messaged the building chat before the sensor reset.", "fact", "noise", True, [], [], None, None),
    # --- 44. decision ---
    ("ACME account keys are per-environment, not shared; dev, staging, and prod each register their own account with Let's Encrypt so a rate-limit or revocation in one never cascades into the others.", "decision", "technical", False,
     [("ACME", "protocol"), ("account key", "concept"), ("Let's Encrypt", "service"), ("rate-limit", "concept")],
     [("account key", "rate-limit", "IMPROVES_ON")],
     "why does each environment hold its own ACME account key and what blast-radius property does that protect",
     "acme account key environment dev stage prod letsencrypt rate limit"),
    # --- 45. architecture ---
    ("Certificate distribution to edge nodes uses a pull-based agent that reads from HashiCorp Vault PKI; ACME-issued leaves are stored in Vault's KV v2 after issuance so the agent never talks to Let's Encrypt directly.", "architecture", "technical", False,
     [("Vault PKI", "library"), ("Vault", "tool"), ("KV v2", "library"), ("ACME", "protocol"), ("Let's Encrypt", "service")],
     [("Vault PKI", "Let's Encrypt", "COMMUNICATES_WITH")],
     "how do edge nodes receive ACME-issued certificates and why don't they talk to Let's Encrypt directly",
     "vault pki kv v2 acme letsencrypt edge pull agent distribution"),
    # --- 46. milestone ---
    ("Hit full DNSSEC coverage across every parent zone and child zone the company owns; the last legacy unsigned delegation was cut over, and DNSViz reports a clean chain from the root down to every leaf.", "milestone", "technical", False,
     [("DNSSEC", "protocol"), ("parent zone", "concept"), ("child zone", "concept"), ("DNSViz", "tool")],
     [],
     "which DNSSEC coverage milestone did the team hit and which tool confirmed the chain from the root to every leaf",
     "dnssec parent child zone full coverage dnsviz chain root leaf legacy"),
    # --- 47. reference ---
    ("The acme-dns side-project acts as a tiny dedicated authoritative DNS server for the _acme-challenge subdomain only; CNAMEing the challenge out to it isolates API-key scope from the production zone.", "reference", "technical", False,
     [("acme-dns", "tool"), ("_acme-challenge", "concept"), ("CNAME", "concept"), ("authoritative DNS", "concept")],
     [("CNAME", "acme-dns", "APPLIES_TO")],
     "which dedicated tool handles only the _acme-challenge subdomain and how does the CNAME indirection scope API keys",
     "acme dns cname challenge isolate api key production zone authoritative"),
    # --- 48. reference ---
    ("BIND 9's response-policy zone feature lets the resolver override RPZ-listed names; it's the defensive hook we use to sinkhole known malware domains without touching the public zone content.", "reference", "technical", False,
     [("BIND 9", "library"), ("response-policy zone", "pattern"), ("RPZ", "concept"), ("sinkhole", "pattern")],
     [("BIND 9", "RPZ", "USES")],
     "which BIND 9 feature does the resolver use to sinkhole malware domains and what does it leave untouched",
     "bind 9 response policy zone rpz sinkhole malware resolver override"),
    # --- 49. milestone ---
    ("Rolled out DoH endpoints on every public resolver fronted by Cloudflare Workers; query latency at the 99th percentile fell below the plain UDP baseline because of HTTP/3 and 0-RTT resumption on repeat clients.", "milestone", "technical", False,
     [("DoH", "protocol"), ("Cloudflare Workers", "service"), ("HTTP/3", "protocol"), ("0-RTT", "concept"), ("UDP", "protocol")],
     [("DoH", "UDP", "IMPROVES_ON"), ("DoH", "HTTP/3", "USES")],
     "which DoH rollout beat plain UDP on 99th-percentile latency and which two protocol features drove the win",
     "doh cloudflare workers http 3 0 rtt udp latency 99th percentile"),
    # --- 50. reference ---
    ("The CAB Forum Baseline Requirements cap publicly-trusted cert lifetimes and dictate domain validation reuse windows; every ACME CA we integrate with inherits those limits, which is why ninety-day max isn't negotiable.", "reference", "technical", False,
     [("CAB Forum", "organization"), ("Baseline Requirements", "publication"), ("ACME CA", "service"), ("domain validation", "concept")],
     [("Baseline Requirements", "ACME CA", "APPLIES_TO")],
     "which governance body sets the ninety-day cert lifetime ceiling that every ACME CA inherits",
     "cab forum baseline requirement acme ca domain validation ninety day"),
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
