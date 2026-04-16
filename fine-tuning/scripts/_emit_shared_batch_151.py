"""One-off emitter for shared-base batch-151 — technical domain (networking protocols and transports: BGP, OSPF, QUIC, MPLS, VXLAN, EVPN, WireGuard, SRv6 and friends).

Writes 50 rows to data/v2/shared/batch_151.tmp.jsonl with ids shared-07501..07550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_151.tmp.jsonl"
ID_OFFSET = 7500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Picked BGP over OSPF for the WAN edge because administrative boundaries between the two AS numbers needed policy control that link-state simply does not express cleanly.", "decision", "technical", False,
     [("BGP", "protocol"), ("OSPF", "protocol"), ("WAN", "infrastructure")],
     [("BGP", "OSPF", "PREFERS"), ("BGP", "WAN", "APPLIES_TO")],
     "which exterior routing protocol won over OSPF for the WAN edge and why did policy control drive the call",
     "bgp ospf wan edge as policy link state exterior"),
    # --- 2 ---
    ("EIGRP stayed in the lab network only; the wider fabric moved to IS-IS years ago because multi-topology and IPv6 parity made the operational story cleaner across vendors.", "decision", "technical", False,
     [("EIGRP", "protocol"), ("IS-IS", "protocol"), ("IPv6", "protocol")],
     [("IS-IS", "EIGRP", "REPLACES"), ("IS-IS", "IPv6", "SUPPORTS")],
     "which IGP replaced EIGRP on the main fabric and what IPv6 story sealed the choice",
     "is-is eigrp igp fabric ipv6 multi topology vendor"),
    # --- 3 ---
    ("The data-centre underlay runs IS-IS with wide metrics and SRv6 segment-routing on top; MPLS-LDP got retired because the dual control plane was costing us operational hours every week.", "architecture", "technical", False,
     [("IS-IS", "protocol"), ("SRv6", "protocol"), ("MPLS-LDP", "protocol")],
     [("SRv6", "MPLS-LDP", "REPLACES"), ("SRv6", "IS-IS", "DEPENDS_ON")],
     "which segment-routing stack replaced MPLS-LDP on the data-centre underlay and which IGP supports it",
     "srv6 mpls ldp is-is underlay segment routing wide metric"),
    # --- 4 ---
    ("VXLAN with EVPN control plane is the overlay across all three pods; head-end replication was disabled in favour of multicast underlay once PIM-SM went stable in the spine layer.", "architecture", "technical", False,
     [("VXLAN", "protocol"), ("EVPN", "protocol"), ("PIM-SM", "protocol"), ("head-end replication", "pattern")],
     [("VXLAN", "EVPN", "USES"), ("PIM-SM", "head-end replication", "REPLACES")],
     "which overlay and control plane combination spans the three pods and what took over from head-end replication",
     "vxlan evpn overlay pim sm spine multicast head end"),
    # --- 5 ---
    ("Migrated the public API endpoints to HTTP/3 over QUIC; the 0-RTT resumption and head-of-line blocking fix shaved real latency off mobile sessions on high-loss LTE paths.", "milestone", "technical", False,
     [("HTTP/3", "protocol"), ("QUIC", "protocol"), ("LTE", "technology")],
     [("HTTP/3", "QUIC", "USES"), ("QUIC", "LTE", "APPLIES_TO")],
     "which transport upgrade did the public API land and which mobile scenario gained the most from it",
     "http3 quic 0-rtt mobile lte api head of line"),
    # --- 6 ---
    ("TCP congestion control is BBR v2 on the edge load balancers; CUBIC was still acceptable on LAN paths but BBR's bandwidth estimate beat it on bufferbloated last miles.", "decision", "technical", False,
     [("BBR", "algorithm"), ("CUBIC", "algorithm"), ("TCP", "protocol")],
     [("BBR", "CUBIC", "REPLACES"), ("BBR", "TCP", "APPLIES_TO")],
     "which TCP congestion algorithm replaced CUBIC on edge load balancers and what last-mile signal drove the change",
     "bbr cubic tcp edge load balancer bufferbloat last mile"),
    # --- 7 ---
    ("SCTP came back into the stack for the signalling gateway because multi-homing and message boundaries dropped a layer of glue code that had been re-implementing both over TCP.", "decision", "technical", False,
     [("SCTP", "protocol"), ("TCP", "protocol"), ("signalling gateway", "service")],
     [("SCTP", "TCP", "REPLACES"), ("SCTP", "signalling gateway", "APPLIES_TO")],
     "which transport replaced TCP for the signalling gateway and which two SCTP features eliminated glue code",
     "sctp tcp signalling multi homing message boundary gateway"),
    # --- 8 ---
    ("DCCP shows up nowhere in production; evaluated it for unreliable media transport but QUIC datagrams already covered the use case without a separate kernel socket family to operate.", "fact", "technical", False,
     [("DCCP", "protocol"), ("QUIC", "protocol")],
     [("QUIC", "DCCP", "REPLACES")],
     "why did DCCP never reach production for unreliable media and which QUIC feature absorbed the use case",
     "dccp quic datagram unreliable media kernel socket"),
    # --- 9 ---
    ("WireGuard replaced the old IPSec IKEv2 site-to-site tunnels between the two regions; key-rotation scripting shrank and the cryptokey routing model made ACL tracing radically simpler.", "decision", "technical", False,
     [("WireGuard", "protocol"), ("IPSec", "protocol"), ("IKEv2", "protocol")],
     [("WireGuard", "IPSec", "REPLACES"), ("WireGuard", "IKEv2", "REPLACES")],
     "which VPN protocol replaced IPSec IKEv2 between the regions and what operational wins followed",
     "wireguard ipsec ikev2 vpn tunnel cryptokey routing"),
    # --- 10. noise ---
    ("A box of office plants outgrew the sill above reception and someone added a second row of pots on a salvaged library ladder.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Tailscale handles the remote-developer mesh; it sits on top of WireGuard and the coordination server handles NAT traversal without us running a STUN or TURN deployment of our own.", "architecture", "technical", False,
     [("Tailscale", "service"), ("WireGuard", "protocol"), ("STUN", "protocol"), ("TURN", "protocol")],
     [("Tailscale", "WireGuard", "USES"), ("Tailscale", "STUN", "REPLACES")],
     "which mesh VPN covers remote developers and which NAT-traversal servers did it let us retire",
     "tailscale wireguard mesh stun turn nat traversal developer"),
    # --- 12 ---
    ("OpenVPN survives only on the legacy contractor gateway; new users get onboarded into the WireGuard mesh and the box is flagged for decommission before the next budget cycle closes.", "fact", "technical", False,
     [("OpenVPN", "protocol"), ("WireGuard", "protocol"), ("contractor gateway", "service")],
     [("WireGuard", "OpenVPN", "REPLACES")],
     "where does OpenVPN still run in the estate and what is the decommission path for the contractor gateway",
     "openvpn wireguard contractor gateway legacy decommission"),
    # --- 13 ---
    ("BGP community 65000:666 blackholes a prefix at the transit edge during a DDoS; the community value is documented in the transit-provider playbook and propagates no-export outbound.", "reference", "technical", False,
     [("BGP", "protocol"), ("65000:666", "config"), ("no-export", "config")],
     [("BGP", "65000:666", "CONFIGURES")],
     "which BGP community blackholes a prefix at the transit edge during a DDoS event",
     "bgp community blackhole ddos transit no-export 65000 666"),
    # --- 14 ---
    ("Path MTU discovery stopped working across one peer because ICMP Fragmentation Needed was filtered on their side; pinned TCP MSS clamp to 1360 on the tunnel interface as the workaround.", "decision", "technical", False,
     [("Path MTU discovery", "concept"), ("ICMP Fragmentation Needed", "protocol"), ("TCP MSS", "concept"), ("1360", "config")],
     [("TCP MSS", "Path MTU discovery", "REPLACES")],
     "which PMTUD failure forced an MSS clamp to 1360 on the tunnel interface and what upstream filter caused it",
     "pmtud icmp fragmentation needed mss clamp 1360 tunnel"),
    # --- 15 ---
    ("Jumbo frames at 9000 bytes run between the storage nodes and the TOR switches only; anywhere the path crosses the campus core MTU drops back to 1500 because the WAN edge cannot pass them.", "fact", "technical", False,
     [("Jumbo frames", "concept"), ("9000", "config"), ("1500", "config"), ("TOR", "infrastructure"), ("WAN", "infrastructure")],
     [("Jumbo frames", "TOR", "APPLIES_TO")],
     "where do 9000-byte jumbo frames run and where does MTU fall back to 1500 on the path",
     "jumbo frame 9000 mtu tor storage campus core wan"),
    # --- 16 ---
    ("Anycast for the public resolver ships the same /24 from four sites with equal BGP path attributes; inbound traffic engineering is done with AS-path prepending on the two backup sites.", "architecture", "technical", False,
     [("Anycast", "concept"), ("BGP", "protocol"), ("AS-path prepending", "pattern")],
     [("Anycast", "BGP", "USES"), ("AS-path prepending", "BGP", "CONFIGURES")],
     "how does the public resolver spread load across sites and which BGP knob steers traffic to the primary pair",
     "anycast bgp /24 as-path prepend resolver site"),
    # --- 17 ---
    ("ECMP hashing on the leaf switches is set to symmetric 5-tuple; an asymmetric hash used to break return paths for long-lived TCP flows through the stateful firewall cluster.", "decision", "technical", False,
     [("ECMP", "algorithm"), ("5-tuple", "concept"), ("asymmetric hash", "pattern"), ("stateful firewall", "infrastructure")],
     [("5-tuple", "asymmetric hash", "REPLACES")],
     "what hash tweak on the leaves cured reverse-path breaks for persistent sessions traversing firewall state",
     "ecmp symmetric 5-tuple asymmetric firewall return path"),
    # --- 18 ---
    ("LACP bundles between the spines and each leaf run in active mode with a 30-second slow rate; fast rate caused false-positive flaps during control-plane CPU spikes on one vendor's box.", "decision", "technical", False,
     [("LACP", "protocol"), ("30-second", "config"), ("slow rate", "config"), ("fast rate", "config")],
     [("slow rate", "fast rate", "REPLACES")],
     "which LACP rate setting runs between the spines and leaves and what flap caused the swap from fast",
     "lacp active slow rate 30 second flap cpu spine leaf"),
    # --- 19 ---
    ("LLDP is enabled globally on every switch and feeds the cabling inventory; CDP was disabled on all non-Cisco ports after a pair of vendor bugs leaked neighbour data into the wrong VLAN.", "decision", "technical", False,
     [("LLDP", "protocol"), ("CDP", "protocol"), ("VLAN", "protocol")],
     [("LLDP", "CDP", "REPLACES")],
     "which neighbour-discovery protocol runs globally on switches and which proprietary alternative got disabled",
     "lldp cdp neighbour discovery vlan cabling inventory"),
    # --- 20 ---
    ("VLAN 4094 is reserved for the out-of-band management network; nothing on that VLAN is reachable from the production address space and the span-session mirror targets live there by policy.", "reference", "technical", False,
     [("VLAN 4094", "config"), ("out-of-band", "infrastructure"), ("span-session", "concept")],
     [("VLAN 4094", "out-of-band", "APPLIES_TO")],
     "which VLAN holds the out-of-band management network and what other traffic sits on it by policy",
     "vlan 4094 out of band management span mirror reserved"),
    # --- 21 ---
    ("IPv6 is dual-stack on every external service; NAT64 with DNS64 handles the IPv6-only client mobile segment when it hits an IPv4-literal third-party endpoint that still has not shipped AAAA.", "architecture", "technical", False,
     [("IPv6", "protocol"), ("NAT64", "protocol"), ("DNS64", "protocol"), ("AAAA", "config")],
     [("NAT64", "IPv6", "SUPPORTS"), ("NAT64", "DNS64", "DEPENDS_ON")],
     "how do IPv6-only mobile clients reach IPv4-literal third parties that lack AAAA records",
     "ipv6 nat64 dns64 dual stack aaaa mobile client"),
    # --- 22 ---
    ("CGNAT on the residential ISP aggregates subscribers behind 100.64.0.0/10; port-block allocation runs 2048 ports per subscriber and the logging sink writes one record per block, not per flow.", "fact", "technical", False,
     [("CGNAT", "protocol"), ("100.64.0.0/10", "config"), ("port-block allocation", "pattern"), ("2048", "config")],
     [("CGNAT", "100.64.0.0/10", "USES")],
     "which shared address range and port-block size does the residential ISP use for CGNAT logging",
     "cgnat 100.64 port block 2048 subscriber log"),
    # --- 23 ---
    ("IPSec tunnels between the two on-prem DCs run IKEv2 with AES-GCM-256 and PFS group 19; dead-peer-detection at ten seconds recovers within a BGP hold-down without route churn.", "reference", "technical", False,
     [("IPSec", "protocol"), ("IKEv2", "protocol"), ("AES-GCM-256", "algorithm"), ("PFS group 19", "config"), ("BGP", "protocol")],
     [("IPSec", "IKEv2", "USES"), ("IPSec", "AES-GCM-256", "USES")],
     "which IKEv2 cipher and PFS group run on the inter-DC IPSec tunnels and how fast does DPD recover",
     "ipsec ikev2 aes gcm 256 pfs 19 dpd bgp hold"),
    # --- 24 ---
    ("MPLS-TE tunnels with fast-reroute protect every long-haul link on the backbone; the bypass path is precomputed per node and failover finishes inside fifty milliseconds on a cut fibre.", "architecture", "technical", False,
     [("MPLS-TE", "protocol"), ("fast-reroute", "pattern"), ("fifty milliseconds", "config")],
     [("MPLS-TE", "fast-reroute", "USES")],
     "which MPLS protection mechanism covers backbone links and what failover budget does it meet on a fibre cut",
     "mpls te fast reroute bypass 50 ms fibre long haul"),
    # --- 25 ---
    ("Upgraded the EVPN fabric to Type-5 routes so prefix advertisement decouples from MAC/IP; east-west inter-subnet routing now happens in the fabric rather than hairpinning through a core firewall.", "milestone", "technical", False,
     [("EVPN", "protocol"), ("Type-5", "config"), ("east-west", "concept")],
     [("EVPN", "Type-5", "USES")],
     "which EVPN route type upgrade pulled east-west inter-subnet routing back into the fabric",
     "evpn type 5 east west inter subnet fabric hairpin"),
    # --- 26 ---
    ("The SRv6 uSID compression is in use on the core; full 128-bit SIDs bloated the header to the point that TCP timestamps no longer fit under the default MTU on legacy transit segments.", "problem", "technical", False,
     [("SRv6", "protocol"), ("uSID", "pattern"), ("TCP timestamps", "concept"), ("MTU", "concept")],
     [("uSID", "SRv6", "APPLIES_TO")],
     "which SRv6 compression variant runs on the core and which MTU interaction drove the switch from full SIDs",
     "srv6 usid sid compression tcp timestamp mtu core"),
    # --- 27 ---
    ("MLD snooping is on at the TOR layer so IPv6 multicast does not flood to every access port; video distribution inside the DC depends on this and the neighbour-solicitation storm problem went away.", "fact", "technical", False,
     [("MLD snooping", "protocol"), ("IPv6", "protocol"), ("TOR", "infrastructure"), ("neighbour-solicitation", "concept")],
     [("MLD snooping", "IPv6", "SUPPORTS")],
     "which snooping feature runs at the TOR for IPv6 multicast and which storm pattern did it silence",
     "mld snooping ipv6 multicast tor neighbour solicitation storm"),
    # --- 28 ---
    ("ARP storm on VLAN 102 traced back to a loop between two access ports that STP BPDU-guard was disabled on; BPDU-guard is now enforced everywhere via a config template, not per-port knobs.", "decision", "technical", False,
     [("ARP", "protocol"), ("VLAN 102", "config"), ("STP", "protocol"), ("BPDU-guard", "config")],
     [("BPDU-guard", "ARP", "FIXES")],
     "which STP feature was missing on the access ports that caused the VLAN 102 ARP storm and how is it enforced",
     "arp storm vlan 102 stp bpdu guard access loop template"),
    # --- 29 ---
    ("IPv6 NDP inspection is on at the leaves with RA-guard filtering all non-router ports; a rogue Windows laptop once advertised itself as default router during a hackathon and took out a whole lab subnet.", "problem", "technical", False,
     [("NDP", "protocol"), ("RA-guard", "config"), ("IPv6", "protocol"), ("default router", "concept")],
     [("RA-guard", "NDP", "SUPPORTS")],
     "which IPv6 feature filters rogue router advertisements at the leaf after the hackathon outage",
     "ndp ra guard ipv6 rogue router advertisement leaf lab"),
    # --- 30 ---
    ("The WebTransport endpoint for the real-time collab service runs over HTTP/3; browsers get datagrams and streams without a separate WebSocket fallback path to maintain in the client code.", "architecture", "technical", False,
     [("WebTransport", "protocol"), ("HTTP/3", "protocol"), ("WebSocket", "protocol")],
     [("WebTransport", "HTTP/3", "USES"), ("WebTransport", "WebSocket", "REPLACES")],
     "which browser transport did the real-time collab service adopt and which fallback path did it retire",
     "webtransport http3 websocket collab datagram stream"),
    # --- 31 ---
    ("HTTP/2 multiplexing still covers the legacy mobile clients that predate the QUIC rollout; the server advertises both h2 and h3 via Alt-Svc and the newer builds upgrade on the second request.", "fact", "technical", False,
     [("HTTP/2", "protocol"), ("QUIC", "protocol"), ("Alt-Svc", "config"), ("h2", "config"), ("h3", "config")],
     [("HTTP/2", "Alt-Svc", "CONFIGURES")],
     "how do older mobile clients coexist with the HTTP/3 rollout and which header steers the upgrade",
     "http2 http3 quic alt svc h2 h3 mobile client"),
    # --- 32 ---
    ("OSPF area 0 is the transit backbone; area 51 and area 52 are stub areas for the campus branches so they never see external LSA flooding from the internet-facing ABRs during reconvergence.", "fact", "technical", False,
     [("OSPF", "protocol"), ("area 0", "config"), ("area 51", "config"), ("stub areas", "concept"), ("LSA", "concept")],
     [("stub areas", "LSA", "REPLACES")],
     "which OSPF area carries the backbone transit and which stub areas shield campus branches from external LSAs",
     "ospf area 0 51 52 stub lsa backbone campus"),
    # --- 33 ---
    ("IS-IS wide metrics replaced narrow metrics so the path-metric headroom survives a decade of capacity planning; narrow-metric TLVs got clamped at 63 and routine upgrades were bumping the ceiling.", "decision", "technical", False,
     [("IS-IS", "protocol"), ("wide metrics", "config"), ("narrow metrics", "config"), ("63", "config")],
     [("wide metrics", "narrow metrics", "REPLACES")],
     "which IS-IS metric format replaced narrow metrics and what ceiling forced the move",
     "is-is wide metric narrow tlv 63 ceiling"),
    # --- 34 ---
    ("BFD is enabled between every pair of BGP neighbours on the data-centre fabric at 150 ms intervals with a three-times multiplier; hold-timer-based convergence took close to 180 seconds before.", "milestone", "technical", False,
     [("BFD", "protocol"), ("BGP", "protocol"), ("150 ms", "config"), ("180 seconds", "config")],
     [("BFD", "BGP", "SUPPORTS")],
     "which sub-second liveness protocol backs the BGP sessions on the fabric and how fast does it detect failure",
     "bfd bgp 150 ms multiplier hold timer 180 second"),
    # --- 35 ---
    ("Prefer TCP BBR on cross-continent paths and CUBIC on intra-region ones; mixed results on satellite links made us leave CUBIC as the default on the ground-station tunnel until more data lands.", "preference", "technical", False,
     [("BBR", "algorithm"), ("CUBIC", "algorithm"), ("satellite", "infrastructure")],
     [("BBR", "CUBIC", "PREFERS")],
     "where does BBR win against CUBIC in the deployment and why does satellite still keep CUBIC as default",
     "bbr cubic cross continent intra region satellite ground"),
    # --- 36 ---
    ("Preference is to keep WireGuard user-space off hot paths and run the kernel module on every Linux node; the user-space implementation is fine for phones but chews through small-packet budget on servers.", "preference", "technical", False,
     [("WireGuard", "protocol"), ("kernel module", "pattern"), ("user-space", "pattern"), ("Linux", "platform")],
     [("kernel module", "user-space", "PREFERS")],
     "where should WireGuard run kernel-side versus user-space in the deployment and why",
     "wireguard kernel user space linux server phone packet"),
    # --- 37 ---
    ("Preference is QUIC over TCP for any new service that has a browser client; the congestion control is co-evolving with BBR research and the handshake cost shrinks with 0-RTT on reconnect.", "preference", "technical", False,
     [("QUIC", "protocol"), ("TCP", "protocol"), ("BBR", "algorithm"), ("0-RTT", "concept")],
     [("QUIC", "TCP", "PREFERS")],
     "what is the transport preference for new browser-facing services and which congestion-control research rides along",
     "quic tcp browser service bbr 0-rtt handshake"),
    # --- 38 ---
    ("Prefer LACP fast-rate on inter-DC dark fibre where BFD is not terminated and slow-rate everywhere else; fast-rate gives sub-second detection without the control-plane overhead BFD adds.", "preference", "technical", False,
     [("LACP", "protocol"), ("BFD", "protocol"), ("fast-rate", "config"), ("slow-rate", "config")],
     [("LACP", "BFD", "REPLACES")],
     "where should LACP fast-rate run instead of BFD and what operational cost does it avoid",
     "lacp fast rate slow bfd inter dc dark fibre"),
    # --- 39 ---
    ("Migrated the storage replication ring to SCTP multi-homing; single-path TCP was rebooting replication state on a flap even when the secondary link was healthy and available.", "milestone", "technical", False,
     [("SCTP", "protocol"), ("TCP", "protocol"), ("storage replication", "service")],
     [("SCTP", "TCP", "REPLACES"), ("SCTP", "storage replication", "APPLIES_TO")],
     "which SCTP feature replaced single-path TCP on the storage replication ring and what flap pattern did it cure",
     "sctp multi homing tcp storage replication flap"),
    # --- 40 ---
    ("QUIC version negotiation caused a day-zero bug with one CDN edge; clients with draft-29 hit an unexpected retry loop and the mitigation was to disable downgrade until both sides landed RFC 9000.", "decision", "technical", False,
     [("QUIC", "protocol"), ("CDN", "infrastructure"), ("draft-29", "config"), ("RFC 9000", "publication")],
     [("RFC 9000", "draft-29", "REPLACES")],
     "which QUIC negotiation bug hit the CDN edge and what mitigation held until RFC 9000 landed on both sides",
     "quic draft 29 rfc 9000 cdn retry negotiation"),
    # --- 41 ---
    ("BGP graceful restart is on for every eBGP session to transit providers; a control-plane reload no longer drops forwarding and the upstream sees us as stale rather than gone for up to 240 seconds.", "milestone", "technical", False,
     [("BGP", "protocol"), ("graceful restart", "config"), ("240 seconds", "config"), ("eBGP", "protocol")],
     [("BGP", "graceful restart", "USES")],
     "which BGP feature keeps forwarding alive through a control-plane reload and how long is the upstream stale window",
     "bgp graceful restart ebgp 240 second control plane"),
    # --- 42 ---
    ("Shipped the first SRv6 uSID production cutover on the north-south backbone; route churn was zero during the flip because both MPLS-LDP and SRv6 ran hot-standby for a fortnight before the cutover.", "milestone", "technical", False,
     [("SRv6", "protocol"), ("uSID", "pattern"), ("MPLS-LDP", "protocol"), ("north-south", "concept")],
     [("SRv6", "MPLS-LDP", "REPLACES")],
     "which SRv6 cutover landed on the backbone and how was MPLS-LDP kept alive during the transition",
     "srv6 usid cutover backbone mpls ldp north south"),
    # --- 43. noise ---
    ("Two crows have started sitting on the rooftop AC unit every afternoon and one of them swiped a staffer's keyring last week.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The HTTP/3 rollout on the admin console finished last sprint; feature flag is permanently on for all users and the rollback path via h2 Alt-Svc survives only as a break-glass lever.", "milestone", "technical", False,
     [("HTTP/3", "protocol"), ("admin console", "service"), ("Alt-Svc", "config"), ("h2", "config")],
     [("HTTP/3", "admin console", "APPLIES_TO")],
     "which service finished its HTTP/3 rollout and what rollback lever remains in place",
     "http3 admin console alt svc h2 rollout rollback"),
    # --- 45 ---
    ("The Tailscale ACL lives as a JSON file in the repo and deploys via CI; the derp-server selection is pinned to two in-region relays so exit traffic never leaves the compliance boundary.", "architecture", "technical", False,
     [("Tailscale", "service"), ("ACL", "config"), ("derp-server", "infrastructure")],
     [("Tailscale", "ACL", "CONFIGURES")],
     "how is the Tailscale ACL managed and which relay selection keeps exit traffic inside the compliance boundary",
     "tailscale acl json ci derp relay compliance"),
    # --- 46 ---
    ("VXLAN VNI 10023 carries the PCI workload VRF; a dedicated set of VTEPs and EVPN route-targets isolate it from the general tenants and audit sign-off hinges on that route-target not leaking.", "reference", "technical", False,
     [("VXLAN", "protocol"), ("VNI 10023", "config"), ("VTEP", "infrastructure"), ("EVPN", "protocol"), ("PCI", "concept")],
     [("VXLAN", "VNI 10023", "USES")],
     "which VXLAN VNI carries the PCI workload VRF and what isolation mechanism underpins the audit sign-off",
     "vxlan vni 10023 pci vtep evpn route target"),
    # --- 47 ---
    ("Cross-region latency between the us-east and eu-west clusters settles around 78 ms on the primary path and 94 ms on the MPLS-TE fast-reroute bypass; the SLO target is anything under 120 ms.", "reference", "technical", False,
     [("us-east", "place"), ("eu-west", "place"), ("78 ms", "config"), ("MPLS-TE", "protocol"), ("120 ms", "config")],
     [("MPLS-TE", "us-east", "APPLIES_TO")],
     "what latency values anchor the us-east to eu-west path on primary and bypass, and where does the SLO sit",
     "us east eu west 78 ms mpls te bypass slo 120"),
    # --- 48 ---
    ("IPv6 PMTUD now works end-to-end after we stopped filtering ICMPv6 Packet Too Big at the edge; TCP flows to mobile handsets on 1280-byte paths stopped stalling mid-response when we lifted the filter.", "problem", "technical", False,
     [("PMTUD", "concept"), ("IPv6", "protocol"), ("ICMPv6 Packet Too Big", "protocol"), ("1280", "config")],
     [("ICMPv6 Packet Too Big", "PMTUD", "SUPPORTS")],
     "which ICMPv6 message had to stop being filtered for end-to-end PMTUD to work on 1280-byte IPv6 mobile paths",
     "pmtud ipv6 icmpv6 packet too big 1280 mobile"),
    # --- 49 ---
    ("BGP flowspec rules at the transit edge drop known-bad source ports during volumetric attacks; the rules are injected from the scrubbing platform via a dedicated iBGP session with strict filters.", "architecture", "technical", False,
     [("BGP flowspec", "protocol"), ("iBGP", "protocol"), ("scrubbing platform", "service"), ("transit edge", "infrastructure")],
     [("BGP flowspec", "scrubbing platform", "USES")],
     "which BGP extension drops known-bad source ports at the transit edge and where do the rules originate",
     "bgp flowspec ibgp scrubbing transit volumetric"),
    # --- 50 ---
    ("MSS clamp on the ingress LB is set to 1360 for IPv4 and 1340 for IPv6 because the WireGuard hop subtracts a larger per-packet overhead on v6; this covers the worst-case path through the estate.", "reference", "technical", False,
     [("MSS clamp", "concept"), ("1360", "config"), ("1340", "config"), ("IPv6", "protocol"), ("WireGuard", "protocol")],
     [("MSS clamp", "WireGuard", "APPLIES_TO")],
     "what MSS clamp values are set at the ingress LB for IPv4 versus IPv6 and why does WireGuard drive the IPv6 number",
     "mss clamp 1360 1340 ipv4 ipv6 wireguard ingress"),
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
