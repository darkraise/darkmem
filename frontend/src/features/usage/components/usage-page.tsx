import { useState } from "react"
import { DollarSign } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"

import { PageChrome } from "@/components/app-chrome"
import { EmptyState, HelpTip } from "@/components/darkmem"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import {
  useModelPrices,
  useSaveModelPrices,
  useUsageOverview,
  useUsageSubject,
  useUsageTop,
  type UsageWindow,
} from "@/hooks/api"
import { formatUsd } from "../format"
import { ModelPricesPanel } from "./model-prices-panel"
import { UsageOverview } from "./usage-overview"
import { UsageSubjectPanel } from "./usage-subject-panel"

const WINDOWS: ReadonlyArray<{ value: UsageWindow; label: string }> = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "all", label: "All" },
]

function TopSpenders({
  window,
  onSelect,
}: {
  window: UsageWindow
  onSelect: (subjectType: string, subjectId: string) => void
}) {
  const { data, isLoading, isError } = useUsageTop(window, "cost", 20)
  if (isLoading) return <Skeleton className="h-40 w-full" />
  if (isError) {
    return (
      <EmptyState
        kind="failed"
        title="Could not read the outlier list"
        description="A failed read is not an empty one; nothing is being asserted about spend here."
      />
    )
  }
  const items = data?.items ?? []
  if (items.length === 0) {
    return <EmptyState kind="empty" title="No recorded calls in this window" />
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Most expensive subjects</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Subject</TableHead>
                <TableHead>Id</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="text-right">Calls</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((row) => (
                <TableRow
                  key={`${row.subject_type}:${row.subject_id}`}
                  className="cursor-pointer"
                  onClick={() =>
                    row.subject_id &&
                    onSelect(row.subject_type, row.subject_id)
                  }
                >
                  <TableCell className="text-xs">{row.subject_type}</TableCell>
                  <TableCell className="max-w-[24rem] truncate font-mono text-xs">
                    {row.subject_id ?? "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {formatUsd(row.cost_micros)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {row.calls}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}

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
      <EmptyState
        kind="failed"
        title="Could not read that subject"
        description="A failed read is not an empty one."
      />
    )
  }
  return <UsageSubjectPanel data={data} />
}

export function UsagePage() {
  const [window, setWindow] = useState<UsageWindow>("30d")
  const [selected, setSelected] = useState<
    { subjectType: string; subjectId: string } | null
  >(null)
  const overview = useUsageOverview(window)
  const prices = useModelPrices()
  const savePrices = useSaveModelPrices()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={DollarSign}
        title="Usage"
        description="What every LLM call cost, and which work caused it."
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
          <span>Spend by purpose, model and subject, with its outliers.</span>
          <HelpTip label="About Usage">
            Every call is recorded, successes and failures alike, on a session
            of its own — so a failed call, which the vendor still billed, is not
            rolled back with the work it was metering. Costs are computed from
            the price table at call time and stored with the rates used, so
            re-pricing a model does not rewrite history.
          </HelpTip>
        </div>
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
            <EmptyState
              kind="failed"
              title="Could not read usage"
              description="A failed read is not an empty one; this is not a claim that nothing was spent."
            />
          ) : (
            <UsageOverview data={overview.data} />
          )}
        </TabsContent>

        <TabsContent className="space-y-4 pt-4" value="outliers">
          <TopSpenders
            window={window}
            onSelect={(subjectType, subjectId) =>
              setSelected({ subjectType, subjectId })
            }
          />
          {selected ? (
            <SubjectDetail
              subjectId={selected.subjectId}
              subjectType={selected.subjectType}
            />
          ) : null}
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
