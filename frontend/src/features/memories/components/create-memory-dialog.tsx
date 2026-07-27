import { useForm } from "@tanstack/react-form"
import { useCreateMemory } from "@/hooks/api"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "darkraise-ui/components/dialog"
import { TextareaField, SelectField, FieldWrapper } from "darkraise-ui/forms"
import {
  TagsInput,
  TagsInputControl,
  TagsInputInput,
  TagsInputItem,
  TagsInputItemPreview,
  TagsInputItemText,
  TagsInputItemDeleteTrigger,
} from "darkraise-ui/components/tags-input"
import { toast } from "darkraise-ui/components/sonner"
import { MEMORY_TYPE_OPTIONS } from "@/lib/taxonomy"
import { createMemorySchema, type CreateMemoryInput } from "../schemas"

type MemoryTypeValue = CreateMemoryInput["memory_type"]

interface CreateMemoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateMemoryDialog({
  open,
  onOpenChange,
}: CreateMemoryDialogProps) {
  const createMemory = useCreateMemory()

  const form = useForm({
    defaultValues: {
      content: "",
      project: "default",
      memory_type: "fact" as MemoryTypeValue,
      tags: [] as string[],
    },
    onSubmit: async ({ value }) => {
      await createMemory.mutateAsync({
        content: value.content,
        memory_type: value.memory_type,
        tags: value.tags.length > 0 ? value.tags : undefined,
        source: "dashboard",
      })
      toast.success("Memory created")
      form.reset()
      onOpenChange(false)
    },
  })

  const handleOpenChange = (next: boolean) => {
    if (!next) form.reset()
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Memory</DialogTitle>
          <DialogDescription>
            Create a memory to save a fact, decision, or note. Content is
            required.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            form.handleSubmit()
          }}
          className="space-y-4"
          aria-label="Create memory"
        >
          <form.Field
            name="content"
            validators={{
              onChange: ({ value }) => {
                const result = createMemorySchema.shape.content.safeParse(value)
                return result.success
                  ? undefined
                  : result.error.issues[0]?.message
              },
            }}
          >
            {(field) => (
              <TextareaField
                name={field.name}
                label="Content"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
                placeholder="What do you want to remember?"
                rows={5}
                isInvalid={field.state.meta.errors.length > 0}
                errors={
                  field.state.meta.errors.length > 0
                    ? field.state.meta.errors.map((e) => ({
                        message: e ?? undefined,
                      }))
                    : undefined
                }
              />
            )}
          </form.Field>

          <form.Field name="memory_type">
            {(field) => (
              <SelectField
                name={field.name}
                label="Memory Type"
                value={field.state.value}
                onChange={(v) => field.handleChange(v as MemoryTypeValue)}
                onBlur={field.handleBlur}
                options={MEMORY_TYPE_OPTIONS}
                isInvalid={field.state.meta.errors.length > 0}
                errors={
                  field.state.meta.errors.length > 0
                    ? field.state.meta.errors.map((e) => ({
                        message: e ?? undefined,
                      }))
                    : undefined
                }
              />
            )}
          </form.Field>

          <form.Field name="tags">
            {(field) => (
              <FieldWrapper
                name={field.name}
                label="Tags"
                description="Press Enter or comma to add a tag"
                isInvalid={field.state.meta.errors.length > 0}
                errors={
                  field.state.meta.errors.length > 0
                    ? field.state.meta.errors.map((e) => ({
                        message: e ?? undefined,
                      }))
                    : undefined
                }
              >
                {() => (
                  <TagsInput
                    value={field.state.value}
                    onValueChange={({ value }) => field.handleChange(value)}
                  >
                    <TagsInputControl>
                      {field.state.value.map((tag, index) => (
                        <TagsInputItem key={tag} index={index} value={tag}>
                          <TagsInputItemPreview>
                            <TagsInputItemText>{tag}</TagsInputItemText>
                            <TagsInputItemDeleteTrigger />
                          </TagsInputItemPreview>
                        </TagsInputItem>
                      ))}
                      <TagsInputInput
                        placeholder={
                          field.state.value.length === 0 ? "Add tags…" : ""
                        }
                      />
                    </TagsInputControl>
                  </TagsInput>
                )}
              </FieldWrapper>
            )}
          </form.Field>

          {createMemory.isError && (
            <p
              role="alert"
              aria-live="assertive"
              className="text-destructive text-sm"
            >
              {(createMemory.error as Error).message}
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleOpenChange(false)}
              disabled={createMemory.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMemory.isPending}>
              {createMemory.isPending ? "Creating…" : "Create Memory"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
