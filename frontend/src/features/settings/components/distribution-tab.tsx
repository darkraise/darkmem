import { FileText, Plug } from "lucide-react"
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { ApiKeysCard } from "./api-keys-card"
import { McpPromptDialog } from "./mcp-prompt-dialog"
import { McpConnectSnippets, mcpEndpoint } from "./mcp-connect-snippets"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { DEMO } from "@/lib/demo-flag"
import { EmptyState, useDetailLevel } from "@/components/darkmem"
import { useDistribution } from "@/hooks/api"

function SectionHead({
  icon: Icon,
  children,
}: {
  icon: typeof Plug
  children: React.ReactNode
}) {
  return (
    <h3 className="flex items-center gap-2 text-sm font-semibold">
      <Icon aria-hidden className="text-muted-foreground h-4 w-4" />
      {children}
    </h3>
  )
}

/** The registry's targets and the configured rows it refused. */
function LiveDistribution() {
  const level = useDetailLevel((s) => s.level)
  const { data, isLoading, isError, error, refetch } = useDistribution({
    enabled: !DEMO,
  })

  if (isError && !data) {
    return (
      <EmptyState
        kind="failed"
        title="The distribution settings could not be loaded"
        description={error.message}
        action={<Button onClick={() => void refetch()}>Retry</Button>}
      />
    )
  }
  if (isLoading || !data) {
    return <p className="text-muted-foreground text-sm">loading…</p>
  }

  const { targets, rejected } = data

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2">
        <SectionHead icon={FileText}>Managed block per target</SectionHead>
        {targets.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No targets configured.
          </p>
        ) : (
          targets.map((target) => (
            <div
              key={target.tool}
              className="border-inset flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border p-2.5 text-sm"
            >
              <b className="font-semibold">{target.tool}</b>
              <code className="text-muted-foreground font-mono">
                {target.context_file}
              </code>
              {level === "advanced" && (
                <span className="text-muted-foreground ml-auto font-mono text-sm">
                  mcp: {target.mcp_config}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {rejected.length > 0 && (
        <div className="border-warning-edge/55 bg-warning-solid/10 flex flex-col gap-1 rounded-md border border-dashed px-3 py-2.5 text-sm">
          <b className="font-semibold">
            {rejected.length} configured{" "}
            {rejected.length === 1 ? "entry" : "entries"} did not take effect
          </b>
          {rejected.map((row) => (
            <span key={row.tool} className="text-muted-foreground">
              <code className="font-mono">{row.tool}</code>: {row.reason}
            </span>
          ))}
        </div>
      )}

    </div>
  )
}

/** How to point an MCP client at this instance. The key field only fills the
 *  snippets in: it is never sent or stored, since the server cannot hand a
 *  secret back and this page must not become a second place one lives. */
function McpConnectCard({ onViewPrompt }: { onViewPrompt: () => void }) {
  const [apiKey, setApiKey] = useState("")
  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 border-b px-4 py-2.5">
        <Plug aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 truncate font-mono text-xs font-semibold tracking-[0.14em] uppercase">
          Connect an MCP client
        </h3>
        <span className="flex-1" />
        {/* The pull door is the one that works today, and its instructions
            are the only thing darkmem tells a connecting client about itself.
            It sits in this card's header (the slot New key takes on the keys
            card) rather than floating alone above every card. */}
        <Button
          size="sm"
          variant="outline"
          className="shrink-0"
          onClick={onViewPrompt}
        >
          <FileText aria-hidden className="size-[var(--icon-size)]" />
          <span className="hidden sm:inline">View injected MCP prompt</span>
          <span className="sm:hidden">MCP prompt</span>
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 p-4">
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Endpoint</dt>
          <dd className="font-mono break-all">{mcpEndpoint()}</dd>
          <dt className="text-muted-foreground">Transport</dt>
          <dd>Streamable HTTP</dd>
          <dt className="text-muted-foreground">Auth</dt>
          <dd>
            <code className="font-mono">Authorization: Bearer dmk_…</code>
          </dd>
        </dl>
        <p className="text-muted-foreground text-sm">
          Create a key under{" "}
          <b className="text-foreground">Keys for apps and agents</b> above. If
          the client runs on another machine, add this host to{" "}
          <code className="font-mono">MCP_ALLOWED_HOSTS</code> (for example{" "}
          <code className="font-mono">{window.location.host}</code>).
        </p>
        <div className="flex max-w-md flex-col gap-1">
          <Label
            htmlFor="mcp-connect-key"
            className="text-muted-foreground text-sm"
          >
            API key (optional, fills in the snippets below)
          </Label>
          <Input
            id="mcp-connect-key"
            type="password"
            autoComplete="off"
            placeholder="dmk_…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>
        <McpConnectSnippets apiKey={apiKey} />
      </CardContent>
    </Card>
  )
}

export function DistributionTab() {
  const [promptOpen, setPromptOpen] = useState(false)

  return (
    <div className="space-y-4">
      {/* Mounted only while open, for the same reason the live panel below is
          mounted only outside demo: the dialog's query hook runs whenever it
          is in the tree, and an `enabled: false` query still needs a
          QueryClient above it. */}
      <ApiKeysCard />
      <McpConnectCard onViewPrompt={() => setPromptOpen(true)} />
      {promptOpen && <McpPromptDialog open onOpenChange={setPromptOpen} />}
      {/* Mounted only outside demo: a conditional *return* would still run
          the query hook, which is what put a QueryClient requirement on the
          demo path that never had one. */}
      {!DEMO && (
        <ModuleSurface title="Distribution" state="populated">
          <LiveDistribution />
        </ModuleSurface>
      )}
    </div>
  )
}
