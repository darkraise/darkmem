import { SystemPromptDialog } from "./system-prompt-dialog"

/**
 * The text an MCP client receives on connect.
 *
 * Editing it is the same mechanism as editing any other system prompt, so it
 * is the same dialog: `refresh_mcp_instructions` re-pushes the saved value
 * onto the live server, which is why an edit here reaches the next client
 * without a restart.
 */
export function McpPromptDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <SystemPromptDialog
      open={open}
      onOpenChange={onOpenChange}
      promptKey="agent_instructions"
      title="Injected MCP instructions"
      description="Sent to MCP clients when they connect. An edit reaches the next client without a restart."
      emptyTitle="No instructions are injected"
      emptyDescription="Connecting clients receive no instructions."
    />
  )
}
