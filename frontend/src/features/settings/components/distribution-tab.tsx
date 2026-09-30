import { Clock, Eye, FileText, Gauge, Plug, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { McpPromptDialog } from "./mcp-prompt-dialog"
import { McpConnectSnippets, mcpEndpoint } from "./mcp-connect-snippets"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { NumberField } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { DEMO } from "@/lib/demo-flag"
import { useDetailLevel } from "@/components/darkmem"
import { useDistribution, useEvents, useSetDistributionPolicy } from "@/hooks/api"
import { relativeTime } from "@/lib/format"

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

/** The token-budget input, controlled and re-seeded from the server's value.
 *
 *  Its own component so the state hook mounts only once the policy has been
 *  read — a conditional return in `LiveDistribution` still runs every hook
 *  above it, so a hook there would have to sit above the loading and error
 *  returns and hold a value that does not exist yet.
 *
 *  Uncontrolled with `defaultValue` was the bug: `<input type="number">`
 *  reports `""` for text it cannot parse, `Number("")` is 0 and 0 is finite,
 *  so blurring a typo wrote a budget of zero while the field went on showing
 *  the typo — the screen asserting something other than what is in force,
 *  which is the exact failure this route's 200-not-204 response exists to
 *  prevent.
 */
function TokenBudgetField({
  budget,
  onCommit,
}: {
  budget: number
  /** Resolves when the server has accepted the value, rejects when it has not.
   *
   *  A promise rather than a shared `isError` flag: the curb switch and this
   *  field write through the same mutation, so keying the reset on that flag
   *  meant a *failed curb* wiped an uncommitted budget edit — a control the
   *  human was not touching discarding their typing. This way each write
   *  learns its own outcome. */
  onCommit: (next: number) => Promise<unknown>
}) {
  const [draft, setDraft] = useState(budget)
  const [seed, setSeed] = useState(budget)
  if (seed !== budget) {
    // The server's value moved (a write landed, or a refetch): take it.
    setSeed(budget)
    setDraft(budget)
  }

  return (
    <NumberField
      value={draft}
      min={0}
      max={100000}
      aria-label="Token budget"
      className="w-32"
      // `valueAsNumber` is NaN for text the field cannot parse, which is the
      // distinction a raw number input lost: it reported "" for a typo, and
      // Number("") is 0 and 0 is finite, so blurring a typo wrote a budget of
      // zero while the field went on showing the typo.
      onValueChange={setDraft}
      onBlur={() => {
        if (!Number.isFinite(draft)) {
          setDraft(budget)
          return
        }
        if (draft !== budget) {
          // The field must not go on showing a number the server refused,
          // while the banner above says the value in force is shown below.
          onCommit(draft).catch(() => setDraft(budget))
        }
      }}
    />
  )
}

const RECENT_INJECT_LIMIT = 10

/** The inject log, inline (T4.08).
 *
 * Two server-filtered queries rather than one page filtered here: a client
 * that fetched every `system` event and kept the inject ones would under-report
 * the moment the page bound truncated, and this list is the record doc 15 §7
 * asks push to leave.
 *
 * A push and a curb are different facts, which is why they are different event
 * types; they are merged here for display only, newest first, and each keeps
 * its own sentence.
 */
function RecentInjects() {
  const pushes = useEvents(
    { event_type: "inject", limit: RECENT_INJECT_LIMIT },
    { enabled: !DEMO },
  )
  const curbs = useEvents(
    { event_type: "inject_curbed", limit: RECENT_INJECT_LIMIT },
    { enabled: !DEMO },
  )

  const rows = [...(pushes.data?.items ?? []), ...(curbs.data?.items ?? [])]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, RECENT_INJECT_LIMIT)

  return (
    <div className="flex flex-col gap-2">
      <SectionHead icon={Clock}>Inject log</SectionHead>
      {pushes.isError || curbs.isError ? (
        <p className="text-muted-foreground text-sm">
          The inject log could not be loaded.
        </p>
      ) : pushes.isLoading || curbs.isLoading ? (
        <p className="text-muted-foreground text-sm">loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No context has been pushed yet.
        </p>
      ) : (
        rows.map((row) => {
          const payload = row.payload as Record<string, unknown>
          const tool = typeof payload.tool === "string" ? payload.tool : "unknown target"
          const trigger =
            typeof payload.trigger === "string" ? payload.trigger : null
          const used =
            typeof payload.tokens_used === "number" ? payload.tokens_used : null
          const budget =
            typeof payload.budget_tokens === "number" ? payload.budget_tokens : null
          const items = (["fact_ids", "article_ids", "memory_ids"] as const).reduce(
            (n, key) => n + (Array.isArray(payload[key]) ? (payload[key] as unknown[]).length : 0),
            0,
          )
          return (
            <div
              key={row.id}
              className="border-inset flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border p-2.5 text-sm"
            >
              <b className="font-semibold">{tool}</b>
              <span className="text-muted-foreground">
                {row.event_type === "inject_curbed"
                  ? "push curbed — nothing was pushed"
                  : `${items} item${items === 1 ? "" : "s"}${
                      used !== null && budget !== null
                        ? ` · ${used.toLocaleString()} / ${budget.toLocaleString()} tokens`
                        : ""
                    }`}
              </span>
              {trigger && (
                <span className="text-info-text">re-injected: {trigger} changed</span>
              )}
              <span className="text-muted-foreground ml-auto font-mono text-sm">
                {relativeTime(row.created_at)}
              </span>
            </div>
          )
        })
      )}
    </div>
  )
}

