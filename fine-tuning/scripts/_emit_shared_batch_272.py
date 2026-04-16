"""One-off emitter for shared-base batch-272 — technical domain (ORMs and query builders: Prisma, Drizzle, Kysely, SQLAlchemy, Django ORM, Eloquent, diesel, sqlx, sqlc, Ent, gorm, jOOQ, Hibernate, Ecto, Entity Framework, Doctrine, Knex, transactions).

Writes 50 rows to data/v2/shared/batch_272.tmp.jsonl with ids shared-13551..13600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_272.tmp.jsonl"
ID_OFFSET = 13550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Migrated the checkout service from TypeORM to Drizzle ORM because the schema-first TypeScript inference eliminated a whole class of runtime mapping bugs that TypeORM's decorators kept producing on discriminated unions.", "decision", "technical", False,
     [("TypeORM", "library"), ("Drizzle ORM", "library"), ("TypeScript", "language")],
     [("Drizzle ORM", "TypeORM", "REPLACES"), ("Drizzle ORM", "TypeScript", "USES")],
     "which ORM swap did the checkout service adopt for schema-first inference and which runtime bug class retired",
     "drizzle typeorm typescript schema first inference discriminated union"),
    # --- 2 --- architecture
    ("Prisma sits in front of Postgres via Accelerate for the edge runtime while Pulse fans out change-data events to subscriber workers; the direct Postgres proxy only carries the dashboard's long-running analytics queries.", "architecture", "technical", False,
     [("Prisma", "library"), ("Postgres", "database"), ("Accelerate", "service"), ("Pulse", "service"), ("Postgres proxy", "service")],
     [("Prisma", "Postgres", "USES"), ("Accelerate", "Postgres", "COMMUNICATES_WITH"), ("Pulse", "Postgres", "COMMUNICATES_WITH")],
     "how does the Prisma stack split edge reads, change events, and analytics across Accelerate, Pulse, and the direct proxy",
     "prisma accelerate pulse postgres proxy edge change data analytics"),
    # --- 3 --- milestone
    ("Shipped the SQLAlchemy 2.0 unified API migration across the monolith; every legacy Query() call site moved to select() and the async engine now drives the hot request path end-to-end.", "milestone", "technical", False,
     [("SQLAlchemy", "library"), ("2.0", "date"), ("async engine", "pattern")],
     [("SQLAlchemy", "async engine", "USES")],
     "which SQLAlchemy version migration finished across the monolith and what did it unify on the request path",
     "sqlalchemy 2 0 unified api select query async engine migration"),
    # --- 4 --- fact
    ("Kysely generates fully type-safe SQL strings from a TypeScript schema type; the query builder refuses to compile a join whose ON clause references a column not present on either side.", "fact", "technical", False,
     [("Kysely", "library"), ("TypeScript", "language"), ("SQL", "language")],
     [("Kysely", "TypeScript", "USES"), ("Kysely", "SQL", "PRODUCES")],
     "which type-safe SQL builder rejects a join at compile time when the ON clause names an unknown column",
     "kysely typescript sql join on clause compile type safe builder"),
    # --- 5 --- decision
    ("Picked sqlc over an ORM for the payments service in Go: SQL lives in .sql files, the generator emits typed query methods, and there is no runtime reflection layer between the handler and the database.", "decision", "technical", False,
     [("sqlc", "tool"), ("Go", "language"), ("SQL", "language"), ("payments service", "project")],
     [("sqlc", "SQL", "USES"), ("sqlc", "Go", "PRODUCES"), ("sqlc", "payments service", "APPLIES_TO")],
     "which SQL-first generator did the Go payments service pick over an ORM and what runtime layer did it retire",
     "sqlc go payments sql generator typed query reflection orm replace"),
    # --- 6 --- architecture
    ("Diesel enforces schema at compile time via the schema.rs derive set on the Rust crate; a column rename forces a schema regeneration step and anything that still refers to the old name fails to build before it can reach staging.", "fact", "technical", False,
     [("Diesel", "library"), ("Rust", "language"), ("schema.rs", "file")],
     [("Diesel", "Rust", "USES"), ("Diesel", "schema.rs", "DEPENDS_ON")],
     "how does Diesel catch a column rename across the Rust codebase before a build can ship to staging",
     "diesel rust schema rs derive column rename compile build fail"),
    # --- 7 --- problem
    ("sqlx macro compilation broke in CI because the database wasn't reachable from the runner; moved from query!() to query_as!() with an offline SQLX_OFFLINE cache that commits the prepared metadata alongside the code.", "problem", "technical", False,
     [("sqlx", "library"), ("SQLX_OFFLINE", "config"), ("CI", "infrastructure")],
     [("sqlx", "SQLX_OFFLINE", "USES")],
     "which sqlx feature resolved CI builds failing because the runner could not reach the database for macro checks",
     "sqlx offline query macro ci cache prepared metadata runner build"),
    # --- 8 --- reference
    ("Drizzle's migration workflow is split between drizzle-kit for schema diff generation and drizzle-migrate for application: kit writes a numbered SQL file, migrate applies the pending set inside a single transaction per file.", "reference", "technical", False,
     [("drizzle-kit", "tool"), ("drizzle-migrate", "tool"), ("SQL", "language")],
     [("drizzle-migrate", "drizzle-kit", "DEPENDS_ON"), ("drizzle-kit", "SQL", "PRODUCES")],
     "which two Drizzle tools split schema diffing from migration application and how does migrate bound its transactions",
     "drizzle kit migrate sql diff schema numbered file transaction apply"),
    # --- 9 --- architecture
    ("Django ORM backs the admin panel while raw SQLAlchemy Core drives the analytics warehouse queries; the same Postgres cluster serves both but through separate role credentials with read-only and read-write scopes respectively.", "architecture", "technical", False,
     [("Django ORM", "library"), ("SQLAlchemy", "library"), ("Core", "framework"), ("Postgres", "database")],
     [("Django ORM", "Postgres", "USES"), ("SQLAlchemy", "Postgres", "USES"), ("Core", "SQLAlchemy", "HAS_PART")],
     "which ORM and query-builder pair share a Postgres cluster and how are their credentials scoped",
     "django orm sqlalchemy core postgres admin analytics role credential"),
    # --- 10 --- noise
    ("The team whiteboard is down to two working markers and someone has been refilling the blue one in secret for a week.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- decision
    ("SQLModel was chosen for the FastAPI service because it glues Pydantic validation and SQLAlchemy persistence into one class; two parallel models per table were doubling the surface area every sprint before the switch.", "decision", "technical", False,
     [("SQLModel", "library"), ("FastAPI", "framework"), ("Pydantic", "library"), ("SQLAlchemy", "library")],
     [("SQLModel", "Pydantic", "USES"), ("SQLModel", "SQLAlchemy", "USES"), ("SQLModel", "FastAPI", "APPLIES_TO")],
     "which library merged Pydantic validation with SQLAlchemy models for the FastAPI service and what duplication did it collapse",
     "sqlmodel fastapi pydantic sqlalchemy tiangolo duplicate model class"),
    # --- 12 --- problem
    ("Hibernate's default N+1 fetch plan blew up the profile page under load; switching the association to @Fetch(FetchMode.SUBSELECT) collapsed five thousand round-trips per request into two batched queries.", "problem", "technical", False,
     [("Hibernate", "library"), ("profile page", "project"), ("SUBSELECT", "pattern")],
     [("SUBSELECT", "Hibernate", "CONFIGURES"), ("Hibernate", "profile page", "APPLIES_TO")],
     "which Hibernate fetch mode fixed the profile page's N+1 fan-out and how many round-trips did it collapse",
     "hibernate n plus one fetch subselect profile page batched query"),
    # --- 13 --- architecture
    ("jOOQ generates a Java DSL from the production database schema during the Maven build; the DSL is the only code path allowed to touch the transactional database, so dynamic SQL concatenation is effectively banned in code review.", "architecture", "technical", False,
     [("jOOQ", "library"), ("Java", "language"), ("Maven", "tool")],
     [("jOOQ", "Java", "PRODUCES"), ("jOOQ", "Maven", "DEPENDS_ON")],
     "which Java DSL generator acts as the transactional gate and which build tool drives its regeneration",
     "jooq java dsl maven generate schema transactional dynamic sql ban"),
    # --- 14 --- reference
    ("Ent models a graph-first schema for Go services: edges are first-class declarations on entities, and the generator emits traversal methods like QueryFriends().QueryPosts() that compile down to SQL joins against the storage driver.", "reference", "technical", False,
     [("Ent", "framework"), ("Go", "language"), ("SQL", "language")],
     [("Ent", "Go", "PRODUCES"), ("Ent", "SQL", "PRODUCES")],
     "which Facebook-originated Go framework treats edges as first-class and emits traversal methods that lower to SQL joins",
     "ent facebook go graph edge traversal query generate sql join"),
    # --- 15 --- decision
    ("Chose GORM over sqlx for the admin CRUD layer in the Go service because the auto-migration and hook interfaces covered ninety percent of what the team would otherwise hand-roll; the reporting side kept sqlx for its explicit SQL.", "decision", "technical", False,
     [("GORM", "library"), ("sqlx", "library"), ("Go", "language"), ("CRUD", "pattern")],
     [("GORM", "sqlx", "REPLACES"), ("GORM", "CRUD", "APPLIES_TO")],
     "which Go ORM won the admin CRUD bake-off against sqlx and which side stayed on sqlx",
     "gorm sqlx go admin crud auto migrate hook reporting sql explicit"),
    # --- 16 --- fact
    ("Laravel Eloquent's lazy-loading default is a known foot-gun on list endpoints in the PHP monolith; the project standardised on ->with() eager loads declared at controller level and a global withoutLazy() guard in non-production environments.", "fact", "technical", False,
     [("Laravel Eloquent", "framework"), ("PHP", "language"), ("withoutLazy", "api")],
     [("Laravel Eloquent", "PHP", "USES"), ("withoutLazy", "Laravel Eloquent", "CONFIGURES")],
     "which Eloquent feature flips lazy-loading into an error in non-production to force eager declarations",
     "laravel eloquent php lazy eager with without lazy controller guard"),
    # --- 17 --- architecture
    ("Active Record in the Rails monolith gets scoped per bounded context: each engine mounts its own abstract base class so a migration inside the Billing engine cannot race another engine's connection pool configuration.", "milestone", "technical", False,
     [("Active Record", "framework"), ("Rails", "framework"), ("Billing", "project")],
     [("Active Record", "Rails", "USES"), ("Active Record", "Billing", "APPLIES_TO")],
     "how did the Rails monolith isolate Active Record per engine so connection pools stopped racing on migration",
     "active record rails engine bounded context connection pool migration"),
    # --- 18 --- problem
    ("Sequelize's include-based eager loading generated a Cartesian explosion on the orders report; replaced the nested include with two sequential queries joined in JavaScript, cutting the plan from 40 seconds to 600 ms.", "fact", "technical", False,
     [("Sequelize", "library"), ("JavaScript", "language"), ("orders report", "project")],
     [("Sequelize", "JavaScript", "USES"), ("Sequelize", "orders report", "APPLIES_TO")],
     "which Sequelize fetch pattern caused the orders report to fan out into a Cartesian plan and what replaced it",
     "sequelize include eager cartesian orders report javascript join split"),
    # --- 19 --- decision
    ("MikroORM replaced TypeORM on the billing service because the unit-of-work identity map matched the team's DDD aggregate model better; stale-entity bugs from TypeORM's merge() semantics disappeared after the switch.", "decision", "technical", False,
     [("MikroORM", "library"), ("TypeORM", "library"), ("billing service", "project")],
     [("MikroORM", "TypeORM", "REPLACES"), ("MikroORM", "billing service", "APPLIES_TO")],
     "which TypeScript ORM replaced TypeORM on the billing service and which bug class retired with merge semantics",
     "mikroorm typeorm billing unit of work identity map ddd aggregate"),
    # --- 20 --- reference
    ("Objection.js layers its model classes on top of Knex query builder in the JavaScript stack; a .query().withGraphFetched() call composes with raw Knex joins on the same connection so query-builder escapes are never mixed with ORM-synthesised strings.", "reference", "technical", False,
     [("Objection.js", "library"), ("Knex", "library"), ("JavaScript", "language")],
     [("Objection.js", "Knex", "BUILDS_ON"), ("Objection.js", "JavaScript", "USES")],
     "which JavaScript ORM composes its queries on top of Knex and which call combines graph fetch with raw joins",
     "objection knex javascript query builder with graph fetched join compose"),
    # --- 21 --- architecture
    ("sea-orm sits on top of SQLx for the Rust API surface: the entity macros compile into typed queries, transactions flow through SQLx's pool, and migration generation piggybacks on sea-schema for introspection.", "architecture", "technical", False,
     [("sea-orm", "library"), ("SQLx", "library"), ("sea-schema", "library"), ("Rust", "language")],
     [("sea-orm", "SQLx", "BUILDS_ON"), ("sea-orm", "sea-schema", "USES"), ("sea-orm", "Rust", "USES")],
     "which Rust ORM layers its entity macros on SQLx and what handles migration introspection for it",
     "sea orm sqlx sea schema rust entity macro transaction pool migrate"),
    # --- 22 --- milestone
    ("Cut over the telemetry ingest from Hibernate to MyBatis so that the insert-heavy path could use parameterised batch inserts directly; p95 ingest latency dropped from 210 ms to 38 ms in the first week on production.", "milestone", "technical", False,
     [("Hibernate", "library"), ("MyBatis", "library"), ("telemetry ingest", "project")],
     [("MyBatis", "Hibernate", "REPLACES"), ("MyBatis", "telemetry ingest", "APPLIES_TO")],
     "which ORM cutover let the telemetry ingest use direct batch inserts and what p95 latency win did it post",
     "hibernate mybatis telemetry ingest batch insert p95 latency cutover"),
    # --- 23 --- decision
    ("Ecto is the persistence layer for the Elixir services because its changeset pipeline composes validation, casting, and constraint mapping in one value; ad-hoc Phoenix form handlers could reuse the same changesets end-to-end.", "decision", "technical", False,
     [("Ecto", "framework"), ("Elixir", "language"), ("Phoenix", "framework"), ("changeset", "pattern")],
     [("Ecto", "Elixir", "USES"), ("Ecto", "Phoenix", "APPLIES_TO"), ("changeset", "Ecto", "HAS_PART")],
     "which Elixir persistence layer composes validation and casting into a single changeset value reused by Phoenix forms",
     "ecto elixir phoenix changeset validate cast constraint reuse form"),
    # --- 24 --- reference
    ("Slick exposes a Scala query DSL that compiles Scala for-comprehensions to SQL at runtime; the lifted-embedding macro refuses to compile a filter whose lambda uses a Scala collection method that has no SQL equivalent.", "reference", "technical", False,
     [("Slick", "library"), ("Scala", "language"), ("SQL", "language")],
     [("Slick", "Scala", "USES"), ("Slick", "SQL", "PRODUCES")],
     "which Scala library compiles for-comprehensions to SQL and rejects lambdas with no SQL equivalent at compile time",
     "slick scala sql lifted embedding for comprehension lambda reject"),
    # --- 25 --- problem
    ("Entity Framework Core change-tracker blow-up in the bulk import path: thirty thousand entities in one SaveChanges call took eighteen seconds; switched to AsNoTracking for the read leg and EFCore.BulkExtensions for the write leg.", "problem", "technical", False,
     [("Entity Framework Core", "framework"), ("AsNoTracking", "api"), ("EFCore.BulkExtensions", "library")],
     [("AsNoTracking", "Entity Framework Core", "CONFIGURES"), ("EFCore.BulkExtensions", "Entity Framework Core", "EXTENDS")],
     "which two EF Core escape hatches cut the bulk-import path down from the eighteen-second SaveChanges stall",
     "entity framework core bulk import save changes tracking bulk extensions"),
    # --- 26 --- fact
    ("Doctrine's DQL is not SQL: query parsing happens in PHP and the generated SQL depends on the configured platform driver, so a MariaDB-only function in a DQL string will silently fail on the Postgres staging mirror.", "fact", "technical", False,
     [("Doctrine", "library"), ("DQL", "language"), ("PHP", "language"), ("MariaDB", "database"), ("Postgres", "database")],
     [("Doctrine", "PHP", "USES"), ("Doctrine", "DQL", "USES"), ("Doctrine", "MariaDB", "APPLIES_TO"), ("Doctrine", "Postgres", "APPLIES_TO")],
     "which Doctrine layer is platform-dependent and how does a MariaDB-only call fail when the staging mirror is Postgres",
     "doctrine dql php mariadb postgres platform driver staging silent"),
    # --- 27 --- decision
    ("Kysely replaced the hand-rolled query builder on the TypeScript reporting service because a generic Expression<Columns, 'number'> made aggregate composition typecheck; the old builder was building strings that passed review but failed at runtime.", "decision", "technical", False,
     [("Kysely", "library"), ("reporting service", "project"), ("TypeScript", "language")],
     [("Kysely", "reporting service", "APPLIES_TO"), ("Kysely", "TypeScript", "USES")],
     "which query builder took over the reporting service's aggregates and what type made composition safe",
     "kysely reporting type safe aggregate expression builder compose"),
    # --- 28 --- architecture
    ("Transaction boundaries on the checkout flow live at the use-case layer, not the repository: a single SQLAlchemy session is opened per command handler and every repository call inside it shares one unit-of-work commit point.", "decision", "technical", False,
     [("SQLAlchemy", "library"), ("command handler", "pattern"), ("unit-of-work", "pattern"), ("checkout flow", "project")],
     [("command handler", "SQLAlchemy", "USES"), ("unit-of-work", "command handler", "APPLIES_TO"), ("SQLAlchemy", "checkout flow", "APPLIES_TO")],
     "at which layer does the checkout flow anchor SQLAlchemy transactions so all repositories share one commit",
     "sqlalchemy transaction boundary use case command handler unit of work"),
    # --- 29 --- fact
    ("Drizzle's db.transaction() takes a callback whose return value is the transaction result; nested calls map to SAVEPOINTs on Postgres so a caller can retry an inner step without rolling back the outer batch.", "fact", "technical", False,
     [("Drizzle", "library"), ("Postgres", "database"), ("SAVEPOINT", "pattern")],
     [("Drizzle", "Postgres", "USES"), ("SAVEPOINT", "Drizzle", "APPLIES_TO")],
     "how does Drizzle model nested transactions on Postgres so an inner retry leaves the outer batch intact",
     "drizzle transaction postgres savepoint nested callback retry outer"),
    # --- 30 --- decision
    ("Adopted Peewee for the internal scripts because the codebase was already CPython and the teardown-friendly connection pool kept memory bounded on one-shot cron jobs that a heavier ORM would have over-imported for.", "decision", "technical", False,
     [("Peewee", "library"), ("CPython", "platform"), ("cron", "tool")],
     [("Peewee", "CPython", "USES"), ("Peewee", "cron", "APPLIES_TO")],
     "which lightweight Python ORM did the internal cron scripts pick over a heavier option and why",
     "peewee cpython cron internal scripts connection pool teardown light"),
    # --- 31 --- reference
    ("Tortoise ORM mirrors Django's model syntax but runs on asyncio for async Python services; the fields module declares IntField and ForeignKeyField just like Django, and the Meta class supports table naming, indexes, and unique-together.", "reference", "technical", False,
     [("Tortoise ORM", "library"), ("Django", "framework"), ("asyncio", "library"), ("Python", "language")],
     [("Tortoise ORM", "Django", "IMPROVES_ON"), ("Tortoise ORM", "asyncio", "USES"), ("Tortoise ORM", "Python", "USES")],
     "which async Python ORM mirrors Django's model syntax and which Meta options carry over",
     "tortoise orm django asyncio python fields meta table index unique"),
    # --- 32 --- architecture
    ("Knex is the single query builder for the Node.js JavaScript backends: every repository returns a Knex query object unexecuted so the caller can compose .where() clauses on top, and .then() executes against the current transaction.", "architecture", "technical", False,
     [("Knex", "library"), ("Node.js", "platform"), ("JavaScript", "language")],
     [("Knex", "Node.js", "USES"), ("Knex", "JavaScript", "USES")],
     "how does the Node.js backend share composition by returning unexecuted Knex query objects from repositories",
     "knex node js javascript query builder repository compose where then"),
    # --- 33 --- milestone
    ("Finished the Prisma-to-Drizzle migration on the dashboard: all forty-seven Prisma schemas regenerated as Drizzle tables, migrations ran clean in staging, and the bundle shrank by 4.2 MB after dropping the Prisma client.", "milestone", "technical", False,
     [("Prisma", "library"), ("Drizzle", "library"), ("dashboard", "project")],
     [("Drizzle", "Prisma", "REPLACES"), ("Drizzle", "dashboard", "APPLIES_TO")],
     "which ORM migration finished on the dashboard and what bundle-size win did dropping Prisma post",
     "prisma drizzle dashboard migrate bundle size schema regenerate"),
    # --- 34 --- problem
    ("NHibernate's second-level cache returned stale join-fetched rows after a concurrent update from a second app node; disabled the 2LC for the affected entity and relied on the request-scoped session cache instead.", "fact", "technical", False,
     [("NHibernate", "library"), ("second-level cache", "pattern"), ("session cache", "pattern")],
     [("session cache", "second-level cache", "REPLACES"), ("NHibernate", "second-level cache", "CONFIGURES")],
     "which NHibernate cache layer was serving stale rows across nodes and which scope replaced it",
     "nhibernate second level cache stale concurrent update session scope"),
    # --- 35 --- preference
    ("Team preference: write SQL in .sql files and let sqlc or Kysely surface it as types; hand-written ORM query expressions that read like prose go in as a review comment and get asked to move to a named query.", "preference", "technical", False,
     [("SQL", "language"), ("sqlc", "tool"), ("Kysely", "library")],
     [("sqlc", "SQL", "USES"), ("Kysely", "SQL", "USES")],
     "what is the team's SQL authoring preference and how does code review push back on prose-style ORM queries",
     "sql sqlc kysely named query review prose orm expression preference"),
    # --- 36 --- architecture
    ("Sequelize's transaction helper wraps a callback in a managed transaction: if the promise rejects the library rolls back automatically, and a SERIALIZABLE isolation option is passed via the transaction options for the payments path.", "architecture", "technical", False,
     [("Sequelize", "library"), ("SERIALIZABLE", "config"), ("payments path", "project")],
     [("SERIALIZABLE", "Sequelize", "CONFIGURES"), ("Sequelize", "payments path", "APPLIES_TO")],
     "how does Sequelize's managed-transaction callback roll back on rejection and where is SERIALIZABLE chosen",
     "sequelize transaction managed callback rollback serializable payments"),
    # --- 37 --- fact
    ("Prisma's interactive transactions expose a txClient inside a callback: writes issued against the txClient share one Postgres transaction, and the default timeout is five seconds before the library rolls back on its own.", "fact", "technical", False,
     [("Prisma", "library"), ("Postgres", "database"), ("txClient", "api")],
     [("Prisma", "Postgres", "USES"), ("txClient", "Prisma", "HAS_PART")],
     "how does Prisma bound an interactive transaction's lifetime and which client name scopes the writes",
     "prisma interactive transaction tx client postgres timeout rollback"),
    # --- 38 --- decision
    ("Went with Records and Patterns DSLs in Java 21 for the report-mapping layer instead of a dedicated mapping library; the exhaustive-switch compiler check caught three column-order bugs that Jackson would have silently accepted.", "decision", "technical", False,
     [("Records", "pattern"), ("Patterns", "pattern"), ("Java", "language"), ("Jackson", "library")],
     [("Records", "Java", "APPLIES_TO"), ("Patterns", "Java", "APPLIES_TO"), ("Records", "Jackson", "REPLACES")],
     "which Java 21 language features replaced a mapping library in the report layer and what bug class did the compiler catch",
     "java records patterns dsl report mapping jackson exhaustive switch"),
    # --- 39 --- problem
    ("Connection-pool exhaustion on the Eloquent app traced to long-running Guzzle calls inside a DB transaction; extracted the HTTP side into a pre-transaction step so the database connection is only checked out for the write itself.", "preference", "technical", False,
     [("Eloquent", "framework"), ("Guzzle", "library"), ("Connection-pool", "pattern")],
     [("Eloquent", "Guzzle", "USES"), ("Guzzle", "Connection-pool", "CAUSES")],
     "which cross-boundary call inside an Eloquent transaction exhausted the pool and how did the fix reshape the flow",
     "eloquent guzzle connection pool transaction http long running split"),
    # --- 40 --- reference
    ("The Diesel-migrations crate ships the embed_migrations! macro that bakes the migration set into the compiled Rust binary; the service runs diesel_migrations::run on boot so deploys are one artifact and no external migration tool is required.", "reference", "technical", False,
     [("Diesel-migrations", "library"), ("Rust", "language")],
     [("Diesel-migrations", "Rust", "USES")],
     "which Diesel helper bakes migrations into the compiled Rust binary so deploy is a single artifact",
     "diesel migrations embed macro rust binary boot deploy single artifact"),
    # --- 41 --- architecture
    ("SQLAlchemy Core and ORM coexist in the same session: Core is used for bulk inserts via insert().values(), while the ORM handles the typical row-by-row updates; both share one engine and one connection pool configuration.", "decision", "technical", False,
     [("SQLAlchemy", "library"), ("Core", "framework"), ("ORM", "pattern")],
     [("Core", "SQLAlchemy", "HAS_PART"), ("ORM", "SQLAlchemy", "HAS_PART")],
     "how do SQLAlchemy Core and ORM split bulk versus row-by-row work while sharing an engine and pool",
     "sqlalchemy core orm bulk insert values engine connection pool share"),
    # --- 42 --- milestone
    ("Rolled out Prisma Accelerate globally on the marketing site: edge reads now hit the nearest cache rather than the primary Postgres, and the 95th-percentile read latency from Sydney dropped from 310 ms to 48 ms.", "milestone", "technical", False,
     [("Prisma Accelerate", "service"), ("Postgres", "database"), ("marketing site", "project"), ("Sydney", "place")],
     [("Prisma Accelerate", "Postgres", "USES"), ("Prisma Accelerate", "marketing site", "APPLIES_TO")],
     "which Prisma service went global on the marketing site and what p95 read-latency win did Sydney see",
     "prisma accelerate marketing postgres edge cache p95 sydney latency"),
    # --- 43 --- fact
    ("Prisma Pulse delivers logical-replication change events to a TypeScript subscriber; the client receives a typed event keyed on the Prisma model name, so the consumer code does not have to parse WAL records by hand.", "milestone", "technical", False,
     [("Prisma Pulse", "service"), ("TypeScript", "language"), ("WAL", "concept")],
     [("Prisma Pulse", "TypeScript", "PRODUCES"), ("Prisma Pulse", "WAL", "USES")],
     "how does Prisma Pulse present change events to a TypeScript subscriber without raw WAL parsing",
     "prisma pulse change data typescript wal logical replication subscriber"),
    # --- 44 --- noise
    ("The office coffee machine displays a sad bean animation whenever the hopper is more than two-thirds empty, regardless of whether anyone is waiting.", "fact", "noise", True, [], [], None, None),
    # --- 45 --- decision
    ("Picked sqlx with compile-time checked queries over sea-orm for the auth service: the macros inspect SQL against the live database during cargo check, so schema drift between the Rust types and Postgres is caught at build.", "decision", "technical", False,
     [("sqlx", "library"), ("sea-orm", "library"), ("auth service", "project"), ("Postgres", "database")],
     [("sqlx", "sea-orm", "PREFERS"), ("sqlx", "Postgres", "USES"), ("sqlx", "auth service", "APPLIES_TO")],
     "which Rust data-access layer won the auth service over sea-orm and what does it check at build time",
     "sqlx sea orm auth service postgres compile time check schema drift"),
    # --- 46 --- preference
    ("Engineering preference: no implicit Active Record scopes in shared libraries; any query that reads from a user-owned table must take an explicit current_user argument rather than pulling it from request-local storage.", "preference", "technical", False,
     [("Active Record", "framework"), ("current_user", "pattern"), ("request-local", "pattern")],
     [("current_user", "request-local", "REPLACES"), ("current_user", "Active Record", "CONFIGURES")],
     "what Active Record convention does the team ban in shared libraries and which explicit argument replaces it",
     "active record scope shared library current user request local explicit"),
    # --- 47 --- architecture
    ("MikroORM's EntityManager is request-scoped via middleware: each HTTP request forks a new EntityManager off the global ORM, runs the handler within it, and the identity map dies with the request so cross-request leakage is impossible.", "architecture", "technical", False,
     [("MikroORM", "library"), ("EntityManager", "api"), ("middleware", "pattern")],
     [("EntityManager", "MikroORM", "HAS_PART"), ("middleware", "EntityManager", "CONFIGURES")],
     "how does MikroORM scope its EntityManager per HTTP request so identity-map leakage across requests is impossible",
     "mikroorm entity manager request scope middleware identity map fork"),
    # --- 48 --- problem
    ("Objection.js transaction propagation broke when a helper function forgot to accept the trx parameter: the nested call silently used the default Knex connection and the outer rollback left an orphaned row. Fixed by threading trx explicitly.", "preference", "technical", False,
     [("Objection.js", "library"), ("Knex", "library"), ("trx", "pattern")],
     [("Objection.js", "Knex", "BUILDS_ON"), ("trx", "Objection.js", "CONFIGURES")],
     "which Objection.js threading bug caused an orphaned row on rollback and how was it remediated",
     "objection trx transaction knex connection orphan rollback thread"),
    # --- 49 --- milestone
    ("Finished the Ecto 3.x async-pool cutover for the Elixir order service: every query goes through DBConnection, migrations are versioned with ecto_sql, and the p99 checkout time on Postgres dropped below 4 ms on sustained load.", "milestone", "technical", False,
     [("Ecto", "framework"), ("Elixir", "language"), ("DBConnection", "library"), ("ecto_sql", "library"), ("Postgres", "database")],
     [("Ecto", "DBConnection", "USES"), ("Ecto", "ecto_sql", "USES"), ("Ecto", "Postgres", "USES")],
     "which Ecto cutover on the order service routed queries through DBConnection and what Postgres p99 win did it land",
     "ecto elixir dbconnection ecto sql postgres p99 checkout order service"),
    # --- 50 --- architecture
    ("Schema migrations across the polyglot stack are serialised through a shared orchestrator: Prisma migrate, Alembic for SQLAlchemy, and Diesel's embed_migrations each emit a lock record so no two services run migrations on the same Postgres cluster concurrently.", "architecture", "technical", False,
     [("Prisma", "library"), ("Alembic", "tool"), ("SQLAlchemy", "library"), ("Diesel", "library"), ("Postgres", "database")],
     [("Alembic", "SQLAlchemy", "APPLIES_TO"), ("Prisma", "Postgres", "APPLIES_TO"), ("Diesel", "Postgres", "APPLIES_TO")],
     "how do Prisma, Alembic, and Diesel coordinate migrations across services so no two run on the same Postgres concurrently",
     "prisma alembic sqlalchemy diesel postgres migration lock orchestrator"),
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
