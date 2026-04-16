"""One-off emitter for shared-base batch-174 — technical domain (zero-trust networking and VPN mesh: WireGuard, Tailscale, Netbird, Cloudflare Zero Trust, Teleport, Boundary, headscale, DERP, NAT traversal, ACLs, JIT access, audit).

Writes 50 rows to data/v2/shared/batch_174.tmp.jsonl with ids shared-08651..08700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_174.tmp.jsonl"
ID_OFFSET = 8650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced the legacy OpenVPN concentrator with a Tailscale tailnet for remote engineers; NAT traversal via DERP meant we stopped opening UDP 1194 on the edge firewall entirely.", "decision", "technical", False,
     [("OpenVPN", "technology"), ("Tailscale", "service"), ("DERP", "protocol"), ("UDP 1194", "config")],
     [("Tailscale", "OpenVPN", "REPLACES"), ("Tailscale", "DERP", "USES")],
     "which mesh VPN replaced the OpenVPN concentrator and how did traversal avoid inbound UDP",
     "tailscale openvpn derp nat traversal udp 1194 edge firewall mesh"),
    # --- 2 ---
    ("WireGuard sits underneath Tailscale as the data-plane crypto; the userspace wireguard-go implementation ships on macOS while kernel WireGuard handles the Linux gateway nodes.", "architecture", "technical", False,
     [("WireGuard", "protocol"), ("Tailscale", "service"), ("wireguard-go", "library"), ("macOS", "platform"), ("Linux", "platform")],
     [("Tailscale", "WireGuard", "USES"), ("wireguard-go", "WireGuard", "IMPLEMENTS")],
     "how does Tailscale split its WireGuard data plane between userspace and kernel on different platforms",
     "wireguard tailscale userspace kernel macos linux data plane"),
    # --- 3 ---
    ("Stood up headscale as the coordination server so the tailnet control plane stays in our VPC; clients still talk to upstream DERP relays for fallback but key exchange never leaves the account.", "decision", "technical", False,
     [("headscale", "service"), ("tailnet", "concept"), ("VPC", "infrastructure"), ("DERP", "protocol")],
     [("headscale", "DERP", "COMMUNICATES_WITH"), ("headscale", "VPC", "DEPLOYED_ON")],
     "which self-hosted coordinator keeps the tailnet control plane inside our VPC while retaining DERP fallback",
     "headscale tailnet coordination self host vpc derp relay control"),
    # --- 4 ---
    ("Cloudflare Access fronts every internal admin panel now; device posture from WARP plus an SSO claim from Okta gates each request, so the old allowlisted office IP range is retired.", "decision", "technical", False,
     [("Cloudflare Access", "service"), ("WARP", "service"), ("Okta", "service"), ("allowlisted office IP", "pattern")],
     [("Cloudflare Access", "WARP", "USES"), ("Cloudflare Access", "Okta", "USES"), ("Cloudflare Access", "allowlisted office IP", "REPLACES")],
     "which zero-trust front door replaced the allowlisted office IP range for internal admin panels",
     "cloudflare access warp okta device posture sso admin panel allowlist"),
    # --- 5 ---
    ("Teleport now brokers all SSH and kubectl sessions to production; the raw ~/.ssh key files got wiped from laptops and short-lived certs issued per login handle the actual auth.", "milestone", "technical", False,
     [("Teleport", "service"), ("SSH", "protocol"), ("kubectl", "tool"), ("short-lived certs", "pattern")],
     [("Teleport", "SSH", "USES"), ("Teleport", "short-lived certs", "PRODUCES")],
     "which bastion product brokers SSH and kubectl sessions and how did it retire static key files",
     "teleport ssh kubectl short lived cert bastion session broker laptop"),
    # --- 6 ---
    ("Netbird was evaluated against Tailscale and Zerotier for a customer that wanted self-hosted plus WireGuard; Netbird won because its coturn fallback gave deterministic NAT handling in carrier-NAT regions.", "decision", "technical", False,
     [("Netbird", "service"), ("Tailscale", "service"), ("Zerotier", "service"), ("coturn", "service"), ("carrier-NAT", "concept")],
     [("Netbird", "coturn", "USES"), ("Netbird", "Tailscale", "PREFERS")],
     "which self-hosted mesh VPN won over Tailscale for a carrier-NAT customer and what relay sealed it",
     "netbird tailscale zerotier coturn carrier nat self host wireguard"),
    # --- 7 ---
    ("Twingate replaced the reverse-proxy hack for contractor RDP access; a connector inside the private subnet advertises resources by FQDN without any inbound firewall rule.", "architecture", "technical", False,
     [("Twingate", "service"), ("RDP", "protocol"), ("connector", "pattern"), ("reverse-proxy hack", "pattern")],
     [("Twingate", "reverse-proxy hack", "REPLACES")],
     "how does Twingate expose contractor RDP without opening any inbound firewall rule on the private subnet",
     "twingate connector rdp contractor reverse proxy inbound firewall"),
    # --- 8 ---
    ("Adopted the BeyondCorp model across the corporate network: trust no longer derives from being on the office LAN, every request carries a signed device token plus a user identity.", "decision", "technical", False,
     [("BeyondCorp", "pattern"), ("office LAN", "infrastructure"), ("device token", "concept"), ("user identity", "concept")],
     [("BeyondCorp", "office LAN", "REPLACES")],
     "which access model replaced office LAN trust for the corporate network and what does each request carry",
     "beyondcorp office lan device token user identity zero trust adopt"),
    # --- 9 ---
    ("StrongSwan handles the site-to-site IPsec tunnel to the colo rack because the HP switch there only speaks IKEv2; WireGuard would have been simpler but the hardware is locked to IPsec.", "problem", "technical", False,
     [("StrongSwan", "service"), ("IPsec", "protocol"), ("IKEv2", "protocol"), ("WireGuard", "protocol"), ("HP switch", "infrastructure")],
     [("StrongSwan", "IKEv2", "USES"), ("StrongSwan", "HP switch", "COMMUNICATES_WITH")],
     "why does the colo rack still run StrongSwan IPsec instead of WireGuard for the site-to-site link",
     "strongswan ipsec ikev2 wireguard hp switch colo site to site"),
    # --- 10. noise ---
    ("The office plant in the corner finally flowered after eighteen months and the team named it Geoff over a weeklong Slack thread.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("ACLs in the tailnet are expressed as tag-to-tag grants: tag:ci can reach tag:build-cache on TCP 6379 and nothing else, so a rogue CI runner can't pivot into tag:prod-db.", "architecture", "technical", False,
     [("ACL", "concept"), ("tailnet", "concept"), ("tag:ci", "config"), ("tag:build-cache", "config"), ("tag:prod-db", "config"), ("TCP 6379", "config")],
     [("tag:ci", "tag:build-cache", "COMMUNICATES_WITH")],
     "how do tag-based ACLs in the tailnet keep a compromised CI runner away from the production database",
     "tailscale acl tag ci build cache prod db tcp 6379 pivot"),
    # --- 12 ---
    ("Just-in-time access through Teleport's access-request flow replaced the always-on sudoers entries; an engineer files a reason, a reviewer approves, and the role expires after four hours.", "decision", "technical", False,
     [("Teleport", "service"), ("access-request", "pattern"), ("sudoers", "config"), ("Just-in-time access", "concept")],
     [("access-request", "sudoers", "REPLACES"), ("Teleport", "Just-in-time access", "IMPLEMENTS")],
     "which Teleport flow replaced always-on sudoers entries and how long does an approved role last",
     "teleport jit access request sudoers reviewer expire four hour"),
    # --- 13 ---
    ("Session recording lands in S3 for every Teleport SSH and database session; playback is a DOM-rendered asciinema stream, so compliance audits no longer need tcpdump captures from the bastion.", "architecture", "technical", False,
     [("Teleport", "service"), ("S3", "service"), ("asciinema", "tool"), ("tcpdump", "tool"), ("bastion", "pattern")],
     [("Teleport", "S3", "USES"), ("Teleport", "asciinema", "PRODUCES")],
     "which session-recording stack does Teleport use and what audit tool does it retire",
     "teleport session record s3 asciinema tcpdump bastion playback dom"),
    # --- 14 ---
    ("AWS SSM Session Manager is now the only path to EC2 shells; the Internet-facing bastion host was decommissioned and the security group no longer allows port 22 from anywhere.", "milestone", "technical", False,
     [("AWS SSM Session Manager", "service"), ("EC2", "service"), ("bastion host", "pattern"), ("port 22", "config")],
     [("AWS SSM Session Manager", "bastion host", "REPLACES"), ("AWS SSM Session Manager", "EC2", "APPLIES_TO")],
     "which AWS feature replaced the Internet-facing bastion and what port did the security group drop",
     "aws ssm session manager ec2 bastion port 22 security group decommission"),
    # --- 15 ---
    ("Google Identity-Aware Proxy fronts the internal Looker instance; context-aware access checks the device has ChromeOS verified boot before issuing the IAP cookie.", "decision", "technical", False,
     [("Google Identity-Aware Proxy", "service"), ("Looker", "service"), ("ChromeOS", "platform"), ("verified boot", "concept")],
     [("Google Identity-Aware Proxy", "Looker", "APPLIES_TO"), ("Google Identity-Aware Proxy", "ChromeOS", "USES")],
     "which Google proxy gates Looker and what device-posture signal does it check before issuing the cookie",
     "google iap identity aware proxy looker chromeos verified boot"),
    # --- 16 ---
    ("DERP relays carry peer traffic when direct UDP hole punching fails; roughly eight percent of sessions in mobile-heavy regions stay relayed end-to-end per the Tailscale admin dashboard.", "fact", "technical", False,
     [("DERP", "protocol"), ("UDP hole punching", "method"), ("Tailscale", "service")],
     [("Tailscale", "DERP", "USES")],
     "what fraction of Tailscale sessions fall back to DERP relays in mobile-heavy regions",
     "derp relay udp hole punch tailscale mobile percent session relay"),
    # --- 17 ---
    ("STUN discovery runs on every Netbird agent at startup to classify the NAT type; symmetric NATs drop to the TURN fallback immediately rather than wasting a hole-punch round trip.", "architecture", "technical", False,
     [("STUN", "protocol"), ("Netbird", "service"), ("NAT", "concept"), ("TURN", "protocol"), ("symmetric NAT", "concept")],
     [("Netbird", "STUN", "USES"), ("Netbird", "TURN", "USES")],
     "how does the Netbird agent classify NAT type at startup and what fallback does symmetric NAT trigger",
     "stun netbird nat turn symmetric hole punch agent startup classify"),
    # --- 18 ---
    ("Split-horizon DNS over the tailnet serves internal.example.com to connected devices and NXDOMAIN to the public internet; the MagicDNS resolver rewrites queries to the tailnet authoritative zone.", "architecture", "technical", False,
     [("Split-horizon DNS", "concept"), ("tailnet", "concept"), ("MagicDNS", "service"), ("NXDOMAIN", "concept")],
     [("MagicDNS", "Split-horizon DNS", "IMPLEMENTS")],
     "which DNS resolver gives tailnet clients internal hostnames while public queries see NXDOMAIN",
     "split horizon dns magicdns tailnet nxdomain internal zone resolver"),
    # --- 19 ---
    ("mTLS-everywhere is enforced at the service mesh layer via Istio; sidecars inject SPIFFE identities and any pod without a valid SVID is rejected at the Envoy proxy in front of it.", "architecture", "technical", False,
     [("mTLS", "protocol"), ("Istio", "framework"), ("SPIFFE", "protocol"), ("SVID", "concept"), ("Envoy", "service")],
     [("Istio", "mTLS", "IMPLEMENTS"), ("Envoy", "SPIFFE", "USES")],
     "how does Istio enforce mTLS across the mesh and what identity format do sidecars present",
     "istio mtls spiffe svid envoy sidecar pod mesh identity enforce"),
    # --- 20 ---
    ("HashiCorp Boundary fronts the Postgres and Redis targets for the on-call crew; dynamic host catalogs read from Consul so newly registered replicas show up without editing a static target list.", "decision", "technical", False,
     [("HashiCorp Boundary", "service"), ("Postgres", "database"), ("Redis", "database"), ("Consul", "service"), ("dynamic host catalog", "pattern")],
     [("HashiCorp Boundary", "Consul", "USES"), ("HashiCorp Boundary", "dynamic host catalog", "IMPLEMENTS")],
     "which access broker fronts Postgres and Redis and how does it pick up newly registered replicas",
     "boundary postgres redis consul dynamic host catalog on call replica"),
    # --- 21 ---
    ("Audit logs from every Teleport session stream into Loki via Promtail; a Grafana dashboard panels them by actor, target, and command so the security team stops exporting CSVs weekly.", "fact", "technical", False,
     [("Teleport", "service"), ("Loki", "service"), ("Promtail", "tool"), ("Grafana", "service")],
     [("Teleport", "Loki", "COMMUNICATES_WITH"), ("Promtail", "Loki", "COMMUNICATES_WITH"), ("Grafana", "Loki", "USES")],
     "which logging pipeline moves Teleport audit events into Grafana dashboards for the security team",
     "teleport audit log loki promtail grafana dashboard actor target"),
    # --- 22 ---
    ("Zerotier's global earth controller was dropped in favour of a self-hosted controller after a surprise outage knocked our backup mesh offline for forty minutes during a cutover window.", "decision", "technical", False,
     [("Zerotier", "service"), ("global earth controller", "service"), ("self-hosted controller", "pattern")],
     [("self-hosted controller", "global earth controller", "REPLACES")],
     "which Zerotier control-plane change followed the forty-minute backup-mesh outage during cutover",
     "zerotier earth controller self host outage backup mesh cutover"),
    # --- 23 ---
    ("SoftEther survives on one Windows Server 2019 box because a legacy vendor portal only speaks SSTP; migration is blocked until the vendor ships a certificate-based SDK later this year.", "problem", "technical", False,
     [("SoftEther", "service"), ("Windows Server 2019", "platform"), ("SSTP", "protocol")],
     [("SoftEther", "SSTP", "USES"), ("SoftEther", "Windows Server 2019", "DEPLOYED_ON")],
     "why does one SoftEther install linger on Windows Server 2019 and what blocks its retirement",
     "softether windows server 2019 sstp legacy vendor certificate sdk"),
    # --- 24 ---
    ("Cloudflare WARP client pushes device-posture signals like disk encryption and OS patch level back to Cloudflare Zero Trust; a failing signal triggers a step-up MFA challenge before any allow.", "fact", "technical", False,
     [("Cloudflare WARP", "service"), ("Cloudflare Zero Trust", "service"), ("device-posture", "concept"), ("step-up MFA", "pattern")],
     [("Cloudflare WARP", "Cloudflare Zero Trust", "COMMUNICATES_WITH"), ("Cloudflare Zero Trust", "step-up MFA", "USES")],
     "what posture signals does WARP send to Zero Trust and what does a failing signal trigger",
     "cloudflare warp zero trust device posture disk encryption patch mfa"),
    # --- 25 ---
    ("The mesh routing table on the Tailscale exit node advertises 10.50.0.0/16 for the colo rack; subnet routes are enabled via --advertise-routes and the approver is a named operator in ACLs.", "fact", "technical", False,
     [("Tailscale", "service"), ("exit node", "pattern"), ("10.50.0.0/16", "config"), ("--advertise-routes", "command"), ("ACL", "concept")],
     [("Tailscale", "exit node", "USES")],
     "which subnet does the Tailscale exit node advertise for the colo and who approves it in ACLs",
     "tailscale exit node advertise route colo subnet acl operator approve"),
    # --- 26 ---
    ("Service tagging pushes security metadata into Consul: tag service:payments restricts intent-based traffic so only service:checkout can dial it on the mesh gateway.", "architecture", "technical", False,
     [("Consul", "service"), ("service:payments", "config"), ("service:checkout", "config"), ("mesh gateway", "pattern"), ("intent", "concept")],
     [("Consul", "intent", "USES"), ("service:checkout", "service:payments", "COMMUNICATES_WITH")],
     "how does Consul tag-based intent restrict traffic between payments and checkout on the mesh gateway",
     "consul service tag payments checkout intent mesh gateway restrict"),
    # --- 27 ---
    ("SSH bastions were consolidated from seven per-environment jump boxes into one Teleport proxy pool; cost dropped, but the real win was killing the shared SSH key that had rotated once in three years.", "milestone", "technical", False,
     [("SSH bastion", "pattern"), ("Teleport proxy pool", "pattern"), ("shared SSH key", "pattern")],
     [("Teleport proxy pool", "SSH bastion", "REPLACES"), ("Teleport proxy pool", "shared SSH key", "REPLACES")],
     "which consolidation retired seven jump boxes and what stale shared credential did it finally kill",
     "teleport bastion jump box consolidation shared ssh key rotate"),
    # --- 28 ---
    ("A DERP relay was added in Singapore after p95 latency for APAC engineers hit 240 ms; the new relay dropped median round-trip to 38 ms within the first week of rollout.", "milestone", "technical", False,
     [("DERP", "protocol"), ("Singapore", "place"), ("APAC", "place"), ("latency", "concept")],
     [("DERP", "Singapore", "DEPLOYED_ON")],
     "where was a new DERP relay placed to reduce APAC p95 latency and what median did it reach",
     "derp relay singapore apac latency p95 median drop round trip"),
    # --- 29 ---
    ("UDP hole punching failed consistently from one partner's hotel-grade carrier NAT; a dedicated TURN relay in Frankfurt behind Netbird fixed the last-mile connectivity for their travelling sales team.", "problem", "technical", False,
     [("UDP hole punching", "method"), ("carrier NAT", "concept"), ("TURN", "protocol"), ("Frankfurt", "place"), ("Netbird", "service")],
     [("TURN", "UDP hole punching", "REPLACES"), ("Netbird", "TURN", "USES")],
     "which relay in Frankfurt rescued a partner whose carrier NAT blocked UDP hole punching",
     "udp hole punch carrier nat turn frankfurt netbird hotel travelling"),
    # --- 30 ---
    ("Runbook entry: rotate the headscale PreAuthKey quarterly and revoke old nodes; stale keys have indefinite lifetime unless explicitly expired and were the root cause of the ghost-node incident.", "reference", "technical", False,
     [("headscale", "service"), ("PreAuthKey", "config"), ("ghost-node incident", "event")],
     [("PreAuthKey", "ghost-node incident", "CAUSES")],
     "what quarterly rotation does the runbook require for headscale keys and which incident drove it",
     "headscale preauth key rotate revoke ghost node quarterly runbook"),
    # --- 31 ---
    ("Reference: the WireGuard handshake is Noise_IK, using Curve25519 for DH, ChaCha20-Poly1305 for AEAD, and BLAKE2s for hashing; Perfect Forward Secrecy is provided per session.", "reference", "technical", False,
     [("WireGuard", "protocol"), ("Noise_IK", "method"), ("Curve25519", "algorithm"), ("ChaCha20-Poly1305", "algorithm"), ("BLAKE2s", "algorithm")],
     [("WireGuard", "Noise_IK", "IMPLEMENTS"), ("Noise_IK", "Curve25519", "USES"), ("Noise_IK", "ChaCha20-Poly1305", "USES")],
     "which cryptographic primitives make up the WireGuard handshake and what property does it guarantee",
     "wireguard noise ik curve25519 chacha20 poly1305 blake2s pfs handshake"),
    # --- 32 ---
    ("Prefer headscale over the hosted Tailscale control plane for regulated customers where the coordination server must live in-region; everything else stays on the managed offering for simplicity.", "preference", "technical", False,
     [("headscale", "service"), ("Tailscale", "service"), ("coordination server", "concept")],
     [("headscale", "Tailscale", "PREFERS")],
     "when do we prefer headscale over the hosted Tailscale control plane and what drives the choice",
     "headscale tailscale prefer regulated region coordination server host"),
    # --- 33 ---
    ("Preference: always issue short-lived certs via Teleport rather than provisioning IAM users for humans; bots keep their IAM roles but people go through the cert-broker path.", "preference", "technical", False,
     [("Teleport", "service"), ("short-lived certs", "pattern"), ("IAM user", "concept"), ("IAM role", "concept")],
     [("short-lived certs", "IAM user", "PREFERS")],
     "how do we prefer to grant human access compared to IAM users and where do bots still live",
     "teleport short lived cert iam user role bot human prefer broker"),
    # --- 34 ---
    ("Prefer WireGuard over IPsec for all new site-to-site links unless a vendor box forces IKEv2; fewer tunables, smaller attack surface, and the config files are auditable in git.", "preference", "technical", False,
     [("WireGuard", "protocol"), ("IPsec", "protocol"), ("IKEv2", "protocol"), ("git", "tool")],
     [("WireGuard", "IPsec", "PREFERS")],
     "when do we pick WireGuard over IPsec for new site-to-site links and what operational wins drive it",
     "wireguard ipsec ikev2 prefer site tunable attack surface git"),
    # --- 35 ---
    ("Preference: route CI runner egress through a single Cloudflare Zero Trust tunnel so outbound connections to third-party APIs carry a stable identity instead of rotating NAT addresses.", "preference", "technical", False,
     [("CI runner", "service"), ("Cloudflare Zero Trust", "service"), ("tunnel", "pattern"), ("third-party APIs", "concept")],
     [("CI runner", "Cloudflare Zero Trust", "USES")],
     "how do we prefer to egress CI runner traffic so third-party APIs see a stable identity",
     "ci runner cloudflare zero trust tunnel egress third party api identity"),
    # --- 36 ---
    ("Reference: BeyondCorp's three access-tier model maps untrusted, basic, and privileged tiers to device-trust levels; the highest tier requires a managed laptop plus a hardware security key.", "reference", "technical", False,
     [("BeyondCorp", "pattern"), ("access-tier model", "concept"), ("managed laptop", "concept"), ("hardware security key", "concept")],
     [("BeyondCorp", "access-tier model", "IMPLEMENTS")],
     "which tiered model does BeyondCorp prescribe and what is required for the top privileged tier",
     "beyondcorp access tier untrusted basic privileged managed laptop key"),
    # --- 37 ---
    ("Reference docs: Teleport documents the certificate TTL for SSH as 1h default with a 12h cap for regular users; Machine ID certs default to 20m and renew via the tbot agent.", "reference", "technical", False,
     [("Teleport", "service"), ("SSH", "protocol"), ("Machine ID", "service"), ("tbot", "tool")],
     [("Machine ID", "tbot", "USES")],
     "what certificate TTL defaults does Teleport document for users versus the Machine ID path",
     "teleport ssh cert ttl machine id tbot renew default cap user"),
    # --- 38 ---
    ("Reference note: Cloudflare Zero Trust distinguishes Access for HTTP-only apps and Tunnel for TCP/UDP origins; gotchas include cookie size limits when chaining multiple Access apps.", "reference", "technical", False,
     [("Cloudflare Zero Trust", "service"), ("Access", "service"), ("Tunnel", "service"), ("cookie", "concept")],
     [("Cloudflare Zero Trust", "Access", "HAS_PART"), ("Cloudflare Zero Trust", "Tunnel", "HAS_PART")],
     "how does Cloudflare Zero Trust split Access from Tunnel and what cookie gotcha matters when chaining",
     "cloudflare zero trust access tunnel http tcp udp cookie chain limit"),
    # --- 39 ---
    ("Fact: Netbird's management server runs as a single Go binary with a Postgres backend; the REST API at /api/peers drives both the web UI and the netbird CLI.", "fact", "technical", False,
     [("Netbird", "service"), ("Go", "language"), ("Postgres", "database"), ("/api/peers", "api"), ("netbird CLI", "tool")],
     [("Netbird", "Postgres", "USES"), ("netbird CLI", "/api/peers", "USES")],
     "how is the Netbird management server implemented and which REST endpoint backs its UI and CLI",
     "netbird go postgres api peers cli management server rest backend"),
    # --- 40 ---
    ("Twingate connectors phone home over an outbound gRPC channel; no inbound firewall rules are needed, which is exactly why it survived the security review the reverse-proxy box failed.", "fact", "technical", False,
     [("Twingate", "service"), ("connector", "pattern"), ("gRPC", "protocol"), ("reverse-proxy box", "pattern")],
     [("Twingate", "gRPC", "USES"), ("Twingate", "reverse-proxy box", "REPLACES")],
     "what outbound protocol does the Twingate connector use and which predecessor failed the security review",
     "twingate connector grpc outbound inbound firewall reverse proxy review"),
    # --- 41 ---
    ("Milestone: rolled out device-posture checks to 100 percent of employee laptops via Cloudflare WARP this quarter; unpatched boxes now see a captive-portal style remediation page.", "milestone", "technical", False,
     [("device-posture", "concept"), ("Cloudflare WARP", "service"), ("laptop", "infrastructure"), ("captive-portal", "pattern")],
     [("Cloudflare WARP", "device-posture", "IMPLEMENTS")],
     "which rollout hit 100 percent of employee laptops this quarter and what do unpatched boxes now see",
     "warp device posture laptop captive portal remediation quarter rollout"),
    # --- 42 ---
    ("Milestone: retired the last OpenVPN endpoint in the datacenter after a three-month parallel run with Tailscale subnet routes; no outage was reported during the cutover weekend.", "milestone", "technical", False,
     [("OpenVPN", "technology"), ("Tailscale", "service"), ("subnet routes", "pattern"), ("datacenter", "infrastructure")],
     [("Tailscale", "OpenVPN", "REPLACES"), ("Tailscale", "subnet routes", "USES")],
     "what migration endpoint did the datacenter retire after three months of parallel running Tailscale",
     "openvpn tailscale subnet route datacenter retire parallel cutover"),
    # --- 43. noise ---
    ("The coffee machine in the kitchen started demanding descaling every morning and nobody wants to be the one holding the vinegar bottle.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Milestone: migrated all prod SSH from IP-allowlisted keys to Teleport certs; post-migration the SSH lateral-movement detections in the SIEM dropped by 83 percent week-over-week.", "milestone", "technical", False,
     [("SSH", "protocol"), ("Teleport", "service"), ("SIEM", "service"), ("lateral-movement", "concept")],
     [("Teleport", "SSH", "REPLACES")],
     "which migration cut SIEM lateral-movement detections by 83 percent the following week",
     "ssh teleport cert siem lateral movement detect migration allowlist"),
    # --- 45 ---
    ("Fact: Boundary stores session state in Postgres and uses KMS-wrapped root keys for worker auth; misconfiguring the KMS ARN produces a startup error visible in the worker logs.", "fact", "technical", False,
     [("Boundary", "service"), ("Postgres", "database"), ("KMS", "service"), ("worker", "service")],
     [("Boundary", "Postgres", "USES"), ("Boundary", "KMS", "USES")],
     "which stores does Boundary use for session state and worker auth and how does a bad KMS ARN surface",
     "boundary postgres kms root key worker session state arn start error"),
    # --- 46 ---
    ("Reference: a Tailscale subnet router kept being auto-killed by systemd-oomd under memory pressure during nightly backups; carved out a dedicated slice with MemoryHigh=2G and the flaps stopped.", "reference", "technical", False,
     [("Tailscale", "service"), ("subnet router", "pattern"), ("systemd-oomd", "service"), ("MemoryHigh=2G", "config")],
     [("MemoryHigh=2G", "systemd-oomd", "FIXES")],
     "which systemd knob stopped the Tailscale subnet router from getting killed during nightly backups",
     "tailscale subnet router systemd oomd memoryhigh slice backup kill"),
    # --- 47 ---
    ("Architecture: Teleport's Machine ID issues certs to build agents via tbot, which writes them to a tmpfs destination; no long-lived secret ever touches the agent's disk in the pipeline.", "architecture", "technical", False,
     [("Teleport", "service"), ("Machine ID", "service"), ("tbot", "tool"), ("tmpfs", "concept"), ("build agent", "service")],
     [("Machine ID", "tbot", "USES"), ("tbot", "tmpfs", "USES")],
     "what broker keeps pipeline credentials off agent disks and in memory only via tmpfs",
     "teleport machine id tbot tmpfs build agent pipeline cert secret"),
    # --- 48 ---
    ("Decision: pick Tailscale SSH over a third Teleport deployment for the small internal-tools cluster; the five engineers that touch it don't need session recording or RBAC that deep.", "decision", "technical", False,
     [("Tailscale SSH", "service"), ("Teleport", "service"), ("RBAC", "concept"), ("session recording", "concept")],
     [("Tailscale SSH", "Teleport", "PREFERS")],
     "why does the internal-tools cluster pick Tailscale SSH over another Teleport deployment",
     "tailscale ssh teleport internal tool cluster session recording rbac"),
    # --- 49 ---
    ("Decision: route every admin-tier API behind Google Identity-Aware Proxy with BeyondCorp Enterprise context rules; alternatives like Cloudflare Access were close but the GCP-native SSO was already wired up.", "decision", "technical", False,
     [("Google Identity-Aware Proxy", "service"), ("BeyondCorp Enterprise", "service"), ("Cloudflare Access", "service"), ("admin-tier API", "api")],
     [("admin-tier API", "Google Identity-Aware Proxy", "USES"), ("Google Identity-Aware Proxy", "Cloudflare Access", "PREFERS")],
     "which proxy ended up fronting the admin-tier APIs and which alternative lost on integration cost",
     "iap beyondcorp enterprise cloudflare access admin api gcp sso"),
    # --- 50 ---
    ("Architecture: the zero-trust audit pipeline fans Teleport, Boundary, and Cloudflare Access logs into a single OpenSearch index partitioned by principal, so investigators query one place instead of three consoles.", "decision", "technical", False,
     [("Teleport", "service"), ("Boundary", "service"), ("Cloudflare Access", "service"), ("OpenSearch", "database"), ("principal", "concept")],
     [("Teleport", "OpenSearch", "COMMUNICATES_WITH"), ("Boundary", "OpenSearch", "COMMUNICATES_WITH"), ("Cloudflare Access", "OpenSearch", "COMMUNICATES_WITH")],
     "which single index do Teleport, Boundary, and Cloudflare Access logs land in for investigators",
     "teleport boundary cloudflare access opensearch audit index principal"),
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
