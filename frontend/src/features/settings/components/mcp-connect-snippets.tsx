import { useState } from "react"
import { Copy, Check } from "lucide-react"
import {
  Clipboard,
  ClipboardIndicator,
  ClipboardTrigger,
} from "darkraise-ui/components/clipboard"
import { Tabs, TabsContent, TabsTrigger } from "darkraise-ui/components/tabs"
import { ScrollTabsList } from "@/components/darkmem/scroll-tabs-list"

export const KEY_PLACEHOLDER = "<YOUR_API_KEY>"

// The trailing slash is load-bearing: the MCP app is mounted at /mcp, so
// `POST /mcp` is answered 405 by the router before it reaches the transport.
export function mcpEndpoint(origin = window.location.origin) {
  return `${origin}/mcp/`
}

function snippets(url: string, key: string) {
  const auth = `Bearer ${key}`
  return [
    {
      id: "claude-code",
      label: "Claude Code",
      hint: "Run in a terminal. Add --scope user to make it available in every project.",
      code: `claude mcp add --transport http darkmem ${url} \\\n  --header "Authorization: ${auth}"`,
    },
    {
      id: "json",
      label: "JSON config",
      hint: "For clients configured with an mcpServers file: .mcp.json, Cursor's mcp.json, VS Code, Windsurf.",
      code: JSON.stringify(
        {
          mcpServers: {
            darkmem: {
              type: "http",
              url,
              headers: { Authorization: auth },
            },
          },
        },
        null,
        2,
      ),
    },
    {
      id: "codex",
      label: "Codex",
      hint: "Add to ~/.codex/config.toml.",
      code: `[mcp_servers.darkmem]\nurl = "${url}"\nhttp_headers = { Authorization = "${auth}" }`,
    },
    {
      id: "curl",
      label: "Test with curl",
      hint: "A 200 carrying a tool list means the key and the endpoint both work; 401 means the key was refused.",
      code: `curl -sS ${url} \\\n  -H "Authorization: ${auth}" \\\n  -H "Content-Type: application/json" \\\n  -H "Accept: application/json, text/event-stream" \\\n  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`,
    },
  ]
}

// The copy button sits in its own column beside the scrolling code, not over
// it: positioned absolutely it covered the text whenever a long line scrolled
// under it, which on a phone is every line (padding only reserves room at
// the end of the scroll, not at the visible edge).
function CodeBlock({ code }: { code: string }) {
  return (
    <div
      className="border-inset bg-muted/15 flex items-start rounded-md border"
      data-testid="snippet"
    >
      <pre className="min-w-0 flex-1 overflow-x-auto px-3 py-2.5 font-mono text-sm leading-relaxed whitespace-pre">
        {code}
      </pre>
      <Clipboard value={code} toast className="shrink-0 p-1.5">
        <ClipboardTrigger aria-label="Copy snippet">
          <ClipboardIndicator
            copied={<Check className="size-4" />}
            fallback={<Copy className="size-4" />}
          />
        </ClipboardTrigger>
      </Clipboard>
    </div>
  )
}

/** Copyable client configs for the /mcp endpoint. Without `apiKey` they carry
 *  a placeholder the reader replaces; every call to /mcp needs a key, so there
 *  is no keyless variant to offer. */
export function McpConnectSnippets({ apiKey }: { apiKey?: string }) {
  const url = mcpEndpoint()
  const items = snippets(url, apiKey?.trim() || KEY_PLACEHOLDER)
  const [tab, setTab] = useState("claude-code")
  return (
    <Tabs value={tab} onValueChange={setTab} className="min-w-0">
      {/* Scrolls inside itself: a bare TabsList pushed "Test with curl" past
          a phone viewport and gave the whole tab a horizontal scroll. */}
      <ScrollTabsList activeValue={tab} className="justify-start">
        {items.map((s) => (
          <TabsTrigger key={s.id} value={s.id}>
            {s.label}
          </TabsTrigger>
        ))}
      </ScrollTabsList>
      {items.map((s) => (
        <TabsContent
          key={s.id}
          value={s.id}
          className="flex flex-col gap-2 pt-2"
        >
          <p className="text-muted-foreground text-sm">{s.hint}</p>
          <CodeBlock code={s.code} />
        </TabsContent>
      ))}
    </Tabs>
  )
}
