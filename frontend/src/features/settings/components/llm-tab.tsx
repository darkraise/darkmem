import { useState } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"
import { Trash2 } from "lucide-react"
import { HelpTip, IconSegmented } from "@/components/darkmem"
import type { DemoLLMPurpose } from "@/features/settings/types"
import {
  LLM_LAYOUT_OPTIONS,
  usePurposesLayout,
} from "@/features/settings/use-llm-layout"
import { useLLMTabBinding } from "../use-llm-tab-binding"
import { ProvidersPanel } from "./providers-panel"
import { PurposeDialog } from "./purpose-dialog"
import { PurposeItem, TierCPurposeItem } from "./purpose-item"

/**
 * The panels the flattening removed. `llm-providers` left this list when the
 * Providers sub-tab came back as a different mechanism — a shared connection
 * row rather than the deleted `provider_ref`/`profile_ref` columns. The other
 * two are genuinely gone and are not coming back, so the block still records a
 * real decision.
 */
function RemovedChrome() {
  return (
    <div className="border-border bg-muted/12 flex flex-col gap-2 rounded-lg border border-dashed p-4">
      <div className="text-muted-foreground flex items-center gap-2 font-mono text-[10px] tracking-wide uppercase">
        <Trash2 aria-hidden className="h-3.5 w-3.5" />
        removed with the flattening — not rendered, not disabled, deleted
        <HelpTip label="Why the profile tabs were removed">
          darkmem is not an LLM proxy. A profile picker over a schema with no
          profiles table would be scaffolding rendered as a feature — the
          honest move is deletion, not a greyed-out control. The Providers
          sub-tab is a different mechanism: one shared connection row several
          purposes reference, not the dropped profile indirection.
        </HelpTip>
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {["llm-profiles tab", "ml-profiles tab"].map((label) => (
          <span
            key={label}
            className="text-muted-foreground/70 font-mono text-xs line-through"
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

function PurposesPanel() {
  const binding = useLLMTabBinding()
  const layout = usePurposesLayout((s) => s.layout)
  const setLayout = usePurposesLayout((s) => s.setLayout)
  const [editing, setEditing] = useState<DemoLLMPurpose | null>(null)

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Seven purposes — each picking a provider from the Providers sub-tab
          plus the model and params that vary per purpose, including the
          seeded-inert `synthesis` purpose — plus `verification`, read-only
          here (it judges the verification ladder and its qualification is a
          gate&apos;s evidence). A save live-reloads the orchestrator; no
          redeploy, no LLM_* env vars.
        </span>
        <HelpTip label="About the LLM tab">
          Each purpose is one row naming a shared provider row, so a credential
          rotation on the Providers sub-tab reaches every purpose that uses it
          with nothing to re-apply here. Every vendor auth, reasoning-control
          and structured-output quirk that api_kind selects is resolved by the
          backend orchestrator, never re-implemented here.
        </HelpTip>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <IconSegmented
          value={layout}
          options={LLM_LAYOUT_OPTIONS}
          onChange={setLayout}
          label="Purposes layout"
        />
      </div>

      {/* The dialog seeds its draft from the row on open, so waiting for the
          first load is what makes that seed real; `isLoading` is false on
          every later refetch, so this does not flash between saves. */}
      {binding.isLoading ? (
        <div className="grid gap-3.5 sm:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-md" />
          ))}
        </div>
      ) : (
        <div
          className={cn(
            layout === "grid"
              ? "grid gap-3.5 sm:grid-cols-2"
              : "flex flex-col gap-2.5",
          )}
        >
          {binding.purposes.map((purpose) => (
            <PurposeItem
              key={purpose.purpose}
              purpose={purpose}
              layout={layout}
              onEdit={() => setEditing(purpose)}
            />
          ))}
          {binding.tierCPurposes.map((purpose) => (
            <TierCPurposeItem
              key={purpose.purpose}
              purpose={purpose}
              layout={layout}
            />
          ))}
        </div>
      )}

      {editing && (
        <PurposeDialog
          key={editing.purpose}
          purpose={editing}
          binding={binding}
          open
          onOpenChange={(next) => {
            if (!next) setEditing(null)
          }}
        />
      )}

      <RemovedChrome />
    </div>
  )
}

export function LLMTab() {
  return (
    <Tabs defaultValue="purposes">
      <TabsList>
        <TabsTrigger value="providers">Providers</TabsTrigger>
        <TabsTrigger value="purposes">Purposes</TabsTrigger>
      </TabsList>
      <TabsContent value="providers" className="pt-4">
        <ProvidersPanel />
      </TabsContent>
      <TabsContent value="purposes" className="pt-4">
        <PurposesPanel />
      </TabsContent>
    </Tabs>
  )
}
