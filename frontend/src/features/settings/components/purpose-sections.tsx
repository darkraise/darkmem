import type { ReactNode } from "react"
import { Input } from "darkraise-ui/components/input"
import { cn } from "darkraise-ui/lib"
import { Cloud, Cpu } from "lucide-react"
import {
  HelpTip,
  IconSegmented,
  type IconSegmentedOption,
} from "@/components/darkmem"
import type { DemoCodeBucket } from "@/features/settings/types"
import type { LLMTabBinding } from "../use-llm-tab-binding"

/**
 * The pieces a purpose editor is built from, lifted out of the tab so the
 * dialog can render the same ones. Kept together rather than inlined in the
 * dialog because `CodeBuckets` belongs to exactly one purpose and reads better
 * beside the row it sits under.
 */

/** Sentence-case names for the wire keys the LLM dialogs edit. The key
 *  itself stays beside the name as a mono hint (as the Flags tab's
 *  SettingName does), so the dialogs read like the git and API-key dialogs
 *  while an operator can still match a field to the config it writes. */
const FIELD_NAMES: Record<string, string> = {
  name: "Name",
  api_kind: "API kind",
  base_url: "Base URL",
  api_key: "API key",
  model: "Model",
  provider_name: "Provider",
  dimensions: "Dimensions",
  reasoning: "Reasoning",
  params: "Parameters",
}

export function Field({
  label,
  span2,
  children,
}: {
  /** The wire key; shown as a mono hint under its sentence-case name. */
  label: string
  span2?: boolean
  children: ReactNode
}) {
  const name = FIELD_NAMES[label]
  return (
    <div className={cn("flex flex-col gap-1", span2 && "sm:col-span-2")}>
      <span className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-muted-foreground text-sm">{name ?? label}</span>
        {name && (
          <span className="text-muted-foreground/80 font-mono text-xs">
            {label}
          </span>
        )}
      </span>
      {children}
    </div>
  )
}

const CLASSIFIER_KIND_OPTIONS: ReadonlyArray<
  IconSegmentedOption<"llm" | "local">
> = [
  // Visible text, not icons alone: the two differ in cost and in where the
  // model runs, which should not be readable only on hover.
  { value: "llm", label: "LLM-backed classifier", icon: Cloud, text: "LLM" },
  {
    value: "local",
    label: "In-process classifier",
    icon: Cpu,
    text: "In-process",
  },
]

export function ClassifierKindRow({ binding }: { binding: LLMTabBinding }) {
  return (
    <div className="border-primary/40 bg-primary/5 flex flex-wrap items-center gap-2.5 rounded-md border border-dashed px-2.5 py-2">
      <span className="font-mono text-sm">classifier_kind</span>
      <IconSegmented
        value={binding.classifierKind}
        options={CLASSIFIER_KIND_OPTIONS}
        onChange={binding.setClassifierKind}
        label="classifier_kind"
      />
      <HelpTip label="About classifier_kind">
        Which classifier labels new memories: an LLM, or a model that runs
        in-process.
      </HelpTip>
    </div>
  )
}

export function CodeBuckets({
  buckets,
  saveCodeBucket,
}: {
  buckets: DemoCodeBucket[]
  saveCodeBucket: NonNullable<LLMTabBinding["saveCodeBucket"]>
}) {
  return (
    <div className="border-border flex flex-col gap-2 border-t border-dashed pt-2.5">
      <div className="flex items-center gap-1.5">
        <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
          code-summarization buckets
        </span>
        <HelpTip label="About code-summarization buckets">
          Each bucket uses its own model over the summarization provider.
        </HelpTip>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-3">
        {buckets.map((bucket) => (
          <div
            key={bucket.key}
            className="border-inset bg-background flex flex-col gap-1.5 rounded-md border px-2.5 py-2"
          >
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-sm font-semibold">
                {bucket.key}
              </span>
              <HelpTip label={`About the ${bucket.key} bucket`}>
                {bucket.note}
              </HelpTip>
            </div>
            <Input
              value={bucket.model}
              aria-label={`${bucket.key} bucket model`}
              onChange={(e) => saveCodeBucket(bucket.key, e.target.value)}
              className="font-mono"
            />
          </div>
        ))}
      </div>
    </div>
  )
}
