import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import { Archive, Search, SearchX } from "lucide-react"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { useDemoFacts } from "@/demo/hooks"
import {
  distinctFactProjects,
  distinctFactRelations,
  filterFacts,
} from "@/demo/knowledge"
import type { DemoFact } from "@/demo/types"
import { ListSurface } from "./list-surface"
import { AppliesWhenChips, FactTriple } from "./fact-parts"

const STATUS_OPTIONS = ["candidate", "corroborated", "confirmed", "disputed"]

function FactRow({ fact }: { fact: DemoFact }) {
  const candidate = fact.verification_status === "candidate"
  const disputed = fact.verification_status === "disputed"
  return (
    <div
      className={cn(
        "border-border space-y-1.5 rounded-md border p-2.5",
        candidate && "bg-muted/15 border-dashed",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <LayerChip layer={2} />
        <VerificationBadge
          status={fact.verification_status}
          detail={fact.claim}
        />
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {disputed ? (
            <Link
              to="/knowledge/facts/$factId"
              params={{ factId: fact.id }}
              className="hover:text-primary transition-colors"
            >
              view both sides →
            </Link>
          ) : (
            fact.meta
          )}
        </span>
      </div>
      <Link
        to="/knowledge/facts/$factId"
        params={{ factId: fact.id }}
        className="hover:text-primary block space-y-1 transition-colors"
      >
        <FactTriple
          subject={fact.subject_name}
          rel={fact.rel_type}
          object={fact.object_name}
        />
        <p className="text-muted-foreground text-sm">
          {disputed && fact.dispute ? fact.dispute.summary : fact.fact_text}
        </p>
      </Link>
      {fact.verification_status === "corroborated" && (
        <p className="font-mono text-sm">{fact.claim}</p>
      )}
      <AppliesWhenChips items={fact.applies_when} />
      {fact.candidate_note && (
        <p className="text-muted-foreground text-sm">{fact.candidate_note}</p>
      )}
    </div>
  )
}

export function FactsTab() {
  const facts = useDemoFacts()
  const [subject, setSubject] = useState("")
  const [relation, setRelation] = useState("any")
  const [status, setStatus] = useState("any")
  const [project, setProject] = useState("darkmem")

  const relations = useMemo(() => distinctFactRelations(facts), [facts])
  const projects = useMemo(() => distinctFactProjects(facts), [facts])
  const scoped = useMemo(
    () => filterFacts(facts, { subject, relation, status, project }),
    [facts, subject, relation, status, project],
  )

  const projectLabel = project === "all" ? "all projects" : project
  const totalInProject = useMemo(
    () =>
      facts.filter((f) => project === "all" || f.project === project).length,
    [facts, project],
  )
  const filtered = subject.trim() !== "" || relation !== "any" || status !== "any"

  return (
    <div className="space-y-4">
      {/* Four distinct controls, never one ambiguous "filters" blob:
          subject free-texts, relation and status constrain their columns,
          project mirrors the global switcher (the isolation boundary). */}
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="subject — e.g. darkmem, hybrid_search…"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          groupClassName="min-w-56 flex-1"
          aria-label="Filter facts by subject"
        />
        <Select value={relation} onValueChange={setRelation}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Relation filter">
            <SelectValue>relation: {relation}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">any</SelectItem>
            {relations.map((rel) => (
              <SelectItem key={rel} value={rel}>
                {rel}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Status filter">
            <SelectValue>status: {status}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">any</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={project} onValueChange={setProject}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Project scope">
            <SelectValue>project: {projectLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <ListSurface
        title={`Facts — project: ${projectLabel}`}
        populated={scoped.length > 0}
        meta={`${scoped.length} of ${totalInProject} shown`}
      >
        {scoped.length > 0 ? (
          scoped.map((fact) => <FactRow key={fact.id} fact={fact} />)
        ) : filtered ? (
          <EmptyState
            icon={<SearchX aria-hidden className="h-6 w-6" />}
            title="No facts match these filters"
            description="Nothing was hidden — no fact in this scope matches the subject, relation, and status constraints. Widen a filter to see the rest."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setSubject("")
                  setRelation("any")
                  setStatus("any")
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          // Cold-start is not a generic empty state: the vault stays empty
          // of corroborated facts until distinct origins accumulate.
          <EmptyState
            icon={<Archive aria-hidden className="h-6 w-6" />}
            title="No corroborated facts yet"
            description="no corroborated facts yet; candidates are served labelled in search — corroboration takes multiple distinct origins across memory, code, and human review. Nothing here means not yet, not broken."
          />
        )}
      </ListSurface>
    </div>
  )
}
