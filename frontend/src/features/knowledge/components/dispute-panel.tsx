import { VerificationBadge } from "@/components/darkmem"
import type { DisputeSide, FactDispute } from "@/demo/types"
import { AppliesWhenChips } from "./fact-parts"
import { SourceRow } from "./fact-sources"
import { BeliefWindowRow } from "./belief-window"

function DisputeSideCard({ side }: { side: DisputeSide }) {
  return (
    <div className="border-border space-y-2 rounded-md border p-3">
      <VerificationBadge status="disputed" />
      <p className="text-muted-foreground font-mono text-sm">
        object_name: {side.object_name}
      </p>
      <p className="text-sm">{side.assertion}</p>
      <p className="text-muted-foreground text-sm">
        {side.origin_count} {side.origin_count === 1 ? "origin" : "origins"} ·{" "}
        {side.origin_kinds.length === 1 ? "kind" : "kinds"} [
        {side.origin_kinds.join(", ")}]
      </p>
      <p className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        sources — grouped by origin_key
      </p>
      <div>
        {side.sources.map((source, i) => (
          <SourceRow key={i} source={source} />
        ))}
      </div>
      <p className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        belief window
      </p>
      <BeliefWindowRow window={side.window} />
      <AppliesWhenChips items={side.applies_when} />
    </div>
  )
}

// Both sides at strictly equal visual weight — no comparative bar, no
// picked winner, the earlier-asserted side rendered first. Corroboration
// count does not adjudicate a dispute; one non-echo contradiction over an
// overlapping window vetoes regardless of count. Resolution happens only
// in the Review queue.
export function DisputePanel({ dispute }: { dispute: FactDispute }) {
  const [first, second] = dispute.sides
  return (
    <div className="grid grid-cols-1 gap-2.5 md:grid-cols-[1fr_auto_1fr]">
      <DisputeSideCard side={first} />
      <div className="text-muted-foreground flex items-center justify-center font-mono text-sm tracking-wide uppercase">
        vs
      </div>
      <DisputeSideCard side={second} />
    </div>
  )
}
