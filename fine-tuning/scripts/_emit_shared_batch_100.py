"""One-off emitter for shared-base batch-100 — ai_coding domain (DDD / event sourcing / CQRS as code architecture).

Writes 50 rows to data/v2/shared/batch_100.tmp.jsonl with ids shared-04951..05000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_100.tmp.jsonl"
ID_OFFSET = 4950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Carved the billing bounded context out of the monolith with its own ubiquitous language; 'invoice' now means a settled document in billing and a draft work item in sales, and the two are translated at the boundary.", "architecture", "ai_coding", False,
     [("billing", "concept"), ("ubiquitous language", "concept"), ("invoice", "concept"), ("sales", "concept")],
     [("billing", "sales", "COMMUNICATES_WITH")],
     "how did the billing and sales modules reconcile a clashing definition of invoice after the split",
     "bounded context ubiquitous language invoice billing sales translate"),
    # --- 2 ---
    ("Replaced the cross-context direct database view with an anti-corruption layer in the shipping module; shipping now consumes billing's public contract and never peeks at billing tables.", "decision", "ai_coding", False,
     [("anti-corruption layer", "pattern"), ("shipping", "concept"), ("billing", "concept")],
     [("anti-corruption layer", "shipping", "APPLIES_TO"), ("anti-corruption layer", "billing", "REPLACES")],
     "which DDD pattern severed shipping's dependency on billing's private schema",
     "anti corruption layer shipping billing schema cross context replace"),
    # --- 3 ---
    ("Order aggregate root owns its line items and enforces the totals invariant; line items are never mutated directly and the repository only saves the root.", "architecture", "ai_coding", False,
     [("Order", "concept"), ("aggregate root", "concept"), ("line items", "concept"), ("repository", "pattern")],
     [("aggregate root", "Order", "APPLIES_TO")],
     "how does the Order aggregate keep its totals invariant when child line items change",
     "order aggregate root invariant line items repository save root only"),
    # --- 4 ---
    ("Money became a value object with currency and minor-units amount; equality is structural and you can't mutate it, which killed a whole class of FX rounding drift bugs.", "problem", "ai_coding", False,
     [("Money", "concept"), ("value object", "concept"), ("currency", "concept")],
     [("Money", "value object", "IS_A")],
     "which value-object conversion closed the recurring FX rounding drift in the pricing code",
     "money value object immutable minor units currency fx rounding drift"),
    # --- 5 ---
    ("Cited Evans' Blue Book when arguing for a separate context for risk scoring; the 'bounded context' chapter was the exact reference the platform lead needed to sign off on the split.", "reference", "ai_coding", False,
     [("Evans' Blue Book", "publication"), ("risk scoring", "concept"), ("bounded context", "concept")],
     [("bounded context", "Evans' Blue Book", "PUBLISHED_IN")],
     "which DDD book backed the case for giving risk scoring its own bounded context",
     "evans blue book bounded context risk scoring reference split sign off"),
    # --- 6 ---
    ("Adopted Vaughn Vernon's IDDD 'Implementing Domain-Driven Design' chapter on aggregates as the house rule; small aggregates plus eventual consistency between them is the default unless proven otherwise.", "decision", "ai_coding", False,
     [("Vaughn Vernon", "person"), ("IDDD", "publication"), ("aggregates", "concept"), ("eventual consistency", "concept")],
     [("IDDD", "Vaughn Vernon", "AUTHORED_BY")],
     "which book sets the house rule on aggregate size and cross-aggregate consistency",
     "vaughn vernon iddd aggregate small eventual consistency house rule"),
    # --- 7 ---
    ("Replaced the home-grown append-only events table with EventStoreDB; per-stream optimistic concurrency and projections came out of the box instead of being yet another in-house puzzle.", "decision", "ai_coding", False,
     [("EventStoreDB", "database"), ("events table", "concept"), ("projections", "concept")],
     [("EventStoreDB", "events table", "REPLACES")],
     "which event-store product replaced the home-grown Postgres append table and what did it give us for free",
     "eventstoredb replace events table stream optimistic concurrency projection"),
    # --- 8 ---
    ("Marten landed as the event store for the .NET side because the team already ran Postgres; it improves on raw-SQL journaling by handling schema, projections, and inline aggregates.", "architecture", "ai_coding", False,
     [("Marten", "library"), (".NET", "framework"), ("Postgres", "database"), ("journaling", "concept")],
     [("Marten", "journaling", "IMPROVES_ON"), ("Marten", "Postgres", "USES")],
     "which library took over event journaling on the .NET stack and why did it win over raw SQL",
     "marten event store dotnet postgres journal improve projection inline"),
    # --- 9 ---
    ("Axon Framework drives the Java trading module; AxonDB holds the event log and the framework's saga manager runs the long-running settlement flows.", "architecture", "ai_coding", False,
     [("Axon Framework", "framework"), ("Java", "language"), ("AxonDB", "database"), ("saga manager", "pattern")],
     [("Axon Framework", "AxonDB", "USES")],
     "which Java event-sourcing stack runs the trading module and what drives its long-lived flows",
     "axon framework java axondb saga manager trading settlement flow"),
    # --- 10. noise ---
    ("The office coffee machine now hisses a single B-flat whenever the steam wand runs dry.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kurrent joined the evaluation shortlist as the EventStoreDB successor brand; API shape is compatible enough that the client libraries dropped in with only a connection string change.", "fact", "ai_coding", False,
     [("Kurrent", "database"), ("EventStoreDB", "database")],
     [("Kurrent", "EventStoreDB", "REPLACES")],
     "which rebranded successor to EventStoreDB entered the shortlist and how disruptive was the client change",
     "kurrent eventstoredb successor brand client library connection string"),
    # --- 12 ---
    ("CQRS split the order service into a write model keyed on the aggregate and a read model denormalised per UI screen; the ORM-backed aggregate-on-read path is gone.", "architecture", "ai_coding", False,
     [("CQRS", "pattern"), ("write model", "concept"), ("read model", "concept"), ("ORM", "pattern")],
     [("read model", "ORM", "REPLACES"), ("CQRS", "write model", "HAS_PART"), ("CQRS", "read model", "HAS_PART")],
     "how does the order service now separate its read and write shapes and what did it retire",
     "cqrs write model read model denormalised orm aggregate replace"),
    # --- 13 ---
    ("Greg Young's CQRS documents are the canonical reference for the separation; the 'CQRS, Task-Based UIs, Event Sourcing' paper is linked from the module README so newcomers read it before touching the write side.", "reference", "ai_coding", False,
     [("Greg Young", "person"), ("CQRS", "pattern"), ("README", "file")],
     [("CQRS", "Greg Young", "AUTHORED_BY")],
     "which CQRS paper does the write-side README pin as required reading for newcomers",
     "greg young cqrs task based ui event sourcing paper readme"),
    # --- 14 ---
    ("Domain events live in their own package and are named in past tense: OrderPlaced, PaymentCaptured, ShipmentDispatched; no verbs in the imperative mood make it into the event bus.", "preference", "ai_coding", False,
     [("Domain events", "concept"), ("OrderPlaced", "event"), ("PaymentCaptured", "event"), ("ShipmentDispatched", "event")],
     [],
     "which naming rule governs domain-event classes on the bus",
     "domain event past tense order placed payment captured naming rule"),
    # --- 15 ---
    ("Hexagonal architecture was the first structural commit: domain in the centre, ports as interfaces, adapters per transport; the HTTP controller and the Kafka consumer both implement the same inbound port.", "architecture", "ai_coding", False,
     [("Hexagonal architecture", "pattern"), ("ports", "concept"), ("adapters", "concept"), ("HTTP", "protocol"), ("Kafka", "technology")],
     [("HTTP", "ports", "IMPLEMENTS"), ("Kafka", "ports", "IMPLEMENTS")],
     "how do the HTTP controller and Kafka consumer end up driving the same application code",
     "hexagonal architecture port adapter inbound http kafka consumer"),
    # --- 16 ---
    ("Onion architecture layering is enforced by an ArchUnit test that fails the build if domain code imports infrastructure; the rule is more valuable than any diagram in the wiki.", "architecture", "ai_coding", False,
     [("Onion architecture", "pattern"), ("ArchUnit", "tool"), ("domain", "concept"), ("infrastructure", "concept")],
     [("ArchUnit", "Onion architecture", "APPLIES_TO")],
     "which test tool enforces the Onion-architecture layering rule at build time",
     "Onion architecture archunit test domain infrastructure layer enforce"),
    # --- 17 ---
    ("Clean Architecture's use-case interactor pattern replaced the fat service classes; each use case is its own object with an input port, an output port, and a single execute method.", "decision", "ai_coding", False,
     [("Clean Architecture", "pattern"), ("use-case interactor", "pattern"), ("service classes", "pattern")],
     [("use-case interactor", "service classes", "REPLACES")],
     "which structural pattern replaced the fat service classes on the application layer",
     "clean architecture use case interactor input port service class replace"),
    # --- 18 ---
    ("Repository interfaces sit in the domain package and concrete JPA implementations live in infrastructure; the domain compiles without the persistence jar on the classpath.", "architecture", "ai_coding", False,
     [("Repository", "pattern"), ("domain", "concept"), ("JPA", "framework"), ("infrastructure", "concept")],
     [("JPA", "Repository", "IMPLEMENTS")],
     "how is the repository pattern split between domain and infrastructure in the codebase",
     "repository interface domain jpa infrastructure split classpath"),
    # --- 19 ---
    ("Aggregate reconstitution replays events from the store into a fold; for the shopping cart that grew past ten thousand events we added a snapshot every five hundred events to keep load times sub-second.", "decision", "ai_coding", False,
     [("Aggregate", "concept"), ("snapshot", "pattern"), ("shopping cart", "concept")],
     [("snapshot", "Aggregate", "APPLIES_TO")],
     "which snapshot strategy did the shopping-cart aggregate adopt to keep replay under a second",
     "aggregate replay snapshot every five hundred events shopping cart"),
    # --- 20 ---
    ("Projection rebuilds run through a dedicated 'replay' consumer group; the read database is rebuilt from the event log into a shadow schema and then atomically swapped in.", "architecture", "ai_coding", False,
     [("Projection", "concept"), ("consumer group", "pattern"), ("event log", "concept"), ("shadow schema", "pattern")],
     [("Projection", "event log", "USES")],
     "how does a projection rebuild land without downtime on the read side",
     "projection rebuild consumer group replay shadow schema swap"),
    # --- 21 ---
    ("Saga for the order-to-cash flow is implemented as a code module with explicit compensation handlers; a choreography-only version tangled the modules together and was rolled back after one sprint.", "problem", "ai_coding", False,
     [("Saga", "pattern"), ("order-to-cash", "concept"), ("compensation", "concept"), ("choreography", "pattern")],
     [("Saga", "choreography", "REPLACES")],
     "which saga style did the order-to-cash flow settle on after choreography got rolled back",
     "saga orchestration compensation choreography rollback order to cash"),
    # --- 22 ---
    ("The Outbox pattern replaced dual-writes between Postgres and Kafka; a relay reads the outbox table inside the same transaction and publishes once per row to the topic.", "decision", "ai_coding", False,
     [("Outbox", "pattern"), ("dual-writes", "pattern"), ("Postgres", "database"), ("Kafka", "technology")],
     [("Outbox", "dual-writes", "REPLACES")],
     "which pattern fixed the Postgres-to-Kafka dual-write race and what sits between them now",
     "outbox pattern dual write replace postgres kafka relay transaction"),
    # --- 23 ---
    ("Read models are keyed per screen: one for the cart icon count, one for the full cart page, one for the admin refund view; join logic lives in projection code, never in the query.", "preference", "ai_coding", False,
     [("Read models", "concept"), ("cart", "concept"), ("refund", "concept"), ("projection", "concept")],
     [],
     "how are read models scoped across the shopping experience and where does join logic live",
     "read model per screen cart refund projection join code preference"),
    # --- 24 ---
    ("Value-object validation throws in the constructor; an EmailAddress can't exist in an invalid state, so downstream handlers never defensively re-check a field they already received typed.", "architecture", "ai_coding", False,
     [("Value-object", "concept"), ("EmailAddress", "concept"), ("constructor", "concept")],
     [("EmailAddress", "Value-object", "IS_A")],
     "which DDD rule lets handlers stop defensive-revalidating fields like EmailAddress",
     "value object constructor throw invalid state email address typed"),
    # --- 25 ---
    ("Aggregate size guidance from Vaughn Vernon's 'Effective Aggregate Design' essays landed as a code-review checklist; 'keep aggregates small, reference other aggregates by id' is item one.", "reference", "ai_coding", False,
     [("Vaughn Vernon", "person"), ("Effective Aggregate Design", "publication"), ("code-review", "pattern")],
     [("Effective Aggregate Design", "Vaughn Vernon", "AUTHORED_BY")],
     "which essays turned into the code-review checklist for aggregate design",
     "effective aggregate design vernon code review checklist reference id"),
    # --- 26 ---
    ("Event schema evolution uses upcasters registered per event type and version; an OrderPlaced_v1 flows through the upcaster chain and surfaces to handlers as the current schema.", "architecture", "ai_coding", False,
     [("upcasters", "pattern"), ("Event schema", "concept"), ("OrderPlaced_v1", "event")],
     [("upcasters", "OrderPlaced_v1", "APPLIES_TO")],
     "how do older event versions reach current handlers without rewriting the store",
     "event schema upcaster version chain order placed v1 handler"),
    # --- 27 ---
    ("Context map diagrams live beside the code as PlantUML checked into /docs/context-map; teams touching a shared kernel update the diagram in the same PR that changes the contract.", "preference", "ai_coding", False,
     [("Context map", "concept"), ("PlantUML", "tool"), ("/docs/context-map", "file"), ("shared kernel", "concept")],
     [],
     "where do context-map diagrams live and when do teams update them",
     "context map plantuml docs shared kernel pull request update"),
    # --- 28 ---
    ("Switched from 'customer' as a shared kernel to a published-language interchange; each context keeps its own customer model and a translator renders it from the upstream contract.", "decision", "ai_coding", False,
     [("shared kernel", "concept"), ("published-language", "concept"), ("customer", "concept"), ("translator", "pattern")],
     [("published-language", "shared kernel", "REPLACES")],
     "which integration pattern replaced the shared-kernel customer model between contexts",
     "published language shared kernel customer translator integration"),
    # --- 29 ---
    ("Domain services hold logic that doesn't fit a single aggregate; pricing calculation takes an Order, a PricingPolicy, and a TaxTable and returns a PriceBreakdown without owning state.", "architecture", "ai_coding", False,
     [("Domain services", "concept"), ("Order", "concept"), ("PricingPolicy", "concept"), ("TaxTable", "concept"), ("PriceBreakdown", "concept")],
     [],
     "how does the pricing calculation live in the domain without belonging to one aggregate",
     "domain service pricing policy tax table price breakdown stateless"),
    # --- 30 ---
    ("Reached milestone: the write side of the orders context is 100% event-sourced; no mutable row is updated in-place and every state change is a diff derived from the event stream.", "milestone", "ai_coding", False,
     [("orders", "concept"), ("event-sourced", "pattern"), ("event stream", "concept")],
     [],
     "which milestone marked the orders context becoming fully event-sourced",
     "orders context event sourced milestone no mutable row stream"),
    # --- 31 ---
    ("Corporeal-world tip from the IDDD book: model the ubiquitous language in whiteboard sessions with domain experts first, then translate to code; skipping step one bit us twice in the billing rewrite.", "problem", "ai_coding", False,
     [("IDDD", "publication"), ("ubiquitous language", "concept"), ("billing", "concept")],
     [],
     "which IDDD practice did we skip twice in the billing rewrite and regret",
     "iddd ubiquitous language whiteboard domain expert billing rewrite"),
    # --- 32 ---
    ("Kafka topics map one-to-one to aggregate types; the key is the aggregate id so per-aggregate ordering survives, and the consumer groups match bounded contexts.", "architecture", "ai_coding", False,
     [("Kafka", "technology"), ("aggregate", "concept"), ("consumer groups", "pattern"), ("bounded contexts", "concept")],
     [("Kafka", "aggregate", "APPLIES_TO")],
     "how does the Kafka topic layout line up with aggregates and contexts",
     "kafka topic aggregate key ordering consumer group bounded context"),
    # --- 33 ---
    ("Command handlers return void and raise events; query handlers are pure functions over read models, cacheable, and never touch the write store even to peek.", "preference", "ai_coding", False,
     [("Command handlers", "pattern"), ("query handlers", "pattern"), ("read models", "concept")],
     [],
     "which discipline separates command and query handlers in the codebase",
     "command handler void event query handler pure cache read model"),
    # --- 34 ---
    ("Replaced the 'update-in-place plus audit log' scheme in inventory with a real event-sourced aggregate; the audit log that was 90% correct is now by construction 100% correct.", "decision", "ai_coding", False,
     [("inventory", "concept"), ("audit log", "concept"), ("event-sourced", "pattern")],
     [("event-sourced", "audit log", "REPLACES")],
     "which inventory pattern swap turned a best-effort audit log into the source of truth",
     "inventory event sourced replace update in place audit log correct"),
    # --- 35 ---
    ("Snapshot strategy for the Account aggregate: snapshot every one thousand events or every seven days, whichever comes first; the dual trigger stops long-idle streams rehydrating forever.", "architecture", "ai_coding", False,
     [("snapshot", "pattern"), ("Account", "concept")],
     [("snapshot", "Account", "APPLIES_TO")],
     "which snapshot cadence covers both busy and long-idle Account streams",
     "snapshot account thousand events seven days idle rehydrate"),
    # --- 36 ---
    ("Cross-context integration events are versioned with semver in the topic name (orders.v2.OrderPlaced); consumers pin a major and are explicit about upgrade windows.", "architecture", "ai_coding", False,
     [("integration events", "concept"), ("semver", "pattern"), ("orders.v2.OrderPlaced", "event")],
     [],
     "how are cross-context event schemas versioned in topic names and what do consumers pin",
     "integration event semver topic name major pin upgrade window"),
    # --- 37 ---
    ("Vernon's Red Book chapter on application services drove the refactor: commands come in through an application service, which loads the aggregate, calls a domain method, and hands off to the repository.", "reference", "ai_coding", False,
     [("Vernon's Red Book", "publication"), ("application services", "concept"), ("repository", "pattern")],
     [("application services", "Vernon's Red Book", "PUBLISHED_IN")],
     "which chapter of Vernon's Red Book shaped the application-service refactor",
     "vernon red book application service command aggregate repository refactor"),
    # --- 38 ---
    ("Policy handlers listen on OrderPlaced and dispatch ReserveStock; the policy is its own class so the domain event and the reaction don't get wired through an ESB config file we never read.", "preference", "ai_coding", False,
     [("Policy handlers", "pattern"), ("OrderPlaced", "event"), ("ReserveStock", "event"), ("ESB", "technology")],
     [("Policy handlers", "ESB", "REPLACES")],
     "how are event-to-command policies expressed in the code instead of an ESB config",
     "policy handler order placed reserve stock esb config replace"),
    # --- 39 ---
    ("Temporal queries are trivial on the event log: 'what did the cart look like at 14:02 on 2026-03-10' is just a fold up to that sequence number, which is the classic event-sourcing superpower.", "fact", "ai_coding", False,
     [("event log", "concept"), ("fold", "concept"), ("2026-03-10", "date")],
     [],
     "which event-sourcing capability makes 'state as of a past timestamp' a one-liner",
     "event log fold temporal query sequence number as of timestamp"),
    # --- 40 ---
    ("Invariants that span aggregates go through a saga with eventual consistency, not a distributed transaction; the book line from Vernon 'do not cross aggregate boundaries in one tx' is pinned in the module doc.", "architecture", "ai_coding", False,
     [("Invariants", "concept"), ("saga", "pattern"), ("distributed transaction", "pattern"), ("Vernon", "person")],
     [("saga", "distributed transaction", "REPLACES")],
     "how are cross-aggregate invariants handled and which quote is pinned in the module docs",
     "invariant saga eventual consistency distributed transaction vernon quote"),
    # --- 41 ---
    ("Replaced the per-entity ORM cascade-save with a unit-of-work that only flushes the aggregate root; orphaned partial saves from cascade misfires finally stopped appearing in support tickets.", "problem", "ai_coding", False,
     [("ORM", "pattern"), ("cascade-save", "pattern"), ("unit-of-work", "pattern"), ("aggregate root", "concept")],
     [("unit-of-work", "cascade-save", "REPLACES")],
     "which ORM behaviour did the unit-of-work replace and what class of ticket did it end",
     "unit of work orm cascade save aggregate root orphan partial ticket"),
    # --- 42 ---
    ("Event names carry the business verb, not the implementation detail; we renamed CartRowUpdated to ItemQuantityAdjusted after a Vernon-style 'speak the language' review.", "decision", "ai_coding", False,
     [("CartRowUpdated", "event"), ("ItemQuantityAdjusted", "event"), ("Vernon", "person")],
     [("ItemQuantityAdjusted", "CartRowUpdated", "REPLACES")],
     "which rename captures the shift from implementation-speak to business verbs in event names",
     "cart row updated item quantity adjusted rename vernon language"),
    # --- 43 ---
    ("Projections are idempotent by construction: every handler checks the projection-offset table before applying, so a replay after a crash never double-counts revenue.", "architecture", "ai_coding", False,
     [("Projections", "concept"), ("projection-offset", "pattern"), ("revenue", "concept")],
     [],
     "how do projections stay idempotent across crashes and replays",
     "projection idempotent offset table replay crash revenue handler"),
    # --- 44 ---
    ("Adopted a 'one aggregate per transaction' rule borrowed straight from IDDD; any story that wants two aggregates in one tx is rewritten as a saga or rejected in review.", "preference", "ai_coding", False,
     [("IDDD", "publication"), ("saga", "pattern"), ("transaction", "concept")],
     [("saga", "transaction", "APPLIES_TO")],
     "which IDDD rule bans multi-aggregate transactions and what replaces them",
     "one aggregate per transaction iddd saga rewrite review rule"),
    # --- 45 ---
    ("The read side runs on Postgres materialised views for slow analytics and on Elasticsearch for free-text search; both are projections from the same event log.", "architecture", "ai_coding", False,
     [("Postgres", "database"), ("materialised views", "pattern"), ("Elasticsearch", "database"), ("event log", "concept")],
     [("materialised views", "event log", "USES"), ("Elasticsearch", "event log", "USES")],
     "which two read-side stores feed off the single event log and what does each specialise in",
     "postgres materialised view elasticsearch projection event log read side"),
    # --- 46 ---
    ("Command validation splits into syntactic (Pydantic) and domain (aggregate method); rejecting a malformed payload never reaches the aggregate, and the aggregate never re-checks shape.", "architecture", "ai_coding", False,
     [("Pydantic", "library"), ("aggregate", "concept"), ("Command", "concept")],
     [],
     "where does syntactic versus domain validation split when a command arrives",
     "command validation pydantic syntactic aggregate domain method split"),
    # --- 47 ---
    ("Event payloads carry only the facts the domain produced, not derived aggregates; consumers compute their own read shapes, which stopped the 'event became an API' smell cold.", "decision", "ai_coding", False,
     [("Event payloads", "concept"), ("consumers", "concept"), ("API", "concept")],
     [],
     "which event-design rule stopped the 'event became an API' drift between services",
     "event payload fact derived consumer shape api smell rule"),
    # --- 48 ---
    ("Ran a context-storming workshop with three domain experts in one room; the sticky-note walls became the first context map and kicked off two bounded-context renames within a week.", "milestone", "ai_coding", False,
     [("context-storming", "activity"), ("domain experts", "person"), ("context map", "concept"), ("bounded-context", "concept")],
     [],
     "which workshop produced the first context map and what concrete renames did it trigger",
     "context storming workshop domain expert sticky note context map rename"),
    # --- 49. noise ---
    ("Someone left a rubber duck wearing a tiny knit scarf on top of the fridge in the kitchen.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Outbox relay runs as a sidecar that tails the outbox table via logical replication; the relay pushes to Kafka and marks rows delivered in a second tx, giving at-least-once without dual-write hazards.", "architecture", "ai_coding", False,
     [("Outbox", "pattern"), ("sidecar", "pattern"), ("logical replication", "pattern"), ("Kafka", "technology")],
     [("sidecar", "Outbox", "IMPLEMENTS"), ("sidecar", "Kafka", "COMMUNICATES_WITH")],
     "how does the Outbox relay get messages to Kafka without reintroducing dual-writes",
     "outbox sidecar logical replication kafka at least once deliver mark"),
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
