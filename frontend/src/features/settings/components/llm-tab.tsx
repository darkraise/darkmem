import { useState } from "react"
import { Alert, AlertDescription } from "darkraise-ui/components/alert"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"
import { EmptyState, IconSegmented } from "@/components/darkmem"
import type { DemoLLMPurpose } from "@/features/settings/types"
import {
  LLM_LAYOUT_OPTIONS,
  usePurposesLayout,
} from "@/features/settings/use-llm-layout"
import { promptKeyForPurpose } from "@/features/settings/llm-purpose-prompts"
import { useLLMTabBinding } from "../use-llm-tab-binding"
import { ProvidersPanel } from "./providers-panel"
import { PurposeDialog } from "./purpose-dialog"
import { PurposeItem, TierCPurposeItem } from "./purpose-item"
import { SystemPromptDialog } from "./system-prompt-dialog"

function PurposesPanel() {
  const binding = useLLMTabBinding()
  const layout = usePurposesLayout((s) => s.layout)
  const setLayout = usePurposesLayout((s) => s.setLayout)
  const [editing, setEditing] = useState<DemoLLMPurpose | null>(null)
  const [promptFor, setPromptFor] = useState<DemoLLMPurpose | null>(null)

  return (
    <div className="space-y-4">
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
      ) : binding.error ? (
        <EmptyState
          kind="failed"
          title="LLM configuration could not be loaded"
          description={binding.error.message}
          action={<Button onClick={binding.retry}>Retry</Button>}
        />
      ) : (
        <div
          className={cn(
            layout === "grid"
              ? "grid gap-3.5 sm:grid-cols-2"
              : "flex flex-col gap-2.5",
          )}
        >
          {binding.purposes.map((purpose) => {
            const item = (
              <PurposeItem
                key={purpose.purpose}
                purpose={purpose}
                layout={layout}
                onEdit={() => setEditing(purpose)}
                onShowPrompt={
                  promptKeyForPurpose(purpose.purpose)
                    ? () => setPromptFor(purpose)
                    : undefined
                }
              />
            )
            if (
              purpose.purpose !== "classification" ||
              !binding.classifierUnavailable
            ) {
              return item
            }
            return (
              <div key={purpose.purpose} className="flex flex-col gap-2">
                {item}
                <Alert variant="warning">
                  <AlertDescription>
                    Local classifier unavailable, using the LLM classifier
                  </AlertDescription>
                </Alert>
              </div>
            )
          })}
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

      {promptFor && (
        <SystemPromptDialog
          key={promptFor.purpose}
          open
          onOpenChange={(next) => {
            if (!next) setPromptFor(null)
          }}
          promptKey={promptKeyForPurpose(promptFor.purpose)!}
          title={`${promptFor.purpose} system prompt`}
          description={`Sent as the system message on every ${promptFor.purpose} call. An edit takes effect on the next call.`}
        />
      )}
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
