import { useEffect } from "react"
import { useForm } from "@tanstack/react-form"
import { useStore } from "@tanstack/react-store"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
import { CheckboxField } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import { reindexSchema, type ReindexInput } from "../schemas"
import type { Repo } from "@/hooks/api"

// POST /repos/{id}/reindex accepts exactly {full, enrich_symbols,
// generate_wiki}, all default false — ported from
// features/repos/components/reindex-dialog.tsx's validated shape (T1.59).
export function RealReindexDialog({
  repo,
  open,
  onOpenChange,
  onConfirm,
  emphasizeWiki = false,
}: {
  repo: Repo | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (v: ReindexInput) => Promise<void>
  /** Opened from the Wiki empty state: pre-enable generate_wiki. */
  emphasizeWiki?: boolean
}) {
  const form = useForm({
    defaultValues: {
      full: !emphasizeWiki,
      enrich_symbols: false,
      generate_wiki: emphasizeWiki,
    },
    onSubmit: async ({ value }) => {
      const parsed = reindexSchema.safeParse(value)
      if (!parsed.success) return
      await onConfirm(parsed.data)
      onOpenChange(false)
    },
  })

  useEffect(() => {
    if (!open) form.reset()
  }, [open, form])

  const values = useStore(form.store, (s) => s.values)
  const wholeFormError =
    !values.full && !values.enrich_symbols && !values.generate_wiki
      ? "Pick at least one reindex action"
      : undefined

  if (!repo) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reindex — {repo.name}</DialogTitle>
          <p className="text-muted-foreground font-mono text-sm">
            {repo.last_indexed_commit
              ? `last indexed HEAD ${repo.last_indexed_commit}`
              : "never indexed"}
          </p>
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
                label="Full rebuild"
                description="Rebuild the whole graph instead of only the files changed since the last index."
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
                description="Summarise symbols with the LLM during this run instead of in the background."
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
                description="Write the wiki with the LLM after this run."
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>

          {wholeFormError && (
            <p
              id="real-reindex-form-error"
              role="alert"
              className="text-destructive text-sm"
            >
              {wholeFormError}
            </p>
          )}

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              disabled={!!wholeFormError}
              aria-describedby={
                wholeFormError ? "real-reindex-form-error" : undefined
              }
            >
              Run reindex
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
