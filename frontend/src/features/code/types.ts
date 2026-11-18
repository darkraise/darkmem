// Relocated out of src/demo/types.ts by T1.68: `graph-derive.ts` builds real
// values of every type below from GET /code/graph/{repo_id}'s actual response
// (deriveCodeGraph / deriveCommunities / deriveProcesses), and
// real-code-graph-view.tsx / real-code-inspector.tsx consume them directly —
// this is the canonical code-graph view-model, not demo fixture data. See the
// task's report for the full per-type evidence trail.

// The demo fixture only ever emits the original five (file/class/method/
// function/module). The real backend's GET /code/graph/{repo_id} response
// merges two vocabularies into this one field: file/symbol nodes carry the
// CodeSymbol.kind value (KIND_MAP in code_parser.py), aux code_graph_nodes
// rows carry their own top-level kind column — T1.59 widened this union to
// the full real union so neither vocabulary gets silently narrowed. See
// KIND_CHART in code-glow-canvas.tsx / code-explorer.tsx / code-filters.tsx,
// which must stay exhaustive over every value added here.
export type CodeNodeKind =
  | "file"
  | "module"
  | "class"
  | "method"
  | "function"
  | "struct"
  | "interface"
  | "trait"
  | "enum"
  | "namespace"
  | "impl"
  | "type"
  | "property"
  | "route"
  | "tool"

export interface DemoCodeNode {
  id: string
  name: string
  kind: CodeNodeKind
  file: string
  community: string
}

export interface DemoCodeEdge {
  /** Caller/container side — blast radius walks these in reverse. */
  source: string
  target: string
  type: string
  /** Symbol edges folded into a file-level edge; absent on symbol edges. */
  weight?: number
}

export interface DemoCodeCommunity {
  id: string
  label: string
  /** Index into the --chart-N ramp. */
  chart: 1 | 2 | 3 | 4 | 5
}

export interface DemoCodeProcess {
  id: string
  label: string
  /** Ordered node ids. */
  steps: string[]
}

export interface DemoCodeGraph {
  repo_id: string
  nodes: DemoCodeNode[]
  edges: DemoCodeEdge[]
  communities: DemoCodeCommunity[]
  processes: DemoCodeProcess[]
}
