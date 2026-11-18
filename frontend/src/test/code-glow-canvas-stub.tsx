import {
  drawnGraph,
  type CodeGlowCanvasProps,
} from "@/features/code/components/code-glow-canvas"

export function CodeGlowCanvasStub({ graph, hiddenKinds, onSelect }: CodeGlowCanvasProps) {
  const { nodes, edges } = drawnGraph(graph, hiddenKinds)
  return (
    <div
      role="group"
      aria-label={`Code graph — ${nodes.length} nodes, ${edges.length} edges`}
    >
      {nodes.map((n) => (
        <button
          key={n.id}
          type="button"
          aria-label={`${n.name} (${n.kind})`}
          onClick={() => onSelect(n.id)}
        />
      ))}
    </div>
  )
}
