import { useState } from "react"
import { DollarSign } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"

import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import {
  useModelPrices,
  useSaveModelPrices,
  useUsageOverview,
  useUsageSeries,
  useUsageSubject,
  useUsageTop,
  type UsageWindow,
} from "@/hooks/api"
import { ModelPricesPanel } from "./model-prices-panel"
import { OutliersPanel, type OutlierAxis } from "./outliers-panel"
import { UsageOverview } from "./usage-overview"
import { UsageSubjectPanel } from "./usage-subject-panel"

const WINDOWS: ReadonlyArray<{ value: UsageWindow; label: string }> = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "all", label: "All" },
]

function SubjectDetail({
  subjectType,
  subjectId,
}: {
  subjectType: string
  subjectId: string
}) {
  const { data, isLoading, isError } = useUsageSubject(subjectType, subjectId)
  if (isLoading) return <Skeleton className="h-40 w-full" />
  if (isError || !data) {
    return (
      <EmptyState kind="failed" title="Could not read that subject" />
    )
  }
  return <UsageSubjectPanel data={data} />
}

export function UsagePage() {
  const [window, setWindow] = useState<UsageWindow>("30d")
  const [selected, setSelected] = useState<
    { subjectType: string; subjectId: string } | null
  >(null)
  const [axis, setAxis] = useState<OutlierAxis>("cost")
  const [typeFilter, setTypeFilter] = useState<string | null>(null)
  const overview = useUsageOverview(window)
  // Hourly buckets for a one-day window: a 24h span drawn in days is
  // one column, which says nothing.
  const series = useUsageSeries(window, window === "24h" ? "hour" : "day")
  const top = useUsageTop(window, axis, 20)
  const prices = useModelPrices()
  const topRows = top.data?.items ?? []
  // Filtered client-side rather than by refetching: the list is already capped
  // at twenty rows, so a round-trip per chip would cost a request to narrow
  // something the page is holding.
  const availableTypes = [...new Set(topRows.map((r) => r.subject_type))].sort()
  const visibleRows = typeFilter
    ? topRows.filter((r) => r.subject_type === typeFilter)
    : topRows
  const savePrices = useSaveModelPrices()

  return (
    <div className="space-y-4">
      <PageChrome icon={DollarSign} title="Usage" />

      <div className="flex flex-wrap items-center gap-3">
        <div className="ml-auto">
          <SegmentGroup
            aria-label="Window"
            color="accent"
            value={window}
            onValueChange={(v) => {
              if (v) setWindow(v as UsageWindow)
            }}
          >
            <SegmentGroupIndicator />
            {WINDOWS.map((w) => (
              <SegmentGroupItem key={w.value} value={w.value}>
                {w.label}
              </SegmentGroupItem>
            ))}
          </SegmentGroup>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="outliers">Outliers</TabsTrigger>
          <TabsTrigger value="prices">Prices</TabsTrigger>
        </TabsList>

        <TabsContent className="pt-4" value="overview">
          {overview.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : overview.isError || !overview.data ? (
            <EmptyState kind="failed" title="Could not read usage" />
          ) : (
            <UsageOverview
              data={overview.data}
              series={series.data?.buckets ?? []}
            />
          )}
        </TabsContent>

        <TabsContent className="pt-4" value="outliers">
          <div
            className={
              selected
                ? "grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] xl:items-start"
                : "grid gap-4"
            }
          >
          <OutliersPanel
            availableTypes={availableTypes}
            axis={axis}
            isError={top.isError}
            isLoading={top.isLoading}
            onAxisChange={setAxis}
            onSelect={(subjectType, subjectId) =>
              setSelected({ subjectType, subjectId })
            }
            onTypeFilterChange={(t) => {
              setTypeFilter(t)
              setSelected(null)
            }}
            rows={visibleRows}
            selectedKey={
              selected ? `${selected.subjectType}:${selected.subjectId}` : null
            }
            typeFilter={typeFilter}
            windowCalls={overview.data?.total_calls ?? 0}
            windowTotal={overview.data?.total_cost_micros ?? 0}
          />
          {selected ? (
            <div className="xl:sticky xl:top-4">
              <SubjectDetail
                subjectId={selected.subjectId}
                subjectType={selected.subjectType}
              />
            </div>
          ) : null}
          </div>
        </TabsContent>

        <TabsContent className="pt-4" value="prices">
          {prices.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : prices.isError || !prices.data ? (
            <EmptyState kind="failed" title="Could not read the price table" />
          ) : (
            <ModelPricesPanel
              models={prices.data.models}
              saving={savePrices.isPending}
              onSave={(next) =>
                savePrices.mutate(next, {
                  onSuccess: () => toast.success("Prices saved"),
                  onError: (err) =>
                    toast.error("Could not save prices", {
                      description: err.message,
                    }),
                })
              }
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
