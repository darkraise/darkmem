import { useEffect, useId, useRef, useState } from "react"
import { X } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Textarea } from "darkraise-ui/components/textarea"
import {
  TagsInput,
  TagsInputControl,
  TagsInputInput,
  TagsInputItem,
  TagsInputItemDeleteTrigger,
  TagsInputItemPreview,
  TagsInputItemText,
} from "darkraise-ui/components/tags-input"
import { toast } from "darkraise-ui/components/sonner"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
import type { DemoMemory } from "@/features/memories/types"
import { useUpdateMemory, type Memory } from "@/hooks/api/use-memory-api"
import { MEMORY_TYPE_OPTIONS } from "@/lib/taxonomy"

// A DemoMemory carries the fields this form edits directly (project,
// applies_when). The real update route (`MemoryUpdate`) takes no
// applies_when, so the real-mode edit hides that field and project and saves
// content, type and tags only. Real create never reaches this component at
// all (RealMemoriesView routes create through CreateMemoryDialog), so
// `memory` unset always means the demo create path.
function isDemoMemory(memory: DemoMemory | Memory): memory is DemoMemory {
  return "project" in memory
}

export interface MemoryEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** When set the dialog edits this memory; otherwise it creates one. */
  memory?: DemoMemory | Memory
  projects: string[]
  defaultProject?: string
}

