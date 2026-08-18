import {
  Bookmark,
  CircleOff,
  Clock,
  Eye,
  FileText,
  Gauge,
  Plug,
  ShieldCheck,
  Tags,
  Zap,
} from "lucide-react"
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { McpPromptDialog } from "./mcp-prompt-dialog"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import {
  HelpTip,
  LayerChip,
  NumberField,
  VerificationBadge,
} from "@/components/darkmem"
import {
  ModuleSurface,
  SurfaceStateChip,
} from "@/features/activity/components/module-surface"
import { DEMO } from "@/lib/demo-flag"
import { useDetailLevel } from "@/components/darkmem"
import { useDistribution, useEvents, useSetDistributionPolicy } from "@/hooks/api"
import { relativeTime } from "@/lib/format"
import { useDemoDistribution } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoDistClient } from "@/demo/types"

function SectionHead({
  icon: Icon,
  help,
  children,
}: {
  icon: typeof Plug
  help?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <h3 className="flex items-center gap-2 text-sm font-semibold">
      <Icon aria-hidden className="text-muted-foreground h-4 w-4" />
      {children}
      {help && <HelpTip label="About this section">{help}</HelpTip>}
    </h3>
  )
}

function ClientRow({ client }: { client: DemoDistClient }) {
  const setCurb = useDemoStore((s) => s.setDistributionCurb)
  const connected = client.status !== "disconnected"
  const curbed = client.status === "curbed"

  return (
    <div
      className={cn(
        "border-border bg-card flex flex-col gap-2 rounded-md border px-3.5 py-3",
        curbed && "border-warning/50 bg-warning/5",
        !connected && "border-dashed",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        {connected ? (
          <ShieldCheck aria-hidden className="text-muted-foreground h-4 w-4" />
        ) : (
          <CircleOff aria-hidden className="text-muted-foreground h-4 w-4" />
        )}
        <span className="text-sm font-semibold">{client.name}</span>
        <SurfaceStateChip
          state={connected ? "populated" : "empty"}
          label={connected ? "connected" : "not connected"}
        />
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {client.handshake ?? "no MCP config detected"}
        </span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono text-sm">
        <dt className="text-muted-foreground">context file</dt>
        <dd className="break-words">{client.context_file}</dd>
        <dt className="text-muted-foreground">mcp config</dt>
        <dd className="break-words">{client.mcp_config}</dd>
      </dl>
      {connected ? (
        <div className="text-muted-foreground flex flex-wrap items-center gap-2.5 text-sm">
          <span>
            push: <b className="text-foreground font-semibold">{client.push_note}</b>
          </span>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-muted-foreground font-mono text-sm">
              curb push
            </span>
            <Switch
              checked={!curbed}
              onCheckedChange={(on) => setCurb(client.id, !on)}
              aria-label={`${client.name} push`}
            />
          </div>
        </div>
      ) : (
        <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
          <Button size="sm" variant="outline" className="border-primary/60 text-primary w-fit font-mono">
            darkmem connect {client.id}
          </Button>
          {client.connect_hint && (
            <HelpTip label={`Why ${client.name} is not connected`}>
              {client.connect_hint}
            </HelpTip>
          )}
        </div>
      )}
      {curbed && client.curbed_note && (
        <div className="border-warning/55 bg-warning/10 flex items-center gap-2 rounded-md border border-dashed px-2.5 py-1.5 text-sm">
          <CircleOff aria-hidden className="text-warning h-3.5 w-3.5 shrink-0" />
          {client.curbed_note}
        </div>
      )}
    </div>
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
      <SectionHead icon={Clock}>
        Inject log — which inject happened where
      </SectionHead>
      {pushes.isError || curbs.isError ? (
        <p className="text-muted-foreground text-sm">
          the inject log could not be read — this says nothing about whether a
          push happened, only that the journal is unavailable
        </p>
      ) : pushes.isLoading || curbs.isLoading ? (
        <p className="text-muted-foreground text-sm">loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          no inject has happened. Nothing else writes this log, so an empty one
          means no context has been pushed from this instance — not that the
          record is missing.
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
              className="border-border flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border p-2.5 text-sm"
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
                <span className="text-info">re-injected: {trigger} changed</span>
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

/** The live half: the registry's targets, the policy, and the one curb.
 *
 *  Separate from the demo panel below rather than merged, matching the split
 *  the knowledge surfaces use: a demo fixture and a live read are two
 *  producers, and a component that branched per field would make "is this
 *  real" unanswerable from the screen.
 */
function LiveDistribution() {
  const level = useDetailLevel((s) => s.level)
  const { data, isLoading, isError } = useDistribution({ enabled: !DEMO })
  const setPolicy = useSetDistributionPolicy()

  if (isError) {
    return (
      <p className="text-muted-foreground text-sm">
        distribution config unavailable — the targets and the curb could not be
        read, so nothing here describes what push would do
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
          the change was not saved — push is still whatever the server last
          accepted, shown below
        </p>
      )}
      <div className="border-border flex flex-wrap items-center gap-3 rounded-md border p-3">
        <ShieldCheck aria-hidden className="text-muted-foreground h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {policy.curbed ? "Push is curbed" : "Push is live"}
          </p>
          <p className="text-muted-foreground text-sm">
            One control, stored on the server: every target stops at once. It
            is <b className="font-semibold">enforced server-side</b> — a watch
            refresh reads this flag fresh every time and refuses while it is
            on, so a curb set here stops the next swap rather than the next
            session. The client is the thing being curbed, which is why it is
            not the client that decides. The session-start path has no caller
            yet, so nothing pushes on that cadence to stop. When it lands it
            will clear each managed block to an empty marker pair rather than
            deleting it, leaving the human&apos;s own file untouched.
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

      <div className="border-border flex flex-wrap items-center gap-3 rounded-md border p-3">
        <Eye aria-hidden className="text-muted-foreground h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {policy.watch_enabled ? "Watch is on" : "Watch is off"}
          </p>
          <p className="text-muted-foreground text-sm">
            Off by default. On, a target may re-inject as the project, the open
            file or the declared context shifts, instead of at session start
            only — and every refresh journals what shifted, so the swap is
            visible below rather than silent. It{" "}
            <b className="font-semibold">permits</b> the cadence and does not
            impose it: a target watches only if its own adapter row asks for
            it. The curb above outranks this.
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
            no targets configured — add a row to the inject_adapters config
          </p>
        ) : (
          targets.map((target) => (
            <div
              key={target.tool}
              className="border-border flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border p-2.5 text-sm"
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
                  "rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide",
                  target.watched
                    ? "border-info/55 text-info"
                    : "border-border text-muted-foreground",
                )}
              >
                {target.watched ? "watched" : "session start"}
              </span>
              {target.refresh === "watch" && !target.watched && (
                <span className="text-muted-foreground text-sm">
                  this row asks for watch; the install has it off
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

/** What the fixture panel below claims, on an install that has no live source
 *  for any of it (doc 13 §6.5's stated empty state).
 *
 *  Connect status, the inject log and the watermark were rendered from
 *  `CURATED_DISTRIBUTION` on every install, not only in demo — four clients
 *  reporting "handshake ok", an inject log of deliveries that never happened,
 *  and watermark rows for a writer that does not exist. They stayed on screen
 *  while the live read was *failing*. Doc 15 §7's whole stance is that push
 *  must be visible; a fabricated log is the inverse of visible, and doc 13
 *  §6.5 states the honest alternative outright: "empty is 'no clients
 *  connected'".
 */
function NoLiveDistributionSignal() {
  return (
    <div className="flex flex-col gap-2 pt-2">
      <SectionHead icon={Plug}>Connect status per client</SectionHead>
      <p className="text-muted-foreground text-sm">
        no clients connected — nothing has completed the handshake against this
        instance. Connect one with <code className="font-mono">darkmem
        connect &lt;tool&gt;</code>, which verifies over{" "}
        <code className="font-mono">/mcp</code> and writes the client&apos;s own
        config.
      </p>
      <SectionHead icon={Bookmark}>Render watermark</SectionHead>
      <p className="text-muted-foreground text-sm">
        no watermark — one <code className="font-mono">config</code> row per
        target is written by the first inject cycle, and none has run.
      </p>
    </div>
  )
}

export function DistributionTab() {
  const [promptOpen, setPromptOpen] = useState(false)
  const d = useDemoDistribution()
  const connected = d.clients.filter((c) => c.status !== "disconnected").length
  const curbed = d.clients.filter((c) => c.status === "curbed").length
  const disconnected = d.clients.length - connected
  // Counting the fixture clients on a live install would put a fabricated
  // tally in the surface header, which is the same claim the panel below was
  // making in longer form.
  const meta = DEMO
    ? `${connected} connected · ${curbed} curbed · ${disconnected} not connected`
    : "no clients connected · push not yet implemented"

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
          <span>
            Per-client connect status, the managed block, inject policy, the
            curb control, and the inject log — push shown staged, not implied
            shipped.
          </span>
        <HelpTip label="About the Distribution tab">
          Connect status per client, the per-target managed block written into
          each tool&apos;s native context file, the inject content policy and
          token budget, the curb control (the human sees and curbs push —
          never a silent context swap), the durable inject log, and the render
          watermark. The pull door (memory_search over /mcp) exists today;
          DistributionService, auto-inject, and the managed-block writer are
          target work — shown staged, not implied shipped.
        </HelpTip>
        </div>
        {/* The pull door is the one that works today, and its instructions are
            the only thing darkmem tells a connecting client about itself.
            They were readable nowhere on this surface. */}
        <Button
          variant="outline"
          size="sm"
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
      {promptOpen && (
        <McpPromptDialog open onOpenChange={setPromptOpen} />
      )}
      <ModuleSurface title="Distribution" state="staged" meta={meta}>
        {/* Mounted only outside demo: a conditional *return* would still run
            the query hook, which is what put a QueryClient requirement on the
            demo path that never had one. */}
        {!DEMO && <LiveDistribution />}
        {!DEMO && <NoLiveDistributionSignal />}

        {DEMO && (
        <>
        <div className="flex flex-col gap-2">
          <SectionHead icon={Plug}>Connect status per client</SectionHead>
          {d.clients.map((client) => (
            <ClientRow key={client.id} client={client} />
          ))}
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <SectionHead
            icon={FileText}
            help="Only the bytes between the two markers change on refresh (strip-before-rewrite); the human's own content above the block is never touched."
          >
            Per-target managed-block configuration — CLAUDE.md example
          </SectionHead>
          <pre className="border-border bg-muted/15 overflow-x-auto rounded-md border px-3 py-2.5 font-mono text-sm leading-relaxed">
            {d.block_preview}
          </pre>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <SectionHead icon={Gauge}>
            Inject content policy &amp; token budget
          </SectionHead>
          <div className="border-border flex flex-wrap items-center gap-2 rounded-md border border-dashed px-3 py-2.5 text-sm">
            <LayerChip layer={2} />
            <span className="text-muted-foreground">→</span>
            <LayerChip layer={3} />
            <span className="text-muted-foreground">→</span>
            <LayerChip layer={0} />
            <span className="text-muted-foreground">→</span>
            <span className="text-muted-foreground">
              fill truth-first until the budget is spent, then stop (top-K,
              stated in the block header — not silent degradation)
            </span>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            {d.policy.map((row) => (
              <div
                key={row.key}
                className="border-border bg-card flex flex-col gap-1 rounded-md border px-3 py-2.5"
              >
                <span className="flex items-center gap-1.5 font-mono text-sm font-semibold">
                  {row.key}
                  <HelpTip label={`About ${row.key}`}>{row.desc}</HelpTip>
                </span>
                <span className="text-primary font-mono text-sm">
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <SectionHead
            icon={Clock}
            help="inject_curbed is a taxonomy-first addition to the closed event_type vocabulary. Each row records that the server selected and returned N items for a target; it is not a receipt that the client's file was actually written — an honest limit of the pull-then-write model, stated rather than implied away."
          >
            Inject log — which inject happened where
          </SectionHead>
          {d.log.map((row) => (
            <div
              key={row.id}
              className={cn(
                "border-border bg-card flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2 text-sm",
                row.event_type === "inject_curbed" &&
                  "border-warning/50 bg-warning/5",
              )}
            >
              {row.event_type === "inject_curbed" ? (
                <CircleOff aria-hidden className="text-warning h-3.5 w-3.5" />
              ) : (
                <Zap aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
              )}
              <span className="font-mono font-semibold">{row.target}</span>
              <span className="text-muted-foreground min-w-40 flex-1">
                event_type{" "}
                <b className="text-foreground font-semibold">
                  {row.event_type}
                </b>{" "}
                · {row.detail}
              </span>
              <span className="text-muted-foreground font-mono text-sm">
                {row.time_label}
              </span>
              <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
                {row.meta}
              </span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <SectionHead
            icon={Tags}
            help="Neither item is relabelled on the way into the tool: a corroborated fact keeps its full badge claim, and a superseded memory keeps its amber lifecycle label rather than being silently promoted to active or dropped."
          >
            Labels survive injection — expanding the 14:12 UTC claude-code
            delivery
          </SectionHead>
          <div className="border-border bg-muted/10 flex flex-col gap-2 rounded-md border p-3">
            {d.inject_items.map((item) => (
              <div
                key={item.text}
                className="border-border bg-card flex flex-col gap-1.5 rounded-md border px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <LayerChip layer={item.layer} />
                  <VerificationBadge status={item.badge} />
                  <span className="text-muted-foreground ml-auto font-mono text-[10px] tracking-wide uppercase">
                    injected as:{" "}
                    <b className="text-foreground">{item.as_label}</b>
                  </span>
                </div>
                <span className="text-sm">{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <SectionHead
            icon={Bookmark}
            help="One config row per target — no per-client heavy table, no queue, no broker. Used only for idempotent diffing on the next inject cycle; it is the server's best knowledge of the last delivered set, not a proof the file was rewritten."
          >
            Render watermark — a config row, not a table
          </SectionHead>
          <dl className="border-border grid grid-cols-1 gap-x-3.5 gap-y-1 rounded-md border border-dashed px-3 py-2.5 font-mono text-sm sm:grid-cols-[auto_1fr]">
            {d.watermarks.map((w) => (
              <div key={w.key} className="contents">
                <dt className="text-muted-foreground">{w.key}</dt>
                <dd className="break-words">{w.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        </>
        )}
      </ModuleSurface>
    </div>
  )
}
