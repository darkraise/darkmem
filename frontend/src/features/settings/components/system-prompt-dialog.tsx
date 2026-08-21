import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import { Pencil, RotateCcw } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import { useSystemPrompts, useUpdateSystemPrompts } from "@/hooks/api"
import {
  PromptPanes,
  PromptViewToggle,
  type PromptViewMode,
} from "./prompt-view"

/** Mirrors the cap `PUT /config/system-prompts` enforces, so an over-long
 *  prompt is refused where it is typed rather than after a round-trip. */
const MAX_PROMPT_LENGTH = 20_000

/**
 * View and edit one system prompt.
 *
 * Reads `effective`, not `defaults`: an override is what the model — or, for
 * `agent_instructions`, the connecting MCP client — is actually served, so
 * showing the default would misreport the system whenever anyone has edited
 * it.
 *
 * Saving a draft that equals the in-code default clears the override rather
 * than storing a copy of it. The distinction outlives this dialog: a stored
 * copy pins the prompt to today's wording, so a later default improvement
 * silently never reaches an installation that once opened this editor and
 * pressed Save.
 */
export function SystemPromptDialog({
  open,
  onOpenChange,
  promptKey,
  title,
  description,
  emptyTitle = "No prompt is configured",
  emptyDescription = "This purpose resolves an empty system prompt, so the model is sent no instructions at all.",
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  promptKey: string
  title: string
  description: string
  emptyTitle?: string
  emptyDescription?: string
}) {
  const { data, isLoading, isError } = useSystemPrompts({ enabled: open })
  const update = useUpdateSystemPrompts()

  // Closing resets this state by unmounting: both callers render the dialog
  // behind a condition rather than toggling `open` on a mounted one, so there
  // is no state to clear on the way out. A caller that keeps it mounted would
  // reopen onto its own unsaved draft, which is the better of the two
  // behaviours anyway.
  const [view, setView] = useState<PromptViewMode>("plain")
  const [editing, setEditing] = useState(false)
  // Null means "not editing"; the draft only diverges from `effective` once
  // something is typed, so a refetch cannot overwrite what is being written.
  const [draft, setDraft] = useState<string | null>(null)

  const effective = data?.effective?.[promptKey] ?? ""
  const fallback = data?.defaults?.[promptKey] ?? ""
  const overridden = Boolean(data?.overrides && promptKey in data.overrides)

  const value = draft ?? effective
  const dirty = draft !== null && draft !== effective
  const tooLong = value.length > MAX_PROMPT_LENGTH

  function startEditing() {
    setDraft(effective)
    setEditing(true)
    // Split is the editing view: the source is being changed and the render
    // is how the change is judged.
    setView("split")
  }

  function save() {
    // An empty string is the API's "clear this override" signal, which is
    // also what a draft equal to the default means.
    const next = draft === fallback ? "" : (draft ?? "")
    update.mutate(
      { overrides: { [promptKey]: next } },
      {
        onSuccess: () => {
          setEditing(false)
          setDraft(null)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] max-w-4xl flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {title}
            <Badge variant={overridden ? "default" : "outline"}>
              {overridden ? "overridden" : "default"}
            </Badge>
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the prompt"
            description="The /config/system-prompts request failed — this is an error, not an empty prompt."
          />
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <PromptViewToggle value={view} onChange={setView} />
              <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
                {promptKey}
              </span>
              <span className="flex-1" />
              {!editing && (
                <Button variant="outline" onClick={startEditing}>
                  <Pencil aria-hidden className="size-[var(--icon-size)]" />
                  Edit
                </Button>
              )}
            </div>

            {editing ? (
              <div
                className={cn(
                  "grid min-h-0 flex-1 gap-2",
                  view === "split"
                    ? "grid-cols-1 sm:grid-cols-2"
                    : "grid-cols-1",
                )}
              >
                {view !== "markdown" && (
                  <Textarea
                    value={value}
                    aria-label={`${promptKey} system prompt`}
                    onChange={(e) => setDraft(e.target.value)}
                    className={cn(
                      "min-h-64 flex-1 resize-none font-mono text-sm",
                      tooLong && "border-destructive",
                    )}
                  />
                )}
                {view !== "plain" && (
                  <PromptPanes value={value} mode="markdown" />
                )}
              </div>
            ) : effective ? (
              <PromptPanes value={effective} mode={view} />
            ) : (
              <EmptyState
                kind="failed"
                title={emptyTitle}
                description={emptyDescription}
              />
            )}

            {editing && (
              <div className="flex flex-wrap items-center gap-2.5 pt-1">
                <span
                  className={cn(
                    "text-muted-foreground text-sm",
                    tooLong && "text-destructive",
                  )}
                >
                  {value.length.toLocaleString()} /{" "}
                  {MAX_PROMPT_LENGTH.toLocaleString()} characters
                </span>
                {update.isError && (
                  <span className="text-destructive text-sm">
                    {update.error.message}
                  </span>
                )}
                <Button
                  variant="ghost"
                  className="ml-auto"
                  disabled={value === fallback}
                  onClick={() => setDraft(fallback)}
                >
                  <RotateCcw aria-hidden className="size-[var(--icon-size)]" />
                  Reset to default
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setEditing(false)
                    setDraft(null)
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="outline"
                  className="border-primary/60 text-primary"
                  disabled={!dirty || tooLong || update.isPending}
                  onClick={save}
                >
                  Save
                </Button>
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
