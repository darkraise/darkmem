import type {
  EntityRelation,
  GraphEntity,
  SimilarityEdge,
  UnifiedMemory,
} from "@/hooks/api/use-graph-api"
import small from "./real-corpus-200.json"
import mid from "./real-corpus-1000.json"
import all from "./real-corpus-all.json"

export type RealCorpusSize = 200 | 1000 | "all"

export interface RealCorpus {
  memories: UnifiedMemory[]
  edges: SimilarityEdge[]
  clusterNames: Record<string, string>
  entities: GraphEntity[]
  entityRelations: EntityRelation[]
}

interface RealCorpusFixture {
  memories: { id: string; cluster: number; memory_type: string | null; importance: number }[]
  edges: SimilarityEdge[]
  clusterNames: Record<string, string>
  entities?: { id: string; name: string; entity_type: string; memory_ids: string[] }[]
  entityRelations?: EntityRelation[]
}

const FIXTURES: Record<string, RealCorpusFixture> = {
  "200": small,
  "1000": mid,
  all: all,
}

export function loadRealCorpus(size: RealCorpusSize): RealCorpus {
  const fx = FIXTURES[String(size)]!
  return {
    memories: fx.memories.map((m, i) => ({
      id: m.id,
      content: `Memory ${i + 1}`,
      source: "fixture",
      tags: [],
      memory_type: m.memory_type,
      importance: m.importance,
      cluster: m.cluster,
      status: "active",
    })),
    edges: fx.edges,
    clusterNames: fx.clusterNames,
    entities: (fx.entities ?? []).map((e) => ({ ...e, properties: {} })),
    entityRelations: fx.entityRelations ?? [],
  }
}
