import { useForm } from "@tanstack/react-form"
import { FieldWrapper } from "darkraise-ui/forms"
import { Button } from "darkraise-ui/components/button"
import {
  PasswordInput,
  PasswordInputControl,
  PasswordInputField,
  PasswordInputVisibilityTrigger,
  PasswordInputIndicator,
} from "darkraise-ui/components/password-input"
import { loginSchema } from "../schemas"
import { useLogin } from "../hooks/useLogin"
import { DEMO } from "@/lib/demo-flag"

export function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const login = useLogin()
  const form = useForm({
    defaultValues: { password: "" },
    onSubmit: async ({ value }) => {
      // Demo submit is a no-op: any password signs into the demo store.
      if (DEMO) {
        onSuccess()
        return
      }
      await login.mutateAsync(value)
      onSuccess()
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
      className="space-y-4"
    >
      <form.Field
        name="password"
        validators={{
          onChange: ({ value }) => {
            const result = loginSchema.shape.password.safeParse(value)
            return result.success ? undefined : result.error.issues[0]?.message
          },
        }}
      >
        {(field) => (
          <FieldWrapper
            name={field.name}
            label="Password"
            isInvalid={field.state.meta.errors.length > 0}
            errors={
              field.state.meta.errors.length > 0
                ? field.state.meta.errors.map((e) => ({
                    message: e ?? undefined,
                  }))
                : undefined
            }
          >
            {(isInvalid, ariaDescribedBy) => (
              <PasswordInput>
                <PasswordInputControl>
                  <PasswordInputField
                    id={field.name}
                    autoComplete="current-password"
                    autoFocus
                    value={field.state.value}
                    aria-invalid={isInvalid}
                    aria-describedby={ariaDescribedBy}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                  />
                  <PasswordInputVisibilityTrigger>
                    <PasswordInputIndicator />
                  </PasswordInputVisibilityTrigger>
                </PasswordInputControl>
              </PasswordInput>
            )}
          </FieldWrapper>
        )}
      </form.Field>

      <Button type="submit" disabled={login.isPending} className="w-full">
        {login.isPending ? "Signing in…" : "Sign in"}
      </Button>

      {login.isError && (
        <p
          role="alert"
          className="bg-destructive/15 text-destructive rounded-md px-3 py-2 text-sm"
        >
          {(login.error as Error).message}
        </p>
      )}
    </form>
  )
}
