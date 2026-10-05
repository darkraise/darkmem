import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "darkraise-ui/components/chart"

import type { UsageBreakdownRow, UsageSeriesBucket } from "@/hooks/api"
import { formatTokens, formatUsd } from "../format"

/**
 * Both charts here plot magnitude, which is a one-hue job: bar length carries
 * the quantity and the colour carries nothing, so there is no categorical
 * palette to get wrong, and a single series needs no legend -- the card title
 * already names what is plotted.
 *
 * `--chart-1` follows the user's accent axis, which is the right behaviour for
 * this design system and comes with a measured cost: the shipped green is
 * 11.15:1 on the dark card and **1.74:1 on a light one**, and the token is a
 * single value rather than a per-mode step. Rather than fork the accent for one
 * chart, both charts carry the relief a sub-3:1 mark obliges -- a direct value
 * label on every bar of the ranked chart and on the extreme of the time series,
 * plus the by-model and by-subject tables underneath, which carry every number
 * in text.
 */
const ONE_SERIES = {
  value: { label: "Cost", color: "var(--chart-1)" },
} satisfies ChartConfig

/** Marks stay thin and the grid recessive: the data is the only loud thing. */
const BAR_MAX = 24
const GRID = "hsl(var(--border))"
const AXIS_TICK = { fill: "hsl(var(--muted-foreground))", fontSize: 11 }

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}

export function SpendOverTime({ buckets }: { buckets: UsageSeriesBucket[] }) {
  const data = buckets.map((b) => ({
    label: dayLabel(b.bucket_start),
    value: b.cost_micros,
    calls: b.calls,
    unmeasured: b.unmeasured_calls,
  }))
  const peak = data.reduce((m, d) => Math.max(m, d.value), 0)

  if (data.length === 0) {
    return (
      <p className="text-muted-foreground py-8 text-center text-xs">
        No recorded calls in this window.
      </p>
    )
  }

  return (
    <ChartContainer
      className="h-56 w-full"
      config={ONE_SERIES}
      initialDimension={{ width: 640, height: 224 }}
    >
      {/* Right margin leaves room for the peak label when the peak is the
          last column; at phone width it was cut at the card edge. */}
      <BarChart data={data} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
        <XAxis
          axisLine={false}
          dataKey="label"
          tick={AXIS_TICK}
          tickLine={false}
          tickMargin={8}
        />
        <YAxis
          axisLine={false}
          tick={AXIS_TICK}
          tickFormatter={(v: number) => formatUsd(v)}
          tickLine={false}
          width={64}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value, _name, item) => {
                const row = (item as { payload?: (typeof data)[number] })
                  ?.payload
                return (
                  <span className="font-mono text-xs">
                    {formatUsd(Number(value))} · {row?.calls ?? 0} calls
                    {row?.unmeasured ? ` · ${row.unmeasured} unmeasured` : ""}
                  </span>
                )
              }}
            />
          }
          cursor={false}
        />
        <Bar
          dataKey="value"
          fill="var(--color-value)"
          maxBarSize={BAR_MAX}
          radius={[4, 4, 0, 0]}
        >
          {/* The extreme only. A value on every column is chaos and goes
              unread; the axis and the tooltip carry the rest. */}
          <LabelList
            className="fill-foreground font-mono"
            dataKey="value"
            fontSize={11}
            formatter={(v) => (Number(v) === peak ? formatUsd(Number(v)) : "")}
            position="top"
          />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}

export function CostByPurpose({ rows }: { rows: UsageBreakdownRow[] }) {
  // Sorted descending so the reader's eye lands on where the money went.
  const data = [...rows]
    .sort((a, b) => b.cost_micros - a.cost_micros)
    .map((r) => ({
      label: r.key,
      value: r.cost_micros,
      calls: r.calls,
      // A purpose with an unmeasured or unpriced call is not fully costed, and
      // the bar cannot say so on its own.
      incomplete: r.unmeasured_calls > 0 || r.unpriced_calls > 0,
    }))

  if (data.length === 0) {
    return (
      <p className="text-muted-foreground py-8 text-center text-xs">
        No recorded calls in this window.
      </p>
    )
  }

  return (
    <ChartContainer
      className="h-56 w-full"
      config={ONE_SERIES}
      initialDimension={{ width: 640, height: 224 }}
    >
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 56, bottom: 0, left: 0 }}
      >
        <CartesianGrid horizontal={false} stroke={GRID} strokeWidth={1} />
        <XAxis
          axisLine={false}
          tick={AXIS_TICK}
          tickFormatter={(v: number) => formatUsd(v)}
          tickLine={false}
          type="number"
        />
        <YAxis
          axisLine={false}
          dataKey="label"
          tick={AXIS_TICK}
          tickLine={false}
          type="category"
          width={104}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value, _name, item) => {
                const row = (item as { payload?: (typeof data)[number] })
                  ?.payload
                return (
                  <span className="font-mono text-xs">
                    {formatUsd(Number(value))} · {row?.calls ?? 0} calls
                    {row?.incomplete ? " · not fully costed" : ""}
                  </span>
                )
              }}
            />
          }
          cursor={false}
        />
        <Bar dataKey="value" maxBarSize={BAR_MAX} radius={[0, 4, 4, 0]}>
          {/* Outside the bar end, so a short bar's label is never clipped and
              never sits on the fill. */}
          <LabelList
            className="fill-foreground font-mono"
            dataKey="value"
            fontSize={11}
            formatter={(v) => formatUsd(Number(v))}
            offset={8}
            position="right"
          />
          {data.map((row) => (
            // Every bar is the same hue -- the length is the quantity. The
            // dimmed fill marks a bar whose total is a floor, not a total.
            <Cell
              key={row.label}
              fill="var(--color-value)"
              fillOpacity={row.incomplete ? 0.45 : 1}
            />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}

/** A proportional bar inside a table row: the same magnitude job as the chart
 *  above, at a scale where a second chart would be noise. */
export function ShareBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0
  return (
    <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
      <div
        className="h-full rounded-full"
        style={{ width: `${pct}%`, background: "var(--chart-1)" }}
      />
    </div>
  )
}

export { formatTokens }
