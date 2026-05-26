import { useForm } from "@tanstack/react-form"
import { useStore } from "@tanstack/react-store"
import { TextField, SelectField, SwitchField } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import { llmProfileSchema, type LLMProfileInput } from "../schemas"

const API_KIND_OPTIONS = [
  { value: "openai", label: "OpenAI-compatible" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "zai", label: "z.ai" },
  { value: "ollama", label: "Ollama" },
]

const REASONING_EFFORT_OPTIONS = [
  { value: "", label: "(none)" },
  { value: "none", label: "none" },
  { value: "low", label: "low" },
  { value: "medium", label: "medium" },
  { value: "high", label: "high" },
  { value: "xhigh", label: "xhigh" },
]

function makeErrors(
  errs: (string | undefined)[],
): Array<{ message?: string }> | undefined {
  if (errs.length === 0) return undefined
  return errs.map((e) => ({ message: e ?? undefined }))
}

export function LLMProfileForm({
  initial,
  onSave,
}: {
  initial: Partial<LLMProfileInput>
  onSave: (p: LLMProfileInput) => Promise<void>
}) {
  const form = useForm({
    defaultValues: {
      name: initial.name ?? "",
      api_kind: (initial.api_kind ?? "openai") as LLMProfileInput["api_kind"],
      model: initial.model ?? "",
      reasoning_effort: initial.reasoning_effort ?? ("" as string),
      supports_embedding: initial.supports_embedding ?? false,
    },
    onSubmit: async ({ value }) => {
      const normalized: LLMProfileInput = {
        name: value.name,
        api_kind: value.api_kind,
        model: value.model,
        reasoning_effort: value.reasoning_effort
          ? (value.reasoning_effort as LLMProfileInput["reasoning_effort"])
          : undefined,
        supports_embedding: value.supports_embedding,
        params: initial.params ?? {},
        thinking: initial.thinking,
        provider_ref: initial.provider_ref,
      }
      const parsed = llmProfileSchema.safeParse(normalized)
      if (!parsed.success) return
      await onSave(parsed.data)
    },
  })

  const isDirty = useStore(form.store, (s) => s.isDirty)

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
      className="space-y-4"
    >
      <form.Field
        name="name"
        validators={{
          onChange: ({ value }) => {
            const r = llmProfileSchema.shape.name.safeParse(value)
            return r.success ? undefined : r.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <TextField
            name={field.name}
            label="Profile name"
            value={field.state.value}
            onChange={(v) => field.handleChange(v)}
            onBlur={field.handleBlur}
            isInvalid={field.state.meta.errors.length > 0}
            errors={makeErrors(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Field
        name="api_kind"
        validators={{
          onChange: ({ value }) => {
            const r = llmProfileSchema.shape.api_kind.safeParse(value)
            return r.success ? undefined : r.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <SelectField
            name={field.name}
            label="API kind"
            value={field.state.value}
            onChange={(v) =>
              field.handleChange(v as LLMProfileInput["api_kind"])
            }
            onBlur={field.handleBlur}
            isInvalid={field.state.meta.errors.length > 0}
            errors={makeErrors(field.state.meta.errors)}
            options={API_KIND_OPTIONS}
          />
        )}
      </form.Field>

      <form.Field
        name="model"
        validators={{
          onChange: ({ value }) => {
            const r = llmProfileSchema.shape.model.safeParse(value)
            return r.success ? undefined : r.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <TextField
            name={field.name}
            label="Model"
            value={field.state.value}
            onChange={(v) => field.handleChange(v)}
            onBlur={field.handleBlur}
            isInvalid={field.state.meta.errors.length > 0}
            errors={makeErrors(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <form.Field name="reasoning_effort">
        {(field) => (
          <SelectField
            name={field.name}
            label="Reasoning effort"
            value={field.state.value}
            onChange={(v) => field.handleChange(v)}
            onBlur={field.handleBlur}
            isInvalid={field.state.meta.errors.length > 0}
            errors={makeErrors(field.state.meta.errors)}
            options={REASONING_EFFORT_OPTIONS}
          />
        )}
      </form.Field>

      <form.Field
        name="supports_embedding"
        validators={{
          onChange: ({ value }) => {
            const r = llmProfileSchema.shape.supports_embedding.safeParse(value)
            return r.success ? undefined : r.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <SwitchField
            name={field.name}
            label="Supports embedding"
            value={field.state.value}
            onChange={(v) => field.handleChange(v)}
            onBlur={field.handleBlur}
            isInvalid={field.state.meta.errors.length > 0}
            errors={makeErrors(field.state.meta.errors)}
          />
        )}
      </form.Field>

      <Button type="submit" disabled={!isDirty}>
        Save
      </Button>
    </form>
  )
}
