"""Emit retrieval top-up batch-011 (code-switch kind).

For shared rows shared-01001..shared-01100, emit one code-switch retrieval row
each. Each query mixes English with another language; the other language varies
across the 100 items.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_011.tmp.jsonl"

ID_OFFSET = 1000
SHARED_OFFSET = 1000
QUERY_KIND = "code-switch"

# 100 code-switch queries, each 5-20 words, mixing English with a varying
# second language. The second language rotates across ~40 languages.
QUERIES: list[str] = [
    # 01001 Readwise -> Zotero pipeline, PDF annotations, ebook quotes (Spanish)
    "How do I pipe Readwise highlights a Zotero cada domingo for thesis prep notes?",
    # 01002 Bayesian stats Allen Downey replaced Gelman (French)
    "Quel livre de statistiques bayesiennes replaced Gelman with Python notebooks?",
    # 01003 Merriam-Webster cron -> Anki GRE deck (German)
    "Which nightly cron zieht word-of-the-day entries into Anki cards for GRE prep?",
    # 01004 JupyterHub on Hetzner for weekend math (Italian)
    "Dov'e hosted the self-hosted JupyterHub per weekend mathematics notebooks?",
    # 01005 Logseq molecular biology + Campbell textbook (Portuguese)
    "Qual ferramenta guarda molecular biology notes com backlinks para Campbell chapters?",
    # 01006 SM-17 paper -> Anki FSRS scheduler (Vietnamese)
    "Bai bao nao ve spaced repetition da lam toi chuyen sang FSRS scheduler?",
    # 01007 Paperpile vs Mendeley, neuroscience reading group (Japanese romaji)
    "Naze wa user ga prefers Paperpile over Mendeley for neuroscience reading group calls?",
    # 01008 Hypothesis arXiv -> Obsidian via Pandoc (Korean romaja)
    "Eotteohge Hypothesis annotations go into Obsidian through a Pandoc filter matil?",
    # 01009 Linux Kernel Development by Robert Love replaced Bovet (Mandarin pinyin)
    "Shenme shu replaced Bovet for learning the Linux kernel xiangmu?",
    # 01010 Noise row (Russian transliterated) - still produce a natural code-switch query
    "Podozhdi a second poka I switch tabs na drugoye okno please.",
    # 01011 Coursera deep-learning certificate landed 2026-02-14 (Arabic transliterated)
    "Mata hasal al-certificate for the Coursera deep-learning specialisation ba'd arba'a shuhur?",
    # 01012 TiddlyWiki Stoicism Chromebook, Dendron too heavy (Hindi transliterated)
    "Kaunsa tool chalaata hai my Stoicism commonplace book on the old Chromebook?",
    # 01013 Apple Health + ARIMA in R for desk bike (Indonesian)
    "Bagaimana I exported Apple Health step history dan ran ARIMA fit di R?",
    # 01014 Kindle -> Notion via Readwise, linguistics tag (Swedish)
    "Hur flyter Kindle highlights in i Notion through the official Readwise integration?",
    # 01015 Overleaf -> local TeXLive quantum writeups (Dutch)
    "Welke LaTeX workflow verving Overleaf with local TeXLive voor quantum writeups?",
    # 01016 Lichess + Aimchess time pressure middlegame (Polish)
    "Dlaczego I lose most chess games to time pressure w srodkowej grze?",
    # 01017 SkySafari -> Flask app -> bedroom TV (Turkish)
    "Hangi app logs my amateur astronomy sessions and gosterir them on bedroom TV?",
    # 01018 Streamlit + Kaggle climate, Fellowship.ai due 2026-05-01 (Greek transliterated)
    "Poia dashboard did I build on top of Kaggle climate data for Fellowship.ai submission?",
    # 01019 CS229 notes in DEVONthink + Stanford problem sets (Hebrew transliterated)
    "Eifo sit ha-CS229 lecture notes alongside the Stanford problem sets for full-text search?",
    # 01020 Duolingo + Lingvist + Pimsleur rotate, Korean plateau (Tagalog)
    "Bakit ko ini-rotate Duolingo, Lingvist, at Pimsleur every week para sa Korean study?",
    # 01021 Oura ring -> DuckDB + Quarto notebook Sunday (Thai transliterated)
    "Oura ring khayan exports JSON nightly into which DuckDB file that I query weekly?",
    # 01022 Feynman QED on Plex vs Griffiths, kids ask about light (Swahili)
    "Ni video gani ya Feynman I stream kwenye Plex when the kids ask about light?",
    # 01023 Khan Academy cousin -> Airtable -> grandma in Lisbon (Finnish)
    "Miten cousin's Khan Academy progress shows up in shared Airtable for grandma Lissabonissa?",
    # 01024 Sipser Theory of Computation + Obsidian pumping lemma (Czech)
    "Ktera kniha o theory of computation went faster once pumping lemma notes were tagged?",
    # 01025 Go Discord bot -> arXiv ML digest, 8am daily (Norwegian)
    "Hvilken Discord-bot written in Go rotates arXiv machine learning digest klokka atte?",
    # 01026 Noise row (Danish)
    "Selvfolgelig, jeg er happy to help with that lille opgave.",
    # 01027 ChessBase imports from Lichess, Caro-Kann prep (Catalan)
    "Quina eina imports Lichess studies into ChessBase for Caro-Kann opening prep?",
    # 01028 Hargrave group theory Calibre replaced Dummit and Foote (Hungarian)
    "Melyik konyv replaced Dummit and Foote for the abstract algebra weekend session?",
    # 01029 Leitner box 365 days, Python reminder script, 2026-03-30 (Romanian)
    "Cand am atins 365 consecutive days cu Leitner box si script Python pentru reminders?",
    # 01030 MIT OCW -> Whisper Markdown for commute (Ukrainian transliterated)
    "Yaka pipeline dumps MIT OpenCourseWare lectures into Whisper-corrected Markdown dlya komyuta?",
    # 01031 Zotero iPad sync dropped chapters before Tuesday seminar (Filipino/Cebuano)
    "Unsa nga Zotero iPad sync issue silently dropped two chapters sa dili pa ang Tuesday seminar?",
    # 01032 Karpathy zero-to-hero + Mei in Taipei PyTorch (Malay)
    "Siapa rakan belajar di Taipei yang drove the Sunday transformer build-along dalam PyTorch?",
    # 01033 Open Library API -> Raycast -> Zotero (Serbian transliterated)
    "Koji Raycast extension vuce ISBN from Open Library directly into my Zotero inbox?",
    # 01034 Feynman technique Notion beats AI summary, Standard Model (Croatian)
    "Koja tehnika written out by hand u Notion beats AI summaries for the Standard Model?",
    # 01035 Tandem with Pablo Thursday, Italki unavailable (Slovak)
    "Ktoreho dna in the week mam conversation practice s Pablom cez Tandem?",
    # 01036 Rust Programming Language replaced Programming Rust, Tokio (Slovenian)
    "Katera knjiga je replaced Programming Rust once the Tokio async chapter bila prepisana?",
    # 01037 Goedel Escher Bach done 2026-04-07, Supernote -> Obsidian (Bulgarian transliterated)
    "Koga zavarshih reading Goedel Escher Bach with margin notes synced sa Supernote and Obsidian?",
    # 01038 Raspberry Pi Pico + Drosophila + SQLite lab journal (Estonian)
    "Mis Raspberry Pi Pico setup stamps Drosophila behaviour timestamps into the SQLite labori paeviku?",
    # 01039 Google Sheet -> Apps Script -> Habitica Khan (Latvian)
    "Kurs Apps Script beidzot pushes daily Khan Academy deltas from a Google Sheet into Habitica?",
    # 01040 Cambridge Handbook Computing Education in Zotero (Lithuanian)
    "Kuri knyga replaced a stack of blog posts su cognitive load research properly cited?",
    # 01041 Jupyter kernels over Colab, air-gapped demos (Icelandic)
    "Hvers vegna ég prefers building Jupyter kernels fyrir each class over shared Colab notebooks?",
    # 01042 GitHub Classroom nbgrader Docker autograder (Maltese)
    "Liema nbgrader setup fixed the GitHub Classroom autograder fil-kors Docker container?",
    # 01043 Coursera Scala capstone Akka actor supervision (Albanian)
    "Cili kapaciteti project perdori a small Akka cluster to grok actor supervision?",
    # 01044 Category theory Toggl + Mac Lane on iPad Pro (Welsh)
    "Pa lyfr sydd open on iPad Pro while Toggl timer runs for category theory self-study?",
    # 01045 Polar HR -> R Markdown -> coach Saturday (Basque)
    "Zein R Markdown pipeline turns Polar heart rate data into PDF coach-era bidali larunbatetan?",
    # 01046 2026-03-15 CS50x homework delay, Linode outage (Galician)
    "Por que houbo a 2026-03-15 homework delay para o Harvard CS50x final exam submission?",
    # 01047 PyMC + Efron 1979 bootstrap (Afrikaans)
    "Hoekom het confidence in Bayes gegroei when PyMC confirmed Efron's 1979 bootstrap estimates?",
    # 01048 Sabine reverberation + REW study room (Irish Gaeilge)
    "Cen teoiric le Sabine a threoraigh the room-correction script running in REW every time?",
    # 01049 Chinchilla scaling -> nanoGPT on RTX 3090 (Esperanto)
    "Kiu paper kaj nanoGPT run kuris sur RTX 3090 por senti la token loss curve?",
    # 01050 Remnote + Clayden org chem beat Sketchy November retest (Persian/Farsi transliterated)
    "Kodam flashcard setup dar Remnote with Clayden structures shekast Sketchy videos for retention?",
    # 01051 Snowflake external tables Iceberg bronze layer (Spanish)
    "Que Snowflake external tables apuntan al bronze layer so lake files stay queryable sin load step?",
    # 01052 BigQuery slot reservations vs on-demand quarter-close (French)
    "Pourquoi les slot reservations dans BigQuery ont remplace on-demand pricing pour the analytics workspace?",
    # 01053 Databricks SQL Unity Catalog governance (German)
    "Welche Governance-Regeln gelten jetzt for Databricks SQL warehouses und Unity Catalog notebooks?",
    # 01054 Redshift RA3 managed storage resize (Italian)
    "Come Redshift RA3 nodes con managed storage let us resize compute senza reshuffling blocks?",
    # 01055 Delta Lake -> Iceberg engine-agnostic Trino Flink (Portuguese)
    "Porque o time moveu new tables from Delta Lake para Apache Iceberg for engine-agnostic reads?",
    # 01056 Hudi copy-on-write CDC, merge-on-read later (Vietnamese)
    "Apache Hudi copy-on-write tables da dung cho first CDC sink o cho cai nao truoc?",
    # 01057 Kafka Connect Debezium Postgres, replication slot (Japanese romaji)
    "Naze wa the replication slot is survive suru connector restarts without replay storms?",
    # 01058 Pulsar over Kafka, tiered storage, multi-tenant (Korean romaja)
    "Waeyo Apache Pulsar is preferred over Kafka for the multi-tenant analytics bus daesinoro?",
    # 01059 Kinesis on-demand clickstream (Mandarin pinyin)
    "Weishenme on-demand mode removed the capacity-planning mafan from the Kinesis clickstream pipeline?",
    # 01060 Noise row (Arabic transliterated)
    "Khalli ni double-check that partition spec real quick min fadhlik please.",
    # 01061 ClickHouse MergeTree event day TTL (Hindi transliterated)
    "Kaunsa ClickHouse MergeTree partition scheme keeps TTL drops cheap for product analytics dashboards?",
    # 01062 Druid sub-second funnel roll-up trade-off (Indonesian)
    "Mengapa Apache Druid handles sub-second slice-and-dice on funnel pages dengan roll-up di ingest?",
    # 01063 Pinot beat Druid real-time leaderboards upsert (Swedish)
    "Varfor Apache Pinot beat Druid for real-time leaderboards utan en secondary reconciler?",
    # 01064 Doris replaced lambda pipeline ad-hoc OLAP (Dutch)
    "Welke engine verving a home-grown lambda pipeline voor ad-hoc OLAP met unified batch and stream ingest?",
    # 01065 StarRocks mid-TB cost-per-query vectorised (Polish)
    "Dlaczego StarRocks improves on legacy MPP warehouses w kwestii kosztu-na-zapytanie at mid-TB scale?",
    # 01066 Airbyte replaced Python ingest, dbt normalisation (Turkish)
    "Hangi tool took over bespoke Python ingest scripts for SaaS connectors ve dbt normalisation?",
    # 01067 Fivetran rejected for Airbyte PII residency (Greek transliterated)
    "Giati Fivetran was rejected in favour of Airbyte for PII residency self-hosting control?",
    # 01068 Qlik Replicate DB2 mainframe CDC (Hebrew transliterated)
    "Eize tool mekhase the mainframe-to-lake CDC path keeping DB2 off the critical-path commit log?",
    # 01069 dbt Core state-based CI selection (Tagalog)
    "Paano dbt Core models compile into warehouse-native SQL at ano ang state-based CI selection?",
    # 01070 SQLMesh over dbt virtual envs column lineage (Thai transliterated)
    "Thammai SQLMesh is preferred over dbt with virtual environments and column-level lineage removed?",
    # 01071 Dataform shelved off BigQuery (Swahili)
    "Kwa nini Dataform iliwekwa pembeni wakati warehouse ilitoka BigQuery kwenda polyglot stack?",
    # 01072 Airflow -> Dagster heartbeat backfills (Finnish)
    "Miksi kriittiset DAG:it siirtyivat Airflow'sta Dagsteriin to stop silent task backfills?",
    # 01073 Prefect 2 over Airflow, small pipelines (Czech)
    "Proc Prefect 2 is preferred over Airflow for malych internal pipelines without DAG ceremony?",
    # 01074 Great Expectations gate dbt merges (Norwegian)
    "Hvilke Great Expectations suites gate merges pa core fact tables before dbt downstream run?",
    # 01075 Soda Core YAML data quality (Danish)
    "Hvordan Soda Core improves pa ad-hoc SQL checks for data quality med YAML-first rules?",
    # 01076 Monte Carlo stale Snowflake 2026-03-02 (Catalan)
    "Quan va alertar Monte Carlo about a stale Snowflake pipeline three hours abans que nosaltres?",
    # 01077 OpenLineage + Marquez single graph (Hungarian)
    "Melyik graph now answers which model broke the downstream dashboard a Marquez-ben?",
    # 01078 DataHub replaced Marquez column lineage (Romanian)
    "De ce DataHub a luat locul Marquez as the cross-team catalogue with column-level lineage?",
    # 01079 Spark on Kubernetes Yunikorn fair share (Ukrainian transliterated)
    "Chomu Apache Spark batch jobs migrated to Kubernetes with Yunikorn dlya fair scheduling?",
    # 01080 Flink batch mode one codebase (Cebuano)
    "Unsa nga Flink batch mode nag-dagan sa nightly reconciliation pipelines sama sa streaming sa usa ka codebase?",
    # 01081 Trino federates Iceberg + Postgres (Malay)
    "Bagaimana Trino federates queries across Iceberg dan Postgres dengan push-down predicates ringan?",
    # 01082 Presto frozen, Trino governance split (Serbian transliterated)
    "Zasto Presto is frozen after the Trino governance split and old cluster je samo za citanje?",
    # 01083 Dremio semantic layer Iceberg reflections (Croatian)
    "Koji semantic layer na Iceberg uses reflections so BI tools keslo without shipping cubes?",
    # 01084 Noise row (Slovak)
    "Pockaj chvilu, kicking off the backfill right now a dam ti vediet.",
    # 01085 Iceberg hidden partitioning event_hour (Slovenian)
    "Kako Iceberg hidden partitioning on event_hour je odstranila the user-visible partition column za date filters?",
    # 01086 ZSTD over Snappy fact tables (Bulgarian transliterated)
    "Zashto ZSTD columnar compression beat Snappy on fact tables za size and scan time?",
    # 01087 Parquet 128MB row group dictionary encoding (Estonian)
    "Millised Parquet row-group sizing ja dictionary encoding settings cut shuffle read volume felgi-poole?",
    # 01088 ORC over Parquet Hive legacy bloom (Latvian)
    "Kapec ORC is preferred over Parquet legacy Hive warehouse with predicate push-down un bloom filters?",
    # 01089 DuckDB OLAP from SQLite (Lithuanian)
    "Kaip DuckDB stato virs SQLite embeddability bet taikinys is OLAP for local Parquet slices?",
    # 01090 Polars over Pandas lazy frames Arrow (Icelandic)
    "Af hverju Polars yfir Pandas became the default for data-science feature extraction hlaup?",
    # 01091 Arrow Flight SQL over ODBC BI (Maltese)
    "Liema Arrow Flight SQL protocol hadet post ODBC round-trips bejn BI layer and query engine?",
    # 01092 Iceberg REST catalog over Hive Metastore (Albanian)
    "Pse Iceberg REST catalog mori ne dore table discovery in vend te Hive Metastore?",
    # 01093 Partition by bucket user_id vs month (Welsh)
    "Pam newidiodd partitioning o calendar-month i bucket-by-user-id for top events table?",
    # 01094 Materialize incremental CDC views (Basque)
    "Zein Materialize incremental views CDC stream gainean eguneratzen dituzte dashboardak milisegundoetan?",
    # 01095 RisingWave over Materialize decoupled storage (Galician)
    "Por que RisingWave e preferido sobre Materialize para cost-sensitive streaming SQL cun almacenamento desacoplado?",
    # 01096 Kinesis hot partition 2026-02-18 backlog composite key (Afrikaans)
    "Hoekom het hot partitions in Kinesis veroorsaak 'n 45-minute backlog op 2026-02-18 deur user_id?",
    # 01097 Azure Synapse rejected for Databricks SQL Delta Iceberg (Irish Gaeilge)
    "Cen fath ar diultaiodh Azure Synapse in favour of Databricks SQL with open Delta and Iceberg?",
    # 01098 OpenLineage column-level lineage dbt 2026-03-25 (Esperanto)
    "Kiam OpenLineage column-level lineage shipped por dbt kaj downstream impact review sxangxis?",
    # 01099 Iceberg maintenance weekly expire snapshots compact (Persian transliterated)
    "Kodam Iceberg table maintenance kar-ha run weekly to expire snapshots and compact small files?",
    # 01100 Pub/Sub -> BigQuery subscription skip Dataflow (Spanish)
    "Por que Google Pub/Sub alimenta a BigQuery subscription directamente skipping the Dataflow hop?",
]


def main() -> None:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"

    sources: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < SHARED_OFFSET:
                continue
            if i >= SHARED_OFFSET + 100:
                break
            sources.append(json.loads(line))
    assert len(sources) == 100, f"expected 100 source rows, got {len(sources)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for k, (src, query) in enumerate(zip(sources, QUERIES)):
            row_id = f"ret-{ID_OFFSET + k + 1:05d}"
            row = {
                "id": row_id,
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(sources)} rows to {OUT}")


if __name__ == "__main__":
    main()
