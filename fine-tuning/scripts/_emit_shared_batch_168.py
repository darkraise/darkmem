"""One-off emitter for shared-base batch-168 — technical domain (realtime transports: WebSockets, SSE, WebTransport, MQTT, WebRTC, SFU/MCU, ICE/TURN/STUN, fanout via Redis/NATS).

Writes 50 rows to data/v2/shared/batch_168.tmp.jsonl with ids shared-08351..08400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_168.tmp.jsonl"
ID_OFFSET = 8350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The chat gateway upgrades clients to WebSockets per RFC 6455 and keeps a per-connection send queue; slow readers get a 1008 close rather than blocking the fanout loop.", "architecture", "technical", False,
     [("WebSockets", "protocol"), ("RFC 6455", "concept"), ("send queue", "pattern")],
     [("WebSockets", "RFC 6455", "IMPLEMENTS")],
     "how does the chat gateway handle slow WebSocket readers without stalling the broadcast loop",
     "websocket rfc 6455 send queue slow reader close fanout"),
    # --- 2 ---
    ("Replaced long-polling with Server-Sent Events for the dashboard push path; one-way server updates are a natural fit and the auto-reconnect in EventSource saved a pile of client glue.", "decision", "technical", False,
     [("Server-Sent Events", "protocol"), ("long-polling", "pattern"), ("EventSource", "api")],
     [("Server-Sent Events", "long-polling", "REPLACES")],
     "which push transport replaced long-polling for the dashboard and what client feature simplified the code",
     "sse server sent events long polling eventsource dashboard push"),
    # --- 3 ---
    ("WebTransport over HTTP/3 is behind a feature flag for the game-client beta; unreliable datagrams carry state snapshots and a reliable stream handles the chat sidechannel.", "milestone", "technical", False,
     [("WebTransport", "protocol"), ("HTTP/3", "protocol"), ("datagrams", "concept")],
     [("WebTransport", "HTTP/3", "DEPENDS_ON")],
     "which new transport rolled out behind a flag for the game beta and how are unreliable versus reliable paths split",
     "webtransport http3 datagram stream game beta feature flag"),
    # --- 4 ---
    ("The IoT ingest layer speaks MQTT 3.1.1 over TLS to the broker; QoS 1 with persistent sessions handles brief cell-network drops without losing thermostat telemetry.", "fact", "technical", False,
     [("MQTT", "protocol"), ("QoS 1", "config"), ("persistent sessions", "pattern"), ("TLS", "protocol")],
     [("MQTT", "TLS", "USES")],
     "which broker protocol and QoS level does the IoT ingest use to survive cell-network dropouts",
     "mqtt qos 1 persistent session tls thermostat iot ingest broker"),
    # --- 5 ---
    ("STOMP over WebSocket frames the message bus so browsers can subscribe to the same destinations JMS clients hit; the prefix /topic maps to pub-sub and /queue to point-to-point.", "fact", "technical", False,
     [("STOMP", "protocol"), ("WebSocket", "protocol"), ("JMS", "technology"), ("/topic", "pattern"), ("/queue", "pattern")],
     [("STOMP", "WebSocket", "USES")],
     "how does the browser client share destinations with JMS backends and which prefixes split pub-sub from queues",
     "stomp websocket jms topic queue destination subscribe browser"),
    # --- 6 ---
    ("SockJS stays in the stack as the compatibility shim for corporate proxies that strip Upgrade headers; native WebSocket is tried first and xhr-streaming is the last fallback.", "fact", "technical", False,
     [("SockJS", "library"), ("Upgrade headers", "concept"), ("xhr-streaming", "pattern"), ("WebSocket", "protocol")],
     [("SockJS", "WebSocket", "EXTENDS")],
     "why does SockJS still ship and what transport ladder does it walk on locked-down corporate proxies",
     "sockjs upgrade header xhr streaming proxy fallback websocket"),
    # --- 7 ---
    ("Centrifugo runs as the dedicated realtime node behind the app; connections hit the Centrifugo frontend and the backend publishes via its HTTP API so the main process never holds sockets.", "architecture", "technical", False,
     [("Centrifugo", "service"), ("HTTP API", "api"), ("backend", "service")],
     [("Centrifugo", "HTTP API", "USES")],
     "how is Centrifugo wired so the main app backend does not directly own long-lived client sockets",
     "centrifugo realtime node http api publish frontend socket backend"),
    # --- 8 ---
    ("socket.io was retired from the new admin panel in favour of a plain WebSocket client; the room semantics were reimplemented in 80 lines and the bundle dropped by 45 KB gzipped.", "decision", "technical", False,
     [("socket.io", "library"), ("WebSocket", "protocol"), ("admin panel", "project")],
     [("WebSocket", "socket.io", "REPLACES")],
     "which library got dropped from the admin panel for a plain WebSocket client and what bundle size win followed",
     "socket io websocket admin panel bundle room semantic gzip drop"),
    # --- 9 ---
    ("Phoenix Channels power the presence list; the built-in tracker CRDT converges across nodes and the browser sees join and leave events without us running a separate presence service.", "fact", "technical", False,
     [("Phoenix Channels", "framework"), ("tracker CRDT", "pattern"), ("presence list", "pattern")],
     [("Phoenix Channels", "tracker CRDT", "USES")],
     "which framework handles multi-node presence without a bespoke service and what data structure powers convergence",
     "phoenix channel tracker crdt presence join leave multi node"),
    # --- 10. noise ---
    ("The office espresso machine started whining on the third pull and someone taped a sign saying the bean hopper needs two scoops of decaf to calm it down.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Ably is the managed pub-sub for the mobile SDK; message history replay on reconnect saved us from having to build our own at-least-once layer for in-flight sends.", "decision", "technical", False,
     [("Ably", "service"), ("mobile SDK", "project"), ("message history replay", "pattern")],
     [("mobile SDK", "Ably", "USES")],
     "which managed realtime service does the mobile SDK lean on and which feature removed the need for a custom delivery layer",
     "ably mobile sdk managed pubsub history replay reconnect delivery"),
    # --- 12 ---
    ("Pusher was dropped after the per-message cost overtook a self-hosted Centrifugo deployment at our fanout volume; the migration ran hot-hot for a week before cutover.", "decision", "technical", False,
     [("Pusher", "service"), ("Centrifugo", "service"), ("fanout", "concept")],
     [("Centrifugo", "Pusher", "REPLACES")],
     "which self-hosted realtime service replaced Pusher after cost crossed over and how was the cutover staged",
     "pusher centrifugo cost fanout migration hot hot cutover volume"),
    # --- 13 ---
    ("PubNub handles the cross-region presence for the collaborative editor; regional edge POPs keep latency under 90 ms for APAC users without us running our own edge fleet.", "fact", "technical", False,
     [("PubNub", "service"), ("collaborative editor", "project"), ("edge POPs", "infrastructure"), ("APAC", "place")],
     [("collaborative editor", "PubNub", "USES")],
     "which managed realtime network keeps APAC presence latency low for the collaborative editor",
     "pubnub apac latency edge pop collaborative editor presence region"),
    # --- 14 ---
    ("LiveKit replaced our homemade SFU for group video; the built-in simulcast layers and client SDKs across iOS, Android, and web shaved months off the v2 rollout.", "decision", "technical", False,
     [("LiveKit", "platform"), ("homemade SFU", "project"), ("simulcast", "pattern")],
     [("LiveKit", "homemade SFU", "REPLACES")],
     "which hosted realtime media platform replaced the in-house SFU and which features unlocked the v2 rollout",
     "livekit sfu simulcast homemade group video ios android web"),
    # --- 15 ---
    ("WebRTC data channels carry the cursor-position stream in the whiteboard; unreliable mode with a maxRetransmits of 0 gives us UDP-like semantics without leaving the browser sandbox.", "architecture", "technical", False,
     [("WebRTC data channels", "protocol"), ("whiteboard", "project"), ("maxRetransmits", "config"), ("UDP", "protocol")],
     [("whiteboard", "WebRTC data channels", "USES")],
     "which in-browser transport carries whiteboard cursors and how is it configured for UDP-like behaviour",
     "webrtc data channel whiteboard cursor unreliable maxretransmits udp"),
    # --- 16 ---
    ("SimplePeer wraps the RTCPeerConnection API for the peer-to-peer file-share tool; the stream interface fits node-land code reuse on the signalling server side.", "fact", "technical", False,
     [("SimplePeer", "library"), ("RTCPeerConnection", "api"), ("file-share tool", "project")],
     [("SimplePeer", "RTCPeerConnection", "USES")],
     "which wrapper did our P2P sharing client adopt and why did node-side servers appreciate its shape",
     "simplepeer rtcpeerconnection file share stream node signal"),
    # --- 17 ---
    ("The Janus WebRTC gateway fronts the audio bridge room; its room plugin mixes up to 20 participants server-side, which spared the mobile clients from N-to-N audio decoding.", "architecture", "technical", False,
     [("Janus WebRTC gateway", "service"), ("audio bridge", "pattern"), ("room plugin", "library")],
     [("audio bridge", "Janus WebRTC gateway", "USES")],
     "which gateway mixes the audio-bridge room server-side to keep mobile clients off N-to-N decoding",
     "janus webrtc gateway audio bridge room plugin mobile mix"),
    # --- 18 ---
    ("mediasoup drives the selective forwarding for the live-classroom product; its worker-per-core model scales past 2000 concurrent students on a single 32-core box.", "milestone", "technical", False,
     [("mediasoup", "library"), ("live-classroom", "project"), ("worker-per-core", "pattern")],
     [("live-classroom", "mediasoup", "USES")],
     "which SFU library and concurrency model handle two thousand concurrent live-classroom students on one box",
     "mediasoup sfu worker per core classroom 32 core concurrent student"),
    # --- 19 ---
    ("ICE candidate gathering uses STUN for public-mapped candidates and a coturn TURN server for relay fallback; about 8% of sessions in the field end up on TURN/UDP.", "fact", "technical", False,
     [("ICE", "protocol"), ("STUN", "protocol"), ("TURN", "protocol"), ("coturn", "service")],
     [("TURN", "coturn", "IMPLEMENTS"), ("ICE", "STUN", "USES")],
     "how does the app gather connectivity candidates and what share of sessions needs TURN relay in the wild",
     "ice stun turn coturn candidate relay fallback session field"),
    # --- 20 ---
    ("Chose SFU over MCU for the conference product; bandwidth per uplink stays flat per sender and CPU cost is decode-free on the server, which matters when every room needs GPUs elsewhere.", "decision", "technical", False,
     [("SFU", "pattern"), ("MCU", "pattern"), ("conference product", "project")],
     [("SFU", "MCU", "PREFERS")],
     "which forwarding topology won over MCU for the conference product and what cost arguments sealed it",
     "sfu mcu topology conference bandwidth cpu decode gpu server"),
    # --- 21 ---
    ("The WebSocket server sends a ping frame every 20 seconds and drops the connection if no pong arrives within 10; this caught a batch of silent NATs in the staging region last quarter.", "decision", "technical", False,
     [("WebSocket", "protocol"), ("ping frame", "concept"), ("pong", "concept"), ("NAT", "infrastructure")],
     [],
     "which keepalive schedule does the WebSocket server use and what class of silent failure did it catch in staging",
     "websocket ping pong heartbeat nat silent timeout keepalive"),
    # --- 22 ---
    ("Backpressure on the publish path uses a bounded channel with a drop-oldest policy for presence updates and a block-producer policy for chat; presence staleness is cheaper than chat loss.", "decision", "technical", False,
     [("bounded channel", "pattern"), ("drop-oldest", "pattern"), ("block-producer", "pattern"), ("presence", "concept"), ("chat", "concept")],
     [],
     "how does the publish path apply different backpressure policies to presence versus chat traffic",
     "backpressure bounded channel drop oldest block producer presence chat"),
    # --- 23 ---
    ("permessage-deflate is disabled on the public WebSocket endpoint; the CRIME-style leakage risk on mixed-tenant traffic outweighed the 30-40% bandwidth savings we measured in the lab.", "decision", "technical", False,
     [("permessage-deflate", "protocol"), ("WebSocket", "protocol"), ("CRIME", "concept")],
     [("permessage-deflate", "CRIME", "RELATED_TO")],
     "which WebSocket compression extension did we disable and why did the risk outweigh the bandwidth win",
     "permessage deflate websocket crime compression leakage tenant public"),
    # --- 24 ---
    ("The server passes the Autobahn Testsuite fuzzing-client run with zero non-informational failures; CI gates every release by replaying the 12.x and 13.x cases against the gateway.", "milestone", "technical", False,
     [("Autobahn Testsuite", "tool"), ("fuzzing-client", "pattern"), ("CI", "infrastructure")],
     [("CI", "Autobahn Testsuite", "USES")],
     "which conformance suite gates every realtime release and which case ranges does CI replay",
     "autobahn testsuite fuzzing client ci gate conformance 12 13"),
    # --- 25 ---
    ("Fanout across gateway nodes goes over Redis pub/sub on the Lua channel; each node subscribes to room:* and the publish path is one PUBLISH call per room rather than per subscriber.", "architecture", "technical", False,
     [("Redis pub/sub", "service"), ("gateway node", "service"), ("room:*", "pattern")],
     [("gateway node", "Redis pub/sub", "USES")],
     "how does fanout move between gateway nodes via Redis and what keeps publishes from scaling per subscriber",
     "redis pubsub fanout gateway room channel publish subscribe"),
    # --- 26 ---
    ("Cut over from Redis pub/sub to NATS JetStream for durable fanout; at-least-once delivery and consumer acks meant we could drop the bespoke outbox table that sat in front of Redis.", "decision", "technical", False,
     [("Redis pub/sub", "service"), ("NATS JetStream", "service"), ("outbox table", "pattern")],
     [("NATS JetStream", "Redis pub/sub", "REPLACES"), ("NATS JetStream", "outbox table", "REPLACES")],
     "which streaming system replaced Redis pub-sub for durable fanout and which legacy pattern did it retire",
     "nats jetstream redis pubsub durable outbox ack at least once"),
    # --- 27 ---
    ("The realtime node is stateless except for the per-connection struct; session state lives in Redis with a 30-second TTL so a pod restart is a reconnect, not a global outage.", "decision", "technical", False,
     [("realtime node", "service"), ("Redis", "database"), ("TTL", "config"), ("pod", "infrastructure")],
     [("realtime node", "Redis", "USES")],
     "how does the realtime node survive pod restarts without propagating into a cluster-wide outage",
     "realtime node stateless redis ttl pod reconnect session restart"),
    # --- 28 ---
    ("A blocking write in the WebSocket handler caused a cascading slowdown when one client's socket buffer filled; switching to a per-conn goroutine with a bounded outbox isolated the blast radius.", "milestone", "technical", False,
     [("WebSocket", "protocol"), ("goroutine", "pattern"), ("bounded outbox", "pattern")],
     [("bounded outbox", "goroutine", "USES")],
     "which handler concurrency change stopped one stuck socket from slowing the whole gateway",
     "websocket goroutine bounded outbox blocking write cascade slowdown"),
    # --- 29 ---
    ("RFC 6455 frame parsing is in the hot path so we pre-allocate mask-xor scratch per connection; the old per-frame allocation showed up as 12% of CPU in pprof on the 10k-connection soak.", "problem", "technical", False,
     [("RFC 6455", "concept"), ("mask-xor scratch", "pattern"), ("pprof", "tool")],
     [],
     "which allocation hotspot in RFC 6455 frame parsing showed up in soak profiles and how was it flattened",
     "rfc 6455 mask xor scratch pprof allocation hot path soak"),
    # --- 30 ---
    ("Presence fanout batches events in 50 ms windows before pushing to clients; the old per-event push hit the network 20x harder on join-storms in giant rooms.", "milestone", "technical", False,
     [("Presence fanout", "pattern"), ("50 ms windows", "config"), ("join-storms", "pattern")],
     [],
     "which batching window tamed presence join-storm traffic and how much per-event overhead did it replace",
     "presence fanout batch window 50 ms join storm room per event"),
    # --- 31 ---
    ("The WebTransport POC uses QUIC datagrams for the input channel; packet loss is tolerated for mouse-move events because the next sample replaces the stale one within one tick.", "architecture", "technical", False,
     [("WebTransport", "protocol"), ("QUIC", "protocol"), ("datagrams", "concept")],
     [("WebTransport", "QUIC", "USES")],
     "why does the WebTransport POC send mouse-move events over QUIC datagrams and tolerate losses",
     "webtransport quic datagram mouse move input tick loss tolerance"),
    # --- 32 ---
    ("socket.io's default EIO v4 handshake needs sticky sessions behind a load balancer; we documented the ALB target-group stickiness cookie as a prerequisite after a cryptic reconnect bug.", "reference", "technical", False,
     [("socket.io", "library"), ("EIO v4", "protocol"), ("ALB", "service"), ("stickiness cookie", "config")],
     [("socket.io", "stickiness cookie", "DEPENDS_ON")],
     "which load-balancer setting did socket.io quietly require after a cryptic reconnect bug surfaced",
     "socket io eio v4 sticky session alb target group cookie reconnect"),
    # --- 33 ---
    ("MQTT retained messages carry the last-known device shadow on the home-automation topic; new subscribers get an immediate snapshot instead of waiting for the next telemetry publish.", "reference", "technical", False,
     [("MQTT", "protocol"), ("retained messages", "pattern"), ("device shadow", "pattern")],
     [],
     "which MQTT feature delivers an immediate last-known snapshot to newly subscribing home-automation clients",
     "mqtt retained message device shadow home automation snapshot subscribe"),
    # --- 34 ---
    ("Server-Sent Events carry a Last-Event-ID header on reconnect; the server replays events since that id from an in-memory ring buffer that holds 30 seconds of history per channel.", "reference", "technical", False,
     [("Server-Sent Events", "protocol"), ("Last-Event-ID", "api"), ("ring buffer", "pattern")],
     [],
     "how does SSE recover missed events after a reconnect and what bounds the replay window on the server",
     "sse last event id reconnect ring buffer replay history channel"),
    # --- 35 ---
    ("The TURN relay is split from the STUN endpoint; coturn runs in TURN-only mode behind a dedicated allowlist while public STUN lives on a tiny Cloudflare worker that just echoes mappings.", "architecture", "technical", False,
     [("TURN relay", "service"), ("STUN", "protocol"), ("coturn", "service"), ("Cloudflare worker", "service")],
     [("coturn", "TURN relay", "IMPLEMENTS"), ("Cloudflare worker", "STUN", "IMPLEMENTS")],
     "how are TURN and STUN split in production and which service hosts each of the two roles",
     "turn stun coturn cloudflare worker relay split mapping allow"),
    # --- 36 ---
    ("We document the precedence: heartbeat at the protocol level, then application-level ping, then TCP keepalive as a last-resort check; each catches a different class of dead connection.", "reference", "technical", False,
     [("heartbeat", "concept"), ("application-level ping", "pattern"), ("TCP keepalive", "concept")],
     [],
     "which three-layer liveness stack do we document and what class of dead connection does each layer catch",
     "heartbeat ping tcp keepalive liveness layer protocol application"),
    # --- 37 ---
    ("Client prefers WebTransport, falls back to WebSocket, then SSE for receive-only, and XHR long-poll as the ancient-browser floor; the ladder is encoded in a single capability probe on boot.", "preference", "technical", False,
     [("WebTransport", "protocol"), ("WebSocket", "protocol"), ("SSE", "protocol"), ("XHR long-poll", "pattern")],
     [("WebTransport", "WebSocket", "PREFERS"), ("WebSocket", "SSE", "PREFERS")],
     "which transport ladder does the client walk at boot and where does XHR long-poll sit in it",
     "webtransport websocket sse xhr long poll ladder capability probe"),
    # --- 38 ---
    ("Prefer NATS JetStream subjects over Kafka topics for realtime fanout; JetStream's lower-latency consumer deliveries and wildcard subjects fit per-room routing better than partitioned logs.", "preference", "technical", False,
     [("NATS JetStream", "service"), ("Kafka", "service"), ("wildcard subjects", "pattern")],
     [("NATS JetStream", "Kafka", "PREFERS")],
     "which streaming system do we prefer over Kafka for realtime room fanout and which routing feature clinched it",
     "nats jetstream kafka wildcard subject room fanout latency partition"),
    # --- 39 ---
    ("A Centrifugo-to-NATS bridge is running in staging so the realtime node can consume business events without opening a second client connection per subscriber on the app side.", "milestone", "technical", False,
     [("Centrifugo", "service"), ("NATS", "service"), ("bridge", "pattern")],
     [("Centrifugo", "NATS", "COMMUNICATES_WITH")],
     "which bridge is in staging so Centrifugo can pick up business events without per-subscriber app connections",
     "centrifugo nats bridge staging business event subscriber connection"),
    # --- 40 ---
    ("Prefer SFU-based group calls over WebRTC mesh beyond three participants; mesh uplink grows as N-1 per sender and the laptop fans gave it away in every 4-way test.", "preference", "technical", False,
     [("SFU", "pattern"), ("WebRTC mesh", "pattern"), ("group calls", "concept")],
     [("SFU", "WebRTC mesh", "PREFERS")],
     "which topology do we prefer past three participants for group calls and what symptom betrayed the alternative",
     "sfu webrtc mesh group call uplink laptop fan four way test"),
    # --- 41 ---
    ("The load test replays a captured WebSocket trace at 10x speed through tsung workers; p99 frame-delivery latency stayed under 120 ms up to 50k concurrent connections on a 16-core node.", "milestone", "technical", False,
     [("WebSocket", "protocol"), ("tsung", "tool"), ("p99", "concept")],
     [("tsung", "WebSocket", "USES")],
     "which load generator replays WebSocket traces at 10x and what p99 latency headroom did it clear at 50k connections",
     "tsung websocket replay load test p99 latency 50k connection"),
    # --- 42 ---
    ("The realtime deploy strategy is drain-and-swap: new pods take connections only after health-check, then old pods send a 1012 Service Restart close so clients reconnect to the new fleet.", "architecture", "technical", False,
     [("drain-and-swap", "pattern"), ("1012 Service Restart", "concept"), ("pod", "infrastructure")],
     [],
     "how does the realtime fleet roll without dropping connections abruptly and which close code does it emit",
     "drain swap realtime deploy 1012 service restart pod health check"),
    # --- 43. noise ---
    ("A food truck parked near the side door claims to do a breakfast burrito that cured someone's hangover last Thursday according to the group chat.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("A WebRTC data-channel memory leak in Chrome 118 held SCTP buffers after close; we pinned the client workaround to explicit RTCPeerConnection.close() after datachannel.close() until 121 shipped the fix.", "problem", "technical", False,
     [("WebRTC", "protocol"), ("Chrome 118", "platform"), ("SCTP", "protocol"), ("RTCPeerConnection", "api")],
     [("RTCPeerConnection", "SCTP", "USES")],
     "which Chrome version held SCTP buffers after datachannel close and what client workaround unblocked us until 121",
     "webrtc chrome 118 sctp data channel close leak workaround 121"),
    # --- 45 ---
    ("mediasoup producer-consumer pairs are bound to the same Worker so transports share a SCTP association; cross-worker pairing is an anti-pattern that doubled SFU CPU in one test.", "reference", "technical", False,
     [("mediasoup", "library"), ("Worker", "concept"), ("SCTP", "protocol"), ("SFU", "pattern")],
     [("mediasoup", "SCTP", "USES")],
     "which mediasoup pairing rule keeps SCTP associations shared and what does breaking it do to SFU CPU",
     "mediasoup producer consumer worker sctp association cpu double"),
    # --- 46 ---
    ("Phoenix Channels are topic-sharded across the cluster using Horde; a topic is owned by exactly one node at a time and presence CRDT syncs as a separate layer on top.", "decision", "technical", False,
     [("Phoenix Channels", "framework"), ("Horde", "library"), ("topic-sharded", "pattern"), ("presence CRDT", "pattern")],
     [("Phoenix Channels", "Horde", "USES")],
     "how does Phoenix Channels partition topics across the cluster and where does presence sit relative to that sharding",
     "phoenix channel horde topic shard cluster presence crdt layer"),
    # --- 47 ---
    ("Prefer WebSocket close code 4000-4999 range for application-defined reasons; the IANA-assigned 1000-series is reserved and using 1011 as a generic error was fooling our monitoring filters.", "preference", "technical", False,
     [("WebSocket", "protocol"), ("close code", "concept"), ("IANA", "organization"), ("1011", "concept")],
     [],
     "which close-code range do we prefer for application-defined reasons and which misuse tripped monitoring filters",
     "websocket close code 4000 1011 iana application reserved monitor"),
    # --- 48 ---
    ("Wrote a reference one-pager: when to pick SSE versus WebSocket versus WebTransport for a given feature, with rows on directionality, reconnect cost, and proxy-friendliness noted.", "reference", "technical", False,
     [("SSE", "protocol"), ("WebSocket", "protocol"), ("WebTransport", "protocol")],
     [],
     "which decision one-pager covers SSE versus WebSocket versus WebTransport and what axes does it score them on",
     "sse websocket webtransport reference one pager direction reconnect"),
    # --- 49 ---
    ("Room sharding in the Ably-backed mobile SDK uses a consistent-hash of room id to a fixed set of channel shards; hot rooms get pinned manually to avoid shard-boundary latency during promos.", "architecture", "technical", False,
     [("Ably", "service"), ("consistent-hash", "algorithm"), ("channel shards", "pattern")],
     [("Ably", "consistent-hash", "USES")],
     "how does the Ably-backed SDK assign rooms to channel shards and how are hot rooms handled during promotions",
     "ably consistent hash channel shard hot room promo pin mobile"),
    # --- 50 ---
    ("Hit a WebRTC ICE-restart storm when a corporate firewall flap rewrote the STUN-mapped port every 30 seconds; adding a per-session ICE-restart cooldown of 60s stopped the thundering herd.", "problem", "technical", False,
     [("WebRTC", "protocol"), ("ICE-restart", "pattern"), ("STUN", "protocol"), ("cooldown", "config")],
     [("ICE-restart", "STUN", "RELATED_TO")],
     "which storm pattern did a firewall port-rewrite trigger and what cooldown knob tamed the thundering herd",
     "webrtc ice restart storm stun port firewall cooldown thundering"),
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
