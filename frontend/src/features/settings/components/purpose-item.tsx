import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import {
  ArrowDownUp,
  Bot,
  Braces,
  FileText,
  Filter,
  Pencil,
  ScrollText,
  ShieldCheck,
  Tag,
  type LucideIcon,
} from "lucide-react"
import { HelpTip, IconButton } from "@/components/darkmem"
import type { DemoLLMPurpose } from "@/features/settings/types"
import type { LlmLayout } from "@/features/settings/use-llm-layout"
import type { TierCLLMPurpose } from "../llm-tier-c-purposes"
import type { TierCPurposeView } from "../use-llm-tab-binding"

const PURPOSE_ICONS: Record<DemoLLMPurpose["purpose"], LucideIcon> = {
  embedding: Braces,
  extraction: Filter,
  classification: Tag,
  summarization: FileText,
  reranker: ArrowDownUp,
  reasoning: Bot,
  synthesis: FileText,
}

const TIER_C_PURPOSE_ICONS: Record<TierCLLMPurpose["purpose"], LucideIcon> = {
  verification: ShieldCheck,
}

function TierBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="border-inset bg-muted text-muted-foreground ml-auto rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap uppercase">
      {children}
    </span>
  )
}

/**
 * One writable purpose, read-only, in either layout. Editing lives in the
 * dialog `onEdit` opens.
 *
 * Grid and list are one component with a layout prop rather than two: they
 * show the same fields and offer the same action, differing only in
 * arrangement, so a split would be two places for them to drift.
 */
export function PurposeItem({
  purpose,
  layout,
  onEdit,
  onShowPrompt,
}: {
  purpose: DemoLLMPurpose
  layout: LlmLayout
  onEdit: () => void
  /** Omitted for the purposes that have no system prompt, which is what
   *  keeps them from showing a button that opens an empty editor. */
  onShowPrompt?: () => void
}) {
  const Icon = PURPOSE_ICONS[purpose.purpose]

  const identity = (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <Icon aria-hidden className="text-primary h-4 w-4 shrink-0" />
      <span className="font-mono text-sm font-semibold">{purpose.purpose}</span>
      <HelpTip label={`About the ${purpose.purpose} purpose`}>
        {purpose.role}
        {purpose.hint && ` — ${purpose.hint.text}`}
      </HelpTip>
      <TierBadge>{purpose.tier}</TierBadge>
    </div>
  )

  const summary = (
    <div
      className={cn(
        "text-muted-foreground min-w-0 font-mono text-xs",
        layout === "grid" ? "flex flex-col gap-0.5" : "flex flex-wrap gap-x-3",
      )}
    >
      <span className="truncate">{purpose.model || "no model set"}</span>
      <span className="truncate">
        via {purpose.provider_name || "no provider"}
      </span>
    </div>
  )

  const action = (
    <div className="flex flex-wrap items-center gap-2">
      {onShowPrompt && (
        <Button
          variant="ghost"
          aria-label={`System prompt for ${purpose.purpose}`}
          onClick={onShowPrompt}
        >
          <ScrollText aria-hidden className="mr-1 h-3.5 w-3.5" />
          System prompt
        </Button>
      )}
      <IconButton
        icon={Pencil}
        label={`Edit ${purpose.purpose}`}
        variant="outline"
        className="border-primary/60 text-primary"
        onClick={onEdit}
      />
    </div>
  )

  if (layout === "list") {
    return (
      <div className="border-inset bg-card flex flex-wrap items-center gap-3 rounded-lg border px-4 py-3">
        {identity}
        {summary}
        <div className="ml-auto">{action}</div>
      </div>
    )
  }

  return (
    <div className="border-inset bg-card flex flex-col gap-2.5 rounded-lg border p-4">
      {identity}
      {summary}
      {/* Right-aligned to match the list layout, which anchors the same
          action group with `ml-auto`. `justify-end` rather than
          `justify-between`: a purpose with no system prompt renders only the
          edit button, and `justify-between` would strand that lone child on
          the left — the opposite of the intent. */}
      <div className="flex items-center justify-end pt-1">{action}</div>
    </div>
  )
}

/**
 * The Tier-C purpose. No edit affordance at all, by owner ruling: its
 * connection is pinned to a measured qualification identity, and the supported
 * way to change the judge is to re-run the qualification harness against the
 * gold set — not a settings form.
 */
export function TierCPurposeItem({
  purpose,
  layout,
}: {
  purpose: TierCPurposeView
  layout: LlmLayout
}) {
  const Icon = TIER_C_PURPOSE_ICONS[purpose.purpose]
  const live = purpose.activatesWith === null

  const identity = (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <Icon aria-hidden className="text-muted-foreground h-4 w-4 shrink-0" />
      <span className="font-mono text-sm font-semibold">{purpose.purpose}</span>
      <HelpTip label={`About the ${purpose.purpose} purpose`}>
        {purpose.role}
      </HelpTip>
      <TierBadge>{live ? "tier c · live" : "tier c · inert"}</TierBadge>
    </div>
  )

  const summary = (
    <div
      className={cn(
        "text-muted-foreground min-w-0 font-mono text-xs",
        layout === "grid" ? "flex flex-col gap-0.5" : "flex flex-wrap gap-x-3",
      )}
    >
      <span className="truncate">{purpose.model}</span>
      <span className="truncate">via {purpose.provider_name}</span>
      <span>{purpose.api_kind}</span>
    </div>
  )

  const note = (
    <p className="text-muted-foreground text-sm">
      {live ? (
        <>
          Read-only by deliberate ruling, not an oversight. Its qualification
          record is a gate's evidence, pinned to this exact model identity, and
          the judge refuses to serve on a mismatched one. Changing the judge is
          supported — re-run the qualification harness against the gold set,
          which mints a record at the new identity — but it is a measurement,
          not a settings edit.
        </>
      ) : (
        <>
          Seeded row, resolvable, no consumer yet — activates with{" "}
          <span className="font-mono">{purpose.activatesWith}</span>. Rendered
          rather than omitted: a hidden inert purpose reads as "not configured".
        </>
      )}
    </p>
  )

  if (layout === "list") {
    return (
      <div className="border-inset bg-card/60 flex flex-col gap-2 rounded-lg border border-dashed px-4 py-3 opacity-90">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {identity}
          {summary}
        </div>
        {note}
      </div>
    )
  }

  return (
    <div className="border-inset bg-card/60 flex flex-col gap-2.5 rounded-lg border border-dashed p-4 opacity-90">
      {identity}
      {summary}
      {note}
    </div>
  )
}
