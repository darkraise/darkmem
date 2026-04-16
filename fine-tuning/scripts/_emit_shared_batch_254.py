"""One-off emitter for shared-base batch-254 — technical domain (SQLite internals and embedded databases: WAL mode, journal mode, PRAGMAs, FTS5, JSON1, STRICT, Litestream, LiteFS, Datasette, sqlcipher, embedded alternatives).

Writes 50 rows to data/v2/shared/batch_254.tmp.jsonl with ids shared-12651..12700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_254.tmp.jsonl"
ID_OFFSET = 12650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Flipped every production SQLite database from the default rollback journal to WAL mode via PRAGMA journal_mode=WAL; concurrent readers no longer block the writer, which is the whole reason we bothered.", "decision", "technical", False,
     [("SQLite", "database"), ("WAL mode", "concept"), ("rollback journal", "concept"), ("PRAGMA journal_mode", "command")],
     [("WAL mode", "rollback journal", "REPLACES"), ("PRAGMA journal_mode", "SQLite", "CONFIGURES")],
     "which SQLite journaling mode replaced the rollback journal in production and which pragma flipped it",
     "sqlite wal journal mode pragma rollback concurrent reader writer"),
    # --- 2 ---
    ("Lowered PRAGMA synchronous from FULL to NORMAL on the analytics replica after measuring a 3x commit speedup; durability is still safe enough because WAL mode only loses uncommitted transactions on a power cut.", "fact", "technical", False,
     [("PRAGMA synchronous", "command"), ("FULL", "config"), ("NORMAL", "config"), ("WAL mode", "concept")],
     [("NORMAL", "FULL", "REPLACES")],
     "which synchronous level replaced FULL on the analytics replica and why was the durability trade acceptable",
     "sqlite pragma synchronous full normal wal commit speed durability"),
    # --- 3 ---
    ("PRAGMA foreign_keys defaults off in SQLite for backward compatibility, so every connection opener in the service now runs it as ON right after connect; orphan rows stopped appearing in the audit table within a day.", "problem", "technical", False,
     [("PRAGMA foreign_keys", "command"), ("SQLite", "database"), ("audit table", "concept")],
     [("PRAGMA foreign_keys", "SQLite", "CONFIGURES")],
     "which per-connection pragma stopped orphan rows in the audit table and why is it off by default",
     "sqlite pragma foreign keys orphan audit connection default off"),
    # --- 4 ---
    ("Bumped PRAGMA cache_size to -65536 to let SQLite hold roughly 64 MB of pages per connection in memory; the large reporting query that used to chew disk now stays entirely in the page cache.", "fact", "technical", False,
     [("PRAGMA cache_size", "command"), ("SQLite", "database"), ("page cache", "concept")],
     [("PRAGMA cache_size", "SQLite", "CONFIGURES")],
     "which pragma expanded the per-connection page cache to about 64 MB and what query benefited",
     "sqlite pragma cache size page reporting query memory connection"),
    # --- 5 ---
    ("Turned on PRAGMA mmap_size=268435456 for the read-mostly replica so SQLite memory-maps up to 256 MB of the database file; random reads drop under the syscall threshold and the kernel page cache does the rest.", "architecture", "technical", False,
     [("PRAGMA mmap_size", "command"), ("SQLite", "database"), ("kernel page cache", "concept")],
     [("PRAGMA mmap_size", "SQLite", "CONFIGURES")],
     "which SQLite pragma memory-maps up to 256 MB of the database file on the read replica",
     "sqlite pragma mmap size memory map replica kernel cache random"),
    # --- 6 ---
    ("Ripped shared-cache mode out of the SQLite connection opener after an upstream warning that it is deprecated and error-prone; each connection now owns its cache and the intermittent SQLITE_LOCKED under load disappeared.", "decision", "technical", False,
     [("shared-cache mode", "concept"), ("SQLite", "database"), ("SQLITE_LOCKED", "error")],
     [("shared-cache mode", "SQLITE_LOCKED", "CAUSES")],
     "which deprecated SQLite feature was removed after locking errors under load and what replaced it",
     "sqlite shared cache deprecate locked connection own private"),
    # --- 7 ---
    ("Switched the hot-path lookup tables to WITHOUT ROWID; SQLite stores them as a clustered index on the primary key rather than a rowid heap with a secondary index, and point lookups dropped by roughly a third.", "decision", "technical", False,
     [("WITHOUT ROWID", "concept"), ("SQLite", "database"), ("rowid", "concept"), ("clustered index", "concept")],
     [("WITHOUT ROWID", "rowid", "REPLACES")],
     "which SQLite table flavour replaced rowid tables on hot-path lookups and what storage shape does it use",
     "sqlite without rowid clustered index primary key hot lookup"),
    # --- 8 ---
    ("Adopted SQLite FTS5 virtual tables for the product search index; the earlier LIKE scan on the description column stopped scaling past about fifty thousand rows and the tokenizer unicode61 folded diacritics for free.", "milestone", "technical", False,
     [("SQLite", "database"), ("FTS5", "library"), ("virtual table", "concept"), ("unicode61", "config")],
     [("FTS5", "SQLite", "EXTENDS")],
     "which SQLite extension replaced a LIKE scan for product search and which tokenizer handled diacritics",
     "sqlite fts5 virtual table like scan unicode61 tokenizer diacritic"),
    # --- 9 ---
    ("The FTS5 BM25 ranker sorts search results without a second trip through the main table; the built-in bm25() function takes the virtual-table row and returns a score we feed straight into the ORDER BY.", "architecture", "technical", False,
     [("FTS5", "library"), ("BM25", "algorithm"), ("bm25()", "api")],
     [("FTS5", "BM25", "IMPLEMENTS")],
     "which ranking function does FTS5 expose for ordering matches and where does it plug into the query",
     "fts5 bm25 rank function virtual table order by score sqlite"),
    # --- 10. noise ---
    ("The office espresso machine was making a new rattling sound this morning and nobody is willing to open the panel to investigate.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Added the spellfix1 extension alongside FTS5 so typo-tolerant lookups fall back to edit-distance candidates; the product catalogue now returns results for queries like 'headphnes' that used to come back empty.", "architecture", "technical", False,
     [("spellfix1", "library"), ("FTS5", "library"), ("edit-distance", "algorithm")],
     [("spellfix1", "FTS5", "EXTENDS")],
     "which SQLite extension adds typo-tolerant fallback to FTS5 and what algorithm powers the candidates",
     "sqlite spellfix1 fts5 edit distance typo tolerant fallback product"),
    # --- 12 ---
    ("SQLite R-Tree virtual tables drive the 'stores near me' query; a bounding-box prefilter on latitude and longitude pairs narrows the candidate set before the haversine sort, and p99 dropped under 20 ms.", "architecture", "technical", False,
     [("SQLite", "database"), ("R-Tree", "library"), ("virtual table", "concept"), ("haversine", "algorithm")],
     [("R-Tree", "SQLite", "EXTENDS")],
     "which spatial virtual table prefilters the stores-near-me query before the haversine sort",
     "sqlite r tree virtual table bounding box haversine latitude longitude"),
    # --- 13 ---
    ("Imported the legacy CSV dumps with the SQLite CSV virtual table so we can SELECT against the file directly without a load step; a one-off migration used it to reconcile two years of invoices in an hour.", "fact", "technical", False,
     [("SQLite", "database"), ("CSV virtual table", "library"), ("invoice", "concept")],
     [("CSV virtual table", "SQLite", "EXTENDS")],
     "which SQLite virtual table let us SELECT against raw CSV without a load step during invoice reconciliation",
     "sqlite csv virtual table select file load migration invoice"),
    # --- 14 ---
    ("The JSON1 extension is now the only JSON path; every code path uses json_extract, json_each, and json_group_array instead of parsing strings in the application layer after pulling blobs out.", "decision", "technical", False,
     [("JSON1", "library"), ("json_extract", "api"), ("json_each", "api"), ("json_group_array", "api")],
     [("JSON1", "json_extract", "IMPLEMENTS")],
     "which SQLite extension replaced application-side JSON parsing and which three operators cover most queries",
     "sqlite json1 json extract each group array application parse"),
    # --- 15 ---
    ("Series virtual table generate_series(1, 1000) fills the calendar-dim table without a host-side loop; a recursive CTE used to do the same job but the virtual table keeps the schema migration single-statement.", "preference", "technical", False,
     [("generate_series", "api"), ("virtual table", "concept"), ("recursive CTE", "concept")],
     [("generate_series", "recursive CTE", "PREFERS")],
     "which SQLite virtual table fills calendar-dim rows and what did it replace in the migration",
     "sqlite generate series virtual table recursive cte calendar migration"),
    # --- 16 ---
    ("Generated columns on the orders table materialise tax and total from the base line items; STORED generated columns get indexed like any normal column, so the reporting view no longer recomputes on every read.", "fact", "technical", False,
     [("generated columns", "concept"), ("STORED", "config"), ("orders table", "concept")],
     [("generated columns", "STORED", "USES")],
     "which SQLite feature materialises tax and total columns so reports stop recomputing on every read",
     "sqlite generated column stored indexed orders tax total report"),
    # --- 17 ---
    ("Rolled the reporting dashboards onto SQLite window functions; ROW_NUMBER, LAG, and SUM OVER replaced a nest of correlated subqueries and the quarterly comparison query runs in sub-second time.", "milestone", "technical", False,
     [("window functions", "concept"), ("ROW_NUMBER", "api"), ("LAG", "api"), ("SUM OVER", "api"), ("SQLite", "database")],
     [("window functions", "SQLite", "EXTENDS")],
     "which SQL feature replaced correlated subqueries on the reporting dashboards and which window operators matter most",
     "sqlite window function row number lag sum over correlated subquery"),
    # --- 18 ---
    ("The org-chart traversal uses WITH RECURSIVE on a parent_id column; SQLite's common-table-expression (CTE) support handles the closure walk without a stored procedure, which we would not have had anyway.", "fact", "technical", False,
     [("WITH RECURSIVE", "concept"), ("CTE", "concept"), ("parent_id", "concept"), ("SQLite", "database")],
     [("WITH RECURSIVE", "SQLite", "EXTENDS")],
     "which SQL construct walks the org-chart closure in SQLite without relying on a stored procedure",
     "sqlite with recursive cte parent id org chart closure walk"),
    # --- 19 ---
    ("Migrated SQLite schema definitions to STRICT tables on the new service; the type affinity footgun where inserting 'abc' into an INTEGER column silently stored a TEXT value is now a hard error instead of a surprise.", "decision", "technical", False,
     [("SQLite", "database"), ("STRICT tables", "concept"), ("type affinity", "concept"), ("INTEGER", "config")],
     [("STRICT tables", "type affinity", "REPLACES")],
     "which SQLite table mode replaced type-affinity laxness and what class of silent bug did it retire",
     "sqlite strict table type affinity integer text silent bug"),
    # --- 20 ---
    ("The SQLite RETURNING clause dropped a round trip on every order insert; the INSERT now returns the generated id and timestamp in the same statement, replacing a follow-up SELECT last_insert_rowid() call.", "decision", "technical", False,
     [("SQLite", "database"), ("RETURNING clause", "concept"), ("INSERT", "command"), ("last_insert_rowid()", "api")],
     [("RETURNING clause", "last_insert_rowid()", "REPLACES")],
     "which SQLite clause dropped a second round trip after INSERT and what did it replace",
     "sqlite returning clause insert last insert rowid round trip"),
    # --- 21 ---
    ("SQLite ON CONFLICT DO UPDATE is the upsert pattern on the user-settings table; matching on the unique key either inserts the row or bumps updated_at, and the application no longer needs a SELECT-then-branch.", "preference", "technical", False,
     [("SQLite", "database"), ("ON CONFLICT", "concept"), ("DO UPDATE", "concept"), ("upsert", "concept")],
     [("ON CONFLICT", "upsert", "IMPLEMENTS")],
     "which SQLite upsert pattern replaced the select-then-branch on user settings",
     "sqlite on conflict do update upsert user settings unique"),
    # --- 22 ---
    ("AFTER UPDATE triggers sync the audit_log table whenever a row in accounts changes; the trigger body writes the old and new JSON blobs with json_object so downstream consumers always see the diff.", "fact", "technical", False,
     [("AFTER UPDATE trigger", "concept"), ("audit_log", "concept"), ("json_object", "api"), ("accounts", "concept")],
     [("AFTER UPDATE trigger", "audit_log", "PRODUCES")],
     "which trigger populates the audit log on account changes and how are old and new values captured",
     "sqlite after update trigger audit log accounts json object"),
    # --- 23 ---
    ("Adopted SQLCipher for the on-device store on the mobile client; transparent AES-256 page encryption replaced our previous app-layer field encryption and key rotation is now a single PRAGMA rekey call.", "decision", "technical", False,
     [("SQLCipher", "library"), ("AES-256", "algorithm"), ("PRAGMA rekey", "command"), ("field encryption", "concept")],
     [("SQLCipher", "field encryption", "REPLACES"), ("PRAGMA rekey", "SQLCipher", "CONFIGURES")],
     "which encryption layer replaced app-level field encryption on the mobile store and how does key rotation work",
     "sqlcipher aes 256 pragma rekey field encryption mobile rotate"),
    # --- 24 ---
    ("Litestream streams WAL segments to S3 continuously from the edge VPS; a crash-restart on the primary rehydrates from the last WAL segment and the RPO is measured in single-digit seconds.", "architecture", "technical", False,
     [("Litestream", "tool"), ("WAL", "concept"), ("S3", "service"), ("edge VPS", "infrastructure")],
     [("Litestream", "S3", "DEPLOYED_ON"), ("Litestream", "WAL", "USES")],
     "which tool streams SQLite WAL segments to S3 and what is the recovery-point objective it achieves",
     "litestream sqlite wal s3 edge vps rpo replication stream"),
    # --- 25 ---
    ("Moved multi-region reads to LiteFS on Fly.io; the FUSE-backed distributed file system gives every region a read replica of the SQLite file, and write forwarding to the primary is handled in-process.", "milestone", "technical", False,
     [("LiteFS", "tool"), ("Fly.io", "platform"), ("FUSE", "concept"), ("SQLite", "database")],
     [("LiteFS", "Fly.io", "DEPLOYED_ON"), ("LiteFS", "FUSE", "USES")],
     "which distributed file system gave multi-region SQLite reads on Fly.io and how does it surface replicas",
     "litefs fly io fuse sqlite multi region replica write forward"),
    # --- 26 ---
    ("Simon Willison's sqlite-utils is the default CLI for ad-hoc work; piping JSON into sqlite-utils insert creates the schema, indexes a column, and returns a queryable file in one shell command.", "preference", "technical", False,
     [("sqlite-utils", "tool"), ("Simon Willison", "person"), ("JSON", "technology"), ("CLI", "concept")],
     [("sqlite-utils", "Simon Willison", "AUTHORED_BY")],
     "which CLI do we reach for on ad-hoc SQLite work and who wrote it",
     "sqlite utils cli simon willison json insert schema ad hoc"),
    # --- 27 ---
    ("sqlite-web gets launched against the prod replica when a support engineer needs to poke at rows; the tiny Flask UI beats installing a desktop GUI client and the replica is read-only so nothing gets clobbered.", "fact", "technical", False,
     [("sqlite-web", "tool"), ("Flask", "framework"), ("prod replica", "infrastructure")],
     [("sqlite-web", "Flask", "USES")],
     "which tool lets support engineers browse the prod replica without a desktop GUI",
     "sqlite web flask prod replica read only support browser"),
    # --- 28 ---
    ("Published the open-data snapshots through Datasette; Simon Willison's publish command wraps the database in a read-only JSON API with facets, which means the frontend team stopped asking for bespoke endpoints.", "milestone", "technical", False,
     [("Datasette", "tool"), ("Simon Willison", "person"), ("JSON API", "concept"), ("facets", "concept")],
     [("Datasette", "Simon Willison", "AUTHORED_BY")],
     "which tool turns a SQLite file into a read-only JSON API with facets and who authored it",
     "datasette simon willison json api facet read only snapshot"),
    # --- 29 ---
    ("iOS Core Data still runs on top of SQLite under the hood; dropping to raw FMDB for the bulk-import path was cheaper than fighting managed-object-context merge conflicts on 50k rows.", "decision", "technical", False,
     [("Core Data", "framework"), ("SQLite", "database"), ("FMDB", "library"), ("iOS", "platform")],
     [("Core Data", "SQLite", "USES"), ("FMDB", "Core Data", "REPLACES")],
     "which iOS persistence path dropped under Core Data for bulk import and what is its backing store",
     "ios core data sqlite fmdb bulk import managed object context"),
    # --- 30 ---
    ("Android Room generates the SQLite schema and DAO code at compile time; the @Query annotations get validated against the actual schema, which caught two drift bugs before they shipped.", "architecture", "technical", False,
     [("Room", "library"), ("SQLite", "database"), ("Android", "platform"), ("@Query", "api")],
     [("Room", "SQLite", "USES"), ("Room", "Android", "DEPLOYED_ON")],
     "which Android library validates SQL against the actual SQLite schema at compile time",
     "android room sqlite dao query annotation compile schema drift"),
    # --- 31 ---
    ("Picked DuckDB over SQLite for the analytics-only service; columnar storage, vectorised execution, and native Parquet reads demolished the row-based scan path on our six-way joins.", "decision", "technical", False,
     [("DuckDB", "database"), ("SQLite", "database"), ("Parquet", "technology"), ("columnar storage", "concept")],
     [("DuckDB", "SQLite", "REPLACES")],
     "which embedded OLAP engine replaced SQLite for the analytics service and what made the difference",
     "duckdb sqlite parquet columnar vectorised analytics join scan"),
    # --- 32 ---
    ("The embedded KV under the indexer moved from SQLite to libmdbx after the B-tree page-split pattern on monotonically-increasing keys spiked write amplification; mdbx copy-on-write pages behaved better.", "problem", "technical", False,
     [("libmdbx", "library"), ("SQLite", "database"), ("B-tree", "algorithm"), ("copy-on-write", "concept")],
     [("libmdbx", "SQLite", "REPLACES")],
     "which embedded KV replaced SQLite under the indexer and what B-tree pathology forced the swap",
     "libmdbx sqlite b tree page split write amplification copy on write"),
    # --- 33 ---
    ("LMDB powers the session cache in the gateway; memory-mapped reads with zero-copy keys meant the hot path bypasses the user-space allocator entirely, and p99 on session lookup sits under 50 microseconds.", "architecture", "technical", False,
     [("LMDB", "library"), ("session cache", "concept"), ("memory-mapped", "concept"), ("gateway", "service")],
     [("LMDB", "gateway", "DEPLOYED_ON")],
     "which embedded database backs the gateway session cache and what latency does the memory map deliver",
     "lmdb session cache gateway memory map zero copy p99 microsecond"),
    # --- 34 ---
    ("RocksDB sits under the write-heavy event store; LSM compaction copes with the append rate where a B-tree engine would have been buried, and tiered compression keeps disk spend flat.", "milestone", "technical", False,
     [("RocksDB", "library"), ("LSM", "algorithm"), ("B-tree", "algorithm"), ("event store", "service")],
     [("RocksDB", "LSM", "USES"), ("RocksDB", "B-tree", "REPLACES")],
     "which embedded engine underpins the event store and what compaction model does it use",
     "rocksdb lsm b tree event store compaction append write heavy"),
    # --- 35 ---
    ("Sled was fun to prototype against but we dropped it for the durable pipeline; the project maintainer explicitly flagged it as beta and the sister project Fjall is taking the LSM torch forward.", "decision", "technical", False,
     [("Sled", "library"), ("Fjall", "library"), ("LSM", "algorithm")],
     [("Fjall", "Sled", "REPLACES")],
     "which Rust embedded database replaced Sled for the durable pipeline after a beta-status warning",
     "sled fjall rust embedded lsm beta durable pipeline"),
    # --- 36 ---
    ("Rust services use rusqlite for the SQLite bindings; compile-time prepared statements via the include_str! macro mean a typo in SQL fails the build, not a 3 a.m. pager.", "reference", "technical", False,
     [("rusqlite", "library"), ("SQLite", "database"), ("Rust", "language"), ("include_str!", "api")],
     [("rusqlite", "SQLite", "USES"), ("Rust", "rusqlite", "USES")],
     "which Rust SQLite binding catches SQL typos at build time and which macro loads the query",
     "rusqlite rust sqlite include str compile time prepared statement"),
    # --- 37 ---
    ("better-sqlite3 is the Node.js binding to SQLite on the CLI tools; the synchronous API is the right call there because there is no event loop to starve and the numbers on bulk insert clobber async bindings.", "decision", "technical", False,
     [("better-sqlite3", "library"), ("Node.js", "platform"), ("SQLite", "database")],
     [("better-sqlite3", "SQLite", "USES"), ("better-sqlite3", "Node.js", "DEPLOYED_ON")],
     "which synchronous Node binding powers the CLI tools and why is the sync API correct there",
     "better sqlite3 node cli synchronous api bulk insert event loop"),
    # --- 38 ---
    ("sqlx in its offline mode ships a cached schema so the Rust service compiles without a live database; the build step runs cargo sqlx prepare against a dev SQLite file and commits the JSON cache.", "architecture", "technical", False,
     [("sqlx", "library"), ("SQLite", "database"), ("Rust", "language"), ("cargo sqlx prepare", "command")],
     [("sqlx", "SQLite", "USES"), ("cargo sqlx prepare", "sqlx", "CONFIGURES")],
     "which Rust query crate supports an offline schema cache and what command populates it",
     "sqlx rust sqlite offline cargo prepare schema cache compile"),
    # --- 39 ---
    ("Python async services use aiosqlite on the IO boundary; the thread-pool executor under the hood is a compromise because libsqlite3 is synchronous, but the async surface stays consistent with the rest of asyncio.", "architecture", "technical", False,
     [("aiosqlite", "library"), ("Python", "language"), ("asyncio", "framework"), ("libsqlite3", "library")],
     [("aiosqlite", "asyncio", "USES"), ("aiosqlite", "libsqlite3", "USES")],
     "which Python library gives an async surface over the synchronous libsqlite3 and what is under the hood",
     "aiosqlite python asyncio libsqlite3 thread pool async surface"),
    # --- 40 ---
    ("Swapped the stdlib sqlite3 module for pysqlite3 on the analytics workers because the shipped Python was pinned to an old SQLite build without JSON1 or window functions support; pysqlite3-binary carries a newer library.", "problem", "technical", False,
     [("pysqlite3", "library"), ("sqlite3", "library"), ("JSON1", "library"), ("window functions", "concept"), ("Python", "language")],
     [("pysqlite3", "sqlite3", "REPLACES")],
     "which Python module replaced stdlib sqlite3 on workers and what features were missing from the bundled build",
     "pysqlite3 stdlib python json1 window function analytics worker"),
    # --- 41 ---
    ("SQLite itself is maintained by D. Richard Hipp and the SQLite consortium; the codebase has the TH3 test harness with branch coverage over 100 percent, which is why we trust a file-shaped database in production.", "reference", "technical", False,
     [("SQLite", "database"), ("D. Richard Hipp", "person"), ("TH3", "tool"), ("SQLite consortium", "organization")],
     [("SQLite", "D. Richard Hipp", "AUTHORED_BY"), ("TH3", "SQLite", "APPLIES_TO")],
     "who maintains SQLite and which proprietary test harness gives it over 100 percent branch coverage",
     "sqlite richard hipp consortium th3 test harness branch coverage"),
    # --- 42 ---
    ("Richard Hipp originally wrote SQLite in 2000 for a US Navy project on General Dynamics guided-missile destroyers; that origin story is in the official documentation and is why the public-domain license still holds.", "reference", "technical", False,
     [("SQLite", "database"), ("Richard Hipp", "person"), ("US Navy", "organization"), ("public-domain", "concept")],
     [("SQLite", "Richard Hipp", "AUTHORED_BY")],
     "which 2000 Navy project birthed SQLite and which license choice dates to that origin",
     "sqlite richard hipp us navy general dynamics public domain 2000"),
    # --- 43. noise ---
    ("Someone left a birthday cake in the kitchen with no name on the card and the third-floor team is in a standoff about whether it is polite to cut it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference the PRAGMA journal_mode documentation when onboarding new engineers; the page enumerates DELETE, TRUNCATE, PERSIST, MEMORY, WAL, and OFF with the trade-offs of each, and the WAL section links out to the WAL2 future-work notes.", "reference", "technical", False,
     [("PRAGMA journal_mode", "command"), ("WAL", "concept"), ("DELETE", "config"), ("TRUNCATE", "config"), ("PERSIST", "config"), ("MEMORY", "config")],
     [("PRAGMA journal_mode", "WAL", "CONFIGURES")],
     "which SQLite doc page covers the journal-mode options and how they trade off durability",
     "sqlite pragma journal mode delete truncate persist memory wal off"),
    # --- 45 ---
    ("Keep the FTS5 contentless-table trick in the playbook; declaring content='' tells SQLite to skip storing the indexed text, and we point the BM25 ranker at the primary orders table via an external-content FTS index.", "reference", "technical", False,
     [("FTS5", "library"), ("contentless-table", "concept"), ("external-content", "concept"), ("BM25", "algorithm")],
     [("FTS5", "BM25", "IMPLEMENTS")],
     "which FTS5 storage trick avoids duplicating indexed text while still supporting BM25 ranking",
     "fts5 contentless external content bm25 orders index duplicate"),
    # --- 46 ---
    ("Turned on SQLite PRAGMA temp_store=MEMORY on the batch importer; temporary b-trees for ORDER BY and GROUP BY stay in RAM instead of spilling to the temp file, which cut the long aggregation runs by about 40 percent.", "decision", "technical", False,
     [("SQLite", "database"), ("PRAGMA temp_store", "command"), ("MEMORY", "config"), ("ORDER BY", "api"), ("GROUP BY", "api")],
     [("PRAGMA temp_store", "SQLite", "CONFIGURES")],
     "which SQLite pragma keeps temporary b-trees in RAM and which clauses benefit most on the batch importer",
     "sqlite pragma temp store memory order by group by aggregation"),
    # --- 47 ---
    ("Shipped the first milestone of the offline-first mobile client: SQLite under SQLCipher on device, Litestream replicating to S3, and a LiteFS-backed primary on Fly.io tying the two ends together.", "milestone", "technical", False,
     [("SQLite", "database"), ("SQLCipher", "library"), ("Litestream", "tool"), ("LiteFS", "tool"), ("Fly.io", "platform"), ("S3", "service")],
     [("SQLCipher", "SQLite", "EXTENDS"), ("Litestream", "S3", "DEPLOYED_ON"), ("LiteFS", "Fly.io", "DEPLOYED_ON")],
     "which four-piece stack ties the offline-first mobile client to a Fly.io primary and S3 archive",
     "offline mobile sqlite sqlcipher litestream litefs fly io s3"),
    # --- 48 ---
    ("Landed the cross-database migration milestone: moved the analytics pipeline from SQLite to DuckDB while keeping SQLite for the OLTP service, with the same sqlite-utils import tooling feeding both engines.", "milestone", "technical", False,
     [("SQLite", "database"), ("DuckDB", "database"), ("sqlite-utils", "tool"), ("analytics pipeline", "service")],
     [("DuckDB", "SQLite", "REPLACES"), ("sqlite-utils", "DuckDB", "APPLIES_TO")],
     "which dual-engine split landed with sqlite-utils feeding both the OLTP SQLite and the analytics DuckDB",
     "sqlite duckdb sqlite utils analytics oltp pipeline migration"),
    # --- 49 ---
    ("Published a reference runbook for SQLite corruption triage: first PRAGMA integrity_check, then PRAGMA quick_check, then .recover in the sqlite3 CLI, and only if all three fail do we restore from the last Litestream generation.", "reference", "technical", False,
     [("PRAGMA integrity_check", "command"), ("PRAGMA quick_check", "command"), (".recover", "command"), ("Litestream", "tool"), ("sqlite3 CLI", "tool")],
     [("PRAGMA integrity_check", "sqlite3 CLI", "APPLIES_TO")],
     "which three-step corruption triage runs before we fall back to a Litestream restore",
     "sqlite integrity check quick recover cli litestream corruption runbook"),
    # --- 50 ---
    ("Preferred binding stack across services: rusqlite for Rust, better-sqlite3 for Node CLIs, aiosqlite for Python async, and sqlx for the Rust services that need compile-time query checking against a dev SQLite file.", "preference", "technical", False,
     [("rusqlite", "library"), ("better-sqlite3", "library"), ("aiosqlite", "library"), ("sqlx", "library"), ("SQLite", "database")],
     [("rusqlite", "SQLite", "USES"), ("better-sqlite3", "SQLite", "USES"), ("aiosqlite", "SQLite", "USES"), ("sqlx", "SQLite", "USES")],
     "which SQLite bindings are preferred across Rust services, Node CLIs, and Python async code",
     "rusqlite better sqlite3 aiosqlite sqlx binding preference rust node python"),
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
