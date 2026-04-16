"""One-off emitter for shared-base batch-169 — technical domain (gRPC and Protocol Buffers: proto3, oneof, FieldMask, wire format, streaming, deadlines, Buf, gRPC-Gateway).

Writes 50 rows to data/v2/shared/batch_169.tmp.jsonl with ids shared-08401..08450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_169.tmp.jsonl"
ID_OFFSET = 8400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the billing service wire format from JSON over HTTP to gRPC with Protobuf; payload shrank by about sixty percent and p99 latency dropped under half on the internal fan-out.", "milestone", "technical", False,
     [("gRPC", "protocol"), ("Protobuf", "library"), ("JSON", "technology"), ("HTTP", "protocol")],
     [("gRPC", "JSON", "REPLACES"), ("gRPC", "Protobuf", "USES")],
     "which wire-format swap cut billing payloads and tail latency on the internal fan-out",
     "grpc protobuf json http billing payload latency fan out"),
    # --- 2 ---
    ("Adopted proto3 across every schema in the monorepo; proto2 survives only in the legacy inventory package where required fields are still load-bearing for a handful of offline pipelines.", "decision", "technical", False,
     [("proto3", "language"), ("proto2", "language"), ("monorepo", "pattern")],
     [("proto3", "proto2", "REPLACES")],
     "which proto syntax version became the monorepo default and where did the older syntax survive",
     "proto3 proto2 monorepo schema default legacy inventory required"),
    # --- 3 ---
    ("Added the optional keyword to scalar fields in the User message so presence can be distinguished from default; the earlier has_field ambiguity broke a patch endpoint twice on zero-value diffs.", "problem", "technical", False,
     [("optional", "config"), ("User", "pattern"), ("has_field", "method")],
     [("optional", "has_field", "FIXES")],
     "which proto3 feature restored presence semantics on the User message and ended the patch-endpoint bugs",
     "optional proto3 presence user message patch has field zero default"),
    # --- 4 ---
    ("The Event message uses a oneof named payload to carry either OrderPlaced, OrderCancelled, or PaymentCaptured; only one variant is set on the wire and generated getters expose the tag.", "architecture", "technical", False,
     [("oneof", "pattern"), ("Event", "pattern"), ("OrderPlaced", "pattern"), ("OrderCancelled", "pattern"), ("PaymentCaptured", "pattern")],
     [("Event", "oneof", "USES")],
     "which protobuf construct models the Event variants so only one payload rides the wire",
     "oneof event order placed cancelled payment captured variant tag"),
    # --- 5 ---
    ("Enum aliases let the Status enum ship STATUS_OK and STATUS_SUCCESS as two names for value one; the allow_alias option was flipped on after the rename fight with the mobile team.", "decision", "technical", False,
     [("Enum aliases", "pattern"), ("Status", "pattern"), ("allow_alias", "config"), ("mobile team", "organization")],
     [("Status", "Enum aliases", "USES")],
     "which protobuf option let the Status enum carry two names for the same tag value",
     "enum alias status allow_alias success ok mobile rename value"),
    # --- 6 ---
    ("FieldMask drives partial updates on the Profile API; the server applies only the listed paths so clients can PATCH a single field without round-tripping the full message.", "architecture", "technical", False,
     [("FieldMask", "pattern"), ("Profile", "pattern"), ("PATCH", "method")],
     [("FieldMask", "Profile", "APPLIES_TO")],
     "which well-known type powers partial updates on the Profile API without full-message round trips",
     "field mask profile partial update patch path client server"),
    # --- 7 ---
    ("Varint encoding on the wire cost us one bad day: a negative int32 took ten bytes because two's-complement flipped the high bits; switched the field type to sint32 with zigzag and it dropped to one byte.", "problem", "technical", False,
     [("Varint", "pattern"), ("int32", "pattern"), ("sint32", "pattern"), ("zigzag", "pattern")],
     [("sint32", "int32", "REPLACES"), ("sint32", "zigzag", "USES")],
     "which field-type swap fixed the ten-byte negative-integer blowup on the wire",
     "varint int32 sint32 zigzag negative two complement byte wire"),
    # --- 8 ---
    ("Length-delimited wire type carries every embedded message and string; the framing is a varint length followed by bytes, which is why truncation at the transport shows up as a parse error not silent corruption.", "fact", "technical", False,
     [("Length-delimited", "pattern"), ("varint", "pattern"), ("parse error", "error")],
     [("Length-delimited", "varint", "USES")],
     "how does protobuf frame embedded messages on the wire so truncation surfaces as a parse error",
     "length delimited varint frame embedded string truncate parse error"),
    # --- 9 ---
    ("Bidirectional streaming RPCs power the live-trading session: the client streams order intents while the server streams fills and market ticks over the same HTTP/2 stream with back-pressure.", "architecture", "technical", False,
     [("Bidirectional streaming", "pattern"), ("HTTP/2", "protocol"), ("live-trading", "project"), ("back-pressure", "pattern")],
     [("live-trading", "Bidirectional streaming", "USES")],
     "which gRPC streaming flavour drives the live-trading session with back-pressure on a single stream",
     "bidirectional stream live trading http2 order fill back pressure"),
    # --- 10. noise ---
    ("The office coffee grinder has developed a rattle that correlates with the espresso queue depth somehow and nobody can explain why.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Server-streaming RPC drives the search-results feed; a single request opens a stream and the server pushes ranked batches until it decides the query is exhausted or the deadline fires.", "architecture", "technical", False,
     [("Server-streaming", "pattern"), ("search-results", "project"), ("deadline", "concept")],
     [("search-results", "Server-streaming", "USES")],
     "which gRPC streaming model powers the search-results feed and how does it terminate",
     "server stream search result rank batch deadline exhaust push"),
    # --- 12 ---
    ("Client-streaming RPC handles bulk telemetry ingest: agents stream samples into the collector and the server returns a single ack summary once the client closes the send side.", "architecture", "technical", False,
     [("Client-streaming", "pattern"), ("telemetry", "service"), ("collector", "service")],
     [("telemetry", "Client-streaming", "USES")],
     "which gRPC streaming pattern powers bulk telemetry ingest into the collector",
     "client stream telemetry collector sample ingest ack summary close"),
    # --- 13 ---
    ("Unary RPC still carries ninety percent of internal calls; the streaming flavours get pulled out only where request-response framing would force awkward pagination loops or chunked uploads.", "fact", "technical", False,
     [("Unary RPC", "pattern"), ("pagination", "pattern"), ("chunked upload", "pattern")],
     [],
     "which gRPC call style stays the default internally and which cases push us toward streaming",
     "unary rpc default streaming pagination chunk upload internal"),
    # --- 14 ---
    ("Every server RPC sets a deadline propagated from the caller; handlers that exceed the remaining budget cancel downstream work instead of spending cycles on a response nobody will read.", "architecture", "technical", False,
     [("deadline", "concept"), ("RPC", "protocol"), ("handler", "pattern")],
     [],
     "how does the gRPC server avoid wasted work after a caller's deadline has already expired",
     "deadline propagate rpc handler cancel downstream budget caller"),
    # --- 15 ---
    ("Retry policy lives in the service config JSON: idempotent methods get up to three attempts on UNAVAILABLE, and exponential backoff with jitter avoids retry storms during regional brown-outs.", "decision", "technical", False,
     [("Retry policy", "pattern"), ("service config", "config"), ("exponential backoff", "algorithm"), ("UNAVAILABLE", "error")],
     [("Retry policy", "exponential backoff", "USES")],
     "how does the service config define retries for idempotent methods and what keeps storms off the backend",
     "retry policy service config unavailable exponential backoff jitter"),
    # --- 16 ---
    ("Backoff jitter is full-jitter not equal-jitter; the synchronised retry spikes we saw on the old client stopped once every caller's delay was uniform over the full window instead of half.", "problem", "technical", False,
     [("full-jitter", "algorithm"), ("equal-jitter", "algorithm"), ("Backoff", "pattern")],
     [("full-jitter", "equal-jitter", "REPLACES")],
     "which jitter scheme replaced equal-jitter and why did it kill the synchronised retry spikes",
     "full jitter equal jitter backoff retry spike synchronise window"),
    # --- 17 ---
    ("Client-side load balancing uses round_robin on a headless Kubernetes Service; pick_first kept pinning whole clients to one replica and the hotspot made the p99 graph useless.", "decision", "technical", False,
     [("round_robin", "algorithm"), ("pick_first", "algorithm"), ("Kubernetes", "platform")],
     [("round_robin", "pick_first", "REPLACES")],
     "which gRPC load-balancing policy replaced pick_first and what hotspot did it fix on Kubernetes",
     "round robin pick first kubernetes headless service hotspot p99"),
    # --- 18 ---
    ("Moved the fleet to xDS-based load balancing backed by the in-house control plane; round_robin on headless Services didn't give us locality-aware routing and cross-AZ traffic cost was climbing fast.", "decision", "technical", False,
     [("xDS", "protocol"), ("control plane", "service"), ("round_robin", "algorithm"), ("locality-aware routing", "pattern")],
     [("xDS", "round_robin", "REPLACES")],
     "which load-balancing upgrade replaced round_robin to cut cross-AZ traffic with locality-aware routing",
     "xds control plane round robin locality routing cross az cost"),
    # --- 19 ---
    ("Interceptors handle auth, tracing, and metrics on every call; the per-handler boilerplate got retired and a new cross-cutting concern lands as one interceptor in the chain rather than dozens of edits.", "architecture", "technical", False,
     [("interceptor", "pattern"), ("auth", "concept"), ("tracing", "concept"), ("metrics", "concept")],
     [],
     "which gRPC pattern absorbs auth, tracing, and metrics without editing every handler",
     "interceptor auth tracing metric chain cross cut handler boiler"),
    # --- 20 ---
    ("Browser clients call the same gRPC backend through gRPC-Web; an Envoy-side proxy translates between the text framing and native gRPC over HTTP/2 without a bespoke gateway per service.", "architecture", "technical", False,
     [("gRPC-Web", "protocol"), ("Envoy", "service"), ("HTTP/2", "protocol"), ("Browser", "platform")],
     [("gRPC-Web", "Envoy", "DEPENDS_ON")],
     "how do browser clients reach the native gRPC backend without a bespoke gateway per service",
     "grpc web envoy proxy browser http2 translate framing native"),
    # --- 21 ---
    ("Picked connect-go over grpc-go for the public edge: Connect speaks gRPC, gRPC-Web, and Connect's own JSON protocol from one handler, so browser and server clients share a single implementation.", "decision", "technical", False,
     [("connect-go", "framework"), ("grpc-go", "framework"), ("Connect", "protocol"), ("gRPC-Web", "protocol")],
     [("connect-go", "grpc-go", "PREFERS")],
     "which Go gRPC framework won for the public edge and which three protocols does it unify",
     "connect go grpc go public edge browser json server handler"),
    # --- 22 ---
    ("Buf CLI replaced protoc for lint, format, and breaking-change detection; the custom Makefile chains that orchestrated protoc plugins across the monorepo finally got deleted.", "milestone", "technical", False,
     [("Buf CLI", "tool"), ("protoc", "tool"), ("Makefile", "file"), ("monorepo", "pattern")],
     [("Buf CLI", "protoc", "REPLACES")],
     "which tool took over from protoc for lint, format, and breaking-change detection on the schemas",
     "buf cli protoc lint format breaking change makefile monorepo"),
    # --- 23 ---
    ("buf.gen.yaml is the single source of truth for codegen: one file lists the go, python, and ts plugins along with their output directories, and a buf generate call in CI regenerates everything.", "architecture", "technical", False,
     [("buf.gen.yaml", "file"), ("codegen", "concept"), ("go", "language"), ("python", "language"), ("ts", "language"), ("buf generate", "command")],
     [("buf.gen.yaml", "codegen", "CONFIGURES")],
     "which config file pins codegen across go, python, and ts plugins in one generate call",
     "buf gen yaml codegen go python ts plugin generate ci output"),
    # --- 24 ---
    ("Schemas are published to the buf.build registry under the org module; downstream repos pull a pinned commit hash via buf dep update so breaking changes never land silently in consumer builds.", "architecture", "technical", False,
     [("buf.build", "platform"), ("buf dep update", "command"), ("commit hash", "concept"), ("org module", "pattern")],
     [("org module", "buf.build", "DEPLOYED_ON")],
     "how do downstream repos consume the shared schemas without picking up silent breaking changes",
     "buf build registry module commit hash dep update consumer pin"),
    # --- 25 ---
    ("Added protoc-gen-go and protoc-gen-go-grpc as managed Buf plugins; the team no longer fights version drift between developer boxes and the CI image because Buf resolves plugins by tag.", "decision", "technical", False,
     [("protoc-gen-go", "tool"), ("protoc-gen-go-grpc", "tool"), ("Buf", "tool"), ("CI", "service")],
     [("Buf", "protoc-gen-go", "CONFIGURES")],
     "how did Buf-managed plugins solve the version-drift fight between developer boxes and CI",
     "protoc gen go grpc buf plugin version drift developer ci tag"),
    # --- 26 ---
    ("grpcurl is the default debug client for on-call: it discovers service descriptors via the reflection API so engineers don't need the .proto files to poke a live handler.", "preference", "technical", False,
     [("grpcurl", "tool"), ("reflection API", "api"), (".proto", "file"), ("on-call", "activity")],
     [("grpcurl", "reflection API", "USES")],
     "which on-call debug client discovers service descriptors without the original proto files on hand",
     "grpcurl reflection api proto debug on call service descriptor"),
    # --- 27 ---
    ("Reflection API is enabled on staging and on-prem support pods but disabled on the public internet edge; leaking the full service catalog to random scanners adds nothing but fingerprinting risk.", "decision", "technical", False,
     [("Reflection API", "api"), ("staging", "infrastructure"), ("public internet edge", "infrastructure")],
     [],
     "where is the gRPC reflection API enabled and why is it off at the public internet edge",
     "reflection api staging public edge fingerprint scanner leak catalog"),
    # --- 28 ---
    ("The gRPC health check protocol runs on every server so the load balancer only routes to replicas reporting SERVING; NOT_SERVING during startup delays traffic until migrations finish.", "architecture", "technical", False,
     [("health check protocol", "protocol"), ("SERVING", "config"), ("NOT_SERVING", "config"), ("load balancer", "service")],
     [("load balancer", "health check protocol", "USES")],
     "which gRPC protocol gates load-balancer traffic until replicas finish startup migrations",
     "health check protocol serving not serving load balancer startup"),
    # --- 29 ---
    ("gRPC-Gateway exposes the same services as HTTP/JSON for partners; annotations on the .proto define the URL mapping and the generated reverse proxy does the translation at the edge.", "architecture", "technical", False,
     [("gRPC-Gateway", "framework"), ("HTTP", "protocol"), ("JSON", "technology"), ("reverse proxy", "pattern"), ("annotations", "config")],
     [("gRPC-Gateway", "HTTP", "USES")],
     "how does the platform expose gRPC services as HTTP/JSON for partners without a hand-written shim",
     "grpc gateway http json reverse proxy annotation partner mapping"),
    # --- 30 ---
    ("Binary-to-text gotcha bit the payments team: logging a Protobuf with the default Go stringer produced non-UTF-8 bytes that corrupted the Loki index; switched to protojson for log lines.", "problem", "technical", False,
     [("Protobuf", "library"), ("protojson", "library"), ("Loki", "service"), ("Go stringer", "method")],
     [("protojson", "Go stringer", "REPLACES")],
     "which Protobuf-to-text change fixed the Loki index corruption from logging raw binary messages",
     "protobuf protojson go stringer loki index log utf 8 binary"),
    # --- 31 ---
    ("Backward compatibility rule: adding a new field is always allowed, renaming a field is never allowed, and changing a field's tag number is a breaking change that Buf breaking catches in CI.", "reference", "technical", False,
     [("Backward compatibility", "concept"), ("tag number", "concept"), ("Buf breaking", "command")],
     [("Buf breaking", "tag number", "APPLIES_TO")],
     "which three Protobuf change rules does the team enforce and which tool catches violations in CI",
     "backward compatibility tag number rename add field buf breaking"),
    # --- 32 ---
    ("Deprecated fields carry the [deprecated = true] option and stay in the schema for two release cycles; a CI lint emits a warning when generated code still references a deprecated field.", "architecture", "technical", False,
     [("deprecated", "config"), ("CI lint", "tool"), ("release cycle", "event")],
     [("CI lint", "deprecated", "USES")],
     "how does the schema handle deprecation so old fields fade out without breaking any live consumer",
     "deprecated field release cycle ci lint warn generated schema"),
    # --- 33 ---
    ("Reserved ranges on the OrderLine message block the previous tag numbers 5 through 7 from being reused; the reservation prevents a future field reintroducing a shape that old decoders will misread.", "architecture", "technical", False,
     [("Reserved", "config"), ("OrderLine", "pattern"), ("tag number", "concept")],
     [("Reserved", "tag number", "APPLIES_TO")],
     "which Protobuf construct on OrderLine blocks old tag numbers from being reused with a new shape",
     "reserved tag number order line reuse decode misread range"),
    # --- 34 ---
    ("The Timestamp and Duration well-known types ship on every time field; wrapping raw int64 epochs in Timestamp made the gateway JSON output RFC3339-compliant without a custom serialiser.", "decision", "technical", False,
     [("Timestamp", "pattern"), ("Duration", "pattern"), ("RFC3339", "protocol"), ("int64 epoch", "pattern")],
     [("Timestamp", "int64 epoch", "REPLACES")],
     "which well-known types standardised time fields and what RFC compliance did they unlock for free",
     "timestamp duration well known int64 epoch rfc3339 gateway json"),
    # --- 35 ---
    ("Error model uses google.rpc.Status with typed details; clients pull a BadRequest detail out of the status rather than parsing free-text messages that drifted across language bindings.", "architecture", "technical", False,
     [("google.rpc.Status", "pattern"), ("BadRequest", "pattern"), ("typed details", "pattern")],
     [],
     "which gRPC error model carries typed details so clients stop parsing free-text messages",
     "google rpc status bad request typed detail error client parse"),
    # --- 36 ---
    ("Metadata headers carry request ids, auth tokens, and trace context; headers go on the initial request and trailers carry the final status metadata at the end of the stream.", "fact", "technical", False,
     [("metadata", "concept"), ("trailer", "pattern"), ("trace context", "pattern")],
     [],
     "how does gRPC split metadata between the request header and the closing trailer frame",
     "metadata header trailer request id auth trace context final"),
    # --- 37 ---
    ("Message size limits default to 4 MiB on both directions; bumped the inbound limit on the import service to 64 MiB because batched CSV uploads kept hitting RESOURCE_EXHAUSTED.", "problem", "technical", False,
     [("Message size", "config"), ("RESOURCE_EXHAUSTED", "error"), ("import service", "service"), ("CSV", "technology")],
     [("Message size", "RESOURCE_EXHAUSTED", "CAUSES")],
     "which gRPC limit bump on the import service stopped the RESOURCE_EXHAUSTED errors on CSV batches",
     "message size 4 mib 64 mib resource exhausted import csv batch"),
    # --- 38 ---
    ("Compression set to gzip per call rather than per connection; the chat-history stream saves about forty percent on egress while the tiny unary health probes skip compression entirely.", "decision", "technical", False,
     [("gzip", "algorithm"), ("chat-history", "service"), ("health probe", "pattern")],
     [("chat-history", "gzip", "USES")],
     "how does per-call compression save egress on chat-history without taxing the tiny health probes",
     "gzip compression per call chat history egress health probe skip"),
    # --- 39 ---
    ("Keep-alive pings are tuned to 30 seconds on the mobile gateway; the earlier 2-hour HTTP/2 default meant carrier NATs aged out the connection and every resume spent a TLS handshake.", "problem", "technical", False,
     [("Keep-alive", "pattern"), ("HTTP/2", "protocol"), ("carrier NAT", "infrastructure"), ("TLS handshake", "concept")],
     [("Keep-alive", "carrier NAT", "FIXES")],
     "which keep-alive change fixed the TLS-handshake thrash caused by carrier NAT timeouts on mobile",
     "keep alive ping 30 second http2 carrier nat tls handshake mobile"),
    # --- 40 ---
    ("TLS terminates at the service itself, not at Envoy, because the service mesh wants mTLS identity end-to-end; the extra handshake cost is paid once per long-lived HTTP/2 connection.", "decision", "technical", False,
     [("TLS", "protocol"), ("Envoy", "service"), ("mTLS", "protocol"), ("service mesh", "pattern"), ("HTTP/2", "protocol")],
     [("service mesh", "mTLS", "USES")],
     "why does TLS terminate at the service rather than at Envoy under the service mesh model",
     "tls envoy mtls service mesh identity end to end http2 connection"),
    # --- 41 ---
    ("Context deadlines flow through the call chain via the incoming metadata; the database driver respects the remaining budget and cancels the query when the deadline is already blown.", "architecture", "technical", False,
     [("Context deadline", "concept"), ("metadata", "concept"), ("database driver", "library")],
     [("database driver", "Context deadline", "USES")],
     "how does the database driver avoid running queries for an already-blown deadline on the call chain",
     "context deadline metadata database driver cancel budget chain"),
    # --- 42 ---
    ("The gRPC status code DEADLINE_EXCEEDED gets a server-side metric with method labels; spikes on one method lit up the slow downstream without trawling traces for every call.", "milestone", "technical", False,
     [("DEADLINE_EXCEEDED", "error"), ("metric", "concept"), ("method label", "config")],
     [],
     "which gRPC status metric exposed the slow downstream method without digging through every trace",
     "deadline exceeded metric method label spike slow downstream trace"),
    # --- 43. noise ---
    ("The kitchen printer ran out of ribbon on a Friday and someone left a hand-drawn sticky note on it that just says 'sad'.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Server reflection plus grpcurl let support engineers script replay of failing prod calls against staging; the same payload captured from the access log gets reissued with a tweaked tenant id.", "fact", "technical", False,
     [("Server reflection", "api"), ("grpcurl", "tool"), ("staging", "infrastructure"), ("tenant id", "concept")],
     [("grpcurl", "Server reflection", "USES")],
     "how do support engineers replay failing prod calls against staging using reflection and grpcurl",
     "server reflection grpcurl staging replay prod payload tenant id"),
    # --- 45 ---
    ("A connection-level streaming bug leaked goroutines on cancelled RPCs; the fix closed the recv loop on context Done rather than waiting for the peer to half-close the stream.", "problem", "technical", False,
     [("goroutine", "concept"), ("recv loop", "pattern"), ("context Done", "method"), ("streaming", "pattern")],
     [("context Done", "goroutine", "FIXES")],
     "which cancellation path fix plugged the goroutine leak on cancelled streaming RPCs",
     "goroutine leak streaming rpc cancel recv loop context done half close"),
    # --- 46 ---
    ("Picked Connect-RPC's JSON codec for the public SDK so partner integrators can curl endpoints while the same handlers still speak native gRPC to our internal callers.", "preference", "technical", False,
     [("Connect-RPC", "framework"), ("JSON", "technology"), ("curl", "tool"), ("SDK", "concept")],
     [("Connect-RPC", "JSON", "USES")],
     "which codec choice on Connect-RPC lets partner integrators curl the public SDK endpoints",
     "connect rpc json codec public sdk curl partner integrator handler"),
    # --- 47 ---
    ("Schema evolution rule on message fields: int32 to int64 is wire-compatible because both encode as varint, but int32 to string is a hard break because the wire type flips to length-delimited.", "reference", "technical", False,
     [("int32", "pattern"), ("int64", "pattern"), ("varint", "pattern"), ("length-delimited", "pattern")],
     [("int32", "int64", "RELATED_TO")],
     "which integer widening stays wire-compatible and which scalar change breaks because the wire type flips",
     "int32 int64 varint length delimited wire compatible evolve schema"),
    # --- 48 ---
    ("Proto imports are pinned by module and commit on buf.build; the old googleapis/api annotations used to live in a vendored tree and drifted out of sync with every protoc upgrade.", "decision", "technical", False,
     [("buf.build", "platform"), ("googleapis", "organization"), ("vendored tree", "pattern"), ("protoc", "tool")],
     [("buf.build", "vendored tree", "REPLACES")],
     "how did buf.build module pinning replace the vendored googleapis tree that drifted with every protoc upgrade",
     "buf build module pin googleapis api vendor drift protoc upgrade"),
    # --- 49 ---
    ("Code review rule: any new RPC method with streaming semantics needs an explicit deadline contract in the doc comment and a corresponding service-config entry, otherwise CI blocks the merge.", "preference", "technical", False,
     [("streaming", "pattern"), ("deadline contract", "concept"), ("service-config", "config"), ("CI", "service")],
     [("CI", "deadline contract", "SUPPORTS")],
     "which review rule forces new streaming RPCs to carry a deadline contract before CI lets them merge",
     "streaming rpc deadline contract doc comment service config ci block"),
    # --- 50 ---
    ("Migrated partner webhooks to gRPC-Gateway so the same Protobuf service definitions drive HTTP/JSON for inbound partner pushes and native gRPC for internal fan-out; the hand-written Flask shim finally got deleted.", "milestone", "technical", False,
     [("gRPC-Gateway", "framework"), ("Protobuf", "library"), ("Flask", "framework"), ("webhook", "pattern"), ("HTTP", "protocol")],
     [("gRPC-Gateway", "Flask", "REPLACES")],
     "which migration retired the Flask webhook shim and unified partner HTTP with native gRPC fan-out",
     "grpc gateway protobuf flask webhook http json partner fan out"),
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
