import type { Decorator, Meta, StoryObj } from "@storybook/react"
import { useEffect, useMemo, useState } from "react"
import { CodeGlowCanvas } from "./code-glow-canvas"
import type {
  CodeNodeKind,
  DemoCodeEdge,
  DemoCodeGraph,
  DemoCodeNode,
} from "@/features/code/types"

const WEBGL_CONTEXTS = new Set(["webgl", "webgl2", "experimental-webgl"])

/** Makes every WebGL context request fail while mounted, as on a browser with
 *  WebGL turned off. Patched during render: the canvas builds in its own
 *  effect, before a decorator's effect would run. */
const withoutWebGL: Decorator = (Story) => {
  const [original] = useState(() => {
    const getContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...rest: unknown[]
    ) {
      if (WEBGL_CONTEXTS.has(type)) return null
      return (getContext as (...a: unknown[]) => unknown).call(this, type, ...rest)
    } as typeof getContext
    return getContext
  })
  useEffect(
    () => () => {
      HTMLCanvasElement.prototype.getContext = original
    },
    [original],
  )
  return <Story />
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const SYMBOL_KINDS: CodeNodeKind[] = ["function", "class", "method", "interface", "type"]

/**
 * Files each CONTAIN a handful of symbols. CALLS link the first 60% of files
 * into one core; the next 25% stay their own small satellites; the rest are
 * lone routes and tools with no edges, the halo.
 */
function syntheticCodeGraph(n: number, seed = 1): DemoCodeGraph {
  const rand = mulberry32(seed)
  const nodes: DemoCodeNode[] = []
  const edges: DemoCodeEdge[] = []
  const communities = [1, 2, 3, 4, 5].map((chart) => ({
    id: `c${chart}`,
    label: `community ${chart}`,
    chart: chart as 1 | 2 | 3 | 4 | 5,
  }))
  const haloCount = Math.floor(n * 0.15)
  const files: string[][] = []
  while (nodes.length < n - haloCount) {
    const f = files.length
    const community = `c${(f % 5) + 1}`
    const file = `src/module_${f}.py`
    const fileId = `f${f}`
    nodes.push({ id: fileId, name: `module_${f}.py`, kind: "file", file, community })
    const members = [fileId]
    const symbols = 2 + Math.floor(rand() * 5)
    for (let s = 0; s < symbols && nodes.length < n - haloCount; s++) {
      const id = `f${f}s${s}`
      nodes.push({
        id,
        name: `symbol_${f}_${s}`,
        kind: SYMBOL_KINDS[Math.floor(rand() * SYMBOL_KINDS.length)]!,
        file,
        community,
      })
      edges.push({ source: fileId, target: id, type: "CONTAINS" })
      members.push(id)
    }
    files.push(members)
  }
  const coreFiles = Math.max(1, Math.floor(files.length * 0.6))
  for (let f = 1; f < coreFiles; f++) {
    for (let k = 0; k < 2; k++) {
      const from = files[f]![1 + Math.floor(rand() * (files[f]!.length - 1))] ?? files[f]![0]!
      const to = files[Math.floor(rand() * f)]!
      edges.push({ source: from, target: to[Math.floor(rand() * to.length)]!, type: "CALLS" })
    }
  }
  for (let h = 0; h < haloCount; h++) {
    const kind: CodeNodeKind = h % 2 ? "route" : "tool"
    nodes.push({
      id: `h${h}`,
      name: `${kind}_${h}`,
      kind,
      file: `src/entry_${h}.py`,
      community: `c${(h % 5) + 1}`,
    })
  }
  return { repo_id: "story", nodes, edges, communities, processes: [] }
}

interface HarnessProps {
  n: number
  selected?: string | null
  blast?: string[]
  process?: string[]
  community?: string | null
  depthOf?: string
  hidden?: CodeNodeKind[]
  colorBy?: "community" | "kind"
}

function Harness({
  n,
  selected = null,
  blast,
  process,
  community = null,
  depthOf,
  hidden,
  colorBy = "community",
}: HarnessProps) {
  const graph = useMemo(() => syntheticCodeGraph(n), [n])
  const [selectedId, setSelectedId] = useState<string | null>(selected)
  const blastIds = useMemo(() => (blast ? new Set(blast) : null), [blast])
  const processIds = useMemo(() => (process ? new Set(process) : null), [process])
  const hiddenKinds = useMemo(() => (hidden ? new Set(hidden) : undefined), [hidden])
  const visibleIds = useMemo(() => {
    if (!depthOf) return null
    const keep = new Set([depthOf])
    for (const e of graph.edges) {
      if (e.source === depthOf) keep.add(e.target)
      if (e.target === depthOf) keep.add(e.source)
    }
    return keep
  }, [graph, depthOf])
  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <CodeGlowCanvas
        graph={graph}
        colorBy={colorBy}
        selectedId={selectedId}
        onSelect={setSelectedId}
        visibleIds={visibleIds}
        hiddenKinds={hiddenKinds}
        blastIds={blastIds}
        highlightCommunity={community}
        processIds={processIds}
        zoom={1}
      />
    </div>
  )
}

const meta: Meta<typeof Harness> = {
  title: "Graph/Constellation/Code",
  component: Harness,
  parameters: { layout: "fullscreen" },
}
export default meta

type S = StoryObj<typeof Harness>

export const Mixed: S = { args: { n: 150 } }
export const OneNode: S = { args: { n: 1 } }
export const Selected: S = { args: { n: 150, selected: "f0s0" } }
export const BlastRadius: S = {
  args: { n: 150, selected: "f0s0", blast: ["f0", "f1s0", "f2s1", "f3s0", "f4s0"] },
}
export const ActiveProcess: S = {
  args: { n: 150, process: ["f1", "f1s0", "f2s0", "f3s1", "f5s0"] },
}
export const HighlightedCommunity: S = { args: { n: 150, community: "c2" } }
export const DepthFilter: S = { args: { n: 150, selected: "f0", depthOf: "f0" } }
export const HiddenKinds: S = { args: { n: 150, hidden: ["file"], colorBy: "kind" } }
export const WebGLUnavailable: S = { args: { n: 150 }, decorators: [withoutWebGL] }
export const Worst2000: S = { args: { n: 2000 } }
