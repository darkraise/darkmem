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

/** A rate the server will take: a finite, non-negative number. Checked here so
 *  "abc" is named beside its field instead of returning as the validator's
 *  "prices.<model>.<field>: Input should be a valid number". */
function validRate(dollars: string): boolean {
  if (dollars.trim() === "") return false
  const n = Number(dollars)
  return Number.isFinite(n) && n >= 0
}

const EMPTY_ROW = {
  input_micros_per_mtok: 0,
  cached_micros_per_mtok: 0,
  output_micros_per_mtok: 0,
  overridden: false,
} as const

export function ModelPricesPanel({
  models,
  unpricedModels = [],
  onSave,
  saving = false,
}: {
  models: ModelPriceRow[]
  /** Models that made calls in the window and have no rate. The overview's
   *  caveat sends the reader here to price them, so they are rows to fill
   *  in rather than names to retype. */
  unpricedModels?: string[]
  onSave: (
    prices: Record<string, Record<string, number>>,
  ) => void
  saving?: boolean
}) {
  const [draft, setDraft] = useState<Draft>({})
  const [added, setAdded] = useState<string[]>([])
  const [newModel, setNewModel] = useState("")

  const valueFor = (row: ModelPriceRow, field: string) =>
    draft[row.model]?.[field] ??
    toDollars(row[field as keyof ModelPriceRow] as number)

  const known = new Set(models.map((row) => row.model))
  const extra = [...unpricedModels, ...added].filter(
    (model, i, all) => !known.has(model) && all.indexOf(model) === i,
  )
  const rows: ModelPriceRow[] = [
    ...models,
    ...extra.map((model) => ({ model, ...EMPTY_ROW })),
  ]
  // A new row nobody typed into is not sent: it would price the model at
  // zero, which reads as "free" rather than "not priced".
  const isUntouchedExtra = (row: ModelPriceRow) =>
    !known.has(row.model) && !draft[row.model]
  const invalid = rows.some(
    (row) =>
      !isUntouchedExtra(row) &&
      FIELDS.some(([field]) => !validRate(valueFor(row, field))),
  )

  const handleSave = () => {
    // A full replace, matching the config-singleton PUT: every row is sent, so
    // clearing an override means editing it back rather than deleting a key
    // the server can no longer see.
    const prices: Record<string, Record<string, number>> = {}
    for (const row of rows) {
      if (isUntouchedExtra(row)) continue
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
          Dollars per million tokens. Changing a rate affects future calls
          only.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                {FIELDS.map(([field, label]) => (
                  <TableHead key={field} className="w-32 text-right">
                    {label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.model}>
                  <TableCell className="font-mono text-xs">
                    {row.model}
                    {row.overridden ? (
                      <Badge className="ml-1" variant="secondary">
                        overridden
                      </Badge>
                    ) : null}
                    {!known.has(row.model) ? (
                      <Badge className="ml-1" variant="outline">
                        not priced
                      </Badge>
                    ) : null}
                  </TableCell>
                  {FIELDS.map(([field, label]) => (
                    <TableCell key={field}>
                      {/* `text-right` on the cell does not move the input:
                          it is a block box of fixed width, and text-align
                          positions inline content only. Right-aligning the
                          box itself is what puts it under its header. */}
                      <div className="flex justify-end">
                        <Input
                          aria-label={`${row.model} ${label} rate`}
                          aria-invalid={
                            !isUntouchedExtra(row) &&
                            !validRate(valueFor(row, field))
                          }
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
                      </div>
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            const model = newModel.trim()
            if (model) setAdded((list) => [...list, model])
            setNewModel("")
          }}
        >
          <Input
            aria-label="Model to price"
            placeholder="model id, e.g. qwen2.5:3b"
            className="w-64 font-mono text-xs"
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
          />
          <Button type="submit" variant="outline" size="sm">
            Add model
          </Button>
        </form>
        {invalid ? (
          <p role="alert" className="text-destructive text-sm">
            Every rate must be a number of dollars, zero or more.
          </p>
        ) : null}
        <Button disabled={saving || invalid} onClick={handleSave} size="sm">
          {saving ? "Saving…" : "Save prices"}
        </Button>
      </CardContent>
    </Card>
  )
}
