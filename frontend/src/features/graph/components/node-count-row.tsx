import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import {
  NumberInput,
  NumberInputControl,
  NumberInputDecrementTrigger,
  NumberInputField,
  NumberInputIncrementTrigger,
  NumberInputLabel,
  NumberInputTriggerGroup,
} from "darkraise-ui/components/number-input"
import { useId } from "react"
import {
  NODE_LIMIT_MAX,
  NODE_LIMIT_MIN,
  NODE_LIMIT_STEP,
} from "@/features/graph/lib/graph-prefs"

interface NodeCountRowProps {
  nodeLimit: number
  onNodeLimitChange: (n: number) => void
  allNodes: boolean
  onAllNodesChange: (all: boolean) => void
  /** Memories in the current response. */
  shown: number
  /** In-scope memories the server could plot; absent until a response lands. */
  total?: number
  truncated?: boolean
}

export function NodeCountRow({
  nodeLimit,
  onNodeLimitChange,
  allNodes,
  onAllNodesChange,
  shown,
  total,
  truncated = false,
}: NodeCountRowProps) {
  const allId = useId()
  return (
    <div className="space-y-1">
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Label className="w-16 shrink-0 text-right font-normal">Nodes</Label>
        <NumberInput
          className="w-28"
          value={nodeLimit}
          min={NODE_LIMIT_MIN}
          max={NODE_LIMIT_MAX}
          step={NODE_LIMIT_STEP}
          disabled={allNodes}
          onValueChange={(d) => {
            if (Number.isNaN(d.valueAsNumber)) return
            onNodeLimitChange(d.valueAsNumber)
          }}
        >
          <NumberInputLabel className="sr-only">Node limit</NumberInputLabel>
          <NumberInputControl>
            <NumberInputField />
            <NumberInputTriggerGroup>
              <NumberInputDecrementTrigger />
              <NumberInputIncrementTrigger />
            </NumberInputTriggerGroup>
          </NumberInputControl>
        </NumberInput>
        <Checkbox
          id={allId}
          size="sm"
          checked={allNodes}
          onCheckedChange={(checked) => onAllNodesChange(checked === true)}
          aria-label="All nodes"
        />
        <label htmlFor={allId} className="cursor-pointer">
          All
        </label>
      </div>
      {total !== undefined && (
        <p
          className="text-muted-foreground pl-[4.5rem] text-xs"
          data-testid="node-count-summary"
        >
          Showing {shown.toLocaleString("en-US")} of {total.toLocaleString("en-US")}
          {allNodes && truncated
            ? ` (capped at ${NODE_LIMIT_MAX.toLocaleString("en-US")})`
            : ""}
        </p>
      )}
    </div>
  )
}
