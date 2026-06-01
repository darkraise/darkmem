import { useForm } from "@tanstack/react-form"
import { useStore } from "@tanstack/react-store"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "darkraise-ui/components/dialog"
import { CheckboxField } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import { reindexSchema, type ReindexInput } from "../schemas"

export function ReindexDialog({
  open,
  onOpenChange,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (v: ReindexInput) => Promise<void>
}) {
  const form = useForm({
    defaultValues: {
      full: false,
      enrich_symbols: false,
      generate_wiki: false,
    },
    onSubmit: async ({ value }) => {
      const parsed = reindexSchema.safeParse(value)
      if (!parsed.success) return
      await onConfirm(parsed.data)
      onOpenChange(false)
    },
  })

  const values = useStore(form.store, (s) => s.values)
  const wholeFormError =
    !values.full && !values.enrich_symbols && !values.generate_wiki
      ? "Pick at least one reindex action"
      : undefined

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reindex</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            form.handleSubmit()
          }}
          className="space-y-3"
        >
          <form.Field name="full">
            {(field) => (
              <CheckboxField
                name={field.name}
                label="Full reindex"
                description="Re-clone and rebuild the entire index from scratch."
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>

          <form.Field name="enrich_symbols">
            {(field) => (
              <CheckboxField
                name={field.name}
                label="Enrich symbols"
                description="Run LLM summarisation on code symbols."
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>

          <form.Field name="generate_wiki">
            {(field) => (
              <CheckboxField
                name={field.name}
                label="Generate wiki"
                description="Produce a wiki from indexed files."
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>

          {wholeFormError && (
            <p className="text-destructive text-base">{wholeFormError}</p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={!!wholeFormError}>
              Reindex
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
