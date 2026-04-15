"""One-off emitter for shared-base batch-097 — technical domain (realtime delivery systems).

Writes 50 rows to data/v2/shared/batch_097.tmp.jsonl with ids shared-04801..04850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_097.tmp.jsonl"
ID_OFFSET = 4800

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("WebSockets carried the bidirectional trade feed to the browser; SSE did not fit because the client needed to push order cancellations on the same channel.", "decision", "technical", False,
     [("WebSockets", "protocol"), ("SSE", "protocol")],
     [("WebSockets", "SSE", "REPLACES")],
     "which realtime transport beat SSE for the bidirectional trade feed",
     "bidirectional socket push cancel order feed trade swap"),
    # --- 2 ---
    ("SSE replaced long-polling on the status page; the one-way event stream kept the connection count flat under traffic spikes.", "decision", "technical", False,
     [("SSE", "protocol"), ("long-polling", "pattern")],
     [("SSE", "long-polling", "REPLACES")],
     "which one-way transport retired long-polling on the public status page",
     "server sent events one way poll retire status connection"),
    # --- 3 ---
    ("HTTP/3 server push was evaluated for asset hints but rejected; the feature was removed from the spec in 2022 and the CDN cache already covered the win.", "decision", "technical", False,
     [("HTTP/3", "protocol"), ("CDN", "infrastructure")],
     [],
     "why was HTTP/3 server push not adopted for the asset prefetch path",
     "push spec remove prefetch asset hint cache cover reject"),
    # --- 4 ---
    ("mediasoup powered the group-call SFU on the Node backend; per-worker CPU isolation kept a single bad peer from tanking an entire room.", "architecture", "technical", False,
     [("mediasoup", "library"), ("Node", "technology"), ("SFU", "pattern")],
     [],
     "which WebRTC SFU library ran on the Node backend for group calls",
     "SFU worker CPU isolation bad peer room WebRTC group call"),
    # --- 5 ---
    ("LiveKit improved on the raw mediasoup wrapper with managed signaling and a typed client SDK; the team dropped the custom REST signaling layer.", "decision", "technical", False,
     [("LiveKit", "platform"), ("mediasoup", "library"), ("REST", "protocol")],
     [("LiveKit", "mediasoup", "IMPROVES_ON")],
     "which SFU product took over from the hand-rolled mediasoup wrapper",
     "managed signaling typed SDK wrapper drop custom REST swap"),
    # --- 6 ---
    ("Janus handled the SIP-to-WebRTC bridge for the call-center pilot; its plugin model beat writing a custom gateway on top of Pion.", "decision", "technical", False,
     [("Janus", "platform"), ("SIP", "protocol"), ("WebRTC", "protocol"), ("Pion", "library")],
     [("Janus", "Pion", "PREFERS")],
     "which gateway ran the SIP bridge on top of the call-center pilot stack",
     "plugin gateway SIP bridge call center custom avoid swap"),
    # --- 7 ---
    ("Pion was preferred over native C WebRTC stacks for the Go service; pure Go made cross-compilation to ARM64 edge nodes trivial.", "preference", "technical", False,
     [("Pion", "library"), ("Go", "language"), ("WebRTC", "protocol"), ("ARM64", "platform")],
     [("Pion", "WebRTC", "IMPLEMENTS")],
     "which WebRTC stack beat native C bindings on the Go edge service",
     "pure Go cross compile ARM64 edge binding native avoid"),
    # --- 8 ---
    ("Jitsi Videobridge was retired from the classroom product; LiveKit's simulcast and dynacast covered the low-bandwidth student path better.", "decision", "technical", False,
     [("Jitsi Videobridge", "platform"), ("LiveKit", "platform")],
     [("LiveKit", "Jitsi Videobridge", "REPLACES")],
     "which SFU displaced Jitsi Videobridge on the classroom product",
     "simulcast dynacast low bandwidth student classroom retire"),
    # --- 9 ---
    ("STUN alone failed for roughly 15 percent of the enterprise peers; coturn with TURN-over-TLS on 443 rescued the symmetric-NAT office networks.", "problem", "technical", False,
     [("STUN", "protocol"), ("coturn", "tool"), ("TURN", "protocol"), ("TLS", "protocol")],
     [],
     "which ICE fallback rescued the symmetric-NAT enterprise peers",
     "symmetric NAT TURN TLS 443 enterprise office peer rescue"),
    # --- 10 ---
    ("ICE candidate gathering was capped at 3 seconds on mobile; waiting longer burned the battery without improving the connect ratio in production data.", "decision", "technical", False,
     [("ICE", "protocol")],
     [],
     "which ICE timeout cap kept mobile battery burn in check",
     "candidate gather timeout mobile battery connect ratio cap"),
    # --- 11 ---
    ("EMQX replaced Mosquitto as the fleet MQTT broker; the clustered broker held 2 million concurrent IoT sessions where Mosquitto maxed around 100k per node.", "decision", "technical", False,
     [("EMQX", "service"), ("Mosquitto", "service"), ("MQTT", "protocol"), ("IoT", "concept")],
     [("EMQX", "Mosquitto", "REPLACES")],
     "which MQTT broker scaled past Mosquitto on the concurrent IoT fleet",
     "cluster broker concurrent session scale fleet swap IoT"),
    # --- 12 ---
    ("HiveMQ was preferred on the automotive contract; the enterprise-grade MQTT 5 compliance and audit tooling matched the OEM's procurement checklist.", "preference", "technical", False,
     [("HiveMQ", "service"), ("MQTT 5", "protocol")],
     [],
     "which MQTT broker won the automotive contract on procurement fit",
     "enterprise broker MQTT 5 compliance audit procurement swap"),
    # --- 13 ---
    ("Phoenix Channels carried the live dashboard to the trader desktop; the Elixir BEAM's per-process isolation ate a runaway chart render without blocking peers.", "architecture", "technical", False,
     [("Phoenix Channels", "framework"), ("Elixir", "language"), ("BEAM", "platform")],
     [],
     "which realtime framework carried the live dashboard on Elixir",
     "channel process isolation runaway render peer block swap"),
    # --- 14 ---
    ("LiveView replaced a React-plus-WebSocket page for the admin console; server-rendered diffs cut the client bundle by 380 KB without losing reactivity.", "decision", "technical", False,
     [("LiveView", "framework"), ("React", "framework"), ("WebSocket", "protocol")],
     [("LiveView", "React", "REPLACES")],
     "which realtime framework retired React-plus-WebSocket on the admin console",
     "server render diff bundle client cut admin console swap"),
    # --- 15 ---
    ("Yjs powered the shared document editor; the CRDT merge kept concurrent edits conflict-free without a central ordering server.", "architecture", "technical", False,
     [("Yjs", "library"), ("CRDT", "algorithm")],
     [("Yjs", "CRDT", "IMPLEMENTS")],
     "which CRDT library ran the conflict-free shared document editor",
     "CRDT merge concurrent edit central order server avoid"),
    # --- 16 ---
    ("Automerge was tested against Yjs for the offline-first notes app; Yjs won on memory footprint for long documents with many authors.", "decision", "technical", False,
     [("Automerge", "library"), ("Yjs", "library")],
     [("Yjs", "Automerge", "PREFERS")],
     "which CRDT library beat Automerge for the offline-first notes app",
     "memory footprint long document author offline note swap"),
    # --- 17 ---
    ("APNs carried the urgent iOS alerts via token-based auth; provider-certificate auth was retired after the renewal outage on 2026-02-11.", "decision", "technical", False,
     [("APNs", "service"), ("iOS", "platform"), ("2026-02-11", "date")],
     [],
     "which APNs auth mode took over from provider certificates after the outage",
     "token auth provider certificate renewal outage iOS push"),
    # --- 18 ---
    ("FCM delivered the Android push fan-out; topic messaging replaced a per-device loop that was hitting the per-minute quota during promo sends.", "decision", "technical", False,
     [("FCM", "service"), ("Android", "platform")],
     [("FCM", "FCM", "IMPROVES_ON")],
     "which FCM feature retired the per-device loop during promo sends",
     "topic message device loop quota promo send retire swap"),
    # --- 19 ---
    ("Web Push under RFC 8030 with VAPID keys replaced the old GCM browser push; the new flow worked across Firefox and Safari without vendor keys.", "decision", "technical", False,
     [("Web Push", "protocol"), ("RFC 8030", "publication"), ("VAPID", "protocol"), ("GCM", "service"), ("Firefox", "platform"), ("Safari", "platform")],
     [("Web Push", "GCM", "REPLACES")],
     "which web push flow took over from the vendor-locked GCM browser push",
     "VAPID RFC standard browser Firefox Safari vendor key drop"),
    # --- 20. noise ---
    ("Hang on, my Wi-Fi just dropped for a second.", "fact", "noise", True, [], [], None, None),
    # --- 21 ---
    ("Centrifugo ran the presence channel for the multiplayer whiteboard; the Redis engine plus sharded channels handled 50k concurrent cursors per region.", "architecture", "technical", False,
     [("Centrifugo", "platform"), ("Redis", "database")],
     [],
     "which presence server carried the multiplayer whiteboard cursors",
     "presence shard channel Redis engine whiteboard cursor scale"),
    # --- 22 ---
    ("Pusher Channels was swapped for Ably on the live-sports app; Ably's global edge mesh and stronger message ordering survived the World Cup traffic.", "decision", "technical", False,
     [("Pusher Channels", "service"), ("Ably", "service")],
     [("Ably", "Pusher Channels", "REPLACES")],
     "which realtime service displaced Pusher on the live-sports app",
     "edge mesh order guarantee world cup live sport swap"),
    # --- 23 ---
    ("Ably's presence membership set beat a DIY Redis hash for the chat room roster; automatic enter/leave events and connection recovery were included.", "preference", "technical", False,
     [("Ably", "service"), ("Redis", "database")],
     [("Ably", "Redis", "PREFERS")],
     "which presence primitive beat a hand-rolled Redis hash on chat rosters",
     "presence member set enter leave recovery chat roster swap"),
    # --- 24 ---
    ("LL-HLS replaced plain HLS on the esports live feed; glass-to-glass latency dropped from 18 seconds to 3 seconds without rewriting the CDN plan.", "decision", "technical", False,
     [("LL-HLS", "protocol"), ("HLS", "protocol"), ("CDN", "infrastructure")],
     [("LL-HLS", "HLS", "REPLACES")],
     "which HLS variant slashed glass-to-glass latency on the esports feed",
     "low latency part HLS glass to glass drop second CDN"),
    # --- 25 ---
    ("WHIP replaced RTMP for OBS ingest into the WebRTC SFU; the browser-aligned signaling removed the transcode step between the contributor and the mesh.", "decision", "technical", False,
     [("WHIP", "protocol"), ("RTMP", "protocol"), ("OBS", "tool"), ("WebRTC", "protocol"), ("SFU", "pattern")],
     [("WHIP", "RTMP", "REPLACES")],
     "which ingest protocol retired RTMP on the OBS-to-SFU path",
     "WebRTC ingest signaling OBS transcode mesh retire swap"),
    # --- 26 ---
    ("WHEP served the low-latency viewer egress; viewers on the public site connected in under 800 ms versus 6-8 seconds on the old DASH player.", "milestone", "technical", False,
     [("WHEP", "protocol"), ("DASH", "protocol")],
     [("WHEP", "DASH", "IMPROVES_ON")],
     "which egress protocol beat DASH on public-site time-to-first-frame",
     "viewer egress low latency time first frame player swap"),
    # --- 27 ---
    ("Convex handled the realtime database for the React dashboard; live queries re-ran on write without a subscription hook per component.", "architecture", "technical", False,
     [("Convex", "database"), ("React", "framework")],
     [],
     "which realtime database carried the live queries on the React dashboard",
     "live query re-run subscription hook component dashboard"),
    # --- 28 ---
    ("RethinkDB changefeeds were retired when the project forked to Convex; unmaintained drivers and Mongo-style ops were not worth the drag.", "decision", "technical", False,
     [("RethinkDB", "database"), ("Convex", "database"), ("Mongo", "database")],
     [("Convex", "RethinkDB", "REPLACES")],
     "which realtime database took over from RethinkDB changefeeds",
     "changefeed driver unmaintained fork ops drag retire swap"),
    # --- 29 ---
    ("Firestore live queries powered the mobile chat; onSnapshot beat rolling our own long-poll loop against a REST endpoint on battery draw alone.", "decision", "technical", False,
     [("Firestore", "database"), ("REST", "protocol")],
     [],
     "which live-query API won on mobile battery against a REST long-poll",
     "live query snapshot REST long poll battery draw swap"),
    # --- 30 ---
    ("WebTransport was evaluated against WebSockets for the game lobby; unreliable datagrams matched the player-position stream but tooling was not yet ready.", "problem", "technical", False,
     [("WebTransport", "protocol"), ("WebSockets", "protocol")],
     [],
     "why did WebTransport lose to WebSockets for the game lobby in 2026",
     "datagram unreliable player position tool mature lobby hold"),
    # --- 31 ---
    ("socket.io was swapped for native WebSocket on the chat app; the custom framing added 14 KB to the client bundle with no feature we still used.", "decision", "technical", False,
     [("socket.io", "library"), ("WebSocket", "protocol")],
     [("WebSocket", "socket.io", "REPLACES")],
     "which native transport retired socket.io on the chat client",
     "custom framing bundle size client chat feature unused swap"),
    # --- 32. noise ---
    ("Can you hear me now? Let me unmute.", "fact", "noise", True, [], [], None, None),
    # --- 33 ---
    ("TURN bandwidth was capped per user on the coturn deployment; the quota stopped one abusive tab from draining the egress budget for the region.", "problem", "technical", False,
     [("TURN", "protocol"), ("coturn", "tool")],
     [],
     "which TURN quota stopped a single tab from draining the region egress",
     "bandwidth quota abuse tab egress budget region cap"),
    # --- 34 ---
    ("WebRTC replaced Flash for browser audio and video on the tutoring product; modern browsers dropped Flash in 2020 and the migration was overdue.", "decision", "technical", False,
     [("WebRTC", "protocol"), ("Flash", "technology")],
     [("WebRTC", "Flash", "REPLACES")],
     "which protocol finally retired Flash on the tutoring browser stack",
     "browser audio video Flash drop migrate tutor overdue swap"),
    # --- 35 ---
    ("Simulcast layers on LiveKit served 1080p, 720p, and 180p from the publisher; the SFU picked the lowest layer for bandwidth-constrained subscribers.", "architecture", "technical", False,
     [("LiveKit", "platform"), ("SFU", "pattern")],
     [],
     "which simulcast strategy served bandwidth-constrained subscribers on LiveKit",
     "simulcast layer publisher SFU pick low bandwidth subscriber"),
    # --- 36 ---
    ("Opus at 32 kbps handled the voice channel; switching from G.711 saved roughly 60 percent of the RTP bandwidth per participant.", "decision", "technical", False,
     [("Opus", "protocol"), ("G.711", "protocol"), ("RTP", "protocol")],
     [("Opus", "G.711", "REPLACES")],
     "which audio codec displaced G.711 on the voice-channel path",
     "Opus codec voice bandwidth RTP participant save swap"),
    # --- 37 ---
    ("The WebRTC bandwidth estimator TCC was tuned against the congestion controller BBR on the origin link; default GCC was too slow to back off on mobile drops.", "problem", "technical", False,
     [("TCC", "protocol"), ("BBR", "algorithm"), ("GCC", "algorithm")],
     [("TCC", "GCC", "REPLACES")],
     "which WebRTC bandwidth estimator replaced GCC on the mobile path",
     "transport congestion control back off mobile drop tune swap"),
    # --- 38 ---
    ("Cloudflare Calls was evaluated against a self-hosted LiveKit cluster; the managed SFU saved two SRE FTEs but the per-minute bill doubled at peak.", "decision", "technical", False,
     [("Cloudflare Calls", "service"), ("LiveKit", "platform"), ("SFU", "pattern")],
     [],
     "which managed SFU was weighed against self-hosted LiveKit on ops cost",
     "managed SFU SRE FTE cost per minute peak trade swap"),
    # --- 39 ---
    ("The presence timeout was dropped from 60 seconds to 10 on the collaborative editor; zombie cursors on dropped connections used to confuse users for a full minute.", "decision", "technical", False,
     [("presence timeout", "config")],
     [],
     "which presence tweak killed zombie cursors on the collaborative editor",
     "zombie cursor drop connection minute confuse user timeout"),
    # --- 40 ---
    ("Matrix via Synapse was rejected for the internal chat; the federation surface was overkill and the Postgres write amplification scared the DB team.", "decision", "technical", False,
     [("Matrix", "protocol"), ("Synapse", "service"), ("Postgres", "database")],
     [],
     "why was Matrix on Synapse rejected for the internal chat deployment",
     "federation surface write amplification database team reject"),
    # --- 41 ---
    ("WebSocket backpressure on the market-data feed used per-client send queues with a 1 MB high-watermark; breaching the limit dropped the slow consumer cleanly.", "architecture", "technical", False,
     [("WebSocket", "protocol")],
     [],
     "which backpressure strategy dropped slow WebSocket consumers cleanly",
     "backpressure queue watermark slow consumer drop send cap"),
    # --- 42 ---
    ("Cloudflare Durable Objects coordinated the per-room WebSocket fan-out; a single JS object per room avoided a Redis pubsub hop on every message.", "architecture", "technical", False,
     [("Cloudflare Durable Objects", "service"), ("WebSocket", "protocol"), ("Redis", "database"), ("JS", "language")],
     [("Cloudflare Durable Objects", "Redis", "REPLACES")],
     "which edge primitive replaced Redis pubsub for room WebSocket fan-out",
     "durable object room fan out pubsub hop Redis swap"),
    # --- 43 ---
    ("Rust Axum handled the WebSocket upgrade on the trading edge; tokio-tungstenite plus a custom heartbeat frame held 80k sockets per pod.", "architecture", "technical", False,
     [("Rust", "language"), ("Axum", "framework"), ("WebSocket", "protocol"), ("tokio-tungstenite", "library")],
     [],
     "which Rust stack held 80k WebSocket sockets per trading-edge pod",
     "Rust framework WebSocket heartbeat pod scale trading edge"),
    # --- 44 ---
    ("The RFC 8030 Web Push spec is the reference for the browser notification payload encryption; aes128gcm with the client's P-256 key is mandatory now.", "reference", "technical", False,
     [("RFC 8030", "publication"), ("Web Push", "protocol"), ("aes128gcm", "algorithm"), ("P-256", "algorithm")],
     [],
     "which spec defines the browser push payload encryption requirements",
     "RFC web push aes128gcm elliptic curve mandatory spec reference"),
    # --- 45 ---
    ("Mosquitto MQTT bridging was kept for the on-prem factory gateway even after EMQX took over the cloud broker; bridge mode fit the air-gapped edge well.", "fact", "technical", False,
     [("Mosquitto", "service"), ("MQTT", "protocol"), ("EMQX", "service")],
     [],
     "which MQTT product stayed on the factory floor despite the EMQX migration",
     "bridge mode on prem gateway air gap edge keep Mosquitto"),
    # --- 46 ---
    ("PeerJS was rejected for the production mesh call; the unmaintained signaling server and tight coupling to its own ID scheme blocked the migration.", "decision", "technical", False,
     [("PeerJS", "library")],
     [],
     "why was PeerJS rejected as the signaling layer for the mesh call product",
     "signaling unmaintained ID scheme couple mesh call reject"),
    # --- 47 ---
    ("Presence heartbeats on the Phoenix Channels app landed in the Postgres audit log via a dedicated write batch; naive per-event inserts had buried the DB.", "problem", "technical", False,
     [("Phoenix Channels", "framework"), ("Postgres", "database")],
     [],
     "which batching tweak saved Postgres from presence heartbeat floods",
     "heartbeat presence audit batch insert flood DB rescue"),
    # --- 48 ---
    ("The live-cursor CRDT doc was persisted every 5 seconds to S3 via Yjs providers; clients still reconnected to the in-memory Yjs doc for the live state.", "architecture", "technical", False,
     [("Yjs", "library"), ("CRDT", "algorithm"), ("S3", "service")],
     [],
     "which persistence cadence backed the live-cursor CRDT document",
     "periodic snapshot provider persist reconnect live CRDT cadence"),
    # --- 49 ---
    ("On 2026-03-02 the live-chat product cut end-to-end delivery latency from 340 ms to 95 ms by moving Centrifugo from a single region to an anycast mesh.", "milestone", "technical", False,
     [("Centrifugo", "platform"), ("2026-03-02", "date")],
     [],
     "when did the live-chat product cut delivery latency past the 100 ms bar",
     "anycast mesh region deliver latency chat milestone date"),
    # --- 50 ---
    ("Last-event-id on the SSE stream let the browser resume cleanly after reconnect; a per-tab cursor in localStorage avoided reprocessing events on tab switches.", "architecture", "technical", False,
     [("SSE", "protocol"), ("localStorage", "api")],
     [],
     "which SSE feature let the browser resume cleanly on reconnect",
     "last event id resume reconnect cursor local storage tab"),
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
