import { useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"

import type { ModelPriceRow } from "@/hooks/api"

type Draft = Record<string, Record<string, string>>

const FIELDS = [
  ["input_micros_per_mtok", "Input"],
  ["cached_micros_per_mtok", "Cached"],
  ["output_micros_per_mtok", "Output"],
] as const

/** Rates are entered in dollars per million tokens and stored as integer
 *  micro-USD. The conversion lives here so the wire stays integral. */
function toMicros(dollars: string): number {
  return Math.round(Number(dollars) * 1_000_000)
}

function toDollars(micros: number): string {
  return (micros / 1_000_000).toString()
}

export function ModelPricesPanel({
  models,
  onSave,
  saving = false,
}: {
  models: ModelPriceRow[]
  onSave: (
    prices: Record<string, Record<string, number>>,
  ) => void
  saving?: boolean
}) {
  const [draft, setDraft] = useState<Draft>({})

  const valueFor = (row: ModelPriceRow, field: string) =>
    draft[row.model]?.[field] ??
    toDollars(row[field as keyof ModelPriceRow] as number)

  const handleSave = () => {
    // A full replace, matching the config-singleton PUT: every row is sent, so
    // clearing an override means editing it back rather than deleting a key
    // the server can no longer see.
    const prices: Record<string, Record<string, number>> = {}
    for (const row of models) {
      prices[row.model] = Object.fromEntries(
        FIELDS.map(([field]) => [field, toMicros(valueFor(row, field))]),
      )
    }
    onSave(prices)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Model prices</CardTitle>
        <CardDescription>
          Dollars per million tokens. A model with no rate here is reported as
          &ldquo;not priced&rdquo; rather than as free, and editing a rate
          changes what future calls cost — stored rows keep the rates they were
          written with.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                {FIELDS.map(([field, label]) => (
                  <TableHead key={field} className="text-right">
                    {label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {models.map((row) => (
                <TableRow key={row.model}>
                  <TableCell className="font-mono text-xs">
                    {row.model}
                    {row.overridden ? (
                      <Badge className="ml-1" variant="secondary">
                        overridden
                      </Badge>
                    ) : null}
                  </TableCell>
                  {FIELDS.map(([field, label]) => (
                    <TableCell key={field} className="text-right">
                      <Input
                        aria-label={`${row.model} ${label} rate`}
                        className="w-28 text-right font-mono text-xs"
                        inputMode="decimal"
                        value={valueFor(row, field)}
                        onChange={(e) =>
                          setDraft((d) => ({
                            ...d,
                            [row.model]: {
                              ...d[row.model],
                              [field]: e.target.value,
                            },
                          }))
                        }
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <Button disabled={saving} onClick={handleSave} size="sm">
          {saving ? "Saving…" : "Save prices"}
        </Button>
      </CardContent>
    </Card>
  )
}
