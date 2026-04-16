"""One-off emitter for shared-base batch-170 — technical domain (GraphQL ecosystem: Apollo, Relay, URQL, Yoga, Hasura, Federation, subscriptions, APQ, dataloader).

Writes 50 rows to data/v2/shared/batch_170.tmp.jsonl with ids shared-08451..08500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_170.tmp.jsonl"
ID_OFFSET = 8450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the product gateway from schema stitching to Apollo Federation v2; subgraphs now own their types and composition happens in the router instead of a monolithic bind step.", "architecture", "technical", False,
     [("schema stitching", "pattern"), ("Apollo Federation v2", "framework"), ("subgraphs", "concept"), ("router", "service")],
     [("Apollo Federation v2", "schema stitching", "REPLACES")],
     "which federation model replaced schema stitching at the product gateway and where does composition run",
     "apollo federation v2 schema stitching subgraph router compose"),
    # --- 2 ---
    ("Apollo Server is fronted by a persisted-queries allowlist; clients send a SHA-256 id and arbitrary documents are rejected, so injection attacks via ad-hoc operations can't reach resolvers.", "decision", "technical", False,
     [("Apollo Server", "framework"), ("persisted-queries", "pattern"), ("SHA-256", "algorithm")],
     [("Apollo Server", "persisted-queries", "USES")],
     "how does the Apollo Server block ad-hoc GraphQL documents from hitting the resolvers in production",
     "apollo server persisted query allowlist sha256 hash injection reject"),
    # --- 3 ---
    ("Swapped Apollo Client for URQL on the marketing site; the bundle shrank by roughly sixty kilobytes gzipped and the document cache was enough for a read-mostly surface.", "decision", "technical", False,
     [("Apollo Client", "library"), ("URQL", "library"), ("document cache", "pattern")],
     [("URQL", "Apollo Client", "REPLACES")],
     "which GraphQL client replaced Apollo Client on the marketing site and what bundle win did it deliver",
     "urql apollo client bundle size document cache marketing site swap"),
    # --- 4 ---
    ("Relay drives the data layer for the consumer app; the compiler's fragment-colocation rules force each component to declare exactly the fields it reads and catch overfetching at build time.", "architecture", "technical", False,
     [("Relay", "framework"), ("fragment-colocation", "pattern"), ("compiler", "tool")],
     [("Relay", "fragment-colocation", "USES")],
     "which Relay feature catches overfetching at build time rather than at runtime in the consumer app",
     "relay fragment colocation compiler overfetch build time component"),
    # --- 5 ---
    ("Resolved the N+1 resolver blow-up by wiring DataLoader per request; author lookups that used to fire one query per post now batch into a single IN clause against Postgres.", "problem", "technical", False,
     [("N+1 resolver", "pattern"), ("DataLoader", "library"), ("Postgres", "database")],
     [("DataLoader", "N+1 resolver", "FIXES")],
     "which library fixed the per-post author lookup explosion and how did it batch against Postgres",
     "dataloader n+1 resolver batch in clause postgres author lookup"),
    # --- 6 ---
    ("graphql-yoga replaced a hand-rolled Express GraphQL handler in the internal API; plugin hooks gave us rate-limiting and CSRF prevention without writing middleware from scratch.", "decision", "technical", False,
     [("graphql-yoga", "framework"), ("Express", "framework"), ("rate-limiting", "pattern"), ("CSRF", "pattern")],
     [("graphql-yoga", "Express", "REPLACES")],
     "which Yoga features replaced the hand-rolled Express handler for rate-limiting and CSRF in the internal API",
     "graphql yoga express handler plugin rate limit csrf internal"),
    # --- 7 ---
    ("Hasura fronts the analytics read-replica: permissions are declared per role on the metadata, and complex predicates fall through to custom actions backed by a GraphQL.js service.", "architecture", "technical", False,
     [("Hasura", "service"), ("read-replica", "database"), ("GraphQL.js", "library"), ("custom actions", "pattern")],
     [("Hasura", "GraphQL.js", "COMMUNICATES_WITH")],
     "how does Hasura handle predicates it cannot express directly on the analytics read-replica",
     "hasura read replica custom action graphql js predicate permission"),
    # --- 8 ---
    ("PostGraphile generates the admin API straight off the Postgres schema; row-level security policies are the authorization story and we never hand-write a resolver for standard CRUD.", "decision", "technical", False,
     [("PostGraphile", "framework"), ("Postgres", "database"), ("row-level security", "pattern")],
     [("PostGraphile", "Postgres", "DEPENDS_ON")],
     "how does PostGraphile authorize the admin API without hand-rolled resolvers on standard CRUD paths",
     "postgraphile postgres row level security admin api crud resolver"),
    # --- 9 ---
    ("Mercurius powers the Fastify-based checkout service; JIT compilation of queries via graphql-jit cut per-operation CPU by roughly forty percent under load tests.", "milestone", "technical", False,
     [("Mercurius", "library"), ("Fastify", "framework"), ("graphql-jit", "library")],
     [("Mercurius", "graphql-jit", "USES")],
     "which JIT integration cut per-operation CPU on the Mercurius checkout service under load",
     "mercurius fastify graphql jit compile cpu load test checkout"),
    # --- 10. noise ---
    ("The team's ping-pong table has a wobble that everyone pretends is a skill test rather than a leg-level problem.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("AppSync is the mobile backend; resolvers are VTL templates against DynamoDB for hot paths and Lambda only for the two endpoints that need cross-table joins at request time.", "architecture", "technical", False,
     [("AppSync", "service"), ("VTL", "language"), ("DynamoDB", "database"), ("Lambda", "service")],
     [("AppSync", "DynamoDB", "COMMUNICATES_WITH")],
     "how does AppSync split resolvers between VTL against DynamoDB and Lambda for the mobile backend",
     "appsync vtl dynamodb lambda resolver mobile backend hot path join"),
    # --- 12 ---
    ("Composition errors from the Federation v2 router surfaced when two subgraphs shared a type without an @key directive; adding the key and a reference resolver cleared the rover check.", "problem", "technical", False,
     [("Federation v2", "framework"), ("@key", "pattern"), ("reference resolver", "pattern"), ("rover", "tool")],
     [("@key", "Federation v2", "APPLIES_TO")],
     "which directive did two subgraphs need to share a type and how did we verify the composition",
     "federation v2 key directive reference resolver rover composition"),
    # --- 13 ---
    ("Automatic persisted queries are on for the web client; the first uncached operation POSTs the document, subsequent calls send only the hash, and we saved about thirty percent on request body size.", "fact", "technical", False,
     [("Automatic persisted queries", "pattern"), ("web client", "service"), ("hash", "concept")],
     [("web client", "Automatic persisted queries", "USES")],
     "how does the automatic persisted queries flow cut request body size for the web client",
     "automatic persisted query apq hash document post web client"),
    # --- 14 ---
    ("Field-level caching is driven by a @cacheControl hint on each type; the CDN reads the max-age from the response extensions and caches public fields while private hits bypass.", "fact", "technical", False,
     [("@cacheControl", "pattern"), ("CDN", "infrastructure"), ("extensions", "pattern")],
     [],
     "how does field-level caching propagate TTLs from the schema out to the CDN in front of the gateway",
     "field cache control directive cdn max age extensions public private"),
    # --- 15 ---
    ("Query cost analysis runs before resolver execution; each field carries a weight, aggregate cost over a threshold triggers a rejection, and pagination arguments multiply nested cost.", "architecture", "technical", False,
     [("Query cost analysis", "pattern"), ("resolver", "concept"), ("pagination", "pattern")],
     [("Query cost analysis", "resolver", "APPLIES_TO")],
     "how does the gateway bound pathological queries before any resolver runs and how does pagination factor in",
     "query cost analysis weight threshold reject pagination nested"),
    # --- 16 ---
    ("Complexity limits are capped at 1000 points per operation; the previous 5000-point ceiling let a single nested friends-of-friends query hog a resolver worker for seconds.", "decision", "technical", False,
     [("Complexity limits", "pattern"), ("resolver worker", "service"), ("friends-of-friends", "pattern")],
     [],
     "which complexity ceiling did we drop to after a friends-of-friends query stalled resolver workers",
     "complexity limit point operation friends of friends worker stall"),
    # --- 17 ---
    ("Subscriptions run over graphql-ws with a Redis pub-sub backing the event fan-out; the older subscriptions-transport-ws was abandoned for heartbeat and auth reasons.", "decision", "technical", False,
     [("graphql-ws", "protocol"), ("Redis", "database"), ("subscriptions-transport-ws", "protocol")],
     [("graphql-ws", "subscriptions-transport-ws", "REPLACES"), ("graphql-ws", "Redis", "USES")],
     "which subscription transport replaced subscriptions-transport-ws and what backs the event fan-out",
     "graphql ws redis pubsub subscription transport heartbeat auth"),
    # --- 18 ---
    ("Live queries are served via a push model: a mutation tags affected documents, the gateway invalidates matching subscriptions, and clients receive a patched payload rather than a full refetch.", "decision", "technical", False,
     [("Live queries", "pattern"), ("mutation", "concept"), ("patched payload", "pattern")],
     [("Live queries", "patched payload", "PRODUCES")],
     "how does the live-query push model avoid full refetches when a mutation invalidates subscribed documents",
     "live query push mutation invalidate tag patch payload refetch"),
    # --- 19 ---
    ("Mutations that write across two subgraphs use the Federation v2 entity-reference pattern plus a saga coordinator; a failure in the second subgraph triggers a compensating mutation in the first.", "architecture", "technical", False,
     [("Federation v2", "framework"), ("saga coordinator", "pattern"), ("compensating mutation", "pattern")],
     [],
     "how do cross-subgraph mutations recover when the second subgraph's write fails mid-operation",
     "federation mutation saga compensate subgraph cross entity failure"),
    # --- 20 ---
    ("Fragments are shared through a @graphql-codegen plugin: TypeScript types and typed document nodes regenerate on save so a schema change surfaces as a compile error in the component tree.", "reference", "technical", False,
     [("@graphql-codegen", "tool"), ("TypeScript", "language"), ("typed document nodes", "pattern")],
     [("@graphql-codegen", "TypeScript", "PRODUCES")],
     "which codegen setup makes a schema change show up as a compile error in components that read the fragment",
     "graphql codegen typescript typed document node fragment compile"),
    # --- 21 ---
    ("The @defer directive is turned on for the profile page; above-the-fold fields ship in the initial response and a multipart chunk finishes the slow reviews section after the main paint.", "fact", "technical", False,
     [("@defer", "pattern"), ("profile page", "service"), ("multipart", "protocol")],
     [],
     "how does the @defer directive split the profile page payload between the initial response and later chunks",
     "defer directive profile multipart above fold paint reviews chunk"),
    # --- 22 ---
    ("The @stream directive chunks the activity feed: each ten-item batch flushes as it's ready so the first items render without blocking on the tail of a long list.", "fact", "technical", False,
     [("@stream", "pattern"), ("activity feed", "service")],
     [],
     "which GraphQL directive lets us start painting the feed before the backend has finished loading all items",
     "stream directive activity feed chunk batch render first tail"),
    # --- 23 ---
    ("Introspection is disabled in production for the public gateway; internal tooling reads the schema from a checked-in SDL artifact instead, so attackers can't probe types through the live endpoint.", "decision", "technical", False,
     [("Introspection", "concept"), ("public gateway", "service"), ("SDL", "language")],
     [],
     "how does the gateway block schema probing in production while still serving internal tooling",
     "introspection disable production gateway sdl artifact probe schema"),
    # --- 24 ---
    ("Schema versioning follows a deprecation-then-remove policy with the @deprecated directive; fields stay for at least two release cycles and the metrics pipeline tracks usage by operation hash.", "preference", "technical", False,
     [("@deprecated", "pattern"), ("metrics pipeline", "service"), ("operation hash", "concept")],
     [],
     "how does the schema retire fields safely and how do we confirm no client still calls them",
     "schema version deprecated directive release cycle operation hash"),
    # --- 25 ---
    ("Codegen hooks are wired into the pre-commit: a schema.graphql change forces regen of the typed client and staging any stale generated files blocks the commit.", "decision", "technical", False,
     [("Codegen", "tool"), ("pre-commit", "tool"), ("schema.graphql", "file")],
     [],
     "how does the pre-commit hook keep the generated typed client in sync with schema.graphql",
     "codegen pre commit schema graphql regen typed client stale"),
    # --- 26 ---
    ("Persisted queries are stored in a manifest file shipped with the client build; CI uploads the manifest to the gateway before the rollout so the new hashes are live before users hit them.", "architecture", "technical", False,
     [("Persisted queries", "pattern"), ("manifest", "file"), ("CI", "tool")],
     [],
     "how does CI keep persisted-query hashes live on the gateway before a client rollout reaches users",
     "persisted query manifest ci upload gateway rollout hash"),
    # --- 27 ---
    ("Chose Pothos over Nexus for the new booking service schema; the plugin ergonomics and the first-class Relay connection helpers shaved a lot of builder boilerplate off the admin types.", "decision", "technical", False,
     [("Pothos", "library"), ("Nexus", "library"), ("Relay", "framework")],
     [("Pothos", "Nexus", "PREFERS")],
     "which schema builder won the bake-off for the booking service and which plugin feature sealed it",
     "pothos nexus schema builder relay connection plugin booking"),
    # --- 28 ---
    ("Rolled out Apollo Studio tracing as the gateway's observability backend last sprint; field-level timings are live, a p99 alert is wired, and the field heat-map already drove two resolver wins.", "milestone", "technical", False,
     [("Apollo Studio", "service"), ("field-level timings", "concept"), ("p99", "concept")],
     [],
     "which tracing rollout landed last sprint and what resolver wins did the field heat-map drive",
     "apollo studio tracing rollout field timing p99 heat map resolver"),
    # --- 29 ---
    ("Query planner picked a slow path on a deeply nested subgraph fan-out; pinning an @provides hint on the common id field cut the cross-subgraph call count from four to one.", "decision", "technical", False,
     [("Query planner", "algorithm"), ("@provides", "pattern"), ("subgraph", "concept")],
     [("@provides", "Query planner", "CONFIGURES")],
     "which hint changed the query planner's subgraph fan-out and by how much did cross-subgraph calls drop",
     "query planner provides hint subgraph fan out cross call pin"),
    # --- 30 ---
    ("Schema stitching still powers the legacy CMS gateway where ownership is too tangled to split into subgraphs; a migration to Federation v2 is scoped but blocked on the auth rewrite.", "fact", "technical", False,
     [("Schema stitching", "pattern"), ("CMS", "service"), ("Federation v2", "framework"), ("auth rewrite", "project")],
     [],
     "which legacy surface still runs schema stitching and what blocks its move to Federation v2",
     "schema stitching legacy cms federation v2 auth rewrite migrate"),
    # --- 31 ---
    ("DataLoader cache-per-request is scoped to a single operation; carrying the loader across requests leaked stale rows into a mutation response during the incident on 2026-03-14.", "decision", "technical", False,
     [("DataLoader", "library"), ("cache-per-request", "pattern"), ("2026-03-14", "date")],
     [],
     "why must the batch cache stay scoped per operation and what went wrong when it was shared across calls",
     "dataloader cache per request stale row mutation leak incident"),
    # --- 32 ---
    ("Introduced Envelop as the plugin layer on top of graphql-yoga; lifecycle hooks for onParse, onValidate, and onExecute let us inject auth and logging without monkey-patching the server.", "architecture", "technical", False,
     [("Envelop", "library"), ("graphql-yoga", "framework"), ("onParse", "api"), ("onValidate", "api"), ("onExecute", "api")],
     [("Envelop", "graphql-yoga", "EXTENDS")],
     "which plugin layer sits on top of graphql-yoga and which lifecycle hooks does it expose for auth and logging",
     "envelop yoga plugin on parse validate execute auth log hook"),
    # --- 33 ---
    ("The mobile client uses Relay's store-only updater to keep optimistic mutation state coherent; a network failure rolls back the store and the UI reverts without a refetch.", "fact", "technical", False,
     [("Relay", "framework"), ("store-only updater", "pattern"), ("optimistic mutation", "pattern")],
     [],
     "which Relay pattern keeps optimistic mutation state coherent when the network call eventually fails",
     "relay store updater optimistic mutation rollback network fail"),
    # --- 34 ---
    ("Prefer URQL graphcache over the default document cache for the dashboard; normalised storage lets mutation results update list views without manually writing every refetch query.", "preference", "technical", False,
     [("URQL", "library"), ("graphcache", "library"), ("document cache", "pattern"), ("dashboard", "service")],
     [("graphcache", "document cache", "PREFERS")],
     "which URQL cache layer do we prefer for the dashboard and what does the normalised store unlock",
     "urql graphcache document cache normalise mutation dashboard refetch"),
    # --- 35 ---
    ("Prefer Relay's connection spec for any paginated list; the edge and cursor contract lines up with our cursor-paginated Postgres queries without a translation layer at the resolver.", "preference", "technical", False,
     [("Relay", "framework"), ("connection spec", "pattern"), ("cursor-paginated", "pattern"), ("Postgres", "database")],
     [("connection spec", "cursor-paginated", "APPLIES_TO")],
     "which pagination contract do we reach for on lists and why does it avoid a resolver translation layer",
     "relay connection spec cursor pagination postgres edge list"),
    # --- 36 ---
    ("The public docs for the partner API are generated from the schema via SpectaQL; a release job rebuilds the HTML on every main-branch schema change and the static site rolls out automatically.", "architecture", "technical", False,
     [("SpectaQL", "tool"), ("partner API", "service"), ("main-branch", "concept")],
     [("SpectaQL", "partner API", "APPLIES_TO")],
     "how does the partner API keep its public docs in sync with the schema without a manual rebuild",
     "spectaql docs schema partner release main branch static site"),
    # --- 37 ---
    ("Reference: the Federation v2 spec pins _entities and _service as internal fields on subgraphs; removing them or renaming them breaks the router's composition probe at startup.", "reference", "technical", False,
     [("Federation v2", "framework"), ("_entities", "api"), ("_service", "api")],
     [],
     "which two internal subgraph fields does the Federation v2 router rely on during composition",
     "federation v2 entities service subgraph router composition probe"),
    # --- 38 ---
    ("Reference: the graphql-ws protocol uses a connection_init message followed by subscribe frames; ping and pong keep the socket alive through proxies that idle-kill at sixty seconds.", "reference", "technical", False,
     [("graphql-ws", "protocol"), ("connection_init", "api"), ("subscribe", "api")],
     [],
     "which graphql-ws frames open a subscription session and how does the protocol survive idle proxies",
     "graphql ws connection init subscribe ping pong proxy idle"),
    # --- 39 ---
    ("Reference: the DataLoader constructor takes a batch function and a cache-key function; the batch function must return results in the same order as the input keys or lookups resolve to the wrong row.", "reference", "technical", False,
     [("DataLoader", "library"), ("batch function", "api"), ("cache-key function", "api")],
     [],
     "which DataLoader contract must the batch function honour to avoid scrambled row lookups",
     "dataloader batch function cache key order input return row"),
    # --- 40 ---
    ("Reference: Apollo Federation v2 swapped @extends for the extend type keyword and introduced @shareable for types owned by multiple subgraphs without conflict.", "reference", "technical", False,
     [("Apollo Federation v2", "framework"), ("@extends", "pattern"), ("@shareable", "pattern")],
     [("@shareable", "Apollo Federation v2", "APPLIES_TO")],
     "which Federation v2 directive change lets multiple subgraphs own the same type without a composition error",
     "federation v2 extends shareable directive subgraph own type conflict"),
    # --- 41 ---
    ("Reference: Hasura permissions are compiled into Postgres row filters at query plan time; a role with no matching permission returns an empty result rather than a 403.", "reference", "technical", False,
     [("Hasura", "service"), ("Postgres", "database"), ("role", "concept")],
     [("Hasura", "Postgres", "COMMUNICATES_WITH")],
     "how does Hasura represent a missing permission at the response level rather than returning an HTTP error",
     "hasura postgres permission role row filter empty 403 plan"),
    # --- 42 ---
    ("Reference: AppSync resolvers written in VTL receive the request context under $context and the upstream response under $context.result; skipping the response mapping drops fields silently.", "reference", "technical", False,
     [("AppSync", "service"), ("VTL", "language"), ("$context", "api")],
     [],
     "which VTL context object in AppSync holds the upstream response and what happens if you skip mapping it",
     "appsync vtl context result response mapping drop field silent"),
    # --- 43. noise ---
    ("Someone filled the kitchen cookie jar with pistachio shells as a prank and nobody has admitted to it yet after two weeks.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Stood up the unified shopping gateway on Apollo Router 1.0 with four subgraphs; a week of shadow traffic caught one composition conflict on the Product type before the cutover.", "milestone", "technical", False,
     [("Apollo Router", "service"), ("shopping gateway", "service"), ("Product", "concept"), ("shadow traffic", "pattern")],
     [("shopping gateway", "Apollo Router", "DEPLOYED_ON")],
     "which gateway went live on Apollo Router and what caught the Product-type conflict before users hit it",
     "apollo router shopping gateway subgraph shadow traffic product conflict"),
    # --- 45 ---
    ("Shipped the first Relay-based page on the consumer app after a three-month migration from Apollo Client; the compiler-enforced data requirements caught four over-fetch bugs in review.", "milestone", "technical", False,
     [("Relay", "framework"), ("Apollo Client", "library"), ("consumer app", "service")],
     [("Relay", "Apollo Client", "REPLACES")],
     "which migration milestone landed a Relay page in the consumer app and how many over-fetch bugs did the compiler catch",
     "relay apollo client migration consumer over fetch compiler page"),
    # --- 46 ---
    ("Cut over subscriptions from Socket.io to graphql-ws with Redis; p95 event latency dropped from 180 ms to 55 ms and reconnection storms stopped saturating the node pool.", "milestone", "technical", False,
     [("Socket.io", "library"), ("graphql-ws", "protocol"), ("Redis", "database")],
     [("graphql-ws", "Socket.io", "REPLACES")],
     "which transport change cut tail latency for pushes and ended the reconnection-driven saturation on nodes",
     "socket io graphql ws redis subscription latency reconnect storm"),
    # --- 47 ---
    ("Turned on APQ across all mobile clients after the v4.2 release; request body size dropped, and the iOS team's flaky slow-network upload path became reliable enough to close the long-running bug.", "milestone", "technical", False,
     [("APQ", "pattern"), ("mobile clients", "service"), ("v4.2", "date"), ("iOS", "platform")],
     [("mobile clients", "APQ", "USES")],
     "which release turned APQ on for mobile and which flaky network path finally stabilised after",
     "apq mobile client v4 2 ios slow network upload release"),
    # --- 48 ---
    ("Landed query cost analysis on the public gateway with a 1000-point ceiling; within two days the analytics dashboard showed a seventy-percent drop in resolver CPU spikes from adversarial traffic.", "milestone", "technical", False,
     [("query cost analysis", "pattern"), ("public gateway", "service"), ("resolver CPU", "concept")],
     [],
     "which milestone deployed query cost analysis and what CPU-spike drop landed within two days",
     "query cost analysis public gateway resolver cpu spike adversarial"),
    # --- 49 ---
    ("Prefer graphql-yoga over Apollo Server for new edge workers: the smaller dependency footprint and the Fetch API-native handler fit Cloudflare and Deno runtimes without a shim.", "preference", "technical", False,
     [("graphql-yoga", "framework"), ("Apollo Server", "framework"), ("Cloudflare", "platform"), ("Deno", "platform")],
     [("graphql-yoga", "Apollo Server", "PREFERS")],
     "which server do we prefer for edge workers and which runtime compatibility seals the choice",
     "graphql yoga apollo server edge worker cloudflare deno fetch api"),
    # --- 50 ---
    ("Federation composition broke on deploy when two subgraphs independently added a status enum value; the fix pins enum ownership to a single subgraph and uses @inaccessible for private variants.", "problem", "technical", False,
     [("Federation", "framework"), ("status enum", "concept"), ("@inaccessible", "pattern")],
     [("@inaccessible", "Federation", "APPLIES_TO")],
     "which composition break happened when two subgraphs added an enum value and which directive hides private variants",
     "federation composition enum status subgraph inaccessible variant"),
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
