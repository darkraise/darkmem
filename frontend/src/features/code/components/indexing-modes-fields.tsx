import {
  NumberInput,
  NumberInputControl,
  NumberInputDecrementTrigger,
  NumberInputField,
  NumberInputIncrementTrigger,
  NumberInputLabel,
  NumberInputSuffix,
  NumberInputTriggerGroup,
} from "darkraise-ui/components/number-input"
import { Switch } from "darkraise-ui/components/switch"
import { useId } from "react"

export interface IndexingModes {
  fetch_enabled: boolean
  fetch_interval_seconds: number
  index_on_commit_enabled: boolean
  commit_poll_seconds: number
  index_uncommitted: boolean
}

const FETCH_INTERVAL_FLOOR_SECONDS = 30
const COMMIT_POLL_FLOOR_SECONDS = 15

/**
 * Every field here is a per-repo opt-in switch defaulting off, replacing the
 * single always-on sync flag this repo used to carry. Fetching is the one
 * switch that writes to the operator's checkout (`git fetch` +
 * `git merge --ff-only`); index-on-commit only reads HEAD. An operator
 * sharing a checkout with darkmem needs that asymmetry stated, not inferred
 * from the switch names.
 *
 * Both intervals are shown in the unit they are stored in. Displaying the
 * fetch interval in minutes meant its floor landed at half a minute, so the
 * control could show a fraction and its step walked off the stored grain.
 * Each stepper's step is that field's own floor, so walking from the floor
 * only ever lands on a value the API accepts.
 */
export function IndexingModesFields({
  value,
  onChange,
}: {
  value: IndexingModes
  onChange: (next: IndexingModes) => void
}) {
  // The captions sit beside the switches rather than wrapping them: the first
  // two rows hold a NumberInput, so an enclosing <label> would toggle the
  // switch when the operator clicks into the number field.
  const ids = useId()

  return (
    <div className="space-y-3 rounded-md border px-3 py-2">
      <div className="text-sm font-medium">Indexing</div>

      <div className="flex items-start gap-2">
        <Switch
          id={`${ids}-fetch`}
          className="mt-0.5"
          checked={value.fetch_enabled}
          onCheckedChange={(v) => onChange({ ...value, fetch_enabled: v })}
        />
        <div className="flex-1 space-y-1 text-sm">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor={`${ids}-fetch`} className="cursor-pointer">
              Fetch from remote
            </label>
            <NumberInput
              className="w-28"
              value={value.fetch_interval_seconds}
              min={FETCH_INTERVAL_FLOOR_SECONDS}
              step={FETCH_INTERVAL_FLOOR_SECONDS}
              disabled={!value.fetch_enabled}
              onValueChange={(d) => {
                if (Number.isNaN(d.valueAsNumber)) return
                onChange({
                  ...value,
                  fetch_interval_seconds: Math.round(d.valueAsNumber),
                })
              }}
            >
              <NumberInputLabel className="sr-only">
                Fetch interval
              </NumberInputLabel>
              <NumberInputControl>
                <NumberInputField />
                <NumberInputSuffix>sec</NumberInputSuffix>
                <NumberInputTriggerGroup>
                  <NumberInputDecrementTrigger />
                  <NumberInputIncrementTrigger />
                </NumberInputTriggerGroup>
              </NumberInputControl>
            </NumberInput>
          </div>
          <p className="text-muted-foreground text-sm">
            Advances your working tree. Fast-forward only.
          </p>
        </div>
      </div>

      <div className="flex items-start gap-2">
        <Switch
          id={`${ids}-commit`}
          className="mt-0.5"
          checked={value.index_on_commit_enabled}
          onCheckedChange={(v) =>
            onChange({ ...value, index_on_commit_enabled: v })
          }
        />
        <div className="flex-1 space-y-2 text-sm">
          <div className="flex items-center justify-between gap-3">
            <label htmlFor={`${ids}-commit`} className="cursor-pointer">
              Index on new commit
            </label>
            <NumberInput
              className="w-28"
              value={value.commit_poll_seconds}
              min={COMMIT_POLL_FLOOR_SECONDS}
              step={COMMIT_POLL_FLOOR_SECONDS}
              disabled={!value.index_on_commit_enabled}
              onValueChange={(d) => {
                if (Number.isNaN(d.valueAsNumber)) return
                onChange({
                  ...value,
                  commit_poll_seconds: Math.round(d.valueAsNumber),
                })
              }}
            >
              <NumberInputLabel className="sr-only">
                Commit poll interval
              </NumberInputLabel>
              <NumberInputControl>
                <NumberInputField />
                <NumberInputSuffix>sec</NumberInputSuffix>
                <NumberInputTriggerGroup>
                  <NumberInputDecrementTrigger />
                  <NumberInputIncrementTrigger />
                </NumberInputTriggerGroup>
              </NumberInputControl>
            </NumberInput>
          </div>
          <p className="text-muted-foreground text-sm">
            Watches HEAD. Covers commits from any source.
          </p>

          <div className="flex items-start gap-2">
            <Switch
              id={`${ids}-uncommitted`}
              className="mt-0.5"
              checked={value.index_uncommitted}
              disabled={!value.index_on_commit_enabled}
              onCheckedChange={(v) =>
                onChange({ ...value, index_uncommitted: v })
              }
            />
            <div className="text-sm">
              <label
                htmlFor={`${ids}-uncommitted`}
                className="block cursor-pointer"
              >
                Also index uncommitted changes
              </label>
              <p className="text-muted-foreground text-sm">
                Indexes saved files before they are committed.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
