import { useForm } from "@tanstack/react-form"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
import { TextField, SwitchField } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import { editRepoSchema, type EditRepoInput } from "../schemas"

function makeErrors(
  errs: (string | undefined)[],
): Array<{ message?: string }> | undefined {
  if (errs.length === 0) return undefined
  return errs.map((e) => ({ message: e ?? undefined }))
}

export function EditRepoDialog({
  open,
  onOpenChange,
  initial,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  initial: Partial<EditRepoInput>
  onSave: (v: EditRepoInput) => Promise<void>
}) {
  const form = useForm({
    defaultValues: {
      name: initial.name ?? "",
      path: initial.path ?? "",
      branch: initial.branch ?? "main",
      auto_sync: initial.auto_sync ?? true,
    },
    onSubmit: async ({ value }) => {
      const parsed = editRepoSchema.safeParse(value)
      if (!parsed.success) return
      await onSave(parsed.data)
      onOpenChange(false)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit repository</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            form.handleSubmit()
          }}
          className="space-y-3"
        >
          <form.Field
            name="name"
            validators={{
              onChange: ({ value }) => {
                const r = editRepoSchema.shape.name.safeParse(value)
                return r.success ? undefined : r.error.issues[0]?.message
              },
            }}
          >
            {(field) => (
              <TextField
                name={field.name}
                label="Name"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
                isInvalid={field.state.meta.errors.length > 0}
                errors={makeErrors(field.state.meta.errors)}
              />
            )}
          </form.Field>

          <form.Field
            name="path"
            validators={{
              onChange: ({ value }) => {
                const r = editRepoSchema.shape.path.safeParse(value)
                return r.success ? undefined : r.error.issues[0]?.message
              },
            }}
          >
            {(field) => (
              <TextField
                name={field.name}
                label="Path"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
                isInvalid={field.state.meta.errors.length > 0}
                errors={makeErrors(field.state.meta.errors)}
              />
            )}
          </form.Field>

          <form.Field name="branch">
            {(field) => (
              <TextField
                name={field.name}
                label="Branch"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
                isInvalid={field.state.meta.errors.length > 0}
                errors={makeErrors(field.state.meta.errors)}
              />
            )}
          </form.Field>

          <form.Field name="auto_sync">
            {(field) => (
              <SwitchField
                name={field.name}
                label="Auto-sync"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit">Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
