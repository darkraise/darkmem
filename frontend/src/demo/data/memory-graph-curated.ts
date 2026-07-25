import type { DemoMemoryGraph } from "../types"

// The L1 candidate entity graph plus its Leiden-detected topics (S17).
// Topics are read-only labels — communities render as halos, never nodes.
export const CURATED_MEMORY_GRAPH: DemoMemoryGraph = {
  topics: [
    {
      id: "t-retrieval",
      label: "Retrieval & ranking",
      detected: "2026-07-18",
      chart: 1,
      project: "darkmem",
    },
    {
      id: "t-storage",
      label: "Storage & embeddings",
      detected: "2026-07-18",
      chart: 3,
      project: "darkmem",
    },
    {
      id: "t-pipeline",
      label: "Pipeline & extraction",
      detected: "2026-07-21",
      chart: 5,
      project: "darkmem",
    },
    {
      id: "t-checkout",
      label: "Checkout & payments",
      detected: "2026-07-22",
      chart: 2,
      project: "acme-storefront",
    },
  ],
  entities: [
    // darkmem · retrieval & ranking
    { id: "e-reranker", name: "reranker", entity_type: "tool", topic: "t-retrieval", project: "darkmem" },
    { id: "e-hybrid", name: "hybrid_search", entity_type: "concept", topic: "t-retrieval", project: "darkmem" },
    { id: "e-rrf", name: "rrf_fusion", entity_type: "algorithm", topic: "t-retrieval", project: "darkmem" },
    { id: "e-gamma", name: "confidence_rank_gamma", entity_type: "concept", topic: "t-retrieval", project: "darkmem" },
    // darkmem · storage & embeddings
    { id: "e-postgres", name: "postgres", entity_type: "database", topic: "t-storage", project: "darkmem" },
    { id: "e-pgvector", name: "pgvector", entity_type: "tool", topic: "t-storage", project: "darkmem" },
    { id: "e-entity-emb", name: "entity_embeddings", entity_type: "concept", topic: "t-storage", project: "darkmem" },
    { id: "e-fingerprint", name: "embedder_fingerprint", entity_type: "concept", topic: "t-storage", project: "darkmem" },
    // darkmem · pipeline & extraction
    { id: "e-extraction", name: "extraction_phase", entity_type: "concept", topic: "t-pipeline", project: "darkmem" },
    { id: "e-classification", name: "classification", entity_type: "concept", topic: "t-pipeline", project: "darkmem" },
    { id: "e-dedup", name: "dedup_threshold", entity_type: "concept", topic: "t-pipeline", project: "darkmem" },
    { id: "e-jobs", name: "JobRegistry", entity_type: "tool", topic: "t-pipeline", project: "darkmem" },
    // acme-storefront · checkout & payments
    { id: "e-checkout", name: "checkout_service", entity_type: "tool", topic: "t-checkout", project: "acme-storefront" },
    { id: "e-stripe", name: "stripe", entity_type: "tool", topic: "t-checkout", project: "acme-storefront" },
    { id: "e-orders-db", name: "orders_db", entity_type: "database", topic: "t-checkout", project: "acme-storefront" },
    { id: "e-idempotency", name: "idempotency_key", entity_type: "concept", topic: "t-checkout", project: "acme-storefront" },
  ],
  relations: [
    { source: "e-reranker", target: "e-hybrid", rel_type: "PART_OF" },
    { source: "e-hybrid", target: "e-rrf", rel_type: "USES" },
    { source: "e-rrf", target: "e-gamma", rel_type: "RELATED_TO" },
    { source: "e-hybrid", target: "e-gamma", rel_type: "CONFIGURED_BY" },
    { source: "e-postgres", target: "e-pgvector", rel_type: "USES" },
    { source: "e-pgvector", target: "e-fingerprint", rel_type: "RELATED_TO" },
    { source: "e-entity-emb", target: "e-fingerprint", rel_type: "PARTITIONED_BY" },
    { source: "e-postgres", target: "e-entity-emb", rel_type: "STORES" },
    { source: "e-extraction", target: "e-classification", rel_type: "RUNS_WITH" },
    { source: "e-extraction", target: "e-dedup", rel_type: "RELATED_TO" },
    { source: "e-classification", target: "e-jobs", rel_type: "RELATED_TO" },
    { source: "e-dedup", target: "e-jobs", rel_type: "SWEPT_BY" },
    // cross-topic bridges
    { source: "e-hybrid", target: "e-entity-emb", rel_type: "QUERIES" },
    { source: "e-extraction", target: "e-entity-emb", rel_type: "WRITES" },
    // acme-storefront
    { source: "e-checkout", target: "e-stripe", rel_type: "USES" },
    { source: "e-checkout", target: "e-orders-db", rel_type: "WRITES" },
    { source: "e-checkout", target: "e-idempotency", rel_type: "USES" },
  ],
}
