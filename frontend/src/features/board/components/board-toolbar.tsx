import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Switch } from "darkraise-ui/components/switch"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import type { GroupableProperty, ViewDefinition, ViewFilter } from "@/hooks/api"
import {
  GROUPABLE,
  PROPERTY_LABELS,
  propertyValue,
  shortName,
  type BoardRecord,
} from "../lib/records"

const NO_GROUP = "__none"

/** The `in` filter on `property`, replaced by `values` (removed when empty).
 *  Other filters on the property, such as a built-in's `not_in`, stay. */
export function withInFilter(
  definition: ViewDefinition,
  property: GroupableProperty,
  values: string[],
): ViewDefinition {
  const others = definition.filters.filter(
    (f) => !(f.property === property && f.operator === "in"),
  )
  const added: ViewFilter[] =
    values.length > 0 ? [{ property, operator: "in", values }] : []
  return { ...definition, filters: [...others, ...added] }
}

function optionLabel(property: GroupableProperty, value: string): string {
  return property === "source" || property === "plan" ? shortName(value) : value
}

/** Layout, grouping and filter controls over a view's draft definition. */
export function BoardToolbar({
  records,
  definition,
  onChange,
  text,
  onTextChange,
}: {
  records: BoardRecord[]
  definition: ViewDefinition
  onChange: (next: ViewDefinition) => void
  text: string
  onTextChange: (text: string) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <ToggleGroup
        type="single"
        value={definition.layout}
        onValueChange={(value) => {
          if (value)
            onChange({ ...definition, layout: value as "board" | "table" })
        }}
      >
        <ToggleGroupItem value="board" size="sm">
          Board
        </ToggleGroupItem>
        <ToggleGroupItem value="table" size="sm">
          Table
        </ToggleGroupItem>
      </ToggleGroup>
      <Select
        value={definition.group_by ?? NO_GROUP}
        onValueChange={(value) =>
          onChange({
            ...definition,
            group_by: value === NO_GROUP ? null : (value as GroupableProperty),
          })
        }
      >
        <SelectTrigger className="w-auto min-w-36" aria-label="Group by">
          <SelectValue>
            Group:{" "}
            {definition.group_by
              ? PROPERTY_LABELS[definition.group_by]
              : "none"}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_GROUP}>none</SelectItem>
          {GROUPABLE.map((property) => (
            <SelectItem key={property} value={property}>
              {PROPERTY_LABELS[property]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {GROUPABLE.map((property) => {
        const values = [
          ...new Set(
            records
              .map((r) => propertyValue(r, property))
              .filter((v): v is string => Boolean(v)),
          ),
        ].sort()
        const selected =
          definition.filters.find(
            (f) => f.property === property && f.operator === "in",
          )?.values ?? []
        return (
          <MultiSelect
            key={property}
            className="w-44"
            placeholder={PROPERTY_LABELS[property]}
            items={values.map((value) => ({
              value,
              label: optionLabel(property, value),
            }))}
            value={selected}
            onValueChange={({ value }) =>
              onChange(withInFilter(definition, property, value))
            }
          />
        )
      })}
      <Input
        aria-label="Search title and note"
        placeholder="Search title and note"
        className="w-56"
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
      />
      <div className="flex items-center gap-1.5">
        <Switch
          id="board-show-untracked"
          checked={definition.show_untracked}
          onCheckedChange={(checked) =>
            onChange({ ...definition, show_untracked: checked })
          }
        />
        <Label htmlFor="board-show-untracked">Show untracked</Label>
      </div>
    </div>
  )
}
