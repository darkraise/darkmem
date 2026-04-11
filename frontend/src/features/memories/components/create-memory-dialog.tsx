import { useState } from "react"
import { useCreateMemory } from "@/hooks/api"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Textarea } from "darkraise-ui/components/textarea"
import { Label } from "darkraise-ui/components/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "darkraise-ui/components/dialog"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { toast } from "sonner"

const MEMORY_TYPES = [
  "fact",
  "decision",
  "problem",
  "preference",
  "reference",
  "architecture",
  "milestone",
] as const

const NONE_VALUE = "__none__"

interface CreateMemoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateMemoryDialog({ open, onOpenChange }: CreateMemoryDialogProps) {
  const [content, setContent] = useState("")
  const [source, setSource] = useState("manual")
  const [tagsInput, setTagsInput] = useState("")
  const [memoryType, setMemoryType] = useState<string>(NONE_VALUE)
  const [error, setError] = useState("")
  const createMemory = useCreateMemory()

  const resetForm = () => {
    setContent("")
    setSource("manual")
    setTagsInput("")
    setMemoryType(NONE_VALUE)
    setError("")
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) resetForm()
    onOpenChange(next)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    const trimmedContent = content.trim()
    if (trimmedContent.length === 0) {
      setError("Content is required")
      return
    }

    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0)

    const trimmedSource = source.trim()

    try {
      await createMemory.mutateAsync({
        content: trimmedContent,
        source: trimmedSource.length > 0 ? trimmedSource : "manual",
        tags: tags.length > 0 ? tags : undefined,
        memory_type: memoryType !== NONE_VALUE ? memoryType : undefined,
      })
      toast.success("Memory created")
      resetForm()
      onOpenChange(false)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create memory"
      setError(message)
      toast.error(message)
    }
  }

  const submitting = createMemory.isPending

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Memory</DialogTitle>
          <DialogDescription>
            Create a memory to save a fact, decision, or note. Content is required.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4" aria-label="Create memory">
          <div className="space-y-1">
            <Label htmlFor="create-memory-content">Content</Label>
            <Textarea
              id="create-memory-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What do you want to remember?"
              rows={5}
              autoFocus
              required
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="create-memory-source">Source</Label>
            <Input
              id="create-memory-source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="manual"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="create-memory-tags">Tags</Label>
            <Input
              id="create-memory-tags"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="comma, separated, tags"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="create-memory-type">Memory Type</Label>
            <Select value={memoryType} onValueChange={setMemoryType}>
              <SelectTrigger id="create-memory-type">
                <SelectValue placeholder="Select a type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE_VALUE}>(none)</SelectItem>
                {MEMORY_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && (
            <p role="alert" aria-live="assertive" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleOpenChange(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Memory"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
