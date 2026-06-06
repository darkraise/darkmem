// Derive ordered execution-flow processes from the code-graph payload returned
// by GET /code/graph/{repo}. A process is a node with kind === "process";
// ProcessTracer links its entry symbol via an `entry_point_of` edge and its
// ordered steps via `step_in_process` edges that carry the step index in
// `properties.step` (jsonb_build_object('step', d.step::int)). The same input
// shape the page consumes (CodeGraphNode / CodeGraphEdge) is accepted here, with
// an optional `properties` bag so the step index flows through if the API
// forwards it.

interface GraphNodeInput {
  id: string
  label: string
  kind?: string
  file_path?: string
}

interface GraphEdgeInput {
  source: string
  target: string
  type: string
  properties?: Record<string, unknown> | null
}

export interface ProcessStep {
  index: number
  nodeId: string
  label: string
  kind: string
  file?: string
}

export interface CodeProcess {
  id: string
  label: string
  entryNodeId?: string
  entryKind?: string
  entryFile?: string
  steps: ProcessStep[]
  nodeIds: string[]
  stepCount: number
}

function stepIndexOf(edge: GraphEdgeInput): number | undefined {
  const props = edge.properties
  if (!props) return undefined
  for (const field of ["step", "index", "order"] as const) {
    const raw = props[field]
    if (raw == null) continue
    const n = typeof raw === "number" ? raw : Number(raw)
    if (Number.isFinite(n)) return n
  }
  return undefined
}

export function deriveProcesses(
  nodes: GraphNodeInput[],
  edges: GraphEdgeInput[],
): CodeProcess[] {
  const nodeById = new Map<string, GraphNodeInput>()
  for (const n of nodes) nodeById.set(n.id, n)

  // Pre-bucket edges once by target so each process node reads its own edges in
  // O(1) instead of re-scanning every edge per process (was O(P·E)). The `seq`
  // captured here is the original edge order, keeping the step-sort tie-break
  // deterministic.
  const entryEdgesByTarget = new Map<string, GraphEdgeInput>()
  const stepEdgesByTarget = new Map<
    string,
    { e: GraphEdgeInput; seq: number }[]
  >()
  edges.forEach((e, seq) => {
    if (e.type === "entry_point_of") {
      if (!entryEdgesByTarget.has(e.target)) entryEdgesByTarget.set(e.target, e)
    } else if (e.type === "step_in_process") {
      const bucket = stepEdgesByTarget.get(e.target)
      if (bucket) bucket.push({ e, seq })
      else stepEdgesByTarget.set(e.target, [{ e, seq }])
    }
  })

  const processes: CodeProcess[] = []

  for (const proc of nodes) {
    if (proc.kind !== "process") continue

    const entryEdge = entryEdgesByTarget.get(proc.id)
    const entryNode = entryEdge ? nodeById.get(entryEdge.source) : undefined

    // Pair each step edge with its insertion order so explicit indices win but
    // ties (or missing indices) fall back to encounter order deterministically.
    const stepEdges = (stepEdgesByTarget.get(proc.id) ?? [])
      .slice()
      .sort((a, b) => {
        const ai = stepIndexOf(a.e)
        const bi = stepIndexOf(b.e)
        if (ai != null && bi != null) return ai - bi || a.seq - b.seq
        if (ai != null) return -1
        if (bi != null) return 1
        return a.seq - b.seq
      })

    const steps: ProcessStep[] = stepEdges.map(({ e }, i) => {
      const node = nodeById.get(e.source)
      const explicit = stepIndexOf(e)
      return {
        index: explicit ?? i + 1,
        nodeId: e.source,
        label: node?.label ?? e.source,
        kind: node?.kind ?? "unknown",
        file: node?.file_path,
      }
    })

    const nodeIds: string[] = []
    const seen = new Set<string>()
    const push = (id: string | undefined) => {
      if (!id || seen.has(id)) return
      seen.add(id)
      nodeIds.push(id)
    }
    push(entryNode?.id)
    for (const s of steps) push(s.nodeId)
    push(proc.id) // emphasize the process node itself (root of the flow)

    const label =
      entryNode?.label || proc.label || proc.id

    processes.push({
      id: proc.id,
      label,
      entryNodeId: entryNode?.id,
      entryKind: entryNode?.kind,
      entryFile: entryNode?.file_path,
      steps,
      nodeIds,
      stepCount: steps.length,
    })
  }

  processes.sort((a, b) => b.stepCount - a.stepCount)
  return processes
}

// Mermaid escapes HTML entities in node text; quotes and brackets would
// otherwise break the `["..."]` node syntax. See mermaid flowchart text rules.
function escapeMermaid(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\[/g, "#91;")
    .replace(/\]/g, "#93;")
    .replace(/\{/g, "#123;")
    .replace(/\}/g, "#125;")
    .replace(/[\r\n]+/g, " ")
}

export function processToMermaid(p: CodeProcess): string {
  const lines = ["flowchart TD"]

  if (p.steps.length === 0) {
    lines.push(`  n0[${`"${escapeMermaid(p.label)}"`}]`)
    return lines.join("\n")
  }

  p.steps.forEach((step, i) => {
    const text = `"${escapeMermaid(`${step.label} (${step.kind})`)}"`
    const isEntry = step.nodeId === p.entryNodeId
    // Entry gets a stadium shape ([...]); plain steps get rectangles.
    lines.push(isEntry ? `  n${i}([${text}])` : `  n${i}[${text}]`)
  })

  for (let i = 0; i < p.steps.length - 1; i++) {
    lines.push(`  n${i} --> n${i + 1}`)
  }

  return lines.join("\n")
}
