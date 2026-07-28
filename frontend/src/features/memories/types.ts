import type { Memory, MemoryStatus } from "@/hooks/api"
import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"

// Relocated out of src/demo/types.ts by T1.68: `DemoMemory` is load-bearing
// for real-memory-detail-view.tsx via memory-editor-dialog.tsx's
// `memory?: DemoMemory | Memory` prop, not just the demo route. `relations`/
// `timeline` never carry real data yet (no real caller populates them), but
// they are DemoMemory's own fields, so they move with it rather than leaving
// a real module importing back from src/demo. See the task's report for the
// full per-type evidence trail.

export type MemoryRelationType =
  | "CONTRADICTS"
  | "ELABORATES"
  | "DEPENDS_ON"
  | "FOLLOWS"
  | "RELATES_TO"

export interface MemoryRelation {
  rel_type: MemoryRelationType
  memory_id: string
  excerpt: string
}

export type MemoryTimelineEventKind =
  | "created"
  | "extracted"
  | "verified"
  | "superseded"
  | "deprecated"
  | "updated"

export interface MemoryTimelineEvent {
  at: string
  kind: MemoryTimelineEventKind
  description: string
  note?: string
  /** Rung/lifecycle transition rendered as the from→to badge pair.
   *  `from: null` renders the plain "active (no badge)" label. */
  transition?: { from: string | null; to: string }
}

export interface DemoMemory extends Memory {
  project: string
  confidence: number
  status: MemoryStatus
  layer: KnowledgeLayer
  verification_status?: VerificationStatus | null
  /** The full honest badge claim, e.g. "supports a fact asserted by…". */
  verification_detail?: string
  /** Optional applies_when declaration, e.g. "env=prod". */
  applies_when?: string | null
  relations?: MemoryRelation[]
  timeline?: MemoryTimelineEvent[]
}
