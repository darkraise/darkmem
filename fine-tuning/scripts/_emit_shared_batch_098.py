"""One-off emitter for shared-base batch-098 — technical domain (data formats and serialization protocols).

Writes 50 rows to data/v2/shared/batch_098.tmp.jsonl with ids shared-04851..04900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_098.tmp.jsonl"
ID_OFFSET = 4850

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Apache Parquet page statistics carry min, max, and null counts per column chunk; the row-group reader skipped 78 percent of pages before touching the bytes.", "architecture", "technical", False,
     [("Apache Parquet", "technology")],
     [],
     "which Parquet metadata layer drove the row-group page skipping",
     "page statistic min max null count column chunk skip"),
    # --- 2 ---
    ("Parquet dictionary encoding kicked in on the low-cardinality country column; the compressed size fell by 11x versus plain encoding even before Snappy ran.", "fact", "technical", False,
     [("Parquet", "technology"), ("Snappy", "algorithm")],
     [],
     "which Parquet encoding compressed the low-cardinality country column",
     "dictionary encoding low cardinality size fall before codec"),
    # --- 3 ---
    ("ZSTD replaced Snappy as the default Parquet codec on the cold-tier tables; ratio improved from 2.9x to 4.1x at level 3 with the same decode throughput.", "decision", "technical", False,
     [("ZSTD", "algorithm"), ("Snappy", "algorithm"), ("Parquet", "technology")],
     [("ZSTD", "Snappy", "REPLACES")],
     "which codec displaced Snappy for Parquet on the cold-tier storage",
     "ZSTD Snappy Parquet cold codec swap ratio level"),
    # --- 4 ---
    ("Apache Arrow in-memory columnar buffers fed the analytic IPC stream; Arrow replaced the protobuf-on-the-wire path for cross-process analytic handoff.", "decision", "technical", False,
     [("Apache Arrow", "technology"), ("IPC", "protocol"), ("Arrow", "technology"), ("protobuf", "technology")],
     [("Arrow", "protobuf", "REPLACES")],
     "which format took over analytic IPC from the protobuf wire path",
     "Arrow columnar IPC cross process protobuf swap analytic"),
    # --- 5 ---
    ("Feather v2 files were used for scratch dataframe handoff between Python and R; random-access read beat reparsing a CSV on every notebook boot.", "preference", "technical", False,
     [("Feather", "technology"), ("Python", "language"), ("R", "language"), ("CSV", "technology")],
     [("Feather", "CSV", "REPLACES")],
     "which file format displaced CSV for scratch cross-language dataframes",
     "Feather v2 scratch dataframe hand off random access CSV"),
    # --- 6 ---
    ("Arrow Flight shipped the query result stream between the compute node and the BI tool; gRPC framing on Arrow record batches beat a REST plus JSON encoding by 18x.", "architecture", "technical", False,
     [("Arrow Flight", "protocol"), ("gRPC", "protocol"), ("REST", "protocol"), ("JSON", "technology")],
     [("Arrow Flight", "REST", "REPLACES")],
     "which transport replaced REST plus JSON for the BI result stream",
     "Arrow Flight gRPC record batch REST JSON throughput swap"),
    # --- 7 ---
    ("Apache ORC kept the Hive warehouse native format; stripe-level indexes and lightweight compression were tuned for the HDFS block size, not object storage.", "fact", "technical", False,
     [("Apache ORC", "technology"), ("Hive", "technology"), ("HDFS", "technology")],
     [],
     "which columnar format stayed native to the Hive warehouse on HDFS",
     "ORC stripe index lightweight compression block size warehouse"),
    # --- 8 ---
    ("Avro schemas carried the writer schema alongside every file; reader schemas resolved added fields by default value and dropped removed fields silently.", "reference", "technical", False,
     [("Avro", "technology")],
     [],
     "which Avro mechanic handled added and removed fields across versions",
     "writer reader schema default value drop evolve resolve"),
    # --- 9 ---
    ("Avro replaced JSON on the change-data feed; embedded schema plus binary framing cut payload size by 7x and made producer-consumer drift visible at decode.", "decision", "technical", False,
     [("Avro", "technology"), ("JSON", "technology")],
     [("Avro", "JSON", "REPLACES")],
     "which binary encoding took over from JSON on the change-data feed",
     "Avro JSON feed schema binary framing size drift swap"),
    # --- 10. noise ---
    ("Hold up, my kettle's boiling.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Protocol Buffers proto3 replaced proto2 on new service schemas; required fields were dropped in favor of explicit presence via wrapper types.", "decision", "technical", False,
     [("Protocol Buffers", "technology"), ("proto3", "technology"), ("proto2", "technology")],
     [("proto3", "proto2", "REPLACES")],
     "which ProtoBuf revision took over for new schemas and why",
     "proto3 proto2 required field drop wrapper presence swap"),
    # --- 12 ---
    ("Protobuf well-known types like Timestamp and Duration standardized date handling across the polyglot fleet; ad-hoc int64 millis were retired from the contracts.", "decision", "technical", False,
     [("Protobuf", "technology"), ("Timestamp", "concept"), ("Duration", "concept")],
     [("Timestamp", "Duration", "RELATED_TO")],
     "which Protobuf types took over from ad-hoc millisecond integers",
     "well known type Timestamp Duration contract polyglot swap"),
    # --- 13 ---
    ("Apache Thrift powered the legacy analytics RPC; the tagged field-id plus compact protocol kept cross-language parity with the Hadoop-era services.", "fact", "technical", False,
     [("Apache Thrift", "technology"), ("Hadoop", "technology")],
     [],
     "which RPC framing served the legacy Hadoop-era analytics services",
     "Thrift compact protocol field id tagged legacy Hadoop"),
    # --- 14 ---
    ("FlatBuffers improved on Protobuf for the game's replay format; zero-copy read without a parse step fit the 60-fps inner loop.", "decision", "technical", False,
     [("FlatBuffers", "technology"), ("Protobuf", "technology")],
     [("FlatBuffers", "Protobuf", "IMPROVES_ON")],
     "which serialization beat Protobuf for the zero-copy replay path",
     "FlatBuffers Protobuf zero copy parse step game replay swap"),
    # --- 15 ---
    ("Cap'n Proto was evaluated against FlatBuffers for the IPC shared-memory channel; infinite-sized messages and RPC promise pipelining tipped the choice.", "decision", "technical", False,
     [("Cap'n Proto", "technology"), ("FlatBuffers", "technology"), ("IPC", "protocol")],
     [("Cap'n Proto", "FlatBuffers", "IMPROVES_ON")],
     "which zero-copy format won the shared-memory IPC channel decision",
     "Cap n Proto FlatBuffers shared memory pipeline IPC swap"),
    # --- 16 ---
    ("MessagePack carried the mobile client payloads; type-tagged binary kept schemaless flexibility while halving the JSON byte count.", "architecture", "technical", False,
     [("MessagePack", "technology"), ("JSON", "technology")],
     [("MessagePack", "JSON", "REPLACES")],
     "which binary encoding replaced JSON on the mobile client wire",
     "MessagePack binary JSON schemaless half byte mobile swap"),
    # --- 17 ---
    ("CBOR replaced JSON on the constrained IoT channel; RFC 8949 framing plus tagged semantic types matched the COSE signing envelope cleanly.", "decision", "technical", False,
     [("CBOR", "technology"), ("JSON", "technology"), ("COSE", "protocol"), ("RFC 8949", "publication")],
     [("CBOR", "JSON", "REPLACES")],
     "which binary JSON took over on the IoT constrained channel with COSE",
     "CBOR JSON IoT constrained RFC COSE tagged semantic swap"),
    # --- 18 ---
    ("BSON stayed inside the MongoDB storage engine only; on-the-wire traffic moved to MessagePack because BSON's embedded-length overhead hurt small-document throughput.", "problem", "technical", False,
     [("BSON", "technology"), ("MongoDB", "database"), ("MessagePack", "technology")],
     [("MessagePack", "BSON", "REPLACES")],
     "which encoding displaced BSON on the wire outside MongoDB storage",
     "BSON embedded length MessagePack wire small doc throughput"),
    # --- 19 ---
    ("Apache Iceberg managed Parquet files as a table with snapshot, manifest, and partition-spec metadata; schema evolution stayed ACID at the table layer.", "architecture", "technical", False,
     [("Apache Iceberg", "technology"), ("Parquet", "technology")],
     [("Apache Iceberg", "Parquet", "BUILDS_ON")],
     "which table format wrapped Parquet with snapshot and manifest metadata",
     "Iceberg snapshot manifest partition spec ACID table Parquet"),
    # --- 20 ---
    ("Delta Lake layered a JSON transaction log over Parquet; the _delta_log directory replaced the bespoke audit-trail sidecar the team used to maintain.", "decision", "technical", False,
     [("Delta Lake", "technology"), ("JSON", "technology"), ("Parquet", "technology")],
     [("Delta Lake", "Parquet", "BUILDS_ON")],
     "which format layered a JSON transaction log atop Parquet files",
     "Delta Lake transaction log JSON audit trail sidecar Parquet"),
    # --- 21 ---
    ("Apache Hudi's merge-on-read table kept a row-oriented Avro delta log next to Parquet base files; near-real-time ingestion avoided full Parquet rewrites.", "architecture", "technical", False,
     [("Apache Hudi", "technology"), ("Avro", "technology"), ("Parquet", "technology")],
     [("Apache Hudi", "Parquet", "BUILDS_ON")],
     "which table format combined Avro delta logs with Parquet base files",
     "Hudi merge on read Avro delta Parquet base near real time"),
    # --- 22 ---
    ("LZ4 was preferred over Snappy for the hot Parquet tier; the decode throughput gap at query time dwarfed the small ratio difference.", "preference", "technical", False,
     [("LZ4", "algorithm"), ("Snappy", "algorithm"), ("Parquet", "technology")],
     [("LZ4", "Snappy", "IMPROVES_ON")],
     "which codec beat Snappy for the hot Parquet tier on decode",
     "LZ4 Snappy Parquet hot tier decode throughput prefer"),
    # --- 23 ---
    ("Brotli was tried on Parquet long-term archival but abandoned; the compressed size win did not pay for the 6x slower encode on the ingest pipeline.", "problem", "technical", False,
     [("Brotli", "algorithm"), ("Parquet", "technology")],
     [],
     "which codec was rejected on Parquet because encode cost was too high",
     "Brotli Parquet archive encode slow ingest ratio win reject"),
    # --- 24 ---
    ("JSON Lines replaced the mixed-file CSV dump for the analytics export; one JSON object per line streamed cleanly through jq and downstream loaders.", "decision", "technical", False,
     [("JSON Lines", "technology"), ("CSV", "technology"), ("jq", "tool")],
     [("JSON Lines", "CSV", "REPLACES")],
     "which line-delimited format took over from CSV on analytics export",
     "JSON Lines CSV jq stream loader analytics export swap"),
    # --- 25 ---
    ("NDJSON and JSON Lines were treated as equivalent wire formats in the spec; the loader accepted both extensions to avoid breaking older producers.", "fact", "technical", False,
     [("NDJSON", "technology"), ("JSON Lines", "technology")],
     [("NDJSON", "JSON Lines", "IS_A")],
     "which pair of formats did the loader treat as equivalent",
     "NDJSON JSON Lines equivalent extension loader producer"),
    # --- 26 ---
    ("Confluent Schema Registry governed Avro schema evolution; backward-compatible adds and forward-compatible removes were enforced at publish time, not decode.", "architecture", "technical", False,
     [("Confluent Schema Registry", "tool"), ("Avro", "technology")],
     [],
     "which registry gated Avro schema evolution at publish time",
     "backward forward compatible add remove enforce decode avoid"),
    # --- 27 ---
    ("Apicurio Registry replaced Confluent Schema Registry on the self-hosted stack; the broader Protobuf plus JSON Schema support justified the cut-over.", "decision", "technical", False,
     [("Apicurio Registry", "tool"), ("Confluent Schema Registry", "tool"), ("Protobuf", "technology"), ("JSON Schema", "technology")],
     [("Apicurio Registry", "Confluent Schema Registry", "REPLACES")],
     "which self-hosted schema registry took over from the Confluent one",
     "Apicurio Confluent Protobuf JSON Schema registry swap"),
    # --- 28 ---
    ("Parquet column statistics were disabled on the sensitive PII columns; min/max leakage was worse than the skip-performance gain for the auditors.", "decision", "technical", False,
     [("Parquet", "technology"), ("PII", "concept")],
     [],
     "which Parquet feature was disabled on the sensitive PII columns",
     "column statistic PII min max leak skip perf auditor disable"),
    # --- 29 ---
    ("The Parquet Bloom filter page was enabled for point-lookup columns; false-positive rate stayed under 1 percent at 10 bits per key.", "architecture", "technical", False,
     [("Parquet", "technology"), ("Bloom filter", "algorithm")],
     [("Parquet", "Bloom filter", "USES")],
     "which Parquet optional page accelerated point-lookup queries",
     "Parquet Bloom filter false positive point lookup page enable"),
    # --- 30 ---
    ("Avro's logical types carried decimal, timestamp-millis, and UUID across the warehouse; ad-hoc string encodings were banned from new schemas.", "decision", "technical", False,
     [("Avro", "technology"), ("UUID", "concept")],
     [],
     "which Avro feature standardized decimal, timestamp, and UUID handling",
     "logical type decimal timestamp UUID schema ban string swap"),
    # --- 31 ---
    ("Protobuf's Any type was avoided in public APIs; the bundled type URL plus opaque bytes broke backward compatibility tooling in the registry.", "preference", "technical", False,
     [("Protobuf", "technology"), ("Any", "concept")],
     [],
     "which Protobuf type was avoided because it broke registry tooling",
     "Any type URL opaque backward compat registry tooling avoid"),
    # --- 32 ---
    ("Protobuf field numbers 19000 through 19999 were reserved by the spec; the internal style guide kept user-defined fields in 1-15 to hit the 1-byte tag.", "reference", "technical", False,
     [("Protobuf", "technology")],
     [],
     "which Protobuf tag range was reserved by the spec",
     "field number reserved 19000 1 byte tag style guide"),
    # --- 33 ---
    ("Cap'n Proto packed encoding traded zero-copy for wire size; the team disabled packing on the shared-memory channel and enabled it on the network hop only.", "decision", "technical", False,
     [("Cap'n Proto", "technology")],
     [],
     "which Cap'n Proto toggle was split between shared memory and network",
     "packed encoding zero copy trade shared memory network toggle"),
    # --- 34. noise ---
    ("Hang on, dog needs walking.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Arrow IPC streaming format and file format shared the same record-batch layout; the file format added a footer with block offsets for random access.", "reference", "technical", False,
     [("Arrow IPC", "protocol")],
     [],
     "which Arrow variants differ only by footer and random-access offsets",
     "Arrow IPC streaming file format footer block offset random"),
    # --- 36 ---
    ("ORC Zlib compression stayed on the cold partitions; the ratio beat ZSTD at default level for the specific wide-string columns in the warehouse.", "fact", "technical", False,
     [("ORC", "technology"), ("Zlib", "algorithm"), ("ZSTD", "algorithm")],
     [],
     "which ORC codec won on the wide-string cold partitions",
     "ORC Zlib ZSTD cold partition wide string ratio default"),
    # --- 37 ---
    ("Parquet V2 data pages replaced V1 on the new warehouse ingest; definition and repetition levels moved out of the compressed block for better skip performance.", "decision", "technical", False,
     [("Parquet V2", "technology"), ("V1", "technology")],
     [("Parquet V2", "V1", "REPLACES")],
     "which Parquet page version took over on the new warehouse ingest",
     "V2 V1 definition repetition level compress skip page swap"),
    # --- 38 ---
    ("Iceberg's hidden partitioning decoupled physical layout from the query predicate; partition evolution avoided full-table rewrites that Hive-style partitioning forced.", "architecture", "technical", False,
     [("Iceberg", "technology"), ("Hive", "technology")],
     [("Iceberg", "Hive", "IMPROVES_ON")],
     "which Iceberg feature avoided full-table rewrites on partition change",
     "hidden partition predicate decouple rewrite avoid Iceberg Hive"),
    # --- 39 ---
    ("Delta Lake's deletion vectors replaced copy-on-write rewrites for small delete loads; the per-row bitmap kept Parquet files immutable at the page level.", "decision", "technical", False,
     [("Delta Lake", "technology"), ("Parquet", "technology")],
     [("Delta Lake", "Parquet", "USES")],
     "which Delta feature avoided Parquet rewrites on small delete loads",
     "deletion vector copy on write bitmap Parquet immutable swap"),
    # --- 40 ---
    ("MessagePack's str8 type was added in spec 2.0; older Ruby clients pinned to spec 1.0 decoded it as bin8 and mangled UTF-8 strings.", "problem", "technical", False,
     [("MessagePack", "technology"), ("Ruby", "language"), ("UTF-8", "technology")],
     [],
     "which MessagePack spec bump bit the older Ruby clients",
     "str8 bin8 spec 2 Ruby UTF 8 mangle pin decode"),
    # --- 41 ---
    ("CBOR deterministic encoding rules were required for the COSE_Sign1 envelope; sorted map keys and shortest integer encoding landed signatures that verified across languages.", "architecture", "technical", False,
     [("CBOR", "technology"), ("COSE_Sign1", "protocol")],
     [("CBOR", "COSE_Sign1", "SUPPORTS")],
     "which CBOR rules made COSE_Sign1 signatures portable across languages",
     "deterministic sort map shortest integer COSE sign verify"),
    # --- 42 ---
    ("FlatBuffers schema required explicit field IDs after the first addition; the compiler enforced the rule to preserve binary layout across versions.", "reference", "technical", False,
     [("FlatBuffers", "technology")],
     [],
     "which FlatBuffers rule preserved binary layout across versions",
     "schema field id explicit compiler enforce binary layout"),
    # --- 43 ---
    ("Protobuf to Arrow conversion was codegen'd once at ingest; keeping one canonical in-memory format cut downstream serializer sprawl across four teams.", "decision", "technical", False,
     [("Protobuf", "technology"), ("Arrow", "technology")],
     [("Arrow", "Protobuf", "REPLACES")],
     "which format became canonical in-memory after the Protobuf conversion",
     "Protobuf Arrow codegen canonical memory serializer sprawl"),
    # --- 44 ---
    ("Avro's union types with null were the schema idiom for optional fields; Protobuf fans had to unlearn the implicit-default habit from proto3.", "fact", "technical", False,
     [("Avro", "technology"), ("Protobuf", "technology"), ("proto3", "technology")],
     [],
     "which Avro idiom expressed optional fields across the schema set",
     "union null optional field Avro Protobuf proto3 default idiom"),
    # --- 45 ---
    ("JSON Schema governed the REST API bodies; draft 2020-12 was pinned because the $dynamicRef machinery carried the recursive user-tree validator.", "decision", "technical", False,
     [("JSON Schema", "technology"), ("REST", "protocol")],
     [],
     "which JSON Schema draft the REST API pinned and why",
     "JSON Schema draft 2020 12 dynamicRef recursive user tree"),
    # --- 46 ---
    ("Parquet encryption with uniform mode was shipped on 2026-02-14; the footer-only key wrap kept the reader path simple versus per-column encryption.", "milestone", "technical", False,
     [("Parquet", "technology"), ("2026-02-14", "date")],
     [],
     "when did uniform Parquet encryption ship and what tradeoff drove it",
     "uniform mode footer key wrap encryption ship simple reader"),
    # --- 47 ---
    ("Thrift's TCompactProtocol replaced TBinaryProtocol on the mobile wire; varint field tags cut the payload size 30 percent on typical requests.", "decision", "technical", False,
     [("TCompactProtocol", "protocol"), ("TBinaryProtocol", "protocol"), ("Thrift", "technology")],
     [("TCompactProtocol", "TBinaryProtocol", "REPLACES")],
     "which Thrift protocol took over from the binary one on the mobile wire",
     "compact binary protocol varint field tag payload mobile swap"),
    # --- 48 ---
    ("ORC predicate pushdown used stripe-level bloom filters and SARG evaluation; the query engine skipped stripes before the compressed bytes were touched.", "architecture", "technical", False,
     [("ORC", "technology"), ("SARG", "concept")],
     [],
     "which ORC machinery drove the stripe-level predicate pushdown",
     "predicate pushdown stripe bloom SARG skip compressed engine"),
    # --- 49 ---
    ("ZSTD dictionary mode compressed the small JSON events 4.3x better than raw ZSTD; the shared dictionary was the schema registry entry, not a separate file.", "architecture", "technical", False,
     [("ZSTD", "algorithm"), ("JSON", "technology")],
     [("ZSTD", "JSON", "APPLIES_TO")],
     "which ZSTD mode compressed small JSON events via a shared dictionary",
     "dictionary mode small JSON share schema registry ratio"),
    # --- 50 ---
    ("The lake rewrite to Iceberg plus ZSTD-Parquet finished 2026-03-30; storage footprint fell 58 percent and Trino scan time fell 41 percent on the benchmark.", "milestone", "technical", False,
     [("Iceberg", "technology"), ("ZSTD", "algorithm"), ("Parquet", "technology"), ("Trino", "technology"), ("2026-03-30", "date")],
     [("Iceberg", "Parquet", "BUILDS_ON")],
     "when did the Iceberg plus ZSTD Parquet lake rewrite finish and the win",
     "Iceberg ZSTD Parquet Trino footprint scan time rewrite date"),
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
