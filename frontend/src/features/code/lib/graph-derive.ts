import type { CodeGraphData, CodeGraphEdge, CodeGraphNode } from "@/hooks/api"
import type {
  CodeNodeKind,
  DemoCodeCommunity,
  DemoCodeEdge,
  DemoCodeGraph,
  DemoCodeNode,
  DemoCodeProcess,
} from "@/features/code/types"

const CHART_CYCLE = 5

/**
 * GET /code/graph/{repo_id} returns community/process membership generically
 * (kind='community'/'process' nodes, member_of/entry_point_of/step_in_process
 * edges) rather than the demo's purpose-shaped DemoCodeCommunity/
 * DemoCodeProcess — see CLAUDE.md's "Retrieval"/Code Graph section and T1.59's
 * plan §3. These two functions are the client-side derivation that closes
 * that gap; nothing here is fabricated, every field traces to a real node or
 * edge in the response.
 */
export function deriveCommunities(
  nodes: CodeGraphNode[],
  _edges: CodeGraphEdge[],
): DemoCodeCommunity[] {
  const communityNodes = nodes.filter((n) => n.kind === "community")
  return communityNodes.map((n, i) => ({
    id: n.id,
    label: n.label,
    // Rendering choice, not a data claim — the backend carries no chart
    // field. Cycles 1..5 by first-encounter (array) order.
    chart: ((i % CHART_CYCLE) + 1) as DemoCodeCommunity["chart"],
  }))
}

function stepOf(edge: CodeGraphEdge): number {
  const raw = edge.properties?.["step"]
  return typeof raw === "number" ? raw : Number.POSITIVE_INFINITY
}

/**
 * Groups `step_in_process` edges by their target (the process key) and
 * orders each group by the edge's own `properties.step`, never by array/
 * insertion order — the backend's own ORDER BY pre-sorts today, but a
 * future change to that ordering must not silently corrupt process step
 * order client-side (T1.59 plan §5 falsification pass).
 */
export function deriveProcesses(
  nodes: CodeGraphNode[],
  edges: CodeGraphEdge[],
): DemoCodeProcess[] {
  const processNodes = nodes.filter((n) => n.kind === "process")
  const stepEdgesByProcess = new Map<string, CodeGraphEdge[]>()
  for (const edge of edges) {
    if (edge.type !== "step_in_process") continue
    const list = stepEdgesByProcess.get(edge.target)
    if (list) list.push(edge)
    else stepEdgesByProcess.set(edge.target, [edge])
  }
  return processNodes.map((n) => {
    const stepEdges = [...(stepEdgesByProcess.get(n.id) ?? [])].sort(
      (a, b) => stepOf(a) - stepOf(b),
    )
    return {
      id: n.id,
      label: n.label,
      steps: stepEdges.map((e) => e.source),
    }
  })
}

/** member_of: source = member symbol key, target = community key. A symbol
 *  in a singleton community (CommunityDetector's own `len(members) >= 2`
 *  filter) carries no member_of edge at all, and must resolve to the ""
 *  sentinel rather than throw or silently vanish. */
function communityOfEachNode(edges: CodeGraphEdge[]): Map<string, string> {
  const map = new Map<string, string>()
  for (const edge of edges) {
    if (edge.type !== "member_of") continue
    map.set(edge.source, edge.target)
  }
  return map
}

const KNOWN_KINDS = new Set<CodeNodeKind>([
  "file",
  "module",
  "class",
  "method",
  "function",
  "struct",
  "interface",
  "trait",
  "enum",
  "namespace",
  "impl",
  "type",
  "property",
  "route",
  "tool",
])

function asCodeNodeKind(kind: string): CodeNodeKind {
  return KNOWN_KINDS.has(kind as CodeNodeKind) ? (kind as CodeNodeKind) : "file"
}

/**
 * Builds the full DemoCodeGraph-shaped value CodeGlowCanvas/CodeExplorer/
 * CodeFilters already know how to render, from the raw REST response.
 * Community/process pseudo-nodes are pulled out into their own derived
 * lists (matching the demo's own separate `communities`/`processes`
 * arrays) rather than left in `nodes`, so a colour-by-kind render never
 * has to special-case them.
 */
export function deriveCodeGraph(
  repoId: string,
  raw: CodeGraphData,
): DemoCodeGraph {
  const communities = deriveCommunities(raw.nodes, raw.edges)
  const processes = deriveProcesses(raw.nodes, raw.edges)
  const communityOf = communityOfEachNode(raw.edges)

  const codeNodes = raw.nodes.filter(
    (n) => n.kind !== "community" && n.kind !== "process",
  )
  const nodes: DemoCodeNode[] = codeNodes.map((n) => ({
    id: n.id,
    name: n.label,
    kind: asCodeNodeKind(n.kind ?? "file"),
    file: n.file_path ?? "",
    community: communityOf.get(n.id) ?? "",
  }))

  const nodeIds = new Set(nodes.map((n) => n.id))
  const edges: DemoCodeEdge[] = raw.edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e) => {
      // A file-level `depends_on` edge carries how many symbol edges it
      // folds; the canvas draws that as stroke width.
      const weight = e.properties?.["weight"]
      return typeof weight === "number"
        ? { source: e.source, target: e.target, type: e.type, weight }
        : { source: e.source, target: e.target, type: e.type }
    })

  return { repo_id: repoId, nodes, edges, communities, processes }
}

/** The file a graph key belongs to: a symbol key is `name::file[::owner]`
 *  (graph_keys.py), anything else is returned as it is. At the file level a
 *  process step is still a symbol key, and this is the node it lands on. */
export function fileOfGraphKey(key: string): string {
  const parts = key.split("::")
  return parts.length > 1 && parts[1] ? parts[1] : key
}
