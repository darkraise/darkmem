import { useMemo, useState } from "react"
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandItem,
  CommandEmpty,
} from "darkraise-ui/components/command"

export interface CodeGraphSearchNode {
  id: string
  label: string
  kind: string
}

// A code graph can hold tens of thousands of nodes. Every CommandItem
// registers itself on mount and fires a Command-wide re-render, so mounting
// the whole node set at once janks or freezes the palette. Filter the list
// ourselves and only ever mount a bounded slice.
const MAX_VISIBLE = 50

export function CodeGraphSearch({
  open,
  onOpenChange,
  nodes,
  nodeColors,
  onPick,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  nodes: CodeGraphSearchNode[]
  nodeColors: Record<string, string>
  onPick: (id: string) => void
}) {
  const [query, setQuery] = useState("")

  const handlePick = (id: string) => {
    onPick(id)
    onOpenChange(false)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) setQuery("")
    onOpenChange(next)
  }

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const matches = q
      ? nodes.filter(
          (n) =>
            n.label.toLowerCase().includes(q) ||
            n.kind.toLowerCase().includes(q) ||
            n.id.toLowerCase().includes(q),
        )
      : nodes
    return matches.slice(0, MAX_VISIBLE)
  }, [nodes, query])

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title="Jump to graph node"
      description="Search code graph nodes by name, kind, or id and jump to one."
    >
      <CommandInput
        autoFocus
        placeholder="Jump to a graph node…"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>No matching nodes.</CommandEmpty>
        {visible.map((node) => (
          <CommandItem
            key={node.id}
            value={`${node.label} ${node.kind} ${node.id}`}
            onSelect={() => handlePick(node.id)}
          >
            <span
              aria-hidden="true"
              className="size-2 shrink-0 rounded-full"
              style={{
                backgroundColor:
                  nodeColors[node.kind] ?? "hsl(var(--muted-foreground))",
              }}
            />
            <span className="min-w-0 flex-1 truncate text-foreground">
              {node.label}
            </span>
            <span className="text-muted-foreground shrink-0 text-sm">
              {node.kind}
            </span>
          </CommandItem>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
