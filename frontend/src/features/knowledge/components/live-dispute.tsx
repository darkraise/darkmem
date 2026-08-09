import { Link } from "@tanstack/react-router"
import { useDetailLevel, VerificationBadge } from "@/components/darkmem"
import type { FactDispute, FactDisputeTriple } from "@/hooks/api"
import { FactTriple } from "./fact-parts"

function TripleOrUnrecorded({ triple }: { triple: FactDisputeTriple | null }) {
  if (!triple || !triple.subject || !triple.rel_type || !triple.object) {
    return (
      <p className="text-muted-foreground text-sm italic">no triple on record</p>
    )
  }
  return (
    <FactTriple subject={triple.subject} rel={triple.rel_type} object={triple.object} />
  )
}

/** Doc 12 §4's two-sided rendering, over the live door's structured
 *  `dispute` block (T2.86). The **sentence** is `badge.claim`, shown
 *  elsewhere verbatim — this lays out the same finding's parts (both
 *  triples, the rule, the witness) so a reader can see the structure behind
 *  the sentence, never composing a second sentence from them.
 *
 *  `counterpart` is absent on a recovery, a caller-overridden verdict, or a
 *  dispute predating T2.64 — three causes the journal cannot distinguish, so
 *  this renders the one honest label the backend gives for all three
 *  (`counterpart_absent`) rather than guessing which applies. */
export function LiveDisputePanel({ dispute }: { dispute: FactDispute }) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  return (
    <div className="grid grid-cols-1 gap-2.5 md:grid-cols-[1fr_auto_1fr]">
      <div className="border-border space-y-2 rounded-md border p-3">
        <VerificationBadge status="disputed" label="this fact" />
        <TripleOrUnrecorded triple={dispute.claim} />
      </div>
      <div className="text-muted-foreground flex items-center justify-center font-mono text-sm tracking-wide uppercase">
        vs
      </div>
      <div className="border-border space-y-2 rounded-md border p-3">
        <VerificationBadge status="disputed" label="counterpart" />
        <TripleOrUnrecorded triple={dispute.counterpart} />
        {!dispute.counterpart && dispute.counterpart_absent && (
          <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
            {dispute.counterpart_absent}
          </p>
        )}
        {dispute.counterpart?.id && (
          <Link
            to="/knowledge/facts/$factId"
            params={{ factId: dispute.counterpart.id }}
            className="text-primary text-sm"
          >
            view the counterpart fact →
          </Link>
        )}
      </div>
      {advanced && (dispute.rule || dispute.witness_origin || dispute.enumeration) && (
        <dl className="text-muted-foreground col-span-full grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1 font-mono text-[10px] tracking-wide uppercase">
          {dispute.rule && (
            <>
              <dt>rule</dt>
              <dd className="lowercase">{dispute.rule}</dd>
            </>
          )}
          {dispute.witness_origin && (
            <>
              <dt>witness_origin</dt>
              <dd className="lowercase">{dispute.witness_origin}</dd>
            </>
          )}
          {dispute.enumeration && (
            <>
              <dt>enumeration</dt>
              <dd className="lowercase">{dispute.enumeration}</dd>
            </>
          )}
        </dl>
      )}
    </div>
  )
}
