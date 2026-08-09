import {
  Bookmark,
  CircleOff,
  Clock,
  FileText,
  Gauge,
  Plug,
  ShieldCheck,
  Tags,
  Zap,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { HelpTip, LayerChip, VerificationBadge } from "@/components/darkmem"
import {
  ModuleSurface,
  SurfaceStateChip,
} from "@/features/activity/components/module-surface"
import { DEMO } from "@/lib/demo-flag"
import { useDetailLevel } from "@/components/darkmem"
import { useDistribution, useSetDistributionPolicy } from "@/hooks/api"
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

  const { targets, policy } = data

  return (
    <div className="space-y-3">
      <div className="border-border flex flex-wrap items-center gap-3 rounded-md border p-3">
        <ShieldCheck aria-hidden className="text-muted-foreground h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">
            {policy.curbed ? "Push is curbed" : "Push is live"}
          </p>
          <p className="text-muted-foreground text-sm">
            One control, applied on the server: every target stops at once.
            Curbing clears each managed block to an empty marker pair rather
            than deleting it, so the human&apos;s own file is untouched.
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
              {level === "advanced" && (
                <span className="text-muted-foreground ml-auto font-mono text-sm">
                  mcp: {target.mcp_config} · refresh: {target.refresh}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      <div className="flex flex-col gap-2">
        <SectionHead icon={Gauge}>Inject content policy</SectionHead>
        <label className="flex flex-wrap items-center gap-2 text-sm">
          <span>Token budget</span>
          <input
            type="number"
            min={0}
            max={100000}
            defaultValue={policy.token_budget}
            aria-label="Token budget"
            className="border-border w-32 rounded-md border px-2 py-1 font-mono text-sm"
            onBlur={(event) => {
              const next = Number(event.currentTarget.value)
              if (Number.isFinite(next) && next !== policy.token_budget) {
                setPolicy.mutate({ ...policy, token_budget: next })
              }
            }}
          />
          <span className="text-muted-foreground">
            spent truth-first: facts, then articles, then memory summaries
          </span>
        </label>
      </div>
    </div>
  )
}

export function DistributionTab() {
  const d = useDemoDistribution()
  const connected = d.clients.filter((c) => c.status !== "disconnected").length
  const curbed = d.clients.filter((c) => c.status === "curbed").length
  const disconnected = d.clients.length - connected

  return (
    <div className="space-y-4">
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
      <ModuleSurface
        title="Distribution"
        state="staged"
        meta={`${connected} connected · ${curbed} curbed · ${disconnected} not connected`}
      >
        {/* Mounted only outside demo: a conditional *return* would still run
            the query hook, which is what put a QueryClient requirement on the
            demo path that never had one. */}
        {!DEMO && <LiveDistribution />}

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
      </ModuleSurface>
    </div>
  )
}
