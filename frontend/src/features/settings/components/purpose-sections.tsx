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

export function Field({
  label,
  span2,
  children,
}: {
  label: string
  span2?: boolean
  children: ReactNode
}) {
  return (
    <div className={cn("flex flex-col gap-1", span2 && "col-span-2")}>
      <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        {label}
      </span>
      {children}
    </div>
  )
}

const CLASSIFIER_KIND_OPTIONS: ReadonlyArray<
  IconSegmentedOption<"llm" | "local">
> = [
  { value: "llm", label: "LLM-backed classifier", icon: Cloud },
  { value: "local", label: "In-process classifier", icon: Cpu },
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