export function MemoryEditorDialog({
  open,
  onOpenChange,
  memory,
  projects,
  defaultProject,
}: MemoryEditorDialogProps) {
  const addMemory = useDemoStore((s) => s.addMemory)
  const updateMemory = useDemoStore((s) => s.updateMemory)
  const updateRealMemory = useUpdateMemory()

  const [content, setContent] = useState("")
  const [memoryType, setMemoryType] = useState("fact")
  const [project, setProject] = useState(defaultProject ?? "default")
  const [tags, setTags] = useState<string[]>([])
  const [context, setContext] = useState("")
  const [contentError, setContentError] = useState(false)
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const contentRef = useRef<HTMLTextAreaElement>(null)
  const dialogContentRef = useRef<HTMLDivElement>(null)
  // The draft as it stood when the dialog opened (serialised); dismissal
  // asks before throwing away anything that differs from it.
  const [initialSnapshot, setInitialSnapshot] = useState("")
  const ids = useId()
  const projectLabelId = `${ids}-project-label`
  const typeLabelId = `${ids}-type-label`
  const tagsLabelId = `${ids}-tags-label`
  const contentErrorId = `${ids}-content-error`

  // Real mode never opens this dialog for create (RealMemoriesView routes
  // create through CreateMemoryDialog); the only real-mode entry is the
  // detail route's Edit action, which always passes a fetched Memory.
  const editingRealMemory = !DEMO && memory !== undefined

  useEffect(() => {
    if (!open) return
    setContent(memory?.content ?? "")
    setMemoryType(memory?.memory_type ?? "fact")
    setProject(
      (memory && isDemoMemory(memory) ? memory.project : undefined) ??
        defaultProject ??
        "default",
    )
    setTags(memory?.tags ?? [])
    setContext(
      (memory && isDemoMemory(memory) ? memory.applies_when : undefined) ?? "",
    )
    setContentError(false)
    setConfirmDiscard(false)
    setInitialSnapshot(
      snapshot(
        memory?.content ?? "",
        memory?.memory_type ?? "fact",
        (memory && isDemoMemory(memory) ? memory.project : undefined) ??
          defaultProject ??
          "default",
        memory?.tags ?? [],
        (memory && isDemoMemory(memory) ? memory.applies_when : undefined) ??
          "",
      ),
    )
  }, [open, memory, defaultProject])

  const dirty =
    snapshot(content, memoryType, project, tags, context) !== initialSnapshot

  // Every dismissal (Escape, outside click, Cancel, the close button) goes
  // through here so a typed draft is never dropped without a confirmation.
  const requestOpenChange = (next: boolean) => {
    if (next || !dirty) {
      onOpenChange(next)
      return
    }
    setConfirmDiscard(true)
  }

  const handleSubmit = () => {
    if (content.trim().length === 0) {
      setContentError(true)
      contentRef.current?.focus()
      return
    }
    if (editingRealMemory) {
      updateRealMemory.mutate(
        {
          id: memory.id,
          content: content.trim(),
          memory_type: memoryType,
          tags,
        },
        {
          onSuccess: () => {
            toast.success("Memory updated")
            onOpenChange(false)
          },
          onError: () => toast.error("Could not save the memory"),
        },
      )
      return
    }
    const now = new Date().toISOString()
    const appliesWhen = context.trim() || null
    if (memory) {
      updateMemory(memory.id, {
        content: content.trim(),
        memory_type: memoryType,
        project,
        tags,
        applies_when: appliesWhen,
        updated_at: now,
        timeline: [
          ...((isDemoMemory(memory) ? memory.timeline : undefined) ?? []),
          {
            at: now,
            kind: "updated",
            description: "object: this memory",
            note: "edited via dashboard",
          },
        ],
      })
      toast.success("Memory updated")
    } else {
      addMemory({
        id: crypto.randomUUID(),
        content: content.trim(),
        source: "dashboard",
        source_agent: null,
        memory_type: memoryType,
        importance: 5,
        metadata: {},
        technologies: [],
        tags,
        project,
        applies_when: appliesWhen,
        confidence: 0.75,
        status: "active",
        layer: 0,
        created_at: now,
        updated_at: now,
        expires_at: null,
        is_archived: false,
        classified_type: null,
        summary: null,
        emotions: [],
        flags: [],
        timeline: [
          {
            at: now,
            kind: "created",
            description: "object: this memory",
            note: "captured via dashboard (mock 202 Accepted)",
          },
        ],
      })
      toast.success("Memory created")
    }
    onOpenChange(false)
  }

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={requestOpenChange}
        closeOnEscape={false}
      >
        <DialogContent
          ref={dialogContentRef}
          className="sm:max-w-lg"
          onEscapeKeyDown={(event) => {
            if (isEscapeForDialog(event, dialogContentRef.current)) {
              requestOpenChange(false)
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>{memory ? "Edit memory" : "New memory"}</DialogTitle>
            <DialogDescription>
              Capture a fact, decision, or note. Content is required.
            </DialogDescription>
          </DialogHeader>
          <form
            aria-label={memory ? "Edit memory" : "Create memory"}
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit()
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="memory-content">Content</Label>
              <Textarea
                ref={contentRef}
                id="memory-content"
                aria-invalid={contentError || undefined}
                aria-describedby={contentError ? contentErrorId : undefined}
                rows={5}
                placeholder="What do you want to remember?"
                value={content}
                onChange={(e) => {
                  setContent(e.target.value)
                  if (e.target.value.trim()) setContentError(false)
                }}
              />
              {contentError && (
                <p
                  id={contentErrorId}
                  role="alert"
                  className="text-destructive text-sm"
                >
                  Content is required.
                </p>
              )}
            </div>

            <div
              className={
                editingRealMemory
                  ? "grid grid-cols-1 gap-4"
                  : "grid grid-cols-1 gap-4 sm:grid-cols-2"
              }
            >
              {!editingRealMemory && (
                <div className="space-y-1.5">
                  <Label id={projectLabelId}>Project</Label>
                  <Select value={project} onValueChange={setProject}>
                    <SelectTrigger aria-labelledby={projectLabelId}>
                      <SelectValue placeholder="Project" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-1.5">
                <Label id={typeLabelId}>
                  Memory type{" "}
                  <span className="text-muted-foreground font-mono text-sm uppercase">
                    optional hint
                  </span>
                </Label>
                <Select value={memoryType} onValueChange={setMemoryType}>
                  <SelectTrigger aria-labelledby={typeLabelId}>
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    {MEMORY_TYPE_OPTIONS.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-muted-foreground text-sm">
                  Classification runs regardless and may relabel it.
                </p>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label id={tagsLabelId}>Tags</Label>
              <TagsInput
                value={tags}
                onValueChange={({ value }) => setTags(value)}
              >
                <TagsInputControl>
                  {tags.map((tag, index) => (
                    <TagsInputItem key={tag} index={index} value={tag}>
                      <TagsInputItemPreview>
                        <TagsInputItemText>{tag}</TagsInputItemText>
                        <TagsInputItemDeleteTrigger>
                          <X aria-hidden className="size-3" />
                        </TagsInputItemDeleteTrigger>
                      </TagsInputItemPreview>
                    </TagsInputItem>
                  ))}
                  <TagsInputInput
                    aria-labelledby={tagsLabelId}
                    placeholder={tags.length === 0 ? "Add tags…" : ""}
                  />
                </TagsInputControl>
              </TagsInput>
            </div>

            {!editingRealMemory && (
              <div className="space-y-1.5">
                <Label htmlFor="memory-context">
                  Context{" "}
                  <span className="text-muted-foreground font-mono text-sm uppercase">
                    optional
                  </span>
                </Label>
                <Input
                  id="memory-context"
                  placeholder="e.g. env=prod"
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                />
                <p className="text-muted-foreground text-sm">
                  When this memory applies. Searches under a conflicting context
                  exclude it.
                </p>
              </div>
            )}

            <DialogFooter className="sm:items-center">
              <Button
                type="button"
                variant="ghost"
                className="w-full sm:w-auto"
                onClick={() => requestOpenChange(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="w-full sm:w-auto"
                disabled={updateRealMemory.isPending}
              >
                {memory ? "Save changes" : "Create memory"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <AlertDialog open={confirmDiscard} onOpenChange={setConfirmDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard this draft?</AlertDialogTitle>
            <AlertDialogDescription>
              {memory
                ? "Your edits to this memory have not been saved."
                : "The memory you started has not been captured."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmDiscard(false)
                onOpenChange(false)
              }}
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function snapshot(
  content: string,
  memoryType: string,
  project: string,
  tags: string[],
  context: string,
): string {
  return JSON.stringify([content, memoryType, project, tags, context])
}

// Escape inside an open Select (or the discard confirmation) must close only
// that layer. darkraise-ui gap: DismissableLayer decides "top layer" by DOM
// containment, and both the Select listbox and the AlertDialog are portalled
// outside the Dialog's node, so the Dialog also treats itself as top and one
// keypress closed the dropdown and the dialog together. The Dialog therefore
// runs with closeOnEscape off and closes itself only for a keypress aimed at
// it; one whose target sits in another portalled layer is that layer's.
// (preventDefault is no use here: every layer reads the one shared event, so
// it would stop the Select from closing too.)
function isEscapeForDialog(
  event: KeyboardEvent,
  dialogNode: HTMLElement | null,
): boolean {
  const target = event.target
  if (!dialogNode || !(target instanceof Node)) return true
  return target === document.body || dialogNode.contains(target)
}
