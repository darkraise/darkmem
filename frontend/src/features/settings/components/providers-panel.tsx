import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"
import { Plug, Plus } from "lucide-react"
import { EmptyState, IconSegmented } from "@/components/darkmem"
import {
  LLM_LAYOUT_OPTIONS,
  useProvidersLayout,
} from "@/features/settings/use-llm-layout"
import {
  useLlmProviders,
  type LlmProvider,
} from "@/hooks/api/use-llm-providers-api"
import { ProviderDialog } from "./provider-dialog"
import { ProviderItem } from "./provider-item"

export function ProvidersPanel() {
  const { data, isLoading } = useLlmProviders()
  const layout = useProvidersLayout((s) => s.layout)
  const setLayout = useProvidersLayout((s) => s.setLayout)
  // `null` with the dialog open is the add case; a provider is the edit case.
  const [editing, setEditing] = useState<LlmProvider | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const providers = data?.providers ?? []

  const openAdd = () => {
    setEditing(null)
    setDialogOpen(true)
  }
  const openEdit = (provider: LlmProvider) => {
    setEditing(provider)
    setDialogOpen(true)
  }

  const header = (
    <div className="flex flex-wrap items-center gap-2">
      <IconSegmented
        value={layout}
        options={LLM_LAYOUT_OPTIONS}
        onChange={setLayout}
        label="Providers layout"
      />
      <Button
        variant="outline"
        className="border-primary/60 text-primary ml-auto"
        onClick={openAdd}
      >
        <Plus aria-hidden className="mr-1 h-4 w-4" />
        Add provider
      </Button>
    </div>
  )

  if (isLoading) {
    return (
      <div className="space-y-4">
        {header}
        <div className="grid gap-3.5 sm:grid-cols-2">
          {Array.from({ length: 2 }, (_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-md" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {header}
      {providers.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={Plug}
          title="No providers configured"
          description="A provider is one vendor connection an operator can point several purposes at instead of configuring each one separately."
        />
      ) : (
        <div
          className={cn(
            layout === "grid" ? "grid gap-3.5 sm:grid-cols-2" : "flex flex-col gap-2.5",
          )}
        >
          {providers.map((p) => (
            <ProviderItem
              key={p.name}
              provider={p}
              layout={layout}
              onEdit={() => openEdit(p)}
            />
          ))}
        </div>
      )}
      {dialogOpen && (
        <ProviderDialog
          key={editing?.name ?? "__add__"}
          provider={editing}
          open
          onOpenChange={setDialogOpen}
        />
      )}
    </div>
  )
}
