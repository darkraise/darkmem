import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { EmptyState } from "@/components/darkmem"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Badge } from "darkraise-ui/components/badge"
import { useSystemPrompts } from "@/hooks/api"

/**
 * The text an MCP client receives on connect.
 *
 * Reads `effective`, not `defaults`: `refresh_mcp_instructions` pushes
 * `prompt.get("agent_instructions")`, which resolves an override when one
 * exists, so showing the default would misreport what clients are actually
 * being told whenever anyone has edited it.
 */
export function McpPromptDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { data, isLoading, isError } = useSystemPrompts({ enabled: open })
  const prompt = data?.effective?.agent_instructions ?? ""
  const overridden = Boolean(
    data?.overrides && "agent_instructions" in data.overrides,
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-2xl flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Injected MCP instructions
            <Badge variant={overridden ? "default" : "outline"}>
              {overridden ? "overridden" : "default"}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Pushed onto the live server as the initialize response&apos;s
            instructions, so an edit reaches the next client without a restart.
          </DialogDescription>
        </DialogHeader>

        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the prompt"
            description="The /config/system-prompts request failed — this is an error, not an empty prompt."
          />
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        ) : prompt ? (
          <pre className="border-border bg-muted/12 min-h-0 flex-1 overflow-auto rounded-md border p-3 font-mono text-sm whitespace-pre-wrap">
            {prompt}
          </pre>
        ) : (
          <EmptyState
            kind="failed"
            title="No instructions are injected"
            description="agent_instructions resolves empty, so the server sends no instructions at all and connecting clients are told nothing about darkmem."
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
