"""One-off emitter for shared-base batch-259 — technical domain (functional / hybrid languages on managed VMs: OCaml, F#, Scala, Elixir, Erlang, Haskell, Clojure).

Writes 50 rows to data/v2/shared/batch_259.tmp.jsonl with ids shared-12901..12950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_259.tmp.jsonl"
ID_OFFSET = 12900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Migrated the scraper pipeline from Lwt to OCaml 5 effect handlers so each stage runs under a Domains pool without a bespoke monadic combinator layer on every call.", "decision", "technical", False,
     [("Lwt", "library"), ("OCaml 5", "language"), ("effect handlers", "pattern"), ("Domains", "api")],
     [("effect handlers", "Lwt", "REPLACES"), ("OCaml 5", "Domains", "USES")],
     "which concurrency primitive replaced Lwt in the scraper after the OCaml 5 upgrade",
     "ocaml 5 effect handler lwt domain pool scraper migrate"),
    # --- 2 --- architecture
    ("The OCaml build stack is standardised on Dune with opam pins; the old hand-rolled Makefile invoking ocamlfind per directory was retired once the switch managed cross-module dependency graphs correctly.", "architecture", "technical", False,
     [("Dune", "tool"), ("opam", "tool"), ("Makefile", "tool"), ("ocamlfind", "tool")],
     [("Dune", "Makefile", "REPLACES"), ("Dune", "opam", "USES")],
     "which build tool did the OCaml project standardise on after retiring the custom Makefile workflow",
     "ocaml dune opam makefile ocamlfind build tool standard"),
    # --- 3 --- milestone
    ("Shipped the first production cutover to OCaml 5.1 multicore; the typechecker service now pins one Domain per CPU and saturates the 16-core box where the old runtime left 14 cores idle.", "milestone", "technical", False,
     [("OCaml 5.1", "language"), ("multicore", "pattern"), ("Domain", "api"), ("typechecker", "service")],
     [("OCaml 5.1", "multicore", "USES")],
     "which OCaml release shipped in production and what core-utilisation win did multicore unlock",
     "ocaml 5 1 multicore domain typechecker cutover production core"),
    # --- 4 --- decision
    ("F# Active Patterns replaced a pile of nested match clauses in the parser; a single (|Keyword|Identifier|Whitespace|) partition reads like the spec and the dead-branch warnings turned back on.", "decision", "technical", False,
     [("F#", "language"), ("Active Patterns", "pattern"), ("parser", "service"), ("nested match", "pattern")],
     [("Active Patterns", "nested match", "REPLACES")],
     "which F# feature replaced the nested match clauses in the parser and what warning class returned",
     "fsharp active pattern nested match parser keyword identifier"),
    # --- 5 --- architecture
    ("The F# web stack runs Giraffe on Kestrel with computation expressions wrapping the request pipeline; Saturn sits on top only for the admin console because the MVC conventions save boilerplate.", "decision", "technical", False,
     [("Giraffe", "framework"), ("Kestrel", "service"), ("computation expressions", "pattern"), ("Saturn", "framework"), ("admin console", "project")],
     [("Saturn", "Giraffe", "USES"), ("Giraffe", "Kestrel", "USES")],
     "how is the F# web stack layered between Giraffe and Saturn across the request pipeline",
     "fsharp giraffe saturn kestrel computation expression admin pipeline"),
    # --- 6 --- fact
    ("Bolero hosts the Blazor WebAssembly front-end in F#, and shared DU types flow from the server project into the client project through a common assembly without a code-gen step.", "fact", "technical", False,
     [("Bolero", "framework"), ("Blazor", "framework"), ("F#", "language"), ("DU types", "pattern")],
     [("Bolero", "Blazor", "USES")],
     "which F# framework hosts the Blazor WebAssembly front-end and how do discriminated unions cross the wire",
     "bolero blazor fsharp webassembly discriminated union shared assembly"),
    # --- 7 --- preference
    ("The desktop team prefers Avalonia FuncUI over WPF for new tools because the declarative Elmish loop matches the server-side Model-View-Update the web team already ships.", "preference", "technical", False,
     [("Avalonia FuncUI", "framework"), ("WPF", "framework"), ("Elmish", "pattern")],
     [("Avalonia FuncUI", "WPF", "PREFERS"), ("Avalonia FuncUI", "Elmish", "USES")],
     "which cross-platform F# UI framework does the desktop team prefer over WPF and why",
     "avalonia funcui wpf elmish desktop fsharp model view update"),
    # --- 8 --- decision
    ("Fable transpiles the shared validation module to JavaScript so the same F# code runs on the React front-end; the hand-written TypeScript mirror drifted weekly and got deleted.", "decision", "technical", False,
     [("Fable", "tool"), ("F#", "language"), ("JavaScript", "language"), ("TypeScript", "language"), ("React", "framework")],
     [("Fable", "TypeScript", "REPLACES")],
     "which transpiler lets the F# validation module run on the React front-end and what did it delete",
     "fable fsharp javascript typescript react transpile validation share"),
    # --- 9 --- architecture
    ("Scala 3 given/using instances carry the request context through the service layer; implicit parameters from the 2.13 era got rewritten so every dependency is explicit in the signature.", "architecture", "technical", False,
     [("Scala 3", "language"), ("given/using", "pattern"), ("implicit parameters", "pattern"), ("service layer", "concept")],
     [("given/using", "implicit parameters", "REPLACES")],
     "which Scala 3 mechanism replaced 2.13 implicit parameters for threading request context",
     "scala 3 given using implicit parameter request context service"),
    # --- 10. noise ---
    ("The kitchenette microwave door lost its handle screw and somebody taped on a popsicle stick that now doubles as a lever.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- fact
    ("Extension methods in Scala 3 let the UserId opaque type expose a render function without widening the call site to the underlying String, so downstream modules still get the newtype discipline.", "fact", "technical", False,
     [("Extension methods", "pattern"), ("Scala 3", "language"), ("opaque type", "pattern"), ("UserId", "concept")],
     [("opaque type", "Extension methods", "USES")],
     "how do Scala 3 extension methods let opaque types expose operations without leaking the underlying representation",
     "scala 3 extension method opaque type userid newtype discipline"),
    # --- 12 --- decision
    ("ZIO 2 replaced Cats Effect 3 for the new billing service; the team wanted the built-in fibers-with-supervision and accepted the ecosystem split on the HTTP client side.", "decision", "technical", False,
     [("ZIO 2", "library"), ("Cats Effect 3", "library"), ("billing service", "project"), ("fibers", "pattern")],
     [("ZIO 2", "Cats Effect 3", "REPLACES")],
     "which Scala effect system replaced Cats Effect for the billing service and which feature sealed the choice",
     "zio cats effect billing service fiber supervision scala 3"),
    # --- 13 --- reference
    ("Scala 3 inline declarations compile the macro into TASTy and cross-version artifacts publish the AST rather than bytecode; older 3.x consumers can recompile against the persisted tree.", "reference", "technical", False,
     [("Scala 3", "language"), ("inline", "pattern"), ("TASTy", "technology"), ("AST", "concept")],
     [("inline", "TASTy", "USES")],
     "how do Scala 3 inline declarations publish macros across versions through the TASTy format",
     "scala 3 inline tasty ast macro cross version persist tree"),
    # --- 14 --- architecture
    ("scala-cli runs the smoke-test harness as single-file scripts with inline //> using dependencies; the gradle multi-module dance is reserved for the actual monorepo services.", "architecture", "technical", False,
     [("scala-cli", "tool"), ("gradle", "tool"), ("smoke-test", "project"), ("//> using", "pattern")],
     [("scala-cli", "gradle", "REPLACES")],
     "which Scala runner handles the single-file smoke-test harness in place of gradle modules",
     "scala cli gradle smoke test using directive single file script"),
    # --- 15 --- milestone
    ("Ported the match-engine core from Akka to Apache Pekko after the Lightbend licence change; the actor supervision trees and message envelopes carried over with a package rename and one config patch.", "milestone", "technical", False,
     [("Akka", "framework"), ("Apache Pekko", "framework"), ("match-engine", "project"), ("Lightbend", "organization")],
     [("Apache Pekko", "Akka", "REPLACES")],
     "which actor framework replaced Akka in the match-engine after the Lightbend licence change",
     "akka pekko match engine lightbend license actor supervision rename"),
    # --- 16 --- reference
    ("Scala.js powers the analytics dashboard and Scala Native builds the CLI helper; both share the cross-published utils module so tax-rule updates land in one place per release.", "reference", "technical", False,
     [("Scala.js", "tool"), ("Scala Native", "tool"), ("analytics dashboard", "project"), ("CLI helper", "project"), ("tax-rule", "concept")],
     [("Scala.js", "analytics dashboard", "APPLIES_TO"), ("Scala Native", "CLI helper", "APPLIES_TO")],
     "how are Scala.js and Scala Native split across the dashboard and CLI in this project",
     "scala js native dashboard cli cross publish utils tax rule release"),
    # --- 17 --- decision
    ("Scala 3 enum types replaced the sealed-trait case-object pattern across the domain model; the compiler now generates the values listing and serialization matches on ordinal without reflection.", "decision", "technical", False,
     [("Scala 3", "language"), ("enum", "pattern"), ("sealed-trait case-object", "pattern"), ("ordinal", "concept")],
     [("enum", "sealed-trait case-object", "REPLACES")],
     "which Scala 3 feature replaced the sealed-trait case-object idiom across the domain model",
     "scala 3 enum sealed trait case object ordinal domain serialize"),
    # --- 18 --- architecture
    ("The Elixir ingest pipeline is a supervision tree with one GenServer per tenant, each owning an ETS cache; restart strategy is :one_for_one so a bad payload crashes only its tenant server.", "architecture", "technical", False,
     [("Elixir", "language"), ("GenServer", "pattern"), ("ETS", "api"), ("supervision tree", "pattern"), (":one_for_one", "config")],
     [("GenServer", "ETS", "USES")],
     "how is the Elixir ingest pipeline structured to isolate per-tenant crashes in production",
     "elixir gen server ets supervision tree one for one tenant ingest"),
    # --- 19 --- fact
    ("Phoenix LiveView drives the admin console over a BEAM-backed WebSocket; the React SPA it replaced kept falling out of sync with server authorisation rules and is fully decommissioned.", "fact", "technical", False,
     [("Phoenix LiveView", "framework"), ("BEAM", "platform"), ("React SPA", "framework"), ("admin console", "project")],
     [("Phoenix LiveView", "React SPA", "REPLACES")],
     "which Elixir framework replaced the React SPA for the admin console and what synchronisation issue did it retire",
     "phoenix liveview beam websocket react spa admin sync authorisation"),
    # --- 20 --- decision
    ("Oban handles all background jobs on top of Postgres instead of Sidekiq on Redis; losing the Redis hop cut p99 latency on webhook fan-out and unified the backup story.", "decision", "technical", False,
     [("Oban", "library"), ("Postgres", "database"), ("Sidekiq", "library"), ("Redis", "database"), ("webhook", "concept")],
     [("Oban", "Sidekiq", "REPLACES"), ("Oban", "Postgres", "USES")],
     "which Elixir job runner replaced Sidekiq and what latency improvement came from the infra consolidation",
     "oban sidekiq postgres redis webhook background job p99 latency"),
    # --- 21 --- architecture
    ("Ecto changesets validate and cast the request body before it reaches the Phoenix controller action; business rules live in domain contexts so the controller only maps result tuples to HTTP codes.", "decision", "technical", False,
     [("Ecto", "library"), ("changesets", "pattern"), ("Phoenix", "framework"), ("domain contexts", "pattern")],
     [("Phoenix", "Ecto", "USES")],
     "how do Ecto changesets layer against Phoenix controllers to keep validation out of the web layer",
     "ecto changeset phoenix controller domain context validate http tuple"),
    # --- 22 --- milestone
    ("Broadway shipped in front of the Kafka consumer group; the previous hand-written ConsumerSupervisor lost messages under rebalance and Broadway's batcher made the acknowledgement story explicit.", "milestone", "technical", False,
     [("Broadway", "library"), ("Kafka", "service"), ("ConsumerSupervisor", "pattern"), ("batcher", "pattern")],
     [("Broadway", "ConsumerSupervisor", "REPLACES")],
     "which Elixir streaming library replaced the custom ConsumerSupervisor in front of Kafka",
     "broadway kafka consumer supervisor rebalance batcher elixir stream"),
    # --- 23 --- fact
    ("Nerves cross-compiles the firmware image for the edge gateway; the BEAM runs on the device and pushes OTA updates signed with the fwup keyring shipped in the factory image.", "fact", "technical", False,
     [("Nerves", "framework"), ("BEAM", "platform"), ("edge gateway", "project"), ("fwup", "tool"), ("OTA", "pattern")],
     [("Nerves", "BEAM", "USES")],
     "which Elixir framework builds the edge gateway firmware and how does the OTA update flow authenticate",
     "nerves beam edge gateway fwup ota firmware cross compile sign"),
    # --- 24 --- reference
    ("Nx numerical tensors back the recommendation ranker in Elixir; the inference step reuses the GPU driver through EXLA and Livebook notebooks serve as the reproducible experiment trail.", "reference", "technical", False,
     [("Nx", "library"), ("Elixir", "language"), ("EXLA", "library"), ("Livebook", "tool"), ("recommendation ranker", "project")],
     [("Nx", "EXLA", "USES")],
     "how does the Elixir recommendation ranker reach the GPU and keep its experiments reproducible",
     "nx exla livebook elixir gpu recommendation ranker tensor experiment"),
    # --- 25 --- architecture
    ("Erlang OTP supervisor trees wrap every externally-visible service; the rest-for-one strategy on the session cluster means a crashed session_registry takes its dependent pools with it on restart.", "architecture", "technical", False,
     [("Erlang", "language"), ("OTP", "framework"), ("supervisor trees", "pattern"), ("rest-for-one", "config"), ("session_registry", "service")],
     [("OTP", "supervisor trees", "USES")],
     "which OTP supervision strategy does the session cluster use and what does it do when session_registry crashes",
     "erlang otp supervisor rest for one session registry pool crash"),
    # --- 26 --- reference
    ("Armstrong's Programming Erlang is the canonical onboarding text; new hires finish the workers-and-supervisors chapter before touching the production GenServer codebase per the team runbook.", "reference", "technical", False,
     [("Programming Erlang", "publication"), ("Armstrong", "person"), ("workers-and-supervisors", "concept"), ("GenServer", "pattern")],
     [],
     "which book do new hires finish before touching the production Erlang GenServer codebase",
     "armstrong programming erlang book worker supervisor genserver onboard"),
    # --- 27 --- decision
    ("Moved the Haskell monorepo from Stack to Cabal with a freeze file; the hpack intermediate was removed and cabal.project now pins GHC 9.6 directly to keep CI determinism.", "decision", "technical", False,
     [("Stack", "tool"), ("Cabal", "tool"), ("hpack", "tool"), ("GHC 9.6", "language"), ("cabal.project", "file")],
     [("Cabal", "Stack", "REPLACES"), ("Cabal", "hpack", "REPLACES")],
     "which Haskell build driver replaced Stack in the monorepo and how is GHC pinned for CI",
     "haskell stack cabal hpack ghc 9 6 freeze file ci determinism"),
    # --- 28 --- architecture
    ("The Servant API layer describes the HTTP surface as a type and the server/client/docs fall out of the same definition; the hand-rolled servant-style Spock routes retired after the migration.", "architecture", "technical", False,
     [("Servant", "library"), ("HTTP", "protocol"), ("Spock", "framework")],
     [("Servant", "Spock", "REPLACES")],
     "which Haskell library describes the HTTP surface as a type and what did it retire from the old Spock routes",
     "servant spock haskell http type server client docs route"),
    # --- 29 --- preference
    ("The infra team prefers Nix-build over raw Cabal for reproducible CI images; the Haskell work bench still defaults to cabal v2-build for inner-loop speed on developer laptops.", "reference", "technical", False,
     [("Nix-build", "tool"), ("Cabal", "tool"), ("Haskell", "language"), ("CI", "concept"), ("work bench", "project")],
     [("Nix-build", "Cabal", "PREFERS")],
     "which build tool does the infra team prefer for reproducible Haskell CI images over raw Cabal",
     "nix build cabal haskell ci reproducible work bench v2 laptop"),
    # --- 30 --- fact
    ("IHP sits on top of Haskell for the intranet CRUD app; the generator scaffolds controllers, views, and schema migrations from a single Schema.sql, which removed roughly half the boilerplate Yesod required.", "fact", "technical", False,
     [("IHP", "framework"), ("Haskell", "language"), ("Yesod", "framework"), ("Schema.sql", "file"), ("intranet CRUD", "project")],
     [("IHP", "Yesod", "REPLACES")],
     "which Haskell framework replaced Yesod for the intranet CRUD app and what scaffolding did it bring",
     "ihp yesod haskell intranet crud schema sql scaffold boilerplate"),
    # --- 31 --- decision
    ("Clojure tooling moved from Leiningen to deps.edn with tools.build; project.clj plugins that nobody owned were deleted and the build graph is now a plain map instead of a DSL.", "decision", "technical", False,
     [("Leiningen", "tool"), ("deps.edn", "file"), ("tools.build", "library"), ("project.clj", "file"), ("Clojure", "language")],
     [("deps.edn", "Leiningen", "REPLACES")],
     "which Clojure build system replaced Leiningen and what happened to the project.clj plugin graph",
     "clojure leiningen deps edn tools build project plugin map dsl"),
    # --- 32 --- architecture
    ("core.async channels wire the ingestion goroutines in the Clojure service; the earlier future/promise pair chain hid back-pressure and the channel buffer now bounds queue depth explicitly.", "problem", "technical", False,
     [("core.async", "library"), ("Clojure", "language"), ("channels", "pattern"), ("future/promise", "pattern"), ("back-pressure", "concept")],
     [("core.async", "future/promise", "REPLACES")],
     "which Clojure concurrency primitive replaced the future/promise chain and what property became explicit",
     "core async clojure channel future promise back pressure buffer queue"),
    # --- 33 --- milestone
    ("Datomic Cloud replaced the Postgres event log in the audit service; the bi-temporal model let us answer as-of questions without a bolted-on history table and the backfill ran in three hours.", "milestone", "technical", False,
     [("Datomic", "database"), ("Postgres", "database"), ("audit service", "project"), ("bi-temporal", "concept")],
     [("Datomic", "Postgres", "REPLACES")],
     "which database replaced Postgres for the audit service and what temporal feature justified the move",
     "datomic postgres audit service bi temporal as of history backfill"),
    # --- 34 --- preference
    ("The ops team prefers Babashka for one-off scripts over Bash because the Clojure syntax and java.nio bindings give typed error handling without reaching for a second language.", "preference", "technical", False,
     [("Babashka", "tool"), ("Bash", "language"), ("Clojure", "language"), ("java.nio", "api")],
     [("Babashka", "Bash", "PREFERS")],
     "which scripting tool does the ops team prefer over Bash for one-off automation and why",
     "babashka bash clojure java nio script error handle typed ops"),
    # --- 35 --- problem
    ("OCaml 5 Domains deadlocked on a shared Mutex because the worker pool held the lock across an effect-handler resumption; fix was to release the lock before performing the effect.", "problem", "technical", False,
     [("OCaml 5", "language"), ("Domains", "api"), ("Mutex", "concept"), ("effect-handler", "pattern")],
     [],
     "which OCaml 5 concurrency trap caused the deadlock across Domains and how was the ordering fixed",
     "ocaml 5 domain mutex effect handler deadlock lock resume release"),
    # --- 36 --- architecture
    ("Akka actors on the legacy trade router use Persistence with a Cassandra journal; Pekko inherits the same schema so the rolling migration reuses the event stream without a replay.", "architecture", "technical", False,
     [("Akka", "framework"), ("Pekko", "framework"), ("Persistence", "pattern"), ("Cassandra", "database"), ("trade router", "project")],
     [("Pekko", "Akka", "REPLACES"), ("Akka", "Cassandra", "USES")],
     "how do Akka and Pekko share the Cassandra journal during the trade-router rolling migration",
     "akka pekko persistence cassandra journal trade router migrate replay"),
    # --- 37 --- fact
    ("Elixir's BEAM scheduler preempts on reduction count rather than wall clock, which is why a tight numeric loop still yields; the Nx path uses NIFs wrapped in dirty schedulers to avoid starving other processes.", "fact", "technical", False,
     [("Elixir", "language"), ("BEAM", "platform"), ("NIFs", "api"), ("dirty schedulers", "pattern"), ("Nx", "library")],
     [("Nx", "dirty schedulers", "USES")],
     "which BEAM scheduling mechanism keeps tight loops cooperative and what does Nx use to avoid starvation",
     "elixir beam scheduler reduction nif dirty numeric loop starve"),
    # --- 38 --- reference
    ("Team reading list pairs Okasaki's Purely Functional Data Structures with the Haskell GHC user guide; Servant patterns are cross-referenced against the Scala 3 given/using refactor doc.", "reference", "technical", False,
     [("Okasaki", "person"), ("Purely Functional Data Structures", "publication"), ("GHC", "language"), ("Servant", "library"), ("Scala 3", "language")],
     [],
     "which two canonical references anchor the team reading list for functional programming work",
     "okasaki purely functional data structure ghc haskell servant scala"),
    # --- 39 --- decision
    ("Chose Leiningen over deps.edn only for the plugin-heavy legacy reporting project; the team accepts the split because migrating the cljsbuild and ring-server plugins would cost a sprint.", "decision", "technical", False,
     [("Leiningen", "tool"), ("deps.edn", "file"), ("cljsbuild", "tool"), ("ring-server", "library"), ("reporting project", "project")],
     [("Leiningen", "deps.edn", "PREFERS")],
     "why did the reporting project stay on Leiningen instead of moving to deps.edn",
     "leiningen deps edn cljsbuild ring server reporting legacy split"),
    # --- 40 --- architecture
    ("F# computation expressions wrap the Saturn controller actions as a task { } builder; exceptions flow into the Result monad and the global error middleware maps them to problem-details JSON.", "architecture", "technical", False,
     [("F#", "language"), ("computation expressions", "pattern"), ("Saturn", "framework"), ("Result monad", "pattern"), ("problem-details", "protocol")],
     [("Saturn", "computation expressions", "USES")],
     "how do F# computation expressions structure Saturn controller error flow through Result and problem-details",
     "fsharp computation expression saturn task result monad problem details"),
    # --- 41 --- milestone
    ("Cut over the analytics warehouse ETL to ZIO Streams; the previous FS2 pipeline held because of Cats Effect maturity, but the ZIO 2 Scope model made resource cleanup easier to audit.", "milestone", "technical", False,
     [("ZIO Streams", "library"), ("FS2", "library"), ("Cats Effect", "library"), ("ZIO 2", "library"), ("analytics warehouse ETL", "project")],
     [("ZIO Streams", "FS2", "REPLACES")],
     "which streaming library replaced FS2 in the analytics ETL and what resource-model feature drove the cutover",
     "zio streams fs2 cats effect analytics etl scope cutover resource"),
    # --- 42 --- problem
    ("Phoenix LiveView crashed under reconnect storms because every socket resubscribed to a Postgres LISTEN channel; fix was to multiplex subscriptions through a single PubSub process per node.", "problem", "technical", False,
     [("Phoenix LiveView", "framework"), ("Postgres", "database"), ("LISTEN", "api"), ("PubSub", "pattern")],
     [("PubSub", "LISTEN", "REPLACES")],
     "which Phoenix LiveView crash did reconnect storms expose and what multiplexing fix landed",
     "phoenix liveview reconnect storm postgres listen pubsub multiplex"),
    # --- 43. noise ---
    ("The office plant on the fourth floor has a handwritten sign demanding no overwatering and a laminated schedule of who forgot last.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- fact
    ("Haskell's Servant client generates the type-safe HTTP client used by the ingestion pipeline; request bodies share Aeson instances with the server so drift between client and server is compile-time caught.", "fact", "technical", False,
     [("Servant", "library"), ("Haskell", "language"), ("Aeson", "library"), ("ingestion pipeline", "project")],
     [("Servant", "Aeson", "USES")],
     "how does the Haskell ingestion pipeline get a type-safe HTTP client and catch drift at compile time",
     "servant haskell aeson ingestion type safe http client drift compile"),
    # --- 45 --- decision
    ("Kept the actor model on Erlang for the SMS gateway instead of rewriting to Scala Pekko; the OTP release tooling and hot-code-upgrade path were cheaper than retraining the ops rotation.", "decision", "technical", False,
     [("Erlang", "language"), ("Pekko", "framework"), ("OTP", "framework"), ("SMS gateway", "project"), ("hot-code-upgrade", "pattern")],
     [("Erlang", "Pekko", "PREFERS")],
     "why did the SMS gateway stay on Erlang instead of rewriting to Scala Pekko",
     "erlang pekko otp sms gateway hot code upgrade rewrite ops"),
    # --- 46 --- preference
    ("The data-science team prefers Livebook over Jupyter for Elixir workflows because Nx tensors survive restarts through the Kino persistence layer and the collaboration story matches the rest of the stack.", "preference", "technical", False,
     [("Livebook", "tool"), ("Jupyter", "tool"), ("Elixir", "language"), ("Nx", "library"), ("Kino", "library")],
     [("Livebook", "Jupyter", "PREFERS"), ("Livebook", "Kino", "USES")],
     "which notebook tool does the data-science team prefer for Elixir and what persistence feature drove it",
     "livebook jupyter elixir nx kino notebook tensor persist collaborate"),
    # --- 47 --- architecture
    ("The Clojure web app serves Ring handlers behind Jetty with Reitit routing; Compojure was retired because the data-driven route tree in Reitit plugs into the OpenAPI generator without reflection.", "architecture", "technical", False,
     [("Clojure", "language"), ("Ring", "library"), ("Jetty", "service"), ("Reitit", "library"), ("Compojure", "library"), ("OpenAPI", "protocol")],
     [("Reitit", "Compojure", "REPLACES"), ("Ring", "Jetty", "USES")],
     "which Clojure routing library replaced Compojure and what OpenAPI feature motivated the switch",
     "clojure ring jetty reitit compojure openapi route data driven"),
    # --- 48 --- milestone
    ("Shipped the first Scala Native build of the offline reconciler to production customers; startup dropped from 3.8 seconds on the JVM to 180 ms and the container memory floor moved from 280 MB to 40 MB.", "milestone", "technical", False,
     [("Scala Native", "tool"), ("offline reconciler", "project"), ("JVM", "platform")],
     [("Scala Native", "JVM", "REPLACES")],
     "which runtime swap cut the offline reconciler startup from 3.8 seconds to 180 ms",
     "scala native jvm offline reconciler startup memory container ship"),
    # --- 49 --- milestone
    ("Rolled the OCaml 5 effect-handler retry combinator into the payments gateway; the retired Lwt.catch ladder lost three layers and the flame graph finally stopped showing the callback trampoline.", "milestone", "technical", False,
     [("OCaml 5", "language"), ("effect-handler", "pattern"), ("payments gateway", "project"), ("Lwt.catch", "method"), ("flame graph", "tool")],
     [("effect-handler", "Lwt.catch", "REPLACES")],
     "which OCaml 5 construct replaced the Lwt.catch ladder in the payments gateway",
     "ocaml 5 effect handler payments gateway lwt catch flame graph retry"),
    # --- 50 --- preference
    ("The platform team prefers F# records with shape-typed DUs over Scala 3 enum for internal schemas because the FsCheck generators plug in without a cats-laws dependency chain on the test side.", "preference", "technical", False,
     [("F#", "language"), ("Scala 3", "language"), ("FsCheck", "library"), ("cats-laws", "library"), ("DUs", "pattern")],
     [("F#", "Scala 3", "PREFERS"), ("F#", "FsCheck", "USES")],
     "why does the platform team prefer F# records and DUs over Scala 3 enum for internal schemas",
     "fsharp scala 3 fscheck cats laws du record internal schema generator"),
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
