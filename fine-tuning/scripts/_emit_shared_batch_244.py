"""One-off emitter for shared-base batch-244 — technical domain (microservices architectural patterns: Strangler Fig, ACL, Bounded Contexts, DDD, CQRS, Event Sourcing, Outbox/Inbox, Saga, BFF, API Gateway, Service Discovery, Circuit Breaker, Bulkhead, Retry/Timeout, Idempotency, DLQ, Sidecar, Ambassador, Compensating Transactions, Aggregate Roots).

Writes 50 rows to data/v2/shared/batch_244.tmp.jsonl with ids shared-12151..12200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_244.tmp.jsonl"
ID_OFFSET = 12150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Adopted the Strangler Fig pattern to peel routes off the legacy monolith one at a time; the new payments service now fronts checkout while the rest of the PHP codebase keeps serving everything else.", "decision", "technical", False,
     [("Strangler Fig", "pattern"), ("monolith", "pattern"), ("payments service", "service"), ("PHP", "language")],
     [("Strangler Fig", "monolith", "REPLACES"), ("payments service", "Strangler Fig", "USES")],
     "which migration pattern did the team pick to peel routes off the legacy monolith incrementally",
     "strangler fig monolith payments checkout legacy php incremental"),
    # --- 2 architecture ---
    ("An Anti-Corruption Layer sits between the new order service and the legacy ERP; inbound SAP payloads get translated into the order domain model so the ERP's naming quirks never leak past the boundary.", "architecture", "technical", False,
     [("Anti-Corruption Layer", "pattern"), ("order service", "service"), ("ERP", "service"), ("SAP", "technology")],
     [("Anti-Corruption Layer", "SAP", "APPLIES_TO"), ("order service", "Anti-Corruption Layer", "USES")],
     "how does the new order service shield itself from the legacy SAP naming quirks",
     "anti corruption layer order erp sap translate boundary legacy"),
    # --- 3 architecture ---
    ("Bounded Contexts were drawn around Billing, Shipping, and Inventory during the DDD workshop; the shared Customer concept has a different shape in each context rather than one mega-entity across the monolith.", "architecture", "technical", False,
     [("Bounded Contexts", "pattern"), ("Billing", "service"), ("Shipping", "service"), ("Inventory", "service"), ("DDD", "theory"), ("Customer", "concept")],
     [("Bounded Contexts", "DDD", "USES")],
     "which DDD technique let Billing, Shipping, and Inventory each carry their own Customer shape",
     "bounded context ddd billing shipping inventory customer domain split"),
    # --- 4 decision ---
    ("Picked CQRS for the catalog service after read traffic outpaced writes 400 to 1; the command side stays in Postgres while the query side fans out denormalised projections into Elasticsearch.", "decision", "technical", False,
     [("CQRS", "pattern"), ("catalog service", "service"), ("Postgres", "database"), ("Elasticsearch", "database")],
     [("catalog service", "CQRS", "USES"), ("CQRS", "Elasticsearch", "APPLIES_TO")],
     "which read-write split pattern did catalog adopt once reads dwarfed writes 400 to 1",
     "cqrs catalog read write split postgres elasticsearch projection"),
    # --- 5 architecture ---
    ("Event Sourcing backs the ledger service: every debit and credit is an append-only event, and the current balance is a fold over the stream rather than a mutable row in a table.", "architecture", "technical", False,
     [("Event Sourcing", "pattern"), ("ledger service", "service"), ("append-only", "pattern"), ("fold", "concept")],
     [("ledger service", "Event Sourcing", "USES")],
     "how does the ledger service compute current balances without a mutable row",
     "event sourcing ledger append only fold balance stream debit credit"),
    # --- 6 decision ---
    ("Replaced the dual-write to Postgres and Kafka with the Outbox pattern; the service writes the event row inside the same transaction as the business row, and a relay tails the table into the broker.", "decision", "technical", False,
     [("Outbox pattern", "pattern"), ("Postgres", "database"), ("Kafka", "service"), ("dual-write", "pattern"), ("relay", "pattern")],
     [("Outbox pattern", "dual-write", "REPLACES"), ("relay", "Kafka", "APPLIES_TO")],
     "which pattern killed the dual-write race between Postgres and Kafka for transactional publishing",
     "outbox pattern dual write postgres kafka relay transaction publish"),
    # --- 7 fact ---
    ("The Inbox pattern deduplicates incoming events on the fulfillment side: the consumer stashes each event id in an inbox table inside the same transaction as the handler, so redeliveries become no-ops.", "fact", "technical", False,
     [("Inbox pattern", "pattern"), ("fulfillment", "service"), ("event id", "concept"), ("inbox table", "pattern")],
     [("fulfillment", "Inbox pattern", "USES")],
     "how does the fulfillment consumer make broker redeliveries idempotent at the database level",
     "inbox pattern fulfillment event id dedupe table consumer redeliver"),
    # --- 8 decision ---
    ("Chose Saga orchestration over choreography for the cross-service order flow; a central OrderOrchestrator state machine is easier to debug than chasing events through seven listeners when a step fails.", "decision", "technical", False,
     [("Saga", "pattern"), ("orchestration", "pattern"), ("choreography", "pattern"), ("OrderOrchestrator", "service")],
     [("orchestration", "choreography", "PREFERS"), ("OrderOrchestrator", "Saga", "USES")],
     "which Saga flavour won for the cross-service order flow and what debuggability argument sealed it",
     "saga orchestration choreography order orchestrator debug listener flow"),
    # --- 9 architecture ---
    ("A Backend-For-Frontend service sits in front of the mobile app: it collapses four downstream calls into one screen payload, so the phone doesn't burn radio time chaining requests on a flaky LTE link.", "architecture", "technical", False,
     [("Backend-For-Frontend", "pattern"), ("mobile app", "service"), ("LTE", "protocol")],
     [("mobile app", "Backend-For-Frontend", "USES")],
     "which edge-service pattern cuts the mobile app's request chaining on flaky LTE to a single screen call",
     "backend for frontend bff mobile app lte collapse downstream screen"),
    # --- 10 noise ---
    ("The office espresso machine has started whining on the steam cycle and the facilities ticket has been open for three weeks with no movement.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("The API Gateway pattern is handled by Kong in front of the internal services; it centralises auth, rate limiting, and request shaping so each service stops reimplementing its own JWT middleware.", "architecture", "technical", False,
     [("API Gateway", "pattern"), ("Kong", "service"), ("JWT", "protocol")],
     [("Kong", "API Gateway", "USES")],
     "which edge product fronts the internal mesh so token validation and throttling stop living inside every downstream codebase",
     "api gateway kong jwt auth rate limit centralise middleware"),
    # --- 12 decision ---
    ("Switched the service registry from Eureka to Consul after the Eureka self-preservation mode kept masking real node failures during the network partition drill.", "decision", "technical", False,
     [("Eureka", "service"), ("Consul", "service"), ("service registry", "pattern"), ("self-preservation", "pattern")],
     [("Consul", "Eureka", "REPLACES")],
     "what registry did the platform move to once the prior tool's preservation mode hid dead nodes during the partition drill",
     "consul eureka service registry self preservation partition drill failure"),
    # --- 13 fact ---
    ("Client-side load balancing with Spring Cloud LoadBalancer replaced the old nginx round-robin for internal traffic; callers pull the live Consul list and pick a healthy node per request.", "fact", "technical", False,
     [("Spring Cloud LoadBalancer", "library"), ("nginx", "service"), ("Consul", "service"), ("Client-side load balancing", "pattern")],
     [("Spring Cloud LoadBalancer", "nginx", "REPLACES")],
     "how does the internal call path pick a healthy node now that nginx round-robin is gone",
     "spring cloud load balancer client side nginx consul node healthy"),
    # --- 14 decision ---
    ("Adopted resilience4j for Circuit Breaker wrapping on the payment gateway client; Hystrix is in maintenance mode and we needed the reactive Mono integration for the WebFlux stack.", "decision", "technical", False,
     [("resilience4j", "library"), ("Circuit Breaker", "pattern"), ("Hystrix", "library"), ("WebFlux", "framework"), ("Mono", "concept")],
     [("resilience4j", "Hystrix", "REPLACES"), ("resilience4j", "Circuit Breaker", "USES")],
     "which circuit-breaker library replaced Hystrix and which reactive integration drove the pick",
     "resilience4j circuit breaker hystrix webflux mono reactive payment"),
    # --- 15 reference ---
    ("Polly implements the Circuit Breaker, Retry, and Timeout policies on the .NET side per the official resilience-strategies guide; each HttpClient gets a composed pipeline rather than hand-rolled try-catch.", "reference", "technical", False,
     [("Polly", "library"), ("Circuit Breaker", "pattern"), ("Retry", "pattern"), ("Timeout", "pattern"), (".NET", "framework"), ("HttpClient", "api")],
     [("Polly", "Circuit Breaker", "USES"), ("HttpClient", "Polly", "USES")],
     "which .NET library composes Circuit Breaker, Retry, and Timeout into an HttpClient pipeline",
     "polly dotnet circuit breaker retry timeout httpclient pipeline resilience"),
    # --- 16 milestone ---
    ("Rolled the Bulkhead pattern out across the platform on 2025-10-12 by moving slow reporting queries to a dedicated thread pool; the month-end close that weekend ran without starving the checkout path for the first time.", "milestone", "technical", False,
     [("Bulkhead", "pattern"), ("reporting", "service"), ("thread pool", "pattern"), ("checkout", "service"), ("2025-10-12", "date")],
     [("Bulkhead", "reporting", "APPLIES_TO")],
     "which isolation rollout finally let the month-end close avoid starving checkout threads",
     "bulkhead reporting thread pool checkout starve month end rollout october"),
    # --- 17 decision ---
    ("Set per-hop Timeouts to 800 ms with a 200 ms jitter on Retry; blindly retrying with no jitter stacked thundering-herd waves on the auth service during the 2025-11-04 partial outage.", "decision", "technical", False,
     [("Timeout", "pattern"), ("Retry", "pattern"), ("jitter", "pattern"), ("auth service", "service"), ("thundering-herd", "pattern"), ("2025-11-04", "date")],
     [("jitter", "thundering-herd", "FIXES")],
     "which retry tweak stopped the auth service from seeing thundering-herd waves after the 2025-11-04 outage",
     "timeout retry jitter auth thundering herd outage hop millisecond"),
    # --- 18 fact ---
    ("Idempotency keys are required on every mutating public API call; the server stashes the key with the response for 24 hours so a client replay after a network hiccup returns the first result, not a duplicate charge.", "fact", "technical", False,
     [("Idempotency keys", "pattern"), ("public API", "service"), ("network hiccup", "pattern")],
     [],
     "how do mutating public API endpoints prevent duplicate charges when a client replays after a network hiccup",
     "idempotency key public api replay duplicate charge cache server hour"),
    # --- 19 preference ---
    ("Team stance on Exactly-once processing is that Kafka Streams only gives it inside one cluster, so every consumer must ship idempotent handlers anyway; we never market exactly-once end-to-end to downstream teams.", "preference", "technical", False,
     [("Exactly-once processing", "pattern"), ("Kafka Streams", "framework"), ("idempotent handlers", "pattern")],
     [("Kafka Streams", "Exactly-once processing", "USES")],
     "which stance does the team take on exactly-once semantics for consumers outside a single Kafka cluster",
     "exactly once kafka streams cross cluster idempotent handler stance team"),
    # --- 20 architecture ---
    ("Competing consumers scale the order-fulfillment workers horizontally: a single Kafka partition count caps the parallelism, so we moved high-fanout topics to 48 partitions during the Black Friday ramp-up.", "architecture", "technical", False,
     [("Competing consumers", "pattern"), ("order-fulfillment", "service"), ("Kafka", "service"), ("partition", "concept"), ("Black Friday", "date")],
     [("order-fulfillment", "Competing consumers", "USES")],
     "which consumer pattern scales the order-fulfillment workers and which Kafka knob caps their parallelism",
     "competing consumer order fulfillment kafka partition parallel black friday"),
    # --- 21 decision ---
    ("Routing poison-pill messages to a Dead Letter Queue is mandatory for every consumer group; the earlier habit of blocking the partition on a bad payload wedged the whole topic for hours on 2025-08-14.", "decision", "technical", False,
     [("Dead Letter Queue", "pattern"), ("poison-pill", "pattern"), ("consumer group", "concept"), ("partition", "concept"), ("2025-08-14", "date")],
     [("Dead Letter Queue", "poison-pill", "APPLIES_TO")],
     "which mandatory rule prevents poison-pill messages from wedging a partition the way they did on 2025-08-14",
     "dead letter queue dlq poison pill consumer group partition wedge"),
    # --- 22 milestone ---
    ("Shipped Transactional messaging to every write path on 2025-09-30 so the database commit and the broker publish travel through the outbox-relay pair; a service never acks the client until the event row is durably committed locally.", "milestone", "technical", False,
     [("Transactional messaging", "pattern"), ("outbox-relay", "pattern"), ("broker", "service"), ("event row", "concept"), ("2025-09-30", "date")],
     [("Transactional messaging", "outbox-relay", "USES")],
     "which rollout on 2025-09-30 bound the database commit to the broker publish through the outbox-relay pair",
     "transactional messaging outbox relay broker commit event row ship september"),
    # --- 23 fact ---
    ("Each pod runs an Envoy Sidecar for mTLS, tracing, and retry policy; application code stops carrying the retry loop because the Sidecar enforces the service mesh policy centrally.", "fact", "technical", False,
     [("Envoy", "service"), ("Sidecar", "pattern"), ("mTLS", "protocol"), ("service mesh", "pattern")],
     [("Envoy", "Sidecar", "USES"), ("Sidecar", "mTLS", "APPLIES_TO")],
     "which sidecar proxy handles mTLS and retry policy so application code stops carrying the loop itself",
     "envoy sidecar mtls tracing retry service mesh policy central pod"),
    # --- 24 decision ---
    ("Added an Ambassador proxy in front of the legacy SOAP billing endpoint; new services speak REST to the Ambassador and it handles the WS-Security handshake the old server still requires.", "decision", "technical", False,
     [("Ambassador", "pattern"), ("SOAP", "protocol"), ("billing endpoint", "service"), ("REST", "protocol"), ("WS-Security", "protocol")],
     [("Ambassador", "SOAP", "APPLIES_TO"), ("Ambassador", "REST", "USES")],
     "which pattern lets new REST services talk to a legacy SOAP billing endpoint without reimplementing WS-Security",
     "ambassador soap billing rest ws security handshake legacy proxy"),
    # --- 25 decision ---
    ("Went shared-nothing for the tenant data stores; the brief shared-database phase during migration kept producing lock contention between tenants and multi-tenant queries slipped past the isolation boundary.", "decision", "technical", False,
     [("shared-nothing", "pattern"), ("shared-database", "pattern"), ("tenant", "concept"), ("lock contention", "pattern")],
     [("shared-nothing", "shared-database", "REPLACES")],
     "which data-ownership model replaced the shared-database phase after cross-tenant lock contention flared up",
     "shared nothing shared database tenant lock contention isolation migration"),
    # --- 26 architecture ---
    ("Saga rollback uses compensating transactions rather than distributed 2PC; on a payment failure the orchestrator emits ReleaseInventory and RefundPreauth instead of trying to roll back across services atomically.", "architecture", "technical", False,
     [("compensating transactions", "pattern"), ("2PC", "protocol"), ("ReleaseInventory", "api"), ("RefundPreauth", "api"), ("orchestrator", "service")],
     [("compensating transactions", "2PC", "REPLACES"), ("orchestrator", "compensating transactions", "USES")],
     "how does the Saga orchestrator roll back across services without resorting to distributed 2PC",
     "compensating transaction saga 2pc orchestrator release inventory refund"),
    # --- 27 reference ---
    ("Aggregate roots in the Order service follow Vaughn Vernon's Implementing Domain-Driven Design rules verbatim: line items, shipping addresses, and payment methods mutate only through the Order root, never by reaching into children from the outside.", "reference", "technical", False,
     [("Aggregate roots", "pattern"), ("Order service", "service"), ("line items", "concept"), ("Vaughn Vernon", "person"), ("Implementing Domain-Driven Design", "publication")],
     [("Order service", "Aggregate roots", "USES")],
     "which book does the Order service cite as the canonical rulebook for aggregate-root mutation discipline",
     "aggregate root order line item ddd vaughn vernon canonical"),
    # --- 28 decision ---
    ("Event-carried state transfer replaced the chatty sync lookup to the customer service; the profile payload rides on every OrderPlaced event so downstream consumers don't hit the customer API for basic fields.", "decision", "technical", False,
     [("Event-carried state transfer", "pattern"), ("customer service", "service"), ("OrderPlaced", "api"), ("profile payload", "concept")],
     [("Event-carried state transfer", "customer service", "REPLACES")],
     "which messaging pattern cut the chatty sync lookups to the customer service during order processing",
     "event carried state transfer customer order placed profile payload"),
    # --- 29 milestone ---
    ("Cut over the final legacy checkout route behind the Strangler Fig on 2026-02-18; the old ColdFusion application was retired the following Friday after a week with zero routed traffic.", "milestone", "technical", False,
     [("Strangler Fig", "pattern"), ("checkout route", "service"), ("ColdFusion", "language"), ("2026-02-18", "date")],
     [],
     "which date did the Strangler Fig reach the final legacy checkout route and when did ColdFusion get retired",
     "strangler fig coldfusion cut over checkout route retire 2026 february"),
    # --- 30 preference ---
    ("Team preference is orchestration-first for new sagas; choreography is only approved when the interaction is genuinely two-service and unlikely to grow, because our past three-party choreographies all drifted toward unreadable.", "preference", "technical", False,
     [("orchestration", "pattern"), ("choreography", "pattern"), ("saga", "pattern")],
     [("orchestration", "choreography", "PREFERS")],
     "which default does the team take for new sagas and when is choreography allowed as an exception",
     "orchestration first choreography saga two service preference unread"),
    # --- 31 architecture ---
    ("DDD ubiquitous language is enforced in the API contracts: the same word means the same thing in a Protobuf message, a REST schema, and a Kafka event within a Bounded Context.", "architecture", "technical", False,
     [("DDD", "theory"), ("ubiquitous language", "pattern"), ("Protobuf", "library"), ("REST", "protocol"), ("Kafka", "service"), ("Bounded Context", "pattern")],
     [("ubiquitous language", "Bounded Context", "APPLIES_TO")],
     "which DDD tenet keeps Protobuf messages, REST schemas, and Kafka events consistent inside one Bounded Context",
     "ddd ubiquitous language protobuf rest kafka bounded context contract"),
    # --- 32 reference ---
    ("Greg Young's Event Sourcing talk is the canonical reference in the wiki: it grounds why the event log is the source of truth and snapshots are a cache, not the other way around.", "reference", "technical", False,
     [("Greg Young", "person"), ("Event Sourcing", "pattern"), ("event log", "concept"), ("snapshots", "pattern")],
     [],
     "which canonical talk anchors the team's understanding of the event log as source of truth",
     "greg young event sourcing talk source truth log snapshot cache"),
    # --- 33 reference ---
    ("Eric Evans' Domain-Driven Design blue book is the onboarding reading for new service owners; chapters on Bounded Contexts and Aggregates are mandatory before the architecture review.", "reference", "technical", False,
     [("Eric Evans", "person"), ("Domain-Driven Design", "theory"), ("Bounded Contexts", "pattern"), ("Aggregates", "pattern")],
     [],
     "which book and chapters are the onboarding prerequisite before an architecture review for a new service",
     "eric evans domain driven design book bounded context aggregate review"),
    # --- 34 milestone ---
    ("Hit 99.95% delivery success on the Outbox relay to Kafka for three straight months; the remaining misses traced to planned broker rebalances and the inbox dedup swallowed them on replay.", "milestone", "technical", False,
     [("Outbox relay", "pattern"), ("Kafka", "service"), ("inbox dedup", "pattern"), ("broker", "service")],
     [],
     "which delivery figure did the Outbox relay sustain against Kafka and how were the remaining misses absorbed",
     "outbox relay kafka delivery success broker rebalance inbox dedup"),
    # --- 35 fact ---
    ("The circuit breaker on the payment gateway trips after 20 consecutive failures in a 10-second window and stays open for 30 seconds before a half-open probe; resilience4j config lives in application.yml.", "fact", "technical", False,
     [("circuit breaker", "pattern"), ("payment gateway", "service"), ("resilience4j", "library"), ("application.yml", "file"), ("half-open", "pattern")],
     [],
     "what thresholds configure the payment-gateway circuit breaker and which file holds the settings",
     "circuit breaker payment gateway resilience4j half open window trip"),
    # --- 36 problem ---
    ("Hystrix fallback swallowed exceptions silently and hid a real bug for two sprints; we added a fallback-invoked counter to Prometheus so a fallback storm is visible on the dashboard within a minute.", "problem", "technical", False,
     [("Hystrix", "library"), ("fallback", "pattern"), ("Prometheus", "service"), ("dashboard", "concept")],
     [("Prometheus", "Hystrix", "APPLIES_TO")],
     "which observability gap did a Hystrix silent fallback cause and how is it now surfaced on the dashboard",
     "hystrix fallback silent prometheus counter dashboard storm sprint bug"),
    # --- 37 fact ---
    ("The BFF for web collapses the product, price, inventory, and review calls into one GraphQL resolver; the mobile BFF keeps REST because the iOS team avoids the GraphQL client footprint on older devices.", "fact", "technical", False,
     [("BFF", "pattern"), ("GraphQL", "protocol"), ("REST", "protocol"), ("iOS", "platform"), ("resolver", "concept")],
     [("BFF", "GraphQL", "USES")],
     "how does the web BFF differ from the mobile BFF in protocol choice and why does iOS avoid GraphQL",
     "bff graphql rest resolver ios web mobile footprint older device"),
    # --- 38 decision ---
    ("Picked Consul Connect for service-to-service mTLS over Istio after the platform team rejected the sidecar-injection complexity; the Consul agents already ran on every node for the registry.", "decision", "technical", False,
     [("Consul Connect", "service"), ("Istio", "service"), ("mTLS", "protocol"), ("Consul", "service")],
     [("Consul Connect", "Istio", "PREFERS")],
     "which service-mesh option beat Istio for mTLS and what existing footprint tipped the decision",
     "consul connect istio mtls sidecar inject agent node registry"),
    # --- 39 fact ---
    ("Kafka's transactional-producer API underpins the outbox on the payments service; the send-and-commit couples the producer commit to the database transaction id so a rollback discards the uncommitted events.", "fact", "technical", False,
     [("Kafka", "service"), ("transactional-producer", "api"), ("outbox", "pattern"), ("payments service", "service")],
     [("payments service", "transactional-producer", "USES")],
     "which Kafka producer feature ties the outbox commit on the payments service to the database transaction",
     "kafka transactional producer outbox payments commit rollback send"),
    # --- 40 milestone ---
    ("The order saga hit 100% compensating-transaction coverage in the chaos drill on 2026-01-21; every step has a tested inverse and injected failures unwind cleanly without manual cleanup.", "milestone", "technical", False,
     [("order saga", "pattern"), ("compensating-transaction", "pattern"), ("chaos drill", "concept"), ("2026-01-21", "date")],
     [],
     "what coverage milestone did the order saga reach in the 2026-01-21 chaos drill",
     "order saga compensating transaction chaos drill coverage january unwind"),
    # --- 41 problem ---
    ("Idempotency keys collided across tenants because the original key scope was global; moving the key to (tenant_id, idempotency_key) composite fixed a near-miss double-charge reported by the billing team.", "problem", "technical", False,
     [("Idempotency keys", "pattern"), ("tenant_id", "concept"), ("billing team", "organization"), ("composite", "pattern")],
     [("composite", "Idempotency keys", "FIXES")],
     "which key scoping change fixed the cross-tenant idempotency collision the billing team caught",
     "idempotency key tenant composite collision double charge billing scope"),
    # --- 42 architecture ---
    ("Service Discovery in dev uses Docker DNS while prod uses Consul; the client library papers over the difference with a provider interface so service code compiles the same in both environments.", "architecture", "technical", False,
     [("Service Discovery", "pattern"), ("Docker", "tool"), ("Consul", "service"), ("provider interface", "pattern")],
     [("provider interface", "Service Discovery", "USES")],
     "which abstraction keeps service code identical while dev uses Docker DNS and prod uses Consul",
     "service discovery docker dns consul provider interface dev prod abstract"),
    # --- 43 noise ---
    ("A bird built a nest in the rooftop satellite dish on the east wing and the weather feed has been sporadic ever since.", "fact", "noise", True, [], [], None, None),
    # --- 44 reference ---
    ("The Microsoft Azure Architecture Center's resiliency patterns page is the team wiki's canonical link for Retry, Circuit Breaker, and Bulkhead guidance on distributed calls.", "reference", "technical", False,
     [("Microsoft Azure Architecture Center", "service"), ("Retry", "pattern"), ("Circuit Breaker", "pattern"), ("Bulkhead", "pattern")],
     [],
     "which public reference is the canonical source on the team wiki for Retry, Circuit Breaker, and Bulkhead",
     "azure architecture center resiliency pattern retry breaker bulkhead wiki"),
    # --- 45 preference ---
    ("Team preference is event-carried state transfer for cross-context reads whenever the data is slow-changing; synchronous lookup is only used for strongly-consistent checks like credit-limit verification.", "preference", "technical", False,
     [("event-carried state transfer", "pattern"), ("cross-context", "pattern"), ("credit-limit verification", "concept"), ("synchronous lookup", "pattern")],
     [("event-carried state transfer", "synchronous lookup", "PREFERS")],
     "when does the team reach for event-carried state transfer versus a synchronous lookup across contexts",
     "event carried state transfer cross context sync lookup credit slow"),
    # --- 46 preference ---
    ("Engineers prefer explicit Timeout and Retry configuration in code over relying on framework defaults; the 2024 incident where a missing Timeout exhausted the Tomcat thread pool left a lasting scar.", "preference", "technical", False,
     [("Timeout", "pattern"), ("Retry", "pattern"), ("Tomcat", "service"), ("thread pool", "pattern")],
     [],
     "which configuration habit did the team lock in after the 2024 Tomcat thread-pool exhaustion",
     "timeout retry explicit code tomcat thread pool incident scar default"),
    # --- 47 milestone ---
    ("Rolled out the Dead Letter Queue dashboard across all 37 consumer groups on 2026-03-05; a single pane now shows rejects per minute and the top three poison payloads per topic.", "milestone", "technical", False,
     [("Dead Letter Queue", "pattern"), ("consumer group", "concept"), ("dashboard", "concept"), ("2026-03-05", "date"), ("poison payloads", "pattern")],
     [],
     "which observability rollout on 2026-03-05 unified Dead Letter Queue views across all consumer groups",
     "dead letter queue dashboard consumer group poison march"),
    # --- 48 problem ---
    ("Event Sourcing projection lag ballooned to 90 seconds during the 2025-12-09 backfill; the fix was to parallelise projections by aggregate id hash rather than one thread per projector.", "problem", "technical", False,
     [("Event Sourcing", "pattern"), ("projection", "pattern"), ("aggregate id", "concept"), ("2025-12-09", "date")],
     [("projection", "aggregate id", "USES")],
     "which parallelisation change cut the 2025-12-09 Event Sourcing projection lag from 90 seconds",
     "event sourcing projection lag backfill aggregate id hash parallel december"),
    # --- 49 milestone ---
    ("All 12 microservices hit the API Gateway auth migration milestone on 2026-02-28; every public JWT validation now goes through Kong instead of per-service filters.", "milestone", "technical", False,
     [("API Gateway", "pattern"), ("Kong", "service"), ("JWT", "protocol"), ("2026-02-28", "date"), ("microservice", "service")],
     [("Kong", "JWT", "USES")],
     "which migration milestone did all 12 microservices hit on 2026-02-28 for gateway-centric JWT auth",
     "api gateway kong jwt microservice migration auth february per service"),
    # --- 50 reference ---
    ("Chris Richardson's microservices.io patterns catalog is linked from the service template README; new services cite the relevant pattern page in their design doc under Prior Art.", "reference", "technical", False,
     [("Chris Richardson", "person"), ("microservices.io", "service"), ("service template", "project"), ("README", "file"), ("Prior Art", "concept")],
     [],
     "which pattern catalog does the service template README point to for the Prior Art section of design docs",
     "chris richardson microservices io pattern catalog readme template design"),
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
