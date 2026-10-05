import { useEffect, useState } from "react"
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
  }, [open, memory, defaultProject])

  const handleSubmit = () => {
    if (content.trim().length === 0) {
      setContentError(true)
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
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
              id="memory-content"
              rows={5}
              placeholder="What do you want to remember?"
              value={content}
              onChange={(e) => {
                setContent(e.target.value)
                if (e.target.value.trim()) setContentError(false)
              }}
            />
            {contentError && (
              <p role="alert" className="text-destructive text-sm">
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
                <Label>Project</Label>
                <Select value={project} onValueChange={setProject}>
                  <SelectTrigger>
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
              <Label>
                Memory type{" "}
                <span className="text-muted-foreground font-mono text-sm uppercase">
                  optional hint
                </span>
              </Label>
              <Select value={memoryType} onValueChange={setMemoryType}>
                <SelectTrigger>
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
            <Label>Tags</Label>
            <TagsInput
              value={tags}
              onValueChange={({ value }) => setTags(value)}
            >
              <TagsInputControl>
                {tags.map((tag, index) => (
                  <TagsInputItem key={tag} index={index} value={tag}>
                    <TagsInputItemPreview>
                      <TagsInputItemText>{tag}</TagsInputItemText>
                      <TagsInputItemDeleteTrigger />
                    </TagsInputItemPreview>
                  </TagsInputItem>
                ))}
                <TagsInputInput
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

          <DialogFooter className="items-center">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={updateRealMemory.isPending}>
              {memory ? "Save changes" : "Create memory"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