/** The registry's targets, the policy, and the one curb. */
function LiveDistribution() {
  const level = useDetailLevel((s) => s.level)
  const { data, isLoading, isError } = useDistribution({ enabled: !DEMO })
  const setPolicy = useSetDistributionPolicy()

  if (isError) {
    return (
      <p className="text-muted-foreground text-sm">
        The distribution settings could not be loaded.
      </p>
    )
  }
  if (isLoading || !data) {
    return <p className="text-muted-foreground text-sm">loading…</p>
  }

  const { targets, policy, rejected } = data

  return (
    <div className="space-y-3">
      {setPolicy.isError && (
        // The switch snaps back to server truth on the next render, so without
        // this a human who believes they stopped push has no signal that they
        // did not — on the one control whose whole purpose is "you can always
        // stop it".
        <p className="border-destructive/55 text-destructive rounded-md border border-dashed px-2.5 py-1.5 text-sm">
          The change was not saved.
        </p>
      )}
      <div className="border-inset flex flex-wrap items-center gap-3 rounded-md border p-3">
        <ShieldCheck aria-hidden className="text-muted-foreground h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {policy.curbed ? "Push is curbed" : "Push is live"}
          </p>
          <p className="text-muted-foreground text-sm">
            Turning push off stops every target at once.
          </p>
        </div>
        <Switch
          aria-label="Allow push"
          checked={!policy.curbed}
          disabled={setPolicy.isPending}
          onCheckedChange={(on) =>
            setPolicy.mutate({ ...policy, curbed: !on })
          }
        />
      </div>

      <div className="border-inset flex flex-wrap items-center gap-3 rounded-md border p-3">
        <Eye aria-hidden className="text-muted-foreground h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {policy.watch_enabled ? "Watch is on" : "Watch is off"}
          </p>
          <p className="text-muted-foreground text-sm">
            Lets targets set to watch re-inject when the project or open file
            changes, instead of only at session start.
          </p>
        </div>
        <Switch
          aria-label="Watch mode"
          checked={policy.watch_enabled}
          disabled={setPolicy.isPending}
          onCheckedChange={(on) =>
            setPolicy.mutate({ ...policy, watch_enabled: on })
          }
        />
      </div>

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
              {/* The effective state, not the declared one, and at both
                  detail levels: whether a tool is being watched is what the
                  human curbs, not a technical aside. */}
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 font-mono text-xs uppercase tracking-wide",
                  target.watched
                    ? "border-info/55 text-info-text"
                    : "border-border text-muted-foreground",
                )}
              >
                {target.watched ? "watched" : "session start"}
              </span>
              {target.refresh === "watch" && !target.watched && (
                <span className="text-muted-foreground text-sm">
                  set to watch, but watch is off
                </span>
              )}
              {level === "advanced" && (
                <span className="text-muted-foreground ml-auto font-mono text-sm">
                  mcp: {target.mcp_config} · refresh: {target.refresh}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {rejected.length > 0 && (
        <div className="border-warning/55 bg-warning/10 flex flex-col gap-1 rounded-md border border-dashed px-3 py-2.5 text-sm">
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

      <RecentInjects />

      <div className="flex flex-col gap-2">
        <SectionHead icon={Gauge}>Inject content policy</SectionHead>
        <label className="flex flex-wrap items-center gap-2 text-sm">
          <span>Token budget</span>
          <TokenBudgetField
            budget={policy.token_budget}
            onCommit={(token_budget) =>
              setPolicy.mutateAsync({ ...policy, token_budget })
            }
          />
          <span className="text-muted-foreground">
            spent truth-first: facts, then articles, then memory summaries
          </span>
        </label>
      </div>
    </div>
  )
}

/** How to point an MCP client at this instance. The key field only fills the
 *  snippets in: it is never sent or stored, since the server cannot hand a
 *  secret back and this page must not become a second place one lives. */
function McpConnectCard() {
  const [apiKey, setApiKey] = useState("")
  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-border bg-muted/30 flex flex-row flex-nowrap items-center gap-2 space-y-0 border-b px-4 py-2.5">
        <Plug aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
        <h3 className="text-foreground min-w-0 truncate font-mono text-xs font-semibold tracking-[0.14em] uppercase">
          Connect an MCP client
        </h3>
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
          Create a key under <b className="text-foreground">Security → Keys for apps and agents</b>.
          If the client runs on another machine, add this host to{" "}
          <code className="font-mono">MCP_ALLOWED_HOSTS</code> (for example{" "}
          <code className="font-mono">{window.location.host}</code>).
        </p>
        <div className="flex max-w-md flex-col gap-1">
          <Label htmlFor="mcp-connect-key" className="text-muted-foreground text-sm">
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
      <div className="flex flex-wrap items-start justify-end gap-2">
        {/* The pull door is the one that works today, and its instructions are
            the only thing darkmem tells a connecting client about itself.
            They were readable nowhere on this surface. */}
        <Button
          variant="outline"
          onClick={() => setPromptOpen(true)}
        >
          <FileText aria-hidden className="size-[var(--icon-size)]" />
          View injected MCP prompt
        </Button>
      </div>
      {/* Mounted only while open, for the same reason the live panel below is
          mounted only outside demo: the dialog's query hook runs whenever it
          is in the tree, and an `enabled: false` query still needs a
          QueryClient above it. */}
      <McpConnectCard />
      {promptOpen && (
        <McpPromptDialog open onOpenChange={setPromptOpen} />
      )}
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
