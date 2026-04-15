"""One-off emitter for retrieval top-up batch-026 — multi-sentence queries.

Each row pairs a longer, paragraph-shaped query (2-4 sentences, 20-60 words) with
its source shared row as the positive. Queries simulate a careful user typing out
context and a specific question instead of a terse search phrase.

Writes 100 rows to data/v2/retrieval/batch_026.tmp.jsonl with ids ret-02501..02600,
pulling positives from shared rows at zero-indexed offsets 2500..2599.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_026.tmp.jsonl"
ID_OFFSET = 2500
SHARED_OFFSET = 2500
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with shared rows 2501..2601.
QUERIES: list[str] = [
    # 02501 Kiwi.com for Lisbon open-jaw
    "We're planning a messy open-jaw itinerary to Lisbon with a train segment in the middle. Which flight aggregator ended up taking over from Google Flights for that kind of trip, and what specifically did Google refuse to price?",
    # 02502 ExpertFlyer over SeatSpy Polaris
    "Award-seat hunting for United Polaris has been hit-and-miss on one tool. Which tracker is preferred over SeatSpy for that, and what does its fare-class rules layer catch that SeatSpy's crawler apparently misses?",
    # 02503 SmartEX Shinkansen Tokyo trip
    "A Tokyo trip in May is coming up and the Japan Rail Pass situation has shifted. Which booking tool handles the Shinkansen reservations now, and why did we stop relying on the Japan Rail Pass for the Nozomi runs?",
    # 02504 Wanderlog replaced Google Sheet Iceland
    "Our shared trip planning used to live in a Google Sheet. When did it move to a dedicated app, and what specifically about the Iceland ring-road itinerary finally made Mei push for the switch?",
    # 02505 Airalo vs Holafly Thailand
    "We split data-eSIM duty between two providers this year. Which one handles short city hops versus the long Thailand stay, and what was the deciding factor for picking the second one for Chiang Mai?",
    # 02507 Citymapper vs Google London
    "Our London transit week went surprisingly smoothly despite weekend works. Which app beat Google Maps for that trip, and what specifically about its overlays caught the Jubilee closure before official alerts fired?",
    # 02508 Organic Maps Dolomites
    "We needed truly offline maps for a hike in the Dolomites. Which region pack was pre-downloaded, and what did we discover about AllTrails' offline tier that pushed us away from relying on it?",
    # 02509 Deutsche Bahn Navigator Bahncard
    "Trainline used to be the default for European rail bookings on the phone. Which app replaced it, and what specifically changed with the Bahncard 50 discount that forced the switch?",
    # 02510 Splitwise Kyoto Wise FX
    "Group expenses for the Kyoto trip across four travelers needed to stay clean. Which app kept the tally, and what was the lucky alignment between the card statements and the app's FX rate for the JPY receipts?",
    # 02511 Wise replaced Revolut Prague
    "Our primary travel card changed in late January. Which card replaced Revolut, and what specific event in Prague tipped the decision after a weekend of Christmas markets?",
    # 02512 PackPoint plus Google Keep Patagonia
    "Packing for a Patagonia trek needed both a structured checklist and custom tracking. Which tool produced the base list, where did the custom gear list ultimately live, and what specifically couldn't the first tool handle?",
    # 02513 Booking.com Genius discount Porto
    "There was a frustrating experience with a Porto hotel booking on Valentine's Day. Which discount silently dropped at checkout, and roughly how long did the refund dispute drag on afterwards?",
    # 02514 Mobile Passport Control JFK
    "Re-entering the US at JFK used to mean paper customs forms at a Global Entry kiosk. Which app replaced that workflow, and what did it pre-file before the plane even arrived at the gate?",
    # 02515 Rome2Rio over Google Maps Bari Patras
    "For the planning phase of a Greek island trip, Google Maps was hiding options. Which tool is preferred over Google Maps, and what specific overnight ferry route did it surface that Google buried?",
    # 02516 Timeshifter Sydney jet lag
    "A long flight to Sydney in June had me worried about jet lag. Which app produced the plan, and what specific shift did it recommend that actually paid off on the first day in country?",
    # 02517 Amex Travel Greece honeymoon
    "Honeymoon booking for Greece moved off one travel portal. Which portal took over from Chase Ultimate Rewards, and which two benefits finally stacked at the Santorini property that couldn't be combined before?",
    # 02518 Navigo Easy Apple Wallet Paris
    "The Paris metro carnet of paper tickets is officially retired for my setup. What replaced it on the phone, and what edge case around the iPhone battery reserve turned out to still work at the turnstiles?",
    # 02519 Anki iCloud Tokyo flight
    "Japanese flashcard study needed to survive a long-haul flight with no Wi-Fi. Which app kept the streak alive during the Tokyo flight, and what happened with the queued cards once the connection came back at Haneda?",
    # 02520 Rick Steves Borghese Bluetooth
    "Touring the Borghese Gallery in Rome felt eerily seamless with an audio guide. Which guide was being used, and what mechanism auto-advanced the narration as I walked through the rooms?",
    # 02521 Immich selective sync Marrakech
    "Photo backup while roaming in Marrakech threatened to blow the data budget. Which sync mode kept things efficient, and what still uploaded every night from the riad despite the selective setting?",
    # 02522 Polar H10 Komoot Mallorca
    "Training rides in Mallorca needed cleaner turn-by-turn than the watch could give. Which apps were chained together for the route, and why did the Garmin end up beating the Polar watch's prompts in practice?",
    # 02523 World Nomads Seoul claim
    "A Seoul flight cancellation in early February triggered an insurance claim. Which provider processed it, roughly how long did the payout take, and what paperwork from the booking site had to be attached?",
    # 02524 Subsurface dive logbook Egypt
    "Paper dive logbooks had to go before an Egypt liveaboard trip. Which app replaced the logbook, and what specific export did it produce that the dive shop needed for its fill records?",
    # 02525 Google Translate Pixel 9 Hanoi
    "Ordering street food in Hanoi without hostel Wi-Fi seemed risky. Which app carried the translation on a Pixel 9, and what specifically about its Vietnamese two-way mode made it hostel-independent?",
    # 02526 Nomad List Lisbon coworking
    "Finding a Lisbon co-working plan under a tight budget had been dragging on. Which tool finally surfaced a workable option, and what two constraints actually had to line up before it stuck?",
    # 02527 Tokyo Metro app Shinjuku exits
    "Google Maps alone keeps sending me out of Shinjuku Station at the wrong exit. Which additional app stayed on the phone for that reason, and what offline feature specifically saves the day there?",
    # 02528 HealthPassport Kenya yellow fever
    "Paper yellow-fever certificates felt fragile going into a Kenya trip at the end of March. Which app replaced that workflow, and where specifically did the electronic version need to be presented first?",
    # 02529 Booking.com replaced Airbnb Buenos Aires
    "Airbnb had a bad run for a Buenos Aires trip in late April. What finally got booked instead, how many Airbnb cancellations preceded the switch, and what property of the replacement booking calmed the nerves?",
    # 02530 Strava Wahoo Bolt Cotswolds
    "Two rainy days on a Cotswolds bike-packing loop wrecked the phone bar mount. Which device pair carried the navigation through it, and what specifically about the head unit's cues kept working when the iPhone didn't?",
    # 02531 Matrix ITA Doha vs Istanbul
    "Skyscanner's cheapest-first ranking keeps hiding the pain of bad layovers. Which sort style is preferred instead, and what specific layover comparison between two Gulf hubs is it actually good at surfacing?",
    # 02532 Roadtrippers Pro PCH RV
    "A Pacific Coast Highway trip on July 4 needed an RV-aware planning tool. Which subscription turned out to be worth the money, and what specifically did it catch that Google's truck-route overlay missed?",
    # 02533 Google Sheets importHTML KLM
    "Long-lead award availability tracking for SkyTeam is still better than every dedicated fare alert. Which spreadsheet trick handles it, and what free trigger keeps the KLM calendar polled every ten minutes?",
    # 02534 noise
    "The other side just said to hold while they dig through notes. Should I treat that as a normal pause in the conversation, or is there something I should be doing on my end while the check happens?",
    # 02535 Mobile Passport Control photo Mexico City
    "The iOS pre-file flow for Mobile Passport Control broke on one specific return trip. When exactly did it fail, and which step inside the app rejected three times in a row because of the lighting?",
    # 02536 Google Maps Hokkaido offline Noboribetsu
    "An offline area download for Hokkaido left a gap around one onsen town. Which town wasn't covered, why did it fall outside the download box, and what specifically made that painful at the ryokan?",
    # 02537 Chase Sapphire Priority Pass Lisbon
    "LoungeBuddy had been drifting out of date for one important airport. Which filter replaced its search, and what specific Lisbon lounge disappeared from LoungeBuddy's database that pushed the switch?",
    # 02538 Gravitymark Julian Sicily
    "A family-built rental aggregator beat the big-name platforms for a Sicily villa hunt in 2026. Who built it, what stack is it on, and which two services did it outperform on that trip?",
    # 02539 Uber vs Bolt Lisbon Amex
    "In Lisbon, the normal ride-hailing preference flipped. Which app is preferred over Bolt there, and what specific Amex Platinum credit detail made that preference economically obvious for the Bairro Alto rides?",
    # 02540 TripIt Pro Heathrow Edinburgh
    "A customs delay at Heathrow on February 24 threatened a connection to Edinburgh. Which tool pinged the rebook before the gate agent's queue formed, and which airline's alert did it actually front-run?",
    # 02541 ExpertFlyer Qsuites Alaska
    "A Qatar Qsuites opening showed up at 3am my time for an August Doha flight. Which seat-alert tool caught it, and which partner program was the award ultimately booked through before the space vanished?",
    # 02542 Hotwire Denver Marriott
    "For a one-night Denver layover the usual Marriott loyalty booking didn't make sense. Which opaque-rate product replaced the direct booking, what star level came in, and roughly what price tipped the decision?",
    # 02543 Windy Santorini ferry
    "A Santorini ferry run on May 9 got canceled by weather a full day early. Which app's wind-gust forecast warned first, and which dedicated ferry app only caught up later with the operator notice?",
    # 02544 Schiphol KLM Delta self-transfer
    "A self-transfer at Schiphol with KLM and Delta got stuck at the boarding pass. What specifically could the KLM app not do, and what had already happened on the Delta partner leg back at JFK that caused it?",
    # 02545 Notion Wanderlog Croatia sailing
    "A June Croatia sailing trip itinerary outgrew the usual planning tool. Where does it live now, why did the previous tool choke, and how were the fourteen marina waypoints originally sent over?",
    # 02546 DJI Mini 4 Pro Airdata World Nomads
    "For trip footage and insurance paperwork, the camera choice matters more than it used to. Which drone is preferred over the GoPro 13, and which flight-log service ties its data into the insurance-claim workflow?",
    # 02547 Bogota Airbnb hot water
    "A Bogota Airbnb stay on January 30 lost hot water for most of the trip. How many of the four nights were affected, what was the refund outcome through the Superhost dispute, and how much actually came back?",
    # 02548 Obsidian D7 visa Portugal
    "Expat paperwork tracking moved off Google Docs when the Portugal D7 renewal hit. Which vault app took over, when did the switch happen, and what specifically had to be organized differently for the consulate?",
    # 02549 Seat31B Avianca LifeMiles Point.me
    "One blog post tipped me to a Star Alliance sweet spot I wouldn't have found elsewhere. Which blog and which post gave the hint, and which polished search tool still doesn't surface that same routing?",
    # 02550 Remote Year Splitwise Mei Chiang Mai
    "A cohort dinner in early April lined up with a small personal milestone. Which program was the cohort part of, what balance finally zeroed out, and which trip had made the original split messy?",
    # 02551 Postgres WAL replay wal_receiver_timeout
    "A Postgres streaming replica kept stalling on WAL replay. Which timeout on the replica was misaligned with the primary, and what tuning change pulled the streaming lag back inside a second?",
    # 02552 autovacuum orders table
    "The orders table hit 40 percent bloat between manual vacuum runs. What threshold was dropped on autovacuum, and which companion setting was also raised in lockstep to keep cleanup aggressive?",
    # 02553 HOT updates covering index
    "HOT updates on one table were degrading over time. What was happening inside the ctid chain when the update went non-HOT, and which indexing change restored the HOT ratio afterwards?",
    # 02554 TOAST LZ4 pglz
    "TOAST compression on a document column got reworked. Which algorithm replaced pglz, and what happened to read latency versus compression ratio after the swap?",
    # 02555 fillfactor 70 ledger
    "A heavily updated ledger table was thrashing indexes on every update. What fillfactor value did it drop to, and what specifically did the resulting free space let HOT updates avoid during peak hour?",
    # 02556 pg_stat_statements bitmap random_page_cost
    "One prepared statement was burning 60 percent of cluster CPU. Which extension surfaced it, and what planner knob tuning flipped the plan onto a bitmap scan afterwards?",
    # 02557 pg_repack VACUUM FULL
    "The maintenance window for clustering a billion-row table had been dreaded for months. Which tool replaced VACUUM FULL, and what kept the rebuild from showing a downtime banner to users?",
    # 02558 BRIN vs GIN time series
    "A time-series partition's index choice turned out to be far smaller than expected. Which index type beat GIN there, why did the correlation with insertion order matter, and roughly how much did the index size shrink?",
    # 02559 GiST vs GIN geometry
    "Spatial overlap predicates weren't a clean fit for our default index type. Which index kind ended up being used for the geometry workload, and what property of operator classes decided the call?",
    # 02560 noise
    "The other side just said they need to grab an explain plan before answering. Is this a pause worth waiting through, or should I nudge them while they go look?",
    # 02561 INCLUDE covering Postgres 15
    "One dashboard query got fast enough to avoid heap fetches entirely. Which indexing feature on Postgres 15 unlocked index-only scans there, and what had to happen with VACUUM before the heap fetch count in EXPLAIN went to zero?",
    # 02562 parallel seq scan 2GB
    "Parallel sequential scan on the analytics cluster had a clear tipping point. Around what size did it start paying off, and what specifically dominated the cost below that threshold?",
    # 02563 hash join orders customers work_mem
    "A join between orders and customers was spilling sorts to disk. Which join algorithm replaced merge join, what setting was doubled to enable that, and roughly how much did latency drop?",
    # 02564 MVCC xmin report replica
    "A long-running report on a hot table was blocking autovacuum. Which MVCC concept was behind that interaction, and what topology change freed the xmin horizon without killing the report?",
    # 02565 SSI reservation serialization_failure
    "Our reservation flow had a phantom write bug that only appeared under concurrency. Which Postgres isolation level caught it, and what pattern kept throughput acceptable when the anomaly was detected?",
    # 02566 ULID InnoDB orders
    "Random UUID primary keys were fragmenting the InnoDB B+ tree on the orders table. What ID scheme replaced them, and what secondary-index pain specifically cleared up once the keys became monotonic?",
    # 02567 MyISAM retired InnoDB
    "The legacy reporting database was still on MyISAM until recently. What replaced it, and which two specific shortcomings of MyISAM couldn't stand up to the new write volume?",
    # 02568 InnoDB undo tablespaces 200 GB
    "Undo data on InnoDB used to live in the system tablespace and was bloating it. What structural change let us reclaim space, and roughly how much storage came back after truncation during off-hours?",
    # 02569 RocksDB L0 stalls compactions
    "RocksDB started stalling writes under load. Which two settings had to be raised together, and what behavior in the L0 layer cleared up once the compactions caught up to the flush rate?",
    # 02570 leveled vs tiered compaction
    "We run different RocksDB compaction styles for different workloads. Which style suits the read-heavy metrics store, and which one stayed on the audit log where read amplification mattered less?",
    # 02571 universal compaction session store
    "One RocksDB store needed burst-friendly compaction. Which compaction style was chosen for it, and which amplification trade-off did we accept in exchange for keeping SST file counts low?",
    # 02572 bloom bits-per-key 16
    "Negative lookups on an SSTable-backed service were hammering disk. Which structure was tuned to cut them, and what was the before-and-after bits-per-key setting once the miss rate spiked?",
    # 02573 ClickHouse TTL S3 tiered
    "The ClickHouse cluster was running hot on local NVMe. Which tiered-storage feature pushed cold parts out to S3-backed volumes, and what target size was the hot tier kept under once the move rules kicked in?",
    # 02574 FoundationDB versionstamps
    "Our append-only event feed used to embed wall-clock timestamps from clients. What replaced those as the authoritative ordering, and which database's feature made that possible?",
    # 02575 CockroachDB range splits 512 MB
    "CockroachDB range management has a clear threshold for splitting. Around what size does it trigger, and what latency behavior did we see during the accompanying raft lease transfers?",
    # 02576 Spanner TrueTime commit wait
    "Global external consistency isn't free in Spanner. Which mechanism bounds the clock uncertainty, and what operational cost does the commit wait add in exchange for the linearisable guarantee?",
    # 02577 TiDB Placement Rules EU replicas
    "A compliance tenant on TiDB must never leave the EU. Which feature pins its replicas, and how did analytics queries still get cross-region follower reads without violating that?",
    # 02578 Yugabyte tablet auto-splitting range
    "Yugabyte hot shards were overloading single nodes. What feature kept the shards from hogging a node, and what triggered the sharding-strategy flip once composite keys entered the schema?",
    # 02579 DuckDB vectorised pandas ETL
    "A pandas ETL pipeline on a 5 GB parquet was painful on my laptop. Which engine's vectorised execution replaced it, and roughly how long did the same aggregation end up taking afterwards?",
    # 02580 MonetDB Vertica OLAP
    "An OLAP benchmark pitted two column-stores against each other on long join chains. Which one won, and what architectural difference between column-at-a-time and pipelined vectorised execution was the deciding factor?",
    # 02581 extended statistics ndistinct correlated
    "A correlated-predicate query on Postgres was getting wildly bad row estimates. Which feature fixed the underestimate, and what plan change followed once the ndistinct statistic became honest?",
    # 02582 pg_hint_plan approved escape-hatch
    "Our stance on planner hints is deliberately conservative. Which extension is approved, under what narrow conditions is it allowed, and what's the default posture on hints otherwise?",
    # 02583 plan_cache_mode force_custom_plan
    "Prepared-statement plan caching was hurting one multi-tenant service. What specifically went wrong for skewed tenants, and which setting value fixed it by forcing custom plans each time?",
    # 02584 noise
    "Someone on the other side said they're tailing the log and need a second. Should I just sit tight, or is this pause long enough that I should poke the conversation along?",
    # 02585 pt-osc gh-ost MySQL
    "Online DDL on MySQL has changed tools over time in our environment. Which tool handled the earlier column-type widening, and which one replaced it once foreign-key handling and binlog tailing were mature enough?",
    # 02586 logical replication cross-major
    "A Postgres major-version upgrade used to mean a physical streaming setup. Which replication style replaced it for cross-major upgrades, and which additional migration option did per-table filtering unlock?",
    # 02587 archive_command warm standby
    "During a network outage the warm standby still had to stay current. Which mechanism held it over the gap, and what resumed once the link came back and caught up the feed?",
    # 02588 ClickHouse AVX-512 funnel
    "The funnel query on ClickHouse got much faster on newer hosts. Which SIMD path doubled aggregation throughput, and what happens on hosts that don't support it?",
    # 02589 RocksDB LevelDB embedded
    "Our embedded metadata service used to run on LevelDB. What replaced it, and which two features alone were enough to justify the swap even before tombstone handling entered the case?",
    # 02590 Cassandra bucketed time composite
    "A Cassandra wide-row design was suffering on deletes. What changed in the clustering-key layout to bring tombstone scans back inside safe thresholds?",
    # 02591 B+ tree vs LSM OLTP
    "Two storage engines competed for a small-key OLTP workload. Which design won, and what two specific behaviors tipped the call against the LSM alternative?",
    # 02592 LSM vs B-tree telemetry ingestion
    "For a separate ingestion-heavy telemetry store the storage call went the other way. Which design was preferred there, which trade-off was acceptable, and when did the compactions actually run?",
    # 02593 CockroachDB raft etcd
    "CockroachDB's range-rebalancer traces a lineage back to another open-source system. Which project pioneered the raft lease design it leans on, and what abstraction did Cockroach add on top?",
    # 02594 Citus sharding manual partitioning
    "Manual partitioning on Postgres had been hand-rolled for a while before one extension landed. Which tool now handles sharding, and what specific cross-node cost did its hash-distributed tables cut down?",
    # 02595 CockroachDB F1 Spanner TrueTime
    "Open-source distributed SQL still lives in Spanner's shadow in some ways. Which project improves on the Spanner F1 approach for workloads where TrueTime isn't available, and what remains Spanner's unmatched property?",
    # 02596 Vitess MySQL VTGate YouTube
    "Vitess predates its open-source life by a good margin. Which company's pre-open-source proxy pattern does the sharding build on, and what component abstracts the shard map so application code stays single-node-like?",
    # 02597 ScyllaDB Seastar shard-per-core
    "ScyllaDB took a different concurrency path from Cassandra. Which architectural model is it built on, which framework ties each shard to a reactor, and what hardware assumption does that choice lean into?",
    # 02598 ZHeap Postgres MVCC
    "A Postgres storage experiment aimed at avoiding MVCC bloat never quite made mainline. What was it called, what goal was it pursuing on updates, and what happened to the work afterwards?",
    # 02599 pgBackRest homegrown basebackup
    "Our primary Postgres cluster used to be backed up by a homegrown basebackup wrapper. Which tool replaced it, and which two features drove the decision over the custom script?",
    # 02600 Postgres 16 parallel hash aggregate
    "Postgres 16's planner improvements landed in our analytics cluster on March 9. Which feature specifically cut funnel query runtime, roughly by how much, and what knob had to be tuned up to take advantage of it?",
    # 02601 BuildBuddy Bazel us-east-2
    "A Bazel monorepo's remote-execution farm moved to a new provider and region. Which service handles the execution, where were the self-hosted executors brought online, and what happened to p95 action wall time as a result?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SHARED.open("r", encoding="utf-8") as f:
        shared_lines = f.readlines()
    positives = [json.loads(l) for l in shared_lines[SHARED_OFFSET:SHARED_OFFSET + 100]]
    assert len(positives) == 100, f"expected 100 positives, got {len(positives)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (query, pos) in enumerate(zip(QUERIES, positives), start=1):
            row_id = f"ret-{ID_OFFSET + i:05d}"
            row = {
                "id": row_id,
                "source_id": pos["id"],
                "query": query,
                "positive": pos["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
