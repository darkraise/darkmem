import {
  Command,
  CommandInput,
  CommandList,
  CommandItem,
  CommandEmpty,
} from "darkraise-ui/components/command"
import { Dialog, DialogContent } from "darkraise-ui/components/dialog"

export interface CodeGraphSearchNode {
  id: string
  label: string
  kind: string
}

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
  const handlePick = (id: string) => {
    onPick(id)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0">
        <Command>
          <CommandInput autoFocus placeholder="Jump to a graph node…" />
          <CommandList>
            <CommandEmpty>No matching nodes.</CommandEmpty>
            {nodes.map((node) => (
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
        </Command>
      </DialogContent>
    </Dialog>
  )
}
